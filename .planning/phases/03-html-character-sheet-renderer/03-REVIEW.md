---
phase: 03-html-character-sheet-renderer
reviewed: 2026-05-04T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - requirements.txt
  - writers/__init__.py
  - tests/test_writers.py
  - renderer/__init__.py
  - renderer/templates/character_sheet.html
  - tests/test_renderer.py
  - tests/test_renderer_helpers.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-04
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 3 introduces the HTML renderer, Jinja2 template, and file writer. The implementation is well-structured: `_build_context()` correctly pre-processes all None values before the template sees them, autoescape is correctly enabled, and `importlib.resources` is used for PyInstaller-safe template loading. No security vulnerabilities or data loss risks found.

Three warnings are raised: a silent rendering inconsistency when `disk_free_gb=0.0`, a visual defect where the HP bar renders at 100% width when disk data is unknown, and a missing parent-directory guard in `write_html` that will produce a cryptic error under unexpected inputs. Two info items flag duplicate test functions and a minor template inconsistency in the muted-class conditional for the Station field.

---

## Warnings

### WR-01: `disk_free_gb=0.0` renders hp-red bar but blank disk label

**File:** `renderer/__init__.py:59-77`

**Issue:** The HP class branch (line 59) and the `disk_label` branch (line 75) share the same condition: `if report.disk_total_gb and report.disk_free_gb is not None`. For the case `disk_total_gb=100.0, disk_free_gb=0.0` (a fully-used disk — unusual but valid), `0.0 is not None` is `True`, so the HP bar correctly calculates `pct=0.0` and assigns `hp-red`. However, `disk_label` on line 75 uses `f'{report.disk_free_gb:.0f} GB free / ...'` and is computed inside the same guard — so `disk_label` would be `'0 GB free / 100 GB total'`. That is actually fine for these lines. The real inconsistency is in `disk_total_display` (line 70-73): it uses `is not None` for its guard, so `disk_total_display` = `'100 GB total'`, but the HP bar path runs. No rendering crash occurs. 

The actual latent bug is at line 59: `report.disk_total_gb and` is a falsy check, meaning `disk_total_gb=0.0` skips the HP bar calculation entirely (falls through to `hp-none`) while `disk_total_display` (line 72, guarded by `is not None`) still renders `'0 GB total'`. The output would show `"0 GB total"` in the stat block while the HP bar displays as gray (`hp-none`) with `disk_label=None`. This is internally inconsistent: the stat block shows a total of 0 GB but the HP bar signals "no data."

**Fix:** Align both guards. Since `disk_total_gb=0.0` is physically nonsensical (a 0-byte disk), treating it the same as `None` in the HP bar is defensible — but `disk_total_display` should be suppressed in the same case. Change line 70-73 to use the same falsy guard:

```python
# Disk total display — D-06 (match HP bar guard: falsy covers None and 0.0)
disk_total_display = (
    f'{int(report.disk_total_gb)} GB total'
    if report.disk_total_gb else None
)
```

---

### WR-02: HP bar renders at 100% width when disk data is unknown

**File:** `renderer/__init__.py:63-64` and `renderer/templates/character_sheet.html:311`

**Issue:** When `disk_total_gb` is `None` or `0.0`, `_build_context` sets `pct = 100.0` and `hp_class = 'hp-none'` (lines 63-64). The template then renders:

```html
<div class="hp-fill hp-none" style="width: 100%"></div>
```

The result is a full-width gray bar. Visually, a full gray bar resembles a full green bar from a quick glance, and does not communicate "data unavailable." A more honest representation for the unknown/no-data state is a zero-width or empty bar.

**Fix:** Set `pct = 0.0` for the no-data case rather than `100.0`, or add a dedicated template branch that omits the fill element entirely when `hp_class == 'hp-none'`:

```python
else:
    pct = 0.0          # changed from 100.0 — empty bar for no-data state
    hp_class = 'hp-none'
```

Or in the template (line 310-312):

```html
<div class="hp-track">
  {% if hp_class != 'hp-none' %}
  <div class="hp-fill {{ hp_class }}" style="width: {{ disk_pct }}%"></div>
  {% endif %}
</div>
```

---

### WR-03: `write_html` silently fails with cryptic error when output directory does not exist

**File:** `writers/__init__.py:16-17`

**Issue:** `dest.write_text(html, encoding='utf-8')` will raise `FileNotFoundError: [Errno 2] No such file or directory` if `output_path` does not exist. The function has no guard and no helpful error message. While `output_path = Path(sys.executable).parent` always exists in production, this will fail with a hard-to-diagnose error in any dev/CI context where the directory hasn't been created (e.g., a test that passes a nonexistent path).

The test suite always uses `tempfile.TemporaryDirectory()` which creates the directory, so no test exercises this path. The failure would only surface when `write_html` is called from outside tests with a missing directory.

**Fix:** Add a `mkdir` guard before writing, or raise a descriptive error:

```python
def write_html(html: str, output_path: Path) -> Path:
    output_path.mkdir(parents=True, exist_ok=True)
    dest = output_path / 'status_report.html'
    dest.write_text(html, encoding='utf-8')
    return dest
```

If the project constraint is "never create directories on the host PC," then at minimum raise a clear error rather than letting `write_text` fail with an opaque OS error:

```python
if not output_path.is_dir():
    raise FileNotFoundError(
        f"write_html: output directory does not exist: {output_path}"
    )
```

---

## Info

### IN-01: Duplicate test functions across `test_renderer_helpers.py` and `test_renderer.py`

**File:** `tests/test_renderer_helpers.py:27-109` and `tests/test_renderer.py:60-184`

**Issue:** `test_renderer_helpers.py` contains 9 test functions (`test_load_template_source_returns_string`, `test_build_context_all_none_hardware`, `test_build_context_disk_zero_produces_hp_none`, `test_build_context_hp_green`, `test_build_context_hp_amber`, `test_build_context_hp_red`, `test_build_context_guild_warehouse`, `test_build_context_guild_laptop`, `test_build_context_guild_none_when_both_none`) that are substantively identical to functions in `test_renderer.py`. The file's own docstring says these are "superseded by test_renderer.py in Task 3."

Pytest will discover and run both files, doubling the test execution time for these cases. More importantly, if a helper's behavior changes, developers must update both files or risk false-green tests.

**Fix:** Remove `tests/test_renderer_helpers.py` entirely, since `test_renderer.py` is the designated superseding suite. If there is a reason to retain it (e.g., it is the TDD gate artifact for task 1), add a skip marker or a comment directing maintainers not to add new tests there.

---

### IN-02: Inconsistent muted-class conditional for `station` vs other header fields in template

**File:** `renderer/templates/character_sheet.html:291`

**Issue:** The `station` field uses `{% if station is none %}` to apply the muted CSS class, while all other header fields (`device_type`, `city`, `guild`) use `{% if not field %}`. Since `station` is typed as `int | None`, using `is none` is the correct check — it means a `station=0` would correctly render as non-muted. However, the inconsistency creates a maintenance risk: a future developer reading the template may normalize it to `{% if not station %}`, which would silently mute the valid value `station=0`.

**Fix:** Apply the same `is none` pattern to all four header fields for consistency and correctness, since all of them should show muted only when absent, not when falsy:

```html
<span class="field-value{% if device_type is none %} muted{% endif %}">
<span class="field-value{% if city is none %} muted{% endif %}">
<span class="field-value{% if guild is none %} muted{% endif %}">
<span class="field-value{% if station is none %} muted{% endif %}">
```

Note: `guild`, `city`, and `device_type` are all `str | None` in context, so an empty-string value (`""`) would be incorrectly treated as non-muted. If empty strings are possible, the `| default('—', true)` filter already handles display; using `is none` for the muted-class guard is still the safer choice.

---

_Reviewed: 2026-05-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
