# Milestones: StatusReport

## v1.0 MVP

**Shipped:** 2026-05-05
**Archived:** 2026-05-07
**Phases:** 1–5 (5 phases, 14 plans)
**Timeline:** 2 days (2026-05-04 → 2026-05-05)
**LOC:** 2,647 Python | 35 files changed

### Delivered

Self-contained Windows .exe running from a USB flash drive that decodes a Master Electronics hostname, collects hardware stats and installed software status, and renders a D&D/RPG-styled HTML character sheet written back to the USB drive — validated on a CrowdStrike Falcon-enrolled machine as a standard user.

### Key Accomplishments

1. **Hostname parser** — pure-function decoder for the Master Electronics naming convention; 21 city codes, 4 device types, 26 tests; zero Windows API calls
2. **Data contract** — `AuditReport`, `ParsedHostname`, `AppStatus`, `CollectionResult[T]` dataclasses; platform-agnostic foundation
3. **Hardware collectors** — WMI/psutil/winreg with `_WMI_AVAILABLE` guard for CI; CPU, RAM, disk, OS, all local profiles; graceful degradation as standard user
4. **D&D character sheet** — dark navy HTML via Jinja2; stat block, HP bar, 11-app equipment table with color-coded badges, quest status banner; template bundled via `importlib.resources`
5. **App detection engine** — winreg across all 4 Uninstall paths; NinjaOne, CrowdStrike Falcon, M365 suite, Zoom, Chrome, Claude desktop, MERP
6. **CrowdStrike-safe packaging** — PyInstaller `--onedir` + `upx=False` validated on enrolled ME machine; no quarantine, no block, HTML confirmed on USB

### Known Deferred Items at Close (3)

Items acknowledged and deferred at milestone close 2026-05-07:

| Category | Item | Status |
|----------|------|--------|
| uat_gaps | Phase 04: 04-HUMAN-UAT.md — Live NinjaOne/CrowdStrike detection tests, M365 single-suite stakeholder sign-off | partial (4 pending) |
| verification_gaps | Phase 03: 03-VERIFICATION.md — Visual browser verification of HTML character sheet | human_needed |
| verification_gaps | Phase 04: 04-VERIFICATION.md — Live machine verification of app detection | human_needed |

### Archive

- `.planning/milestones/v1.0-ROADMAP.md` — full phase details
- `.planning/milestones/v1.0-REQUIREMENTS.md` — all requirements with traceability
