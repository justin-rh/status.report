# Roadmap: StatusReport

## Overview

StatusReport is built in five phases following strict data dependencies. The data contract and hostname parser come first because every subsequent layer imports from them and the naming convention is the riskiest underdocumented logic. Hardware collectors and the rendering pipeline follow, with app detection isolated late because it depends on external validation (MERP registry path, CrowdStrike behavior on enrolled machines). Packaging closes the milestone once the full data pipeline is proven end-to-end.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Models and Hostname Parser** - Define the data contract and decode the Master Electronics naming convention
- [ ] **Phase 2: System Collectors** - Collect hardware stats and user profiles via WMI, psutil, and winreg
- [ ] **Phase 3: HTML Character Sheet Renderer** - Build the D&D-styled HTML output from mock data, nail the visual design
- [ ] **Phase 4: App Detection and Compliance Engine** - Detect all 7 target apps via registry, file, and service checks
- [ ] **Phase 5: Packaging and Distribution** - Package as PyInstaller --onedir .exe and validate USB output path

## Phase Details

### Phase 1: Models and Hostname Parser
**Goal**: The data contract is defined and the Master Electronics hostname naming convention is fully decoded in a testable, platform-agnostic parser
**Depends on**: Nothing (first phase)
**Requirements**: COLL-01, OUT-03
**Success Criteria** (what must be TRUE):
  1. Given `PHX-INV-003`, the parser returns city=Phoenix, device_type=Warehouse Workstation, department=INV, station=3
  2. Given `PHX-ABC123-ME`, the parser returns device_type=User-Assigned Laptop, company_code=ME
  3. Given an unrecognized hostname like `DESKTOP-XYZ123`, the parser returns device_type=Unknown with the raw hostname preserved and no exception raised
  4. All 21 city codes and all known department codes are covered by unit tests that pass without any Windows API calls
  5. AuditReport, ParsedHostname, AppStatus, and CollectionResult dataclasses exist and can be imported from models.py
**Plans**: TBD

### Phase 2: System Collectors
**Goal**: Hardware facts and local user profiles are collected from the live Windows machine and stored in an AuditReport instance, with graceful degradation when running without elevation
**Depends on**: Phase 1
**Requirements**: COLL-02, COLL-03
**Success Criteria** (what must be TRUE):
  1. Running the collector on any Windows 10/11 machine populates CPU model, total RAM, disk capacity, disk free space, and OS version/build in the AuditReport without crashing
  2. All local user profile paths are enumerated from the registry (not just the currently logged-in user) and appear in the AuditReport
  3. When a WMI query fails or the process is running as a standard user, the affected field shows a degraded value (e.g., "Unavailable") rather than raising an exception
  4. Output path is derived from `Path(sys.executable).parent` when `sys.frozen` is set — console-printed path points to the USB drive directory, not the host PC
**Plans**: TBD

### Phase 3: HTML Character Sheet Renderer
**Goal**: A visually complete D&D/RPG-styled character sheet is rendered from mock AuditReport data and saved as an HTML file, with all RPG mappings (class, guild, realm, HP bar, spellbook, quest status) correctly displayed
**Depends on**: Phase 2
**Requirements**: OUT-01, OUT-02
**Success Criteria** (what must be TRUE):
  1. Opening the rendered HTML file in a browser shows a character sheet with header (name, class, realm, guild, level), stat block (STR/CON derived from CPU/RAM, HP bar for disk), equipment list (app slots), and footer (chronicle date)
  2. App slots display color-coded pass/fail/missing badges — green for installed, red for missing
  3. The "Quest Status" footer shows QUEST COMPLETE when all required apps are present and QUEST INCOMPLETE with a gap count when any are missing
  4. The HTML file is written to the directory passed as the output path, not to the current working directory
  5. The Jinja2 template is loaded via importlib.resources so the renderer works correctly from inside a PyInstaller bundle
**Plans**: TBD
**UI hint**: yes

### Phase 4: App Detection and Compliance Engine
**Goal**: All 7 target applications are detected via registry enumeration across all four Uninstall key paths with filesystem and service fallbacks, and the compliance gap list is populated in the AuditReport
**Depends on**: Phase 3
**Requirements**: APP-01, APP-02, APP-03, APP-04, APP-05, APP-06, APP-07
**Success Criteria** (what must be TRUE):
  1. On a machine with NinjaOne installed, NinjaRMM detection returns Installed with version; on a machine without it, returns Missing — no false positives or false negatives from stale registry keys
  2. On a machine with CrowdStrike Falcon installed, detection returns Installed and the service state (Running/Stopped) is captured; on a machine without it, returns Missing
  3. Each of the M365 apps (Word, Excel, Outlook, Teams, OneDrive) is detected individually and correctly reflects installed/missing state on a provisioned M365 machine
  4. Zoom, Chrome, and Claude desktop app are each independently detected and their registry-reported versions are captured in AppStatus
  5. APP-03 (MERP) detection uses the registry path confirmed with IT before this phase begins; if MERP is not installed the field shows Missing without crashing
**Plans**: TBD

### Phase 5: Packaging and Distribution
**Goal**: The complete tool is packaged as a PyInstaller --onedir .exe that runs from a USB flash drive without installation, writes HTML output back to the drive, and leaves no artifacts on the host PC
**Depends on**: Phase 4
**Requirements**: PKG-01, PKG-02
**Success Criteria** (what must be TRUE):
  1. Running `status_report.exe` from a USB drive on a Windows 10 or 11 machine (as a standard user, no admin rights) produces an HTML character sheet in the same directory as the .exe within 30 seconds
  2. After the .exe completes, no files are written to the host PC's filesystem (no writes to C:\, %TEMP%, %APPDATA%, or registry)
  3. The packaged .exe directory is under 50 MB
  4. Running the .exe on a CrowdStrike Falcon-enrolled machine does not trigger quarantine — test result (pass or documented fallback decision) is recorded before distribution
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Models and Hostname Parser | 0/? | Not started | - |
| 2. System Collectors | 0/? | Not started | - |
| 3. HTML Character Sheet Renderer | 0/? | Not started | - |
| 4. App Detection and Compliance Engine | 0/? | Not started | - |
| 5. Packaging and Distribution | 0/? | Not started | - |
