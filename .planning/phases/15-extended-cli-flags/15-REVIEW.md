---
phase: 15-extended-cli-flags
reviewed: 2026-05-18T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - main.py
  - tests/test_cli_phase15.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 15: Code Review Report

**Reviewed:** 2026-05-18
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Phase 15 added `--json`, `--output PATH`, and `--app NAME` flags to `main.py`. The implementation is generally sound: the dispatch order (app-mode first, then cli-mode, then full pipeline) is correct, error handling is consistent with the project's no-raise contract, and the `--json` override of targeted flags is intentional and correctly implemented.

Two warnings require attention before shipping. First, `_run_cli_app` unconditionally indexes `report.apps[0]` after calling `_detect_one_app`, but nothing guarantees the app was actually appended — if the collector silently returns without mutating `report.apps` (a valid behavior under the project's no-raise contract), this is an `IndexError` crash. Second, the `--output` path is accepted from the command line and passed directly to `Path.mkdir(parents=True, exist_ok=True)` without any validation, allowing a caller to direct output to any writable location on the host PC — directly violating the project's PKG-02 / CLAUDE.md constraint against writing to the host.

Three informational items cover a duplicated test helper, a weak assertion in test 6, and an unguarded `spec["name"]` key access.

---

## Warnings

### WR-01: Unconditional `report.apps[0]` — potential `IndexError` crash

**File:** `main.py:149`

**Issue:** After calling `_detect_one_app(spec, report)` inside a try/except, code immediately accesses `report.apps[0]`. The `except` block appends a fallback `AppStatus` (line 147), so the exception path is safe. However, under the project's no-raise contract, `_detect_one_app` is also permitted to return silently without appending anything to `report.apps` (e.g., if it hits an internal guard that skips appending). In that non-exception, no-append path, `report.apps` is empty and `report.apps[0]` raises `IndexError`, crashing the process uncaught.

The comment on line 143 explicitly notes "never raises (D-16)" — but "never raises" does not guarantee "always appends." The two properties are independent.

**Fix:**
```python
app_status_list = report.apps  # mutated by _detect_one_app
if not app_status_list:
    # Defensive fallback: collector returned without appending
    from models import AppStatus
    app_status_list = [AppStatus(name=spec["name"], installed=False, error="collector returned no result")]

app_status = app_status_list[0]
```

Alternatively, guard with a clear assertion so failures surface during development:

```python
if not report.apps:
    raise RuntimeError(
        f"_detect_one_app did not append a result for spec '{spec['name']}'"
    )
app_status = report.apps[0]
```

---

### WR-02: `--output PATH` not validated — can direct writes to host PC (PKG-02 violation)

**File:** `main.py:226-229`

**Issue:** The `--output` path is accepted verbatim from `sys.argv` and used as-is as the write destination:

```python
if args.output:
    logs_dir = Path(args.output)
```

CLAUDE.md constraint PKG-02 states: "NEVER write to the host PC — no C:\, %TEMP%, %APPDATA%, or registry writes." An operator passing `--output C:\Users\Public\` or `--output %TEMP%` would silently write the audit HTML (and JSON if `--json` is present) to the host machine, violating the core security model of the tool. This is especially risky because the tool is designed to be invoked from a USB drive in double-click / batch contexts where a misconfigured path is easy to miss.

**Fix:** Validate that the resolved output path starts with the USB root (`usb_root`) before accepting it, or at minimum warn loudly when the path does not share the same drive root:

```python
if args.output:
    logs_dir = Path(args.output).resolve()
    # Enforce USB-only write constraint (PKG-02, CLAUDE.md)
    if sys.platform != "darwin":
        usb_drive = usb_root.drive  # e.g., 'E:'
        if logs_dir.drive.lower() != usb_drive.lower():
            print(
                f"[ERROR] --output path '{logs_dir}' is not on the USB drive ({usb_drive}). "
                "Writing to the host PC is not permitted (PKG-02).",
                file=sys.stderr,
            )
            sys.exit(1)
else:
    logs_dir = usb_root / "logs"
```

---

## Info

### IN-01: `_patched_main` helper duplicated between test files

**File:** `tests/test_cli_phase15.py:18-62`

**Issue:** The `_patched_main` context manager is copied verbatim from `tests/test_main.py`. The only difference is the docstring wording. Duplication means any future change to the patching strategy (e.g., adding a new import to `main.py`) must be applied in two places or tests will diverge.

**Fix:** Extract `_patched_main` into a shared conftest:

```python
# tests/conftest.py
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from models import AuditReport
from parsers.name_parser import parse_hostname

@contextmanager
def patched_main(isatty_value: bool, report_overrides: dict | None = None):
    ...  # single canonical implementation

import pytest
@pytest.fixture
def patched_main_fixture():
    return patched_main
```

Both test files then import from `conftest` or use the fixture, eliminating the duplicate.

---

### IN-02: `test_output_flag_overrides_logs_dir` assertion is over-broad

**File:** `tests/test_cli_phase15.py:186-188`

**Issue:** The assertion checks for `"/custom/audit_results"` OR `"custom"` OR `"audit_results"` in any written path. The `"custom"` and `"audit_results"` conditions are each individually so broad they would pass even if the path were something incidental like `/usr/local/custom_data/`. The intent is to verify the exact override path is honored — the assertion should be tighter.

**Fix:**
```python
assert any(p.startswith("/custom/audit_results") or "custom/audit_results" in p or "custom\\audit_results" in p for p in written_paths), (
    f"Expected output under /custom/audit_results path; got: {written_paths}"
)
```

Or, better, make the test platform-aware and assert the full directory segment is present:

```python
assert any("audit_results" in p and "custom" in p for p in written_paths), (
    f"Expected output under /custom/audit_results path; got: {written_paths}"
)
```

---

### IN-03: Unguarded `spec["name"]` key access in `_find_app_spec` error message

**File:** `main.py:132`

**Issue:** When `_find_app_spec` returns `None`, the error message is built by iterating all specs and accessing `s["name"]`:

```python
known = ", ".join(s["name"] for s in specs)
```

This assumes every dict in `specs` has a `"name"` key. If a spec entry is malformed (missing `"name"`), this raises `KeyError` and produces an unhandled traceback instead of the intended error message. Given that specs are authored as module-level constants (not user input), this is low probability — but it is still an unguarded access.

**Fix:**
```python
known = ", ".join(s.get("name", "<unnamed>") for s in specs)
```

---

_Reviewed: 2026-05-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
