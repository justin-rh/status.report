# Architecture Research

**Domain:** Windows IT audit executable — self-contained PyInstaller .exe, USB-deployed, read-only
**Researched:** 2026-05-04
**Confidence:** HIGH

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Entry Point (main.py)                         │
│  Orchestrates run: collect → normalize → render → write                  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
             ┌─────────────────▼──────────────────┐
             │           Collector Layer            │
             │  (platform-abstracted via ABC)       │
             │                                      │
             │  ┌───────────┐  ┌──────────────┐    │
             │  │ SysInfo   │  │  AppDetector │    │
             │  │ Collector │  │  Collector   │    │
             │  └─────┬─────┘  └──────┬───────┘    │
             │        │               │             │
             │  ┌─────▼──────────────▼───────────┐ │
             │  │         NameParser              │ │
             │  │   (hostname → structured dict)  │ │
             │  └────────────────────────────────┘ │
             └──────────────┬─────────────────────┘
                            │ AuditReport dataclass
             ┌──────────────▼─────────────────────┐
             │           Render Layer               │
             │                                      │
             │  ┌──────────────────────────────┐   │
             │  │  HTMLRenderer (Jinja2)        │   │
             │  │  template embedded in package │   │
             │  └──────────────────────────────┘   │
             └──────────────┬─────────────────────┘
                            │ rendered strings
             ┌──────────────▼─────────────────────┐
             │           Output Layer               │
             │                                      │
             │  ┌──────────────┐  ┌─────────────┐  │
             │  │  HTMLWriter  │  │  JSONLogger │  │
             │  │  (to USB)    │  │  (to USB)   │  │
             │  └──────────────┘  └─────────────┘  │
             └────────────────────────────────────-─┘
```

---

## Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `main.py` | Entry point; calls each layer in order; catches top-level exceptions; sets exit code | All layers |
| `collectors/base.py` | Abstract base class `BaseCollector` with `collect() -> dict` contract | Nothing — defines interface only |
| `collectors/windows/sysinfo.py` | Reads hostname, OS version, CPU, RAM, disk, logged-in user, local profiles via WMI + winreg + psutil | `base.py` |
| `collectors/windows/appdetector.py` | Detects presence and version of target apps via registry HKLM\...\Uninstall and known filesystem paths | `base.py` |
| `parsers/name_parser.py` | Pure function: hostname string → `ParsedHostname` dataclass (city, device type, dept, company code, station) | Nothing — pure function |
| `models.py` | `AuditReport` dataclass — the single normalized data container passed between layers | All layers read/write |
| `renderer/html_renderer.py` | Loads Jinja2 template (embedded via `importlib.resources`), renders to HTML string | `models.py`, template file |
| `renderer/templates/character_sheet.html` | D&D-styled Jinja2 template — no logic beyond conditionals and loops | `html_renderer.py` |
| `writers/html_writer.py` | Writes rendered HTML to `<exe_dir>/status_report_<hostname>_<timestamp>.html` | `renderer/` |
| `writers/json_logger.py` | Serializes `AuditReport` to JSON, writes to `<exe_dir>/log_<hostname>_<timestamp>.json` | `models.py` |
| `utils/path_helper.py` | Resolves output directory = directory of running .exe (handles PyInstaller `sys.frozen` + `sys._MEIPASS`) | `writers/` |
| `utils/error_handler.py` | `CollectionResult` wrapper — holds `value` or `error` string; never raises; used by all collectors | `collectors/` |

---

## Recommended Project Structure

```
status_report/
├── main.py                         # Orchestrator — collect, render, write
├── models.py                       # AuditReport dataclass (the data contract)
│
├── collectors/
│   ├── base.py                     # Abstract BaseCollector (ABC)
│   ├── windows/
│   │   ├── __init__.py
│   │   ├── sysinfo.py              # WMI + psutil + winreg system facts
│   │   └── appdetector.py          # Registry + filesystem app checks
│   └── mac/                        # (stub — future milestone)
│       ├── __init__.py
│       └── sysinfo.py              # subprocess + plistlib equivalents
│
├── parsers/
│   └── name_parser.py              # Pure function: hostname → ParsedHostname
│
├── renderer/
│   ├── html_renderer.py            # Jinja2 rendering logic
│   └── templates/
│       └── character_sheet.html    # D&D HTML template
│
├── writers/
│   ├── html_writer.py              # Write HTML to USB output dir
│   └── json_logger.py              # Write JSON log to USB output dir
│
└── utils/
    ├── path_helper.py              # PyInstaller-aware exe/output dir resolution
    └── error_handler.py            # CollectionResult wrapper for safe returns
```

### Structure Rationale

- **`collectors/windows/` vs `collectors/mac/`:** Platform isolation lives entirely in the `collectors/` subdirectories. `main.py` selects the right collector set using `platform.system()` at startup — everything above the collector layer is platform-agnostic.
- **`models.py` as single source of truth:** All layers communicate through `AuditReport`. Collectors produce it; renderers consume it; writers serialize it. No layer passes raw WMI objects or registry handles to another layer.
- **`renderer/templates/`:** Template is a plain file in the package, bundled by PyInstaller via `--add-data` and loaded at runtime with `importlib.resources`. This is preferable to embedding the template as a Python string because it allows the template to be edited without touching Python code.
- **`utils/error_handler.py`:** Collectors never raise exceptions to `main.py`. They return `CollectionResult(value=..., error=None)` on success or `CollectionResult(value=None, error="description")` on failure. The renderer then shows "unavailable" in the HTML for any errored field — the audit completes even if half the checks fail.

---

## Architectural Patterns

### Pattern 1: Platform-Dispatch Collector Selection

**What:** `main.py` selects the correct collector module at startup based on `platform.system()`. The rest of the program only sees `BaseCollector`.

**When to use:** Any time OS-specific APIs must be isolated from cross-platform logic. This is the correct extension point for the Mac milestone.

**Trade-offs:** Adds one indirection level but keeps all Windows-isms out of the orchestrator and renderer. Stub mac/ directory costs nothing and documents intent clearly.

```python
# main.py
import platform
from collectors.base import BaseCollector

def get_collectors() -> list[BaseCollector]:
    os_name = platform.system()
    if os_name == "Windows":
        from collectors.windows.sysinfo import WindowsSysInfoCollector
        from collectors.windows.appdetector import WindowsAppDetector
        return [WindowsSysInfoCollector(), WindowsAppDetector()]
    elif os_name == "Darwin":
        from collectors.mac.sysinfo import MacSysInfoCollector
        return [MacSysInfoCollector()]
    else:
        raise RuntimeError(f"Unsupported platform: {os_name}")
```

### Pattern 2: CollectionResult Error Envelope

**What:** Every collector method returns a `CollectionResult` (a dataclass with `value` and `error` fields) rather than raising exceptions or returning `None`. Callers check `result.error` to decide whether to display a fallback.

**When to use:** Any read that can fail silently: missing registry key, WMI service unavailable, permission denied.

**Trade-offs:** Slightly more verbose call sites, but the audit tool never crashes and always produces output — which is the primary constraint.

```python
# utils/error_handler.py
from dataclasses import dataclass
from typing import Any

@dataclass
class CollectionResult:
    value: Any
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

# Usage in sysinfo.py
def get_os_version() -> CollectionResult:
    try:
        import platform
        return CollectionResult(value=platform.version())
    except Exception as e:
        return CollectionResult(value=None, error=str(e))
```

### Pattern 3: AuditReport as the Single Data Contract

**What:** A frozen `@dataclass` (or nested dataclasses) that represents everything collected. Constructed in `main.py` from collector outputs and passed to both the renderer and JSON logger. No raw dicts cross layer boundaries.

**When to use:** Always — the `AuditReport` is the contract between collection and output.

**Trade-offs:** Requires upfront field design, but makes the renderer completely independent of collection implementation details.

```python
# models.py
from dataclasses import dataclass, field

@dataclass
class ParsedHostname:
    city: str | None
    device_type: str | None       # "Warehouse Workstation", "User Laptop", etc.
    department: str | None
    company_code: str | None
    station: str | None
    raw: str
    parse_error: str | None = None

@dataclass
class AppStatus:
    name: str
    detected: bool
    version: str | None
    detection_method: str         # "registry" | "filesystem" | "wmi"
    error: str | None = None

@dataclass
class AuditReport:
    hostname: str
    parsed_name: ParsedHostname
    os_version: str | None
    os_build: str | None
    cpu_model: str | None
    ram_gb: float | None
    disk_total_gb: float | None
    disk_free_gb: float | None
    current_user: str | None
    local_profiles: list[str] = field(default_factory=list)
    apps: list[AppStatus] = field(default_factory=list)
    collection_errors: list[str] = field(default_factory=list)
    timestamp: str = ""
```

### Pattern 4: Jinja2 Template via importlib.resources

**What:** The HTML template lives in `renderer/templates/character_sheet.html` as a regular file. PyInstaller includes it via `--add-data`. At runtime, the renderer loads it using `importlib.resources` (Python 3.9+) which correctly resolves the path whether running from source or from the extracted PyInstaller bundle.

**When to use:** Any non-Python asset (templates, images, bundled data) that must survive PyInstaller one-file packaging.

**Trade-offs:** Requires a one-line spec file addition (`--add-data renderer/templates:renderer/templates`) but avoids the template-not-found bug that plagues naive `open()` calls inside packaged executables. Do not use `sys._MEIPASS` directly — `importlib.resources` abstracts this correctly.

```python
# renderer/html_renderer.py
import importlib.resources
from jinja2 import Environment, BaseLoader

def render(report: AuditReport) -> str:
    ref = importlib.resources.files("renderer.templates").joinpath("character_sheet.html")
    template_src = ref.read_text(encoding="utf-8")
    env = Environment(loader=BaseLoader())
    tpl = env.from_string(template_src)
    return tpl.render(report=report)
```

---

## Data Flow

```
USB drive: user double-clicks status_report.exe
    |
    v
main.py starts
    |
    +--> platform.system() == "Windows"
    |         |
    |         v
    |    WindowsSysInfoCollector.collect()
    |      -> WMI: OS, CPU, RAM, disk
    |      -> winreg: current user, profiles
    |      -> psutil: disk free space (fallback)
    |      -> Returns dict of CollectionResult values
    |
    +--> WindowsAppDetector.collect()
    |      -> winreg HKLM\...\Uninstall: enumerate installed apps
    |      -> filesystem: check known install paths as fallback
    |      -> Returns list[AppStatus]
    |
    +--> NameParser.parse(hostname)
    |      -> Regex splits hostname into segments
    |      -> Returns ParsedHostname (error field set if no match)
    |
    +--> Assemble AuditReport dataclass
    |
    +--> HTMLRenderer.render(report)
    |      -> Load character_sheet.html via importlib.resources
    |      -> Jinja2 render with report as context
    |      -> Returns HTML string
    |
    +--> JSONLogger.serialize(report)
    |      -> dataclasses.asdict(report)
    |      -> Add timestamp
    |      -> Returns JSON string
    |
    +--> PathHelper.get_output_dir()
    |      -> sys.frozen ? Path(sys.executable).parent : Path(__file__).parent
    |
    +--> HTMLWriter.write(html_str, output_dir, hostname, timestamp)
    +--> JSONWriter.write(json_str, output_dir, hostname, timestamp)
    |
    v
Output on USB:
  status_report_PHX-SHP-001_20260504T143012.html
  log_PHX-SHP-001_20260504T143012.json
```

---

## Suggested Build Order (Fastest Path to Working Demo)

Build in this order — each step produces something runnable or testable:

1. **`models.py`** — Define `AuditReport`, `ParsedHostname`, `AppStatus`, `CollectionResult`. No dependencies. Everything else imports from here. Takes 30 minutes, unlocks all other work.

2. **`parsers/name_parser.py`** — Pure Python regex, no Windows APIs, fully unit-testable on any machine. Gets the hostname decode working immediately and proves the naming convention logic is right before touching WMI.

3. **`collectors/windows/sysinfo.py`** — Minimal version: `platform.node()`, `platform.version()`, `platform.processor()`. No WMI yet. Produces a partial but real `AuditReport`. Ship a console print at this point to confirm end-to-end flow.

4. **`renderer/` + Jinja2 template** — Build the HTML template with hardcoded/mock data first. Get the D&D character sheet looking right before any real data flows through it. This is the highest-visibility deliverable — it's the demo.

5. **`writers/`** — `HTMLWriter` and `JSONLogger` are trivial once the rendered strings exist. Add `PathHelper` to make USB output work.

6. **`collectors/windows/appdetector.py`** — Registry app detection is the most Windows-specific and error-prone piece. Build last, after the scaffold is proven, so failures are isolated.

7. **WMI deep dive** in `sysinfo.py` — Upgrade from `platform` module basics to full WMI queries (RAM, disk, profiles). Can be deferred to a second pass without blocking the demo.

8. **PyInstaller packaging** — Wire up `.spec` file, test `--onefile` build, verify `importlib.resources` works in the frozen binary.

---

## Error Handling Strategy

This tool is read-only and must complete under all conditions. The strategy is: **never raise, always annotate**.

| Scenario | Response | User Sees |
|----------|----------|-----------|
| Registry key missing | `CollectionResult(value=None, error="Key not found: ...")` | "Not detected" badge on app |
| WMI service unavailable | Catch `wmi.x_wmi`, return error envelope | "Unavailable" in stats block |
| Hostname does not match any convention | `ParsedHostname(parse_error="No match")` | "Unknown Adventurer" class label + raw hostname shown |
| Output directory not writable | Top-level try/except in `main.py`, print error to console, exit code 1 | Console message; no files written |
| App install detected but version unreadable | `AppStatus(detected=True, version=None)` | App shown as present, version as "unknown" |
| Running without elevation | Note in `collection_errors` list | Warning section in HTML: "Some checks require elevation" |

Rule: collectors catch all exceptions at method boundaries. `main.py` catches only fatal I/O errors (cannot write output). Everything else degrades gracefully.

---

## Mac Extensibility Pattern

The abstraction is `BaseCollector`. Adding Mac support in a future milestone requires:

1. Create `collectors/mac/sysinfo.py` implementing `BaseCollector.collect()`. Use `subprocess` with `system_profiler`, `sysctl`, and `sw_vers` instead of WMI/winreg.
2. Create `collectors/mac/appdetector.py`. Use filesystem paths (`/Applications/`, `plistlib` for `Info.plist` version reads) instead of registry.
3. Update `main.py` dispatch block to include `elif os_name == "Darwin"`.
4. `models.py`, `parsers/name_parser.py`, `renderer/`, and `writers/` require zero changes.

Nothing above the collector layer is Windows-specific. The `ParsedHostname` parser is pure string logic — it works on Mac because hostnames do not change by platform.

---

## Anti-Patterns

### Anti-Pattern 1: WMI Everywhere

**What people do:** Call `wmi.WMI()` directly from `main.py` or the renderer to fetch individual fields on demand.

**Why it's wrong:** WMI service can be unavailable, slow, or require elevation. Calling it from render code makes error handling impossible and produces partial output or crashes at render time.

**Do this instead:** All WMI calls live in `collectors/windows/sysinfo.py`. They return `CollectionResult` objects. The renderer only sees `AuditReport` with already-resolved values (or `None` with an error note).

### Anti-Pattern 2: Hardcoded Output Path

**What people do:** `open("C:/output/report.html", "w")` or `open("./report.html", "w")`.

**Why it's wrong:** PyInstaller one-file executables extract to a temp directory (`sys._MEIPASS`). The working directory at launch is wherever the user double-clicked from — which may not be the USB drive.

**Do this instead:** `PathHelper.get_output_dir()` returns `Path(sys.executable).parent` when `sys.frozen` is set, which resolves to the USB drive directory where the .exe lives.

### Anti-Pattern 3: Template as Python String

**What people do:** Store the entire HTML template as a multi-line Python string in `html_renderer.py`.

**Why it's wrong:** The template is hundreds of lines of HTML/CSS. Mixing it with Python makes both harder to edit. D&D styling requires iteration — designers cannot touch it without running Python.

**Do this instead:** External template file loaded via `importlib.resources`. PyInstaller bundles it cleanly; the file is editable independently of Python code.

### Anti-Pattern 4: Raising Exceptions Across Layer Boundaries

**What people do:** `sysinfo.py` raises `PermissionError` when a registry key is inaccessible; `main.py` crashes with an unhandled exception and produces no output.

**Why it's wrong:** The entire value of this tool is that it always produces output. A partial audit is far more useful than no audit.

**Do this instead:** Catch at every collection method, return `CollectionResult` with an `error` string. Aggregate all errors in `AuditReport.collection_errors`. Display them as a "warnings" section in the HTML.

---

## Integration Points

### External Services

None. The tool is intentionally offline and leaves no artifacts on the host PC.

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `collectors/` → `main.py` | `dict` of `CollectionResult` values | Collectors never import from `renderer/` or `writers/` |
| `parsers/` → `main.py` | `ParsedHostname` dataclass | Pure function — no side effects, fully unit-testable |
| `main.py` → `renderer/` | `AuditReport` dataclass | Renderer has no knowledge of how data was collected |
| `renderer/` → `writers/` | `str` (rendered HTML) | Writer only does file I/O — no rendering logic |
| All layers → `utils/` | `CollectionResult`, `PathHelper` | Utils have no upward dependencies |

---

## Sources

- Python `winreg` documentation: https://docs.python.org/3/library/winreg.html
- `psutil` cross-platform system info: https://psutil.readthedocs.io/
- `platform` module docs: https://docs.python.org/3/library/platform.html
- `importlib.resources` (Python 3.9+): https://docs.python.org/3/library/importlib.resources.html
- PyInstaller onefile + `--add-data`: https://pyinstaller.org/en/stable/CHANGES.html
- `jinja2-embedded` package for PyInstaller bundling: https://pypi.org/project/jinja2-embedded/
- Python ABC pattern for platform abstraction: https://docs.python.org/3/library/abc.html
- Windows installed software via registry (`HKLM\...\Uninstall`): https://medium.com/@tubelwj/winreg-python-library-to-retrieve-installed-software-information-on-windows-machines-f1f14b39650f
- Plugin architecture patterns: https://mathieularose.com/plugin-architecture-in-python

---

*Architecture research for: Windows IT audit executable (StatusReport)*
*Researched: 2026-05-04*
