# Pitfalls Research — v2.0 Update

**Domain:** Windows IT audit/inventory executable — v2.0 additions: Company Portal detection, warnings system, Mac collectors, NinjaOne SYSTEM-account execution
**Researched:** 2026-05-07
**Confidence:** HIGH for Windows/NinjaOne pitfalls (registry behavior verified against official docs, existing codebase patterns known). MEDIUM for Mac-specific pitfalls (based on community issues and Apple docs; no live Mac build exists yet to validate).

---

## Context: What Already Works (v1.0 Validated)

These pitfalls were resolved in v1.0 and are documented for reference. **Do not re-solve them in v2.0:**

| Pitfall | Resolution |
|---------|-----------|
| CrowdStrike quarantine of `--onefile` | Use `--onedir` only (enforced in CLAUDE.md) |
| SmartScreen on unsigned binary | Document "More info → Run anyway"; EV cert deferred to v2 backlog |
| `Win32_Product` MSI reconfiguration | Prohibited; registry `Uninstall` paths only |
| 32-bit/64-bit registry redirection | All four `UNINSTALL_PATHS` enumerated in `apps.py` |
| `os.getcwd()` output path | `Path(sys.executable).parent` used in `main.py` |
| `CrowdStrike Falcon` DisplayName mismatch | "CrowdStrike Windows Sensor" / "CrowdStrike Sensor Platform" confirmed live |
| `importlib.resources` single-string `joinpath` | Enforced in renderer for PyInstaller bundled templates |
| Disk `hp bar` falsy guard for `None vs 0.0` | Exists in renderer; must extend to new `disk_pct` warning field |

---

## Critical Pitfalls — v2.0 Features

### Pitfall 1: Company Portal Installation Detection ≠ Intune MDM Enrollment Detection

**What goes wrong:**
The audit tool adds an "Intune / Company Portal" row and detects Company Portal (the Store app) as installed, then reports the device as "Intune enrolled." These are different things. A device can have Company Portal installed but not be MDM enrolled (happens when a user sideloads the app for app access only). Conversely, a device can be MDM enrolled via Autopilot or Settings → Work or school account without Company Portal being installed at all. If the requirement is "detect Intune enrollment," searching only for the Company Portal MSIX package gives false positives and false negatives.

**Why it happens:**
Company Portal is an optional user-facing portal application. MDM enrollment is a separate Windows subsystem state stored in `HKLM\SOFTWARE\Microsoft\Enrollments\{GUID}`. The MSIX detection pattern that works for Claude (the `_detect_msix` helper in `apps.py`) is not sufficient here.

**Prevention — two separate signals:**

1. **For MDM enrollment detection** (the right signal for an IT audit):
   ```python
   import winreg

   def is_mdm_enrolled() -> bool:
       """Return True if any non-empty enrollment GUID exists under HKLM Enrollments."""
       key_path = r"SOFTWARE\Microsoft\Enrollments"
       try:
           with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as root:
               i = 0
               while True:
                   try:
                       guid = winreg.EnumKey(root, i)
                       i += 1
                   except OSError:
                       break
                   # Skip the sub-keys that are always present on non-enrolled machines
                   if len(guid) == 36 and guid.count('-') == 4:  # valid GUID format
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
   The `UPN` value under a GUID subkey confirms active enrollment; GUIDs without `UPN` are stale/partial entries.

2. **For Company Portal app detection** (separate from enrollment):
   Use the existing `_detect_msix` helper with prefix `"Microsoft.CompanyPortal_"`. This tells you the app is installed, not that the device is enrolled.

**The naming decision matters:** If the `AppStatus.name` is "Intune / Company Portal", the IT audit interpretation becomes ambiguous. Consider two distinct rows: one for MDM Enrollment (registry signal) and one for Company Portal (MSIX signal), or name the row precisely based on which signal you use.

**Stale registry ghost:** The `HKLM\SOFTWARE\Microsoft\Enrollments` GUID key sometimes survives unenrollment. Always require the `UPN` value — a GUID key without `UPN` is an artifact, not active enrollment. Document this as "Enrolled (registry confirmed)" in the report.

**Warning signs:**
- Tool reports "Intune enrolled" on freshly imaged machines that have no MDM policy applied.
- Machines with Company Portal sideloaded (user-context) show as "enrolled" when they are not.

**Phase to address:** Company Portal detection implementation. Decide enrollment-vs-app-installed before writing any detection code.

---

### Pitfall 2: `os.environ.get("USERNAME")` Returns `"SYSTEM"` Under NinjaOne — Current User Logic Breaks

**What goes wrong:**
`main.py` calls `_collect_current_user()`, which reads `os.environ.get("USERNAME")`. When NinjaOne executes the tool as the SYSTEM account, `USERNAME` is `"SYSTEM"` (or absent on some configurations). The rendered report shows `current_user: SYSTEM` which is meaningless for an IT audit. Worse, any code that uses `USERNAME` or `USERPROFILE` for output path construction, profile filtering, or Jinja2 template logic will be operating on the SYSTEM account's context, not the logged-in user.

**Specific breakages in existing code:**
- `_collect_current_user()` in `hardware.py` — returns `"SYSTEM"` instead of the actual logged-in username.
- `_detect_msix()` in `apps.py` — opens `HKEY_CURRENT_USER`, which when running as SYSTEM is the SYSTEM user's hive, not any logged-in user's hive. This means Claude, Company Portal, and any other MSIX apps installed per-user will show as "Not Found."
- Any code reading `%USERPROFILE%`, `%TEMP%`, `%APPDATA%` will get SYSTEM-account paths (`C:\Windows\System32\config\systemprofile`), which are unrelated to the audited user.

**Prevention:**

For current user display under SYSTEM, use the Windows session API:
```python
import subprocess

def get_logged_in_user() -> str | None:
    """Return the active console session username via quser/query session.
    Works under SYSTEM account; falls back to USERNAME env var."""
    try:
        result = subprocess.run(
            ["query", "session"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if "Active" in line or "Actif" in line:  # locale-aware
                parts = line.split()
                if parts:
                    return parts[0].lstrip(">")
    except Exception:
        pass
    return os.environ.get("USERNAME") or None
```

For MSIX detection under SYSTEM, enumerate the HKEY_USERS hive rather than HKEY_CURRENT_USER:
```python
import winreg

def _detect_msix_all_users(family_prefix: str) -> tuple[bool, str | None]:
    """Enumerate all loaded user hives in HKU for MSIX packages.
    Required when running as SYSTEM — HKCU is the wrong hive."""
    try:
        with winreg.OpenKey(winreg.HKEY_USERS, "") as hku:
            i = 0
            while True:
                try:
                    sid = winreg.EnumKey(hku, i)
                    i += 1
                except OSError:
                    break
                if sid.startswith("S-1-5-") and "_Classes" not in sid:
                    msix_path = sid + "\\" + _MSIX_REPO_PATH
                    # ... search per-user hive
    except (FileNotFoundError, OSError):
        pass
    return False, None
```

**Warning signs:**
- `current_user` field shows "SYSTEM" in the rendered report.
- Claude and Company Portal always show "Not Found" when run via NinjaOne, but are present when run interactively.
- `USERPROFILE` env var resolves to `C:\Windows\System32\config\systemprofile`.

**Phase to address:** NinjaOne compatibility phase. Audit every `os.environ.get("USERNAME")`, `os.environ.get("USERPROFILE")`, and `HKEY_CURRENT_USER` usage before that phase completes.

---

### Pitfall 3: `input()` at End of `main.py` Hangs NinjaOne Script Execution Forever

**What goes wrong:**
`main.py` ends with `input("\nPress Enter to close this window...")`. NinjaOne captures script output and considers a script "complete" when the process exits. Under SYSTEM account, there is no interactive console and no user to press Enter. The script hangs indefinitely, NinjaOne eventually times it out (default: 10 minutes), and the run is marked as failed even though the report was successfully written.

**Why it happens:**
`input()` blocks on stdin. Under NinjaOne's SYSTEM-context execution, stdin is either closed, connected to `/dev/null`-equivalent, or connected to a pipe that never sends data.

**Prevention:**
Gate the interactive pause on whether the process has an interactive console:
```python
def _should_pause() -> bool:
    """Return True only when running interactively (not under NinjaOne or CI)."""
    # sys.stdin.isatty() returns False when stdin is piped or closed
    import sys
    return sys.stdin is not None and sys.stdin.isatty()

# In main():
if _should_pause():
    input("\nPress Enter to close this window, then eject the USB drive.")
```

Also gate `os.startfile()` on the same condition — attempting to open a browser from a SYSTEM-account process with no desktop session will raise `OSError` (already caught) but is wasted work.

**Warning signs:**
- NinjaOne script runs show no timeout error but take exactly as long as the configured timeout before failing.
- The HTML is written correctly but NinjaOne marks the run as failed.

**Phase to address:** NinjaOne compatibility phase. This is a one-line guard but must be decided intentionally.

---

### Pitfall 4: Warnings System Disk Percent Calculation — `disk.free` vs `disk.percent`

**What goes wrong:**
The warnings system calculates disk usage percentage using `(disk.total - disk.free) / disk.total * 100`. This seems correct but diverges from what Windows Explorer shows users by 0-5%. On macOS (for the future Mac build), it diverges by up to 5% on APFS volumes because `disk.free` includes space reserved for APFS snapshots that users cannot directly use.

The subtler problem: `psutil.disk_usage().percent` is already computed for you, but it uses a different formula — one that matches `df` on UNIX and is 5% larger on Linux/macOS because it treats root-reserved space as "used." Using `disk.percent` directly in warnings will trigger false "low disk" warnings on Mac when the volume is not actually full from the user's perspective.

**The actual psutil fields:**
- `disk.total` — raw filesystem capacity
- `disk.used` — space consumed by data
- `disk.free` — space available to the process writing (may exclude root-reserved blocks on UNIX)
- `disk.percent` — `used / (used + free) * 100` on UNIX (matches `df`; ~5% larger than naive `used/total`)

**Correct approach for this tool:**
```python
disk = psutil.disk_usage("C:\\")   # Windows: disk.free == disk available
disk_pct = round((disk.total - disk.free) / disk.total * 100, 1)
# Use this for the warning threshold, not disk.percent
# This gives "X% of disk is occupied" matching Windows Explorer
```

On Windows, `disk.free` equals what Explorer shows as "free space" — no reserved blocks. Use the naive formula `(total - free) / total` for consistency with what IT staff see in Windows Explorer.

The existing `_collect_memory_and_disk` stores `disk_free_gb` using `disk.free` (correct). The warnings system must use `disk_free_gb` and `disk_total_gb` from the model — **not** re-query `psutil` and not use `disk.percent`.

**Falsy guard on disk values (v1.0 existing pitfall, still applies):**
The model has `disk_total_gb: float | None` and `disk_free_gb: float | None`. A disk at 0.0% free is valid and falsy. Any warning threshold comparison must use `is not None` guards:
```python
# WRONG — 0.0 triggers "not collected" branch
if report.disk_free_gb and report.disk_total_gb:
    pct = ...

# CORRECT
if report.disk_free_gb is not None and report.disk_total_gb is not None:
    pct = (report.disk_total_gb - report.disk_free_gb) / report.disk_total_gb * 100
```

**Warning signs:**
- Warning fires on a machine with 50 GB free on a 1 TB drive because `0.0` free was never triggered but the `is not None` guard was omitted.
- Disk percentage shown in the warning UI is 5% higher than what Windows Explorer shows.

**Phase to address:** Warnings implementation phase. Define the `disk_pct` formula in the model layer once and reference it everywhere.

---

### Pitfall 5: Windows Version Detection — `platform.version()` Returns `"10.0.XXXXX"` for Windows 11

**What goes wrong:**
The existing `_collect_os()` in `hardware.py` already handles this correctly (build >= 22000 → "Windows 11"). The new **warnings system** adds an OS version check (e.g., "Windows 10 end of life approaching" or "Windows 11 below minimum feature update"). The pitfall is that new warning code written without reading `hardware.py` re-implements version detection incorrectly by checking `platform.release()` which returns `"10"` for both Windows 10 and Windows 11.

**Correct signal:** The `report.os_version` ("Windows 10" or "Windows 11") and `report.os_build` (build number string like "22621") are already populated by `_collect_os()`. The warnings system must consume these model fields — not call `platform` again.

**OS build number for feature update warnings:**
If the warning checks "is this OS below a supported build," use `int(report.os_build)` and compare against the documented minimum. Key build milestones:
- Windows 10 22H2: 19045 (final Windows 10 feature update; EOL October 2025)
- Windows 11 23H2: 22631
- Windows 11 24H2: 26100

**Warning signs:**
- Warnings system reports "Windows 11" as "outdated" because it checked `platform.release()` == "10".
- New warning code imports `platform` directly rather than reading from `report.os_build`.

**Phase to address:** Warnings implementation phase. Add a comment in the warnings module: "Do not call `platform` here — use `report.os_version` and `report.os_build` from `collect_hardware`."

---

### Pitfall 6: Mac `psutil.cpu_freq()` Returns `None` on Apple Silicon — Confirmed Bug

**What goes wrong:**
The Mac collector calls `psutil.cpu_freq()` to populate `cpu_model` or a CPU speed field. On all Apple Silicon Macs (M1, M2, M3, M4 series), `psutil.cpu_freq()` returns `None`. This is a confirmed, long-standing open issue in psutil (GitHub issue #1892) with no fix as of 2026. The `hw.cpufrequency` sysctl was removed by Apple on ARM. The tool crashes or shows `None` in the CPU speed field on every Mac the company deploys.

**Prevention:**
Do not call `psutil.cpu_freq()` on macOS at all. Use `system_profiler SPHardwareDataType -json` for CPU information instead:
```python
import json, subprocess

def _collect_mac_hardware() -> dict:
    result = subprocess.run(
        ["system_profiler", "SPHardwareDataType", "-json"],
        capture_output=True, text=True, timeout=15
    )
    data = json.loads(result.stdout)
    hw = data.get("SPHardwareDataType", [{}])[0]
    return {
        "cpu_model": hw.get("cpu_type", hw.get("chip_type")),  # see Pitfall 7
        "ram_gb": _parse_mac_ram(hw.get("physical_memory", "")),
        "serial_number": hw.get("serial_number"),
    }
```

`psutil.virtual_memory().total` works fine on Apple Silicon for RAM.

**Warning signs:**
- Mac collector test passes on Intel Mac but fails or returns `None` on any M-series test machine.
- `cpu_model` field is `None` in the rendered report on all M-series Macs.

**Phase to address:** Mac collector implementation. Add `# psutil.cpu_freq() DOES NOT WORK on Apple Silicon — never call it on macOS` as a module-level comment in the Mac hardware collector.

---

### Pitfall 7: `system_profiler` JSON Key Names Changed Between Intel and Apple Silicon — `cpu_type` vs `chip_type`

**What goes wrong:**
`system_profiler SPHardwareDataType -json` returns `cpu_type` on Intel Macs and `chip_type` on Apple Silicon Macs. Code that only checks `cpu_type` returns `None` on M-series and code that only checks `chip_type` returns `None` on Intel. Master Electronics is mid-fleet with some Intel and some M-series Macs.

**The actual key names:**
- Intel Mac: `"cpu_type": "Intel Core i7"`, no `chip_type` key
- Apple Silicon: `"chip_type": "Apple M2 Pro"`, no `cpu_type` key

Also relevant: `"physical_memory"` is a string like `"16 GB"` not a number — requires parsing.

**Prevention:**
Always check both keys with fallback:
```python
cpu_model = hw.get("chip_type") or hw.get("cpu_type")
```

For RAM parsing:
```python
def _parse_mac_ram(mem_str: str) -> float | None:
    """Parse '16 GB' or '8 GB' into float GBs. Returns None on parse failure."""
    parts = mem_str.strip().split()
    if len(parts) == 2 and parts[1].upper() == "GB":
        try:
            return float(parts[0])
        except ValueError:
            pass
    return None
```

**Warning signs:**
- All Intel Macs show correct CPU model; all M-series show `None`.
- All M-series show correct CPU model; all Intel show `None`.

**Phase to address:** Mac collector implementation. Add a unit test that validates both key names using mocked `system_profiler` JSON fixtures for both architectures.

---

### Pitfall 8: macOS App Detection — `/Applications` (System) vs `~/Applications` (User) vs Managed MDM Path

**What goes wrong:**
Mac app detection checks only `/Applications/AppName.app`. Several common enterprise apps are installed differently:
- Apps deployed via Intune/MDM may land in `/Applications` (device context) or fail to appear there if deployment failed silently.
- User-installed apps via the Mac App Store install to `/Applications` if the user has admin rights, or to `~/Applications` if they don't.
- CrowdStrike on Mac has migrated from `/Library/CS/` (older) to `/Applications/Falcon.app/` (current, post-2023). Both may coexist during upgrades.
- Zoom on Mac installs to `~/Applications/` (user context) by default for non-admin installs, not `/Applications/`.

A tool that only checks `/Applications/AppName.app` will miss user-installed Zoom and report it as absent on machines where it is running.

**Correct detection strategy for each app:**
```python
# Zoom — check both system and user paths
ZOOM_PATHS = [
    Path("/Applications/zoom.us.app"),
    Path.home() / "Applications/zoom.us.app",
]

# CrowdStrike — check both old and new paths
CROWDSTRIKE_MAC_PATHS = [
    Path("/Applications/Falcon.app"),
    Path("/Library/CS/falconctl"),  # older deployments
]

# Chrome — standard /Applications only for managed installs
CHROME_PATHS = [
    Path("/Applications/Google Chrome.app"),
    Path.home() / "Applications/Google Chrome.app",
]
```

Additionally, read `Contents/Info.plist` from the `.app` bundle to confirm identity and get version:
```python
import plistlib
from pathlib import Path

def _read_app_plist(app_path: Path) -> dict:
    plist_path = app_path / "Contents/Info.plist"
    if not plist_path.exists():
        return {}
    with open(plist_path, "rb") as f:
        return plistlib.load(f)

# Then: plist.get("CFBundleShortVersionString") for version
#       plist.get("CFBundleIdentifier") for identity confirmation
```

**Warning signs:**
- Zoom reports "Not Found" on Mac but Zoom is visibly running in the menu bar.
- CrowdStrike reports "Not Found" on an older Mac fleet enrolled before the Falcon.app migration.

**Phase to address:** Mac app detection implementation. Create a test fixture directory with minimal fake `.app` bundles containing `Contents/Info.plist` for each target app.

---

### Pitfall 9: macOS `platform.mac_ver()` Returns `10.16` Instead of `11+` on Some Python Builds

**What goes wrong:**
The Mac OS version check uses `platform.mac_ver()` to get the macOS release string. On some Python builds (particularly those compiled with older SDKs or when `SYSTEM_VERSION_COMPAT=1` is set), `platform.mac_ver()` returns `"10.16"` on machines running macOS Big Sur 11.x or later. An OS version warning comparing against "minimum macOS 12" will incorrectly fire on Monterey and Ventura machines.

**Prevention:**
Use `subprocess` to call `sw_vers` directly, which always returns the correct human-visible version:
```python
import subprocess

def get_macos_version() -> str | None:
    """Return macOS version string (e.g. '14.5') via sw_vers. Always correct."""
    try:
        result = subprocess.run(
            ["sw_vers", "-productVersion"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or None
    except Exception:
        return None
```

Then parse into major/minor for comparison:
```python
version_str = get_macos_version()  # "14.5"
if version_str:
    parts = version_str.split(".")
    major = int(parts[0]) if parts else 0
    # major >= 14 is Sonoma, >= 15 is Sequoia
```

**Warning signs:**
- `platform.mac_ver()` returns a version string starting with "10" on a machine running macOS 14 Sonoma.
- OS version warning fires incorrectly on modern Macs.

**Phase to address:** Mac collector implementation. Do not use `platform.mac_ver()` on macOS at all — use `sw_vers` via subprocess.

---

### Pitfall 10: Mac User Profile Enumeration — `/Users` Listing vs `dscl` — SIP and Permission Differences

**What goes wrong:**
The Windows collector uses HKLM ProfileList (a clean registry read). The Mac equivalent is listing `/Users/` directory contents, but this includes system accounts (`_www`, `_ftp`, `daemon`, etc.) that look like real user directories. Filtering by `_` prefix catches most system accounts but not all (`nobody`, `Guest`). Additionally, a standard user process cannot read the home directory contents of other users (macOS Catalina and later restrict this by default), so checking whether a profile is "active" by testing file access inside `~otheruser/` will raise `PermissionError`.

The correct approach uses `dscl` (Directory Service CLI), which reads user account records without requiring access to the home directory:
```python
import subprocess

def enumerate_mac_profiles() -> list[str]:
    """List real human user accounts via dscl. Excludes system accounts.
    Works at standard user privilege."""
    try:
        result = subprocess.run(
            ["dscl", ".", "-list", "/Users"],
            capture_output=True, text=True, timeout=5
        )
        users = []
        for line in result.stdout.splitlines():
            name = line.strip()
            # Skip system/service accounts (underscore prefix, known names)
            if name and not name.startswith("_") and name not in {
                "nobody", "daemon", "root", "Guest"
            }:
                users.append(name)
        return users
    except Exception:
        return []
```

**SIP note:** SIP (System Integrity Protection) does **not** block `dscl` reads at standard user privilege — SIP blocks writes to `/System`, `/usr`, `/bin`, `/sbin`. Reading user account metadata is unrestricted.

**Warning signs:**
- Mac profile list includes `_www`, `_spotlight`, `_networkd` alongside real users.
- `PermissionError` raised when attempting to verify a profile by reading files inside another user's home directory.

**Phase to address:** Mac collector implementation. Mirror the Windows filter pattern — enumerate all, then filter against a known system account list from `dscl`.

---

### Pitfall 11: NinjaOne Output Path — USB Drive May Not Be Available; SYSTEM Account Cannot Write to It

**What goes wrong:**
The v1.0 tool writes to `Path(sys.executable).parent / "logs/"`. When run interactively from a USB drive, this is the USB drive. When run remotely via NinjaOne, `sys.executable` points to wherever NinjaOne deployed or cached the script on the local disk — not a USB drive. NinjaOne typically copies scripts to a temp path or a known RMM cache directory. The "logs" directory will be written to that local path, which is writable by SYSTEM but is not the USB drive and is not accessible to IT staff browsing the USB.

**Two distinct execution modes need two distinct output strategies:**
```python
import os, sys
from pathlib import Path

def resolve_output_dir() -> Path:
    """Return output directory appropriate for the execution context.

    Interactive (USB): Path(sys.executable).parent / "logs"
    NinjaOne (SYSTEM): C:\ProgramData\MasterElectronics\StatusReport\logs
                       or %ProgramData% fallback
    """
    # Detect NinjaOne SYSTEM context
    username = os.environ.get("USERNAME", "")
    if username.upper() in ("SYSTEM", "") or not sys.stdin.isatty():
        # NinjaOne / headless execution — write to a stable, SYSTEM-writable location
        program_data = os.environ.get("ProgramData", r"C:\ProgramData")
        out_dir = Path(program_data) / "MasterElectronics" / "StatusReport" / "logs"
    else:
        # Interactive USB execution — keep v1.0 behavior
        out_dir = Path(sys.executable).parent / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir
```

`C:\ProgramData` is the correct SYSTEM-writable, all-user-visible path on Windows. It does not require elevation to write to (SYSTEM has full control), survives reboots, and IT staff can retrieve reports via NinjaOne's file retrieval or by browsing the path over the network.

**Permission reality on USB drives from SYSTEM:**
FAT32 USB drives have no NTFS permission layer — SYSTEM can write to them. NTFS-formatted USB drives may have ACLs that do not include SYSTEM. Do not assume SYSTEM can write to the USB drive. The output path must not depend on USB availability in the NinjaOne execution context.

**Warning signs:**
- NinjaOne run succeeds (process exits 0) but no report appears on the USB drive.
- `sys.executable` path when launched via NinjaOne contains `C:\Windows\Temp\NinjaRMM` or similar — the USB drive path is absent.

**Phase to address:** NinjaOne compatibility phase. This is an architectural decision that must be made before any NinjaOne testing begins. Document the `ProgramData` output path in the NinjaOne runbook.

---

### Pitfall 12: NinjaOne stdout Buffering — Summary Line Never Appears in Script Output Log

**What goes wrong:**
NinjaOne captures the stdout of the script and displays it in the script run history. Python stdout is block-buffered by default when not attached to a TTY (i.e., when run under NinjaOne). If the script writes a summary line at the end and then exits normally, the buffer may not be flushed before the process terminates on Windows, and the NinjaOne log shows no output. This makes every remote run appear silent/hung until IT staff look at `C:\ProgramData\...\logs`.

**Prevention:**
Two options:
1. Set `PYTHONUNBUFFERED=1` in the PyInstaller spec's runtime environment — forces unbuffered stdout regardless of TTY detection.
2. Call `sys.stdout.reconfigure(line_buffering=True)` at the top of `main()` (Python 3.7+) and add explicit `sys.stdout.flush()` after each progress print.

The correct approach for a frozen PyInstaller exe is to add to the spec:
```python
# In status_report.spec
exe = EXE(
    ...
    env={"PYTHONUNBUFFERED": "1"},  # Force line-buffered stdout under NinjaOne
)
```

Or in `main.py` before any print calls:
```python
import sys
if not sys.stdout.isatty():
    sys.stdout.reconfigure(line_buffering=True)
```

NinjaOne script output is also limited — keep the stdout summary under ~500 characters. Long output may be truncated. The summary line should be: `STATUS: OK | Host: HOSTNAME | Apps: X/Y detected | Disk: Z% free`.

**Warning signs:**
- NinjaOne script history shows "Script completed" with empty output body.
- Status prints appear in local dev runs but not in NinjaOne logs.

**Phase to address:** NinjaOne compatibility phase.

---

### Pitfall 13: PyInstaller macOS `.app` Bundle — Code Signing and Notarization Required for Gatekeeper

**What goes wrong:**
The Windows `--onedir` build passes CrowdStrike because it is not `--onefile`. On macOS, Gatekeeper applies separately from CrowdStrike, and it **blocks any unsigned or unnotarized binary** distributed outside the Mac App Store when downloaded from the internet (quarantine attribute). IT staff who download the Mac build from Slack or email will see "cannot be opened because the developer cannot be verified." USB distribution bypasses this for the quarantine check, but Gatekeeper still checks code signature on Sonoma/Sequoia for hardened runtime executables.

**For USB distribution (likely for v2.0):**
The quarantine extended attribute (`com.apple.quarantine`) is set on files downloaded from the internet but **not** on files copied from a USB drive formatted as FAT32/exFAT. USB distribution avoids the Gatekeeper quarantine problem without notarization, which is why the Windows version works on USB without SmartScreen problems (the `--onedir` layout helps, but USB also lacks the quarantine attribute).

**For Notarization (if distributing via network/Slack):**
PyInstaller `--onedir` + notarization requires:
1. Sign with a Developer ID Application certificate (not just ad-hoc signing)
2. Sign **every binary** in `_internal/` with `codesign --deep --force --options runtime`
3. Notarize the `.zip` or `.dmg` containing the bundle via `notarytool`
4. Staple the ticket: `xcrun stapler staple`

Note from the PyInstaller issue tracker (2024): `--onedir` notarization fails unless every `.dylib` and helper binary inside `_internal/` is individually signed before notarizing the outer bundle. `--deep` flag alone is insufficient for notarized submissions.

**For v2.0, recommendation:** USB distribution avoids the notarization problem. Mac builds should be tested on a Mac that is **not** quarantine-flagging the files (i.e., transfer via USB or direct rsync, not via web download). Document this distribution requirement in the Mac runbook.

**Warning signs:**
- macOS shows "cannot be opened because the developer cannot be verified" dialog.
- The quarantine attribute is visible: `xattr -l StatusReport.app | grep quarantine`.

**Phase to address:** Mac packaging phase. Decide USB vs. network distribution first. If network distribution is required, budget for Developer ID Apple certificate and notarization pipeline.

---

## Moderate Pitfalls

### Pitfall 14: `_detect_msix()` Always Returns False When Run as SYSTEM — Claude and Company Portal Miss

**What goes wrong:**
The existing `_detect_msix()` in `apps.py` opens `HKEY_CURRENT_USER`. Under SYSTEM, `HKCU` is the SYSTEM account's hive, which contains no MSIX package registrations. Claude, Company Portal, and any per-user MSIX app will always report "Not Found" when run via NinjaOne.

**Prevention:** (See full code in Pitfall 2.) Enumerate `HKEY_USERS` and check each per-user hive. This is the correct approach for SYSTEM-context MSIX detection.

**Phase to address:** NinjaOne compatibility phase. Before the phase closes, run a NinjaOne test on a machine with Claude installed and verify it shows as detected.

---

### Pitfall 15: Company Portal Registry Stale Key After Unenrollment — Same Pattern as App Uninstall

**What goes wrong:**
The `HKLM\SOFTWARE\Microsoft\Enrollments\{GUID}` key (used for MDM enrollment detection per Pitfall 1) sometimes persists after unenrollment. If the tool uses GUID key existence alone as the enrollment signal, it will report "Enrolled" on a device that was enrolled in the past but is now unenrolled.

**Prevention:** Require the `UPN` value within the GUID subkey (as shown in Pitfall 1). A GUID key without `UPN` is a stale artifact. Label the result "Enrolled (confirmed)" vs. "Enrolled (stale — verify)".

**Phase to address:** Company Portal detection phase. Add a test fixture that simulates a GUID key without `UPN` to confirm the stale detection logic.

---

### Pitfall 16: macOS `subprocess` Calls Time Out on Heavily Loaded Machines — `system_profiler` Is Slow

**What goes wrong:**
`system_profiler SPHardwareDataType -json` typically returns in 1-2 seconds but can take 10-15 seconds on an overloaded Mac or one with a slow disk. Without a timeout, the Mac collector hangs the entire audit tool. The existing Windows pattern uses WMI with no explicit timeout (WMI has its own internal timeout), but `subprocess.run(..., timeout=N)` must be specified explicitly on macOS.

**Prevention:**
All Mac subprocess calls must specify `timeout=15` (generous but bounded):
```python
result = subprocess.run(
    ["system_profiler", "SPHardwareDataType", "-json"],
    capture_output=True, text=True, timeout=15
)
```

Wrap in `try/except subprocess.TimeoutExpired` and treat as a collection failure, not a crash.

**Phase to address:** Mac collector implementation. Every `subprocess.run()` in the Mac module must have a timeout.

---

### Pitfall 17: NinjaOne SYSTEM Account — `wmi` Module Requires COM, COM Available Under SYSTEM

**What goes wrong (non-issue, but often assumed to be one):** The `wmi` Python module uses COM. Under SYSTEM, COM is available — SYSTEM has access to all COM servers. The `_wmi_module`/`_WMI_AVAILABLE` guard pattern in `hardware.py` will work correctly under NinjaOne. This is explicitly NOT a blocker.

**What IS a problem:** `wmi.WMI()` connects to the local WMI namespace. Under SYSTEM, this succeeds. However, if the PyInstaller exe is deployed via NinjaOne to a different drive path than expected, the `_internal/` directory containing the bundled `wmi` `.pyd` files must be co-located with the `.exe`. NinjaOne typically runs scripts from a fixed path — confirm the full `_internal/` directory is deployed, not just the `.exe`.

**Phase to address:** NinjaOne packaging/testing phase. Confirm the full `--onedir` bundle structure is deployed, not just the launcher executable.

---

### Pitfall 18: Mac Plist Parsing — `plistlib.load()` Fails on Binary Plists in Older `Info.plist` Files

**What goes wrong:**
`plistlib.load()` in Python 3.12 handles both XML (`<?xml`) and binary (`bplist00`) plist formats. However, some very old `.app` bundles (PowerPC era, pre-2009) have binary plists that use format version 01, which Python's `plistlib` cannot parse. This is not a concern for any current application being detected (CrowdStrike, Zoom, Chrome, NinjaOne all have modern plists), but a generic Mac app detection function that calls `plistlib.load()` without `try/except` will crash if it encounters a legacy bundle.

**Prevention:** Wrap all `plistlib.load()` calls in `try/except (Exception,)` and treat parse failure as "version unknown" — the app is still detected by path existence. This matches the existing pattern in `apps.py` for `QueryValueEx` failures.

**Phase to address:** Mac app detection implementation.

---

## Minor Pitfalls

### Pitfall 19: Warnings Collapsible HTML Box — Jinja2 Template Already Has HP Bar False Guard; Warning Box Needs Same

**What goes wrong:**
The renderer has a guard for the disk HP bar (from the v1.0 pitfall doc — `disk_free_gb` can be `None`). The new warnings system adds a `disk_pct` warning threshold. If the Jinja2 template renders the warning box before the `if disk_pct is not none` check, it renders an empty or broken warning box on machines where disk data could not be collected.

**Prevention:** Add the same `is not none` pattern used in the HP bar to the warning box template block. The warning box should only render if at least one warning condition is `True`.

**Phase to address:** Warnings rendering phase.

---

### Pitfall 20: `os.startfile()` Under NinjaOne SYSTEM — Raises `OSError` — Already Caught But Logs a Ghost Warning

**What goes wrong:**
`main.py` wraps `os.startfile()` in `try/except OSError: pass`. Under NinjaOne, `os.startfile()` raises because there is no user desktop session to open the HTML in. The exception is silently swallowed (correct behavior), but if a warning is added for other `OSError` cases, this branch must not be conflated.

**Prevention:** Already handled in v1.0 `main.py`. No change needed. **Do not add logging inside the `os.startfile` except block** — it will produce a misleading warning in the NinjaOne output log on every remote run.

**Phase to address:** NinjaOne compatibility review.

---

### Pitfall 21: Mac Build — `winreg` Import in `collectors/windows/apps.py` Will Crash Mac Interpreter

**What goes wrong:**
`winreg` is a Windows-only stdlib module. The Mac collector must live in `collectors/mac/` and must never import `winreg`. If someone adds a shared utility module that imports `winreg` at the top level (not inside a `if sys.platform == "win32"` guard), the Mac build will fail at import time with `ModuleNotFoundError: No module named 'winreg'`.

**Prevention:** The existing architecture already separates `collectors/windows/` from future `collectors/mac/`. Enforce the rule: **`winreg` must never appear outside `collectors/windows/`**. Add a CI check (grep or a test) that asserts `winreg` is not imported in any file outside the `windows/` collector directory. Do the same for `wmi`.

**Phase to address:** Mac platform scaffolding phase (the first phase of Mac support).

---

## Integration Gotchas — v2.0 Specific

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Company Portal vs MDM enrollment | Detect MSIX package and call it "enrolled" | Detect `HKLM\SOFTWARE\Microsoft\Enrollments\{GUID}\UPN` for enrollment; detect MSIX for app presence; report both separately |
| SYSTEM context current user | `os.environ.get("USERNAME")` returns "SYSTEM" | Use `query session` subprocess to find the active console session user |
| SYSTEM context MSIX detection | `HKCU` is SYSTEM's hive; Claude shows "Not Found" | Enumerate `HKEY_USERS` across all loaded user hives |
| NinjaOne stdout | Block-buffered; summary line may not appear in log | `sys.stdout.reconfigure(line_buffering=True)` at startup when `not sys.stdout.isatty()` |
| NinjaOne output path | `sys.executable` points to RMM cache, not USB | Write to `C:\ProgramData\MasterElectronics\StatusReport\logs\` in SYSTEM context |
| NinjaOne `input()` hang | Script hangs forever waiting for Enter | Gate on `sys.stdin.isatty()` |
| Mac `psutil.cpu_freq()` | Returns `None` on M1/M2/M3/M4 | Use `system_profiler SPHardwareDataType -json` exclusively for Mac CPU info |
| Mac `system_profiler` key names | `cpu_type` (Intel) vs `chip_type` (Apple Silicon) | `hw.get("chip_type") or hw.get("cpu_type")` with both fallbacks |
| Mac OS version | `platform.mac_ver()` returns "10.16" on macOS 11+ | Use `sw_vers -productVersion` via subprocess |
| Mac app detection | Only checks `/Applications/` | Check `/Applications/` and `~/Applications/` (Zoom especially installs to user context) |
| Mac user profiles | `/Users/` listing includes system accounts | Filter with `dscl . -list /Users` and exclude `_`-prefixed and known system names |
| Disk pct warning | Uses `disk.percent` from psutil (includes root reserve) | Use `(disk_total_gb - disk_free_gb) / disk_total_gb` from model fields; guard `is not None` |
| Windows 11 detection in warnings | Re-implements via `platform.release()` == "10" for both W10/W11 | Consume `report.os_version` and `report.os_build` already set by `_collect_os()` |
| `winreg` on Mac | `import winreg` in a shared module fails on Mac interpreter | Confine `winreg` and `wmi` imports strictly to `collectors/windows/` |

---

## Phase-Specific Warnings — v2.0

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Company Portal detection | Detecting installation vs enrollment — different signals | Two checks: `HKLM\Enrollments\{GUID}\UPN` for enrollment; MSIX for app; document distinction in `AppStatus.name` |
| Warnings system — disk | `is not None` guard on `disk_free_gb`; wrong formula from psutil | Use model fields; use `(total - free) / total` not `disk.percent` |
| Warnings system — OS | Re-implementing version detection instead of reading model fields | Consume `report.os_version` / `report.os_build`; no `platform` calls in warnings module |
| Mac hardware collector | `psutil.cpu_freq()` → `None` on Apple Silicon | Use `system_profiler` JSON; both `cpu_type` and `chip_type` keys |
| Mac hardware collector | `platform.mac_ver()` returns 10.16 on modern macOS | Use `sw_vers -productVersion` subprocess |
| Mac app detection | `/Applications` only misses user-installed Zoom; old CrowdStrike path | Check both paths; verify CrowdStrike path generation with `ls /Library/CS` on a test machine |
| Mac user profiles | System accounts mixed with real users | `dscl . -list /Users` + filter |
| Mac platform abstraction | `winreg`/`wmi` import in shared module crashes Mac interpreter | Enforce `winreg` and `wmi` to `collectors/windows/` only; add CI grep check |
| NinjaOne compatibility | `USERNAME` == SYSTEM; `HKCU` is SYSTEM's hive | `query session` for current user; `HKEY_USERS` enumeration for MSIX |
| NinjaOne compatibility | `input()` hangs script; `os.startfile()` raises OSError | Gate both on `sys.stdin.isatty()` |
| NinjaOne compatibility | stdout block-buffered; summary invisible in log | `sys.stdout.reconfigure(line_buffering=True)` when not TTY |
| NinjaOne compatibility | Output path writes to RMM cache, not USB | Detect SYSTEM context; write to `%ProgramData%\MasterElectronics\StatusReport\logs` |
| NinjaOne packaging | Only `.exe` deployed, `_internal/` missing | Confirm full `--onedir` bundle structure in NinjaOne script deployment; test with a `wmi` call to verify bundled `.pyd` |
| Mac PyInstaller packaging | Gatekeeper blocks unsigned binary when distributed via network | USB distribution avoids quarantine attribute; document USB-only requirement for Mac v2.0 |

---

## Technical Debt Patterns — v2.0 Additions

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Detect Company Portal MSIX = "Intune enrolled" | One check for one row | False positives on sideloaded CP; false negatives on Autopilot-enrolled machines without CP | Never — use enrollment registry signal |
| `os.environ.get("USERNAME")` everywhere | Works in dev/interactive | Returns "SYSTEM" under NinjaOne; breaks current user display and HKCU MSIX detection | Never in SYSTEM-context code paths |
| `HKCU` for MSIX detection in NinjaOne mode | Existing `_detect_msix()` unchanged | Claude, CP always "Not Found" in NinjaOne runs | Never for SYSTEM-context runs |
| `input()` without TTY guard | Familiar UX for interactive use | Hangs NinjaOne scripts forever | Never without `isatty()` guard |
| `psutil.cpu_freq()` on macOS | Single API call | Returns `None` on 100% of M-series Macs | Never on macOS |
| Check only `/Applications/` on Mac | Simple path check | Misses user-installed Zoom, pre-2023 CrowdStrike | Never — always check both paths |
| `platform.mac_ver()` for OS version | One-liner | Returns "10.16" on macOS 11+ in some Python builds | Never — use `sw_vers` subprocess |
| `disk.percent` from psutil for warning threshold | One-liner | 5% discrepancy from Windows Explorer on UNIX; misleads IT staff | Never — compute from model fields |

---

## Sources

- psutil disk_usage reserved blocks issue: https://github.com/giampaolo/psutil/issues/829
- psutil `cpu_freq()` broken on Apple M1 (confirmed open issue): https://github.com/giampaolo/psutil/issues/1892
- MDM enrollment registry keys (`HKLM\SOFTWARE\Microsoft\Enrollments`): https://en.ittrip.xyz/windows/enrollments-registry-check
- Intune enrollment registry and UPN detection: https://techcommunity.microsoft.com/discussions/microsoft-intune/intune-re-enrollment-registry-key-mmpcenrollmentflag/4423269
- CrowdStrike on macOS — new path `/Applications/Falcon.app`: https://www.applivery.com/docs/mobile-device-management/apple-mdm/macos/configure-crowdstrike-falcon-sensor-on-macos-devices/
- PyInstaller `--onedir` macOS notarization issues (2024): https://github.com/pyinstaller/pyinstaller/issues/8927
- Windows 11 detection — build number 22000 threshold: https://learn.microsoft.com/en-us/answers/questions/547050/win32-api-to-detect-windows-11
- `platform.mac_ver()` returns 10.16 on macOS Big Sur+: https://bugs.python.org/issue35344
- Python stdout buffering under non-TTY: `sys.stdout.reconfigure(line_buffering=True)` — https://discuss.python.org/t/set-sys-stdout-line-buffering-from-environment/23345
- NinjaOne SYSTEM vs current user execution: https://www.ninjaone.com/docs/scripting-and-automation/using-variables-automation-scripts/
- `C:\ProgramData` as SYSTEM-writable output path: https://adamtheautomator.com/powershell-environment-variables/
- macOS `dscl` for user enumeration: https://ss64.com/mac/dscl.html
- CrowdStrike Mac falconctl stats command: https://oit.duke.edu/help/articles/kb0035361/
- Intune Company Portal vs enrollment distinction: https://techcommunity.microsoft.com/discussions/microsoft-intune/web-based-device-enrollment-vs-company-portal/4397015

---

*Pitfalls research for: StatusReport v2.0 — Company Portal, Warnings, Mac Parity, NinjaOne*
*Researched: 2026-05-07*
*Replaces v1.0 pitfalls doc from 2026-05-04*

---
---

# Pitfalls — v3.0 Additions

**Scope:** Adding WUA COM pending update count, uptime/UPTIME_STALE, DCU/LSU vendor detection, JSON serialization, and extended CLI flags to the existing codebase.
**Researched:** 2026-05-14

---

## 1. WUA COM API — Windows Update Pending Count (HEALTH-01)

### Pitfall W1: IUpdateSearcher.Search() Makes a Live Network Call and Can Hang

**What goes wrong:** `IUpdateSearcher.Search("IsInstalled=0")` is synchronous. On WSUS-managed machines pointing at a dead or unreachable WSUS server, the call blocks indefinitely — there is no built-in timeout. On pre-enrollment machines with no update server configured, it contacts Microsoft directly. Either way, if the network or service is slow, the call can freeze the entire audit for minutes.

**Why it matters for this system:** StatusReport plugs into machines of unknown configuration. NinjaOne expects the tool to complete on a time budget. A hang is worse than a missing field — the SYSTEM-account process has no user to cancel it.

**Prevention:**
- Set `searcher.Online = False` before calling `Search()`. This reads from the local Windows Update cache only — fast, no network, and sufficient for the IT audit use case (approximate count of deferred updates).
- If `Online=False` is not acceptable (stakeholder insists on live count), wrap `Search()` in a `concurrent.futures.ThreadPoolExecutor` with `future.result(timeout=30)` and catch `TimeoutError`.
- Any thread calling WUA COM must call `pythoncom.CoInitialize()` first (see W3 below).
- On any exception or timeout, return `CollectionResult(value=None, error="WUA search unavailable")` — consistent with existing `_WMI_AVAILABLE` discipline.

---

### Pitfall W2: Standard User Can Search; SYSTEM Can Also Search — But Zero Count May Be Silent Failure

**What goes wrong:** `IUpdateSearcher` (search/read) is available to standard users, power users, and SYSTEM. No elevation is needed for a count query. However, on machines where the Windows Update service (wuauserv) is stopped or disabled by policy, `Search()` returns an empty result set with zero updates — not an error. The collector cannot distinguish "genuinely zero pending updates" from "update service disabled." Reporting `pending_updates=0` when the service is off is a false negative that misleads IT.

**Why it matters for this system:** Managed machines that IT has intentionally disabled auto-update on will always show 0, which is accurate but misleading without the service-state context.

**Prevention:**
- After getting a count of zero, check the wuauserv service state using the existing WMI service detection pattern from `apps.py` (CrowdStrike service check). If wuauserv is stopped or disabled, set `pending_updates` to `None` with error `"Windows Update service not running"`.
- In the HTML template and JSON output, `None` must render as "N/A" (not "0" or "None") so IT staff can distinguish unavailable from zero.

---

### Pitfall W3: COM Initialization Required in Non-Main Threads

**What goes wrong:** `win32com.client.Dispatch("Microsoft.Update.Session")` requires the calling thread to have an initialized COM apartment. On the main thread, pywin32 initializes COM automatically. In any worker thread (required for the timeout pattern in W1), the thread starts with no COM apartment and throws `pywintypes.com_error: CoInitialize has not been called`.

**Prevention:** The thread function that calls WUA must begin with:
```python
import pythoncom
pythoncom.CoInitialize()
try:
    # all WUA calls here
finally:
    pythoncom.CoUninitialize()
```
This must be the first statement before any `win32com.client.Dispatch()` call.

---

### Pitfall W4: PyInstaller --onedir Does Not Auto-Collect All pywin32 DLLs After Hook Removal

**What goes wrong:** PyInstaller removed the automatic `win32com` runtime hook in version 6.6+ (issue #8309). DLLs from the `pywin32_system32` directory — including `pywintypes.dll` — are no longer collected automatically. A frozen `--onedir` build that uses WUA via `win32com` may fail on a clean machine (no Python installed) with `ImportError: DLL load failed while importing pywintypes`.

**Why it matters for this system:** The existing `wmi` module works in the frozen build (already validated in v2.0). WUA via `win32com.client.Dispatch` is a different code path and may require different DLLs.

**Prevention:**
- After implementing the WUA collector, test the frozen bundle on a machine with no Python installed.
- If `pywintypes.dll` is missing, add it to the `.spec` binaries list explicitly, or add `--collect-all pywin32` to the build command.
- Apply the `_WMI_AVAILABLE` guard pattern: wrap `import win32com.client` and `import pythoncom` in a `try/except ImportError` at module load time, set `_WUA_AVAILABLE = False` on failure. The collector body is gated on this flag and returns `CollectionResult(value=None, error="win32com not available")` when false.

---

### Pitfall W5: Windows Update Disabled / WSUS Policy — Zero Count Is Indistinguishable from "No Updates"

This is covered in W2. The key point: always pair the update count with a service-state check. If the service is not running, the count is unreliable regardless of value.

---

## 2. psutil.boot_time() — Uptime (HEALTH-02, WARN-04)

### Pitfall B1: boot_time() Includes Hibernation Time — Inflated Uptime on Laptop Fleet

**What goes wrong:** `psutil.boot_time()` on Windows returns the system boot timestamp. When a machine hibernates and resumes, the system clock continues from pre-hibernation wall time. The result is that `time.time() - psutil.boot_time()` includes all hibernation periods as "uptime." A laptop that hibernates every night appears to have been running for weeks without a reboot.

**Why it matters for this system:** The `UPTIME_STALE` warning (WARN-04) triggers when uptime exceeds a threshold. Master Electronics laptops hibernate frequently. A 7-day threshold would fire on nearly every laptop in the fleet, creating alert fatigue that destroys IT trust in the warning system.

**There is no reliable workaround** for separating hibernate time from uptime using psutil alone. This is a confirmed psutil limitation (issue #2094).

**Prevention:**
- Set the `UPTIME_STALE` threshold conservatively (30 days minimum, not 7 days).
- Word the warning message to acknowledge the limitation: `"No cold boot in 30+ days (includes hibernation time)"` rather than `"Machine has been running for 30 days"`.
- Do not attempt to subtract hibernate durations — the data is not accessible without additional WMI queries that add failure modes.

---

### Pitfall B2: boot_time() Returns a Value ±1 Second Across Calls — Tests Must Mock Both Values

**What goes wrong:** On Windows, `psutil.boot_time()` can return slightly different values on repeated calls within the same process (psutil issue #1007). The 1-second variance is invisible to users but makes tests that assert exact uptime calculations flaky.

**Prevention:** Every test involving uptime calculation must mock both `psutil.boot_time` and `time.time`. Never call the real `psutil.boot_time()` in unit tests. Pattern:
```python
with patch("collectors.windows.health.psutil.boot_time", return_value=1_700_000_000.0), \
     patch("collectors.windows.health.time.time", return_value=1_700_000_000.0 + 86400 * 35):
    result = collect_uptime(report)
```

---

### Pitfall B3: SYSTEM Account Has No Interactive Session — USERNAME Is "SYSTEM"

This is pre-existing behavior covered in v2.0 Pitfall 2. For uptime specifically: `psutil.boot_time()` works correctly under the SYSTEM account. No special privilege handling needed.

---

## 3. Vendor Update Detection — DCU and LSU (VENDOR-01, VENDOR-02)

### Pitfall V1: "Pending Count" Is Not in the Registry — This Requires Running DCU/LSU

**What goes wrong:** Neither Dell Command Update nor Lenovo System Update writes a "pending firmware/driver update count" to the registry. The registry only records installation state and configuration. Obtaining a pending count requires executing the vendor tool in scan mode, which:
- May take 30–120 seconds.
- Requires network or local catalog access.
- May require administrator privileges.
- Has side effects on some versions (triggering background download queues).

**Why it matters for this system:** If VENDOR-01 means "count of pending Dell driver updates," it cannot be implemented as a registry read. If it means "DCU is installed and what version," that is a registry read. This ambiguity must be resolved before the phase begins, or the implementation will need to be rewritten.

**Prevention:** Resolve the requirement with the product owner before writing any code. The recommended scope for v3.0 is presence and version only: "DCU installed: Yes/No, version X.Y.Z." Pending count should be deferred or marked as out of scope unless the team is prepared to execute DCU's CLI and handle all the timeout and privilege implications that entails.

---

### Pitfall V2: DCU DisplayName Varies Across Versions — Strict String Match Fails

**What goes wrong:** Dell Command Update's `DisplayName` in the Uninstall registry key has varied:
- `"Dell Command | Update"` (most common, version 4.x)
- `"Dell Command Update"` (some older builds)
- `"Dell Command | Update for Windows Universal"` (UWP variant)

A strict `DisplayName == "Dell Command | Update"` equality check misses the UWP variant and older naming.

**Prevention:**
- Use case-insensitive substring match: `"dell command" in display_name.lower()`.
- Check all four Uninstall paths (the project already enforces this for app detection in `apps.py`). DCU is always a machine-scope install (HKLM), but checking all four is free and consistent with the existing pattern.

---

### Pitfall V3: LSU Uninstall Key Is in Wow6432Node — Easy to Miss on 64-bit Windows

**What goes wrong:** Lenovo System Update uses an Inno Setup installer and registers under `HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\TVSU_is1` on 64-bit Windows (it is a 32-bit installer). Code that only checks `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\` will miss it on 64-bit machines — which is every target machine in this fleet.

**Prevention:**
- Always check the Wow6432Node path explicitly, or use the existing `UNINSTALL_PATHS` constant from `apps.py` which already enumerates all four paths.
- The `DisplayName` is consistently `"Lenovo System Update"` — this string has not varied across recent versions.

---

### Pitfall V4: Neither DCU Nor LSU Is Installed — Return Presence=False, Not an Error

**What goes wrong:** On non-Dell machines (Lenovo) there is no DCU. On non-Lenovo machines (Dell) there is no LSU. On HP or other hardware, neither is present. If the collector treats "not found in registry" as a collection error, the HTML and JSON will show an error indicator for every non-Dell machine, which is noise.

**Prevention:**
- A missing DCU or LSU is not an error — it is an expected absence. Return `CollectionResult(value={"installed": False, "version": None}, error=None)`.
- Only set `error` on the `CollectionResult` if the registry could not be read due to an OS-level failure (e.g., `PermissionError`), not for the normal "key not found" case.
- The HTML template should render "Not installed" (neutral) rather than a warning indicator when `installed=False`.

---

## 4. JSON Serialization of AuditReport (OUT-V3-01, OUT-V3-02)

### Pitfall J1: dataclasses.asdict() Does Not Handle Path Objects — TypeError at json.dumps()

**What goes wrong:** `dataclasses.asdict()` recursively converts nested dataclasses to dicts, but it passes non-dataclass, non-primitive types through unchanged. A `Path` object in any field will survive `asdict()` and then cause `TypeError: Object of type PosixPath is not JSON serializable` when passed to `json.dumps()`.

**Why it matters for this system:** `AuditReport` does not currently have `Path` fields, but v3.0 adds `--output <path>`. If a `Path` is stored on the report (even temporarily), or if any new collector field is typed as `Path`, the JSON serialization will break silently in testing and loudly in production.

**Prevention:**
- Never store `Path` objects on `AuditReport`. Convert paths to `str` at the boundary where the path is determined.
- Add a custom JSON encoder as a safety net:
  ```python
  import json
  from pathlib import Path

  class _AuditEncoder(json.JSONEncoder):
      def default(self, obj):
          if isinstance(obj, Path):
              return str(obj)
          return super().default(obj)
  ```
  Use `json.dumps(dataclasses.asdict(report), cls=_AuditEncoder, indent=2)`.

---

### Pitfall J2: Optional[T] Fields Serialize as JSON null — None and 0 Must Be Distinguishable

**What goes wrong:** `Optional[T]` fields set to `None` correctly serialize to JSON `null`. However, `pending_updates=0` and `pending_updates=None` are semantically different (zero pending vs. count unavailable) but both look like falsy values in Python. Code that writes `"pending_updates": report.pending_updates or "N/A"` will incorrectly show "N/A" when there are genuinely zero pending updates.

**Prevention:**
- Always use `is not None` guards, never truthiness checks, for count fields that can legitimately be zero.
- In JSON output, `null` is the correct representation for "unavailable." Consumers of the JSON must handle `null`.
- In the HTML template, use `{% if report.pending_updates is not none %}{{ report.pending_updates }}{% else %}N/A{% endif %}` — not `{{ report.pending_updates or "N/A" }}`.

---

### Pitfall J3: stdout JSON Output Breaks on Windows cp1252 Console Encoding

**What goes wrong:** When `--json` writes to stdout and the console is cp1252-encoded (the Windows default in many environments), `print()` with non-ASCII characters raises `UnicodeEncodeError`. PyInstaller-frozen executables may ignore `PYTHONIOENCODING` (pyinstaller issue #2032), making the environment variable workaround unreliable.

**Why it matters for this system:** NinjaOne captures stdout. If `--json` is used in a NinjaOne script, stdout is a pipe with cp1252 encoding. Hostnames with ASCII characters only are safe, but usernames or error messages with non-ASCII characters (accented names) would break.

**Prevention:**
- Use `json.dumps(..., ensure_ascii=True)` (the Python default). This escapes all non-ASCII as `\uXXXX` sequences, which are safe on any encoding.
- Do not set `ensure_ascii=False` for stdout JSON output.
- For file output via `--output`, always open with `encoding="utf-8"` explicitly (consistent with the existing `write_text(html, encoding="utf-8")` pattern).
- Do not call `sys.stdout.reconfigure(encoding="utf-8")` globally — it changes behavior for all subsequent stdout writes including the `[SUMMARY]` line, which NinjaOne parses.

---

### Pitfall J4: AppStatus.sub_apps Is a list[AppStatus] — asdict() Handles It Correctly

This is a non-issue. `dataclasses.asdict()` recursively processes lists of dataclasses. `sub_apps` serializes correctly as a JSON array of objects. Empty `sub_apps` becomes `[]`, not absent. This is correct behavior; document it for JSON consumers but no code change needed.

---

## 5. argparse Extension — New Flags (OUT-V3-01, OUT-V3-02, CLI-V3-01)

### Pitfall A1: pytest Consuming sys.argv — Known Phase 11 Burn — Every New Test Must Patch sys.argv

**What goes wrong:** When pytest runs `test_main.py`, `sys.argv` contains pytest's own arguments. Any test that calls `main.main()` without patching `sys.argv` either fails with "unrecognized arguments" or silently exercises the wrong code path.

This already happened in Phase 11. Every existing test in `test_main.py` patches `sys.argv` explicitly. Every new test added for `--json`, `--output`, and `--app` must do the same.

**Why it matters for this system:** The pattern `patch("sys.argv", ["status_report", "--json"])` must appear in every test that exercises `main.main()` or `_run_cli()`. A test that forgets this patch will pass locally if the developer happens to run pytest without `--verbose` (pytest's own `-v` flag will be interpreted as an unrecognized argument by argparse, raising SystemExit(2) and the test will fail with a confusing error).

**Prevention:**
- Add a `conftest.py` fixture that patches `sys.argv` to `["status_report"]` by default, overridable per-test:
  ```python
  # tests/conftest.py
  import pytest
  from unittest.mock import patch

  @pytest.fixture(autouse=False)
  def clean_argv():
      with patch("sys.argv", ["status_report"]):
          yield
  ```
- All new `--json`, `--output`, `--app` tests must either use this fixture or patch `sys.argv` explicitly with the desired flags.

---

### Pitfall A2: --app + --json Composition — Ambiguous Pipeline Branching

**What goes wrong:** The existing `cli_mode` detection is `cli_mode = args.name or args.serial or args.warnings`. Adding `--json` and `--app` without a clear semantic decision creates branching ambiguity:
- `--json` alone: full pipeline with JSON output instead of HTML? Or CLI-mode JSON?
- `--app name --json`: single-app check with JSON output (clearly CLI mode).
- `--json` without `--app`: could mean "full audit but serialize to JSON" (full pipeline) or "targeted JSON query" (CLI mode).

If `--json` is added to the `cli_mode` guard naively, bare `--json` triggers CLI mode and bypasses HTML rendering, which may or may not be the intent.

**Prevention:**
- Treat `--json` as an output-format modifier, not a mode-selector. The mode (CLI vs full pipeline) is determined by the presence of targeting flags (`--app`, `--name`, `--serial`, `--warnings`).
- `--app <name>` is the CLI-mode trigger. `--json` alone does not trigger CLI mode — it changes the output format of whichever mode is active.
- Update `cli_mode` to: `cli_mode = args.name or args.serial or args.warnings or bool(args.app)`.
- Document this semantic decision as a comment in `main()` before implementation begins.

---

### Pitfall A3: --output Path Must Respect the "No Host Writes" Constraint

**What goes wrong:** `--output <path>` overrides the default `logs/` destination. If a user passes `--output C:\temp\report.json`, the tool writes to the host PC — a direct violation of PKG-02. Under NinjaOne (SYSTEM account), `--output` could write to any path the SYSTEM account can reach.

**Why it matters for this system:** This is the highest-risk v3.0 change from a constraint perspective. The `Path(sys.executable).parent` discipline is foundational to the tool's trust model with IT.

**Prevention:**
- Validate the `--output` path at parse time. One approach: check whether the path is under `Path(sys.executable).parent`; if not, print a warning to stderr and exit unless the user explicitly passes `--allow-host-write` (or similar deliberate override flag).
- Alternatively, document that `--output` is only for NinjaOne / pipeline use cases and update PKG-02 to note this exception explicitly.
- In all tests for `--output`, verify the default behavior (no `--output` flag) still writes under `Path(sys.executable).parent`.

---

### Pitfall A4: Adding New Flags Breaks cli_mode Boundary Detection in Existing Tests

**What goes wrong:** `test_cli_mode_suppresses_summary_line` and `test_no_flags_runs_full_pipeline` test the boundary between CLI mode and full pipeline. If `--json` is added and a test accidentally passes `--json` in `sys.argv` without also triggering a CLI-mode flag, the full pipeline runs, HTML is written (via the patched `write_text`), and the test assertion about `[SUMMARY]` may pass or fail depending on where `--json` output goes.

**Prevention:**
- Run the full existing test suite after every single flag addition before writing any more code. Do not batch multiple flag additions then run tests.
- Add a regression test that specifically asserts `--json` alone (no `--app`, `--name`, `--serial`, `--warnings`) still triggers the full pipeline and still emits `[SUMMARY]`.

---

## 6. AuditReport Model Changes — Impact on Existing Tests

### Pitfall M1: All New AuditReport Fields Must Be Optional with None Default

**What goes wrong:** Every test file in `tests/` that constructs `AuditReport` directly will fail with `TypeError: missing required argument` if any new field is added as a required positional argument (no default value).

Current codebase has these direct `AuditReport` constructions:
- `test_main.py`: `_patched_main()` builds `AuditReport(hostname=..., parsed_hostname=...)`.
- `test_renderer.py`, `test_health_checks.py`: construct `AuditReport` for rendering/warning tests.

Adding even one required field breaks all of them simultaneously.

**Why it matters for this system:** v3.0 adds at minimum: `pending_updates: int | None`, `uptime_seconds: float | None`, `dell_dcu_version: str | None`, `lenovo_lsu_version: str | None`. These must all be `Optional[T] = None` to be backward-compatible.

**Prevention:**
- Enforce the rule: every new field on `AuditReport` must have an `Optional[T]` type annotation and `= None` default. This is already the established pattern for all existing fields (see `models.py`).
- After adding any field to `AuditReport`, run `pytest` before writing the collector code. This proves backward compatibility before anything else changes.

---

### Pitfall M2: fake_collect_all in test_main.py Has a Hardcoded Field List

**What goes wrong:** `test_main.py`'s `fake_collect_all` copies specific named fields from a pre-built report onto the live report:
```python
for field_name in ("os_version", "os_build", "serial_number", "cpu_model", ...):
    setattr(report, field_name, getattr(fixed_report, field_name))
```

New health fields (`pending_updates`, `uptime_seconds`, etc.) are not in this list. This means `test_main.py` tests run with `None` for all new health fields, which is the correct isolated behavior. However, if a test needs to verify `[SUMMARY]` output with uptime included, the field list must be updated intentionally.

**Prevention:**
- Do not make `fake_collect_all` dynamic (e.g., using `dataclasses.fields()`) — this would couple it to unrelated field changes.
- When a test specifically requires a new health field to be populated, add the field name to the list explicitly with a comment explaining why.

---

### Pitfall M3: Jinja2 Template Renders None as the String "None" — Not Blank

**What goes wrong:** Jinja2 renders `{{ report.pending_updates }}` as the string `"None"` when the field is `None`. IT staff will see `"None"` in the character sheet for any health field that could not be collected, which looks like a code bug.

**Prevention:**
- Use the `default()` filter for every new field in the template: `{{ report.pending_updates | default("N/A") }}`.
- Add renderer tests that construct `AuditReport` with all new health fields set to `None` and assert the rendered HTML does not contain the string `"None"`.

---

## Phase-Specific Warnings — v3.0

| Phase Topic | Likely Pitfall | Required Mitigation |
|-------------|---------------|---------------------|
| WUA COM collector | Search() hangs on WSUS-managed or slow machines | Use `Online=False` first; if Live is required, wrap in thread with 30s timeout |
| WUA COM collector | Missing pywin32 DLLs in frozen bundle | Test frozen build on clean machine; add `_WUA_AVAILABLE` guard mirroring `_WMI_AVAILABLE` |
| WUA COM collector | Zero count when wuauserv is disabled | Check wuauserv state; return `None` not `0` when service is not running |
| WUA COM in thread | `CoInitialize has not been called` error | Call `pythoncom.CoInitialize()` at start of every worker thread that touches COM |
| Uptime collector | Inflated uptime from hibernation on laptop fleet | Use 30-day threshold minimum; document limitation in warning message text |
| Uptime tests | Flaky tests from real psutil.boot_time() ±1s variance | Always mock both `psutil.boot_time` and `time.time` in tests; never call real psutil |
| DCU/LSU detection | Pending count not in registry — requirement ambiguity | Resolve with product owner before coding: presence/version vs. pending count are different |
| DCU detection | DisplayName varies across versions | Case-insensitive substring: `"dell command" in display_name.lower()` |
| LSU detection | 32-bit installer in Wow6432Node — missed on 64-bit | Check Wow6432Node path explicitly; use existing `UNINSTALL_PATHS` pattern |
| DCU/LSU not installed | "Not found" treated as error | Return `CollectionResult(value={"installed": False}, error=None)` — absence is not failure |
| JSON serialization | Path objects cause TypeError in json.dumps | Never store Path on AuditReport; add `_AuditEncoder` as safety net |
| JSON stdout | UnicodeEncodeError on cp1252 console (NinjaOne pipe) | Use `ensure_ascii=True`; never `reconfigure(encoding="utf-8")` globally |
| JSON null vs 0 | `pending_updates or "N/A"` masks genuine zero | Always use `is not None` guards for count fields; `null` in JSON for unavailable |
| --output flag | Writes to host PC if path not validated | Validate output path against PKG-02; warn or block non-flash-drive paths |
| --app + --json | Ambiguous branching: --json alone as mode selector | Treat --json as format modifier; mode determined by --app/--name/--serial/--warnings |
| argparse pytest isolation | sys.argv contamination (Phase 11 known burn) | Patch sys.argv in every test; consider conftest.py autouse fixture |
| AuditReport new fields | Required fields break all existing test constructions | All new fields: `Optional[T] = None` — run pytest after model change, before collector code |
| Jinja2 template | None renders as string "None" | `\| default("N/A")` filter on every new field; add renderer test for None values |

---

*v3.0 pitfalls section researched 2026-05-14*
*Sources: Microsoft Learn WUA SDK, psutil GitHub issues #658/#1007/#2094, PyInstaller issues #7255/#8543, Simon Willison pytest/argparse TIL, PEP 528, Dell ADMX Registry Guide, Silent Install HQ Lenovo System Update detection*
