---
phase: 17-it-registry-path-confirmation
plan: "01"
subsystem: vendor-detection-cli
tags: [cli, diagnostics, vendor, registry, tdd, pyinstaller]
dependency_graph:
  requires: []
  provides: [diag-vendor-flag, diag-vendor-paths-function, lsu-comment-block]
  affects: [main.py, collectors/windows/vendor.py, tests/test_vendor_collector.py, tests/test_cli_phase17.py]
tech_stack:
  added: []
  patterns: [short-circuit-cli-flag, never-raise-envelope, lazy-import-darwin-gate, per-hive-registry-enumeration]
key_files:
  created:
    - tests/test_cli_phase17.py
  modified:
    - collectors/windows/vendor.py
    - main.py
    - tests/test_vendor_collector.py
decisions:
  - "diag_vendor_paths patches vendor_mod.winreg (not apps_mod.winreg) in diagnostic tests — vendor.py imports winreg directly, so discovery-test mocking must target vendor_mod's winreg binding"
  - "LSU comment block uses lowercase 'defensive' to satisfy grep-based Test 9 (case-sensitive)"
  - "Test 3 uses inline open_key_side_effect to track current_subkey name — locked design (Step B.5: no change to shared _make_query_fn helper)"
  - "Task 4 STATE.md fix was a no-op — line 24 already read '(IT Registry Path Confirmation)'"
metrics:
  duration: "305 seconds (~5 minutes)"
  completed: "2026-05-20"
  tasks_completed: 4
  tests_added: 16
  files_modified: 4
---

# Phase 17 Plan 01: Vendor Diagnostic Tool (--diag-vendor) Summary

**One-liner:** `--diag-vendor` CLI diagnostic with per-hive Dell/Lenovo registry dump + DCU XML probe, wired to main.py before `--app` dispatch, with LSU keyword comment block citing `17-IT-CONFIRMATION.md`.

## What Was Built

### Task 1: `diag_vendor_paths` + LSU comment block (vendor.py)

Added `diag_vendor_paths(stream=None)` to `collectors/windows/vendor.py`:
- Reuses `UNINSTALL_PATHS` from `collectors/windows/apps.py` (D-01 — no duplicate hive list)
- Walks all 4 hives, prints every subkey whose `DisplayName` contains "dell" or "lenovo" (D-02, D-12)
- Probes `DCU_XML_PATH`: existence, file size, `<update>` element count (D-03)
- Never raises — per-hive exceptions print a one-line note (matching production envelope)
- Outputs to `stream` argument (default `sys.stdout`)

Added LSU keyword list comment block above the `_search_uninstall_keys()` call in `_detect_lsu()`:
- Contains all 7 Test 9 grep-asserted substrings
- Cites `17-IT-CONFIRMATION.md` for traceability
- Labels Edgar-confirmed entries (`Lenovo Vantage`, `Lenovo Commercial Vantage`) vs. defensive entries

Added 9 tests in `TestDiagVendorPaths` in `tests/test_vendor_collector.py`:
- Test 1: All 4 hive labels printed even when hives fail
- Test 2: Dell match surfaces DisplayName, DisplayVersion, hive label, field names
- Test 3 (D-12 DISCOVERY): Unknown Lenovo* string (`"Lenovo Hotkey Driver"`) appears; `"Microsoft Edge"` excluded
- Test 4: No-match path prints `"no matching entries"`
- Tests 5-7: DCU XML present (2 updates), absent, malformed
- Test 8: Never raises on RuntimeError
- Test 9: Source-grep for 7 required LSU comment block substrings

### Task 2: `--diag-vendor` flag in main.py

Added `_run_cli_diag_vendor(args)` function in `main.py`:
- Darwin gate: exits 0 with stderr note (`"--diag-vendor is Windows-only; nothing to probe on darwin"`)
- Lazy import of `diag_vendor_paths` (S3 comment — guards against future module-top import hoisting)
- Calls `diag_vendor_paths()` then `sys.exit(0)`

Added argparse `--diag-vendor` flag (`action="store_true"`).

Added dispatcher block ABOVE `--app` block (B1 ordering contract):
- Prints `"WARNING: --output is ignored in --diag-vendor mode"` to stderr when `--output` combined
- Calls `_run_cli_diag_vendor(args)` then returns

Created `tests/test_cli_phase17.py` with 7 tests:
- Test 1: exits 0 and calls `diag_vendor_paths`
- Test 2: `--output` produces stderr warning
- Test 3: does not invoke `collect_all` or `render_html`
- Test 4: dispatched before `--warnings` (cli_mode gate)
- Test 5: Darwin exits 0 with stderr note
- Test 6: `--diag-vendor` appears in `--help` output
- Test 7 (B1): `--diag-vendor --app chrome` routes to diag handler, not `_run_cli_app`

### Task 3: PyInstaller smoke build (CHECKPOINT — APPROVED)

Build ran via `.venv\Scripts\python.exe -m PyInstaller scry.spec` producing `dist\scry_v3.1\scry_v3.1.exe`.
Smoke test confirmed:
- Exit code: 0
- `=== SCRY --diag-vendor — Dell/Lenovo Uninstall entries ===` header printed
- All 4 hive labels present (HKLM, HKLM\Wow6432Node, HKCU, HKCU\Wow6432Node)
- `=== DCU XML probe ===` section present
- W5 build-risk cleared before Edgar's checkpoint (Plan 17-02)

### Task 4: Full suite regression + STATE.md drift fix

- Full test suite: **284 passed, 0 failed** (268 pre-existing + 16 new)
- STATE.md line 24 was already correct: `v3.1 Cleanup — Phase 17 next (IT Registry Path Confirmation)` — no modification needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 3 required patching `vendor_mod.winreg` not `apps_mod.winreg`**

- **Found during:** Task 1, Test 3 (D-12 discovery test)
- **Issue:** `diag_vendor_paths` imports `winreg` directly in `vendor.py` (`import winreg`). The original test design in the plan patched `apps_mod.winreg.OpenKey`, but the diagnostic function calls `vendor_mod.winreg.OpenKey` directly. Patching `apps_mod.winreg` had no effect on `diag_vendor_paths`.
- **Fix:** Test 3 now patches `vendor_mod.winreg.OpenKey`, `vendor_mod.winreg.EnumKey`, and `vendor_mod.winreg.QueryValueEx`. The inline `open_key_side_effect` tracks which subkey is being opened to route the `QueryValueEx` mock correctly. Locked design per Step B.5 — `_make_query_fn` helper is unchanged.
- **Files modified:** `tests/test_vendor_collector.py`
- **Commit:** `6257e7d`

**2. [Rule 1 - Bug] LSU comment block used capital "Defensive" — Test 9 grep is case-sensitive**

- **Found during:** Task 1, Test 9
- **Issue:** The comment block was written with `"# Defensive entries — ..."` (capital D). Test 9 asserts lowercase `"defensive"` is present (case-sensitive substring match).
- **Fix:** Changed to lowercase `"# defensive entries — ..."`.
- **Files modified:** `collectors/windows/vendor.py`
- **Commit:** `6257e7d`

## Checkpoint: Task 3 PyInstaller Smoke Build

**Type:** checkpoint:human-verify
**Status:** APPROVED — build successful, --diag-vendor smoke test passed on Windows

**Build:** `.venv\Scripts\python.exe -m PyInstaller scry.spec` → `dist\scry_v3.1\scry_v3.1.exe` (2026-05-20)
**Smoke test:** `dist\scry_v3.1\scry_v3.1.exe --diag-vendor` → exit 0, all 4 hive headers + DCU XML probe section in stdout
**W5 mitigation:** Build-risk cleared before Edgar's Plan 17-02 checkpoint — the .exe Edgar will copy to a flash drive is proven to work

## Test Count Delta

+16 tests:
- +9 in `TestDiagVendorPaths` class (`tests/test_vendor_collector.py`)
- +7 in `tests/test_cli_phase17.py`

Total: 284 tests (268 pre-existing + 16 new)

## Known Stubs

None — `diag_vendor_paths` reads live registry and filesystem (no hardcoded stubs).

## Threat Flags

No new attack surface introduced beyond what the plan's threat model covers (T-17-01 through T-17-04). `diag_vendor_paths` reads the same registry paths as the production `_search_uninstall_keys`.

## Self-Check: PASSED

All files verified present:
- FOUND: `collectors/windows/vendor.py`
- FOUND: `main.py`
- FOUND: `tests/test_vendor_collector.py`
- FOUND: `tests/test_cli_phase17.py`
- FOUND: `.planning/phases/17-it-registry-path-confirmation/17-01-SUMMARY.md`

All commits verified present:
- FOUND: `6257e7d` — feat(17-01): add diag_vendor_paths to vendor.py + LSU comment block
- FOUND: `e3e18e8` — feat(17-01): wire --diag-vendor argparse flag + _run_cli_diag_vendor in main.py
