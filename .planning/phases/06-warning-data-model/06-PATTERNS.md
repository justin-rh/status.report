# Phase 6: Warning Data Model - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 3
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `models.py` (modify) | model | transform | `models.py` itself — existing dataclasses | exact |
| `health_checks.py` (new) | utility/service | transform | `parsers/name_parser.py` | exact |
| `tests/test_health_checks.py` (new) | test | — | `tests/test_name_parser.py` | exact |

---

## Pattern Assignments

### `models.py` — Add `Warning` dataclass + `AuditReport.warnings` field

**Analog:** `models.py` lines 1–66 (read in full above)

**Imports pattern** (lines 1–6):
```python
"""StatusReport data contract. All layers import from this module.
ROADMAP SC5: AuditReport, ParsedHostname, AppStatus, CollectionResult importable here.
"""
from dataclasses import dataclass, field
from typing import Generic, TypeVar
```

**Dataclass with optional str field pattern** — `AppStatus` (lines 37–44):
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
```
Key observations:
- No `frozen=True` — mutable dataclasses throughout.
- Bounded string fields (e.g. `service_state`) are plain `str | None`, no Enum, no Literal — matches D-03.
- Optional fields with `None` default use `field_name: type | None = None` syntax.

**`field(default_factory=list)` pattern on AuditReport** (lines 48–66):
```python
@dataclass
class AuditReport:
    """The single normalized data container passed between all layers."""
    hostname: str
    parsed_hostname: ParsedHostname
    # Hardware — populated by Phase 2 collectors
    os_version: str | None = None
    os_build: str | None = None
    ...
    local_profiles: list[str] = field(default_factory=list)
    # Apps — populated by Phase 4
    apps: list[AppStatus] = field(default_factory=list)
    # Error accumulation — never raises; collectors populate this list
    collection_errors: list[str] = field(default_factory=list)
    timestamp: str = ''
```
Key observations:
- All list fields use `field(default_factory=list)` — never `= []`.
- Section comments (`# Apps — populated by Phase 4`) mark each logical group.
- New `warnings` field follows the same section-comment + `field(default_factory=list)` pattern.

**What to add to `models.py`:**
1. New `Warning` dataclass — insert before `AuditReport`, after `AppStatus`. Follow the `AppStatus` shape exactly: required positional fields first, optional fields with `None` defaults last.
2. New `AuditReport.warnings` field — add as `warnings: list['Warning'] = field(default_factory=list)` after the `collection_errors` line, with a section comment `# Health checks — populated by Phase 6`.

---

### `health_checks.py` — New module with `evaluate_warnings()`

**Analog:** `parsers/name_parser.py` (pure-function module, no OS calls, constants at top, single public function)

**Module docstring + import pattern** (`parsers/name_parser.py` lines 1–6):
```python
"""Hostname parser — decodes Master Electronics naming convention to ParsedHostname.

Decision rules D-01 through D-09 from 01-CONTEXT.md govern all disambiguation.
Anti-pattern: never check seg3.isdigit() before checking seg2 in P3_CODES (Pitfall 1).
"""
from models import ParsedHostname
```
Replicate this shape: one-liner module docstring citing requirements, then `from models import ...`.

**Module-level constants pattern** (`parsers/name_parser.py` lines 10–35 — `CITY_CODES`, `P3_CODES`):
```python
# 21 confirmed city codes as of 2026-05-04.
CITY_CODES: dict[str, str] = { ... }

P3_CODES: frozenset[str] = frozenset({'P3A', 'P3B', 'P3C'})
```
Replicate for thresholds:
```python
# Threshold constants — adjust here without touching function logic (D-09).
OS_WARN_BUILD: int = 22000
DISK_WARN_PCT: float = 0.15
```

**Pure public function pattern** (`parsers/name_parser.py` lines 38–43):
```python
def parse_hostname(hostname: str) -> ParsedHostname:
    """Pure function: hostname string -> ParsedHostname. Never raises.

    Decision rules D-01 through D-09 from CONTEXT.md apply.
    """
```
Replicate: `evaluate_warnings(report: AuditReport) -> list[Warning]` with a matching docstring stating it is a pure function and always returns exactly two Warning objects.

**Section-separator comment pattern** (`collectors/windows/hardware.py` lines 14–17):
```python
# ---------------------------------------------------------------------------
# Module-level wmi import — allows tests to patch _wmi_module without
# requiring a real COM server installed in CI (D-06).
# ---------------------------------------------------------------------------
```
Use the same `# ---...---` 79-char rule separators between logical sections: constants, public interface, private helpers (if any).

**No `CollectionResult` envelope** — `evaluate_warnings()` returns `list[Warning]` directly. This is confirmed by D-06 in CONTEXT.md: the function cannot fail in a meaningful way. The `CollectionResult` pattern is only used by collector functions that interact with OS APIs.

---

### `tests/test_health_checks.py` — New test file

**Primary analog:** `tests/test_name_parser.py` (pure-function tests, no mocks needed, parametrize for boundary cases)

**Secondary analog:** `tests/test_hardware_collector.py` (for `make_report()` helper shape and `from __future__ import annotations` header)

**File header pattern** (`tests/test_hardware_collector.py` lines 1–16):
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
Key observations:
- `"""Unit tests for <module> — <function> function."""` as the first line.
- `from __future__ import annotations` always present.
- `import pytest` always imported even when not all tests use it (guards no-raise tests).
- `make_report()` factory function — always defined at module top, returns minimal valid `AuditReport`.
- Import the module under test at the top, not inside test functions (unless testing import behavior specifically).

**Section separator comment pattern** (`tests/test_hardware_collector.py` lines 58–64):
```python
# ---------------------------------------------------------------------------
# _collect_os helpers
# ---------------------------------------------------------------------------
```
Group tests by logical behavior with the same 79-char separator comments.

**Parametrize pattern** (`tests/test_name_parser.py` lines 5–38):
```python
@pytest.mark.parametrize('hostname,expected', [
    ('PHX-INV-003',  {'city': 'Phoenix', 'device_type': 'Warehouse Workstation'}),
    ...
])
def test_parse_hostname(hostname, expected):
    result = parse_hostname(hostname)
    for field_name, value in expected.items():
        assert getattr(result, field_name) == value, (
            f'{hostname}: expected {field_name}={value!r}, got {getattr(result, field_name)!r}'
        )
```
Use `@pytest.mark.parametrize` for boundary cases (build = 21999 WARN, 22000 OK, 22621 OK; disk at 15% WARN, 16% OK, None OK-skip).

**No-raise guarantee pattern** (`tests/test_hardware_collector.py` lines 215–232):
```python
def test_collect_hardware_never_raises():
    """collect_hardware must not propagate any exception under any circumstances."""
    ...
    try:
        report = make_report()
        collect_hardware(report)
    except Exception as exc:
        pytest.fail(f"collect_hardware raised an exception: {exc}")
```
Include an analogous test that passes `AuditReport` instances with all `None` fields to confirm `evaluate_warnings()` never raises.

**Import location pattern** — `tests/test_app_collector.py` line 15 imports the module at top level (`import collectors.windows.apps as apps_mod`), not inside test functions. Do the same: `import health_checks as hc_mod` or `from health_checks import evaluate_warnings` at top of the test file.

---

## Shared Patterns

### Dataclass Definition Style
**Source:** `models.py` lines 10–66
**Apply to:** `Warning` dataclass in `models.py`
```python
@dataclass
class Warning:
    """<one-line description>."""
    code: str           # required positional first
    severity: str       # required positional second
    message: str        # required positional third
    detail: str | None = None  # optional last, same as AppStatus.error
```
Rules: no `frozen=True`, no `__post_init__`, no Enum — plain `str` for bounded values per D-03.

### AuditReport List Field Addition
**Source:** `models.py` lines 61–65
**Apply to:** `AuditReport.warnings` field addition
```python
    # Health checks — populated by Phase 6
    warnings: list['Warning'] = field(default_factory=list)
```
Place after `collection_errors` line. Use forward reference string `'Warning'` if `Warning` is defined later in the same file; otherwise plain `Warning` if defined before `AuditReport`.

### Module-Level Constants
**Source:** `parsers/name_parser.py` lines 8–35; `collectors/windows/hardware.py` lines 29–35
**Apply to:** `health_checks.py` threshold constants
```python
# Threshold constants — adjust here without touching function logic (D-09).
OS_WARN_BUILD: int = 22000
DISK_WARN_PCT: float = 0.15
```

### Pure-Function Docstring Convention
**Source:** `parsers/name_parser.py` line 39
**Apply to:** `evaluate_warnings()` in `health_checks.py`
```python
def evaluate_warnings(report: AuditReport) -> list[Warning]:
    """Pure function: AuditReport -> list[Warning]. Never raises.

    Always returns exactly two Warning objects — one per check — so the
    Phase 7 renderer can display a complete status table regardless of
    pass/fail outcome (D-06).
    """
```

### `make_report()` Test Factory
**Source:** `tests/test_hardware_collector.py` lines 16–17; `tests/test_app_collector.py` lines 22–23
**Apply to:** `tests/test_health_checks.py`
```python
def make_report(**kwargs) -> AuditReport:
    defaults = dict(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))
    defaults.update(kwargs)
    return AuditReport(**defaults)
```
The `**kwargs` override variant (from `tests/test_renderer.py` line 16) is preferred here because tests need to vary `os_build`, `disk_free_gb`, `disk_total_gb` independently.

---

## No Analog Found

None — all three files have strong codebase analogs.

---

## Metadata

**Analog search scope:** `models.py`, `parsers/`, `collectors/windows/`, `tests/`
**Files scanned:** 6 source files read in full
**Pattern extraction date:** 2026-05-07
