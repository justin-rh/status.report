---
phase: 04-app-detection-and-compliance-engine
reviewed: 2026-05-05T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - collectors/windows/apps.py
  - tests/test_app_collector.py
  - collectors/__init__.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-05-05
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files were reviewed: the core app detection collector (`collectors/windows/apps.py`), its test suite (`tests/test_app_collector.py`), and the collector orchestrator (`collectors/__init__.py`). The implementation is well-structured and clearly aligns with the spec-driven design decisions documented in RESEARCH.md and the PLAN files.

No critical security issues were found. The registry reads are read-only, use well-defined key paths, and no input is executed or written back to any system.

Three warnings were identified: one in the test suite that causes a key behavioral contract (`collection_errors` population) to go untested, one in the collector orchestrator where deferred imports can raise uncaught across a "never raises" boundary, and one logic gap in `_detect_one_app` where the MSIX path leaves `detection_method` as `"registry"` even when the MSIX branch sets `installed=True` — creating a state inconsistency between `installed` and `detection_method` for subsequent fallback guard logic. Three info items cover dead code and a missing edge-case test.

---

## Warnings

### WR-01: `test_collect_apps_never_raises` Does Not Exercise `collection_errors` Path

**File:** `tests/test_app_collector.py:264`

**Issue:** The test asserts that `collect_apps` never raises when patching `OpenKey` with `PermissionError`. However, `PermissionError` is a subclass of `OSError`, and `_search_uninstall_keys` catches `(FileNotFoundError, OSError)` at line 122 of `apps.py`. The exception is silently swallowed inside the helper before `_detect_one_app` ever sees it. As a result, `detect_apps`'s outer `except Exception` block (line 241, `apps.py`) is never triggered, `collection_errors` is never populated, and the test passes trivially — not because the boundary contract works, but because the inner catch absorbs the error first.

The contract the test is meant to verify — that a lower-level failure routes to `collection_errors` with an `AppStatus(error=...)` sentinel — remains untested.

**Fix:** Replace `PermissionError` (which `OSError` catches internally) with an exception that escapes all inner catches, such as raising inside `_detect_one_app` itself. Alternatively, inject the failure at a point where the outer guard is the only catcher:

```python
def test_collect_apps_never_raises():
    """collect_apps must not propagate exceptions — errors go to collection_errors."""
    with patch.object(apps_mod, "_detect_one_app", side_effect=RuntimeError("boom")):
        try:
            report = make_report()
            apps_mod.collect_apps(report)
        except Exception as exc:
            pytest.fail(f"collect_apps raised unexpectedly: {exc}")

    # Each app should have an error sentinel entry
    assert len(report.apps) == 7
    assert all(a.error is not None for a in report.apps)
    assert len(report.collection_errors) == 7
```

---

### WR-02: `detect_method` Not Set to `"registry"` Explicitly After MSIX Hit — Fallback Guard Uses Stale Default

**File:** `collectors/windows/apps.py:188-194`

**Issue:** In `_detect_one_app`, `detection_method` is initialized to `"registry"` on line 185. When the MSIX branch finds the app (lines 188–194), `installed` is set to `True` but `detection_method` is left at its default `"registry"` with only a comment explaining the intent. The guard on line 196 (`if not installed`) then correctly skips the filesystem path for an MSIX-detected app. However, if Step 3 (Uninstall registry sweep at line 205) is also skipped because `installed` is already `True`, the `detection_method` accurately reflects a registry detection path — but the *reason* it was found (MSIX repository vs. Uninstall key) is lost.

More concretely: an MSIX-detected Claude install and a registry-detected NinjaOne install both report `detection_method="registry"`, making it impossible to distinguish them in the output report without inspecting `version` heuristics. This is a correctness gap for the rendered character sheet and for any compliance downstream that distinguishes install methods.

**Fix:** Assign a distinct value in the MSIX branch:

```python
# Step 1: MSIX detection (primary for Claude; standard keyword sweep is fallback)
if "msix_family_prefix" in spec:
    msix_found, msix_version = _detect_msix(spec["msix_family_prefix"])
    if msix_found:
        installed = True
        version = msix_version
        detection_method = "msix"  # Distinguish from Uninstall-key registry hits
```

Update `AppStatus.detection_method` docstring in `models.py` to add `"msix"` as a valid value (`'registry' | 'filesystem' | 'msix'`).

---

### WR-03: Deferred Import in `collect_all` Can Raise Across "Never Raises" Boundary

**File:** `collectors/__init__.py:17-18`

**Issue:** `collect_all` docstring states "Never raises," and the design intent is that errors are routed to `report.collection_errors`. However, the deferred imports at lines 17–18 are not wrapped in any exception handler:

```python
from collectors.windows.hardware import collect_hardware, collect_profiles
from collectors.windows.apps import collect_apps
```

If the `collectors.windows` package is absent, broken, or running on a non-Windows platform (e.g., CI on macOS/Linux without a `winreg` stub), these lines raise `ImportError` or `ModuleNotFoundError`, which propagates directly to `main.py`'s caller — violating the "never raises" contract and producing an unhandled crash rather than a graceful degradation.

**Fix:** Wrap the imports and calls in a try/except block:

```python
def collect_all(report: AuditReport) -> None:
    """Run all collectors in order. Mutates report in place. Never raises."""
    try:
        from collectors.windows.hardware import collect_hardware, collect_profiles
        from collectors.windows.apps import collect_apps
    except ImportError as exc:
        report.collection_errors.append(f"Collector import failed: {exc}")
        return
    collect_hardware(report)
    collect_profiles(report)
    collect_apps(report)
```

---

## Info

### IN-01: Unused Variables in `test_crowdstrike_service_state_none_when_key_absent`

**File:** `tests/test_app_collector.py:227-229`

**Issue:** Two variables are initialized but never used:
- `fake_service_ctx` (line 227) — a `MagicMock` created for the service key path, but `open_key_side` raises `OSError` before it could be returned, so it is never referenced.
- `open_call_count` (line 229) — a list counter initialized to `[0]` but never incremented in `open_key_side` or read in any assertion.

These are dead code left from earlier drafts and add confusion without contributing to the test.

**Fix:** Remove both unused variables:

```python
def test_crowdstrike_service_state_none_when_key_absent():
    subkeys = ["CrowdStrike Windows Sensor"]
    fake_uninstall_ctx = _make_fake_ctx()
    # (remove fake_service_ctx and open_call_count)
    ...
```

---

### IN-02: No Test for Zoom Keyword Ordering (Pitfall 2 Protection)

**File:** `tests/test_app_collector.py` (missing test)

**Issue:** The `apps.py` spec comment (line 48) explicitly documents that `"Zoom Workplace"` must appear before `"Zoom"` in keywords to avoid matching `"Zoom Outlook Plugin"` (Pitfall 2). This protection is only in ordering — if the list order were accidentally reversed during a future refactor, no test would catch it. The current test suite has no case where a `"Zoom Outlook Plugin"` DisplayName is present to verify it is correctly skipped.

**Fix:** Add a test that injects `"Zoom Outlook Plugin"` as the DisplayName and asserts `Zoom` remains `installed=False`:

```python
def test_zoom_outlook_plugin_not_matched():
    """'Zoom Outlook Plugin' must NOT match Zoom — Pitfall 2 guard."""
    subkeys = ["Zoom Outlook Plugin"]
    fake_ctx = _make_fake_ctx()

    with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=_make_enum_fn(subkeys)), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=_make_query_fn("Zoom Outlook Plugin", None)), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    zoom = next(a for a in report.apps if a.name == "Zoom")
    assert zoom.installed is False, "Zoom Outlook Plugin must not match Zoom app"
```

---

### IN-03: `_START_MAP` Silently Returns `None` for Unmapped Service Start Values

**File:** `collectors/windows/apps.py:27`

**Issue:** `_START_MAP` maps Start DWORD values `{2: "Automatic", 3: "Manual", 4: "Disabled"}`. Values `0` (Boot) and `1` (System) are valid Windows service start types but are not mapped. `_START_MAP.get(int(val))` returns `None` for these, which is indistinguishable in the output from a missing service key. If Microsoft or a vendor ever configures CSFalconService with a non-standard start type, the service state will silently appear as `None` rather than flagging an unexpected value. This is a low-severity observability gap.

**Fix:** Add a fallback in `_read_service_start` to preserve the raw numeric value when it falls outside the known map:

```python
def _read_service_start(service_name: str) -> str | None:
    key_path = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            val, _ = winreg.QueryValueEx(key, "Start")
            return _START_MAP.get(int(val), f"Unknown({val})")
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return None
```

---

_Reviewed: 2026-05-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
