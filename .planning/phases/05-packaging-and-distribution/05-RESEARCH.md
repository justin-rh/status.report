# Phase 5: Packaging and Distribution — Research

**Researched:** 2026-05-05
**Domain:** PyInstaller 6.x, Windows .exe packaging, USB deployment, CrowdStrike Falcon AV compatibility
**Confidence:** MEDIUM-HIGH (core PyInstaller patterns HIGH; pywin32 hidden import list MEDIUM due to build-time trial required; CrowdStrike behavior LOW — must test on enrolled machine)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**main.py Entry Point**
- D-01: `main.py` orchestrates: `collect_all(report)` → `render_html(report)` → write HTML to `logs/` subdir → open in browser
- D-02: Output path: `Path(sys.executable).parent / "logs" / f"status_{hostname}_{date}.html"`. `logs/` created with `mkdir(parents=True, exist_ok=True)`.
- D-03: Filename: `status_{HOSTNAME}_{DATE}.html` (e.g., `status_PHX-INV-003_2026-05-05.html`). Each run accumulates; never overwrites.
- D-04: Console window shown (not `--noconsole`). Verbose progress via `print()`.
- D-05: `webbrowser.open(str(output_path))` after write. OUT-V2-02 pulled into v1.
- D-06: Collector failures print a warning and continue — never `sys.exit`. HTML always generated. Only write failure (disk full / permissions) is a fatal top-level error.

**PyInstaller Packaging**
- D-07: `--onedir` only. `--onefile` is explicitly prohibited (CrowdStrike Falcon quarantine — CLAUDE.md).
- D-08: `status_report.spec` checked into repo. Captures entry point, hiddenimports, datas.
- D-09: `build.bat` at repo root — activates venv, runs `pyinstaller status_report.spec`.
- D-10: Output in `dist/status_report/`. `dist/` and `build/` gitignored.

**CrowdStrike Falcon Validation**
- D-11: Run `status_report.exe` on a CrowdStrike Falcon-enrolled ME machine before distribution.
- D-12: If quarantined: (a) request admin exclusion by path/hash, or (b) evaluate code-signing (DIST-V2-01).
- D-13: Test result recorded in ROADMAP.md SC4 before distribution.

### Claude's Discretion
- Exact hidden imports list in `.spec` — Claude identifies transitive imports PyInstaller misses (wmi, win32com, pywintypes, Jinja2/MarkupSafe internals) via trial build + error checking
- Whether to include `--icon` in spec (default Windows icon or leave unset)
- `PyInstaller` version pin in `requirements-dev.txt`
- Error message text for write failures (disk full, permission denied on USB)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PKG-01 | Windows .exe, PyInstaller `--onedir`, runnable without install or admin rights, Windows 10/11 | PyInstaller 6.20.0 confirmed; `--onedir` + console mode supports standard user execution |
| PKG-02 | All output to flash drive only — no writes to host PC filesystem, registry, or %TEMP% | `Path(sys.executable).parent` pattern verified in CLAUDE.md and Phase 2; write error handling pattern documented |
</phase_requirements>

---

## Summary

Phase 5 wires `main.py` as the PyInstaller entry point and produces a `dist/status_report/` folder that IT staff copies to a USB drive. The technical surface is: (1) a `main.py` orchestration script, (2) a `status_report.spec` build definition, and (3) a `build.bat` one-command build script.

The primary research risk is the pywin32/wmi hidden imports. PyInstaller 6.x has improved pywin32 auto-detection significantly — the `pywin32_system32` DLL directory is now automatically added to the search path at runtime via a bootstrap module introduced in PyInstaller 5.5. However, WMI's COM-based import chain (`wmi` → `win32com.client` → `pythoncom`, `pywintypes`) is not fully statically analyzable. A trial build followed by `pyi-archive_viewer` inspection and runtime import error checks is the correct verification approach. Exact hidden imports can only be confirmed by executing the frozen exe.

The second risk is CrowdStrike Falcon behavior. `--onedir` mode is confirmed as significantly less flagged than `--onefile` because no runtime extraction occurs. On Master Electronics' tenant the behavior depends on their prevention policy settings and any existing exclusions. The test (D-11) is the only way to confirm — no amount of research resolves this ahead of time.

**Critical pre-build finding:** `.gitignore` currently contains `*.spec`, which conflicts with D-08 (spec must be checked into the repo). The `*.spec` line must be removed before the spec file is committed.

**Interface reconciliation needed:** CONTEXT.md describes `render_html(report) -> str` but the actual renderer exposes `render_report(report, output_path) -> Path`. `main.py` must call `render_report` with a constructed output path, OR call `renderer`'s internal `_build_context` + Jinja directly. The cleanest approach: `main.py` constructs the full `output_path` (including dynamic filename), then calls `render_report(report, output_path)` — but `render_report` currently calls `write_html(html, output_path)` which appends `status_report.html`, making the filename dynamic name impossible. Phase 5 must either (a) refactor `writers.write_html` to accept a full file path, or (b) add a `render_html(report) -> str` function to `renderer/__init__.py` and have `main.py` do the write directly.

**Primary recommendation:** Use PyInstaller 6.20.0 pinned in `requirements-dev.txt`. Start with `collect_submodules('win32com')` in the spec's `hiddenimports`. Run trial build from the activated venv. Use `pyi-archive_viewer` to inspect. Run the frozen exe and iterate on any `ModuleNotFoundError`. Remove `*.spec` from `.gitignore` before first commit of spec.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pipeline orchestration | main.py (entry point) | — | Wires all phases; frozen exe entry |
| Data collection | collectors/ layer | — | Existing; called via collect_all() |
| HTML rendering | renderer/ layer | writers/ layer | Existing; render_report writes file |
| Output path construction | main.py | — | sys.executable known only at runtime; Phase 2 pattern |
| Dynamic filename assembly | main.py | — | Hostname + date logic belongs at orchestration layer |
| Browser launch | main.py | — | webbrowser.open() after write confirms success |
| Build definition | status_report.spec | — | Declarative; checked into repo |
| Build automation | build.bat | — | Wraps venv activation + pyinstaller |
| USB write error handling | main.py | — | Top-level error handler; D-06 guidance |
| AV exclusion (if needed) | Manual / IT admin | — | D-12; out of code scope |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyInstaller | 6.20.0 | Package Python app as Windows .exe | Latest stable; Python 3.8–3.14 support; pywin32 bootstrap fix in 5.5+ |
| pywin32 | 311 (already installed) | pywin32 DLLs required by wmi, win32com | Already in venv; pywintypes312.dll + pythoncom312.dll auto-collected in 6.x |
| Python stdlib: socket | 3.12 | Hostname for output filename | stdlib; no extra dep |
| Python stdlib: datetime | 3.12 | Date for output filename | stdlib; no extra dep |
| Python stdlib: webbrowser | 3.12 | Open HTML in default browser | stdlib; no extra dep |
| Python stdlib: sys | 3.12 | `sys.executable`, `sys.frozen` detection | stdlib; no extra dep |

[VERIFIED: pypi.org/project/pyinstaller] PyInstaller 6.20.0 released 2026-04-22, supports Python 3.8–3.14.
[VERIFIED: venv inspection] pywin32 311 installed; pywintypes312.dll and pythoncom312.dll present in `.venv/Lib/site-packages/pywin32_system32/`.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyinstaller-hooks-contrib | (installed with PyInstaller) | Community hooks for obscure packages | Auto-installed; no direct reference needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyInstaller 6.20.0 | PyInstaller 6.0.0–6.5.0 | Earlier versions have pywin32 regression bugs (6.6.0 win32ctypes issue); use latest |
| PyInstaller | Nuitka | Nuitka compiles to C — fewer AV false positives, but requires C compiler, longer build, more complex setup |
| `build.bat` | PowerShell `.ps1` | .bat is universally executable on Windows without policy changes; PS1 may require execution policy change |

**Installation (to add to `requirements-dev.txt`):**
```bash
pip install pyinstaller==6.20.0
```

**Version verification:**
```bash
pip view pyinstaller  # shows 6.20.0
```
[VERIFIED: pypi.org] Version 6.20.0 is current as of 2026-04-22.

---

## Architecture Patterns

### System Architecture Diagram

```
USB Drive
└── status_report/
    ├── status_report.exe          ← IT double-clicks here
    └── _internal/                 ← All supporting files (PyInstaller 6 default)
        ├── python312.dll
        ├── pywin32_system32/
        │   ├── pywintypes312.dll
        │   └── pythoncom312.dll
        ├── win32/
        ├── win32com/
        ├── renderer/
        │   └── templates/
        │       └── character_sheet.html
        └── ... (stdlib + deps)

Execution flow (frozen exe):
  status_report.exe
      │
      ▼
  main.py
      │
      ├─→ socket.gethostname()          → hostname string
      ├─→ AuditReport(hostname, ...)    → empty report
      ├─→ collect_all(report)           → mutates report in place
      │       ├─ collect_hardware()     → WMI + psutil
      │       ├─ collect_profiles()     → winreg
      │       └─ collect_apps()         → winreg × 4 paths
      │
      ├─→ Path(sys.executable).parent   → USB root (e.g., D:\status_report\)
      ├─→ logs_dir = usb_root / "logs"
      ├─→ logs_dir.mkdir(...)
      ├─→ output_path = logs_dir / f"status_{hostname}_{date}.html"
      │
      ├─→ render_report(report, ???)    ← INTERFACE CONFLICT — see below
      │
      ├─→ write HTML to output_path     ← must land on USB only
      │
      └─→ webbrowser.open(str(output_path))
              │
              └─→ Default browser opens HTML
```

### Interface Conflict: writers.write_html vs D-02/D-03

**Current state:**
- `write_html(html: str, output_path: Path) -> Path` treats `output_path` as a **directory** and appends `status_report.html` (hardcoded)
- `render_report(report, output_path)` calls `write_html(html, output_path)` internally

**CONTEXT.md D-02/D-03 requires:**
- Filename `status_{hostname}_{date}.html` — dynamically constructed in `main.py`
- `main.py` must control the full path including filename

**Recommended resolution (Phase 5 task):**
Option A (minimal change): Add `render_html(report: AuditReport) -> str` to `renderer/__init__.py` that returns the HTML string without writing. `main.py` constructs full path and calls `output_path.write_text(html, encoding='utf-8')` directly. `writers.write_html` unchanged (tests pass). No breaking changes to existing test suite.

Option B (clean): Change `write_html(html, path)` to treat `path` as a full file path (not a directory). This breaks `test_writers.py` — all tests must be updated.

**Recommendation:** Option A. `main.py` is the layer that knows the dynamic filename; having it write directly via pathlib is consistent with CLAUDE.md's `pathlib.Path.write_text` convention and avoids breaking the existing test suite.

### Recommended Project Structure (new files only)

```
status.report/
├── main.py                     ← NEW: PyInstaller entry point
├── status_report.spec          ← NEW: build definition (checked in, remove *.spec from .gitignore)
├── build.bat                   ← NEW: one-command build script
└── requirements-dev.txt        ← UPDATE: add pyinstaller==6.20.0
```

### Pattern 1: main.py Orchestration

```python
# Source: CONTEXT.md D-01 through D-06
import sys
import socket
import datetime
import webbrowser
from pathlib import Path

from models import AuditReport
from parsers.name_parser import parse_hostname
from collectors import collect_all
from renderer import render_html  # Option A: new function returning str

def main() -> None:
    hostname = socket.gethostname()
    date_str = datetime.date.today().isoformat()

    print("StatusReport — Master Electronics IT Audit Tool")

    report = AuditReport(
        hostname=hostname,
        parsed_hostname=parse_hostname(hostname),
        timestamp=datetime.datetime.now().isoformat(),
    )

    print("Collecting hardware info...")
    collect_all(report)

    # Warn on collection errors but never exit
    for err in report.collection_errors:
        print(f"[WARN] {err}")

    print("Rendering character sheet...")

    # Output path — USB only (D-02, CLAUDE.md constraint)
    usb_root = Path(sys.executable).parent
    logs_dir = usb_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    output_path = logs_dir / f"status_{hostname}_{date_str}.html"

    html = render_html(report)  # Option A: returns str

    try:
        output_path.write_text(html, encoding="utf-8")
    except PermissionError as e:
        print(f"[ERROR] Cannot write to USB: {e}")
        print("Check the drive is not write-protected and has free space.")
        sys.exit(1)
    except OSError as e:
        print(f"[ERROR] Write failed: {e}")
        sys.exit(1)

    print(f"Saved: {output_path}")
    print("Opening in browser...")
    webbrowser.open(str(output_path))
    print("Done.")

if __name__ == "__main__":
    main()
```

### Pattern 2: PyInstaller Spec File (status_report.spec)

```python
# Source: PyInstaller 6.20.0 docs + verified venv inspection
# [VERIFIED: pyinstaller.org/en/stable/spec-files.html]
# [VERIFIED: venv inspection of .venv/Lib/site-packages/]

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# win32com has COM-dispatched imports PyInstaller cannot detect statically
win32com_hidden = collect_submodules('win32com')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Bundle Jinja2 templates for importlib.resources access at runtime
        # (renderer/_load_template_source uses ir.files('renderer').joinpath(...))
        ('renderer/templates', 'renderer/templates'),
    ],
    hiddenimports=[
        'wmi',
        'win32api',
        'win32con',
        'win32com',
        'win32com.client',
        'win32com.server',
        'pywintypes',
        'pythoncom',
        'win32transaction',
        'win32security',
    ] + win32com_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'email',
        'xml',
        'xmlrpc',
        'http',
        'urllib',
        'multiprocessing',
        'concurrent',
        'asyncio',
        'sqlite3',
        'ssl',
        '_ssl',
        'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='status_report',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX increases AV suspicion; skip
    console=True,       # D-04: show console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='status_report',
)
```

**Note on `excludes`:** These are safe to exclude for this tool (no network, no GUI, no DB). Each exclusion can save 1–5 MB. Test after adding each batch to confirm no `ModuleNotFoundError` at runtime.

**Note on `contents_directory`:** PyInstaller 6.0+ puts all supporting files in `_internal/` by default. If IT staff need all files at the same level as the .exe (old behavior), add `contents_directory='.'` to `EXE()`. For this tool the default `_internal/` layout is fine — `sys.executable` still resolves correctly.

### Pattern 3: build.bat

```batch
@ECHO OFF
REM StatusReport — One-command build script
REM Run from the repo root after cloning and creating .venv

ECHO Activating virtual environment...
CALL .venv\Scripts\activate.bat

ECHO Building status_report with PyInstaller...
CALL pyinstaller status_report.spec --noconfirm

IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] PyInstaller build failed. Check output above.
    EXIT /B %ERRORLEVEL%
)

ECHO.
ECHO Build complete. Distributable is in: dist\status_report\
ECHO Copy dist\status_report\ to the USB flash drive.
```

**Key points:**
- `CALL` before both `activate.bat` and `pyinstaller` — without `CALL`, the batch exits after the first call [CITED: PyInstaller discussions/7084]
- `--noconfirm` overwrites the previous `dist/status_report/` without prompting
- `EXIT /B %ERRORLEVEL%` propagates the exit code for CI / future automation use

### Anti-Patterns to Avoid

- **`--onefile`:** Extracts to `%TEMP%\_MEI*` at runtime — this is exactly what CrowdStrike Falcon's behavioral engine flags as suspicious (self-extracting + execute). Also writes to the host PC, violating PKG-02.
- **`os.getcwd()` for output path:** Returns the working directory (often `C:\Windows\System32` when double-clicked), not the USB drive. Always use `Path(sys.executable).parent`.
- **`sys.exit()` on collector failure:** Produces an empty error screen with no HTML. D-06 requires graceful degradation.
- **UPX compression:** `upx=True` in the spec packs DLLs with a known packer signature — increases AV suspicion significantly. Keep `upx=False`. [CITED: pythonguis.com/faq/problems-with-antivirus-software-and-pyinstaller]
- **`*.spec` in `.gitignore`:** The current `.gitignore` contains `*.spec`. This must be removed before committing `status_report.spec` per D-08. `.gitignore` already excludes `build/` and `dist/` correctly.
- **Building from system Python (not venv):** Bundling from system Python includes every globally installed package, producing bundles that can exceed 500 MB. Always build from the clean `.venv`. [CITED: PyInstaller docs]
- **`win32com.client.gencache.EnsureDispatch()`:** The gen_py runtime hook was removed in PyInstaller 6.x. The `wmi` module uses `win32com.client.GetObject()`, not `EnsureDispatch`, so this is not a concern for this project. Do not add gen_py hooks.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python → Windows .exe | Custom packing, cx_Freeze | PyInstaller 6.x | Handles DLL dependency resolution, pywin32 bootstrap, frozen sys path |
| pywin32 DLL discovery | Manual DLL copy in spec | PyInstaller's built-in pywin32 bootstrap (v5.5+) | Auto-adds `pywin32_system32` to search path at runtime; handles venv layout |
| COM dispatch type stubs | Pre-generating gen_py cache at build time | Don't — wmi uses `GetObject`, not `EnsureDispatch` | gen_py hook was removed in 6.x; wmi doesn't need it |
| Template bundling | File-copy script | `datas=[('renderer/templates', 'renderer/templates')]` in spec | Declarative; preserved in `_internal/renderer/templates/` at runtime |
| AV bypass | Obfuscation / custom bootloader | --onedir (no extraction) + test + request exclusion if needed | Obfuscation increases AV suspicion; --onedir is the correct architectural answer |

---

## Runtime State Inventory

> Step 2.5 trigger check: Phase 5 is a packaging phase — no rename, refactor, or migration. No existing runtime state is being changed by this phase. The exe runs read-only against the host machine and writes only to the USB.

Not applicable — greenfield exe + spec file creation. No stored data, live service config, OS-registered state, secrets, or stale build artifacts affected.

---

## Common Pitfalls

### Pitfall 1: wmi COM Imports Not Detected by PyInstaller

**What goes wrong:** `wmi` uses `win32com.client.GetObject()` which dispatches COM calls at runtime. PyInstaller cannot statically trace `import win32com.client` through COM dispatch. The frozen exe crashes on first WMI query with `ModuleNotFoundError: No module named 'win32com.client'`.

**Why it happens:** COM-based dispatch means the import chain is resolved dynamically at runtime, not at import-parse time.

**How to avoid:** Add explicit `hiddenimports=['wmi', 'win32com', 'win32com.client', 'pythoncom', 'pywintypes']` in the spec. Additionally use `collect_submodules('win32com')` to catch all submodules. Run trial build → execute frozen exe → iterate on any `ModuleNotFoundError`.

**Warning signs:** Build succeeds but exe crashes immediately, or crashes on first `wmi.WMI()` call. Check the console output for `ModuleNotFoundError` lines.

[VERIFIED: venv inspection] wmi 1.5.1 is a single `wmi.py` module; its entry points use `win32com.client`. win32com is at `.venv/Lib/site-packages/win32com/`.

### Pitfall 2: pywintypes312.dll / pythoncom312.dll Not Found at Runtime

**What goes wrong:** Frozen exe raises `ImportError: DLL load failed while importing win32api` or similar. The DLLs exist in the venv at `pywin32_system32/` but are not being found by the frozen exe's DLL loader.

**Why it happens:** PyInstaller 6.x introduced DLL directory structure preservation. The pywin32 bootstrap adds `pywin32_system32` to the DLL search path at runtime — but this only works if PyInstaller collected the bootstrap module.

**How to avoid:** Install PyInstaller 6.20.0 (not older). The pywin32 bootstrap fix was introduced in 5.5 and should auto-collect the `pywin32_system32` directory. Do NOT manually copy DLLs to top-level in the spec (old workaround); let PyInstaller handle it. If the error still appears, add explicit `binaries` entries:

```python
binaries=[
    ('.venv/Lib/site-packages/pywin32_system32/pywintypes312.dll', 'pywin32_system32'),
    ('.venv/Lib/site-packages/pywin32_system32/pythoncom312.dll', 'pywin32_system32'),
],
```

**Warning signs:** Build completes; exe crashes before any output with DLL load error.

[VERIFIED: venv inspection] pywintypes312.dll and pythoncom312.dll confirmed at `.venv/Lib/site-packages/pywin32_system32/`.
[CITED: pyinstaller.org/en/v6.1.0/CHANGES.html] pywin32 bootstrap introduced in PyInstaller 5.5.

### Pitfall 3: Jinja2 Templates Not Found in Frozen Bundle

**What goes wrong:** `renderer/_load_template_source()` raises `FileNotFoundError` when the frozen exe tries to read `character_sheet.html` via `importlib.resources`.

**Why it happens:** `ir.files('renderer').joinpath('templates/character_sheet.html')` works in development because `renderer/templates/` is on the filesystem. In a frozen exe, files must be explicitly declared in `datas` in the spec; PyInstaller does not auto-collect arbitrary non-`.py` files.

**How to avoid:** The spec already includes `datas=[('renderer/templates', 'renderer/templates')]`. In `--onedir` mode this places the templates at `_internal/renderer/templates/` — which is where `importlib.resources` will look since `sys.path` is adjusted to point at `_internal/`. This pattern is verified to work in --onedir mode (files remain on disk; `ir.files()` traversal works).

**Warning signs:** `FileNotFoundError` mentioning `character_sheet.html` on first run.

[CITED: Phase 3 CONTEXT.md D-15] Template loaded via `importlib.resources` — this is PyInstaller-safe in --onedir mode.
[CITED: pyinstaller.org/en/stable/spec-files.html] datas tuples: (source, dest_in_bundle).

### Pitfall 4: `*.spec` in `.gitignore` Blocks D-08

**What goes wrong:** The developer commits `status_report.spec` but git silently ignores it (or refuses to add it). CI/IT staff cannot reproduce the build because the spec is absent from the repo.

**Why it happens:** The current `.gitignore` contains `*.spec` (line 12). This was likely added to ignore auto-generated trial spec files from `pyinstaller main.py` (which produces `main.spec`).

**How to avoid:** Remove the `*.spec` line from `.gitignore`. The spec is now an intentional, curated build artifact that must be version-controlled.

**Alternative (narrower):** If you want to keep ignoring auto-generated specs while keeping `status_report.spec`, add a negation rule after the glob: `!status_report.spec`. Either approach works; removal of `*.spec` is simpler.

[VERIFIED: git ls-files + .gitignore inspection]

### Pitfall 5: CrowdStrike Falcon Quarantine Blocks Exe

**What goes wrong:** IT staff copies `dist/status_report/` to USB, runs `status_report.exe` on an enrolled machine, and CrowdStrike quarantines or blocks it.

**Why it happens:** CrowdStrike uses behavioral detection (IOAs). In `--onefile` mode, the self-extraction behavior is a direct trigger. In `--onedir` mode, the risk is lower because nothing is extracted at runtime, but the PyInstaller bootloader signature may still appear in CrowdStrike's threat intelligence.

**How to avoid:**
1. Use `--onedir` (already decided; D-07)
2. Do NOT use UPX compression (`upx=False` in spec) — UPX is a known packer used by malware
3. Test on an enrolled machine before distribution (D-11)
4. If quarantined: request a path-based or hash-based exclusion from the CrowdStrike tenant admin (D-12a)
5. Code signing (DIST-V2-01) is the long-term answer — a signed exe with a known publisher is far less likely to be flagged

**Warning signs:** Exe silently fails to launch, or Windows shows "Operation did not complete successfully because the file contains a virus or potentially unwanted software."

[CITED: pythonguis.com/faq] --onedir distributes as a folder; nothing extracted at runtime; "behavior looks less suspicious to AV software."
[ASSUMED] The specific behavior of the Master Electronics CrowdStrike tenant with unsigned PyInstaller --onedir exes is unknown until the D-11 test is run.

### Pitfall 6: USB Write-Protection or Full Disk — Silent Failure

**What goes wrong:** `output_path.write_text(...)` raises `PermissionError` (write-protected USB) or `OSError: [Errno 28] No space left on device`. If not caught, Python shows an ugly traceback and the IT staff sees no actionable message.

**Why it happens:** USB drives can have hardware write-protection switches, be NTFS-formatted with ACL restrictions, or simply be full (the `_internal/` directory itself may consume most of the drive's capacity if it's small).

**How to avoid:** Wrap the write in a `try/except (PermissionError, OSError)` block in `main.py`. Print a clear, actionable error message before `sys.exit(1)`. Example messages:
- `PermissionError`: "Cannot write to USB drive — it may be write-protected. Check the physical lock switch."
- `OSError` with errno 28: "USB drive is full. Free space and try again."
- Generic `OSError`: Show the OS error string.

**Warning signs:** IT staff reports "tool ran but no HTML appeared." Check USB drive properties (free space, write protection).

### Pitfall 7: webbrowser.open() May Show Empty/Wrong URL on Some Machines

**What goes wrong:** `webbrowser.open(str(output_path))` opens the browser but shows an error or blank page instead of the HTML file.

**Why it happens:** On Windows, `webbrowser.open()` with an absolute path is generally reliable (`file:///D:/status_report/logs/status_PHX-INV-003_2026-05-05.html`). However, some enterprise environments block file:// protocol in the default browser (Chrome enterprise policy `BlockExternalExtensions` or similar).

**How to avoid:** This is low risk — `webbrowser.open()` is a best-effort feature (D-05). The file is already written before the browser opens. If the browser fails, IT staff can open the HTML file manually from the USB. Print the path before calling `webbrowser.open()` so IT always has the file location regardless of browser behavior.

No special handling needed beyond what D-05 already specifies. The frozen exe path issue that exists on Linux (XDG_DATA_DIRS modification) does NOT apply to Windows — `webbrowser` on Windows directly calls `ShellExecute`. [CITED: pyinstaller.org/en/stable/common-issues-and-pitfalls.html — Linux-only issue]

### Pitfall 8: Build Produces Oversized Bundle

**What goes wrong:** `dist/status_report/` exceeds the 50 MB success criterion (ROADMAP SC3), making it impractical to copy to small USB drives or causing slow copy times.

**Why it happens:** PyInstaller includes the full Python stdlib and all importable packages by default. Without `excludes`, packages like `tkinter`, `unittest`, `http`, `email` etc. are bundled even though the tool never uses them.

**How to avoid:**
- Use the `excludes` list in the spec (shown in Pattern 2 above)
- Build from `.venv` (not system Python or Conda) — this is the single most impactful step
- Run `pyi-archive_viewer dist/status_report/_internal/status_report.pkg` to inspect what was included
- Use `du -sh dist/status_report/` (or Windows: `dir /s dist\status_report\`) to measure total size

**Expected size:** psutil + wmi + jinja2 + pywin32 + stdlib subset ≈ 30–45 MB. Well under 50 MB target when built from clean venv with excludes.

---

## Code Examples

### Output Path Construction (frozen exe)

```python
# Source: CLAUDE.md constraint + Phase 2 D-04 pattern
import sys
from pathlib import Path

# In frozen exe: sys.executable = D:\status_report\status_report.exe
# Path(sys.executable).parent = D:\status_report\
# logs_dir = D:\status_report\logs\
usb_root = Path(sys.executable).parent
logs_dir = usb_root / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)
output_path = logs_dir / f"status_{hostname}_{date_str}.html"
```

### collect_submodules in Spec File

```python
# Source: pyinstaller.org/en/stable/hooks.html
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    'wmi', 'win32api', 'win32con', 'win32com', 'win32com.client',
    'pywintypes', 'pythoncom',
] + collect_submodules('win32com')
```

### build.bat — Correct CALL Syntax

```batch
@ECHO OFF
CALL .venv\Scripts\activate.bat
CALL pyinstaller status_report.spec --noconfirm
EXIT /B %ERRORLEVEL%
```

`CALL` is required before both commands; without it, the batch exits after `activate.bat`. [CITED: github.com/orgs/pyinstaller/discussions/7084]

### USB Write Error Handling

```python
# Source: Python stdlib OSError, PermissionError hierarchy
import errno

try:
    output_path.write_text(html, encoding="utf-8")
except PermissionError:
    print("[ERROR] Cannot write to USB drive — it may be write-protected.")
    print("        Check the physical lock switch on the drive.")
    sys.exit(1)
except OSError as e:
    if e.errno == errno.ENOSPC:
        print("[ERROR] USB drive is full. Free up space and try again.")
    else:
        print(f"[ERROR] Write failed: {e}")
    sys.exit(1)
```

### Checking Bundle Contents After Build

```bash
# Run after: pyinstaller status_report.spec
pyi-archive_viewer dist\status_report\_internal\status_report.pkg
# Interactive: type 'U' to list, look for wmi, win32com entries
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| --onefile (extracts to %TEMP%) | --onedir (no extraction) | PyInstaller 3.x onwards | No runtime extraction = lower AV false positive rate |
| DLLs scattered to top-level dir | DLL directory structure preserved; pywin32 bootstrap module | PyInstaller 5.5 (2022-10) | Auto-resolves pywin32 DLL lookup without manual spec entries |
| All files next to .exe | `_internal/` subdirectory (default) | PyInstaller 6.0 (2023) | Cleaner USB root; `sys.executable` parent still correct for output path |
| win32com gen_py runtime hook | Hook removed; not needed for `GetObject()` usage | PyInstaller 6.x (via issue 8309) | Simplifies spec; wmi.py uses GetObject, not EnsureDispatch |
| System Python for builds | Venv-based builds (clean deps only) | Best practice, always | 5× smaller bundles vs Conda/system Python |

**Deprecated/outdated:**
- UPX compression in PyInstaller: was common for size reduction; now increases AV false positive rate — skip it
- `pyinstaller main.py` (command-line, no spec): Use a committed spec file for reproducible builds

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Build environment | ✓ | 3.12.10 | — |
| .venv (project venv) | build.bat + pyinstaller | ✓ | present | — |
| PyInstaller | build.bat | ✗ | not installed | `pip install pyinstaller==6.20.0` in Wave 0 |
| pywin32 | PyInstaller hook + wmi | ✓ | 311 | — |
| wmi | collectors | ✓ | 1.5.1 | — |
| Jinja2 | renderer | ✓ | 3.1.6 | — |
| CrowdStrike-enrolled test machine | D-11 validation | ✗ | — | Manual step; blocker for distribution |

**Missing dependencies with no fallback:**
- CrowdStrike-enrolled test machine: D-11 is a manual validation checkpoint, not an automated build step. Distribution is blocked until this test is performed.

**Missing dependencies with fallback:**
- PyInstaller: not installed in venv. Wave 0 must add `pip install pyinstaller==6.20.0` to `requirements-dev.txt` and install it.

[VERIFIED: venv inspection via `pip list`]

---

## Open Questions

1. **Exact hidden imports for wmi/win32com on this specific machine**
   - What we know: wmi 1.5.1 uses `win32com.client.GetObject()`. PyInstaller may miss submodules. `collect_submodules('win32com')` is the safe default.
   - What's unclear: Which specific win32com submodules are invoked by WMI 1.5.1's dispatch path. Trial build is the only way to confirm.
   - Recommendation: Build with the full `collect_submodules('win32com')` list. Test frozen exe. Remove unused entries only if size is a problem.

2. **`render_html` vs `render_report` interface for main.py**
   - What we know: Renderer exposes `render_report(report, output_path)`. CONTEXT.md references `render_html(report) -> str`. These are incompatible.
   - What's unclear: Which approach the planner wants to adopt.
   - Recommendation: Add `render_html(report: AuditReport) -> str` to `renderer/__init__.py` (thin wrapper around `_build_context` + Jinja). `main.py` then controls write with the dynamic filename. No existing tests break.

3. **CrowdStrike Falcon behavior on ME tenant**
   - What we know: --onedir is significantly less flagged than --onefile. UPX off. Console mode.
   - What's unclear: ME's specific prevention policy — detect-only vs block, existing exclusions for dev tools, etc.
   - Recommendation: Build first, test on enrolled machine (D-11), escalate only if quarantined.

4. **Should spec use `contents_directory='.'` to flatten `_internal/`?**
   - What we know: Default PyInstaller 6 puts everything in `_internal/`. `sys.executable` parent is still the USB root dir. `importlib.resources` still works.
   - What's unclear: IT staff preference — does having `_internal/` confuse them?
   - Recommendation: Keep default `_internal/` layout. IT copies the whole `dist/status_report/` folder; internal structure doesn't matter.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PyInstaller 6.20.0's built-in pywin32 bootstrap will auto-collect pywintypes312.dll and pythoncom312.dll from the venv's `pywin32_system32/` directory without manual `binaries` entries in the spec | Pitfall 2, Standard Stack | DLL not found at runtime → exe crashes on first win32 call. Fallback: add explicit `binaries` entries. Trial build confirms. |
| A2 | `collect_submodules('win32com')` + explicit `wmi`, `win32com.client`, `pywintypes`, `pythoncom` hidden imports covers all transitive COM dispatch paths used by wmi 1.5.1 | Pitfall 1, Pattern 2 | Missing module at runtime when WMI queries execute. Fallback: add discovered modules to spec after trial run error analysis. |
| A3 | `--onedir` + `upx=False` on the ME CrowdStrike tenant does not trigger behavioral quarantine | Pitfall 5 | Exe quarantined before IT can run it. Fallback: path exclusion from CS admin (D-12a). |
| A4 | The `excludes` list in Pattern 2 (tkinter, unittest, http, etc.) does not accidentally exclude anything needed by wmi, psutil, or jinja2 | Pitfall 8, Pattern 2 | Missing module at runtime from over-aggressive exclusion. Fallback: remove offending exclude entries. Trial build + runtime test confirms. |
| A5 | `webbrowser.open(str(output_path))` with a file:// path works on all ME Windows 10/11 machines (no enterprise browser policy blocking file:// protocol) | Pitfall 7 | Browser opens but shows "This site can't be reached." File is already written; IT can open manually. Low severity. |

---

## Sources

### Primary (HIGH confidence)
- [pypi.org/project/pyinstaller](https://pypi.org/project/pyinstaller/) — version 6.20.0 confirmed, Python 3.8–3.14 support, release date 2026-04-22
- [pyinstaller.org/en/stable/spec-files.html](https://pyinstaller.org/en/stable/spec-files.html) — Analysis/PYZ/EXE/COLLECT structure, datas syntax
- [pyinstaller.org/en/stable/hooks.html](https://pyinstaller.org/en/stable/hooks.html) — collect_submodules, collect_data_files import syntax
- [pyinstaller.org/en/stable/common-issues-and-pitfalls.html](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html) — subprocess environment sanitization, webbrowser (Linux-only issue confirmed)
- Venv inspection (live) — Python 3.12.10, pywin32 311, wmi 1.5.1, Jinja2 3.1.6, pywintypes312.dll + pythoncom312.dll confirmed at expected paths

### Secondary (MEDIUM confidence)
- [pyinstaller.org/en/v6.1.0/CHANGES.html](https://pyinstaller.org/en/v6.1.0/CHANGES.html) — pywin32 bootstrap history (fixed in 5.5), DLL path preservation
- [pythonguis.com/faq/problems-with-antivirus-software-and-pyinstaller](https://www.pythonguis.com/faq/problems-with-antivirus-software-and-pyinstaller/) — --onedir vs --onefile AV behavior, UPX risk, enterprise whitelist path
- [github.com/orgs/pyinstaller/discussions/6771](https://github.com/orgs/pyinstaller/discussions/6771) — collect_submodules in spec file syntax

### Tertiary (LOW confidence)
- WebSearch results on CrowdStrike Falcon + PyInstaller — general behavioral detection principles; ME-specific policy unknown until D-11 test
- WebSearch on pywin32 312 hidden imports — multiple conflicting reports; trial build is authoritative

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyInstaller 6.20.0 verified via PyPI; all venv packages confirmed installed
- main.py patterns: HIGH — derived from locked decisions in CONTEXT.md + existing code contracts
- Spec file hiddenimports: MEDIUM — framework confirmed; exact wmi/win32com list requires trial build to finalize
- CrowdStrike behavior: LOW — --onedir is the correct choice but ME tenant policy unknown until D-11 test

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (PyInstaller releases frequently; re-check version if > 30 days)
