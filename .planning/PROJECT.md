# StatusReport

## What This Is

A self-contained Windows .exe that runs from a USB flash drive and audits a Windows PC. It decodes the Master Electronics hostname (city + device type + department + station), collects hardware stats and local user profiles, detects 11 target applications, and renders a D&D/RPG-styled HTML character sheet written back to the flash drive — with no changes to the host PC. Distributed as a PyInstaller `--onedir` bundle; validated on CrowdStrike Falcon-enrolled machines.

## Core Value

IT staff plugs in, runs the tool, and instantly knows what they're looking at — device type, location, department, software status, and any gaps — no manual lookup required.

## Current State (v1.0)

- **Shipped:** 2026-05-05
- **Codebase:** ~2,647 lines Python, 35 files
- **Stack:** Python 3.12 + psutil + wmi + winreg + Jinja2 + PyInstaller `--onedir`
- **Distribution:** CrowdStrike Falcon-safe (`--onedir` + `upx=False`); validated on enrolled ME machine
- **Tests:** 85+ passing (name parser, hardware collectors, renderer, app detection)
- **Output:** HTML character sheet written to USB `logs/` directory

## Requirements

### Validated — v1.0

- [x] **COLL-01**: Parse hostname → city, device type, department, company code, station (Master Electronics naming convention) — *Phase 1*
- [x] **COLL-02**: Collect CPU model, total RAM, disk capacity/free space, Windows OS version and build — *Phase 2*
- [x] **COLL-03**: Enumerate all local user profiles (not just current user) — *Phase 2*
- [x] **APP-01**: Detect NinjaRMM / NinjaOne (registry, all 4 Uninstall paths) — *Phase 4*
- [x] **APP-02**: Detect CrowdStrike Falcon + service state — *Phase 4*
- [x] **APP-03**: Detect MERP (Master Electronics ERP) — *Phase 4*
- [x] **APP-04**: Detect Microsoft 365 (single suite entry per D-05) — *Phase 4*
- [x] **APP-05**: Detect Zoom — *Phase 4*
- [x] **APP-06**: Detect Google Chrome — *Phase 4*
- [x] **APP-07**: Detect Claude desktop app — *Phase 4*
- [x] **OUT-01**: HTML character sheet with D&D/RPG aesthetic (stat block, equipment table, quest status) — *Phase 3*
- [x] **OUT-02**: HTML written to flash drive via `Path(sys.executable).parent` — *Phase 3+5*
- [x] **OUT-03**: Unrecognized hostnames handled gracefully (Unknown type, raw hostname, no exception) — *Phase 1*
- [x] **PKG-01**: PyInstaller `--onedir` .exe, no install required, Windows 10/11 standard user — *Phase 5*
- [x] **PKG-02**: No writes to host PC filesystem, registry, or %TEMP% — *Phase 5*

### Active — v2

- [ ] **OUT-V2-01**: JSON structured log file saved to flash drive alongside HTML
- [ ] **OUT-V2-02**: Auto-open HTML in default browser after generation
- [ ] **APP-V2-01**: Detect Intune enrollment / Company Portal
- [ ] **APP-V2-02**: Detect remote access tools (TeamViewer, AnyDesk, RDP enabled)
- [ ] **PLAT-V2-01**: Mac-compatible collectors (same data models + rendering pipeline)
- [ ] **DIST-V2-01**: Code-signed .exe to eliminate SmartScreen prompt

### Out of Scope

| Feature | Reason |
|---------|--------|
| Active Directory / domain queries | Adds network dependency; tool must work offline and on pre-enrollment machines |
| Sending data to a remote server or API | Security/trust boundary concern; flash drive is the audit trail |
| Writing any data to the host PC | Core constraint — no artifacts left behind |
| Detecting all installed software (full inventory) | Scoped to specific app list; full inventory is slow, noisy, not the goal |
| Win32_Product for app detection | Triggers MSI consistency checks — side effects on production machines |
| PyInstaller --onefile packaging | Quarantined by CrowdStrike Falcon behavioral detection |

## Context

- **Organization:** Master Electronics IT department, auditing PCs across all offices
- **Naming convention:** Created by Edgar (2025-09-10). Encodes: city code (21 locations: PHX, CHI, NYC, MIA, etc.) + device type segment + department or serial + station/identifier
  - `CITY-DEPT-###` → Warehouse Workstation
  - `CITY-SERIAL-COMPANY` → User-assigned Laptop (company codes: ME, ES, EC, AP, OL)
  - `CITY-DEPTLAP-###` → Department Laptop (contains "LAP" in segment 2)
  - `CITY-P3A/B/C-###` → P3 Warehouse device
- **Departments (warehouse):** AGG, ASI, ASP, DCC, FLX, INV, LTL, PAK, PAR, QCD, REC, RMA, SHP, STK, REV, VAD, RLT, P2P, P3A, P3B, PBT
- **Key apps detected:** NinjaOne (RMM), CrowdStrike Falcon (EDR), MERP (proprietary ERP), M365 suite, Zoom, Chrome, Claude desktop
- **Target environment:** May run on pre-enrollment, freshly imaged, or unmanaged machines; standard user, no internet required

## Constraints

- **Platform:** Windows-only for v1; architecture abstracts OS-specific calls for future Mac support
- **Distribution:** USB flash drive; no installation, no internet, no changes to host PC
- **Output location:** All output written to `Path(sys.executable).parent` (back to flash drive)
- **Packaging:** PyInstaller `--onedir` only — `--onefile` quarantined by CrowdStrike
- **Privilege level:** Standard user; documents which checks require elevation, degrades gracefully

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + PyInstaller `--onedir` for packaging | Native Windows API access via wmi/winreg/subprocess; CrowdStrike-safe with `upx=False`; same codebase targets Mac later | ✓ Validated — CrowdStrike test passed 2026-05-05 |
| HTML for character sheet output | Browser-renderable, arbitrary D&D styling, shareable/printable without tooling | ✓ Delivered — dark navy D&D sheet, 23/23 renderer tests |
| Output written to flash drive only | Keeps audit trail with IT; no artifacts on target PC | ✓ Validated Phase 5 — confirmed no host writes |
| `_wmi_module`/`_WMI_AVAILABLE` guard pattern | Enables CI testing without COM server; avoids runtime crash when wmi not installed | ✓ Pattern established — used in all WMI callers |
| `Win32_Product` prohibited | Triggers MSI reconfiguration on every installed app — production machines affected | ✓ Enforced — Win32_Processor used for CPU model |
| `station: int \| None` (not str) | ROADMAP SC1 requirement; integer semantics for station number | ✓ Enforced in parser + dataclass |
| CrowdStrike detection: 'CrowdStrike Windows Sensor'/'CrowdStrike Sensor Platform' | Actual DisplayName on enrolled machines (confirmed from live registry); not 'CrowdStrike Falcon' | ✓ Validated — live registry confirmed |
| M365 single suite entry (D-05) | IT audit workflow needs one compliance row, not five; reduces noise | ⚠ Stakeholder sign-off deferred to v2 validation |
| MERP: filesystem-first at PVX Plus path | Registry path unknown; filesystem check most reliable given D-02 CONTEXT | ✓ Implemented |
| `ir.files('renderer').joinpath(...)` single-string form | Required for PyInstaller `importlib.resources` compatibility | ✓ Enforced — no PackageLoader or FileSystemLoader |
| Code signing deferred to v2 | CrowdStrike test passed without it; budget decision deferred | — v2 backlog (DIST-V2-01) |
| JSON output deferred to v2 | v1 scope decision; HTML is sufficient for immediate IT use case | — v2 backlog (OUT-V2-01) |

---
*Last updated: 2026-05-07 after v1.0 milestone*
