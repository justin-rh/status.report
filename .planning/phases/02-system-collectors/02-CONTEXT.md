# Phase 2: System Collectors - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement Windows collectors that populate an AuditReport instance with hardware facts (CPU model, RAM, disk capacity/free, OS version/build, current user) and local user profiles enumerated from the registry. Graceful degradation is the critical behavior: the tool must always produce an AuditReport without crashing, even when running as a standard user or when WMI is unavailable. Rendering, app detection, and main.py wiring are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Degradation Pattern
- **D-01:** When a collector call fails, the affected AuditReport field stays `None` (already the model default for all hardware fields). The failure reason is appended to `collection_errors` as a string. No field ever holds a string sentinel like `"Unavailable"` — that display decision belongs to the renderer.
- **D-02:** When a whole collector subsystem fails (e.g., `wmi` module cannot import), all fields that subsystem would have populated stay `None`, and a single error message is appended to `collection_errors`. No per-field error entries for a single root cause.

### User Profile Format
- **D-03:** `local_profiles` contains usernames only — the last path segment of each profile path (e.g., `C:\Users\john.doe` → `"john.doe"`).
- **D-04:** System SIDs are filtered out before populating `local_profiles`: S-1-5-18 (SYSTEM), S-1-5-19 (LOCAL SERVICE), S-1-5-20 (NETWORK SERVICE). Human-visible profiles including Default and Public are retained.

### Library-to-Field Assignment
- **D-05:** `psutil` is primary for RAM, disk capacity/free, and current user. These work at standard user privilege with no elevation.
- **D-06:** `wmi` is used only for `cpu_model` (via `Win32_Processor.Name`). If the wmi module fails to import or the query fails, `cpu_model` stays `None` and an error is logged to `collection_errors`.
- **D-07:** `os_version` and `os_build` come from `platform` stdlib (`platform.release()` and `platform.version()`). Zero dependencies, always works, no elevation required.
- **D-08:** `local_profiles` is enumerated from `winreg` via `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList`. Each SID subkey's `ProfileImagePath` value is read and the username extracted.

### Collector Structure
- **D-09:** `collectors/windows/hardware.py` contains two functions: `collect_hardware(report: AuditReport) -> None` and `collect_profiles(report: AuditReport) -> None`. Both mutate the AuditReport in place following the same in-place pattern as the existing stub structure.
- **D-10:** `collectors/__init__.py` exposes `collect_all(report: AuditReport) -> None` which calls `collect_hardware` then `collect_profiles` in order.
- **D-11:** Phase 2 delivers the collectors only. `main.py` wiring (calling `collect_all`, then renderer, then writer) is deferred to a later phase when the full pipeline is assembled.

### Claude's Discretion
- Exact `platform` API calls for OS version/build (e.g., `platform.version()` vs `platform.uname()` internals) — any reliable stdlib approach is acceptable.
- Whether `current_user` comes from `os.environ.get('USERNAME')` or `psutil.users()` — Claude picks the most reliable option for the context (frozen exe, standard user).
- Test structure for collectors: how to mock WMI and winreg in unit tests without real Windows APIs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Technical Constraints
- `CLAUDE.md` — Critical constraints: `--onedir` only, `Win32_Product` prohibited, output path from `sys.executable`, `winreg` for app detection, stack versions (psutil 6.x, wmi 1.5.1, winreg stdlib).

### Data Contract
- `models.py` — AuditReport field names and types (all hardware fields are `str | None` or `float | None`, `local_profiles: list[str]`). These are locked — Phase 2 must populate exactly these fields, no new fields added to AuditReport in this phase.

### Requirements
- `.planning/REQUIREMENTS.md` §COLL-02 — Hardware stats requirement: CPU model, total RAM, disk capacity/free, OS version and build.
- `.planning/REQUIREMENTS.md` §COLL-03 — User profile enumeration requirement: all local user profiles, not just the currently logged-in user.
- `.planning/ROADMAP.md` §Phase 2 — Success criteria (4 items): standard user hardware collection, registry-based profile enumeration, graceful degradation to "Unavailable" on WMI failure, output path from `sys.executable`.

### Phase 1 Established Patterns
- `.planning/phases/01-models-and-hostname-parser/01-CONTEXT.md` §Established Patterns — CollectionResult envelope, platform-swappable collector architecture, never-raise-across-layer-boundaries rule.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `models.py` — AuditReport dataclass with all hardware fields pre-defined (`cpu_model`, `ram_gb`, `disk_total_gb`, `disk_free_gb`, `os_version`, `os_build`, `current_user`, `local_profiles`, `collection_errors`). Phase 2 populates these; no schema changes needed.
- `collectors/__init__.py` — Stub file exists. Phase 2 adds `collect_all()` here.
- `collectors/windows/__init__.py` — Stub directory exists. Phase 2 adds `hardware.py` here.
- `collectors/base.py` — Comment stub only, no interface to implement.

### Established Patterns
- Error handling: `CollectionResult(value, error)` envelope defined in Phase 1 — collectors may use this internally for sub-operations, but the in-place mutation pattern (`collect_hardware(report)`) is the top-level interface.
- Never raise across layer boundaries — all exceptions caught inside collector functions, degradation written to `collection_errors`.

### Integration Points
- `AuditReport` is passed by reference through the collector chain — `collect_all(report)` mutates it directly.
- Phase 3 (renderer) reads all AuditReport hardware fields and must handle `None` for any field — that's the degradation contract Phase 2 establishes.

</code_context>

<specifics>
## Specific Ideas

No specific references — open to standard approaches within the locked library split.

</specifics>

<deferred>
## Deferred Ideas

- Minimal `main.py` for early end-to-end validation — considered but deferred; full pipeline wiring happens when renderer and writer are ready.
- Per-field error granularity in `collection_errors` — considered; rejected in favor of one message per failed subsystem for simplicity.

</deferred>

---

*Phase: 02-system-collectors*
*Context gathered: 2026-05-04*
