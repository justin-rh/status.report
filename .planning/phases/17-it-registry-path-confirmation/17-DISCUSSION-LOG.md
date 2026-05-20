# Phase 17: IT Registry Path Confirmation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** 17-it-registry-path-confirmation
**Areas discussed:** Verification artifact, Findings capture, Lenovo keyword scope, Discrepancy & not-installed handling

---

## Verification artifact

### Q1: Form factor of the probe — how should Edgar actually run the check?

| Option | Description | Selected |
|--------|-------------|----------|
| SCRY --diag-vendor flag | Add a flag to SCRY itself. Reuses the exact code that ships in production — what Edgar sees IS what SCRY's collector sees. Only ~30 lines, fits SCRY's CLI pattern (RECOMMENDED) | ✓ |
| Standalone tools/probe_vendor_paths.py | Separate script in tools/ that imports the same _search_uninstall_keys helper. Easier to send via email/Slack without bundling a new SCRY release | |
| Doc with reg query / PowerShell | Markdown runbook in .planning/ with copy-paste commands Edgar runs in cmd/PowerShell. No SCRY code change, but commands diverge from collector logic | |

**User's choice:** SCRY --diag-vendor flag
**Notes:** Drives D-01. Choice locks the probe into SCRY's own argparse and the production `_search_uninstall_keys` path — eliminates the drift-from-collector risk in the doc-runbook option.

### Q2: What does the probe output — just keyword matches, or full registry entries?

| Option | Description | Selected |
|--------|-------------|----------|
| Full registry dump | Print DisplayName, DisplayVersion, hive+path, InstallLocation for every Uninstall entry whose DisplayName contains 'Dell' or 'Lenovo'. Edgar sees everything — catches DisplayNames not in our keyword list (RECOMMENDED) | ✓ |
| Match results only | Just print 'Dell Command Update: found / not found' — doesn't surface unmapped DisplayNames. Smaller output, less Edgar can do with it | |
| Both — match results + raw dump | Top section shows pass/fail, bottom section shows raw registry data. More output but covers both viewpoints | |

**User's choice:** Full registry dump
**Notes:** Drives D-02. Open-ended sweep is the only mode that catches unknown DisplayName variants — critical because that is exactly what CONF-01 / CONF-02 are looking for.

### Q3: Should the probe also check the DCU XML filesystem path?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — print XML path + existence + size + count | DCU_XML_PATH is just as much of a 'path SCRY uses' as the registry. If it lives elsewhere, vendor.py needs the same patch (RECOMMENDED) | ✓ |
| No — registry only | Phase 17 SC says 'registry key path(s)'. Keep scope tight; XML path issue is out-of-band | |

**User's choice:** Yes
**Notes:** Drives D-03. SC technically scopes to "registry key path(s)" but the XML path is exposed to the same drift risk; covering it in the same phase avoids a separate confirmation cycle later.

### Q4: Should the probe run on any user account, or only under SYSTEM/Admin?

| Option | Description | Selected |
|--------|-------------|----------|
| Any account | Mirrors how SCRY runs in production — reads HKLM/HKCU Uninstall keys which are readable by standard users. Edgar can run it on his own login without elevation (RECOMMENDED) | ✓ |
| Document both — run as Edgar's account AND as SYSTEM if possible | Catches asymmetries between standard-user HKCU and SYSTEM-account HKCU. More work for Edgar but more thorough | |

**User's choice:** Any account
**Notes:** Drives D-04. Production-parity is the goal; SYSTEM-account assymetries aren't relevant because production runs (NinjaOne) already hit them through SCRY's normal pipeline, not the diagnostic.

---

## Findings capture

### Q1: Where should Edgar's findings be persisted?

| Option | Description | Selected |
|--------|-------------|----------|
| 17-IT-CONFIRMATION.md in phase dir | New markdown file alongside CONTEXT.md / PLAN.md. Lives with the phase, committed to git, easy to cite from STATE.md and phase 19 plans (RECOMMENDED) | ✓ |
| Paste raw --diag-vendor output into 17-IT-CONFIRMATION.md | Same location, but verbatim probe output (timestamped, machine hostname, full registry dump) rather than a curated summary. Less work for Edgar but noisier file | |
| In-code comment block at top of vendor.py | Document confirmed DisplayNames + source machine inline. Lives with the code but harder to grep across phases | |

**User's choice:** 17-IT-CONFIRMATION.md in phase dir
**Notes:** Drives D-05.

### Q2: What is the minimum content that must be captured per machine?

| Option | Description | Selected |
|--------|-------------|----------|
| Hostname + date + raw DisplayName/DisplayVersion + hive | Hostname proves it's a real enrolled machine; date proves recency; DisplayName/Version + hive answers the actual code question; lets phase 19 cite specific evidence (RECOMMENDED) | ✓ |
| Just the matched DisplayName per vendor | Minimal — just what changed (or 'no change needed'). Lowest friction but no traceability if questions arise later | |
| Full probe output verbatim + 1-line summary | Everything the probe printed, plus a human-readable 'matches D-10 keyword list / requires update to X' summary at the top | |

**User's choice:** Hostname + date + DisplayName/Version + hive
**Notes:** Drives D-06.

### Q3: How many machines must be confirmed for phase 17 to close?

| Option | Description | Selected |
|--------|-------------|----------|
| One Dell + one Lenovo (matches SC bar) | Phase SC1/SC2 say 'at least one' — stay at the floor. Adding more is welcome but not required to close phase (RECOMMENDED) | ✓ |
| Two of each | Catches divergence between corporate-imaged and warehouse-imaged machines. More confidence but harder to schedule | |
| One Dell + one Lenovo + one non-Dell-non-Lenovo (negative control) | Confirms 'Not installed' rendering on a machine that genuinely has neither — partial overlap with phase 19 SC2 | |

**User's choice:** One Dell + one Lenovo
**Notes:** Drives D-07. Stays at the SC floor; additional machines welcome but not required.

### Q4: Atomicity — can phase 17 close with one vendor confirmed and the other pending?

| Option | Description | Selected |
|--------|-------------|----------|
| Both must be confirmed before phase closes | Phase has two requirements (CONF-01, CONF-02) and both gate phase 19. Closing partial leaves a half-done STATE.md blocker (RECOMMENDED) | ✓ |
| Allow split close — close CONF-01 and CONF-02 independently | If Edgar can only get to a Dell this week, Dell side can be marked done; Lenovo waits. More phase ceremony but unblocks half of phase 19 faster | |

**User's choice:** Atomic close
**Notes:** Drives D-08.

---

## Lenovo keyword scope

### Q1: Which Lenovo DisplayNames should Edgar confirm against real machines?

| Option | Description | Selected |
|--------|-------------|----------|
| All 4 currently in code | Confirm 'Lenovo System Update', 'Lenovo Vantage Service', 'Lenovo Vantage', 'Lenovo Commercial Vantage' — the code-vs-doc drift gets resolved this phase. What ships IS what's verified (RECOMMENDED) | |
| Just 'Lenovo System Update' (per D-13) | Stay in original phase 14 scope. Trim the 3 Vantage variants out of vendor.py to match D-13 | |
| Split — confirm 'Lenovo System Update' here; defer Vantage variants | Phase 17 closes on D-13 scope. Vantage entries get a new requirement and a follow-up phase | |
| **(Other)** Just Lenovo Vantage and Lenovo Commercial Vantage | User-supplied: Edgar confirms only the two Vantage variants — these reflect the actual Master Electronics fleet stack | ✓ |

**User's choice:** Just Lenovo Vantage and Lenovo Commercial Vantage (free text)
**Notes:** Drives D-09. Reflects the actual fleet — Master Electronics is on the modern Vantage stack, not legacy LSU. Tension with the keyword list (which retains all 4) is resolved by the follow-up Q5 below.

### Q2: What is treated as the canonical Lenovo behavior — LSU only, or 'Lenovo updater family'?

| Option | Description | Selected |
|--------|-------------|----------|
| 'Lenovo updater family' — any of the 4 means installed=True | Matches current code. Reflects reality: enrolled Lenovo machines may ship Vantage, not LSU. Update CONTEXT to formalize this and amend D-13 retroactively (RECOMMENDED) | ✓ |
| Strict LSU only — Vantage doesn't count as 'LSU installed' | Reverts code to D-13 scope. Vantage-only machines show 'Not installed' in the LSU row | |

**User's choice:** Lenovo updater family
**Notes:** Drives D-10. Retroactively amends Phase 14 D-13.

### Q3: How is the keyword list maintained going forward?

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded list in vendor.py with a comment citing 17-IT-CONFIRMATION.md | Same shape as today; just adds traceability to the confirmation evidence (RECOMMENDED) | ✓ |
| Move list to a constant in a shared registry-keywords module | Easier for future phases to add new vendors. Adds a module for one tiny list — yagni risk | |

**User's choice:** Hardcoded in vendor.py with traceability comment
**Notes:** Drives D-11. Yagni-respecting; no new module for one tiny list.

### Q4: Are there Lenovo DisplayName variants NOT in our list that Edgar should specifically look for?

| Option | Description | Selected |
|--------|-------------|----------|
| Probe surfaces all 'Lenovo*' DisplayNames — Edgar reports any not on our list | --diag-vendor already prints any DisplayName containing 'Lenovo'. No prior knowledge needed; the probe IS the discovery mechanism (RECOMMENDED) | ✓ |
| Pre-seed the probe with known-likely names | Add to a watchlist printed by the probe. Requires speculation about what's out there | |

**User's choice:** Open-ended probe discovery
**Notes:** Drives D-12.

### Q5 (clarifier): Reconcile Q1 (confirm only Vantage + Commercial Vantage) with the vendor.py keyword list

| Option | Description | Selected |
|--------|-------------|----------|
| Keep all 4 keywords; only Vantage + Commercial Vantage have Edgar evidence | vendor.py keyword list stays as-is. LSU and Vantage Service remain as defensive entries with a code comment noting they are not Edgar-confirmed (RECOMMENDED) | ✓ |
| Trim to just Vantage + Commercial Vantage | Remove 'Lenovo System Update' and 'Lenovo Vantage Service' from the keyword list — only confirmed names ship | |
| Keep all 4 but flag the unconfirmed ones for follow-up backlog item | Same shape as option 1, plus a backlog entry to confirm when older Lenovo machines are found | |

**User's choice:** Keep all 4, comment marks unconfirmed
**Notes:** Drives D-09 / D-11. Defensive entries cost nothing (only flip installed=True if matched) and removing them creates a regression risk for older / mixed-fleet machines.

---

## Discrepancy & not-installed handling

### Q1: If Edgar finds a DisplayName variant not in the keyword list, what happens?

| Option | Description | Selected |
|--------|-------------|----------|
| Append to vendor.py keyword list + add unit test using that exact string | test_vendor_collector.py gets a parameterized case with the new DisplayName mocked. Evidence committed alongside the change (RECOMMENDED) | ✓ |
| Append to keyword list only — no new test | _search_uninstall_keys is already exhaustively tested. Adding a per-keyword test is redundant since the search is keyword-agnostic | |
| Treat as a finding to report only — don't auto-add | Document in 17-IT-CONFIRMATION.md but require a follow-up phase + decision before changing the list | |

**User's choice:** Append + add unit test
**Notes:** Drives D-13.

### Q2: If Edgar finds the DCU XML lives at a different path than our hardcoded DCU_XML_PATH, what happens?

| Option | Description | Selected |
|--------|-------------|----------|
| Update DCU_XML_PATH constant + add a regression test | tests/test_vendor_collector.py gets a case asserting the new path is the one consulted (RECOMMENDED) | ✓ |
| Add the new path as a fallback (try original then new) | vendor.py probes multiple candidate paths. More robust but adds code complexity | |
| Update constant only — no new test | Mechanical re-pointing; existing tests already cover XML present/absent branches | |

**User's choice:** Update constant + regression test
**Notes:** Drives D-14. Single source of truth; no fallback path list.

### Q3: If NO enrolled Dell machine in Edgar's reach has DCU installed, how does phase 17 close?

| Option | Description | Selected |
|--------|-------------|----------|
| Close as 'No DCU in fleet; current code defensible; phase 19 catches divergence' | Phase SC says 'compared… against at least one enrolled machine'. Document the negative result and clear the blocker. Phase 19 stays the safety net (RECOMMENDED) | ✓ |
| Phase 17 cannot close — escalate to find a Dell with DCU before phase 19 | Treats CONF-01 as un-met until positive confirmation exists | |
| Mark CONF-01 deferred to v3.2 | Roll forward; v3.1 closes without it | |

**User's choice:** Close with negative result documented
**Notes:** Drives D-15.

### Q4: If no enrolled Lenovo machine has any of the 4 keywords installed, how does phase 17 close?

| Option | Description | Selected |
|--------|-------------|----------|
| Same answer as Dell — close with negative result documented | Symmetric treatment. 17-IT-CONFIRMATION.md records 'no Lenovo updater detected on inspected machines' (RECOMMENDED) | ✓ |
| Lenovo is lower priority — always close even with no evidence | LSU has no pending count source anyway (D-14). Only thing the code does is set installed=True/False | |
| Block phase 17 close until a Lenovo with one of the 4 keywords is found | Strict reading of CONF-02 — phase doesn't close without positive Lenovo evidence | |

**User's choice:** Symmetric to Dell
**Notes:** Drives D-16.

---

## Claude's Discretion

- Exact CLI help text for `--diag-vendor`
- Output format details: column ordering, per-block vs per-hive grouping, plain-text vs JSON
- Whether `--diag-vendor` accepts `--json` for a machine-readable variant
- Exact wording of the comment block above the LSU keyword list in vendor.py
- Whether to probe LSU-equivalent registry/filesystem evidence the same way as DCU XML
- Template / heading structure of `17-IT-CONFIRMATION.md`

## Deferred Ideas

- `--diag-vendor --json` machine-readable output (Claude's discretion, not committed)
- LSU pending-count source (already tracked as LSU-PENDING future requirement)
- Probing other vendor updaters (HP, Acer, ASUS, Surface) — out of scope per VENDOR-01 / VENDOR-02
- Second-machine confirmation per vendor (SC floor is one; staying at floor)
- Auto-extending the keyword list at runtime — not pursued; deterministic detection preserved
