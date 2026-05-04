# Phase 3: HTML Character Sheet Renderer - Pattern Map

**Mapped:** 2026-05-04
**Files analyzed:** 5 new/modified files
**Analogs found:** 4 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `renderer/__init__.py` | service | transform (dataclass → HTML string) | `collectors/windows/hardware.py` | role-match (service with clear public function, private helpers, graceful degradation) |
| `renderer/templates/character_sheet.html` | template | transform (context dict → rendered HTML) | none in codebase | no analog — use RESEARCH.md patterns |
| `writers/__init__.py` | utility | file-I/O (write str to Path) | `collectors/__init__.py` | partial (thin orchestration `__init__` that exposes single public function) |
| `tests/test_renderer.py` | test | request-response (call function, assert output) | `tests/test_hardware_collector.py` | exact (same project, same pytest + unittest.mock structure, same make_report factory pattern) |
| `requirements.txt` (new) | config | n/a | `requirements-dev.txt` | role-match (same pip pinning style) |

---

## Pattern Assignments

### `renderer/__init__.py` (service, transform)

**Analog:** `collectors/windows/hardware.py`

**Why this analog:** Both are service modules with:
- A single public function that is the documented entry point for other layers
- Multiple private `_helper()` functions that do the real work
- Graceful degradation — never raise across layer boundaries
- Module-level imports that may need guarding (wmi in hardware; importlib.resources in renderer)
- Mutation or transformation of a project dataclass (`AuditReport`)

**Imports pattern** (`collectors/windows/hardware.py` lines 1–13):
```python
"""Windows hardware and profile collectors.
Implements COLL-02 (hardware stats) and COLL-03 (local user profiles).
Both functions mutate AuditReport in place and never raise (D-01, D-02).
"""
from __future__ import annotations

import os
import platform
import winreg

import psutil

from models import AuditReport
```

**renderer/__init__.py imports to write** (copy this pattern, adapt stdlib imports):
```python
"""HTML character sheet renderer. Phase 3.
render_report(report, output_path) is the single public entry point.
Never raises — D-12/D-13 None fields are handled before template render.
"""
from __future__ import annotations

import importlib.resources as ir
from pathlib import Path

from jinja2 import Environment

from models import AuditReport
from writers import write_html
```

**Public function signature pattern** (`collectors/windows/hardware.py` lines 38–47):
```python
def collect_hardware(report: AuditReport) -> None:
    """Populate hardware fields on *report* in place.

    Calls four private helpers in order. No exception propagates out of this
    function under any circumstances (D-01, D-02).
    """
    _collect_os(report)
    _collect_cpu_model(report)
    _collect_memory_and_disk(report)
    _collect_current_user(report)
```

**renderer/__init__.py public function to write** (same structure, adapted signature from D-16):
```python
def render_report(report: AuditReport, output_path: Path) -> Path:
    """Render AuditReport to HTML character sheet and write to output_path.

    Returns the full path of the written file.
    Caller resolves output_path from Path(sys.executable).parent — D-16.
    Never raises on None hardware fields — all None values pre-processed in
    _build_context() before template render (D-12, D-13).
    """
    template_source = _load_template_source()
    env = Environment(autoescape=True)
    template = env.from_string(template_source)
    ctx = _build_context(report)
    html = template.render(**ctx)
    return write_html(html, output_path)
```

**Private helper pattern** (`collectors/windows/hardware.py` lines 66–73 and 96–111):
```python
def _collect_os(report: AuditReport) -> None:
    """Populate os_version and os_build from platform stdlib.

    platform.release() / platform.version() never fail on Windows Python 3.12.
    No try/except needed (D-07).
    """
    report.os_version = platform.release()
    report.os_build = platform.version()

def _collect_memory_and_disk(report: AuditReport) -> None:
    """Populate ram_gb, disk_total_gb, disk_free_gb via psutil (D-05).

    Disk is wrapped because unusual configurations can cause FileNotFoundError.
    """
    report.ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    try:
        disk = psutil.disk_usage("C:\\")
        report.disk_total_gb = round(disk.total / (1024 ** 3), 1)
        report.disk_free_gb = round(disk.free / (1024 ** 3), 1)
    except Exception as exc:
        report.collection_errors.append(f"Disk usage collection failed: {exc}")
```

**renderer/__init__.py private helpers to write** (one helper per concern, same docstring style):
```python
def _load_template_source() -> str:
    """Load Jinja2 template source via importlib.resources (D-15, PyInstaller-safe).

    ir.files('renderer').joinpath() works in --onedir bundles where templates
    stay as real files on disk. Do NOT use jinja2.PackageLoader — it fails in
    frozen environments (RESEARCH.md Pitfall 1).
    """
    return (
        ir.files('renderer')
        .joinpath('templates/character_sheet.html')
        .read_text(encoding='utf-8')
    )


def _build_context(report: AuditReport) -> dict:
    """Build Jinja2 template context from AuditReport. All None handling here.

    Pre-computes all derived values (disk pct, hp_class, guild, quest status)
    so the template stays logic-free. None fields become None in the dict;
    the template's {{ value | default('—') }} filter handles display (D-12).
    """
    ph = report.parsed_hostname

    # Guild — D-03: warehouse=department, laptop=company_code, both None -> None -> '—'
    guild = ph.department or ph.company_code

    # Disk HP bar — D-07, D-13: falsy guard catches both None and 0.0
    if report.disk_total_gb and report.disk_free_gb is not None:
        pct = (report.disk_free_gb / report.disk_total_gb) * 100
        hp_class = 'hp-green' if pct > 50 else ('hp-amber' if pct > 20 else 'hp-red')
    else:
        pct = 100.0
        hp_class = 'hp-none'

    # RAM display — D-06
    ram_display = f'{report.ram_gb:.1f} GB' if report.ram_gb is not None else None

    # Disk total display — D-06
    disk_total_display = (
        f'{int(report.disk_total_gb)} GB total'
        if report.disk_total_gb is not None else None
    )
    disk_label = (
        f'{report.disk_free_gb:.0f} GB free / {report.disk_total_gb:.0f} GB total'
        if report.disk_total_gb and report.disk_free_gb is not None else None
    )

    # OS combined — UI-SPEC Stat Block table
    if report.os_version and report.os_build:
        os_combined = f'{report.os_version} — Build {report.os_build}'
    else:
        os_combined = report.os_version  # may be None -> template renders '—'

    # Quest status — D-11
    missing = [app for app in report.apps if not app.installed]

    return {
        'hostname': report.hostname,
        'device_type': ph.device_type,
        'city': ph.city,
        'guild': guild,
        'station': ph.station,
        'cpu_model': report.cpu_model,
        'ram_display': ram_display,
        'disk_total_display': disk_total_display,
        'disk_pct': round(pct, 1),
        'hp_class': hp_class,
        'disk_label': disk_label,
        'os_combined': os_combined,
        'current_user': report.current_user,
        'apps': report.apps,
        'quest_complete': len(missing) == 0,
        'missing_count': len(missing),
        'timestamp': report.timestamp,
    }
```

---

### `writers/__init__.py` (utility, file-I/O)

**Analog:** `collectors/__init__.py`

**Why this analog:** Both are thin package `__init__.py` files that expose exactly one public function with a clear docstring. `collectors/__init__.py` is the closest pattern for a small orchestration module — minimal imports, one entry-point function, deferred implementation imports if needed.

**Analog full content** (`collectors/__init__.py` lines 1–18):
```python
"""Collector orchestration. Selects platform implementation.
Phase 2: Windows implementation only. Mac stubs reserved for v2.
collect_all(report) is the single entry point called by main.py (Phase 3 wiring).
"""
from __future__ import annotations
from models import AuditReport


def collect_all(report: AuditReport) -> None:
    """Run all collectors in order. Mutates report in place. Never raises.

    Calls collect_hardware first (OS, CPU, RAM, disk, current user),
    then collect_profiles (local user profiles from registry).
    Both functions degrade gracefully — collection_errors accumulates failures.
    """
    from collectors.windows.hardware import collect_hardware, collect_profiles
    collect_hardware(report)
    collect_profiles(report)
```

**writers/__init__.py to write** (same pattern — module docstring, one public function, pathlib convention):
```python
"""File writer — writes rendered HTML to flash drive output path.
write_html(html, output_path) is the single entry point (D-17).
"""
from __future__ import annotations

from pathlib import Path


def write_html(html: str, output_path: Path) -> Path:
    """Write HTML string to output_path / 'status_report.html'. Returns full path.

    Uses pathlib.Path.write_text (project convention).
    Caller (renderer/__init__.py) is responsible for resolving output_path
    from Path(sys.executable).parent — D-16.
    """
    dest = output_path / 'status_report.html'
    dest.write_text(html, encoding='utf-8')
    return dest
```

---

### `tests/test_renderer.py` (test, request-response)

**Analog:** `tests/test_hardware_collector.py`

**Why this analog:** Exact same project, same pytest version, same testing patterns:
- Module docstring noting phase and RED/GREEN status
- `make_report()` factory function returning a fresh `AuditReport`
- `from __future__ import annotations` at top
- `unittest.mock.patch` / `patch.object` for isolation
- Grouped test functions under `# -----` section comment banners
- `pytest.fail()` for no-raise guarantees
- Direct `from module import function` inside each test (not at module level)

**Module header pattern** (`tests/test_hardware_collector.py` lines 1–17):
```python
"""Unit tests for collectors.windows.hardware — collect_hardware function.
RED phase: These tests fail before implementation exists.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))
```

**tests/test_renderer.py header to write** (copy pattern, adjust imports and docstring):
```python
"""Unit tests for renderer — render_report function and helpers.
RED phase: Tests written against the public interface before full implementation.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

import pytest

from models import AuditReport, ParsedHostname, AppStatus
from parsers.name_parser import parse_hostname
```

**Mock data factory pattern** (from `tests/test_hardware_collector.py` lines 16–17, extended for renderer):
```python
# Minimal make_report — used for tests that only need AuditReport structure
def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))
```

**Full mock AuditReport** (from RESEARCH.md Pattern 4, D-10 — used for renderer integration tests):
```python
# MOCK_REPORT exercises: both badge states, service_state, Quest Incomplete path,
# None field degradation. All 11 required apps.
MOCK_REPORT = AuditReport(
    hostname='PHX-INV-003',
    parsed_hostname=parse_hostname('PHX-INV-003'),
    os_version='Windows 10 Pro',
    os_build='19045',
    cpu_model='Intel Core i7-10700',
    ram_gb=16.0,
    disk_total_gb=476.0,
    disk_free_gb=38.0,   # ~8% free -> hp-red
    current_user='jsmith',
    local_profiles=['C:\\Users\\jsmith', 'C:\\Users\\admin'],
    apps=[
        AppStatus('NinjaOne', installed=True, version='5.8.1234'),
        AppStatus('CrowdStrike Falcon', installed=True, version='7.14.17608', service_state='Running'),
        AppStatus('MERP', installed=False),
        AppStatus('Word', installed=True, version='16.0.17628'),
        AppStatus('Excel', installed=True, version='16.0.17628'),
        AppStatus('Outlook', installed=True, version='16.0.17628'),
        AppStatus('Teams', installed=False),
        AppStatus('OneDrive', installed=True, version='24.021.0201'),
        AppStatus('Zoom', installed=False),
        AppStatus('Chrome', installed=True, version='124.0.6367.60'),
        AppStatus('Claude desktop app', installed=False),
    ],
    timestamp='2026-05-04 22:10:00',
)
```

**Section banner pattern** (`tests/test_hardware_collector.py` lines 32–34, 59–61, 121–122):
```python
# ---------------------------------------------------------------------------
# Section name
# ---------------------------------------------------------------------------
```

**No-raise guarantee pattern** (`tests/test_hardware_collector.py` lines 211–228):
```python
def test_collect_hardware_never_raises():
    """collect_hardware must not propagate any exception under any circumstances."""
    from collectors.windows.hardware import collect_hardware
    import collectors.windows.hardware as hw_mod

    # Make everything fail simultaneously
    with patch.object(hw_mod, "_WMI_AVAILABLE", True), \
         patch.object(hw_mod, "_wmi_module", create=True) as mock_mod, \
         patch.object(hw_mod, "psutil") as mock_psutil:
        mock_mod.WMI = MagicMock(side_effect=RuntimeError("WMI exploded"))
        mock_psutil.virtual_memory.return_value.total = 8 * (1024 ** 3)
        mock_psutil.disk_usage.side_effect = Exception("disk gone")

        try:
            report = make_report()
            collect_hardware(report)
        except Exception as exc:
            pytest.fail(f"collect_hardware raised an exception: {exc}")
```

**tests/test_renderer.py test groups to model** (adapt from test_hardware_collector.py section structure):

```
# ---------------------------------------------------------------------------
# _load_template_source — importlib.resources path
# ---------------------------------------------------------------------------
# test: template file loads without error
# test: returns a non-empty string
# test: returned string contains expected HTML landmarks

# ---------------------------------------------------------------------------
# _build_context — None field handling (D-12, D-13)
# ---------------------------------------------------------------------------
# test: all None hardware fields produce None values in context (template default filter handles display)
# test: disk_pct is 100.0 and hp_class is 'hp-none' when disk_total_gb is None
# test: disk_pct is 100.0 and hp_class is 'hp-none' when disk_total_gb is 0.0
# test: hp_class is 'hp-green' when disk >50% free
# test: hp_class is 'hp-amber' when disk 20-50% free
# test: hp_class is 'hp-red' when disk <=20% free
# test: guild = department for Warehouse Workstation
# test: guild = company_code for User-Assigned Laptop
# test: guild = None when both department and company_code are None

# ---------------------------------------------------------------------------
# _build_context — quest status (D-11)
# ---------------------------------------------------------------------------
# test: quest_complete=True and missing_count=0 when all apps installed
# test: quest_complete=False and missing_count=4 for MOCK_REPORT (4 missing apps)

# ---------------------------------------------------------------------------
# render_report — integration (writes real file)
# ---------------------------------------------------------------------------
# test: render_report with MOCK_REPORT writes status_report.html to output_path
# test: returned Path points to existing file
# test: HTML contains hostname PHX-INV-003
# test: HTML contains '✓' for installed apps and '✗' for missing apps
# test: HTML contains 'QUEST INCOMPLETE' (MOCK_REPORT has 4 missing apps)
# test: None cpu_model renders em-dash, not 'None' string

# ---------------------------------------------------------------------------
# write_html (writers/__init__.py)
# ---------------------------------------------------------------------------
# test: creates status_report.html in the given directory
# test: file contents match the html argument exactly

# ---------------------------------------------------------------------------
# No-raise guarantee
# ---------------------------------------------------------------------------
# test: render_report with all-None AuditReport does not raise
```

**tempfile isolation pattern for file-write tests** (new — no existing analog, use stdlib):
```python
def test_render_report_writes_file():
    """render_report writes status_report.html to output_path."""
    from renderer import render_report

    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        assert out.exists()
        assert out.name == 'status_report.html'
```

---

### `renderer/templates/character_sheet.html` (template, transform)

**Analog:** None in codebase — no existing Jinja2 templates.

**Source:** Use RESEARCH.md Pattern 3 + UI-SPEC component specs exclusively.

Key conventions locked by UI-SPEC and RESEARCH.md:
- All styles in a single `<style>` block — no `<link>`, no inline `style=""` except HP bar fill width
- CSS custom properties (`--bg-dominant`, `--green`, etc.) from UI-SPEC Color table
- `{{ value | default('—') }}` for all nullable fields (D-12)
- CSS classes `hp-green` / `hp-amber` / `hp-red` / `hp-none` on the HP fill div
- CSS `:nth-child(even)` for zebra stripe — zero Python, pure CSS (RESEARCH.md "Don't Hand-Roll" table)
- `autoescape=True` on the Environment means `<` in cpu_model is auto-escaped — template author does nothing extra
- `<title>Status Report — {{ hostname }}</title>`
- Layout: `<body>` → `<div class="sheet">` → header / stat-block / equipment / quest-status / chronicle divs

---

### `requirements.txt` (config, n/a)

**Analog:** `requirements-dev.txt`

**Analog full content** (`requirements-dev.txt` lines 1):
```
pytest==8.*
```

**requirements.txt to write** (same major-version pin style):
```
jinja2==3.1.6
psutil==6.*
wmi==1.5.1
```

Note: `requirements-dev.txt` already exists for dev-only deps (pytest). A separate `requirements.txt` for runtime deps follows the same single-dependency-per-line, pinned-version convention.

---

## Shared Patterns

### No-Raise / Graceful Degradation
**Source:** `collectors/windows/hardware.py` (entire file) + `collectors/__init__.py`
**Apply to:** `renderer/__init__.py`

The project rule (CLAUDE.md, Phase 1 rule) is: never raise across layer boundaries. In `hardware.py` this means each `_collect_*` helper wraps risky calls in try/except and appends to `collection_errors`. In the renderer, all None fields must be pre-processed in `_build_context()` before the template is called — the template should never receive a value that could cause a Jinja2 error. The `autoescape=True` Environment handles XSS; the `| default('—')` filter handles None display.

```python
# Pattern from hardware.py lines 96-111: isolate risky operation, log error, degrade
def _collect_memory_and_disk(report: AuditReport) -> None:
    report.ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    try:
        disk = psutil.disk_usage("C:\\")
        report.disk_total_gb = round(disk.total / (1024 ** 3), 1)
        report.disk_free_gb = round(disk.free / (1024 ** 3), 1)
    except Exception as exc:
        report.collection_errors.append(f"Disk usage collection failed: {exc}")
```

### Module Docstring Convention
**Source:** `collectors/windows/hardware.py` line 1–3, `collectors/__init__.py` lines 1–3, `parsers/name_parser.py` lines 1–3
**Apply to:** `renderer/__init__.py`, `writers/__init__.py`

All project modules open with a triple-quoted docstring that states: what the module does, what the public entry point is, and which decisions/rules govern it. No blank line between `"""` opening and first sentence.

```python
"""Hostname parser — decodes Master Electronics naming convention to ParsedHostname.

Decision rules D-01 through D-09 from 01-CONTEXT.md govern all disambiguation.
Anti-pattern: never check seg3.isdigit() before checking seg2 in P3_CODES (Pitfall 1).
"""
```

### `from __future__ import annotations`
**Source:** Every `.py` file in `collectors/` and `tests/`
**Apply to:** `renderer/__init__.py`, `writers/__init__.py`, `tests/test_renderer.py`

All project modules use `from __future__ import annotations` as the first import line (after the module docstring). This is non-negotiable project style — copy it.

### pytest Import Style (Deferred / Local Imports in Tests)
**Source:** `tests/test_hardware_collector.py` throughout
**Apply to:** `tests/test_renderer.py`

Test functions import the module under test inside the function body (`from renderer import render_report`), not at module level. This isolates import errors to specific tests and makes patching cleaner.

```python
# From test_hardware_collector.py lines 35-40:
def test_collect_hardware_populates_os_version():
    """os_version is a non-empty string after collect_hardware."""
    from collectors.windows.hardware import collect_hardware  # local import

    report = make_report()
    collect_hardware(report)

    assert report.os_version is not None
```

### pathlib.Path for All File I/O
**Source:** `collectors/windows/hardware.py` (uses `Path` via psutil), CLAUDE.md ("derive output path from `Path(sys.executable).parent`")
**Apply to:** `writers/__init__.py`, `tests/test_renderer.py`

All file paths are `pathlib.Path` objects. No `os.path`, no `open(str_path)`. Use `path.write_text(content, encoding='utf-8')`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `renderer/templates/character_sheet.html` | template | transform | No existing Jinja2 templates in the codebase. Use RESEARCH.md Pattern 3 and 03-UI-SPEC.md component specs as the full specification. |

---

## Metadata

**Analog search scope:** `collectors/`, `parsers/`, `tests/`, `writers/`, `renderer/`, root-level `.py` and `.txt` files
**Files scanned:** 13 project files (excluding `.venv/`)
**Pattern extraction date:** 2026-05-04
