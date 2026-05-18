# Phase 13: System Health Collectors — Research

**Researched:** 2026-05-18
**Domain:** Python system metrics (psutil boot_time), Windows COM/WUA pending update collection, dataclass field extension, Jinja2 template warning-color rendering
**Confidence:** HIGH — all decisions locked in CONTEXT.md; code is read directly from the working tree

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Severity Model**
- D-01: Add `level: str | None = None` field to the `Warning` dataclass in `models.py`. Values: `'yellow'` (caution) | `'red'` (critical) | `None` (OK or informational). This is the only change to `Warning`.
- D-02: `severity` field stays `'OK'` / `'WARN'` — Phase 6 D-03 is unchanged. Phase 11 `--warnings` CLI filter works without modification.
- D-03: Renderer determines warning color from `w.level` when `w.severity == 'WARN'`. Both `level='yellow'` and `level='red'` must trigger auto-expand. `level=None` warnings do not contribute to auto-expand.

**AuditReport New Fields**
- D-04: Add `uptime_seconds: int | None = None` and `pending_updates: int | None = None` to `AuditReport`.

**Uptime Collection**
- D-05: `psutil.boot_time()` — already in stack, no new dep. `int(time.time() - psutil.boot_time())`.
- D-06: Fits in existing `collectors/windows/hardware.py` and `collectors/mac/hardware.py`.
- D-07: Display format `"N days H hours"`. Edge cases (< 1 day, < 1 hour) are Claude's discretion.

**Pending Updates Collection**
- D-08: `win32com.client.Dispatch("Microsoft.Update.Session")`. New dep: `pywin32==311`.
- D-09: Guard with `_WIN32COM_AVAILABLE` — mirrors `_WMI_AVAILABLE` pattern exactly. When `False`, `pending_updates` stays `None`. CI runs without a COM server.
- D-10: Standard user gets `None` → display `"N/A"`. SYSTEM / Administrator gets the integer count.

**Warning Shape**
- D-11: `evaluate_warnings()` returns one UPTIME `Warning` (escalating). Logic: `None` uptime → OK/None; ≤ 7 days → OK/None; 7–30 days → `code='UPTIME_WARN'`, `severity='WARN'`, `level='yellow'`; > 30 days → `code='UPTIME_STALE'`, `severity='WARN'`, `level='red'` with hibernation note.
- D-12: `UPTIME_WARN_DAYS: int = 7` and `UPTIME_STALE_DAYS: int = 30` constants in `health_checks.py`.
- D-13: No `Warning` for `pending_updates` — informational display only.
- D-14: `evaluate_warnings()` now returns 4 objects: OS_VERSION, DISK_SPACE, RENAME_REQUIRED, UPTIME.

**Character Sheet Stat Block**
- D-15: New "System Health" group of rows in the existing stat block.
- D-16: `pending_updates` displays as `"N pending"` or `"N/A"` when `None`. Zero → `"0 pending"`.

### Claude's Discretion

- Exact display label text for the System Health rows
- Sub-hour and sub-day edge case formatting for uptime display
- Whether `uptime_seconds` collection in hardware collectors is a new private helper or inline
- Exact WUA COM query logic (searcher criteria string, result counting)
- Test fixture approach for `_WIN32COM_AVAILABLE = False` path

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HEALTH-01 | Pending Windows update count in stat block; degrades to N/A as standard user | WUA COM collection with `_WIN32COM_AVAILABLE` guard; `pending_updates: int | None` on AuditReport; `_build_context()` produces `pending_updates_display` string |
| HEALTH-02 | Uptime since last reboot in stat block (days + hours format) | `psutil.boot_time()` already available; `uptime_seconds: int | None` on AuditReport; `_build_context()` produces `uptime_display` string |
| WARN-04 | Yellow caution warning when uptime > 7 days | `_check_uptime()` in `health_checks.py`; `UPTIME_WARN_DAYS = 7`; `level='yellow'` triggers auto-expand via renderer `has_warnings` flag |
| WARN-05 | Red critical warning when uptime > 30 days; text notes hibernation time is counted | `UPTIME_STALE_DAYS = 30`; `level='red'`; detail string includes hibernation note |
</phase_requirements>

---

## Summary

Phase 13 extends the SCRY audit tool with two new system health signals: uptime since last reboot and pending Windows update count. The phase touches five files in a coordinated sequence: `models.py` (two dataclass additions), `health_checks.py` (new threshold constants + one new check function + extended return), `collectors/windows/hardware.py` (uptime via psutil + new WUA COM collector with guard), `collectors/__init__.py` (call new collectors), and `renderer/__init__.py` + `character_sheet.html` (new System Health stat block section + level-colored warning badges).

All user decisions are locked in CONTEXT.md. There are no alternative designs to evaluate. The primary risk is regression: the `Warning` dataclass `level` field must be added as the last field with a `None` default to avoid breaking the 22 existing `test_health_checks.py` tests that construct `Warning` objects positionally or by keyword without `level`. The existing `test_evaluate_warnings_always_returns_three` test must also be updated to assert 4 (not 3) objects.

pywin32==311 is not currently installed in the project venv (confirmed: `pip show pywin32` returns "not found"). The `_WIN32COM_AVAILABLE` guard pattern means this does not break CI — all 203 current tests pass without pywin32. The WUA COM collector is Windows-only and must never be imported on macOS.

**Primary recommendation:** Implement in order — models first, health_checks second, hardware collector third, collect_all wiring fourth, renderer last. Each step is independently testable. SC5 (no regression) is the gating criterion throughout.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Uptime collection | Collector (windows/mac hardware) | — | Pure data acquisition; psutil already imported in both hardware modules |
| WUA pending update count | Collector (windows/hardware) | — | Windows-only COM call; belongs alongside other WMI guards in same file |
| Uptime threshold evaluation | Health checks (`health_checks.py`) | — | Pure function over AuditReport; mirrors existing `_check_disk_space` pattern |
| Display formatting (uptime, updates) | Renderer (`renderer/__init__.py`) | — | `_build_context()` pre-computes all display strings before template render |
| Warning color (yellow/red badge) | Renderer template (Jinja2) | — | `level` field drives CSS class; logic-free template reads pre-computed value |
| Auto-expand warnings box | Renderer template (Jinja2) | — | Currently driven by `has_warnings`; must update to include `level`-aware logic |

---

## Standard Stack

### Core (existing — verified in working tree)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| psutil | 7.2.2 [VERIFIED: pip show psutil] | `boot_time()` for uptime | Already imported in both hardware collectors |
| Jinja2 | 3.1.6 [VERIFIED: requirements.txt] | HTML template rendering | `character_sheet.html` already has warning badge pattern |
| dataclasses | stdlib | `Warning` and `AuditReport` extension | `field(default=None)` pattern in use |

### New Dependency
| Library | Version | Purpose | Installation |
|---------|---------|---------|-------------|
| pywin32 | 311 [VERIFIED: CONTEXT.md D-08, REQUIREMENTS.md] | `win32com.client.Dispatch` for WUA COM | `pip install pywin32==311` |

**Installation:**
```bash
pip install pywin32==311
```

Add to `requirements.txt`:
```
pywin32==311
```

Add to `scry.spec` `hiddenimports`:
```python
'win32timezone',
```
Note: `win32com`, `win32com.client`, `win32com.server`, `pywintypes`, `pythoncom` are already in `scry.spec` hiddenimports [VERIFIED: scry.spec lines 33–43]. Only `win32timezone` is the new addition per REQUIREMENTS.md implementation note.

---

## Architecture Patterns

### System Architecture Diagram

```
main.py
  │
  ├─ collect_all(report)
  │      ├─ [windows] collectors/windows/hardware.py
  │      │      ├─ collect_hardware(report)
  │      │      │      └─ _collect_uptime(report)       ← NEW: psutil.boot_time()
  │      │      └─ collect_pending_updates(report)      ← NEW: win32com WUA, guarded
  │      └─ [darwin] collectors/mac/hardware.py
  │             └─ collect_hardware(report)
  │                    └─ _collect_uptime(report)       ← NEW: psutil.boot_time()
  │
  ├─ evaluate_warnings(report)   [health_checks.py]
  │      └─ _check_uptime(report)  ← NEW: 4th Warning object
  │             UPTIME_WARN_DAYS=7, UPTIME_STALE_DAYS=30
  │
  └─ render_html(report)   [renderer/__init__.py]
         └─ _build_context(report)
                ├─ uptime_display: str    ← NEW
                ├─ pending_updates_display: str  ← NEW
                └─ warning level → badge class  ← NEW
         └─ character_sheet.html
                ├─ System Health section in stat block  ← NEW
                └─ level-colored WARN badges            ← NEW
```

### Recommended Project Structure (unchanged)
```
collectors/
├── windows/
│   └── hardware.py    # Add _collect_uptime() + collect_pending_updates()
├── mac/
│   └── hardware.py    # Add _collect_uptime() only
└── __init__.py        # Add collect_pending_updates call (Windows path only)
health_checks.py       # Add constants + _check_uptime() + extend evaluate_warnings()
models.py              # Add Warning.level, AuditReport.uptime_seconds/.pending_updates
renderer/
├── __init__.py        # Add uptime_display, pending_updates_display to _build_context()
└── templates/
    └── character_sheet.html  # Add System Health rows, level-aware badge CSS
```

### Pattern 1: WMI Guard Mirror (_WIN32COM_AVAILABLE)

The exact pattern from `collectors/windows/hardware.py` [VERIFIED: lines 19–24]:

```python
# Existing pattern (WMI):
try:
    import wmi as _wmi_module
    _WMI_AVAILABLE = True
except ImportError:
    _wmi_module = None
    _WMI_AVAILABLE = False
```

New COM guard must mirror this exactly:
```python
# New pattern (win32com) — add immediately after _WMI_AVAILABLE block:
try:
    import win32com.client as _win32com_client  # type: ignore[import-untyped]
    _WIN32COM_AVAILABLE = True
except ImportError:
    _win32com_client = None  # type: ignore[assignment]
    _WIN32COM_AVAILABLE = False
```

Tests patch `_WIN32COM_AVAILABLE` and `_win32com_client` on the module using `patch.object(hw_mod, "_WIN32COM_AVAILABLE", False)` — exactly the same technique as WMI tests at lines 79 and 113 of `test_hardware_collector.py`.

### Pattern 2: Uptime Collection (psutil.boot_time)

```python
# Source: psutil API, confirmed working [VERIFIED: python -c "import time; import psutil; print(int(time.time() - psutil.boot_time()))"]
import time

def _collect_uptime(report: AuditReport) -> None:
    """Populate uptime_seconds via psutil.boot_time(). Never raises."""
    try:
        report.uptime_seconds = int(time.time() - psutil.boot_time())
    except Exception as exc:
        report.collection_errors.append(f"Uptime collection failed: {exc}")
```

No new imports needed — `psutil` and `time` are already imported in both hardware modules [VERIFIED: hardware.py imports].

### Pattern 3: WUA COM Query

```python
# Source: CONTEXT.md D-08, REQUIREMENTS.md WUA privilege note [ASSUMED: exact COM API shape]
def collect_pending_updates(report: AuditReport) -> None:
    """Populate pending_updates via WUA COM. Windows-only. Never raises.

    Returns None when _WIN32COM_AVAILABLE is False (CI) or when running as
    standard user (COM call raises COMError — degrades to None per D-10).
    """
    if not _WIN32COM_AVAILABLE:
        return
    try:
        session = _win32com_client.Dispatch("Microsoft.Update.Session")
        searcher = session.CreateUpdateSearcher()
        result = searcher.Search("IsInstalled=0 and Type='Software'")
        report.pending_updates = result.Updates.Count
    except Exception as exc:
        report.collection_errors.append(f"Pending updates collection failed: {exc}")
        # pending_updates stays None (D-10: standard user → None → N/A display)
```

The search criteria `"IsInstalled=0 and Type='Software'"` is the standard WUA query for software updates not yet installed. [ASSUMED: exact criteria string — standard WUA usage but not verified against live COM session in this research]

### Pattern 4: _check_uptime in health_checks.py

Follows the exact shape of `_check_disk_space` [VERIFIED: health_checks.py lines 71–104]:

```python
UPTIME_WARN_DAYS: int = 7
UPTIME_STALE_DAYS: int = 30

def _check_uptime(report: AuditReport) -> Warning:
    """Return UPTIME Warning. Escalates: OK → UPTIME_WARN (yellow) → UPTIME_STALE (red)."""
    if report.uptime_seconds is None:
        return Warning(
            code='UPTIME',
            severity='OK',
            message='Uptime check skipped',
            detail='uptime_seconds not collected',
        )
    days = report.uptime_seconds // 86400
    if days > UPTIME_STALE_DAYS:
        return Warning(
            code='UPTIME_STALE',
            severity='WARN',
            message=f'Uptime is {days} days — reboot required',
            detail='Hibernation time is counted on Windows',
            level='red',
        )
    if days > UPTIME_WARN_DAYS:
        return Warning(
            code='UPTIME_WARN',
            severity='WARN',
            message=f'Uptime is {days} days',
            detail=f'Uptime exceeds {UPTIME_WARN_DAYS}-day caution threshold',
            level='yellow',
        )
    return Warning(code='UPTIME', severity='OK', message='Uptime is within normal range', detail=None)
```

### Pattern 5: Warning Dataclass Field Addition

Add `level` as the final field to avoid breaking positional construction [VERIFIED: models.py Warning dataclass lines 51–57]:

```python
@dataclass
class Warning:
    """A single health check result produced by evaluate_warnings()."""
    code: str
    severity: str
    message: str
    detail: str | None = None
    level: str | None = None   # NEW: 'yellow' | 'red' | None
```

All 22 existing test constructions use keyword or named args and do not pass `level` — adding it as the last optional field with `None` default is fully backward-compatible.

### Pattern 6: _build_context Extensions

```python
# In renderer/__init__.py _build_context(), add after existing display calculations:

# Uptime display
def _format_uptime(seconds: int) -> str:
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''} {hours} hour{'s' if hours != 1 else ''}"
    if hours >= 1:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{minutes} minute{'s' if minutes != 1 else ''}"

uptime_display = _format_uptime(report.uptime_seconds) if report.uptime_seconds is not None else None
pending_updates_display = (
    f"{report.pending_updates} pending"
    if report.pending_updates is not None
    else "N/A"
)
```

Return dict additions:
```python
'uptime_display': uptime_display,
'pending_updates_display': pending_updates_display,
```

### Pattern 7: Template Warning Box — Level-Aware Coloring

Current badge in `character_sheet.html` [VERIFIED: lines 509–511]:
```html
<span class="badge {% if w.severity == 'WARN' %}badge-warn{% else %}badge-installed{% endif %}">
  {% if w.severity == 'WARN' %}&#9888; WARN{% else %}&#10003; OK{% endif %}
</span>
```

Updated badge (per D-03 — level drives color, severity drives WARN/OK display):
```html
<span class="badge {% if w.severity == 'WARN' %}{% if w.level == 'red' %}badge-critical{% else %}badge-warn{% endif %}{% else %}badge-installed{% endif %}">
  {% if w.severity == 'WARN' %}&#9888; WARN{% else %}&#10003; OK{% endif %}
</span>
```

Add CSS variable and class (template already has `--red: #ef4444` [VERIFIED: line 18]):
```css
.badge-critical {
  background: var(--red);
  color: #fff;
}
```

Auto-expand logic: the `has_warnings` context variable is already `any(w.severity == 'WARN' for w in report.warnings)` [VERIFIED: renderer/__init__.py line 167]. Since UPTIME_WARN and UPTIME_STALE both have `severity='WARN'`, the `has_warnings` flag will be `True` for both, correctly triggering auto-expand. No change needed to the `has_warnings` computation.

### Pattern 8: System Health Stat Block Section

Insert after the "Serial Number" / "Current User" rows, before closing `</div>` of `.stat-grid` [VERIFIED: character_sheet.html lines 412–421]:

```html
<!-- System Health rows — Phase 13 -->
<div class="stat-label">Uptime</div>
<div class="stat-value{% if uptime_display is none %} muted{% endif %}">
  {{ uptime_display | default('—', true) }}
</div>

<div class="stat-label">Pending Updates</div>
<div class="stat-value">{{ pending_updates_display }}</div>
```

### Pattern 9: collect_all Wiring

Current `collectors/__init__.py` [VERIFIED: lines 18–27] calls `collect_hardware`, `collect_profiles`, `collect_apps`. For Phase 13, uptime collection goes inside `collect_hardware()` itself (a new private helper called from that function). The WUA collector is a separate function called explicitly only on the Windows path:

```python
# collectors/__init__.py — Windows path only
if sys.platform == "darwin":
    from collectors.mac.hardware import collect_hardware, collect_profiles
    from collectors.mac.apps import collect_apps
    collect_hardware(report)      # includes _collect_uptime
    collect_profiles(report)
    collect_apps(report)
else:
    from collectors.windows.hardware import collect_hardware, collect_profiles, collect_pending_updates
    from collectors.windows.apps import collect_apps
    collect_hardware(report)      # includes _collect_uptime
    collect_profiles(report)
    collect_apps(report)
    collect_pending_updates(report)   # Windows-only; guarded by _WIN32COM_AVAILABLE
```

### Anti-Patterns to Avoid

- **Adding `level` as a non-optional field:** Breaks all existing Warning constructions in test files — always use `level: str | None = None` with a default.
- **Calling `collect_pending_updates` on macOS path:** WUA/win32com is Windows-only. The Mac path must never call it. Guard with both `sys.platform != "darwin"` and `_WIN32COM_AVAILABLE`.
- **Using `Win32_Product` for update queries:** Prohibited by CLAUDE.md. WUA COM is the correct path.
- **Using `--onefile` in PyInstaller:** Quarantined by CrowdStrike Falcon on target machines. `scry.spec` already uses `--onedir`. Do not change.
- **Importing `win32com` unconditionally at module top:** Will crash CI and non-Windows systems. The `try/except ImportError` guard is mandatory.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Boot time calculation | Custom uptime via WMI or registry | `psutil.boot_time()` | Already in stack; cross-platform; standard user privilege; no new dependency |
| Windows update enumeration | Registry scan or WMI Win32_QuickFixEngineering | `win32com.client` WUA COM | WUA is the authoritative Windows Update API; WMI update queries are deprecated |
| Display string formatting for uptime | External humanize library | Inline `_format_uptime()` helper | One simple function; no additional dependency justified |

**Key insight:** The entire phase reuses existing architectural patterns (guard flags, CollectionResult degradation, private helper convention, Jinja2 `| default('—', true)`) — no new patterns need to be invented.

---

## Common Pitfalls

### Pitfall 1: Warning level field breaks positional test constructions
**What goes wrong:** If `level` is inserted before `detail` in the dataclass, any test constructing `Warning(code, severity, message, detail_value)` by position will assign `detail_value` to `level` instead.
**Why it happens:** Python dataclass positional construction follows field declaration order.
**How to avoid:** Always add `level` as the LAST field (after `detail`). Confirmed: `detail` is currently the last field [VERIFIED: models.py line 57].
**Warning signs:** Tests asserting `w.detail == 'some text'` start failing with `w.detail == None`.

### Pitfall 2: test_evaluate_warnings_always_returns_three will fail after Phase 13
**What goes wrong:** `test_evaluate_warnings_always_returns_three` in `test_health_checks.py` [VERIFIED: line 91] explicitly asserts `len(warnings) == 3` and `warnings[2].code == 'RENAME_REQUIRED'`. After Phase 13, `evaluate_warnings()` returns 4 objects.
**Why it happens:** D-14 (CONTEXT.md) extends the contract from 3 to 4; the test was written to guard the old contract.
**How to avoid:** Update this test to assert `len(warnings) == 4`, `warnings[2].code == 'RENAME_REQUIRED'`, `warnings[3].code` is one of `'UPTIME'|'UPTIME_WARN'|'UPTIME_STALE'`. SC5 requires all tests pass after the change.
**Warning signs:** `test_evaluate_warnings_always_returns_three` fails with `assert 4 == 3`.

### Pitfall 3: WUA COM searcher raises on standard user — must not crash
**What goes wrong:** `searcher.Search(...)` raises a COM error (`pywintypes.com_error`) when the calling process is not SYSTEM or Administrator.
**Why it happens:** WUA COM requires elevated privilege to query pending updates.
**How to avoid:** The outer `except Exception` in `collect_pending_updates` catches `pywintypes.com_error` (which is a subclass of `Exception`) and leaves `pending_updates = None`. The `"N/A"` display path then triggers.
**Warning signs:** SCRY crashes instead of showing `"N/A"` when run as a standard user.

### Pitfall 4: win32timezone missing from PyInstaller build
**What goes wrong:** `scry.exe` raises `ImportError: No module named 'win32timezone'` at runtime because PyInstaller cannot statically trace COM timezone imports.
**Why it happens:** `win32com.client` dispatches COM calls that internally import `win32timezone` at runtime — PyInstaller misses it.
**How to avoid:** `scry.spec` already has a `win32com_hidden = collect_submodules('win32com')` block [VERIFIED: scry.spec lines 13–19]. Adding `'win32timezone'` to `hiddenimports` explicitly is the REQUIREMENTS.md-mandated safeguard. Confirm it is added.
**Warning signs:** Tool works in dev but crashes immediately when run from USB.

### Pitfall 5: Mac hardware collector importing win32com
**What goes wrong:** `collectors/mac/hardware.py` crashes on macOS if it tries to import `win32com`.
**Why it happens:** `win32com` is Windows-only. macOS does not have it even with pywin32 installed.
**How to avoid:** WUA collection must only exist in `collectors/windows/hardware.py`. The Mac hardware collector gets `_collect_uptime()` only.
**Warning signs:** Mac CI or macOS test run raises `ModuleNotFoundError: No module named 'win32com'`.

### Pitfall 6: Hibernation uptime inflation — detail text must be explicit
**What goes wrong:** IT staff reboot a machine but uptime stays high due to hibernation/fast startup.
**Why it happens:** On Windows, `psutil.boot_time()` returns the time the system came out of hibernation (fast startup), not the last full shutdown + reboot. Hibernate time is counted as uptime.
**How to avoid:** The UPTIME_STALE warning `detail` field must include the phrase "Hibernation time is counted on Windows" [VERIFIED: REQUIREMENTS.md WARN-05 note, CONTEXT.md Specifics section].
**Warning signs:** IT reboots a machine, tool still shows UPTIME_STALE. Expected — not a bug.

### Pitfall 7: `has_warnings` renderer context — no change needed
**What goes wrong:** Developer modifies `has_warnings` computation to add `level`-awareness, breaking the existing `--warnings` CLI filter.
**Why it happens:** Confusion about where level-awareness belongs.
**How to avoid:** `has_warnings` is `any(w.severity == 'WARN' for w in report.warnings)` [VERIFIED: renderer/__init__.py line 167]. UPTIME_WARN and UPTIME_STALE both have `severity='WARN'`, so auto-expand works without changing this line. Only the badge CSS class (not `has_warnings`) uses `w.level`.

---

## Code Examples

### Verified Pattern: WMI guard in hardware.py (reference for _WIN32COM_AVAILABLE)
```python
# Source: collectors/windows/hardware.py lines 19–24 [VERIFIED]
try:
    import wmi as _wmi_module  # type: ignore[import-untyped]
    _WMI_AVAILABLE = True
except ImportError:
    _wmi_module = None  # type: ignore[assignment]
    _WMI_AVAILABLE = False
```

### Verified Pattern: AuditReport field with None default
```python
# Source: models.py AuditReport — existing pattern [VERIFIED: lines 65–70]
os_version: str | None = None
os_build: str | None = None
serial_number: str | None = None
# New fields follow same pattern:
uptime_seconds: int | None = None
pending_updates: int | None = None
```

### Verified Pattern: threshold constants in health_checks.py
```python
# Source: health_checks.py lines 12–13 [VERIFIED]
OS_WARN_BUILD: int = 22000
DISK_WARN_PCT: float = 0.15
# New constants follow same pattern:
UPTIME_WARN_DAYS: int = 7
UPTIME_STALE_DAYS: int = 30
```

### Verified Pattern: psutil.boot_time() works on this machine
```python
# Confirmed working: [VERIFIED: python -c "import psutil, time; print(int(time.time() - psutil.boot_time()))"]
# Output: 520948 (seconds — ~6 days uptime)
uptime_seconds = int(time.time() - psutil.boot_time())
```

### Verified Pattern: existing warning badge in template
```html
<!-- Source: character_sheet.html lines 509–511 [VERIFIED] -->
<span class="badge {% if w.severity == 'WARN' %}badge-warn{% else %}badge-installed{% endif %}">
  {% if w.severity == 'WARN' %}&#9888; WARN{% else %}&#10003; OK{% endif %}
</span>
```

### Verified Pattern: stat-grid row structure
```html
<!-- Source: character_sheet.html lines 394–395 [VERIFIED] -->
<div class="stat-label">CPU</div>
<div class="stat-value{% if not cpu_model %} muted{% endif %}">{{ cpu_model | default('—', true) }}</div>
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| WMI Win32_QuickFixEngineering for update queries | WUA COM `Microsoft.Update.Session` | WMI path is read-only and deprecated; WUA is the correct API |
| Hardcoded warning color in badge CSS class | `level` field drives color variant | Supports multi-level severity without adding new warning types |

**Deprecated/outdated:**
- `Win32_Product`: Prohibited in this codebase (MSI reconfiguration side effect). Never use for any purpose.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | WUA COM search criteria `"IsInstalled=0 and Type='Software'"` returns the correct pending update count | Code Examples — Pattern 3 | Wrong count displayed in stat block; IT-level impact, not crash |
| A2 | `pywintypes.com_error` is caught by bare `except Exception` when standard user calls WUA COM | Pitfall 3 | Standard user run crashes instead of showing N/A — critical |
| A3 | `result.Updates.Count` is the correct attribute to read after `searcher.Search()` | Code Examples — Pattern 3 | AttributeError at runtime when running as SYSTEM; fallback to None via except |

Both A2 and A3 are [ASSUMED] — win32com is not installed in this dev environment and cannot be live-tested. The CONTEXT.md note confirms COM access is verified by IT in SYSTEM context before phase closes.

---

## Open Questions

1. **win32com not installed in current dev venv**
   - What we know: `pip show pywin32` returns "not found"; psutil 7.2.2 is present
   - What's unclear: Whether CI runs against a fresh venv install that will need `requirements.txt` updated
   - Recommendation: Add `pywin32==311` to `requirements.txt` as the first task; CI will pick it up on next install

2. **Mac: does psutil.boot_time() work reliably under macOS?**
   - What we know: psutil documents `boot_time()` as cross-platform [VERIFIED: psutil available on this machine]
   - What's unclear: Whether there is any privilege restriction on macOS (unlikely)
   - Recommendation: [ASSUMED] No restriction. If collection fails, the `try/except` catches it and `uptime_seconds` stays `None`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| psutil | Uptime collection | Yes | 7.2.2 [VERIFIED] | — |
| pywin32 (win32com) | WUA pending update collection | No — not installed [VERIFIED: pip show pywin32 = not found] | — | `_WIN32COM_AVAILABLE=False` guard; `pending_updates=None`; CI tests use this path |
| wmi | Existing CPU/serial collectors | No (CI guard in place) [VERIFIED: pip show wmi = not found] | — | `_WMI_AVAILABLE=False` guard already active |
| Python 3.12 | Runtime | Yes [VERIFIED: project stack] | 3.12 | — |

**Missing dependencies with no fallback:**
- None — pywin32 absence is fully handled by `_WIN32COM_AVAILABLE` guard. All new code paths degrade cleanly without it.

**Missing dependencies with fallback:**
- `pywin32==311` — not in dev venv. Must be added to `requirements.txt` and installed before live SYSTEM-context testing. CI tests use the `_WIN32COM_AVAILABLE=False` path only.

---

## Sources

### Primary (HIGH confidence)
- `models.py` (working tree) — current `Warning` and `AuditReport` field order and defaults [VERIFIED]
- `health_checks.py` (working tree) — current threshold constants pattern, 3-object return, private helper shape [VERIFIED]
- `collectors/windows/hardware.py` (working tree) — `_WMI_AVAILABLE` guard pattern, psutil imports, module structure [VERIFIED]
- `collectors/mac/hardware.py` (working tree) — Mac collector structure, psutil imports [VERIFIED]
- `collectors/__init__.py` (working tree) — `collect_all()` dispatch pattern [VERIFIED]
- `renderer/__init__.py` (working tree) — `_build_context()` None handling, `has_warnings` computation [VERIFIED]
- `renderer/templates/character_sheet.html` (working tree) — stat-grid row pattern, warning badge markup, `--red` CSS variable [VERIFIED]
- `tests/test_health_checks.py` (working tree) — existing tests that must continue to pass (SC5) [VERIFIED]
- `tests/test_hardware_collector.py` (working tree) — `_WIN32COM_AVAILABLE` test patching pattern [VERIFIED]
- `scry.spec` (working tree) — current `hiddenimports`, `win32com_hidden` collect_submodules [VERIFIED]
- `requirements.txt` (working tree) — current deps; `pywin32` absent [VERIFIED]
- `.planning/phases/13-system-health-collectors/13-CONTEXT.md` — all locked decisions [VERIFIED]
- `.planning/REQUIREMENTS.md` — HEALTH-01, HEALTH-02, WARN-04, WARN-05; implementation notes [VERIFIED]
- 203 tests passing before phase starts [VERIFIED: pytest run]

### Tertiary (LOW confidence — ASSUMED)
- WUA COM search criteria string and `.Updates.Count` attribute — standard Windows Update Agent API usage, not verified against live COM session

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in working tree; pywin32 version locked in CONTEXT.md
- Architecture: HIGH — all patterns read directly from current source files
- Pitfalls: HIGH (structural) / MEDIUM (WUA COM behavior) — Pitfalls 1–2 and 4–7 from verified code; Pitfalls 3 relies on Windows COM error behavior (assumed)
- Test impact: HIGH — existing test file read; exact line numbers of tests that need updating confirmed

**Research date:** 2026-05-18
**Valid until:** 2026-06-18 (stable stack; pywin32 API is long-stable)
