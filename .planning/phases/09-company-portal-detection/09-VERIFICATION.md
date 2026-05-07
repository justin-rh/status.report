---
phase: 09-company-portal-detection
verified: 2026-05-07T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open the generated HTML character sheet and find the Company Portal row in the equipment table"
    expected: "Row shows 'Company Portal' in the Name column, installation status in the Installed column, and either 'Enrolled: {UPN}' or blank in the Service column"
    why_human: "Visual rendering of service_state in the equipment table cannot be verified without running the tool on a live Windows machine or inspecting a real HTML output against actual registry data"
  - test: "Run the tool on a machine enrolled in Intune via NinjaOne (SYSTEM account)"
    expected: "Company Portal row shows installed=False (HKCU absent) but Service column shows 'Enrolled: {UPN}' from HKLM Enrollments"
    why_human: "D-01 behavior (installed=False + enrollment visible) requires a real enrolled device running under SYSTEM account; no substitute for live verification"
---

# Phase 9: Company Portal Detection Verification Report

**Phase Goal:** IT staff can see whether Company Portal is installed and whether the device is enrolled in Intune, as distinct signals in the character sheet
**Verified:** 2026-05-07
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Company Portal row appears in report.apps on a machine where the UWP is installed | VERIFIED | `_detect_msix("Microsoft.CompanyPortal_")` called in `_detect_one_app()` step 1; `test_company_portal_msix_detected` passes with `installed=True`, `version="11.5.1204.0"` |
| 2 | Service column shows 'Enrolled: {UPN}' when device is enrolled in Intune (HKLM Enrollments contains a non-empty UPN) | VERIFIED | `_detect_mdm_enrollment()` returns `f"Enrolled: {upn}"` on first non-empty UPN; `test_company_portal_not_installed_but_enrolled` passes asserting `service_state == "Enrolled: justin.rhoda@masterelectronics.com"` |
| 3 | Service column is None when no GUID subkey has a non-empty UPN (not enrolled) | VERIFIED | `_detect_mdm_enrollment()` exhausts all GUIDs and returns `None`; `test_company_portal_not_enrolled_returns_none` passes asserting `service_state is None` |
| 4 | GUID subkeys without a UPN value are skipped — they do not produce an enrolled result | VERIFIED | `if upn:` guard at line 218 skips empty strings; `except (FileNotFoundError, OSError): continue` skips missing UPN values; `test_company_portal_stale_guid_skipped` passes showing second GUID wins when first has empty UPN |
| 5 | When running under SYSTEM account (HKCU absent), Company Portal shows Not Found but enrollment check still runs and returns enrollment status from HKLM | VERIFIED | MDM hook at line 445 is unconditional (`if spec.get("name") == "Company Portal":`), runs regardless of `installed` state; `test_company_portal_not_installed_but_enrolled` simulates SYSTEM via `OSError("HKCU absent — SYSTEM account")` and asserts `installed=False, service_state="Enrolled: ..."` |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `collectors/windows/apps.py` | `_detect_mdm_enrollment()` helper + Company Portal APP_SPECS entry + MDM hook in `_detect_one_app()` | VERIFIED | `_detect_mdm_enrollment` present at line 197; `_MDM_ENROLLMENTS_PATH = r"SOFTWARE\Microsoft\Enrollments"` at line 194; Company Portal entry at lines 123–127; MDM hook at lines 443–446 |
| `tests/test_app_collector.py` | 6 new tests covering CP MSIX detection, enrollment found, enrollment absent, stale GUID, SYSTEM+enrolled, exception safety | VERIFIED | 6 `test_company_portal_*` tests present at lines 619–818, all PASS |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `APP_SPECS` Company Portal entry | `_detect_one_app()` | `msix_family_prefix="Microsoft.CompanyPortal_"` | WIRED | Pattern `Microsoft\.CompanyPortal_` found at line 125; `_detect_msix()` called with this prefix in step 1 of `_detect_one_app()` |
| `_detect_one_app()` | `_detect_mdm_enrollment()` | MDM hook after MSIX detection block | WIRED | `spec.get("name") == "Company Portal"` check at line 445; `service_state = _detect_mdm_enrollment()` at line 446 |
| `_detect_mdm_enrollment()` | `HKLM\SOFTWARE\Microsoft\Enrollments\{GUID}\UPN` | `winreg.OpenKey / EnumKey / QueryValueEx` | WIRED | `winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _MDM_ENROLLMENTS_PATH)` at line 207; `winreg.EnumKey(root, i)` at line 211; `winreg.QueryValueEx(subkey, "UPN")` at line 217 |
| `AppStatus.service_state` | `character_sheet.html` Service column | Jinja2 `{{ app.service_state or '' }}` | WIRED | Template line 426: `<td>{{ app.service_state or '' }}</td>` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `collectors/windows/apps.py` `_detect_one_app()` for Company Portal | `service_state` | `_detect_mdm_enrollment()` → `winreg.QueryValueEx(subkey, "UPN")` | Yes — reads from HKLM registry | FLOWING |
| `renderer/templates/character_sheet.html` | `app.service_state` | `AppStatus.service_state` populated by `_detect_one_app()` | Yes — passes through from registry read | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_detect_mdm_enrollment` symbol exists in module | `python -c "import collectors.windows.apps as a; print(hasattr(a, '_detect_mdm_enrollment'))"` | `True` | PASS |
| APP_SPECS has 9 entries including Company Portal | `python -c "import collectors.windows.apps as a; cp = next(s for s in a.APP_SPECS if s['name'] == 'Company Portal'); print(len(a.APP_SPECS), cp['msix_family_prefix'])"` | `9 Microsoft.CompanyPortal_` | PASS |
| Full test suite (153 tests) | `python -m pytest -x -q` | `153 passed in 2.06s` | PASS |
| All 6 company portal tests pass | `python -m pytest tests/test_app_collector.py -v` | All 6 `test_company_portal_*` PASSED | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| APP-V2-01 | 09-01-PLAN.md | User can see whether Company Portal (UWP) is installed on a Windows device, with MDM enrollment status shown in the Service column of that row | SATISFIED | Company Portal entry in APP_SPECS with `msix_family_prefix="Microsoft.CompanyPortal_"`; `_detect_mdm_enrollment()` populates `service_state`; service_state rendered in template Service column (`{{ app.service_state or '' }}` at line 426 of character_sheet.html) |

**Roadmap Success Criteria Coverage (Phase 9):**

| SC | Criterion | Status | Evidence |
|----|-----------|--------|----------|
| SC1 | Company Portal appears in the equipment table on a machine where the UWP app is installed | VERIFIED (needs human for visual) | `_detect_msix("Microsoft.CompanyPortal_")` wired; `test_company_portal_msix_detected` passes |
| SC2 | MDM enrollment status (Enrolled / Not Enrolled) appears in the Service column for the Company Portal row, derived from HKLM Enrollments UPN value | VERIFIED (needs human for visual) | `_detect_mdm_enrollment()` returns `"Enrolled: {upn}"` or `None`; service_state rendered in template |
| SC3 | GUID keys without a UPN value are treated as stale artifacts and do not report as enrolled (no false positives) | VERIFIED | `if upn:` guard + `continue` on FileNotFoundError; `test_company_portal_stale_guid_skipped` and `test_company_portal_not_enrolled_returns_none` both pass |
| SC4 | "Not Found" is shown cleanly in the equipment table on a machine where Company Portal is not installed | VERIFIED (needs human for visual) | `installed=False` when MSIX absent; template handles `installed=False` rows; `test_company_portal_not_installed_but_enrolled` confirms `installed=False` case |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_app_collector.py` | 280 | Section comment says "all 7 apps" but there are now 9 apps in the spec | Info | No functional impact — comment is stale, test body is correct and passes |

No blockers or warnings found. No TODO/FIXME/placeholder markers. No empty implementations or stub returns. No hardcoded empty data flowing to rendering.

### Human Verification Required

#### 1. Visual Equipment Table Rendering

**Test:** Generate a real HTML character sheet output (or use `preview_output/status_report.html` if a recent run exists) and open it in a browser. Locate the Company Portal row in the equipment table.
**Expected:** One row labeled "Company Portal" exists. The Installed cell reflects actual install state. The Service cell either shows "Enrolled: {UPN}" or is blank (not enrolled). The row is visually consistent with other app rows.
**Why human:** Jinja2 template rendering of `app.service_state` and the Service column layout cannot be verified programmatically without running the tool against live registry data. The template wiring is confirmed (line 426), but visual correctness requires a human to confirm the cell renders as intended.

#### 2. Live SYSTEM Account Enrollment Test (D-01 + D-08)

**Test:** Run the packaged exe via NinjaOne or equivalent SYSTEM account context on a device enrolled in Intune. Check the resulting HTML character sheet.
**Expected:** Company Portal row shows "Not Found" (installed=False, version blank) because HKCU MSIX is inaccessible under SYSTEM, but the Service column shows "Enrolled: {UPN}" because HKLM Enrollments is accessible under SYSTEM.
**Why human:** Requires a real enrolled device, real NinjaOne/SYSTEM execution context, and real HKLM Enrollments registry data. The logic for this scenario is fully tested in `test_company_portal_not_installed_but_enrolled` (which simulates SYSTEM by raising OSError on AppModel) but live validation closes the gap between simulation and production.

### Gaps Summary

No gaps. All automated checks pass. All 5 must-have truths are verified against the actual code. The 2 human verification items are standard live-environment tests for visual rendering and SYSTEM-account behavior — both are expected at this stage and do not indicate implementation defects.

---

_Verified: 2026-05-07_
_Verifier: Claude (gsd-verifier)_
