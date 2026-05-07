---
phase: 06-warning-data-model
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - health_checks.py
  - models.py
  - tests/test_health_checks.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-05-07
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed `health_checks.py`, `models.py`, and `tests/test_health_checks.py` for the Phase 06 warning data model. The logic in `health_checks.py` is correct — boundary conditions, division-by-zero guard, and None handling are all sound. The test suite has strong parametric coverage of all boundary cases and the always-two guarantee.

Two warning-level issues were found: an unconstrained `severity` field on the `Warning` dataclass that can silently accept invalid values, and a `CollectionResult.ok` property that returns `True` even when `value is None`. One info item notes a fragile cross-module dependency in the test fixture.

No critical security or data-loss issues were found.

---

## Warnings

### WR-01: `Warning.severity` is unconstrained — typos silently accepted

**File:** `models.py:51`
**Issue:** `severity: str` accepts any string. The docstring documents `'OK'` or `'WARN'` as the only valid values, but nothing enforces this. A caller that passes `'warn'`, `'WARNING'`, or any typo produces a structurally valid `Warning` object. If the Phase 7 renderer does a case-sensitive match on `severity` (e.g., `if w.severity == 'WARN'`), a miscased value would silently produce wrong output — no exception, no visible error.

**Fix:** Add `__post_init__` validation, or use a `Literal` type annotation to make type checkers catch invalid values:

```python
from typing import Literal

@dataclass
class Warning:
    code: str
    severity: Literal['OK', 'WARN']   # type checkers now flag invalid literals
    message: str
    detail: str | None = None

    def __post_init__(self) -> None:
        if self.severity not in ('OK', 'WARN'):
            raise ValueError(
                f"Warning.severity must be 'OK' or 'WARN', got {self.severity!r}"
            )
```

The `Literal` annotation alone catches mistakes at static analysis time; `__post_init__` catches them at runtime if static analysis is not enforced in CI.

---

### WR-02: `CollectionResult.ok` returns `True` when `value is None` and `error is None`

**File:** `models.py:19-20`
**Issue:** `ok` is defined as `not self.error`, so `CollectionResult(value=None, error=None)` reports `.ok == True`. Any collector that returns this (e.g., a collector that encounters a non-exception failure and forgets to set `error`) will appear successful to callers who check `.ok` without also guarding `value is not None`. This is a silent correctness trap that becomes a `TypeError` or `AttributeError` downstream when the caller dereferences `.value`.

```python
# Silent trap — .ok is True but value is None
result = CollectionResult(value=None)
if result.ok:
    process(result.value)  # AttributeError / NoneType error deferred to here
```

**Fix:** Tighten the invariant so that `.ok` requires a non-None value:

```python
@property
def ok(self) -> bool:
    return self.error is None and self.value is not None
```

Or, document the invariant explicitly in the docstring so every caller knows to check both:

```python
@property
def ok(self) -> bool:
    """True only when error is None. Callers must still guard `value is not None`
    before use — a missing-but-non-error result is valid (e.g. optional collector)."""
    return not self.error
```

The first option (tightening the check) is safer. The second is acceptable only if intentional "no value, no error" results are part of the contract.

---

## Info

### IN-01: Test fixture depends on `parsers.name_parser` — cross-module fragility

**File:** `tests/test_health_checks.py:7,12`
**Issue:** `make_report` calls `parse_hostname("TEST-PC")` from `parsers.name_parser` to populate the required `parsed_hostname` field. This means all health-check unit tests fail at import time if `parsers.name_parser` is missing, broken, or raises. The failure message would be an `ImportError` or parser exception — not a health-check test failure — which obscures the root cause during CI debugging.

**Fix:** Stub `parsed_hostname` directly in `make_report` so `test_health_checks.py` has zero dependency on the parser module:

```python
from models import AuditReport, Warning, ParsedHostname

def make_report(**kwargs) -> AuditReport:
    defaults = dict(
        hostname="TEST-PC",
        parsed_hostname=ParsedHostname(raw_hostname="TEST-PC"),
    )
    defaults.update(kwargs)
    return AuditReport(**defaults)
```

`ParsedHostname` is already imported from `models`, which is the only module `health_checks.py` itself depends on. This makes the test file truly self-contained.

---

_Reviewed: 2026-05-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
