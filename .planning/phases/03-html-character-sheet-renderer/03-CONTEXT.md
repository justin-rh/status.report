# Phase 3: HTML Character Sheet Renderer - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a Jinja2 HTML renderer that takes a mock `AuditReport` instance and produces a D&D/RPG-styled HTML character sheet, then writes it to the output path derived from `sys.executable`. Phase scope is the renderer and writer only — no live collector calls, no app detection logic. Mock AuditReport data is used for development and test. Template must be loaded via `importlib.resources` so it works inside a PyInstaller bundle.

</domain>

<decisions>
## Implementation Decisions

### Character Sheet Header Fields
- **D-01:** The "class" field shows `device_type` verbatim (e.g., "Warehouse Workstation", "User-Assigned Laptop", "Unknown"). No fantasy renaming.
- **D-02:** The "realm" field shows the parsed city name verbatim (e.g., "Phoenix"). No renaming.
- **D-03:** The "guild" field shows `department` for warehouse devices, `company_code` for user-assigned laptops. When both are None (Unknown device type), show `—`.
- **D-04:** The "station" field shows the raw station number (e.g., `3`). For device types where `station` is None, show `—`.

### Stat Block
- **D-05:** Use plain hardware labels — CPU, RAM, Disk. No D&D stat names (STR/CON/HP). The IT-readable label IS the stat name.
- **D-06:** Stat values are raw hardware values: CPU model string, RAM as `X.X GB`, disk capacity as `X GB total`.
- **D-07:** Disk HP bar = `disk_free_gb / disk_total_gb` percentage, displayed as a proportional bar. Full bar = empty disk, depleted bar = nearly full. Label below bar shows `X GB free / Y GB total`. Low HP (≤20% free) → bar renders red; medium (≤50% free) → amber; healthy (>50% free) → green.

### Equipment List (App Slots)
- **D-08:** Each app slot shows: app name + installed/missing badge (✓ green / ✗ red) + version string when installed (blank cell when missing).
- **D-09:** Apps with a `service_state` value (e.g., CrowdStrike Falcon) show service state (Running/Stopped) as a small supplementary label beside the version.
- **D-10:** Mock AuditReport for Phase 3 development uses all required apps in mixed installed/missing state — sufficient to test both badge states, version display, and the Quest Incomplete path. App list: NinjaOne, CrowdStrike Falcon, MERP, Word, Excel, Outlook, Teams, OneDrive, Zoom, Chrome, Claude desktop app.

### Quest Status
- **D-11:** Footer shows "QUEST COMPLETE" (green) when all required apps have `installed=True`, or "QUEST INCOMPLETE — X app(s) missing" (red) with a count of missing apps.

### None Field Rendering
- **D-12:** Any hardware field that is `None` renders as an em-dash `—` in muted grey. No row omitted, no "Unavailable" text. Applied consistently to: cpu_model, ram_gb, disk_total_gb, disk_free_gb, os_version, os_build, current_user.
- **D-13:** For the disk HP bar specifically: if `disk_total_gb` is None, the bar renders as a grey empty bar with `—` text rather than crashing or showing 0%.

### Visual Style
- **D-14:** Dark panel aesthetic with colored accents. Dark background (e.g., `#1a1a2e` or similar deep navy/charcoal), white/light-grey body text, colored section headers. App badge colors: green for installed, red for missing. No parchment texture, no serif fonts.

### Template and File Structure
- **D-15:** Jinja2 template lives at `renderer/templates/character_sheet.html`. Loaded via `importlib.resources` using `importlib.resources.files('renderer').joinpath('templates/character_sheet.html')`. This is the PyInstaller-safe approach.
- **D-16:** `renderer/__init__.py` exposes `render_report(report: AuditReport, output_path: Path) -> Path`. Writes HTML file to `output_path / "status_report.html"` and returns the full path. Does not call `sys.executable` itself — caller passes the resolved output path.
- **D-17:** `writers/__init__.py` exposes `write_html(html: str, output_path: Path) -> Path`. Handles the file write. Renderer calls writer; they are separate concerns.

### Claude's Discretion
- Exact CSS framework or approach (inline styles vs `<style>` block vs external CSS bundled into the template) — Claude picks the approach most compatible with PyInstaller (external files are a risk; inline or embedded `<style>` is safer).
- Exact dark colour palette values beyond the general direction (deep navy/charcoal background, white body text, green/red/amber accents for HP and badges).
- Jinja2 filter or macro design for the HP bar, badge rendering, and None → `—` substitution.
- Whether OS version and OS build render as separate rows or combined (e.g., "Windows 10 — Build 19045").
- Whether `local_profiles` renders in the character sheet at all in Phase 3 (it's collected data but wasn't mentioned in the ROADMAP SC layout — Claude can include or omit it in the detail section).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Technical Constraints
- `CLAUDE.md` — Critical constraints: `--onedir` only, `Win32_Product` prohibited, output path from `sys.executable`, Jinja2 via `importlib.resources`. Read before writing any code.

### Data Contract
- `models.py` — AuditReport, ParsedHostname, AppStatus, CollectionResult dataclasses. All hardware fields are `str | None` or `float | None`. `apps: list[AppStatus]`. Renderer reads these fields exactly — no new fields added to AuditReport in Phase 3.

### Requirements
- `.planning/REQUIREMENTS.md` §OUT-01 — HTML character sheet with RPG/D&D aesthetic, functionally readable as IT data without RPG knowledge.
- `.planning/REQUIREMENTS.md` §OUT-02 — HTML file written to `sys.executable` parent directory (flash drive), not `os.getcwd()`.
- `.planning/ROADMAP.md` §Phase 3 — Success criteria (5 items): header fields, stat block, equipment list, output path, importlib.resources template loading.

### Prior Phase Context
- `.planning/phases/02-system-collectors/02-CONTEXT.md` §Integration Points — Phase 2 degradation contract: any hardware field may be None; renderer must handle all None fields without crashing (D-12 above).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `models.py` — AuditReport dataclass fully defined. All fields Phase 3 needs (cpu_model, ram_gb, disk_total_gb, disk_free_gb, os_version, os_build, current_user, local_profiles, apps, parsed_hostname, hostname, timestamp) exist and are typed.
- `AppStatus` — `name`, `installed`, `version`, `service_state` fields match exactly what D-08/D-09 require. No model changes needed.
- `renderer/__init__.py` — Stub file exists with a comment noting it's the Phase 3 home. Phase 3 adds `render_report()` here.
- `writers/__init__.py` — Stub file exists. Phase 3 adds `write_html()` here.

### Established Patterns
- Never raise across layer boundaries (Phase 1 rule). Renderer must not raise on None fields — degrade gracefully per D-12/D-13.
- Output path from `Path(sys.executable).parent` (CLAUDE.md constraint). The renderer receives this path as an argument — it does not resolve it internally.

### Integration Points
- `render_report(report: AuditReport, output_path: Path) -> Path` is the public interface. `main.py` (Phase 5 or earlier wiring phase) will call this after `collect_all()` completes.
- Jinja2 template is a `renderer/` package resource — must be included in `MANIFEST.in` or equivalent so PyInstaller bundles it. This is a packaging concern but must be considered in Phase 3 file placement.

</code_context>

<specifics>
## Specific Ideas

- User confirmed: no fantasy renaming of any field. All labels use real IT terminology (device type, city, department, station number, CPU, RAM, disk). The D&D-style layout and visual aesthetic provide the RPG flavor without obscuring the actual data.
- Color logic for disk HP bar: green >50% free, amber 20–50% free, red ≤20% free. Intuitive: low HP = disk almost full.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-html-character-sheet-renderer*
*Context gathered: 2026-05-04*
