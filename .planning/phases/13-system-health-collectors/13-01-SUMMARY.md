---
phase: 13-system-health-collectors
plan: 01
subsystem: collectors
tags: [python, psutil, pywin32, win32com, wua, dataclass, tdd]

# Dependency graph
requires:
  - phase: 12-scry-rename
    provides: models.py, collectors/windows/hardware.py, collectors/mac/hardware.py, collectors/__init__.py

provides:
  - Warning.level field (str | None) as last field of Warning dataclass
  - AuditReport.uptime_seconds and AuditReport.pending_updates scalar fields
  - _collect_uptime() in both Windows and Mac hardware collectors using psutil.boot_time()
  - collect_pending_updates() in Windows hardware collector with _WIN32COM_AVAILABLE guard
  - collect_all() wired to call collect_pending_updates on Windows path only
  - pywin32==311 pinned in requirements.txt
  - win32timezone hidden import in scry.spec

affects:
  - 13-02 (health checks — uses Warning.level and AuditReport.uptime_seconds/pending_updates)
  - 13-03 (renderer — uses Warning.level for color, AuditReport.uptime_seconds/pending_updates for display)

# Tech tracking
tech-stack:
  added:
    - pywin32==311 (WUA COM access via win32com.client)
  patterns:
    - _WIN32COM_AVAILABLE guard mirrors _WMI_AVAILABLE exactly (try/except ImportError, None fallback)
    - collect_pending_updates() degrades gracefully: returns immediately if guard False, catches all exceptions
    - _collect_uptime() private helper: wraps psutil.boot_time() in try/except, never raises

key-files:
  created:
    - tests/test_models_phase13.py
    - tests/test_collectors_phase13.py
  modified:
    - models.py
    - collectors/windows/hardware.py
    - collectors/mac/hardware.py
    - collectors/__init__.py
    - requirements.txt
    - scry.spec

key-decisions:
  - "Warning.level added as LAST field after detail — ensures positional Warning(code, severity, message, detail_value) construction remains backward-compatible"
  - "_WIN32COM_AVAILABLE guard placed immediately after _WMI_AVAILABLE block in windows/hardware.py — consistent guard pattern for CI compatibility"
  - "collect_pending_updates returns immediately (not silently) when _WIN32COM_AVAILABLE is False — standard user interactive runs get pending_updates=None, SYSTEM runs get integer count"
  - "collect_all() split into explicit darwin/else branches — removes shared call list, enables Windows-only wiring cleanly"
  - "uptime_seconds and pending_updates placed after current_user in AuditReport — logically grouped with hardware/system fields before local_profiles list"

patterns-established:
  - "_WIN32COM_AVAILABLE: bool module-level flag + _win32com_client guard in collectors/windows/hardware.py mirrors _WMI_AVAILABLE pattern exactly"
  - "Phase 13 TDD: RED commit (test) → GREEN commit (feat) per task, both tasks follow same cycle"

requirements-completed: [HEALTH-01, HEALTH-02]

# Metrics
duration: 24min
completed: 2026-05-18
---

# Phase 13 Plan 01: System Health Collectors — Data Contract and Collection Layer Summary

**Warning.level field, AuditReport.uptime_seconds/pending_updates fields, psutil uptime collectors for Windows and Mac, and WUA COM pending-updates collector with _WIN32COM_AVAILABLE guard**

## Performance

- **Duration:** 24 min
- **Started:** 2026-05-18T18:23:05Z
- **Completed:** 2026-05-18T18:47:02Z
- **Tasks:** 2 (both TDD — 4 commits total)
- **Files modified:** 7 (2 source, 3 collectors, 1 requirements, 1 spec) + 2 test files created

## Accomplishments

- Extended Warning dataclass with `level: str | None = None` as last field — backward-compatible with all 203 existing tests that construct Warning positionally
- Extended AuditReport with `uptime_seconds: int | None = None` and `pending_updates: int | None = None` fields immediately after `current_user`
- Added `_collect_uptime()` to both Windows and Mac hardware collectors using `psutil.boot_time()` wrapped in try/except; called as final step in `collect_hardware()` in both modules
- Added `_WIN32COM_AVAILABLE` guard to `collectors/windows/hardware.py` immediately after `_WMI_AVAILABLE` block; `collect_pending_updates()` public function queries WUA COM via `Microsoft.Update.Session` and degrades gracefully to `None` on any exception
- Wired `collect_all()` to call `collect_pending_updates(report)` on Windows path only — Mac path unchanged; split-branch structure makes platform-specific wiring explicit and clean
- Added `pywin32==311` to `requirements.txt` and `'win32timezone'` to `scry.spec` hiddenimports

## Task Commits

Each task was committed atomically using TDD RED/GREEN cycle:

1. **Task 1 RED: Warning.level and AuditReport health fields (failing tests)** - `278ba50` (test)
2. **Task 1 GREEN: Extend Warning and AuditReport dataclasses** - `352e26f` (feat)
3. **Task 2 RED: Phase 13 collector additions (failing tests)** - `1b30816` (test)
4. **Task 2 GREEN: Add uptime/WUA collectors; wire collect_all; update infrastructure** - `8e699ba` (feat)

## TDD Gate Compliance

Both tasks followed full RED/GREEN cycle:
- Task 1: `test(13-01)` commit `278ba50` (RED) → `feat(13-01)` commit `352e26f` (GREEN)
- Task 2: `test(13-01)` commit `1b30816` (RED) → `feat(13-01)` commit `8e699ba` (GREEN)

No REFACTOR phase needed — implementation was clean on first pass.

## Files Created/Modified

- `models.py` — Warning.level field added (last field); AuditReport.uptime_seconds and pending_updates fields added after current_user; module docstring updated
- `collectors/windows/hardware.py` — import time added; _WIN32COM_AVAILABLE guard added; _collect_uptime() private helper added; collect_pending_updates() public function added; collect_hardware() updated to call _collect_uptime() as final step
- `collectors/mac/hardware.py` — import time added; _collect_uptime() private helper added; collect_hardware() updated to call _collect_uptime() as final step
- `collectors/__init__.py` — collect_all() refactored to explicit darwin/else branches; Windows branch imports and calls collect_pending_updates
- `requirements.txt` — pywin32==311 added
- `scry.spec` — win32timezone added to hiddenimports list
- `tests/test_models_phase13.py` — 11 tests for Warning.level and AuditReport health fields (created)
- `tests/test_collectors_phase13.py` — 15 tests for uptime/WUA collectors and collect_all wiring (created)

## Decisions Made

- Warning.level placed as LAST field after `detail` — this is critical for backward compatibility. Existing tests use positional `Warning(code, severity, message, detail_value)` construction. If `level` were placed before `detail`, `detail_value` would silently be assigned to `level`. The test `test_warning_positional_construction_not_broken` guards this invariant.
- collect_all() refactored from shared call list to explicit split branches — the previous shared `collect_hardware(report); collect_profiles(report); collect_apps(report)` block could not accommodate Windows-only calls cleanly. Split branches make platform-specific wiring explicit.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all acceptance criteria met on first implementation pass. No test failures in GREEN phase.

## User Setup Required

None — no external service configuration required. pywin32 is a pip dependency already in requirements.txt.

## Known Stubs

None — all new fields (`uptime_seconds`, `pending_updates`, `Warning.level`) are populated by collectors or left as `None` (not hardcoded placeholders). The `None` default is intentional per D-04/D-09/D-10 — represents "collection not yet run" or "inaccessible at current privilege level".

## Next Phase Readiness

- Phase 13 Plan 02 (health checks) can now import `Warning.level`, `AuditReport.uptime_seconds`, and `AuditReport.pending_updates` — all fields verified present with correct defaults
- `_collect_uptime()` populates `report.uptime_seconds` before `evaluate_warnings()` is called (main.py line 126: `report.warnings = evaluate_warnings(report)`)
- `collect_pending_updates()` is wired on the Windows path — `report.pending_updates` is populated before `evaluate_warnings()` on live Windows runs; stays None on CI
- No blockers for Plan 02

---
*Phase: 13-system-health-collectors*
*Completed: 2026-05-18*
