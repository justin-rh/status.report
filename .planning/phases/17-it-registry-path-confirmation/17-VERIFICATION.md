---
phase: 17-it-registry-path-confirmation
verified: 2026-05-20T00:00:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
---

# Phase 17: IT Registry Path Confirmation — Verification Report

**Phase Goal:** The registry paths SCRY uses to detect Dell Command Update and Lenovo System Update are confirmed against real enrolled machines, and the code is corrected if they differ.
**Verified:** 2026-05-20T00:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Edgar/IT compared DCU registry key path(s) against at least one enrolled Dell machine; documented whether they match; code updated if they differ | VERIFIED | `17-IT-CONFIRMATION.md` Machine: dev-dell-justin entry — CONFIRMED-MATCH, "Dell Command \| Update" 5.5.0 found in HKLM\Wow6432Node; no code change required |
| 2 | Edgar/IT compared LSU registry key path(s) against at least one enrolled Lenovo machine; documented whether they match; code updated if they differ | VERIFIED | `17-IT-CONFIRMATION.md` Machine: dev-lenovo-justin entry — CONFIRMED-MATCH, "Lenovo Vantage Service" 4.2601.21.0 found in HKLM\Wow6432Node; no code change required |
| 3 | Full test suite passes (no regressions); "DCU registry path uncertainty" and "LSU registry path uncertainty" open blockers removed from STATE.md | VERIFIED | `python -m pytest -x -q` = 284 passed, 0 failed; `grep "Dell Command Update and Lenovo System Update registry paths unconfirmed" STATE.md` = 0 matches; blocker line deleted per Plan 17-03 Task 3 |

**Score:** 3/3 ROADMAP success criteria verified

### Plan-Level Must-Have Truths

#### Plan 17-01 Must-Haves (9 truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `--diag-vendor` exits 0 without invoking full pipeline and writes nothing to disk | VERIFIED | Test 1 (`test_diag_vendor_short_circuits_and_exits_0`) and Test 3 (`test_diag_vendor_does_not_invoke_full_pipeline`) pass; `collect_all`/`render_html` mocks confirm not called |
| 2 | `--diag-vendor` prints every Uninstall subkey across all 4 hives whose DisplayName contains 'dell' or 'lenovo' | VERIFIED | `diag_vendor_paths` in vendor.py lines 127-168 iterates `UNINSTALL_PATHS`, checks `"dell" not in dn_lower and "lenovo" not in dn_lower`; Tests 1-3 pass |
| 3 | `--diag-vendor` prints DCU XML section showing path, existence, size if present, update count if parseable | VERIFIED | `diag_vendor_paths` lines 176-195; Tests 5-7 pass |
| 4 | `--diag-vendor` reuses `UNINSTALL_PATHS` from `collectors/windows/apps.py` (no duplicate hive list) | VERIFIED | `vendor.py` line 15: `from collectors.windows.apps import UNINSTALL_PATHS, _search_uninstall_keys`; line 127: `for hive, path in UNINSTALL_PATHS:` |
| 5 | `--diag-vendor --output PATH` prints `WARNING: --output is ignored in --diag-vendor mode` to stderr | VERIFIED | `main.py` line 202: exact string present; Test 2 (`test_diag_vendor_with_output_warns_to_stderr`) passes |
| 6 | `vendor.py` contains LSU comment block above keyword list citing `17-IT-CONFIRMATION.md`, naming Edgar-confirmed entries, labeling defensive entries | VERIFIED | `vendor.py` lines 68-79: all 7 grep-asserted substrings present (`Edgar-confirmed`, `defensive`, `17-IT-CONFIRMATION.md`, `Lenovo Vantage`, `Lenovo Commercial Vantage`, `Lenovo System Update`, `Lenovo Vantage Service`); Test 9 passes |
| 7 | `--diag-vendor` discovers Lenovo DisplayNames NOT in keyword list (D-12 discovery property) — verified via Test 3 using unknown Lenovo* DisplayName | VERIFIED | Test 3 (`test_discovery_property_unknown_lenovo_entry`) uses "Lenovo Hotkey Driver" (not in 4-entry keyword list); asserts it appears in output, "Microsoft Edge" does not |
| 8 | `--diag-vendor` is dispatched in main.py BEFORE the existing `--app` block | VERIFIED | `main.py` lines 197-204 (`--diag-vendor` block) precede lines 207-212 (`--app` block); Test 7 (`test_diag_vendor_dispatched_before_app`) enforces ordering contract |
| 9 | PyInstaller build produces `dist/scry/scry.exe` and `scry.exe --diag-vendor` exits 0 with diagnostic header | VERIFIED | Plan 17-01 Summary Task 3 checkpoint APPROVED: `dist\scry_v3.1\scry_v3.1.exe --diag-vendor` exit 0, all 4 hive headers + DCU XML probe section confirmed on developer's Windows machine |

**Score:** 9/9 Plan 17-01 truths verified

#### Plan 17-02 Must-Haves (4 truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `17-IT-CONFIRMATION.md` exists with at least one CONF-01 entry AND at least one CONF-02 entry (positive OR negative) | VERIFIED | File exists; Summary table shows CONF-01 CONFIRMED-MATCH (Dell) and CONF-02 CONFIRMED-MATCH (Lenovo); two machine entries present |
| 2 | Each per-machine entry contains: hostname, date of run, and matched DisplayName + hive label or explicit negative-result note | VERIFIED | Both entries contain all D-06 fields; dev-dell-justin: "Dell Command \| Update", HKLM\Wow6432Node; dev-lenovo-justin: "Lenovo Vantage Service", HKLM\Wow6432Node |
| 3 | Top-line Summary table states final CONF-01 and CONF-02 status (not `_pending Edgar run_`) | VERIFIED | Summary table shows "confirmed 2026-05-20 / CONFIRMED-MATCH" for both CONF-01 and CONF-02 |
| 4 | Artifact is committed to git so LSU comment block citation resolves to a real file | VERIFIED | Git commit `576b130` (skeleton) + subsequent population; file present at `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` |

**Score:** 4/4 Plan 17-02 truths verified

#### Plan 17-03 Must-Haves (7 truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | If CONFIRMED-DIVERGENT for Dell: new DisplayName appended + parameterized test added | VERIFIED (N/A — CONFIRMED-MATCH) | Both dispositions are CONFIRMED-MATCH; no code change required; Task 2 skipped per `option-no-changes` |
| 2 | If CONFIRMED-DIVERGENT for Lenovo: new DisplayName appended + parameterized test added | VERIFIED (N/A — CONFIRMED-MATCH) | Same — `option-no-changes` path |
| 3 | If DCU XML path differs: `DCU_XML_PATH` constant updated + constant-value regression test added | VERIFIED (N/A — CONFIRMED-MATCH) | DCU_XML_PATH confirmed at `C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml`; exists=False only because no pending updates |
| 4 | If both CONF-IDs CONFIRMED-MATCH: `vendor.py` unchanged and `17-IT-CONFIRMATION.md` records "no code changes required" | VERIFIED | `vendor.py` unchanged since Plan 17-01; Summary table confirmed; Plan 17-03 Summary states option-no-changes |
| 5 | If NEGATIVE-RESULT: `vendor.py` unchanged and negative result documented | VERIFIED (N/A) | No NEGATIVE-RESULT dispositions; both CONFIRMED-MATCH |
| 6 | `STATE.md` no longer contains the registry-path uncertainty blocker line | VERIFIED | Grep for "Dell Command Update and Lenovo System Update registry paths unconfirmed" = 0 matches; STATE.md `status: phase-complete`, `percent: 50` |
| 7 | `REQUIREMENTS.md` traceability table shows CONF-01 and CONF-02 with Phase 17 plan refs and non-pending status | VERIFIED | REQUIREMENTS.md: CONF-01 Phase 17 / 17-01,17-02,17-03 / complete; CONF-02 Phase 17 / 17-01,17-02,17-03 / complete; checkboxes `[x]` for both; DEBT-01/02/03 also closed (drive-by) |

**Score:** 7/7 Plan 17-03 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `collectors/windows/vendor.py` | `diag_vendor_paths` function + LSU comment block citing 17-IT-CONFIRMATION.md | VERIFIED | Function at line 98; comment block lines 68-79; all 7 grep substrings present |
| `main.py` | `--diag-vendor` argparse flag + `_run_cli_diag_vendor` short-circuit handler | VERIFIED | Argparse at lines 190-194; `_run_cli_diag_vendor` at lines 113-132; dispatcher at lines 197-204 |
| `tests/test_vendor_collector.py` | `TestDiagVendorPaths` class with 9 tests + LSU comment block test | VERIFIED | Class present lines 166-354; all 9 tests present and pass |
| `tests/test_cli_phase17.py` | 7 CLI tests for `--diag-vendor` | VERIFIED | All 7 tests present and pass (26 tests total in both files) |
| `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` | Edgar-authored confirmation evidence for CONF-01 and CONF-02 | VERIFIED | File exists; two machine entries; both CONFIRMED-MATCH; raw `--diag-vendor` output in `<details>` blocks |
| `.planning/STATE.md` | Blocker line removed; status phase-complete; percent 50 | VERIFIED | `status: phase-complete`; no "unconfirmed" blocker line; `percent: 50`; Phase 18 pointer |
| `.planning/REQUIREMENTS.md` | CONF-01/02 marked complete; traceability table closed | VERIFIED | `[x]` checkboxes; traceability rows with `complete` status |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main.py _run_cli_diag_vendor` | `collectors/windows/vendor.py diag_vendor_paths` | `from collectors.windows.vendor import diag_vendor_paths` (lazy import) | WIRED | `main.py` line 130; lazy import inside `_run_cli_diag_vendor` body |
| `collectors/windows/vendor.py diag_vendor_paths` | `collectors/windows/apps.py UNINSTALL_PATHS` | `for hive, path in UNINSTALL_PATHS` | WIRED | `vendor.py` line 15 imports `UNINSTALL_PATHS`; line 127 iterates it |
| `main.py argparse dispatcher` | `args.diag_vendor` short-circuit | `if args.diag_vendor:` BEFORE `--app` block | WIRED | `main.py` lines 197-204 precede lines 207-212; Test 7 enforces ordering |
| `vendor.py LSU comment block` | `17-IT-CONFIRMATION.md` | Code comment cites artifact filename | WIRED | `vendor.py` line 74: `17-IT-CONFIRMATION.md` present in comment |
| `17-IT-CONFIRMATION.md` | Plan 17-03 conditional patch decision | Plan 17-03 reads Summary table before any code change | WIRED | Plan 17-03 Summary: `option-no-changes` decision made from Summary table; REQUIREMENTS.md updated |

---

### Data-Flow Trace (Level 4)

Not applicable for this phase. Phase 17 produces a diagnostic CLI tool (`--diag-vendor`) that reads live registry and filesystem — no component renders dynamic data from a stored/fetched source that could be hollow. The tool's output is always direct from registry enumeration and `Path.exists()` calls at runtime. No Level 4 trace needed.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `diag_vendor_paths` importable | `python -c "from collectors.windows.vendor import diag_vendor_paths"` | Exit 0 (no error) | PASS |
| `--diag-vendor` in argparse help | Covered by Test 6 (`test_diag_vendor_flag_in_help`) | Test passes | PASS |
| Full suite — 284 tests pass | `python -m pytest -x -q` | 284 passed, 0 failed | PASS |
| Phase 17 tests only (26 tests) | `python -m pytest tests/test_vendor_collector.py tests/test_cli_phase17.py -x -q` | 26 passed | PASS |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CONF-01 | 17-01, 17-02, 17-03 | Dell Command Update registry path confirmed against enrolled Dell machines | SATISFIED | `17-IT-CONFIRMATION.md` dev-dell-justin entry; REQUIREMENTS.md `[x] CONF-01`; traceability row `complete` |
| CONF-02 | 17-01, 17-02, 17-03 | Lenovo updater family registry path confirmed against enrolled Lenovo machines | SATISFIED | `17-IT-CONFIRMATION.md` dev-lenovo-justin entry; REQUIREMENTS.md `[x] CONF-02`; traceability row `complete` |

Drive-by requirements closed in Plan 17-03 Task 3 (correct — these were Phase 16 requirements with no prior traceability closure):

| Requirement | Drive-by Plan | Status | Evidence |
|-------------|--------------|--------|----------|
| DEBT-01 | 16-01 (closed via 17-03 drive-by) | SATISFIED | REQUIREMENTS.md `[x] DEBT-01`; traceability row Phase 16 / 16-01 / complete |
| DEBT-02 | 16-02 (closed via 17-03 drive-by) | SATISFIED | REQUIREMENTS.md `[x] DEBT-02`; traceability row Phase 16 / 16-02 / complete |
| DEBT-03 | 16-02 (closed via 17-03 drive-by) | SATISFIED | REQUIREMENTS.md `[x] DEBT-03`; traceability row Phase 16 / 16-02 / complete |

---

### Anti-Patterns Found

No blockers or warnings found. Specific checks run on Phase 17 modified files:

| File | Pattern | Severity | Result |
|------|---------|----------|--------|
| `collectors/windows/vendor.py` | TODO/FIXME/placeholder | Info | None found in Phase 17 additions |
| `collectors/windows/vendor.py` | Empty implementations (return null/[]/\{\}) | Info | None — `diag_vendor_paths` has real implementation |
| `main.py` | `_run_cli_diag_vendor` stub patterns | Info | None — full implementation with Darwin gate + lazy import |
| `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` | `_pending Edgar run_` placeholder rows | Info | Summary table fully populated; `_pending Edgar run_` no longer present in Status/Disposition columns |

One notable non-blocker: the `17-IT-CONFIRMATION.md` entries were run on a developer's personal machines (`dev-lenovo-justin`, `dev-dell-justin`) rather than enrolled fleet machines. The plan's BY-PROXY path (D-15/D-16) explicitly permits this and the evidence format meets the D-06 floor requirements. Phase 19 is the live-fleet safety net.

---

### Human Verification Required

None. All must-haves are mechanically verifiable:
- Code artifacts exist and are substantive (not stubs)
- Key links are wired (import chain verified)
- Tests pass (284/284)
- Planning artifacts (STATE.md, REQUIREMENTS.md, 17-IT-CONFIRMATION.md) contain the required content
- Blocker line removed from STATE.md (grep-confirmed 0 matches)

---

### Gaps Summary

No gaps. All three ROADMAP success criteria are satisfied:

1. **SC-1 (Dell confirmation):** `17-IT-CONFIRMATION.md` contains a Dell machine entry with CONFIRMED-MATCH disposition. No code change was needed.
2. **SC-2 (Lenovo confirmation):** `17-IT-CONFIRMATION.md` contains a Lenovo machine entry with CONFIRMED-MATCH disposition. No code change was needed.
3. **SC-3 (No regressions + blockers removed):** 284 tests pass; the registry-path uncertainty blocker line is absent from STATE.md; CONF-01 and CONF-02 are marked complete in REQUIREMENTS.md.

The `--diag-vendor` CLI diagnostic was shipped as the mechanism that enabled Edgar/IT to produce the confirmation evidence. The tool is substantively implemented, wired through argparse dispatch, tested with 16 new tests (9 unit + 7 CLI), and proven to build into a working `.exe` via PyInstaller smoke test.

---

_Verified: 2026-05-20T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
