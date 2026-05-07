---
phase: 09-company-portal-detection
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - collectors/windows/apps.py
  - tests/test_app_collector.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-05-07
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Phase 9 adds Company Portal MSIX detection, MDM enrollment reporting via `_detect_mdm_enrollment()`, Zscaler as a new target app, and several new sub-app detection methods (`path_executable`, `chrome_extension_id`, `filesystem_path` for sub-apps). The implementation is well-structured and the error-isolation contract (D-16) is correctly upheld throughout.

Three warnings and three info items were found. No critical security or data-loss issues exist. The most significant finding is a fragile dispatch mechanism for MDM enrollment that uses a hardcoded name string, and a potential `KeyError` in the MERP filesystem branch if future specs omit `display_name_keywords`.

---

## Warnings

### WR-01: Hardcoded name string drives MDM enrollment dispatch

**File:** `collectors/windows/apps.py:445`
**Issue:** The MDM enrollment check is gated on `spec.get("name") == "Company Portal"` — a magic string comparison. If the app's `name` value in `APP_SPECS` is ever changed (e.g., renamed to "Intune Company Portal"), the enrollment check silently stops running with no error, no test failure at the spec level, and no indication in the output. This is the only spec-driven behavior that is NOT driven by a spec key.

**Fix:** Add an explicit `"mdm_enrollment": True` key to the Company Portal spec entry and check that flag instead of the name:

```python
# In APP_SPECS entry for Company Portal:
{
    "name": "Company Portal",
    "display_name_keywords": ["Company Portal", "Microsoft Intune Company Portal"],
    "msix_family_prefix": "Microsoft.CompanyPortal_",
    "mdm_enrollment": True,          # <-- add this
},

# In _detect_one_app, replace line 445:
if spec.get("mdm_enrollment"):
    service_state = _detect_mdm_enrollment()
```

---

### WR-02: `KeyError` if a future `filesystem_path` spec omits `display_name_keywords`

**File:** `collectors/windows/apps.py:428`
**Issue:** When the filesystem check succeeds (Step 2), the code calls `_search_uninstall_keys(spec["display_name_keywords"], _excludes)` to retrieve the version from the registry. This indexing is a hard `KeyError` if a spec has `filesystem_path` but no `display_name_keywords`. All current specs with `filesystem_path` also have `display_name_keywords`, so this is not currently reachable — but the pattern is fragile. Given the spec-driven architecture and documented extensibility, a future author adding a filesystem-only app spec would get an unhandled exception inside `_detect_one_app`, which is then silently swallowed by `detect_apps`, producing an `installed=False` entry with no version and a spurious `collection_errors` entry.

**Fix:** Guard the version-only registry lookup:

```python
# Step 2: Filesystem check (primary for MERP; D-02)
if not installed and "filesystem_path" in spec:
    if Path(spec["filesystem_path"]).exists():
        installed = True
        detection_method = "filesystem"
        # Attempt registry search for version only (D-03)
        if "display_name_keywords" in spec:
            _, reg_version = _search_uninstall_keys(spec["display_name_keywords"], _excludes)
            version = reg_version
```

---

### WR-03: Test count assertions hardcode `9` instead of `len(APP_SPECS)`

**File:** `tests/test_app_collector.py:89, 276, 818`
**Issue:** Three tests assert `len(report.apps) == 9` (lines 89, 276, 818). This number is the current count of entries in `APP_SPECS`. When the next app is added, all three tests fail with a misleading assertion error that looks like a bug in the collector, not a test that needs updating. The test for `test_detect_app_registry_miss` even documents "all 9 apps" in its docstring — this was updated from "7" in this phase, confirming the pattern is already causing maintenance friction.

**Fix:** Assert against the spec count dynamically:

```python
expected_count = len(apps_mod.APP_SPECS)
assert len(report.apps) == expected_count
```

This makes the tests self-maintaining and correctly signals intent: "every spec produces one entry."

---

## Info

### IN-01: `subprocess.run` for `node --version` does not close stdin

**File:** `collectors/windows/apps.py:321-328`
**Issue:** `subprocess.run([exe_path, '--version'], capture_output=True, text=True, timeout=5)` inherits stdin from the parent process. In a PyInstaller `--onedir` executable running without a console (double-clicked from USB), stdin is typically a null handle and this is harmless. However, explicitly passing `stdin=subprocess.DEVNULL` is the defensive practice for subprocesses spawned from GUI/headless processes and makes the intent clear.

**Fix:**
```python
result = subprocess.run(
    [exe_path, '--version'],
    capture_output=True, text=True, timeout=5,
    stdin=subprocess.DEVNULL,
)
```

---

### IN-02: `_detect_chrome_extension` version directory iteration order is non-deterministic

**File:** `collectors/windows/apps.py:348-354`
**Issue:** `ext_dir.iterdir()` returns directory entries in filesystem order, which is not guaranteed to be stable or version-sorted. If a Chrome extension has two version directories present simultaneously (common during background updates — old version stays until browser restart), the function returns whichever manifest is encountered first. This is unlikely to matter in practice (any version is acceptable), but the behavior is undocumented.

**Fix:** Add a comment or sort by version string if determinism matters:
```python
# iterdir() order is non-deterministic; returns first manifest found.
# For Chrome extensions this is acceptable — version is informational only.
for version_dir in ext_dir.iterdir():
```

---

### IN-03: `filesystem_path` values use forward slashes inconsistently with Windows path conventions

**File:** `collectors/windows/apps.py:84, 90-93`
**Issue:** Sub-app and MERP filesystem paths use forward slashes (`r"C:/Program Files/Microsoft Office/..."`) while the rest of the codebase uses backslash-style registry paths and Windows conventions. Python's `pathlib.Path` normalizes these correctly on Windows, so there is no runtime bug — but the inconsistency can mislead readers into thinking these are URL-style paths or Unix paths.

**Fix:** Use backslash-style paths for consistency:
```python
{"name": "Word", "filesystem_path": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"},
```

---

_Reviewed: 2026-05-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
