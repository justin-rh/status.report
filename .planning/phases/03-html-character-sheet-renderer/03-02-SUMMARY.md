---
phase: 03-html-character-sheet-renderer
plan: "02"
subsystem: output
tags: [jinja2, python, html, css, pytest, tdd, renderer, character-sheet]

# Dependency graph
requires:
  - phase: 03-html-character-sheet-renderer
    provides: write_html() from writers/__init__.py, jinja2==3.1.6 installed (03-01)
  - phase: 02-system-collectors
    provides: AuditReport dataclass with all hardware/app fields, graceful None degradation pattern

provides:
  - renderer/__init__.py exposing render_report(report: AuditReport, output_path: Path) -> Path
  - renderer/templates/character_sheet.html — self-contained D&D-styled dark-panel Jinja2 template
  - tests/test_renderer.py — 23 pytest tests covering all renderer/writers behavior
  - tests/test_renderer_helpers.py — 9 TDD RED/GREEN gate tests for _build_context helpers

affects:
  - 05-packaging (renderer package must be included in PyInstaller spec; templates/ dir must bundle)
  - main.py wiring phase (calls render_report(report, Path(sys.executable).parent))

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Jinja2 default('—', true) required for Python None — default() alone only replaces Undefined"
    - "ir.files('renderer').joinpath('templates/character_sheet.html') — single-string joinpath for importlib.resources"
    - "Environment(autoescape=True) with env.from_string() — no PackageLoader, no FileSystemLoader"
    - "_build_context() pre-processes all None fields; template stays logic-free"
    - "Falsy guard `if report.disk_total_gb and report.disk_free_gb is not None` handles both None and 0.0"

key-files:
  created:
    - renderer/__init__.py
    - renderer/templates/character_sheet.html
    - tests/test_renderer.py
    - tests/test_renderer_helpers.py
  modified: []

key-decisions:
  - "Jinja2 default filter requires boolean=True arg to replace Python None: {{ x | default('—', true) }}"
  - "Template uses CSS custom properties for all UI-SPEC colors — no inline styles except HP bar width"
  - "HP bar None guard: `if report.disk_total_gb` catches both None and 0.0 (D-13 / Pitfall 3)"
  - "TDD RED commit written for _build_context tests before implementation; GREEN followed immediately"
  - "test_renderer_helpers.py retained alongside test_renderer.py as TDD gate artifact"

patterns-established:
  - "renderer package follows collectors/ service module pattern: module docstring, one public function, private helpers"
  - "importlib.resources.files() over PackageLoader — PyInstaller-safe, works in --onedir bundles"
  - "All nullable display values pre-computed in _build_context(); template receives ready-to-render strings or None"

requirements-completed:
  - OUT-01
  - OUT-02

# Metrics
duration: 5min
completed: 2026-05-04
---

# Phase 3 Plan 02: HTML Character Sheet Renderer Summary

**Jinja2 renderer with dark-panel D&D character sheet template — renders AuditReport to status_report.html with HP bar, app equipment table, and quest status footer; all 85 tests passing**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-04T23:19:57Z
- **Completed:** 2026-05-04T23:24:47Z
- **Tasks:** 3 (Task 1: renderer/__init__.py TDD; Task 2: character_sheet.html; Task 3: full test suite)
- **Files modified:** 4 created (renderer/__init__.py, renderer/templates/character_sheet.html, tests/test_renderer.py, tests/test_renderer_helpers.py)

## Accomplishments

- Implemented `render_report(report, output_path)` with `_load_template_source()` and `_build_context()` helpers — importlib.resources loading, autoescape=True, all None fields pre-processed
- Built complete self-contained D&D character sheet template: dark navy palette, HP bar with hp-green/hp-amber/hp-red/hp-none classes, equipment table with installed/missing badges, QUEST COMPLETE/INCOMPLETE banner
- Wrote 23-test pytest suite covering all logic paths: 11 `_build_context` unit tests, 7 `render_report` integration tests, 2 `write_html` tests, 2 template loading tests, 1 no-raise guarantee
- Auto-fixed Rule 1 bug: `| default('—')` doesn't replace Python `None` in Jinja2 — changed to `| default('—', true)` throughout template

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for renderer helpers** - `43623ce` (test)
2. **Task 1 GREEN: Implement renderer/__init__.py** - `d57ce03` (feat)
3. **Task 2: Build full Jinja2 character sheet template** - `c9bb3e1` (feat)
4. **Task 3: Full test suite + Jinja2 default filter bug fix** - `b633edd` (feat)

_Note: Task 1 TDD has 2 commits (RED gate → GREEN gate). Task 3 includes Rule 1 auto-fix to the template (default filter)._

## Files Created/Modified

- `renderer/__init__.py` — `render_report()`, `_load_template_source()`, `_build_context()` — 98 lines, ir.files() pattern, autoescape=True
- `renderer/templates/character_sheet.html` — 10KB self-contained Jinja2 template: CSS custom properties, HP bar, equipment table, quest banner, chronicle
- `tests/test_renderer.py` — 23 pytest tests: full coverage of _build_context logic, render_report integration, write_html, no-raise guarantee
- `tests/test_renderer_helpers.py` — 9 TDD RED/GREEN gate tests for Task 1 (retained as artifact)

## Decisions Made

- `| default('—', true)` not `| default('—')` — Jinja2's `default()` filter without boolean=True only replaces `Undefined` (template variable not passed), not Python `None`. Since `_build_context()` passes explicit `None` for absent fields, `true` is required.
- Template-level `{% if station is none %}` (not `{% if not station %}`) for station number — avoids false muted class when station=0
- TDD intermediate test file (`test_renderer_helpers.py`) retained to preserve the TDD gate commit history

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Jinja2 default filter doesn't replace Python None without boolean=True**
- **Found during:** Task 3 (test_render_report_none_cpu_model_renders_emdash failed)
- **Issue:** `{{ cpu_model | default('—') }}` rendered the string `'None'` in the HTML when `cpu_model=None`, instead of the em-dash. Jinja2's `default()` filter without `boolean=True` only replaces `Undefined`, not Python `None`.
- **Fix:** Changed all nullable field default filters in `character_sheet.html` from `| default('—')` to `| default('—', true)` — applies to device_type, city, guild, station, cpu_model, ram_display, disk_total_display, disk_label, os_combined, current_user
- **Files modified:** `renderer/templates/character_sheet.html`
- **Verification:** `test_render_report_none_cpu_model_renders_emdash` passes; string `>None<` not present in rendered HTML
- **Committed in:** `b633edd` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in template None handling)
**Impact on plan:** Fix is required for correctness — D-12 mandates em-dash for None fields. Without it, "None" would appear as literal text in the character sheet. No scope creep.

## Issues Encountered

Pre-existing `psutil`/`wmi` not installed in venv caused 21 failures in `test_hardware_collector.py` and `test_profile_collector.py` during full regression run. Resolved by running `.venv/Scripts/pip install -r requirements.txt` (same root cause documented in 03-01 SUMMARY). After install, all 85 tests pass.

## Known Stubs

None — `render_report()` uses the real template and real `write_html()`. All context dict fields are wired to real `AuditReport` fields. No hardcoded values or placeholder text.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. All threat mitigations from the plan's threat model are implemented:
- T-03-02-01 (XSS): `Environment(autoescape=True)` confirmed in `renderer/__init__.py`
- T-03-02-02 through T-03-02-05: Accepted risks as specified

## Next Phase Readiness

- Phase 3 is complete — both plans (03-01 and 03-02) done
- Phase 4 (app detection via winreg) is fully unblocked: `render_report()` accepts `AuditReport.apps` list as-is
- Phase 5 (packaging): `renderer/templates/` directory must be included in PyInstaller spec — templates are plain files in the package, not inside `__pycache__`

---
*Phase: 03-html-character-sheet-renderer*
*Completed: 2026-05-04*
