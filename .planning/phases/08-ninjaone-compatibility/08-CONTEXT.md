# Phase 8: NinjaOne Compatibility - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the exe safe to run headless under the NinjaOne SYSTEM account: guard the two interactive calls (`input()` and `os.startfile()`) with `sys.stdin.isatty()`, ensure HKCU registry reads degrade gracefully when SYSTEM has no user hive, and emit a structured `[SUMMARY]` line to stdout that NinjaOne's activity log captures after every run.

No changes to the HTML output path logic — `exe_parent/logs/` always (same path for USB and NinjaOne-deployed runs).

</domain>

<decisions>
## Implementation Decisions

### Headless Detection
- **D-01:** Use `sys.stdin.isatty()` as the single headless guard. When `False`, skip both `input()` (the "Press Enter" pause) and `os.startfile()` (the browser open). ROADMAP SC2 specifies this mechanism exactly — no other detection needed.
- **D-02:** The headless path exits cleanly with `return` (or `sys.exit(0)`) after printing the `[SUMMARY]` line. No prompts, no browser, no hangs.

### HTML Output Path
- **D-03:** `exe_parent/logs/` always — `Path(sys.executable).parent / "logs"`. No path branching based on headless mode. When NinjaOne deploys the exe to a local folder, HTML lands there. When run from USB, HTML lands on the USB. Same code path, same behavior. No `C:\ProgramData\...` switching.

### [SUMMARY] stdout Line
- **D-04:** Format: pipe-delimited, human-readable. Printed to stdout after every run (both interactive and headless).
  ```
  [SUMMARY] PHX-INV-001 | Windows 11 Build 26100 | Intel Core i7-1265U | 16 GB RAM | 42% disk used | 0 warnings
  ```
  Fields in order: hostname, OS version + build, CPU model, total RAM (GB), disk used %, active warning count.
- **D-05:** `[SUMMARY]` is a literal prefix — NinjaOne activity log readers can search for this token to find the line.
- **D-06:** Disk used % = `round((disk_total_gb - disk_free_gb) / disk_total_gb * 100)` from existing `AuditReport` fields. Warning count = `len([w for w in report.warnings if w.severity == 'WARN'])`.
- **D-07:** `[SUMMARY]` line is printed via `print()` after the HTML write step, before the interactive block. It appears in both interactive runs (visible in the console window) and NinjaOne runs (captured by the activity log).

### HKCU MSIX Detection Under SYSTEM
- **D-08:** No change to `_detect_msix_package()`. The current code already catches `(FileNotFoundError, OSError)` and returns `(False, None)` — which maps to "Not Found" in the equipment table. ROADMAP SC4 is satisfied by the existing error handling. No HKLM AppModel fallback needed.
- **D-09:** Claude Desktop and Company Portal (Phase 9) are per-user MSIX installs. Under SYSTEM, they legitimately aren't visible. "Not Found" is the correct and honest result.

### Claude's Discretion
- Exact `[SUMMARY]` field formatting for None/unavailable values (e.g., CPU model = None → `"Unknown CPU"` or `"N/A"`)
- Whether to add a unit test that monkeypatches `sys.stdin.isatty` to `False` and asserts `input()` / `os.startfile()` are not called
- The exact placement of the `print("[SUMMARY] ...")` call in `main.py` relative to the write/error handling block

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §NINJA-01 — SYSTEM account execution, no hangs, no interactive prompts
- `.planning/REQUIREMENTS.md` §NINJA-02 — stdout summary line fields (hostname, OS version, CPU, RAM, disk %, warning count)
- `.planning/ROADMAP.md` §Phase 8 — Success criteria SC1–SC4 (definitive acceptance bar)

### Source Files to Modify
- `main.py` — All three changes land here: `isatty()` guards on `input()` and `os.startfile()`, `[SUMMARY]` print call
- `collectors/windows/apps.py` — `_detect_msix_package()` at line ~168 — verify existing HKCU error handling satisfies SC4 (read-only verification, no change expected)

### Prior Phase Context
- `.planning/phases/05-packaging-and-distribution/05-CONTEXT.md` — D-04 (console window shown), D-05 (os.startfile + input pattern), D-02 (output path via sys.executable)
- `.planning/phases/06-warning-data-model/06-CONTEXT.md` — Warning dataclass, evaluate_warnings() return contract

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main.py:main()` — Current pipeline: collect → warnings → render → write → startfile → input. Phase 8 adds `[SUMMARY]` print and wraps `startfile`/`input` in `isatty()` guard.
- `_detect_msix_package()` in `collectors/windows/apps.py:168` — Already handles HKCU failures cleanly. No change needed; planner should verify and document this.
- `AuditReport` fields available for `[SUMMARY]`: `hostname`, `os_version` (str), `cpu_model` (str|None), `total_ram_gb` (float|None), `disk_total_gb` / `disk_free_gb` (float|None), `report.warnings` (list[Warning]).

### Established Patterns
- `sys.stdin.isatty()` is stdlib — no new dependencies.
- `print()` for all console output — no logging framework. `[SUMMARY]` line follows this pattern.
- Collector failures silently degrade (return None fields) — `[SUMMARY]` builder must handle None values without raising.

### Integration Points
- `main.py` is the only file that changes for the interactive-call guards and `[SUMMARY]` line.
- `_detect_msix_package()` in apps.py needs a read and verification pass, not a code change.
- No changes to models, collectors, renderer, or templates.

</code_context>

<specifics>
## Specific Details

- `[SUMMARY]` line example (all fields populated):
  `[SUMMARY] PHX-INV-001 | Windows 11 Build 26100 | Intel Core i7-1265U | 16 GB RAM | 42% disk used | 0 warnings`
- `[SUMMARY]` line placement in `main.py`: after the `print(f"Saved: {output_path}")` line, before the `isatty()` guard block.
- Headless exit flow:
  ```python
  print(f"[SUMMARY] ...")
  if sys.stdin.isatty():
      try:
          os.startfile(str(output_path))
      except OSError:
          pass
      input("\nPress Enter to close this window, then eject the USB drive.")
  ```
- HKCU AppModel path being read: `Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages` — under `HKEY_CURRENT_USER`. SYSTEM account has no user hive; `winreg.OpenKey(HKCU, ...)` raises `FileNotFoundError` → caught → returns `(False, None)` → mapped to "Not Found".

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-ninjaone-compatibility*
*Context gathered: 2026-05-07*
