# Phase 5: Packaging and Distribution - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire `main.py` as the tool's entry point, bundle the complete application with PyInstaller `--onedir`, and validate the resulting `status_report.exe` on a CrowdStrike Falcon-enrolled machine before distribution. Output is distributed as a folder copied to a USB flash drive — no installation required.

</domain>

<decisions>
## Implementation Decisions

### main.py Entry Point
- **D-01:** `main.py` orchestrates the full pipeline: `collect_all(report)` → `render_html(report)` → write HTML to `logs/` subdirectory → open HTML in browser.
- **D-02:** Output path: `Path(sys.executable).parent / "logs" / f"status_{hostname}_{date}.html"`. The `logs/` directory is created with `mkdir(parents=True, exist_ok=True)` if it doesn't exist. This is USB-only — PKG-02 satisfied.
- **D-03:** Filename format: `status_{HOSTNAME}_{DATE}.html` where HOSTNAME is `socket.gethostname()` (or the raw hostname from `AuditReport`) and DATE is `datetime.date.today().isoformat()` (e.g., `status_PHX-INV-003_2026-05-05.html`). Each run produces a unique file — reports accumulate on the USB without overwriting.
- **D-04:** Console window is shown (not `--noconsole`). Verbose progress output:
  ```
  StatusReport — Master Electronics IT Audit Tool
  Collecting hardware info...
  Detecting installed apps...
  Rendering character sheet...
  Saved: D:\logs\status_PHX-INV-003_2026-05-05.html
  Opening in browser...
  Done.
  ```
- **D-05:** Auto-opens the HTML file in the default browser after write (`webbrowser.open(str(output_path))`). OUT-V2-02 pulled into v1 scope — trivial to implement and significantly improves IT staff UX.
- **D-06:** Collector failures print a warning and continue — never `sys.exit` due to a collector failure. Example: `[WARN] CPU model unavailable — WMI not responding.` Character sheet still generated with "Unavailable" values. Only a failed HTML write (disk full, permissions) warrants a top-level error.

### PyInstaller Packaging
- **D-07:** `--onedir` mode only. `--onefile` is explicitly prohibited — quarantined by CrowdStrike Falcon on every enrolled machine (CLAUDE.md constraint).
- **D-08:** Build is defined in `status_report.spec` (checked into the repo). The spec captures: entry point (`main.py`), `--onedir`, hidden imports (`wmi`, `win32com`, `win32api`, `pywintypes`, Jinja2 internals), and data file bundle for `renderer/templates/character_sheet.html` via `--add-data`.
- **D-09:** `build.bat` at repo root provides a one-command reproducible build: activates the venv and runs `pyinstaller status_report.spec`. IT or developers run `build.bat` after future code changes.
- **D-10:** Build output lands in `dist/status_report/` (standard PyInstaller `--onedir` location). `dist/` and `build/` are `.gitignore`d. IT staff copies `dist/status_report/` to the USB flash drive.

### CrowdStrike Falcon Validation
- **D-11:** Before distribution, run `status_report.exe` on a CrowdStrike Falcon-enrolled Master Electronics machine. If it executes cleanly (no quarantine, HTML generated in `logs/`), the test passes and distribution proceeds.
- **D-12:** If the .exe is quarantined, escalate at that point: options are (a) request an admin exclusion by path/hash from the CrowdStrike tenant admin, or (b) evaluate code-signing (DIST-V2-01). Decision is deferred until the test result is known.
- **D-13:** The test result (pass or documented fallback) must be recorded in ROADMAP.md success criterion 4 before the tool is distributed to IT staff.

### Claude's Discretion
- Exact hidden imports list in the `.spec` file — Claude identifies all transitive imports that PyInstaller misses (wmi, win32com, pywintypes, and any Jinja2/MarkupSafe internals) by running a trial build and checking for import errors
- Whether to include a `--icon` in the spec (Claude can add a default Windows icon or leave unset)
- `PyInstaller` version pin in `requirements-dev.txt` — Claude picks a compatible version with Python 3.12 and the existing deps
- Error message text for write failures (disk full, permission denied on USB)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Critical Constraints
- `CLAUDE.md` — `--onedir` only (never `--onefile`), output path from `sys.executable`, no writes to host PC. Read first.

### Requirements
- `.planning/REQUIREMENTS.md` §PKG-01 — Windows .exe, no installation, standard user, Windows 10/11
- `.planning/REQUIREMENTS.md` §PKG-02 — No writes to host PC filesystem, registry, or %TEMP%
- `.planning/REQUIREMENTS.md` §OUT-02 — Output path derived from `sys.executable` (already wired in writers layer)
- `.planning/ROADMAP.md` §Phase 5 — Success criteria (4 items): run from USB as standard user within 30s, no host PC writes, under 50 MB, CrowdStrike test recorded

### Prior Phase Context
- `.planning/phases/02-system-collectors/02-CONTEXT.md` — `collect_all(report)` interface; output path from `sys.executable` established in D-04
- `.planning/phases/03-html-character-sheet-renderer/03-CONTEXT.md` — `render_html(report)` interface; Jinja2 template via `importlib.resources` (required for PyInstaller bundles)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `collectors/__init__.py` — `collect_all(report: AuditReport) -> None` is the single collection entry point. `main.py` calls this.
- `renderer/__init__.py` — `render_html(report: AuditReport) -> str` returns the HTML string. Template loaded via `importlib.resources` — works correctly inside a PyInstaller bundle.
- `writers/__init__.py` — `write_html(html: str, output_path: Path) -> None` handles the file write. `main.py` constructs `output_path` and passes it here.
- `models.py` — `AuditReport` is the data contract. `main.py` instantiates it, passes to `collect_all`, then to `render_html`.

### Established Patterns
- In-place mutation: `collect_all(report)` mutates the `AuditReport`. `main.py` creates the report, passes it through, never re-assigns.
- Never raises across layer boundaries: all collectors catch exceptions internally. `main.py` reads `report.collection_errors` to surface warnings.
- Output path via `sys.executable`: `Path(sys.executable).parent` gives the USB directory when running as a frozen exe; same value used in Phase 2 documentation and Phase 3 wiring.

### Integration Points
- `main.py` is the new file Phase 5 creates. It is the PyInstaller entry point (`Analysis(['main.py'], ...)` in the spec).
- `renderer/templates/character_sheet.html` must be declared as a data file in the spec: `datas=[('renderer/templates', 'renderer/templates')]` so PyInstaller bundles it.
- `wmi` and `win32com` require explicit `--hidden-import` entries in the spec — PyInstaller cannot auto-detect COM-based imports.

</code_context>

<specifics>
## Specific Details

- Output path construction: `Path(sys.executable).parent / "logs" / f"status_{hostname}_{date}.html"`
- `logs/` directory created with `Path(...).mkdir(parents=True, exist_ok=True)` before write
- Console progress messages use plain `print()` — no logging framework needed at this scale
- `webbrowser.open(str(output_path))` opens the HTML after write (stdlib, no extra deps)
- Build artifacts: `status_report.spec` and `build.bat` checked into repo root; `dist/` and `build/` gitignored
- USB distribution: IT copies `dist/status_report/` folder to USB. Folder contains `status_report.exe` + `_internal/`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-packaging-and-distribution*
*Context gathered: 2026-05-05*
