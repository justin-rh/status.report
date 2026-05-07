# Phase 6: Warning Data Model - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `Warning` dataclass to `models.py` and implement `evaluate_warnings()` in a new `health_checks.py` module. Two health checks: OS version (warn on build < 22000) and disk free space (warn at ≤ 15%). Pure Python — no OS API calls, no Windows-only imports. All 85+ existing tests must pass without modification.

</domain>

<decisions>
## Implementation Decisions

### Warning Dataclass
- **D-01:** `Warning` dataclass lives in `models.py` — consistent with AuditReport, AppStatus, ParsedHostname. Single source of truth for all data contracts.
- **D-02:** Fields: `code: str`, `severity: str`, `message: str`, `detail: str | None = None` — consistent with existing plain-str pattern for bounded string fields (same as `service_state: str | None` in AppStatus).
- **D-03:** Severity values: `'OK'` and `'WARN'` (plain strings, no Enum, no Literal).
- **D-04:** `AuditReport.warnings: list[Warning] = field(default_factory=list)` — added to AuditReport in models.py; defaults to empty list.

### Module Name and Location
- **D-05:** New module named `health_checks.py` at project root (alongside `models.py`, `main.py`). NOT named `warnings.py` — that silently shadows Python's stdlib `warnings` module.

### evaluate_warnings() Behavior
- **D-06:** `evaluate_warnings(report: AuditReport) -> list[Warning]` — returns one `Warning` object per check regardless of outcome (both OK and WARN entries). Two checks → always two Warning objects returned. Phase 7 renderer gets the full check list to render status for each.
- **D-07:** OS version check: `severity='WARN'` when `os_build` < `'22000'` (Windows 10 or earlier); `severity='OK'` when ≥ `'22000'`. `code='OS_VERSION'`.
- **D-08:** Disk space check: `severity='WARN'` when `disk_free_gb / disk_total_gb ≤ 0.15`; `severity='OK'` when above. `code='DISK_SPACE'`. Both `disk_free_gb` and `disk_total_gb` can be `None` — when either is None, return `severity='OK'` with a note in `detail` that the check was skipped (no data).
- **D-09:** Threshold constants are module-level in `health_checks.py`: `OS_WARN_BUILD = 22000` and `DISK_WARN_PCT = 0.15`. Easy to adjust without hunting through logic.

### Claude's Discretion
- Warning `code` string values (`'OS_VERSION'`, `'DISK_SPACE'`) — exact casing and format is Claude's call; keep them short, uppercase, underscore-separated.
- Warning `message` text wording is Claude's call — keep it human-readable and concise.
- `detail` field content for disk check (e.g., showing GB free / GB total) is Claude's call.
- Whether `evaluate_warnings()` is importable in the module's `__init__.py` (if any) is Claude's call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Data Contract
- `models.py` — Existing dataclasses (AuditReport, AppStatus, ParsedHostname, CollectionResult). Warning and AuditReport.warnings field are added here in Phase 6.

### Requirements
- `.planning/REQUIREMENTS.md` §Warnings — WARN-01 and WARN-02 are the two requirements this phase satisfies.
- `.planning/ROADMAP.md` §Phase 6 — Success criteria SC1–SC4; SC4 explicitly requires all 85+ existing tests pass without modification.

### Prior Phase Context (relevant patterns)
- `.planning/phases/02-system-collectors/02-CONTEXT.md` — `_wmi_module`/`_WMI_AVAILABLE` guard pattern; `CollectionResult` usage; `collect_all()` lazy import pattern.
- `.planning/phases/04-app-detection-and-compliance-engine/04-CONTEXT.md` — `AppStatus` dataclass usage; plain-str for bounded states.

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `models.py`: All dataclasses live here. Warning goes here too (D-01). AuditReport already uses `field(default_factory=list)` for `apps` and `collection_errors` — same pattern for `warnings`.
- `tests/` structure: Each module has a dedicated test file (e.g., `test_hardware_collector.py`, `test_renderer.py`). Phase 6 gets `tests/test_health_checks.py`.

### Established Patterns
- `field(default_factory=list)` for list fields on AuditReport — already used for `apps` and `collection_errors`.
- Plain `str` for bounded string fields — `service_state: str | None` in AppStatus. Same for `severity: str`.
- No `frozen=True` on dataclasses — Phase 2 established this.
- `CollectionResult` envelope for collector returns — NOT used here; `evaluate_warnings()` returns a plain list (it cannot fail in a meaningful way — missing data yields OK-with-note).

### Integration Points
- `main.py` — will call `evaluate_warnings(report)` and assign the result to `report.warnings` after collectors run, before `render_html()`.
- `health_checks.py` imports only from `models.py` (no OS-specific imports — pure Python per phase constraint).
- Phase 7 renderer reads `report.warnings` to render the collapsible warnings box.

</code_context>

<specifics>
## Specific Ideas

- Two checks always return two Warning objects (one per check), so Phase 7 can render a complete status table regardless of pass/fail.
- Threshold constants (`OS_WARN_BUILD`, `DISK_WARN_PCT`) at module top of `health_checks.py` so IT can adjust without reading function logic.
- Disk check handles `None` disk data gracefully — skipped checks return `severity='OK'` so they don't trigger expansion of the Phase 7 warnings box on uncollected data.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-warning-data-model*
*Context gathered: 2026-05-07*
