---
phase: 14-vendor-update-detection
verified: 2026-05-18T00:00:00Z
status: human_needed
score: 17/17 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open test_vendor_render_case1.html in a browser (DCU installed, 2 pending; LSU not installed)"
    expected: "System Health section shows 'Dell Cmd Update' row with value '2 pending' (not muted); 'Lenovo Sys Update' row with value 'Not installed' (muted/gray)"
    why_human: "Visual rendering of HTML and CSS muted style cannot be verified programmatically"
  - test: "Open test_vendor_render_case2.html in a browser (DCU installed, no scan data; LSU installed)"
    expected: "'Dell Cmd Update' row shows 'Unknown (no scan data)' (muted/gray); 'Lenovo Sys Update' row shows 'N/A' (muted/gray)"
    why_human: "Visual rendering of HTML and CSS muted style cannot be verified programmatically"
  - test: "Open test_vendor_render_case3.html in a browser (--updates not passed, both fields None)"
    expected: "System Health section contains neither 'Dell Cmd Update' nor 'Lenovo Sys Update' rows; no errors or placeholder text"
    why_human: "Absence of rows cannot be verified without rendering the full Jinja2 template visually"
  - test: "Run scry.exe --updates on a real Dell machine where DCU has run at least once"
    expected: "Character sheet System Health section shows 'Dell Cmd Update' with a pending count integer (e.g. '2 pending')"
    why_human: "Registry detection and XML path are Windows-only and require a real Dell machine with DCU installed"
  - test: "Run scry.exe --updates on a non-Dell, non-Lenovo machine"
    expected: "Character sheet shows 'Not installed' for both Dell Cmd Update and Lenovo Sys Update; no errors or crashes"
    why_human: "Live registry behavior cannot be tested without a real Windows machine"
---

# Phase 14: Vendor Update Detection Verification Report

**Phase Goal:** IT staff can see whether Dell Command Update or Lenovo System Update is installed and how many vendor updates are pending, without the tool invoking any vendor CLI
**Verified:** 2026-05-18
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | VendorUpdateStatus dataclass exists in models.py with installed, pending_count, scan_data_present fields | VERIFIED | models.py lines 62-70; all three fields present with correct types |
| 2 | AuditReport has dell_dcu and lenovo_lsu fields immediately after pending_updates | VERIFIED | models.py lines 90-91; field order confirmed: pending_updates → dell_dcu → lenovo_lsu → local_profiles |
| 3 | collect_vendor_updates(report) populates dell_dcu when DCU is in registry | VERIFIED | vendor.py _detect_dcu(); test_dcu_installed_xml_absent passes |
| 4 | collect_vendor_updates(report) populates dell_dcu with scan data from DCUApplicableUpdates.xml when present | VERIFIED | vendor.py lines 38-49 parse XML; tests for 2 updates, 0 updates, parse error all pass |
| 5 | collect_vendor_updates(report) populates lenovo_lsu when LSU is in registry | VERIFIED | vendor.py _detect_lsu(); test_lsu_installed_pending_count_always_none passes |
| 6 | collect_vendor_updates is called only when --updates is passed (both main.py locations) | VERIFIED | main.py lines 59-60 (_run_cli) and 128-129 (main()), both inside `if args.updates and sys.platform != "darwin"` blocks |
| 7 | No vendor CLI is ever invoked; detection is registry-only, count is XML-only | VERIFIED | grep for dcu-cli and tvsu.exe in vendor.py returns no matches |
| 8 | All vendor collector tests pass; overall test suite count does not regress | VERIFIED | 10/10 test_vendor_collector.py tests pass; full suite 284 passed (was 256 prior to phase 14) |
| 9 | _build_context returns dell_dcu_display and lenovo_lsu_display keys covering all D-07/D-08 states | VERIFIED | renderer/__init__.py lines 166-215; all display branches present and tested |
| 10 | When --updates is passed and DCU installed with pending count, character sheet shows "N pending" in System Health | VERIFIED | Template line 431 renders dell_dcu_display; renderer test test_dell_dcu_installed_xml_present_pending_count passes ("3 pending") |
| 11 | When --updates is passed and DCU installed but XML absent, character sheet shows "Unknown (no scan data)" | VERIFIED | renderer/__init__.py line 173; test_dell_dcu_installed_xml_absent passes |
| 12 | When --updates is passed and DCU not installed, character sheet shows "Not installed" | VERIFIED | renderer/__init__.py line 171; test_dell_dcu_not_installed passes |
| 13 | When --updates is passed and LSU installed, character sheet shows "N/A" in System Health | VERIFIED | renderer/__init__.py line 185; test_lenovo_lsu_installed_shows_na passes |
| 14 | When --updates is passed and LSU not installed, character sheet shows "Not installed" | VERIFIED | renderer/__init__.py line 185; test_lenovo_lsu_not_installed passes |
| 15 | When --updates is NOT passed, vendor rows are completely absent from rendered HTML | VERIFIED | Template uses `{% if dell_dcu_display is not none %}` (lines 429, 434); test_dell_dcu_none_when_updates_not_passed and test_lenovo_lsu_none_when_updates_not_passed pass |
| 16 | Vendor rows appear inside the existing System Health block — no new section header added | VERIFIED | character_sheet.html lines 429-437 insert rows between Pending Updates and closing </div>; no new section header added |
| 17 | muted CSS class applied to "Not installed", "Unknown (no scan data)", and "N/A" values | VERIFIED | character_sheet.html lines 431, 436; muted applied for "Not installed" and "Unknown (no scan data)" on Dell row; "Not installed" and "N/A" on Lenovo row |

**Score:** 17/17 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `models.py` | VendorUpdateStatus dataclass; dell_dcu + lenovo_lsu on AuditReport | VERIFIED | VendorUpdateStatus at line 62; dell_dcu at line 90, lenovo_lsu at line 91 |
| `collectors/windows/vendor.py` | collect_vendor_updates public function | VERIFIED | Exists; collect_vendor_updates exported at line 19 |
| `tests/test_vendor_collector.py` | 10 unit tests covering all collection paths | VERIFIED | TestCollectVendorUpdates class with 10 tests, all passing |
| `renderer/__init__.py` | dell_dcu_display and lenovo_lsu_display in _build_context return dict | VERIFIED | Lines 166-215 compute display values; lines 214-215 in return dict |
| `renderer/templates/character_sheet.html` | Conditional vendor rows in System Health block | VERIFIED | Lines 429-437; Jinja2 conditional blocks for both rows |
| `tests/test_renderer_phase14.py` | Renderer tests for all vendor display paths | VERIFIED | TestVendorDisplayValues class with 10 tests, all passing |
| `tests/test_models_phase14.py` | Model tests for VendorUpdateStatus variants | VERIFIED | 8 tests (bonus artifact noted in summary; not in plan must_haves) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `collectors/windows/vendor.py` | `collectors/windows/apps.py` | `_search_uninstall_keys` import | WIRED | Line 13: `from collectors.windows.apps import _search_uninstall_keys`; used at lines 32 and 66 |
| `main.py` | `collectors/windows/vendor.py` | --updates gate (two locations) | WIRED | Lines 59-60 (_run_cli) and 128-129 (main()); both inside `if args.updates` blocks |
| `collectors/windows/vendor.py` | `models.VendorUpdateStatus` | VendorUpdateStatus instantiation | WIRED | Lines 51-55, 58-60, 67-71, 74-76 all instantiate VendorUpdateStatus with `installed=` keyword |
| `renderer/__init__.py` | `renderer/templates/character_sheet.html` | dell_dcu_display and lenovo_lsu_display context keys | WIRED | Both keys in return dict lines 214-215; template references them at lines 429-436 |
| `character_sheet.html` | `dell_dcu_display` | Jinja2 conditional `{% if dell_dcu_display is not none %}` | WIRED | Line 429 uses `is not none` (lowercase, correct Jinja2 syntax) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `character_sheet.html` (dell row) | `dell_dcu_display` | `renderer/_build_context()` derives from `report.dell_dcu` which is populated by `collect_vendor_updates()` from registry + XML | Yes — registry read via `_search_uninstall_keys`; XML parsed with `ET.parse` | FLOWING |
| `character_sheet.html` (lenovo row) | `lenovo_lsu_display` | `renderer/_build_context()` derives from `report.lenovo_lsu` which is populated by `collect_vendor_updates()` from registry | Yes — registry read via `_search_uninstall_keys` | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| VendorUpdateStatus importable and fields correct | `python -c "from models import VendorUpdateStatus, AuditReport; r = AuditReport(hostname='X', parsed_hostname=None); assert r.dell_dcu is None and r.lenovo_lsu is None; print('OK')"` | model OK | PASS |
| vendor.py imports clean, no CLI invocations | `grep dcu-cli tvsu.exe collectors/windows/vendor.py` | no matches | PASS |
| collect_vendor_updates at both main.py --updates gates | `grep -c "collect_vendor_updates" main.py` | 4 | PASS |
| 10 vendor collector tests pass | `pytest tests/test_vendor_collector.py` | 10 passed | PASS |
| 10 renderer phase 14 tests pass | `pytest tests/test_renderer_phase14.py` | 10 passed | PASS |
| Full suite passes with no regression | `pytest tests/` | 284 passed, 0 failures | PASS |
| All 8 commits referenced in summaries exist in git log | `git log --oneline | grep ...` | All 8 found (f437247, 77bf291, 78922cb, 1440add, aa78757, ed0f371, cc5367c, 16d6f2c) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| VENDOR-01 | 14-01, 14-02 | User can see Dell Command Update installation status and pending update count in character sheet; count read passively from DCUApplicableUpdates.xml (never invokes dcu-cli.exe) | SATISFIED | `vendor.py` reads XML passively; no CLI invocation confirmed by grep; renderer displays all D-07 states; tests cover all paths |
| VENDOR-02 | 14-01, 14-02 | User can see Lenovo System Update installation status in character sheet; pending count shown as N/A; never invokes tvsu.exe | SATISFIED | `vendor.py` detects LSU via registry only; pending_count always None per D-14; template shows "N/A" when installed; no CLI invocation confirmed by grep |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scanned all phase-14 modified files for: TODO/FIXME/placeholder comments, empty return values, hardcoded empty data, props with hardcoded empty values, console.log-only implementations. No issues found. The only `None` returns are intentional (LSU `pending_count=None` per D-14; display values `None` when --updates absent — both are design decisions, not stubs).

### Human Verification Required

Plan 14-02 includes a `checkpoint:human-verify` gate (blocking) that was reported as approved in the SUMMARY. This verification cannot be confirmed programmatically — the visual rendering of the HTML character sheet in a browser requires human eyes.

Additionally, live registry-based detection on real Dell/Lenovo hardware cannot be tested in CI.

#### 1. Visual render — DCU pending count

**Test:** Generate test_vendor_render_case1.html per Plan 02 checkpoint script; open in browser
**Expected:** System Health section shows "Dell Cmd Update" / "2 pending" (not muted); "Lenovo Sys Update" / "Not installed" (muted/gray)
**Why human:** CSS muted styling and row layout cannot be verified without browser rendering

#### 2. Visual render — DCU no scan data and LSU installed

**Test:** Generate test_vendor_render_case2.html per Plan 02 checkpoint script; open in browser
**Expected:** "Dell Cmd Update" / "Unknown (no scan data)" (muted/gray); "Lenovo Sys Update" / "N/A" (muted/gray)
**Why human:** CSS muted styling and row layout cannot be verified without browser rendering

#### 3. Visual render — --updates not passed

**Test:** Generate test_vendor_render_case3.html per Plan 02 checkpoint script; open in browser
**Expected:** System Health section contains neither "Dell Cmd Update" nor "Lenovo Sys Update" rows; no errors or placeholder text
**Why human:** Absence of rows from rendered HTML requires visual confirmation

#### 4. Live Dell machine validation

**Test:** Run scry.exe --updates on a real Dell machine where DCU has run at least once
**Expected:** Character sheet shows "Dell Cmd Update" with a pending count (e.g. "2 pending") in System Health
**Why human:** Requires real Dell hardware with DCU installed and DCUApplicableUpdates.xml present at `C:\ProgramData\Dell\UpdateService\Temp\`

#### 5. Live non-Dell/non-Lenovo machine

**Test:** Run scry.exe --updates on a non-Dell, non-Lenovo machine
**Expected:** Both vendor rows show "Not installed"; no crashes; no errors to console beyond any pre-existing collection errors
**Why human:** Live registry behavior requires a real Windows machine

### Gaps Summary

No automated gaps found. All 17 observable truths are VERIFIED, all artifacts exist and are substantive and wired, all key links are confirmed, and the full 284-test suite passes with zero failures.

The `human_needed` status reflects the Plan 02 blocking checkpoint (visual HTML rendering) and the inherent need for live hardware validation of registry-based detection — both standard for any Windows-only, registry-dependent feature.

The SUMMARY reports the visual checkpoint was approved by the developer. If the developer confirms this remains valid, the only remaining item is live hardware validation (item 4 and 5 above), which was noted as a known blocker in STATE.md.

---

_Verified: 2026-05-18_
_Verifier: Claude (gsd-verifier)_
