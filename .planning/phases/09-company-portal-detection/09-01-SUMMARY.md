---
phase: 09-company-portal-detection
plan: "01"
subsystem: app-detection
tags: [company-portal, mdm, intune, msix, enrollment, winreg]
dependency_graph:
  requires: []
  provides: [company-portal-detection, mdm-enrollment-status]
  affects: [collectors/windows/apps.py, tests/test_app_collector.py]
tech_stack:
  added: []
  patterns: [mdm-enrollment-via-hklm-enumeration, spec-driven-app-detection]
key_files:
  created: []
  modified:
    - collectors/windows/apps.py
    - tests/test_app_collector.py
decisions:
  - "MDM hook runs unconditionally regardless of installed state (D-01) — enrollment visible even when HKCU absent under SYSTEM"
  - "Empty UPN strings treated as stale GUIDs and skipped (D-06)"
  - "First non-empty UPN wins across all GUID subkeys (D-05)"
  - "_detect_mdm_enrollment() wraps entire body in try/except Exception — never raises across layer boundary"
  - "No service_key field in Company Portal spec — MDM enrollment hook uses spec name check instead"
metrics:
  duration_seconds: 167
  completed_date: "2026-05-07"
  tasks_completed: 2
  files_modified: 2
---

# Phase 9 Plan 01: Company Portal Detection Summary

**One-liner:** Company Portal MSIX detection + Intune MDM enrollment via HKLM Enrollments enumeration, surfaced as `service_state="Enrolled: {UPN}"` in the equipment table.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add _detect_mdm_enrollment(), Company Portal APP_SPECS entry, MDM hook | 97a6684 | collectors/windows/apps.py |
| 2 | Add 6 Company Portal tests, update 3 count assertions to 9 | 0ecc6ac | tests/test_app_collector.py |

## What Was Built

### `collectors/windows/apps.py`

- **`_MDM_ENROLLMENTS_PATH`** constant: `r"SOFTWARE\Microsoft\Enrollments"`
- **`_detect_mdm_enrollment()`** helper: enumerates all GUID subkeys under `HKLM\SOFTWARE\Microsoft\Enrollments`, reads `UPN` value from each, returns `"Enrolled: {upn}"` for the first non-empty UPN found. Skips stale GUIDs (empty or missing UPN). Returns `None` on any exception — never raises.
- **Company Portal entry in `APP_SPECS`**: `name="Company Portal"`, `display_name_keywords=["Company Portal", "Microsoft Intune Company Portal"]`, `msix_family_prefix="Microsoft.CompanyPortal_"`
- **Step 4b MDM enrollment hook in `_detect_one_app()`**: runs unconditionally when `spec.get("name") == "Company Portal"`, assigns `_detect_mdm_enrollment()` result to `service_state` regardless of installed state.
- Module docstring updated: 8 → 9 target applications.

### `tests/test_app_collector.py`

Six new tests covering all CONTEXT.md decisions:

| Test | Decision Covered |
|------|-----------------|
| `test_company_portal_msix_detected` | MSIX key present → installed=True, version parsed |
| `test_company_portal_not_installed_but_enrolled` | D-01: HKCU absent + HKLM UPN → service_state set |
| `test_company_portal_stale_guid_skipped` | D-06: empty UPN skipped, second GUID wins |
| `test_company_portal_not_enrolled_returns_none` | D-02/D-04: UPN missing → service_state=None |
| `test_company_portal_enrollment_exception_returns_none` | PermissionError swallowed → None |
| `test_company_portal_always_present` | D-15: CP always produces AppStatus (9 apps total) |

Three existing count assertions updated: `test_detect_app_registry_miss`, `test_collect_apps_never_raises` (8→9), `test_all_apps_always_present` (added "Company Portal" to expected_names list).

## Verification

```
153 passed in 2.11s
```

Full suite passes (153 tests — suite had grown beyond the 135 baseline counted at Phase 8 close; all new tests pass, zero regressions).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — Company Portal detection is fully wired. `service_state` flows from `_detect_mdm_enrollment()` through `_detect_one_app()` to `AppStatus.service_state`, which the existing Jinja2 template already renders in the Service column.

## Threat Surface Scan

No new threat surface beyond what the plan's threat model covers. `_detect_mdm_enrollment()` is read-only HKLM access; T-09-03 (DoS via PermissionError / EnumKey exhaustion) is mitigated by the outer `try/except Exception` and the `OSError` break on index exhaustion.

## Self-Check: PASSED

- `collectors/windows/apps.py` — modified and committed at 97a6684
- `tests/test_app_collector.py` — modified and committed at 0ecc6ac
- Both commits verified in git log
- `_detect_mdm_enrollment` present in module: confirmed
- `APP_SPECS` count == 9: confirmed
- `Microsoft.CompanyPortal_` in APP_SPECS: confirmed
- 153 tests pass, 0 failures: confirmed
