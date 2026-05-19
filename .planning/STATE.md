---
gsd_state_version: 1.0
milestone: v3.1
milestone_name: "Cleanup"
status: defining-requirements
stopped_at: milestone v3.1 started
last_updated: "2026-05-19T00:00:00Z"
last_activity: 2026-05-19 — Milestone v3.1 Cleanup started; PROJECT.md updated, defining requirements
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-19 for v3.1 Cleanup)

**Core value:** IT staff plugs in, runs the tool, and instantly knows what they're looking at — device type, location, department, software status, and any gaps — no manual lookup required.
**Current focus:** v3.1 Cleanup — close 20 hardware-gated UAT items, confirm Dell/Lenovo registry paths with IT, add REQUIREMENTS automation hook, remove tech debt.

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-05-19 — Milestone v3.1 Cleanup started

## Accumulated Context

### Roadmap Evolution

- v1.0 Phases 1–5 (shipped 2026-05-05, archived 2026-05-07)
- v2.0 Phases 6–11 (shipped 2026-05-12, archived 2026-05-14)
- v3.0 Phases 12–15 (shipped 2026-05-18, archived 2026-05-19)
  - Phase 12: SCRY rename
  - Phase 13: System health collectors (uptime, pending updates, yellow/red severity)
  - Phase 14: Vendor update detection (Dell DCU XML, Lenovo LSU registry)
  - Phase 15: Extended CLI flags (--json, --output, --app)

### Decisions

Full decision log in PROJECT.md Key Decisions table. Standing constraints across all milestones:

- PyInstaller --onedir only (--onefile quarantined by CrowdStrike Falcon)
- Win32_Product prohibited (MSI reconfiguration side effect)
- Output path from sys.executable, not os.getcwd()
- No writes to host PC enforced by code, no longer by CLI validation (D-02/D-03 — `--output PATH` accepts any writable path)
- WMI / pwd / win32com callers use `_*_AVAILABLE` guard pattern for CI compatibility
- Vendor detection is registry+file passive only — no CLI subprocess invocation
- `Warning.level` is positional-LAST in dataclass for backward-compat

### Pending Hardware-Gated Validation (carried into next milestone)

**v3.0 new (11 items):**
- Live Windows SYSTEM/Admin run: uptime + pending update count populated values (Phase 13)
- Real machine uptime > 7 days → yellow UPTIME_WARN badge (Phase 13)
- Real machine uptime > 30 days → red UPTIME_STALE badge + hibernation note (Phase 13)
- Standard-user (non-admin) "N/A" degradation for pending updates (Phase 13)
- Live Dell DCU pending count on real Dell machine (Phase 14)
- Live non-Dell/non-Lenovo "Not installed" rendering (Phase 14)
- 3 visual HTML render checks (test_vendor_render_case1/2/3.html) for vendor row states (Phase 14)

**v3.0 open blockers (2 items):**
- Dell Command Update registry path uncertainty — needs IT confirmation
- Lenovo System Update registry path uncertainty — needs IT confirmation

**Carried from v2.0 (6 items):**
- Phase 04: Live NinjaOne/CrowdStrike detection, M365 sign-off (4 pending)
- Phase 10: Mac end-to-end run, NinjaOne launchctl label (2 pending)
- Phase 03: Visual browser check of HTML character sheet
- Phase 09: Company Portal on real machine

**Total deferred: 20 items.** Suggest scheduling a "live machine day" early in next milestone.

### Tech Debt at v3.0 Close

- `writers.write_html` is dead code from the user pipeline (`main.py` calls `render_html()` directly); hard-coded "scry.html" filename in unreachable path — recommend deprecation in v3.1
- `_run_cli --updates` runs `collect_pending_updates` + `collect_vendor_updates` but discards the data (only prints hostname/serial/warnings) — wasted work, not a bug
- `--app NAME --output PATH` silently ignores `--output` (matches D-08/D-13; not surfaced to user)
- REQUIREMENTS.md checkbox bookkeeping lag for the third milestone running — install an automation hook before v4.0

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| App Detection | Remote access tools (APP-V2-02) | future | v3.0 planning |
| Distribution | Code-signed .exe (DIST-V2-01) | future | v1.0 close (budget decision) |
| Platform | Mac PyInstaller packaging (.app/notarization) | future | v2.0 planning |
| Vendor | LSU-PENDING — Lenovo System Update pending count | future | v3.0 close (no passive source) |

### Acknowledged at v3.0 Milestone Close (2026-05-19)

| Category | Item | Status |
|----------|------|--------|
| uat_gaps | Phase 13: hardware-gated uptime + pending update + yellow/red badge + standard-user N/A | partial (4 pending) |
| uat_gaps | Phase 14: live Dell DCU + non-Dell/non-Lenovo + visual HTML render | partial (5 pending) |
| open_blockers | Dell Command Update registry path needs IT confirmation | carried |
| open_blockers | Lenovo System Update registry path needs IT confirmation | carried |
| uat_gaps | Phase 04: Live NinjaOne/CrowdStrike detection, M365 sign-off | partial (4 pending) — carried from v2.0 |
| uat_gaps | Phase 10: Mac end-to-end run, NinjaOne launchctl label | partial (2 pending) — carried from v2.0 |
| verification_gaps | Phase 03: Visual browser check of HTML character sheet | human_needed — carried from v1.0 |
| verification_gaps | Phase 04: Live app detection on real provisioned machines | human_needed — carried from v1.0 |
| verification_gaps | Phase 09: Company Portal on real machine | human_needed — carried from v2.0 |
| verification_gaps | Phase 10: Mac end-to-end run | human_needed — carried from v2.0 |

## Session Continuity

Last session: 2026-05-19T00:00:00Z
Stopped at: v3.0 milestone archived (ROADMAP collapsed, REQUIREMENTS.md removed, git tag v3.0 created)
Resume file: None
Next action: Run `/gsd-new-milestone` to plan the next milestone, or run `/gsd-progress` to confirm current state.
