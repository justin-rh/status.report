---
phase: 04-app-detection-and-compliance-engine
plan: "01"
subsystem: collectors/windows/apps
tags:
  - app-detection
  - winreg
  - compliance
  - windows
dependency_graph:
  requires:
    - models.AppStatus
    - models.AuditReport
  provides:
    - collectors/windows/apps.APP_SPECS
    - collectors/windows/apps.collect_apps
    - collectors/windows/apps.detect_apps
  affects:
    - collectors/__init__.py (collect_all must add collect_apps call)
    - renderer (report.apps now populated for Quest Status display)
tech_stack:
  added: []
  patterns:
    - winreg EnumKey exhaustion sentinel (mirrored from hardware.py)
    - per-app exception catch with D-15 always-one-entry guarantee
    - MSIX AppModel repository enumeration for Claude detection
    - filesystem-first detection with registry fallback for MERP
key_files:
  created:
    - collectors/windows/apps.py
  modified: []
decisions:
  - CrowdStrike keywords set to 'CrowdStrike Windows Sensor' / 'CrowdStrike Sensor Platform' (not 'CrowdStrike Falcon') per RESEARCH.md Pitfall 1 — live registry verified
  - Claude MSIX detection via 'Claude_' family prefix in AppModel repository as primary; standard keyword sweep as fallback per RESEARCH.md Pitfall 3
  - MERP filesystem-first at hardcoded PVX Plus path per D-02; registry search for version only on filesystem hit per D-03
  - detection_method stays 'registry' for MSIX detection (MSIX repo is still a registry read, not filesystem) per D-17
  - Zoom uses 'Zoom Workplace' first in keywords to avoid false-positive match on 'Zoom Outlook Plugin' per RESEARCH.md Pitfall 2
metrics:
  duration: "~10 min"
  completed_date: "2026-05-05"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 04 Plan 01: App Detection Collector Summary

**One-liner:** Config-driven APP_SPECS table with 7 entries driving `detect_apps()` via winreg Uninstall enumeration, MSIX AppModel detection (Claude), filesystem fallback (MERP), and service state read (CrowdStrike).

## What Was Built

`collectors/windows/apps.py` — the core app detection module for Phase 4. Implements the full detection pipeline for 7 target applications: NinjaOne, CrowdStrike Falcon, MERP, Microsoft 365, Zoom, Google Chrome, and Claude.

### Functions

| Function | Purpose |
|----------|---------|
| `collect_apps(report)` | Public entry point; calls `detect_apps`. Consumed by `collectors/__init__.py`. |
| `detect_apps(report)` | Iterates APP_SPECS; calls `_detect_one_app` per spec inside per-app try/except. |
| `_detect_one_app(spec, report)` | Runs detection precedence: MSIX → filesystem → registry → service state. Appends one AppStatus. |
| `_search_uninstall_keys(keywords)` | Enumerates all 4 Uninstall paths; returns (bool, version) on first keyword match. |
| `_read_service_start(service_name)` | Reads HKLM Services `Start` DWORD; maps 2/3/4 to Automatic/Manual/Disabled. |
| `_detect_msix(family_prefix)` | Enumerates HKCU AppModel repository; returns (bool, version) for matching package. |

### Constants

- `UNINSTALL_PATHS` — 4 (hive, path) tuples covering HKLM 64-bit, HKLM Wow6432Node, HKCU 64-bit, HKCU Wow6432Node
- `_START_MAP` — DWORD→string service start type mapping
- `_MSIX_REPO_PATH` — HKCU AppModel repository path for MSIX package enumeration
- `APP_SPECS` — 7-entry list[dict] config table

## Commits

| Hash | Message |
|------|---------|
| `326038e` | `feat(04-01): add collectors/windows/apps.py with APP_SPECS and detect_apps` |

## Deviations from Plan

None — plan executed exactly as written. All keyword choices, detection method precedence, and error handling patterns implemented per the plan's `<action>` spec, RESEARCH.md Pitfalls 1-3, and CONTEXT.md decisions D-01 through D-17.

## Verification Results

All plan verification checks passed:

```
python -c "import collectors.windows.apps as m; assert len(m.APP_SPECS) == 7"  → exit 0
python -c "from collectors.windows.apps import collect_apps, detect_apps"       → exit 0
grep "CrowdStrike Windows Sensor" collectors/windows/apps.py                    → match found (line 60)
grep "msix_family_prefix" collectors/windows/apps.py                           → match found (line 83)
grep "filesystem_path" collectors/windows/apps.py                               → match found (line 66)
5 function defs found: collect_apps, detect_apps, _search_uninstall_keys,
                       _read_service_start, _detect_msix
```

Functional tests (mocked winreg):
- All 7 apps present in report.apps even when registry raises OSError and filesystem returns False
- CrowdStrike keywords verified correct (no Pitfall 1)
- Claude msix_family_prefix="Claude_" verified
- MERP filesystem_path correct
- collect_apps never raises under PermissionError — all 7 entries still appear

## Known Stubs

None. The module is fully functional. `report.apps` will be an empty list until `collect_apps` is wired into `collectors/__init__.py` (this is Plan 02's responsibility — adding the `collect_apps(report)` call to `collect_all()`).

## Threat Flags

No new threat surface introduced beyond what the plan's threat model covers. All registry reads are read-only, values are treated as strings (never executed), paths are hardcoded constants (no user input), and exceptions are caught with only the message string appended to `collection_errors`.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `collectors/windows/apps.py` exists | FOUND |
| Commit `326038e` exists | FOUND |
