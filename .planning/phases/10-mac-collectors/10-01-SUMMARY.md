---
phase: "10-mac-collectors"
plan: "01"
subsystem: "collectors/mac"
tags: [mac, hardware, collectors, psutil, subprocess, pwd, tdd]
dependency_graph:
  requires:
    - models.AuditReport (all fields populated by this plan)
    - psutil (already in requirements.txt)
  provides:
    - collectors.mac package (importable)
    - collectors.mac.hardware.collect_hardware()
    - collectors.mac.hardware.collect_profiles()
  affects:
    - collectors/__init__.py (darwin branch — added in plan 03)
tech_stack:
  added: []
  patterns:
    - pwd import guard (mirrors _wmi_module pattern from collectors/windows/hardware.py)
    - Two-branch CPU detection via platform.machine() — x86_64 (sysctl) vs arm64 (system_profiler)
    - in-place mutation — collect_hardware/collect_profiles mutate AuditReport, never raise
    - collection_errors append convention for all subprocess/psutil failures
key_files:
  created:
    - collectors/mac/__init__.py
    - collectors/mac/hardware.py
    - tests/test_mac_hardware_collector.py
    - tests/test_mac_init.py
  modified: []
decisions:
  - pwd import guarded with try/except ImportError — enables Windows CI to import the module without error
  - platform.machine() == "x86_64" branches to sysctl; arm64 goes directly to system_profiler (avoids Pitfall 1)
  - os.environ.get("USER") is primary current_user source (Mac uses USER, not USERNAME)
  - psutil.disk_usage("/") — root partition on macOS (not "C:\\")
  - _enumerate_profiles raises RuntimeError when _PWD_AVAILABLE=False — collect_profiles catches it
metrics:
  duration: "~3 minutes"
  completed: "2026-05-08"
  tasks_completed: 2
  files_created: 4
  files_modified: 0
  tests_added: 10
  tests_total: 163
requirements_satisfied:
  - PLAT-V2-01
  - PLAT-V2-02
---

# Phase 10 Plan 01: Mac Hardware Collectors Summary

**One-liner:** macOS hardware collector using subprocess (sw_vers, sysctl, system_profiler), psutil, and pwd.getpwall() with UID>=501 filtering for user profiles.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create collectors/mac/__init__.py | 0880a36 | collectors/mac/__init__.py, tests/test_mac_init.py |
| 2 | Implement collectors/mac/hardware.py | ac1b6a6 | collectors/mac/hardware.py, tests/test_mac_hardware_collector.py |

## What Was Built

**collectors/mac/__init__.py** — Single-line comment package marker, mirrors `collectors/windows/__init__.py` exactly. Enables `import collectors.mac` as a proper package (not just a namespace package).

**collectors/mac/hardware.py** — macOS hardware and profile collector with:

- `collect_hardware(report)` — calls four private helpers:
  - `_collect_os()` — `sw_vers -productVersion` → `"macOS X.Y.Z"`, `sw_vers -buildVersion` → `os_build`
  - `_collect_cpu_model()` — two-branch: x86_64 uses `sysctl -n machdep.cpu.brand_string`; arm64 uses `system_profiler SPHardwareDataType -json` with `chip_type`/`cpu_type` fallback chain
  - `_collect_memory_and_disk()` — `psutil.virtual_memory().total` and `psutil.disk_usage("/")`
  - `_collect_current_user()` — `os.environ.get("USER")` primary, `USERNAME` fallback
- `collect_profiles(report)` — wraps `_enumerate_profiles()`, catches all exceptions
- `_enumerate_profiles()` — `pwd.getpwall()` filtered to `pw_uid >= 501` (macOS human accounts)
- `pwd` module guarded with `try/except ImportError` (`_pwd_module`/`_PWD_AVAILABLE` pattern)
- All subprocess calls have `timeout=5` or `timeout=10` parameters
- All failures appended to `report.collection_errors`, never raised

## Test Coverage

10 new tests in 2 new test files:
- `tests/test_mac_init.py` — package importability (1 test)
- `tests/test_mac_hardware_collector.py` — 9 tests covering:
  - OS version/build population
  - Intel CPU (sysctl) parametrized
  - Apple Silicon CPU (system_profiler) parametrized
  - All subprocess calls failing (cpu_model=None, errors logged)
  - collect_hardware never raises
  - Profile UID filtering (alice/bob UID 501/502 included; root/daemon UID 0/1 excluded)
  - collect_profiles never raises
  - collect_profiles degrades when _PWD_AVAILABLE=False

Total: 163 tests passing (was 153 before this plan).

## Deviations from Plan

None — plan executed exactly as written. The TDD RED phase noted that Python 3.12 namespace packages allow `import collectors.mac` without `__init__.py`, but the file was created as required for an explicit package marker.

## Known Stubs

None. All functions are fully implemented. `_PWD_AVAILABLE = False` on Windows CI is the correct behavior (pwd is POSIX-only) — this is a platform guard, not a stub.

## Threat Flags

No new threat surface. The `subprocess` calls use hardcoded system tool names (`sw_vers`, `sysctl`, `system_profiler`) — no user-controlled input. `pwd.getpwall()` reads the local Open Directory database — same trust boundary as Windows ProfileList registry walk (T-10-01-01, T-10-01-02, T-10-01-03 all previously assessed in plan threat model).

## Self-Check

Files created:
- collectors/mac/__init__.py — exists
- collectors/mac/hardware.py — exists
- tests/test_mac_hardware_collector.py — exists
- tests/test_mac_init.py — exists

Commits:
- 0880a36 — Task 1 (package marker)
- ac1b6a6 — Task 2 (hardware.py)

Test suite: 163/163 passing.
