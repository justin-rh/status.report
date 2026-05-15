# Phase 7: HTML Warnings Section - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 6
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `health_checks.py` | service | transform | `health_checks.py` (existing) | exact — add third helper to same file |
| `renderer/templates/character_sheet.html` | template | request-response | `renderer/templates/character_sheet.html` (existing) | exact — modify in place |
| `renderer/__init__.py` | renderer/service | request-response | `renderer/__init__.py` (existing `_build_context`) | exact — modify in place |
| `main.py` | controller/entry-point | request-response | `main.py` (existing pipeline section) | exact — one insertion before `render_html` call |
| `tests/test_health_checks.py` | test | transform | `tests/test_health_checks.py` (existing Phase 6 tests) | exact — append new parametrize block |
| `tests/test_renderer.py` | test | request-response | `tests/test_renderer.py` (existing render tests) | exact — append new assertions |

---

## Pattern Assignments

### `health_checks.py` — add `_check_rename` + update `evaluate_warnings`

**Analog:** `health_checks.py` — `_check_disk_space` helper (lines 69–102) and `evaluate_warnings` return list (lines 19–29)

**Existing helper signature + None-guard pattern** (lines 69–86):
```python
def _check_disk_space(report: AuditReport) -> Warning:
    """Return DISK_SPACE Warning. WARN when free/total <= DISK_WARN_PCT (0.15)."""
    free = report.disk_free_gb
    total = report.disk_total_gb
    if free is None or total is None:
        return Warning(
            code='DISK_SPACE',
            severity='OK',
            message='Disk space check skipped',
            detail='disk_free_gb or disk_total_gb not collected',
        )
```

**New `_check_rename` must copy this exact structure:**
- Function signature: `def _check_rename(report: AuditReport) -> Warning:`
- Access field: `report.parsed_hostname.device_type`
- WARN condition: `report.parsed_hostname.device_type == 'Unknown'`
- No None-guard needed (device_type is always set by `parse_hostname`; 'Unknown' is the sentinel)
- Return `Warning(code='RENAME_REQUIRED', severity='WARN', message=..., detail=None)` on warn
- Return `Warning(code='RENAME_REQUIRED', severity='OK', message=..., detail=None)` on pass

**Updated `evaluate_warnings` return list** (lines 26–29):
```python
    return [
        _check_os_version(report),
        _check_disk_space(report),
    ]
```
Phase 7 change: append `_check_rename(report)` as the third element. The docstring "Always returns exactly two" updates to "exactly three".

---

### `renderer/templates/character_sheet.html` — warnings box + remove old banners

**Analog:** `renderer/templates/character_sheet.html` — existing section-card pattern and os/rename warning blocks

**Section-card pattern to replicate** (lines 327–348, 351–383, 386–422):
```html
<div class="SECTION-NAME section-card">
  <div class="section-title">SECTION LABEL</div>
  <!-- content -->
</div>
```

**Collapsible variant for warnings box** — use `<details>` in place of `<div>` as the card element, and `<summary>` in place of the inner `<div class="section-title">`:
```html
<details class="section-card warnings-box" {% if has_warnings %}open{% endif %}>
  <summary class="section-title">
    {% if has_warnings %}
      &#9888; Health Checks — {{ warnings | selectattr('severity', 'eq', 'WARN') | list | length }} warning(s)
    {% else %}
      &#10003; All checks passed
    {% endif %}
  </summary>
  <!-- warning rows here -->
</details>
```

**Badge pattern for OK/WARN rows** — copy from equipment table badge (lines 222–233):
```html
<span class="badge badge-installed">&#10003; OK</span>
<span class="badge badge-warn">&#9888; WARN</span>
```
Note: `badge-warn` is new; use `background: var(--amber)`. `badge-installed` (green) already exists.

**Detail line pattern** — copy `.stat-value.muted` pattern (lines 143–144):
```html
<div class="stat-value muted">{{ w.detail }}</div>
```
Indented version for detail line: add `style="padding-left: 1rem"` inline or a `.warning-detail` class using `var(--text-muted)`.

**Blocks to REMOVE** (lines 431–443):
```html
<!-- OS UPGRADE WARNING -->
{% if os_warning %}
<div class="rename-warning">
  &#9888; Device is running {{ os_combined | default('Windows 10', true) }} — upgrade to Windows 11 required
</div>
{% endif %}

<!-- RENAME WARNING -->
{% if rename_warning %}
<div class="rename-warning">
  &#9888; Device needs to be renamed — hostname "{{ hostname }}" does not match the Master Electronics naming convention
</div>
{% endif %}
```
Both `{% if os_warning %}` and `{% if rename_warning %}` blocks are deleted entirely. The `.rename-warning` CSS class (lines 277–287) becomes dead CSS but is harmless to leave.

**Placement:** Insert the new `<details>` warnings box between the QUEST STATUS block (line 429) and the DEPARTMENT REFERENCE block (line 445).

---

### `renderer/__init__.py` — update `_build_context()`

**Analog:** `renderer/__init__.py` — existing `_build_context` return dict (lines 156–179)

**Current keys to REMOVE** from the return dict (lines 176–177):
```python
        'rename_warning': rename_warning,
        'os_warning': os_warning,
```

**Current pre-computation blocks to REMOVE** (lines 140–147):
```python
    # Rename warning — shown when hostname could not be parsed
    rename_warning = ph.device_type == 'Unknown'

    # OS upgrade warning — Windows 10 or earlier (build < 22000)
    try:
        _build_int = int(report.os_build or '0')
    except ValueError:
        _build_int = 0
    os_warning = 0 < _build_int < 22000
```

**New keys to ADD** to the return dict — follow the same inline-comment style used for `quest_complete` and `missing_count` (lines 174–175):
```python
        'warnings': report.warnings,
        'has_warnings': any(w.severity == 'WARN' for w in report.warnings),
```

**Summary label pre-computation** — per CONTEXT.md D-06 and the "logic-light template" principle established in the code context, pre-compute the summary label string in Python rather than in the template. Add to return dict:
```python
        'warnings_summary': _warnings_summary(report.warnings),
```
Where `_warnings_summary` is a private helper that returns the string `"✓ All checks passed"` or `"⚠ Health Checks — N warning"` / `"⚠ Health Checks — N warnings"` (singular/plural). This keeps the template free of count logic.

Alternatively (simpler, per CONTEXT.md Specific Ideas): pass `has_warnings` bool + `warnings` list and let the template use `| selectattr | list | length` for the count inline — acceptable since the template already does simple Jinja2 filter chains (e.g., line 408). Both approaches are valid; the pre-computed key is preferred per the "logic-free template" principle.

---

### `main.py` — wire `evaluate_warnings` before `render_html`

**Analog:** `main.py` lines 40–64 — the existing pipeline section

**Current pipeline** (lines 40–64):
```python
    collect_all(report)  # mutates report in place -- D-06: never raises

    # Surface collector warnings -- never exit on collection failure (D-06)
    for err in report.collection_errors:
        print(f"[WARN] {err}")

    print("Detecting installed apps...")
    print("Rendering character sheet...")
    ...
    html = render_html(report)
```

**Import to add** at top of file (follow existing import block lines 14–26):
```python
from health_checks import evaluate_warnings
```

**Insertion point** — after `collect_all(report)` collector block and before `render_html(report)`, following the same mutate-in-place convention used by `collect_all`:
```python
    report.warnings = evaluate_warnings(report)
```

Place this assignment after the collector warning print loop and before the `print("Rendering character sheet...")` line, so it executes as part of the data preparation phase before rendering begins.

---

### `tests/test_health_checks.py` — add RENAME_REQUIRED test cases

**Analog:** `tests/test_health_checks.py` — existing OS version and disk space test blocks

**`make_report` factory** (lines 11–14) — reuse exactly as-is:
```python
def make_report(**kwargs) -> AuditReport:
    defaults = dict(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))
    defaults.update(kwargs)
    return AuditReport(**defaults)
```
For rename tests, pass a `ParsedHostname` directly via `parsed_hostname=ParsedHostname(raw_hostname=..., device_type=...)`.

**Parametrize pattern to copy** (lines 21–37):
```python
@pytest.mark.parametrize('os_build,expected_severity', [
    ('21999', 'WARN'),
    ('22000', 'OK'),
    ...
])
def test_os_version_check(os_build, expected_severity):
    report = make_report(os_build=os_build)
    warnings = evaluate_warnings(report)
    os_warning = warnings[0]
    assert os_warning.code == 'OS_VERSION', (...)
    assert os_warning.severity == expected_severity, (...)
```

**New parametrize block for RENAME_REQUIRED** — same structure, index `[2]`:
```python
@pytest.mark.parametrize('device_type,expected_severity', [
    ('Unknown',              'WARN'),   # unrecognized hostname — rename required
    ('Warehouse Workstation','OK'),     # valid type — no rename needed
    ('Department Laptop',   'OK'),     # valid type — no rename needed
])
def test_rename_check(device_type, expected_severity):
    ph = ParsedHostname(raw_hostname='TEST-PC', device_type=device_type)
    report = make_report(parsed_hostname=ph)
    warnings = evaluate_warnings(report)
    rename_warning = warnings[2]
    assert rename_warning.code == 'RENAME_REQUIRED', (...)
    assert rename_warning.severity == expected_severity, (...)
```

**Always-three guarantee** — update the existing `test_evaluate_warnings_always_returns_two` test (line 91):
```python
def test_evaluate_warnings_always_returns_three():
    """evaluate_warnings must always return exactly 3 Warning objects (Phase 7)."""
    report = make_report()
    warnings = evaluate_warnings(report)
    assert len(warnings) == 3
    assert warnings[0].code == 'OS_VERSION'
    assert warnings[1].code == 'DISK_SPACE'
    assert warnings[2].code == 'RENAME_REQUIRED'
```
The existing `test_evaluate_warnings_always_returns_two` test must be updated (not left as-is) because it asserts `len(warnings) == 2`, which will fail after Phase 7 adds the third check.

**Import additions needed** — add `ParsedHostname` to the import from `models`:
```python
from models import AuditReport, Warning, ParsedHostname
```

---

### `tests/test_renderer.py` — add warnings box HTML tests

**Analog:** `tests/test_renderer.py` — existing render_report integration tests (lines 191–244)

**MOCK_REPORT** (lines 28–53) — currently has `os_build='19045'` (Win10, triggers OS_VERSION WARN) and `parsed_hostname=parse_hostname('PHX-INV-003')` (valid hostname, RENAME_REQUIRED OK). After Phase 7, `MOCK_REPORT` must have `warnings` pre-populated for the template to render the warnings box. Add `warnings=evaluate_warnings(MOCK_REPORT_without_warnings)` or set it directly:
```python
from health_checks import evaluate_warnings
# At bottom of MOCK_REPORT definition or in a fixture:
MOCK_REPORT.warnings = evaluate_warnings(MOCK_REPORT)
```
This ensures `warnings` is populated in the MOCK_REPORT used by all existing tests.

**Pattern for new HTML assertion tests** — copy from `test_render_report_html_contains_hostname` (lines 208–214):
```python
def test_render_report_html_contains_hostname():
    from renderer import render_report
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        html = out.read_text(encoding='utf-8')
        assert 'PHX-INV-003' in html
```

**New tests to add:**

1. Warnings box present — `details` element with class `warnings-box` renders:
```python
def test_render_report_html_contains_warnings_box():
    from renderer import render_report
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        html = out.read_text(encoding='utf-8')
        assert 'warnings-box' in html
```

2. Warnings box auto-opens when WARN present — `open` attribute present in rendered HTML (MOCK_REPORT has OS_VERSION WARN):
```python
def test_render_report_warnings_box_open_when_warn():
    from renderer import render_report
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        html = out.read_text(encoding='utf-8')
        assert 'open' in html  # <details ... open>
```

3. All-pass report renders collapsed (no `open` attribute): use `make_report` with `os_build='22621'`, valid hostname (parsed OK), large disk:
```python
def test_render_report_warnings_box_closed_when_all_ok():
    from renderer import render_report
    from health_checks import evaluate_warnings
    report = make_report(os_build='22621', disk_total_gb=100.0, disk_free_gb=60.0)
    report.warnings = evaluate_warnings(report)
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(report, Path(tmp))
        html = out.read_text(encoding='utf-8')
        assert 'warnings-box' in html
        assert '<details class="section-card warnings-box" open' not in html
```

4. Old banner elements gone — `os_warning` and `rename_warning` context vars no longer appear:
```python
def test_render_report_no_old_warning_banners():
    from renderer import _build_context
    report = make_report()
    ctx = _build_context(report)
    assert 'os_warning' not in ctx
    assert 'rename_warning' not in ctx
```

5. New context keys present:
```python
def test_build_context_warnings_keys_present():
    from renderer import _build_context
    report = make_report()
    ctx = _build_context(report)
    assert 'warnings' in ctx
    assert 'has_warnings' in ctx
    assert isinstance(ctx['warnings'], list)
    assert isinstance(ctx['has_warnings'], bool)
```

---

## Shared Patterns

### Never-raise discipline
**Source:** `health_checks.py` docstring line 20–21, all `_check_*` helpers
**Apply to:** `_check_rename` in `health_checks.py`
Pattern: Return `Warning(severity='OK', ...)` for any unexpected state; never raise. No try/except needed in `_check_rename` since `device_type` is always a plain string (never raises on comparison), but maintain the contract.

### Template logic-free principle
**Source:** `renderer/__init__.py` docstring line 3–4: "Pre-computes all derived values... so the template stays logic-free."
**Apply to:** `_build_context()` additions
Pattern: `has_warnings = any(w.severity == 'WARN' for w in report.warnings)` computed in Python, passed as a bool. Template uses `{% if has_warnings %}open{% endif %}` — no Python logic in Jinja2.

### `default('—', true)` filter for None display
**Source:** `renderer/templates/character_sheet.html` lines 337, 344, 356, 359, etc.
**Apply to:** Warning `detail` field rendering in the template
Pattern: `{{ w.detail | default('', true) }}` — use empty string default (not em-dash) since detail is shown only when present (the row is conditionally rendered with `{% if w.detail %}`).

### `make_report(**kwargs)` factory
**Source:** `tests/test_health_checks.py` lines 11–14 and `tests/test_renderer.py` lines 16–23
**Apply to:** All new test cases in both test files
Pattern: Both files define an identical `make_report` factory. New tests reuse it directly; no new fixture infrastructure needed.

### `@pytest.mark.parametrize` with inline assertion messages
**Source:** `tests/test_health_checks.py` lines 21–37
**Apply to:** New `test_rename_check` parametrize block
Pattern: Assertion messages include the input value for easy debugging — e.g., `f'device_type={device_type!r}: expected ...'`.

---

## No Analog Found

None. All six files have exact analogs in the existing codebase.

---

## Metadata

**Analog search scope:** `health_checks.py`, `renderer/__init__.py`, `renderer/templates/character_sheet.html`, `main.py`, `tests/test_health_checks.py`, `tests/test_renderer.py`, `tests/test_renderer_helpers.py`, `models.py`
**Files scanned:** 8
**Pattern extraction date:** 2026-05-07
