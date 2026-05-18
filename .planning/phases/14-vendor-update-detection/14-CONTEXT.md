# Phase 14: Vendor Update Detection - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Detect Dell Command Update and Lenovo System Update installation status, read pending Dell update count passively from `DCUApplicableUpdates.xml`, and surface both in the System Health stat block group — without invoking any vendor CLI (`dcu-cli.exe` or `tvsu.exe` are never called).

Vendor detection runs only when `--updates` is passed; rows are omitted from the character sheet entirely when `--updates` is absent.

</domain>

<decisions>
## Implementation Decisions

### Data Model
- **D-01:** Add a new `VendorUpdateStatus` dataclass to `models.py` with three fields:
  - `installed: bool | None` — `True` = found in registry; `False` = not found; `None` = collection error
  - `pending_count: int | None` — integer from XML parse; `None` when not installed, XML absent, or parse error
  - `scan_data_present: bool` — `True` only when the XML file exists and was readable
- **D-02:** Add two new fields to `AuditReport` after `pending_updates`:
  - `dell_dcu: VendorUpdateStatus | None = None`
  - `lenovo_lsu: VendorUpdateStatus | None = None`
  Both are `None` when `--updates` was not passed (not collected).
- **D-03:** No `error` field on `VendorUpdateStatus`. Errors silently set fields to `None` and append to `report.collection_errors` — same contract as all other collectors.

### CLI Gating
- **D-04:** `collect_vendor_updates(report)` is called only when `--updates` is passed, alongside `collect_pending_updates(report)` in `main.py`. No new flag needed.
- **D-05:** When `--updates` is not passed, `dell_dcu` and `lenovo_lsu` remain `None`. The renderer checks for `None` and omits vendor rows entirely — no "Not checked" placeholder.

### Character Sheet Placement
- **D-06:** Vendor rows live inside the existing **"System Health"** stat block group (Phase 13 D-15 reserved space). No new section header is added.
- **D-07:** Display values for Dell Command Update:
  - Not installed → `"Not installed"`
  - Installed, XML absent (`scan_data_present = False`) → `"Unknown (no scan data)"`
  - Installed, XML present → `"{N} pending"` (e.g., `"2 pending"`)
- **D-08:** Display values for Lenovo System Update:
  - Not installed → `"Not installed"`
  - Installed → `"N/A"` for pending count (no passive source in v3.0, per VENDOR-02)
- **D-09:** Row label text (e.g., "Dell Cmd Update", "Lenovo Sys Update") is Claude's discretion.

### Dell Detection
- **D-10:** DCU installation detected via registry Uninstall sweep using `display_name_keywords: ["Dell Command Update", "Dell Command | Update"]`. Reuses the same `_search_uninstall_keys()` pattern from `collectors/windows/apps.py`.
- **D-11:** `DCUApplicableUpdates.xml` probed at one fixed path:
  `C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml`
  No fallback paths. If absent → `scan_data_present = False`, `pending_count = None`.
- **D-12:** Parse the XML to extract the pending update count. Claude's discretion on the exact XML element/attribute to read (researcher to confirm structure).

### Lenovo Detection
- **D-13:** LSU installation detected via registry Uninstall sweep using `display_name_keywords: ["Lenovo System Update"]`. Same pattern as DCU (D-10).
- **D-14:** No XML or passive count source for LSU in v3.0. `scan_data_present` is always `False` for LSU; `pending_count` is always `None`.

### Collector Structure
- **D-15:** New module: `collectors/windows/vendor.py` — single exported function `collect_vendor_updates(report: AuditReport) -> None`. Follows the same one-concern-per-file structure as `hardware.py` and `apps.py`.
- **D-16:** `UNINSTALL_PATHS` constant should be imported from `collectors/windows/apps.py` (or moved to a shared location) rather than duplicated.

### Claude's Discretion
- Exact row label text for vendor rows in System Health section
- Whether `UNINSTALL_PATHS` is imported from `apps.py` or extracted to a shared `collectors/windows/_registry.py` helper
- DCUApplicableUpdates.xml element/attribute structure for pending count extraction (researcher to confirm)
- Test fixture approach for the "DCU installed but XML absent" and "DCU not installed" paths

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data Contract
- `models.py` — Add `VendorUpdateStatus` dataclass before `AuditReport`; add `dell_dcu` and `lenovo_lsu` fields after `pending_updates`. Read current field order before inserting.

### Collector Patterns
- `collectors/windows/apps.py` — `UNINSTALL_PATHS` constant and `_search_uninstall_keys()` function are the patterns to reuse for registry Uninstall detection. Read before implementing vendor detection.
- `collectors/windows/hardware.py` lines 50–62 — `collect_hardware()` shows how a top-level collector is structured. `collect_pending_updates()` (line 76) shows the `--updates`-gated collector shape.

### CLI Wiring
- `main.py` lines 55–58 and 123–125 — `--updates` flag wiring. `collect_vendor_updates(report)` is added in both locations (startup path and CLI path) alongside `collect_pending_updates(report)`.

### Renderer
- `renderer/__init__.py` — System Health rendering; extend with conditional vendor rows (check `report.dell_dcu is not None` before rendering).
- `renderer/templates/character_sheet.html` — System Health section Jinja2 template; add vendor rows here.

### Requirements
- `.planning/REQUIREMENTS.md` §VENDOR-01, VENDOR-02 — Full acceptance criteria for vendor detection behavior.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `UNINSTALL_PATHS` (collectors/windows/apps.py) — 4-path registry sweep constant; import rather than duplicate
- `_search_uninstall_keys()` (collectors/windows/apps.py) — Returns `(display_name, version)` or raises; drives all registry-based app detection
- `_WIN32COM_AVAILABLE` guard pattern (collectors/windows/hardware.py) — Reference for structuring any new optional-dependency guard if needed (vendor detection doesn't need one — winreg and pathlib are always available)

### Established Patterns
- Collectors mutate `AuditReport` in place and never raise — wrap all vendor detection in try/except; append to `report.collection_errors` on failure
- `VendorUpdateStatus` follows the `AppStatus` naming convention but is a separate dataclass (AppStatus is for the apps list; VendorUpdateStatus is for dedicated report fields)

### Integration Points
- `models.py`: insert `VendorUpdateStatus` as a new dataclass; add `dell_dcu` and `lenovo_lsu` to `AuditReport` after line 77 (`pending_updates`)
- `main.py`: add `collect_vendor_updates(report)` call in the `--updates` block (two locations: lines ~56–58 and ~123–125)
- `renderer/__init__.py` + `character_sheet.html`: extend System Health section; vendor rows conditioned on `report.dell_dcu is not None`

</code_context>

<specifics>
## Specific Ideas

- Phase 13 D-15 explicitly "leaves room for Phase 14 vendor update rows" in the System Health group — vendor rows slot directly into that reserved space without adding a new section header
- "Unknown (no scan data)" is the exact wording specified in Phase 14 SC2 — use that string verbatim

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-vendor-update-detection*
*Context gathered: 2026-05-18*
