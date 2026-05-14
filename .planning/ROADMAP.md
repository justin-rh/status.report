# Roadmap: StatusReport

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5 (shipped 2026-05-05)
- ✅ **v2.0 Warnings, Mac Parity, and NinjaOne Compatibility** — Phases 6–11 (shipped 2026-05-12)
- 🔄 **v3.0 System Health, Vendor Updates, and Extended CLI** — Phases 12–14 (in progress)

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

<details>
<summary>✅ v2.0 Warnings, Mac Parity, and NinjaOne Compatibility (Phases 6–11) — SHIPPED 2026-05-12</summary>

- [x] **Phase 6: Warning Data Model** — 2/2 plans — completed 2026-05-07
- [x] **Phase 7: HTML Warnings Section** — 3/3 plans — completed 2026-05-07
- [x] **Phase 8: NinjaOne Compatibility** — 1/1 plan — completed 2026-05-07
- [x] **Phase 9: Company Portal Detection** — 1/1 plan — completed 2026-05-08
- [x] **Phase 10: Mac Collectors** — 4/4 plans — completed 2026-05-08
- [x] **Phase 11: Steve** — 1/1 plan — completed 2026-05-12

Full phase details: `.planning/milestones/v2.0-ROADMAP.md`

</details>

<details open>
<summary>🔄 v3.0 System Health, Vendor Updates, and Extended CLI (Phases 12–14) — IN PROGRESS</summary>

- [ ] **Phase 12: System Health Collectors** — Add `severity` field to `Warning`, collect uptime and pending Windows update count, emit UPTIME_WARN and UPTIME_STALE warnings
- [ ] **Phase 13: Vendor Update Detection** — Surface Dell Command Update and Lenovo System Update status in the character sheet
- [ ] **Phase 14: Extended CLI Flags** — `--json`, `--output <path>`, and `--app <name>` flags with JSON support

</details>

## Phase Details

### Phase 12: System Health Collectors
**Goal**: IT staff can see machine health signals — uptime and pending Windows update count — directly in the character sheet, with automatic warnings when uptime exceeds safe thresholds
**Depends on**: Phase 11 (v2.0 complete)
**Requirements**: HEALTH-01, HEALTH-02, WARN-04, WARN-05
**Success Criteria** (what must be TRUE):
  1. IT staff sees uptime formatted as "12 days 4 hours" in the stat block of a freshly run character sheet
  2. IT staff sees pending Windows update count (e.g. "3 pending") in the stat block; a machine where WUA is inaccessible as standard user shows "N/A" — no crash
  3. A machine with uptime > 7 days shows a yellow (caution) warning in the collapsible warnings box; the box auto-expands
  4. A machine with uptime > 30 days shows a red (critical) warning noting that hibernation time is counted; the box auto-expands
  5. All existing 203 tests pass after the `severity` field is added to the `Warning` dataclass (no regression)
**Plans**: TBD
**UI hint**: yes

### Phase 13: Vendor Update Detection
**Goal**: IT staff can see whether Dell Command Update or Lenovo System Update is installed and how many vendor updates are pending, without the tool invoking any vendor CLI
**Depends on**: Phase 12
**Requirements**: VENDOR-01, VENDOR-02
**Success Criteria** (what must be TRUE):
  1. On a Dell machine where DCU has run at least once, IT staff sees the pending update count from `DCUApplicableUpdates.xml` in the character sheet (e.g. "2 pending")
  2. On a Dell machine where DCU has never run or the XML is absent, IT staff sees "Unknown (no scan data)" — not 0
  3. On a non-Dell machine, the character sheet shows "Not installed" for Dell Command Update with no error
  4. On a Lenovo machine, the character sheet shows Lenovo System Update installation status; pending count displays as "N/A" (passive source unavailable in v3.0)
  5. On a non-Lenovo machine, the character sheet shows "Not installed" for Lenovo System Update with no error
**Plans**: TBD

### Phase 14: Extended CLI Flags
**Goal**: IT staff and NinjaOne scripts can retrieve audit output as JSON, override the output path, and query a single app — without generating a full HTML report when not needed
**Depends on**: Phase 13
**Requirements**: OUT-V3-01, OUT-V3-02, CLI-V3-01
**Success Criteria** (what must be TRUE):
  1. Running `status_report.exe --json` produces a valid JSON file in `logs/` alongside the HTML report; the JSON deserializes back to the same field values present in the HTML
  2. Running `status_report.exe --output D:\audit_results` writes both HTML and JSON to that path; running with a host-PC path (e.g. `C:\Users\...`) is rejected with a clear error and no files written
  3. Running `status_report.exe --app ninjaone` prints a single-line result to stdout and exits without generating an HTML or JSON report
  4. Running `status_report.exe --app ninjaone --json` prints a JSON blob for that one app to stdout; app name matching is case-insensitive ("NinjaOne", "ninjaone", "NINJAONE" all resolve)
**Plans**: TBD
**UI hint**: yes

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
| 9. Company Portal Detection | v2.0 | 1/1 | Complete | 2026-05-08 |
| 10. Mac Collectors | v2.0 | 4/4 | Complete | 2026-05-08 |
| 11. Steve | v2.0 | 1/1 | Complete | 2026-05-12 |
| 12. System Health Collectors | v3.0 | 0/? | Not started | - |
| 13. Vendor Update Detection | v3.0 | 0/? | Not started | - |
| 14. Extended CLI Flags | v3.0 | 0/? | Not started | - |
