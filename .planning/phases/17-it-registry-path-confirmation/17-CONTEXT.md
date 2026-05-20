# Phase 17: IT Registry Path Confirmation - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Confirm the Dell Command Update (DCU) and Lenovo updater family detection paths SCRY uses against at least one enrolled Dell and one enrolled Lenovo machine, and patch `collectors/windows/vendor.py` only if findings diverge from current code. Closes CONF-01 and CONF-02 and removes the two registry-path blockers from STATE.md.

The phase has two layers:
1. **Tooling layer (always shipped):** Add a `--diag-vendor` CLI flag to SCRY that prints every Dell* / Lenovo* Uninstall entry on the host plus the DCU XML path state. This is the artifact Edgar runs.
2. **Confirmation + patch layer (conditional):** Edgar runs `--diag-vendor` on real hardware; findings are captured in `17-IT-CONFIRMATION.md`; vendor.py keyword list and/or `DCU_XML_PATH` are updated only if the findings show divergence.

Not in scope: changing detection method (still registry+file passive — no CLI invocation per the PROJECT.md key decision), adding an LSU pending-count source (deferred as LSU-PENDING), or live runtime validation of the rendered vendor row (that is phase 19 SC1/SC2).

</domain>

<decisions>
## Implementation Decisions

### Verification Artifact (Area 1)
- **D-01:** Add a `--diag-vendor` flag to SCRY (`main.py` argparse). Reuses the production `_search_uninstall_keys` helper so what Edgar sees IS what the production collector sees. No standalone script and no PowerShell runbook.
- **D-02:** `--diag-vendor` output is a full registry dump: for every Uninstall subkey across all 4 hives whose `DisplayName` contains "Dell" or "Lenovo" (case-insensitive), print `DisplayName`, `DisplayVersion`, hive label (HKLM / HKLM\Wow6432Node / HKCU / HKCU\Wow6432Node), and `InstallLocation` if present. Not just match results — Edgar must be able to spot DisplayNames not in our keyword list.
- **D-03:** `--diag-vendor` also probes the DCU XML filesystem path. Prints `DCU_XML_PATH`, whether it exists, file size if present, and the count of `<update>` elements if parseable. The XML path is just as much a "path SCRY uses" as the registry — same divergence risk.
- **D-04:** `--diag-vendor` is a short-circuit mode like `--name` / `--app` (exits after printing; does NOT run the full pipeline or write HTML). Runs under any account — no SYSTEM elevation required. Mirrors production: standard-user runs read both HKLM and HKCU Uninstall keys.

### Findings Capture (Area 2)
- **D-05:** Create `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` as the canonical confirmation artifact. Committed to git alongside CONTEXT.md and PLAN.md; cited from STATE.md when the blockers are cleared; referenced by phase 19 PLAN.md when it cites confirmed paths.
- **D-06:** Per-machine entry minimum content: hostname, date of the run, raw matched DisplayName + DisplayVersion, and the hive where the matching Uninstall subkey was found. Hostname proves it's a real enrolled machine; date proves recency; DisplayName + hive answers the actual code question; gives phase 19 specific evidence to cite.
- **D-07:** Floor of one enrolled Dell + one enrolled Lenovo per phase SC1/SC2. More machines welcome but not required. Additional machines append to the same file.
- **D-08:** Phase 17 closes atomically — both CONF-01 (Dell) and CONF-02 (Lenovo) must have an entry in `17-IT-CONFIRMATION.md` (positive or negative result — see D-15/D-16) before the phase is verified and the STATE.md blockers cleared.

### Lenovo Keyword Scope (Area 3)
- **D-09:** Edgar's real-machine confirmation only attests to two of the four Lenovo keywords: `"Lenovo Vantage"` and `"Lenovo Commercial Vantage"`. These reflect Master Electronics' actual Lenovo updater stack. The remaining two — `"Lenovo System Update"` and `"Lenovo Vantage Service"` — stay in the keyword list as defensive entries for older / mixed-fleet machines but carry no Edgar evidence.
- **D-10:** Canonical Lenovo behavior is "Lenovo updater family" — any of the 4 keywords matching means `installed=True` for `report.lenovo_lsu`. This formalizes the current code shape and retroactively amends Phase 14 D-13 (which only specified `"Lenovo System Update"`). Note this amendment in vendor.py and in the phase 14 → phase 17 traceability.
- **D-11:** Keep the keyword list hardcoded in `collectors/windows/vendor.py`. Add a comment block above the LSU keyword list naming the confirmed entries and citing `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` for traceability. The two unconfirmed entries are explicitly labeled "defensive — not Edgar-confirmed." No new shared-keywords module — yagni.
- **D-12:** `--diag-vendor` prints every `Lenovo*` DisplayName, not just the 4 we know about. The probe IS the discovery mechanism — no pre-seeded watchlist.

### Discrepancy & Not-Installed Handling (Area 4)
- **D-13:** If Edgar reports a Dell DisplayName variant not in the keyword list (current list: `["Dell Command Update", "Dell Command | Update"]`): append the exact string to the list AND add a parameterized unit test in `tests/test_vendor_collector.py` whose mocked registry exposes that DisplayName. Same rule for any new Lenovo DisplayName variant.
- **D-14:** If Edgar finds the DCU XML lives at a path other than the current `DCU_XML_PATH = r"C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml"`: update the constant in `vendor.py` AND add a regression test that asserts the new path is the one consulted. Single source of truth — no fallback path list (keeps vendor.py simple; the XML path is owned by Dell's installer, not us).
- **D-15:** If no enrolled Dell machine in Edgar's reach has DCU installed (negative-only result): close CONF-01 as "no DCU in fleet; current code defensible; phase 19 is the safety net for vendor row rendering." Document the negative result in `17-IT-CONFIRMATION.md` with the inspected hostnames. Do NOT block phase 17 close, do NOT escalate, do NOT defer to v3.2.
- **D-16:** Symmetric handling for Lenovo. If no enrolled Lenovo machine has any of the 4 keywords installed: close CONF-02 with the negative result documented. Same artifact, same close path. Phase 19 still validates the "Not installed" rendering on a non-Lenovo machine (SC2).

### Claude's Discretion
- Exact CLI help text for `--diag-vendor` (one-line description in argparse)
- Output format details: column ordering, whether to emit one block per match or one section per hive, whether to color-code (probably not — output may be redirected to a file)
- Whether `--diag-vendor` accepts `--json` to emit a machine-readable variant (likely yes for symmetry with `--name --json`, but only if the planner finds it cheap)
- Exact wording of the comment block above the LSU keyword list in vendor.py
- Whether to also probe (read-only) the LSU equivalent registry / filesystem locations the same way as DCU XML, even though there is no pending-count source — likely yes for surfacing future-state evidence (defer to planner)
- Template / heading structure of `17-IT-CONFIRMATION.md` — keep it simple; one section per machine, plus a top-line summary of which CONF-IDs are closed

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Code being verified (and potentially patched)
- `collectors/windows/vendor.py` — DCU + LSU detection. `DCU_XML_PATH` constant on line 16; LSU keyword list on lines 67–72; DCU keyword list on line 33. Subject to update under D-13 / D-14.
- `collectors/windows/apps.py` lines 134–177 — `_search_uninstall_keys()` and `UNINSTALL_PATHS`. Reused verbatim by `--diag-vendor`; do not duplicate the registry-enumeration logic.

### CLI patterns to mirror
- `main.py` — argparse wiring for `--name`, `--serial`, `--warnings`, `--app`, `--updates`, `--json`, `--output`. The `--diag-vendor` flag follows the short-circuit pattern of `--name` / `--app`: parse, run, print, exit before the full pipeline. See the short-circuit guard layout in `main.py` (Phase 15 wiring).

### Test patterns
- `tests/test_vendor_collector.py` — existing parameterized tests for DCU installed/not-installed and XML present/absent/malformed. New keyword-variant tests (D-13) and XML-path regression tests (D-14) extend this file.

### Phase context being amended
- `.planning/phases/14-vendor-update-detection/14-CONTEXT.md` D-10 (DCU keywords), D-11 (DCU XML path), D-13 (LSU keyword), D-14 (no LSU pending source). D-13 is retroactively expanded by Phase 17 D-09 / D-10 — preserve the original D-13 wording but reference the amendment.

### Requirements
- `.planning/REQUIREMENTS.md` §CONF-01 (DCU) and §CONF-02 (LSU) — full acceptance criteria.
- `.planning/ROADMAP.md` Phase 17 Success Criteria (3 items) — the verification contract.

### Standing constraints (PROJECT.md)
- "Vendor detection is registry+file passive only — no CLI subprocess invocation" — `--diag-vendor` must not invoke `dcu-cli.exe` or `tvsu.exe`. Probe reads only.
- "No writes to host PC filesystem, registry, or %TEMP%" — `--diag-vendor` output goes to stdout only; if redirected, the user owns the destination (consistent with how `--name` etc. work today).

### Confirmation artifact (created by this phase)
- `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` — created by phase 17 execution; cited from vendor.py code comment (D-11), from STATE.md blocker-removal, and from phase 19 PLAN.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_search_uninstall_keys(keywords, excludes)` in `collectors/windows/apps.py` — already enumerates all 4 hives. `--diag-vendor` calls this with no keyword filter (or with `["dell", "lenovo"]` as a coarse substring filter at the call site) to surface every relevant entry.
- `UNINSTALL_PATHS` constant in `collectors/windows/apps.py` — the 4-hive tuple list. Already imported by `vendor.py` per Phase 14 D-16.
- `Path(DCU_XML_PATH).exists()` / `ET.parse(...).getroot()` pattern in `vendor.py` lines 39–49 — reuse the existing XML probe for the `--diag-vendor` XML section so the diagnostic logic matches the production read.

### Established Patterns
- Short-circuit CLI flags (`--name`, `--serial`, `--warnings`, `--app`) exit before the full pipeline and write nothing to disk. `--diag-vendor` follows the same shape.
- Collectors never raise across the layer boundary. The diagnostic must mirror this — never raise even if registry enumeration fails on a sub-hive (silently skip, print a one-line note).
- Existing `--app NAME --output PATH` warning (DEBT-03, Phase 16) is the precedent for diagnostic / query modes warning on irrelevant flags. `--diag-vendor` combined with `--output` should print the same kind of stderr warning (planner decides).

### Integration Points
- `main.py` argparse: add `--diag-vendor` boolean flag. New short-circuit branch parallel to `_run_cli` short-circuits. Likely lives in or next to the existing argparse mode dispatcher.
- `tests/test_cli_phase15.py` is the analog for short-circuit-flag CLI tests; new short-circuit `--diag-vendor` tests follow the same pattern (mock the registry / XML, capture stdout, assert content).
- `.planning/STATE.md` Blockers/Concerns lines mention "Phase 18 gate: Dell Command Update and Lenovo System Update registry paths unconfirmed" — those two blocker lines (currently mis-tagged to "Phase 18" — they actually gate phases 18 AND 19) get cleared by phase 17 close. Phase 17 execution updates STATE.md as part of the verification step.

### Drift to fix during this phase
- STATE.md line 24: `Current focus: v3.1 Cleanup — Phase 17 next (Requirements Automation Hook)`. The parenthetical is leftover from the removed phase. Update to `Phase 17 next (IT Registry Path Confirmation)` when phase 17 closes (or earlier — could be a one-line side-fix at plan-phase start).

</code_context>

<specifics>
## Specific Ideas

- The `--diag-vendor` flag name keeps the `--` prefix consistent with all other SCRY flags; the `diag-` prefix groups it as diagnostic / not-for-production-output (parallel to how `--app` groups single-app queries). Edgar runs it from a flash-drive copy of SCRY, no new install.
- The Lenovo decision is the most consequential outcome of this discussion: the actual production keyword list (4 entries) becomes officially canonicalized, but Edgar's confirmation is bounded to the 2 entries that reflect the current fleet. This is the right tradeoff because the 2 unconfirmed entries cost nothing (they only flip `installed=True` if matched) and removing them would create a regression risk for any Lenovo machine still on the older updater.
- Negative-only results (D-15 / D-16) are treated as valid evidence — the phase does NOT require finding a DCU-installed Dell to close. The combination of (a) defensive code unchanged by negative-only evidence and (b) phase 19's live rendering check on whatever hardware IS available is sufficient to clear the blocker.

</specifics>

<deferred>
## Deferred Ideas

- **`--diag-vendor --json` machine-readable output** — Not committed. Claude's discretion (D-Discretion §3). If the planner finds it cheap, include; otherwise plain text only for phase 17.
- **LSU pending-count source** — Already a tracked future requirement (LSU-PENDING). Not reopened.
- **Probing other vendor updaters (HP, Acer, ASUS, Surface)** — Out of scope. SCRY's vendor detection is limited to Dell + Lenovo per VENDOR-01 / VENDOR-02. If a fleet shift demands HP / Microsoft Surface updater coverage, that's a future requirement (e.g. VENDOR-V4-XX) and a future phase.
- **Confirming the same DisplayNames on a second machine for each vendor** — Phase SC bar is "at least one"; we are staying at the floor (D-07). Additional machines welcome but not required.
- **Auto-extending the keyword list at runtime via a learned cache** — Not pursued. Keeps detection deterministic and auditable; new keywords require a phase + Edgar sign-off (D-11).

</deferred>

---

*Phase: 17-it-registry-path-confirmation*
*Context gathered: 2026-05-20*
