---
phase: 10-mac-collectors
plan: "03"
subsystem: platform
tags: [mac, darwin, platform-dispatch, subprocess, collectors, main]

# Dependency graph
requires:
  - phase: 10-01
    provides: collectors/mac/hardware.py with collect_hardware and collect_profiles
  - phase: 10-02
    provides: collectors/mac/apps.py with collect_apps and MAC_APP_SPECS
provides:
  - "Platform-dispatching collect_all() that routes darwin to collectors.mac and else to collectors.windows"
  - "main.py with subprocess import, darwin usb_root = Path(__file__).parent, and darwin open via subprocess.run(['open', ...])"
affects:
  - 10-mac-collectors
  - main

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy import dispatch inside function body — if sys.platform == 'darwin' with all imports inside collect_all()"
    - "Platform-aware usb_root split — inline two-branch if/else in main() (no helper function, per D-02)"
    - "subprocess.run(['open', path]) for macOS auto-open vs os.startfile() for Windows (per D-03)"

key-files:
  created:
    - tests/test_collectors_init.py
    - tests/test_main_mac.py
  modified:
    - collectors/__init__.py
    - main.py

key-decisions:
  - "10-03: sys.platform == 'darwin' dispatch lives inside collect_all() body (lazy import pattern) — module remains importable on any platform (D-05)"
  - "10-03: usb_root split inline in main() as two-line if/else — no helper function per D-02 decision"
  - "10-03: subprocess.run(['open', str(output_path)]) wrapped in try/except OSError matching Windows startfile pattern"

patterns-established:
  - "Platform dispatch pattern: if sys.platform == 'darwin': / else: inside function body, lazy imports only"

requirements-completed:
  - PLAT-V2-04

# Metrics
duration: 3min
completed: "2026-05-08"
---

# Phase 10 Plan 03: Mac Integration Wiring Summary

**Platform-dispatching collect_all() with darwin branch + main.py subprocess import, Path(__file__).parent usb_root, and subprocess.run(['open', ...]) auto-open**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-08T18:18:37Z
- **Completed:** 2026-05-08T18:21:25Z
- **Tasks:** 2
- **Files modified:** 4 (2 source, 2 test)

## Accomplishments

- collectors/__init__.py updated with if sys.platform == "darwin" dispatch branch — darwin imports from collectors.mac.hardware and collectors.mac.apps; else imports from collectors.windows (unchanged)
- main.py patched with all three required changes: import subprocess, Platform-aware usb_root (Path(__file__).parent on darwin), and platform-aware auto-open (subprocess.run(["open",...]) on darwin)
- 7 new tests added (3 for collectors/__init__.py dispatch, 4 for main.py Mac behavior); all 182 tests pass

## Task Commits

Each task was committed atomically using TDD (RED then GREEN):

1. **Task 1 RED: collectors/__init__.py failing tests** - `aa62794` (test)
2. **Task 1 GREEN: collectors/__init__.py darwin dispatch** - `8b2d4ec` (feat)
3. **Task 2 RED: main.py Mac failing tests** - `8ab8b86` (test)
4. **Task 2 GREEN: main.py subprocess + darwin branches** - `883774a` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `collectors/__init__.py` - Updated with platform dispatch: darwin branch imports from collectors.mac, else from collectors.windows; import sys inside function body (lazy pattern)
- `main.py` - Three edits: import subprocess added to stdlib block; usb_root split to darwin/else; isatty() open block split to darwin subprocess.run/else os.startfile
- `tests/test_collectors_init.py` - 3 tests: darwin dispatch calls mac collectors, non-darwin calls windows collectors, module importable without platform imports
- `tests/test_main_mac.py` - 4 tests: subprocess present in main.py imports, darwin interactive calls subprocess.run open, non-darwin calls os.startfile, main.py contains darwin usb_root branch

## Decisions Made

- D-05 enforced: lazy import pattern — `import sys` and all from-imports inside collect_all() body. Module-level imports remain only `from __future__ import annotations` and `from models import AuditReport`. This keeps collectors/__init__.py importable on any platform including Windows CI.
- D-02 enforced: usb_root split is inline two-branch if/else directly in main() — no helper function as specified in context.
- D-03 enforced: subprocess.run(["open", str(output_path)]) wrapped in OSError try/except to match the Windows startfile error handling pattern exactly.
- Docstring in collectors/__init__.py updated: removed "Mac stubs reserved for v2" — Phase 10 now complete wiring.

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

Both tasks followed RED-GREEN cycle:
- Task 1: RED commit aa62794 (test) → GREEN commit 8b2d4ec (feat)
- Task 2: RED commit 8ab8b86 (test) → GREEN commit 883774a (feat)

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- collectors/__init__.py and main.py are now fully wired for Mac execution
- `python3 main.py` on macOS will route through collectors.mac.hardware and collectors.mac.apps, write output to Path(__file__).parent/logs/, and open the HTML in the default browser
- Phase 10 Plan 04 (if any) or milestone close: validate MAC_APP_SPECS bundle paths on a real Mac fleet device
- Pending: NinjaOne launchdaemon_label "com.ninjarmm.agent" — LOW confidence, requires live Mac verification before Phase 10 closes

---
*Phase: 10-mac-collectors*
*Completed: 2026-05-08*
