# Phase 18: Live Machine Validation — System Health and Apps - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

IT staff (Edgar) runs SCRY on real enrolled Windows machines and documents findings — confirming that system health signals (uptime badges, pending Windows update count), app detection (NinjaOne, CrowdStrike, M365, Company Portal), and HTML character sheet rendering all work correctly on live hardware. Closes VALID-01, VALID-03, and VALID-05.

SC2 (uptime badge states) is pre-validated by Justin — both UPTIME_WARN and UPTIME_STALE badge states have been personally observed working on real hardware and are recorded in the confirmation artifact with his sign-off. Edgar does not need to re-validate SC2.

Not in scope: vendor detection (VALID-02 is Phase 19), Mac validation (VALID-04 is Phase 19), adding new SCRY CLI flags, or any code changes unless validation finds a failing SC.

</domain>

<decisions>
## Implementation Decisions

### Validation Artifact (Area 1)
- **D-01:** Create `.planning/phases/18-live-machine-validation-system-health-and-apps/18-VALIDATION-RESULTS.md` as the canonical confirmation artifact — parallel to `17-IT-CONFIRMATION.md`. Committed to git; Edgar fills it in during his validation run.
- **D-02:** Structure is **per-success-criterion**: one section per SC (SC1–SC5). Each section contains: what Edgar ran (command + flags), the machine/account used, what he observed, and a PASS / FAIL / DEFERRED result.
- **D-03:** SC2 is pre-populated with Justin's direct observation before Edgar's run. Justin's sign-off entry covers both UPTIME_WARN (yellow, >7 days) and UPTIME_STALE (red, >30 days) badge states. Edgar does not need to find specific-uptime machines for SC2.
- **D-04:** Phase 18 closes atomically — all SC sections must have a PASS or an explicit DEFERRED (with documented rationale) before the phase is verified. A FAIL that has been fixed and re-validated counts as PASS.

### Uptime Badge Pre-validation (Area 2)
- **D-05:** Both uptime badge states (UPTIME_WARN and UPTIME_STALE) have been confirmed working on real Windows hardware by Justin prior to this phase. This evidence is recorded in `18-VALIDATION-RESULTS.md` SC2 section with Justin's name and date. Edgar's validation runs cover SC1, SC3, SC4, and SC5 only.
- **D-06:** SC2 is not repeated in Edgar's validation instructions — the IT runsheet only lists SC1/SC3/SC4/SC5 for Edgar's action items.

### M365 Sign-off (Area 3)
- **D-07:** Edgar is the IT stakeholder for the M365 single-suite-entry display sign-off required by VALID-03. No separate approval chain is needed.
- **D-08:** The M365 sign-off is recorded as a PASS in the SC4 section of `18-VALIDATION-RESULTS.md`. Edgar writes a brief text observation confirming what he sees in the HTML character sheet (e.g., "Microsoft 365 appears as a single row with sub-apps listed"). No screenshot is required.

### Bug-fix Scope (Area 4)
- **D-09:** If Edgar's validation reveals a failing SC, Phase 18 grows a conditional fix plan inline — parallel to Phase 17's D-13/D-14 conditional patch pattern. The fix plan is added to the phase, SCRY is re-packaged, and Edgar re-validates before the phase can close.
- **D-10:** High confidence that all SCs will pass cleanly — the test suite thoroughly covers uptime badge logic, app detection, and HTML rendering. No code changes are expected. Conditional fix plan is a safety net, not an anticipated path.

### Claude's Discretion
- Exact IT runsheet wording and format (step-by-step instructions for Edgar inside the plan, covering what to run, what to look for, and how to fill in `18-VALIDATION-RESULTS.md`)
- Template heading structure for `18-VALIDATION-RESULTS.md` — one section per SC with PASS/FAIL/DEFERRED columns and an Observations field
- Whether the plan includes an IT-facing README or embeds the instructions directly in the plan file
- Phase structure (number of plans and how the human-action checkpoint is framed): likely mirrors Phase 17's 3-plan shape — (1) create runsheet + template, (2) Edgar runs + fills artifact (checkpoint: human-action), (3) conditional fix plan if any SC fails

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements being closed
- `.planning/REQUIREMENTS.md` §VALID-01, §VALID-03, §VALID-05 — full acceptance criteria for each success criterion this phase closes

### Roadmap success criteria
- `.planning/ROADMAP.md` Phase 18 Success Criteria (SC1–SC5) — the validation contract; every SC must have a PASS or DEFERRED entry in `18-VALIDATION-RESULTS.md`

### Code paths Edgar will exercise
- `collectors/windows/hardware.py` `collect_pending_updates()` — WUA COM call, SYSTEM/Admin required; degrades to `None` for non-admin (D-09/D-10). This is the function behind SC1/SC3 pending update values.
- `collectors/windows/hardware.py` `_collect_uptime()` — `psutil.boot_time()` path. Already pre-validated by Justin (SC2).
- `health_checks.py` — `UPTIME_WARN_DAYS = 7`, `UPTIME_STALE_DAYS = 30`, UPTIME_WARN / UPTIME_STALE logic (lines 132–161). Pre-validated by Justin.
- `collectors/windows/apps.py` — NinjaOne (`NinjaRMMAgent` / `NinjaRMM` / `NinjaOne Agent` keywords), CrowdStrike Falcon (`CrowdStrike Windows Sensor` / `CrowdStrike Sensor Platform` keywords + service state read), Microsoft 365 (single-suite collapse), Company Portal (MSIX + MDM enrollment check). SC4.
- `renderer/__init__.py` `render_html()` — produces the HTML character sheet Edgar opens in a browser. SC5.

### Phase 17 precedent (parallel structure)
- `.planning/phases/17-it-registry-path-confirmation/17-CONTEXT.md` — D-05 through D-08 define the confirmation artifact pattern this phase follows. D-13/D-14 define the conditional-patch model Phase 18 D-09 adopts.
- `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` — concrete example of a completed confirmation artifact

### Test coverage (evidence that code is correct)
- `tests/test_health_checks.py` lines 182–205 — parameterized UPTIME_WARN / UPTIME_STALE tests
- `tests/test_app_collector.py` lines 55–817 — NinjaOne, CrowdStrike, M365, Company Portal detection tests
- `tests/test_renderer.py` — HTML rendering test suite

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_search_uninstall_keys()` in `collectors/windows/apps.py` — already enumerates all 4 hives (HKLM, HKLM\Wow6432Node, HKCU, HKCU\Wow6432Node). NinjaOne and CrowdStrike detection routes through this.
- `collect_pending_updates()` in `collectors/windows/hardware.py` — WUA COM call; returns `None` gracefully when `_WIN32COM_AVAILABLE` is False or privilege is insufficient. SC1/SC3 behavior is already implemented.
- `health_checks.py` `check_uptime_warning()` — pre-validated badge logic. No changes expected.

### Established Patterns
- Human-action checkpoint plan: Phase 17 Plan 17-02 is the model — plan describes what Edgar runs, where to record findings, and marks the plan complete only when `17-IT-CONFIRMATION.md` is populated. Phase 18 Plan 18-02 follows the same shape.
- Conditional fix plan: Phase 17 Plan 17-03 added `--diag-vendor` patches only if findings diverged. Phase 18's conditional plan adds code fixes only if a SC fails.
- `CollectionResult` envelope: all collectors return `(value, error)` and never raise across layer boundaries. Any edge case Edgar hits will surface as a `None` value + error string, not a crash.

### Integration Points
- No new SCRY CLI flags needed for Phase 18 — Edgar runs plain `scry.exe` (or with `--updates` for vendor rows, though that's Phase 19 scope) and opens the generated HTML.
- `18-VALIDATION-RESULTS.md` is a git-committed planning artifact only — not read by SCRY at runtime.

</code_context>

<specifics>
## Specific Ideas

- SC2 is the cleanest pre-validation ever done on this project: Justin directly observed the production badge states on real hardware. Recording this in `18-VALIDATION-RESULTS.md` with his name means the validation artifact is already partially complete before the plan even starts.
- The "single-suite-entry display" for M365 refers to SCRY collapsing Word, Excel, Outlook, etc. into one "Microsoft 365" row in the HTML equipment table rather than listing them as separate rows. Edgar's SC4 sign-off confirms this display choice is acceptable to IT.
- Company Portal detection (SC4) requires an Intune-enrolled machine — Edgar should use one of the standard-fleet enrolled machines. The enrollment check reads the MDM Enrollment registry path (not a COM call), so it works at standard-user privilege.

</specifics>

<deferred>
## Deferred Ideas

- **Vendor row validation (VALID-02)** — Dell DCU pending count on real Dell, "Not installed" on non-Dell/non-Lenovo, visual vendor HTML renders — all Phase 19 scope.
- **Mac end-to-end validation (VALID-04)** — Phase 19 scope.
- **Automated screenshot capture** — Suggested implicitly (whether to require screenshots). Not pursued; text observations in `18-VALIDATION-RESULTS.md` are sufficient evidence.

</deferred>

---

*Phase: 18-live-machine-validation-system-health-and-apps*
*Context gathered: 2026-05-21*
