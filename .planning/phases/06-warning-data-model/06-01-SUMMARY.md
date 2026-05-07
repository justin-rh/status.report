---
phase: 06-warning-data-model
plan: "01"
subsystem: models
tags: [python, dataclass, health-checks, warnings]

requires:
  - phase: 01-models-and-hostname-parser
    provides: AuditReport, AppStatus, ParsedHostname dataclasses in models.py

provides:
  - Warning dataclass in models.py (code, severity, message, detail fields)
  - AuditReport.warnings field (list[Warning], default empty)
  - health_checks.py module with evaluate_warnings() function
  - OS_WARN_BUILD = 22000 and DISK_WARN_PCT = 0.15 threshold constants

affects:
  - 07-warning-display-renderer
  - 08-ninjaoone-output
  - main.py (caller of evaluate_warnings)

tech-stack:
  added: []
  patterns:
    - "Pure-function health check module: no OS imports, returns list[Warning] always"
    - "Always-two pattern: evaluate_warnings always returns exactly 2 Warning objects"

key-files:
  created:
    - health_checks.py
  modified:
    - models.py

key-decisions:
  - "Warning dataclass uses plain str for severity ('OK'/'WARN') — no Enum, consistent with AppStatus.service_state pattern (D-03)"
  - "health_checks.py not warnings.py — avoids shadowing stdlib warnings module (D-05)"
  - "evaluate_warnings always returns 2 Warning objects regardless of check result — Phase 7 gets complete status table (D-06)"
  - "os_build compared as int(os_build) not lexicographic string — '9999' < '22000' numerically but not lexicographically (D-07)"
  - "Disk check uses <= 0.15 not < 0.15 — exactly 15% free triggers WARN (D-08)"
  - "None disk fields return severity='OK' with detail note — missing data is not a warning condition (D-08)"

requirements-completed:
  - WARN-01
  - WARN-02

duration: 1min
completed: 2026-05-07
---

# Phase 6 Plan 01: Warning Data Model Summary

**Warning dataclass + health_checks.py with OS version and disk space checks using build-22000 and 15% thresholds**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-05-07T19:46:17Z
- **Completed:** 2026-05-07T19:47:33Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `Warning` dataclass to models.py with `code`, `severity`, `message`, `detail` fields — inserted after AppStatus, before AuditReport
- Added `AuditReport.warnings: list[Warning] = field(default_factory=list)` after `collection_errors`
- Created `health_checks.py` with `evaluate_warnings()`, `_check_os_version()`, `_check_disk_space()` and threshold constants
- All 94 existing tests pass without modification

## Task Commits

1. **Task 1: Add Warning dataclass and AuditReport.warnings** - `61ecc9c` (feat)
2. **Task 2: Create health_checks.py** - `32d5dbd` (feat)

## Files Created/Modified

- `models.py` — Added `Warning` dataclass and `AuditReport.warnings` field
- `health_checks.py` — New module: `evaluate_warnings()`, `OS_WARN_BUILD = 22000`, `DISK_WARN_PCT = 0.15`

## Decisions Made

- `list[Warning]` (not `list['Warning']`) used in AuditReport.warnings — Warning is defined before AuditReport in the same file, so no forward reference needed
- `_check_os_version` wraps `int()` in `try/except ValueError` — non-numeric os_build returns OK with detail note (T-06-01-01 mitigation)
- `_check_disk_space` guards `total == 0` before division — prevents ZeroDivisionError (T-06-01-02 mitigation)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `Warning` dataclass and `evaluate_warnings()` are ready for Plan 06-02 tests
- `AuditReport.warnings` field is wired and defaults to empty list — existing code unaffected
- Phase 7 renderer can import and use `report.warnings` once populated by `main.py`

---
*Phase: 06-warning-data-model*
*Completed: 2026-05-07*

## Self-Check: PASSED
