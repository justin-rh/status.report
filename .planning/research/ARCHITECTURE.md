# Architecture Research — v3.0 Integration

**Domain:** Windows IT audit executable — self-contained PyInstaller .exe, USB-deployed, read-only
**Researched:** 2026-05-14
**Confidence:** HIGH (based on direct source inspection of shipped v2.0 codebase)

---

## Baseline: Current v2.0 Architecture

```
status.report/
├── main.py                             # Orchestrator + argparse CLI (_run_cli / main)
├── models.py                           # AuditReport, ParsedHostname, AppStatus, Warning, CollectionResult
├── health_checks.py                    # evaluate_warnings() — pure function
│
├── collectors/
│   ├── __init__.py                     # collect_all() — lazy platform dispatch
│   ├── base.py                         # Stub (empty)
│   ├── windows/
│   │   ├── __init__.py
│   │   ├── hardware.py                 # collect_hardware(), collect_profiles()
│   │   └── apps.py                     # collect_apps(), detect_apps(), APP_SPECS table
│   └── mac/
│       ├── __init__.py
│       ├── hardware.py
│       └── apps.py
│
├── parsers/
│   └── name_parser.py
│
├── renderer/
│   ├── __init__.py                     # render_html() → str, render_report() → Path
│   └── templates/
│       └── character_sheet.html
│
└── writers/
    └── __init__.py                     # write_html(html, path) → Path
```

### Active Pipeline (v2.0, per main.py)

```
main()
  socket.gethostname() + parse_hostname()
  AuditReport(...)
  collect_all(report)              ← mutates in place, never raises
    collect_hardware(report)
    collect_profiles(report)
    collect_apps(report)
  report.warnings = evaluate_warnings(report)   ← pure function, returns list[Warning]
  html = render_html(report)       ← returns str, no side effects
  output_path = logs_dir / "status_{hostname}_{date}.html"
  output_path.write_text(html)
  print("[SUMMARY] ...")
  os.startfile() + input()         ← guarded by sys.stdin.isatty()
```

### Existing Guard Pattern (established in v2.0)

```python
# collectors/windows/hardware.py
try:
    import wmi as _wmi_module
    _WMI_AVAILABLE = True
except ImportError:
    _wmi_module = None
    _WMI_AVAILABLE = False
```

This pattern is the canonical way to make COM-dependent collectors importable on any platform (CI, Mac, test runners). All new COM dependencies follow this exact pattern.

---

## v3.0 Feature Integration

---

### Feature 1: System Health Collectors (HEALTH-01, HEALTH-02, WARN-04)

#### New file: `collectors/windows/health.py`

System health collection is its own domain and does not belong in `hardware.py` (which is already shipping and tested). A new `health.py` in `collectors/windows/` keeps the pattern consistent (one responsibility per file, same as `hardware.py` and `apps.py`).

```
collectors/windows/
    hardware.py     ← UNCHANGED
    apps.py         ← UNCHANGED
    health.py       ← NEW: collect_health(report)
```

**Uptime** uses `psutil.boot_time()` — no elevation required at standard user level. The calculation is `time.time() - psutil.boot_time()`. `psutil` is already a project dependency. No guard needed — `psutil` is always available.

**Pending Windows updates** uses the WUA COM API via `win32com.client.Dispatch("Microsoft.Update.Session")`. This requires `pywin32` (`win32com`). A module-level guard follows the exact `_wmi_module` pattern — rename to `_win32com` for clarity:

```python
# collectors/windows/health.py
try:
    import win32com.client as _win32com
    _WIN32COM_AVAILABLE = True
except ImportError:
    _win32com = None
    _WIN32COM_AVAILABLE = False
```

**Guard name: `_WIN32COM_AVAILABLE` (not `_WUA_AVAILABLE`).** Rationale: the same `win32com.client` import is shared by any future COM automation (not just WUA). Naming it after the library rather than the feature makes it reusable for vendor detection (Feature 2) if needed, and avoids a proliferation of per-feature guard names.

**WUA query (standard user, read-only search):**

```python
def _collect_pending_updates(report: AuditReport) -> None:
    if not _WIN32COM_AVAILABLE:
        return
    try:
        session = _win32com.Dispatch("Microsoft.Update.Session")
        searcher = session.CreateUpdateSearcher()
        result = searcher.Search("IsInstalled=0 and Type='Software'")
        report.pending_updates = result.Updates.Count
    except Exception as exc:
        report.collection_errors.append(f"Windows update count failed: {exc}")
```

IUpdateSearcher.Search() with "IsInstalled=0" is a read-only query that does not require elevation and does not trigger downloads or installs. This is consistent with the "no side effects on production machines" constraint.

**Public interface:**

```python
def collect_health(report: AuditReport) -> None:
    """Populate uptime_seconds and pending_updates on report. Never raises."""
    _collect_uptime(report)
    _collect_pending_updates(report)
```

#### Hook into `collect_all()`

`collectors/__init__.py` adds one import + one call to the Windows branch:

```python
# collectors/__init__.py
def collect_all(report: AuditReport) -> None:
    import sys
    if sys.platform == "darwin":
        from collectors.mac.hardware import collect_hardware, collect_profiles
        from collectors.mac.apps import collect_apps
    else:
        from collectors.windows.hardware import collect_hardware, collect_profiles
        from collectors.windows.apps import collect_apps
        from collectors.windows.health import collect_health   # NEW
    collect_hardware(report)
    collect_profiles(report)
    collect_apps(report)
    if sys.platform != "darwin":
        collect_health(report)                                  # NEW
```

`collect_health` is not called on Mac — health fields stay `None` on that platform, which is handled gracefully by `None`-safe rendering.

#### New fields on `AuditReport`

```python
@dataclass
class AuditReport:
    ...
    # System health — populated by health.py (Windows only)
    uptime_seconds: float | None = None
    pending_updates: int | None = None
```

Both fields default to `None`. No existing test fixtures break — all `AuditReport(...)` construction without these fields continues to work.

#### `UPTIME_STALE` warning in `health_checks.py`

The existing `evaluate_warnings()` returns exactly 3 warnings (one per check, enforced by tests). Adding `UPTIME_STALE` means returning 4 warnings. The test `test_evaluate_warnings_always_returns_three` must be updated to expect 4, and the constant `3` in that assertion becomes the count of non-uptime checks.

Threshold constant lives in `health_checks.py` alongside `OS_WARN_BUILD` and `DISK_WARN_PCT`:

```python
UPTIME_STALE_DAYS: int = 30   # WARN-04: warn if uptime exceeds this many days
```

New private check:

```python
def _check_uptime(report: AuditReport) -> Warning:
    """Return UPTIME_STALE Warning. WARN when uptime_seconds > UPTIME_STALE_DAYS * 86400."""
    if report.uptime_seconds is None:
        return Warning(code='UPTIME_STALE', severity='OK',
                       message='Uptime check skipped', detail='uptime_seconds not collected')
    days = report.uptime_seconds / 86400
    if days > UPTIME_STALE_DAYS:
        return Warning(code='UPTIME_STALE', severity='WARN',
                       message=f'Device has not rebooted in {int(days)} days',
                       detail=f'Last reboot was {int(days)} days ago (threshold: {UPTIME_STALE_DAYS} days)')
    return Warning(code='UPTIME_STALE', severity='OK',
                   message=f'Uptime is acceptable ({int(days)} days)',
                   detail=None)
```

`evaluate_warnings()` adds `_check_uptime(report)` to the returned list.

#### HTML rendering (Jinja2 template)

Uptime and pending updates appear in the **stat block** alongside CPU, RAM, disk — they are machine facts, not warnings. The UPTIME_STALE warning surfaces in the existing warnings section automatically (it is a `Warning` object like any other).

In `renderer/__init__.py`, `_build_context()` adds:

```python
# Uptime display
if report.uptime_seconds is not None:
    uptime_days = int(report.uptime_seconds // 86400)
    uptime_hours = int((report.uptime_seconds % 86400) // 3600)
    uptime_display = f"{uptime_days}d {uptime_hours}h"
else:
    uptime_display = None

# Pending updates display
pending_updates = report.pending_updates  # int | None; template uses | default('—')
```

Template stat block gains two rows. No new section, no new template file — two additional `<tr>` rows in the existing stats table.

---

### Feature 2: Vendor Update Detection (VENDOR-01, VENDOR-02)

#### New file: `collectors/windows/vendor_updates.py`

Vendor update detection is Dell-specific and Lenovo-specific. It does not belong in `health.py` (health is OS-level signals) or `apps.py` (apps is installed software detection). A dedicated `vendor_updates.py` isolates this logic cleanly and makes it easy to add HP or other vendors later.

```
collectors/windows/
    hardware.py
    apps.py
    health.py
    vendor_updates.py    ← NEW: collect_vendor_updates(report)
```

#### Dell Command Update (VENDOR-01)

Dell Command Update installs `dcu-cli.exe` at one of two paths:
- `C:\Program Files (x86)\Dell\CommandUpdate\dcu-cli.exe` (older)
- `C:\Program Files\Dell\CommandUpdate\dcu-cli.exe` (newer)

Detection strategy: check if `dcu-cli.exe` exists. If it does, run `/scan -silent -report=<tmpdir>` and count `<update>` elements in the generated `DCUApplicableUpdates.xml`. This produces an exact pending count.

**No elevation required** for `/scan`. Dell Command Update's scan-only mode is designed for standard user invocation. The `-report` flag writes the XML to a caller-specified path; write to a temp directory under `%TEMP%` (this is the one permitted host-write — `%TEMP%` is a per-session scratch space, not a permanent artifact). However, the project constraint is "no writes to the host PC." The workaround: write the report XML to a subdirectory of `Path(sys.executable).parent` (the USB), not to the host. On failure, fall back to counting the `<update>` occurrences in stdout if `/scan` produces parseable output, otherwise leave `dell_pending = None`.

Actually, a simpler approach avoids host writes entirely: use only the exit code. Exit code 0 = no updates pending; exit code non-zero with specific codes = updates found. However, the exit codes do not give a count.

**Recommended approach:** Run `dcu-cli.exe /scan -silent` (no `-report` flag), capture stdout, parse the update count from stdout text patterns ("X update(s) found"), or capture the return code. If stdout is machine-parseable, extract the count. If it is not (varies by version), set `dell_pending = None` and only record `True/False` whether updates exist.

Because stdout format varies across DCU versions 3.x/4.x/5.x, use a defensive parse: attempt regex match for a count, fall back to `None` if pattern not found. Never write to host PC.

```python
def _collect_dell_updates(report: AuditReport) -> None:
    dcu_paths = [
        Path(r"C:\Program Files (x86)\Dell\CommandUpdate\dcu-cli.exe"),
        Path(r"C:\Program Files\Dell\CommandUpdate\dcu-cli.exe"),
    ]
    dcu_exe = next((p for p in dcu_paths if p.exists()), None)
    if dcu_exe is None:
        return  # Not a Dell machine or DCU not installed
    try:
        result = subprocess.run(
            [str(dcu_exe), "/scan", "-silent"],
            capture_output=True, text=True, timeout=120
        )
        # Attempt to parse count from stdout; leave None if unparseable
        import re
        m = re.search(r'(\d+)\s+update', result.stdout, re.IGNORECASE)
        report.dell_pending = int(m.group(1)) if m else None
    except Exception as exc:
        report.collection_errors.append(f"Dell update scan failed: {exc}")
```

**Timeout:** `dcu-cli /scan` can take 60-90 seconds on a slow machine. Use `timeout=120`.

#### Lenovo System Update (VENDOR-02)

Lenovo System Update installs at `C:\Program Files\Lenovo\System Update\tvsukernel.exe`. There is no documented standard-user CLI scan-only mode analogous to Dell's. The Lenovo tools are designed for interactive use or SCCM/WSUS integration.

**Recommended approach for v3.0:** Detect whether Lenovo System Update is installed (check the exe path and/or registry Uninstall key). If installed, report `lenovo_pending = None` (unknown count) rather than attempting a CLI invocation that may hang or prompt for elevation. Record installed status only. This is honest and avoids any risk of side effects on a production machine.

This is a deliberate conservative choice. The roadmapper should flag VENDOR-02 as needing a deeper research phase if a count is truly required — Lenovo's CLI documentation is thin and behavior varies across ThinkPad/IdeaPad firmware update suites.

```python
def _collect_lenovo_updates(report: AuditReport) -> None:
    lenovo_exe = Path(r"C:\Program Files\Lenovo\System Update\tvsukernel.exe")
    if lenovo_exe.exists():
        # Lenovo System Update is installed; pending count not queryable without elevation/interaction
        report.lenovo_pending = None  # presence known, count unknown
        # Could set a boolean flag instead; field type reflects this ambiguity
```

**Alternative:** If the project decides a count is mandatory, a future phase can investigate writing the Lenovo scan report to USB and parsing it. For v3.0, `None` is the correct and safe value.

#### Platform dispatch

`vendor_updates.py` is Windows-only. Add to the Windows branch of `collect_all()`:

```python
from collectors.windows.vendor_updates import collect_vendor_updates  # NEW
...
collect_vendor_updates(report)  # NEW — after collect_apps
```

#### New fields on `AuditReport`

```python
@dataclass
class AuditReport:
    ...
    # Vendor update detection — Windows only
    dell_pending: int | None = None     # int if Dell + DCU installed + count parseable; None otherwise
    lenovo_pending: int | None = None   # None for v3.0 (presence known, count unknown for Lenovo)
```

`None` semantics: `None` means "not applicable" (not a Dell/Lenovo machine, or tool not installed) or "count could not be determined." The HTML template must handle this with `| default('—')` — same pattern as all other nullable fields.

#### HTML rendering

Vendor update counts appear in a new row in the stat block or as a sub-row under the OS/hardware section. They are informational facts, not warnings, so they do not trigger warning-severity treatment. The template adds two rows (Dell Pending, Lenovo Pending) that render `—` when `None`.

If `dell_pending` is an integer greater than 0, the renderer may apply a visual indicator (amber text). This is a rendering detail; the data model carries only `int | None`.

---

### Feature 3: Extended CLI Flags (OUT-V3-01, OUT-V3-02, CLI-V3-01)

#### 3a. `--json` flag (OUT-V3-01)

**Serialization location:** `writers/json_writer.py` (new file). This keeps serialization logic out of `models.py` (which is the data contract, not a serialization layer) and out of `main.py` (which is the orchestrator, not a formatter).

```python
# writers/json_writer.py
import json
import dataclasses
from models import AuditReport

def report_to_json(report: AuditReport) -> str:
    """Serialize AuditReport to a JSON string. All fields included."""
    return json.dumps(dataclasses.asdict(report), indent=2, default=str)
```

`dataclasses.asdict()` recursively converts all nested dataclasses (`ParsedHostname`, `AppStatus`, `Warning`) to dicts. The `default=str` fallback handles any types JSON cannot serialize natively (e.g., `Path` objects if any appear).

`writers/__init__.py` gains a re-export:

```python
# writers/__init__.py
from writers.json_writer import report_to_json  # NEW
```

**main.py pipeline for `--json`:** When `--json` is passed as a standalone flag (no `--app`):
1. Run the full pipeline (collect + evaluate_warnings + render_html as normal)
2. Additionally serialize `report_to_json(report)`
3. Write the JSON to `logs/status_{hostname}_{date}.json` (same `logs_dir` logic, same collision-avoidance counter)
4. Print the JSON path to stdout

The HTML is still written. `--json` is additive — it adds a JSON artifact alongside the HTML.

#### 3b. `--output <path>` flag (OUT-V3-02)

**Layer ownership:** The output path derivation lives in `main.py` — that is where it currently lives and where it should stay. `main.py` is the orchestrator that controls where output goes; no other layer needs to know.

Current derivation:
```python
if sys.platform == "darwin":
    usb_root = Path(__file__).parent
else:
    usb_root = Path(sys.executable).parent
logs_dir = usb_root / "logs"
```

With `--output`:
```python
if args.output:
    logs_dir = Path(args.output)
else:
    # existing logic
    usb_root = ...
    logs_dir = usb_root / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)
```

`--output` replaces `logs_dir` entirely. The filename and collision-avoidance counter continue to operate on whatever directory was chosen. No other layer changes.

**`--output` in `_run_cli()`:** The CLI branch also uses output paths if writing files (e.g., `--json` combined with `--output`). The `--output` override must be available to both the full pipeline path and `_run_cli()`. Resolve `logs_dir` once at the top of `main()` before the `cli_mode` branch check, then pass it down, or resolve it again inside `_run_cli()` using the same logic. The simpler approach: keep `_run_cli()` stdout-only (no file writing) and require `--output` to only apply to the full pipeline. The `--json` flag in `_run_cli()` prints to stdout; only the full-pipeline `--json` writes a file.

#### 3c. `--app <name>` flag (CLI-V3-01)

**Where to call:** `detect_apps()` in `collectors/windows/apps.py` already accepts `report` and populates `report.apps`. The `--app` filter calls `detect_apps()` but filters `APP_SPECS` to the one named entry.

Do not modify `detect_apps()` to accept a filter parameter — that would change an established, tested interface. Instead, in `_run_cli()`, import `APP_SPECS` and `_detect_one_app` directly and invoke just the matching spec:

```python
if args.app:
    from collectors.windows.apps import APP_SPECS, _detect_one_app
    spec = next((s for s in APP_SPECS if s["name"].lower() == args.app.lower()), None)
    if spec is None:
        print(f"Unknown app: {args.app}")
        sys.exit(1)
    report = AuditReport(hostname=hostname, parsed_hostname=parse_hostname(hostname),
                         timestamp=datetime.datetime.now().isoformat())
    _detect_one_app(spec, report)
    # report.apps now has exactly one AppStatus
```

**No hardware collection needed** for `--app` alone. `collect_hardware()` is skipped entirely — the detection functions in `apps.py` only use the `report.apps` list and `report.collection_errors`, neither of which requires hardware fields to be populated first. This is consistent with the existing `--serial` optimization (D-09: "hardware collection only — avoid full collect_all").

**`--app + --json` composition:** After `_detect_one_app(spec, report)`, serialize `report.apps[0]` to JSON and print to stdout:

```python
if args.json:
    import json
    import dataclasses
    print(json.dumps(dataclasses.asdict(report.apps[0]), indent=2, default=str))
```

This prints the single `AppStatus` dict. It does not write a file — stdout only, because `--app` is a targeted query mode, not a full audit.

#### Extended `_run_cli()` logic

The existing `_run_cli()` structure (collection scope determination → output loop) extends cleanly:

```
_run_cli() decision matrix (extended):

Flag combination             Collection needed       Output
-----------------------------------------------------------------
--name only                  none                    hostname to stdout
--serial only                hardware only           serial to stdout
--warnings only              full collect_all        warnings to stdout
--app <name>                 app detection only      app status to stdout (or JSON)
--app <name> --json          app detection only      AppStatus JSON to stdout
--json (no --app)            full collect_all        (handled in main(), not _run_cli)
--output <path>              (not in _run_cli scope)
```

`--json` without `--app` is not a CLI-exit mode — it runs the full pipeline and writes both HTML and JSON files, so it falls through to `main()`, not `_run_cli()`. Only `--app` (with or without `--json`) is handled in `_run_cli()`.

**argparse additions in `main()`:**

```python
parser.add_argument("--json", action="store_true", help="Write JSON audit output in addition to HTML")
parser.add_argument("--output", metavar="PATH", help="Override output directory (default: USB logs/)")
parser.add_argument("--app", metavar="NAME", help="Check a single app and exit")
```

`cli_mode` detection extends to include `args.app` (but not `args.json` alone, and not `args.output` alone):

```python
cli_mode = args.name or args.serial or args.warnings or args.app
```

---

## New vs Modified Files Summary

### New Files

| File | Purpose |
|------|---------|
| `collectors/windows/health.py` | `collect_health(report)` — uptime via psutil, pending Windows updates via WUA COM |
| `collectors/windows/vendor_updates.py` | `collect_vendor_updates(report)` — Dell Command Update scan, Lenovo detection |
| `writers/json_writer.py` | `report_to_json(report) -> str` — AuditReport to JSON via dataclasses.asdict() |

### Modified Files

| File | Change |
|------|--------|
| `models.py` | Add `uptime_seconds: float | None`, `pending_updates: int | None`, `dell_pending: int | None`, `lenovo_pending: int | None` to `AuditReport` |
| `collectors/__init__.py` | Import and call `collect_health` and `collect_vendor_updates` in the Windows branch |
| `health_checks.py` | Add `UPTIME_STALE_DAYS` constant; add `_check_uptime()` private function; extend `evaluate_warnings()` to include uptime check; update return contract (was 3 warnings, becomes 4) |
| `renderer/__init__.py` | Add `uptime_display`, `pending_updates`, `dell_pending`, `lenovo_pending` to `_build_context()` |
| `renderer/templates/character_sheet.html` | Add stat block rows for uptime, pending updates, Dell/Lenovo vendor counts |
| `writers/__init__.py` | Re-export `report_to_json` from `writers.json_writer` |
| `main.py` | Add `--json`, `--output`, `--app` argparse flags; extend `_run_cli()` for `--app` + `--app --json`; add full-pipeline JSON write path; integrate `--output` path override |

### Unchanged Files

| File | Reason |
|------|--------|
| `collectors/windows/hardware.py` | No new hardware fields; uptime uses psutil not WMI |
| `collectors/windows/apps.py` | No new apps in scope for v3.0 |
| `collectors/mac/hardware.py` | Health collection is Windows-only for v3.0 |
| `collectors/mac/apps.py` | Vendor updates are Windows-only |
| `parsers/name_parser.py` | No hostname parsing changes |

---

## Guard Pattern Recommendation

Use `_WIN32COM_AVAILABLE` (not `_WUA_AVAILABLE`) in `health.py`:

```python
try:
    import win32com.client as _win32com
    _WIN32COM_AVAILABLE = True
except ImportError:
    _win32com = None
    _WIN32COM_AVAILABLE = False
```

**Rationale:**
- `_wmi_module` / `_WMI_AVAILABLE` is already the pattern for the `wmi` library (a separate high-level wrapper)
- `win32com.client` is a lower-level COM dispatch layer from `pywin32`, distinct from the `wmi` package
- Naming the guard after the import target (`win32com`) makes it clear what is being guarded
- The same guard can be reused in `vendor_updates.py` if any future vendor tool uses COM automation
- Tests mock `_WIN32COM_AVAILABLE = False` to disable COM calls in CI, identical to how `_WMI_AVAILABLE` is mocked today

`vendor_updates.py` uses `subprocess` only (no COM), so it requires no module-level guard — just `Path.exists()` to detect the CLI binary before invoking it.

---

## Data Flow After v3.0 Changes

```
main()
  socket.gethostname() + parse_hostname()
  AuditReport(...)
  collect_all(report)
    collect_hardware(report)                       [hardware.py — unchanged]
    collect_profiles(report)                       [hardware.py — unchanged]
    collect_apps(report)                           [apps.py — unchanged]
    collect_health(report)           [NEW health.py — uptime + pending_updates]
    collect_vendor_updates(report)   [NEW vendor_updates.py — dell_pending + lenovo_pending]
  report.warnings = evaluate_warnings(report)    [health_checks.py — +1 UPTIME_STALE check]
  html = render_html(report)                     [renderer — +4 new context fields]
  output_path = resolve_output_path(args)        [modified — --output override]
  output_path.write_text(html)
  if args.json:
      json_path = output_path.with_suffix('.json')
      json_path.write_text(report_to_json(report))   [NEW json_writer]
  print("[SUMMARY] ...")
```

For `--app <name>` (CLI mode, no full pipeline):
```
_run_cli(args)
  detect one app via _detect_one_app(spec, report)   [apps.py — no change to function]
  if args.json:
      print(json.dumps(dataclasses.asdict(report.apps[0])))   [stdout only, no file]
  sys.exit(0)
```

---

## Build Order Table

Dependencies are noted. Each phase can be individually tested and shipped. Later phases cannot start until their dependencies are complete.

| Phase | Name | Files Changed | Depends On | Why This Order |
|-------|------|---------------|-----------|----------------|
| 1 | Models — health + vendor fields | `models.py` | — | All other phases read new fields; adding `None`-defaulted fields is backward-compatible |
| 2 | System health collector | `collectors/windows/health.py` (NEW), `collectors/__init__.py` | Phase 1 (fields must exist) | Uptime and pending updates; self-contained; no HTML yet |
| 3 | UPTIME_STALE warning | `health_checks.py` | Phase 1 (uptime_seconds field), Phase 2 (collector populates it) | Warning logic requires the field to exist AND be populated |
| 4 | Vendor update detection | `collectors/windows/vendor_updates.py` (NEW), `collectors/__init__.py` | Phase 1 (dell_pending + lenovo_pending fields) | Dell subprocess; independent of health; can be parallelized with Phase 2/3 if desired |
| 5 | HTML stat block additions | `renderer/__init__.py`, `renderer/templates/character_sheet.html` | Phases 1–4 (all new fields + warnings must be defined before template uses them) | Render all new data; one template pass covers health + vendor + uptime warning display |
| 6 | JSON writer | `writers/json_writer.py` (NEW), `writers/__init__.py` | Phase 1 (AuditReport fields must be final) | Serialization; pure function; no external dependencies |
| 7 | Extended CLI flags | `main.py` | Phase 6 (json_writer must exist for --json), Phase 1 (fields must exist for --app JSON output) | Wires all new capabilities into argparse; final integration layer |

**Strict dependencies:**
- Phase 1 must be first — it defines the fields every other phase reads or writes.
- Phase 3 (UPTIME_STALE warning) must follow Phase 2 (health collector) — the warning check reads `uptime_seconds`, which is only populated after collection.
- Phase 5 (HTML) should follow Phases 1-4 — rendering uninitialized fields produces `None` correctly but the template rows are pointless without data.
- Phase 6 (JSON writer) must follow Phase 1 — `AuditReport` shape must be final before writing a serialization layer.
- Phase 7 (CLI) is last — it integrates everything.

**Can be parallelized:**
- Phases 2 and 4 have no dependency on each other and can be built concurrently.
- Phase 6 only depends on Phase 1 and can be built concurrently with Phases 2-5.

---

## `evaluate_warnings()` Return Contract Change

The current contract (enforced by `test_evaluate_warnings_always_returns_three`) is "always returns exactly 3 Warning objects." After Phase 3, it returns exactly 4.

The test `test_evaluate_warnings_always_returns_three` must be updated to assert `len(warnings) == 4` and add `warnings[3].code == 'UPTIME_STALE'`. The positional index assertions (`warnings[0]`, `warnings[1]`, `warnings[2]`) remain valid — the new check appends at index 3.

---

## Error Handling for New Features

| Scenario | Behavior |
|----------|----------|
| `win32com.client` not installed (CI, Mac) | `_WIN32COM_AVAILABLE = False`; `_collect_pending_updates` returns immediately; `pending_updates` stays `None` |
| WUA COM server unavailable at runtime | `try/except Exception` in `_collect_pending_updates`; appends to `collection_errors`; `pending_updates` stays `None` |
| `dcu-cli.exe` not found | `_collect_dell_updates` returns immediately; `dell_pending` stays `None` (not a Dell machine) |
| `dcu-cli.exe` timeout after 120s | `subprocess.TimeoutExpired` caught; appends to `collection_errors`; `dell_pending` stays `None` |
| `dcu-cli.exe` stdout format not parseable | Regex finds no match; `dell_pending = None` (unknown count); no error logged — this is expected for some DCU versions |
| Lenovo exe not found | Returns immediately; `lenovo_pending` stays `None` (not a Lenovo machine) |
| `psutil.boot_time()` raises (rare edge case) | `try/except` in `_collect_uptime`; appends to `collection_errors`; `uptime_seconds` stays `None` |
| `--app <name>` not in APP_SPECS | `sys.exit(1)` with message; clean error, no crash |
| `dataclasses.asdict()` on AuditReport fails | Should not occur; all fields are dataclasses, primitives, or lists thereof; `default=str` fallback covers any edge cases |
| `--output <path>` points to read-only location | `PermissionError` caught by existing write error handler in `main.py` (already handles this for the default path) |

---

## Anti-Patterns to Avoid in v3.0

### Do not add `pywin32` to the `wmi` guard

The `wmi` library is a separate package from `pywin32`. They have separate import paths (`wmi` vs `win32com.client`). Use a separate guard variable (`_WIN32COM_AVAILABLE`) — do not reuse `_WMI_AVAILABLE` to gate `win32com` usage. They can fail independently.

### Do not write vendor scan reports to host PC

Dell Command Update's `-report` option writes XML to a specified path. Do not use `%TEMP%` or any path under `C:\` — that violates the "no writes to host PC" constraint. Either write to USB (under `Path(sys.executable).parent`) or avoid the `-report` flag entirely and parse stdout.

### Do not call `detect_apps()` for `--app` single-app mode

`detect_apps()` iterates all of `APP_SPECS`. For `--app <name>`, call `_detect_one_app(spec, report)` directly after finding the matching spec. Calling `detect_apps()` and filtering the result wastes time and produces extra entries in `report.apps`.

### Do not put JSON serialization in `models.py`

`models.py` is the data contract layer. Serialization concerns (JSON format, field ordering, `default=str` fallback) belong in a writer. Adding a `to_json()` method to `AuditReport` would couple the data model to a serialization format and make `models.py` testable only with JSON output assertions.

### Do not make `collect_health` raise if WUA is slow

WUA `IUpdateSearcher.Search()` can block for 10-30 seconds on machines with large update queues. The existing `timeout` on subprocess calls does not apply to COM calls. Wrap the COM call in a thread with a timeout, or accept that the tool may be slower on machines with many pending updates. Do not raise — append to `collection_errors` and leave `pending_updates = None`. Blocking forever is worse than missing a count.

---

## Sources

- v2.0 shipped source code (direct inspection): `main.py`, `models.py`, `health_checks.py`, `collectors/__init__.py`, `collectors/windows/hardware.py`, `collectors/windows/apps.py`, `renderer/__init__.py`, `writers/__init__.py`
- WUA IUpdateSearcher API: https://learn.microsoft.com/en-us/windows/win32/wua_sdk/iupdatesearcher-methods
- WUA searching for updates: https://learn.microsoft.com/en-us/windows/win32/wua_sdk/searching--downloading--and-installing-updates
- Dell Command Update CLI Reference: https://www.dell.com/support/manuals/en-us/command-update/dcu_rg/dell-command-update-cli-commands
- Dell Command Update exit codes: https://www.dell.com/support/manuals/en-ca/command-update/dcu_rg/command-line-interface-error-codes
- psutil boot_time documentation: https://psutil.readthedocs.io/
- Python dataclasses.asdict(): https://docs.python.org/3/library/dataclasses.html#dataclasses.asdict

---

*Architecture research updated for: StatusReport v3.0 milestone*
*Researched: 2026-05-14*
