# Phase 1: Models and Hostname Parser - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Define the Python data contract (dataclasses: AuditReport, ParsedHostname, AppStatus, CollectionResult) and implement the Master Electronics hostname parser that decodes city, device type, department/serial, company code, and station number from the naming convention. The parser must be testable with no Windows API calls. Hardware collection, app detection, and rendering are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Partial Match Handling
- **D-01:** Device type is determined by segment structure, not by whitelisting individual code values. If the pattern fits, device type is inferred.
- **D-02:** Unrecognized dept code with a valid city + `CITY-DEPT-###` structure → `device_type=Warehouse Workstation`, `dept_code` preserved as the raw unrecognized value.
- **D-03:** Unrecognized company code with a valid city + `CITY-SERIAL-COMPANY` structure → `device_type=User-Assigned Laptop`, `company_code` preserved as the raw unrecognized value.

### City Code Strictness
- **D-04:** Unrecognized city prefix → `device_type=Unknown`, silent. Tool does not attempt to parse the rest of the hostname. IT staff see the Unknown class in the character sheet and know the city code list needs updating.
- **D-05:** Raw hostname is always preserved in ParsedHostname regardless of outcome.

### Department Code Policy
- **D-06:** Any short uppercase segment in position 2 (non-LAP, non-P3, non-numeric serial) qualifies as a warehouse department code. No whitelist enforcement. New IT department codes are accepted automatically by the parser.
- **D-07:** Unit tests use a representative sample of known dept codes (e.g., INV, SHP, REC) plus one test with an unrecognized code to verify pattern-based acceptance. Not one test per known code.

### Unknown Hostname Data Preservation
- **D-08:** Fully unrecognized hostname (e.g., `DESKTOP-XYZ123` — no recognizable city prefix, no `CITY-X-X` structure): `device_type=Unknown`, `raw_hostname` preserved, all other ParsedHostname fields are `None`.
- **D-09:** Near-miss hostname with a recognized city but structure that can't determine device type (e.g., `PHX-BADSTRUCT`, only 2 segments): `city` field is populated (e.g., `city=Phoenix`), `device_type=Unknown`, remaining fields `None`. City prefix matched successfully before structure failed.

### Claude's Discretion
- CollectionResult typing: whether to use `CollectionResult[T]` generic typing or plain untyped is Claude's call — the envelope pattern `(value, error)` is fixed.
- AppStatus field design: `installed`, `version`, `service_state` — Claude selects fields to satisfy Phase 3 (renderer) and Phase 4 (app detection) contracts without re-asking.
- Exact module/file layout within the package (e.g., `models.py` as single file vs. re-exports) — success criteria requires importability from `models.py`; internals are Claude's call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Naming Convention and Constraints
- `CLAUDE.md` — Critical technical constraints: PyInstaller --onedir only, Win32_Product prohibited, output path from sys.executable, winreg for app detection. Read before writing any code.
- `.planning/PROJECT.md` §Naming Convention Reference — Full hostname format table (4 device type patterns), city codes (21), warehouse dept codes (~20).
- `.planning/REQUIREMENTS.md` §COLL-01 and §OUT-03 — The two requirements scoped to Phase 1.
- `.planning/ROADMAP.md` §Phase 1 — Success criteria (5 items): city codes, device types, unknown hostname behavior, test requirements, importable dataclasses.

### Phase 1 Success Criteria (verbatim from ROADMAP.md)
1. `PHX-INV-003` → `city=Phoenix, device_type=Warehouse Workstation, department=INV, station=3`
2. `PHX-ABC123-ME` → `device_type=User-Assigned Laptop, company_code=ME`
3. `DESKTOP-XYZ123` → `device_type=Unknown`, raw hostname preserved, no exception
4. All 21 city codes and known dept codes covered by unit tests (no Windows API calls)
5. AuditReport, ParsedHostname, AppStatus, CollectionResult importable from `models.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. No existing components.

### Established Patterns
- Architecture is decided: `main.py → collectors/ → models.AuditReport → renderer/ → writers/` (from CLAUDE.md)
- Each collector returns `CollectionResult(value, error)` — never raises across layer boundaries
- Platform-swappable collector design: `windows/` vs `mac/` stubs (for future v2 Mac support)

### Integration Points
- `ParsedHostname` will be embedded in `AuditReport` — shape decided here affects every downstream phase
- `AppStatus` will be consumed by Phase 3 (renderer, needs installed/version/badge status) and Phase 4 (app detection, sets the values)
- `CollectionResult` envelope wraps all collector return values — Phase 2 uses it; define it completely here

</code_context>

<specifics>
## Specific Ideas

No specific references — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-models-and-hostname-parser*
*Context gathered: 2026-05-04*
