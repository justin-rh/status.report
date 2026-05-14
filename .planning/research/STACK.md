# Stack Research — v2.0 Milestone Update

**Domain:** Windows/macOS IT audit portable executable (USB-portable, no-install)
**Researched:** 2026-05-07 (v2.0 update; replaces v1.0 research from 2026-05-04)
**Confidence:** HIGH (macOS stdlib APIs, registry paths) / MEDIUM (NinjaOne SYSTEM constraints, plistlib app detection)

---

## Scope

This document covers ONLY the stack additions and changes needed for the four v2.0 features.
The v1.0 stack (Python 3.12, psutil 6.x, wmi 1.5.1, winreg, Jinja2 3.1.x, PyInstaller 6.x --onedir)
is unchanged. Do not re-evaluate it.

---

## Feature 1: macOS Hardware Collectors

### What psutil covers on macOS (no additions needed)

psutil is genuinely cross-platform. The following calls work on macOS at standard-user privilege with no changes to the existing collector pattern:

| Data Point | psutil Call | Notes |
|---|---|---|
| RAM total | `psutil.virtual_memory().total` | Identical to Windows call — no change needed |
| Disk total/free | `psutil.disk_usage("/")` | Use `/` as mount point, not `C:\` |
| Current user | `os.environ.get("USER")` | macOS sets `USER`; Windows sets `USERNAME`; hardware.py already does `os.environ.get("USERNAME") or os.environ.get("USER")` — already correct |

### What psutil does NOT cover on macOS — requires subprocess

psutil does NOT expose CPU marketing name or the Mac hardware model identifier. These are vendor-specific data that psutil intentionally omits. Use `subprocess` + `sysctl`:

| Data Point | Command | Key |
|---|---|---|
| CPU model (Intel) | `sysctl -n machdep.cpu.brand_string` | Returns e.g. `Intel(R) Core(TM) i9-9880H CPU @ 2.30GHz` |
| CPU type (Apple Silicon) | `sysctl -n machdep.cpu.brand_string` | Returns `Apple M1 Pro` etc. on M-series |
| RAM total (cross-check) | `sysctl -n hw.memsize` | Returns bytes as integer string; use as a sanity check or replace `psutil.virtual_memory()` if preferred |
| Mac model identifier | `sysctl -n hw.model` | Returns `MacBookPro18,3` etc. — not a human name, but useful for audit |

All `sysctl` reads are available to standard users without sudo. They are pure read operations on kernel state that macOS exposes to all accounts.

**Implementation pattern** — consistent with existing CollectionResult discipline:

```python
import subprocess

def _sysctl(key: str) -> str | None:
    """Read one sysctl value; return None on any failure."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", key],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or None
    except Exception:
        return None
```

### OS version on macOS

Use `platform.mac_ver()` (stdlib, no addition needed). Returns `(release, versioninfo, machine)` where `release` is the marketing version string like `"14.4.1"`. Pair with `platform.system()` which returns `"Darwin"` — use this to branch between Windows and Mac paths.

```python
import platform
if platform.system() == "Darwin":
    mac_release, _, _ = platform.mac_ver()   # e.g. "14.4.1" (Sonoma)
    report.os_version = f"macOS {mac_release}"
```

**No new library needed.** `platform` is stdlib, already imported in `hardware.py`.

### macOS local user profiles — requires subprocess + dscl

`psutil.users()` returns only CURRENTLY LOGGED-IN users (same session-based semantics as `who`). It does NOT enumerate all local user accounts — this is a documented behavioral limitation, not a bug.

To enumerate all local profiles (matching what Windows ProfileList gives), use `dscl`:

```python
import subprocess

def _enumerate_mac_profiles() -> list[str]:
    """Enumerate local human user accounts via dscl."""
    try:
        result = subprocess.run(
            ["dscl", ".", "-list", "/Users", "UniqueID"],
            capture_output=True, text=True, timeout=10
        )
        profiles = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) == 2:
                username, uid_str = parts
                # UIDs >= 500 are human user accounts on macOS
                # UIDs < 500 and names starting with _ are system/service accounts
                try:
                    if int(uid_str) >= 500 and not username.startswith("_"):
                        profiles.append(username)
                except ValueError:
                    continue
        return profiles
    except Exception as exc:
        return []  # Caller logs via collection_errors
```

`dscl` reads from the local directory and does not require sudo for listing users and their UIDs. UID threshold 500 is the established macOS convention for human accounts (confirmed via Apple community and Jamf documentation). System accounts use negative UIDs or UIDs under 500 and underscore-prefixed names.

**No new library.** `subprocess` is stdlib, already used as a WMI fallback in the Windows collector.

### macOS app detection — plistlib (stdlib) + pathlib

macOS apps are `.app` bundles in `/Applications/`. Each bundle contains `Contents/Info.plist` with `CFBundleName` (internal name) and `CFBundleDisplayName` (shown in Finder). Both are readable by standard users without sudo.

**Detection strategy for the existing APP_SPECS pattern:**

Do NOT use `system_profiler SPApplicationsDataType`. It uses the Spotlight index which can be incomplete if Spotlight is indexing or if a volume is excluded. Direct filesystem + plistlib is faster, more reliable, and requires no new dependency.

```python
import plistlib
from pathlib import Path

def _mac_app_installed(bundle_display_name: str) -> tuple[bool, str | None]:
    """Check /Applications and ~/Applications for an app by display name."""
    search_roots = [Path("/Applications"), Path.home() / "Applications"]
    for root in search_roots:
        if not root.exists():
            continue
        for app_bundle in root.glob("*.app"):
            plist_path = app_bundle / "Contents" / "Info.plist"
            if not plist_path.exists():
                continue
            try:
                with plist_path.open("rb") as f:
                    info = plistlib.load(f)
                name = info.get("CFBundleDisplayName") or info.get("CFBundleName") or ""
                if bundle_display_name.lower() in name.lower():
                    version = info.get("CFBundleShortVersionString")
                    return True, version
            except Exception:
                continue
    return False, None
```

`plistlib` is Python stdlib — no new dependency. Binary and XML plists are both supported by `plistlib.load()` in Python 3.4+.

**App name mappings for Mac equivalents:**

| App | macOS Bundle Display Name |
|---|---|
| NinjaOne | `NinjaRMM` or `NinjaOne` |
| CrowdStrike Falcon | `Falcon` (bundle: `com.crowdstrike.falcon`) |
| Microsoft 365 | Check for `Microsoft Word`, `Microsoft Excel`, or `Microsoft 365` |
| Zoom | `Zoom` or `Zoom Workplace` |
| Google Chrome | `Google Chrome` |
| Claude | `Claude` |
| Company Portal | `Company Portal` |
| MERP (WindX) | Not expected on Mac — mark as N/A |

**No new library needed.** `plistlib` and `pathlib` are both already used in the project (pathlib) or are stdlib imports available for free.

---

## Feature 2: Company Portal / Intune Detection (Windows)

### Registry paths — HIGH confidence

Intune enrollment and the IntuneManagementExtension service are detectable via standard-user-readable registry keys and service inspection. Use a layered detection approach — any one indicator is sufficient to flag enrollment.

**Primary detection — enrollment registry key:**

```
HKLM\SOFTWARE\Microsoft\Enrollments\
```

This key contains one GUID-named subkey per enrolled MDM profile. Presence of any subkey with a non-null `UPN` value (user principal name) indicates active Intune enrollment. The key is present and readable without admin rights.

```python
INTUNE_ENROLLMENT_PATH = r"SOFTWARE\Microsoft\Enrollments"

def _check_intune_enrollment_registry() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, INTUNE_ENROLLMENT_PATH) as root:
            i = 0
            while True:
                try:
                    guid = winreg.EnumKey(root, i)
                    i += 1
                except OSError:
                    break
                try:
                    with winreg.OpenKey(root, guid) as sub:
                        upn, _ = winreg.QueryValueEx(sub, "UPN")
                        if upn:
                            return True
                except (FileNotFoundError, OSError):
                    continue
    except (FileNotFoundError, OSError):
        pass
    return False
```

**Secondary detection — IntuneManagementExtension service:**

The `IntuneManagementExtension` Windows service is installed by Intune for Win32 app management. Its presence confirms Intune is (or was) managing the device. Use the existing `_read_service_start()` pattern from `apps.py`:

```
HKLM\SYSTEM\CurrentControlSet\Services\IntuneManagementExtension
```

**Tertiary detection — Company Portal uninstall registry entry:**

Company Portal for Windows is distributed as an MSIX package. Detect it through the existing MSIX detection path (`_detect_msix`) with the family prefix `Microsoft.CompanyPortal_`.

```python
{
    "name": "Company Portal",
    "display_name_keywords": ["Company Portal", "Intune Company Portal"],
    "msix_family_prefix": "Microsoft.CompanyPortal_",
    "service_key": "IntuneManagementExtension",
}
```

**Recommended AppStatus semantics for Company Portal / Intune:**

- `installed=True` when Company Portal MSIX is present OR IntuneManagementExtension service exists OR enrollment registry key has a UPN.
- `service_state` carries `"Automatic"` / `"Manual"` / `"Disabled"` from `IntuneManagementExtension`.
- No new fields needed on `AuditReport` or `AppStatus`.

**No new library.** All detection uses existing `winreg` + the established `_detect_msix` and `_read_service_start` helpers from `apps.py`.

---

## Feature 3: NinjaOne SYSTEM-Account Compatibility

### The SYSTEM-account execution context

When NinjaOne deploys a script as SYSTEM, the running process has:
- No `USERPROFILE` or `APPDATA` environment variable (or they point to `C:\Windows\system32\config\systemprofile`)
- No interactive desktop session
- No `%TEMP%` reliably writable without explicit setup (though `C:\Windows\Temp` is always writable by SYSTEM)
- `USERNAME` env var is set to `SYSTEM`

### PyInstaller --onedir under SYSTEM — critical constraint

The existing `--onedir` bundle is SAFE under SYSTEM. The launcher exe does NOT self-extract — all files are already on disk in the bundle directory. The `--onefile` mode would be dangerous here (extracts to `%TEMP%`), but `--onedir` is used and that decision must not be changed.

**One risk:** if any collector calls `os.environ.get("USERNAME")` to populate `current_user` and the value is `"SYSTEM"`, that should be treated as "no interactive user" and set to `None` or a sentinel value. The existing `_collect_current_user` in `hardware.py` passes the USERNAME env var through unchanged — add a guard:

```python
_SYSTEM_ACCOUNTS = {"SYSTEM", "LOCAL SERVICE", "NETWORK SERVICE"}

def _collect_current_user(report: AuditReport) -> None:
    user = os.environ.get("USERNAME") or os.environ.get("USER") or None
    if user and user.upper() in _SYSTEM_ACCOUNTS:
        user = None  # Not a real user session
    report.current_user = user
```

### HKCU registry access under SYSTEM

When running as SYSTEM, `HKCU` maps to `HKEY_USERS\.DEFAULT`, NOT to any real user's hive. This means:
- MSIX detection via `_detect_msix` (which reads HKCU AppModel repository) will find nothing under SYSTEM — this is expected behavior, not a bug.
- Per-user app installs in HKCU Uninstall keys will not be visible.
- The `detect_apps` function should not crash — all HKCU `OpenKey` calls already return `FileNotFoundError` / `OSError` and are silently skipped.

**No code changes needed for graceful degradation** — the existing try/except pattern already handles this. Document it as expected behavior in the collector comments.

### stdout reporting for NinjaOne

NinjaOne captures a Python script's stdout as the "Script Output" visible in the dashboard. NinjaOne also supports writing to custom device fields via `ninjarmm-cli.exe`, but that requires the CLI to be present and running as SYSTEM specifically.

**Recommendation: stdout-only.** Print a plain-text summary to stdout at the end of `main.py`. This works under SYSTEM, standard user, and interactive use without any API dependency.

```
[StatusReport] hostname=PHX-ABC-001 os=Windows 11 (22621) cpu=Intel Core i7-1265U
[StatusReport] ram=16.0GB disk=45.2/476.3GB free=9.5%
[StatusReport] apps=NinjaOne:YES CrowdStrike:YES M365:YES Zoom:NO
[StatusReport] warnings=LOW_DISK_SPACE
[StatusReport] output=D:\logs\PHX-ABC-001_20260507_143022.html
```

NinjaOne collects exit code in addition to stdout. Use `sys.exit(0)` on success and `sys.exit(1)` on critical failure. Do NOT use NinjaOne custom fields API — it requires the `ninjarmm-cli.exe` binary to be present on the machine, adds network dependency, and requires SYSTEM context to write to protected paths.

**No new library.** `sys.stdout` / `print()` is sufficient.

### Output path under SYSTEM

The existing `Path(sys.executable).parent` output strategy writes to the bundle directory. When NinjaOne deploys and runs the exe, `sys.executable` correctly points to the exe location regardless of execution context — this is a PyInstaller guarantee for `--onedir` bundles. The HTML file will be written adjacent to the exe in whatever directory NinjaOne placed the bundle. Document this in `main.py`.

One concern: if NinjaOne places the exe in a system-protected directory, the write will fail. Wrap the output write in try/except and print the error to stdout — the existing `writers/` layer already returns errors rather than raising.

---

## Feature 4: HTML Warnings System

### No new library needed

The warnings system is a rendering concern, not a collection concern. The data for both checks is already collected:
- `report.os_build` is populated by `_collect_os()` — compare the build number integer against the minimum acceptable build
- `report.disk_free_gb` and `report.disk_total_gb` are populated by `_collect_memory_and_disk()` — compute percent free inline

Add a `warnings: list[str]` field to `AuditReport` (or compute inline in the renderer). Populate it in a new `evaluate_warnings(report)` function called from `main.py` after collection, before rendering.

**Suggested thresholds** (to be confirmed with IT):

| Check | Threshold | Warning label |
|---|---|---|
| OS version | Windows 11 build < 22631 (23H2) or Windows 10 build < 19045 (22H2) | `OS_OUT_OF_DATE` |
| Disk free space | < 15% free of total | `LOW_DISK_SPACE` |

These thresholds are suggestions. The planner should confirm the exact build numbers with the team before coding.

**HTML rendering pattern** — collapsible box using only HTML + inline CSS (no JavaScript needed for a details/summary element):

```html
<details class="warnings-box" open>
  <summary>Warnings ({{ warnings|length }})</summary>
  {% for w in warnings %}
  <div class="warning-item">{{ w }}</div>
  {% endfor %}
</details>
```

Jinja2 conditionally renders this block only when `warnings` is non-empty. The `<details>` element is collapsed by removing the `open` attribute — all in existing template logic.

**No new library needed.** Pure Jinja2 template logic on existing data.

---

## Summary: What Changes vs. What Stays the Same

| Concern | Change? | Details |
|---|---|---|
| psutil | No change | `virtual_memory()` and `disk_usage()` already work on Mac |
| wmi | Windows-only, no change | Not imported on Mac (already behind `_WMI_AVAILABLE` guard) |
| winreg | Windows-only, no change | Not available on Mac (stdlib; simply not imported in Mac collectors) |
| subprocess | Already present (WMI fallback) | Add two Mac-specific calls: `sysctl` for CPU, `dscl` for profiles |
| plistlib | NEW import (stdlib) | Used in Mac app detection; no pip install required |
| platform | Already imported | `platform.mac_ver()` and `platform.system()` added to Mac path |
| pathlib | Already used | Extended to `/Applications` glob in Mac app collector |
| Jinja2 | No change | Warnings block is an additive template change |
| PyInstaller | No change | `--onedir` already correct; no new hidden imports for stdlib additions |

**No new pip dependencies are required for any of the four v2.0 features.** All additions use Python stdlib (`plistlib`, `subprocess`, `platform`, `pathlib`) or extend existing patterns.

---

## Mac Distribution — Separate Research Needed

Packaging a Mac version as a `.app` bundle or standalone executable requires a separate research pass. Options include:
- PyInstaller on macOS produces a `.app` bundle (different from the Windows `--onedir` folder)
- Code signing and notarization is required for macOS Gatekeeper to allow running downloaded executables
- Consider `briefcase` or `py2app` as PyInstaller alternatives on macOS

This is out of scope for the v2.0 milestone, which focuses on collector parity (the Python code that runs), not Mac packaging. Defer to a future milestone.

---

## Registry Path Reference — Company Portal / Intune

Collected here for the planner:

| Path | Type | Readable Without Admin | Purpose |
|---|---|---|---|
| `HKLM\SOFTWARE\Microsoft\Enrollments\{GUID}\UPN` | REG_SZ | Yes | MDM enrollment indicator; non-null value = enrolled |
| `HKLM\SYSTEM\CurrentControlSet\Services\IntuneManagementExtension` | Key | Yes | Service key for IME; presence = Intune Win32 management active |
| `HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages\Microsoft.CompanyPortal_*` | Key | Yes (but empty under SYSTEM) | MSIX package presence |

---

## macOS API Reference — Quick Reference for Implementer

| Data | Method | Module | sudo? |
|---|---|---|---|
| OS version | `platform.mac_ver()[0]` | `platform` (stdlib) | No |
| Platform check | `platform.system() == "Darwin"` | `platform` (stdlib) | No |
| CPU model | `subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"])` | `subprocess` (stdlib) | No |
| RAM total | `psutil.virtual_memory().total` | `psutil` (existing) | No |
| Disk free/total | `psutil.disk_usage("/")` | `psutil` (existing) | No |
| Local user profiles | `subprocess.run(["dscl", ".", "-list", "/Users", "UniqueID"])` | `subprocess` (stdlib) | No |
| App presence | `plistlib.load(open(".../Contents/Info.plist", "rb"))` | `plistlib` (stdlib) | No |
| Current user | `os.environ.get("USER")` | `os` (stdlib) | No |

---

## What NOT to Add (v2.0)

| Do Not Add | Why |
|---|---|
| `pyobjc` / `AppKit` | Heavy ObjC bridge; not needed; no PyInstaller hooks tested |
| `system_profiler SPApplicationsDataType` | Spotlight-dependent; can miss apps; plistlib filesystem scan is more reliable |
| `ninjarmm-cli` API calls | Network dependency; requires CLI binary; stdout is sufficient |
| `mdmclient` subprocess (macOS MDM) | Requires admin on most macOS versions; out of scope for v2 |
| `requests` or any HTTP library | No network calls in scope; adds AV surface area |
| New pip packages for warnings | Pure data model + Jinja2 template logic; no library needed |

---

## Sources (v2.0)

- [psutil PyPI — 6.x current](https://pypi.org/project/psutil/) — cross-platform coverage confirmed
- [psutil GitHub issue #2259](https://github.com/giampaolo/psutil/issues/2259) — `users()` returns logged-in only, not all local accounts (confirmed limitation)
- [ss64 sysctl reference](https://ss64.com/mac/sysctl.html) — `hw.memsize`, `machdep.cpu.brand_string` documented as standard unprivileged reads
- [Python docs: plistlib](https://docs.python.org/3/library/plistlib.html) — stdlib, supports binary and XML plists, Python 3.4+
- [Python docs: platform.mac_ver](https://docs.python.org/3/library/platform.html) — returns macOS release version string
- [ss64 dscl reference](https://ss64.com/mac/dscl.html) — `dscl . -list /Users UniqueID` documented; reads without sudo
- [Jamf community: dscl user filter](https://community.jamf.com/general-discussions-2/dscl-command-to-list-local-users-but-exclude-system-accounts-36591) — UID >= 500 filter for human accounts confirmed
- [Microsoft Learn: MDM enrollment registry](https://learn.microsoft.com/en-us/windows/client-management/mdm-diagnose-enrollment) — `HKLM\SOFTWARE\Microsoft\Enrollments` documented as enrollment indicator
- [anoopcnair: Intune registry paths](https://www.anoopcnair.com/windows-10-intune-mdm-support-help-1/) — `Enrollments\{GUID}\UPN` pattern confirmed
- [NinjaOne docs: CLI custom fields](https://www.ninjaone.com/docs/endpoint-management/scripting-and-automation/command-line-interface-cli/cli-custom-fields-documentation-scripting/) — `ninjarmm-cli` requires SYSTEM and protected path access
- [NinjaOne docs: Script output](https://www.ninjaone.com/docs/administration/script-library/) — stdout captured as script output in dashboard; exit code captured separately
- [PyInstaller docs: run-time information](https://pyinstaller.org/en/stable/runtime-information.html) — `sys.executable` reliable in `--onedir` mode regardless of execution account

---

*Stack research for: StatusReport v2.0 — Mac collectors, Company Portal, NinjaOne, Warnings*
*Researched: 2026-05-07*

---
---

# Stack Research — v3.0 Milestone Additions

**Researched:** 2026-05-14
**Confidence:** HIGH (psutil uptime, winreg vendor detection, stdlib JSON) / MEDIUM (WUA COM privilege behavior) / LOW (Dell/Lenovo pending-count via CLI — requires live machine verification)

---

## Scope

This section covers ONLY the new stack additions needed for v3.0:
1. System health collectors (uptime, pending Windows updates)
2. Vendor update detection (Dell Command Update, Lenovo System Update)
3. Extended CLI output (JSON serialization, output path override, single-app check)

The existing stack and v2.0 additions are unchanged. Do not re-evaluate them.

---

## Feature 1: System Health Collectors

### 1a. Uptime since last reboot — psutil.boot_time() (no new dependency)

`psutil.boot_time()` returns a Unix timestamp (float) of the last system boot. Uptime in days is `(time.time() - psutil.boot_time()) / 86400`. This call is available to standard users, requires no COM server, and works under SYSTEM account. No new dependency needed.

**Confidence:** HIGH. psutil 6.x is already a project dependency. `boot_time()` is a top-level psutil call documented as cross-platform and privilege-free.

**Known caveat (LOW risk):** psutil issue #2094 documents that on some Windows configurations `boot_time()` can return a timestamp slightly before the actual boot time. The delta is typically seconds, not hours. For a stale-uptime warning at a threshold of N days, this is inconsequential. No mitigation needed.

**Implementation pattern:**

```python
import psutil, time

def collect_uptime() -> tuple[float, str]:
    """Returns (uptime_days: float, formatted: str)."""
    boot_ts = psutil.boot_time()
    uptime_seconds = time.time() - boot_ts
    uptime_days = uptime_seconds / 86400
    days = int(uptime_days)
    hours = int((uptime_seconds % 86400) / 3600)
    return uptime_days, f"{days}d {hours}h"
```

The `UPTIME_STALE` warning threshold (N days) should be a module-level constant, not hardcoded inline, so it can be changed without hunting through logic:

```python
UPTIME_STALE_THRESHOLD_DAYS = 30  # configurable
```

### 1b. Pending Windows update count — WUA COM via win32com (new dependency: pywin32)

The Windows Update Agent (WUA) COM API is the correct mechanism for reading the locally-cached count of pending updates without triggering any downloads or network calls.

**Pattern:**

```python
import win32com.client  # from pywin32

session = win32com.client.Dispatch("Microsoft.Update.Session")
searcher = session.CreateUpdateSearcher()
result = searcher.Search("IsInstalled=0 and IsHidden=0 and Type='Software'")
pending_count = result.Updates.Count
```

**Privilege level:** MEDIUM confidence based on multiple corroborating sources. Searching for updates (read-only `Search()`) works under standard user accounts in an interactive desktop session. The Paessler documentation and Microsoft Q&A confirm this explicitly: "New-Object -ComObject Microsoft.Update.Session can run successfully in a non-administrator user account when logged on to a desktop session." Installation requires elevation; search does not.

**SYSTEM account caveat:** Under SYSTEM (NinjaOne execution context), WUA COM may behave differently. The WUA service (`wuauserv`) runs as SYSTEM, so COM dispatch to it from a SYSTEM context should succeed. However, this is MEDIUM confidence — it should be tested on a live machine before shipping. The guard pattern handles failure gracefully (see below).

**Network requirement:** `Search()` against the default service uses the Windows Update client's locally-cached update catalog. It does NOT require internet connectivity or a WSUS server to return a count of previously-detected pending updates. The count reflects what Windows Update last detected, not a fresh scan. This satisfies the "no internet required" constraint.

**pywin32 version:** Current is 311 (released July 14, 2025), supporting Python 3.8–3.14 including Python 3.12. Install with `pip install pywin32==311`.

**Guard pattern — required for CI compatibility:**

Follow the existing `_WMI_AVAILABLE` pattern. WUA COM will not be available in CI (no Windows Update Agent COM server). Wrap behind a `_WUA_AVAILABLE` flag:

```python
try:
    import win32com.client as _win32com_client
    _WUA_AVAILABLE = True
except ImportError:
    _win32com_client = None
    _WUA_AVAILABLE = False

def collect_pending_windows_updates() -> int | None:
    """Returns pending update count, or None if WUA is unavailable."""
    if not _WUA_AVAILABLE:
        return None
    try:
        session = _win32com_client.Dispatch("Microsoft.Update.Session")
        searcher = session.CreateUpdateSearcher()
        result = searcher.Search("IsInstalled=0 and IsHidden=0 and Type='Software'")
        return result.Updates.Count
    except Exception:
        return None  # COM dispatch failed; degrade gracefully
```

Return `None` (not 0) when unavailable — callers must distinguish "0 pending" from "could not check."

**PyInstaller --onedir packaging implications for pywin32:**

pywin32 has historically had friction with PyInstaller due to `win32com`'s dynamic `__path__` manipulation. As of PyInstaller 6.x (current project version), the DLL bootstrap for pywin32 has been fixed — PyInstaller now preserves the `pywin32_system32` directory layout and adds it to DLL search paths. The win32com runtime hook was removed in recent versions (no longer needed).

Required addition to the `.spec` file or build command:

```
--hidden-import win32timezone
```

`win32timezone` is the most commonly missing hidden import when using `win32com.client.Dispatch` in a frozen exe. Without it, `Dispatch()` calls that return objects with time-zone-aware properties will raise `ImportError` at runtime. Add it proactively.

The existing `--onedir` mode is compatible with pywin32 311. No `--onefile` change; no `upx=False` change needed.

**Alternatives evaluated and rejected:**

| Alternative | Why Rejected |
|---|---|
| `subprocess` calling PowerShell `Get-WindowsUpdate` | Requires PSWindowsUpdate module (third-party, not present on all machines); `(Get-WUList).Count` also wraps WUA COM — same dependency, more failure surface |
| `subprocess` + `wmic /namespace:\\root\Microsoft\Windows\WindowsUpdate` | WMI namespace for Windows Update is restricted; not reliably readable by standard users; also violates the spirit of the WMI prohibition pattern |
| `subprocess` + `usoclient.exe` or `wuauclt.exe` | These trigger detection/download operations — side effects prohibited. They do not return a count. |
| PowerShell `Get-WindowsUpdateLog` | Parses ETW traces into a text log; does not provide a pending count; file may not exist |
| Reading `C:\Windows\SoftwareDistribution\DataStore\DataStore.edb` | ESE database; requires elevated access and an ESE parsing library (not stdlib); overkill |

**Verdict: pywin32 311, win32com.client.Dispatch("Microsoft.Update.Session"), guarded behind _WUA_AVAILABLE.**

---

## Feature 2: Vendor Update Detection

### 2a. Dell Command Update pending count

**What Dell Command Update is:** A CLI + background service tool for Dell commercial machines that checks for BIOS, firmware, driver, and application updates. Installed at:
- 64-bit: `C:\Program Files\Dell\CommandUpdate\dcu-cli.exe`
- 32-bit: `C:\Program Files (x86)\Dell\CommandUpdate\dcu-cli.exe`

**Detection strategy (two-stage):**

Stage 1 — Detect whether DCU is installed, using existing winreg Uninstall path pattern (no new dependency). Search standard Uninstall keys for `DisplayName` matching `"Dell Command | Update"`:

```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*
HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*
```

If the key is not present, the machine is not Dell or DCU is not installed. Return `None` (not applicable) rather than 0.

Stage 2 — Get pending count by invoking `dcu-cli.exe /scan -silent -report=<temp_path>` and parsing the output XML. The `-report` flag writes an XML file listing applicable updates.

**Critical constraint — admin elevation required for dcu-cli.exe:**

Dell's official documentation states: "To run the CLI, you must launch the command prompt as an Administrator." Exit code 4 from `dcu-cli.exe` explicitly means "The CLI was not launched with administrative privilege."

Under a standard user or SYSTEM account without explicit elevation, `dcu-cli.exe /scan` will return exit code 4 and produce no report. This is a hard constraint.

**Recommended approach for standard user / SYSTEM context:**

Do NOT invoke `dcu-cli.exe` as a subprocess from StatusReport. Doing so will fail silently (exit code 4) and potentially log an error in DCU's own activity log. Instead, read DCU's activity log to detect the last-known scan result:

```
C:\ProgramData\Dell\UpdateService\Log\activity.log
```

The activity log contains lines like `found [N] updates`. This is read-only filesystem access — no elevation, no side effects, no COM. Parse the most recent "found [N] updates" line for the count. This is a passive, side-effect-free approach.

**Log parsing pattern:**

```python
import re
from pathlib import Path

DCU_LOG_PATH = Path(r"C:\ProgramData\Dell\UpdateService\Log\activity.log")

def collect_dell_pending_updates() -> int | None:
    """
    Returns the last-known pending Dell update count from DCU activity log.
    Returns None if DCU is not installed or log is absent/unreadable.
    """
    if not DCU_LOG_PATH.exists():
        return None
    try:
        text = DCU_LOG_PATH.read_text(encoding="utf-8", errors="replace")
        # Find all "found [N] updates" lines; take the last one
        matches = re.findall(r"found \[(\d+)\] updates", text, re.IGNORECASE)
        if matches:
            return int(matches[-1])
        return None
    except Exception:
        return None
```

**Confidence:** MEDIUM. The log format "found [N] updates" is confirmed from community documentation (Automox worklets, Dell service log references). The exact regex pattern requires validation against a live DCU log. Flag for live-machine testing before shipping.

**No new dependency.** `re` and `pathlib` are stdlib.

**PyInstaller packaging:** No impact. Filesystem read only.

### 2b. Lenovo System Update pending count

**What Lenovo System Update is:** A background tool for Lenovo commercial machines (ThinkPad, ThinkCentre, ThinkStation) that checks for firmware, driver, and BIOS updates. Installed at:
- `C:\Program Files (x86)\Lenovo\System Update\tvsu.exe`

As of mid-2024, Lenovo also ships "Commercial Vantage" with a System Update Addin, which uses a different log path.

**Detection strategy (two-stage):**

Stage 1 — Detect whether Lenovo System Update is installed via existing winreg Uninstall pattern:

```
HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*
```

Search for `DisplayName` matching `"Lenovo System Update"` or `"System Update"` with publisher `"Lenovo"`.

Stage 2 — Read the log file. Lenovo System Update writes per-session log files to:

```
C:\ProgramData\Lenovo\SystemUpdate\logs\
```

Log file naming pattern: `tvsu_YYMMDDHHMMSS.log`

**Important 2024 change:** In Lenovo System Update versions released in 2024 and later, logging is DISABLED by default as a security precaution. Log files may not exist even if System Update has run. The registry key to enable logging is:

```
HKLM\SOFTWARE\WOW6432Node\Lenovo\System Update\Preferences\UCSettings\Log
Value: FileName = tvsu.log
```

This means log-based detection is unreliable on machines with recent Lenovo System Update versions unless logging has been explicitly enabled by IT policy.

**Recommended fallback — WMI-based detection if -exporttowmi was used:**

Lenovo System Update's CLI supports `-exporttowmi` which writes update data to WMI. However, this requires the update to have been run with that flag, and reading WMI data requires the existing `_WMI_AVAILABLE` guard. This is too fragile for a general-purpose tool.

**Recommended approach:** Registry-detect Lenovo System Update presence. Attempt log read. Return `None` if logs are absent (logging disabled by default in 2024+). Do not invoke `tvsu.exe` as a subprocess — it requires admin elevation and creates side effects (temporary admin account creation per Lenovo FAQ).

**Log parsing pattern:**

```python
from pathlib import Path
import re

LENOVO_LOG_DIR = Path(r"C:\ProgramData\Lenovo\SystemUpdate\logs")

def collect_lenovo_pending_updates() -> int | None:
    """
    Returns pending Lenovo update count from most recent tvsu log.
    Returns None if not installed, logs absent, or count unreadable.
    Note: Logging disabled by default in 2024+ Lenovo System Update versions.
    """
    if not LENOVO_LOG_DIR.exists():
        return None
    try:
        log_files = sorted(LENOVO_LOG_DIR.glob("tvsu_*.log"), reverse=True)
        if not log_files:
            return None
        text = log_files[0].read_text(encoding="utf-8", errors="replace")
        # Log format varies by version; search for update count indicators
        matches = re.findall(r"(\d+)\s+package[s]?\s+(?:found|available|to install)", text, re.IGNORECASE)
        if matches:
            return int(matches[-1])
        return None
    except Exception:
        return None
```

**Confidence:** LOW. The log format for Lenovo System Update is not formally documented. The regex is a best-effort pattern based on community observations. This requires validation against live log files. Flag for live-machine testing.

**Fallback behavior:** If log parsing returns `None`, the character sheet should display "N/A" or "Log unavailable" rather than 0. The distinction matters for IT staff.

**No new dependency.** `re` and `pathlib` are stdlib.

---

## Feature 3: Extended CLI Output

### 3a. JSON serialization of AuditReport — stdlib only (no new dependency)

`AuditReport` and its nested dataclasses (`AppStatus`, `Warning`) are Python dataclasses. Serialization to JSON uses `dataclasses.asdict()` + `json.dumps()` from the stdlib. No third-party library needed.

**Pattern:**

```python
import json
import dataclasses

def report_to_json(report: AuditReport) -> str:
    """Serialize AuditReport to a JSON string."""
    return json.dumps(
        dataclasses.asdict(report),
        indent=2,
        default=str  # handles datetime, Path, and any non-serializable fields
    )
```

`dataclasses.asdict()` is recursive — it handles nested dataclasses, lists of dataclasses, and dicts. The `default=str` fallback in `json.dumps` handles `datetime` objects (uptime boot time) and `Path` objects without a custom encoder class.

**Edge cases to handle before coding:**
- `uptime_days: float` serializes cleanly as a JSON number.
- `boot_time: datetime` — use `default=str` which calls `datetime.__str__()`, producing ISO-like strings. Acceptable for IT tool output.
- `pending_windows_updates: int | None` — `None` serializes as JSON `null`. This is correct semantics (unavailable vs. zero).

**Confidence:** HIGH. `dataclasses.asdict` + `json.dumps` with `default=str` is the stdlib-idiomatic pattern for Python 3.7+. No new imports beyond what Python provides.

**PyInstaller packaging:** No impact. Both `dataclasses` and `json` are stdlib modules bundled with Python itself.

### 3b. Output path override — argparse (already present)

`--output <path>` is a new argparse flag added to the existing argument parser. No new library. The path is passed through to `writers/`, which already accepts a path argument via `Path(sys.executable).parent`. Replace that default with `Path(args.output)` when the flag is present.

**Validation:** Validate that the target directory exists (or create it) and is writable before running the full pipeline. Print a clear error to stderr and `sys.exit(1)` if the path is invalid. Do not silently fall back to the default path — that would cause confusion when `--output` is specified in a NinjaOne script.

### 3c. Single-app detection — argparse + existing app detection logic

`--app <name>` runs only the app detection pipeline for the named app and exits. No new library. Implementation:

1. Parse `--app` from argparse.
2. Match the value against `APP_SPECS` by name (case-insensitive).
3. Run only `detect_single_app(name)` — a new thin wrapper around the existing per-app detection logic in `apps.py`.
4. If `--json` is also present, serialize the single `AppStatus` dataclass to JSON and print to stdout.
5. If `--json` is absent, print a human-readable one-liner: `NinjaOne: INSTALLED (v8.0.1234)`.

**Exit codes for `--app`:**
- `0` — app found / installed
- `1` — app not found / not installed
- `2` — app name not recognized

These exit codes enable NinjaOne condition checks (`if exit_code == 0 then...`) without parsing stdout.

---

## New pip Dependency Summary

| Package | Version | Purpose | Why This One |
|---|---|---|---|
| `pywin32` | `311` | `win32com.client.Dispatch` for WUA COM API (pending Windows updates) | Only Python binding for WUA COM; no lighter alternative exists for COM dispatch |

**All other v3.0 features use stdlib exclusively.**

---

## v3.0 Guard Pattern Requirements

Both `_WMI_AVAILABLE` (existing) and `_WUA_AVAILABLE` (new) guards are required. They follow the same pattern:

```python
# In collectors/windows/health.py

try:
    import win32com.client as _win32com
    _WUA_AVAILABLE = True
except ImportError:
    _win32com = None
    _WUA_AVAILABLE = False
```

CI environments will have `_WUA_AVAILABLE = False`. Tests that cover WUA behavior must mock `_win32com` at the module level, not patch `win32com.client` directly.

---

## PyInstaller --onedir Packaging Changes for v3.0

| Change | Required | Notes |
|---|---|---|
| `pip install pywin32==311` in build environment | Yes | New dependency |
| `--hidden-import win32timezone` in build spec | Yes | Required for win32com.client.Dispatch in frozen exe; missing it causes runtime ImportError |
| `--hidden-import win32com.client` | Probably not needed | PyInstaller 6.x detects it via static analysis, but add if runtime errors occur |
| `--onedir` mode | Unchanged | No change; pywin32 311 is compatible with onedir |
| `upx=False` | Unchanged | Keep as-is for CrowdStrike compatibility |

---

## Privilege Matrix for v3.0 Collectors

| Collector | Standard User | SYSTEM (NinjaOne) | Notes |
|---|---|---|---|
| `psutil.boot_time()` | Yes | Yes | No privilege needed |
| WUA `Search("IsInstalled=0")` | Yes (interactive session) | MEDIUM confidence — test needed | COM dispatch to `wuauserv` from SYSTEM context; likely works |
| DCU log read (`activity.log`) | Yes | Yes | Filesystem read; world-readable |
| Lenovo log read (`tvsu_*.log`) | Yes | Yes | Filesystem read; world-readable |
| `dataclasses.asdict` + `json.dumps` | N/A | N/A | Pure Python |

---

## What NOT to Add (v3.0)

| Do Not Add | Why |
|---|---|
| `pywin32` for anything other than WUA | `wmi 1.5.1` already handles all other COM needs; do not duplicate |
| `dcu-cli.exe /scan` subprocess call | Requires admin elevation (exit code 4 otherwise); creates side effects; log reading is the correct passive approach |
| `tvsu.exe` subprocess call | Requires elevation; creates temporary admin account; log reading is the correct passive approach |
| `PSWindowsUpdate` PowerShell module | Third-party PS module; not present on all machines; wraps WUA COM anyway — use WUA directly |
| `requests` / `httpx` / any HTTP library | No network access in scope |
| `dataclasses-json` or `pydantic` | Overkill; `dataclasses.asdict` + `json.dumps(default=str)` covers all requirements |
| `orjson` | Faster but adds a binary dependency; not needed at audit tool scale |
| `win32com.client.gencache.EnsureDispatch` | Uses generated COM dispatch cache; known to break in PyInstaller frozen exes (PyInstaller issue #6257); use `Dispatch()` (late-binding) instead |

---

## Sources (v3.0)

- [psutil PyPI — 6.x current](https://pypi.org/project/psutil/) — `boot_time()` documented as cross-platform, standard user
- [psutil issue #2094](https://github.com/giampaolo/psutil/issues/2094) — Windows `boot_time()` pre-boot timestamp caveat; low-severity for day-level thresholds
- [Microsoft Learn: WUA Searching, Downloading, and Installing Updates](https://learn.microsoft.com/en-us/windows/win32/wua_sdk/searching--downloading--and-installing-updates) — `Search("IsInstalled=0")` criteria, COM objects documented
- [Paessler Knowledge Base: Windows Update Sensor](https://helpdesk.paessler.com/en/support/solutions/articles/76000077585-windows-update-sensor-access-denied-creating-an-instance-of-the-com-component) — confirmed: `Microsoft.Update.Session` works in standard user interactive session; fails in remote PS session without admin
- [pywin32 PyPI — version 311](https://pypi.org/project/pywin32/) — latest release July 14, 2025; Python 3.12 support confirmed
- [PyInstaller issue #7255: pywin32 import fails](https://github.com/pyinstaller/pyinstaller/issues/7255) — bootstrap DLL fix in recent PyInstaller; `win32timezone` hidden import requirement noted
- [PyInstaller issue #6257: gencache.EnsureDispatch breaks frozen exe](https://github.com/pyinstaller/pyinstaller/issues/6257) — use `Dispatch()` (late-binding), not `EnsureDispatch()`
- [Dell Command Update Version 5.x Reference Guide — CLI commands](https://www.dell.com/support/manuals/en-us/command-update/dcu_rg/dell-command-update-cli-commands?guid=guid-92619086-5f7c-4a05-bce2-0d560c15e8ed&lang=en-us) — `/scan -report` XML output documented
- [Dell Command Update CLI error codes](https://www.dell.com/support/manuals/en-ca/command-update/dcu_rg/command-line-interface-error-codes?guid=guid-fbb96b06-4603-423a-baec-cbf5963d8948) — exit code 4 = not launched with admin privilege
- [Automox: Basic Dell Command Update Worklet](https://community.automox.com/find-share-worklets-12/basic-dell-command-update-worklet-2278) — "found [N] updates" log line format confirmed from community usage
- [Lenovo CDRT: System Update FAQ](https://docs.lenovocdrt.com/guides/sus/system_update_faq/) — admin account creation for standard user confirmed; tvsu.exe location at `C:\Program Files (x86)\Lenovo\System Update\`
- [Lenovo CDRT: System Update Command Line Reference](https://docs.lenovocdrt.com/guides/sus/su_dg/su_dg_ch5/) — CLI parameters, `/CM -search -action LIST` documented
- [WebSearch: Lenovo 2024 logging default disabled](https://forums.lenovo.com/t5/) — logging disabled by default in 2024+ versions; registry key to re-enable documented
- [Python docs: dataclasses.asdict](https://docs.python.org/3/library/dataclasses.html#dataclasses.asdict) — recursive conversion of nested dataclasses confirmed
- [Python docs: json.dumps default parameter](https://docs.python.org/3/library/json.html) — `default=str` pattern for non-serializable types

---

*Stack research for: StatusReport v3.0 — System health, vendor updates, extended CLI*
*Researched: 2026-05-14*
