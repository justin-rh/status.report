# SCRY v3.1 Requirements — Cleanup

**Milestone:** v3.1 Cleanup
**Goal:** Close all accumulated debt — validate the tool on real hardware, confirm vendor registry paths with IT, automate REQUIREMENTS tracking, and remove code tech debt.
**Created:** 2026-05-19

---

## Requirements

### Hardware Validation (VALID)

- [ ] **VALID-01**: IT staff runs SCRY under a Windows SYSTEM/Admin account and observes real uptime and pending update count values; yellow UPTIME_WARN badge renders when uptime >7 days; red UPTIME_STALE badge renders when uptime >30 days; standard-user (non-admin) run shows "N/A" for pending updates
- [ ] **VALID-02**: IT staff runs SCRY on a real Dell machine and observes DCU pending count populated; runs on a non-Dell/non-Lenovo machine and observes "Not installed" vendor row; 3 visual HTML vendor row renders (test_vendor_render_case1/2/3.html) verified in browser
- [ ] **VALID-03**: IT staff runs SCRY on an enrolled Windows machine and confirms NinjaOne and CrowdStrike detected; IT/stakeholder signs off on M365 single-suite-entry display; SCRY runs on real Intune-enrolled machine and Company Portal detected
- [ ] **VALID-04**: IT staff runs SCRY on a real Mac and confirms hardware collectors, profile enumeration, app detection, and HTML render complete without error; NinjaOne launchctl label confirmed
- [ ] **VALID-05**: IT staff opens generated HTML character sheet in a real browser and confirms D&D-styled sheet renders correctly (layout, colors, stat block, equipment table, quest status)

### IT Confirmation (CONF)

- [ ] **CONF-01**: Edgar/IT confirms Dell Command Update registry path(s) used by SCRY match the actual path on enrolled Dell machines; code updated and tests added if paths differ from current implementation
- [ ] **CONF-02**: Edgar/IT confirms Lenovo System Update registry path(s) used by SCRY match the actual path on enrolled Lenovo machines; code updated and tests added if paths differ from current implementation

### Automation (AUTO)

- [ ] **AUTO-01**: A PreToolUse hook exists that intercepts SUMMARY commit attempts and fails if any REQUIREMENTS.md REQ checkbox matched by the current phase is still `[ ]` — preventing phases from closing with unchecked requirements

### Tech Debt (DEBT)

- [ ] **DEBT-01**: `writers.write_html` function and its unreachable call path are removed; hard-coded `scry.html` filename in dead code is eliminated; all existing tests continue to pass
- [ ] **DEBT-02**: `_run_cli` with `--updates` flag no longer calls `collect_pending_updates` or `collect_vendor_updates` when it only needs hostname, serial, and warnings output; collector invocations are gated on whether their results are used
- [ ] **DEBT-03**: When `--app NAME` is combined with `--output PATH`, SCRY prints a warning to stderr that `--output` is ignored in app-query mode, rather than silently discarding it

---

## Future Requirements

| ID | Description | Deferred From |
|----|-------------|---------------|
| APP-V2-02 | Detect remote access tools (TeamViewer, AnyDesk, RDP enabled) | v3.0 planning |
| DIST-V2-01 | Code-signed .exe to eliminate SmartScreen prompt | v1.0 close (budget) |
| LSU-PENDING | Lenovo System Update pending count (no passive source available) | v3.0 close |

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Active Directory / domain queries | Adds network dependency; tool must work offline |
| Sending data to a remote server or API | Security/trust boundary; flash drive is the audit trail |
| Writing any data to the host PC | Core constraint |
| Detecting all installed software (full inventory) | Scoped to specific app list |
| Win32_Product for app detection | Triggers MSI reconfiguration — production machines affected |
| PyInstaller --onefile packaging | Quarantined by CrowdStrike Falcon behavioral detection |
| Mac PyInstaller packaging (.app/notarization) | Deferred to future milestone |

---

## Traceability

| REQ-ID | Phase | Plan | Status |
|--------|-------|------|--------|
| VALID-01 | — | — | pending |
| VALID-02 | — | — | pending |
| VALID-03 | — | — | pending |
| VALID-04 | — | — | pending |
| VALID-05 | — | — | pending |
| CONF-01 | — | — | pending |
| CONF-02 | — | — | pending |
| AUTO-01 | — | — | pending |
| DEBT-01 | — | — | pending |
| DEBT-02 | — | — | pending |
| DEBT-03 | — | — | pending |
