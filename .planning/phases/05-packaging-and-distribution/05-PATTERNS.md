# Phase 5: Packaging and Distribution - Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 6 (3 new, 3 modified)
**Analogs found:** 5 / 6 (status_report.spec has no analog — novel file type)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `main.py` | entry-point | request-response (pipeline) | `collectors/__init__.py` | role-match — both are thin orchestrators |
| `status_report.spec` | config | batch | none | no analog — novel file type |
| `build.bat` | utility | batch | none (no .bat files exist) | no analog — novel file type |
| `renderer/__init__.py` | service | transform | `renderer/__init__.py` itself | exact — additive change only |
| `.gitignore` | config | — | `.gitignore` itself | exact — line removal |
| `requirements-dev.txt` | config | — | `requirements-dev.txt` itself | exact — line addition |

---

## Pattern Assignments

### `main.py` (entry-point, pipeline orchestration)

**Analog:** `collectors/__init__.py` (thin orchestrator that calls sub-layers in order, never raises, mutates a shared data object)

**Secondary analog for error handling:** `collectors/windows/hardware.py` (pattern: try/except per sub-call, append to `collection_errors`, degrade gracefully)

**Imports pattern** — project conventions from `collectors/__init__.py` lines 1-6 and `collectors/windows/hardware.py` lines 1-13:
```python
from __future__ import annotations
import sys
import socket
import datetime
import webbrowser
from pathlib import Path

from models import AuditReport
from parsers.name_parser import parse_hostname
from collectors import collect_all
from renderer import render_html  # new function added in this phase (Option A)
```

**Core orchestration pattern** — modeled after `collectors/__init__.py` lines 9-21 (sequential calls, in-place mutation, no re-assignment):
```python
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
    collect_all(report)  # mutates report in place — never re-assign

    # Surface collector warnings — pattern from hardware.py lines 108-111
    for err in report.collection_errors:
        print(f"[WARN] {err}")

    print("Rendering character sheet...")

    # Output path — USB only (CLAUDE.md constraint, D-02)
    # Path(sys.executable).parent = USB root when running as frozen exe
    usb_root = Path(sys.executable).parent
    logs_dir = usb_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    output_path = logs_dir / f"status_{hostname}_{date_str}.html"

    html = render_html(report)

    try:
        output_path.write_text(html, encoding="utf-8")
    except PermissionError:
        print("[ERROR] Cannot write to USB drive — it may be write-protected.")
        print("        Check the physical lock switch on the drive.")
        sys.exit(1)
    except OSError as e:
        import errno as _errno
        if e.errno == _errno.ENOSPC:
            print("[ERROR] USB drive is full. Free up space and try again.")
        else:
            print(f"[ERROR] Write failed: {e}")
        sys.exit(1)

    print(f"Saved: {output_path}")
    print("Opening in browser...")
    webbrowser.open(str(output_path))
    print("Done.")


if __name__ == "__main__":
    main()
```

**Error handling pattern** — copy from `collectors/windows/hardware.py` lines 108-118 (try/except, append error string, degrade silently for collectors; `sys.exit(1)` only for fatal write failures per D-06):
```python
# Collector-level: never exit, just accumulate
try:
    c = _wmi_module.WMI()
    ...
except Exception as exc:
    report.collection_errors.append(f"CPU model collection failed (WMI): {exc}")

# Write-level: fatal, print actionable message, exit
except PermissionError:
    print("[ERROR] Cannot write to USB drive — it may be write-protected.")
    sys.exit(1)
```

**Pathlib convention** — copy from `writers/__init__.py` lines 9-18 (always `Path.write_text`, never `open()`):
```python
# writers/__init__.py lines 16-17 — project write convention
dest = output_path / 'status_report.html'
dest.write_text(html, encoding='utf-8')

# main.py equivalent (full path already constructed):
output_path.write_text(html, encoding='utf-8')
```

---

### `status_report.spec` (config, batch build definition)

**Analog:** None — no existing `.spec` file in the codebase. Use RESEARCH.md Pattern 2 as the authoritative template.

**Key conventions from RESEARCH.md Pattern 2:**
```python
# Source: RESEARCH.md Pattern 2 + pyinstaller.org/en/stable/spec-files.html
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

win32com_hidden = collect_submodules('win32com')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # renderer/templates must be declared — PyInstaller does not auto-collect .html
        # In --onedir: lands at _internal/renderer/templates/ where ir.files() finds it
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
        'tkinter', 'unittest', 'email', 'xml', 'xmlrpc',
        'http', 'urllib', 'multiprocessing', 'concurrent',
        'asyncio', 'sqlite3', 'ssl', '_ssl', 'test',
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
    upx=False,       # NEVER True — UPX increases AV suspicion (RESEARCH.md Anti-Patterns)
    console=True,    # D-04: show console window; NEVER --noconsole
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

---

### `build.bat` (utility, batch)

**Analog:** None — no `.bat` files exist in the project. Use RESEARCH.md Pattern 3.

**Key conventions from RESEARCH.md Pattern 3 (CALL syntax is critical):**
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

**Critical:** `CALL` is required before both `activate.bat` and `pyinstaller`. Without `CALL`, the batch file exits immediately after the first command returns. (RESEARCH.md Pitfall footnote; cited: github.com/orgs/pyinstaller/discussions/7084)

---

### `renderer/__init__.py` (service, transform) — ADDITIVE MODIFICATION ONLY

**Analog:** `renderer/__init__.py` itself — this is an additive change. A new `render_html()` function is inserted alongside the existing `render_report()`. No existing code changes.

**Current file state** (`renderer/__init__.py` lines 1-59 — read in full above):
- Public entry point: `render_report(report: AuditReport, output_path: Path) -> Path` (lines 46-59)
- Calls `write_html(html, output_path)` internally (line 59)
- `write_html` appends hardcoded `status_report.html` to a directory path — incompatible with D-03 dynamic filename

**Pattern for new `render_html()` function** — thin wrapper, same signature style as `render_report()` (lines 46-48):
```python
def render_html(report: AuditReport) -> str:
    """Return rendered HTML string for report without writing to disk.

    Option A resolution of the render_report/render_html interface conflict
    (RESEARCH.md § Interface Conflict). main.py calls this to get the HTML
    string, then writes it directly to the dynamically-named output path.
    Existing render_report() and write_html() are unchanged — no test breakage.
    """
    template_source = _load_template_source()
    env = Environment(autoescape=True)
    template = env.from_string(template_source)
    ctx = _build_context(report)
    return template.render(**ctx)
```

**Insertion point:** Add `render_html()` immediately after `render_report()` (after line 59), before `_load_template_source()`. The module docstring on line 1 should also reference the new function.

**Updated module docstring:**
```python
"""HTML character sheet renderer. Phase 3.
render_report(report, output_path) writes HTML to a directory (existing).
render_html(report) returns the HTML string without writing (Phase 5 addition).
Never raises on None hardware fields — D-12/D-13 None handling is in _build_context().
"""
```

---

### `.gitignore` (config) — LINE REMOVAL

**Current file** (`.gitignore` lines 1-23 — read in full above):

Line 12 currently reads:
```
*.spec
```

**Required change:** Remove line 12 (`*.spec`) entirely. The spec file `status_report.spec` must be committed per D-08. Removing the glob is simpler than adding a negation rule (`!status_report.spec`).

**After removal, the PyInstaller section becomes:**
```gitignore
# PyInstaller build output
build/
dist/
```

No other lines change.

---

### `requirements-dev.txt` (config) — LINE ADDITION

**Current file** (`requirements-dev.txt` line 1):
```
pytest==8.*
```

**Required change:** Append `pyinstaller==6.20.0` on a new line:
```
pytest==8.*
pyinstaller==6.20.0
```

**Version rationale:** 6.20.0 is the latest stable (released 2026-04-22). Contains the pywin32 bootstrap fix (introduced in 5.5) that auto-collects `pywintypes312.dll` and `pythoncom312.dll` without manual `binaries` entries in the spec.

---

## Shared Patterns

### In-Place Mutation (never re-assign the report)
**Source:** `collectors/__init__.py` lines 9-21; `collectors/windows/hardware.py` lines 42-53
**Apply to:** `main.py`
```python
# collect_all mutates report; main.py never does: report = collect_all(report)
collect_all(report)
```

### Graceful Degradation (collectors never exit; write failures do exit)
**Source:** `collectors/windows/hardware.py` lines 60-65 (profiles), lines 108-118 (CPU)
**Apply to:** `main.py`
```python
# Collector pattern — accumulate, never exit
try:
    report.local_profiles = _enumerate_profiles()
except Exception as exc:
    report.collection_errors.append(f"Profile enumeration failed: {exc}")

# main.py applies D-06: only write failures warrant sys.exit(1)
```

### pathlib.Path.write_text (never open())
**Source:** `writers/__init__.py` lines 16-17
**Apply to:** `main.py`
```python
dest.write_text(html, encoding='utf-8')
```

### importlib.resources Template Loading (PyInstaller-safe)
**Source:** `renderer/__init__.py` lines 62-73
**Apply to:** `status_report.spec` datas declaration — the spec must bundle `renderer/templates/` so `ir.files('renderer')` resolves correctly inside `_internal/`
```python
# renderer/__init__.py lines 68-73 — the pattern that drives the spec datas entry
return (
    ir.files('renderer')
    .joinpath('templates/character_sheet.html')
    .read_text(encoding='utf-8')
)
# Required spec entry: datas=[('renderer/templates', 'renderer/templates')]
```

### from __future__ import annotations
**Source:** Every project module (`collectors/__init__.py` line 5, `renderer/__init__.py` line 5, `writers/__init__.py` line 3, `models.py` line 3)
**Apply to:** `main.py`, `render_html()` addition in `renderer/__init__.py`

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `status_report.spec` | config | batch | No PyInstaller spec files exist in the project; novel file type. Use RESEARCH.md Pattern 2. |
| `build.bat` | utility | batch | No batch/shell scripts exist in the project. Use RESEARCH.md Pattern 3. |

---

## Critical Constraints (from CLAUDE.md)

These must be enforced in every new file:

| Constraint | Enforced In | How |
|------------|-------------|-----|
| NEVER `--onefile` | `status_report.spec` | `EXE(exclude_binaries=True)` + `COLLECT()` = `--onedir`; no `onefile=True` |
| NEVER `os.getcwd()` for output | `main.py` | `Path(sys.executable).parent` only |
| NEVER write to host PC | `main.py` | All writes go to `usb_root / "logs" / filename` |
| NEVER `Win32_Product` | collectors (existing) | Not relevant to Phase 5 |
| Load templates via `importlib.resources` | `renderer/__init__.py` | Existing `_load_template_source()` unchanged; spec bundles the templates |

---

## Metadata

**Analog search scope:** All `.py` files in project root and subdirectories (excluding `.venv/`); `.gitignore`, `requirements.txt`, `requirements-dev.txt`
**Files scanned:** `collectors/__init__.py`, `collectors/windows/hardware.py`, `renderer/__init__.py`, `writers/__init__.py`, `models.py`, `parsers/name_parser.py`, `tests/test_writers.py`, `.gitignore`, `requirements-dev.txt`, `requirements.txt`
**Pattern extraction date:** 2026-05-05
