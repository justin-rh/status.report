# Phase 1: Models and Hostname Parser - Research

**Researched:** 2026-05-04
**Domain:** Python dataclasses, pure-function string parsing, Master Electronics hostname naming convention
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Partial Match Handling**
- D-01: Device type is determined by segment structure, not by whitelisting individual code values. If the pattern fits, device type is inferred.
- D-02: Unrecognized dept code with a valid city + `CITY-DEPT-###` structure -> `device_type=Warehouse Workstation`, `dept_code` preserved as the raw unrecognized value.
- D-03: Unrecognized company code with a valid city + `CITY-SERIAL-COMPANY` structure -> `device_type=User-Assigned Laptop`, `company_code` preserved as the raw unrecognized value.

**City Code Strictness**
- D-04: Unrecognized city prefix -> `device_type=Unknown`, silent. Tool does not attempt to parse the rest of the hostname.
- D-05: Raw hostname is always preserved in ParsedHostname regardless of outcome.

**Department Code Policy**
- D-06: Any short uppercase segment in position 2 (non-LAP, non-P3, non-numeric serial) qualifies as a warehouse department code. No whitelist enforcement.
- D-07: Unit tests use a representative sample of known dept codes plus one test with an unrecognized code. Not one test per known code.

**Unknown Hostname Data Preservation**
- D-08: Fully unrecognized hostname (e.g., `DESKTOP-XYZ123`): `device_type=Unknown`, `raw_hostname` preserved, all other ParsedHostname fields are `None`.
- D-09: Near-miss hostname with recognized city but bad structure (e.g., `PHX-BADSTRUCT` — only 2 segments): `city` field populated, `device_type=Unknown`, remaining fields `None`.

### Claude's Discretion
- CollectionResult typing: whether to use `CollectionResult[T]` generic typing or plain untyped is Claude's call — the envelope pattern `(value, error)` is fixed.
- AppStatus field design: `installed`, `version`, `service_state` — Claude selects fields to satisfy Phase 3 (renderer) and Phase 4 (app detection) contracts without re-asking.
- Exact module/file layout within the package — success criteria requires importability from `models.py`; internals are Claude's call.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COLL-01 | Tool parses the PC hostname and decodes city, device type (warehouse workstation, user-assigned laptop, department laptop, P3), department code, company code, and station number using the Master Electronics naming convention | Hostname parser design in Architecture Patterns section; full pattern disambiguation table |
| OUT-03 | Tool handles unrecognized or non-conforming hostnames gracefully (renders with "Unknown" device type and displays raw hostname without crashing) | D-04, D-08, D-09 behavior documented; CollectionResult envelope pattern eliminates cross-layer exceptions |

</phase_requirements>

---

## Summary

Phase 1 is a pure Python phase with no Windows API calls, no external service dependencies, and no packaging concerns. The work divides cleanly into two deliverables: (1) the data contract (`models.py` with four dataclasses) and (2) the hostname parser (`parsers/name_parser.py` as a pure function). Both are testable with stdlib `unittest` or `pytest` on any platform including the developer's machine.

The data contract drives every downstream phase. `ParsedHostname` shape is fixed by the locked decisions (D-01 through D-09). `AuditReport` must be designed wide enough to accommodate Phase 2 (hardware fields), Phase 3 (rendering fields), and Phase 4 (app status list) — all of which are known from the roadmap. Designing these correctly now avoids retroactive breaking changes to the contract in later phases.

The hostname parser's primary engineering challenge is disambiguation: all four device types share the same `CITY-SEG2-SEG3` three-segment structure. The correct evaluation order (P3 check -> LAP substring check -> seg3 numeric/alpha classification) eliminates all ambiguity and has been verified against all locked decision test cases in this research session.

**Primary recommendation:** Define all four dataclasses in `models.py` first (no parser logic there), then implement the parser in `parsers/name_parser.py` as a pure function that returns `ParsedHostname`. Install `pytest` as a dev dependency and write tests before the parser implementation to establish the acceptance criterion baseline.

---

## Project Constraints (from CLAUDE.md)

| Directive | Applies to Phase 1 | Note |
|-----------|-------------------|------|
| NEVER use PyInstaller `--onefile` | No | Packaging is Phase 5 |
| NEVER use `Win32_Product` | No | No WMI calls in Phase 1 |
| ALWAYS enumerate all 4 registry Uninstall paths | No | Registry is Phase 4 |
| ALWAYS derive output path from `Path(sys.executable).parent` | No | File I/O is Phase 3/5 |
| NEVER write to the host PC | No | No file I/O in Phase 1 |
| Python 3.12, psutil 6.x, wmi 1.5.1, Jinja2 3.1.x, PyInstaller 6.x | Partial | Phase 1 uses only stdlib + pytest |
| Architecture: `main.py -> collectors/ -> models.AuditReport -> renderer/ -> writers/` | Yes | `models.py` is the hub; parser lives in `parsers/` |
| Each collector returns `CollectionResult(value, error)` envelope — never raises across layer boundaries | Yes | `CollectionResult` defined here; pattern applies to all phases |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Data contract definition | `models.py` | — | All layers import from here; zero upward dependencies |
| Hostname parsing | `parsers/name_parser.py` | — | Pure function; no OS calls; platform-agnostic by design |
| Error envelope pattern | `models.py` (CollectionResult) | Used by `collectors/` | Defined in Phase 1; consumed starting Phase 2 |
| AppStatus field design | `models.py` | Consumed by Phase 3 renderer + Phase 4 detector | Shape locked here to avoid downstream rework |
| Unit tests | `tests/` | Run on any platform | No Windows APIs means tests run in CI, developer machine, or remotely |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib: `dataclasses` | Built-in (3.12) | Define AuditReport, ParsedHostname, AppStatus, CollectionResult | Zero dependencies; `@dataclass` gives `__repr__`, `__eq__`, `__init__` for free; `field(default_factory=list)` handles mutable defaults safely |
| Python stdlib: `typing` | Built-in (3.12) | Generic[T] for CollectionResult, `T | None` union syntax | Python 3.10+ union syntax (`X | Y`) is cleaner than `Optional[X]`; works natively in 3.12 |
| Python stdlib: `re` | Built-in (3.12) | Hostname segment splitting and pattern matching | No dependencies; sufficient for the delimiter-split + segment classification approach |
| pytest | 8.x (install as dev dep) | Unit tests for hostname parser | Standard Python test runner; cleaner than `unittest` for parametrize; no Windows API calls in Phase 1 tests |

[VERIFIED: Python 3.12.10 installed at C:\Users\justin.rhoda\AppData\Local\Programs\Python\Python312\python.exe]
[VERIFIED: `dataclasses`, `typing`, `re`, `unittest` all importable from stdlib — confirmed by runtime check in this session]
[VERIFIED: pytest NOT currently installed in Python 3.12 environment — Wave 0 task required]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib: `unittest` | Built-in (3.12) | Fallback test runner if pytest install is blocked | Use if pytest cannot be installed in the project venv; less ergonomic for parametrize but works |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@dataclass` | `TypedDict` | TypedDict doesn't give `__init__` or `__repr__`; dataclass is correct for structured objects with behavior |
| `@dataclass` | `pydantic.BaseModel` | Pydantic adds validation but is a heavy dependency; not needed for Phase 1's pure data containers |
| `CollectionResult(Generic[T])` | Plain untyped `CollectionResult` | Generic version gives IDE type inference at call sites; adds no runtime cost; Claude's call (discretion) |
| `re` for parsing | `str.split('-')` then classify | Split-then-classify is simpler and sufficient; regex is not needed for this pattern |

**Installation (dev environment):**
```bash
# From project root, after creating venv
python -m venv .venv
.venv\Scripts\activate
pip install pytest==8.*
# No other dependencies needed for Phase 1
```

---

## Architecture Patterns

### System Architecture Diagram

```
Hostname string (e.g., "PHX-INV-003")
          |
          v
  parsers/name_parser.py
    parse_hostname(raw: str) -> ParsedHostname
          |
     [pure function — no OS calls, no side effects]
          |
     Step 1: Split on '-' -> segments list
          |
     Step 2: segments[0] in CITY_CODES?
          |-- NO  -> device_type=Unknown, raw preserved, return
          |-- YES -> city = CITY_CODES[segments[0]]
          |
     Step 3: len(segments) >= 3?
          |-- NO  -> city populated, device_type=Unknown, return (D-09)
          |-- YES -> seg2 = segments[1], seg3 = segments[2]
          |
     Step 4: seg2 in P3_CODES (P3A/P3B/P3C)?
          |-- YES -> P3 Warehouse Device, station=int(seg3), return
          |
     Step 5: 'LAP' in seg2?
          |-- YES -> Department Laptop, department=seg2, station=int(seg3), return
          |
     Step 6: seg3.isdigit()?
          |-- YES -> Warehouse Workstation, department=seg2, station=int(seg3) (D-02 applies)
          |
     Step 7: seg3 is alpha/company-code pattern?
          |-- YES -> User-Assigned Laptop, company_code=seg3 (D-03 applies)
          |
     Step 8: -> device_type=Unknown (city populated, rest None)
          |
          v
    ParsedHostname dataclass instance
          |
          v
   Assembled into AuditReport.parsed_hostname
   (by main.py, Phase 2+)
```

### Recommended Project Structure
```
status_report/          <- project root (currently only CLAUDE.md exists)
├── models.py           <- AuditReport, ParsedHostname, AppStatus, CollectionResult
├── parsers/
│   ├── __init__.py
│   └── name_parser.py  <- parse_hostname() pure function + CITY_CODES constant
├── tests/
│   ├── __init__.py
│   └── test_name_parser.py  <- pytest unit tests, no Windows API calls
├── collectors/         <- stub (Phase 2 fills this in)
│   ├── base.py
│   └── windows/
│       └── __init__.py
├── renderer/           <- stub (Phase 3 fills this in)
└── writers/            <- stub (Phase 5 fills this in)
```

Note: `models.py` lives at the root (not inside a package) because CONTEXT.md success criteria SC5 says "importable from `models.py`." This matches the architecture diagram from ARCHITECTURE.md.

### Pattern 1: Dataclass Data Contract

**What:** All four models are `@dataclass` classes in `models.py`. Fields use Python 3.10+ union syntax (`X | None`). Mutable defaults use `field(default_factory=...)`. `CollectionResult` uses `Generic[T]` for type-safe call sites.

**When to use:** Always — this is the single source of truth for data shapes across all phases.

```python
# Source: Python 3.12 stdlib docs, verified in this session
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar('T')

@dataclass
class CollectionResult(Generic[T]):
    value: T | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class ParsedHostname:
    raw_hostname: str              # D-05, D-08: always preserved
    city: str | None = None        # e.g., "Phoenix" — None if D-04 applies
    device_type: str | None = None # "Warehouse Workstation" | "User-Assigned Laptop" |
                                   # "Department Laptop" | "P3 Warehouse Device" | "Unknown"
    department: str | None = None  # Warehouse dept code (D-02: preserved even if unrecognized)
    company_code: str | None = None # Laptop company code (D-03: preserved even if unrecognized)
    station: int | None = None     # Numeric station from seg3 (ROADMAP SC1: station=3 not '003')


@dataclass
class AppStatus:
    name: str                              # Human-readable app name
    installed: bool                        # Primary flag for Phase 3 badge rendering
    version: str | None = None             # Registry DisplayVersion value
    service_state: str | None = None       # "Running" | "Stopped" | None (N/A)
    detection_method: str = 'registry'     # 'registry' | 'filesystem' | 'service'
    error: str | None = None               # If detection failed, reason here


@dataclass
class AuditReport:
    hostname: str
    parsed_hostname: ParsedHostname
    # Hardware (populated by Phase 2 collectors)
    os_version: str | None = None
    os_build: str | None = None
    cpu_model: str | None = None
    ram_gb: float | None = None
    disk_total_gb: float | None = None
    disk_free_gb: float | None = None
    current_user: str | None = None
    local_profiles: list[str] = field(default_factory=list)
    # App detection (populated by Phase 4)
    apps: list[AppStatus] = field(default_factory=list)
    # Error accumulation (never raises — errors collected here)
    collection_errors: list[str] = field(default_factory=list)
    timestamp: str = ''
```

### Pattern 2: Hostname Parser — Pure Function

**What:** A module-level function `parse_hostname(hostname: str) -> ParsedHostname` with no side effects, no OS calls, no global state mutation. Constants (`CITY_CODES`, `P3_CODES`) defined at module level.

**When to use:** Called by `main.py` after getting the raw hostname string. Also callable directly in unit tests.

```python
# parsers/name_parser.py
from models import ParsedHostname

CITY_CODES: dict[str, str] = {
    'AMM': 'Amman',        'AMS': 'Amsterdam',     'CHI': 'Chicago',
    'EDE': 'Eden Prairie', 'GEO': 'Georgetown',    'GER': 'Germany',
    'GUA': 'Guadalajara',  'MIA': 'Miami',          'MON': 'Montreal',
    'NYC': 'New York',     'PEO': 'Peoria',         'PEN': 'Pensacola',
    'PHX': 'Phoenix',      'ROC': 'Rockford',       'SCL': 'Santiago',
    'SEA': 'Seattle',      'SMO': 'Santa Monica',   'TAM': 'Tampa',
    'TOR': 'Toronto',      'TSU': 'Tsuchiura',      'VAN': 'Vancouver',
}

P3_CODES: frozenset[str] = frozenset({'P3A', 'P3B', 'P3C'})


def parse_hostname(hostname: str) -> ParsedHostname:
    """Pure function: hostname string -> ParsedHostname.

    Decision rules (D-01 through D-09 from CONTEXT.md):
    - D-04: Unrecognized city -> device_type=Unknown, silent, no further parsing
    - D-09: Recognized city but < 3 segments -> city populated, device_type=Unknown
    - D-01: Device type by segment structure, not code whitelisting
    - D-02: Unknown dept code + CITY-DEPT-### structure -> Warehouse Workstation
    - D-03: Unknown company code + CITY-SERIAL-COMPANY structure -> User-Assigned Laptop
    - D-05: raw_hostname always preserved
    - D-08: Fully unrecognized -> device_type=Unknown, all other fields None
    """
    parts = hostname.upper().split('-')

    # D-04: unrecognized city prefix
    if not parts or parts[0] not in CITY_CODES:
        return ParsedHostname(raw_hostname=hostname, device_type='Unknown')

    city = CITY_CODES[parts[0]]

    # D-09: near-miss (recognized city, not enough segments)
    if len(parts) < 3:
        return ParsedHostname(raw_hostname=hostname, city=city, device_type='Unknown')

    seg2, seg3 = parts[1], parts[2]

    # P3 Warehouse Device (explicit match — checked first to avoid LAP substring interference)
    if seg2 in P3_CODES:
        return ParsedHostname(
            raw_hostname=hostname, city=city,
            device_type='P3 Warehouse Device',
            station=_parse_station(seg3),
        )

    # Department Laptop (LAP substring in segment 2)
    if 'LAP' in seg2:
        return ParsedHostname(
            raw_hostname=hostname, city=city,
            device_type='Department Laptop',
            department=seg2,
            station=_parse_station(seg3),
        )

    # Warehouse Workstation: seg3 is numeric (D-01, D-02, D-06)
    if seg3.isdigit():
        return ParsedHostname(
            raw_hostname=hostname, city=city,
            device_type='Warehouse Workstation',
            department=seg2,
            station=int(seg3),
        )

    # User-Assigned Laptop: seg3 is alphabetic (D-01, D-03)
    if seg3.isalpha() and seg3.isupper():
        return ParsedHostname(
            raw_hostname=hostname, city=city,
            device_type='User-Assigned Laptop',
            company_code=seg3,
        )

    # Recognized city but structure unclear (D-09 extension)
    return ParsedHostname(raw_hostname=hostname, city=city, device_type='Unknown')


def _parse_station(seg: str) -> int | None:
    """Convert seg3 to int station number, or None if not numeric."""
    try:
        return int(seg)
    except (ValueError, TypeError):
        return None
```

### Pattern 3: Unit Test Structure (No Windows API Calls)

**What:** pytest parametrize covers all device type paths, all 21 city codes (spot-check, not exhaustive), and all locked edge cases from D-04 through D-09.

**When to use:** Tests run in `tests/test_name_parser.py` without any OS API calls, making them runnable on any platform.

```python
# tests/test_name_parser.py
import pytest
from parsers.name_parser import parse_hostname

@pytest.mark.parametrize('hostname,expected', [
    # SC1: Warehouse Workstation (ROADMAP success criterion 1)
    ('PHX-INV-003', {'city': 'Phoenix', 'device_type': 'Warehouse Workstation',
                     'department': 'INV', 'station': 3}),
    # SC2: User-Assigned Laptop (ROADMAP success criterion 2)
    ('PHX-ABC123-ME', {'device_type': 'User-Assigned Laptop', 'company_code': 'ME'}),
    # SC3: Unknown hostname (ROADMAP success criterion 3)
    ('DESKTOP-XYZ123', {'device_type': 'Unknown', 'raw_hostname': 'DESKTOP-XYZ123'}),
    # P3 device
    ('CHI-P3B-002', {'device_type': 'P3 Warehouse Device', 'city': 'Chicago', 'station': 2}),
    # Department Laptop
    ('NYC-INVLAP-004', {'device_type': 'Department Laptop', 'department': 'INVLAP'}),
    # D-02: unrecognized dept code -> still Warehouse Workstation
    ('PHX-NEWDEPT-005', {'device_type': 'Warehouse Workstation', 'department': 'NEWDEPT'}),
    # D-03: unrecognized company code -> still User-Assigned Laptop
    ('PHX-ABC123-XX', {'device_type': 'User-Assigned Laptop', 'company_code': 'XX'}),
    # D-04: unrecognized city prefix
    ('ZZZ-INV-003', {'device_type': 'Unknown', 'city': None}),
    # D-08: fully unrecognized (no CITY-X-X structure)
    ('DESKTOP-XYZ123', {'device_type': 'Unknown', 'city': None}),
    # D-09: recognized city, too few segments
    ('PHX-BADSTRUCT', {'city': 'Phoenix', 'device_type': 'Unknown'}),
    # Sample of city codes (D-07: representative sample, not exhaustive)
    ('AMM-SHP-001', {'city': 'Amman', 'device_type': 'Warehouse Workstation'}),
    ('VAN-REC-007', {'city': 'Vancouver', 'device_type': 'Warehouse Workstation'}),
    ('TSU-P3A-003', {'city': 'Tsuchiura', 'device_type': 'P3 Warehouse Device'}),
])
def test_parse_hostname(hostname, expected):
    result = parse_hostname(hostname)
    for field, value in expected.items():
        assert getattr(result, field) == value, (
            f'{hostname}: expected {field}={value!r}, got {getattr(result, field)!r}'
        )

def test_raw_hostname_always_preserved():
    """D-05: raw_hostname preserved regardless of parse outcome."""
    for hostname in ['PHX-INV-003', 'DESKTOP-XYZ123', 'PHX-BADSTRUCT', 'ZZZ-X-X']:
        result = parse_hostname(hostname)
        assert result.raw_hostname == hostname

def test_no_exception_on_any_input():
    """OUT-03: no crash on unrecognized hostname."""
    for bad in ['', '-', '--', 'PHX', 'phx-inv-003', '123-INV-003', 'PHX-INV']:
        result = parse_hostname(bad)  # must not raise
        assert result.device_type is not None  # Always returns something
```

### Anti-Patterns to Avoid

- **Frozen dataclass on AuditReport:** `@dataclass(frozen=True)` would prevent Phase 2 collectors from populating fields after construction. Use mutable dataclasses; the contract enforces discipline, not immutability.
- **Whitelist-based device type detection:** Checking `if seg2 in KNOWN_DEPT_CODES` for Warehouse Workstations violates D-01 and D-06. New IT department codes must auto-qualify.
- **Raising from parse_hostname:** `parse_hostname` must never raise. Bad input -> `ParsedHostname(raw_hostname=..., device_type='Unknown')`. This satisfies OUT-03 at the parser level.
- **Eager city code upper-casing in the input:** The parser should apply `.upper()` to segments when splitting so that `phx-inv-003` is handled the same as `PHX-INV-003`. Hostname is preserved raw (D-05 — the `raw_hostname` field stores the original).
- **CollectionResult in models.py importing from parsers:** Models must have zero upward dependencies. `parsers/name_parser.py` imports from `models.py`, never the reverse.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mutable default in dataclass | `apps: list = []` at class level | `field(default_factory=list)` | Shared mutable default is a Python footgun — all instances share the same list object |
| Optional field syntax | `Optional[str]` from `typing` | `str \| None` (Python 3.10+) | Cleaner syntax, native to Python 3.12, no typing import needed for this pattern |
| Type-safe result wrapper | Custom tuple or dict | `CollectionResult(Generic[T])` | Generic provides IDE inference; `.ok` property makes call sites clean |

**Key insight:** Phase 1 is almost entirely stdlib. The only external dependency to install is `pytest` for development. Do not add Pydantic, attrs, or any validation library — the data contract here does not need runtime validation, only structural clarity.

---

## Common Pitfalls

### Pitfall 1: Segment Disambiguation Order Is Wrong
**What goes wrong:** Warehouse Workstation case catches `PHX-P3A-001` before the P3 check runs, because P3A contains all uppercase alpha characters and seg3 is numeric.
**Why it happens:** If the evaluation order is `seg3.isdigit()` first, `PHX-P3A-001` is classified as a Warehouse Workstation with `department='P3A'` instead of `P3 Warehouse Device`.
**How to avoid:** Always check P3 (`seg2 in P3_CODES`) before the `seg3.isdigit()` branch. The correct order is: P3 -> LAP -> numeric seg3 -> alpha seg3 -> Unknown.
**Warning signs:** `PHX-P3A-001` returns `device_type='Warehouse Workstation'` in tests.

### Pitfall 2: Station Field Type Mismatch
**What goes wrong:** Parser stores `station='003'` (string) instead of `station=3` (int). Phase 3 renderer displays `003` or crashes when doing arithmetic on the station number.
**Why it happens:** `seg3` is a string from `split('-')`; a naive `station=seg3` forgets the int conversion.
**How to avoid:** Always apply `int(seg3)` when populating the `station` field. ROADMAP SC1 states `station=3`, not `station='003'`.
**Warning signs:** `test_parse_hostname('PHX-INV-003', ...)` fails the `station=3` assertion.

### Pitfall 3: Hostname Casing Not Normalized Before Lookup
**What goes wrong:** `parse_hostname('phx-inv-003')` returns `device_type='Unknown'` because `'phx'` is not in `CITY_CODES` (which has `'PHX'`).
**Why it happens:** Windows hostnames are case-insensitive; real machines may return mixed-case from `socket.gethostname()`.
**How to avoid:** Apply `.upper()` to all segment comparisons: `parts = hostname.upper().split('-')`. The `raw_hostname` field still stores the original unmodified string (D-05).
**Warning signs:** Parser fails on lowercase or mixed-case test inputs.

### Pitfall 4: AuditReport.parsed_hostname Field Name Drift
**What goes wrong:** ARCHITECTURE.md example uses `parsed_name: ParsedHostname`; CONTEXT.md and ROADMAP use `ParsedHostname` as the type but don't specify the field name. If the planner names the field `parsed_name` but the renderer template looks for `report.parsed_hostname`, Phase 3 breaks.
**How to avoid:** Use `parsed_hostname` as the field name (more descriptive, consistent with the class name suffix pattern). Lock this in models.py and reference it by name in all downstream work.
**Warning signs:** Phase 3 template access produces `AttributeError` on `report.parsed_hostname`.

### Pitfall 5: Missing `__init__.py` in parsers/
**What goes wrong:** `from parsers.name_parser import parse_hostname` raises `ModuleNotFoundError` at runtime despite the file existing.
**Why it happens:** Python package discovery requires `__init__.py` in every directory that is treated as a package. Greenfield project means this is easy to forget.
**How to avoid:** Create `parsers/__init__.py` (empty is fine) alongside `parsers/name_parser.py`.
**Warning signs:** Import works when running directly from the `parsers/` directory but fails from `main.py`.

---

## Code Examples

### Complete models.py

```python
# models.py — single file, all four required dataclasses
# ROADMAP SC5: AuditReport, ParsedHostname, AppStatus, CollectionResult
# importable from models.py
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar('T')


@dataclass
class CollectionResult(Generic[T]):
    """Error envelope for all collector return values.
    Never raise across layer boundaries — return CollectionResult instead.
    """
    value: T | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class ParsedHostname:
    """Decoded Master Electronics hostname.
    All fields except raw_hostname are None if parsing fails (D-08).
    """
    raw_hostname: str               # Always preserved (D-05)
    city: str | None = None         # Full city name (e.g., "Phoenix") or None (D-04)
    device_type: str | None = None  # One of four types or "Unknown"
    department: str | None = None   # Warehouse dept code; preserved even if unrecognized (D-02)
    company_code: str | None = None # Laptop company code; preserved even if unrecognized (D-03)
    station: int | None = None      # Station number as int (e.g., 3 not '003')


@dataclass
class AppStatus:
    """Detection result for a single target application."""
    name: str
    installed: bool
    version: str | None = None
    service_state: str | None = None    # 'Running' | 'Stopped' | None
    detection_method: str = 'registry'  # 'registry' | 'filesystem' | 'service'
    error: str | None = None


@dataclass
class AuditReport:
    """The single normalized data container passed between all layers."""
    hostname: str
    parsed_hostname: ParsedHostname
    # Hardware — populated by Phase 2 collectors
    os_version: str | None = None
    os_build: str | None = None
    cpu_model: str | None = None
    ram_gb: float | None = None
    disk_total_gb: float | None = None
    disk_free_gb: float | None = None
    current_user: str | None = None
    local_profiles: list[str] = field(default_factory=list)
    # Apps — populated by Phase 4
    apps: list[AppStatus] = field(default_factory=list)
    # Error accumulation — never raises; collectors populate this list
    collection_errors: list[str] = field(default_factory=list)
    timestamp: str = ''
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Optional[str]` from typing | `str \| None` union syntax | Python 3.10 | Cleaner; no typing import for simple optionals |
| `typing.Generic` with verbose syntax | `Generic[T]` with `T \| None` | Python 3.10+ | Works natively in Python 3.12; confirmed in this session |
| `dataclass(frozen=True)` for all models | Mutable `@dataclass` for report, frozen only where needed | Stable | Mutable AuditReport lets collectors populate fields incrementally |

**Deprecated/outdated:**
- `Optional[str]`: Still works but prefer `str | None` for new Python 3.12 code
- `typing.List[str]`: Prefer `list[str]` (lowercase) in Python 3.9+

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `station` field should be `int` based on ROADMAP SC1 showing `station=3` | Architecture Patterns, Code Examples | If renderer needs zero-padded string `'003'`, int -> str formatting in the template is easy, but int is the correct canonical form |
| A2 | `parsed_hostname` is the correct field name for `AuditReport.parsed_hostname` (ARCHITECTURE.md uses `parsed_name`) | Code Examples | If Phase 3 template uses a different name, one-line rename required |
| A3 | `department` is the field name for the warehouse dept code segment (ROADMAP SC1 says `department=INV`) | Code Examples | CONTEXT.md says `dept_code` in D-02 but ROADMAP says `department`; using `department` to match ROADMAP |

---

## Open Questions

1. **International city codes (KUL, HKG not in the 21)**
   - What we know: STATE.md blocker notes "international offices: AMM, AMS, KUL, HKG" need validation. The 21 city codes in CLAUDE.md do not include KUL or HKG.
   - What's unclear: Are KUL (Kuala Lumpur) and HKG (Hong Kong) current offices using the naming convention, or historical? AMM and AMS are in the 21-code list.
   - Recommendation: Implement the parser with the 21 confirmed codes. The CITY_CODES dict is a module-level constant — adding codes is a one-line change. Document the blocker in code comments.

2. **Zero-padding in station numbers**
   - What we know: ROADMAP SC1 shows `station=3` for `PHX-INV-003`. The raw segment is `'003'`.
   - What's unclear: Does the renderer ever need the zero-padded form for display?
   - Recommendation: Store as `int`. If the renderer needs `'003'`, apply `str(station).zfill(3)` in the Jinja2 template. This keeps the model clean.

3. **Can segment 3 be alphanumeric (mixed) and not match any laptop pattern?**
   - What we know: Current rules classify `seg3.isdigit()` -> workstation, `seg3.isalpha()` -> laptop.
   - What's unclear: What if seg3 is something like `'A1B'`? Currently falls to `device_type=Unknown`.
   - Recommendation: Treat `Unknown` as the correct result for ambiguous structures. This is consistent with D-01 (structure-based detection) — if the structure is ambiguous, Unknown is honest.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All Phase 1 code | Yes | 3.12.10 at C:\Users\justin.rhoda\AppData\Local\Programs\Python\Python312\python.exe | — |
| pytest | Unit tests | No | — (not installed) | `unittest` from stdlib (less ergonomic) |
| stdlib: dataclasses | models.py | Yes | Built-in 3.12 | — |
| stdlib: typing | models.py (Generic) | Yes | Built-in 3.12 | — |
| stdlib: re | parsers/name_parser.py (optional) | Yes | Built-in 3.12 | str.split() is sufficient without re |

**Missing dependencies with no fallback:**
- None (pytest has a stdlib fallback)

**Missing dependencies with fallback:**
- pytest: not installed in Python 3.12 env — Wave 0 task: `pip install pytest==8.*` in project venv. `unittest` is the fallback if venv setup is deferred.

[VERIFIED: Python 3.12.10 confirmed installed]
[VERIFIED: pytest NOT installed — confirmed by `python -m pip show pytest` returning not-found]
[VERIFIED: All stdlib modules (dataclasses, typing, re, unittest) confirmed importable]

---

## Sources

### Primary (HIGH confidence)
- Python 3.12 stdlib `dataclasses` module — verified by runtime execution in this session
- Python 3.12 stdlib `typing` module — `Generic[T]` with `T | None` syntax verified by runtime execution
- CONTEXT.md Phase 1 locked decisions D-01 through D-09 — authoritative user input
- ROADMAP.md Phase 1 Success Criteria — authoritative success conditions
- CLAUDE.md — project technical constraints
- ARCHITECTURE.md — established project architecture patterns
- STACK.md — verified stack choices (Python 3.12, stdlib for Phase 1)

### Secondary (MEDIUM confidence)
- ARCHITECTURE.md `models.py` example — used as reference; field names adjusted to match ROADMAP SC1 (`department` vs `dept_code`, `parsed_hostname` vs `parsed_name`)

### Tertiary (LOW confidence)
- None — all Phase 1 research confirmed against project documents and runtime verification

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Python 3.12 confirmed installed; all stdlib modules verified in runtime
- Architecture: HIGH — patterns verified against runtime + locked decisions + ROADMAP success criteria
- Pitfalls: HIGH — all pitfalls identified from reasoning about the specific parser disambiguation problem, verified with code execution

**Research date:** 2026-05-04
**Valid until:** 2026-11-04 (stable stdlib; city code list may need update per STATE.md blocker)
