# Phase 14: Vendor Update Detection - Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 7
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `models.py` | model | CRUD | `models.py` (AppStatus / Warning dataclasses) | exact |
| `collectors/windows/vendor.py` | collector | request-response | `collectors/windows/hardware.py` (`collect_pending_updates`) + `collectors/windows/apps.py` (`_search_uninstall_keys`) | exact |
| `collectors/windows/apps.py` | collector | request-response | self (read-only — `UNINSTALL_PATHS` export concern) | exact |
| `main.py` | entry-point | request-response | `main.py` lines 56–58 and 123–125 (existing `--updates` blocks) | exact |
| `renderer/__init__.py` | renderer | transform | `renderer/__init__.py` lines 159–164 (`pending_updates_display` pattern) | exact |
| `renderer/templates/character_sheet.html` | template | transform | `character_sheet.html` lines 422–429 (System Health block) | exact |
| `tests/test_vendor_collector.py` | test | request-response | `tests/test_collectors_phase13.py` + `tests/test_app_collector.py` | exact |

---

## Pattern Assignments

### `models.py` (model, CRUD)

**Analog:** `models.py` — `Warning` dataclass (lines 51–58) and `AppStatus` dataclass (lines 40–48)

**Existing dataclass style** (lines 39–58):
```python
@dataclass
class AppStatus:
    """Detection result for a single target application."""
    name: str
    installed: bool
    version: str | None = None
    service_state: str | None = None    # 'Running' | 'Stopped' | None
    detection_method: str = 'registry'  # 'registry' | 'filesystem' | 'service'
    error: str | None = None
    sub_apps: list[AppStatus] = field(default_factory=list)


@dataclass
class Warning:
    """A single health check result produced by evaluate_warnings()."""
    code: str           # Short identifier: 'OS_VERSION' | 'DISK_SPACE'
    severity: str       # 'OK' or 'WARN' — plain str per D-03
    message: str        # Human-readable one-line summary
    detail: str | None = None  # Extended info or skip reason; None when not needed
    level: str | None = None   # 'yellow' | 'red' | None — D-01 (Phase 13)
```

**New `VendorUpdateStatus` dataclass — copy this style, insert after `Warning` (line 59), before `AuditReport` (line 62):**
```python
@dataclass
class VendorUpdateStatus:
    """Detection result for a vendor update tool.
    No error field — errors set installed/pending_count to None
    and append to report.collection_errors (D-03).
    """
    installed: bool | None       # True=found; False=not found; None=collection error
    pending_count: int | None    # int from XML; None when not installed, XML absent, or parse error
    scan_data_present: bool      # True only when XML file exists and was readable
```

**AuditReport insertion point** (lines 75–79) — insert `dell_dcu` and `lenovo_lsu` after `pending_updates`:
```python
    # System health — populated by Phase 13 collectors
    uptime_seconds: int | None = None    # seconds since last reboot; None if collection fails (D-04/D-05)
    pending_updates: int | None = None   # Windows update count from WUA COM; None when inaccessible (D-04/D-08)
    # *** INSERT HERE (Phase 14): ***
    dell_dcu: VendorUpdateStatus | None = None    # D-02 (Phase 14)
    lenovo_lsu: VendorUpdateStatus | None = None  # D-02 (Phase 14)
    local_profiles: list[str] = field(default_factory=list)
```

**Import block** (lines 1–8) — `VendorUpdateStatus` requires no new imports; `field` and `dataclass` already imported:
```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar
```

---

### `collectors/windows/vendor.py` (collector, request-response)

**Primary analog:** `collectors/windows/hardware.py` — `collect_pending_updates()` lines 76–90 (collector shape)
**Secondary analog:** `collectors/windows/apps.py` — `_search_uninstall_keys()` lines 134–174 and `UNINSTALL_PATHS` lines 25–30 (registry sweep reuse)

**Imports pattern** — copy from `hardware.py` and `apps.py`:
```python
"""Windows vendor update detection collector.
Detects Dell Command Update and Lenovo System Update installation status.
Reads pending update count passively from DCUApplicableUpdates.xml (never invokes CLI).
Never raises across the layer boundary — errors appended to report.collection_errors (D-03).
"""
from __future__ import annotations

import winreg
import xml.etree.ElementTree as ET
from pathlib import Path

from models import AuditReport, VendorUpdateStatus
from collectors.windows.apps import UNINSTALL_PATHS, _search_uninstall_keys
```

**Module-level constant pattern** — copy style from `apps.py` lines 25–30:
```python
DCU_XML_PATH = r"C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml"
```

**Public interface shape** — copy from `hardware.py` `collect_pending_updates` (lines 76–90):
```python
def collect_vendor_updates(report: AuditReport) -> None:
    """Populate report.dell_dcu and report.lenovo_lsu in place.

    Called only when --updates is passed (main.py). Never raises (D-03).
    Errors set fields to None and append to report.collection_errors.
    """
    _detect_dcu(report)
    _detect_lsu(report)
```

**Private helper: DCU detection** — guard → try → mutate → except (hardware.py lines 82–90 pattern):
```python
def _detect_dcu(report: AuditReport) -> None:
    try:
        installed, _version = _search_uninstall_keys(
            ["Dell Command Update", "Dell Command | Update"]
        )
        pending_count: int | None = None
        scan_data_present = False

        if installed:
            p = Path(DCU_XML_PATH)
            if p.exists():
                try:
                    root = ET.parse(p).getroot()
                    pending_count = len(root.findall("update"))
                    scan_data_present = True
                except ET.ParseError:
                    scan_data_present = True   # file present but unparseable
                    pending_count = None

        report.dell_dcu = VendorUpdateStatus(
            installed=installed,
            pending_count=pending_count,
            scan_data_present=scan_data_present,
        )
    except Exception as exc:
        report.collection_errors.append(f"DCU detection failed: {exc}")
        report.dell_dcu = VendorUpdateStatus(
            installed=None, pending_count=None, scan_data_present=False
        )
```

**Private helper: LSU detection** — same shape, no XML step:
```python
def _detect_lsu(report: AuditReport) -> None:
    try:
        installed, _version = _search_uninstall_keys(["Lenovo System Update"])
        report.lenovo_lsu = VendorUpdateStatus(
            installed=installed,
            pending_count=None,
            scan_data_present=False,
        )
    except Exception as exc:
        report.collection_errors.append(f"LSU detection failed: {exc}")
        report.lenovo_lsu = VendorUpdateStatus(
            installed=None, pending_count=None, scan_data_present=False
        )
```

**Error handling pattern** — matches all other collectors: catch `Exception`, append message, set field to safe default. Never re-raise. (See `hardware.py` line 90: `report.collection_errors.append(f"Pending updates collection failed: {exc}")`.)

---

### `collectors/windows/apps.py` (collector — no new code, export concern only)

**Analog:** self

The only change is that `UNINSTALL_PATHS` and `_search_uninstall_keys` are imported by `vendor.py`. No edits to `apps.py` are required under Option A (D-16 as-is). The existing definitions at lines 25–30 and 134–174 are sufficient.

**Key note for planner:** `_search_uninstall_keys` has an underscore prefix (private by convention). Importing it from a sibling module is acceptable within this package (same package, same layer). No change to `apps.py`.

---

### `main.py` (entry-point, request-response)

**Analog:** `main.py` lines 56–58 (CLI path) and lines 123–125 (full pipeline path) — existing `--updates` gate pattern

**Existing pattern to copy and extend** (lines 56–58):
```python
        if args.updates and sys.platform != "darwin":
            from collectors.windows.hardware import collect_pending_updates
            collect_pending_updates(report)
```

**New state — Location 1 (CLI path, ~line 57–61):**
```python
        if args.updates and sys.platform != "darwin":
            from collectors.windows.hardware import collect_pending_updates
            collect_pending_updates(report)
            from collectors.windows.vendor import collect_vendor_updates
            collect_vendor_updates(report)
```

**Existing pattern to copy and extend** (lines 123–125):
```python
    if args.updates and sys.platform != "darwin":
        from collectors.windows.hardware import collect_pending_updates
        collect_pending_updates(report)
```

**New state — Location 2 (full pipeline path, ~line 123–127):**
```python
    if args.updates and sys.platform != "darwin":
        from collectors.windows.hardware import collect_pending_updates
        collect_pending_updates(report)
        from collectors.windows.vendor import collect_vendor_updates
        collect_vendor_updates(report)
```

Both locations use lazy inline imports (not top-of-file) — match existing style.

---

### `renderer/__init__.py` (renderer, transform)

**Analog:** `renderer/__init__.py` lines 159–164 — `pending_updates_display` computation pattern

**Existing pattern to copy** (lines 159–164):
```python
    # Pending updates display — D-16 (Phase 13)
    pending_updates_display = (
        f"{report.pending_updates} pending"
        if report.pending_updates is not None
        else "N/A"
    )
```

**New display-value computations — insert after `pending_updates_display` block, before `return {`:**
```python
    # Dell DCU display — Phase 14
    if report.dell_dcu is not None:
        dcu = report.dell_dcu
        if not dcu.installed:
            dell_dcu_display: str | None = "Not installed"
        elif not dcu.scan_data_present:
            dell_dcu_display = "Unknown (no scan data)"
        else:
            dell_dcu_display = f"{dcu.pending_count} pending"
    else:
        dell_dcu_display = None  # --updates absent; omit row entirely (D-05)

    # Lenovo LSU display — Phase 14
    if report.lenovo_lsu is not None:
        lsu = report.lenovo_lsu
        lenovo_lsu_display: str | None = "Not installed" if not lsu.installed else "N/A"
    else:
        lenovo_lsu_display = None  # --updates absent; omit row entirely (D-05)
```

**Return dict additions** — copy style from existing `return {` block (lines 166–191):
```python
        'dell_dcu_display': dell_dcu_display,
        'lenovo_lsu_display': lenovo_lsu_display,
```

---

### `renderer/templates/character_sheet.html` (template, transform)

**Analog:** `character_sheet.html` lines 422–429 — existing System Health block (Uptime + Pending Updates rows)

**Existing rows to copy `muted` class pattern from** (lines 423–427):
```html
        <!-- System Health — Phase 13 -->
        <div class="stat-label">Uptime</div>
        <div class="stat-value{% if uptime_display is none %} muted{% endif %}">{{ uptime_display | default('—', true) }}</div>

        <div class="stat-label">Pending Updates</div>
        <div class="stat-value{% if pending_updates_display == 'N/A' %} muted{% endif %}">{{ pending_updates_display }}</div>
```

**Insertion point:** Lines 428–429 (the blank line between `Pending Updates` row and the closing `</div>`).

**New rows to insert before `</div>` (line 429):**
```html
        {% if dell_dcu_display is not none %}
        <div class="stat-label">Dell Cmd Update</div>
        <div class="stat-value{% if dell_dcu_display == 'Not installed' or dell_dcu_display == 'Unknown (no scan data)' %} muted{% endif %}">{{ dell_dcu_display }}</div>
        {% endif %}

        {% if lenovo_lsu_display is not none %}
        <div class="stat-label">Lenovo Sys Update</div>
        <div class="stat-value{% if lenovo_lsu_display == 'Not installed' or lenovo_lsu_display == 'N/A' %} muted{% endif %}">{{ lenovo_lsu_display }}</div>
        {% endif %}
```

**Pattern notes:**
- `is not none` (lowercase) is Jinja2 syntax — matches existing template usage
- `muted` CSS class is the established pattern for not-available / degraded values
- Row labels "Dell Cmd Update" and "Lenovo Sys Update" match the abbreviated style of sibling labels ("Serial Number", "Current User", "Pending Updates")
- No new section header — vendor rows extend the existing System Health block (D-06)

---

### `tests/test_vendor_collector.py` (test, request-response)

**Primary analog:** `tests/test_collectors_phase13.py` — `TestCollectPendingUpdates` class (lines 105–182) — same guard/try/except pattern
**Secondary analog:** `tests/test_app_collector.py` — `make_report()`, `_make_fake_ctx()`, `_make_enum_fn()`, `_make_query_fn()` helpers (lines 22–52) — registry mock helpers

**File header and imports pattern** (test_app_collector.py lines 1–16):
```python
"""Unit tests for collectors.windows.vendor — collect_vendor_updates function.

Mock pattern: patch.object(apps_mod.winreg, ...) patches the winreg reference
inside apps.py (where _search_uninstall_keys lives), not the stdlib module globally.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname
import collectors.windows.vendor as vendor_mod
import collectors.windows.apps as apps_mod
```

**`make_report()` helper** — copy exactly from test_app_collector.py line 22–23:
```python
def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))
```

**Registry mock helpers** — copy from test_app_collector.py lines 26–52:
```python
def _make_fake_ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx

def _make_enum_fn(subkeys: list[str]):
    def enum_fn(key, index):
        if index < len(subkeys):
            return subkeys[index]
        raise OSError("exhausted")
    return enum_fn

def _make_query_fn(display_name: str, display_version: str | None = None):
    def query_fn(key, value_name):
        if value_name == "DisplayName":
            return (display_name, 1)
        if value_name == "DisplayVersion" and display_version is not None:
            return (display_version, 1)
        raise FileNotFoundError(f"no value {value_name!r}")
    return query_fn
```

**Test class structure** — copy class-per-concern pattern from test_collectors_phase13.py:
```python
class TestCollectVendorUpdates:
    """collect_vendor_updates() in collectors/windows/vendor.py."""

    def test_collect_vendor_updates_is_exported(self): ...
    def test_dcu_not_installed_when_registry_miss(self): ...
    def test_dcu_installed_xml_absent(self): ...
    def test_dcu_installed_xml_present_two_updates(self, tmp_path): ...
    def test_dcu_installed_xml_present_zero_updates(self, tmp_path): ...
    def test_dcu_xml_parse_error_sets_pending_count_none_scan_data_true(self, tmp_path): ...
    def test_lsu_not_installed_when_registry_miss(self): ...
    def test_lsu_installed_pending_count_always_none(self): ...
    def test_never_raises_on_exception(self): ...
    def test_appends_to_collection_errors_on_exception(self): ...
```

**Registry mock target for vendor.py tests:** Because `vendor.py` imports `_search_uninstall_keys` from `apps.py`, mock `apps_mod.winreg` (not `vendor_mod.winreg`). Pattern from test_app_collector.py lines 63–66:
```python
with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
     patch.object(apps_mod.winreg, "EnumKey", side_effect=_make_enum_fn(["DCU key"])), \
     patch.object(apps_mod.winreg, "QueryValueEx",
                  side_effect=_make_query_fn("Dell Command | Update", "5.5.0")):
```

**XML fixture approach for `tmp_path` tests** — from RESEARCH.md Pattern 7 (preferred):
```python
def test_dcu_installed_xml_present_two_updates(tmp_path):
    xml_content = """<updates>
  <update><name>Driver A</name><urgency>Recommended</urgency></update>
  <update><name>BIOS 1.5</name><urgency>Urgent</urgency></update>
</updates>"""
    xml_file = tmp_path / "DCUApplicableUpdates.xml"
    xml_file.write_text(xml_content)

    fake_ctx = _make_fake_ctx()
    with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey",
                      side_effect=_make_enum_fn(["DCU key"])), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=_make_query_fn("Dell Command | Update", "5.5.0")), \
         patch.object(vendor_mod, "DCU_XML_PATH", str(xml_file)):
        report = make_report()
        vendor_mod.collect_vendor_updates(report)

    assert report.dell_dcu.installed is True
    assert report.dell_dcu.pending_count == 2
    assert report.dell_dcu.scan_data_present is True
```

**Guard test pattern** — copy from test_collectors_phase13.py lines 113–123:
```python
def test_dcu_not_installed_when_registry_miss(self):
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no registry")):
        report = make_report()
        vendor_mod.collect_vendor_updates(report)
    assert report.dell_dcu.installed is False
    assert report.dell_dcu.pending_count is None
    assert report.dell_dcu.scan_data_present is False
```

**Never-raises test pattern** — copy from test_collectors_phase13.py lines 168–182:
```python
def test_never_raises_on_exception(self):
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=RuntimeError("total failure")):
        report = make_report()
        try:
            vendor_mod.collect_vendor_updates(report)
        except Exception as exc:
            pytest.fail(f"collect_vendor_updates raised: {exc}")
```

---

## Shared Patterns

### Error Handling (all collector functions)
**Source:** `collectors/windows/hardware.py` lines 82–90 and `collectors/windows/apps.py` lines 479–490
**Apply to:** `vendor.py` — all private helper functions and the public `collect_vendor_updates`
```python
    except Exception as exc:
        report.collection_errors.append(f"[Description] failed: {exc}")
        # set report field to safe default (None or VendorUpdateStatus with None fields)
```

### Registry Sweep (via `_search_uninstall_keys`)
**Source:** `collectors/windows/apps.py` lines 134–174
**Apply to:** `collectors/windows/vendor.py` — `_detect_dcu()` and `_detect_lsu()`

Key contract:
- Returns `(True, version_or_None)` on match — discard version for VendorUpdateStatus
- Returns `(False, None)` on clean miss — `installed=False`, NOT `installed=None`
- Never raises — all `(FileNotFoundError, OSError)` silently skipped inside the function

```python
installed, _version = _search_uninstall_keys(["Dell Command Update", "Dell Command | Update"])
# installed is bool (True/False), never None on a clean call
```

### `muted` CSS Class Pattern (template)
**Source:** `character_sheet.html` lines 423–427
**Apply to:** Both vendor rows in System Health block
```html
<div class="stat-value{% if <condition> %} muted{% endif %}">{{ value }}</div>
```
`muted` indicates not-available / degraded values. Use for: `"Not installed"`, `"Unknown (no scan data)"`, `"N/A"`.

### Display-Value Computation in `_build_context`
**Source:** `renderer/__init__.py` lines 159–164 (`pending_updates_display`)
**Apply to:** `dell_dcu_display` and `lenovo_lsu_display` in `renderer/__init__.py`

Pattern: compute display string from raw report field; set to `None` when field is `None` (not collected); add key to `return {}` dict. Template checks `is not none` to decide whether to render the row.

### Test Module Import Pattern
**Source:** `tests/test_app_collector.py` line 15, `tests/test_collectors_phase13.py` line 14
**Apply to:** `tests/test_vendor_collector.py`
```python
import collectors.windows.vendor as vendor_mod
import collectors.windows.apps as apps_mod   # needed to patch apps_mod.winreg
```

---

## No Analog Found

All 7 files have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `collectors/windows/`, `models.py`, `renderer/`, `renderer/templates/`, `tests/`, `main.py`
**Files scanned:** 10 source files read directly
**Pattern extraction date:** 2026-05-18
