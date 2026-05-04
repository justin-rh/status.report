# Phase 2: System Collectors — Research

**Phase:** 2 — System Collectors
**Requirements:** COLL-02, COLL-03
**Researched:** 2026-05-04

---

## Phase Goal

Implement `collectors/windows/hardware.py` with `collect_hardware(report)` and `collect_profiles(report)`. Expose `collect_all(report)` from `collectors/__init__.py`. All collectors mutate `AuditReport` in place, never raise, and degrade gracefully to `None` + `collection_errors` on any failure.

---

## Library-to-Field Implementation

### psutil — RAM, Disk, Current User

```python
import psutil

# RAM — always works standard user
ram_bytes = psutil.virtual_memory().total
ram_gb = round(ram_bytes / (1024 ** 3), 1)   # float, 1 decimal

# Disk — use the C:\ root volume
disk = psutil.disk_usage('C:\\')
disk_total_gb = round(disk.total / (1024 ** 3), 1)
disk_free_gb = round(disk.free / (1024 ** 3), 1)

# Current user — os.environ is more reliable than psutil.users() in a frozen exe context
import os
current_user = os.environ.get('USERNAME') or os.environ.get('USER')
```

**Why `os.environ` over `psutil.users()`:** In a PyInstaller frozen exe, `psutil.users()` can return an empty list when no TTY session is attached (e.g., launched from Windows Explorer with no terminal). `os.environ['USERNAME']` is set by Windows for all interactive sessions.

**Disk path note:** Use `'C:\\'` as the primary disk target. If it fails (junction point, unusual Windows install), catch and log to `collection_errors`.

### wmi — CPU Model Only

```python
import wmi

c = wmi.WMI()
processors = c.Win32_Processor()
if processors:
    cpu_model = processors[0].Name.strip()  # "Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz"
```

**WMI COM initialization in PyInstaller bundles:**
- `wmi.WMI()` requires the COM apartment to be initialized. In a PyInstaller frozen exe running from a double-click (STA context), this works automatically.
- Wrap the entire WMI instantiation and query in `try/except Exception` — if the WMI service is unavailable (can happen on freshly imaged machines), COM raises `x_wmi` or a generic `Exception`.
- Do NOT call `pythoncom.CoInitialize()` explicitly — it's only needed if spawning threads, and calling it in the main thread when COM is already initialized is a no-op at best, a crash at worst.

**Standard-user accessibility:** Win32_Processor is accessible to standard users on all Windows 10/11 machines. No elevation needed.

### platform stdlib — OS Version and Build

```python
import platform

os_version = platform.release()          # "10" or "11"
os_build = platform.version()            # "10.0.19045" (Windows 10 22H2)
```

**Alternative if more detail is needed:**
```python
# platform.win32_ver() → (release, version, csd, ptype)
# release = '10', version = '10.0.19045', csd = '', ptype = 'Multiprocessor Free'
release, version, _, _ = platform.win32_ver()
```

`platform.version()` returns the full dotted version string. `platform.release()` returns just "10" or "11". Together they give the renderer what it needs to display "Windows 11 (22H2)".

### winreg — Local User Profile Enumeration

Registry path: `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList`

Each subkey is a SID. Read the `ProfileImagePath` REG_EXPAND_SZ value from each subkey.

```python
import winreg

PROFILE_LIST_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"

# System SIDs to skip
SYSTEM_SIDS = {'S-1-5-18', 'S-1-5-19', 'S-1-5-20'}

def enumerate_profiles() -> list[str]:
    profiles = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, PROFILE_LIST_KEY) as key:
            i = 0
            while True:
                try:
                    sid = winreg.EnumKey(key, i)
                    i += 1
                    # Skip system SIDs
                    if sid in SYSTEM_SIDS:
                        continue
                    # Read profile path
                    try:
                        with winreg.OpenKey(key, sid) as sid_key:
                            path, _ = winreg.QueryValueEx(sid_key, 'ProfileImagePath')
                            # Expand %SystemDrive% etc.
                            expanded = winreg.ExpandEnvironmentStrings(path)
                            username = expanded.rstrip('\\').split('\\')[-1]
                            if username:
                                profiles.append(username)
                    except (FileNotFoundError, OSError):
                        continue
                except OSError:
                    break  # No more subkeys
    except OSError:
        return []
    return profiles
```

**Key notes:**
- `ProfileImagePath` is `REG_EXPAND_SZ` — call `winreg.ExpandEnvironmentStrings()` before splitting to handle `%SystemDrive%\Users\john` patterns.
- Filter by SID prefix: S-1-5-18, S-1-5-19, S-1-5-20 are SYSTEM, LOCAL SERVICE, NETWORK SERVICE respectively.
- S-1-5-21-* SIDs are all domain/local user accounts — keep them all (including Default, DefaultAppPool, Public).
- `EnumKey` raises `OSError` (specifically `WindowsError`) when the index exceeds the count — this is the normal loop termination condition.

---

## Collector Structure

### `collectors/windows/hardware.py`

```python
"""Windows hardware and profile collectors for Phase 2."""
import os
import platform
import winreg
from models import AuditReport

def collect_hardware(report: AuditReport) -> None:
    """Populates hardware fields. Degrades to None on failure."""
    _collect_os(report)
    _collect_cpu_model(report)
    _collect_memory_and_disk(report)
    _collect_current_user(report)

def collect_profiles(report: AuditReport) -> None:
    """Populates local_profiles from HKLM ProfileList registry."""
    try:
        report.local_profiles = _enumerate_profiles()
    except Exception as e:
        report.collection_errors.append(f"Profile enumeration failed: {e}")
```

### `collectors/__init__.py`

```python
"""Collector orchestration. Selects platform implementation."""

def collect_all(report) -> None:
    from collectors.windows.hardware import collect_hardware, collect_profiles
    collect_hardware(report)
    collect_profiles(report)
```

---

## Testing Strategy

### WMI Mocking

WMI cannot be installed in CI (no COM server). Test the WMI-dependent path by mocking at the function boundary:

```python
# tests/test_hardware_collector.py
from unittest.mock import patch, MagicMock
from models import AuditReport
from parsers.name_parser import parse_hostname

def make_report():
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))

def test_collect_hardware_populates_cpu_model():
    mock_proc = MagicMock()
    mock_proc.Name = "Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz"
    mock_wmi = MagicMock()
    mock_wmi.return_value.Win32_Processor.return_value = [mock_proc]
    
    with patch("collectors.windows.hardware.wmi.WMI", mock_wmi):
        report = make_report()
        from collectors.windows.hardware import collect_hardware
        collect_hardware(report)
    
    assert report.cpu_model == "Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz"

def test_collect_hardware_degrades_when_wmi_fails():
    with patch("collectors.windows.hardware.wmi.WMI", side_effect=Exception("COM unavailable")):
        report = make_report()
        from collectors.windows.hardware import collect_hardware
        collect_hardware(report)
    
    assert report.cpu_model is None
    assert any("cpu" in e.lower() or "wmi" in e.lower() or "processor" in e.lower()
               for e in report.collection_errors)
```

### winreg Mocking

```python
def test_collect_profiles_skips_system_sids():
    # Mock: three SIDs — one system, two user
    mock_sids = ['S-1-5-18', 'S-1-5-21-111-222-333-1001', 'S-1-5-21-111-222-333-1002']
    mock_paths = {
        'S-1-5-18': r'C:\Windows\system32\config\systemprofile',
        'S-1-5-21-111-222-333-1001': r'C:\Users\john.doe',
        'S-1-5-21-111-222-333-1002': r'C:\Users\jane.smith',
    }
    # ... mock winreg.OpenKey and EnumKey appropriately
    assert 'john.doe' in report.local_profiles
    assert 'jane.smith' in report.local_profiles
    assert 'systemprofile' not in report.local_profiles
```

### psutil — No Mocking Needed in Unit Tests

`psutil.virtual_memory()`, `psutil.disk_usage()` work on all platforms (including CI Linux/Windows runners). Do not mock them for unit tests — let them run against the real machine. Only mock for isolation testing of error paths:

```python
def test_collect_hardware_degrades_on_disk_error():
    with patch("collectors.windows.hardware.psutil.disk_usage", side_effect=PermissionError):
        report = make_report()
        collect_hardware(report)
    assert report.disk_total_gb is None
    assert any("disk" in e.lower() for e in report.collection_errors)
```

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| WMI service unavailable (fresh image) | `cpu_model = None`, error logged |
| Machine has no C:\ (unusual) | `disk_total_gb = None`, error logged |
| `psutil.virtual_memory()` fails | `ram_gb = None`, error logged |
| ProfileList key empty | `local_profiles = []`, no error |
| ProfileList key inaccessible | `local_profiles = []`, error logged |
| ProfileImagePath expands to non-existent path | Include the username anyway — existence check is out of scope |
| Username contains non-ASCII chars | Use `str` directly — Python 3 strings are Unicode; winreg returns str |
| USERNAME env var not set | Fall back to `os.environ.get('USER', 'Unknown')` |

---

## Known Pitfalls for This Phase

**From global research (PITFALLS.md):**

1. **Encoding (Pitfall 5):** Profile paths from registry can contain non-ASCII on international machines. `winreg` returns Python `str` (Unicode) on Python 3, so this is safe. But `os.environ.get('USERNAME')` on Windows is always ASCII in the hostname convention. No special handling needed for Phase 2.

2. **WMI in frozen exe:** If `pythoncom` is not initialized when a thread calls `wmi.WMI()`, COM raises. The primary executable thread is safe. Do not call WMI from background threads.

3. **Disk target `C:\\`:** On some unusual configurations (Windows on D:, RAM disk at C:), this can fail. Catch `FileNotFoundError` and degrade.

---

## Validation Architecture

### Success Criteria Verification

| Success Criterion | Verification Method |
|------------------|---------------------|
| SC1: CPU, RAM, disk, OS populated without crash | Run `collect_all` on a real Windows machine; assert all 6 fields non-None |
| SC2: All local profiles enumerated | Assert `local_profiles` contains known accounts on test machine |
| SC3: WMI failure → "Unavailable" degradation | Mock WMI to raise; assert fields=None, collection_errors non-empty |
| SC4: Output path from sys.executable (not Phase 2 scope) | Deferred to packaging phase |

### Test Suite Structure

```
tests/
  test_hardware_collector.py     # Unit: WMI mock, psutil mock, platform
  test_profile_collector.py      # Unit: winreg mock, SID filtering
  test_collector_integration.py  # Integration: real psutil + platform (no WMI)
```

---

## Files to Create/Modify

| File | Action | Phase |
|------|--------|-------|
| `collectors/__init__.py` | Add `collect_all(report)` | 2 |
| `collectors/windows/__init__.py` | No changes (stub remains) | 2 |
| `collectors/windows/hardware.py` | Create — full implementation | 2 |
| `tests/test_hardware_collector.py` | Create — unit tests | 2 |
| `tests/test_profile_collector.py` | Create — unit tests | 2 |

---

## RESEARCH COMPLETE

All implementation patterns, API specifics, edge cases, and test strategies are documented above. The planner has sufficient detail to create executor-ready plans.
