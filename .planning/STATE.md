---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Warnings, Mac Parity, and NinjaOne Compatibility
status: in_progress
stopped_at: Completed 09-01-PLAN.md — Company Portal MSIX + MDM enrollment; 153 tests pass
last_updated: "2026-05-07T23:18:00Z"
last_activity: "2026-05-07 — Phase 9 complete (Company Portal MSIX detection + Intune MDM enrollment, 6 new tests, 153 total pass)"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 5
  completed_plans: 5
  percent: 80
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-07)

**Core value:** IT staff plugs in, runs the tool, and instantly knows what they're looking at — device type, location, department, software status, and any gaps — no manual lookup required.
**Current focus:** Milestone v2.0 — Phase 9 is next (Company Portal Detection)

## Current Position

Phase: 9 — Company Portal Detection (complete)
Plan: 01 (1/1 complete)
Status: Phase 9 complete — Company Portal MSIX detection + Intune MDM enrollment; 153 tests pass
Last activity: 2026-05-07 — Phase 9 executed (09-01-PLAN.md; 6 new CP tests; 153 total pass)

Progress: [████████__] 80% (4/5 v2.0 phases complete)

## Performance Metrics

**Velocity (v1.0 baseline):**

- Total plans completed: 14 (v1.0)
- Average duration: ~3 min/plan
- Total execution time: ~2 days (2026-05-04 → 2026-05-05)

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | ~4 min | ~1 min |
| 03 | 2 | ~7 min | ~3.5 min |
| 04 | 2 | ~13 min | ~6.5 min |
| 05 | 2 (of 3) | ~5 min | ~2.5 min |

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
- 07-02: Warnings box uses <details open> auto-expand when has_warnings is true — no JS required
- 07-02: has_warnings computed in _build_context() (not template) — keeps template logic-free per D-12 pattern
- 07-02: evaluate_warnings placed after collect_all and before render_html in main.py pipeline
- 08-01: sys.stdin.isatty() as single headless guard — wraps os.startfile() and input() only (D-01)
- 08-01: [SUMMARY] print is outside isatty() guard — emitted on every run, headless and interactive (D-07)
- 08-01: if report.disk_total_gb: guard prevents ZeroDivisionError on None/0 (T-08-03 mitigated)
- 08-01: report.ram_gb is the correct AuditReport field (plan interface section listed total_ram_gb incorrectly)
- 08-01: _detect_msix() HKCU exception handling already present — SC4 satisfied, no code change (D-08)
- 08-01: Patch target is main.os.startfile (not os.startfile) — main.py uses import os, not from-import
- 09-01: MDM hook runs unconditionally regardless of installed state (D-01) — enrollment visible even when HKCU absent under SYSTEM
- 09-01: Empty UPN strings treated as stale GUIDs and skipped (D-06); first non-empty UPN wins (D-05)
- 09-01: _detect_mdm_enrollment() wraps entire body in try/except Exception — never raises across layer boundary
- 09-01: No service_key field in Company Portal spec — MDM enrollment hook uses spec name check in _detect_one_app()

### v2.0 Open Decisions (require stakeholder input before implementation)

| Decision | Needed For | Default If No Answer |
|----------|-----------|---------------------|
| NinjaOne output path — confirm C:\ProgramData\MasterElectronics\StatusReport\logs\ | Phase 8 | Use that path — SYSTEM-writable, IT-retrievable |
| Company Portal row naming — enrollment vs app presence vs both | Phase 9 | Show both as separate signals, clearly labeled |
| NinjaOne Mac agent app path — validate /Applications/NinjaRMMAgent/ against fleet Mac | Phase 10 | Use that path per NinjaOne official docs |
| OS warning threshold — confirm minimum acceptable build | Phase 6 | Warn on any Win10 (build < 22000); informational for Win11 below 22631 |
| Disk space thresholds — confirm 15% / 10 GB dual threshold | Phase 6 | Ship those defaults; constants in warnings.py, easy to adjust |

### Pending Todos

- Validate NinjaOne Mac agent path against a real Mac in the fleet before Phase 10 closes
- Confirm Company Portal row naming with IT before Phase 9 closes
- Confirm NinjaOne output path (ProgramData) with IT before Phase 8 closes

### Blockers/Concerns

- Phase 10: Mac app bundle paths require live Mac validation — no Mac build tested yet (MEDIUM confidence)
- Phase 10: system_profiler chip_type vs cpu_type — unit test fixtures needed from both Intel and Apple Silicon

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Output | JSON audit log (OUT-V2-01) | v3 | v2.0 planning |
| Output | Auto-open HTML in browser (OUT-V2-02) | v3 | v2.0 planning (incompatible with SYSTEM/headless) |
| App Detection | Remote access tools (APP-V2-02) | v3 | v2.0 planning |
| Distribution | Code-signed .exe (DIST-V2-01) | v3 | v1.0 close (budget decision) |
| Platform | Mac PyInstaller packaging (.app/notarization) | v3 | v2.0 planning (requires Apple Developer account) |

### Acknowledged at v1.0 Milestone Close (2026-05-07)

Items deferred rather than resolved before milestone close:

| Category | Item | Status |
|----------|------|--------|
| uat_gaps | Phase 04: 04-HUMAN-UAT.md — Live NinjaOne/CrowdStrike detection tests + M365 single-suite stakeholder sign-off | partial (4 pending) |
| verification_gaps | Phase 03: 03-VERIFICATION.md — Visual browser check of HTML character sheet (8/8 automated tests pass) | human_needed |
| verification_gaps | Phase 04: 04-VERIFICATION.md — Live app detection on real provisioned machines | human_needed |

## Session Continuity

Last session: 2026-05-07
Stopped at: Completed 09-01-PLAN.md — Company Portal MSIX + MDM enrollment detection + 6 tests; 153 tests pass
Resume file: None
Next action: Phase 9 complete — proceed to next v2.0 phase (Phase 10: Mac Collectors)
