# Phase 4: App Detection and Compliance Engine - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Detect all target applications via registry enumeration across all 4 Uninstall key paths (HKLM, HKLM\Wow6432Node, HKCU, HKCU\Wow6432Node) with filesystem and service fallbacks where needed, and populate `AuditReport.apps` with one `AppStatus` entry per logical app. All apps always appear in the list (even if Missing) so the renderer's Quest Status logic can operate correctly.

Apps in scope: NinjaOne/NinjaRMM, CrowdStrike Falcon, MERP (WindX), Microsoft 365 (suite), Zoom, Google Chrome, Claude desktop app.

</domain>

<decisions>
## Implementation Decisions

### MERP Detection
- **D-01:** MERP is built on PVX Plus Technologies WindX. Registry path is unknown; use filesystem-first detection.
- **D-02:** Primary check: `Path("C:/PVX Plus Technologies/WindX Plugin-64 2022 Upd 1/WindX").exists()`. If found: `installed=True`, `detection_method='filesystem'`.
- **D-03:** After filesystem hit, attempt a registry search across all 4 Uninstall key paths for DisplayName or Publisher containing `"WindX"` or `"PVX Plus Technologies"` to capture the version string. If registry found: populate `version`; if not: `version=None` is acceptable.
- **D-04:** If filesystem path does not exist and registry search finds nothing: `installed=False`. No exception raised.

### Microsoft 365 Detection
- **D-05:** Detect M365 as a single suite entry — one `AppStatus` entry named `"Microsoft 365"`. No per-app individual entries for Word, Excel, Outlook, Teams, OneDrive.
- **D-06:** Detection target: Click-to-Run suite registry key. Search all 4 Uninstall paths for DisplayName containing `"Microsoft 365"` or `"Microsoft Office"` (Click-to-Run installs typically use one of these). First match wins; `version` from `DisplayVersion`.

### CrowdStrike Falcon Service State
- **D-07:** CrowdStrike is detected via the standard 4 Uninstall paths (DisplayName: `"CrowdStrike Falcon"`). Version from `DisplayVersion`.
- **D-08:** `service_state` is populated from `HKLM\SYSTEM\CurrentControlSet\Services\CSFalconService` Start DWORD. Mapping: `2 → "Automatic"`, `3 → "Manual"`, `4 → "Disabled"`. If the key doesn't exist, `service_state=None`.
- **D-09:** Service key read uses winreg only — no wmi, no subprocess. Consistent with the project's winreg-first constraint.

### Detector Code Architecture
- **D-10:** Config-driven table: `APP_SPECS` list of dicts in `collectors/windows/apps.py`. Each entry declares the app's `name`, `display_name_keywords`, optional `publisher_keywords`, optional `filesystem_path` (for MERP-style fallback), and optional `service_key` (for CrowdStrike-style service state).
- **D-11:** A single `detect_apps(report: AuditReport) -> None` function iterates `APP_SPECS`, runs the unified registry search (all 4 paths) per app, applies filesystem/service fallbacks where flagged in the spec. Mutates `report.apps` in place.
- **D-12:** `collect_all()` in `collectors/__init__.py` calls `collect_apps(report)` after `collect_hardware` and `collect_profiles` — preserving the existing ordering convention.
- **D-13:** Each app spec entry in `APP_SPECS` is independent. Adding a new app is one dict entry. No new detector function needed for standard apps.

### General Detection Rules
- **D-14:** All 4 Uninstall paths are enumerated for every app, per CLAUDE.md constraint. Missing 32-bit entries is a silent bug — the loop covers all 4 unconditionally.
- **D-15:** Every app always produces one `AppStatus` entry appended to `report.apps`, even if `installed=False`. This ensures the renderer's Quest Status logic can count missing apps.
- **D-16:** Errors during detection (e.g., registry access exception) are caught per-app, `AppStatus.error` is set, and a message is appended to `report.collection_errors`. Never raises across layer boundary.
- **D-17:** `detection_method` field values: `'registry'` for standard registry hits, `'filesystem'` for path-based detection (MERP primary), `'service'` is not used (service state supplements registry detection, doesn't replace it).

### Claude's Discretion
- Exact DisplayName keyword matching for NinjaOne (may appear as "NinjaRMM", "NinjaOne", "NinjaRMM Agent" — Claude selects keywords that avoid false positives from stale entries)
- Exact registry key iteration pattern (open subkey, read DisplayName value, compare, close — error handling per subkey)
- Whether to de-duplicate in the rare case the same app appears in multiple Uninstall paths (e.g., both HKLM and HKCU) — Claude picks the highest-privilege match

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Technical Constraints
- `CLAUDE.md` — Critical constraints: `winreg` only for app detection, all 4 Uninstall key paths mandatory, `Win32_Product` prohibited, `--onedir` packaging only. Read before writing any code.

### Data Contract
- `models.py` — `AppStatus` (name, installed, version, service_state, detection_method, error) and `AuditReport.apps: list[AppStatus]`. Phase 4 populates these fields exactly — no schema changes.

### Requirements
- `.planning/REQUIREMENTS.md` §APP-01 through §APP-07 — The 7 app detection requirements this phase implements.
- `.planning/ROADMAP.md` §Phase 4 — Success criteria (5 items): NinjaOne, CrowdStrike, M365, Zoom/Chrome/Claude, MERP.

### Prior Phase Context
- `.planning/phases/01-models-and-hostname-parser/01-CONTEXT.md` §Established Patterns — CollectionResult envelope, never-raise rule.
- `.planning/phases/02-system-collectors/02-CONTEXT.md` §Collector Structure — `detect_apps(report)` in-place mutation pattern mirrors `collect_hardware(report)`. `collect_all()` call ordering.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `models.py` — `AppStatus` dataclass fully defined. `detection_method` field already supports `'registry'` and `'filesystem'` values. No model changes needed.
- `collectors/__init__.py` — `collect_all()` already calls `collect_hardware` then `collect_profiles`. Phase 4 adds `collect_apps(report)` call at the end.
- `collectors/windows/__init__.py` — Stub exists. Phase 4 adds `apps.py` here alongside `hardware.py`.
- `collectors/windows/hardware.py` — Reference implementation for the in-place mutation collector pattern. Phase 4 follows the same structure.

### Established Patterns
- In-place mutation: `detect_apps(report: AuditReport) -> None` — same interface as `collect_hardware`.
- Never raise across layer boundaries: all registry access exceptions caught inside `detect_apps`, errors written to `report.collection_errors`.
- Module-level import guard pattern (`_WMI_AVAILABLE` pattern from hardware.py): not needed here — `winreg` is stdlib and always available on Windows.

### Integration Points
- `AuditReport.apps` starts as an empty list (default_factory). Phase 4 fills it with one `AppStatus` per app target.
- Phase 3 renderer reads `report.apps` for the equipment list and Quest Status. The renderer expects all intended apps to be present in the list (installed or missing) — never an empty list on a provisioned machine.

</code_context>

<specifics>
## Specific Details

- **MERP filesystem path:** `C:\PVX Plus Technologies\WindX Plugin-64 2022 Upd 1\WindX` — use `Path("C:/PVX Plus Technologies/WindX Plugin-64 2022 Upd 1/WindX").exists()` for detection.
- **CrowdStrike service key:** `HKLM\SYSTEM\CurrentControlSet\Services\CSFalconService`, `Start` DWORD → `2="Automatic"`, `3="Manual"`, `4="Disabled"`.
- **M365 suite detection:** DisplayName search for `"Microsoft 365"` or `"Microsoft Office"` across 4 Uninstall paths.
- App list and expected AppStatus names: NinjaOne, CrowdStrike Falcon, MERP, Microsoft 365, Zoom, Google Chrome, Claude.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-app-detection-and-compliance-engine*
*Context gathered: 2026-05-05*
