# Milestones: SCRY

## v3.0 — System Health, Vendor Updates, and Extended CLI

**Shipped:** 2026-05-18
**Archived:** 2026-05-19
**Phases:** 12–15 (4 phases, 9 plans)
**Timeline:** 4 days (2026-05-14 → 2026-05-18)
**LOC:** ~+1,903 net new Python | 29 source files changed (+1,629/-85 excl. `.planning`) | 70 commits | 291 tests (88 new, +43%)

### Delivered

Renamed the project to SCRY, surfaced system health signals (uptime, pending Windows update count, yellow/red uptime warnings with hibernation note), added passive vendor update detection (Dell Command Update via XML, Lenovo System Update via registry — no vendor CLIs invoked), and extended the CLI with `--json` (full AuditReport serialization), `--output PATH` (writable-path override), and `--app NAME` (single-app stdout query with case-insensitive matching and optional JSON blob).

### Key Accomplishments

1. **SCRY rename** — Full rebrand (StatusReport → SCRY); `scry.spec` → `dist/scry_v3.0/scry.exe`; output filename `{date}_scry_{hostname}.html`; 203 tests preserved
2. **System health collectors** — `psutil.boot_time()` uptime (Win+Mac); WUA COM pending update count with `_WIN32COM_AVAILABLE` guard; `Warning.level` field (positional-LAST for backward-compat); `UPTIME_WARN` yellow (>7d), `UPTIME_STALE` red (>30d) with hibernation note; `badge-critical` CSS class
3. **Vendor update detection** — Dell DCU via passive `DCUApplicableUpdates.xml` parse; Lenovo LSU via registry only; never invokes `dcu-cli.exe` or `tvsu.exe`; `VendorUpdateStatus` dataclass; gated by `--updates` flag; Mac silent no-op
4. **Extended CLI flags** — `--json` (full `dataclasses.asdict()` serialization, recurses through nested dataclasses); `--output PATH` overrides `logs_dir`; `--app NAME` case-insensitive single-app stdout with `--app --json` JSON blob variant; unknown app → stderr + exit 1
5. **Quality** — 88 new tests (203 → 291, +43%); zero regressions across the rename; full suite green at close
6. **Audit hygiene** — 3-source cross-reference of requirements (VERIFICATION.md + SUMMARY frontmatter + REQUIREMENTS.md checkboxes); integration checker verified all 12 requirement integrations and 11 E2E flows

### Audit

- Status: **passed** — 11/11 requirements satisfied, 4/4 phases verified, 12/12 integration paths wired, 11/11 flows pass
- Report: `.planning/milestones/v3.0-MILESTONE-AUDIT.md`

### Known Deferred Items at Close (11)

Items acknowledged and deferred at milestone close 2026-05-19 — all hardware-gated or visual:

| Category | Item | Status |
|----------|------|--------|
| uat_gaps | Phase 13: Live SYSTEM/Admin uptime + pending update count; yellow > 7d badge; red > 30d badge with hibernation note; standard-user N/A degradation | partial (4 pending) |
| uat_gaps | Phase 14: Live Dell DCU pending count on real machine; live non-Dell/non-Lenovo "Not installed"; 3 visual HTML render checks for vendor row states | partial (5 pending) |
| open_blockers | Dell Command Update registry path uncertainty — needs IT confirmation | carried |
| open_blockers | Lenovo System Update registry path uncertainty — needs IT confirmation | carried |

### Carried Forward from v2.0 (still open at v3.0 close)

| Category | Item | Status |
|----------|------|--------|
| uat_gaps | Phase 04: Live NinjaOne/CrowdStrike detection, M365 sign-off | partial (4 pending) |
| uat_gaps | Phase 10: Mac end-to-end run, NinjaOne launchctl label | partial (2 pending) |
| verification_gaps | Phase 03: Visual browser check of HTML character sheet | human_needed |
| verification_gaps | Phase 04: Live app detection on real provisioned machines | human_needed |
| verification_gaps | Phase 09: Company Portal on real machine | human_needed |
| verification_gaps | Phase 10: Mac end-to-end run | human_needed |

### Tech Debt at Close

- `writers.write_html` dead code: hard-coded `scry.html` filename in unreachable path — recommend deprecation in v3.1
- `_run_cli --updates` runs vendor collection but discards data — wasted work, not a bug
- `--app NAME --output PATH` silently ignores `--output` (matches D-08/D-13 spec; not surfaced to user)
- REQUIREMENTS.md checkbox bookkeeping lag for the third milestone running — worth automating before v4.0

### Archive

- `.planning/milestones/v3.0-ROADMAP.md` — full phase details
- `.planning/milestones/v3.0-REQUIREMENTS.md` — all requirements with traceability
- `.planning/milestones/v3.0-MILESTONE-AUDIT.md` — full audit report

---

## v2.0 — Warnings, Mac Parity, and NinjaOne Compatibility

**Shipped:** 2026-05-12
**Archived:** 2026-05-14
**Phases:** 6–11 (6 phases, 12 plans)
**Timeline:** 5 days (2026-05-07 → 2026-05-12)
**LOC:** ~2,600 net new Python | 85 files changed | 203 tests

### Delivered

Extended the audit tool with proactive health warnings (OS version, disk space, rename), Company Portal/Intune enrollment detection, NinjaOne SYSTEM-account compatibility with stdout summary line, full macOS hardware/profile/app collector parity, and Steve CLI flags (`--name`, `--serial`, `--warnings`, `--help`) for targeted stdout queries without generating a full character sheet.

### Key Accomplishments

1. **Warning system** — `Warning` dataclass + `evaluate_warnings()` with OS/disk/rename checks; 17 boundary tests; collapsible HTML box with `<details open>` auto-expand
2. **NinjaOne compatibility** — `sys.stdin.isatty()` guard on all interactive calls; `[SUMMARY]` stdout line on every run; SYSTEM-account safe
3. **Company Portal + Intune** — MSIX detection + `HKLM\Enrollments` UPN enrollment check; MDM status in Service column
4. **Mac collectors** — `collectors/mac/` package: Intel + Apple Silicon CPU, `sw_vers`, `psutil`, `pwd`; 7-app `MAC_APP_SPECS` via plistlib/launchctl; platform dispatch in `collect_all()` and `main.py`
5. **Steve CLI flags** — argparse branch exits before full pipeline; `--name/--serial/--warnings/--help` with union collection scope; 8 new tests
6. **Logo watermark** — ME logo embedded in character sheet; dark navy aesthetic preserved

### Known Deferred Items at Close (6)

Items acknowledged and deferred at milestone close 2026-05-14 — all hardware-gated:

| Category | Item | Status |
|----------|------|--------|
| uat_gaps | Phase 04: 04-HUMAN-UAT.md — Live NinjaOne/CrowdStrike detection, M365 sign-off | partial (4 pending) |
| uat_gaps | Phase 10: 10-HUMAN-UAT.md — Mac end-to-end run, NinjaOne launchctl label | partial (2 pending) |
| verification_gaps | Phase 03: 03-VERIFICATION.md — Visual browser check of HTML character sheet | human_needed |
| verification_gaps | Phase 04: 04-VERIFICATION.md — Live app detection on real provisioned machines | human_needed |
| verification_gaps | Phase 09: 09-VERIFICATION.md — Company Portal on real machine | human_needed |
| verification_gaps | Phase 10: 10-VERIFICATION.md — Mac end-to-end run | human_needed |

### Archive

- `.planning/milestones/v2.0-ROADMAP.md` — full phase details
- `.planning/milestones/v2.0-REQUIREMENTS.md` — all requirements with traceability

---

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
