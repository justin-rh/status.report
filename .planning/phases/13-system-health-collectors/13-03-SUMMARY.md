---
phase: 13-system-health-collectors
plan: 03
subsystem: renderer
tags: [python, jinja2, html, tdd, uptime, pending-updates, badge]

# Dependency graph
requires:
  - phase: 13-01
    provides: AuditReport.uptime_seconds, AuditReport.pending_updates, Warning.level
  - phase: 13-02
    provides: UPTIME_WARN_DAYS/UPTIME_STALE_DAYS constants, _check_uptime() with level='yellow'/'red'

provides:
  - _format_uptime() nested helper in _build_context() with singular/plural days/hours/minutes
  - uptime_display key in _build_context() return dict (formatted string or None)
  - pending_updates_display key in _build_context() return dict ('N pending' or 'N/A')
  - System Health stat block section in character_sheet.html (Uptime + Pending Updates rows)
  - badge-critical CSS class in character_sheet.html
  - Level-aware warning badge span (level='red' -> badge-critical, else badge-warn/badge-installed)
  - 5 new hardware collector tests (uptime populates, uptime degrades, WUA skipped, WUA mock count, WUA degrades)

affects:
  - HTML output: IT staff now sees Uptime and Pending Updates in the stat block
  - HTML output: UPTIME_STALE warnings render with red badge-critical background

# Tech tracking
tech-stack:
  added: []
  patterns:
    - _format_uptime nested helper inside _build_context — local to function, not module-level
    - pending_updates_display uses None-check (not falsy) to distinguish 0 from absent
    - Jinja2 muted class: uptime uses 'is none' test; pending_updates uses string equality 'N/A'
    - badge level-aware nesting: outer severity check, inner level check for critical vs warn

key-files:
  created:
    - tests/test_renderer_phase13.py
  modified:
    - renderer/__init__.py
    - renderer/templates/character_sheet.html
    - tests/test_hardware_collector.py

key-decisions:
  - "_format_uptime defined as nested function inside _build_context — scoped to its use site, not a module-level utility; mirrors existing pattern of helper logic inline"
  - "pending_updates_display uses explicit None check (not falsy) — pending_updates=0 must produce '0 pending', not 'N/A'"
  - "Jinja2 muted condition uses 'is none' for uptime_display (None object) vs string equality '== N/A' for pending_updates_display (always a string)"
  - "badge-critical placed immediately after badge-warn in CSS — visual proximity signals semantic relationship"
  - "Hardware collector tests for Phase 13 pass immediately — implementation already complete from Plan 01; tests serve as explicit verification contract"

# Metrics
duration: 11min
completed: 2026-05-18
---

# Phase 13 Plan 03: System Health Renderer and Template Summary

**Jinja2 _format_uptime() helper, uptime/pending_updates display in _build_context(), System Health stat rows in character sheet, badge-critical CSS, level-aware warning badge, and 5 hardware collector tests**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-05-18T19:00:32Z
- **Completed:** 2026-05-18T19:11:20Z
- **Tasks:** 2 (both TDD — 4 commits total)
- **Files modified:** 3 (renderer/__init__.py, character_sheet.html, tests/test_hardware_collector.py) + 1 test file created

## Accomplishments

- Added `_format_uptime(seconds: int) -> str` nested helper inside `_build_context()` with correct singular/plural handling for days/hours/minutes; handles 0 seconds (returns "0 minutes") — T-13-11 mitigation
- Added `uptime_display` and `pending_updates_display` keys to `_build_context()` return dict; both None-safe using explicit `is not None` check to distinguish `pending_updates=0` from absent
- Added `<!-- System Health — Phase 13 -->` section with Uptime and Pending Updates stat rows after the Other Profiles row in the stat-grid; muted class applied when `uptime_display is none` or `pending_updates_display == 'N/A'`
- Added `.badge-critical { background: var(--red); color: #fff; }` CSS class immediately after `.badge-warn`
- Updated warning badge `<span>` to level-aware markup: `level='red'` → `badge-critical`, other WARN → `badge-warn`, OK → `badge-installed`
- Added 5 hardware collector tests covering uptime population, psutil degradation, WUA COM skip/mock/error paths; all pass (implementation present from Plan 01)
- Full test suite: 256 tests passing (up from 238 after Plan 02, +18: 13 renderer phase13 + 5 hardware collector)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing renderer uptime/pending_updates tests** — `0825adc` (test)
2. **Task 1 GREEN: _format_uptime helper and display keys in _build_context** — `877cce8` (feat)
3. **Task 2 test: Hardware collector Phase 13 tests** — `a963591` (test)
4. **Task 2 feat: System Health rows, badge-critical, level-aware badge** — `bc49d76` (feat)

## TDD Gate Compliance

Task 1 followed full RED/GREEN cycle:
- Task 1 RED: `test(13-03)` commit `0825adc` — 13 tests fail (KeyError: 'uptime_display')
- Task 1 GREEN: `feat(13-03)` commit `877cce8` — all 13 tests pass

Task 2 hardware collector tests passed immediately (Plan 01 implementation already covers all paths). Test commit `a963591` serves as explicit verification contract for the Plan 01 collector work. Template changes committed as `bc49d76` — no separate RED/GREEN needed for HTML changes (template is not test-driven; verified via smoke tests).

## Files Created/Modified

- `renderer/__init__.py` — `_format_uptime()` nested helper added inside `_build_context()`; `uptime_display` and `pending_updates_display` computed and added to return dict
- `renderer/templates/character_sheet.html` — `.badge-critical` CSS class added after `.badge-warn`; System Health section with Uptime/Pending Updates stat rows inserted after Other Profiles row; warning badge span updated to level-aware nested conditionals
- `tests/test_renderer_phase13.py` — 13 tests for `_build_context()` uptime/pending_updates display (created)
- `tests/test_hardware_collector.py` — 5 Phase 13 tests added: `test_collect_uptime_populates_uptime_seconds`, `test_collect_uptime_degrades_on_psutil_error`, `test_collect_pending_updates_skipped_when_win32com_unavailable`, `test_collect_pending_updates_populates_count_when_com_available`, `test_collect_pending_updates_degrades_on_com_error`

## Decisions Made

- `_format_uptime` defined as a nested function inside `_build_context()` rather than a module-level helper. It is only needed in one place and is too specific to be reused. This keeps `renderer/__init__.py` clean.
- `pending_updates_display` uses an explicit `is not None` check: `pending_updates=0` means "zero pending updates" (a meaningful value) and must produce `"0 pending"`, not `"N/A"`. A falsy check would incorrectly treat 0 as absent.
- The Jinja2 muted condition uses `is none` for `uptime_display` (a Python None object rendered as Jinja2 `none`) but string equality `== 'N/A'` for `pending_updates_display` (always a string — never None in context).

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

- Hardware collector tests (Task 2) passed immediately on first run. The Plan 01 implementation of `collect_pending_updates()` and `_collect_uptime()` already satisfies all 5 test contracts. This is expected — Plan 01 was designed to provide these exact behaviors.

## Known Stubs

None — `uptime_display` and `pending_updates_display` are fully wired from `report.uptime_seconds` and `report.pending_updates`, which are populated by `_collect_uptime()` and `collect_pending_updates()` (Plan 01). The template renders real values on live Windows runs; `None`/`"N/A"` display is the intentional degraded state for CI or standard-user runs.

## Threat Flags

No new threat surface introduced. T-13-09, T-13-10, T-13-11 from the plan threat model are all `accept` disposition — `autoescape=True` in the Jinja2 Environment covers T-13-09/T-13-10; the `_format_uptime(0)` → "0 minutes" path covers T-13-11 (no division by zero; verified in `test_build_context_uptime_display_zero_seconds`).

## Self-Check: PASSED

- `renderer/__init__.py` contains `def _format_uptime` and `uptime_display` in return dict
- `renderer/templates/character_sheet.html` contains `badge-critical`, `stat-label">Uptime</div>`, `stat-label">Pending Updates</div>`
- `tests/test_renderer_phase13.py` exists with 13 tests
- `tests/test_hardware_collector.py` contains all 5 new Phase 13 test functions
- Commits `0825adc`, `877cce8`, `a963591`, `bc49d76` all present in git log
- 256 tests passing, 0 failures
