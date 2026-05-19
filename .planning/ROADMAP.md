# Roadmap: SCRY

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5 (shipped 2026-05-05)
- ✅ **v2.0 Warnings, Mac Parity, and NinjaOne Compatibility** — Phases 6–11 (shipped 2026-05-12)
- ✅ **v3.0 System Health, Vendor Updates, and Extended CLI** — Phases 12–15 (shipped 2026-05-18)
- 🚧 **v3.1 Cleanup** — Phases 16–20 (in progress)

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

<details>
<summary>✅ v3.0 System Health, Vendor Updates, and Extended CLI (Phases 12–15) — SHIPPED 2026-05-18</summary>

- [x] **Phase 12: SCRY Rename** — 3/3 plans — completed 2026-05-15
- [x] **Phase 13: System Health Collectors** — 3/3 plans — completed 2026-05-18
- [x] **Phase 14: Vendor Update Detection** — 2/2 plans — completed 2026-05-18
- [x] **Phase 15: Extended CLI Flags** — 1/1 plan — completed 2026-05-18

Full phase details: `.planning/milestones/v3.0-ROADMAP.md`
Audit: `.planning/milestones/v3.0-MILESTONE-AUDIT.md`

</details>

### 🚧 v3.1 Cleanup (In Progress)

**Milestone Goal:** Close all accumulated debt — remove dead code, fix wasted collector work, automate REQUIREMENTS tracking, confirm vendor registry paths with IT, and validate SCRY on real hardware across all 20 deferred UAT items.

- [ ] **Phase 16: Tech Debt Cleanup** — Remove dead writers.write_html, fix --updates wasted collector calls, warn on --app/--output conflict
- [ ] **Phase 17: Requirements Automation Hook** — Install PreToolUse hook that blocks SUMMARY commit when REQUIREMENTS.md checkboxes are unchecked
- [ ] **Phase 18: IT Registry Path Confirmation** — Edgar/IT confirms Dell Command Update and Lenovo System Update registry paths; code updated if paths differ
- [ ] **Phase 19: Live Machine Validation — System Health and Apps** — IT staff validates uptime badges, pending updates, app detection, and HTML render on real enrolled Windows machines
- [ ] **Phase 20: Live Machine Validation — Vendor and Mac** — IT staff validates Dell DCU vendor row on a real Dell machine and verifies Mac end-to-end run

## Phase Details

### Phase 16: Tech Debt Cleanup
**Goal**: Dead code and silent misbehaviors are eliminated so the codebase reflects only what SCRY actually does
**Depends on**: Phase 15 (v3.0 complete)
**Requirements**: DEBT-01, DEBT-02, DEBT-03
**Success Criteria** (what must be TRUE):
  1. `writers.write_html` and its unreachable call site no longer exist in the codebase; the hard-coded `scry.html` string in that dead path is gone; all existing tests pass with no regressions
  2. Running SCRY with `--name`, `--serial`, or `--warnings` does not invoke `collect_pending_updates` or `collect_vendor_updates`; profiling or logging confirms the collectors are not called in that code path
  3. Running `scry.exe --app chrome --output C:\temp` (or equivalent) prints a warning to stderr that `--output` is ignored in app-query mode; the warning is absent when `--output` is used without `--app`
**Plans**: TBD

### Phase 17: Requirements Automation Hook
**Goal**: A PreToolUse hook enforces REQUIREMENTS.md checkbox discipline so phases can no longer close with unchecked requirements
**Depends on**: Phase 16
**Requirements**: AUTO-01
**Success Criteria** (what must be TRUE):
  1. A PreToolUse hook file exists in the project's `.claude/` hook directory targeting SUMMARY commit operations
  2. Attempting to create a SUMMARY commit when the current phase has at least one unchecked `[ ]` requirement checkbox causes the hook to exit non-zero with an error message identifying the unchecked requirements
  3. Creating a SUMMARY commit when all requirements for the current phase are checked `[x]` proceeds without hook intervention
**Plans**: TBD

### Phase 18: IT Registry Path Confirmation
**Goal**: The registry paths SCRY uses to detect Dell Command Update and Lenovo System Update are confirmed against real enrolled machines, and the code is corrected if they differ
**Depends on**: Phase 17
**Requirements**: CONF-01, CONF-02
**Success Criteria** (what must be TRUE):
  1. Edgar or IT has compared the DCU registry key path(s) in `collectors/windows/vendor.py` against at least one enrolled Dell machine and documented whether they match; if they differ, `vendor.py` is updated with the correct path
  2. Edgar or IT has compared the LSU registry key path(s) in `collectors/windows/vendor.py` against at least one enrolled Lenovo machine and documented whether they match; if they differ, `vendor.py` is updated with the correct path
  3. The full test suite passes (no regressions) after any code updates; the "DCU registry path uncertainty" and "LSU registry path uncertainty" open blockers are removed from STATE.md
**Plans**: TBD

### Phase 19: Live Machine Validation — System Health and Apps
**Goal**: IT staff has confirmed on real enrolled Windows machines that SCRY correctly reports system health signals, app detection results, and HTML character sheet rendering — closing all carried validation debt from v2.0 and v3.0 for these areas
**Depends on**: Phase 17
**Requirements**: VALID-01, VALID-03, VALID-05
**Success Criteria** (what must be TRUE):
  1. IT staff runs SCRY under a SYSTEM or Admin account and observes real (non-None, non-"N/A") uptime and pending Windows update count values displayed in the character sheet
  2. IT staff observes a yellow UPTIME_WARN badge on a machine whose uptime exceeds 7 days, and a red UPTIME_STALE badge with "Hibernation time is counted on Windows" note on a machine whose uptime exceeds 30 days
  3. IT staff runs SCRY as a standard non-admin user and confirms pending updates displays "N/A" rather than a number
  4. IT staff runs SCRY on an enrolled Windows machine and confirms NinjaOne and CrowdStrike Falcon are detected as present; an IT stakeholder signs off on the M365 single-suite-entry display; Company Portal is detected on a real Intune-enrolled machine
  5. IT staff opens the generated HTML character sheet in a real browser and confirms the full D&D-styled sheet renders correctly — layout, dark color scheme, stat block, equipment/app table, and quest status section all present and legible
**Plans**: TBD
**UI hint**: yes

### Phase 20: Live Machine Validation — Vendor and Mac
**Goal**: IT staff has confirmed vendor update detection on real Dell and non-Dell hardware, and Mac end-to-end execution is verified on real Apple hardware — closing all remaining carried validation debt
**Depends on**: Phase 18, Phase 19
**Requirements**: VALID-02, VALID-04
**Success Criteria** (what must be TRUE):
  1. IT staff runs SCRY with `--updates` on a real Dell machine and observes a DCU pending count (or "Unknown (no scan data)" if DCU has not been run since imaging) — the vendor row is not "Not installed"
  2. IT staff runs SCRY with `--updates` on a real non-Dell/non-Lenovo machine and observes "Not installed" in both vendor rows
  3. IT staff opens `test_vendor_render_case1.html`, `test_vendor_render_case2.html`, and `test_vendor_render_case3.html` in a real browser and confirms each vendor row state (pending count, no scan data, not installed) renders with correct layout and badge styling
  4. IT staff runs SCRY on a real Mac and confirms hardware collectors (CPU, RAM, disk, macOS version), profile enumeration, app detection (including NinjaOne launchctl label match), and HTML character sheet render all complete without error
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
| 12. SCRY Rename | v3.0 | 3/3 | Complete | 2026-05-15 |
| 13. System Health Collectors | v3.0 | 3/3 | Complete | 2026-05-18 |
| 14. Vendor Update Detection | v3.0 | 2/2 | Complete | 2026-05-18 |
| 15. Extended CLI Flags | v3.0 | 1/1 | Complete | 2026-05-18 |
| 16. Tech Debt Cleanup | v3.1 | 0/TBD | Not started | - |
| 17. Requirements Automation Hook | v3.1 | 0/TBD | Not started | - |
| 18. IT Registry Path Confirmation | v3.1 | 0/TBD | Not started | - |
| 19. Live Machine Validation — System Health and Apps | v3.1 | 0/TBD | Not started | - |
| 20. Live Machine Validation — Vendor and Mac | v3.1 | 0/TBD | Not started | - |
