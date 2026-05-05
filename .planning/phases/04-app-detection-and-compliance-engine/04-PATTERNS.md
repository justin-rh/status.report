# Phase 4: App Detection and Compliance Engine - Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 3 new/modified files
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `collectors/windows/apps.py` | collector | request-response (registry I/O) | `collectors/windows/hardware.py` | exact — same in-place mutation pattern, same winreg iteration |
| `collectors/__init__.py` | orchestrator | request-response | `collectors/__init__.py` (self — modify) | exact — add one `collect_apps(report)` call to `collect_all` |
| `tests/test_app_collector.py` | test | N/A | `tests/test_profile_collector.py` | exact — same `patch.object(mod.winreg, ...)` mock pattern |

---

## Pattern Assignments

### `collectors/windows/apps.py` (collector, registry I/O)

**Analog:** `collectors/windows/hardware.py`

**Imports pattern** (hardware.py lines 1–14):
```python
from __future__ import annotations

import winreg
from pathlib import Path

from models import AuditReport, AppStatus
```
Notes: `winreg` is stdlib, no import guard needed (unlike `_wmi_module`). `pathlib.Path` needed for MERP filesystem check. No `psutil`, no `wmi`.

**Public function signature** — mirror `collect_hardware` / `collect_profiles` (hardware.py lines 38–48, 50–59):
```python
def collect_apps(report: AuditReport) -> None:
    """Populate report.apps with one AppStatus per target application.

    Iterates APP_SPECS. Never raises across layer boundary — all exceptions
    caught per-app; errors appended to report.collection_errors (D-16).
    """
    for spec in APP_SPECS:
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
```

**Core registry enumeration loop** — copy from hardware.py `_enumerate_profiles` (lines 127–153), adapted for 4 Uninstall paths:
```python
UNINSTALL_PATHS: list[tuple[int, str]] = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
]

def _search_uninstall_keys(
    keywords: list[str],
) -> tuple[bool, str | None]:
    """Return (installed, version). First subkey whose DisplayName contains any
    keyword wins. Breaks immediately — no duplicate AppStatus entries (D-15, Pitfall 5)."""
    for hive, path in UNINSTALL_PATHS:
        try:
            with winreg.OpenKey(hive, path) as root:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root, i)
                        i += 1
                    except OSError:
                        break  # exhausted — normal loop end (mirrors hardware.py:142)
                    try:
                        with winreg.OpenKey(root, subkey_name) as subkey:
                            display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            if any(kw.lower() in display_name.lower() for kw in keywords):
                                try:
                                    version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                                except (FileNotFoundError, OSError):
                                    version = None
                                return True, version
                    except (FileNotFoundError, OSError):
                        continue  # skip unreadable subkey silently (mirrors hardware.py:152)
        except (FileNotFoundError, OSError):
            continue  # path absent on this machine
    return False, None
```
Key: `except (FileNotFoundError, OSError)` is used throughout because `FileNotFoundError` is technically a subclass of `OSError`, but hardware.py uses both explicitly for clarity — follow the same style (Pitfall 6 in RESEARCH.md).

**Service state read** (no analog exists yet — new pattern, sourced from RESEARCH.md):
```python
_START_MAP: dict[int, str] = {2: "Automatic", 3: "Manual", 4: "Disabled"}

def _read_service_start(service_name: str) -> str | None:
    key_path = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            val, _ = winreg.QueryValueEx(key, "Start")
            return _START_MAP.get(int(val))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return None
```

**MSIX detection** (no analog exists yet — new pattern, sourced from RESEARCH.md):
```python
_MSIX_REPO_PATH = (
    r"Software\Classes\Local Settings\Software\Microsoft\Windows"
    r"\CurrentVersion\AppModel\Repository\Packages"
)

def _detect_msix(family_prefix: str) -> tuple[bool, str | None]:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _MSIX_REPO_PATH) as root:
            i = 0
            while True:
                try:
                    pkg_key_name = winreg.EnumKey(root, i)
                    i += 1
                except OSError:
                    break
                if pkg_key_name.startswith(family_prefix):
                    parts = pkg_key_name.split("_")
                    version = parts[1] if len(parts) >= 2 else None
                    return True, version
    except (FileNotFoundError, OSError):
        pass
    return False, None
```

**Error handling per-app** — mirrors `collect_profiles` wrapper style (hardware.py lines 50–59):
```python
# In collect_profiles (hardware.py lines 55-59):
try:
    report.local_profiles = _enumerate_profiles()
except Exception as exc:
    report.collection_errors.append(f"Profile enumeration failed: {exc}")
```
For `apps.py`, the equivalent is a per-spec try/except inside the `for spec in APP_SPECS` loop. Each failure appends to `report.collection_errors` and appends an `AppStatus(installed=False, error=str(exc))` — ensuring D-15 (always one entry per app) is maintained even under failure.

**APP_SPECS table** (sourced from RESEARCH.md Pattern 4):
```python
APP_SPECS: list[dict] = [
    {
        "name": "NinjaOne",
        "display_name_keywords": ["NinjaRMMAgent", "NinjaRMM", "NinjaOne Agent"],
    },
    {
        "name": "CrowdStrike Falcon",
        "display_name_keywords": ["CrowdStrike Windows Sensor", "CrowdStrike Sensor Platform"],
        "service_key": "CSFalconService",
    },
    {
        "name": "MERP",
        "display_name_keywords": ["WindX", "PVX Plus Technologies"],
        "filesystem_path": r"C:/PVX Plus Technologies/WindX Plugin-64 2022 Upd 1/WindX",
    },
    {
        "name": "Microsoft 365",
        "display_name_keywords": ["Microsoft 365", "Microsoft Office"],
    },
    {
        "name": "Zoom",
        "display_name_keywords": ["Zoom Workplace", "Zoom"],
    },
    {
        "name": "Google Chrome",
        "display_name_keywords": ["Google Chrome"],
    },
    {
        "name": "Claude",
        "display_name_keywords": ["Claude"],
        "msix_family_prefix": "Claude_",
    },
]
```
Notes: CrowdStrike keywords must be `"CrowdStrike Windows Sensor"` and `"CrowdStrike Sensor Platform"` — NOT `"CrowdStrike Falcon"` which does not appear in the live registry (RESEARCH.md Pitfall 1). Claude must use `msix_family_prefix` as primary path, standard keywords as fallback (RESEARCH.md Pitfall 3). Zoom should use `"Zoom Workplace"` to avoid matching "Zoom Outlook Plugin" (RESEARCH.md Pitfall 2).

---

### `collectors/__init__.py` (orchestrator — modify existing)

**Analog:** `collectors/__init__.py` (current file, lines 1–19)

**Current file** (lines 1–19):
```python
"""Collector orchestration. Selects platform implementation.
Phase 2: Windows implementation only. Mac stubs reserved for v2.
collect_all(report) is the single entry point called by main.py (Phase 3 wiring).
"""
from __future__ import annotations
from models import AuditReport


def collect_all(report: AuditReport) -> None:
    """Run all collectors in order. Mutates report in place. Never raises.

    Calls collect_hardware first (OS, CPU, RAM, disk, current user),
    then collect_profiles (local user profiles from registry).
    Both functions degrade gracefully — collection_errors accumulates failures.
    """
    from collectors.windows.hardware import collect_hardware, collect_profiles
    collect_hardware(report)
    collect_profiles(report)
```

**Modified version** — add `collect_apps` import and call (D-12):
```python
def collect_all(report: AuditReport) -> None:
    """Run all collectors in order. Mutates report in place. Never raises.

    Calls collect_hardware first (OS, CPU, RAM, disk, current user),
    then collect_profiles (local user profiles from registry),
    then collect_apps (installed application detection).
    All functions degrade gracefully — collection_errors accumulates failures.
    """
    from collectors.windows.hardware import collect_hardware, collect_profiles
    from collectors.windows.apps import collect_apps   # Phase 4 addition
    collect_hardware(report)
    collect_profiles(report)
    collect_apps(report)   # Phase 4 addition — after profiles, per D-12
```
Pattern: lazy import inside function body (same style as existing `collect_hardware` import). Docstring updated to describe third step.

---

### `tests/test_app_collector.py` (test)

**Analog:** `tests/test_profile_collector.py`

**File header and make_report fixture** (test_profile_collector.py lines 1–16):
```python
"""Unit tests for collectors.windows.apps — collect_apps function."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))
```

**Core mock pattern** — `patch.object(mod.winreg, ...)` (test_profile_collector.py lines 88–108):
```python
import collectors.windows.apps as apps_mod

def test_detect_ninjaone_installed():
    subkeys = ["NinjaRMMAgent 5.8.9154"]

    def enum_fn(key, index):
        if index < len(subkeys):
            return subkeys[index]
        raise OSError("exhausted")

    fake_ctx = MagicMock()
    fake_ctx.__enter__ = MagicMock(return_value=fake_ctx)
    fake_ctx.__exit__ = MagicMock(return_value=False)

    def query_fn(key, value_name):
        responses = {
            "DisplayName": ("NinjaRMMAgent", 1),
            "DisplayVersion": ("13.0.7346", 1),
        }
        if value_name in responses:
            return responses[value_name]
        raise FileNotFoundError(f"no value {value_name}")

    with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=enum_fn), \
         patch.object(apps_mod.winreg, "QueryValueEx", side_effect=query_fn):
        report = make_report()
        apps_mod.collect_apps(report)

    ninja = next(a for a in report.apps if a.name == "NinjaOne")
    assert ninja.installed is True
    assert ninja.version == "13.0.7346"
    assert ninja.detection_method == "registry"
```
Key: always import the module as `apps_mod` (not `from ... import collect_apps`) so `patch.object(apps_mod.winreg, ...)` works — this patches the `winreg` reference inside `apps.py` itself, not the stdlib module globally.

**Never-raises test pattern** (test_profile_collector.py lines 314–326):
```python
def test_collect_apps_never_raises():
    """collect_apps must not propagate any exception."""
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=PermissionError("denied")):
        try:
            report = make_report()
            apps_mod.collect_apps(report)
        except Exception as exc:
            pytest.fail(f"collect_apps raised: {exc}")

    # All 7 apps still present even under total failure
    assert len(report.apps) == 7
```

**Missing app test pattern** (new — no direct analog, but mirrors the inverse of the installed test):
```python
def test_all_apps_always_present(monkeypatch):
    """D-15: every app produces one AppStatus entry even when not installed."""
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no registry")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    app_names = [a.name for a in report.apps]
    for expected in ["NinjaOne", "CrowdStrike Falcon", "MERP",
                     "Microsoft 365", "Zoom", "Google Chrome", "Claude"]:
        assert expected in app_names
```

**MERP filesystem test pattern** (new — uses `patch("collectors.windows.apps.Path")`):
```python
def test_merp_detected_via_filesystem():
    """MERP filesystem-first detection: installed=True, detection_method='filesystem'."""
    with patch("collectors.windows.apps.Path") as mock_path, \
         patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no reg")):
        mock_path.return_value.exists.return_value = True
        report = make_report()
        apps_mod.collect_apps(report)

    merp = next(a for a in report.apps if a.name == "MERP")
    assert merp.installed is True
    assert merp.detection_method == "filesystem"
```

---

## Shared Patterns

### Never-raise across layer boundary
**Source:** `collectors/windows/hardware.py` lines 38–47 (`collect_hardware`) and lines 50–59 (`collect_profiles`)
**Apply to:** `collect_apps` in `apps.py`
```python
# Pattern: top-level try/except per subsystem; specific exception handling inside
try:
    _detect_one_app(spec, report)
except Exception as exc:
    report.collection_errors.append(f"App detection failed for {spec['name']}: {exc}")
    report.apps.append(AppStatus(name=spec["name"], installed=False, error=str(exc)))
```

### winreg EnumKey exhaustion sentinel
**Source:** `collectors/windows/hardware.py` lines 138–142
**Apply to:** All registry enumeration loops in `apps.py`
```python
while True:
    try:
        sid = winreg.EnumKey(key, i)
        i += 1
    except OSError:
        break  # EnumKey raises OSError when index exhausted — normal end
```

### Silent per-subkey skip
**Source:** `collectors/windows/hardware.py` lines 145–153
**Apply to:** Inner subkey read inside UNINSTALL_PATHS loop
```python
try:
    with winreg.OpenKey(key, sid) as sid_key:
        path, _ = winreg.QueryValueEx(sid_key, "ProfileImagePath")
        # ... process
except (FileNotFoundError, OSError):
    continue  # Skip unreadable SID subkey silently
```

### patch.object(mod.winreg, ...) test mock
**Source:** `tests/test_profile_collector.py` lines 104–108
**Apply to:** All winreg-dependent tests in `test_app_collector.py`
```python
from collectors.windows import hardware as hw_mod

with patch.object(hw_mod.winreg, "OpenKey") as mock_open, \
     patch.object(hw_mod.winreg, "EnumKey") as mock_enum, \
     patch.object(hw_mod.winreg, "QueryValueEx") as mock_query, \
     patch.object(hw_mod.winreg, "ExpandEnvironmentStrings", side_effect=lambda p: p):
    ...
```
Substitute `hw_mod` with `apps_mod` for the app collector tests.

### In-place mutation, no return value
**Source:** `collectors/windows/hardware.py` lines 38–47
**Apply to:** `collect_apps` function signature
```python
def collect_apps(report: AuditReport) -> None:
    # mutates report.apps in place
    # never returns a value
    # never raises
```

---

## No Analog Found

| File / Pattern | Role | Data Flow | Reason |
|---|---|---|---|
| `_read_service_start()` helper | utility | registry I/O | No service-state reads exist yet; use RESEARCH.md Pattern 2 |
| `_detect_msix()` helper | utility | registry I/O | No MSIX detection exists yet; use RESEARCH.md Pattern 3 |
| MERP filesystem fallback | utility | file I/O | No `Path.exists()` detection pattern in any existing collector |

---

## Metadata

**Analog search scope:** `collectors/`, `tests/`, `models.py`
**Files scanned:** 8 (`hardware.py`, `collectors/__init__.py`, `collectors/windows/__init__.py`, `models.py`, `tests/test_profile_collector.py`, `tests/test_hardware_collector.py`, `tests/test_writers.py`, `tests/test_renderer.py`)
**Pattern extraction date:** 2026-05-05
