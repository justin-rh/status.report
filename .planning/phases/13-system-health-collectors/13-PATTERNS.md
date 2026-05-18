# Phase 13: System Health Collectors - Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 11
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `models.py` | model | transform | `models.py` (existing Warning/AuditReport dataclasses) | exact — field addition |
| `health_checks.py` | service | transform | `health_checks.py` (existing `_check_disk_space`) | exact — same module, same helper shape |
| `collectors/windows/hardware.py` | collector | request-response | `collectors/windows/hardware.py` (existing `_WMI_AVAILABLE` guard + psutil helpers) | exact — same module, same guard pattern |
| `collectors/mac/hardware.py` | collector | request-response | `collectors/mac/hardware.py` (existing `_PWD_AVAILABLE` guard + psutil helpers) | exact — same module, parallel Windows pattern |
| `collectors/__init__.py` | orchestrator | request-response | `collectors/__init__.py` (existing `collect_all` Windows/Mac dispatch) | exact — same module |
| `renderer/__init__.py` | renderer | transform | `renderer/__init__.py` (existing `_build_context` derived values) | exact — same module |
| `renderer/templates/character_sheet.html` | template | transform | `renderer/templates/character_sheet.html` (existing stat-grid rows + badge pattern) | exact — same file |
| `requirements.txt` | config | — | `requirements.txt` (existing `jinja2==3.1.6` line) | exact — pinned version pattern |
| `scry.spec` | config | — | `scry.spec` (existing `hiddenimports` list, lines 32–43) | exact — same list |
| `tests/test_health_checks.py` | test | transform | `tests/test_health_checks.py` (existing parametrize + make_report pattern) | exact — same file |
| `tests/test_hardware_collector.py` | test | request-response | `tests/test_hardware_collector.py` (existing `patch.object(hw_mod, "_WMI_AVAILABLE", ...)` pattern) | exact — same file |

---

## Pattern Assignments

### `models.py` — add `level` field to Warning; add `uptime_seconds`/`pending_updates` to AuditReport

**Analog:** `models.py` (self — field extension)

**Warning dataclass — current shape** (lines 50–57):
```python
@dataclass
class Warning:
    """A single health check result produced by evaluate_warnings()."""
    code: str           # Short identifier: 'OS_VERSION' | 'DISK_SPACE'
    severity: str       # 'OK' or 'WARN' — plain str per D-03
    message: str        # Human-readable one-line summary
    detail: str | None = None  # Extended info or skip reason; None when not needed
```

**Add `level` as the LAST field** — appended after `detail` to preserve positional construction compatibility:
```python
    detail: str | None = None  # Extended info or skip reason; None when not needed
    level: str | None = None   # NEW: 'yellow' | 'red' | None (D-01)
```

**AuditReport — existing None-default scalar pattern** (lines 64–72):
```python
    os_version: str | None = None
    os_build: str | None = None
    serial_number: str | None = None
    cpu_model: str | None = None
    ram_gb: float | None = None
    disk_total_gb: float | None = None
    disk_free_gb: float | None = None
    current_user: str | None = None
```

**Add two new fields using the same pattern** after the existing hardware fields (after `current_user`):
```python
    uptime_seconds: int | None = None    # NEW: D-04 / D-05
    pending_updates: int | None = None   # NEW: D-04 / D-08; None when inaccessible
```

**Critical placement rule:** `level` must be last field in Warning — any position before `detail` will silently corrupt the 22 existing tests that construct `Warning(code, severity, message, detail_value)` by position.

---

### `health_checks.py` — add constants, `_check_uptime()`, extend `evaluate_warnings()`

**Analog:** `health_checks.py` (self)

**Threshold constants pattern** (lines 12–13 — copy style exactly):
```python
OS_WARN_BUILD: int = 22000
DISK_WARN_PCT: float = 0.15
```
Add immediately after these two lines:
```python
UPTIME_WARN_DAYS: int = 7
UPTIME_STALE_DAYS: int = 30
```

**Private helper shape — copy from `_check_disk_space`** (lines 71–104):
```python
def _check_disk_space(report: AuditReport) -> Warning:
    """Return DISK_SPACE Warning. WARN when free/total <= DISK_WARN_PCT (0.15)."""
    free = report.disk_free_gb
    total = report.disk_total_gb
    if free is None or total is None:
        return Warning(
            code='DISK_SPACE',
            severity='OK',
            message='Disk space check skipped',
            detail='disk_free_gb or disk_total_gb not collected',
        )
    ...
    if pct_free <= DISK_WARN_PCT:
        return Warning(
            code='DISK_SPACE',
            severity='WARN',
            message='Low disk space',
            detail=f'{free:.1f} GB free of {total:.1f} GB ({free_pct_display}% free)',
        )
    return Warning(
        code='DISK_SPACE',
        severity='OK',
        message='Disk space is adequate',
        detail=f'{free:.1f} GB free of {total:.1f} GB ({free_pct_display}% free)',
    )
```

**New `_check_uptime()` — escalating check, same structural shape:**
```python
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

**`evaluate_warnings()` — extend return list from 3 to 4** (current lines 27–31):
```python
    return [
        _check_os_version(report),
        _check_disk_space(report),
        _check_rename(report),
    ]
```
Change to:
```python
    return [
        _check_os_version(report),
        _check_disk_space(report),
        _check_rename(report),
        _check_uptime(report),
    ]
```
Also update the module docstring "exactly three" → "exactly four" and the D-06 inline comment to reflect 4 objects.

---

### `collectors/windows/hardware.py` — add `_WIN32COM_AVAILABLE` guard, `_collect_uptime()`, `collect_pending_updates()`

**Analog:** `collectors/windows/hardware.py` (self)

**`_WMI_AVAILABLE` guard — copy exactly** (lines 19–24):
```python
try:
    import wmi as _wmi_module  # type: ignore[import-untyped]
    _WMI_AVAILABLE = True
except ImportError:
    _wmi_module = None  # type: ignore[assignment]
    _WMI_AVAILABLE = False
```
Add immediately after this block:
```python
try:
    import win32com.client as _win32com_client  # type: ignore[import-untyped]
    _WIN32COM_AVAILABLE = True
except ImportError:
    _win32com_client = None  # type: ignore[assignment]
    _WIN32COM_AVAILABLE = False
```

**`collect_hardware()` dispatch pattern** (lines 42–52) — the function that calls private helpers in order:
```python
def collect_hardware(report: AuditReport) -> None:
    """Populate hardware fields on *report* in place.

    Calls five private helpers in order. No exception propagates out of this
    function under any circumstances (D-01, D-02).
    """
    _collect_os(report)
    _collect_cpu_model(report)
    _collect_memory_and_disk(report)
    _collect_current_user(report)
    _collect_serial_number(report)
```
Add `_collect_uptime(report)` call at the end of this sequence.

**`_collect_memory_and_disk` error pattern — copy for `_collect_uptime`** (lines 152–167):
```python
def _collect_memory_and_disk(report: AuditReport) -> None:
    # RAM — always works at standard user privilege
    report.ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    # Disk — target C:\ primary volume
    try:
        disk = psutil.disk_usage("C:\\")
        report.disk_total_gb = round(disk.total / (1024 ** 3), 1)
        report.disk_free_gb = round(disk.free / (1024 ** 3), 1)
    except Exception as exc:
        report.collection_errors.append(f"Disk usage collection failed: {exc}")
```

**New `_collect_uptime()` — mirrors the try/except + collection_errors pattern:**
```python
def _collect_uptime(report: AuditReport) -> None:
    """Populate uptime_seconds via psutil.boot_time(). Never raises."""
    try:
        report.uptime_seconds = int(time.time() - psutil.boot_time())
    except Exception as exc:
        report.collection_errors.append(f"Uptime collection failed: {exc}")
```
Note: `import time` must be added to the module-level imports (currently not imported in windows/hardware.py). Check with `Grep("^import time", ...)` before adding.

**`_collect_serial_number` guard pattern — copy for `collect_pending_updates`** (lines 129–149):
```python
def _collect_serial_number(report: AuditReport) -> None:
    if not _WMI_AVAILABLE:
        return
    try:
        c = _wmi_module.WMI()
        ...
    except Exception as exc:
        report.collection_errors.append(
            f"Serial number collection failed (WMI): {exc}"
        )
```

**New `collect_pending_updates()` — public function, same guard + try/except shape:**
```python
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
```

---

### `collectors/mac/hardware.py` — add `_collect_uptime()` only

**Analog:** `collectors/mac/hardware.py` (self)

**`_pwd_module` guard — structural reference** (lines 21–26):
```python
try:
    import pwd as _pwd_module
    _PWD_AVAILABLE = True
except ImportError:
    _pwd_module = None  # type: ignore[assignment]
    _PWD_AVAILABLE = False
```
No new guard needed. `_collect_uptime()` uses only `psutil` and `time`, already available.

**`collect_hardware()` dispatch** (lines 33–43):
```python
def collect_hardware(report: AuditReport) -> None:
    _collect_os(report)
    _collect_cpu_model(report)
    _collect_memory_and_disk(report)
    _collect_current_user(report)
```
Add `_collect_uptime(report)` at end of sequence (identical call site pattern to Windows version).

**`_collect_memory_and_disk` error pattern** (lines 127–142) — same try/except + collection_errors pattern as Windows. Copy for `_collect_uptime()`:
```python
def _collect_uptime(report: AuditReport) -> None:
    """Populate uptime_seconds via psutil.boot_time(). Never raises."""
    try:
        report.uptime_seconds = int(time.time() - psutil.boot_time())
    except Exception as exc:
        report.collection_errors.append(f"Uptime collection failed: {exc}")
```
`psutil` is already imported at line 12. Add `import time` to the module imports.

---

### `collectors/__init__.py` — wire `collect_pending_updates()` on Windows path

**Analog:** `collectors/__init__.py` (self)

**Current `collect_all()` dispatch** (lines 9–27):
```python
def collect_all(report: AuditReport) -> None:
    import sys
    if sys.platform == "darwin":
        from collectors.mac.hardware import collect_hardware, collect_profiles
        from collectors.mac.apps import collect_apps
    else:
        from collectors.windows.hardware import collect_hardware, collect_profiles
        from collectors.windows.apps import collect_apps
    collect_hardware(report)
    collect_profiles(report)
    collect_apps(report)
```

**Pattern: add `collect_pending_updates` to the Windows import and call it after `collect_apps`:**
```python
def collect_all(report: AuditReport) -> None:
    import sys
    if sys.platform == "darwin":
        from collectors.mac.hardware import collect_hardware, collect_profiles
        from collectors.mac.apps import collect_apps
        collect_hardware(report)
        collect_profiles(report)
        collect_apps(report)
    else:
        from collectors.windows.hardware import collect_hardware, collect_profiles, collect_pending_updates
        from collectors.windows.apps import collect_apps
        collect_hardware(report)
        collect_profiles(report)
        collect_apps(report)
        collect_pending_updates(report)
```
Note: `_collect_uptime()` is called inside `collect_hardware()` on both platforms — not called separately here.

---

### `renderer/__init__.py` — add `uptime_display` and `pending_updates_display` to `_build_context()`

**Analog:** `renderer/__init__.py` (self)

**Existing derived value pattern in `_build_context()`** (lines 113–128) — the "compute display string from raw field" pattern:
```python
    # RAM display — D-06
    if report.ram_gb is not None:
        nearest = _nearest_standard_ram(report.ram_gb)
        ram_display = f'{report.ram_gb:.1f} GB ({nearest} GB)'
    else:
        ram_display = None

    # Disk total display — D-06
    disk_total_display = (
        f'{int(report.disk_total_gb)} GB total'
        if report.disk_total_gb is not None else None
    )
```

**Add after existing display calculations, before the `return` dict:**
```python
    # Uptime display — D-07
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

    # Pending updates display — D-16
    pending_updates_display = (
        f"{report.pending_updates} pending"
        if report.pending_updates is not None
        else "N/A"
    )
```

**Existing `return` dict pattern** (lines 146–169) — add new keys using the same structure:
```python
        'uptime_display': uptime_display,
        'pending_updates_display': pending_updates_display,
```

---

### `renderer/templates/character_sheet.html` — add System Health stat block + update warning badge

**Analog:** `renderer/templates/character_sheet.html` (self)

**Existing stat-grid row pattern** (lines 394–419) — copy the `serial_number` / `current_user` style exactly:
```html
        <div class="stat-label">Serial Number</div>
        <div class="stat-value{% if serial_number is none %} muted{% endif %}">{{ serial_number | default('—', true) }}</div>

        <div class="stat-label">Current User</div>
        <div class="stat-value{% if not current_user %} muted{% endif %}">{{ current_user | default('—', true) }}</div>
```

**New System Health rows — insert after line 419 (after the "Other Profiles" row), before `</div>` on line 421:**
```html
        <!-- System Health — Phase 13 -->
        <div class="stat-label">Uptime</div>
        <div class="stat-value{% if uptime_display is none %} muted{% endif %}">{{ uptime_display | default('—', true) }}</div>

        <div class="stat-label">Pending Updates</div>
        <div class="stat-value">{{ pending_updates_display }}</div>
```

**Existing warning badge** (lines 509–511):
```html
            <span class="badge {% if w.severity == 'WARN' %}badge-warn{% else %}badge-installed{% endif %}">
              {% if w.severity == 'WARN' %}&#9888; WARN{% else %}&#10003; OK{% endif %}
            </span>
```

**Updated badge — `w.level` drives CSS class variant (D-03):**
```html
            <span class="badge {% if w.severity == 'WARN' %}{% if w.level == 'red' %}badge-critical{% else %}badge-warn{% endif %}{% else %}badge-installed{% endif %}">
              {% if w.severity == 'WARN' %}&#9888; WARN{% else %}&#10003; OK{% endif %}
            </span>
```

**New CSS class to add after `badge-warn` on line 233:**
```css
    .badge-critical { background: var(--red); color: #fff; }
```
`--red: #ef4444` is already defined at line 18. No new CSS variable needed.

---

### `requirements.txt` — add `pywin32==311`

**Analog:** `requirements.txt` (self)

**Current file** (lines 1–3):
```
jinja2==3.1.6
psutil==6.*
wmi==1.5.1
```

**Add `pywin32==311` using the same pinned-version pattern:**
```
jinja2==3.1.6
psutil==6.*
wmi==1.5.1
pywin32==311
```

---

### `scry.spec` — add `win32timezone` to `hiddenimports`

**Analog:** `scry.spec` (self)

**Current `hiddenimports` list** (lines 32–43):
```python
    hiddenimports=[
        'wmi',
        'win32api',
        'win32con',
        'win32com',
        'win32com.client',
        'win32com.server',
        'pywintypes',
        'pythoncom',
        'win32transaction',
        'win32security',
    ] + win32com_hidden,
```

**Add `'win32timezone'` to the list** (REQUIREMENTS.md implementation note):
```python
    hiddenimports=[
        'wmi',
        'win32api',
        'win32con',
        'win32com',
        'win32com.client',
        'win32com.server',
        'pywintypes',
        'pythoncom',
        'win32transaction',
        'win32security',
        'win32timezone',
    ] + win32com_hidden,
```

---

### `tests/test_health_checks.py` — update always-N test, add uptime tests

**Analog:** `tests/test_health_checks.py` (self)

**`make_report` factory** (lines 11–14) — reuse without change:
```python
def make_report(**kwargs) -> AuditReport:
    defaults = dict(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))
    defaults.update(kwargs)
    return AuditReport(**defaults)
```

**`test_evaluate_warnings_always_returns_three` — update count** (lines 91–98):
```python
def test_evaluate_warnings_always_returns_three():
    """evaluate_warnings must always return exactly 3 Warning objects (Phase 7 D-01)."""
    report = make_report()
    warnings = evaluate_warnings(report)
    assert len(warnings) == 3, f'expected 3 warnings, got {len(warnings)}'
    assert warnings[0].code == 'OS_VERSION'
    assert warnings[1].code == 'DISK_SPACE'
    assert warnings[2].code == 'RENAME_REQUIRED'
```
Change to:
```python
def test_evaluate_warnings_always_returns_four():
    """evaluate_warnings must always return exactly 4 Warning objects (Phase 13 D-14)."""
    report = make_report()
    warnings = evaluate_warnings(report)
    assert len(warnings) == 4, f'expected 4 warnings, got {len(warnings)}'
    assert warnings[0].code == 'OS_VERSION'
    assert warnings[1].code == 'DISK_SPACE'
    assert warnings[2].code == 'RENAME_REQUIRED'
    assert warnings[3].code in ('UPTIME', 'UPTIME_WARN', 'UPTIME_STALE')
```

**`test_evaluate_warnings_never_raises` — update `assert len(result) == 3`** (line 119):
```python
        assert len(result) == 3
```
Change to:
```python
        assert len(result) == 4
```

**New uptime check parametrize — copy style of `test_os_version_check` (lines 21–37):**
```python
@pytest.mark.parametrize('uptime_seconds,expected_code,expected_severity,expected_level', [
    (None,          'UPTIME',       'OK',   None),       # collection failed
    (0,             'UPTIME',       'OK',   None),       # 0 seconds — OK
    (6 * 86400,     'UPTIME',       'OK',   None),       # 6 days — below warn threshold
    (7 * 86400,     'UPTIME',       'OK',   None),       # exactly 7 days — not yet WARN
    (7 * 86400 + 1, 'UPTIME_WARN',  'WARN', 'yellow'),  # 7 days + 1 sec — crosses warn
    (8 * 86400,     'UPTIME_WARN',  'WARN', 'yellow'),  # 8 days — warn range
    (30 * 86400,    'UPTIME_WARN',  'WARN', 'yellow'),  # exactly 30 days — not yet stale
    (31 * 86400,    'UPTIME_STALE', 'WARN', 'red'),     # 31 days — stale
])
def test_uptime_check(uptime_seconds, expected_code, expected_severity, expected_level):
    report = make_report(uptime_seconds=uptime_seconds)
    warnings = evaluate_warnings(report)
    uptime_warning = warnings[3]
    assert uptime_warning.code == expected_code
    assert uptime_warning.severity == expected_severity
    assert uptime_warning.level == expected_level
```

**Stale detail text test — copy style of `test_rename_check_warn_has_detail` (lines 147–156):**
```python
def test_uptime_stale_detail_mentions_hibernation():
    """UPTIME_STALE detail must mention hibernation time counting (REQUIREMENTS.md WARN-05)."""
    report = make_report(uptime_seconds=31 * 86400)
    warnings = evaluate_warnings(report)
    assert 'hibernation' in warnings[3].detail.lower()
```

---

### `tests/test_hardware_collector.py` — add uptime and pending_updates tests

**Analog:** `tests/test_hardware_collector.py` (self)

**`make_report` factory** (lines 16–17) — reuse without change:
```python
def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))
```

**`patch.object(hw_mod, "_WMI_AVAILABLE", ...)` guard bypass pattern** (lines 77–82 and 113):
```python
    with patch.object(hw_mod, "_wmi_module", create=True) as mock_mod:
        mock_mod.WMI = mock_wmi_cls
        with patch.object(hw_mod, "_WMI_AVAILABLE", True):
            ...

    with patch.object(hw_mod, "_WMI_AVAILABLE", False), \
         patch.object(hw_mod.winreg, "OpenKey", side_effect=OSError):
        ...
```

**New uptime tests — copy the no-raise + psutil mock pattern from `test_collect_hardware_degrades_on_disk_error` (lines 151–165):**
```python
def test_collect_uptime_populates_uptime_seconds():
    """uptime_seconds is a positive int after collect_hardware runs."""
    import collectors.windows.hardware as hw_mod
    from collectors.windows.hardware import collect_hardware

    report = make_report()
    collect_hardware(report)
    assert report.uptime_seconds is not None
    assert isinstance(report.uptime_seconds, int)
    assert report.uptime_seconds > 0


def test_collect_uptime_degrades_on_psutil_error():
    """uptime_seconds stays None and error is logged when psutil.boot_time raises."""
    import collectors.windows.hardware as hw_mod
    from collectors.windows.hardware import collect_hardware

    with patch.object(hw_mod, "psutil") as mock_psutil:
        mock_psutil.virtual_memory.return_value.total = 16 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.total = 512 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.free = 100 * (1024 ** 3)
        mock_psutil.boot_time.side_effect = Exception("boot_time unavailable")

        report = make_report()
        collect_hardware(report)

    assert report.uptime_seconds is None
    assert any("uptime" in e.lower() for e in report.collection_errors)
```

**New pending_updates tests — copy `patch.object(hw_mod, "_WMI_AVAILABLE", False)` pattern:**
```python
def test_collect_pending_updates_skipped_when_win32com_unavailable():
    """pending_updates stays None when _WIN32COM_AVAILABLE is False (CI path)."""
    import collectors.windows.hardware as hw_mod
    from collectors.windows.hardware import collect_pending_updates

    with patch.object(hw_mod, "_WIN32COM_AVAILABLE", False):
        report = make_report()
        collect_pending_updates(report)

    assert report.pending_updates is None
    assert report.collection_errors == []


def test_collect_pending_updates_populates_count_when_com_available():
    """pending_updates is populated with integer count from WUA COM mock."""
    import collectors.windows.hardware as hw_mod
    from collectors.windows.hardware import collect_pending_updates

    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_searcher = MagicMock()
    mock_result = MagicMock()
    mock_result.Updates.Count = 3
    mock_searcher.Search.return_value = mock_result
    mock_session.CreateUpdateSearcher.return_value = mock_searcher
    mock_client.Dispatch.return_value = mock_session

    with patch.object(hw_mod, "_WIN32COM_AVAILABLE", True), \
         patch.object(hw_mod, "_win32com_client", mock_client):
        report = make_report()
        collect_pending_updates(report)

    assert report.pending_updates == 3


def test_collect_pending_updates_degrades_on_com_error():
    """pending_updates stays None and error is logged when COM raises (standard user)."""
    import collectors.windows.hardware as hw_mod
    from collectors.windows.hardware import collect_pending_updates

    mock_client = MagicMock()
    mock_client.Dispatch.side_effect = Exception("Access denied (standard user)")

    with patch.object(hw_mod, "_WIN32COM_AVAILABLE", True), \
         patch.object(hw_mod, "_win32com_client", mock_client):
        report = make_report()
        collect_pending_updates(report)

    assert report.pending_updates is None
    assert any("pending updates" in e.lower() for e in report.collection_errors)
```

---

## Shared Patterns

### Guard flag pattern (module-level try/except ImportError)
**Source:** `collectors/windows/hardware.py` lines 19–24
**Apply to:** The new `_WIN32COM_AVAILABLE` block in `collectors/windows/hardware.py`
```python
try:
    import wmi as _wmi_module  # type: ignore[import-untyped]
    _WMI_AVAILABLE = True
except ImportError:
    _wmi_module = None  # type: ignore[assignment]
    _WMI_AVAILABLE = False
```

### Never-raise collector pattern (try/except + collection_errors.append)
**Source:** `collectors/windows/hardware.py` lines 61–64, 109–111, 146–148, 164–167
**Apply to:** `_collect_uptime()` and `collect_pending_updates()` in both hardware modules
```python
    except Exception as exc:
        report.collection_errors.append(f"<collector name> failed: {exc}")
```

### `_build_context()` None-safe display string pattern
**Source:** `renderer/__init__.py` lines 113–128
**Apply to:** `uptime_display` and `pending_updates_display` in `_build_context()`
```python
    if report.ram_gb is not None:
        ...
        ram_display = f'...'
    else:
        ram_display = None
```

### Jinja2 `| default('—', true)` + `muted` CSS class pattern
**Source:** `renderer/templates/character_sheet.html` lines 394–419
**Apply to:** new System Health stat-grid rows
```html
<div class="stat-value{% if field is none %} muted{% endif %}">{{ field | default('—', true) }}</div>
```

### `patch.object(hw_mod, "_FLAG", ...)` test isolation pattern
**Source:** `tests/test_hardware_collector.py` lines 77–82, 113–114
**Apply to:** all new hardware collector tests that need to bypass `_WIN32COM_AVAILABLE`

### Parametrize boundary-case test pattern
**Source:** `tests/test_health_checks.py` lines 21–37 (`test_os_version_check`)
**Apply to:** `test_uptime_check` — boundary values at UPTIME_WARN_DAYS (7) and UPTIME_STALE_DAYS (30)

---

## No Analog Found

All 11 files have direct analogs in the existing codebase. No files require fallback to RESEARCH.md-only patterns.

---

## Metadata

**Analog search scope:** `collectors/`, `renderer/`, `tests/`, `models.py`, `health_checks.py`, `requirements.txt`, `scry.spec`
**Files scanned:** 11 source files read in full
**Pattern extraction date:** 2026-05-18
