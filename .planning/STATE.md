---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: complete
stopped_at: Completed 05-03-PLAN.md — CrowdStrike Falcon validation passed; all phases complete; v1.0 milestone delivered
last_updated: "2026-05-05T20:30:00Z"
last_activity: "2026-05-05 — 05-03 complete (PyInstaller build validated on CrowdStrike-enrolled ME machine as standard user; no quarantine; HTML confirmed on USB; distribution approved)"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 14
  completed_plans: 14
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-04)

**Core value:** IT staff plugs in, runs the tool, and instantly knows what they're looking at — device type, location, department, software status, and any gaps — no manual lookup required.
**Current focus:** All phases complete — v1.0 milestone delivered

## Current Position

Phase: 5 of 5 (Packaging and Distribution) — complete
Plan: 3 of 3 complete
Status: 05-03 complete — CrowdStrike Falcon validation passed; all 14 plans complete; v1.0 milestone delivered
Last activity: 2026-05-05 — 05-03 complete (PyInstaller --onedir exe validated on CrowdStrike Falcon-enrolled ME machine as standard user; no quarantine; HTML confirmed on USB logs/; distribution approved)

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 8
- Average duration: ~1 min
- Total execution time: ~2 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | ~4 min | ~1 min |
| 03 | 2 | ~7 min | ~3.5 min |
| 04 | 2 | ~13 min | ~6.5 min |
| 05 | 2 (of 3) | ~5 min | ~2.5 min |

**Recent Trend:**

- Last 5 plans: 03-02 (~5 min), 04-01 (~10 min), 04-02 (~3 min), 05-01 (~2 min), 05-02 (~3 min)
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: PyInstaller --onedir chosen (--onefile quarantined by CrowdStrike Falcon)
- Init: Win32_Product WMI class explicitly prohibited (MSI reconfiguration side effect)
- Init: Output path derived from sys.executable, not os.getcwd()
- Init: winreg used exclusively for app detection (all four Uninstall key paths)
- 01-02: station: int | None (not str) per ROADMAP SC1
- 01-02: department field name (not dept_code) per ROADMAP SC1 and D-02
- 01-02: parsed_hostname on AuditReport (not parsed_name) per ROADMAP SC1
- 01-02: No frozen=True — Phase 2 collectors populate fields after construction
- 01-03: P3_CODES check first in disambiguation chain (before seg3.isdigit) — Pitfall 1 guard
- 01-03: station stored as int(seg3) — Pitfall 2 guard
- 01-03: KUL/HKG excluded from CITY_CODES — unconfirmed for this convention
- 02-01: _wmi_module/_WMI_AVAILABLE module-level import pattern — enables CI testing without COM server
- 02-01: cpu_model silently None (no error) when _WMI_AVAILABLE=False — missing library is not a runtime failure
- 02-01: Win32_Product not used — Win32_Processor used for cpu_model (CLAUDE.md constraint enforced)
- 02-01: psutil imported at module level for patchability in disk error tests
- 02-02: collect_all() uses lazy import inside function body — keeps collectors/__init__.py importable on non-Windows platforms
- 02-02: collect_hardware called before collect_profiles in collect_all() — D-10 ordering enforced
- 03-01: requirements.txt created separate from requirements-dev.txt (runtime vs dev deps split)
- 03-01: write_html uses pathlib.Path.write_text per project convention (no open() with string paths)
- 03-01: Threat T-03-01-01 accepted — output_path validation is Phase 5 / main.py concern, not writers
- 03-02: Jinja2 default() requires boolean=True to replace Python None: {{ x | default('—', true) }}
- 03-02: ir.files('renderer').joinpath('templates/character_sheet.html') — single-string joinpath form required
- 03-02: HP bar falsy guard `if report.disk_total_gb` catches both None and 0.0 (D-13 Pitfall 3)
- 03-02: autoescape=True on Environment — template author does not manually escape; chars auto-escaped
- 04-01: CrowdStrike keywords set to 'CrowdStrike Windows Sensor' / 'CrowdStrike Sensor Platform' (not 'CrowdStrike Falcon') — live registry verified (Pitfall 1)
- 04-01: Claude MSIX detection via 'Claude_' family prefix in AppModel repository as primary; standard keyword sweep as fallback (Pitfall 3)
- 04-01: MERP filesystem-first at hardcoded PVX Plus path per D-02; registry search for version only on filesystem hit per D-03
- 04-02: Claude MSIX test uses distinct context manager objects per OpenKey path so EnumKey dispatch can distinguish MSIX repo from Uninstall path enumeration
- 05-01: render_html(report) -> str added as Option A interface — returns HTML string without writing; main.py controls path and write (avoids breaking 94 existing tests)
- 05-01: *.spec removed entirely from .gitignore (not negation rule) — simpler, allows status_report.spec to be committed (D-08/Pitfall 4)
- 05-02: Output path uses Path(sys.executable).parent/logs/status_{hostname}_{date}.html (D-02/D-03) — USB-only, CLAUDE.md constraint enforced
- 05-02: Collector failures warn and continue; only write failure (PermissionError, ENOSPC) exits with code 1 (D-06)
- 05-02: spec uses Analysis+PYZ+EXE(exclude_binaries=True)+COLLECT — --onedir structure; NEVER EXE(onefile=True)
- 05-02: upx=False in both EXE() and COLLECT() — two entries required per PyInstaller spec structure
- 05-03: CrowdStrike Falcon test passed 2026-05-05 — no quarantine, no block on enrolled ME machine as standard user; --onedir + upx=False sufficient for v1.0; code signing (DIST-V2-01) deferred to v2

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 1: Hostname naming convention must be validated against real production hostnames (including international offices: AMM, AMS, KUL, HKG) before parser is finalized — confirm with IT/Edgar
- Phase 4: MERP registry path is unknown — must be confirmed with IT before APP-03 detection can be completed
- Phase 5: CrowdStrike --onedir tenant policy behavior must be tested on an enrolled machine at the start of Phase 5; code-signing budget decision needed if blocked — RESOLVED 2026-05-05: test passed, no block, no exclusion needed

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Output | JSON audit log (OUT-V2-01) | v2 | Init |
| Output | Auto-open HTML in browser (OUT-V2-02) | v2 | Init |
| App Detection | Intune/Company Portal (APP-V2-01) | v2 | Init |
| App Detection | Remote access tools (APP-V2-02) | v2 | Init |
| Platform | Mac support (PLAT-V2-01) | v2 | Init |
| Distribution | Code-signed .exe (DIST-V2-01) | v2 | Init |

## Session Continuity

Last session: 2026-05-05T20:30:00Z
Stopped at: Completed 05-03-PLAN.md — CrowdStrike Falcon test passed; all 14 plans complete; v1.0 milestone delivered
Resume file: None
