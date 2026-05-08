---
phase: "10-mac-collectors"
plan: "02"
subsystem: "collectors/mac"
tags: [mac, app-detection, plistlib, launchctl, tdd]
dependency_graph:
  requires:
    - "10-01-SUMMARY.md (collectors/mac package + hardware.py)"
    - "models.AppStatus (name, installed, version, service_state, detection_method, error)"
  provides:
    - "collectors/mac/apps.py (collect_apps, detect_apps, MAC_APP_SPECS)"
  affects:
    - "collectors/__init__.py (darwin branch will import collect_apps from here — Plan 03)"
tech_stack:
  added: []
  patterns:
    - "plistlib.load() with 'rb' binary mode for .app bundle Info.plist version parsing"
    - "Directory-based detection via is_dir() for NinjaOne (not .app bundle)"
    - "LaunchDaemon plist fallback for CrowdStrike (D-15)"
    - "launchctl list <label> for service state — best-effort, standard user (D-17)"
    - "Always-append AppStatus rule — per-app exceptions never block others (D-16)"
    - "Module-constant patching (patch.object APPLICATIONS_DIR) for test isolation"
key_files:
  created:
    - collectors/mac/apps.py
    - tests/test_mac_app_collector.py
  modified: []
decisions:
  - "NinjaOne uses 'app_dir' key (is_dir check) not 'app_bundle' — no .app bundle on Mac (Pitfall 5)"
  - "Zoom bundle is 'zoom.us.app' not 'Zoom.app' — domain-style naming convention (Pitfall 3)"
  - "plistlib imported at module level (not try/except) — pure stdlib, enables test patching"
  - "Tests patch APPLICATIONS_DIR/LAUNCH_DAEMONS_DIR constants not Path class — avoids pre-instantiated constant problem"
  - "NinjaOne launchdaemon_label 'com.ninjarmm.agent' — LOW confidence, TODO verify on live Mac"
metrics:
  duration: "~12 min"
  completed: "2026-05-08T18:15:30Z"
  tasks_completed: 1
  files_created: 2
  files_modified: 0
  tests_added: 12
  tests_total: 175
---

# Phase 10 Plan 02: Mac App Collector Summary

**One-liner:** macOS app detection via .app bundle + Info.plist version parsing + LaunchDaemon plist fallback + launchctl service state for 7 target apps.

## What Was Built

`collectors/mac/apps.py` — the macOS application detection collector. Implements PLAT-V2-03.

### MAC_APP_SPECS Table (7 entries)

| App | Detection Method | Service State |
|-----|-----------------|---------------|
| NinjaOne | `is_dir("/Applications/NinjaRMMAgent")` | `launchctl list com.ninjarmm.agent` (LOW conf) |
| CrowdStrike Falcon | `Falcon.app` bundle → `com.crowdstrike.falcond.plist` fallback | `launchctl list com.crowdstrike.falcond` |
| Microsoft 365 | `Microsoft Word.app` → fallbacks: Excel, PowerPoint, Outlook | None |
| Zoom | `zoom.us.app` (not Zoom.app) | None |
| Google Chrome | `Google Chrome.app` | None |
| Claude | `Claude.app` | None |
| Company Portal | `Company Portal.app` | None |

### Public Interface

- `MAC_APP_SPECS: list[dict]` — 7-entry detection table
- `collect_apps(report: AuditReport) -> None` — public entry point, never raises
- `detect_apps(report: AuditReport) -> None` — per-app always-append loop (D-16)
- `_detect_bundle(app_bundle: str) -> tuple[bool, str | None]` — plist version parsing
- `_query_launchd(label: str) -> str` — launchctl service state (best-effort)
- `_detect_one_app(spec: dict, report: AuditReport) -> None` — single-app detection

## TDD Gate Compliance

- RED commit: `ec6979e` — `test(10-02): add failing tests for mac app collector` (12 tests, all failing at import)
- GREEN commit: `511377a` — `feat(10-02): implement collectors/mac/apps.py` (12 tests pass)
- REFACTOR: Not needed — implementation was clean on first pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Redesigned test patching strategy**
- **Found during:** GREEN phase — 10/12 tests failing after initial implementation
- **Issue:** Tests were patching `Path` class, but `APPLICATIONS_DIR` and `LAUNCH_DAEMONS_DIR` are module-level `Path` instances created at import time. Patching the class did not affect already-created instances.
- **Fix:** Redesigned all path-dependent tests to patch `apps_mod.APPLICATIONS_DIR` and `apps_mod.LAUNCH_DAEMONS_DIR` directly using `patch.object`, plus per-test recursive mock factories with `__truediv__` on each stub.
- **Files modified:** `tests/test_mac_app_collector.py`
- **Commits:** `511377a` (test redesign included in GREEN commit)

## Known Stubs

None — no placeholder values, no hardcoded empty returns that reach the UI.

## Threat Flags

No new trust boundary surface beyond what is in the plan's threat model.
- `T-10-02-01` (subprocess timeout=5) — implemented as specified
- `T-10-02-03` (plistlib malformed plist) — caught in `(OSError, plistlib.InvalidFileException, KeyError, Exception)` block

## Success Criteria Verification

1. `collectors/mac/apps.py` exists and is importable — PASS
2. `MAC_APP_SPECS` has exactly 7 entries; names match D-14 — PASS
3. NinjaOne uses `"app_dir"` key (directory check, not `.app` bundle) — PASS
4. Zoom bundle is `"zoom.us.app"` (not `"Zoom.app"`) — PASS
5. CrowdStrike has `"launchdaemon_plist"` and `"launchdaemon_label"` — PASS
6. Microsoft 365 has `"fallback_bundles"` list with Excel, PowerPoint, Outlook — PASS
7. `plistlib.load()` is always called with `"rb"` mode open — PASS (Test 9 verifies)
8. `collect_apps()` and `detect_apps()` are both present — PASS
9. Per-app exception handler always appends both `collection_errors` AND `report.apps` — PASS (Test 8 verifies)

## Self-Check: PASSED

All files created, all commits exist, all assertions passed.
