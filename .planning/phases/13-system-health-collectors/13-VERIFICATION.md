---
phase: 13-system-health-collectors
verified: 2026-05-18T19:30:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run scry.exe on a live Windows machine as SYSTEM or Administrator"
    expected: "Uptime displays as 'N days H hours' in the stat block with a real value; pending update count shows as 'N pending' (not N/A)"
    why_human: "Cannot invoke psutil.boot_time() or WUA COM without a running Windows machine; the collectors are guarded to degrade to None in CI"
  - test: "Run scry.exe on a machine with uptime > 7 days"
    expected: "The warnings box auto-expands and shows an amber WARN badge with code UPTIME_WARN"
    why_human: "Real uptime value required; cannot simulate live machine uptime in CI"
  - test: "Run scry.exe on a machine with uptime > 30 days"
    expected: "The warnings box auto-expands and shows a red badge-critical badge with code UPTIME_STALE; detail text includes 'Hibernation time is counted on Windows'"
    why_human: "Real uptime value required; badge-critical visual appearance requires human confirmation"
  - test: "Run scry.exe on a machine as a standard user (non-admin)"
    expected: "Pending Updates shows 'N/A' in the stat block; no crash or error dialog"
    why_human: "WUA COM privilege degradation requires a real standard-user session; mock covers the code path but not the end-to-end UX"
---

# Phase 13: System Health Collectors — Verification Report

**Phase Goal:** IT staff can see machine health signals — uptime and pending Windows update count — directly in the character sheet, with automatic warnings when uptime exceeds safe thresholds
**Verified:** 2026-05-18T19:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | IT staff sees uptime formatted as "12 days 4 hours" in the stat block | VERIFIED | `renderer/__init__.py` `_format_uptime()` confirmed; render smoke test `assert '12 days 4 hours' in html` passed |
| 2 | IT staff sees pending Windows update count ("3 pending") or "N/A" when WUA inaccessible | VERIFIED | `pending_updates_display` key in `_build_context()` return dict; `f"{report.pending_updates} pending"` when not None, else `"N/A"`; smoke test passed |
| 3 | Machine with uptime > 7 days shows yellow WARN warning; box auto-expands | VERIFIED | `_check_uptime()` returns `Warning(code='UPTIME_WARN', level='yellow')` when `days > 7`; `has_warnings = any(w.severity == 'WARN' ...)` triggers `open` attribute on `<details>`; test_uptime_check(8*86400) passes |
| 4 | Machine with uptime > 30 days shows red WARN noting hibernation time; box auto-expands | VERIFIED | `_check_uptime()` returns `Warning(code='UPTIME_STALE', level='red', detail='Hibernation time is counted on Windows')`; badge-critical smoke test passed; test_uptime_stale_detail_mentions_hibernation passes |
| 5 | All existing tests pass after Warning.level field added (no regression) | VERIFIED | `pytest tests/ -x -q` exits 0: 256 passed (was 203 pre-phase; +53 new tests across three plans) |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `models.py` | Warning.level field, AuditReport.uptime_seconds, AuditReport.pending_updates | VERIFIED | `level: str \| None = None` is LAST field in Warning (after `detail`); `uptime_seconds` and `pending_updates` fields present after `current_user` |
| `collectors/windows/hardware.py` | _WIN32COM_AVAILABLE guard, _collect_uptime(), collect_pending_updates() | VERIFIED | Guard at lines 27-32 mirroring _WMI_AVAILABLE; `_collect_uptime` private helper; `collect_pending_updates` public function; `collect_hardware()` calls `_collect_uptime(report)` as final (6th) step |
| `collectors/mac/hardware.py` | _collect_uptime() | VERIFIED | `_collect_uptime` private helper present; `collect_hardware()` calls it as final (5th) step; `import time` present |
| `collectors/__init__.py` | collect_pending_updates wired on Windows path only | VERIFIED | Windows branch imports and calls `collect_pending_updates(report)` after `collect_apps`; darwin branch unchanged |
| `requirements.txt` | pywin32==311 | VERIFIED | Line 4: `pywin32==311` |
| `scry.spec` | win32timezone in hiddenimports | VERIFIED | Line 43: `'win32timezone'` present in hiddenimports list |
| `health_checks.py` | UPTIME_WARN_DAYS=7, UPTIME_STALE_DAYS=30, _check_uptime(), evaluate_warnings() returning 4 | VERIFIED | Constants at lines 15-16; `_check_uptime()` at line 131; `evaluate_warnings()` returns 4-element list |
| `renderer/__init__.py` | _format_uptime() helper, uptime_display and pending_updates_display in _build_context() | VERIFIED | `_format_uptime` nested helper inside `_build_context()`; both keys in return dict; handles singular/plural correctly |
| `renderer/templates/character_sheet.html` | System Health stat block, badge-critical CSS, level-aware badge markup | VERIFIED | `<!-- System Health — Phase 13 -->` comment; Uptime and Pending Updates rows with muted class; `.badge-critical { background: var(--red); color: #fff; }` after `.badge-warn`; level-aware badge span at line 517 |
| `tests/test_health_checks.py` | test_evaluate_warnings_always_returns_four, test_uptime_check, test_uptime_stale_detail_mentions_hibernation | VERIFIED | All three functions present; `_three` variant absent; no `== 3` assertions remain |
| `tests/test_hardware_collector.py` | 5 Phase 13 collector tests | VERIFIED | test_collect_uptime_populates_uptime_seconds, test_collect_uptime_degrades_on_psutil_error, test_collect_pending_updates_skipped_when_win32com_unavailable, test_collect_pending_updates_populates_count_when_com_available, test_collect_pending_updates_degrades_on_com_error — all present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| collectors/__init__.py | collectors/windows/hardware.collect_pending_updates | Windows-path import and call | WIRED | Line 26: import; line 31: `collect_pending_updates(report)` — not present in darwin branch |
| collectors/windows/hardware._collect_uptime | psutil.boot_time | `int(time.time() - psutil.boot_time())` | WIRED | Line 199: `int(time.time() - psutil.boot_time())` confirmed |
| collectors/windows/hardware.collect_pending_updates | _win32com_client.Dispatch | _WIN32COM_AVAILABLE guard | WIRED | Guard at lines 82-90; `_win32com_client.Dispatch("Microsoft.Update.Session")` called only when guard True |
| health_checks.evaluate_warnings | health_checks._check_uptime | 4th list element | WIRED | `_check_uptime(report)` as 4th return element at line 34 |
| health_checks._check_uptime | models.Warning.level | keyword arg level='yellow' or level='red' | WIRED | Lines 154 (`level='red'`) and 161 (`level='yellow'`) confirmed |
| renderer/__init__._build_context | character_sheet.html uptime_display variable | return dict key 'uptime_display' | WIRED | Line 189: `'uptime_display': uptime_display` in return dict; template uses `{{ uptime_display \| default('—', true) }}` |
| character_sheet.html badge span | w.level value | Jinja2 `{% if w.level == 'red' %}` condition | WIRED | Line 517: `{% if w.level == 'red' %}badge-critical{% else %}badge-warn{% endif %}` confirmed |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `renderer/templates/character_sheet.html` uptime row | `uptime_display` | `_build_context()` → `_format_uptime(report.uptime_seconds)` → `_collect_uptime()` → `psutil.boot_time()` | Yes (on live Windows; None on CI — intentional degradation) | FLOWING |
| `renderer/templates/character_sheet.html` pending updates row | `pending_updates_display` | `_build_context()` → `report.pending_updates` → `collect_pending_updates()` → WUA COM `result.Updates.Count` | Yes (on live Windows as SYSTEM; "N/A" on CI/standard-user — intentional degradation) | FLOWING |
| `character_sheet.html` warning badge | `w.level` | `report.warnings[3].level` → `_check_uptime()` → set from `report.uptime_seconds` | Yes (flows from uptime collector; None when collection fails — intentional) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| models backward-compat: `Warning(code, severity, message, detail_value)` positional | `python -c "from models import Warning; w=Warning('X','OK','msg','some detail'); assert w.detail=='some detail' and w.level is None"` | Pass | PASS |
| AuditReport new fields have None defaults | `python -c "from models import AuditReport; r=AuditReport('H',None); assert r.uptime_seconds is None and r.pending_updates is None"` | Pass | PASS |
| health_checks returns 4 warnings with correct escalation | Python inline: 8d→UPTIME_WARN/yellow; 31d→UPTIME_STALE/red with 'hibernation' in detail | Pass | PASS |
| render smoke: uptime and pending_updates visible in rendered HTML | `render_html(r)` with uptime_seconds=12*86400+4*3600, pending_updates=3 | `'12 days 4 hours' in html` and `'3 pending' in html` | PASS |
| badge-critical in rendered HTML for level='red' warning | `render_html(r)` with Warning level='red' | `'badge-critical' in html2` | PASS |
| Full test suite | `pytest tests/ -x -q` | 256 passed, 0 failed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| HEALTH-01 | 13-01, 13-03 | Pending Windows update count in stat block; degrades to N/A for standard user | SATISFIED | `collect_pending_updates()` with `_WIN32COM_AVAILABLE` guard; `pending_updates_display` in template; N/A path verified |
| HEALTH-02 | 13-01, 13-03 | Uptime since last reboot in stat block (days + hours format) | SATISFIED | `_collect_uptime()` via psutil; `_format_uptime()` produces "N days H hours"; template row confirmed |
| WARN-04 | 13-02 | Yellow warning when uptime > 7 days; UPTIME_WARN_DAYS=7 constant | SATISFIED | `_check_uptime()` returns level='yellow' when `days > 7`; constant at health_checks.py line 15; badge-warn in template |
| WARN-05 | 13-02 | Red warning when uptime > 30 days; UPTIME_STALE_DAYS=30; text notes hibernation time | SATISFIED | `_check_uptime()` returns level='red' when `days > 30`; detail='Hibernation time is counted on Windows'; badge-critical in template |

No orphaned requirements — all 4 IDs (HEALTH-01, HEALTH-02, WARN-04, WARN-05) claimed across the three plans and verified.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `collectors/mac/apps.py` | 45 | `TODO: verify on live Mac (LOW confidence)` | Info | Pre-existing; unrelated to Phase 13 scope; no impact on health collector goal |

No anti-patterns found in Phase 13 files. The `None` defaults in `uptime_seconds` and `pending_updates` are intentional degraded states (not stubs) — the `_WIN32COM_AVAILABLE` guard explicitly returns early when COM is unavailable, and psutil wraps errors to `collection_errors`. Data flows correctly when collectors have access.

### Human Verification Required

#### 1. Live Windows SYSTEM/Administrator run

**Test:** Run `scry.exe` on a Windows machine as SYSTEM (NinjaOne) or local Administrator
**Expected:** Stat block shows "Uptime: X days Y hours" with a real value; "Pending Updates: N pending" with an actual integer count
**Why human:** psutil.boot_time() and WUA COM (`Microsoft.Update.Session`) require a running Windows machine. CI tests mock both paths; the live path cannot be exercised in CI.

#### 2. Yellow warning at uptime > 7 days

**Test:** Run `scry.exe` on a machine that has been running for more than 7 days without a reboot
**Expected:** The "Health Checks" box is open (auto-expanded) and shows a yellow-amber WARN badge with message "Uptime is N days"
**Why human:** Real uptime required. Test suite covers the logic but not the visual badge color rendering in a browser.

#### 3. Red warning at uptime > 30 days with hibernation note

**Test:** Run `scry.exe` on a machine with uptime > 30 days (or temporarily lower UPTIME_STALE_DAYS to a small value for test)
**Expected:** Red badge-critical badge is visible; warning detail reads "Hibernation time is counted on Windows"; box is auto-expanded
**Why human:** Visual confirmation of red background required; hibernation note text visible to IT staff.

#### 4. Standard user privilege degradation (N/A for pending updates)

**Test:** Run `scry.exe` as a standard user (non-admin) on a Windows machine
**Expected:** Stat block shows "Pending Updates: N/A" (muted styling); no crash, no error dialog
**Why human:** Requires a real standard-user session. The `_WIN32COM_AVAILABLE=False` CI mock covers the code path, but the privilege-based degradation (`_WIN32COM_AVAILABLE=True` but COM raises `Access denied`) needs live confirmation.

### Gaps Summary

No gaps. All 5 roadmap success criteria are fully implemented and verified programmatically. The 4 human verification items represent real-machine behaviors that cannot be tested in CI — they are expected pre-ship checks for a Windows tool that relies on system-level APIs.

---

_Verified: 2026-05-18T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
