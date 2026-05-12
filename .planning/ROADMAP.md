# Roadmap: StatusReport

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5 (shipped 2026-05-05)
- ✅ **v2.0 Warnings, Mac Parity, and NinjaOne Compatibility** — Phases 6–10 (shipped 2026-05-08)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–5) — SHIPPED 2026-05-05</summary>

- [x] **Phase 1: Models and Hostname Parser** — 4/4 plans — completed 2026-05-04
- [x] **Phase 2: System Collectors** — 2/2 plans — completed 2026-05-04
- [x] **Phase 3: HTML Character Sheet Renderer** — 2/2 plans — completed 2026-05-04
- [x] **Phase 4: App Detection and Compliance Engine** — 2/2 plans — completed 2026-05-05
- [x] **Phase 5: Packaging and Distribution** — 3/3 plans — completed 2026-05-05

Full phase details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### v2.0 — Warnings, Mac Parity, and NinjaOne Compatibility

- [x] **Phase 6: Warning Data Model** — Warning dataclass + evaluate_warnings() module; pure Python, no OS dependency — completed 2026-05-07
- [x] **Phase 7: HTML Warnings Section** — Collapsible warnings box in character sheet template; wired into renderer and main.py — completed 2026-05-07
- [x] **Phase 8: NinjaOne Compatibility** — SYSTEM-account execution safety; stdout summary line for log capture — completed 2026-05-07
- [x] **Phase 9: Company Portal Detection** — Company Portal MSIX detection + Intune MDM enrollment registry check — completed 2026-05-08
- [x] **Phase 10: Mac Collectors** — Full macOS hardware, profile, and app collectors; HTML output on Mac
- [x] **Phase 11: Steve** — CLI flags for targeted stdout output: `--name`, `--serial`, `--warnings`, `--help` — completed 2026-05-12

## Phase Details

### Phase 6: Warning Data Model
**Goal**: The tool has a structured warnings layer that evaluates health conditions against collected data and produces typed Warning objects
**Depends on**: Nothing (pure Python, no OS dependency)
**Requirements**: WARN-01, WARN-02
**Success Criteria** (what must be TRUE):
  1. Warning dataclass instantiates with code, severity, message, and optional detail fields
  2. evaluate_warnings() called with a mock AuditReport returns a WARN for Windows 10 (build < 22000) and OK for Windows 11
  3. evaluate_warnings() called with a mock AuditReport returns a WARN when disk free is at or below 15% and OK when above
  4. AuditReport.warnings field defaults to empty list; all 85+ existing tests still pass with no modification
**Plans**: 2 plans
Plans:
- [x] 06-01-PLAN.md — Add Warning dataclass to models.py and implement health_checks.py with evaluate_warnings()
- [x] 06-02-PLAN.md — Write parametrized test suite for evaluate_warnings() boundary cases

### Phase 7: HTML Warnings Section
**Goal**: The character sheet renders a collapsible warnings box that auto-expands on any warning and shows green "All checks passed" when all pass
**Depends on**: Phase 6
**Requirements**: WARN-03
**Success Criteria** (what must be TRUE):
  1. Character sheet rendered with zero warnings shows a collapsed green "All checks passed" summary header
  2. Character sheet rendered with one or more warnings auto-expands the warnings box and displays each check with OK or WARN status
  3. Existing renderer tests pass with warnings=[] (no regression from ad-hoc os_warning/rename_warning flag removal)
  4. New renderer tests confirm correct HTML output for reports containing Warning objects
**Plans**: 3 plans
Plans:
- [x] 07-01-PLAN.md — Add _check_rename helper to health_checks.py; update test_health_checks.py with RENAME_REQUIRED tests and always-three guarantee
- [x] 07-02-PLAN.md — Update renderer/_build_context() and character_sheet.html with warnings box; wire evaluate_warnings in main.py
- [x] 07-03-PLAN.md — Add warnings box HTML tests to test_renderer.py; populate MOCK_REPORT.warnings
**UI hint**: yes

### Phase 8: NinjaOne Compatibility
**Goal**: The exe runs cleanly under the NinjaOne SYSTEM account — no hangs, no blind spots, stdout captured by the activity log
**Depends on**: Phase 6 (warnings needed for summary line warning count)
**Requirements**: NINJA-01, NINJA-02
**Success Criteria** (what must be TRUE):
  1. Exe launched with no TTY (stdin redirected to /dev/null or equivalent) exits cleanly without hanging
  2. os.startfile() and input() are guarded by sys.stdin.isatty() so headless runs never prompt or open a browser
  3. Stdout prints a structured [SUMMARY] line (hostname, OS version, CPU, RAM, disk %, warning count) after every run; line appears in NinjaOne script activity log
  4. HKCU registry reads (MSIX detection for Claude and Company Portal) return "Not Found" without exception when running under the SYSTEM account
**Plans**: 1 plan
Plans:
- [x] 08-01-PLAN.md — Add [SUMMARY] stdout line and isatty() guard to main.py; create tests/test_main.py

### Phase 9: Company Portal Detection
**Goal**: IT staff can see whether Company Portal is installed and whether the device is enrolled in Intune, as distinct signals in the character sheet
**Depends on**: Phase 8 (SYSTEM-context MSIX fix must be in place before Company Portal is testable via NinjaOne)
**Requirements**: APP-V2-01
**Success Criteria** (what must be TRUE):
  1. Company Portal appears in the equipment table on a machine where the UWP app is installed
  2. MDM enrollment status (Enrolled / Not Enrolled) appears in the Service column for the Company Portal row, derived from HKLM Enrollments UPN value
  3. GUID keys without a UPN value are treated as stale artifacts and do not report as enrolled (no false positives)
  4. "Not Found" is shown cleanly in the equipment table on a machine where Company Portal is not installed
**Plans**: 1 plan
Plans:
- [x] 09-01-PLAN.md — Add _detect_mdm_enrollment() helper, Company Portal APP_SPECS entry, MDM hook in _detect_one_app(), and 6 new tests in test_app_collector.py

### Phase 10: Mac Collectors
**Goal**: Running the tool on macOS produces the same D&D HTML character sheet as Windows, populated with Mac hardware stats, user profiles, and app detection results
**Depends on**: Phase 6, Phase 7 (data model and HTML template must be stable before Mac output is validated)
**Requirements**: PLAT-V2-01, PLAT-V2-02, PLAT-V2-03, PLAT-V2-04
**Success Criteria** (what must be TRUE):
  1. On macOS, hardware stats (CPU model for both Intel and Apple Silicon, total RAM, disk capacity and free space, macOS version) are collected and appear correctly in the stat block
  2. Local user profiles enumerated on macOS show only human accounts (UID >= 501), matching the Windows profile enumeration behavior
  3. All 7 target apps (NinjaOne, CrowdStrike Falcon, Microsoft 365, Zoom, Google Chrome, Claude Desktop, Company Portal) report either detected with version or "Not Found" cleanly — no unhandled exceptions
  4. An HTML character sheet is written to logs/ relative to the exe on macOS, with the same D&D aesthetic and all populated fields
**Plans**: 4 plans
Plans:
- [x] 10-01-PLAN.md — Create collectors/mac/ package and implement hardware.py (collect_hardware + collect_profiles)
- [x] 10-02-PLAN.md — Implement collectors/mac/apps.py (MAC_APP_SPECS + detect_apps for 7 target apps)
- [x] 10-03-PLAN.md — Wire platform dispatch in collectors/__init__.py and Mac output path + open in main.py
- [x] 10-04-PLAN.md — Write test_mac_hardware_collector.py, test_mac_app_collector.py, test_mac_profile_collector.py
**UI hint**: yes

### Phase 11: Steve
**Goal**: The tool accepts CLI flags for targeted stdout output so IT staff can query specific fields without generating a full character sheet
**Depends on**: Phase 1 (hostname/PC name), Phase 2 (serial number via system collectors), Phase 6 (warnings data model)
**Requirements**: CLI-01
**Success Criteria** (what must be TRUE):
  1. `status_report.exe --name` prints the PC hostname to stdout and exits with code 0
  2. `status_report.exe --serial` prints the device serial number to stdout and exits with code 0
  3. `status_report.exe --warnings` prints each active warning (one per line) to stdout and exits with code 0; prints nothing (empty output) when no warnings
  4. `status_report.exe --help` prints all available flags with brief descriptions and exits with code 0
  5. Running with no flags continues to produce the full HTML character sheet with no regression (all existing tests pass)
**Plans**: 1 plan
Plans:
- [x] 11-01-PLAN.md — Add argparse CLI branch to main.py and CLI flag tests to test_main.py

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Models and Hostname Parser | v1.0 | 4/4 | Complete | 2026-05-04 |
| 2. System Collectors | v1.0 | 2/2 | Complete | 2026-05-04 |
| 3. HTML Character Sheet Renderer | v1.0 | 2/2 | Complete | 2026-05-04 |
| 4. App Detection and Compliance Engine | v1.0 | 2/2 | Complete | 2026-05-05 |
| 5. Packaging and Distribution | v1.0 | 3/3 | Complete | 2026-05-05 |
| 6. Warning Data Model | v2.0 | 2/2 | Complete | 2026-05-07 |
| 7. HTML Warnings Section | v2.0 | 3/3 | Complete | 2026-05-07 |
| 8. NinjaOne Compatibility | v2.0 | 1/1 | Complete | 2026-05-07 |
| 9. Company Portal Detection | v2.0 | 1/1 | Complete | 2026-05-07 |
| 10. Mac Collectors | v2.0 | 4/4 | Complete | 2026-05-08 |
| 11. Steve | v2.0 | 1/1 | Complete | 2026-05-12 |
