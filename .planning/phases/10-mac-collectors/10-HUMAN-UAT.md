---
status: partial
phase: 10-mac-collectors
source: [10-VERIFICATION.md]
started: 2026-05-08T18:35:27Z
updated: 2026-05-08T18:35:27Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-end macOS run
expected: Run `python3 main.py` on a physical macOS device — full pipeline completes: hardware/profile/app collection → HTML render → `logs/status_<hostname>_<date>.html` written → browser auto-opens the file. No unhandled exceptions. HTML contains CPU model, OS version, RAM, disk, local profiles, and all 7 app detection rows.
result: [pending]

### 2. NinjaOne launchctl label validation
expected: On a NinjaOne-enrolled Mac, NinjaOne shows `service_state = "Running"` in the HTML character sheet (not "Stopped"). Confirms `launchdaemon_label: "com.ninjarmm.agent"` is the correct label for the live fleet.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
