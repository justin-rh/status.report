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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 5 | 14 | First milestone; constraints-first approach established |
| v2.0 | 6 | 12 | Cross-platform dispatch; `_AVAILABLE` guard pattern extended to Mac; Steve CLI pattern |

### Cumulative Quality

| Milestone | Python LOC | Tests | Phases |
|-----------|-----------|-------|--------|
| v1.0 | 2,647 | 85+ | 5 |
| v2.0 | ~5,226 | 203 | 11 (cumulative) |

### Top Lessons (Verified Across Milestones)

1. Document hard constraints (what NOT to use) before writing any code — eliminates entire bug classes
2. Keep requirement traceability current at each plan completion, not at milestone close (repeated v1.0 → v2.0)
3. LOW-confidence paths need a BLOCKED gate in the plan, not a TODO comment — otherwise they ship unvalidated
4. Cross-session open decisions need an owner + deadline or they carry forever
