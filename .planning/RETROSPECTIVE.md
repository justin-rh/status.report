# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-05-05
**Phases:** 5 | **Plans:** 14 | **Timeline:** 2 days (2026-05-04 → 2026-05-05)

### What Was Built

- **Hostname parser** — pure-function decoder for Master Electronics naming convention; 21 city codes, 4 device types, zero Windows API calls in tests
- **Hardware collectors** — WMI/psutil/winreg with `_WMI_AVAILABLE` guard; CPU, RAM, disk, OS, all local profiles; graceful degradation as standard user
- **D&D character sheet** — dark navy HTML via Jinja2; stat block, HP bar, 11-app equipment table with color-coded badges, quest status banner; `importlib.resources` bundling for PyInstaller
- **App detection engine** — winreg across all 4 Uninstall paths; NinjaOne, CrowdStrike Falcon, M365 suite, Zoom, Chrome, Claude desktop, MERP
- **CrowdStrike-safe packaging** — PyInstaller `--onedir` + `upx=False`; validated on enrolled ME machine as standard user; no quarantine

### What Worked

- **Constraints-first planning** — documenting `Win32_Product` prohibition, `--onefile` ban, and `sys.executable.parent` requirement in CLAUDE.md before any code was written eliminated entire classes of bugs
- **`_WMI_AVAILABLE` guard pattern** — module-level import guard let the full test suite run in CI without a Windows COM server; established once in Phase 2, reused throughout
- **Phase 4 registry research** — confirming actual CrowdStrike DisplayName values from a live registry before writing tests prevented a silent false-negative that would have been hard to debug on enrolled machines
- **PyInstaller `--onedir` + `upx=False`** — two-setting combination was sufficient to pass CrowdStrike Falcon behavioral detection; no code signing or exclusions needed for v1.0
- **`importlib.resources` for template loading** — correct approach for PyInstaller bundles; documented single-string `joinpath` form prevents a subtle packaging bug

### What Was Inefficient

- **REQUIREMENTS.md traceability not kept current** — after Phase 4 completed, APP-01–07 and OUT-01 checkboxes were still marked Pending; had to reconcile at milestone close
- **Human UAT tests not run before close** — live machine verification (NinjaOne detection, CrowdStrike service state) was deferred; these are practical constraints but should be scheduled for early in the next milestone as v1.1 validation
- **M365 product decision (D-05) not formally closed** — the single-suite vs 5-individual-apps decision was made in CONTEXT.md but never got explicit stakeholder sign-off; carried forward as acknowledged debt

### Patterns Established

- `_wmi_module`/`_WMI_AVAILABLE` module-level guard — standard pattern for any Windows COM dependency; enables cross-platform test runs
- `P3_CODES` check before `seg3.isdigit()` in hostname disambiguation — ordering invariant that must be preserved if parser is extended
- CrowdStrike distribution gate: test result must be recorded in ROADMAP.md SC4 before any USB distribution (D-13)
- `render_html(report) -> str` interface — returns HTML string, never writes; `main.py` controls path and write; avoids coupling renderer to filesystem

### Key Lessons

1. **Test the CrowdStrike/AV detection early, not at the end.** The packaging phase went smoothly because `--onedir` had already been selected for AV reasons. In future tool projects, validate the packaging approach against endpoint security before committing to it in the architecture.
2. **"Confirm with IT before Phase X" blockers need a resolution checkpoint.** MERP and hostname convention both had "confirm with IT/Edgar" notes. Having an explicit resolution checkpoint (a decision gate in the PLAN.md) rather than a note in STATE.md would prevent these from silently carrying forward.
3. **REQUIREMENTS.md checkboxes should be updated at phase completion, not milestone close.** The traceability table became a reconciliation task rather than a live tracker. Update requirements as each plan completes.
4. **Human UAT scenarios that need real hardware should be scheduled on a real machine ASAP.** Four pending scenarios (live NinjaOne, live CrowdStrike, compliance gap display, M365 decision) accumulated. These are hard to defer — they confirm the core value of the tool.

### Cost Observations

- Model mix: balanced profile (Sonnet 4.x primary)
- Sessions: multiple over 2 days
- Notable: phases 4 and 5 had the highest cost due to registry research and live machine testing; Phase 1 (pure data modeling) was the most token-efficient

---

## Milestone: v2.0 — Warnings, Mac Parity, and NinjaOne Compatibility

**Shipped:** 2026-05-12
**Phases:** 6 | **Plans:** 12 | **Timeline:** 5 days (2026-05-07 → 2026-05-12)

### What Was Built

- **Warning system** — `Warning` dataclass + `evaluate_warnings()` (OS/disk/rename checks); collapsible `<details open>` HTML box; 17 boundary tests
- **NinjaOne compatibility** — `isatty()` guard on all interactive calls; `[SUMMARY]` stdout line always emitted; SYSTEM-account safe
- **Company Portal + Intune** — MSIX detection + `HKLM\Enrollments` UPN check; MDM enrollment in Service column
- **Mac collectors** — `collectors/mac/` package: Intel + Apple Silicon CPU, `sw_vers`, psutil, pwd; 7-app `MAC_APP_SPECS` via plistlib/launchctl; platform dispatch in `collect_all()` and `main.py`
- **Steve CLI flags** — argparse branch exits before full pipeline; `--name/--serial/--warnings/--help`; union collection scope; 8 new tests (203 total)

### What Worked

- **`_pwd_module`/`_PWD_AVAILABLE` pattern** — reused the `_WMI_AVAILABLE` guard from v1.0 for `pwd` module on Mac; enabled Windows CI import of Mac collectors without platform guards in every test
- **Patching module constants instead of Path class** — `APPLICATIONS_DIR`/`LAUNCH_DAEMONS_DIR` as patchable constants avoided the pre-instantiated constant problem that would have broken Mac app tests
- **`argparse` at top of `main()` with early return** — Steve CLI flags were wired with zero changes to the existing full-pipeline path; `_run_cli()` returns before hostname decode
- **`sys.argv` patch in shared `_patched_main` helper** — one fix location covered the argparse/pytest argv collision in both `test_main.py` and `test_main_mac.py`

### What Was Inefficient

- **REQUIREMENTS.md traceability still not kept current** — same issue as v1.0; 8 of 10 requirements still showed "Pending" at close despite all phases shipping. Pattern not fixed between milestones.
- **NinjaOne Mac agent launchctl label shipped at LOW confidence** — `com.ninjarmm.agent` was not validated against a real fleet Mac; carried as a TODO. Should have been blocked as a decision gate in Phase 10 PLAN.md.
- **M365 stakeholder sign-off still pending from v1.0** — carried across two milestones without a scheduled resolution checkpoint.

### Patterns Established

- `_pwd_module`/`_PWD_AVAILABLE` — standard cross-platform guard for any Unix-only stdlib module; mirrors `_WMI_AVAILABLE`
- Module-level constants for patchable filesystem paths (`APPLICATIONS_DIR`, `LAUNCH_DAEMONS_DIR`) — avoids pre-instantiated constant problem in tests
- `argparse` branch at top of `main()` with `_run_cli()` + early return — clean CLI extension pattern that doesn't touch the full pipeline
- `patch("sys.argv", ["status_report"])` in shared `_patched_main` helper — standard fix for argparse + pytest argv conflict

### Key Lessons

1. **Repeat lesson from v1.0: update requirement traceability at each plan, not at close.** Two milestones in a row this became a reconciliation task. Add traceability checkbox update to the PLAN.md success criteria template.
2. **LOW-confidence paths need a decision gate in the PLAN.md, not a TODO comment.** The NinjaOne Mac launchctl label shipped unvalidated. A `BLOCKED` gate in the plan would have forced a resolution before execution.
3. **Cross-session issues (M365 sign-off) need an explicit owner and deadline, or they carry forever.** Three milestones in, this is still "pending stakeholder input." Either schedule it or move it to Out of Scope.
4. **The `_AVAILABLE` guard pattern scales well.** Four modules now use it (wmi, pwd, and two test-time patches). It's the right abstraction for any platform-specific import.

### Cost Observations

- Model mix: balanced profile (Sonnet 4.x primary)
- Sessions: multiple over 5 days
- Notable: Phase 10 (Mac collectors) was the most complex — 4 plans, cross-platform dispatch, new test infrastructure; Phase 11 (Steve) was the most token-efficient despite touching main.py and two test files

---

## Milestone: v3.0 — System Health, Vendor Updates, and Extended CLI

**Shipped:** 2026-05-18
**Phases:** 4 | **Plans:** 9 | **Timeline:** 4 days (2026-05-14 → 2026-05-18)

### What Was Built

- **SCRY rename** — Full project rebrand (StatusReport → SCRY); `scry.spec` → `dist/scry_v3.0/scry.exe`; output filename `{date}_scry_{hostname}.html`; 203 tests preserved
- **System health collectors** — `psutil.boot_time()` uptime on both Win and Mac; WUA COM pending update count via `pywin32==311` with `_WIN32COM_AVAILABLE` guard; `Warning.level` field positional-LAST for backward-compat; `UPTIME_WARN` yellow (>7d), `UPTIME_STALE` red (>30d) with hibernation note; `badge-critical` CSS
- **Vendor update detection** — Dell DCU via passive `DCUApplicableUpdates.xml` parse; Lenovo LSU via registry only; **never** invokes vendor CLIs; `VendorUpdateStatus` dataclass; `--updates` flag gates collection; Mac silent no-op via `sys.platform` check
- **Extended CLI flags** — `--json` (`dataclasses.asdict()` + `json.dumps(..., default=str)` recurses through nested dataclasses); `--output PATH` (no host-path validation per D-02/D-03); `--app NAME` case-insensitive single-app stdout; `--app --json` JSON blob variant; unknown app → stderr exit 1
- **Test growth** — 88 new tests (203 → 291, +43%); zero regressions across the rename or refactors

### What Worked

- **3-source requirement cross-reference at audit time** — checking VERIFICATION.md SATISFIED state + SUMMARY frontmatter `provides:` + REQUIREMENTS.md checkboxes caught the stale-checkbox issue cleanly and surfaced it as a single, atomic fix rather than scattered confusion
- **`_WIN32COM_AVAILABLE` guard pattern extended** — third instance of the `_AVAILABLE` guard (after `_WMI_AVAILABLE` v1.0, `_PWD_AVAILABLE` v2.0). The pattern keeps scaling — Phase 13's new pywin32 dep dropped in cleanly with no test infrastructure changes
- **`Warning.level: str | None` field positional-LAST** — preserved backward-compat with `Warning(code, severity, message, detail)` positional callers; full v2.0 test suite passed unmodified after the new field landed
- **Vendor detection chose registry+file-only over CLI invocation** — the constraints-first habit (CLAUDE.md: "no admin elevation, no side effects, no host PC writes") drove the design before any code was written; `grep dcu-cli tvsu.exe` returns zero matches as an enforceable post-condition
- **gsd-integration-checker for cross-phase wiring** — at milestone close it verified all 12 requirement integrations and 11 E2E flows in a single pass; caught no real issues but surfaced 3 worthwhile tech-debt observations (dead `writers.write_html`, `_run_cli --updates` wasted work, `--app + --output` silent ignore)
- **Mechanical rename preserving git history** — Phase 12 used `git mv`-style renames; all 203 tests passed after the rebrand; one intentional historical parenthetical kept in CLAUDE.md as a navigation hint for old issue references
- **`--json` as output-format modifier (not pipeline mode)** — `if cli_mode and not args.json:` guard kept `--json --name` working as a full-pipeline run, which matches user mental model (JSON is an output format, not a pipeline switch)

### What Was Inefficient

- **REQUIREMENTS.md checkbox bookkeeping lag — third milestone running** — RENAME-01, RENAME-02, VENDOR-01, VENDOR-02 all shipped checked-off but were still `[ ]` in REQUIREMENTS.md at audit time. Phase 15's VERIFICATION.md correctly flagged OUT-V3-* and CLI-V3-* checkboxes as a gap. The v1.0 and v2.0 retrospectives both called this out; it needs an automation hook before v4.0 (e.g. PreToolUse hook on plan SUMMARY write that requires the matching REQ checkbox flip)
- **Hardware-gated UAT continues to accumulate** — Phase 13 added 4 new hardware-gated checks; Phase 14 added 5 more. Now 11 v3.0 items + 6 carried from v1.0/v2.0 = 17 deferred human-verification items. Without a scheduled "live machine day" these compound across milestones
- **Dell/Lenovo registry path uncertainty shipped without IT confirmation** — flagged as a blocker in STATE.md, then shipped anyway with the researched path. Same pattern as v2.0's NinjaOne Mac launchctl label — a "needs confirmation" note in STATE.md is not strong enough to actually gate
- **OUT-V3-02 host-path validation removed mid-planning** — D-02/D-03 changed the requirement after planning started. REQUIREMENTS.md description retained the old "validates resolved path does not write to host PC" language; only ROADMAP SC2 was updated. Caught at Phase 15 verification

### Patterns Established

- `_WIN32COM_AVAILABLE` guard for pywin32 / WUA COM — third concrete instance of the `_AVAILABLE` family
- Vendor detection contract: registry+file passive read, never CLI subprocess — enforced by `grep` post-condition
- `Warning.level: str | None` positional-LAST — preserves backward-compat when extending a public dataclass
- `dataclasses.asdict(report, default=str)` for full AuditReport JSON serialization — handles nested dataclasses (VendorUpdateStatus, AppStatus, Warning, ParsedHostname) and any non-serializable edge cases
- `_run_cli_app()` early-exit pattern — extension to v2.0's `_run_cli()` for `--app` with platform dispatch on `sys.platform`
- `if args.<flag> and sys.platform != "darwin":` gate at BOTH call sites — Phase 14's `--updates` was wired in `_run_cli` AND `main()`; verified by integration checker
- 3-source requirement audit (VERIFICATION + SUMMARY frontmatter + REQUIREMENTS.md checkboxes) — surfaces bookkeeping lag deterministically at close

### Key Lessons

1. **Repeat for the third time: requirement traceability needs automation, not discipline.** v1.0 → v2.0 → v3.0 all caught this at close. A manual "update REQUIREMENTS.md checkbox at plan completion" rule has failed three times running. Before v4.0, install a hook that fails the SUMMARY commit if the matching REQ checkbox is still `[ ]`
2. **"Confirm with IT" gates need a Pre-execute checkpoint, not a STATE.md note.** The Dell/Lenovo registry paths are still uncertain at close — same outcome as v2.0's NinjaOne launchctl label. The pattern is: needs-confirmation work proceeds with research, but a `BLOCKED` gate in the PLAN.md success criteria would force resolution before merging the plan
3. **Schedule a "live machine day" or hardware-gated UAT accumulates indefinitely.** 17 items now. The cost-per-item is low but stacks; a single afternoon on enrolled hardware would close most of v2.0 + v3.0 hardware items at once
4. **Output-format-modifier vs pipeline-mode-selector is a load-bearing distinction.** `--json` could have been wired as "skip HTML, write only JSON" — instead it's "also write JSON", and `--json + --name` runs full pipeline. The mental model matches user expectations; the `not args.json` guard is the implementation footprint
5. **`gsd-integration-checker` at milestone close caught zero blockers and 3 useful observations.** Worth the spawn cost — the integration view across 4 phases is hard to keep in head while writing them

### Cost Observations

- Model mix: balanced profile (Sonnet 4.x primary)
- Sessions: multiple over 4 days
- Notable: Phase 12 (mechanical rename) was the most token-efficient — pure search-and-replace + test verification; Phase 13 (3 plans, new pip dep, COM guard, renderer changes) was the most complex; Phase 14 (registry + XML parse + renderer + tests across 2 plans) had the highest per-plan test count (28 new tests in 2 plans)

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 5 | 14 | First milestone; constraints-first approach established |
| v2.0 | 6 | 12 | Cross-platform dispatch; `_AVAILABLE` guard pattern extended to Mac; Steve CLI pattern |
| v3.0 | 4 | 9 | `_AVAILABLE` guard extended to pywin32 COM; vendor detection registry-only contract; 3-source requirement audit; integration-checker at close |

### Cumulative Quality

| Milestone | Python LOC | Tests | Phases (cumulative) |
|-----------|-----------|-------|---------------------|
| v1.0 | 2,647 | 85+ | 5 |
| v2.0 | ~5,226 | 203 | 11 |
| v3.0 | ~7,129 | 291 | 15 |

### Top Lessons (Verified Across Milestones)

1. Document hard constraints (what NOT to use) before writing any code — eliminates entire bug classes (v1.0 → v3.0 vendor CLI prohibition)
2. **Requirement traceability needs automation, not discipline** — manual upkeep failed at all three milestone closes (v1.0, v2.0, v3.0). Install a hook before v4.0
3. **"Needs confirmation" work needs a BLOCKED gate in PLAN.md**, not a STATE.md note — same pattern failed at v2.0 (NinjaOne Mac launchctl) and v3.0 (Dell/Lenovo registry paths)
4. Cross-session open decisions need an owner + deadline or they carry forever (M365 stakeholder sign-off still open from v1.0)
5. **`_AVAILABLE` guard pattern is the right abstraction for platform-specific imports** — now four instances (wmi, pwd, win32com, plus test-time patches)
6. **gsd-integration-checker at milestone close is worth the spawn cost** — surfaces cross-phase observations that are hard to see from within any single phase

### Deferred Human-Verification Backlog (across milestones)

| Milestone | Items | Status |
|-----------|-------|--------|
| v1.0 | 3 | carried |
| v2.0 | 6 | carried |
| v3.0 | 11 | new |
| **Total** | **20** | hardware-gated, needs a scheduled "live machine day" |
