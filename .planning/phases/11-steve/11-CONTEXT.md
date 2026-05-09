# Phase 11: Steve - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `--name`, `--serial`, `--warnings`, and `--help` CLI flags to `main.py`. Each targeted flag outputs a specific field to stdout and exits immediately with code 0. No flags → normal full character sheet pipeline runs unchanged (no regression).

</domain>

<decisions>
## Implementation Decisions

### CLI Design
- **D-01:** Flags are combinable — `--name --serial` prints both fields; no mutually exclusive group in argparse
- **D-02:** Output order when combining is fixed: name → serial → warnings (regardless of order typed on command line)
- **D-03:** No flags → existing full character sheet pipeline runs unchanged; all existing tests continue to pass

### `--warnings` Output
- **D-04:** Print only WARN-severity warnings — one bare `message` string per line
- **D-05:** When all checks pass (no WARN-severity), prints nothing (empty stdout)
- **D-06:** OK-severity Warning objects are NOT printed

### `--serial` Fallback
- **D-07:** When `serial_number` is None (Mac platform or WMI failure), print `Unknown` and exit 0

### Collection Scope (Targeted)
- **D-08:** `--name` only: skip `collect_all()` entirely — `socket.gethostname()` is sufficient
- **D-09:** `--serial` only: run hardware collection only (not full `collect_all()`)
- **D-10:** `--warnings` only: run full `collect_all()` then `evaluate_warnings()`
- **D-11:** Combined flags use the union of required collection — e.g. `--name --warnings` runs full `collect_all()`

### Claude's Discretion
- Use stdlib `argparse.ArgumentParser` — no library decision needed
- `--help` is handled natively by argparse; no custom implementation

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Files
- `main.py` — Entry point; argparse and targeted collection branch go here; currently no argument parsing
- `models.py` — `Warning` dataclass (code, severity, message, detail); `AuditReport.serial_number` field
- `health_checks.py` — `evaluate_warnings(report)` returns exactly 3 Warning objects; filter severity='WARN' for `--warnings` output
- `collectors/windows/hardware.py` — `_collect_serial_number()` at line 121; called from `collect_hardware()`

### Project Constraints
- `CLAUDE.md` — `sys.executable.parent` output path constraint, PKG-02 no host writes, `isatty()` guard
- `.planning/ROADMAP.md` — Phase 11 success criteria (CLI-01)

No external ADRs for this phase — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `socket.gethostname()` — already called at top of `main()` before `collect_all()`; free for `--name`
- `evaluate_warnings(report)` — pure function returning exactly 3 Warning objects; filter `severity == 'WARN'`
- `AuditReport.serial_number` — populated by hardware collection; may be None
- `Warning.message` — human-readable one-liner; this is the string `--warnings` prints

### Established Patterns
- `sys.stdin.isatty()` guard — already in `main.py` for headless/SYSTEM execution; CLI flag mode must not prompt
- `[SUMMARY]` stdout line — printed after every full run; suppress in CLI flag mode (targeted output only)
- Exit codes: `sys.exit(1)` used for write failures; CLI flag paths exit 0 on success

### Integration Points
- `main.py` `main()` function — add argparse at the top, branch before `collect_all()` call
- No changes to collectors, renderer, models, or health_checks needed

</code_context>

<specifics>
## Specific Ideas

No specific references — open to standard argparse implementation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-steve*
*Context gathered: 2026-05-08*
