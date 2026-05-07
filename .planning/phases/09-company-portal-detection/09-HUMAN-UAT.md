---
status: partial
phase: 09-company-portal-detection
source: [09-VERIFICATION.md]
started: 2026-05-07T00:00:00Z
updated: 2026-05-07T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Visual Equipment Table Rendering

expected: Open the generated HTML character sheet and find the Company Portal row in the equipment table. Row shows 'Company Portal' in the Name column, installation status in the Installed column, and either 'Enrolled: {UPN}' or blank in the Service column. Row is visually consistent with other app rows.
result: [pending]

### 2. Live SYSTEM Account Enrollment Test (D-01 + D-08)

expected: Run the packaged exe via NinjaOne or equivalent SYSTEM account context on a device enrolled in Intune. Company Portal row shows "Not Found" (installed=False) because HKCU MSIX is inaccessible under SYSTEM, but Service column shows "Enrolled: {UPN}" from HKLM Enrollments (which IS accessible under SYSTEM).
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
