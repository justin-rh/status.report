---
phase: 16-tech-debt-cleanup
plan: "02"
subsystem: cli
tags: [main.py, cli, argparse, collectors, warnings]

# Dependency graph
requires: []
provides:
  - _run_cli() no longer calls collect_pending_updates or collect_vendor_updates
  - main() emits stderr warning when --app and --output are both set
affects: [16-tech-debt-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Conflict warning pattern: print(WARNING, file=sys.stderr) before routing to subcommand"

key-files:
  created: []
  modified:
    - main.py

key-decisions:
  - "D-10: Warning text chosen as 'WARNING: --output is ignored in --app mode' — matches existing [WARN] convention tone"
  - "D-11: Wasted collector block removed from _run_cli(); full-pipeline block in main() preserved unchanged"

patterns-established:
  - "Stderr warning before subcommand routing: check conflicting flags inside the routing block, print to sys.stderr, then call the subcommand"

requirements-completed:
  - DEBT-02
  - DEBT-03

# Metrics
duration: 5min
completed: 2026-05-19
---

# Phase 16 Plan 02: Fix wasted collector calls in _run_cli and add --app/--output conflict warning Summary

**Removed 4-line dead update-collector block from _run_cli() and added explicit stderr warning when --app and --output flags conflict in main()**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-19T22:48:00Z
- **Completed:** 2026-05-19T22:53:15Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Eliminated wasted collect_pending_updates and collect_vendor_updates calls from _run_cli() — the CLI output path never used their results, so running `scry --warnings --updates` was silently discarding collected data
- Added conditional stderr warning in main() when both --app and --output are set, making the silent flag discard explicit to the user
- All 291 existing tests continue to pass; no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove wasted collector calls from _run_cli()** - `611edeb` (fix)
2. **Task 2: Add --app/--output conflict warning in main()** - `fb6d2ef` (feat)

## Files Created/Modified

- `main.py` - Removed 4-line `if args.updates` block from `_run_cli()` (lines 58-62); added 2-line `if args.output` warning block inside `if args.app:` in `main()`

## Decisions Made

- Warning text chosen as `"WARNING: --output is ignored in --app mode"` — consistent with the [WARN] stderr tone used elsewhere in the codebase
- The warning fires only when BOTH `args.app` AND `args.output` are set; `--output` alone (in full-pipeline mode) is unaffected

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- DEBT-02 and DEBT-03 are resolved; main.py CLI routing is now accurate about what it collects and what it ignores
- No blockers introduced; ready for remaining Phase 16 tech debt plans

---
*Phase: 16-tech-debt-cleanup*
*Completed: 2026-05-19*
