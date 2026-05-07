# Phase 7: HTML Warnings Section - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a collapsible warnings box to the HTML character sheet using the `Warning` objects from Phase 6's `evaluate_warnings()`. The box auto-expands when any warning fires and shows a green "All checks passed" header when all pass. The existing ad-hoc `os_warning` and `rename_warning` flags in `_build_context()` are both removed — `os_warning` is replaced by the Warning object pipeline; `rename_warning` is absorbed into the warnings box as a third health check in `health_checks.py`. No changes to existing 111 tests required when passing `warnings=[]`.

</domain>

<decisions>
## Implementation Decisions

### Rename Warning Fate
- **D-01:** The `rename_warning` banner is absorbed into the warnings box as a third `Warning` object. Add a `RENAME_REQUIRED` check to `health_checks.py` that fires (`severity='WARN'`) when `report.parsed_hostname.device_type == 'Unknown'`. `evaluate_warnings()` now returns 3 Warning objects (OS_VERSION, DISK_SPACE, RENAME_REQUIRED). No changes to `AuditReport` — `parsed_hostname` is already in scope.
- **D-02:** Both `rename_warning` and `os_warning` keys are removed from `_build_context()`. The template no longer uses them. The standalone `.rename-warning` banner elements in the template are also removed.

### Per-Check Row Layout
- **D-03:** Each row in the expanded warnings box shows two lines:
  - Line 1: colored badge (`OK` or `WARN`) + message text
  - Line 2 (indented, muted): `detail` field text — shown only when `detail is not None`
  - Full Warning object rendered per row: code is NOT shown (message is the human-readable label)
- **D-04:** Badge colors match existing CSS variables: `var(--green)` for OK, `var(--amber)` for WARN.

### Collapsible Mechanism
- **D-05:** Use browser-native `<details>/<summary>` — no JavaScript. Jinja2 sets the `open` attribute on `<details>` when any `warning.severity == 'WARN'`; omits it when all pass. Zero JS change to the project.
- **D-06:** Summary header (the always-visible collapsed line):
  - All pass: green "✓ All checks passed" text
  - Any WARN: amber "⚠ Health Checks — {N} warning(s)" text (N = count of WARN entries)
  - Style matches existing `.section-title` + `.section-card` visual language.

### Box Position in the Sheet
- **D-07:** Warnings box placed after Quest Status, before Department Reference. This replaces the existing `os_warning` / `rename_warning` banner slot. New sheet order:
  - header → stat block → software → quest status → **WARNINGS BOX** → dept reference → chronicle

### Renderer Wiring
- **D-08:** `_build_context()` passes `warnings=report.warnings` to the template context. No other changes to the existing context keys — all other fields remain as-is.
- **D-09:** `main.py` calls `evaluate_warnings(report)` and assigns the result to `report.warnings` after all collectors run, before `render_html(report)` is called.

### Claude's Discretion
- CSS class names for the warnings box elements (`.warnings-box`, `.warning-row`, etc.) — Claude picks consistent naming that fits existing class style.
- Whether `<summary>` uses a CSS `::marker` chevron or a Unicode arrow character — Claude picks the simpler option.
- Detail line indentation amount and exact muted styling — match existing `.text-muted` / `var(--text-muted)` pattern.
- Whether to show the count of warnings in the amber summary ("1 warning" vs "1 warning(s)") — Claude picks the natural English form.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Template and Renderer
- `renderer/templates/character_sheet.html` — Current template. Phase 7 adds the warnings box and removes `{% if os_warning %}` and `{% if rename_warning %}` blocks.
- `renderer/__init__.py` — `_build_context()` function. Phase 7 adds `warnings` key, removes `os_warning` and `rename_warning` keys.

### Health Checks Module
- `health_checks.py` — Phase 6 implementation. Phase 7 adds a third `_check_rename(report)` helper and updates `evaluate_warnings()` to return 3 items.

### Data Contract
- `models.py` — `Warning` dataclass (code, severity, message, detail). `AuditReport.warnings: list[Warning]`. `AuditReport.parsed_hostname: ParsedHostname` (used by rename check).

### Requirements
- `.planning/REQUIREMENTS.md` §Warnings — WARN-03 is the requirement this phase satisfies.
- `.planning/ROADMAP.md` §Phase 7 — Success criteria SC1–SC4.

### Existing Tests (must not regress)
- `tests/test_renderer.py` — 23+ tests using `MOCK_REPORT` (no `warnings` field set → defaults to `[]`). All must pass after Phase 7 changes.
- `tests/test_renderer_helpers.py` — Additional helper tests. Must pass.
- `tests/test_health_checks.py` — Phase 6 tests. Phase 7 adds new test cases for RENAME_REQUIRED check; existing 17 tests must still pass.

### Prior Phase Context
- `.planning/phases/06-warning-data-model/06-CONTEXT.md` — D-06 (evaluate_warnings always returns N items, one per check), D-03 (severity plain str 'OK'/'WARN'), D-02 (Warning fields).
- `.planning/phases/03-html-character-sheet-renderer/03-CONTEXT.md` — D-14 (dark panel aesthetic, color palette), D-15 (importlib.resources template loading), existing CSS variables.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- CSS variables already defined: `--green (#22c55e)`, `--amber (#f59e0b)`, `--red (#ef4444)`, `--text-muted (#6b7280)`, `--bg-secondary`, `--bg-accent`, `--border` — use these for the warnings box; no new colors needed.
- `.section-card` + `.section-title` pattern: all existing sections use this. The warnings box should use `<details class="section-card">` with `<summary class="section-title">` as the collapsible header to stay visually consistent.
- `default('—', true)` Jinja2 filter established for None handling — detail field uses same pattern.

### Established Patterns
- Template is logic-light: `_build_context()` pre-computes everything; template only does display. Pass `warnings` list and `has_warnings` (bool) from `_build_context()` rather than computing warning counts in the template.
- `autoescape=True` on the Jinja2 Environment — all template output is auto-escaped; Warning message/detail strings are plain text (no HTML), so this is safe.
- Never raise across layer boundaries — `evaluate_warnings()` already follows this; `_check_rename()` must too.

### Integration Points
- `_build_context()` in `renderer/__init__.py`: add `'warnings': report.warnings` and a `'has_warnings': any(w.severity == 'WARN' for w in report.warnings)` pre-computed bool. Remove `'os_warning'` and `'rename_warning'` keys.
- Template: replace `{% if os_warning %}` block and `{% if rename_warning %}` block with single warnings box section.
- `health_checks.py`: add `_check_rename(report)` that checks `report.parsed_hostname.device_type`. Append its result to the list returned by `evaluate_warnings()`.
- `main.py`: ensure `evaluate_warnings(report)` is called and result assigned to `report.warnings` before `render_html(report)`.

</code_context>

<specifics>
## Specific Ideas

- Warnings box uses `<details class="section-card warnings-box">` with `<summary class="section-title">` — matches the established `.section-card` visual pattern across the whole sheet without new CSS classes for the container.
- `open` attribute on `<details>`: set by Jinja2 via `{% if has_warnings %}open{% endif %}` in the tag. Clean and zero-JS.
- Amber summary header when warnings present: "⚠ Health Checks — 1 warning" (singular/plural handled in Python pre-computation, not in template).
- Green summary header when all pass: "✓ All checks passed".
- OK rows: subdued — green badge is present but visually lightweight. WARN rows: amber badge, stands out.
- Detail line: second `<div>` with `var(--text-muted)` color and slight left-indent below the message line.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-html-warnings-section*
*Context gathered: 2026-05-07*
