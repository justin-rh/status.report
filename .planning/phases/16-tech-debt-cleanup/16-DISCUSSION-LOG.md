# Phase 16: Tech Debt Cleanup — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-19
**Phase:** 16-tech-debt-cleanup
**Areas discussed:** render_report() fate, --app/--output warning behavior, Test cleanup strategy

---

## render_report() fate

| Option | Description | Selected |
|--------|-------------|----------|
| Remove it entirely | Delete writers/ module, remove render_report() from renderer, delete test_writers.py + the ~15 render_report tests in test_renderer.py. Cleanest result — no dead functions remain. | ✓ |
| Keep render_report(), just break the writers dependency | Replace the write_html() call inside render_report() with direct write_text() logic. Writers module deleted, but render_report() survives (still dead, but preserved). | |

**User's choice:** Remove it entirely
**Notes:** render_report() is dead code — main.py never calls it, only render_html(). Full removal is the correct cleanup.

---

## --app/--output warning behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Warn and continue | Print warning, then run the app-query normally. --output is ignored after the warning. | ✓ |
| Warn and exit with error | Print warning to stderr and exit non-zero. Could break scripts that pass --output unconditionally. | |

**User's choice:** Warn and continue
**Notes:** Consistent with REQUIREMENTS.md success criteria phrasing — "prints a warning… rather than silently discarding."

---

## Test cleanup strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Delete outright | _build_context() logic already covered by render_html() tests and phase-specific renderer test files. No coverage gap expected. | ✓ |
| Migrate to render_html() | Convert each render_report() test to call render_html() instead. More work, preserves test intent. | |

**User's choice:** Delete outright
**Notes:** Coverage of _build_context() is maintained by render_html() tests and test_renderer_phase13.py / test_renderer_phase14.py.

---

## Claude's Discretion

- Exact wording of the DEBT-03 stderr warning message

## Deferred Ideas

None
