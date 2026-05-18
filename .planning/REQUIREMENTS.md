# Requirements: SCRY v3.0

**Milestone:** v3.0 — System Health, Vendor Updates, and Extended CLI
**Created:** 2026-05-14
**Status:** Active

## Milestone Goal

Surface system health signals and extend CLI output options so IT staff can assess machine state and integrate output into NinjaOne workflows.

## Requirements

### Rename

- [ ] **RENAME-01**: All source files, build spec, `build.bat`, and planning docs reference SCRY instead of StatusReport; `scry.exe` and `scry.spec` replace `status_report.exe` and `status_report.spec`
- [ ] **RENAME-02**: Output filename format changed from `status_{hostname}_{date}.html` to `{date}_scry_{hostname}.html` (date-first for alphabetical sort, `scry` replaces `status`)

### System Health

- [ ] **HEALTH-01**: User can see pending Windows update count in the character sheet stat block; degrades gracefully to N/A when running as standard user (WUA COM requires SYSTEM or Administrator)
- [ ] **HEALTH-02**: User can see uptime since last reboot in the character sheet stat block (days + hours display format)
- [x] **WARN-04**: Tool emits a **yellow** (caution) warning when uptime > 7 days; `UPTIME_WARN_DAYS = 7` configurable constant in `health_checks.py`
- [x] **WARN-05**: Tool emits a **red** (critical) warning when uptime > 30 days; `UPTIME_STALE_DAYS = 30` configurable constant in `health_checks.py`; warning text notes that hibernation time is counted on Windows

### Vendor Update Detection

- [ ] **VENDOR-01**: User can see Dell Command Update installation status and pending update count in the character sheet; count read passively from `DCUApplicableUpdates.xml` (never invokes `dcu-cli.exe`); shows "Not installed" when DCU is absent
- [ ] **VENDOR-02**: User can see Lenovo System Update installation status in the character sheet; pending count shown as N/A (no passive source available in v3.0); never invokes `tvsu.exe`

### Extended CLI Output

- [ ] **OUT-V3-01**: `--json` flag serializes full `AuditReport` to a JSON file in `logs/` alongside the HTML report; uses `dataclasses.asdict()` + `json.dumps()`
- [ ] **OUT-V3-02**: `--output <path>` flag overrides the default `logs/` destination for HTML and JSON output; validates resolved path does not write to the host PC (`C:\`, `%TEMP%`, etc.) to preserve PKG-02 compliance
- [ ] **CLI-V3-01**: `--app <name>` runs only the app-detection pipeline for one named app and prints result to stdout; `--app + --json` produces a single-app JSON blob to stdout; app name matching is case-insensitive

## Implementation Notes

- **Warning severity:** Existing `Warning` dataclass needs a `severity` field (`"yellow"` / `"red"`) to support WARN-04 and WARN-05. Both levels must still trigger auto-expand of the warnings box. This is a Phase 13 model change.
- **WUA privilege:** Works under SYSTEM (NinjaOne execution) and Administrator. Standard-user interactive runs degrade to `pending_updates = None` with a CollectionResult error. Live SYSTEM-context test required before shipping Phase 13.
- **DCU XML staleness:** If `DCUApplicableUpdates.xml` is absent or older than the DCU scan interval, surface "Unknown (no scan data)" rather than 0. IT must run DCU at least once for the count to appear.
- **`_WIN32COM_AVAILABLE` guard:** Mirror of `_WMI_AVAILABLE` pattern — enables CI testing without a COM server. Named after the library (not the feature) for future reuse.
- **PyInstaller:** Add `--hidden-import win32timezone` to `scry.spec` when pywin32 is added (Phase 13).

## Future Requirements

| REQ-ID | Description | Deferred Reason |
|--------|-------------|-----------------|
| APP-V2-02 | Detect remote access tools (TeamViewer, AnyDesk, RDP enabled) | Not in v3.0 scope |
| DIST-V2-01 | Code-signed .exe to eliminate SmartScreen prompt | Budget decision; CrowdStrike test already passed without it |
| LSU-PENDING | Lenovo System Update pending count | No passive source; requires `tvsu.exe` (admin-only, side effects) |

## Out of Scope

| Feature | Reason |
|---------|--------|
| LSU pending count via `tvsu.exe` | Requires admin elevation, has side effects, may violate PKG-02 |
| DCU pending count via `dcu-cli.exe` | Requires admin elevation, may trigger downloads, violates PKG-02 |
| WUA update listing (titles / KB numbers) | Count is sufficient for the IT audit use case |
| `--json` as pipeline mode selector | JSON is an output-format modifier only; does not skip collection |
| Writing any data to the host PC | Core constraint — no artifacts left behind (PKG-02) |

## Traceability

| REQ-ID | Phase | Phase Name | Status |
|--------|-------|------------|--------|
| RENAME-01 | 12 | SCRY Rename | Pending |
| RENAME-02 | 12 | SCRY Rename | Pending |
| HEALTH-01 | 13 | System Health Collectors | In Progress (data contract + collector — Plan 01; display — Plan 03) |
| HEALTH-02 | 13 | System Health Collectors | In Progress (data contract + collector — Plan 01; display — Plan 03) |
| WARN-04 | 13 | System Health Collectors | Complete (Plan 02 — _check_uptime yellow threshold) |
| WARN-05 | 13 | System Health Collectors | Complete (Plan 02 — _check_uptime red threshold, hibernation note) |
| VENDOR-01 | 14 | Vendor Update Detection | Pending |
| VENDOR-02 | 14 | Vendor Update Detection | Pending |
| OUT-V3-01 | 15 | Extended CLI Flags | Pending |
| OUT-V3-02 | 15 | Extended CLI Flags | Pending |
| CLI-V3-01 | 15 | Extended CLI Flags | Pending |
