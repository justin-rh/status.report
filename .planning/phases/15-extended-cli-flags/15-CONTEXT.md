# Phase 15: Extended CLI Flags - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `--json`, `--output <path>`, and `--app <name>` flags to `scry.exe`.

- `--json` (full pipeline): writes `AuditReport` as JSON to `logs/` alongside the HTML report; `[SUMMARY]` line still prints to stdout.
- `--output <path>`: overrides the default `logs/` destination for both HTML and JSON; no host-path validation (see D-03 — roadmap SC2 removed per user decision).
- `--app <name>`: runs only the app-detection pipeline for one named app, prints a single-line result to stdout, exits without generating any report.
- `--app <name> --json`: prints a raw `AppStatus` dict (JSON) to stdout; no files written.

</domain>

<decisions>
## Implementation Decisions

### --output Flag
- **D-01:** `--output <path>` overrides the default `logs/` destination. Both HTML and JSON (when `--json` is also passed) are written to this path.
- **D-02:** The path is accepted as-is; no host-path validation is performed. IT staff are trusted operators.
- **D-03:** ~~ROADMAP SC2 (host-path rejection)~~ **removed** — `--output` writes to any writable path. Planner must update ROADMAP.md success criteria to remove SC2's rejection requirement.

### --json Flag
- **D-04:** `--json` in full-pipeline mode (no `--app`, no `--name`/`--serial`/`--warnings`) writes a JSON file alongside the HTML report. JSON filename mirrors the HTML filename with `.json` extension (same base name, same uniqueness counter logic).
- **D-05:** `--json` **overrides** targeted CLI flags (`--name`, `--serial`, `--warnings`) — when `--json` is present, the full pipeline runs regardless of other flags. The targeted output from those flags does NOT also print.
- **D-06:** `[SUMMARY]` line still prints to stdout when `--json` runs the full pipeline. NinjaOne log capture is unaffected.
- **D-07:** Serialization: `json.dumps(dataclasses.asdict(report), indent=2)` — per OUT-V3-01 spec. All nested dataclasses (`ParsedHostname`, `AppStatus`, `Warning`, `VendorUpdateStatus`) serialize via `asdict()`. Claude's discretion on handling non-serializable edge cases (e.g., custom `default=str` for any unexpected types).

### --app Flag
- **D-08:** `--app <name>` runs only the app-detection pipeline for one named app. No `collect_all()`, no HTML or JSON report written.
- **D-09:** App name lookup is **case-insensitive substring/contains match** against `AppStatus.name` in `APP_SPECS`. Examples:
  - `"ninjaone"` → `"NinjaOne"` ✓
  - `"crowdstrike"` → `"CrowdStrike Falcon"` ✓
  - `"zoom"` → `"Zoom Workplace"` ✓ (first match wins)
- **D-10:** **First match wins** — returns the first `APP_SPECS` entry whose `name` field contains the query string (case-insensitive). Sub-apps are not included in the top-level lookup.
- **D-11:** If no app matches: print `"Unknown app: <name>. Known apps: NinjaOne, CrowdStrike Falcon, ..."` to stderr, exit code 1.
- **D-12:** Single-line stdout format (no `--json`): `"<canonical_name>: installed (<version>)"` or `"<canonical_name>: not installed"`. Include version when available; include service_state for CrowdStrike (e.g., `"CrowdStrike Falcon: installed (Running)"`). Claude's discretion on exact formatting of the service_state field.
- **D-13:** `--app <name> --json` writes `json.dumps(dataclasses.asdict(app_status), indent=2)` to stdout (raw `AppStatus` dict, no wrapper). No files written.
- **D-14:** `--app` runs only the Windows or Mac app collector for the matched app — same detection logic as `collect_apps()`, but scoped to a single spec entry.

### Flag Interaction Summary
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CLI Entry Point
- `main.py` — Full argparse setup, `_run_cli()` function, full pipeline wiring. Read the entire file before adding new flags. All new flag handling slots into or alongside `_run_cli()`.
- `main.py` lines 28–75 — `_run_cli()` function; new `--app` logic extends this function
- `main.py` lines 77–155 — Full pipeline; `--json` and `--output` wiring goes here

### App Detection
- `collectors/windows/apps.py` — `APP_SPECS` list (all canonical app names), `collect_apps()`, `_detect_app()`. The `name` field in each spec is the canonical name for `--app` lookup. Read before implementing D-09/D-10.
- `collectors/mac/apps.py` — Mac equivalent; `--app` must call the right platform collector.

### Data Contract
- `models.py` — `AuditReport`, `AppStatus`, `ParsedHostname`, `Warning`, `VendorUpdateStatus` — all must serialize cleanly via `dataclasses.asdict()`. Read field types before implementing D-07.

### Requirements
- `.planning/REQUIREMENTS.md` §OUT-V3-01, OUT-V3-02, CLI-V3-01 — Full acceptance criteria. Note: OUT-V3-02's host-path rejection requirement is superseded by D-02/D-03 (removed per user decision).

### Prior CLI Context
- `.planning/phases/11-steve/11-CONTEXT.md` — D-01 through D-11; all Phase 11 CLI decisions remain in effect. New flags must not break `--name`, `--serial`, `--warnings` behavior when used without `--json`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_run_cli(args)` in `main.py` — existing handler for targeted CLI flags; `--app` logic extends this function
- `APP_SPECS` in `collectors/windows/apps.py` — config-driven table; `name` field is the lookup target for `--app`
- `collect_apps()` / `_detect_app()` in `collectors/windows/apps.py` — single-app detection can be extracted from `_detect_app(spec, report)` call
- `dataclasses.asdict()` — stdlib; no new dependency for JSON serialization

### Established Patterns
- All collector functions mutate `AuditReport` in place, never raise — `--app` flow must follow this: wrap detection in try/except, append to `report.collection_errors` on failure
- Output path: `Path(sys.executable).parent / "logs"` (D-02 from Phase 3/5) — `--output` replaces `logs_dir` assignment in `main()`
- `[SUMMARY]` line printed unconditionally after full pipeline runs (NINJA-02 compliance)
- Uniqueness counter: `while output_path.exists(): counter++` — JSON file should follow same pattern

### Integration Points
- `main.py` `parser.add_argument(...)` block — add `--json`, `--output`, `--app` here
- `main.py` `cli_mode` detection logic (line ~83) — must expand to include `--app`; `--json` does NOT set cli_mode
- `main.py` full pipeline (after `cli_mode` check) — `--json` and `--output` handled here
- `logs_dir` assignment (line ~121) — `--output` replaces this value when provided

</code_context>

<specifics>
## Specific Ideas

- `--app` single-line format confirmed: `"NinjaOne: installed (v5.3.1)"` — name, colon, status, version in parens
- `--app --json` confirmed: raw `AppStatus` dict (no wrapper), `dataclasses.asdict()` output to stdout
- SC4 case-insensitive examples from roadmap ("NinjaOne", "ninjaone", "NINJAONE") are handled by the contains-match (D-09) since "ninjaone" is contained in "NinjaOne" case-insensitively
- ROADMAP SC2 to be removed by planner — `--output` writes anywhere; no rejection logic to implement

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-extended-cli-flags*
*Context gathered: 2026-05-18*
