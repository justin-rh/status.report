# StatusReport

## What This Is

A self-contained Windows executable that runs from a USB flash drive and performs an IT audit of the host PC. It decodes the device name using Master Electronics' naming convention (city + device type + department + station), collects system info and installed software status, and presents everything as a D&D-style HTML character sheet — while writing a structured log back to the flash drive.

## Core Value

IT staff plugs in, runs the tool, and instantly knows what they're looking at — device type, location, department, software status, and any gaps — no manual lookup required.

## Requirements

### Validated

- [x] Parse PC hostname into: city, device type (warehouse workstation, user-assigned laptop, dept laptop, P3), department code, company code, and station number using the Master Electronics naming convention — *Validated in Phase 1: Models and Hostname Parser*
- [x] Handle unrecognized or non-conforming device names gracefully (display raw hostname with "Unknown" device type, no exception raised) — *Validated in Phase 1: Models and Hostname Parser*

### Active
- [ ] Collect system information: hostname, OS version and build, CPU model, RAM amount, disk capacity/free space, currently logged-in user, and local user profiles
- [ ] Detect presence and version of: NinjaRMM/NinjaOne, Microsoft 365 apps (Word, Excel, Outlook, Teams, OneDrive), Intune/Company Portal, CrowdStrike Falcon, Zoom, Google Chrome, Claude desktop app, and MERP (Master Electronics ERP)
- [ ] Generate an HTML character sheet with D&D/RPG styling (stats, "class", equipment slots, etc.) displaying all collected data in a thematic layout
- [ ] Write a structured log file (JSON) back to the flash drive with full collected data and a timestamp
- [ ] Package as a self-contained .exe (PyInstaller) that runs on Windows without installation


### Out of Scope

- Mac/Linux support — deferred to a future milestone; Python codebase will be structured to make this addition clean
- Active Directory / domain queries — adds network dependency; tool must work offline or on machines not yet domain-joined
- Sending data to a remote server or API — security and trust boundary concern; flash drive is the audit trail
- Remote access tool detection (TeamViewer, AnyDesk) — not in the v1 requirements list

## Context

- **Organization:** Master Electronics IT department, used by IT staff auditing PCs across all offices
- **Naming convention:** Created by Edgar (2025-09-10). Encodes: city code (21 locations: PHX, CHI, NYC, MIA, etc.) + device type segment + department or serial + station/identifier
  - `CITY-DEPT-###` → Warehouse Workstation
  - `CITY-SERIAL-COMPANY` → User-assigned Laptop (company codes: ME, ES, EC, AP, OL)
  - `CITY-DEPTLAP-###` → Department Laptop (contains "LAP" in segment 2)
  - `CITY-P3A/B/C-###` → P3 Warehouse device
- **Departments (warehouse):** AGG, ASI, ASP, DCC, FLX, INV, LTL, PAK, PAR, QCD, REC, RMA, SHP, STK, REV, VAD, RLT, P2P, P3A, P3B, PBT
- **Key apps:** NinjaOne is the RMM; CrowdStrike is the EDR; MERP is proprietary to Master Electronics
- **Target runtime environment:** May be run by IT staff on machines that could be pre-enrollment, freshly imaged, or unmanaged — tool should not require admin or elevated privileges to collect basic info (will note where elevation would improve results)

## Constraints

- **Platform:** Windows-only for v1; Python codebase should abstract OS-specific calls to enable Mac support in a future milestone
- **Distribution:** Must run from USB flash drive; no installation, no internet required, no changes made to the host PC (read-only audit)
- **Output location:** All output (HTML + JSON log) written to the directory the .exe was launched from (i.e., back to the flash drive)
- **Packaging:** PyInstaller one-file .exe — keep binary under 50MB if possible
- **Privilege level:** Design for standard user; document which checks require elevation and degrade gracefully if not elevated

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + PyInstaller for packaging | Native Windows API access via `wmi`/`winreg`/`subprocess`; PyInstaller one-file .exe runs without install; same codebase can target Mac later | — Pending |
| HTML for character sheet output | Browser-renderable, arbitrary D&D styling, shareable/printable without additional tooling | — Pending |
| JSON for log format | Structured, parseable by future tooling or dashboards; human-readable enough for spot checks | — Pending |
| Output written to flash drive only | Keeps audit trail with IT staff; avoids leaving artifacts on the target PC | — Pending |

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
*Last updated: 2026-05-04 after Phase 1 completion*
