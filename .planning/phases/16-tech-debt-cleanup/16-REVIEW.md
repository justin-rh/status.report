---
phase: 16-tech-debt-cleanup
reviewed: 2026-05-19T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - main.py
  - renderer/__init__.py
  - tests/test_renderer.py
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-05-19
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found (3 info-level items — no blockers)

## Summary

Three files were reviewed as part of the Phase 16 tech debt cleanup: the entry point (`main.py`), the HTML renderer (`renderer/__init__.py`), and the renderer unit tests (`tests/test_renderer.py`).

The cleanup work itself is correct. Dead `writers/` package removal, dead `render_report()` deletion, wasted collector calls removed from `_run_cli()`, and the new `--app` + `--output` stderr warning in `main()` are all implemented cleanly with no logic errors or security issues.

Three minor info-level items were found — all are stale comments or misleading names left behind by the cleanup. None affect runtime behavior or test reliability.

---

## Info

### IN-01: Stale docstring in `render_html` references deleted `render_report()`

**File:** `renderer/__init__.py:51-56`
**Issue:** The docstring for `render_html()` reads "render_report() is unchanged — no breakage to existing 94 tests." `render_report()` was deleted in Phase 16, making this sentence both false and confusing to future readers.
**Fix:** Replace the stale sentence with a description of the current state:
```python
def render_html(report: AuditReport) -> str:
    """Return rendered HTML string without writing to disk.

    main.py calls this to get the HTML string, then writes it directly to the
    dynamically-named output path (D-02/D-03: {date}_scry_{hostname}.html).
    """
```

---

### IN-02: Unreachable `return` after `sys.exit(0)` call in `main()`

**File:** `main.py:176`
**Issue:** `_run_cli_app(args)` always terminates via `sys.exit(0)` (see `main.py:153`). The `return` on line 176 is unreachable. The same pattern exists at line 182 after `_run_cli(args)` (which exits at line 90). Both are harmless but create a misleading impression that control could fall through.
**Fix:** Remove both trailing `return` statements — the `if args.app:` and `if cli_mode and not args.json:` blocks are self-contained exit paths:
```python
    if args.app:
        if args.output:
            print("WARNING: --output is ignored in --app mode", file=sys.stderr)
        _run_cli_app(args)
        # no return needed — _run_cli_app calls sys.exit(0)

    cli_mode = args.name or args.serial or args.warnings
    if cli_mode and not args.json:
        _run_cli(args)
        # no return needed — _run_cli calls sys.exit(0)
```

---

### IN-03: Test function name references deleted `render_report()` function

**File:** `tests/test_renderer.py:186`
**Issue:** `test_render_report_no_old_warning_banners` has "render_report" in its name, but `render_report()` was deleted in Phase 16. The test body calls `_build_context` directly and is still valid — only the name is stale.
**Fix:** Rename to match what it actually tests:
```python
def test_build_context_no_old_warning_banners():
```

---

_Reviewed: 2026-05-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
