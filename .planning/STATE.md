# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-04)

**Core value:** IT staff plugs in, runs the tool, and instantly knows what they're looking at — device type, location, department, software status, and any gaps — no manual lookup required.
**Current focus:** Phase 1 — Models and Hostname Parser

## Current Position

Phase: 1 of 5 (Models and Hostname Parser)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-05-04 — Roadmap created, project initialized

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: PyInstaller --onedir chosen (--onefile quarantined by CrowdStrike Falcon)
- Init: Win32_Product WMI class explicitly prohibited (MSI reconfiguration side effect)
- Init: Output path derived from sys.executable, not os.getcwd()
- Init: winreg used exclusively for app detection (all four Uninstall key paths)

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 1: Hostname naming convention must be validated against real production hostnames (including international offices: AMM, AMS, KUL, HKG) before parser is finalized — confirm with IT/Edgar
- Phase 4: MERP registry path is unknown — must be confirmed with IT before APP-03 detection can be completed
- Phase 5: CrowdStrike --onedir tenant policy behavior must be tested on an enrolled machine at the start of Phase 5; code-signing budget decision needed if blocked

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Output | JSON audit log (OUT-V2-01) | v2 | Init |
| Output | Auto-open HTML in browser (OUT-V2-02) | v2 | Init |
| App Detection | Intune/Company Portal (APP-V2-01) | v2 | Init |
| App Detection | Remote access tools (APP-V2-02) | v2 | Init |
| Platform | Mac support (PLAT-V2-01) | v2 | Init |
| Distribution | Code-signed .exe (DIST-V2-01) | v2 | Init |

## Session Continuity

Last session: 2026-05-04
Stopped at: Roadmap created, all 5 phases defined, 15/15 requirements mapped
Resume file: None
