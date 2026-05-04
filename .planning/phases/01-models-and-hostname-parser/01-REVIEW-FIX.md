---
phase: 01-models-and-hostname-parser
fixed_at: 2026-05-04T00:00:00Z
review_path: .planning/phases/01-models-and-hostname-parser/01-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-05-04
**Source review:** `.planning/phases/01-models-and-hostname-parser/01-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

---

## Fixed Issues

### WR-01: Dead branch `if not parts` is unreachable

**File modified:** `parsers/name_parser.py`
**Commit:** `22c12fb`
**Applied fix:** Removed the dead `if not parts` clause from the city-code guard. `str.split()` always returns at least one element, so the branch was unreachable and gave a false impression it was load-bearing. Condition simplified from `if not parts or parts[0] not in CITY_CODES:` to `if parts[0] not in CITY_CODES:`.

---

### WR-02: `'LAP' in seg2` matches anywhere in the segment, not only as a suffix

**File modified:** `parsers/name_parser.py`
**Commit:** `055d859`
**Applied fix:** Changed the Department Laptop detection from a substring match (`'LAP' in seg2`) to a suffix match (`seg2.endswith('LAP')`). This aligns with the `CITY-DEPTLAP-###` naming convention documented in CLAUDE.md where LAP is always a suffix, preventing false matches on inputs like `LAPDOG` or `SLAPPER`. Comment updated to reflect the suffix-only constraint.

---

### WR-03: `CollectionResult.ok` treats `error=''` as a failure

**File modified:** `models.py`
**Commit:** `ebac52f`
**Applied fix:** Changed `return self.error is None` to `return not self.error` so that both `None` and `''` (empty string) are treated as "no error". This prevents a future collector that accidentally sets `error=''` from silently appearing as a failed collection with no diagnostic message.

---

## Skipped Issues

IN-01, IN-02, IN-03 — Info findings skipped (fix_scope: critical_warning)

---

_Fixed: 2026-05-04_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
