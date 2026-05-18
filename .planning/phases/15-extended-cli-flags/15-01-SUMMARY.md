---
phase: 15-extended-cli-flags
plan: "01"
subsystem: cli
tags: [argparse, json, output-path, app-detection, cli-flags]
dependency_graph:
  requires: [main.py, collectors/windows/apps.py, collectors/mac/apps.py, models.py]
  provides: [--json flag, --output flag, --app flag, _run_cli_app(), _find_app_spec(), _format_app_status_line()]
  affects: [main.py, tests/test_cli_phase15.py]
tech_stack:
  added: []
  patterns: [argparse flag extension, dataclasses.asdict() JSON serialization, platform dispatch for app specs, inline try/except JSON write co-located with HTML write]
key_files:
  created: [tests/test_cli_phase15.py]
  modified: [main.py]
decisions:
  - "D-05: --json overrides --name/--serial/--warnings — full pipeline runs even when targeted flags present"
  - "D-07: json.dumps(dataclasses.asdict(report), indent=2, default=str) — default=str handles any non-serializable edge cases"
  - "D-13: --app --json writes raw AppStatus dict to stdout, no files written"
  - "ROADMAP SC2 already updated during planning — no file change needed in Task 3"
metrics:
  duration: "~2 minutes"
  completed: "2026-05-18"
  tasks_completed: 3
  files_changed: 2
---

# Phase 15 Plan 01: Extended CLI Flags Summary

**One-liner:** Added `--json`, `--output PATH`, and `--app NAME` argparse flags to `main.py` with platform dispatch, `dataclasses.asdict()` JSON serialization, and 7 new tests (291 total).

## What Was Built

Three new CLI flags for `scry.exe`:

- `--json`: Runs the full pipeline and writes an `AuditReport` JSON file alongside the HTML report in `logs/`. JSON filename mirrors HTML (same uniqueness counter, `.json` extension). `[SUMMARY]` still prints. Overrides `--name`/`--serial`/`--warnings` (D-05).
- `--output PATH`: Overrides the default `logs/` destination for all file output. Any writable path accepted (D-02 — no validation). Applied before `mkdir` so the target directory is created if absent.
- `--app NAME`: Case-insensitive substring match against `APP_SPECS` (Windows) or `MAC_APP_SPECS` (Mac). Prints single-line `"<name>: installed (v<version>)"` or `"<name>: not installed"` to stdout and exits. With `--json`, prints raw `AppStatus` dict as JSON to stdout; no files written (D-13).

New functions in `main.py`:
- `_find_app_spec(query, specs)` — substring/contains match, first-wins, case-insensitive
- `_format_app_status_line(app_status)` — version/service_state/bare installed format
- `_run_cli_app(args)` — platform dispatch, minimal AuditReport, single-spec detection, stdout exit

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add --json, --output, --app flags to main.py | edee462 | main.py (+85 lines) |
| 2 | Write tests/test_cli_phase15.py with 7 tests | 3fb1b1f | tests/test_cli_phase15.py (new, 205 lines) |
| 3 | Update ROADMAP.md Phase 15 SC2 (D-03) | — | No change needed (already correct) |

## Verification

- `python -m pytest tests/ -v` — 291 passed (284 existing + 7 new)
- `python -c "import main"` — exits 0
- `python main.py --help` — lists `--json`, `--output PATH`, `--app NAME`
- ROADMAP.md contains "any writable path is accepted"; does not contain "is rejected with a clear error"

## Deviations from Plan

### Task 3: ROADMAP.md already correct

**Found during:** Task 3
**Issue:** ROADMAP.md Phase 15 SC2 already read "any writable path is accepted" and already contained the 15-01-PLAN.md plans list entry — updated during the planning phase (commit c1a77d9).
**Fix:** No change needed. Verified with Python assertion that acceptance criteria already met.
**Files modified:** None
**Impact:** No regression; all acceptance criteria passed.

## Known Stubs

None — all three flags are fully wired end-to-end. No placeholder data sources.

## Threat Flags

No new threat surface beyond what is documented in the plan's threat model (T-15-01 through T-15-05). All threats accepted per user decisions D-02/D-03.

## Self-Check: PASSED

- [x] `main.py` exists and contains all 14 acceptance criteria strings
- [x] `tests/test_cli_phase15.py` exists with 7 test functions
- [x] Commit `edee462` exists (Task 1)
- [x] Commit `3fb1b1f` exists (Task 2)
- [x] Full test suite: 291 passed
- [x] `python main.py --help` lists all three new flags
