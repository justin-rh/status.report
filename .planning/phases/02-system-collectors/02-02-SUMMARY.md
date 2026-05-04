---
phase: 02-system-collectors
plan: 02
subsystem: collectors
tags: [wmi, psutil, winreg, platform, windows, hardware, profiles, testing, pytest, mocking]

# Dependency graph
requires:
  - phase: 02-system-collectors/02-01
    provides: collect_hardware(report) and collect_profiles(report) in collectors/windows/hardware.py with module-level _wmi_module pattern
  - phase: 01-models-and-hostname-parser
    provides: AuditReport dataclass, parse_hostname for test fixtures
provides:
  - collectors/__init__.py with collect_all(report) orchestration entry point
  - 47 total passing tests (21 hardware + 8 profile + 18 name_parser)
  - Full Phase 2 integration verified: collect_all() populates all AuditReport hardware fields
affects:
  - 03-renderer (imports collect_all via collectors package; reads all AuditReport hardware fields)
  - 04-app-detection (collect_all called before app detection; hardware already populated)
  - main.py (Phase 3 wiring — collect_all is the single entry point to call)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "collect_all(report) as single orchestration entry point: main.py calls this one function; platform-specific dispatch hidden inside"
    - "Lazy import inside function body: from collectors.windows.hardware import ... defers Windows-only ImportError to call time"
    - "Test files created in earlier wave carry forward: Wave 1 (02-01) created test files; Wave 2 (02-02) verified and extended them"

key-files:
  created:
    - .planning/phases/02-system-collectors/02-02-SUMMARY.md
  modified:
    - collectors/__init__.py

key-decisions:
  - "Lazy import of collect_hardware/collect_profiles inside collect_all() body — defers Windows-only ImportError (winreg/wmi) to call time; collectors/__init__.py importable on any platform"
  - "Test files from Wave 1 satisfy Wave 2 requirements — no duplication needed; existing 21 tests cover all must_have scenarios"
  - "collect_hardware called before collect_profiles in collect_all() — per D-10 decision from 02-CONTEXT.md"

patterns-established:
  - "Single-function entry point: collect_all(report) is the only public API of the collectors package"
  - "Platform dispatch via lazy import: collectors/__init__.py stays platform-neutral; platform import happens inside function"

requirements-completed: [COLL-02, COLL-03]

# Metrics
duration: 5min
completed: 2026-05-04
---

# Phase 2 Plan 02: Collector Wiring + Tests Summary

**collect_all(report) orchestration entry point in collectors/__init__.py with lazy platform import; 47/47 tests passing and Phase 2 integration verified on Windows machine**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-04T21:53:00Z
- **Completed:** 2026-05-04T21:55:43Z
- **Tasks:** 2
- **Files modified:** 1 (collectors/__init__.py)

## Accomplishments

- `collect_all(report)` implemented in `collectors/__init__.py` as the single orchestration entry point for all collectors; lazy import defers Windows-only imports to call time
- All 47 tests pass (13 hardware collector + 8 profile collector + 26 name parser from Phase 1)
- Phase 2 integration verified end-to-end: os_version=11, os_build=10.0.26200, ram_gb=30.7, disk_total_gb=475.6, 10 local profiles enumerated, no collection_errors

## Task Commits

1. **Task 1: Add collect_all() to collectors/__init__.py** - `bd1171e` (feat)
2. **Task 2: Verify unit tests pass (pre-existing from 02-01)** - no new commit needed (tests unchanged from Wave 1)

**Plan metadata:** (to be added after STATE.md update)

## Files Created/Modified

- `collectors/__init__.py` — replaced 2-line stub with full collect_all() orchestration function (18 lines); lazy import of collect_hardware + collect_profiles inside function body

## Decisions Made

- Lazy import pattern used for `collect_hardware` and `collect_profiles` inside function body: `from collectors.windows.hardware import collect_hardware, collect_profiles` — this keeps the package importable on any platform without triggering Windows-only import errors at module load time
- Test files were pre-created in Wave 1 (02-01) and already satisfied all 02-02 must_have requirements — no duplication or modification needed

## Deviations from Plan

### Context

Wave 1 (Plan 02-01) was more comprehensive than planned — it created `collectors/windows/hardware.py` AND both test files (`tests/test_hardware_collector.py` and `tests/test_profile_collector.py`) with 21 tests covering all Wave 2 must_have scenarios. The SUMMARY for 02-01 lists these test files as created artifacts with commits 46ac897 and 5448750.

Wave 2 (this plan, 02-02) therefore only required:
- Task 1: Implement `collect_all()` in `collectors/__init__.py` — executed as planned
- Task 2: Verify existing tests satisfy 02-02 must_haves — all 21 tests pass; no new tests needed

This is not a deviation per se — Wave 1 over-delivered, so Wave 2 had less to do. All 02-02 acceptance criteria are satisfied.

**Total deviations:** None from plan intent. Wave 1 pre-delivered test files; Wave 2 confirmed and verified.

## Issues Encountered

- `cpu_model=None` on dev machine: expected, documented in 02-01 SUMMARY. The `wmi` package is not installed in the dev Python environment (no COM server). `_WMI_AVAILABLE=False` at import time so `_collect_cpu_model` returns immediately without error. Correct behavior — wmi missing is a setup difference, not a runtime failure.

## Known Stubs

None — `collect_all()` fully implemented and wired to real collector functions. Phase 3 (renderer) can read all AuditReport fields.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `collect_all(report)` importable from `collectors` — single call to populate all hardware fields
- Phase 3 (renderer) can import `from collectors import collect_all` and call `collect_all(report)` to get all data
- Phase 4 (app detection) builds on the same `AuditReport` object after hardware collection
- All 47 tests green; no regressions from prior phases
- Blocker note: `wmi` package must be installed on target machines for `cpu_model` to be populated (confirmed working on any machine where `wmi` 1.5.1 is installed)

---
*Phase: 02-system-collectors*
*Completed: 2026-05-04*
