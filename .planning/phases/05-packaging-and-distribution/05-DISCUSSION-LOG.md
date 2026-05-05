# Phase 5: Packaging and Distribution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 05-packaging-and-distribution
**Areas discussed:** Console / UX behavior, Output filename, CrowdStrike quarantine contingency, Build process

---

## Console / UX behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Console window — verbose | Prints progress lines + final save path + warnings on failure | ✓ |
| Console window — minimal | Console shown, only final path or error printed | |
| No console window | Silent via --noconsole, no visibility into errors | |

**User's choice:** Console window — verbose, with the HTML file automatically opening in the browser after completion.

**Notes:** User explicitly requested auto-open behavior. OUT-V2-02 (auto-open HTML in default browser) was deferred to v2 but was folded into Phase 5 scope — trivial to implement (`webbrowser.open()`), significantly improves IT staff UX. User also confirmed: print warnings and continue on collector failures (never exit 1 due to a collector failure).

---

## Output filename

| Option | Description | Selected |
|--------|-------------|----------|
| audit_{HOSTNAME}_{DATE}.html | Unique per run, accumulates on USB | |
| status_report.html | Same name every run, overwrites | |
| status_{HOSTNAME}_{DATE}.html | User-specified prefix variant | ✓ |

**User's choice:** `status_{HOSTNAME}_{DATE}.html` (user changed prefix from "audit_" to "status_").

**Notes:** User also specified: save to a `logs/` subdirectory under `Path(sys.executable).parent`. Create `logs/` with `mkdir(exist_ok=True)` if it doesn't exist. Full path: `Path(sys.executable).parent / "logs" / f"status_{hostname}_{date}.html"`.

---

## CrowdStrike quarantine contingency

| Option | Description | Selected |
|--------|-------------|----------|
| Test first, decide if blocked | Run on enrolled machine; escalate only if quarantined | ✓ |
| Request admin exclusion preemptively | CrowdStrike admin adds path/hash exclusion before distributing | |
| Pull code-signing into Phase 5 scope | Sign .exe with Authenticode cert (~$100-400/yr) | |

**User's choice:** Test first, decide if blocked.

**Notes:** User asked for clarification on what "the --onedir .exe" referred to — confirmed this is `status_report.exe` being built in Phase 5. ROADMAP success criterion 4 requires test result (pass or documented fallback) recorded before distribution.

---

## Build process

| Option | Description | Selected |
|--------|-------------|----------|
| spec file + build script | status_report.spec + build.bat, reproducible one-command build | ✓ |
| Documented CLI command only | pyinstaller flags documented in README/CLAUDE.md, no extra files | |

**User's choice:** spec file + build script.

**Notes:** Output to `dist/status_report/` (standard PyInstaller --onedir location). `dist/` gitignored. IT staff copies `dist/status_report/` folder to USB.

---

## Claude's Discretion

- Exact hidden imports list in the `.spec` file (wmi, win32com, pywintypes, Jinja2/MarkupSafe internals)
- Whether to include a `--icon` in the spec
- PyInstaller version pin in `requirements-dev.txt`
- Error message text for write failures

## Deferred Ideas

None — discussion stayed within phase scope.
