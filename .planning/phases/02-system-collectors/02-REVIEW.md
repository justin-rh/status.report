---
phase: 02-system-collectors
reviewed: 2026-05-04T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - collectors/windows/hardware.py
  - tests/test_hardware_collector.py
  - tests/test_profile_collector.py
  - collectors/__init__.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-04
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

All four files implement the COLL-02/COLL-03 specification correctly at the functional level. The no-raise contract (D-01, D-02) is upheld throughout: `collect_hardware` never propagates exceptions, `collect_profiles` catches all `Exception` from `_enumerate_profiles`, and per-SID failures are silently skipped. Key constraints are satisfied — `Win32_Product` is absent, system SIDs are filtered, `ExpandEnvironmentStrings` is called before path splitting, and `from __future__ import annotations` is the first import in every file.

One warning-level issue exists: dead/unreachable code in `test_profile_collector.py` that includes a latent `AttributeError` in a never-called function. Three info-level items cover an unused variable, a redundant expression in production code, and a missing docstring blank-line separator.

## Warnings

### WR-01: Dead code block with latent AttributeError in test_collect_profiles_excludes_system_sids

**File:** `tests/test_profile_collector.py:124-133`
**Issue:** Lines 124-133 define `sid_key_to_sid`, `query_fn`, `query_fn.call_count = 0`, and `original_query = query_fn`, but none of these are ever used — `query_side` immediately replaces `query_fn` as the mock's side effect. The dead `query_fn` references `query_fn.call_count` on line 130 before the attribute is assigned on line 132, so if `query_fn` were ever called before line 132 executed it would raise `AttributeError`. The dead code also obscures what the test actually does.

**Fix:** Delete lines 124-133 entirely. The test functions correctly with only `query_side`:

```python
# Remove these lines (124-133):
# sid_key_to_sid: dict = {}
#
# def query_fn(key, value_name):
#     return (sid_paths[user_sids[query_fn.call_count]], 1)
#
# query_fn.call_count = 0
# original_query = query_fn
#
# def query_side(key, value_name): ...  ← keep this
```

## Info

### IN-01: Unused variable call_count_open in test_collect_profiles_silently_skips_unreadable_sid

**File:** `tests/test_profile_collector.py:279`
**Issue:** `call_count_open = [0]` is assigned but never read or mutated. It is likely a leftover from an earlier iteration of the test.

**Fix:** Delete line 279.

```python
# Remove:
call_count_open = [0]
```

### IN-02: Redundant trailing `or None` in _collect_current_user

**File:** `collectors/windows/hardware.py:120`
**Issue:** `os.environ.get("USERNAME") or os.environ.get("USER") or None` — the trailing `or None` is redundant. `os.environ.get()` already returns `None` when the key is absent, and if both keys are absent the expression evaluates to `None` without the explicit suffix. No functional impact, but it reads as if there is a third fallback when there is none.

**Fix:**
```python
report.current_user = os.environ.get("USERNAME") or os.environ.get("USER")
```

### IN-03: Missing blank line after module docstring in collectors/__init__.py

**File:** `collectors/__init__.py:1-2`
**Issue:** The module docstring on line 1 is immediately followed by `from __future__ import annotations` on line 2 with no blank line separator. In `hardware.py` a blank line separates the docstring from imports (lines 4-5). The inconsistency is minor but `from __future__ import annotations` is correctly placed as the first import — this is a style-only issue.

**Fix:**
```python
"""Collector orchestration. Selects platform implementation.
Phase 2: Windows implementation only. Mac stubs reserved for v2.
collect_all(report) is the single entry point called by main.py (Phase 3 wiring).
"""
from __future__ import annotations

from models import AuditReport
```

---

## Constraint Verification

| Constraint | Status | Notes |
|------------|--------|-------|
| `Win32_Product` absent | PASS | Only `Win32_Processor` used |
| Never raises across layer boundary | PASS | Both public functions fully guarded |
| `winreg` handles PermissionError, FileNotFoundError, OSError | PASS | `PermissionError` is `OSError` subclass; caught at both layers |
| WMI failure degrades to `cpu_model=None` with error | PASS | `_collect_cpu_model` lines 90-93 |
| System SIDs S-1-5-18/19/20 filtered | PASS | `SYSTEM_SIDS` set, checked line 143 |
| `ExpandEnvironmentStrings` called before path extraction | PASS | Line 148 |
| `from __future__ import annotations` first after docstring | PASS (all files) | `__init__.py` missing blank line (IN-03) |

---

_Reviewed: 2026-05-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
