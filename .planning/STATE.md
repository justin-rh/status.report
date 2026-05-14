---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: System Health, Vendor Updates, and Extended CLI
status: planning
stopped_at: Roadmap created — phases 12–14 defined; ready to plan Phase 12
last_updated: "2026-05-14T00:00:00Z"
last_activity: 2026-05-14 — Roadmap v3.0 created
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
current_phase: 12
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-14)

**Core value:** IT staff plugs in, runs the tool, and instantly knows what they're looking at — device type, location, department, software status, and any gaps — no manual lookup required.
**Current focus:** v3.0 — system health collectors, vendor update detection, extended CLI flags

## Current Position

Phase: 12 — System Health Collectors
Plan: —
Status: Planning
Last activity: 2026-05-14 — Roadmap v3.0 created (3 phases, 9 requirements)

## Accumulated Context

### Roadmap Evolution

- v1.0 Phases 1–5: hostname parser, hardware collectors, D&D character sheet, app detection, PyInstaller packaging
- v2.0 Phases 6–11: warning system, HTML warnings box, NinjaOne SYSTEM compatibility, Company Portal/Intune, Mac collectors, Steve CLI flags
- Phase 11 added: Steve — CLI flags for targeted stdout output (`--name`, `--serial`, `--warnings`, `--help`)
- v3.0 Phases 12–14: system health collectors, vendor update detection, extended CLI flags

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Key constraints for v3.0:
- PyInstaller --onedir only (--onefile quarantined by CrowdStrike Falcon)
- Win32_Product prohibited (MSI reconfiguration side effect)
- Output path from sys.executable, not os.getcwd()
- No writes to host PC; all output to flash drive
- WMI callers use _wmi_module/_WMI_AVAILABLE guard pattern for CI compatibility
- Phase 12: `severity` field must be added to `Warning` dataclass before health collectors can be wired
- Phase 12: `--hidden-import win32timezone` must be added to `status_report.spec` when pywin32 is added
- Phase 12: WUA COM uses `_WIN32COM_AVAILABLE` guard (mirrors `_WMI_AVAILABLE` pattern); pywin32==311 is the only new pip dep
- Phase 13: Dell/Lenovo registry paths are uncertain — require IT confirmation before phase can close

### Pending Todos

- Confirm Dell Command Update registry path with IT before Phase 13
- Confirm Lenovo System Update registry path with IT before Phase 13
- Validate NinjaOne Mac agent path against a real Mac in the fleet (carried from v2.0)
- Hardware-gated UAT items from v2.0 carried as acknowledged debt

### Blockers/Concerns

- Phase 13: Dell/Lenovo registry paths for pending update counts are uncertain — documented as IT confirmation gate

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| App Detection | Remote access tools (APP-V2-02) | future | v3.0 planning |
| Distribution | Code-signed .exe (DIST-V2-01) | future | v1.0 close (budget decision) |
| Platform | Mac PyInstaller packaging (.app/notarization) | future | v2.0 planning |

### Acknowledged at v2.0 Milestone Close (2026-05-14) — carried forward

| Category | Item | Status |
|----------|------|--------|
| uat_gaps | Phase 04: 04-HUMAN-UAT.md — Live NinjaOne/CrowdStrike detection, M365 sign-off | partial (4 pending) |
| uat_gaps | Phase 10: 10-HUMAN-UAT.md — Mac end-to-end run, NinjaOne launchctl label | partial (2 pending) |
| verification_gaps | Phase 03: 03-VERIFICATION.md — Visual browser check of HTML character sheet | human_needed |
| verification_gaps | Phase 04: 04-VERIFICATION.md — Live app detection on real provisioned machines | human_needed |
| verification_gaps | Phase 09: 09-VERIFICATION.md — Company Portal on real machine | human_needed |
| verification_gaps | Phase 10: 10-VERIFICATION.md — Mac end-to-end run | human_needed |

## Session Continuity

Last session: 2026-05-14
Stopped at: Roadmap v3.0 created — phases 12–14 defined
Resume file: None
Next action: `/gsd-plan-phase 12`
