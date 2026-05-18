---
phase: 15-extended-cli-flags
verified: 2026-05-18T00:00:00Z
status: gaps_found
score: 8/8 must-haves verified
overrides_applied: 0
gaps:
  - truth: "REQUIREMENTS.md reflects completed status for OUT-V3-01, OUT-V3-02, CLI-V3-01"
    status: failed
    reason: "All three requirement IDs remain marked '[ ]' (Pending) in REQUIREMENTS.md and 'Pending' in the traceability table. The implementation is complete, but the tracking document was not updated post-execution."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "Lines 32-34: OUT-V3-01, OUT-V3-02, CLI-V3-01 still show '- [ ]' (unchecked). Lines 74-76: traceability table still reads 'Pending' for all three. OUT-V3-02 description still says 'validates resolved path does not write to the host PC' — contradicts accepted D-02/D-03 decision and updated ROADMAP SC2."
    missing:
      - "Change '- [ ] **OUT-V3-01**' to '- [x] **OUT-V3-01**' in REQUIREMENTS.md"
      - "Change '- [ ] **OUT-V3-02**' to '- [x] **OUT-V3-02**' in REQUIREMENTS.md"
      - "Change '- [ ] **CLI-V3-01**' to '- [x] **CLI-V3-01**' in REQUIREMENTS.md"
      - "Update traceability table: change all three 'Pending' entries to 'Complete' for Phase 15"
      - "Update OUT-V3-02 description to remove 'validates resolved path does not write to the host PC' language and replace with 'any writable path is accepted' to match D-02/D-03 decision and ROADMAP.md SC2"
---

# Phase 15: Extended CLI Flags Verification Report

**Phase Goal:** IT staff and NinjaOne scripts can retrieve audit output as JSON, override the output path, and query a single app — without generating a full HTML report when not needed
**Verified:** 2026-05-18
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running scry.exe --json writes a .json file alongside the .html file in logs/ | VERIFIED | main.py:237 derives `json_path = output_path.with_suffix(".json") if args.json else None`; main.py:243-245 writes it inside HTML try/except. Test 5 passes: asserts exactly one `.json` in written paths. |
| 2 | Running scry.exe --output <path> writes HTML (and JSON when --json is also passed) to the provided path, not logs/ | VERIFIED | main.py:226-229: `if args.output: logs_dir = Path(args.output)`. Test 6 passes: asserts written path contains `custom/audit_results`. |
| 3 | Running scry.exe --app ninjaone prints a single-line result to stdout and exits without generating any report | VERIFIED | `_run_cli_app()` at main.py:118-158 prints formatted line and calls `sys.exit(0)`. No `write_text` is called. Tests 1 and 2 pass. |
| 4 | Running scry.exe --app ninjaone --json prints a JSON blob for the app to stdout; no files written | VERIFIED | main.py:151-153: when `args.json` in `_run_cli_app`, prints `json.dumps(dataclasses.asdict(app_status))` to stdout. Test 4 passes: asserts `mock_write.call_count == 0` and parses JSON from stdout. |
| 5 | App name matching is case-insensitive: 'ninjaone', 'NinjaOne', 'NINJAONE' all resolve to the NinjaOne entry | VERIFIED | `_find_app_spec()` at main.py:98-104 uses `q = query.lower()` and `spec["name"].lower()` for substring match. Tests 1 and 2 use lowercase "ninjaone" and resolve to "NinjaOne" spec. |
| 6 | Running scry.exe --app unknowntool exits with code 1 and prints 'Unknown app: ...' to stderr | VERIFIED | main.py:131-134: `if spec is None: print(..., file=sys.stderr); sys.exit(1)`. Test 3 passes: asserts exit code 1 and "Unknown app: unknowntool" in stderr. |
| 7 | Running scry.exe --json --name runs the full pipeline (not the _run_cli targeted path); [SUMMARY] is printed | VERIFIED | main.py:183: `if cli_mode and not args.json:` — the `not args.json` guard prevents `_run_cli()` when `--json` is present. Test 7 passes: asserts `[SUMMARY]` in stdout when `--json --name` combined. |
| 8 | Running scry.exe with no new flags still emits [SUMMARY] and writes the HTML report (no regression) | VERIFIED | Full 291-test suite passes (284 existing + 7 new). `python -m pytest tests/ -v` exits 0 with 291 passed. No behavioral changes to existing flags. |

**Score:** 8/8 truths verified (code and tests)

### ROADMAP Success Criteria

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| SC1 | Running scry.exe --json produces a valid JSON file in logs/ alongside the HTML report | VERIFIED | json_path derived at main.py:237; written inside HTML try/except at main.py:243-245. Test 5 confirms exactly one .json written. |
| SC2 | Running scry.exe --output D:\audit_results writes both HTML and JSON (when --json also passed) to that path; any writable path is accepted | VERIFIED | main.py:226-229 overrides logs_dir with Path(args.output). No validation. ROADMAP.md SC2 contains "any writable path is accepted". Test 6 confirms path override. |
| SC3 | Running scry.exe --app ninjaone prints a single-line result to stdout and exits without generating an HTML or JSON report | VERIFIED | _run_cli_app() prints result and calls sys.exit(0) before any file write logic. Tests 1, 2, 3 confirm. |
| SC4 | Running scry.exe --app ninjaone --json prints a JSON blob for that one app to stdout; app name matching is case-insensitive | VERIFIED | main.py:151-153 handles --app --json. _find_app_spec uses .lower(). Test 4 confirms JSON stdout output and no file writes. |

**All 4 ROADMAP success criteria met.**

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `main.py` | --json, --output, --app argparse args; _run_cli_app(), _find_app_spec(), _format_app_status_line() | VERIFIED | All three flags registered at lines 170-172. All three functions present at lines 98-158. Contains `parser.add_argument("--json"`. |
| `main.py` | logs_dir override for --output | VERIFIED | `args.output` check at line 226. `logs_dir = Path(args.output)` at line 227. |
| `main.py` | JSON write alongside HTML for --json | VERIFIED | `dataclasses.asdict(report)` at line 244 inside HTML try/except block. |
| `tests/test_cli_phase15.py` | 7 test functions covering all three new flags and their interactions | VERIFIED | All 7 functions present (lines 69, 90, 111, 130, 156, 176, 195). All 7 pass. |
| `.planning/ROADMAP.md` | Updated SC2 removing host-path rejection language (D-03) | VERIFIED | Line 103 contains "any writable path is accepted". "is rejected with a clear error" does not appear anywhere in ROADMAP.md. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| main.py _run_cli_app() | collectors/windows/apps._detect_one_app or collectors/mac/apps._detect_one_app | platform dispatch on sys.platform | WIRED | main.py:125-128: `if sys.platform == "darwin": from collectors.mac.apps import ...` else `from collectors.windows.apps import ...`. Pattern `sys.platform.*darwin` confirmed at line 125. |
| main.py main() | json_path.write_text | args.json check inside existing HTML try/except block | WIRED | main.py:243-245: `if args.json:` inside the same `try:` block as `output_path.write_text`. Pattern `args.json` confirmed at line 243. |
| main.py main() | logs_dir assignment | args.output check before mkdir call | WIRED | main.py:226-230: `if args.output: logs_dir = Path(args.output)` followed by `logs_dir.mkdir(...)`. Pattern `args.output` confirmed at line 226. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| main.py (--json path) | `report` (AuditReport) | `collect_all(report)` at line 199 | Yes — collect_all mutates report with real hardware/app data | FLOWING |
| main.py (--app path) | `app_status` (report.apps[0]) | `_detect_one_app(spec, report)` at line 143 | Yes — platform-appropriate detector queries registry/filesystem | FLOWING |
| main.py (--output path) | `logs_dir` (Path) | `Path(args.output)` at line 227 | Yes — direct user-provided path, no stub | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| main.py syntax valid | `python -c "import ast, pathlib; ast.parse(pathlib.Path('main.py').read_text(encoding='utf-8')); print('syntax OK')"` | `syntax OK` | PASS |
| --help lists all three flags | `python main.py --help` | Output contains `--json`, `--output PATH`, `--app NAME` | PASS |
| All 7 phase 15 tests pass | `python -m pytest tests/test_cli_phase15.py -v` | 7 passed | PASS |
| Full test suite — no regression | `python -m pytest tests/ -v` | 291 passed (284 existing + 7 new) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| OUT-V3-01 | 15-01-PLAN.md | --json flag serializes full AuditReport to JSON alongside HTML; uses dataclasses.asdict() + json.dumps() | SATISFIED | main.py:237,244-245. Test 5 confirms. |
| OUT-V3-02 | 15-01-PLAN.md | --output <path> overrides default logs/ destination | SATISFIED (with deviation) | main.py:226-229. Path validation was removed per D-02/D-03 decision; ROADMAP SC2 updated to reflect this. REQUIREMENTS.md still shows old validation language and Pending status — documentation gap only. |
| CLI-V3-01 | 15-01-PLAN.md | --app <name> runs single-app detection pipeline; --app --json produces single-app JSON blob; case-insensitive matching | SATISFIED | main.py:98-158. Tests 1-4 confirm all behaviors. |

**Note on OUT-V3-02:** The REQUIREMENTS.md description still says "validates resolved path does not write to the host PC" — this validation was explicitly removed per decisions D-02/D-03 (accepted by user during planning). ROADMAP.md SC2 was correctly updated, but REQUIREMENTS.md was not. The implementation matches the accepted decision, not the stale REQUIREMENTS.md text.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | — |

No TODO, FIXME, placeholder, stub, or empty-return patterns found in main.py or tests/test_cli_phase15.py.

### Human Verification Required

None. All behaviors are fully testable programmatically. The test suite covers all new code paths including platform dispatch (patched), file write interception, stdout/stderr capture, and JSON round-trip validation.

### Gaps Summary

**1 gap identified — documentation only, code is complete:**

The code implementation is fully correct. All three new flags work as designed, all 7 tests pass, and all 291 tests in the suite pass with no regressions. The sole gap is that `.planning/REQUIREMENTS.md` was not updated to reflect completion:

- OUT-V3-01, OUT-V3-02, CLI-V3-01 remain `[ ]` (unchecked) in the requirements list
- All three appear as "Pending" in the traceability table
- OUT-V3-02's description still contains the old host-path validation language that was explicitly removed (D-02/D-03)

This gap does not affect running functionality. The ROADMAP.md was correctly updated (SC2). Only REQUIREMENTS.md needs to be reconciled.

---

_Verified: 2026-05-18_
_Verifier: Claude (gsd-verifier)_
