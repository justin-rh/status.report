---
phase: 11-steve
plan: 01
subsystem: cli
tags: [argparse, cli, stdout, sys.argv, pytest, capsys]

# Dependency graph
requires:
  - phase: 10-mac-collectors
    provides: collect_all platform dispatch and main.py pipeline structure
  - phase: 08-ninjaone-compat
    provides: isatty() guard and [SUMMARY] stdout pattern
provides:
  - argparse CLI branch in main.py with --name, --serial, --warnings flags
  - _run_cli() function with union-of-required-collection scope logic
  - 8 CLI flag tests in tests/test_main.py
affects: [any future plan modifying main.py or adding CLI flags]

# Tech tracking
tech-stack:
  added: [argparse (stdlib)]
  patterns:
    - CLI branch before full pipeline — argparse at top of main(), early return via _run_cli()
    - Union collection scope — needs_full / needs_hardware flags determine minimum collection
    - sys.argv patch in test helpers — patch("sys.argv", ["status_report"]) in _patched_main to prevent argparse consuming pytest argv

key-files:
  created: []
  modified:
    - main.py
    - tests/test_main.py
    - tests/test_main_mac.py

key-decisions:
  - "argparse placed at top of main() before hostname line — CLI branch exits before full pipeline"
  - "_run_cli() is a standalone function above main() — keeps main() readable and testable separately"
  - "needs_full = args.warnings; needs_hardware = args.serial and not needs_full — union rule (D-11)"
  - "sys.argv patched in _patched_main helper (not in test functions) — fixes argparse consuming pytest argv without touching test_ functions"
  - "test_main_mac.py _patched_main_platform also needed sys.argv patch — auto-fixed as Rule 1 bug"

patterns-established:
  - "sys.argv patch in test helpers: any future main() test helper must patch sys.argv to prevent argparse consuming pytest argv"
  - "CLI early-return pattern: argparse setup -> check cli_mode -> _run_cli() + return before full pipeline"

requirements-completed: [CLI-01]

# Metrics
duration: 2min
completed: 2026-05-12
---

# Phase 11 Plan 01: Steve Summary

**argparse CLI branch with --name/--serial/--warnings flags using targeted collection scope (D-08 through D-11); 8 new passing tests**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-12T17:05:44Z
- **Completed:** 2026-05-12T17:08:08Z
- **Tasks:** 2
- **Files modified:** 3 (main.py, tests/test_main.py, tests/test_main_mac.py)

## Accomplishments
- Added `import argparse` and `_run_cli(args)` to main.py implementing all 7 flag combinations per D-01 through D-11
- Added 8 CLI flag tests (test_name_flag_prints_hostname, test_serial_flag_prints_serial, test_serial_flag_unknown_when_none, test_warnings_flag_prints_warn_messages, test_warnings_flag_empty_when_all_ok, test_name_serial_combined_output_order, test_cli_mode_suppresses_summary_line, test_no_flags_runs_full_pipeline)
- Full test suite: 203 passing (195 prior + 8 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add argparse CLI branch to main.py** - `3b9af18` (feat)
2. **Task 2: Add CLI flag tests to test_main.py** - `8230190` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `main.py` - Added `import argparse`, `_run_cli()` function, and argparse setup at top of `main()`
- `tests/test_main.py` - Added `patch("sys.argv", ...)` to `_patched_main` helper; appended 8 CLI flag tests
- `tests/test_main_mac.py` - Added `patch("sys.argv", ["status_report"])` to `_patched_main_platform` helper (Rule 1 auto-fix)

## Decisions Made
- `_run_cli()` placed above `main()` so main() stays readable — CLI branch is a clean early return
- `patch("sys.argv", ["status_report"])` added to `_patched_main` helper (not individual test functions) so it covers all 4 existing tests without touching their bodies — honors "Do NOT modify existing tests" constraint
- `test_no_flags_runs_full_pipeline` uses the corrected pattern from the plan (second version): `patch("sys.argv", ["status_report"])` + `_patched_main` context manager + asserts `[SUMMARY]` in output

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_main_mac.py _patched_main_platform missing sys.argv patch**
- **Found during:** Task 2 verification (full suite run)
- **Issue:** `test_darwin_interactive_calls_subprocess_open` and `test_non_darwin_interactive_calls_startfile` failed with `SystemExit: 2` — argparse in main() tried to parse pytest's `tests/ -v` as CLI arguments
- **Fix:** Added `patch("sys.argv", ["status_report"])` to `_patched_main_platform` context manager in `tests/test_main_mac.py`
- **Files modified:** `tests/test_main_mac.py`
- **Verification:** All 203 tests pass after fix
- **Committed in:** `8230190` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary correctness fix; argparse change in Task 1 logically requires sys.argv patching in all main() test helpers. No scope creep.

## Issues Encountered
None beyond the auto-fixed test_main_mac.py deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 11 Plan 01 complete — CLI flags fully implemented and tested
- All 203 tests pass; no regressions
- `python main.py --name`, `--serial`, `--warnings`, `--help` all functional
- Ready for packaging / NinjaOne integration if needed

---
*Phase: 11-steve*
*Completed: 2026-05-12*
