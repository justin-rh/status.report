---
status: partial
phase: 04-app-detection-and-compliance-engine
source: [04-VERIFICATION.md]
started: 2026-05-05T00:00:00Z
updated: 2026-05-05T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live NinjaOne Detection on Provisioned Machine
expected: NinjaOne AppStatus has installed=True with a version string (e.g., "13.0.7346"). HTML character sheet equipment row shows green installed badge.
result: [pending]

### 2. Live CrowdStrike Detection and Service State
expected: CrowdStrike Falcon AppStatus shows installed=True and service_state is one of "Automatic", "Manual", or "Disabled" (not None). HTML sheet shows the installed badge.
result: [pending]

### 3. Compliance Gap Display in Rendered HTML
expected: On a machine without any of the 7 target apps, Quest Status footer reads "MISSING SOFTWARE — 7 app(s)" and all 7 equipment rows show red missing badges.
result: [pending]

### 4. M365 Single-Suite Decision Confirmation (Product Decision)
expected: Stakeholder confirms single "Microsoft 365" row (vs five individual M365 app rows) is acceptable for the IT audit workflow. If rejected, APP-04 must be expanded to 5 separate AppStatus entries.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
