---
phase: 07-html-warnings-section
plan: "02"
subsystem: renderer
tags: [jinja2, html, warnings, health-checks, character-sheet]

# Dependency graph
requires:
  - phase: 06-warning-data-model
    provides: evaluate_warnings() and Warning dataclass
  - phase: 07-html-warnings-section
    plan: "01"
    provides: _check_rename helper, always-three guarantee for evaluate_warnings
provides:
  - Collapsible HTML warnings box driven by structured Warning list
  - _build_context() updated with 'warnings' and 'has_warnings' keys
  - Legacy os_warning and rename_warning banner blocks removed
  - evaluate_warnings wired into main.py pipeline before render_html
affects:
  - phase 08 (NinjaOne): renderer pipeline established; main.py pipeline pattern set
  - future renderer plans: warnings-box CSS pattern available

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Jinja2 selectattr filter for counting WARN-severity items in template"
    - "HTML <details>/<summary> pattern for collapsible section-card"
    - "badge-warn class using CSS var(--amber) consistent with existing badge system"

key-files:
  created: []
  modified:
    - renderer/__init__.py
    - renderer/templates/character_sheet.html
    - main.py

key-decisions:
  - "Warnings box uses <details open> auto-expand when has_warnings is true — no JS required"
  - "has_warnings computed in _build_context() from report.warnings — pure Python, no template logic"
  - "evaluate_warnings placed after collect_all and before render_html in main.py pipeline"

patterns-established:
  - "Warning pipeline: evaluate_warnings(report) -> report.warnings -> _build_context() -> template"
  - "<details class='section-card warnings-box'> as collapsible card pattern"

requirements-completed:
  - WARN-03

# Metrics
duration: 2min
completed: "2026-05-07"
---

# Phase 7 Plan 02: HTML Warnings Section Summary

**Warning pipeline wired end-to-end: evaluate_warnings() -> report.warnings -> _build_context() -> collapsible Jinja2 warnings box in character_sheet.html, replacing two ad-hoc banner flags**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-07T21:06:46Z
- **Completed:** 2026-05-07T21:08:25Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Removed `os_warning` and `rename_warning` pre-computation blocks and dict keys from `_build_context()`
- Added `'warnings': report.warnings` and `'has_warnings': any(w.severity == 'WARN' ...)` to `_build_context()` return dict
- Added `.badge-warn { background: var(--amber); }` CSS rule to character_sheet.html
- Replaced two flat warning banner divs with a collapsible `<details class="section-card warnings-box">` element that auto-opens when warnings exist
- Wired `from health_checks import evaluate_warnings` and `report.warnings = evaluate_warnings(report)` into main.py before `render_html()`
- All 32 existing renderer tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove legacy warning keys, add warnings pipeline to _build_context** - `6371f3e` (refactor)
2. **Task 2: Add collapsible warnings box to character_sheet.html** - `6d6d67c` (feat)
3. **Task 3: Wire evaluate_warnings into main.py before render_html** - `3e7cb46` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `renderer/__init__.py` — removed os_warning/rename_warning blocks; added warnings/has_warnings to _build_context return dict
- `renderer/templates/character_sheet.html` — added .badge-warn CSS; replaced old banners with collapsible warnings-box details element
- `main.py` — added health_checks import and evaluate_warnings assignment in pipeline

## Decisions Made

- Warnings box uses `<details open>` auto-expand when `has_warnings` is true — no JavaScript required, pure HTML/CSS
- `has_warnings` computed in `_build_context()` (not template) — keeps template logic-free per D-12 pattern
- `evaluate_warnings` placed between collector warning print loop and `print("Rendering character sheet...")` — all collectors have run by that point

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Warning pipeline is fully wired: Phase 6 evaluate_warnings -> Phase 7 HTML rendering
- WARN-03 requirement fully satisfied
- Phase 7 Plan 03 (if any) or next phase can proceed — renderer and main.py pipeline are stable
- Threat T-07-02-01 (XSS): Jinja2 autoescape=True already enforced in Environment constructor; Warning strings are auto-escaped

---
*Phase: 07-html-warnings-section*
*Completed: 2026-05-07*
