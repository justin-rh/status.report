# Phase 15: Extended CLI Flags - Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 5 (2 modified, 2 exposed/extracted, 1 new test, 1 doc update)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `main.py` | controller (CLI entry point) | request-response | `main.py` (existing `_run_cli`) | exact — same file, extending existing pattern |
| `collectors/windows/apps.py` | service (app detection) | CRUD | `collectors/windows/apps.py` (existing `_detect_one_app`) | exact — exposing existing private function |
| `collectors/mac/apps.py` | service (app detection) | CRUD | `collectors/mac/apps.py` (existing `_detect_one_app`) | exact — same pattern as Windows analog |
| `tests/test_cli_phase15.py` | test | request-response | `tests/test_main.py` (Phase 11 CLI tests) | role-match — same test structure, new flags |
| `ROADMAP.md` | config/doc | — | `.planning/ROADMAP.md` (existing SC lines) | exact — SC line removal/rewrite |

---

## Pattern Assignments

### `main.py` — Add `--json`, `--output`, `--app` flags

**Analog:** `main.py` existing `main()` and `_run_cli()` functions.

**Imports pattern** (lines 14–28 — already present, no new imports needed):
```python
from __future__ import annotations

import argparse
import datetime
import os
import socket
import subprocess
import sys
from pathlib import Path

from collectors import collect_all
from health_checks import evaluate_warnings
from models import AuditReport
from parsers.name_parser import parse_hostname
from renderer import render_html
```
New additions at the call site (inline, no new top-level imports):
```python
import dataclasses
import json
```
These are stdlib; import them at the top of `main.py` alongside existing stdlib imports.

**argparse block pattern** (lines 101–105 — extend this block):
```python
parser.add_argument("--name",     action="store_true", help="Print PC hostname to stdout and exit")
parser.add_argument("--serial",   action="store_true", help="Print device serial number to stdout and exit")
parser.add_argument("--warnings", action="store_true", help="Print active warnings to stdout and exit")
parser.add_argument("--updates",  action="store_true", help="Query Windows Update Agent for pending update count (slow; omitted by default)")
```
Add three new lines in the same style immediately after `--updates`:
```python
parser.add_argument("--json",   action="store_true", help="Write AuditReport as JSON alongside HTML report; full pipeline always runs")
parser.add_argument("--output", metavar="PATH",      help="Override default logs/ destination for all file output (HTML and JSON)")
parser.add_argument("--app",    metavar="NAME",      help="Run app-detection for one named app; print result to stdout and exit")
```

**cli_mode + dispatch pattern** (lines 106–109 — extend this block):
```python
# Existing (unchanged):
cli_mode = args.name or args.serial or args.warnings
if cli_mode:
    _run_cli(args)
    return
```
New dispatch inserted BEFORE the `cli_mode` block, AFTER `args = parser.parse_args()`:
```python
# --app: single-app detection path — exits before cli_mode check (D-14, Pitfall: --app is NOT cli_mode)
if args.app:
    _run_cli_app(args)
    return

# Existing cli_mode, modified to respect --json override (D-05, Pitfall 2)
cli_mode = args.name or args.serial or args.warnings
if cli_mode and not args.json:   # D-05: --json overrides targeted flags → full pipeline
    _run_cli(args)
    return
```

**`--output` path override pattern** (lines 146–151 — override `logs_dir` here):
```python
# Existing (platform-aware usb_root):
if sys.platform == "darwin":
    usb_root = Path(__file__).parent
else:
    usb_root = Path(sys.executable).parent

# NEW: override logs_dir with --output if provided (D-01, D-02 — no validation)
# Override BEFORE mkdir so the new dir is created (Pitfall 3)
if args.output:
    logs_dir = Path(args.output)
else:
    logs_dir = usb_root / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)   # unchanged
```

**Uniqueness counter pattern** (lines 152–157 — derive JSON path from same base):
```python
# Existing HTML uniqueness loop (unchanged):
base_name = f"{date_str}_scry_{hostname}"
output_path = logs_dir / f"{base_name}.html"
counter = 2
while output_path.exists():
    output_path = logs_dir / f"{base_name} ({counter}).html"
    counter += 1

# NEW: derive JSON path after HTML uniqueness is resolved (D-04, Pattern 2)
# .with_suffix() reuses the already-unique base name; no second while-loop needed
if args.json:
    json_path = output_path.with_suffix(".json")
```

**HTML + JSON write pattern** (lines 161–173 — JSON write goes inside existing try/except):
```python
# Existing HTML write (unchanged structure):
try:
    output_path.write_text(html, encoding="utf-8")
    # NEW: write JSON inside same try/except so JSON only writes if HTML succeeded (Pitfall 5)
    if args.json:
        payload = json.dumps(dataclasses.asdict(report), indent=2, default=str)
        json_path.write_text(payload, encoding="utf-8")
except PermissionError:
    print("[ERROR] Cannot write to USB drive -- it may be write-protected.")
    print("        Check the physical lock switch on the drive.")
    sys.exit(1)
except OSError as exc:
    import errno as _errno
    if exc.errno == _errno.ENOSPC:
        print("[ERROR] USB drive is full. Free up space and try again.")
    else:
        print(f"[ERROR] Write failed: {exc}")
    sys.exit(1)
```

**`[SUMMARY]` line** (line 183 — unchanged; D-06 says it still prints when `--json` runs full pipeline):
```python
print(f"[SUMMARY] {hostname} | {report.os_version or 'Unknown OS'} | {cpu} | {ram} | {disk_used_pct}% disk used | {warning_count} warnings")
```

**New function `_run_cli_app(args)` — place alongside `_run_cli()` before `main()`:**

App name lookup pattern (D-09, D-10, D-11 — derived from APP_SPECS structure):
```python
def _find_app_spec(query: str, specs: list[dict]) -> dict | None:
    q = query.lower()
    for spec in specs:
        if q in spec["name"].lower():
            return spec
    return None
```

Platform dispatch + minimal report + single-spec detection (D-14, Pattern 3):
```python
def _run_cli_app(args: argparse.Namespace) -> None:
    """Handle --app <name> mode: detect one app, print result to stdout, exit.
    Never writes files (D-08/D-13). Exits 0 on match, 1 on no match (D-11).
    """
    import datetime
    import socket
    from parsers.name_parser import parse_hostname
    from models import AuditReport

    if sys.platform == "darwin":
        from collectors.mac.apps import _detect_one_app, MAC_APP_SPECS as specs
    else:
        from collectors.windows.apps import _detect_one_app, APP_SPECS as specs

    spec = _find_app_spec(args.app, specs)
    if spec is None:
        known = ", ".join(s["name"] for s in specs)
        print(f"Unknown app: {args.app}. Known apps: {known}", file=sys.stderr)
        sys.exit(1)

    hostname = socket.gethostname()
    report = AuditReport(
        hostname=hostname,
        parsed_hostname=parse_hostname(hostname),
        timestamp=datetime.datetime.now().isoformat(),
    )
    try:
        _detect_one_app(spec, report)    # mutates report.apps — never raises (D-16)
    except Exception as exc:
        report.collection_errors.append(str(exc))
        from models import AppStatus
        report.apps.append(AppStatus(name=spec["name"], installed=False, error=str(exc)))

    app_status = report.apps[0]

    if args.json:
        # D-13: raw AppStatus dict to stdout, no wrapper, no files written
        import dataclasses, json
        print(json.dumps(dataclasses.asdict(app_status), indent=2))
    else:
        # D-12: single-line format; Claude's discretion applied per RESEARCH.md Pattern 5
        print(_format_app_status_line(app_status))

    sys.exit(0)
```

Single-line format helper (D-12, Claude's discretion — version with `v` prefix, service_state fallback, bare "installed" when neither):
```python
def _format_app_status_line(app_status) -> str:
    if not app_status.installed:
        return f"{app_status.name}: not installed"
    if app_status.version:
        return f"{app_status.name}: installed (v{app_status.version})"
    if app_status.service_state:
        return f"{app_status.name}: installed ({app_status.service_state})"
    return f"{app_status.name}: installed"
```

---

### `collectors/windows/apps.py` — Expose `_detect_one_app` for single-app lookup

**What changes:** No implementation change needed. The function already exists at line 395 with the correct signature `_detect_one_app(spec: dict, report: AuditReport) -> None`. The `--app` handler in `main.py` imports it directly (intentional internal use per RESEARCH.md Pitfall 4 — add comment referencing D-14).

**Existing function signature** (lines 395–407 — copy as-is):
```python
def _detect_one_app(spec: dict, report: AuditReport) -> None:
    """Run detection logic for a single app spec and append one AppStatus to report.apps.
    ...
    Never raises — caller (detect_apps) wraps in try/except.
    """
```

**APP_SPECS name field** (lines 67–127 — the lookup source for `--app` matching):
```python
APP_SPECS: list[dict] = [
    {"name": "NinjaOne",          ...},
    {"name": "CrowdStrike Falcon", ...},
    {"name": "Zscaler",           ...},
    {"name": "MERP",              ...},
    {"name": "Microsoft 365",     ...},
    {"name": "Zoom Workplace",    ...},
    {"name": "Google Chrome",     ...},
    {"name": "Claude",            ...},
    {"name": "Company Portal",    ...},
]
```

**Error accumulation pattern** (lines 479–490 — copy for the `--app` fallback in `_run_cli_app`):
```python
except Exception as exc:
    report.collection_errors.append(
        f"App detection failed for {spec['name']}: {exc}"
    )
    report.apps.append(AppStatus(
        name=spec["name"],
        installed=False,
        error=str(exc),
    ))
```

---

### `collectors/mac/apps.py` — Expose `_detect_one_app` for single-app lookup

**What changes:** Same as Windows — no implementation change. The function exists at line 122 with identical signature. Import path is `collectors.mac.apps._detect_one_app`.

**MAC_APP_SPECS name field** (lines 41–78 — the lookup source on `sys.platform == "darwin"`):
```python
MAC_APP_SPECS: list[dict] = [
    {"name": "NinjaOne",          ...},   # "NinjaOne" — same name as Windows
    {"name": "CrowdStrike Falcon", ...},  # "CrowdStrike Falcon" — same name as Windows
    {"name": "Microsoft 365",     ...},   # same name, different detection
    {"name": "Zoom",              ...},   # "Zoom" NOT "Zoom Workplace" — Pitfall 1 from RESEARCH.md
    {"name": "Google Chrome",     ...},
    {"name": "Claude",            ...},
    {"name": "Company Portal",    ...},
]
# NOTE: Zscaler and MERP are Windows-only. MAC_APP_SPECS has 7 entries vs Windows 9.
# --app zscaler will return "Unknown app" on Mac — correct behavior, not a bug.
```

---

### `tests/test_cli_phase15.py` (new)

**Analog:** `tests/test_main.py` (lines 175–322 — Phase 11 CLI flag tests)

**Imports pattern** (copy from `test_main.py` lines 1–20):
```python
from __future__ import annotations

from unittest.mock import MagicMock, patch, mock_open
import pytest
from models import AuditReport, AppStatus
from parsers.name_parser import parse_hostname
```

**Test structure pattern** (copy from `test_main.py` lines 175–186):
```python
def test_name_flag_prints_hostname(capsys):
    """--name prints the hostname and exits 0 (D-08: no collect_all needed)."""
    import main
    with (
        patch("sys.argv", ["scry", "--name"]),
        patch("main.socket.gethostname", return_value="PHX-INV-001"),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "PHX-INV-001"
```

**Pattern for `--app` found / not-installed** (derive from above; patch `_detect_one_app` to produce AppStatus):
```python
def test_app_flag_not_installed(capsys):
    """--app ninjaone prints '<name>: not installed' when app is absent."""
    import main
    fake_status = AppStatus(name="NinjaOne", installed=False)
    def fake_detect(spec, report):
        report.apps.append(fake_status)
    with (
        patch("sys.argv", ["scry", "--app", "ninjaone"]),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.apps._detect_one_app", side_effect=fake_detect),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "NinjaOne: not installed"
```

**Pattern for `--app` not-found / exit 1** (D-11):
```python
def test_app_flag_unknown_exits_1(capsys):
    """--app with unrecognized name prints to stderr and exits 1 (D-11)."""
    import main
    with (
        patch("sys.argv", ["scry", "--app", "unknowntool"]),
        patch("main.sys.platform", "win32"),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Unknown app: unknowntool" in captured.err
    assert "Known apps:" in captured.err
```

**Pattern for `--app --json`** (D-13, no files written; JSON to stdout):
```python
def test_app_json_flag_prints_json_to_stdout(capsys):
    """--app ninjaone --json prints AppStatus dict as JSON to stdout; no files written (D-13)."""
    import main, json
    fake_status = AppStatus(name="NinjaOne", installed=True, version="5.3.1")
    def fake_detect(spec, report):
        report.apps.append(fake_status)
    mock_write = MagicMock()
    with (
        patch("sys.argv", ["scry", "--app", "ninjaone", "--json"]),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.apps._detect_one_app", side_effect=fake_detect),
        patch("pathlib.Path.write_text", mock_write),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    assert mock_write.call_count == 0, "No files should be written in --app --json mode"
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["name"] == "NinjaOne"
    assert data["installed"] is True
```

**Pattern for `--json` full pipeline** (D-04, D-06 — HTML + JSON written, `[SUMMARY]` in stdout):
```python
def test_json_flag_writes_json_alongside_html(capsys):
    """--json flag triggers full pipeline; JSON file written alongside HTML (D-04)."""
    import main
    written_files = {}
    def fake_write_text(self, content, encoding="utf-8"):
        written_files[str(self)] = content
    with _patched_main(isatty_value=False):
        with (
            patch("sys.argv", ["scry", "--json"]),
            patch("pathlib.Path.write_text", fake_write_text),
        ):
            main.main()
    json_writes = {k: v for k, v in written_files.items() if k.endswith(".json")}
    assert len(json_writes) == 1, "Exactly one JSON file should be written"
    captured = capsys.readouterr()
    assert "[SUMMARY]" in captured.out
```

**Pattern for `--output` override** (D-01):
```python
def test_output_flag_overrides_logs_dir(capsys):
    """--output <path> directs file output to provided path, not default logs/ (D-01)."""
    import main
    written_paths = []
    original_write = MagicMock()
    def capture_write(self, content, encoding="utf-8"):
        written_paths.append(str(self))
    with _patched_main(isatty_value=False):
        with (
            patch("sys.argv", ["scry", "--output", "/custom/audit_results"]),
            patch("pathlib.Path.write_text", capture_write),
        ):
            main.main()
    assert any("/custom/audit_results" in p for p in written_paths), (
        f"Expected output under /custom/audit_results; got: {written_paths}"
    )
```

**Pattern for `--json` overrides `--name`/`--serial`/`--warnings`** (D-05):
```python
def test_json_overrides_cli_mode_flags(capsys):
    """--json overrides --name/--serial/--warnings — full pipeline runs, no early exit (D-05)."""
    import main
    with _patched_main(isatty_value=False):
        with patch("sys.argv", ["scry", "--json", "--name"]):
            main.main()   # Must NOT raise SystemExit(0) from _run_cli
    captured = capsys.readouterr()
    assert "[SUMMARY]" in captured.out, "--json must run full pipeline even with --name present"
```

---

### `ROADMAP.md` — Remove SC2 host-path rejection

**Location:** `.planning/ROADMAP.md` line 103 (current SC2 text):
```
2. Running `scry.exe --output D:\audit_results` writes both HTML and JSON to that path; running with a host-PC path (e.g. `C:\Users\...`) is rejected with a clear error and no files written
```

**Replace with** (D-03 from CONTEXT.md):
```
2. Running `scry.exe --output D:\audit_results` writes both HTML and JSON (when `--json` is also passed) to that path; any writable path is accepted
```

---

## Shared Patterns

### Never-raise collector boundary
**Source:** `collectors/windows/apps.py` lines 479–490, `collectors/mac/apps.py` lines 189–200
**Apply to:** `_run_cli_app()` in `main.py` when calling `_detect_one_app()`
```python
try:
    _detect_one_app(spec, report)
except Exception as exc:
    report.collection_errors.append(str(exc))
    report.apps.append(AppStatus(name=spec["name"], installed=False, error=str(exc)))
```

### AuditReport construction (minimal, for --app mode)
**Source:** `main.py` lines 116–120 and `tests/test_main.py` lines 37–48
**Apply to:** `_run_cli_app()` throwaway report construction
```python
report = AuditReport(
    hostname=hostname,
    parsed_hostname=parse_hostname(hostname),
    timestamp=datetime.datetime.now().isoformat(),
)
```

### JSON serialization
**Source:** RESEARCH.md Code Examples (verified via interactive test)
**Apply to:** `--json` full-pipeline write in `main()`, `--app --json` stdout write in `_run_cli_app()`
```python
# Full report:
payload = json.dumps(dataclasses.asdict(report), indent=2, default=str)
json_path.write_text(payload, encoding="utf-8")

# Single AppStatus (--app --json):
print(json.dumps(dataclasses.asdict(app_status), indent=2))
```

### `sys.exit` + `pytest.raises(SystemExit)` test pattern
**Source:** `tests/test_main.py` lines 179–186
**Apply to:** All new `test_cli_phase15.py` tests that exercise early-exit paths (`--app`, `--app --json`)
```python
with pytest.raises(SystemExit) as exc_info:
    main.main()
assert exc_info.value.code == 0   # or 1 for not-found
```

### `patch("sys.argv", ...)` test wiring
**Source:** `tests/test_main.py` line 180 and all subsequent CLI tests
**Apply to:** Every new test in `test_cli_phase15.py`
```python
with patch("sys.argv", ["scry", "--app", "ninjaone"]):
    ...
```

---

## No Analog Found

All files have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `main.py`, `collectors/windows/apps.py`, `collectors/mac/apps.py`, `models.py`, `tests/test_main.py`, `.planning/ROADMAP.md`
**Files scanned:** 6
**Pattern extraction date:** 2026-05-18
