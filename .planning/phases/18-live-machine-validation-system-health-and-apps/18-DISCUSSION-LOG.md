# Phase 18: Live Machine Validation — System Health and Apps - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-21
**Phase:** 18-live-machine-validation-system-health-and-apps
**Areas discussed:** Validation artifact, Uptime badge test strategy, M365 sign-off, Bug-fix scope

---

## Validation Artifact

| Option | Description | Selected |
|--------|-------------|----------|
| Per-SC checklist | One section per SC (SC1–SC5) with what was run, machine/account, observation, and PASS/FAIL/DEFERRED result | ✓ |
| Per-machine, parallel to Phase 17 | One section per machine run, listing all SCs observed in that run | |
| Combined: per-run header, per-SC rows | Two-level structure — machine run header plus SC table inside each run | |

**Location:**
| Option | Description | Selected |
|--------|-------------|----------|
| `.planning/phases/18-.../18-VALIDATION-RESULTS.md` | Committed to git, same pattern as 17-IT-CONFIRMATION.md | ✓ |
| Root of project | VALIDATION-18.md at top level for Edgar navigation convenience | |

**User's choice:** Per-SC checklist at `.planning/phases/18-.../18-VALIDATION-RESULTS.md`
**Notes:** Mirrors Phase 17 pattern (committed git artifact). Per-SC structure makes it clear which criteria are closed and which are pending across the multiple machine conditions this phase requires.

---

## Uptime Badge Test Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Best-effort: use whatever machines are available | Edgar documents whatever uptime state is present; missing badge states marked DEFERRED | |
| Block on both badge states | Phase doesn't close until both UPTIME_WARN and UPTIME_STALE are observed on real hardware | |
| One badge state is sufficient | Either badge state validates the logic; unit tests cover the other | |

**User's choice:** Free text — "I have personally observed both of these working, so these can be marked off as complete."
**Notes:** Justin has directly observed both UPTIME_WARN (>7 days, yellow) and UPTIME_STALE (>30 days, red) badge states on real Windows hardware prior to this phase. SC2 is pre-validated; Edgar's validation runs cover SC1/SC3/SC4/SC5 only. SC2 entry in 18-VALIDATION-RESULTS.md will be pre-populated with Justin's sign-off.

---

## M365 Sign-off

| Option | Description | Selected |
|--------|-------------|----------|
| Edgar — same person doing all validation | Edgar signs off on M365 display as part of his normal validation run | ✓ |
| Someone above Edgar (manager/supervisor) | Higher-level sign-off for licensing/reporting expectations | |

**Format:**
| Option | Description | Selected |
|--------|-------------|----------|
| Checkbox/PASS in SC4 section with text observation | Edgar writes brief text observation; no screenshot required | ✓ |
| Screenshot attached or referenced | Visual evidence but adds workflow friction | |
| Separate sign-off line in artifact | Explicit stakeholder sign-off row distinct from PASS/FAIL columns | |

**User's choice:** Edgar is the stakeholder; PASS with text observation in SC4 section
**Notes:** M365 "single-suite-entry display" refers to SCRY collapsing Word/Excel/Outlook/etc. into one "Microsoft 365" row rather than individual rows. Edgar's text note confirms this is acceptable to IT.

---

## Bug-fix Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Fix inline — Phase 18 grows a fix plan | If a SC fails, Phase 18 adds a code-fix plan; Edgar re-validates before phase closes | ✓ |
| Document and defer — Phase 18 closes with findings, fix is a new phase | Strictly observe-and-record; failures become requirements in a new phase | |
| Triage on the spot | Minor fixes inline; deeper bugs deferred | |

**Confidence level:**
| Option | Description | Selected |
|--------|-------------|----------|
| High — tests cover everything well, expecting clean pass | Unit tests for uptime badges, app detection, and HTML rendering are thorough | ✓ |
| Medium — a few edge cases might surface | | |
| Low — this is genuinely a discovery run | | |

**User's choice:** Fix inline; high confidence in clean pass
**Notes:** Conditional-fix model mirrors Phase 17's D-13/D-14 pattern. High confidence means the conditional fix plan is a safety net. Phase doesn't close until all SCs have PASS or documented DEFERRED.

---

## Claude's Discretion

- Exact IT runsheet wording and format for Edgar
- Template heading structure for `18-VALIDATION-RESULTS.md`
- Whether the IT instructions are in the plan file or a separate IT-facing README
- Phase plan count and checkpoint structure (likely mirrors Phase 17's 3-plan shape)

## Deferred Ideas

- Vendor row validation (VALID-02) — Phase 19 scope
- Mac end-to-end validation (VALID-04) — Phase 19 scope
- Automated screenshot capture — not pursued; text observations sufficient
