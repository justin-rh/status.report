---
phase: "10-mac-collectors"
plan: "04"
subsystem: "tests"
tags: [mac, tests, hardware, apps, profiles, tdd, pytest, parametrize]
dependency_graph:
  requires:
    - "10-01-SUMMARY.md (collectors/mac/hardware.py — collect_hardware, collect_profiles)"
    - "10-02-SUMMARY.md (collectors/mac/apps.py — collect_apps, MAC_APP_SPECS)"
  provides:
    - "tests/test_mac_hardware_collector.py (13 tests — collect_hardware, OS/CPU/RAM/disk/user, never-raise)"
    - "tests/test_mac_app_collector.py (16 tests — detect_apps, 7-app coverage, plist, launchctl)"
    - "tests/test_mac_profile_collector.py (5 tests — collect_profiles, UID threshold, never-raise)"
  affects:
    - "CI: all 3 Mac test files run on Windows without ImportError"
tech_stack:
  added: []
  patterns:
    - "patch.object(hw_mod, '_pwd_module') + patch.object(hw_mod, '_PWD_AVAILABLE', True) — module-level pwd patching"
    - "patch.object(hw_mod, 'subprocess') — module-level subprocess patching (not global)"
    - "patch.object(hw_mod, 'psutil') — module-level psutil patching"
    - "patch.object(hw_mod, 'platform') — module-level platform patching"
    - "patch.object(apps_mod, 'APPLICATIONS_DIR') + _make_path_stub() factory — constant patching for Path instances"
    - "patch('collectors.mac.apps.plistlib') — module-level plistlib patching"
    - "@pytest.mark.parametrize for Intel + Apple Silicon CPU detection fixtures"
key_files:
  created:
    - tests/test_mac_profile_collector.py
  modified:
    - tests/test_mac_hardware_collector.py
    - tests/test_mac_app_collector.py
decisions:
  - "Hardware profile tests kept in test_mac_hardware_collector.py AND duplicated in test_mac_profile_collector.py — hardware file had them from TDD RED phase; profile file added per plan spec"
  - "test_collect_hardware_os_failure_degrades: patches subprocess.run with OSError (not TimeoutExpired) — simulates sw_vers not found"
  - "test_zoom_bundle_name_is_zoom_us_app: verifies MAC_APP_SPECS constant directly + confirms Zoom.app does not trigger detection"
  - "test_crowdstrike_service_state_stopped: launchctl returncode=1 → service_state='Stopped' verified explicitly"
metrics:
  duration: "~8 min"
  completed: "2026-05-08T18:26:26Z"
  tasks_completed: 2
  files_created: 1
  files_modified: 2
  tests_added: 18
  tests_total: 195
---

# Phase 10 Plan 04: Mac Collector Tests Summary

**One-liner:** Three Mac test files (hardware=13, apps=16, profiles=5) covering Intel/Apple Silicon parametrize, plist/launchctl mocking, UID threshold filtering, and never-raise guarantees — all 195 tests pass on Windows CI.

## What Was Built

Three test files providing full coverage of the collectors added in Plans 01 and 02, all running on Windows CI via module-level mocking.

### tests/test_mac_hardware_collector.py (13 tests)

| Test | What It Covers |
|------|---------------|
| test_module_imports_without_real_pwd | Windows CI import guard |
| test_collect_hardware_populates_os_version_and_build | sw_vers mock → macOS 14.4.1 + 23E224 |
| test_cpu_model_collection[x86_64...] | Intel sysctl → CPU string |
| test_cpu_model_collection[arm64...] | Apple Silicon system_profiler → chip_type |
| test_collect_hardware_all_subprocess_fails | All subprocess raises → cpu_model=None + errors |
| test_collect_hardware_never_raises | All subsystems fail → no exception propagates |
| test_collect_profiles_excludes_system_accounts | UID threshold (alice/bob in, root/_daemon out) |
| test_collect_profiles_never_raises | getpwall raises → no exception, errors logged |
| test_collect_profiles_degrades_when_pwd_unavailable | _PWD_AVAILABLE=False → empty list + error |
| test_collect_hardware_ram_is_float | psutil mock → ram_gb is float > 0 |
| test_collect_hardware_disk_fields_are_floats | psutil mock → disk_total_gb, disk_free_gb are floats |
| test_collect_current_user_from_user_env | USER env var → current_user == "testuser" |
| test_collect_hardware_os_failure_degrades | sw_vers OSError → os_version=None + error logged |

### tests/test_mac_app_collector.py (16 tests)

| Test | What It Covers |
|------|---------------|
| test_all_apps_always_present | All paths False → exactly 7 AppStatus entries |
| test_crowdstrike_falls_back_to_launchdaemon_plist | Falcon.app absent, plist present → installed=True |
| test_m365_fallback_bundle_detected | Word absent, Excel present → M365 installed=True |
| test_ninjaone_detected_via_directory | NinjaRMMAgent is_dir()=True → NinjaOne installed=True |
| test_zoom_detected_with_version | zoom.us.app present + plist → installed, version="5.17.0" |
| test_crowdstrike_service_state_populated_when_installed | Falcon.app present → service_state="Running"/"Stopped" |
| test_standard_bundle_apps_detected[x3] | Chrome, Claude, CompanyPortal bundle + version |
| test_per_app_exception_still_appends_app_status | _detect_one_app raises → 7 AppStatus(installed=False) |
| test_plistlib_load_called_with_binary_mode | .open("rb") verified |
| test_crowdstrike_detected_via_app_bundle | Falcon.app → installed=True, version from plist |
| test_crowdstrike_service_state_stopped | launchctl returncode=1 → service_state="Stopped" |
| test_m365_primary_sentinel | Microsoft Word.app → M365 installed=True |
| test_zoom_bundle_name_is_zoom_us_app | MAC_APP_SPECS has "zoom.us.app"; Zoom.app does NOT trigger |
| test_service_state_only_for_ninja_and_crowdstrike | Zoom/Chrome/Claude/Portal get service_state=None |

### tests/test_mac_profile_collector.py (5 tests)

| Test | What It Covers |
|------|---------------|
| test_collect_profiles_returns_human_accounts | UID 501/502 included; UID 0/1 excluded |
| test_collect_profiles_excludes_system_accounts | Explicit UID threshold assertion |
| test_collect_profiles_never_raises | getpwall RuntimeError → no exception, errors logged |
| test_collect_profiles_degrades_when_pwd_unavailable | _PWD_AVAILABLE=False → empty + error |
| test_collect_profiles_empty_when_no_human_accounts | All UID < 501 → local_profiles == [] |

## Test Count Summary

| File | Tests Before | Tests Added | Tests After |
|------|-------------|-------------|-------------|
| test_mac_hardware_collector.py | 9 | 4 | 13 |
| test_mac_app_collector.py | 10 (12 with parametrize) | 4 | 16 |
| test_mac_profile_collector.py | 0 (new) | 5 | 5 |
| **Total project** | **182** | **+13** | **195** |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written. The existing test files (from earlier TDD RED/GREEN cycles in plans 01-02) already contained some of the required tests; this plan expanded them to meet all coverage requirements.

## Known Stubs

None — test files contain no placeholder values or hardcoded returns that affect test validity.

## Threat Flags

No new trust boundary surface introduced. All mocks are module-level; no global stdlib patches that could affect other test files (T-10-04-01 mitigated as specified).

## Success Criteria Verification

1. `tests/test_mac_hardware_collector.py` exists with `@pytest.mark.parametrize` for Intel + Apple Silicon CPU — PASS
2. `tests/test_mac_app_collector.py` exists with `test_all_apps_always_present` asserting exactly 7 entries — PASS
3. `tests/test_mac_profile_collector.py` exists with UID threshold and never-raise tests — PASS
4. All three files import without error on Windows — PASS (`python -c "import tests.test_mac_*"` succeeds)
5. `patch.object(hw_mod, "_pwd_module")` pattern used (not `patch("pwd")`) — PASS
6. `patch("collectors.mac.apps.plistlib")` pattern used (not `patch("plistlib")`) — PASS
7. `pytest tests/ -q` shows 195 total tests (182 + 13 new), 0 failures — PASS

## Self-Check: PASSED

- `tests/test_mac_hardware_collector.py` — EXISTS (confirmed by pytest run, 13 tests pass)
- `tests/test_mac_app_collector.py` — EXISTS (confirmed by pytest run, 16 tests pass)
- `tests/test_mac_profile_collector.py` — EXISTS (confirmed by pytest run, 5 tests pass)
- Commit `7d8d4b4` — EXISTS (confirmed by `git rev-parse --short HEAD`)
- 195 total tests pass, 0 failures
