# SCRY

## What This Is

A self-contained Windows .exe (and macOS compatible) that runs from a USB flash drive and audits a PC. It decodes the Master Electronics hostname, collects hardware stats and local user profiles, detects 11 target applications, evaluates health warnings (OS version, disk space, rename status), and renders a D&D/RPG-styled HTML character sheet written back to the flash drive — with no changes to the host PC. Distributed as a PyInstaller `--onedir` bundle; supports CLI flags for targeted stdout queries without generating a full report.

## Core Value

IT staff plugs in, runs the tool, and instantly knows what they're looking at — device type, location, department, software status, and any gaps — no manual lookup required.

## Current Milestone: v3.0 System Health, Vendor Updates, and Extended CLI

**Goal:** Surface system health signals and extend CLI output options so IT staff can assess machine state and integrate output into NinjaOne workflows.

**Target features:**
- System health collectors — uptime since last reboot, pending Windows update count, `UPTIME_STALE` warning if uptime > N days
- Vendor update detection — pending Dell Command Update count, pending Lenovo System Update count
- Extended CLI flags — `--json` output, `--output <path>` override, `--app <name>` single-app check with JSON support

## Current State (v3.0 complete — 2026-05-18)

- **Last shipped:** v2.0 archived 2026-05-14; 6 phases (6–11), 12 plans, 203 tests passing
- **Stack:** Python 3.12 + psutil + wmi + winreg + Jinja2 + PyInstaller `--onedir`; 4 phases (12–15), 9 plans, 291 tests passing
- **v3.0 complete:** All 4 phases complete — SCRY rename, system health collectors, vendor update detection, extended CLI flags
- **Phase 15 complete:** Extended CLI flags — `--json`, `--output PATH`, `--app NAME`; 7 new tests; 291 total tests passing
- **Pending human testing:** Live NinjaOne/CrowdStrike detection, Mac end-to-end run, Company Portal on real machine, visual HTML check, Dell/Lenovo registry path confirmation (all hardware-gated; carried as acknowledged debt)
- **Current milestone:** v3.0 complete — ready for `/gsd-complete-milestone`

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

### Validated — v2.0

- [x] **APP-V2-01**: Detect Company Portal (UWP) + Intune MDM enrollment status — *Phase 9* (live machine validation deferred)
- [x] **WARN-01**: Warn when device runs Windows 10 or earlier (OS build < 22000) — *Phase 6*
- [x] **WARN-02**: Warn when disk free space ≤ 15% of total capacity — *Phase 6*
- [x] **WARN-03**: Collapsible warnings box; auto-expand on any warning; green "All checks passed" when all pass — *Phase 7* ✓
- [x] **NINJA-01**: Exe runs under SYSTEM account without hanging or crashing — *Phase 8* (live SYSTEM run deferred)
- [x] **NINJA-02**: `[SUMMARY]` stdout line on every run for NinjaOne log capture — *Phase 8* (live log capture deferred)
- [x] **PLAT-V2-01**: Mac hardware collectors — CPU (Intel + Apple Silicon), RAM, disk, macOS version — *Phase 10* (live Mac deferred)
- [x] **PLAT-V2-02**: Mac profile enumeration — non-system accounts, UID ≥ 501 — *Phase 10* (live Mac deferred)
- [x] **PLAT-V2-03**: Mac app detection — 7 target apps via plistlib/launchctl — *Phase 10* ✓
- [x] **PLAT-V2-04**: D&D HTML character sheet rendered and saved on macOS — *Phase 10* (live Mac deferred)
- [x] **CLI-01**: `--name`, `--serial`, `--warnings`, `--help` flags via argparse; exits before full pipeline — *Phase 11* ✓

### Validated — v3.0

- [x] **HEALTH-01**: Pending Windows update count surfaced in character sheet — *Phase 13*
- [x] **HEALTH-02**: Uptime since last reboot surfaced in character sheet / warnings — *Phase 13*
- [x] **WARN-04**: UPTIME_STALE warning when uptime exceeds threshold (N days, configurable constant) — *Phase 13*
- [x] **VENDOR-01**: Pending Dell Command Update count (Windows) — *Phase 14* (IT registry path confirmation deferred)
- [x] **VENDOR-02**: Pending Lenovo System Update count (Windows) — *Phase 14* (IT registry path confirmation deferred)
- [x] **OUT-V3-01**: `--json` flag serializes AuditReport to JSON alongside HTML; `dataclasses.asdict()` — *Phase 15*
- [x] **OUT-V3-02**: `--output <path>` flag overrides default `logs/`; any writable path accepted (D-02) — *Phase 15*
- [x] **CLI-V3-01**: `--app <name>` single-app detection to stdout; `--app --json` prints JSON blob; case-insensitive match — *Phase 15*

### Deferred — Not v3.0 scope

- [ ] **APP-V2-02**: Detect remote access tools (TeamViewer, AnyDesk, RDP enabled)
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

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-18 — Phase 15 complete (Extended CLI Flags); v3.0 milestone complete*
