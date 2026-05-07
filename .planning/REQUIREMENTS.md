# Requirements: StatusReport v2.0

## Milestone v2.0 — Warnings, Mac Parity, and NinjaOne Compatibility

### App Detection

- [ ] **APP-V2-01**: User can see whether Company Portal (UWP) is installed on a Windows device, with MDM enrollment status shown in the Service column of that row

### Warnings

- [ ] **WARN-01**: HTML sheet warns when the device runs Windows 10 or earlier (OS build < 22000)
- [ ] **WARN-02**: HTML sheet warns when disk free space is ≤ 15% of total capacity
- [ ] **WARN-03**: Warnings appear in a collapsible box at the bottom of the sheet; each check shows OK or WARN status; box is collapsed with a green "All checks passed" header when all pass, auto-expanded when any warning fires

### Mac Platform

- [ ] **PLAT-V2-01**: Tool collects Mac hardware stats — CPU model (Intel and Apple Silicon), total RAM, disk capacity and free space, macOS version
- [ ] **PLAT-V2-02**: Tool enumerates all local user profiles on macOS (non-system accounts, UID ≥ 501)
- [ ] **PLAT-V2-03**: Tool detects the following apps on macOS: NinjaOne, CrowdStrike Falcon, Microsoft 365, Zoom, Google Chrome, Claude Desktop, Company Portal
- [ ] **PLAT-V2-04**: Same D&D HTML character sheet is rendered and saved on macOS runs (output to `logs/` relative to exe)

### NinjaOne Compatibility

- [ ] **NINJA-01**: Exe runs without crashing or hanging under SYSTEM account (no interactive prompts, no display or browser dependency)
- [ ] **NINJA-02**: Key audit stats printed to stdout after each run (hostname, OS version, CPU, RAM, disk %, active warning count) for NinjaOne script log capture

---

## Future Requirements (deferred from v2.0)

| ID | Requirement | Deferred Reason |
|----|-------------|-----------------|
| OUT-V2-01 | JSON structured log saved to flash drive alongside HTML | Not requested for v2.0; useful for future NinjaOne API integration |
| OUT-V2-02 | Auto-open HTML in default browser after generation | Not requested; incompatible with SYSTEM/headless contexts |
| APP-V2-02 | Detect remote access tools (TeamViewer, AnyDesk, RDP enabled) | Not in scope for v2.0 |
| DIST-V2-01 | Code-signed .exe to eliminate SmartScreen prompt | Budget decision deferred; CrowdStrike test passed without it |

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| MERP detection on Mac | Windows-only ERP (PVX Plus path); no macOS equivalent |
| NinjaOne API / custom field reporting | Standard stdout capture covers v2.0 needs; API integration deferred |
| Mac PyInstaller packaging (.app bundle / notarization) | Gatekeeper notarization requires Apple Developer account + separate research; deferred to v3 |
| Active Directory / domain queries | Network dependency; tool must work offline |
| Sending data to remote server | Security/trust boundary; flash drive is the audit trail |
| Full software inventory | Out of scope; tool targets specific app list only |

---

## Traceability

_Filled by roadmapper._

| REQ-ID | Phase |
|--------|-------|
| APP-V2-01 | — |
| WARN-01 | — |
| WARN-02 | — |
| WARN-03 | — |
| PLAT-V2-01 | — |
| PLAT-V2-02 | — |
| PLAT-V2-03 | — |
| PLAT-V2-04 | — |
| NINJA-01 | — |
| NINJA-02 | — |
