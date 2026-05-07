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
