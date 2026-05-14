# Feature Research — v3.0 Milestone

**Domain:** Windows IT audit executable — USB-portable, read-only PC inventory with RPG-themed HTML output
**Researched:** 2026-05-14
**Milestone:** v3.0 — System Health Collectors, Vendor Update Detection, Extended CLI Output
**Confidence:** HIGH (WUA API, psutil uptime, dataclass serialization), MEDIUM (DCU exit code behavior), LOW (LSU pending count — no passive registry path confirmed)

> **Scope note:** v1.0 and v2.0 features are shipped and unchanged. This file covers only v3.0 additions:
> HEALTH-01, HEALTH-02, WARN-04, VENDOR-01, VENDOR-02, OUT-V3-01, OUT-V3-02, CLI-V3-01.
> Prior research for v2.0 features is preserved in git history.

---

## Feature 1: Windows Pending Update Count via WUA (HEALTH-01)

### How It Works

The Windows Update Agent (WUA) is a COM-based API shipped with every modern Windows installation. Python accesses it via `win32com.client.Dispatch("Microsoft.Update.Session")` from the `pywin32` package (already a transitive dependency via `wmi`).

**The canonical search filter for pending updates is:**
```
"IsInstalled=0 and Type='Software' and IsHidden=0"
```

This is the default filter from Microsoft's own VBScript sample (`desktop-src/Wua_Sdk/searching--downloading--and-installing-updates.md`). It returns all applicable software updates that:
- Are not yet installed on this machine (`IsInstalled=0`)
- Are software (not drivers — use `Type='Driver'` separately if needed)
- Are not hidden (user has not explicitly deferred them)

**Minimal Python implementation:**
```python
import win32com.client

session = win32com.client.Dispatch("Microsoft.Update.Session")
searcher = session.CreateUpdateSearcher()
result = searcher.Search("IsInstalled=0 and Type='Software' and IsHidden=0")
count = result.Updates.Count
```

`count` is an integer representing all applicable, not-yet-installed updates known to the local WU service.

### What "Pending" Means

WUA does not distinguish between "downloaded-not-installed" and "available-not-downloaded" in the `IsInstalled=0` filter — both states return `IsInstalled=0`. "Pending" in this context means **any update Windows considers applicable but not yet installed**, regardless of whether it has been downloaded. The count is an "applicable-not-installed" count. This matches what IT staff expect when they ask "how many updates are pending."

If you want only updates that are downloaded and ready to install (closer to "immediately actionable"), add `IsDownloaded=1` to the filter. For an IT audit count, `IsInstalled=0` alone is the right signal.

### Privilege Requirement — Critical Constraint

**WUA interfaces require the caller to be in the Administrators group.** Standard user callers receive `E_ACCESSDENIED (HRESULT 0x80070005)`. The tool runs as standard user by default but runs as SYSTEM when invoked via NinjaOne. SYSTEM has administrative privileges, so the NinjaOne execution path works correctly.

**Implementation contract:** The WUA collector must be guarded with a `CollectionResult` envelope — catch `pywintypes.com_error` and return `CollectionResult(value=None, error="WUA: access denied (standard user)")`. The HTML template and JSON output must handle `None` gracefully (show "N/A" rather than crashing).

### Behavior on Machines With Windows Update Disabled / WSUS

| Configuration | Behavior |
|--------------|----------|
| Windows Update enabled, internet | Returns updates from Windows Update / Microsoft Update service |
| WSUS-managed machine | Returns updates from the WSUS server the machine is pointed to — still works, returns what WSUS has approved |
| Windows Update service disabled (wuauserv stopped) | `searcher.Search()` may return 0 updates or raise a COM error; treat as `None` with `"WU service disabled"` error message |
| Metered connection / update policy blocking scan | May return stale cached data or 0 — acceptable; count reflects current local state |
| Corporate policy blocks WUA API for non-admins | Returns `E_ACCESSDENIED` — caught by envelope pattern |

### Typical Count Range for IT Staff

- **0**: Machine is fully patched (common on fresh image or recently serviced machine)
- **1–5**: Normal operational state for a machine that was recently patched but missed a Patch Tuesday
- **5–20**: Machine not patched in 1–3 months; typical for unmanaged or lapsed NinjaOne coverage
- **20–100+**: Machine significantly behind; audit alert territory
- **100+**: Machine not patched in many months or Windows Update has been broken/disabled

**Useful threshold for display:** Show count as-is in the stat block. Flag as a warning if count > 10 (configurable constant `PENDING_UPDATES_WARN_THRESHOLD = 10`). The exact threshold is a policy call, not a technical one.

### Scan Latency Warning

WUA scan can take 10–60 seconds on first run or when the WU cache is cold. This is a known WUA behavior. For an IT audit tool this is acceptable, but consider running the WUA collector concurrently with other collectors if the pipeline supports it, or at minimum printing progress to stdout so NinjaOne logs show it is working.

**Anti-pattern to avoid:** Do not call `searcher.Search()` in a loop or with a retry — a single call is correct. Do not attempt to download or install updates (this tool is read-only).

### Table Stakes

| Behavior | Why Expected |
|----------|--------------|
| Returns an integer count | IT needs a number, not a list of update titles |
| Returns 0 correctly on patched machines | False positives erode trust |
| Handles access denied gracefully | Standard user invocation must not crash |
| Handles WU service disabled gracefully | Common on unmanaged machines being audited |

### Differentiators

| Behavior | Value |
|----------|-------|
| Surfaced in the HTML character sheet stat block | Makes update posture visible in the RPG-themed audit output |
| Available via `--json` / `--app` CLI flags | Enables NinjaOne to query update status without full pipeline |
| `PENDING_UPDATES_WARN_THRESHOLD` configurable constant | IT staff can tune the alert level |

### Anti-Features

| Anti-Feature | Why Avoid |
|-------------|-----------|
| Listing individual update titles | Slow, noisy, not the goal — count is enough |
| Installing or downloading updates | Core constraint: no changes to host PC |
| Driver updates in the same count | Drivers have different patch cadence; keep `Type='Software'` |
| Re-running scan on failure | WUA scan failures are usually environmental; retry adds latency for no benefit |

### Complexity: MEDIUM
- `win32com.client` pattern already established in the codebase for WMI
- Primary risk: WUA scan latency (10–60s); secondary risk: COM error handling
- Dependency: `pywin32` (already present via `wmi`); `_WMI_AVAILABLE` guard pattern must be replicated as `_WUA_AVAILABLE` guard

---

## Feature 2: Uptime Since Last Reboot (HEALTH-02 + WARN-04)

### How It Works

`psutil.boot_time()` returns a POSIX float timestamp (seconds since epoch) representing when the system last booted. Uptime in seconds is `time.time() - psutil.boot_time()`.

```python
import psutil, time

boot_ts = psutil.boot_time()
uptime_seconds = time.time() - boot_ts
uptime_days = int(uptime_seconds // 86400)
uptime_hours = int((uptime_seconds % 86400) // 3600)
```

`psutil.boot_time()` is cross-platform and available to standard users — no elevation required.

**Known issue:** On Windows, `psutil.boot_time()` can be inaccurate if the system clock was adjusted since boot (github.com/giampaolo/psutil/issues/2094). For an IT audit tool reading current uptime, this is immaterial — we're reading the OS-reported boot time, not performing forensic analysis. Treat it as authoritative.

### Recommended Display Format

**Format recommendation: `"X days Y hours"` spelled out (not abbreviated).**

Rationale: IT staff reading a NinjaOne log or an HTML audit sheet are not terminal power users — clarity beats brevity. The abbreviated form (`"3d 4h"`) is common in CLI tools targeted at sysadmins who live in terminals; the spell-out form is better for the mixed-audience IT staff reading this tool's output.

| Uptime | Display |
|--------|---------|
| 0 days, 4 hours | `"4 hours"` (omit "0 days") |
| 1 day, 0 hours | `"1 day"` (omit "0 hours") |
| 3 days, 14 hours | `"3 days 14 hours"` |
| 0 days, 0 hours | `"less than 1 hour"` (fresh boot) |
| 45 days, 2 hours | `"45 days 2 hours"` |

**Implementation:**
```python
def format_uptime(seconds: float) -> str:
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    if days == 0 and hours == 0:
        return "less than 1 hour"
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    return " ".join(parts)
```

### UPTIME_STALE Warning Threshold — WARN-04

**Recommendation: `UPTIME_STALE_DAYS = 14`**

Rationale:
- NinjaOne's own uptime alert UI suggests thresholds of 5, 15, 30, or 60 days as preset options (confirmed from NinjaOne policy documentation search). Their default suggestion for "endpoint health" alerts is in the 14–30 day range.
- Microsoft's Windows Update compliance deadline is typically set to 7 days from release; a machine that has not rebooted in 14 days has likely missed at least one Patch Tuesday cycle and failed to apply pending updates.
- 7 days is too aggressive for a warning-only audit tool — machines that get rebooted weekly may briefly show 6–7 days and not warrant a warning.
- 30 days is the upper bound most IT shops tolerate before escalating; 14 days is a reasonable middle ground for a "should probably reboot soon" signal.

**Make it a configurable constant** — `UPTIME_STALE_DAYS = 14` in `constants.py` — so the IT team can tune it without a code change. Document the value and rationale in a comment.

**Warning message:** `"Machine uptime is {days} days. Reboot recommended to apply pending updates and maintain system health."`

### Integration With Existing Warning System

`WARN-04` adds a third condition to the existing `warnings: list[Warning]` system established in v2.0. No new model fields required. The `collect_uptime()` collector returns a `CollectionResult` with uptime seconds as the value; the warning evaluator checks `uptime_days > UPTIME_STALE_DAYS` and appends a `Warning` object if true. This pattern is identical to `WARN-01` (OS version) and `WARN-02` (disk space).

### Table Stakes

| Behavior | Why Expected |
|----------|--------------|
| Shows uptime in the HTML stat block | Core health signal — reboot status is routine IT data |
| UPTIME_STALE warning fires correctly | IT needs to know when a machine hasn't been rebooted |
| Displays "less than 1 hour" for fresh boots | Graceful edge case handling |

### Differentiators

| Behavior | Value |
|----------|-------|
| Uptime included in `--json` output | NinjaOne workflows can check uptime programmatically |
| Warning threshold is a named constant | IT-tunable without code change |

### Anti-Features

| Anti-Feature | Why Avoid |
|-------------|-----------|
| Minutes-level granularity | Noise; days/hours is sufficient for audit context |
| Reboot history (multiple boot events) | Requires Windows Event Log parsing; out of scope |
| Uptime in seconds in JSON | Use days + hours integer fields; seconds is implementation detail |

### Complexity: LOW
- `psutil.boot_time()` is a single stdlib call, standard user, no COM overhead
- `format_uptime()` is pure arithmetic
- Warning threshold check is three lines
- Dependency: Existing `Warning` dataclass and `AuditReport.warnings` list (v2.0)

---

## Feature 3: Dell Command Update Pending Count (VENDOR-01)

### Architecture Reality

DCU does not maintain a persistent "pending update count" in the registry that can be read passively. **You cannot read a count without running DCU.** The options are:

1. **Run `dcu-cli.exe /scan` and parse exit code + XML output** (MEDIUM complexity, requires DCU installed and running)
2. **Parse `DCUApplicableUpdates.xml`** if it exists from a prior scan (LOW complexity, but only reflects last scheduled scan — may be stale)
3. **Registry-based installation detection only** (LOW complexity, confirms DCU is installed but gives no update count)

**Recommended approach for v3.0:** Two-tier.
- Tier 1: Detect DCU installation via registry (always do this)
- Tier 2: Check for `DCUApplicableUpdates.xml` and read the count from it (opportunistic — only if the file exists from a prior scheduled scan)
- Do NOT invoke `dcu-cli.exe` as part of the audit — the tool's core constraint is no changes to host and no long-running processes

### DCU Installation Detection

**Primary detection:** Standard Uninstall registry keys. DCU registers as a standard MSI application.

```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\
HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\
```

Search for `DisplayName` matching `"Dell Command | Update"` (exact string, case-insensitive). The GUID changes across versions. Read `DisplayVersion` for the installed version string.

**Secondary detection (configuration exists, DCU has run before):**
```
HKLM\SOFTWARE\DELL\UpdateService\Clients\CommandUpdate\Preferences\
```
Presence of this key confirms DCU has been configured and run at least once. Does not indicate update count.

**This is a Dell-only application.** Only check for DCU on machines where the hardware is a Dell. Hostname convention in this project does not encode hardware vendor, so DCU detection should run on all Windows machines but return `None` (not an error) on non-Dell machines — the collector just reports "not installed."

### DCU Pending Count — DCUApplicableUpdates.xml

DCU stores its last scan results at:
```
C:\ProgramData\dell\DCIUpdatesReport\DCUApplicableUpdates.xml
```

This file is written after every scheduled scan or manual `/scan` run. If it exists, it contains the list of applicable updates from the last scan. Parse the XML to count `<Update>` elements.

```python
import xml.etree.ElementTree as ET
from pathlib import Path

xml_path = Path("C:/ProgramData/dell/DCIUpdatesReport/DCUApplicableUpdates.xml")
if xml_path.exists():
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        count = len(root.findall(".//Update"))
    except ET.ParseError:
        count = None
else:
    count = None  # DCU installed but no scan has run, or scan results cleared
```

**Caveat:** This file reflects the last scheduled scan, not real-time state. The file's `mtime` can be checked to determine how stale the data is. For an IT audit this is acceptable — report count with "as of last scan" qualifier.

### DCU CLI Exit Codes (for documentation only — do NOT invoke)

If a future version of this tool opts to invoke DCU:
- Exit code `0`: Command succeeded (for `/scan`: scan ran, may or may not have found updates — check XML)
- Exit code `500`: No updates found during scan
- Other exit codes: Errors (Dell documents ~50 error codes in the v5.x reference guide)

The exit code does not directly tell you the count of updates found — you still need to parse the XML. This is why passive XML reading is the better approach.

### Table Stakes

| Behavior | Why Expected |
|----------|--------------|
| Reports DCU installed/not installed | Basic compliance signal — Dell machines should have DCU |
| Returns version number when installed | IT needs to know if DCU itself is current |
| Reports pending count when XML exists | Gives update posture without launching DCU |
| Returns None (not error) when no XML | Installed but no scan data is a valid state |

### Differentiators

| Behavior | Value |
|----------|-------|
| Reports XML staleness (mtime) | IT can see if last scan was recent |
| Available in `--app dcu` single-app flag | NinjaOne can check DCU status without full pipeline |

### Anti-Features

| Anti-Feature | Why Avoid |
|-------------|-----------|
| Invoking `dcu-cli.exe /scan` | Launches a process, may trigger update downloads, violates read-only constraint |
| Blocking on DCU scan (10–60s) | Unacceptable latency in audit context |
| Running DCU as standard user | DCU requires elevation; would fail silently or hang |
| Assuming Dell hardware from hostname | Hostname convention does not encode vendor |

### Complexity: LOW–MEDIUM
- Installation detection: LOW (standard winreg Uninstall enumeration — identical to existing app detectors)
- XML parsing: LOW (stdlib `xml.etree.ElementTree`, file read only)
- Primary risk: XML file may not exist (handle gracefully as `None`)
- Dependency: None — independent of existing app collectors

---

## Feature 4: Lenovo System Update Pending Count (VENDOR-02)

### Architecture Reality — Same Constraint as DCU

LSU also does not maintain a passive pending count in the registry. The same two-tier approach applies:

1. **Detect LSU installation via registry** (always)
2. **Passive state reading** — LSU uses WMI export (`-exporttowmi`) rather than an XML file; however, this requires having previously run LSU with the `-exporttowmi` flag, which is not guaranteed

LSU's `-exporttowmi` parameter writes update history to a WMI table, but it records update *history* (what was applied), not pending updates. There is no confirmed passive source for pending LSU update count short of invoking LSU.

**Recommended approach for v3.0:** Installation detection only. Report installed/not installed + version. Return `pending_count: None` with `pending_source: "not available without scan"`. This is honest — surfacing "Lenovo System Update: installed v5.08" is useful even without a count.

This is a deliberate scope reduction from the requirement spec. The requirement says "pending Lenovo System Update count" but there is no confirmed passive data source. Invoking LSU violates the read-only constraint. Document this as a known gap.

### LSU Installation Detection

**Primary detection:** Standard Uninstall registry keys.

```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TVSU_is1
HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\TVSU_is1
```

The key name `TVSU_is1` is the well-known Inno Setup registry key for Lenovo System Update (`TVSU` = ThinkVantage System Update, the historical name). Read `DisplayName` and `DisplayVersion`.

**Secondary paths (policy/config — do not use for detection):**
```
HKLM\SOFTWARE\WOW6432Node\Lenovo\System Update\Preferences\UserSettings\General
HKLM\Software\Policies\Lenovo\System Update\UserSettings\General
```
These are configuration keys, not installation indicators.

**This is a Lenovo-only application.** Same caveat as DCU — detect on all Windows machines, return `None` for "not installed" on non-Lenovo hardware.

### Why Not Invoke LSU

LSU invocation pattern (`tvsukernel.exe /CM -search A -action LIST -exporttowmi`) would:
- Launch a visible or background process
- Take 30–120 seconds to enumerate applicable updates from Lenovo's servers (or local repository)
- Require internet access or a local repository to return useful results
- Potentially write to `C:\ProgramData\Lenovo\` (host PC write — violates core constraint)

None of these are acceptable for this tool.

### Future Path for Pending Count

If a future version needs the pending count, the correct approach is to check the LSU WMI namespace after a scheduled LSU run:
```
ROOT\Lenovo\Tvsukernel (WMI namespace, accessible via wmi library)
```
Query the relevant class after LSU has run with `-exporttowmi`. This is LOW complexity once LSU has already run, but requires LSU to have been executed with that flag previously — not something the audit tool can guarantee.

### Table Stakes

| Behavior | Why Expected |
|----------|--------------|
| Reports LSU installed/not installed | Basic compliance — Lenovo machines should have LSU |
| Returns version number when installed | IT needs to know if LSU is current |
| Does not crash on non-Lenovo machines | Most machines in fleet are not Lenovo |

### Differentiators

| Behavior | Value |
|----------|-------|
| Available in `--app lsu` single-app flag | Consistent with other app flags |

### Anti-Features

| Anti-Feature | Why Avoid |
|-------------|-----------|
| Invoking `tvsukernel.exe` or `TvsuCommandLauncher.exe` | Launches process, requires internet/repo, violates read-only |
| Claiming a pending count from WMI without confirmation the flag was used | Would return stale or empty data and mislead IT |
| Treating LSU detection as a hard requirement for all machines | LSU only exists on Lenovo hardware |

### Complexity: LOW
- Registry detection via `TVSU_is1` key: trivial — identical pattern to existing app detectors
- Pending count: explicitly not implemented (documented gap)
- Risk: Key name may differ on older LSU versions (Inno Setup key name is stable across v5.x — HIGH confidence)

---

## Feature 5: JSON Serialization of AuditReport (OUT-V3-01)

### The Right Approach

**Use `dataclasses.asdict()` with a custom `default` handler in `json.dumps()`.**

`dataclasses.asdict()` recursively converts nested dataclasses to dicts — it does handle nesting correctly (the "shallow copy" warning in some articles refers to mutable containers like lists, not nested dataclasses themselves). The issue is that `asdict()` produces a dict but `json.dumps()` does not know how to serialize non-JSON-primitive types that survive the conversion.

**Types requiring special handling in this codebase:**

| Type | asdict() behavior | json.dumps() issue | Fix |
|------|------------------|-------------------|-----|
| `None` | Passes through as `None` | Serializes as JSON `null` — correct, no fix needed | None |
| `str`, `int`, `float`, `bool` | Passes through | Serialize correctly | None |
| `Path` objects | NOT recursed — `asdict()` returns the `Path` object as-is | `TypeError: Object of type PosixPath is not JSON serializable` | Convert to `str` in `default` handler |
| `Enum` members | NOT recursed — `asdict()` returns the enum member | `TypeError: Object of type MyEnum is not JSON serializable` | Return `.value` in `default` handler |
| `datetime` objects | NOT recursed | `TypeError` | Convert to `.isoformat()` in `default` handler |

**Check the actual `AuditReport` dataclass fields** for `Path` or enum types before implementing — the typical pattern in this codebase uses `str` for most fields, but `Path` may appear in output path fields.

**Implementation:**
```python
import dataclasses, json
from pathlib import Path
from enum import Enum

def _json_default(obj):
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def report_to_json(report: AuditReport, indent: int = 2) -> str:
    return json.dumps(dataclasses.asdict(report), default=_json_default, indent=indent)
```

**Why not a third-party library?**
- `orjson` is fast and handles dataclasses natively, but adds a binary dependency to a PyInstaller bundle — increases bundle size and introduces a packaging step. For this tool, `dataclasses.asdict()` + stdlib `json` is sufficient and keeps the dependency count flat.
- `dataclasses-json`, `pydantic`: same concern — unnecessary dependency for a straightforward serialization task.

### Field Name Convention

Use snake_case (Python convention) for JSON field names. Do not convert to camelCase — NinjaOne scripts consuming this JSON are PowerShell or Python; snake_case is fine for both and avoids a transformation layer.

### Output Destination — OUT-V3-02

`--json` writes to `logs/` by default (same directory as HTML output). `--output <path>` overrides the destination for both HTML and JSON.

**Two modes for `--json`:**
1. `--json` alone: write JSON to `<output_dir>/<hostname>_<date>.json`
2. `--json --stdout`: write JSON to stdout instead of file (useful for NinjaOne pipe capture)

The `--stdout` variant is important for NinjaOne integration — NinjaOne scripts can capture stdout and act on it without needing file I/O. Consider `--json-stdout` as a single flag rather than requiring two flags together.

### Table Stakes

| Behavior | Why Expected |
|----------|--------------|
| All AuditReport fields present in JSON | IT automation tools need complete data |
| Null fields serialize as JSON null, not omitted | Consistent schema for parsing |
| Snake_case field names | Python/PowerShell convention |
| Indented output (indent=2) | Human-readable for log inspection |

### Differentiators

| Behavior | Value |
|----------|-------|
| `--json-stdout` flag for pipe capture | NinjaOne can parse JSON without file access |
| Consistent schema even for error fields | Automation tools can always expect same keys |

### Anti-Features

| Anti-Feature | Why Avoid |
|-------------|-----------|
| camelCase conversion | Extra transformation layer; no benefit for target consumers |
| Third-party serialization library | Adds bundle complexity without benefit |
| Omitting None fields | Breaks schema consistency for automation consumers |
| Minified JSON (no indent) | Hard to inspect in NinjaOne log viewer |

### Complexity: LOW
- `dataclasses.asdict()` + `json.dumps()` is stdlib
- Custom `default` handler is ~5 lines
- Risk: discovering a Path or Enum field not anticipated — handled by the generic `_json_default` function

---

## Feature 6: --app Single-App Flag (CLI-V3-01)

### What Useful Output Looks Like

**For IT staff running from NinjaOne, the single-app flag must produce output that can be:**
1. Read at a glance in a NinjaOne activity log (plain text)
2. Parsed by a NinjaOne script or automation (JSON mode)

These are different use cases that need different formats. The `--app` flag without `--json` should print a single human-readable line. With `--json`, it should print a JSON blob to stdout.

**Plain text format (default):**
```
NinjaOne: Installed v8.0.1.100
CrowdStrike: Installed v7.14.17106 (service: Running)
MERP: Not installed
pending_updates: 12
uptime: 3 days 14 hours [WARNING: exceeds 14-day threshold]
dcu: Installed v5.1.0 (pending updates: 3, as of 2026-05-13)
lsu: Not installed
```

One line per check. Status first, then details. Warning flags inline. No headers, no decoration — this is machine-log output.

**JSON format (`--app <name> --json`):**
```json
{
  "app": "ninjaone",
  "installed": true,
  "version": "8.0.1.100",
  "details": {},
  "error": null
}
```

For health collectors:
```json
{
  "app": "pending_updates",
  "value": 12,
  "error": null
}
```

```json
{
  "app": "uptime",
  "value_seconds": 296400,
  "display": "3 days 14 hours",
  "stale": true,
  "threshold_days": 14,
  "error": null
}
```

**Key design decision:** `--app` must not run the full pipeline. It should invoke only the single relevant collector and print its result. This is the primary value of the flag — IT can query one thing quickly from NinjaOne without waiting for the full audit.

### App Name Aliases

The flag should accept friendly names, not internal collector names:

| Alias | Collector |
|-------|-----------|
| `ninjaone`, `ninja`, `ninjarmm` | NinjaOne app detector |
| `crowdstrike`, `cs`, `falcon` | CrowdStrike detector |
| `merp` | MERP detector |
| `m365`, `office` | M365 detector |
| `zoom` | Zoom detector |
| `chrome` | Chrome detector |
| `claude` | Claude desktop detector |
| `company-portal`, `intune` | Company Portal / Intune detector |
| `pending-updates`, `windows-updates`, `wu` | WUA pending update count |
| `uptime` | Uptime collector |
| `dcu` | Dell Command Update |
| `lsu` | Lenovo System Update |

Case-insensitive. Return a clear error message for unknown names: `"Unknown app: 'foo'. Valid options: ninjaone, crowdstrike, merp, ..."`.

### Integration With --json

`--app <name> --json` should print JSON to stdout. The JSON schema should be consistent enough that a NinjaOne PowerShell script can always do:

```powershell
$result = status_report.exe --app ninjaone --json | ConvertFrom-Json
if ($result.installed) { ... }
```

The `installed` field is boolean for app checks. The `value` field is used for numeric collectors (pending updates, uptime seconds). `error` is null on success, a string on failure.

### Table Stakes

| Behavior | Why Expected |
|----------|--------------|
| `--app <name>` exits immediately after single check | Speed — no waiting for full audit |
| Case-insensitive app name matching | IT staff type quickly; exact casing is friction |
| Clear error on unknown app name | Fail fast, don't silently return nothing |
| Exit code 0 on success | Scripts can check exit code |
| Exit code 1 on unknown app name or collector error | Script-friendly error detection |

### Differentiators

| Behavior | Value |
|----------|-------|
| `--app + --json` produces parseable JSON | Enables NinjaOne script automation |
| Friendly alias support | IT staff don't need to know internal names |
| Uptime and pending-updates as queryable "apps" | Treats health signals like app checks — consistent UX |

### Anti-Features

| Anti-Feature | Why Avoid |
|-------------|-----------|
| Running full pipeline on `--app` | Defeats the purpose; adds 10–60s for WUA scan |
| Requiring exact case-sensitive app names | Unnecessary friction |
| XML or structured plain text output (without --json) | Hard to read in NinjaOne log viewer |
| Printing headers/banners in `--app` output | Noise in log capture |

### Complexity: LOW–MEDIUM
- Argument parsing: LOW (argparse addition, existing pattern)
- Collector dispatch: MEDIUM (need a clean registry of app_name → collector function; avoid copy-pasting `if name == "ninjaone": ...` chains)
- Single-app JSON schema: LOW (consistent output dataclass or dict)
- Dependency: must not trigger full pipeline; `--app` exits via `sys.exit(0)` before `main()` pipeline runs (same pattern as existing `--name`, `--serial`, `--warnings` flags)

---

## v3.0 Feature Dependencies

```
HEALTH-01 (WUA pending count)
    └──requires──> pywin32 win32com.client (already present via wmi)
    └──requires──> _WUA_AVAILABLE guard (new, mirrors _WMI_AVAILABLE pattern)
    └──requires──> CollectionResult envelope (existing)
    └──requires──> Administrator/SYSTEM privilege at runtime (not guaranteed for standard user)
    └──enables──> HTML stat block field, --json output, --app pending-updates

HEALTH-02 (uptime) + WARN-04 (UPTIME_STALE)
    └──requires──> psutil.boot_time() (already present)
    └──requires──> UPTIME_STALE_DAYS constant (new in constants.py)
    └──requires──> Warning dataclass + AuditReport.warnings (existing from v2.0)
    └──enables──> HTML stat block field + warning box, --json output, --app uptime

VENDOR-01 (DCU)
    └──requires──> winreg Uninstall enumeration (existing pattern)
    └──requires──> xml.etree.ElementTree (stdlib, no new dep)
    └──requires──> C:\ProgramData\dell\DCIUpdatesReport\DCUApplicableUpdates.xml (file read, no new dep)
    └──enables──> HTML stat block field, --app dcu

VENDOR-02 (LSU)
    └──requires──> winreg Uninstall enumeration, TVSU_is1 key
    └──enables──> HTML stat block field, --app lsu
    └──NOTE──> Pending count NOT implemented (no passive data source confirmed)

OUT-V3-01 (--json)
    └──requires──> dataclasses.asdict() (stdlib)
    └──requires──> custom _json_default handler for Path/Enum
    └──requires──> AuditReport fully populated (all collectors run first)
    └──enables──> --json-stdout variant for NinjaOne pipe capture

OUT-V3-02 (--output <path>)
    └──requires──> argparse addition (existing pattern)
    └──enables──> NinjaOne output path control (supplements --output-dir from v2.0)

CLI-V3-01 (--app <name>)
    └──requires──> app name registry (new: dict mapping alias → collector function)
    └──requires──> --json flag awareness at arg-parse level
    └──exits before full pipeline (same pattern as --name, --serial, --warnings)
    └──enables──> NinjaOne single-check automation
```

---

## v3.0 MVP Definition

### Must Ship

| Feature | Why | Complexity |
|---------|-----|------------|
| `psutil.boot_time()` uptime collector | Zero-risk, no privilege required, always works | LOW |
| `UPTIME_STALE` warning (WARN-04) | Plugs into existing warning system cleanly | LOW |
| WUA pending update count | Core health signal for patch posture | MEDIUM |
| DCU installation detection + XML count | Passive, read-only, matches architecture | LOW |
| LSU installation detection (count deferred) | Honest scoping — installed/not is still useful | LOW |
| `dataclasses.asdict()` JSON serialization | Enables all downstream CLI and integration work | LOW |
| `--json` flag (file + stdout modes) | NinjaOne integration requires machine-readable output | LOW |
| `--output <path>` override | Needed for NinjaOne deployment context | LOW |
| `--app <name>` single-app check | High value for NinjaOne workflows | MEDIUM |

### Known Gap to Document

| Gap | Reason | Future Path |
|-----|--------|-------------|
| LSU pending count | No confirmed passive data source; invoking LSU violates read-only constraint | Read LSU WMI namespace (`ROOT\Lenovo\Tvsukernel`) after scheduled LSU run with `-exporttowmi` |
| WUA under standard user | Returns E_ACCESSDENIED; NinjaOne (SYSTEM) works fine | Document in `--help` output; CollectionResult captures error gracefully |
| DCU count staleness | XML reflects last scheduled scan, not real-time | Report file mtime alongside count |

---

## Sources

- [Microsoft Learn: Searching, Downloading, and Installing Updates (WUA VBScript sample)](https://learn.microsoft.com/en-us/windows/win32/wua_sdk/searching--downloading--and-installing-updates) — canonical `"IsInstalled=0 and Type='Software' and IsHidden=0"` filter (HIGH confidence)
- [Microsoft Learn: IUpdate::get_IsInstalled](https://learn.microsoft.com/en-us/windows/win32/api/wuapi/nf-wuapi-iupdate-get_isinstalled) — IsInstalled property semantics (HIGH confidence)
- [Microsoft Learn: Windows Update Agent API](https://learn.microsoft.com/en-us/windows/win32/api/_wua/) — API overview, privilege requirements (HIGH confidence)
- [psutil: boot_time issue #2094](https://github.com/giampaolo/psutil/issues/2094) — Windows clock adjustment caveat (MEDIUM confidence)
- [psutil: boot_time issue #658](https://github.com/giampaolo/psutil/issues/658) — Historical accuracy notes (MEDIUM confidence)
- [NinjaOne: Policy condition types (uptime thresholds)](https://www.ninjaone.com/docs/policies-and-conditions/conditions/policy-condition-types-explained/) — threshold reference (5, 15, 30, 60 days) (MEDIUM confidence)
- [Dell Command Update v5.x CLI Reference — Error Codes](https://www.dell.com/support/manuals/en-ca/command-update/dcu_rg/command-line-interface-error-codes) — exit code 0 (success) / 500 (no updates found) (MEDIUM confidence)
- [Dell Community: DCU Registry Keys](https://www.dell.com/community/en/conversations/dell-repository-manager/dell-command-update-registry-keys/647f9b9df4ccf8a8def8cb21) — `HKLM\SOFTWARE\DELL\UpdateService\Clients\CommandUpdate\Preferences` (MEDIUM confidence)
- [Silent Install HQ: DCU Detection Script](https://silentinstallhq.com/create-a-custom-detection-script-for-dell-command-update-powershell/) — Uninstall registry detection pattern (HIGH confidence)
- [Silent Install HQ: LSU Detection Script](https://silentinstallhq.com/create-a-custom-detection-script-for-lenovo-system-update-powershell/) — `TVSU_is1` registry key (HIGH confidence)
- [Lenovo CDRT: System Update Command Line Reference](https://docs.lenovocdrt.com/guides/sus/su_dg/su_dg_ch5/) — `-exporttowmi` parameter, `-action LIST` (MEDIUM confidence)
- [Lenovo CDRT: Appendix A Registry Paths](https://docs.lenovocdrt.com/guides/sus/su_dg/su_dg_ch6/) — confirmed no pending count in registry (HIGH confidence — absence confirmed)
- [Python docs: dataclasses.asdict](https://docs.python.org/3/library/dataclasses.html#dataclasses.asdict) — recursive dict conversion behavior (HIGH confidence)
- [Automox Community: Dell Command Update Worklet](https://community.automox.com/find-share-worklets-12/basic-dell-command-update-worklet-2278) — `DCUApplicableUpdates.xml` path confirmation (MEDIUM confidence)
- [Qualys: LSU Detection Script](https://github.com/Qualys/Custom-Assessment-and-Remediation-Script-Library/blob/main/Security%20Patch%20Update/Lenovo/Lenovo%20System%20Update%20for%20Windows%20Desktop,%20Notebook,%20Workstation/Lenovo%20System%20Update.ps1) — `TVSU_is1` detection cross-reference (HIGH confidence)

---

*Feature research for: StatusReport v3.0 milestone*
*Researched: 2026-05-14*
