# Phase 15: Extended CLI Flags - Research

**Researched:** 2026-05-18
**Domain:** Python argparse / CLI extension, JSON serialization, app detection wiring
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**--output Flag**
- D-01: `--output <path>` overrides the default `logs/` destination. Both HTML and JSON (when `--json` is also passed) are written to this path.
- D-02: The path is accepted as-is; no host-path validation is performed. IT staff are trusted operators.
- D-03: ROADMAP SC2 (host-path rejection) REMOVED — `--output` writes to any writable path. Planner MUST update ROADMAP.md Phase 15 success criteria to remove SC2's rejection requirement.

**--json Flag**
- D-04: `--json` in full-pipeline mode writes a JSON file alongside the HTML report. JSON filename mirrors the HTML filename with `.json` extension (same base name, same uniqueness counter logic).
- D-05: `--json` overrides targeted CLI flags (`--name`, `--serial`, `--warnings`) — full pipeline runs regardless. The targeted output from those flags does NOT also print.
- D-06: `[SUMMARY]` line still prints to stdout when `--json` runs the full pipeline.
- D-07: Serialization: `json.dumps(dataclasses.asdict(report), indent=2)` with `default=str` fallback. All nested dataclasses serialize via `asdict()`.

**--app Flag**
- D-08: `--app <name>` runs only the app-detection pipeline for one named app. No `collect_all()`, no HTML or JSON report written.
- D-09: App name lookup is case-insensitive substring/contains match against `AppStatus.name` in `APP_SPECS`. First match wins.
- D-10: First match wins — returns the first `APP_SPECS` entry whose `name` field contains the query string (case-insensitive). Sub-apps not included in top-level lookup.
- D-11: If no app matches: print `"Unknown app: <name>. Known apps: NinjaOne, CrowdStrike Falcon, ..."` to stderr, exit code 1.
- D-12: Single-line stdout (no `--json`): `"<canonical_name>: installed (<version>)"` or `"<canonical_name>: not installed"`. Include version when available; include service_state for CrowdStrike.
- D-13: `--app <name> --json` writes `json.dumps(dataclasses.asdict(app_status), indent=2)` to stdout (raw `AppStatus` dict, no wrapper). No files written.
- D-14: `--app` runs only the Windows or Mac app collector for the matched app — same detection logic as `collect_apps()`, scoped to a single spec entry.

**Flag Interaction Summary**
- `--json` (alone or with `--output`): full pipeline, write HTML + JSON, print `[SUMMARY]`
- `--app <name>`: single-app stdout, exit, no reports
- `--app <name> --json`: single-app JSON to stdout, exit, no reports
- `--json` + `--name`/`--serial`/`--warnings`: `--json` overrides, full pipeline runs
- `--output <path>` + any pipeline mode: redirect all file output to `<path>`

### Claude's Discretion
- JSON `default=str` fallback for any unexpected non-serializable types in `dataclasses.asdict()` output
- Exact formatting when CrowdStrike `service_state` is included in the single-line `--app` output
- Whether `--app` collection runs `collect_hardware()` first (for context) or only `collect_apps()` for the single app
- Test fixture structure for `--app` not-found and `--app --json` paths

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OUT-V3-01 | `--json` flag serializes full `AuditReport` to a JSON file in `logs/` alongside the HTML report; uses `dataclasses.asdict()` + `json.dumps()` | Verified: `dataclasses.asdict()` handles all nested dataclasses (AuditReport, ParsedHostname, AppStatus, VendorUpdateStatus, Warning) cleanly. `json.dumps` with `default=str` handles None safely. |
| OUT-V3-02 | `--output <path>` flag overrides the default `logs/` destination for HTML and JSON output | NOTE: REQUIREMENTS.md still lists the host-path validation clause, but CONTEXT.md D-02/D-03 removes it. Planner must update ROADMAP SC2 and treat this requirement as "path override only, no validation." |
| CLI-V3-01 | `--app <name>` runs only the app-detection pipeline for one named app; `--app + --json` produces single-app JSON blob to stdout; case-insensitive name matching | Verified: substring match logic confirmed in test run. `APP_SPECS` has 9 Windows entries; MAC_APP_SPECS has 7 entries. `_detect_one_app()` is the callable to scope. |
</phase_requirements>

---

## Summary

Phase 15 adds three new argparse flags to `main.py` with focused, well-defined semantics. The codebase is well-prepared: the existing `_run_cli()` pattern from Phase 11 establishes the fork-before-pipeline idiom; `dataclasses.asdict()` is verified to serialize the full `AuditReport` graph cleanly including the new `VendorUpdateStatus` nested dataclass added in Phase 14; and `APP_SPECS`/`MAC_APP_SPECS` are config-driven tables whose `_detect_one_app()` functions can be called per-spec without modification.

The primary implementation work is in `main.py`: adding three new `parser.add_argument()` calls, expanding the `cli_mode` detection logic to include `--app`, inserting a `--json` override check before the existing `cli_mode` branch, wiring `--output` as a `logs_dir` override, and writing the `--app` handler function. The JSON file write after HTML write follows the exact same uniqueness counter pattern already in place.

The one planner action beyond code changes is updating ROADMAP.md Phase 15 SC2: per D-02/D-03, host-path rejection is removed and `--output` accepts any writable path.

**Primary recommendation:** Implement in one plan — all three flags touch `main.py` and the test file `test_main.py`; splitting into two plans offers no isolation benefit for this scope.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Flag parsing (`--json`, `--output`, `--app`) | CLI entry point (`main.py`) | — | argparse lives entirely in main.py; no other layer parses argv |
| JSON serialization of AuditReport | CLI entry point (`main.py`) | models.py (data contract) | `json.dumps(dataclasses.asdict(...))` called at the write site in main(); models.py defines the dataclass structure |
| Output path override (`--output`) | CLI entry point (`main.py`) | — | `logs_dir` is set in main(); `--output` replaces that assignment |
| Single-app detection (`--app`) | CLI entry point (`main.py`) calling `collectors/windows/apps.py` or `collectors/mac/apps.py` | — | main.py does the platform dispatch; the per-spec `_detect_one_app()` function does the detection |
| App name lookup / error message | CLI entry point (`main.py`) | `APP_SPECS` / `MAC_APP_SPECS` (lookup source) | The match loop runs in main(); spec names come from the collectors |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `argparse` | stdlib | CLI flag parsing | Already in use (Phase 11); no new dep |
| `dataclasses.asdict` | stdlib | Serialize AuditReport to dict | Verified clean on full graph including VendorUpdateStatus and nested AppStatus |
| `json` | stdlib | Serialize dict to JSON string / file | stdlib; `default=str` handles edge cases |
| `pathlib.Path` | stdlib | Output path manipulation | Already used throughout main.py for `logs_dir` and file write |

No new pip dependencies required for this phase. [VERIFIED: codebase grep + interactive test run]

---

## Architecture Patterns

### System Architecture Diagram

```
argv
  |
  v
parser.parse_args()
  |
  +--[--app present]-------> _run_cli_app(args)
  |                               |
  |                         platform dispatch
  |                         (sys.platform == "darwin")
  |                               |
  |                        _detect_one_app(spec, report)
  |                               |
  |                    [--json]   |   [no --json]
  |                       |       |       |
  |               JSON to stdout  |  single-line to stdout
  |                               |
  |                           sys.exit(0 or 1)
  |
  +--[--json overrides --name/--serial/--warnings]
  |       |
  |  full pipeline (collect_all + evaluate_warnings + render_html)
  |       |
  |   write HTML to logs_dir (or --output path)
  |   write JSON to same dir, same base name + .json
  |   print [SUMMARY] to stdout
  |
  +--[cli_mode: --name/--serial/--warnings without --json]
  |       |
  |  existing _run_cli(args)  [Phase 11 — unchanged]
  |       |
  |   sys.exit(0)
  |
  +--[no flags]
          |
     existing full pipeline  [unchanged]
```

### Recommended Project Structure
No new files required. All changes are in:
```
main.py                          # +3 add_argument, expanded cli_mode, --app handler, --json/--output wiring
tests/test_main.py               # +7-9 new test functions covering all three flags
```

### Pattern 1: Flag Override Check (--json beats --name/--serial/--warnings)

**What:** Before the existing `cli_mode` branch, check if `--json` is present. If so, bypass `cli_mode` and continue to the full pipeline. This is the correct placement because `cli_mode` is set before the branch.

**When to use:** Any time a new flag must supersede a set of existing flags.

**Example:**
```python
# Source: main.py (existing pattern extended)
cli_mode = args.name or args.serial or args.warnings
if args.app:
    _run_cli_app(args)  # new: exits before cli_mode check
    return
if cli_mode and not args.json:   # D-05: --json overrides cli_mode flags
    _run_cli(args)
    return
# full pipeline continues...
```
[VERIFIED: codebase read of main.py]

### Pattern 2: Uniqueness Counter for JSON File (mirrors HTML)

**What:** After resolving `html_path` via the existing counter loop, derive the JSON path from the same base name.

**When to use:** Whenever a second output file must be co-located with the HTML report.

**Example:**
```python
# Source: main.py lines 153-157 (existing HTML uniqueness counter)
# After the loop resolves output_path (HTML):
json_path = output_path.with_suffix(".json")
# No separate uniqueness loop needed — HTML counter already resolved uniqueness;
# a .json sibling with same stem will not collide.
```
[VERIFIED: codebase read; `.with_suffix()` is stdlib Path method]

### Pattern 3: Per-spec App Detection for --app

**What:** `_detect_one_app(spec, report)` in both `collectors/windows/apps.py` and `collectors/mac/apps.py` takes a single spec dict and a minimal AuditReport, appends one AppStatus to `report.apps`. The `--app` handler creates a throwaway AuditReport, calls `_detect_one_app` for the matched spec, then reads `report.apps[0]`.

**When to use:** Any time only one app needs to be detected without the full pipeline.

**Example:**
```python
# Source: collectors/windows/apps.py (verified)
from models import AuditReport, AppStatus
import datetime, socket
from parsers.name_parser import parse_hostname

report = AuditReport(
    hostname=socket.gethostname(),
    parsed_hostname=parse_hostname(socket.gethostname()),
    timestamp=datetime.datetime.now().isoformat(),
)
# platform dispatch
if sys.platform == "darwin":
    from collectors.mac.apps import _detect_one_app, MAC_APP_SPECS as specs
else:
    from collectors.windows.apps import _detect_one_app, APP_SPECS as specs

try:
    _detect_one_app(spec, report)
except Exception as exc:
    report.collection_errors.append(str(exc))
    report.apps.append(AppStatus(name=spec["name"], installed=False, error=str(exc)))

app_status = report.apps[0]
```
[VERIFIED: codebase read of both collectors]

### Pattern 4: App Name Lookup (case-insensitive substring match)

**What:** Iterate the spec list, check if `query.lower()` is `in spec["name"].lower()`. First match wins. If no match, write error to stderr and exit 1.

**Example:**
```python
# Source: derived from APP_SPECS structure (verified)
def _find_app_spec(query: str, specs: list[dict]) -> dict | None:
    q = query.lower()
    for spec in specs:
        if q in spec["name"].lower():
            return spec
    return None

spec = _find_app_spec(args.app, specs)
if spec is None:
    known = ", ".join(s["name"] for s in specs)
    print(f"Unknown app: {args.app}. Known apps: {known}", file=sys.stderr)
    sys.exit(1)
```
[VERIFIED: test run confirmed match logic for "ninjaone", "NINJAONE", "crowdstrike", "zoom"]

### Pattern 5: Single-line --app Output Format (D-12, Claude's discretion resolved)

**What:** Format is `"<name>: installed (<detail>)"` or `"<name>: not installed"`. The detail field shows `version` prefixed with `v` if present, or `service_state` if version is None but service_state is present (CrowdStrike case). If neither, omit the parens.

**Recommendation (Claude's discretion):**
- Has version → `"NinjaOne: installed (v5.3.1)"`
- No version, has service_state → `"CrowdStrike Falcon: installed (Automatic)"`
- Neither → `"Zscaler: installed"`
- Not installed → `"MERP: not installed"`

This matches the spec example in CONTEXT.md: `"NinjaOne: installed (v5.3.1)"` and `"CrowdStrike Falcon: installed (Running)"`.

[VERIFIED: CONTEXT.md D-12 + codebase field names in models.py]

### Anti-Patterns to Avoid

- **Calling `collect_all()` in `--app` mode:** D-08 explicitly scopes to app-only detection. `collect_all()` also runs hardware, profiles, vendor update, and health collectors — wrong scope, wrong cost.
- **Writing `--app` output to a file:** D-08/D-13 both specify stdout only; no files written in `--app` mode.
- **Printing `[SUMMARY]` in `--app` mode:** D-12/D-13 specify single-line / JSON to stdout only. `[SUMMARY]` only prints in full-pipeline mode (D-06).
- **Adding `--app` to the `cli_mode` boolean:** `cli_mode` controls Phase 11 flags. `--app` must be checked and handled BEFORE the `cli_mode` branch, not folded into it. This keeps Phase 11 behavior intact (D-03 from Phase 11).
- **Separate uniqueness counter loop for JSON path:** The HTML loop already resolves the base name's uniqueness. Use `.with_suffix(".json")` after the loop, not a second `while` loop.
- **`--output` validation / host-path rejection:** D-02/D-03 explicitly remove this. Do not implement the rejection logic that REQUIREMENTS.md OUT-V3-02 originally described.
- **MAC_APP_SPECS vs APP_SPECS mismatch:** Mac specs do NOT include Zscaler, MERP, Microsoft 365 (sub-apps), Google Chrome Keeper sub-app, or Claude Code sub-app. The `--app` lookup must use the platform-correct spec list to avoid false "not found" errors on Mac.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization of dataclasses | Custom `to_dict()` methods | `dataclasses.asdict()` | stdlib; handles nesting automatically; already sufficient (verified) |
| Non-serializable type fallback | Custom type checkers | `json.dumps(..., default=str)` | stdlib one-liner; handles any edge case including datetime, Path objects |
| CLI argument parsing | Manual `sys.argv` slicing | `argparse` (already used) | Already in main.py; `add_argument` is the correct extension point |
| App name lookup | New lookup data structure | Inline loop over existing `APP_SPECS` | Specs already loaded; no index needed for 9 entries |

---

## Common Pitfalls

### Pitfall 1: MAC_APP_SPECS Has Different App Names Than APP_SPECS

**What goes wrong:** `--app zoom` on Mac fails to match because Mac uses `"Zoom"` (MAC_APP_SPECS) while Windows uses `"Zoom Workplace"` (APP_SPECS). The lookup query `"zoom"` is contained in both, so this specific example works — but other discrepancies (e.g., no `"Zscaler"` in MAC_APP_SPECS, no `"MERP"`) can produce different "known apps" lists.

**Why it happens:** The two spec lists were built independently for platform-specific detection methods; canonical names were not required to match across platforms.

**How to avoid:** Platform-dispatch before building the spec list for lookup. The error message "Known apps:" should list only the platform-correct specs.

**Warning signs:** `--app zscaler` returning "Unknown app" on Windows when Zscaler IS in the Windows specs — caused by accidentally importing MAC_APP_SPECS on Windows.

[VERIFIED: codebase read of both spec lists]

### Pitfall 2: --json Flag Must Not Trigger cli_mode Path

**What goes wrong:** If `args.json` is included in the `cli_mode` boolean (`cli_mode = args.name or args.serial or args.warnings or args.json`), the code enters `_run_cli()` which exits early without running the full pipeline — producing no JSON or HTML output.

**Why it happens:** `--json` looks like a "targeted output" flag but it is a full-pipeline output modifier (D-04/D-05 in Phase 15 CONTEXT.md).

**How to avoid:** Keep `cli_mode` assignment unchanged from Phase 11. Check `args.json` AFTER the `cli_mode` branch to override it. The correct check is: `if cli_mode and not args.json: _run_cli(args)`.

[VERIFIED: main.py read, line 106-108]

### Pitfall 3: --output Must Override logs_dir, Not output_path

**What goes wrong:** Setting `output_path = Path(args.output) / f"{base_name}.html"` directly skips the `logs_dir.mkdir()` call, which would fail if the target directory doesn't exist.

**Why it happens:** Copy-paste from the `output_path` assignment at line 153 without preserving the `mkdir` call.

**How to avoid:** Override `logs_dir` early (after the `usb_root` block), then let the existing `mkdir` + filename construction + uniqueness loop run against the new `logs_dir`. This keeps the write path self-consistent.

[VERIFIED: main.py lines 146-157]

### Pitfall 4: _detect_one_app Is a Private Function

**What goes wrong:** `from collectors.windows.apps import _detect_one_app` triggers linter warnings and may confuse future maintainers. Technically it works.

**Why it happens:** The function is prefixed `_` by convention (internal to the module).

**How to avoid:** Accept the import as intentional internal use; add a comment referencing D-14. Alternatively, the planner may opt to inline the `--app` handling directly in `main.py` using a thin wrapper. Either approach is acceptable — document the rationale in the plan.

[VERIFIED: codebase read]

### Pitfall 5: JSON File Written Even When HTML Write Fails

**What goes wrong:** If the HTML write raises `PermissionError` or `OSError`, the existing error handlers call `sys.exit(1)`. If the JSON write is placed BEFORE the HTML write (or not guarded by the same try/except), it may succeed while HTML fails — leaving a JSON orphan without a matching HTML report.

**Why it happens:** Inserting the JSON write in the wrong position relative to the HTML error handlers.

**How to avoid:** Write HTML first, then write JSON within the same try/except block. If HTML write raises, JSON write never executes. Consistent with the existing single-point error handling in main.py.

[VERIFIED: main.py lines 161-173]

---

## Code Examples

### Full AuditReport JSON serialization (verified)
```python
# Source: verified via interactive test run on this codebase
import dataclasses, json
from models import AuditReport

# All nested dataclasses (ParsedHostname, AppStatus, VendorUpdateStatus, Warning)
# serialize cleanly with no additional helpers.
payload = json.dumps(dataclasses.asdict(report), indent=2, default=str)
json_path.write_text(payload, encoding="utf-8")
```

### Single AppStatus JSON serialization (--app --json path, verified)
```python
# Source: verified via interactive test run
import dataclasses, json
from models import AppStatus

payload = json.dumps(dataclasses.asdict(app_status), indent=2)
print(payload)
# No sys.exit() needed — function returns normally; caller exits
```

### App name lookup with error (D-09, D-11, verified)
```python
# Source: derived from APP_SPECS (verified test run)
import sys

def _find_app_spec(query: str, specs: list[dict]) -> dict | None:
    q = query.lower()
    for spec in specs:
        if q in spec["name"].lower():
            return spec
    return None

spec = _find_app_spec(args.app, specs)
if spec is None:
    known = ", ".join(s["name"] for s in specs)
    print(f"Unknown app: {args.app}. Known apps: {known}", file=sys.stderr)
    sys.exit(1)
```

### Single-line --app output (D-12, Claude's discretion applied)
```python
# Source: CONTEXT.md D-12 + models.py AppStatus fields (verified)
def _format_app_status_line(app_status: AppStatus) -> str:
    if not app_status.installed:
        return f"{app_status.name}: not installed"
    if app_status.version:
        return f"{app_status.name}: installed (v{app_status.version})"
    if app_status.service_state:
        return f"{app_status.name}: installed ({app_status.service_state})"
    return f"{app_status.name}: installed"
```

### --output path override (D-01, verified pattern)
```python
# Source: main.py lines 146-151 (existing logs_dir pattern)
# Override logs_dir before mkdir + filename construction:
if args.output:
    logs_dir = Path(args.output)
else:
    logs_dir = usb_root / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)
# ... existing base_name, output_path, uniqueness counter unchanged ...
```

---

## State of the Art

No external library changes in this phase. All tooling is stdlib. The phase extends existing patterns.

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| cli_mode = name or serial or warnings | cli_mode unchanged; --app checked before branch; --json overrides cli_mode | Phase 15 | No regression to Phase 11 flags |
| HTML only output | HTML + optional JSON sibling | Phase 15 | Same write path, same error handling |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_detect_one_app` is safe to call from `main.py` with a minimal AuditReport (no hardware fields populated) | Pattern 3 / Pitfall 4 | If `_detect_one_app` reads hardware fields (it doesn't — verified in code read), the minimal report would produce wrong results |
| A2 | MAC_APP_SPECS `"Zoom"` entry will still match `--app zoom` on Mac (contains check: "zoom" in "Zoom") | Pitfall 1 | If someone renames it to "Zoom Workplace" on Mac to match Windows, the mismatch notes in Pitfall 1 become accurate instead of partial |

Both assumptions are LOW risk based on verified code reads. No user confirmation required.

---

## Open Questions

1. **collect_hardware() in --app mode (Claude's discretion)**
   - What we know: D-14 says `--app` runs only the app-detection pipeline. D-14 also says "same detection logic as `collect_apps()`, but scoped to a single spec entry."
   - What's unclear: `collect_hardware()` is not needed for app detection (no hardware fields are read in either `_detect_one_app`). But the CONTEXT.md marks it as Claude's discretion whether to call it "for context."
   - Recommendation: Do NOT call `collect_hardware()` in `--app` mode. It adds WMI calls and latency for no benefit — the detection functions never read hardware fields. This keeps `--app` fast and side-effect-free.

2. **ROADMAP.md SC2 update**
   - What we know: CONTEXT.md D-03 says planner must update ROADMAP.md Phase 15 SC2 to remove the host-path rejection requirement.
   - What's unclear: Whether to reword SC2 entirely or just remove it.
   - Recommendation: Planner should replace SC2 with "Running `scry.exe --output D:\audit_results` writes both HTML and JSON (when `--json` is also passed) to that path." This preserves the test scenario while removing the rejection check.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 15 is purely Python stdlib code changes (`argparse`, `json`, `dataclasses`). No external CLI tools, services, or runtimes beyond the existing Python 3.12 environment.

---

## Validation Architecture

`nyquist_validation` is explicitly `false` in `.planning/config.json` — this section is skipped.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | partial | `--app` query is string-only; no eval/shell execution; safe |
| V6 Cryptography | no | — |

### Notes

- `--output <path>` accepts any path (D-02 explicitly removes validation). PKG-02 (no host writes) is a human/operational constraint, not enforced in code per user decision.
- `--app <name>` performs a case-insensitive substring match on a hard-coded list; no user input reaches any shell command or file path.
- JSON output uses `dataclasses.asdict()` + `json.dumps()` — no template injection surface.

No new security concerns introduced. [VERIFIED: code pattern analysis]

---

## Sources

### Primary (HIGH confidence)
- `main.py` (local codebase read) — full argparse setup, `_run_cli()`, full pipeline, `logs_dir` pattern
- `collectors/windows/apps.py` (local codebase read) — `APP_SPECS` (9 entries), `_detect_one_app()`, `collect_apps()`
- `collectors/mac/apps.py` (local codebase read) — `MAC_APP_SPECS` (7 entries), platform divergence confirmed
- `models.py` (local codebase read) — all dataclass field types; no non-serializable types found
- Interactive Python test run — `dataclasses.asdict()` serialization verified on full AuditReport graph including VendorUpdateStatus and nested AppStatus
- Interactive Python test run — case-insensitive substring match logic verified for all D-09 examples
- `.planning/phases/15-extended-cli-flags/15-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- `.planning/phases/11-steve/11-CONTEXT.md` — Phase 11 CLI decisions confirmed still in effect
- `tests/test_main.py` (local read) — 284 existing tests; test patterns established for patching

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib; no new deps; verified in active Python 3.12 environment
- Architecture: HIGH — code read of all relevant files; patterns verified via interactive test
- Pitfalls: HIGH — derived from direct code inspection of main.py, both spec lists, and CONTEXT.md decisions

**Research date:** 2026-05-18
**Valid until:** 2026-06-18 (stable stdlib; no external deps)
