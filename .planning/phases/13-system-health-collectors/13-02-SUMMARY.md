---
phase: 13-system-health-collectors
plan: 02
subsystem: health-checks
tags: [python, health-checks, tdd, uptime, warning]

# Dependency graph
requires:
  - phase: 13-01
    provides: Warning.level field, AuditReport.uptime_seconds field

provides:
  - UPTIME_WARN_DAYS = 7 and UPTIME_STALE_DAYS = 30 module-level constants
  - _check_uptime() private helper with OK->yellow->red escalation
  - evaluate_warnings() returning 4 objects (was 3)
  - test_evaluate_warnings_always_returns_four (renamed from _three)
  - test_uptime_check parametrized over 8 boundary cases
  - test_uptime_stale_detail_mentions_hibernation

affects:
  - 13-03 (renderer — uses Warning.level='yellow'/'red' for uptime color display)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - _check_uptime stale check (> 30d) evaluated before warn check (> 7d) — stricter condition must come first (D-11)
    - uptime_seconds // 86400 floor division — 7d+1s still counts as day 7 (no partial-day escalation)

key-files:
  created: []
  modified:
    - health_checks.py
    - tests/test_health_checks.py

key-decisions:
  - "Stale check evaluated before warn check in _check_uptime — if both > 7d and > 30d conditions are true, stale wins; order enforces escalation per D-11"
  - "Floor division (// 86400) used for day calculation — partial-day seconds do not cross threshold; 7d+1s stays at day 7 and remains OK"
  - "test_uptime_check parametrize case 7d+1s corrected to expect UPTIME/OK — plan action had wrong expected code for this value with floor division; Rule 1 auto-fix applied"

# Metrics
duration: 6min
completed: 2026-05-18
---

# Phase 13 Plan 02: Uptime Health Check Logic and Test Contract Update Summary

**_check_uptime() with OK->yellow->red escalation, UPTIME_WARN_DAYS/UPTIME_STALE_DAYS constants, evaluate_warnings() extended to 4 objects, and 9 new uptime boundary tests**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-18T18:51:32Z
- **Completed:** 2026-05-18T18:56:52Z
- **Tasks:** 2 (both TDD — 4 commits total)
- **Files modified:** 2 (health_checks.py, tests/test_health_checks.py)

## Accomplishments

- Added `UPTIME_WARN_DAYS: int = 7` and `UPTIME_STALE_DAYS: int = 30` module-level constants immediately after `DISK_WARN_PCT` in `health_checks.py`
- Implemented `_check_uptime(report)` private helper with correct escalation: `None -> OK`, `<= 7d -> OK`, `> 7d and <= 30d -> UPTIME_WARN (yellow)`, `> 30d -> UPTIME_STALE (red)`. Stale check comes before warn check per D-11.
- `UPTIME_STALE` detail contains exact verbatim string "Hibernation time is counted on Windows" per WARN-05
- Extended `evaluate_warnings()` return list to 4 elements — `_check_uptime(report)` added as 4th element; docstring updated to reflect D-14
- Renamed `test_evaluate_warnings_always_returns_three` to `test_evaluate_warnings_always_returns_four`; updated docstring (Phase 13 D-14), assertion (`len == 4`), and added 4th code assertion (`warnings[3].code in ('UPTIME', 'UPTIME_WARN', 'UPTIME_STALE')`)
- Updated `assert len(result) == 3` to `assert len(result) == 4` in `test_evaluate_warnings_never_raises`
- Added `test_uptime_check` parametrized over 8 boundary values (None, 0, 6d, 7d, 7d+1s, 8d, 30d, 31d)
- Added `test_uptime_stale_detail_mentions_hibernation` asserting `'hibernation' in detail.lower()`
- Full test suite: 238 tests passing (up from 229 after Plan 01, +9 new uptime tests)

## Task Commits

Each task was committed atomically using TDD RED/GREEN cycle:

1. **Task 1 RED: Add failing uptime check tests** — `9f94704` (test)
2. **Task 1 GREEN: Add _check_uptime() and extend evaluate_warnings to 4 objects** — `1daad94` (feat)
3. **Task 2: Update test suite for 4-object contract; rename always-N test** — `1a1a342` (test)

## TDD Gate Compliance

Task 1 followed full RED/GREEN cycle:
- Task 1 RED: `test(13-02)` commit `9f94704` — tests fail (IndexError: list index out of range at warnings[3])
- Task 1 GREEN: `feat(13-02)` commit `1daad94` — all uptime tests pass

Task 2 was a test-only update (rename + fix existing test assertions). No separate RED/GREEN cycle needed — the "RED" state was the pre-existing `test_evaluate_warnings_always_returns_three` failure (asserting len==3 against a 4-object return), resolved by the test update commit.

## Files Modified

- `health_checks.py` — module docstring updated (three -> four); `UPTIME_WARN_DAYS` and `UPTIME_STALE_DAYS` constants added; `evaluate_warnings()` docstring updated and return list extended with `_check_uptime(report)`; `_check_uptime()` private helper added after `_check_rename()`
- `tests/test_health_checks.py` — `test_evaluate_warnings_always_returns_three` renamed to `test_evaluate_warnings_always_returns_four` with updated assertions; `assert len(result) == 3` updated to `== 4`; `test_uptime_check` parametrize added; `test_uptime_stale_detail_mentions_hibernation` added

## Decisions Made

- Stale check evaluated before warn check in `_check_uptime` — when `uptime_seconds > 30 * 86400`, both the `> 7d` and `> 30d` conditions are true. The stale condition must be evaluated first to escalate correctly. Order enforces D-11 boundary semantics.
- Floor division (`// 86400`) used for day calculation — sub-day seconds do not cross the threshold. `7 * 86400 + 1` seconds gives `days = 7` (not 8), which is `== UPTIME_WARN_DAYS`, not `>`. The threshold is strictly `>` (not `>=`), so exactly 7 days and 7 days + 1 second both remain OK.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect test expectation for 7d+1s boundary case**
- **Found during:** Task 1 GREEN verification
- **Issue:** The plan's action section specified `(7 * 86400 + 1, 'UPTIME_WARN', 'WARN', 'yellow')` for the parametrize table, but the implementation uses floor division (`uptime_seconds // 86400`). `604801 // 86400 = 7`, so `days = 7` and `7 > UPTIME_WARN_DAYS (7)` is `False`. The test expected UPTIME_WARN but the implementation correctly returned UPTIME.
- **Fix:** Changed expected values for the `7 * 86400 + 1` case to `('UPTIME', 'OK', None)` — matching the floor-division behavior specified in the implementation action
- **Files modified:** `tests/test_health_checks.py`
- **Commit:** `1a1a342`

## Known Stubs

None — `_check_uptime()` reads `report.uptime_seconds` which is populated by `_collect_uptime()` (added in Plan 01). The `None` default is intentional (collection not yet run or failed gracefully).

## Threat Flags

No new threat surface introduced. The threat model in the plan covers all new surface (T-13-06, T-13-07, T-13-08) — all accepted per plan disposition.

## Self-Check: PASSED

- `health_checks.py` exists and contains `UPTIME_WARN_DAYS`, `UPTIME_STALE_DAYS`, `_check_uptime`
- `tests/test_health_checks.py` contains `test_evaluate_warnings_always_returns_four`, `test_uptime_check`, `test_uptime_stale_detail_mentions_hibernation`
- Commits `9f94704`, `1daad94`, `1a1a342` all present in git log
- 238 tests passing, 0 failures
