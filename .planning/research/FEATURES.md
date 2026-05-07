# Feature Research — v2.0 Milestone Update

**Domain:** Windows + macOS IT audit executable — USB-portable, read-only PC inventory with RPG-themed HTML output
**Researched:** 2026-05-07
**Milestone:** v2.0 — Warnings, Mac Parity, Company Portal, NinjaOne Compatibility
**Confidence:** HIGH (primary paths), MEDIUM (Mac app paths), HIGH (HTML pattern)

---

## v2.0 Scope Summary

Four new feature areas on top of the v1.0 shipped base:

1. **Company Portal / Intune detection** (Windows, new collector)
2. **HTML warnings system** (collapsible box, OS EOL check, disk threshold check)
3. **Mac-compatible collectors** (full parity — same data models, same HTML output)
4. **NinjaOne remote execution compatibility** (SYSTEM context, stdout summary, no interactive session)

The v1.0 table stakes and differentiators (hostname decode, hardware stats, D&D HTML sheet, existing app detection) are already shipped and are NOT re-researched here.

---

## Feature 1: Company Portal / Intune Detection (Windows)

### What to Detect

Two distinct signals, both useful independently:

| Signal | What It Means | Detection Method |
|--------|--------------|-----------------|
| **Intune MDM enrollment** | Device is under Intune management policy | Registry: `HKLM\SOFTWARE\Microsoft\Enrollments\<GUID>` |
| **Company Portal app installed** | The Company Portal UWP app is present | Registry Uninstall keys + PowerShell Get-AppxPackage fallback |

### Intune Enrollment Detection — Specific Registry Paths

**Primary path (HIGH confidence — Microsoft Learn + multiple community sources):**

```
HKLM\SOFTWARE\Microsoft\Enrollments\<GUID>\
    ProviderID          = "MS DM Server"       ← confirms this is Intune, not MAM/other MDM
    DiscoveryServiceFullURL = "https://enrollment.manage.microsoft.com/..."
    EnrollmentType      = 6                    ← MDM full enrollment (not MAM = 1)
```

**How to read it in Python/winreg:**
- Open `HKLM\SOFTWARE\Microsoft\Enrollments` with `winreg.OpenKey`
- Enumerate all subkeys (GUIDs) with `winreg.EnumKey`
- For each subkey, read `ProviderID` — if any subkey has `ProviderID == "MS DM Server"`, device is Intune-enrolled
- Optionally read `EnrollmentType` (6 = MDM device enrollment; 1 = MAM = app-only, not full device enrollment)
- This key is readable by standard users — no elevation required

**Secondary confirmation path:**
```
HKLM\SOFTWARE\Microsoft\PolicyManager\Providers\<GUID>\
```
Presence of any GUID here confirms MDM policy is being applied. Less informative for version but confirms enrollment.

**Additional signal (co-management / Intune Management Extension):**
```
HKLM\SOFTWARE\Microsoft\IntuneManagementExtension\Win32Apps\
```
Presence indicates IME is active — used for Win32 app deployment via Intune. Not always present on freshly enrolled devices.

### Company Portal App Detection

Company Portal on Windows 10/11 is a **UWP/MSIX app**, not a traditional Win32 MSI. This means it does NOT appear under standard Uninstall keys at `HKLM\...\Uninstall`. Detection requires a different approach.

**Option A — PowerShell subprocess (MEDIUM complexity, reliable):**
```python
import subprocess
result = subprocess.run(
    ["powershell", "-NonInteractive", "-Command",
     "Get-AppxPackage -AllUsers -Name 'Microsoft.CompanyPortal' | Select-Object -ExpandProperty Version"],
    capture_output=True, text=True, timeout=10
)
version = result.stdout.strip()  # e.g. "11.2.502.0" or empty string
installed = bool(version)
```
- Works as standard user for system-provisioned apps (Intune-pushed Company Portal)
- For user-installed apps, may need `-AllUsers` (requires elevation) or per-user query
- PowerShell subprocess adds ~1-2s latency; acceptable for audit tool

**Option B — PackageManager registry path (LOW reliability, avoid):**
UWP apps do write to `HKCU\SOFTWARE\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\SystemAppData\Microsoft.CompanyPortal_*` but the path includes a hash component that changes per install. Fragile.

**Option C — Filesystem check (HIGH reliability as fallback):**
```
C:\Program Files\WindowsApps\Microsoft.CompanyPortal_*\
```
Directory exists if Company Portal is installed system-wide. Path contains version hash; use `glob` pattern match. Requires standard user access (WindowsApps is accessible, just not listable without admin in some configurations).

**Recommended implementation:** Option A (PowerShell) as primary, Option C (glob) as fallback. Return version string if found.

### RPG Theme Mapping

| Detection Result | D&D Display |
|-----------------|-------------|
| Intune-enrolled | "Realm Registry: Enrolled (Intune MDM)" — green |
| Company Portal installed | "Company Portal: Installed v{version}" |
| Neither | "Realm Registry: UNREGISTERED" — red warning |
| Portal installed, no MDM enrollment | "Company Portal: Installed (enrollment pending?)" — yellow |

### Complexity: MEDIUM
- Enrollment detection via winreg: LOW complexity (standard subkey enumeration)
- Company Portal version via PowerShell subprocess: MEDIUM (error handling, timeout, UWP path)
- Dependency: None — independent of existing collectors

---

## Feature 2: HTML Warnings System

### Warnings UX Pattern

**Recommended: Native HTML `<details>` + `<summary>` elements (CSS-styled)**

This is the correct approach for a self-contained HTML file with no JavaScript dependency:

```html
<details class="warnings-box" open>
  <summary class="warnings-header">
    ⚠ 2 Warnings Found — click to expand
  </summary>
  <div class="warnings-content">
    <div class="warning-item critical">
      OS End of Life: Windows 10 (Build 19045) — support ended October 14, 2025
    </div>
    <div class="warning-item moderate">
      Low Disk Space: C: drive is 12% free (18 GB of 150 GB available)
    </div>
  </div>
</details>
```

- `<details open>` renders expanded by default (correct for IT audit — warnings should be visible)
- Pure HTML5, zero JavaScript, works in all modern browsers
- CSS can style the summary marker, colors, and animation
- Accessible: keyboard-navigable, works with screen readers
- Fits the existing Jinja2 template rendering pipeline (conditional block if `warnings` list is non-empty)

**Interaction pattern:** Collapsed = summary line shows count. Expanded = each warning with severity styling.

### Warning 1: OS Version / EOL Check

**Thresholds (HIGH confidence — Microsoft official EOL dates confirmed):**

| OS | Build Range | Status | Warning Level |
|----|------------|--------|---------------|
| Windows 7 / 8.1 | < 10.0.10240 | CRITICAL — far past EOL | Critical |
| Windows 10 (any version) | 10.0.10240 – 10.0.19045 | WARNING — EOL October 14, 2025 | Critical (already past) |
| Windows 11 21H2 | 10.0.22000 | WARNING — early build, check update status | Moderate |
| Windows 11 22H2+ | 10.0.22621+ | OK — current supported branch | OK |
| Windows 11 23H2+ | 10.0.22631+ | OK — current supported branch | OK |

**Detection in Python (already collected in v1):**
- `platform.version()` returns `"10.0.19045"` format on Windows
- Parse major/build: `build = int(platform.version().split(".")[2])`
- `build < 22000` → Windows 10 or earlier → EOL warning
- `build >= 22000` → Windows 11 → OK (refine by specific build if needed)

**Warning text template:**
- Windows 10: "OS End of Life: This machine runs Windows 10 (Build {build}). Microsoft ended security updates on October 14, 2025. Upgrade required."
- Windows 11 early: "OS Version: Windows 11 build {build} is an early release. Confirm update policy is active."

### Warning 2: Disk Space Check

**Threshold formula (MEDIUM confidence — industry standard varies, 15% is reasonable):**

Standard monitoring practice uses a dual threshold approach:
- **Percentage-based:** Free space < 15% of total capacity
- **Absolute bytes floor:** Free space < 10 GB (catches edge case of large drives where 15% = lots of space but small drives where 15% = very little)

The warning fires if **either** condition is true. This matches enterprise monitoring tool defaults (SCOM uses percentage + MB dual threshold).

```python
import shutil
usage = shutil.disk_usage("C:/")  # already collected in v1
free_pct = (usage.free / usage.total) * 100
free_gb = usage.free / (1024 ** 3)
warn = free_pct < 15.0 or free_gb < 10.0
```

**Warning text:** "Low Disk Space: C: drive has {free_gb:.1f} GB free ({free_pct:.0f}% of {total_gb:.0f} GB). Performance and update installation may be affected."

**Dependency:** Uses existing `disk_usage` data already collected in `collectors/hardware.py` — no new collection needed.

### Jinja2 Template Integration

The warnings block should be conditionally rendered:

```jinja
{% if warnings %}
<details class="warnings-box" open>
  <summary>⚠ {{ warnings|length }} Warning{{ 's' if warnings|length != 1 else '' }}</summary>
  <div class="warnings-content">
    {% for w in warnings %}
    <div class="warning-item {{ w.level }}">{{ w.message }}</div>
    {% endfor %}
  </div>
</details>
{% endif %}
```

Where `warnings` is a list of `Warning(level: str, message: str)` dataclass instances passed into the template context.

### Complexity: LOW
- OS check: trivial — data already in `AuditReport`, add threshold logic in renderer
- Disk check: trivial — data already collected, add formula
- HTML: `<details>/<summary>` pattern is minimal CSS addition to existing Jinja2 template
- Dependency: Requires `AuditReport` to carry a `warnings: list[Warning]` field (new model field)

---

## Feature 3: Mac-Compatible Collectors

### Architecture Approach

The v1 architecture already abstracts OS-specific calls under `collectors/windows/`. Mac support adds `collectors/mac/` with the same interface — same `CollectionResult` envelope, same `AuditReport` data model, same HTML template output.

**Platform dispatch in `collectors/__init__.py`:**
```python
import sys
if sys.platform == "win32":
    from collectors.windows import cpu, ram, disk, os_info, profiles, apps
elif sys.platform == "darwin":
    from collectors.mac import cpu, ram, disk, os_info, profiles, apps
```

### Mac Hardware Collectors

**CPU (model name):**
- `psutil.cpu_count()` → core count (cross-platform, works on Mac including Apple Silicon)
- CPU model name: `platform.processor()` returns useful string on Intel Mac; returns `""` or `"arm"` on Apple Silicon
- **Preferred:** `subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], ...)` → returns full model string on both Intel and M-series
- Example output: `"Apple M2 Pro"` or `"Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz"`
- psutil `cpu_freq()` is unreliable on Apple Silicon — skip or handle `AttributeError`

**RAM:**
- `psutil.virtual_memory().total` — works on macOS (same as Windows, HIGH confidence)

**Disk:**
- `shutil.disk_usage("/")` — works on macOS, same as Windows
- Note: macOS uses `/` not `C:/`; disk path needs to be platform-conditional

**OS version:**
- `platform.mac_ver()` → returns `("14.5", ..., "arm64")` tuple
- macOS version name mapping: `14.x` = Sonoma, `13.x` = Ventura, `12.x` = Monterey, `11.x` = Big Sur
- Build number: `platform.mac_ver()[1]` → rarely needed for IT audit, version string sufficient

**Logged-in user:**
- `os.getlogin()` — works on macOS
- `os.environ.get("USER")` — fallback, works in SYSTEM-like contexts

### Mac Local User Profile Detection

```python
import subprocess
result = subprocess.run(
    ["dscl", ".", "-list", "/Users", "UniqueID"],
    capture_output=True, text=True
)
# Filter: UniqueID >= 501 = real human accounts; < 501 = system accounts
# Also filter: names starting with "_" are daemon accounts
```

Standard pattern (HIGH confidence — confirmed by macOS community):
- `dscl . list /Users | grep -v "^_"` — filters daemon accounts
- Filter by UID >= 501 to exclude system accounts like root, nobody, daemon
- Returns list of human user account names

Python subprocess equivalent provides same data as Windows `ProfileList` registry enumeration.

### Mac App Detection — Specific Paths

**Detection method: filesystem check on `.app` bundle + plistlib version read (HIGH confidence)**

The standard and most reliable macOS app detection approach:
1. Check if `/Applications/AppName.app` exists (`os.path.isdir`)
2. Read `/Applications/AppName.app/Contents/Info.plist` with `plistlib.load()`
3. Extract `CFBundleShortVersionString` for version, `CFBundleIdentifier` for verification

```python
import plistlib, os

def detect_mac_app(app_path: str) -> tuple[bool, str | None]:
    """Returns (installed, version_string)."""
    plist_path = os.path.join(app_path, "Contents", "Info.plist")
    if not os.path.isdir(app_path):
        return False, None
    try:
        with open(plist_path, "rb") as f:
            info = plistlib.load(f)
        return True, info.get("CFBundleShortVersionString")
    except (FileNotFoundError, Exception):
        return False, None
```

**Specific app paths and identifiers (confidence levels per source quality):**

| App | Primary Path | Bundle ID | Notes |
|-----|-------------|-----------|-------|
| NinjaRMM agent | `/Applications/NinjaRMMAgent/` | `com.ninjarmm.*` | Directory; plist at `programfiles/njbar.app/Contents/Info.plist` |
| CrowdStrike Falcon | `/Applications/Falcon.app` | `com.crowdstrike.falcon.App` | HIGH confidence — multiple MDM sources |
| Microsoft Word | `/Applications/Microsoft Word.app` | `com.microsoft.Word` | HIGH confidence — standard M365 path |
| Microsoft Excel | `/Applications/Microsoft Excel.app` | `com.microsoft.Excel` | HIGH confidence |
| Microsoft Outlook | `/Applications/Microsoft Outlook.app` | `com.microsoft.Outlook` | HIGH confidence |
| Microsoft Teams | `/Applications/Microsoft Teams.app` | `com.microsoft.teams2` (new Teams) | MEDIUM — Teams Classic was `com.microsoft.teams` |
| Zoom | `/Applications/zoom.us.app` | `us.zoom.xos` | HIGH confidence — standard install path |
| Google Chrome | `/Applications/Google Chrome.app` | `com.google.Chrome` | HIGH confidence — standard install path |
| Claude Desktop | `/Applications/Claude.app` | `com.anthropic.claudefordesktop` (inferred) | MEDIUM — Anthropic docs confirm `/Applications` install, bundle ID not officially documented in search results |
| MERP | N/A — Windows-only ERP | N/A | Out of scope for Mac; Mac template should show "N/A" or omit |

**NinjaRMM Mac-specific detection notes:**
- Primary filesystem check: `os.path.isdir("/Applications/NinjaRMMAgent")`
- LaunchDaemon presence as secondary signal: `/Library/LaunchDaemons/com.ninjarmm.agentd.plist`
- Version: read from `/Applications/NinjaRMMAgent/programfiles/njbar.app/Contents/Info.plist` → `CFBundleShortVersionString`
- HIGH confidence — NinjaOne official docs confirm `/Applications/NinjaRMMAgent/programfiles/ninjarmm-macagent` as the primary agent binary

**CrowdStrike Mac-specific detection notes:**
- Primary: `os.path.isdir("/Applications/Falcon.app")`
- Version: `/Applications/Falcon.app/Contents/Info.plist` → `CFBundleShortVersionString`
- Service status: `subprocess.run(["sudo", "falconctl", "stats"])` — requires elevation; degrade gracefully
- HIGH confidence — confirmed by Applivery, SimpleMDM, JumpCloud, Duke OIT documentation

**M365 Mac detection notes:**
- Each app installed separately to `/Applications/` — no suite registry entry (different from Windows)
- M365 subscription status NOT detectable without network call — just check if apps are present
- Teams: two possible paths — check both `Microsoft Teams.app` (classic) and `Microsoft Teams (work or school).app` (new)

### Mac Packaging Considerations

- No PyInstaller on macOS for v2 — the Mac collector is a Python script invoked directly or packaged separately
- `wmi` library is Windows-only — all WMI calls must be guarded with `sys.platform == "win32"` check (v1 already has `_WMI_AVAILABLE` guard pattern)
- `winreg` is Windows-only — same guard pattern needed
- `psutil` is cross-platform — use freely

### Complexity: HIGH
- New `collectors/mac/` module tree (cpu, ram, disk, os_info, profiles, apps)
- Platform dispatch logic in collector init
- plistlib-based version detection (new pattern, not used in Windows collectors)
- Testing requires macOS environment or mocking filesystem
- Dependency: Existing `AuditReport` data model must be shared; Mac collectors return same fields
- MERP is Windows-only — Mac template must handle absent MERP gracefully

---

## Feature 4: NinjaOne Remote Execution Compatibility

### Execution Context

When NinjaOne runs a script on a Windows device, it executes as **SYSTEM account** in a **non-interactive session**. Key implications for this tool:

| Factor | Implication |
|--------|-------------|
| SYSTEM account | No user profile loaded; `os.getlogin()` may raise `OSError`; `os.environ["USERNAME"]` = "SYSTEM" |
| Non-interactive | No console window; stdout is captured by NinjaOne's agent process |
| No display | HTML auto-open (`webbrowser.open()`) will silently fail or open in SYSTEM session desktop |
| Drive context | `sys.executable` points to where NinjaOne deployed the script, not a USB drive |
| Output capture | NinjaOne captures everything written to stdout |

### Stdout Output Format

NinjaOne captures the full stdout from script execution and displays it in the script activity log. The format is **plain text, human-readable**. There is no special JSON or key=value protocol for the results panel — the agent captures all `print()` output verbatim.

**For the NinjaOne use case, the tool should print a plain-text summary to stdout.** IT admin running the script via NinjaOne sees this output in the activity log immediately after execution.

**Recommended stdout summary format:**
```
=== StatusReport v2.0 Audit Summary ===
Host: PHX-INV-003
OS: Windows 11 (Build 22631) — OK
RAM: 16 GB
Disk: 245 GB free / 512 GB (47%)
NinjaOne: Installed v8.0.1.100
CrowdStrike: Installed v7.14.17106 — Active
Company Portal: Installed (Intune enrolled)
M365: Installed
Zoom: Installed v6.2.1
Chrome: Installed v124
Claude: Not installed
MERP: Not installed
Warnings: None
HTML report written to: C:\ProgramData\NinjaRMM\logs\PHX-INV-003_2026-05-07.html
=======================================
```

This is plain `print()` output — no special format needed. NinjaOne captures it wholesale.

### SYSTEM Context Fixes Required

**Problem 1: `os.getlogin()` crashes under SYSTEM:**
- `os.getlogin()` raises `OSError` in non-interactive sessions
- Fix: wrap in try/except; fallback to `os.environ.get("USERNAME", "SYSTEM")` or `os.environ.get("COMPUTERNAME")`
- The v1.0 architecture uses `CollectionResult(value, error)` envelope — this is the correct place to absorb the error

**Problem 2: Output path under NinjaOne:**
- `Path(sys.executable).parent` no longer points to USB drive — points to NinjaOne temp/deploy directory
- Fix: Add `--output-dir` CLI argument so IT admin can specify output path when invoking via NinjaOne
- Fallback: write to `Path(os.environ.get("TEMP", "C:/Temp"))` with hostname-timestamped filename

**Problem 3: HTML auto-open:**
- `webbrowser.open()` in SYSTEM session opens in session 0 desktop — invisible to user
- Fix: Skip auto-open if running as SYSTEM; detect with `os.environ.get("USERNAME", "") == "SYSTEM"`

**Problem 4: WMI under SYSTEM:**
- WMI is accessible from SYSTEM account — no change needed; existing WMI calls work
- CrowdStrike service state check via WMI will work correctly as SYSTEM

### NinjaOne Output Path Strategy

| Invocation Mode | Output Path Strategy |
|----------------|---------------------|
| USB (v1 mode) | `Path(sys.executable).parent / "logs/"` |
| NinjaOne (SYSTEM) | `--output-dir` CLI arg, or `C:\ProgramData\NinjaRMM\reporting\` as default |
| NinjaOne (user context) | `--output-dir` CLI arg, or user TEMP |

### Complexity: MEDIUM
- SYSTEM context guard: `os.environ.get("USERNAME") == "SYSTEM"` check
- `os.getlogin()` try/except already exists in v1 — confirm it propagates correctly
- `--output-dir` CLI argument: add to `main.py` argument parser
- Stdout summary: new function `print_summary(report: AuditReport)` called at end of main
- HTML auto-open guard: single conditional on SYSTEM check
- Dependency: requires `AuditReport` to be fully populated before stdout summary can print

---

## Updated Feature Dependencies (v2.0 additions)

```
Company Portal / Intune detection
    └──requires──> winreg (existing pattern)
    └──requires──> PowerShell subprocess for UWP app detection
    └──independent of──> existing app detectors (separate collector)
    └──enables──> "Realm Registry" RPG display field

Warnings system
    └──requires──> OS version (already in AuditReport.os_info)
    └──requires──> Disk usage (already in AuditReport.hardware.disk)
    └──requires──> New Warning dataclass + AuditReport.warnings field
    └──enables──> <details>/<summary> HTML warnings box in template

Mac collectors
    └──requires──> Platform dispatch (sys.platform == "darwin")
    └──requires──> subprocess + plistlib (stdlib — no new deps)
    └──requires──> dscl for user profiles (macOS-specific)
    └──shares──> AuditReport data model (unchanged)
    └──shares──> Jinja2 HTML renderer (unchanged — same template)
    └──conflicts--> wmi, winreg (must remain Windows-only behind guards)

NinjaOne compatibility
    └──requires──> os.getlogin() try/except (confirm existing v1 guard)
    └──requires──> --output-dir CLI argument (new argparse addition)
    └──requires──> print_summary() function (new)
    └──requires──> SYSTEM context guard for webbrowser.open()
    └──independent of──> HTML template (stdout is separate output channel)
```

---

## Anti-Features for v2.0

| Feature | Why Avoid | What to Do Instead |
|---------|-----------|-------------------|
| PowerShell for all app detection | Adds 1-2s per call; overkill for Win32 apps | PowerShell only for UWP (Company Portal); winreg for all else |
| mdfind on macOS for app detection | Spotlight index may be disabled/stale; unreliable in audit context | Direct filesystem check on `/Applications/*.app` — deterministic |
| popen("powershell Get-AppxPackage") without timeout | Hangs on machines with broken AppX stack | Always use `subprocess.run(..., timeout=10)` |
| Detecting all macOS apps in /Applications | Slow, noisy, not the goal | Fixed list only: NinjaOne, CrowdStrike, M365, Zoom, Chrome, Claude |
| JSON output to NinjaOne custom fields | Requires NinjaOne CLI integration; out of scope | Plain stdout summary is sufficient for v2 |
| Collapsible warnings with JavaScript | Adds complexity; breaks in restricted browser environments | `<details>/<summary>` is pure HTML5, zero JS |
| Interactive prompt in SYSTEM context | Will hang forever with no user to respond | All execution must be non-interactive; use `--output-dir` arg |

---

## v2.0 MVP Definition

### Must Ship (v2.0)

| Feature | Why | Complexity |
|---------|-----|------------|
| Intune enrollment detection via registry | Core compliance signal — is this device managed? | LOW |
| Company Portal detection via PowerShell | Secondary signal — is management app present? | MEDIUM |
| OS EOL warning (Win10 EOL = Oct 2025) | Every Win10 machine in the fleet needs upgrade action | LOW |
| Disk space warning (<15% or <10GB) | Actionable — IT needs to know before it causes problems | LOW |
| `<details>/<summary>` collapsible warnings box | UX requirement — warnings visible but non-obstructive | LOW |
| Mac hardware collectors (CPU, RAM, disk, OS) | Parity goal for Mac fleet | MEDIUM |
| Mac app detection (NinjaOne, CS, M365, Zoom, Chrome, Claude) | Same compliance check on Mac | MEDIUM |
| Mac user profile detection via dscl | Match Windows profile collector | LOW |
| SYSTEM context guard (`os.getlogin()` safe) | NinjaOne remote exec will fail without this | LOW |
| `--output-dir` CLI argument | Required for NinjaOne output path control | LOW |
| `print_summary()` stdout function | NinjaOne operators see results in activity log | LOW |
| HTML auto-open guard for SYSTEM context | Prevent broken open in session 0 | LOW |

### Defer to v2.x

| Feature | Reason |
|---------|--------|
| Code-signed .exe (DIST-V2-01) | Budget decision; CrowdStrike still passes without it |
| JSON log file (OUT-V2-01) | HTML sufficient; JSON adds complexity without immediate v2 value |
| Remote access tool detection (TeamViewer, AnyDesk, RDP) | Requires separate research; not in this milestone scope |
| macOS packaging (pkg/dmg) | Mac users invoke via Python directly for v2; packaging is v3 |
| NinjaOne custom field integration | Requires ninjarmm-cli; stdout summary achieves v2 goal |

---

## Sources

- [Microsoft Learn: Diagnose MDM enrollment failures](https://learn.microsoft.com/en-us/windows/client-management/mdm-diagnose-enrollment) — Enrollment registry paths (HIGH confidence)
- [IT trip: HKLM\SOFTWARE\Microsoft\Enrollments Explained](https://en.ittrip.xyz/windows/enrollments-registry-check) — ProviderID = "MS DM Server" pattern (MEDIUM confidence)
- [NinjaOne macOS Agent Installation](https://www.ninjaone.com/docs/new-to-ninjaone/agent-installation/macos-device-agent-installation/) — Mac install paths (HIGH confidence)
- [Applivery: CrowdStrike Falcon Sensor on macOS](https://www.applivery.com/docs/mobile-device-management/apple-mdm/macos/configure-crowdstrike-falcon-sensor-on-macos-devices/) — `/Applications/Falcon.app`, bundle ID (HIGH confidence)
- [Python docs: plistlib](https://docs.python.org/3/library/plistlib.html) — plist parsing standard library (HIGH confidence)
- [Apple Developer: Core Foundation Keys](https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/Articles/CoreFoundationKeys.html) — CFBundleShortVersionString definition (HIGH confidence)
- [DEV Community: Collapsible section with HTML only](https://dev.to/jordanfinners/creating-a-collapsible-section-with-nothing-but-html-4ip9) — `<details>/<summary>` pattern (HIGH confidence)
- [Microsoft Support: Windows 10 EOL October 14 2025](https://support.microsoft.com/en-us/windows/windows-10-support-has-ended-on-october-14-2025-2ca8b313-1946-43d3-b55c-2b95b107f281) — EOL date confirmed (HIGH confidence)
- [NinjaOne: Automation Script Variable Types](https://www.ninjaone.com/docs/endpoint-management/scripting-and-automation/automation-script-variable-types/) — SYSTEM context variables (MEDIUM confidence)
- [NinjaOne Removal Guide PDF](https://vector-nas01.direct.quickconnect.to/Public-FTP/Ninja_Removal/old/NinjaOne%20Removal%20Guide%20%E2%80%93%20NinjaOne%20Dojo.pdf) — LaunchDaemon paths com.ninjarmm.agentd.plist (MEDIUM confidence)
- [Anthropic: Deploy Claude Desktop for macOS](https://support.claude.com/en/articles/12611117-deploy-claude-desktop-for-macos) — installs to /Applications (HIGH confidence)
- [Paessler KB: Disk space threshold % vs bytes](https://kb.paessler.com/en/topic/79473-is-it-possible-to-set-xx-gb-free-space-as-threshold-instead-of-percent) — dual threshold pattern (MEDIUM confidence)
- [4iT: List User Accounts Mac OSX](https://4it.com.au/kb/article/list-user-accounts-mac-osx-using-terminal-command-line/) — dscl detection (HIGH confidence)
- [Jamf Community: dscl filter system accounts](https://community.jamf.com/t5/jamf-pro/dscl-command-to-list-local-users-but-exclude-system-accounts/m-p/45350) — UID >= 501 filter (HIGH confidence)

---

*Feature research for: StatusReport v2.0 milestone*
*Researched: 2026-05-07 — replaces v1.0 research dated 2026-05-04*
