---
phase: 07-html-warnings-section
plan: "01"
subsystem: health_checks
tags: [health-checks, warnings, rename-required, tdd]
dependency_graph:
  requires: []
  provides: [_check_rename helper, evaluate_warnings returning 3 items]
  affects: [health_checks.py, tests/test_health_checks.py]
tech_stack:
  added: []
  patterns: [private-helper pattern matching _check_disk_space, parametrize boundary tests]
key_files:
  created: []
  modified:
    - health_checks.py
    - tests/test_health_checks.py
decisions:
  - "_check_rename uses string equality 'Unknown' sentinel — device_type is always str, never None; no None-guard needed"
  - "RENAME_REQUIRED WARN detail includes raw_hostname verbatim for IT diagnostics"
  - "RENAME_REQUIRED OK has detail=None — no extra info needed when hostname is valid"
metrics:
  duration: "113s"
  completed: "2026-05-07"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 7 Plan 01: Add RENAME_REQUIRED health check Summary

One-liner: Added `_check_rename` helper and grew `evaluate_warnings()` from 2 to 3 checks, with 5 new parametrize boundary tests and the always-three guarantee.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add _check_rename helper to health_checks.py | 04e35b3 | health_checks.py |
| 2 | Update test_health_checks.py — RENAME_REQUIRED tests and always-three guarantee | 1401e1b | tests/test_health_checks.py |

## What Was Built

### health_checks.py changes

- Updated module-level docstring from "exactly two" to "exactly three"
- Updated `evaluate_warnings()` docstring from "exactly two" to "exactly three"
- Added `_check_rename(report)` as third element in `evaluate_warnings()` return list
- Added `_check_rename` private helper following exact `_check_disk_space` style:
  - `severity='WARN'` when `device_type == 'Unknown'`; detail includes raw hostname
  - `severity='OK'` for any recognized device_type; `detail=None`
  - Pure comparison, no I/O, never raises (T-07-01-03 mitigated)

### tests/test_health_checks.py changes

- Added `ParsedHostname` to models import
- Renamed `test_evaluate_warnings_always_returns_two` to `test_evaluate_warnings_always_returns_three` (assert len==3, check all 3 codes)
- Updated `test_evaluate_warnings_never_raises` to assert `len(result) == 3`
- Added `test_rename_check` parametrize block (3 cases: Unknown/WARN, Warehouse Workstation/OK, Department Laptop/OK)
- Added `test_rename_check_warn_has_detail` — WARN detail is non-None and contains raw hostname
- Added `test_rename_check_ok_has_no_detail` — OK detail is None

## Test Results

```
22 passed in 0.04s
```

All 22 tests pass (17 prior + 5 new).

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. `_check_rename` is a pure in-memory function operating on already-collected AuditReport data. T-07-01-03 (DoS via malformed AuditReport) mitigated by never-raise contract (pure string comparison, no I/O).

## Self-Check: PASSED

- health_checks.py exists and contains `def _check_rename(` — FOUND
- tests/test_health_checks.py exists and contains `def test_rename_check(` — FOUND
- Commit 04e35b3 exists — FOUND
- Commit 1401e1b exists — FOUND
- 22 tests pass, 0 failures — VERIFIED
