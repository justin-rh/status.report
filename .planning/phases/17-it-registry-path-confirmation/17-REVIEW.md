---
phase: 17-it-registry-path-confirmation
reviewed: 2026-05-20T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - collectors/windows/vendor.py
  - main.py
  - tests/test_vendor_collector.py
  - tests/test_cli_phase17.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-05-20
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Four files reviewed for Phase 17 (IT Registry Path Confirmation). The code is well-structured and follows the project's established patterns — `CollectionResult` envelope discipline is maintained, the `--diag-vendor` short-circuit is correctly placed before `--app` in dispatch order, and all 4 registry hives are enumerated. Two warnings and three info items were found; no critical issues.

The primary warnings concern a patch-target mismatch in a test (the `diag_vendor_paths` function uses `vendor_mod.winreg` directly but some tests patch `apps_mod.winreg`) and a silent data loss risk when `report.apps` is empty after `_detect_one_app` is called.

---

## Warnings

### WR-01: Inconsistent winreg patch target across `TestDiagVendorPaths` tests

**File:** `tests/test_vendor_collector.py:169-332`

**Issue:** `diag_vendor_paths()` in `vendor.py` walks `UNINSTALL_PATHS` and calls `winreg.OpenKey` via its **own** module-level `winreg` import (`vendor_mod.winreg`). Tests 1, 4, 5, 6, 7, and 8 patch `apps_mod.winreg.OpenKey`, which does NOT intercept the calls made inside `diag_vendor_paths`. Only Test 3 correctly patches `vendor_mod.winreg`. As a result, tests 1/4/5/6/7/8 in `TestDiagVendorPaths` silently attempt real registry calls during CI (on Windows they may pass coincidentally; on non-Windows they may silently skip hives via `OSError`). The tests pass today because the `OSError` fallback prints `[note] hive unreadable — skipped`, which is exactly what the patched error would produce — but the patch is not doing what the test author intended.

**Fix:** Change the patch target from `apps_mod.winreg` to `vendor_mod.winreg` in all `TestDiagVendorPaths` tests that need it (matching the correct pattern already used in `test_discovery_property_unknown_lenovo_entry`):

```python
# Wrong (tests 1, 4, 5, 6, 7, 8):
with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no key")):

# Correct:
with patch.object(vendor_mod.winreg, "OpenKey", side_effect=OSError("no key")):
```

---

### WR-02: `_run_cli_app` accesses `report.apps[0]` without length guard

**File:** `main.py:166`

**Issue:** After calling `_detect_one_app(spec, report)`, the code immediately dereferences `report.apps[0]`. `_detect_one_app` is documented to never raise (D-16), but the `except Exception` block that wraps it only appends to `report.apps` if an exception is actually caught. If `_detect_one_app` returns without raising **and** without appending to `report.apps` (a contract violation, but possible if the function has a silent early-return bug), the `report.apps[0]` access will raise an uncaught `IndexError` and crash the process with an unformatted traceback rather than a clean error message.

**Fix:** Guard the access with a length check and exit cleanly:

```python
if not report.apps:
    print(f"[ERROR] App detection returned no result for {spec['name']}", file=sys.stderr)
    sys.exit(1)
app_status = report.apps[0]
```

---

## Info

### IN-01: `_hive_label` in `diag_vendor_paths` silently returns wrong label for HKCU Wow6432Node path

**File:** `collectors/windows/vendor.py:119-123`

**Issue:** `_hive_label` checks `"WOW6432Node" in path` (capital W, capital N) but the constant in `UNINSTALL_PATHS` (imported from `apps.py`) uses `"WOW6432Node"` — which matches. However, the label printed is `HKCU\Wow6432Node` with lowercase 'ow6432' while the string test uses `"WOW6432Node"`. This is cosmetic today but would produce a wrong label if a hive path ever uses `"Wow6432Node"` vs `"WOW6432Node"`. A direct comparison against the known path constants would be more defensive.

**Fix:** Minimal — document the casing dependency with an inline comment, or compare against the literal path strings from `UNINSTALL_PATHS` directly.

---

### IN-02: `test_lsu_keyword_list_has_phase17_comment_block` reads source via filesystem path construction

**File:** `tests/test_vendor_collector.py:333-354`

**Issue:** Test 9 reconstructs the path to `vendor.py` using `os.path.dirname(__file__)` string manipulation. This is fragile if the test file is ever moved or the package layout changes. It also opens the file with a raw `open()` rather than using `importlib.resources` or `inspect.getsource()`.

**Fix:** Use `inspect.getsource` for robustness:

```python
import inspect
import collectors.windows.vendor as vendor_mod
source = inspect.getsource(vendor_mod)
```

---

### IN-03: `collect_vendor_updates` is only invoked when `--updates` is passed but `AuditReport.dell_dcu` and `lenovo_lsu` default to `None`

**File:** `main.py:234-238`, `models.py:90-91`

**Issue:** When `--updates` is not passed, `report.dell_dcu` and `report.lenovo_lsu` remain `None`. Any downstream consumer (renderer, health checks) that accesses these fields must guard against `None`. This is by design per D-04, but there is no `Optional` annotation callout or docstring note in `collect_vendor_updates` warning callers of this "only populated when opted-in" contract. A future health-check author adding a vendor-update check could silently skip it for the majority of runs without realizing.

**Fix:** Add a one-line docstring note to `AuditReport.dell_dcu`/`lenovo_lsu` fields and to `collect_vendor_updates` clarifying the opt-in nature:

```python
dell_dcu: VendorUpdateStatus | None = None    # D-02 (Phase 14); None unless --updates passed
lenovo_lsu: VendorUpdateStatus | None = None  # D-02 (Phase 14); None unless --updates passed
```

---

_Reviewed: 2026-05-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
