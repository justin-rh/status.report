---
phase: 02-system-collectors
plan: 01
subsystem: collectors
tags: [wmi, psutil, winreg, platform, windows, hardware, profiles, pyinstaller]

# Dependency graph
requires:
  - phase: 01-models-and-hostname-parser
    provides: AuditReport dataclass with all hardware fields pre-defined; parse_hostname for test fixtures
provides:
  - collectors/windows/hardware.py with collect_hardware(report) and collect_profiles(report)
  - 21 unit tests covering hardware and profile collection paths including all degradation scenarios
  - Module-level _wmi_module/_WMI_AVAILABLE pattern enabling CI testing without COM server
affects:
  - 02-02 (wiring + tests — imports collect_hardware and collect_profiles via collect_all)
  - 03-renderer (reads all 7 hardware fields and local_profiles from AuditReport)
  - 04-app-detection (AuditReport passed by reference; hardware already populated)

# Tech tracking
tech-stack:
  added:
    - psutil 7.2.2 (RAM, disk usage — standard user; was not installed, auto-installed as Rule 3 fix)
    - wmi 1.5.1 (CPU model via Win32_Processor — lazy module-level import with _WMI_AVAILABLE guard)
    - winreg (stdlib — HKLM ProfileList enumeration)
    - platform (stdlib — os_version, os_build)
  patterns:
    - "_wmi_module/_WMI_AVAILABLE module-level import pattern: allows patching in CI without real COM"
    - "In-place mutation pattern: collect_X(report) mutates AuditReport fields, never returns a value"
    - "One error per subsystem: single collection_errors.append per failed subsystem (D-02)"
    - "Silent skip for per-item errors: unreadable SID subkeys skipped without logging (D-02)"
    - "No exception propagation: every public function has a top-level try/except guarantee"

key-files:
  created:
    - collectors/windows/hardware.py
    - tests/test_hardware_collector.py
    - tests/test_profile_collector.py
  modified: []

key-decisions:
  - "Module-level _wmi_module + _WMI_AVAILABLE pattern chosen over lazy import — enables patch.object targeting in tests without COM server in CI"
  - "psutil imported at module level (not lazy) — consistent with patchability requirement for disk error tests"
  - "win32_Product not used anywhere — CLAUDE.md constraint enforced; Win32_Processor used instead"
  - "cpu_model silently None (no error) when _WMI_AVAILABLE=False — missing library is not a runtime failure"
  - "ExpandEnvironmentStrings called before split — handles REG_EXPAND_SZ paths like %SystemDrive%\\Users\\..."

patterns-established:
  - "Collector public functions (collect_X) call private helpers; never raise across layer boundaries"
  - "Private _enumerate_profiles raises OSError for registry access failure — caught by public collect_profiles"
  - "Per-SID inner errors (FileNotFoundError, OSError) silently continue — only root key failure logged"

requirements-completed: [COLL-02, COLL-03]

# Metrics
duration: 3min
completed: 2026-05-04
---

# Phase 2 Plan 01: System Collectors — Hardware Summary

**Windows hardware and profile collectors using psutil/platform/winreg with module-level WMI import pattern for CI testability and full graceful degradation to None + collection_errors**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-04T21:48:26Z
- **Completed:** 2026-05-04T21:51:45Z
- **Tasks:** 2 (TDD: RED + GREEN for each)
- **Files modified:** 3 created

## Accomplishments

- `collect_hardware(report)` populates all 7 hardware fields: os_version, os_build, cpu_model, ram_gb, disk_total_gb, disk_free_gb, current_user — with graceful degradation for WMI and disk failures
- `collect_profiles(report)` reads HKLM ProfileList, filters S-1-5-18/19/20, expands environment strings, and extracts usernames from path last segment
- 21 unit tests (13 hardware + 8 profile) covering all happy paths and all degradation paths; 47 total pass (including Phase 1 tests)
- Module verified against real Windows machine: 10 user profiles enumerated, OS 11 / 10.0.26200, 30.7 GB RAM, 475.6 GB disk

## Task Commits

1. **Task 1 RED: add failing tests for collect_hardware** - `46ac897` (test)
2. **Task 1 GREEN: implement collect_hardware with WMI/psutil/platform/winreg** - `fa80df1` (feat)
3. **Task 2: add collect_profiles tests** - `5448750` (feat)

## Files Created/Modified

- `collectors/windows/hardware.py` — collect_hardware + collect_profiles + 6 private helpers; 154 lines; module-level _wmi_module pattern
- `tests/test_hardware_collector.py` — 13 unit tests for collect_hardware covering all fields and degradation paths
- `tests/test_profile_collector.py` — 8 unit tests for collect_profiles covering SID filtering, path expansion, error paths

## Decisions Made

- Module-level `_wmi_module` / `_WMI_AVAILABLE` import pattern chosen for testability: allows `patch.object(hw_mod, "_wmi_module")` in tests without any COM server installed
- `psutil` imported at module top level (not lazy) so tests can patch `hw_mod.psutil` for disk error simulation
- `Win32_Product` not used anywhere — confirmed prohibited by CLAUDE.md; Win32_Processor used for cpu_model
- Silent degradation (no error logged) when `_WMI_AVAILABLE=False` — wmi not installed is a setup difference, not a runtime failure
- `winreg` imported at module top level (stdlib, always available on Windows) so tests can patch `hw_mod.winreg`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing psutil dependency**
- **Found during:** Task 1 (GREEN phase — all 13 tests failing at import)
- **Issue:** `ModuleNotFoundError: No module named 'psutil'` — psutil 6.x listed in CLAUDE.md stack but not installed in environment
- **Fix:** `pip install psutil` — installed 7.2.2 (minor version above 6.x spec, fully compatible)
- **Files modified:** none (environment install)
- **Verification:** All 13 tests passed after install; import verified
- **Committed in:** Noted in fa80df1 commit message

---

**Total deviations:** 1 auto-fixed (1 blocking dependency install)
**Impact on plan:** Required for any psutil-dependent code to run. No scope creep.

## Issues Encountered

- `cpu_model=None` on the dev machine because `wmi` package is not installed in the dev Python environment (no COM server). This is expected behavior — `_WMI_AVAILABLE=False` at import time, so `_collect_cpu_model` returns immediately without logging an error. The degradation path works correctly.

## Known Stubs

None — both functions are fully implemented with real data sources. Verified against actual Windows registry and hardware.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `collect_hardware(report)` and `collect_profiles(report)` are fully implemented and importable
- Phase 02-02 can wire `collect_all(report)` in `collectors/__init__.py` calling both functions in order
- Phase 3 (renderer) can read all AuditReport hardware fields, including handling `None` for any field
- WMI package not installed in dev environment — `cpu_model` will remain None in local runs; will work on target Windows machines with WMI available

---
*Phase: 02-system-collectors*
*Completed: 2026-05-04*
