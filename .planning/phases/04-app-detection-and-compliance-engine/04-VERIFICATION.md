---
phase: 04-app-detection-and-compliance-engine
verified: 2026-05-05T00:00:00Z
status: human_needed
score: 6/7 must-haves verified (+ 1 override applied)
overrides_applied: 1
overrides:
  - must_have: "Each of the M365 apps (Word, Excel, Outlook, Teams, OneDrive) is detected individually and correctly reflects installed/missing state on a provisioned M365 machine"
    reason: "CONTEXT.md D-05 explicitly scoped this as a single suite entry: 'Detect M365 as a single suite entry — one AppStatus entry named Microsoft 365. No per-app individual entries for Word, Excel, Outlook, Teams, OneDrive.' The ROADMAP SC-3 was refined by the phase discussion and planning process. The APP_SPECS table implements the D-05 decision correctly and the renderer displays it as a single equipment row. This deviation was a deliberate product decision made before implementation began — not a missed requirement."
    accepted_by: "pending-developer-review"
    accepted_at: "2026-05-05T00:00:00Z"
human_verification:
  - test: "On a machine with NinjaOne installed, run the full pipeline (main.py or collect_all) and confirm the rendered HTML shows NinjaOne as INSTALLED with a version string."
    expected: "NinjaOne AppStatus row shows installed=True and a version such as 13.0.7346 in the equipment list."
    why_human: "Registry detection requires a real Windows machine with NinjaOne present. Mocks verify logic only — live registry access confirms no false-negative on a provisioned machine."
  - test: "On a machine with CrowdStrike Falcon installed, run the full pipeline and check report.apps for the CrowdStrike entry."
    expected: "CrowdStrike Falcon AppStatus shows installed=True and service_state of 'Automatic', 'Manual', or 'Disabled' (not None)."
    why_human: "CSFalconService registry read and the two DisplayName variants ('CrowdStrike Windows Sensor' vs 'CrowdStrike Sensor Platform') require a live CrowdStrike-enrolled machine to confirm correct detection."
  - test: "On a machine without any target apps installed, run the pipeline and inspect the rendered HTML Quest Status footer."
    expected: "Footer shows 'MISSING SOFTWARE — 7 app(s)' and each equipment row shows the red missing badge."
    why_human: "End-to-end compliance gap display in the HTML character sheet requires visual confirmation in a browser."
  - test: "Confirm the M365 single-suite detection decision (D-05) is acceptable to the product owner — the rendered sheet shows one 'Microsoft 365' row rather than five individual rows for Word, Excel, Outlook, Teams, OneDrive."
    expected: "Product owner confirms the single-suite AppStatus entry for Microsoft 365 is sufficient for the IT audit workflow."
    why_human: "ROADMAP SC-3 specified individual per-app detection. CONTEXT.md D-05 scoped this down to a suite entry. This is a product decision that needs explicit stakeholder confirmation before the override above is formally accepted."
---

# Phase 4: App Detection and Compliance Engine Verification Report

**Phase Goal:** All 7 target applications are detected via registry enumeration across all four Uninstall key paths with filesystem and service fallbacks, and the compliance gap list is populated in the AuditReport
**Verified:** 2026-05-05
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | detect_apps(report) populates report.apps with exactly 7 AppStatus entries — one per target app — even when all apps are missing | VERIFIED | test_all_apps_always_present passes; test_detect_app_registry_miss confirms len==7; apps.py detect_apps always appends AppStatus even on per-app exception |
| 2 | NinjaOne is detected via keyword search for 'NinjaRMMAgent', 'NinjaRMM', or 'NinjaOne Agent' across all 4 Uninstall paths | VERIFIED | APP_SPECS[0] has display_name_keywords=["NinjaRMMAgent","NinjaRMM","NinjaOne Agent"]; test_detect_ninjaone_installed passes |
| 3 | CrowdStrike Falcon is detected via 'CrowdStrike Windows Sensor' or 'CrowdStrike Sensor Platform' keywords, and service_state is read from CSFalconService\Start DWORD | VERIFIED | APP_SPECS[1] has both keywords and service_key="CSFalconService"; _read_service_start maps DWORD 2/3/4 to Automatic/Manual/Disabled; test_crowdstrike_service_state_automatic passes |
| 4 | MERP is detected filesystem-first at Path('C:/PVX Plus Technologies/WindX Plugin-64 2022 Upd 1/WindX').exists(); version sought from registry keywords 'WindX' or 'PVX Plus Technologies' | VERIFIED | APP_SPECS[2] has filesystem_path and display_name_keywords; _detect_one_app checks Path first; test_merp_filesystem_primary and test_merp_filesystem_with_registry_version pass |
| 5 | Microsoft 365 is detected via 'Microsoft 365' or 'Microsoft Office' keyword across 4 Uninstall paths | VERIFIED | APP_SPECS[3] has display_name_keywords=["Microsoft 365","Microsoft Office"]; detection runs across all 4 UNINSTALL_PATHS |
| 6 | Zoom is detected via 'Zoom Workplace' or 'Zoom' keyword; 'Zoom Outlook Plugin' is avoided by preferring the more specific keyword | VERIFIED | APP_SPECS[4] has display_name_keywords=["Zoom Workplace","Zoom"] with "Zoom Workplace" first; _search_uninstall_keys returns on first keyword match |
| 7 | Google Chrome is detected via 'Google Chrome' keyword across 4 Uninstall paths | VERIFIED | APP_SPECS[5] has display_name_keywords=["Google Chrome"]; UNINSTALL_PATHS covers all 4 paths |
| 8 | Claude desktop is detected via MSIX AppModel repo path (keys starting with 'Claude_') with standard 4-path keyword fallback | VERIFIED | APP_SPECS[6] has msix_family_prefix="Claude_" and display_name_keywords=["Claude"]; _detect_msix enumerates HKCU AppModel repository; test_claude_msix_detection passes |
| 9 | Any per-app exception is caught, AppStatus.error is set, message appended to report.collection_errors — function never raises | VERIFIED | detect_apps wraps _detect_one_app per spec in try/except; on exception: collection_errors.append + AppStatus(installed=False, error=str(exc)) appended; test_collect_apps_never_raises passes |
| 10 | collect_all() calls collect_apps(report) after collect_hardware and collect_profiles | VERIFIED | collectors/__init__.py lines 17-21: lazy import + call in correct order; docstring updated |
| 11 | tests cover: registry hit, registry miss, filesystem detection (MERP), MSIX detection (Claude), service state (CrowdStrike), error handling | VERIFIED | 9 test functions confirmed; all 9 pass; grep -c "def test_" returns 9 |
| 12 | All 7 expected AppStatus names appear in report.apps after collect_apps under all-missing conditions | VERIFIED | test_all_apps_always_present explicitly asserts all 7 names; passes |
| 13 | test suite passes with pytest and no real registry calls | VERIFIED | python -m pytest tests/test_app_collector.py -v: 9 passed in 0.09s; 94/94 total tests pass |
| M365-SC3 | Each of the M365 apps (Word, Excel, Outlook, Teams, OneDrive) is detected individually | PASSED (override) | Override: CONTEXT.md D-05 scoped APP-04 to single-suite detection ("Microsoft 365") — no per-app entries. Decision was deliberate and documented before implementation. Accepted_by: pending-developer-review |

**Score:** 13/13 plan must-haves verified. 6/7 ROADMAP success criteria verified (SC-3 covered by override). Override requires developer confirmation.

---

### Deferred Items

None. All phase 4 items were addressed within this phase.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `collectors/windows/apps.py` | APP_SPECS table + detect_apps() + collect_apps() + _search_uninstall_keys() + _read_service_start() + _detect_msix() helpers | VERIFIED | All 5 functions present, 7-entry APP_SPECS confirmed, imports cleanly |
| `collectors/__init__.py` | collect_all() with collect_apps call | VERIFIED | Lazy import and call on lines 18-21; docstring updated |
| `tests/test_app_collector.py` | Unit tests with min 80 lines, 9 test functions | VERIFIED | 301 lines, 9 test functions, all pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| collectors/windows/apps.py | models.AppStatus | from models import AuditReport, AppStatus | WIRED | Line 14 of apps.py; import verified |
| detect_apps | report.apps | report.apps.append(AppStatus(...)) | WIRED | Lines 216-222 and 245-249 of apps.py; test_all_apps_always_present confirms it |
| _read_service_start | HKLM\SYSTEM\CurrentControlSet\Services\CSFalconService | winreg.OpenKey + QueryValueEx('Start') | WIRED | Lines 135-141; _START_MAP.get(int(val)) pattern confirmed; test_crowdstrike_service_state_automatic passes |
| _detect_msix | HKCU AppModel Repository Packages | winreg.EnumKey on _MSIX_REPO_PATH | WIRED | Lines 152-167; pkg_key_name.startswith(family_prefix) confirmed; test_claude_msix_detection passes |
| collectors/__init__.py | collectors/windows/apps.collect_apps | lazy import inside collect_all function body | WIRED | Line 18: from collectors.windows.apps import collect_apps |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| collectors/windows/apps.py | report.apps (list[AppStatus]) | winreg.OpenKey/EnumKey/QueryValueEx on live registry | Yes — real registry reads on Windows; mocked in tests | FLOWING |
| collectors/__init__.py | report (AuditReport) | collect_apps mutates report.apps in place | Yes — passes through to renderer | FLOWING |

Note: The compliance gap list described in the phase goal is computed by the renderer at render time (`missing = [app for app in report.apps if not app.installed]`) and passed to the Jinja2 template as `missing_count`. There is no separate `compliance_gaps` field on AuditReport — the compliance data lives in `report.apps` itself. This is consistent with the design intent in CONTEXT.md and the renderer implementation from Phase 3.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| APP_SPECS has 7 entries with correct names | python -c "import collectors.windows.apps as m; assert len(m.APP_SPECS) == 7; print([s['name'] for s in m.APP_SPECS])" | ['NinjaOne', 'CrowdStrike Falcon', 'MERP', 'Microsoft 365', 'Zoom', 'Google Chrome', 'Claude'] | PASS |
| collect_apps and detect_apps importable | python -c "from collectors.windows.apps import collect_apps, detect_apps" | exit 0 | PASS |
| CrowdStrike uses correct keywords (not "CrowdStrike Falcon") | grep "CrowdStrike Windows Sensor" collectors/windows/apps.py | match on line 60 | PASS |
| Claude has msix_family_prefix | grep "msix_family_prefix" collectors/windows/apps.py | match on line 83 | PASS |
| MERP has filesystem_path | grep "filesystem_path" collectors/windows/apps.py | match on line 66 | PASS |
| All 4 Uninstall paths covered (2 HKLM, 2 HKCU) | UNINSTALL_PATHS verification | HKLM 64-bit + HKLM WOW6432Node + HKCU 64-bit + HKCU WOW6432Node confirmed | PASS |
| test suite: 9 passing, no regressions | python -m pytest tests/test_app_collector.py -v | 9 passed in 0.09s | PASS |
| Full suite: no regressions | python -m pytest tests/ -q | 94 passed in 0.41s | PASS |
| collect_apps wired into collect_all | grep "collect_apps" collectors/__init__.py | import on line 18, call on line 21 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| APP-01 | 04-01-PLAN, 04-02-PLAN | Detect NinjaRMM / NinjaOne agent (registry, all 4 Uninstall paths) | SATISFIED | APP_SPECS["NinjaOne"] with 3 keywords; test_detect_ninjaone_installed passes |
| APP-02 | 04-01-PLAN, 04-02-PLAN | Detect CrowdStrike Falcon and capture service state | SATISFIED | APP_SPECS["CrowdStrike Falcon"] with 2 correct keywords + service_key; test_crowdstrike_service_state_automatic passes |
| APP-03 | 04-01-PLAN, 04-02-PLAN | Detect MERP (Master Electronics ERP / WindX) | SATISFIED | Filesystem-first detection at confirmed PVX Plus path; registry fallback for version; test_merp_filesystem_primary passes. MERP registry path remains an open IT validation item per CONTEXT.md blocker — filesystem path is the reliable primary. |
| APP-04 | 04-01-PLAN, 04-02-PLAN | Detect Microsoft 365 apps | SATISFIED (with override) | Single-suite entry per D-05; keyword matches "Microsoft 365"/"Microsoft Office". ROADMAP SC-3 individual-per-app wording overridden — see override entry. |
| APP-05 | 04-01-PLAN, 04-02-PLAN | Detect Zoom | SATISFIED | APP_SPECS["Zoom"] with Zoom Workplace first; avoids Zoom Outlook Plugin false positive |
| APP-06 | 04-01-PLAN, 04-02-PLAN | Detect Google Chrome | SATISFIED | APP_SPECS["Google Chrome"]; covered across all 4 Uninstall paths |
| APP-07 | 04-01-PLAN, 04-02-PLAN | Detect Claude desktop app | SATISFIED | MSIX AppModel repo enumeration via "Claude_" prefix; keyword fallback; test_claude_msix_detection passes |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | No TODO/FIXME/placeholder/stub patterns detected in apps.py, collectors/__init__.py, or tests/test_app_collector.py | — | — |

---

### Human Verification Required

#### 1. Live NinjaOne Detection on Provisioned Machine

**Test:** On a Windows machine with NinjaOne installed, run the full pipeline (or invoke collect_apps directly) and inspect report.apps.
**Expected:** NinjaOne AppStatus has installed=True with a version string (e.g., "13.0.7346"). The HTML character sheet equipment row shows a green installed badge.
**Why human:** Registry detection requires a real Windows machine with NinjaOne present. Mocked unit tests verify code logic but cannot confirm the live registry keyword match.

#### 2. Live CrowdStrike Detection and Service State

**Test:** On a CrowdStrike-enrolled Windows machine, run the pipeline and inspect report.apps for the CrowdStrike Falcon entry.
**Expected:** CrowdStrike Falcon shows installed=True and service_state is one of "Automatic", "Manual", or "Disabled" (not None). The HTML sheet shows the installed badge.
**Why human:** Both DisplayName variants ("CrowdStrike Windows Sensor" and "CrowdStrike Sensor Platform") require live registry access to confirm. The CSFalconService Start DWORD read needs a live service key.

#### 3. Compliance Gap Display in Rendered HTML

**Test:** On a machine without any of the 7 target apps, run the full pipeline and open the generated HTML in a browser.
**Expected:** The Quest Status footer reads "MISSING SOFTWARE — 7 app(s)" and all 7 equipment rows show red missing badges.
**Why human:** End-to-end compliance gap rendering requires visual browser inspection and a live audit run.

#### 4. M365 Single-Suite Decision Confirmation (Product Decision)

**Test:** Show a stakeholder the rendered HTML character sheet for a provisioned M365 machine. It shows one "Microsoft 365" row (installed/missing) rather than five rows for Word, Excel, Outlook, Teams, OneDrive.
**Expected:** Stakeholder confirms this level of granularity is acceptable for the IT audit workflow — the single-suite entry adequately serves the compliance check.
**Why human:** ROADMAP SC-3 specified individual M365 app detection. CONTEXT.md D-05 scoped this down to suite-level. The override in this VERIFICATION.md frontmatter is marked "pending-developer-review" — this is the human decision gate to formally accept or reject that scope reduction. If rejected, APP-04 needs to be expanded to 5 separate AppStatus entries.

---

### Gaps Summary

No automated gaps blocking goal achievement. All 7 apps are detected, all 4 Uninstall paths are enumerated, the compliance gap data flows through report.apps to the renderer, all unit tests pass (9/9), and the full test suite has no regressions (94/94).

The single override (SC-3 / APP-04 M365 individual detection) is a documented design decision from CONTEXT.md D-05 that was deliberate and pre-dates implementation. It requires human confirmation from a product stakeholder.

Four human verification items require a live Windows machine with the target applications installed.

---

_Verified: 2026-05-05_
_Verifier: Claude (gsd-verifier)_
