# Phase 11: Steve - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 11-steve
**Areas discussed:** --warnings output format, Flag combination, Collection scope per flag, --serial when unavailable

---

## --warnings Output Format

| Option | Description | Selected |
|--------|-------------|----------|
| message only | Clean, grep-able, no prefix noise. IT scripts parse it directly. | ✓ |
| [WARN] message | Matches the [SUMMARY] prefix style already in stdout. | |
| code: message | Machine-readable code prefix for structured log parsing. | |

**User's choice:** message only
**Notes:** None.

---

## Which Warnings to Print

| Option | Description | Selected |
|--------|-------------|----------|
| WARN-severity only | Print only severity='WARN'. Empty output when all pass. | ✓ |
| All 3 (OK and WARN) | Print all 3 checks regardless of severity. | |

**User's choice:** WARN-severity only
**Notes:** Matches success criteria "prints nothing when no warnings."

---

## Flag Combination

| Option | Description | Selected |
|--------|-------------|----------|
| Exclusive — one flag at a time | Mutually exclusive argparse group. | |
| Combinable — print each requested field | `--name --serial` prints both. | ✓ |

**User's choice:** Combinable
**Notes:** None.

---

## Output Order When Combining

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed order: name, serial, warnings | Always name → serial → warnings regardless of input order. | ✓ |
| Order as typed on command line | Prints in flag order. | |

**User's choice:** Fixed order
**Notes:** Predictable for scripts parsing the output.

---

## Collection Scope Per Flag

| Option | Description | Selected |
|--------|-------------|----------|
| Targeted — collect only what's needed | --name skips WMI; --serial runs hardware only; --warnings runs full pipeline. | ✓ |
| Always full pipeline | Always run collect_all() regardless of flag. | |

**User's choice:** Targeted collection
**Notes:** Combined flags use union of required collection.

---

## --serial When Unavailable (None)

| Option | Description | Selected |
|--------|-------------|----------|
| Print 'Unknown' | Consistent with character sheet fallback. Exit 0. | ✓ |
| Print nothing | Empty output. Exit 0. | |
| Exit non-zero | Signal collection failure explicitly. | |

**User's choice:** Print 'Unknown', exit 0
**Notes:** None.

---

## Claude's Discretion

- argparse library choice (stdlib, no discussion needed)
- `--help` format (argparse handles natively)

## Deferred Ideas

None — discussion stayed within phase scope.
