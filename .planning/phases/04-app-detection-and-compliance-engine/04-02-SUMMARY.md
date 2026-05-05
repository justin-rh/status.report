---
phase: 04-app-detection-and-compliance-engine
plan: "02"
subsystem: collectors/__init__.py + tests/test_app_collector.py
tags:
  - app-detection
  - winreg
  - testing
  - integration
  - windows
dependency_graph:
  requires:
    - collectors/windows/apps.collect_apps (04-01)
    - models.AuditReport
    - parsers.name_parser.parse_hostname
  provides:
    - collectors/__init__.py with collect_apps wired into collect_all()
    - tests/test_app_collector.py (9 unit tests, full coverage)
  affects:
    - main.py (collect_all now runs app detection automatically)
    - renderer (report.apps populated by the full pipeline)
tech_stack:
  added: []
  patterns:
    - lazy import inside function body (same pattern as collect_hardware/collect_profiles)
    - patch.object(apps_mod.winreg, ...) for winreg mocking without real registry access
    - context-manager-aware OpenKey routing (distinct fake_ctx per path type for MSIX test)
key_files:
  created:
    - tests/test_app_collector.py
  modified:
    - collectors/__init__.py
decisions:
  - Claude MSIX test uses distinct context manager objects (msix_ctx vs other_ctx) returned by OpenKey side_effect so EnumKey dispatch can distinguish MSIX repo enumeration from Uninstall path enumeration — required because both use the same patched EnumKey function
  - Single fake_ctx (return_value) pattern sufficient for NinjaOne, CrowdStrike, MERP tests where all OpenKey calls can share one context; distinct routing only needed for Claude MSIX which requires different EnumKey behavior per path
metrics:
  duration: "~3 min"
  completed_date: "2026-05-05"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 04 Plan 02: Wire collect_apps and Unit Tests Summary

**One-liner:** Wired collect_apps lazy import into collect_all() and created 9-test suite using patch.object(apps_mod.winreg) covering registry hit, registry miss, filesystem detection, MSIX detection, service state, error handling, and D-15 completeness guarantee.

## What Was Built

### collectors/__init__.py — Modified

Added `collect_apps` lazy import and call to `collect_all()`:

```python
from collectors.windows.apps import collect_apps
collect_apps(report)
```

Both placed inside the function body (same lazy-import pattern as `collect_hardware`/`collect_profiles`) so the module remains importable on non-Windows platforms. Docstring updated to describe all three collectors.

### tests/test_app_collector.py — Created

9 unit tests covering the full detection surface:

| Test | Scenario | Decision Covered |
|------|----------|-----------------|
| `test_detect_ninjaone_installed` | Registry subkey with NinjaRMMAgent → installed=True, version | Standard registry hit |
| `test_detect_app_registry_miss` | All OpenKey OSError + Path=False → 7 apps all installed=False | Registry miss baseline |
| `test_merp_filesystem_primary` | Path.exists()=True + no registry → MERP detection_method='filesystem' | D-02 filesystem-first |
| `test_merp_filesystem_with_registry_version` | Filesystem hit + WindX registry version → MERP version="1.2.3" | D-03 version from registry |
| `test_claude_msix_detection` | MSIX AppModel repo key "Claude_1.1617.0.0_x64__..." → installed, version="1.1617.0.0" | RESEARCH.md Pitfall 3 guard |
| `test_crowdstrike_service_state_automatic` | CrowdStrike registry hit + Start DWORD=2 → service_state="Automatic" | D-08 service state |
| `test_crowdstrike_service_state_none_when_key_absent` | Service key raises OSError → service_state=None | D-08 graceful absence |
| `test_collect_apps_never_raises` | PermissionError on all registry → no exception, 7 entries present | D-16 never-raise |
| `test_all_apps_always_present` | All detection fails → all 7 names in report.apps | D-15 always-one-entry |

All tests use `patch.object(apps_mod.winreg, ...)` — no real Windows registry calls.

## Commits

| Hash | Message |
|------|---------|
| `5c7b9a5` | `feat(04-02): wire collect_apps into collectors/__init__.py collect_all()` |
| `e75587f` | `feat(04-02): add tests/test_app_collector.py with 9 unit tests for app detection` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Claude MSIX test mock routing**

- **Found during:** Task 2 (TDD GREEN phase)
- **Issue:** Initial implementation of `test_claude_msix_detection` used a shared `fake_ctx` for all `OpenKey` calls and a stateful `msix_served` flag on `EnumKey`. This caused the MSIX key to be "consumed" by other app's Uninstall path enumeration (which runs first, since Claude is the 7th app in APP_SPECS). The Claude entry came back as `installed=False`.
- **Fix:** Changed `OpenKey` side_effect to return a distinct `msix_ctx` when the MSIX repository path string ("AppModel") is detected, and `other_ctx` for all other paths. `EnumKey` then dispatches by comparing `key is msix_ctx` — returning the Claude package key name only for MSIX repo enumeration, raising `OSError("exhausted")` immediately for all Uninstall path enumerations.
- **Files modified:** `tests/test_app_collector.py`
- **Commit:** `e75587f` (fix included in the single task commit)

## Verification Results

All plan verification checks passed:

```
grep -n "collect_apps" collectors/__init__.py
  14:    then collect_apps (installed application detection).
  18:    from collectors.windows.apps import collect_apps
  21:    collect_apps(report)

python -m pytest tests/test_app_collector.py -v  → 9 passed
grep -c "def test_" tests/test_app_collector.py  → 9
python -m pytest tests/ -q                       → 94 passed, 0 failed (no regressions)
```

## Known Stubs

None. Both files are fully functional. The full audit pipeline (collect_hardware → collect_profiles → collect_apps) now runs end-to-end through `collect_all()`.

## Threat Flags

No new threat surface introduced. The lazy import change is structurally identical to the existing `collect_hardware` lazy import — same trust level, same module path under source control, no dynamic import from user input.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `collectors/__init__.py` contains lazy import + call | FOUND |
| `tests/test_app_collector.py` exists with 9 test functions | FOUND |
| Commit `5c7b9a5` exists | FOUND |
| Commit `e75587f` exists | FOUND |
| 94/94 tests pass, 0 regressions | VERIFIED |
