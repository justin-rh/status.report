# Deferred Items — Phase 03

## Pre-existing test failures (out of scope for 03-01)

**Discovered during:** 03-01 full test suite run
**Files affected:** tests/test_hardware_collector.py (13 failures), tests/test_profile_collector.py (8 failures)
**Root cause:** `psutil` not installed in current venv session — `ModuleNotFoundError: No module named 'psutil'`
**Why deferred:** These failures are pre-existing and not caused by any 03-01 changes. psutil is a runtime dependency listed in requirements.txt. These tests passed during Phase 2 verification. Likely the venv was rebuilt or psutil was not reinstalled before Phase 3 began.
**Resolution:** Run `.venv/Scripts/pip install -r requirements.txt` before the next test run to restore psutil and wmi to the venv.
