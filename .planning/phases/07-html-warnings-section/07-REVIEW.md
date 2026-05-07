---
phase: 07-html-warnings-section
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - health_checks.py
  - main.py
  - renderer/__init__.py
  - renderer/templates/character_sheet.html
  - tests/test_health_checks.py
  - tests/test_renderer.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-05-07
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 7 introduces the unified health-checks warnings box: `health_checks.py` (pure evaluation layer), `renderer/__init__.py` (context builder), and `character_sheet.html` (Jinja2 template). The implementation is largely clean and well-tested. Three warnings and three informational items were found. No critical issues.

The most actionable findings are: (1) `_check_rename` silently passes when `device_type` is `None` rather than `'Unknown'`, which could mask a rename requirement if the name parser ever produces `None`; (2) `render_report` and `render_html` duplicate four lines of template-setup logic; (3) the `import errno` statement is buried inside an `except` block in `main.py`.

---

## Warnings

### WR-01: `_check_rename` silently passes when `device_type` is `None`

**File:** `health_checks.py:109`
**Issue:** The rename check compares `report.parsed_hostname.device_type == 'Unknown'`. The `ParsedHostname` type annotation allows `device_type: str | None = None`. When `device_type` is `None` — a value the parser could theoretically produce for a hostname that fails all pattern matches — the equality check returns `False` and the function returns `RENAME_REQUIRED OK`, incorrectly signaling that no rename is needed. The current `parse_hostname` implementation appears to always set `'Unknown'` rather than `None` for unrecognized hostnames, but the contract is not enforced here.
**Fix:** Guard for both sentinel values so a `None` device type is also caught:
```python
def _check_rename(report: AuditReport) -> Warning:
    device_type = report.parsed_hostname.device_type
    if device_type is None or device_type == 'Unknown':
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

### WR-02: `import errno` inside `except` block masks potential `ImportError`

**File:** `main.py:76`
**Issue:** `import errno as _errno` is placed inside the `except OSError` handler. While `errno` is always available in the stdlib, performing an import inside a `try/except` handler means that if the import fails (e.g., corrupted PyInstaller bundle), an `ImportError` would be raised inside the `except` block, masking the original `OSError` and producing a confusing traceback. The import can safely be moved to the top of the file with all other imports.
**Fix:**
```python
# At top of main.py, with other imports
import errno

# In the except block, replace:
# import errno as _errno
# if exc.errno == _errno.ENOSPC:
# with:
if exc.errno == errno.ENOSPC:
```

---

### WR-03: `render_report` and `render_html` duplicate template-setup logic

**File:** `renderer/__init__.py:55-75`
**Issue:** Both `render_report` (lines 55–60) and `render_html` (lines 63–75) repeat the identical four-line sequence: `_load_template_source()`, `Environment(autoescape=True)`, `env.from_string(template_source)`, `_build_context(report)`. If a change is needed (e.g., adding a Jinja2 extension or a different autoescape policy), it must be applied in two places, risking divergence.
**Fix:** Extract the shared setup into a private helper:
```python
def _render_to_string(report: AuditReport) -> str:
    """Build and render the template, returning the HTML string."""
    template_source = _load_template_source()
    env = Environment(autoescape=True)
    template = env.from_string(template_source)
    ctx = _build_context(report)
    return template.render(**ctx)

def render_report(report: AuditReport, output_path: Path) -> Path:
    html = _render_to_string(report)
    return write_html(html, output_path)

def render_html(report: AuditReport) -> str:
    return _render_to_string(report)
```

---

## Info

### IN-01: Dead CSS — `.rename-warning` class is no longer used in the template

**File:** `renderer/templates/character_sheet.html:277-288`
**Issue:** The `.rename-warning` CSS block (styling a standalone amber banner) was the Phase 6 approach for surfacing the rename warning. Phase 7 replaced it with the unified `<details class="warnings-box">` element. The `.rename-warning` rule is now unreferenced dead code.
**Fix:** Remove lines 277–288:
```css
/* Remove this entire block */
.rename-warning {
  border-radius: 8px;
  padding: 12px 16px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  background: #431407;
  border: 2px solid var(--amber);
  color: var(--amber);
}
```

---

### IN-02: Safari browser compatibility — `<summary>` marker not hidden in WebKit

**File:** `renderer/templates/character_sheet.html:434`
**Issue:** The `<summary>` element uses `list-style: none` to suppress the browser's default disclosure triangle. This works in Chrome and Firefox but does not remove the triangle in Safari, which requires the vendor-prefixed pseudo-element `summary::-webkit-details-marker { display: none }`.
**Fix:** Add the WebKit rule to the `<style>` block alongside the existing `list-style: none`:
```css
details > summary { list-style: none; }
details > summary::-webkit-details-marker { display: none; }
```
Note: If this report is only ever opened in Edge/Chrome on Windows, this is low priority.

---

### IN-03: Jinja2 `selectattr` expression evaluated twice in template

**File:** `renderer/templates/character_sheet.html:436-437`
**Issue:** The expression `warnings | selectattr('severity', 'equalto', 'WARN') | list | length` is evaluated twice in consecutive lines to (a) display the count and (b) apply conditional pluralization. While harmless — Jinja2 is fast and the list is always exactly 3 items — it is slightly harder to read than computing the count once.
**Fix:** Use Jinja2's `set` to capture the count, or pass `warn_count` from `_build_context`:
```jinja2
{% set warn_count = warnings | selectattr('severity', 'equalto', 'WARN') | list | length %}
<span style="color: var(--amber);">&#9888; Health Checks &#8212; {{ warn_count }} warning{% if warn_count != 1 %}s{% endif %}</span>
```
Alternatively, add `warn_count` to `_build_context()` alongside `has_warnings`.

---

_Reviewed: 2026-05-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
