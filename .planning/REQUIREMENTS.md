# Requirements: StatusReport

**Defined:** 2026-05-04
**Core Value:** IT staff plugs in, runs the tool, and instantly knows what they're looking at — device type, location, department, software status, and any gaps — no manual lookup required.

## v1 Requirements

### Data Collection

- [x] **COLL-01**: Tool parses the PC hostname and decodes city, device type (warehouse workstation, user-assigned laptop, department laptop, P3), department code, company code, and station number using the Master Electronics naming convention
- [x] **COLL-02**: Tool collects hardware stats: CPU model, total RAM, disk capacity and free space, Windows OS version and build number — *Validated in Phase 2: System Collectors*
- [x] **COLL-03**: Tool enumerates all local user profiles on the machine (not just the currently logged-in user) — *Validated in Phase 2: System Collectors*

### App Detection

- [ ] **APP-01**: Tool detects whether NinjaRMM / NinjaOne agent is installed (registry-based, all four Uninstall key paths)
- [ ] **APP-02**: Tool detects whether CrowdStrike Falcon is installed and its service is present
- [ ] **APP-03**: Tool detects whether MERP (Master Electronics ERP) is installed (registry path to be confirmed with IT before this phase executes)
- [ ] **APP-04**: Tool detects whether Microsoft 365 apps are installed: Word, Excel, Outlook, Teams, OneDrive
- [ ] **APP-05**: Tool detects whether Zoom is installed
- [ ] **APP-06**: Tool detects whether Google Chrome is installed
- [ ] **APP-07**: Tool detects whether Claude desktop app is installed

### Output

- [ ] **OUT-01**: Tool generates an HTML character sheet with RPG/D&D-influenced aesthetic — stat block layout for hardware, class/guild/realm fields for device identity, equipment list for installed apps — that remains functionally readable as IT data without knowing RPG conventions
- [x] **OUT-02**: HTML file is saved to the same directory the .exe was launched from (i.e., the flash drive), derived from `sys.executable`, not `os.getcwd()` — *write_html(html, output_path) I/O layer implemented in Phase 3 Plan 01; output_path wired from sys.executable in Phase 5*
- [x] **OUT-03**: Tool handles unrecognized or non-conforming hostnames gracefully (renders with "Unknown" device type and displays raw hostname without crashing)

### Packaging

- [ ] **PKG-01**: Tool is packaged as a Windows .exe using PyInstaller `--onedir` mode, runnable without installation or admin rights on Windows 10/11
- [ ] **PKG-02**: All output (HTML file) is written to flash drive only — tool makes no writes to the host PC's filesystem, registry, or %TEMP%

## v2 Requirements

### Output

- **OUT-V2-01**: JSON structured log file saved to flash drive alongside the HTML output
- **OUT-V2-02**: Auto-opens the HTML character sheet in the default browser after generation

### App Detection

- **APP-V2-01**: Detect Intune enrollment status / Company Portal presence
- **APP-V2-02**: Detect remote access tools (TeamViewer, AnyDesk, Remote Desktop enabled)

### Platform

- **PLAT-V2-01**: Mac-compatible version of all collectors, using the same data models and rendering pipeline (platform-swappable architecture designed in v1)

### Distribution

- **DIST-V2-01**: Code-signed .exe to eliminate Windows SmartScreen prompt on first run

## Out of Scope

| Feature | Reason |
|---------|--------|
| Active Directory / domain queries | Adds network dependency; tool must work fully offline and on pre-enrollment machines |
| Sending data to a remote server or API | Security and trust boundary concern; flash drive is the audit trail |
| Writing any data to the host PC | Core constraint — no artifacts left behind on audited machines |
| Detecting all installed software (full inventory) | Scoped to a specific app list; full inventory is slow, noisy, and not the goal |
| Win32_Product for app detection | Anti-feature: triggers MSI consistency checks on every installed app, causing side effects on production machines |
| PyInstaller --onefile packaging | Quarantined by CrowdStrike Falcon's behavioral detection on every target machine |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COLL-01 | Phase 1 | Complete |
| COLL-02 | Phase 2 | Complete |
| COLL-03 | Phase 2 | Complete |
| APP-01 | Phase 4 | Pending |
| APP-02 | Phase 4 | Pending |
| APP-03 | Phase 4 | Pending |
| APP-04 | Phase 4 | Pending |
| APP-05 | Phase 4 | Pending |
| APP-06 | Phase 4 | Pending |
| APP-07 | Phase 4 | Pending |
| OUT-01 | Phase 3 | Pending |
| OUT-02 | Phase 3 | Complete (03-01) |
| OUT-03 | Phase 1 | Complete |
| PKG-01 | Phase 5 | Pending |
| PKG-02 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15 (roadmap complete)
- Unmapped: 0

---
*Requirements defined: 2026-05-04*
*Last updated: 2026-05-04 after roadmap creation*
