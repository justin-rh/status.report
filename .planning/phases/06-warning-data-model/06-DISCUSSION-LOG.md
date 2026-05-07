# Phase 6: Warning Data Model - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 06-warning-data-model
**Areas discussed:** Severity type, Module name, Result shape, Warning home

---

## Severity Type

| Option | Description | Selected |
|--------|-------------|----------|
| str | Plain str, consistent with service_state and other bounded string fields in models.py | ✓ |
| Literal['OK', 'WARN'] | Typed narrowly — mypy catches bad values at call sites | |
| Enum (WarningSeverity) | Full enum class; renderer must import WarningSeverity | |

**User's choice:** str — plain string, consistent with existing patterns  
**Notes:** Keeps models.py pattern consistent. Renderer does simple string comparison.

---

## Module Name

| Option | Description | Selected |
|--------|-------------|----------|
| health_checks.py | Reads naturally; no stdlib conflict; generalizes well | ✓ |
| warn_evaluator.py | Explicit about purpose — evaluates warnings | |
| evaluator.py | Short but vague | |

**User's choice:** health_checks.py  
**Notes:** Python stdlib has a `warnings` module — naming ours `warnings.py` would shadow it silently. `health_checks.py` avoids this entirely.

---

## Result Shape

| Option | Description | Selected |
|--------|-------------|----------|
| All checks (OK + WARN) | Returns one Warning per check regardless of outcome | ✓ |
| Only WARNs | Returns Warning only when a condition fires; empty list = all clear | |

**User's choice:** All checks — always return one Warning per check  
**Notes:** ROADMAP SC2/SC3 explicitly say "returns a WARN ... and OK ..." — both states needed. Phase 7 needs all checks to render the full status list with OK/WARN per row.

---

## Warning Home

| Option | Description | Selected |
|--------|-------------|----------|
| models.py | Consistent with all other dataclasses; AuditReport.warnings needs no cross-module import | ✓ |
| health_checks.py | Self-contained but breaks "models is single source" pattern | |

**User's choice:** models.py — consistent with AuditReport, AppStatus, ParsedHostname  
**Notes:** All dataclasses live in models.py. Putting Warning there keeps the single-import pattern intact.

---

## Claude's Discretion

- Warning code string format (e.g., 'OS_VERSION', 'DISK_SPACE')
- Warning message wording
- detail field content for disk check
- health_checks.py module structure internals

## Deferred Ideas

None — discussion stayed within phase scope.
