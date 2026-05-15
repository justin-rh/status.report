# Phase 10: Mac Collectors - Pattern Map

**Mapped:** 2026-05-08
**Files analyzed:** 9 (5 new, 2 modified, 2 new tests — plus profile test)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `collectors/mac/__init__.py` | config | — | `collectors/windows/__init__.py` | exact |
| `collectors/mac/hardware.py` | collector/service | request-response | `collectors/windows/hardware.py` | exact |
| `collectors/mac/apps.py` | collector/service | request-response | `collectors/windows/apps.py` | exact |
| `collectors/__init__.py` | orchestrator | request-response | `collectors/__init__.py` (self) | exact |
| `main.py` | entrypoint | request-response | `main.py` (self) | exact |
| `tests/test_mac_hardware_collector.py` | test | — | `tests/test_hardware_collector.py` | exact |
| `tests/test_mac_app_collector.py` | test | — | `tests/test_app_collector.py` | exact |
| `tests/test_mac_profile_collector.py` | test | — | `tests/test_profile_collector.py` | exact |

---

## Pattern Assignments

### `collectors/mac/__init__.py` (package marker)

**Analog:** `collectors/windows/__init__.py`

**Full content** (lines 1-1):
```python
# macOS-specific collector implementations (Phase 10)
```

---

### `collectors/mac/hardware.py` (collector, request-response)

**Analog:** `collectors/windows/hardware.py`

**Imports pattern** (lines 1-24 of analog):
```python
"""macOS hardware and profile collectors.
Implements PLAT-V2-01 (hardware stats) and PLAT-V2-02 (local user profiles).
Both functions mutate AuditReport in place and never raise (D-01, D-02).
"""
from __future__ import annotations

import json
import os
import platform
import subprocess

import psutil

from models import AuditReport

# ---------------------------------------------------------------------------
# Module-level pwd import — allows tests to patch _pwd_module without
# requiring a POSIX OS in CI (mirrors _wmi_module guard in windows/hardware.py).
# ---------------------------------------------------------------------------
try:
    import pwd as _pwd_module
    _PWD_AVAILABLE = True
except ImportError:
    _pwd_module = None  # type: ignore[assignment]
    _PWD_AVAILABLE = False
```

**CRITICAL — Module-level guard pattern** (from `collectors/windows/hardware.py` lines 19-24):
```python
try:
    import wmi as _wmi_module  # type: ignore[import-untyped]
    _WMI_AVAILABLE = True
except ImportError:
    _wmi_module = None  # type: ignore[assignment]
    _WMI_AVAILABLE = False
```
Mac equivalent: replace `wmi`/`_WMI_AVAILABLE` with `pwd`/`_PWD_AVAILABLE`. This guard is MANDATORY — `pwd` is POSIX-only and will ImportError on Windows CI. Tests patch `hw_mod._pwd_module` and `hw_mod._PWD_AVAILABLE` via `patch.object`.

**Public interface** (from analog lines 42-65):
```python
def collect_hardware(report: AuditReport) -> None:
    """Populate hardware fields on *report* in place.
    Never raises under any circumstances (D-01, D-02).
    """
    _collect_os(report)
    _collect_cpu_model(report)
    _collect_memory_and_disk(report)
    _collect_current_user(report)


def collect_profiles(report: AuditReport) -> None:
    """Populate local_profiles from pwd database (D-11).
    Filters accounts with UID < 501 (system accounts on macOS).
    Never raises; appends one error to collection_errors on failure.
    """
    try:
        report.local_profiles = _enumerate_profiles()
    except Exception as exc:
        report.collection_errors.append(f"Profile enumeration failed: {exc}")
```

The `collect_profiles` wrapper pattern (lines 55-64 of analog) is identical — catch at the public boundary, log to `collection_errors`, return empty list. Copy this exactly.

**_collect_os pattern** (analog lines 71-92 — Mac variant):
```python
def _collect_os(report: AuditReport) -> None:
    """Populate os_version and os_build from sw_vers subprocess calls (D-06)."""
    try:
        result = subprocess.run(
            ["sw_vers", "-productVersion"],
            capture_output=True, text=True, timeout=5,
        )
        version_str = result.stdout.strip()
        if version_str:
            report.os_version = f"macOS {version_str}"
    except Exception as exc:
        report.collection_errors.append(f"OS version collection failed: {exc}")
    try:
        result = subprocess.run(
            ["sw_vers", "-buildVersion"],
            capture_output=True, text=True, timeout=5,
        )
        build_str = result.stdout.strip()
        if build_str:
            report.os_build = build_str
    except Exception as exc:
        report.collection_errors.append(f"OS build collection failed: {exc}")
```

**_collect_cpu_model pattern** (analog lines 94-118 — Mac variant with two-branch arm64/x86_64):
```python
def _collect_cpu_model(report: AuditReport) -> None:
    """Populate cpu_model — Intel via sysctl, Apple Silicon via system_profiler (D-07)."""
    arch = platform.machine()  # "arm64" on Apple Silicon, "x86_64" on Intel
    if arch == "x86_64":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5,
            )
            report.cpu_model = result.stdout.strip() or None
            return
        except Exception as exc:
            report.collection_errors.append(f"CPU model (sysctl) failed: {exc}")
    # Apple Silicon (arm64) — or Intel sysctl fallback:
    # system_profiler SPHardwareDataType -json key is "chip_type" on Apple Silicon,
    # "cpu_type" on Intel. Use fallback chain to handle both (RESEARCH A1).
    try:
        result = subprocess.run(
            ["system_profiler", "SPHardwareDataType", "-json"],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(result.stdout)
        hw = data["SPHardwareDataType"][0]
        report.cpu_model = hw.get("chip_type") or hw.get("cpu_type") or None
    except Exception as exc:
        report.collection_errors.append(f"CPU model (system_profiler) failed: {exc}")
```

**_collect_memory_and_disk pattern** (analog lines 152-167 — Mac uses "/" not "C:\\"):
```python
def _collect_memory_and_disk(report: AuditReport) -> None:
    """Populate ram_gb, disk_total_gb, disk_free_gb via psutil (D-08, D-09)."""
    # RAM — always works at standard user privilege
    report.ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    # Disk — target "/" root partition on macOS
    try:
        disk = psutil.disk_usage("/")
        report.disk_total_gb = round(disk.total / (1024 ** 3), 1)
        report.disk_free_gb = round(disk.free / (1024 ** 3), 1)
    except Exception as exc:
        report.collection_errors.append(f"Disk usage collection failed: {exc}")
```

**_collect_current_user pattern** (analog lines 170-176):
```python
def _collect_current_user(report: AuditReport) -> None:
    """Populate current_user from macOS session env vars (D-10).
    os.environ.get() never raises. Mac uses USER (not USERNAME).
    """
    report.current_user = os.environ.get("USER") or os.environ.get("USERNAME") or None
```

**_enumerate_profiles pattern** (analog lines 183-210 — Mac pwd variant):
```python
def _enumerate_profiles() -> list[str]:
    """Return list of human account usernames (UID >= 501) from pwd database (D-11).

    Raises if _pwd_module is None (CI guard) or if pwd.getpwall() raises.
    The caller (collect_profiles) catches this and logs to collection_errors.
    """
    if not _PWD_AVAILABLE or _pwd_module is None:
        raise RuntimeError("pwd module not available on this platform")
    profiles: list[str] = []
    for entry in _pwd_module.getpwall():
        if entry.pw_uid >= 501:
            profiles.append(entry.pw_name)
    return profiles
```

**Error handling convention** (from all analog private helpers): Each subprocess call is individually wrapped in `try/except Exception`. On failure, append `f"<subsystem> collection failed: {exc}"` to `report.collection_errors`. Never reraise. Field stays `None` if not populated — caller degrades gracefully.

---

### `collectors/mac/apps.py` (collector, request-response)

**Analog:** `collectors/windows/apps.py`

**Imports pattern** (analog lines 1-19):
```python
"""macOS application detection collector.
Detects 7 target applications via .app bundle existence in /Applications/,
Info.plist version parsing, LaunchDaemon plist fallback, and launchctl service state.

All detection runs per-app. Never raises across the layer boundary — each app's
exceptions are caught individually and appended to report.collection_errors (D-16).
"""
from __future__ import annotations

import json
import plistlib
import subprocess
from pathlib import Path

from models import AuditReport, AppStatus
```

Note: `plistlib` is imported at module level (not try/except — it is pure stdlib available everywhere). This enables tests to patch `collectors.mac.apps.plistlib` directly.

**MAC_APP_SPECS table** (analog to `APP_SPECS` lines 67-127):
```python
APPLICATIONS_DIR = Path("/Applications")
LAUNCH_DAEMONS_DIR = Path("/Library/LaunchDaemons")

MAC_APP_SPECS: list[dict] = [
    {
        "name": "NinjaOne",
        "app_dir": "NinjaRMMAgent",          # Directory check — NOT .app bundle (Pitfall 5)
        "launchdaemon_label": "com.ninjarmm.agent",  # TODO: verify on live Mac (LOW confidence)
    },
    {
        "name": "CrowdStrike Falcon",
        "app_bundle": "Falcon.app",
        "launchdaemon_plist": "com.crowdstrike.falcond.plist",
        "launchdaemon_label": "com.crowdstrike.falcond",
    },
    {
        "name": "Microsoft 365",
        "app_bundle": "Microsoft Word.app",  # Primary sentinel — no monolithic bundle on Mac
        "fallback_bundles": [
            "Microsoft Excel.app",
            "Microsoft PowerPoint.app",
            "Microsoft Outlook.app",
        ],
    },
    {
        "name": "Zoom",
        "app_bundle": "zoom.us.app",         # NOT "Zoom.app" — see Pitfall 3
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

**_detect_bundle private helper** (new — no Windows analog; from RESEARCH Pattern 3):
```python
def _detect_bundle(app_bundle: str) -> tuple[bool, str | None]:
    """Return (installed, version) for an /Applications/ .app bundle.

    Opens Info.plist in binary mode — plistlib.load() requires 'rb' (Pitfall 2).
    Returns (True, None) if bundle exists but version is unreadable.
    Returns (False, None) if bundle does not exist.
    """
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
```

**_query_launchd private helper** (analog to `_read_service_start` lines 177-191):
```python
def _query_launchd(label: str) -> str:
    """Return 'Running' if launchctl reports the daemon loaded, else 'Stopped'.

    Exit code 0 = daemon found in launchd registry (may or may not have active PID).
    This is best-effort — standard user cannot reliably query system daemons on
    macOS Monterey+ without sudo. See RESEARCH.md Pitfall 6.
    """
    try:
        result = subprocess.run(
            ["launchctl", "list", label],
            capture_output=True, text=True, timeout=5,
        )
        return "Running" if result.returncode == 0 else "Stopped"
    except (OSError, subprocess.TimeoutExpired):
        return "Stopped"
```

**_detect_one_app pattern** (analog lines 395-463):
```python
def _detect_one_app(spec: dict, report: AuditReport) -> None:
    """Run detection for a single app spec and append one AppStatus to report.apps.

    Detection precedence:
    1. Directory check if app_dir present (NinjaOne — no .app bundle)
    2. Bundle check (app_bundle) with fallback_bundles for Microsoft 365
    3. LaunchDaemon plist fallback for CrowdStrike if bundle absent (D-15)
    4. Service state via launchctl if launchdaemon_label present (D-17)
    Never raises — caller (collect_apps) wraps in try/except.
    """
    installed = False
    version: str | None = None
    service_state: str | None = None
    detection_method = "filesystem"  # Mac detection is always filesystem-based

    # Step 1: Directory check (NinjaOne special case)
    if "app_dir" in spec:
        app_dir_path = APPLICATIONS_DIR / spec["app_dir"]
        if app_dir_path.is_dir():
            installed = True
            version = None  # No Info.plist in NinjaRMMAgent directory

    # Step 2: Bundle check (standard .app bundles)
    if not installed and "app_bundle" in spec:
        installed, version = _detect_bundle(spec["app_bundle"])
        # Microsoft 365: try fallback bundles if primary sentinel missing
        if not installed and "fallback_bundles" in spec:
            for fb in spec["fallback_bundles"]:
                fb_installed, fb_version = _detect_bundle(fb)
                if fb_installed:
                    installed = True
                    version = fb_version
                    break

    # Step 3: LaunchDaemon plist fallback (CrowdStrike — D-15)
    if not installed and "launchdaemon_plist" in spec:
        plist_path = LAUNCH_DAEMONS_DIR / spec["launchdaemon_plist"]
        if plist_path.exists():
            installed = True
            version = None  # Plist existence only — no version available here

    # Step 4: Service state via launchctl (CrowdStrike + NinjaOne — D-17)
    if installed and "launchdaemon_label" in spec:
        service_state = _query_launchd(spec["launchdaemon_label"])

    report.apps.append(AppStatus(
        name=spec["name"],
        installed=installed,
        version=version,
        service_state=service_state,
        detection_method=detection_method,
    ))
```

**detect_apps / collect_apps public interface** (analog lines 470-499):
```python
def detect_apps(report: AuditReport) -> None:
    """Populate report.apps with one AppStatus per target application.

    Iterates MAC_APP_SPECS. Each app's detection is wrapped in its own try/except
    so a failure in one app never blocks detection of subsequent apps (D-16).
    On exception: appends error to collection_errors AND appends
    AppStatus(installed=False, error=...) to preserve always-append rule (D-16).
    """
    for spec in MAC_APP_SPECS:
        try:
            _detect_one_app(spec, report)
        except Exception as exc:
            report.collection_errors.append(
                f"App detection failed for {spec['name']}: {exc}"
            )
            report.apps.append(AppStatus(
                name=spec["name"],
                installed=False,
                error=str(exc),
            ))


def collect_apps(report: AuditReport) -> None:
    """Public entry point for app detection. Calls detect_apps(report).
    Never raises.
    """
    detect_apps(report)
```

---

### `collectors/__init__.py` (orchestrator, request-response) — MODIFY

**Analog:** current `collectors/__init__.py` (all 22 lines)

**Current content** (lines 1-22):
```python
"""Collector orchestration. Selects platform implementation.
Phase 2: Windows implementation only. Mac stubs reserved for v2.
collect_all(report) is the single entry point called by main.py (Phase 3 wiring).
"""
from __future__ import annotations
from models import AuditReport


def collect_all(report: AuditReport) -> None:
    """Run all collectors in order. Mutates report in place. Never raises.
    ...
    """
    from collectors.windows.hardware import collect_hardware, collect_profiles
    from collectors.windows.apps import collect_apps
    collect_hardware(report)
    collect_profiles(report)
    collect_apps(report)
```

**Modified version — add darwin branch** (D-05, lazy-import pattern preserved):
```python
def collect_all(report: AuditReport) -> None:
    """Run all collectors in order. Mutates report in place. Never raises.

    Platform dispatch: darwin → collectors.mac; anything else → collectors.windows.
    Imports are lazy inside the function body so this module is importable on
    non-native platforms (e.g. mac module importable on Windows CI).
    """
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

The module docstring should be updated to remove "Mac stubs reserved for v2" and reflect Phase 10 completion.

---

### `main.py` (entrypoint, request-response) — MODIFY

**Analog:** current `main.py` (all 102 lines)

**Output path section to modify** (current lines 56-58):
```python
# Current (Windows-only):
usb_root = Path(sys.executable).parent
```

**Replacement — inline two-branch split** (D-02):
```python
# Platform-aware output root (D-02):
# - darwin: Path(__file__).parent because tool runs as "python3 main.py" (not frozen)
# - other:  Path(sys.executable).parent because tool runs as frozen exe (CLAUDE.md)
import sys as _sys_check  # sys already imported at top — use existing import
if sys.platform == "darwin":
    usb_root = Path(__file__).parent
else:
    usb_root = Path(sys.executable).parent
```

Note: `sys` is already imported at line 20 of `main.py`. No new import needed for the path split.

**Auto-open section to modify** (current lines 93-98):
```python
# Current:
if sys.stdin.isatty():
    try:
        os.startfile(str(output_path))
    except OSError:
        pass
    input("\nPress Enter to close this window, then eject the USB drive.")
```

**Replacement — platform-aware open** (D-03):
```python
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

`subprocess` must be imported at the top of `main.py`. Check line 1-25 of main.py — it is NOT currently imported. Add `import subprocess` to the stdlib import block (between `import socket` and `import sys`). The `from __future__ import annotations` and then imports at lines 14-19 are the target block.

---

### `tests/test_mac_hardware_collector.py` (test)

**Analog:** `tests/test_hardware_collector.py`

**File header and make_report** (analog lines 1-18):
```python
"""Unit tests for collectors.mac.hardware — collect_hardware and collect_profiles.
All Mac-specific calls are patched at the module level; no real Mac subprocess calls occur.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname

import collectors.mac.hardware as hw_mod


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-MAC", parsed_hostname=parse_hostname("TEST-MAC"))
```

**Module import guard test** (analog line 25-28):
```python
def test_module_imports_without_real_pwd():
    """collectors.mac.hardware must import even if pwd is unavailable (CI guard)."""
    from collectors.mac import hardware  # noqa: F401
```

**WMI-style patching → pwd patching** (analog lines 77-83):
```python
# Analog pattern for wmi:
with patch.object(hw_mod, "_wmi_module", create=True) as mock_mod:
    mock_mod.WMI = mock_wmi_cls
    with patch.object(hw_mod, "_WMI_AVAILABLE", True):

# Mac equivalent for pwd:
fake_entries = [
    MagicMock(pw_name="alice", pw_uid=501),
    MagicMock(pw_name="bob", pw_uid=502),
    MagicMock(pw_name="_daemon", pw_uid=1),
]
with patch.object(hw_mod, "_pwd_module") as mock_pwd, \
     patch.object(hw_mod, "_PWD_AVAILABLE", True):
    mock_pwd.getpwall.return_value = fake_entries
```

**subprocess patching for hw calls** (from RESEARCH.md test strategy):
```python
with patch.object(hw_mod, "subprocess") as mock_sub:
    mock_sub.run.return_value = MagicMock(stdout="14.4.1\n", returncode=0)
    mock_sub.TimeoutExpired = __import__("subprocess").TimeoutExpired
```

**MANDATORY: Intel vs Apple Silicon parametrize** (from RESEARCH.md / CONTEXT.md STATE.md note):
```python
INTEL_SYSCTL_OUTPUT = "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz\n"
APPLE_SILICON_SP_JSON = json.dumps({
    "SPHardwareDataType": [{"chip_type": "Apple M3 Pro", "_name": "hardware_overview"}]
})

@pytest.mark.parametrize("machine,sysctl_out,sp_json,expected_cpu", [
    ("x86_64", INTEL_SYSCTL_OUTPUT, "", "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz"),
    ("arm64", "", APPLE_SILICON_SP_JSON, "Apple M3 Pro"),
])
def test_cpu_model_collection(machine, sysctl_out, sp_json, expected_cpu):
    ...
```

**No-raise guarantee test** (analog lines 215-232):
```python
def test_collect_hardware_never_raises():
    """collect_hardware must not propagate any exception under any circumstances."""
    with patch.object(hw_mod, "subprocess") as mock_sub, \
         patch.object(hw_mod, "psutil") as mock_psutil, \
         patch.object(hw_mod, "platform") as mock_platform:
        mock_sub.run.side_effect = RuntimeError("subprocess exploded")
        mock_psutil.virtual_memory.return_value.total = 8 * (1024 ** 3)
        mock_psutil.disk_usage.side_effect = Exception("disk gone")
        mock_platform.machine.return_value = "arm64"
        try:
            report = make_report()
            hw_mod.collect_hardware(report)
        except Exception as exc:
            pytest.fail(f"collect_hardware raised an exception: {exc}")
```

---

### `tests/test_mac_app_collector.py` (test)

**Analog:** `tests/test_app_collector.py`

**File header and make_report** (analog lines 1-23):
```python
"""Unit tests for collectors.mac.apps — collect_apps / detect_apps functions.

Mock pattern: patch.object(apps_mod.Path, ...) patches the Path reference inside
apps.py itself. patch("collectors.mac.apps.plistlib") patches plistlib module-level
reference — same pattern as apps_mod.winreg in Windows tests.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import plistlib

from models import AuditReport
from parsers.name_parser import parse_hostname
import collectors.mac.apps as apps_mod


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-MAC", parsed_hostname=parse_hostname("TEST-MAC"))
```

**plistlib patching pattern** (from RESEARCH.md test strategy):
```python
# Patch plistlib at the module level in apps.py (not globally):
with patch("collectors.mac.apps.plistlib") as mock_plib:
    mock_plib.load.return_value = {"CFBundleShortVersionString": "4.60.0"}
    mock_plib.InvalidFileException = plistlib.InvalidFileException
```

**Path patching pattern** (analog lines 83-91):
```python
# Analog (Windows):
with patch("collectors.windows.apps.Path") as mock_path:
    mock_path.return_value.exists.return_value = False

# Mac equivalent:
with patch("collectors.mac.apps.Path") as mock_path:
    mock_path.return_value.exists.return_value = False
    mock_path.return_value.is_dir.return_value = False
```

**All-apps-always-present test** (analog lines 283-305 — 7 apps on Mac, not 9):
```python
def test_all_apps_always_present():
    """D-16: every app produces one AppStatus entry even when nothing is installed."""
    with patch("collectors.mac.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.is_dir.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    app_names = [a.name for a in report.apps]
    expected_names = [
        "NinjaOne",
        "CrowdStrike Falcon",
        "Microsoft 365",
        "Zoom",
        "Google Chrome",
        "Claude",
        "Company Portal",
    ]
    assert len(report.apps) == 7
    for expected in expected_names:
        assert expected in app_names
```

**subprocess patching for launchctl** (analog pattern — patch at module level in apps.py):
```python
with patch.object(apps_mod, "subprocess") as mock_sub:
    mock_sub.run.return_value = MagicMock(returncode=0)
    mock_sub.TimeoutExpired = __import__("subprocess").TimeoutExpired
```

---

### `tests/test_mac_profile_collector.py` (test)

**Analog:** `tests/test_profile_collector.py`

**File header** (analog lines 1-16):
```python
"""Unit tests for collectors.mac.hardware — collect_profiles function.
pwd.getpwall() is patched at module level so no real POSIX calls occur.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname
import collectors.mac.hardware as hw_mod


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-MAC", parsed_hostname=parse_hostname("TEST-MAC"))
```

**Core patching pattern** (replaces winreg-based mock from analog):
```python
# Instead of patching hw_mod.winreg.OpenKey / EnumKey / QueryValueEx,
# Mac profile tests patch hw_mod._pwd_module.getpwall:

fake_entries = [
    MagicMock(pw_name="alice", pw_uid=501),
    MagicMock(pw_name="bob", pw_uid=502),
    MagicMock(pw_name="_daemon", pw_uid=1),
    MagicMock(pw_name="root", pw_uid=0),
]
with patch.object(hw_mod, "_pwd_module") as mock_pwd, \
     patch.object(hw_mod, "_PWD_AVAILABLE", True):
    mock_pwd.getpwall.return_value = fake_entries
    report = make_report()
    hw_mod.collect_profiles(report)
```

**UID threshold test** (Mac-specific — no Windows analog):
```python
def test_collect_profiles_excludes_system_accounts():
    """Accounts with UID < 501 are excluded (macOS system account threshold)."""
    # alice (501) and bob (502) included; _daemon (1) and root (0) excluded
```

**Never-raises test** (analog lines 314-326):
```python
def test_collect_profiles_never_raises():
    """collect_profiles must not propagate any exception."""
    with patch.object(hw_mod, "_pwd_module") as mock_pwd, \
         patch.object(hw_mod, "_PWD_AVAILABLE", True):
        mock_pwd.getpwall.side_effect = RuntimeError("Open Directory failure")
        try:
            report = make_report()
            hw_mod.collect_profiles(report)
        except Exception as exc:
            pytest.fail(f"collect_profiles raised: {exc}")
    assert report.local_profiles == []
    assert len(report.collection_errors) >= 1
```

**Platform unavailable test** (Mac-specific — no Windows analog):
```python
def test_collect_profiles_degrades_when_pwd_unavailable():
    """When _PWD_AVAILABLE is False (Windows CI), local_profiles=[] and error is logged."""
    with patch.object(hw_mod, "_PWD_AVAILABLE", False):
        report = make_report()
        hw_mod.collect_profiles(report)
    assert report.local_profiles == []
    assert len(report.collection_errors) >= 1
```

---

## Shared Patterns

### Never-Raise Rule (applies to all collector functions)
**Source:** `collectors/windows/hardware.py` lines 42-52, 55-64
**Apply to:** `collect_hardware`, `collect_profiles`, `collect_apps` in all Mac files

Pattern: Public functions catch all exceptions at the boundary. Private helpers catch per-subsystem and append to `report.collection_errors`. Fields stay `None`/`[]` on failure. Callers never see exceptions.

### In-Place Mutation Interface
**Source:** `collectors/windows/hardware.py` lines 42, 55; `collectors/windows/apps.py` lines 470, 493
**Apply to:** All Mac collector public functions

```python
def collect_hardware(report: AuditReport) -> None:  # mutates in place, never raises
def collect_profiles(report: AuditReport) -> None:  # mutates in place, never raises
def collect_apps(report: AuditReport) -> None:      # mutates in place, never raises
```

No return value. No exceptions propagated. Always `-> None`.

### collection_errors Append Convention
**Source:** `collectors/windows/hardware.py` lines 109-111, 147-149, 167
**Apply to:** Every `except` block in Mac collectors

```python
except Exception as exc:
    report.collection_errors.append(f"<subsystem description> failed: {exc}")
```

Always use `f"<verb phrase>: {exc}"` format. One error per subsystem per run.

### Always-Append AppStatus Rule (D-16)
**Source:** `collectors/windows/apps.py` lines 479-490
**Apply to:** `detect_apps` in `collectors/mac/apps.py`

```python
except Exception as exc:
    report.collection_errors.append(
        f"App detection failed for {spec['name']}: {exc}"
    )
    report.apps.append(AppStatus(
        name=spec["name"],
        installed=False,
        error=str(exc),
    ))
```

Even on total failure, one `AppStatus` per app is always appended.

### Module-Level Import Guard (try/except ImportError)
**Source:** `collectors/windows/hardware.py` lines 19-24
**Apply to:** `pwd` import in `collectors/mac/hardware.py`

```python
try:
    import <platform_module> as _<module>_module
    _<MODULE>_AVAILABLE = True
except ImportError:
    _<module>_module = None  # type: ignore[assignment]
    _<MODULE>_AVAILABLE = False
```

This pattern is the ONLY safe way to import POSIX-only (`pwd`) or Windows-only (`wmi`, `winreg`) modules in a cross-platform codebase that runs tests on both platforms.

### Test patch.object on module-level references
**Source:** `tests/test_hardware_collector.py` lines 77-79, `tests/test_app_collector.py` lines 63-66
**Apply to:** All Mac test files

```python
# Always patch at the module reference, not the stdlib globally:
with patch.object(hw_mod, "_pwd_module") as mock_pwd:   # not: patch("pwd")
with patch("collectors.mac.apps.plistlib") as mock_plib: # not: patch("plistlib")
with patch("collectors.mac.apps.Path") as mock_path:     # not: patch("pathlib.Path")
```

### make_report() helper
**Source:** `tests/test_hardware_collector.py` lines 16-17, `tests/test_app_collector.py` lines 22-23
**Apply to:** All Mac test files

```python
def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-MAC", parsed_hostname=parse_hostname("TEST-MAC"))
```

Every test file defines this helper at top level. Use `"TEST-MAC"` as the hostname for Mac test files (vs `"TEST-PC"` in Windows tests).

---

## No Analog Found

All files in this phase have close Windows analogs. No files lack a pattern reference.

| File | Unique Mac-specific concern | Pattern source |
|------|-----------------------------|----------------|
| `collectors/mac/__init__.py` | Empty package marker | `collectors/windows/__init__.py` (1 line comment) |
| NinjaOne `is_dir()` check | No `.app` bundle — directory detection | RESEARCH.md §NinjaOne Special Case |
| Microsoft 365 `fallback_bundles` | No monolithic bundle — sentinel + fallbacks | RESEARCH.md §Microsoft 365 on Mac |
| `platform.machine()` branch | Apple Silicon vs Intel CPU detection | RESEARCH.md Pattern 4 |

---

## Metadata

**Analog search scope:** `collectors/windows/`, `tests/`, `main.py`, `models.py`
**Files scanned:** 8 source files, 3 test files
**Pattern extraction date:** 2026-05-08

**Critical pitfalls to copy into plan actions:**
1. `pwd` import guard — MANDATORY or Windows CI breaks at collection time (not test time)
2. `plistlib.load()` must open file in `"rb"` mode — text mode raises `TypeError`
3. Zoom bundle name is `zoom.us.app` NOT `Zoom.app`
4. NinjaOne is a directory check (`is_dir()`) NOT a `.app` bundle check
5. `subprocess` must be added to `main.py` imports (not currently present)
6. All 7 Mac apps (not 9 — no Zscaler, no MERP on Mac) must produce one AppStatus
