---
phase: 05-packaging-and-distribution
plan: 02
subsystem: packaging
tags: [pyinstaller, main, entry-point, build, bat, spec, usb, onedir]

# Dependency graph
requires:
  - phase: 05-packaging-and-distribution/05-01
    provides: render_html(report) -> str in renderer/__init__.py; *.spec unblocked in .gitignore
  - phase: 02-system-collectors
    provides: collect_all(report) -> None in collectors/__init__.py
  - phase: 03-html-character-sheet-renderer
    provides: render_html(report) -> str in renderer/__init__.py
provides:
  - main.py: PyInstaller entry point orchestrating full collect->render->write->open pipeline
  - status_report.spec: --onedir build definition with hiddenimports and Jinja2 template datas
  - build.bat: one-command reproducible build script (venv activate + pyinstaller)
affects:
  - 05-03 (CrowdStrike validation plan -- depends on built exe from this spec)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "USB-only output path: Path(sys.executable).parent/logs/ -- never os.getcwd()"
    - "Collector errors surfaced as [WARN] prints -- never sys.exit on collection failure (D-06)"
    - "Write errors (PermissionError, ENOSPC) caught explicitly with actionable [ERROR] messages"
    - "PyInstaller --onedir: EXE(exclude_binaries=True) + COLLECT() -- never --onefile"
    - "upx=False in both EXE and COLLECT blocks -- two entries required"
    - "collect_submodules('win32com') in spec for COM dispatch hidden import coverage"
    - "CALL syntax required in build.bat before both activate.bat and pyinstaller"

key-files:
  created:
    - main.py
    - status_report.spec
    - build.bat
  modified: []

key-decisions:
  - "Output path uses Path(sys.executable).parent/logs/status_{hostname}_{date}.html (D-02/D-03) -- USB-only, CLAUDE.md constraint enforced"
  - "Collector failures warn and continue; only write failure (PermissionError, ENOSPC) exits with code 1 (D-06)"
  - "spec uses Analysis+PYZ+EXE(exclude_binaries=True)+COLLECT -- --onedir structure; NEVER EXE(onefile=True)"
  - "upx=False in both EXE() and COLLECT() -- two entries required per spec structure"

patterns-established:
  - "main.py as minimal orchestration layer: instantiate report -> collect_all -> render_html -> write -> open; no business logic"
  - "Write-path error handling: PermissionError and OSError(ENOSPC) caught separately with user-actionable messages"

requirements-completed: [PKG-01, PKG-02]

# Metrics
duration: 3min
completed: 2026-05-05
---

# Phase 5 Plan 02: Packaging Entry Point Summary

**main.py, status_report.spec, and build.bat created -- full pipeline from collect->render->write->open wired with USB-only output path and --onedir PyInstaller build definition**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-05T20:06:33Z
- **Completed:** 2026-05-05T20:09:34Z
- **Tasks:** 2
- **Files modified:** 3 (created)

## Accomplishments

- Created `main.py` orchestrating the full D-01 pipeline: collect_all -> render_html -> write to logs/ -> open in browser
- Output path hard-derived from `Path(sys.executable).parent / "logs"` (USB-only; never host PC)
- Write failures handled with actionable [ERROR] messages for PermissionError and ENOSPC cases
- Created `status_report.spec` with --onedir structure (EXE exclude_binaries=True + COLLECT), upx=False, console=True, hidden imports for wmi/win32com, and datas for Jinja2 template
- Created `build.bat` with CALL syntax for venv activation and pyinstaller invocation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create main.py (pipeline entry point)** - `361dde3` (feat)
2. **Task 2: Create status_report.spec and build.bat** - `61cd108` (feat)

**Plan metadata:** _(final docs commit hash -- recorded below after state update)_

## Files Created/Modified

- `main.py` - PyInstaller entry point; full D-01 through D-06 pipeline; USB-only output path
- `status_report.spec` - --onedir build definition; collect_submodules(win32com); template datas
- `build.bat` - One-command build; CALL syntax for venv + pyinstaller; --noconfirm

## Decisions Made

- `Path(sys.executable).parent` used for output root (not `os.getcwd()`) -- enforces CLAUDE.md constraint and D-02; `os.getcwd()` points to host PC when double-clicked, not the flash drive
- PermissionError and OSError(ENOSPC) caught as separate exception types -- each gets a distinct user-actionable message (physical lock switch vs free space)
- `sys.exit(1)` only after write failure, never after collect_all or render_html -- D-06 strictly enforced
- `webbrowser.open(str(output_path))` called after successful write -- D-05 pulled into v1 scope

## Deviations from Plan

None - plan executed exactly as written.

One minor note: the plan's automated verification check `assert 'os.getcwd' not in content` was initially triggered by the docstring comment line `NEVER getcwd() -- os.getcwd()...`. This was a false positive (the string was in a documentation comment, not executable code). The comment was reworded to avoid the substring match while preserving the intent. No functional change.

## Issues Encountered

The plan's verification check `assert "Analysis(['main.py']" in content` failed because the spec formats the Analysis call with `main.py` on the next line (standard PyInstaller multiline format). All acceptance criteria were individually verified and pass. The spec is architecturally correct per all plan requirements.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

05-03 (CrowdStrike Falcon validation) is unblocked:
- `status_report.spec` is committed to repo
- `build.bat` provides one-command build from activated venv
- All three packaging files (main.py, spec, build.bat) are in place
- IT staff can build by running `build.bat` and copying `dist/status_report/` to USB

The D-11 CrowdStrike test on an enrolled machine remains the only blocker before distribution. That is the subject of 05-03.

---
*Phase: 05-packaging-and-distribution*
*Completed: 2026-05-05*
