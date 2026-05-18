---
phase: 14-vendor-update-detection
reviewed: 2026-05-18T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - collectors/windows/vendor.py
  - main.py
  - models.py
  - renderer/__init__.py
  - renderer/templates/character_sheet.html
  - tests/test_models_phase14.py
  - tests/test_renderer_phase14.py
  - tests/test_vendor_collector.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-05-18
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 14 adds vendor update detection for Dell Command Update (DCU) and Lenovo System Update (LSU). The overall design is sound: the collector never raises across the layer boundary, the model is a clean data class, and the renderer correctly gates display on `None`. Three logic issues were found, none of which are crashes, but two produce incorrect display strings in reachable states. Two minor test coverage gaps round out the findings.

---

## Warnings

### WR-01: LSU collection error silently displays "Not installed"

**File:** `renderer/__init__.py:185`

**Issue:** The `lenovo_lsu_display` computation uses `not lsu.installed` as its sole branch condition. In Python, `not None` evaluates to `True`, so `installed=None` (collection error) produces the string `"Not installed"` — the same string as a confirmed registry miss. This misrepresents a collection failure as a definitive absence, which can mislead users auditing Lenovo machines when the registry read errors out.

The DCU path (lines 169-179) handles this correctly with an explicit two-branch cascade. LSU does not.

**Fix:**
```python
# renderer/__init__.py  ~line 183
if report.lenovo_lsu is not None:
    lsu = report.lenovo_lsu
    if lsu.installed is None:
        lenovo_lsu_display: str | None = "Unknown (error)"
    elif not lsu.installed:
        lenovo_lsu_display = "Not installed"
    else:
        lenovo_lsu_display = "N/A"
else:
    lenovo_lsu_display = None
```

---

### WR-02: DCU "Unknown (no scan data)" label shown for two distinct states

**File:** `renderer/__init__.py:173-176`

**Issue:** Lines 172-176 emit `"Unknown (no scan data)"` for both:
- `scan_data_present=False` (XML file was never written — DCU hasn't run a scan yet)
- `scan_data_present=True, pending_count=None` (XML present but malformed — parse error)

These are different situations. A user seeing "Unknown (no scan data)" when the XML actually exists but is corrupt has no way to know a parse error occurred. The comment on line 175 ("still show as unknown") acknowledges this is intentional, but the label is misleading for the second case.

**Fix:** Use a distinct label for the parse-error branch:
```python
elif dcu.pending_count is None:
    # scan_data_present=True but XML was malformed
    dell_dcu_display = "Unknown (parse error)"
```

If the spec explicitly requires identical labels, add a comment in `vendor.py` at line 48 noting that `scan_data_present=True, pending_count=None` is the parse-error sentinel, so the distinction is preserved at the model level even if collapsed in display.

---

### WR-03: `--updates` flag is silently ignored when `--name` or `--serial` is passed without `--warnings`

**File:** `main.py:43-60`

**Issue:** In `_run_cli()`, the `needs_full` path is the only branch that respects `args.updates` (line 56). If the user runs `scry --updates --serial`, `needs_full` is `False` and `needs_hardware` is `True`, so the vendor collector is never invoked. No error or warning is printed. The `--updates` flag silently has no effect in this combination.

This is a logic gap in the CLI flag union semantics described in the docstring: "combined flags: union of required collection." The union is incomplete for the `--updates` + `--serial` and `--updates` + `--name` combinations.

**Fix:** Two options:
1. Force `needs_full = args.warnings or args.updates` so vendor collection is always triggered when `--updates` is present, regardless of other flags.
2. Add a guard at the top of `_run_cli()`:
```python
if args.updates and not args.warnings:
    # --updates only makes sense with --warnings in CLI mode; ignore silently
    # or print a note: print("[INFO] --updates has no effect without --warnings in CLI mode")
    pass
```

Either way, the behavior should be documented or the silent no-op should be eliminated. Option 1 is safer because it matches user intent.

---

## Info

### IN-01: No test for LSU collection error path (`installed=None`) in renderer tests

**File:** `tests/test_renderer_phase14.py`

**Issue:** `TestVendorDisplayValues` covers `lenovo_lsu` for `installed=False` and `installed=True` but has no test for `installed=None` (collection error state). Given that WR-01 above shows the current implementation gets this state wrong, a test would have caught the bug at the RED phase.

**Fix:** Add a test case:
```python
def test_lenovo_lsu_error_state_shows_unknown(self):
    report = _make_report(
        lenovo_lsu=VendorUpdateStatus(installed=None, pending_count=None, scan_data_present=False)
    )
    ctx = _build_context(report)
    assert ctx["lenovo_lsu_display"] == "Unknown (error)"
```

---

### IN-02: No test verifying LSU collection errors are appended to `collection_errors`

**File:** `tests/test_vendor_collector.py`

**Issue:** `test_appends_to_collection_errors_on_exception` (line 158) only asserts that a `"DCU"` string appears in `collection_errors`. There is no corresponding assertion that an LSU failure also appends an error. If `_detect_lsu` were to silently swallow its exception, the test suite would not catch it.

**Fix:** Extend the existing test or add a new one:
```python
def test_appends_lsu_error_to_collection_errors_on_exception(self):
    # Simulate _detect_lsu raising by making winreg fail only on the second call
    call_count = {"n": 0}
    def flaky_open_key(*args, **kwargs):
        call_count["n"] += 1
        raise RuntimeError("flaky")
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=flaky_open_key):
        report = make_report()
        vendor_mod.collect_vendor_updates(report)
    assert any("LSU" in e for e in report.collection_errors)
```

---

_Reviewed: 2026-05-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
