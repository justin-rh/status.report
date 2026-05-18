# Phase 15: Extended CLI Flags - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-18
**Phase:** 15-extended-cli-flags
**Areas discussed:** --output validation, --app output format, --app name matching, --json + existing flags

---

## --output Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Same-drive check | Resolve --output and sys.executable to drive letters; reject if different | |
| Denylist known host roots | Block C:\, %USERPROFILE%, %TEMP%, %SystemRoot% | |
| IT staff can write anywhere | No validation — trust the operator | |
| Remove SC2 from roadmap | Update ROADMAP.md to drop host-path rejection requirement | ✓ |

**User's choice:** Remove SC2 from roadmap — `--output` writes to any writable path, no validation.
**Notes:** User first asked "Why does it matter?" — explained PKG-02 and the ambiguity of USB vs. internal drive letters (E:\, D:\). After clarification, user chose to drop the validation requirement entirely and update the roadmap.

---

## --app Output Format

| Option | Description | Selected |
|--------|-------------|----------|
| Name: status (version) | e.g. "NinjaOne: installed (v5.3.1)" | ✓ |
| Status only | Just "installed" or "not installed" | |
| Key=value | e.g. "NinjaOne=installed" | |

**User's choice:** `"NinjaOne: installed (v5.3.1)"` format — name, colon, status, version in parens when available.
**Notes:** Selected the recommended option with preview. CrowdStrike includes service_state instead of/alongside version.

## --app JSON Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Raw AppStatus dict | dataclasses.asdict() on single AppStatus | ✓ |
| Wrapped object | { "app": "NinjaOne", "status": {...} } | |

**User's choice:** Raw `AppStatus` dict, no wrapper — consistent with how `--json` serializes the full report.

---

## --app Name Matching

| Option | Description | Selected |
|--------|-------------|----------|
| Partial/contains match | Case-insensitive substring match against canonical name | ✓ |
| Exact canonical name only | Case-insensitive but must be exact | |
| Aliases table | Hardcoded lookup table for abbreviations | |

**User's choice:** Partial/contains match — "crowdstrike" matches "CrowdStrike Falcon".

## Ambiguous Match Handling

| Option | Description | Selected |
|--------|-------------|----------|
| First match wins | Return first APP_SPECS entry whose name contains the query | ✓ |
| Error on ambiguous | Print error and list matches if more than one top-level app matches | |
| Print all matches | Print one line per matching app | |

**User's choice:** First match wins — sub-apps excluded from top-level lookup.

## No-Match Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Exit 1 with error message | Print "Unknown app: <name>. Known apps: ..." to stderr, exit 1 | ✓ |
| Print 'not found', exit 0 | Print "<name>: not found" to stdout, exit 0 | |
| Silent exit 1 | No output, just exit code 1 | |

**User's choice:** Exit 1 with error message listing known app names to stderr.

---

## --json + Existing Flags

| Option | Description | Selected |
|--------|-------------|----------|
| --json only applies to full pipeline | --json ignored when --name/--serial/--warnings passed | |
| --json overrides to full pipeline | --json forces full pipeline regardless of other flags | ✓ |
| Error on mixed flags | Combining --json with --name/--serial/--warnings is an argparse error | |

**User's choice:** `--json` overrides to full pipeline — when `--json` is present, full pipeline always runs.

## [SUMMARY] Line with --json

| Option | Description | Selected |
|--------|-------------|----------|
| Keep [SUMMARY] line | Full pipeline always prints [SUMMARY] to stdout | ✓ |
| Suppress [SUMMARY] when --json | No stdout output when --json; clean machine-readable channel | |

**User's choice:** Keep `[SUMMARY]` line — NinjaOne log capture unaffected.

---

## Claude's Discretion

- JSON `default=str` fallback for unexpected non-serializable types
- Exact formatting when CrowdStrike `service_state` is included in single-line output
- Whether `--app` also calls `collect_hardware()` or only app detection
- Test fixture structure for `--app` edge cases

## Deferred Ideas

None — discussion stayed within phase scope.
