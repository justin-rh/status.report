---
phase: 10-mac-collectors
reviewed: 2026-05-08T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - collectors/__init__.py
  - collectors/mac/__init__.py
  - collectors/mac/apps.py
  - collectors/mac/hardware.py
  - main.py
  - tests/test_collectors_init.py
  - tests/test_mac_app_collector.py
  - tests/test_mac_hardware_collector.py
  - tests/test_mac_init.py
  - tests/test_mac_profile_collector.py
  - tests/test_main_mac.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-05-08
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the macOS collector implementation (hardware, profiles, app detection), the platform
dispatch layer, `main.py` Mac additions, and all associated tests. The implementation is
well-structured and the "never raises" contract is correctly applied throughout — with one
gap. Detection logic for all seven target applications is sound. The test suite has good
coverage of edge cases (CrowdStrike fallback, M365 sentinel, Zoom bundle name, per-app
exception isolation).

Two warnings are raised: one for an unguarded psutil call that can violate the "never raises"
contract in `collect_hardware`, and one for fragile relative-path file reads in the test suite.
Four info-level items cover redundant code and dead code patterns.

---

## Warnings

### WR-01: `psutil.virtual_memory()` call is unguarded — can violate the "never raises" contract

**File:** `collectors/mac/hardware.py:135`

**Issue:** `collect_hardware()` is documented as "never raises under any circumstances (D-01,
D-02)." The four private helpers it calls are each individually guarded with try/except, except
for the RAM line: `psutil.virtual_memory().total` is called bare with no exception handler. The
inline comment says "RAM collection never fails at standard user privilege — no try/except",
but that assumption is not guaranteed. A broken psutil installation, a mocked side_effect in a
test, or a permission edge case on a hardened machine would let an exception escape
`collect_hardware()` and break the never-raises contract.

**Fix:** Wrap the RAM line the same way disk is wrapped:
```python
def _collect_memory_and_disk(report: AuditReport) -> None:
    try:
        report.ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except Exception as exc:
        report.collection_errors.append(f"RAM collection failed: {exc}")
    try:
        disk = psutil.disk_usage("/")
        report.disk_total_gb = round(disk.total / (1024 ** 3), 1)
        report.disk_free_gb = round(disk.free / (1024 ** 3), 1)
    except Exception as exc:
        report.collection_errors.append(f"Disk usage collection failed: {exc}")
```

---

### WR-02: Relative `pathlib.Path("main.py")` reads in tests — breaks when run from non-root directory

**File:** `tests/test_main_mac.py:29` and `tests/test_main_mac.py:148`

**Issue:** Two tests read `main.py` source using `pathlib.Path("main.py").read_text(...)` with a
relative path. This resolves against the process working directory, not the test file's location.
Running pytest from any directory other than the project root (e.g., `pytest tests/` from inside
the `tests/` folder, or from a CI workspace with a different cwd) will raise `FileNotFoundError`,
causing test failures that are unrelated to the code under review.

**Fix:** Use a path relative to `__file__` so tests are location-independent:
```python
import pathlib

_PROJECT_ROOT = pathlib.Path(__file__).parent.parent

def test_subprocess_imported_in_main():
    src = (_PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
    ...

def test_main_contains_darwin_usb_root_branch():
    src = (_PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
    ...
```

---

## Info

### IN-01: Dead code — `except` clause lists `Exception` alongside more specific exceptions

**File:** `collectors/mac/apps.py:100`

**Issue:** The except tuple `(OSError, plistlib.InvalidFileException, KeyError, Exception)` ends
with the bare `Exception` superclass, which subsumes all the preceding specific types. The specific
exceptions `OSError`, `plistlib.InvalidFileException`, and `KeyError` are dead — they will never
be the matched branch because `Exception` always matches first (Python tests exception types
left-to-right, and `Exception` is the common base class). The intent to enumerate caught types
is obscured.

**Fix:** Either keep only the meaningful specific types (if you want to surface unexpected
exceptions as bugs) or keep only `Exception` (if silent catch-all is the intent, which is
consistent with D-16):
```python
# Option A: named + catch-all (documents intent, still catches everything)
except (OSError, plistlib.InvalidFileException, KeyError, Exception):
    # rename to just: except Exception:

# Option B: explicit if you want unexpected exceptions to surface:
except (OSError, plistlib.InvalidFileException, KeyError):
    return True, None
```
Given the D-16 design requirement ("Never raises"), `except Exception` alone is cleaner.

---

### IN-02: Dead code — inner function shadowed immediately by a lambda in `_make_path_stub`

**File:** `tests/test_mac_app_collector.py:36-39`

**Issue:** Inside `_make_path_stub`, a nested function `truediv` is defined on line 37 but is
never used. On line 39, the same attribute is assigned via a lambda with identical semantics.
The `truediv` function is dead code.

```python
def truediv(other):          # <-- defined here, never referenced
    return make_stub(f"{path_str}/{other}")

stub.__truediv__ = lambda self, other: make_stub(f"{path_str}/{other}")  # <-- overrides it
```

**Fix:** Delete the unused `truediv` function:
```python
stub.__truediv__ = lambda self, other: make_stub(f"{path_str}/{other}")
```

---

### IN-03: Redundant `or None` — `os.environ.get()` already returns `None` by default

**File:** `collectors/mac/hardware.py:151`

**Issue:** `os.environ.get("USER") or os.environ.get("USERNAME") or None` — the trailing
`or None` is always redundant. `os.environ.get()` with no default returns `None` when the key
is absent. If both `USER` and `USERNAME` are missing, `os.environ.get("USERNAME")` already
evaluates to `None`, so the trailing `or None` is never reached with a non-None value.

**Fix:**
```python
report.current_user = os.environ.get("USER") or os.environ.get("USERNAME")
```

---

### IN-04: TODO comment in production constant — low-confidence launchd label for NinjaOne

**File:** `collectors/mac/apps.py:45`

**Issue:** `"launchdaemon_label": "com.ninjarmm.agent",  # TODO: verify on live Mac (LOW confidence)`

A TODO marking low-confidence data lives in a production constant table. If the label is wrong,
`_query_launchd` will call `launchctl list com.ninjarmm.agent`, get a non-zero exit code, and
silently return `"Stopped"` for all NinjaOne-installed machines, making NinjaOne always appear
stopped in the report even when running. The bug would be invisible in tests because tests mock
subprocess entirely.

This is not a code defect today, but the in-code TODO means the risk is easily forgotten.
Track it in an issue or the RESEARCH.md doc and remove the TODO from the constant table once
verified.

---

_Reviewed: 2026-05-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
