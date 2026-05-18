---
phase: 13-system-health-collectors
reviewed: 2026-05-18T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - collectors/__init__.py
  - collectors/mac/hardware.py
  - collectors/windows/hardware.py
  - health_checks.py
  - models.py
  - renderer/__init__.py
  - renderer/templates/character_sheet.html
  - requirements.txt
  - scry.spec
  - tests/test_collectors_phase13.py
  - tests/test_hardware_collector.py
  - tests/test_health_checks.py
  - tests/test_models_phase13.py
  - tests/test_renderer_phase13.py
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-05-18
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 13 adds uptime collection (`uptime_seconds`), Windows Update pending count (`pending_updates`), a new `Warning.level` field, and a fourth health check (`_check_uptime`). The implementation is solid overall. The never-raise contract is respected across all collectors, the `Warning.level` field ordering is correct (after `detail` — confirmed by the positional safety test), and the two-threshold uptime escalation logic is correctly implemented with proper boundary semantics (`>` not `>=`).

One warning was found: `evaluate_warnings` can raise `AttributeError` when `parsed_hostname=None` — violating its own "never raises" contract. Four info items cover code duplication in the renderer, the Windows-only top-level `winreg` import, a type annotation inconsistency for `parsed_hostname`, and an undocumented design decision to make `pending_updates` display-only with no corresponding health check.

---

## Warnings

### WR-01: `evaluate_warnings` raises `AttributeError` when `parsed_hostname` is `None`

**File:** `health_checks.py:113`
**Issue:** `_check_rename` accesses `report.parsed_hostname.device_type` without a `None` guard. The docstring for `evaluate_warnings` states it "Never raises", but if `parsed_hostname=None` this line raises `AttributeError: 'NoneType' object has no attribute 'device_type'`. The test suite always constructs `AuditReport` with a valid `ParsedHostname`, so this code path has no test coverage. The `test_models_phase13.py` file constructs `AuditReport("HOSTNAME", None)` to test default field values — confirming `None` is accepted at runtime — and the `test_evaluate_warnings_never_raises` test in `test_health_checks.py:106` does not pass `parsed_hostname=None`, leaving this gap unchecked.

In normal production flow (`main.py` always calls `parse_hostname()` before constructing `AuditReport`) this cannot trigger. However the function's documented contract — "never raises" — is not upheld for all inputs.

**Fix:** Add a `None` guard in `_check_rename`:
```python
def _check_rename(report: AuditReport) -> Warning:
    """Return RENAME_REQUIRED Warning. WARN when device_type is 'Unknown' (D-01)."""
    if report.parsed_hostname is None:
        return Warning(
            code='RENAME_REQUIRED',
            severity='OK',
            message='Rename check skipped',
            detail='parsed_hostname not available',
        )
    if report.parsed_hostname.device_type == 'Unknown':
        return Warning(
            code='RENAME_REQUIRED',
            severity='WARN',
            message='Device needs to be renamed',
            detail=(
                f'Hostname "{report.parsed_hostname.raw_hostname}" does not match '
                'the Master Electronics naming convention'
            ),
        )
    return Warning(
        code='RENAME_REQUIRED',
        severity='OK',
        message='Hostname matches naming convention',
        detail=None,
    )
```

---

## Info

### IN-01: Code duplication — `render_report` and `render_html` repeat template load and `Environment` construction

**File:** `renderer/__init__.py:55-75`
**Issue:** `render_report` and `render_html` independently call `_load_template_source()`, construct `Environment(autoescape=True)`, call `env.from_string()`, and call `_build_context()`. The only difference is the final step (write vs. return). Any future change to template loading or rendering options must be applied in two places.

**Fix:** Extract a shared private helper:
```python
def _render_to_string(report: AuditReport) -> str:
    template_source = _load_template_source()
    env = Environment(autoescape=True)
    template = env.from_string(template_source)
    return template.render(**_build_context(report))

def render_report(report: AuditReport, output_path: Path) -> Path:
    return write_html(_render_to_string(report), output_path)

def render_html(report: AuditReport) -> str:
    return _render_to_string(report)
```

---

### IN-02: Top-level `import winreg` prevents import on non-Windows platforms

**File:** `collectors/windows/hardware.py:10`
**Issue:** `winreg` is a Windows-only stdlib module. The unconditional top-level import at line 10 causes `ModuleNotFoundError` when this module is imported on macOS or Linux. The orchestrator (`collectors/__init__.py`) correctly uses lazy imports inside the function body to avoid this, but test files that directly import from `collectors.windows.hardware` (e.g., `test_hardware_collector.py:28`, `test_collectors_phase13.py:34`) will fail at import time on non-Windows CI rather than skipping cleanly.

**Fix:** Add a platform skip marker at the top of each Windows-specific test file:
```python
import sys
import pytest
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="collectors.windows.hardware is Windows-only"
)
```
Alternatively, keep the current design and document that Windows-specific tests require a Windows CI runner.

---

### IN-03: `parsed_hostname` type annotation does not declare `None` as valid

**File:** `models.py:65`, `tests/test_models_phase13.py:55`
**Issue:** `AuditReport.parsed_hostname` is annotated as `ParsedHostname` (not `ParsedHostname | None`), but `test_models_phase13.py` passes `None` as the second positional argument in several test cases. Downstream consumers (`health_checks.py:113`, `renderer/__init__.py:99`) do not guard against `None`, making the type annotation inconsistency a latent defect source. This is related to WR-01.

**Fix:** Either widen the annotation to match what tests exercise:
```python
parsed_hostname: ParsedHostname | None
```
And add `None` guards in downstream callers. Or update the tests to pass a minimal valid `ParsedHostname`:
```python
from parsers.name_parser import parse_hostname
r = AuditReport("HOSTNAME", parse_hostname("HOSTNAME"))
```

---

### IN-04: `pending_updates` is display-only with no health check — design decision is undocumented

**File:** `health_checks.py:23-35`, `models.py:77`
**Issue:** `AuditReport.pending_updates` is collected and surfaced as `pending_updates_display` in the renderer, but `evaluate_warnings` produces no `Warning` for it. All other collected metrics (OS build, disk space, uptime) have corresponding health check warnings. The omission is likely intentional — pending update count is informational, not actionable by the tool — but this design decision is not documented anywhere in the health_checks module.

**Fix:** Add a comment in `health_checks.py` explaining the intentional omission:
```python
# NOTE: pending_updates is display-only. No Warning is produced because the
# tool cannot trigger Windows Update on behalf of the user; the count is
# surfaced in the renderer for human awareness only.
```
If a warning is ever desired, add a `_check_pending_updates` function returning a 5th `Warning` object, and update the "always returns exactly four" contract in the docstring.

---

_Reviewed: 2026-05-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
