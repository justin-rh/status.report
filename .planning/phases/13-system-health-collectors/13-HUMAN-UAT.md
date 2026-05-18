---
status: partial
phase: 13-system-health-collectors
source: [13-VERIFICATION.md]
started: 2026-05-18T19:23:59Z
updated: 2026-05-18T19:23:59Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live SYSTEM/Administrator run — uptime and pending updates appear
expected: Run `scry.exe` on a Windows machine as SYSTEM or Administrator; stat block shows uptime formatted as "N days N hours" (not N/A) and a numeric pending update count (e.g. "3 pending")
result: [pending]

### 2. Yellow warning at >7 days uptime
expected: On a machine that has been running for more than 7 days (and ≤30 days), an amber UPTIME_WARN warning badge appears in the warnings section; the warning auto-expands in the HTML accordion
result: [pending]

### 3. Red warning at >30 days uptime
expected: On a machine running >30 days, a red `badge-critical` UPTIME_STALE warning badge appears with the detail text "Hibernation time is counted on Windows"
result: [pending]

### 4. Standard user N/A degradation
expected: Run as a standard (non-admin) user; WUA COM access is denied; the stat block shows "N/A" for Pending Updates and no crash or uncaught exception occurs
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
