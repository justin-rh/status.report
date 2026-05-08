# Phase 10: Mac Collectors - Research

**Researched:** 2026-05-08
**Domain:** macOS system collection — hardware, user profiles, app detection, launchd service state
**Confidence:** MEDIUM (bundle paths and daemon labels need live-Mac validation per STATE.md blocker)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Mac Execution Context**
- D-01: Tool is invoked as `python3 main.py` from the project directory on Mac. No Mac PyInstaller binary in v2.
- D-02: Output path on Mac: `Path(__file__).parent / "logs"` (relative to main.py). Windows keeps `Path(sys.executable).parent / "logs"`. The platform split lives inline in `main.py` as a two-line `if sys.platform == "darwin":` / `else:` block — no helper function.
- D-03: Mac interactive auto-open: `subprocess.run(["open", str(output_path)])` to open the HTML in the default browser. `sys.stdin.isatty()` guard already in place applies to Mac too.

**Collector Architecture**
- D-04: New `collectors/mac/` directory parallel to `collectors/windows/`. Contains `hardware.py` and `apps.py`. Same in-place mutation interface: `collect_hardware(report)`, `collect_profiles(report)`, `collect_apps(report)`.
- D-05: `collectors/__init__.py` dispatches by `sys.platform`: `"darwin"` imports from `collectors.mac`, anything else imports from `collectors.windows`. Same `collect_all(report)` entry point, no changes to callers.

**Mac Hardware Collection**
- D-06: macOS version: `subprocess.run(["sw_vers", "-productVersion"])` → `os_version`. Build: `subprocess.run(["sw_vers", "-buildVersion"])` → `os_build`.
- D-07: CPU model — platform-aware two-branch detection: Apple Silicon (`platform.machine() == "arm64"`) falls back to `system_profiler SPHardwareDataType` JSON for chip type. Intel (`platform.machine() == "x86_64"`) uses `sysctl -n machdep.cpu.brand_string`.
- D-08: RAM: `psutil.virtual_memory().total` — no new dependency.
- D-09: Disk: `psutil.disk_usage("/")` — root partition on Mac.
- D-10: Current user: `os.environ.get("USER")` or `os.getlogin()` on Mac.

**Mac User Profile Enumeration**
- D-11: `pwd.getpwall()` filtered to `pw_uid >= 501`. Extract `pw_name` for username.

**Mac App Detection**
- D-12: Primary detection: check if `.app` bundle exists in `/Applications/`. Parse `Info.plist` inside the bundle via `plistlib` stdlib for `CFBundleShortVersionString` → `version`.
- D-13: `collectors/mac/apps.py` contains a `MAC_APP_SPECS` table. Each entry declares `name`, `app_bundle`, and optional `launchdaemon_plist`.
- D-14: All 7 target apps: NinjaOne, CrowdStrike Falcon, Microsoft 365, Zoom, Google Chrome, Claude Desktop, Company Portal. MERP excluded (Windows-only ERP).
- D-15: CrowdStrike fallback: if `/Applications/Falcon.app` does not exist, check `/Library/LaunchDaemons/com.crowdstrike.falcond.plist`. If plist exists, `installed=True`.
- D-16: Same `detect_apps(report: AuditReport) -> None` interface — always appends one `AppStatus` per app, catches per-app exceptions into `report.collection_errors`.

**Service State on Mac**
- D-17: CrowdStrike and NinjaOne service state populated via `launchctl list <daemon-label>`. Exit code 0 → `service_state = "Running"`, non-zero → `service_state = "Stopped"`. Daemon labels: `com.crowdstrike.falcond` (CrowdStrike), NinjaOne label to be resolved at research time.
- D-18: All other Mac apps: `service_state = None`.

### Claude's Discretion
- Exact `system_profiler` JSON key names for Apple Silicon chip type
- NinjaOne LaunchDaemon label on Mac
- Whether `pwd.getpwall()` requires elevation to see all accounts
- Company Portal on Mac: exact bundle path
- Microsoft 365 on Mac: detection strategy (single suite app vs individual apps)
- How to mock `plistlib.load()` in unit tests

### Deferred Ideas (OUT OF SCOPE)
- Mac PyInstaller packaging (.app bundle + Gatekeeper notarization) — v3
- macOS-specific health warnings (SIP, Gatekeeper) — out of scope for v2
- MERP detection on Mac — Windows-only ERP
- GitHub Actions macOS CI runner for integration tests — deferred; Phase 10 uses mocked tests only for CI
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLAT-V2-01 | Tool collects Mac hardware stats — CPU model (Intel and Apple Silicon), total RAM, disk capacity and free space, macOS version | D-06 through D-10 are locked; research resolves the `system_profiler` JSON key name for Apple Silicon (see §macOS Hardware Collection) |
| PLAT-V2-02 | Tool enumerates all local user profiles on macOS (non-system accounts, UID >= 501) | D-11 is locked; research confirms `pwd.getpwall()` does not require elevation (see §macOS User Profile Enumeration) |
| PLAT-V2-03 | Tool detects 7 target apps on macOS: NinjaOne, CrowdStrike Falcon, Microsoft 365, Zoom, Google Chrome, Claude Desktop, Company Portal | D-12 through D-18 are locked; research resolves all 7 bundle paths and 2 daemon labels (see §macOS App Detection) |
| PLAT-V2-04 | Same D&D HTML character sheet rendered and saved on macOS runs (output to logs/ relative to exe) | D-01 through D-03 are locked; no renderer changes needed — collectors populate same AuditReport fields |
</phase_requirements>

---

## Summary

Phase 10 adds a parallel `collectors/mac/` implementation that mirrors `collectors/windows/` exactly at the interface level. All callers (`collect_all`, `main.py`, renderer, health_checks) remain unchanged. The only files that change are `collectors/__init__.py` (add `darwin` branch), `main.py` (add `sys.platform == "darwin"` output-path and open block), and the new `collectors/mac/hardware.py` and `collectors/mac/apps.py`.

The architecture is simple and all major decisions are locked. The primary research job was to resolve the five "Claude's Discretion" items in CONTEXT.md. All five are resolved below with confidence levels. The one item that remains LOW confidence (NinjaOne LaunchDaemon label) is a known fleet-validation gap documented in STATE.md and must be verified against a real Mac before the phase closes.

**Primary recommendation:** Implement the `collectors/mac/` module as a near-mirror of `collectors/windows/`, substituting `subprocess`/`psutil`/`plistlib`/`pwd` for `wmi`/`winreg`. The new module introduces zero new runtime dependencies — every tool (`subprocess`, `plistlib`, `pwd`, `platform`) is Python stdlib or already in `requirements.txt` (`psutil`).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Hardware stats collection | collectors/mac/hardware.py | subprocess (sw_vers, sysctl, system_profiler) | Mirrors Windows hardware.py; same AuditReport fields populated |
| User profile enumeration | collectors/mac/hardware.py | pwd stdlib | Parallel to Windows ProfileList registry walk; same field: report.local_profiles |
| App bundle detection | collectors/mac/apps.py | Path + plistlib stdlib | Primary method; version from Info.plist CFBundleShortVersionString |
| Service state detection | collectors/mac/apps.py | subprocess (launchctl) | CrowdStrike + NinjaOne only; others get service_state=None |
| Platform dispatch | collectors/__init__.py | — | Single `if sys.platform == "darwin":` branch; no callers change |
| Output path selection | main.py | — | Two-line inline if/else; no helper function per D-02 |
| HTML rendering | renderer/ (unchanged) | — | AuditReport fields are already platform-agnostic |
| Health checks | health_checks.py (unchanged) | — | evaluate_warnings() uses os_build and disk fields; both populated by Mac collectors |

---

## Standard Stack

### Core (all stdlib or already in requirements.txt)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `subprocess` | stdlib | sw_vers, sysctl, system_profiler, launchctl calls | Already used in Windows apps.py |
| `platform` | stdlib | `platform.machine()` for arm64 vs x86_64 detection | Already in Windows hardware.py |
| `psutil` | 6.x (already installed) | RAM via `virtual_memory().total`; disk via `disk_usage("/")` | No new install needed [VERIFIED: requirements.txt] |
| `plistlib` | stdlib | Parse Info.plist inside .app bundles; `plistlib.load(f)` | Python 3.4+; no install needed |
| `pwd` | stdlib (POSIX only) | `pwd.getpwall()` for user enumeration | Not available on Windows; Mac-only import in collectors/mac/ |
| `os` | stdlib | `os.environ.get("USER")` for current user | Already used in Windows hardware.py |
| `pathlib.Path` | stdlib | Bundle existence check (`Path("/Applications/Falcon.app").exists()`) | Already used project-wide |

**Installation:** No new packages. All tools are stdlib or already in `requirements.txt`.

### No New Dependencies

[VERIFIED: requirements.txt] The current requirements are `jinja2==3.1.6`, `psutil==6.*`, `wmi==1.5.1`. Phase 10 adds zero new entries to `requirements.txt`. The `wmi` package is Windows-only and never imported by Mac collectors; the lazy import pattern already in `collectors/__init__.py` keeps this safe.

---

## Architecture Patterns

### Recommended Project Structure

```
collectors/
├── __init__.py        # Add sys.platform == "darwin" branch
├── base.py            # Unchanged (stub/comment only)
├── windows/
│   ├── __init__.py
│   ├── hardware.py    # Unchanged
│   └── apps.py        # Unchanged
└── mac/               # NEW
    ├── __init__.py    # Empty (package marker)
    ├── hardware.py    # collect_hardware(), collect_profiles()
    └── apps.py        # collect_apps(), detect_apps(), MAC_APP_SPECS
```

### Pattern 1: Platform Dispatch in collectors/__init__.py

**What:** Two-branch `if sys.platform == "darwin":` / `else:` inside `collect_all()`.

**Example (mirrors existing lazy-import pattern from 02-01 decision):**
```python
def collect_all(report: AuditReport) -> None:
    import sys
    if sys.platform == "darwin":
        from collectors.mac.hardware import collect_hardware, collect_profiles
        from collectors.mac.apps import collect_apps
    else:
        from collectors.windows.hardware import collect_hardware, collect_profiles
        from collectors.windows.apps import collect_apps
    collect_hardware(report)
    collect_profiles(report)
    collect_apps(report)
```
[ASSUMED] The `import sys` inside the function follows the existing pattern where imports are lazy to keep `collectors/__init__.py` importable on non-native platforms.

### Pattern 2: main.py Output Path Split

**What:** Inline two-line `if sys.platform == "darwin":` block for output path and open call (D-02, D-03).

```python
import sys
if sys.platform == "darwin":
    usb_root = Path(__file__).parent          # script directory when run as python3 main.py
else:
    usb_root = Path(sys.executable).parent    # exe directory when run as frozen exe
logs_dir = usb_root / "logs"
# ... existing mkdir, filename, write logic unchanged ...

if sys.stdin.isatty():
    if sys.platform == "darwin":
        subprocess.run(["open", str(output_path)])  # macOS open command
    else:
        try:
            os.startfile(str(output_path))          # Windows os.startfile
        except OSError:
            pass
    input("\nPress Enter to close this window...")
```
[ASSUMED] The import `subprocess` is already in `main.py` (used for version checks); if not, it must be added.

### Pattern 3: Mac App Detection via Bundle + Info.plist

**What:** Check bundle path existence, then parse `Info.plist` for version.

```python
import plistlib
from pathlib import Path

def _detect_bundle(app_bundle: str) -> tuple[bool, str | None]:
    """Return (installed, version) for an /Applications/ bundle."""
    bundle_path = Path("/Applications") / app_bundle
    if not bundle_path.exists():
        return False, None
    plist_path = bundle_path / "Contents" / "Info.plist"
    try:
        with plist_path.open("rb") as f:
            data = plistlib.load(f)
        return True, data.get("CFBundleShortVersionString")
    except (OSError, plistlib.InvalidFileException, KeyError):
        return True, None   # Bundle exists but version unreadable — still installed
```
[VERIFIED: chromium.googlesource.com/chromium/reference_builds/chrome_mac — Info.plist contains CFBundleShortVersionString]
[CITED: docs.python.org/3/library/plistlib.html — `plistlib.load(fp)` reads binary or XML plist from a file object opened in binary mode]

### Pattern 4: Mac Hardware Collection — Apple Silicon CPU

**What:** Two-branch CPU detection depending on `platform.machine()`.

```python
import platform, subprocess, json

def _collect_cpu_model(report: AuditReport) -> None:
    arch = platform.machine()  # "arm64" on Apple Silicon, "x86_64" on Intel
    if arch == "x86_64":
        # Intel: sysctl returns "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz"
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5,
            )
            report.cpu_model = result.stdout.strip() or None
            return
        except Exception as exc:
            report.collection_errors.append(f"CPU model (sysctl) failed: {exc}")
    # Apple Silicon: sysctl machdep.cpu.brand_string may be absent on arm64.
    # Use system_profiler SPHardwareDataType JSON — key is "chip_type" on Apple Silicon.
    try:
        result = subprocess.run(
            ["system_profiler", "SPHardwareDataType", "-json"],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(result.stdout)
        hw = data["SPHardwareDataType"][0]
        # "chip_type" present on Apple Silicon (e.g. "Apple M3 Pro")
        # "cpu_type" present on Intel (fallback key)
        report.cpu_model = hw.get("chip_type") or hw.get("cpu_type") or None
    except Exception as exc:
        report.collection_errors.append(f"CPU model (system_profiler) failed: {exc}")
```
See §macOS Hardware Collection for key name confidence notes.

### Anti-Patterns to Avoid

- **Importing `winreg` or `wmi` in mac collectors:** Both are Windows-only. Mac collectors must never import them. The lazy import in `collectors/__init__.py` already enforces this boundary.
- **Using `sysctl machdep.cpu.brand_string` as the only path:** On Apple Silicon (arm64), this key returns either the Rosetta virtualized value or is absent depending on execution context. Always fall back to `system_profiler` for arm64.
- **Opening Info.plist in text mode:** `plistlib.load()` requires the file to be opened in binary mode (`"rb"`). Opening in text mode (`"r"`) causes a `TypeError`.
- **Relying on `launchctl list` exit code 0 as definitive "Running" proof:** Exit code 0 from `launchctl list <label>` means the label was found in the daemon registry; it does not guarantee the process has an active PID. This is the closest programmatic signal available without sudo, so it is acceptable for the tool's purpose, but it cannot distinguish "loaded but crashed" from "running normally." The CONTEXT.md D-17 decision accepts this behavior; document the limitation in a code comment.
- **Parsing `launchctl list` stdout for PID:** The output format of `launchctl list` is explicitly documented as "not API" by Apple and may change between macOS versions. Exit code interpretation is safer than stdout parsing.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Plist parsing | Custom XML parser | `plistlib.load()` (stdlib) | Handles both binary and XML plist formats; binary plists are common in app bundles |
| User enumeration | Directory walk of /Users/ | `pwd.getpwall()` (stdlib) | Directory walk misses accounts without home directories; `pwd` reads the actual user database |
| Disk stats | `df` subprocess + regex | `psutil.disk_usage("/")` | Already installed; cross-platform; no text parsing |
| RAM stats | `sysctl hw.memsize` | `psutil.virtual_memory().total` | Already installed; same call as Windows |
| macOS version | `defaults read` or regex | `sw_vers -productVersion` (stdlib shell cmd) | Standard, documented, stable; `platform.mac_ver()` is another option but sw_vers is already in the decisions |

**Key insight:** All needed tools are already installed or in stdlib. Zero new dependencies is a hard requirement for this phase.

---

## macOS Hardware Collection

### sw_vers — OS Version and Build

[VERIFIED: macOS man page via WebSearch + confirmed pattern used across macOS admin tools]

```bash
sw_vers -productVersion   # → "14.4.1"  (os_version)
sw_vers -buildVersion     # → "23E224"  (os_build)
```

The `os_version` field should be prefixed with "macOS " to match human-readable output: `f"macOS {version_string}"`. Example: `"macOS 14.4.1"`.

The Windows `_collect_os()` parses `platform.version()` to determine "Windows 11" vs "Windows 10". The Mac equivalent just prepends "macOS " to the sw_vers output — simpler. There is no need to reinterpret the build number for display (health_checks.py only uses `os_build` for the Windows 10 check; on Mac the check degrades cleanly because the build format differs).

### sysctl — Intel CPU Brand String

[VERIFIED: multiple macOS admin tools and official Apple documentation use this path]

```bash
sysctl -n machdep.cpu.brand_string
# → "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz"
```

Available on Intel Macs as a standard user with no elevation. Returns a descriptive string matching what users see in "About This Mac".

### system_profiler — Apple Silicon Chip Type

[MEDIUM confidence — key name derived from multiple community sources; not confirmed via direct Apple documentation]

The JSON output of `system_profiler SPHardwareDataType -json` has this structure:
```json
{
  "SPHardwareDataType": [
    {
      "_name": "hardware_overview",
      "chip_type": "Apple M3 Pro",
      "cpu_type": "ARM",
      "machine_name": "MacBook Pro",
      "machine_model": "Mac15,7",
      "physical_memory": "36 GB",
      "serial_number": "...",
      ...
    }
  ]
}
```

**Key resolution for "Claude's Discretion":**

| Key | Present on | Value example | Confidence |
|-----|-----------|---------------|------------|
| `chip_type` | Apple Silicon | `"Apple M3 Pro"` | MEDIUM [ASSUMED from community sources; not in official Apple JSON schema docs] |
| `cpu_type` | Intel and Apple Silicon | `"Intel Core i7"` / `"ARM"` | MEDIUM [ASSUMED — seen in community samples] |
| `machine_name` | Both | `"MacBook Pro"` | MEDIUM |

**Recommendation:** Use `hw.get("chip_type") or hw.get("cpu_type") or None`. On Apple Silicon, `chip_type` returns the friendly chip name (e.g., "Apple M3 Pro"). On Intel, `chip_type` may be absent; `cpu_type` returns the Intel processor family string. The fallback chain handles both.

**STATE.md blocker:** "system_profiler chip_type vs cpu_type — unit test fixtures needed from both Intel and Apple Silicon." Unit tests must parametrize across both key sets using mock JSON fixtures.

**Alternative (plist format, higher fidelity):**
```python
subprocess.run(["system_profiler", "SPHardwareDataType", "-xml"], ...)
# Then: plistlib.loads(result.stdout.encode())
# plist structure: list → dict["_items"] → list → dict["chip_type"]
```
The JSON format (`-json` flag) is simpler for Python consumption. Both produce equivalent data.

### psutil — RAM and Disk

[VERIFIED: requirements.txt confirms psutil 6.x installed; psutil cross-platform API documented]

```python
import psutil
ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
disk = psutil.disk_usage("/")   # "/" is the root partition on macOS
disk_total_gb = round(disk.total / (1024 ** 3), 1)
disk_free_gb = round(disk.free / (1024 ** 3), 1)
```

No changes from Windows calls except the path: `"C:\\"` → `"/"`.

---

## macOS User Profile Enumeration

### pwd.getpwall() — Elevation Not Required

[MEDIUM confidence — confirmed via Python stdlib documentation and macOS security model; no official Apple doc explicitly states "no elevation required"]

`pwd.getpwall()` reads `/etc/passwd` and the Open Directory database. On macOS, this returns all accounts visible to the running process without requiring root. Standard user processes can enumerate all local accounts.

**This resolves the "Claude's Discretion" item:** `pwd.getpwall()` does **not** require elevation to return all local accounts on macOS. [ASSUMED — based on POSIX semantics and community confirmation; not verifiable without a live Mac in this session]

**UID threshold:** macOS reserves UIDs below 500 for system accounts. Human accounts start at UID 501 by default (the first user created during macOS setup gets UID 501). [ASSUMED — consistent across macOS documentation and community sources]

**Pattern:**
```python
import pwd

def _enumerate_profiles() -> list[str]:
    """Return list of human account usernames (UID >= 501)."""
    profiles = []
    for entry in pwd.getpwall():
        if entry.pw_uid >= 501:
            profiles.append(entry.pw_name)
    return profiles
```

**Degradation pattern:** If `pwd.getpwall()` raises (e.g., on a system with broken Open Directory), the caller (`collect_profiles`) catches and logs to `collection_errors`, returning an empty list — identical to the Windows profile fallback.

**Note on UID 500:** Some references use >= 500. macOS assigns UID 501 to the first human account (UID 500 is reserved). Using >= 501 is the conservative and correct choice for this project. [ASSUMED — no Apple official doc reviewed in this session]

---

## macOS App Detection

### Resolution of All "Claude's Discretion" Bundle Paths

| App | Bundle Path | Version Source | Confidence |
|-----|-------------|----------------|------------|
| Google Chrome | `/Applications/Google Chrome.app` | `Info.plist CFBundleShortVersionString` | HIGH [CITED: chromium.googlesource.com — confirmed bundle name and Info.plist key] |
| Zoom | `/Applications/zoom.us.app` | `Info.plist CFBundleShortVersionString` | HIGH [CITED: zoom.us official docs + multiple admin tool references confirm `zoom.us.app`] |
| Claude Desktop | `/Applications/Claude.app` | `Info.plist CFBundleShortVersionString` | HIGH [CITED: support.claude.com/articles/10065433 — "launch from your Applications folder"] |
| Company Portal | `/Applications/Company Portal.app` | `Info.plist CFBundleShortVersionString` | HIGH [CITED: Microsoft Intune shell script samples: `open "/Applications/Company Portal.app"` — direct quote from official Microsoft script] |
| CrowdStrike Falcon | `/Applications/Falcon.app` | `Info.plist CFBundleShortVersionString` | HIGH [CITED: oit.duke.edu/kb0035361 — `sudo /Applications/Falcon.app/Contents/Resources/falconctl load`] |
| NinjaOne | `/Applications/NinjaRMMAgent/` (directory, not .app bundle) | N/A — directory existence check; version from `programfiles/ninjarmm-macagent` executable if present | MEDIUM [CITED: github.com/brokensound77 detection gist — path: `/Applications/NinjaRMMAgent/programfiles/ninjarmm-macagent`; NinjaOne removal script confirms `/Applications/NinjaRMMAgent` dir] |
| Microsoft 365 | Individual apps — see below | Per-app `Info.plist` | HIGH — no `Microsoft 365.app` monolithic bundle exists on Mac |

### Microsoft 365 on Mac — Resolution

[CITED: learn.microsoft.com/en-us/microsoft-365-apps/mac/overview — "The app bundle for each app, such as Word, includes all the resources needed to run the app. There aren't any shared resources among the apps."]

**There is no single `/Applications/Microsoft 365.app` bundle on macOS.** Microsoft 365 installs individual app bundles. The correct detection strategy that mirrors the Windows single-suite intent is to detect presence of **any one Microsoft 365 app**:

```
/Applications/Microsoft Word.app          → indicates suite installed
/Applications/Microsoft Excel.app
/Applications/Microsoft PowerPoint.app
/Applications/Microsoft Outlook.app
/Applications/Microsoft OneNote.app
```

**Recommended MAC_APP_SPECS entry for Microsoft 365:**
```python
{
    "name": "Microsoft 365",
    "app_bundle": "Microsoft Word.app",   # Primary sentinel app
    "fallback_bundles": [                 # Try these if Word missing
        "Microsoft Excel.app",
        "Microsoft PowerPoint.app",
        "Microsoft Outlook.app",
    ],
}
```

The detection reports `installed=True` with the version from whichever bundle is found first. The name shown in the HTML sheet remains "Microsoft 365" — matching the Windows output. This mirrors the Windows intent (D-13 from Phase 4: "suite detection") without requiring a monolithic bundle that does not exist.

**Alternative:** Check `Microsoft Word.app` only as the primary sentinel. If Word is not installed but Outlook is, this gives a false negative. The fallback list is safer.

### NinjaOne — Special Case: Directory, Not .app Bundle

[MEDIUM confidence — confirmed path `/Applications/NinjaRMMAgent/` from detection engineering gist and NinjaOne removal script; exact version file not confirmed]

NinjaOne installs as a **directory** at `/Applications/NinjaRMMAgent/` not a standard `.app` bundle. The primary detection check is:
```python
Path("/Applications/NinjaRMMAgent").is_dir()
```

Version: There is no `Info.plist` in `/Applications/NinjaRMMAgent/`. Version may be available from the binary or an internal plist, but not via the standard bundle mechanism. **Recommendation:** `version = None` for NinjaOne on Mac (acceptable — matches the tool's "Not Found" / detected-no-version pattern already used for some Windows apps).

### MAC_APP_SPECS Table — Recommended Design

```python
MAC_APP_SPECS: list[dict] = [
    {
        "name": "NinjaOne",
        "app_dir": "NinjaRMMAgent",                # Directory check (not .app)
        "launchdaemon_label": "com.ninjarmm.agent", # See §Service State below — LOW confidence
    },
    {
        "name": "CrowdStrike Falcon",
        "app_bundle": "Falcon.app",
        "launchdaemon_plist": "/Library/LaunchDaemons/com.crowdstrike.falcond.plist",
        "launchdaemon_label": "com.crowdstrike.falcond",
    },
    {
        "name": "Microsoft 365",
        "app_bundle": "Microsoft Word.app",
        "fallback_bundles": ["Microsoft Excel.app", "Microsoft PowerPoint.app", "Microsoft Outlook.app"],
    },
    {
        "name": "Zoom",
        "app_bundle": "zoom.us.app",
    },
    {
        "name": "Google Chrome",
        "app_bundle": "Google Chrome.app",
    },
    {
        "name": "Claude",
        "app_bundle": "Claude.app",
    },
    {
        "name": "Company Portal",
        "app_bundle": "Company Portal.app",
    },
]
```

---

## Service State Detection

### launchctl list `<label>` — Behavior and Limitations

[VERIFIED: ss64.com/mac/launchctl.html + multiple community sources]

`launchctl list <label>` returns:
- **Exit code 0** — the label was found in the launchd registry (daemon is loaded; may or may not be currently running with a PID)
- **Non-zero exit code** — the label was not found (daemon not loaded or wrong label)

**Important nuance:** Exit code 0 does NOT guarantee the process is currently running (has a PID). A daemon can be loaded (registered) but currently stopped after a crash. For this tool's purpose (audit snapshot), "loaded = Running" is the accepted approximation per D-17.

**Requires sudo?** `launchctl list` for system daemons in `/Library/LaunchDaemons/` requires the query to target the system domain. On macOS Monterey+, the correct invocation is `launchctl list <label>` (without `sudo`) which queries the system domain as a standard user. However, some macOS versions may require `sudo launchctl list`. Since this tool runs as standard user on Mac, **the `launchctl list` call should not use sudo** and must handle non-zero exits gracefully (treating them as "Stopped").

```python
import subprocess

def _query_launchd_service(label: str) -> str:
    """Return 'Running' if launchctl reports the daemon loaded, else 'Stopped'."""
    try:
        result = subprocess.run(
            ["launchctl", "list", label],
            capture_output=True, text=True, timeout=5,
        )
        return "Running" if result.returncode == 0 else "Stopped"
    except (OSError, subprocess.TimeoutExpired):
        return "Stopped"
```

### CrowdStrike Daemon Label — Resolution

[MEDIUM confidence — multiple sources reference both `com.crowdstrike.falcond` and `com.crowdstrike.falcon.Agent`]

The CrowdStrike Falcon sensor on macOS has multiple launchd entries:
- `/Library/LaunchDaemons/com.crowdstrike.falcond.plist` — the primary sensor daemon (older/common label)
- `/Library/LaunchDaemons/com.crowdstrike.falcon.Agent.plist` — system extension label (newer macOS versions)

**D-15 already locks the fallback behavior:** If `/Applications/Falcon.app` is absent, check for `/Library/LaunchDaemons/com.crowdstrike.falcond.plist`. This plist existence check is independent of the label used in `launchctl list`.

**D-17 uses `com.crowdstrike.falcond` as the daemon label.** This label is confirmed by multiple community sources including CrowdStrike scripts. [MEDIUM — not confirmed from official CrowdStrike macOS docs in this session]

**Recommendation:** Use `com.crowdstrike.falcond` as the primary label. If the service is not detected via launchctl, fall back to plist file existence check.

### NinjaOne Daemon Label — Resolution (LOW Confidence)

[LOW confidence — NinjaOne's removal script confirms daemons "contain ninjarmm in their names" but does not expose the exact label string]

Evidence gathered:
- The agent process is named `ninjarmm-macagent`
- LaunchDaemon files are located in `/Library/LaunchDaemons/` and contain "ninjarmm" in their names
- NinjaOne's MDM profile references the Remote component as `com.ninjarmm.ncstreamer`
- The Team ID is `EBNT3ZX97E`

**Best estimate for daemon label:** `com.ninjarmm.agent` (the most likely reverse-DNS label for the main agent process given the team name pattern). `com.ninjarmm.macagent` is another plausible variant.

**Recommendation for plan:** Use `com.ninjarmm.agent` as the primary label in MAC_APP_SPECS. Add a code comment marking this as unverified, referencing the STATE.md blocker. The planner should add a task to "Validate NinjaOne LaunchDaemon label on live Mac" as a pre-close step for this phase.

**STATE.md blocker explicitly calls this out:** "Validate NinjaOne Mac agent path against a real Mac in the fleet before Phase 10 closes."

---

## Test Strategy

### Overall Approach

All Mac collector tests run on Windows CI without a Mac. The test strategy is identical to the Windows pattern: patch all OS-specific calls at the module level so no real syscalls occur.

### How to Mock Each Mac-Specific Call

**subprocess.run (sw_vers, sysctl, system_profiler, launchctl):**
```python
import collectors.mac.hardware as hw_mod
from unittest.mock import patch, MagicMock

with patch.object(hw_mod.subprocess, "run") as mock_run:
    mock_run.return_value = MagicMock(stdout="14.4.1\n", returncode=0)
    # test body
```
Patch `subprocess` at the module level inside `collectors.mac.hardware` (not stdlib globally). This is the same pattern used for `_wmi_module` in Windows hardware.py.

**Path.exists() and Path.is_dir():**
```python
import collectors.mac.apps as apps_mod
from unittest.mock import patch

with patch.object(apps_mod.Path, "exists", return_value=True):
    # test body
```
Or use `unittest.mock.patch("collectors.mac.apps.Path")` to replace the whole class.

**plistlib.load() — Cleanest Pattern:**

The cleanest approach is to **patch `Path.open`** (which `_detect_bundle` calls) and make it return a fake file object, then patch `plistlib.load` to return a known dict:

```python
from unittest.mock import patch, mock_open, MagicMock
import plistlib

fake_plist_data = {"CFBundleShortVersionString": "4.60.0"}

with patch("collectors.mac.apps.Path.exists", return_value=True), \
     patch("collectors.mac.apps.plistlib") as mock_plib:
    mock_plib.load.return_value = fake_plist_data
    mock_plib.InvalidFileException = plistlib.InvalidFileException
    # test body
```

Alternative: patch `builtins.open` with `mock_open()` and also patch `plistlib.load`. The issue with patching `open` globally is fragility. **Recommended:** Import `plistlib` at module level in `collectors/mac/apps.py`, then patch `collectors.mac.apps.plistlib` in tests — same pattern as `collectors.windows.hardware._wmi_module`.

**pwd.getpwall():**
```python
import collectors.mac.hardware as hw_mod
from unittest.mock import patch, MagicMock

fake_entries = [
    MagicMock(pw_name="alice", pw_uid=501),
    MagicMock(pw_name="bob", pw_uid=502),
    MagicMock(pw_name="_daemon", pw_uid=1),
]
with patch.object(hw_mod.pwd, "getpwall", return_value=fake_entries):
    # test body
```
Import `pwd` at module level in `collectors/mac/hardware.py` so tests can patch `hw_mod.pwd.getpwall`.

### Intel vs Apple Silicon Fixture Parametrize

Tests must cover both hardware generations:
```python
import pytest

INTEL_SYSCTL_OUTPUT = "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz\n"
APPLE_SILICON_SP_JSON = json.dumps({
    "SPHardwareDataType": [{"chip_type": "Apple M3 Pro", "_name": "hardware_overview"}]
})

@pytest.mark.parametrize("machine,sysctl_out,sp_json,expected_cpu", [
    ("x86_64", INTEL_SYSCTL_OUTPUT, "", "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz"),
    ("arm64", "", APPLE_SILICON_SP_JSON, "Apple M3 Pro"),
])
def test_cpu_model_collection(machine, sysctl_out, sp_json, expected_cpu):
    import collectors.mac.hardware as hw_mod
    ...
```

### Test File Location

New files to create:
- `tests/test_mac_hardware_collector.py` — mirrors `tests/test_hardware_collector.py`
- `tests/test_mac_app_collector.py` — mirrors `tests/test_app_collector.py`
- `tests/test_mac_profile_collector.py` — mirrors `tests/test_profile_collector.py`

The `tests/__init__.py` and `conftest.py` (if any) need no changes — the new test files use the same `make_report()` helper pattern.

**CI compatibility:** All Mac collector tests must import on Windows. The `pwd` module is not available on Windows. The test files must guard their imports:
```python
import sys
if sys.platform == "darwin":
    import collectors.mac.hardware as hw_mod
# OR — better: import inside test functions, catching ImportError
```
Actually, since `collectors/mac/hardware.py` imports `pwd` at module level, importing it on Windows will raise `ImportError`. **Solution:** Wrap the `import pwd` in `collectors/mac/hardware.py` with a try/except and provide a `None` stub, identical to the `_wmi_module` pattern. Then tests can patch `hw_mod.pwd.getpwall` on any platform.

---

## Common Pitfalls

### Pitfall 1: `sysctl machdep.cpu.brand_string` Absent on Apple Silicon

**What goes wrong:** On arm64 Macs, `sysctl -n machdep.cpu.brand_string` may return empty string or raise an error because the Intel-specific sysctl node does not exist on ARM hardware.

**Why it happens:** The `machdep.cpu` namespace is Intel-specific.

**How to avoid:** Always branch on `platform.machine()`. Only call `sysctl machdep.cpu.brand_string` when `platform.machine() == "x86_64"`. For arm64, go directly to `system_profiler SPHardwareDataType -json`.

**Warning signs:** `cpu_model = None` on Apple Silicon with an error in `collection_errors` mentioning sysctl.

### Pitfall 2: `plistlib.load()` Requires Binary Mode

**What goes wrong:** `plistlib.load(f)` is called on a file opened in text mode (`"r"` or `open(path)`), raising `TypeError: a bytes-like object is required`.

**Why it happens:** `plistlib.load()` reads bytes, not strings. Both XML and binary plist formats require binary mode.

**How to avoid:** Always open with `"rb"`: `with plist_path.open("rb") as f: data = plistlib.load(f)`.

**Warning signs:** `TypeError` in `collection_errors` when version parsing runs.

### Pitfall 3: `zoom.us.app` Not `Zoom.app`

**What goes wrong:** Checking for `/Applications/Zoom.app` instead of `/Applications/zoom.us.app` — Zoom is not found on any Mac even when installed.

**Why it happens:** The Zoom macOS bundle follows a reverse-domain naming convention (`us.zoom.xos`), and the application bundle uses the domain-style name `zoom.us.app`.

**How to avoid:** Use `"zoom.us.app"` as the `app_bundle` value in MAC_APP_SPECS.

**Warning signs:** Zoom always reports "Not Found" even on machines with Zoom installed.

### Pitfall 4: pwd Import on Windows CI Breaks Test Collection

**What goes wrong:** `import collectors.mac.hardware` at test module level on Windows raises `ImportError: No module named 'pwd'`, causing pytest to fail to collect any tests in the file.

**Why it happens:** `pwd` is a POSIX-only stdlib module not present on Windows.

**How to avoid:** Apply the `_wmi_module` guard pattern in `collectors/mac/hardware.py`:
```python
try:
    import pwd as _pwd_module
    _PWD_AVAILABLE = True
except ImportError:
    _pwd_module = None
    _PWD_AVAILABLE = False
```
Then tests patch `hw_mod._pwd_module.getpwall` and `hw_mod._PWD_AVAILABLE`.

**Warning signs:** CI shows `ImportError` during test collection on Windows, not during test execution.

### Pitfall 5: NinjaOne Is a Directory, Not an `.app` Bundle

**What goes wrong:** Checking `Path("/Applications/NinjaRMMAgent.app").exists()` returns False on every Mac — NinjaOne does not install as an `.app` bundle.

**Why it happens:** NinjaOne's macOS agent installs into a flat directory `/Applications/NinjaRMMAgent/` containing the `programfiles/` subdirectory.

**How to avoid:** Use `Path("/Applications/NinjaRMMAgent").is_dir()` not `.exists()` on a `.app` path. The `MAC_APP_SPECS` entry needs an `app_dir` key distinct from `app_bundle` to signal directory-based detection.

### Pitfall 6: launchctl Domain Scope on Newer macOS

**What goes wrong:** `launchctl list com.crowdstrike.falcond` returns non-zero even when Falcon is running, because the daemon is registered in the system domain and `launchctl list` without `sudo` queries the user domain.

**Why it happens:** macOS Monterey+ distinguishes GUI/user launchd domains from the system domain. System daemons require `sudo launchctl list` or the domain qualifier `system/`.

**How to avoid:** Since this tool runs as standard user on Mac (D-01), accept that `launchctl list` without sudo may show "Stopped" for system daemons even when running. Treat this as a known limitation. The plist existence check (D-15 for CrowdStrike) is more reliable for installation detection. Service state for standard-user runs is best-effort.

**Mitigating approach:** Try `launchctl list <label>` first; if it fails, fall back to plist file existence at `/Library/LaunchDaemons/<label>.plist`. If plist exists but launchctl returned non-zero, set `service_state = "Unknown (check sudo)"` or just `"Stopped"`.

**Warning signs:** CrowdStrike service_state = "Stopped" on a Mac where Falcon is clearly running.

---

## Code Examples

### Complete MAC_APP_SPECS Detection Logic Sketch

```python
# collectors/mac/apps.py
# Source: Reference implementation from collectors/windows/apps.py structure

import json
import plistlib
import subprocess
from pathlib import Path

try:
    import plistlib as _plistlib_module
except ImportError:
    _plistlib_module = None  # type: ignore

from models import AuditReport, AppStatus

APPLICATIONS_DIR = Path("/Applications")
LAUNCH_DAEMONS_DIR = Path("/Library/LaunchDaemons")


def _detect_bundle(app_bundle: str) -> tuple[bool, str | None]:
    bundle_path = APPLICATIONS_DIR / app_bundle
    if not bundle_path.exists():
        return False, None
    plist_path = bundle_path / "Contents" / "Info.plist"
    try:
        with plist_path.open("rb") as f:
            data = plistlib.load(f)
        return True, data.get("CFBundleShortVersionString")
    except (OSError, plistlib.InvalidFileException, KeyError, Exception):
        return True, None  # Bundle exists, version unknown


def _query_launchd(label: str) -> str:
    try:
        result = subprocess.run(
            ["launchctl", "list", label],
            capture_output=True, text=True, timeout=5,
        )
        return "Running" if result.returncode == 0 else "Stopped"
    except (OSError, subprocess.TimeoutExpired):
        return "Stopped"
```

### main.py Darwin Branch

```python
# main.py additions — inline in main() after existing usb_root setup

import sys
if sys.platform == "darwin":
    usb_root = Path(__file__).parent
else:
    usb_root = Path(sys.executable).parent

# ... existing logs_dir, output_path, write logic ...

if sys.stdin.isatty():
    if sys.platform == "darwin":
        try:
            subprocess.run(["open", str(output_path)])
        except OSError:
            pass
    else:
        try:
            os.startfile(str(output_path))
        except OSError:
            pass
    input("\nPress Enter to close this window, then eject the USB drive.")
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `system_profiler` JSON key for Apple Silicon chip type is `chip_type` (e.g., "Apple M3 Pro") | macOS Hardware Collection | cpu_model = None on Apple Silicon; collector degrades gracefully but output is missing chip name |
| A2 | `pwd.getpwall()` does not require elevation on macOS for standard user | macOS User Profile Enumeration | Profile list returns empty; degradation is graceful but PLAT-V2-02 fails |
| A3 | NinjaOne LaunchDaemon label is `com.ninjarmm.agent` | Service State Detection | NinjaOne service_state always "Stopped" even when running; STATE.md blocker already tracks this |
| A4 | macOS human account UID threshold is >= 501 (not >= 500) | macOS User Profile Enumeration | May include or exclude borderline accounts; low risk since threshold is a constant |
| A5 | `import sys` inside `collect_all()` body (lazy import pattern) is already present | Architecture Patterns | collectors/__init__.py may need `import sys` added at top instead |
| A6 | `subprocess` is already imported in `main.py` | main.py Darwin Branch | `subprocess.run(["open", ...])` would NameError; easy fix |
| A7 | `com.crowdstrike.falcond` is the correct label for `launchctl list` | Service State Detection | CrowdStrike service_state unreliable; bundle + plist existence check (D-15) is independent and more reliable |

**Assumptions A1, A2, A3, A7 require live Mac validation per STATE.md blocker. The plan should include a "Validate on live Mac" task.**

---

## Open Questions

1. **NinjaOne LaunchDaemon exact label**
   - What we know: Daemons are in `/Library/LaunchDaemons/` with "ninjarmm" in filename; Remote component is `com.ninjarmm.ncstreamer`
   - What's unclear: The exact label string for the main agent daemon
   - Recommendation: Use `com.ninjarmm.agent` as best estimate; add a `# TODO: verify on live Mac` comment; plan must include a "validate NinjaOne daemon label" task

2. **system_profiler chip_type vs cpu_type key on Apple Silicon**
   - What we know: JSON output structure is `SPHardwareDataType[0]`; key names from community samples suggest `chip_type` for Apple Silicon
   - What's unclear: Whether Apple has changed this key name across macOS versions (Ventura vs Sonoma vs Sequoia)
   - Recommendation: Use `hw.get("chip_type") or hw.get("cpu_type")` fallback chain; parametrize tests with both Intel and Apple Silicon JSON fixtures

3. **launchctl standard-user access to system daemons**
   - What we know: macOS Monterey+ has domain scoping; `sudo launchctl list` may differ from unprivileged `launchctl list`
   - What's unclear: Whether `launchctl list com.crowdstrike.falcond` works without sudo on all supported macOS versions
   - Recommendation: Treat service_state as best-effort on Mac; document the limitation

---

## Environment Availability

The tool runs as `python3 main.py` on Mac (D-01). All tools used by Mac collectors are either stdlib or system commands:

| Dependency | Required By | Notes |
|------------|------------|-------|
| `sw_vers` | os_version, os_build | Ships with every macOS install since 10.0 |
| `sysctl` | Intel CPU model | Ships with every macOS install |
| `system_profiler` | Apple Silicon CPU model | Ships with every macOS install |
| `launchctl` | Service state | Ships with every macOS install |
| `open` | Auto-open HTML (main.py) | Ships with every macOS install |
| `psutil` 6.x | RAM, disk | Already in requirements.txt [VERIFIED] |
| `plistlib` | App version from Info.plist | Python stdlib, always available |
| `pwd` | User enumeration | Python stdlib POSIX-only — must guard import on Windows |
| `platform` | arch detection | Python stdlib, always available |

**No missing dependencies.** All required tools are pre-installed on macOS or already in requirements.txt.

---

## Sources

### Primary (HIGH confidence)
- [Microsoft Intune macOS Company Portal docs](https://learn.microsoft.com/en-us/intune/app-management/deployment/add-company-portal-macos) — confirms `/Applications/Company Portal.app`
- [Microsoft shell-intune-samples Company Portal script](https://github.com/microsoft/shell-intune-samples/tree/master/macOS/Apps/Company%20Portal) — `open "/Applications/Company Portal.app"` verbatim
- [Microsoft 365 Apps for Mac Overview](https://learn.microsoft.com/en-us/microsoft-365-apps/mac/overview) — "app bundle for each app... no shared resources" — confirms no monolithic Microsoft 365.app
- [CrowdStrike Falcon macOS bundle path](https://oit.duke.edu/help/articles/kb0035361/) — `/Applications/Falcon.app/Contents/Resources/falconctl`
- [NinjaOne detection engineering gist](https://gist.github.com/brokensound77/6d8a1e480e65ff20e151099c98267b14) — `/Applications/NinjaRMMAgent/programfiles/ninjarmm-macagent`
- [NinjaOne removal script](https://www.ninjaone.com/docs/scripting-and-automation/custom-scripts/remove-endpoint-agent-macos-custom-scripts/) — `/Applications/NinjaRMMAgent` directory, LaunchDaemons with "ninjarmm" in names
- [Zoom bundle reference: zoom.us.app](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0064957) — confirmed `zoom.us.app` bundle name and `us.zoom.xos` bundle ID
- [chromium.googlesource.com Google Chrome Info.plist](https://chromium.googlesource.com/chromium/reference_builds/chrome_mac/+/43a9e3be5957581876a77de737bb82c568e37fd7/Google%20Chrome.app/Contents/Info.plist) — confirms `/Applications/Google Chrome.app` and `CFBundleShortVersionString` key
- [support.claude.com Install Claude Desktop](https://support.claude.com/en/articles/10065433-install-claude-desktop) — Claude Desktop installs to Applications folder as `Claude.app`

### Secondary (MEDIUM confidence)
- [CrowdStrike daemon label com.crowdstrike.falcond](https://inventivehq.com/knowledge-base/crowdstrike/how-to-verify-the-crowdstrike-falcon-sensor-is-running-properly) — references falcond daemon
- [ss64.com launchctl documentation](https://ss64.com/mac/launchctl.html) — launchctl exit code behavior
- system_profiler SPHardwareDataType JSON key names from community DEV.to and osxdaily sources — `chip_type` for Apple Silicon

### Tertiary (LOW confidence — needs live-Mac validation)
- NinjaOne LaunchDaemon label `com.ninjarmm.agent` — inferred from agent process name and team pattern
- `pwd.getpwall()` no-elevation claim — POSIX semantics + community confirmation, not Apple official doc
- `system_profiler` `chip_type` key present across all macOS 13/14/15 versions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib or existing requirements.txt
- Architecture: HIGH — locked decisions + reference implementation in collectors/windows/
- Bundle paths: HIGH for Chrome, Zoom, Claude, Company Portal, CrowdStrike; MEDIUM for NinjaOne (directory structure confirmed); HIGH for Microsoft 365 (no monolithic bundle — confirmed by Microsoft docs)
- Daemon labels: MEDIUM for CrowdStrike (com.crowdstrike.falcond); LOW for NinjaOne (inferred)
- Pitfalls: HIGH — pwd import on Windows CI and plistlib binary mode are well-known patterns

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (bundle paths and daemon labels stable; macOS JSON key names worth re-verifying if macOS 16 releases before phase closes)
