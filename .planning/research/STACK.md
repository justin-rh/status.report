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

## What NOT to Add

| Do Not Add | Why |
|---|---|
| `pyobjc` / `AppKit` | Heavy ObjC bridge; not needed; no PyInstaller hooks tested |
| `system_profiler SPApplicationsDataType` | Spotlight-dependent; can miss apps; plistlib filesystem scan is more reliable |
| `ninjarmm-cli` API calls | Network dependency; requires CLI binary; stdout is sufficient |
| `mdmclient` subprocess (macOS MDM) | Requires admin on most macOS versions; out of scope for v2 |
| `requests` or any HTTP library | No network calls in scope; adds AV surface area |
| New pip packages for warnings | Pure data model + Jinja2 template logic; no library needed |

---

## Sources

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
