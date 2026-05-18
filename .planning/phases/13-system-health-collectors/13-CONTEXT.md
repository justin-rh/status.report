# Phase 13: System Health Collectors - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Add uptime since last reboot and pending Windows update count to the AuditReport, display both in a new "System Health" section of the character sheet stat block, and emit UPTIME_WARN (yellow) and UPTIME_STALE (red) health warnings when uptime exceeds configurable thresholds.

</domain>

<decisions>
## Implementation Decisions

### Severity Model
- **D-01:** Add `level: str | None = None` field to the `Warning` dataclass in `models.py`. Values: `'yellow'` (caution) | `'red'` (critical) | `None` (OK or informational). This is the only change to `Warning` — no other fields change.
- **D-02:** `severity` field stays `'OK'` / `'WARN'` — Phase 6 D-03 is unchanged. Phase 11 `--warnings` CLI filter (`w.severity == "WARN"`) works without modification.
- **D-03:** Renderer determines warning color from `w.level` when `w.severity == 'WARN'`. Both `level='yellow'` and `level='red'` must trigger auto-expand of the warnings box (WARN-04, WARN-05). `level=None` warnings do not contribute to auto-expand.

### AuditReport New Fields
- **D-04:** Add two new fields to `AuditReport` in `models.py`:
  - `uptime_seconds: int | None = None` — populated by collector; `None` if collection fails
  - `pending_updates: int | None = None` — populated by WUA collector; `None` when inaccessible (standard user)
  These follow the existing flat-field pattern (alongside `os_build`, `ram_gb`, etc.).

### Uptime Collection
- **D-05:** Collect uptime using `psutil.boot_time()` — already in the stack, cross-platform (Windows + Mac), no elevation required, no new dependency. Compute elapsed seconds as `int(time.time() - psutil.boot_time())`. Store as `report.uptime_seconds`.
- **D-06:** Collection fits in the existing hardware collector (`collectors/windows/hardware.py` for Windows, `collectors/mac/hardware.py` for Mac). Claude's discretion on exact placement within those modules.
- **D-07:** Display format in stat block: `"N days H hours"` (e.g., `"12 days 4 hours"`). Edge cases (< 1 day: `"H hours"`, < 1 hour: `"M minutes"`) are Claude's discretion.

### Pending Updates Collection
- **D-08:** Collect via WUA COM: `win32com.client.Dispatch("Microsoft.Update.Session")`. Requires pywin32 (new dep: `pywin32==311`). Add `--hidden-import win32timezone` to `scry.spec` (per REQUIREMENTS.md note).
- **D-09:** Guard with `_WIN32COM_AVAILABLE` — mirrors the `_WMI_AVAILABLE` pattern exactly (named after the library). When guard is `False`, `report.pending_updates` stays `None`. CI tests run without a COM server.
- **D-10:** Standard user gets `None` → character sheet displays `"N/A"`. SYSTEM / Administrator gets the integer count.

### Warning Shape (evaluate_warnings)
- **D-11:** `evaluate_warnings()` returns **one** UPTIME `Warning` object (escalating). The code and level depend on elapsed days computed from `report.uptime_seconds`:
  - `uptime_seconds is None`: `code='UPTIME'`, `severity='OK'`, `level=None`, message indicates collection skipped
  - ≤ UPTIME_WARN_DAYS (7): `code='UPTIME'`, `severity='OK'`, `level=None`
  - > UPTIME_WARN_DAYS and ≤ UPTIME_STALE_DAYS (30): `code='UPTIME_WARN'`, `severity='WARN'`, `level='yellow'`
  - > UPTIME_STALE_DAYS (30): `code='UPTIME_STALE'`, `severity='WARN'`, `level='red'`, detail notes hibernation time is counted
- **D-12:** Constants at module top of `health_checks.py` (per REQUIREMENTS.md): `UPTIME_WARN_DAYS: int = 7` and `UPTIME_STALE_DAYS: int = 30`.
- **D-13:** `evaluate_warnings()` does NOT produce a Warning object for `pending_updates` — that field is informational only (no warning threshold in Phase 13). It appears in the stat block display only.
- **D-14:** `evaluate_warnings()` now returns 4 Warning objects (up from 3): OS_VERSION, DISK_SPACE, RENAME_REQUIRED, UPTIME. The "always returns N objects — one per check" contract (Phase 6 D-06) extends to 4.

### Character Sheet Stat Block
- **D-15:** Uptime and pending updates appear in a new **"System Health"** group of rows in the existing stat block — not inline with OS version. This keeps the stat block organized and leaves room for Phase 14 vendor update rows.
- **D-16:** Pending updates displays as `"N pending"` (e.g., `"3 pending"`) or `"N/A"` when `report.pending_updates is None`. Zero updates displays as `"0 pending"` (no special treatment).

### Claude's Discretion
- Exact display label text for the System Health rows (e.g., "Uptime", "Pending Updates" vs "Updates Pending")
- Sub-hour and sub-day edge case formatting for uptime display
- Whether `uptime_seconds` collection in hardware collectors is a new private helper or inline
- Exact WUA COM query logic (searcher criteria string, result counting)
- Test fixture approach for `_WIN32COM_AVAILABLE = False` path

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data Contract
- `models.py` — `Warning` (add `level` field here), `AuditReport` (add `uptime_seconds`, `pending_updates` here). Read current field order before inserting.

### Health Check Logic
- `health_checks.py` — Current `evaluate_warnings()` returns exactly 3 objects. Phase 13 extends to 4. Read existing threshold constant pattern before adding `UPTIME_WARN_DAYS` / `UPTIME_STALE_DAYS`.

### Collector Patterns
- `collectors/windows/hardware.py` — Existing WMI guard pattern (`_wmi_module`, `_WMI_AVAILABLE`). `_WIN32COM_AVAILABLE` guard mirrors this exactly.
- `collectors/base.py` — Base collector interface; check before adding new collection entry points.

### Entry Point and CLI
- `main.py` lines 79–85 — `--warnings` CLI filter: `w.severity == "WARN"`. This MUST continue to work after `level` field is added (D-02).
- `main.py` line 165 — `[SUMMARY]` warning count: `len([w for w in report.warnings if w.severity == 'WARN'])`. Also unaffected by `level` field.

### Renderer
- `renderer/__init__.py` line 167 — `has_warnings: any(w.severity == 'WARN' for w in report.warnings)`. Unaffected by `level` field but renderer template needs updating for `level`-based warning colors.

### Requirements
- `.planning/REQUIREMENTS.md` §System Health — HEALTH-01, HEALTH-02, WARN-04, WARN-05 and their implementation notes (WUA guard name, pywin32 version, DCU XML staleness note).
- `.planning/ROADMAP.md` §Phase 13 — Success criteria SC1–SC5; SC5 requires all existing tests pass.

### Build
- `scry.spec` — Must add `--hidden-import win32timezone` when pywin32 is added (REQUIREMENTS.md implementation note).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `psutil` — already imported in `collectors/windows/hardware.py`; use same import for `psutil.boot_time()`
- `Warning` dataclass in `models.py` — add `level` field after `detail` (last field) to avoid breaking existing positional construction in tests
- `field(default_factory=list)` pattern on AuditReport — `uptime_seconds` and `pending_updates` are scalars with `= None` default (not lists)
- `_check_os_version()` / `_check_disk_space()` in `health_checks.py` — model for the new `_check_uptime()` private helper

### Established Patterns
- `_WMI_AVAILABLE: bool` module-level flag + `_wmi_module` guard in `collectors/windows/hardware.py` — `_WIN32COM_AVAILABLE` must mirror this exactly (same variable naming convention, same CI-fallback behavior)
- `CollectionResult` envelope — used by hardware collectors; the WUA call should also return `CollectionResult[int | None]`
- Threshold constants at module top with type annotations: `OS_WARN_BUILD: int = 22000`, `DISK_WARN_PCT: float = 0.15` — UPTIME constants follow same pattern
- `evaluate_warnings()` tests in `tests/test_health_checks.py` — new tests for `_check_uptime()` follow the same parametrized fixture pattern

### Integration Points
- `main.py` line 126 — `report.warnings = evaluate_warnings(report)` — called after `collect_all()`, before `render_html()`. No change needed here.
- `collect_all()` in `collectors/__init__.py` — must call the new uptime/WUA collection so `report.uptime_seconds` and `report.pending_updates` are populated before `evaluate_warnings()` is called.
- Renderer template (Jinja2) — needs new `{{ uptime_display }}` and `{{ pending_updates_display }}` template variables, plus color logic for `level`-based warning box rendering.

</code_context>

<specifics>
## Specific Ideas

- `level='yellow'` → caution color in warning box; `level='red'` → critical/danger color. Both trigger auto-expand. `level=None` warnings render as passing checks (green or neutral).
- The `"N/A"` display for pending updates when `pending_updates is None` is explicit IT context: standard user interactive runs won't show a count, SYSTEM runs (NinjaOne) will.
- UPTIME_STALE warning detail should include: "Hibernation time is counted on Windows" — directly from REQUIREMENTS.md WARN-05 note.
- Phase 14 (Vendor Update Detection) will add more System Health rows to the stat block section created in this phase — design the section to be extensible.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-system-health-collectors*
*Context gathered: 2026-05-18*
