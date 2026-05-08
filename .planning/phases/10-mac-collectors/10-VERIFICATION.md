---
phase: 10-mac-collectors
verified: 2026-05-08T18:45:00Z
status: human_needed
score: 7/8 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run 'python3 main.py' on a physical macOS device (Intel or Apple Silicon)"
    expected: "A D&D HTML character sheet is written to logs/ relative to the script location, with cpu_model, os_version, ram_gb, disk_total_gb, disk_free_gb, local_profiles (human accounts only), and all 7 app rows populated. The file opens in the default browser if running interactively."
    why_human: "SC4 (PLAT-V2-04) requires live macOS execution to confirm the full output pipeline — html rendering, logs/ write, and browser-open cannot be exercised from Windows CI."
---

# Phase 10: Mac Collectors Verification Report

**Phase Goal:** Running the tool on macOS produces the same D&D HTML character sheet as Windows, populated with Mac hardware stats, user profiles, and app detection results
**Verified:** 2026-05-08T18:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | On macOS, cpu_model is populated for both Intel (sysctl) and Apple Silicon (system_profiler) | VERIFIED | `_collect_cpu_model` in hardware.py: `platform.machine()` branches x86_64 to sysctl, arm64 to system_profiler JSON. Parametrized test `test_cpu_model_collection[x86_64...]` and `test_cpu_model_collection[arm64...]` both pass. |
| 2 | On macOS, os_version contains 'macOS X.Y.Z' and os_build is populated from sw_vers | VERIFIED | `_collect_os` calls `sw_vers -productVersion` prefixed with "macOS " and `sw_vers -buildVersion`. `test_collect_hardware_populates_os_version_and_build` passes. |
| 3 | ram_gb and disk_total_gb/disk_free_gb are populated via psutil on macOS | VERIFIED | `_collect_memory_and_disk` uses `psutil.virtual_memory()` and `psutil.disk_usage("/")`. Tests `test_collect_hardware_ram_is_float` and `test_collect_hardware_disk_fields_are_floats` pass. |
| 4 | local_profiles contains only usernames with UID >= 501 (human accounts) | VERIFIED | `_enumerate_profiles` filters `entry.pw_uid >= 501`. `test_collect_profiles_returns_human_accounts` confirms alice(501)/bob(502) included, root(0)/_daemon(1) excluded. |
| 5 | All hardware and profile functions never raise; failures go to collection_errors only | VERIFIED | `collect_hardware` and `collect_profiles` wrap all helpers in try/except. Tests `test_collect_hardware_never_raises` and `test_collect_profiles_never_raises` confirm no exception propagates. |
| 6 | collectors/mac/hardware.py imports on Windows CI without ImportError (pwd guard) | VERIFIED | `try: import pwd as _pwd_module; _PWD_AVAILABLE = True except ImportError: _pwd_module = None; _PWD_AVAILABLE = False`. Confirmed on live Windows CI: `_PWD_AVAILABLE=False`, `_pwd_module=None`, no ImportError. `test_module_imports_without_real_pwd` passes. |
| 7 | All 7 target Mac apps produce exactly one AppStatus entry each, installed or not | VERIFIED | `detect_apps` iterates `MAC_APP_SPECS` (7 entries). Always-append rule in except block ensures 7 entries even when all paths False. `test_all_apps_always_present` asserts `len(report.apps) == 7` and all names present. |
| 8 | collect_all() dispatches to collectors.mac on darwin and collectors.windows on all other platforms; main.py writes HTML to logs/ on macOS | VERIFIED (code) / NEEDS HUMAN (live run) | `collect_all()` has `if sys.platform == "darwin": from collectors.mac...` inside function body. main.py has `if sys.platform == "darwin": usb_root = Path(__file__).parent` and `subprocess.run(["open", ...])`. Code verified. End-to-end output on a real Mac cannot be verified from Windows CI. |

**Score:** 7/8 truths verified (1 requires human/live-Mac verification)

### Deferred Items

None.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `collectors/mac/__init__.py` | Package marker for collectors.mac | VERIFIED | Exists, 1-line comment. `import collectors.mac` succeeds. |
| `collectors/mac/hardware.py` | collect_hardware() and collect_profiles() for macOS | VERIFIED | 175 lines. Contains both public functions, all 4 private helpers, pwd import guard, subprocess calls with timeout=. All exports present. |
| `collectors/mac/apps.py` | collect_apps() / detect_apps() + MAC_APP_SPECS table | VERIFIED | 208 lines. MAC_APP_SPECS has exactly 7 entries with correct names. `plistlib.load()` called with "rb" mode (line 97). All public functions present. |
| `collectors/__init__.py` | Platform-dispatching collect_all() with darwin branch | VERIFIED | Contains `if sys.platform == "darwin":` at line 19 with lazy imports inside `collect_all()`. |
| `main.py` | Platform-aware output path and auto-open | VERIFIED | `import subprocess` present (line 19). `if sys.platform == "darwin": usb_root = Path(__file__).parent` at line 60. `subprocess.run(["open", ...])` at line 102. |
| `tests/test_mac_hardware_collector.py` | Unit tests for collect_hardware() and helpers | VERIFIED | 13 tests, 100+ lines. `@pytest.mark.parametrize` covering Intel + Apple Silicon. All 13 pass. |
| `tests/test_mac_app_collector.py` | Unit tests for detect_apps() and MAC_APP_SPECS | VERIFIED | 16 tests (including 3 parametrized). All 16 pass. |
| `tests/test_mac_profile_collector.py` | Unit tests for collect_profiles() | VERIFIED | 5 tests, UID threshold + never-raise + pwd unavailable. All 5 pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `collectors/mac/hardware.py` | `models.AuditReport` | `report.cpu_model`, `report.os_version`, `report.local_profiles` | WIRED | Lines 75, 108, 122, 52 directly mutate report fields. |
| `collectors/mac/hardware.py` | subprocess (sw_vers, sysctl, system_profiler) | `subprocess.run()` calls | WIRED | 4 subprocess.run calls found in hardware.py lines 69, 79, 104, 116. All have `timeout=` parameter. |
| `collectors/mac/apps.py` | `models.AppStatus` | `report.apps.append(AppStatus(...))` | WIRED | Lines 168 and 196 both append AppStatus. Always-append rule enforced. |
| `_detect_bundle` | `plistlib.load` | `plist_path.open("rb")` — binary mode | WIRED | Line 97: `with plist_path.open("rb") as f: data = plistlib.load(f)`. Binary mode confirmed. |
| `collectors/__init__.py` | `collectors.mac.hardware` | Lazy import inside `collect_all()` body when `sys.platform == "darwin"` | WIRED | Line 20: `from collectors.mac.hardware import collect_hardware, collect_profiles`. |
| `main.py` | `subprocess.run(["open", ...])` | `isatty()` guard + darwin branch | WIRED | Lines 99-103: `if sys.stdin.isatty(): if sys.platform == "darwin": subprocess.run(["open", str(output_path)])`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `collectors/mac/hardware.py` | `report.cpu_model` | `subprocess.run(sysctl / system_profiler)` → parsed stdout | Yes — subprocess to real macOS tools | FLOWING |
| `collectors/mac/hardware.py` | `report.local_profiles` | `_pwd_module.getpwall()` filtered by UID >= 501 | Yes — pwd database query | FLOWING |
| `collectors/mac/apps.py` | `report.apps` | `MAC_APP_SPECS` table → filesystem checks + plistlib | Yes — filesystem traversal + plist parsing | FLOWING |
| `main.py` | HTML output file | `render_html(report)` → `output_path.write_text(html)` | Yes — render_html called unconditionally at line 73 | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 195 tests pass | `python -m pytest tests/ -q --tb=no` | 195 passed in 2.43s | PASS |
| 34 Mac-specific tests pass | `python -m pytest tests/test_mac_hardware_collector.py tests/test_mac_app_collector.py tests/test_mac_profile_collector.py -q` | 34 passed in 0.26s | PASS |
| collectors.mac.hardware importable on Windows | `python -c "import collectors.mac.hardware as h; print(h._PWD_AVAILABLE)"` | `False` (no ImportError) | PASS |
| MAC_APP_SPECS has 7 entries with correct names | `python -c "from collectors.mac.apps import MAC_APP_SPECS; print(len(MAC_APP_SPECS))"` | 7 | PASS |
| subprocess in main.py imports | AST parse of main.py | `subprocess in imports: True` | PASS |
| Full macOS output pipeline (html to logs/) | Requires live macOS | Not runnable from Windows CI | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PLAT-V2-01 | 10-01-PLAN.md, 10-04-PLAN.md | Tool collects Mac hardware stats — CPU model (Intel and Apple Silicon), total RAM, disk capacity and free space, macOS version | SATISFIED | `hardware.py` implements all fields. 13 tests in `test_mac_hardware_collector.py` verify each field. |
| PLAT-V2-02 | 10-01-PLAN.md, 10-04-PLAN.md | Tool enumerates all local user profiles on macOS (non-system accounts, UID >= 501) | SATISFIED | `collect_profiles()` + `_enumerate_profiles()` with UID >= 501 filter. 5 tests in `test_mac_profile_collector.py` verify threshold and never-raise. |
| PLAT-V2-03 | 10-02-PLAN.md, 10-04-PLAN.md | Tool detects 7 target apps on macOS | SATISFIED | `apps.py` with 7-entry MAC_APP_SPECS. 16 tests verify all detection paths. REQUIREMENTS.md shows `[x]` for this requirement. |
| PLAT-V2-04 | 10-03-PLAN.md | Same D&D HTML character sheet is rendered and saved on macOS runs (output to `logs/` relative to exe) | SATISFIED (code) / NEEDS HUMAN (live run) | Platform dispatch in `collect_all()` and darwin branches in `main.py` are fully wired. Live macOS run required to confirm end-to-end output. |

**Note:** REQUIREMENTS.md traceability table shows PLAT-V2-01, PLAT-V2-02, PLAT-V2-04 still as `[ ]` (not checked) while PLAT-V2-03 shows `[x]`. The implementations are complete — this is a documentation artifact that was not updated. Not a blocker.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `collectors/mac/apps.py` | 45 | `# TODO: verify on live Mac (LOW confidence)` on `launchdaemon_label: "com.ninjarmm.agent"` | INFO | NinjaOne launchctl label is unverified. The code runs correctly (returns "Stopped" on failure gracefully), but the label may not match the real NinjaOne daemon on Mac. Not a functional blocker — service_state degrades to "Stopped" if the label is wrong. |

No stub patterns (empty returns, placeholder components, or hardcoded empty data flowing to rendering) found in any Mac collector file.

### Human Verification Required

#### 1. End-to-End macOS Output (PLAT-V2-04)

**Test:** On a physical macOS device (Intel or Apple Silicon), run `python3 main.py` from the project root.

**Expected:**
- A file `logs/status_{hostname}_{date}.html` is created relative to `main.py`'s directory
- The HTML character sheet shows `cpu_model` (e.g., "Apple M3 Pro" or an Intel string), `os_version` (e.g., "macOS 14.4.1"), `ram_gb`, `disk_total_gb`, `disk_free_gb`
- `local_profiles` shows only human accounts (UID >= 501)
- All 7 app rows are present in the equipment table with either a version or "Not Found"
- If running interactively (terminal), the HTML file opens in the default browser

**Why human:** PLAT-V2-04 requires live macOS execution. The platform dispatch, output path logic, and browser-open are all wired correctly in code, but the full pipeline — collect_all() → render_html() → write to logs/ → open — can only be validated on actual macOS hardware.

#### 2. NinjaOne launchctl label verification (INFO-level)

**Test:** On a macOS device with NinjaOne RMM installed, check whether `launchctl list com.ninjarmm.agent` returns exit code 0.

**Expected:** Exit code 0 if the label is correct; otherwise NinjaOne service_state will always show "Stopped" (graceful degradation — not a crash).

**Why human:** The NinjaOne `launchdaemon_label` value `"com.ninjarmm.agent"` was documented as LOW confidence in PATTERNS.md. The code handles incorrect labels gracefully, but the correct label needs live-device verification.

### Gaps Summary

No gaps blocking goal achievement. All code artifacts exist, are substantive, and are wired. The 34 Mac-specific tests and 195 total tests all pass. One item requires human verification: the end-to-end macOS output pipeline (PLAT-V2-04) cannot be exercised from Windows CI.

---

_Verified: 2026-05-08T18:45:00Z_
_Verifier: Claude (gsd-verifier)_
