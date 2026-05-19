# Phase 16: Tech Debt Cleanup — Context

**Gathered:** 2026-05-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove three specific pieces of dead code and silent misbehaviors from the existing codebase. No new features. All three items have concrete, verifiable success criteria defined in REQUIREMENTS.md (DEBT-01, DEBT-02, DEBT-03).

</domain>

<decisions>
## Implementation Decisions

### DEBT-01: Remove writers.write_html and its call path

- **D-01:** Remove `writers/` package entirely (`writers/__init__.py` and the directory).
- **D-02:** Remove `render_report()` from `renderer/__init__.py` entirely — it is the only caller of `write_html`, and it is itself dead code (`main.py` never calls it; `main.py` only calls `render_html()`). The `from writers import write_html` import at the top of `renderer/__init__.py` is also removed.
- **D-03:** `render_html()` in `renderer/__init__.py` is live code — it is called by `main.py` and must be preserved untouched.
- **D-04:** Delete `tests/test_writers.py` entirely (6 tests — all test the dead `write_html` function).
- **D-05:** Delete the `render_report()` tests and the direct `write_html` import tests from `tests/test_renderer.py` outright — do NOT migrate them to use `render_html()`. Rationale: `_build_context()` logic is already covered by `render_html()` tests and the phase-specific renderer test files (`test_renderer_phase13.py`, `test_renderer_phase14.py`). No coverage gap is expected.

### DEBT-02: Remove wasted collector calls from _run_cli

- **D-06:** In `_run_cli()` in `main.py` (lines 58–62), remove the entire `if args.updates and sys.platform != "darwin":` block that calls `collect_pending_updates` and `collect_vendor_updates`. These results are never used in the `--name`/`--serial`/`--warnings` output path — `evaluate_warnings()` only checks OS version, disk space, rename, and uptime; it does not use update data.
- **D-07:** The identical `--updates` block in `main()` (full pipeline, lines 201–205) is **not touched** — that is live code used when SCRY runs the full audit.
- **D-08:** No test changes needed for DEBT-02 — any existing CLI tests that verify `--updates` in full-pipeline mode are unaffected.

### DEBT-03: --app + --output conflict warning

- **D-09:** When `args.app` is set AND `args.output` is also set, print a warning to `sys.stderr` immediately before routing to `_run_cli_app()` in `main()`. After printing the warning, execution continues normally into app-query mode — `--output` is silently ignored.
- **D-10:** Warning placement is in `main()`, not inside `_run_cli_app()`, so the routing logic stays co-located. Suggested text: `"WARNING: --output is ignored in --app mode"` (exact wording left to planner's discretion per this decision).
- **D-11:** The warning must be absent when `--output` is used without `--app` (success criteria 3).

### Claude's Discretion

- Exact wording of the DEBT-03 stderr warning message (as long as it clearly states `--output` is ignored in app/app-query mode).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Tech Debt (DEBT) — DEBT-01, DEBT-02, DEBT-03 requirements and success criteria

### Source files being modified
- `main.py` — `_run_cli()` (DEBT-02 fix), `main()` routing (DEBT-03 warning)
- `renderer/__init__.py` — remove `render_report()` and `write_html` import (DEBT-01)
- `writers/__init__.py` — delete entirely (DEBT-01)

### Test files being modified/deleted
- `tests/test_writers.py` — delete entirely (DEBT-01)
- `tests/test_renderer.py` — remove `render_report()` tests and direct `write_html` tests (DEBT-01)

No external ADRs or specs — all requirements fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `render_html()` in `renderer/__init__.py`: the live render function — untouched by this phase
- `_build_context()` in `renderer/__init__.py`: private helper — untouched, but its coverage is maintained via existing `render_html()` tests

### Established Patterns
- Dead code removal: delete the dead function + its tests together (no migration, no compatibility shims)
- stderr warnings in main.py: use `print(..., file=sys.stderr)` — consistent with existing `print("[WARN] {err}")` pattern for collection errors

### Integration Points
- `renderer/__init__.py` public surface narrows from two functions (`render_report`, `render_html`) to one (`render_html`). No callers outside of `main.py` and the test suite.
- `writers/` package has no other importers beyond `renderer/__init__.py` — confirmed by grep.
- `_run_cli_app()` signature is unchanged; the warning is emitted by the caller (`main()`) before invoking it.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond what the success criteria define — open to standard implementation approaches for each fix.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 16-tech-debt-cleanup*
*Context gathered: 2026-05-19*
