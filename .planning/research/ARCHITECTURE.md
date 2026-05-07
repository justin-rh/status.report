# Architecture Research — v2.0 Update

**Domain:** Windows/Mac IT audit executable — self-contained PyInstaller .exe, USB-deployed, read-only
**Researched:** 2026-05-07
**Confidence:** HIGH (based on direct source inspection of shipped v1.0 codebase)

---

## Current Architecture (v1.0 Confirmed)

This section documents the actual shipped state, not the planned state. Several v1.0 decisions
differ from the original research doc and must be understood before extending.

### Confirmed File Structure

```
status.report/
├── main.py                             # Orchestrator — collect_all → render_html → write
├── models.py                           # AuditReport, ParsedHostname, AppStatus, CollectionResult
│
├── collectors/
│   ├── __init__.py                     # collect_all() — platform dispatch (Windows only for now)
│   ├── base.py                         # Stub (empty — no ABC defined yet)
│   └── windows/
│       ├── __init__.py
│       ├── hardware.py                 # collect_hardware(), collect_profiles()
│       └── apps.py                     # detect_apps(), collect_apps(), APP_SPECS table
│
├── parsers/
│   └── name_parser.py                  # parse_hostname(str) → ParsedHostname
│
├── renderer/
│   ├── __init__.py                     # render_html(report) → str, render_report(report, path) → Path
│   └── templates/
│       └── character_sheet.html        # Jinja2 D&D character sheet
│
└── writers/
    └── __init__.py                     # write_html(html, output_path) → Path
```

**No mac/ directory exists yet.** The v1.0 architecture doc called for stubs; none were created.

### Actual Data Flow (v1.0)

```
main.py
  └─ socket.gethostname() + parse_hostname()
  └─ AuditReport(...) constructed
  └─ collect_all(report)                     ← mutates report in place
       ├─ collect_hardware(report)           [hardware.py]
       ├─ collect_profiles(report)           [hardware.py]
       └─ collect_apps(report)              [apps.py]
  └─ render_html(report) → html str         [renderer/__init__.py]
       └─ _build_context(report)            derives display values, flags
       └─ Jinja2 template render
  └─ output_path = logs_dir / f"status_{hostname}_{date_str}.html"
  └─ output_path.write_text(html)
  └─ os.startfile(output_path)              ← PROBLEM for NinjaOne (no display)
  └─ input("Press Enter...")                ← PROBLEM for NinjaOne (no TTY)
```

### Actual models.py (v1.0)

```python
@dataclass
class CollectionResult(Generic[T]):
    value: T | None
    error: str | None = None
    ok: bool (property)

@dataclass
class ParsedHostname:
    raw_hostname: str
    city: str | None
    device_type: str | None
    department: str | None
    company_code: str | None
    station: int | None

@dataclass
class AppStatus:
    name: str
    installed: bool
    version: str | None = None
    service_state: str | None = None
    detection_method: str = 'registry'
    error: str | None = None

@dataclass
class AuditReport:
    hostname: str
    parsed_hostname: ParsedHostname
    os_version: str | None = None
    os_build: str | None = None
    serial_number: str | None = None
    cpu_model: str | None = None
    ram_gb: float | None = None
    disk_total_gb: float | None = None
    disk_free_gb: float | None = None
    current_user: str | None = None
    local_profiles: list[str] = field(default_factory=list)
    apps: list[AppStatus] = field(default_factory=list)
    collection_errors: list[str] = field(default_factory=list)
    timestamp: str = ''
```

### Key v1.0 Patterns Already Established

- **Mutation pattern:** `collect_all(report)` mutates `AuditReport` in place. No return value from collectors.
- **Error pattern:** Collectors catch all exceptions, append to `report.collection_errors`, never raise.
- **APP_SPECS table:** `apps.py` uses a list-of-dicts config table to drive detection. New apps = add a dict entry.
- **Renderer context:** `_build_context(report)` in `renderer/__init__.py` is the single place where
  display values are derived (disk %, OS warning flag, rename warning flag). Template is logic-free.
- **Warnings already partly exist:** `os_warning` and `rename_warning` are computed in `_build_context()`
  and rendered as inline `<div class="rename-warning">` blocks after the quest status section. These are
  not structured data — they are booleans derived at render time, not fields on AuditReport.

---

## v2.0 Integration Architecture

### Feature 1: Company Portal Detection (Windows only)

**Where it lives:** `collectors/windows/apps.py` — add one entry to `APP_SPECS`.

Company Portal is an MSIX app (installed from the Microsoft Store / Intune). Detection follows the
same `msix_family_prefix` pattern already used for Claude. It also appears in the standard Uninstall
registry under some Intune enrollment paths, so providing both `msix_family_prefix` and
`display_name_keywords` gives maximum coverage.

**New dict in APP_SPECS:**
```python
{
    "name": "Company Portal",
    "display_name_keywords": ["Company Portal", "Microsoft Intune Company Portal"],
    "msix_family_prefix": "Microsoft.CompanyPortal_",
},
```

**Files modified:** `collectors/windows/apps.py` only.
**Files new:** None.
**models.py change:** None. `AppStatus` already has all required fields.

---

### Feature 2: Warnings System

#### Data model decision: new `warnings` field on `AuditReport`

The v1.0 approach puts warning flags (`os_warning`, `rename_warning`) in `_build_context()` as
booleans derived at render time. This works for simple boolean flags but does not scale to a
structured warnings section with multiple warning types, severity levels, and detail strings.

**Recommendation:** Add a `list[Warning]` field to `AuditReport`. Warnings are evaluated in a
dedicated `warnings.py` module after collection, before rendering. The renderer reads
`report.warnings` directly.

**Rationale:**
- Warnings depend on collected data (os_build, disk_free_gb) — the data is already on AuditReport
  after `collect_all()`. There is no reason to re-derive it in the renderer.
- A structured list lets the renderer iterate and display multiple warnings without adding more
  boolean flags to `_build_context()`.
- The existing `os_warning` and `rename_warning` booleans in `_build_context()` should be
  **migrated** to the new system and removed from the context dict. This is a clean break.
- `collection_errors` already exists for collector failures. `warnings` is conceptually separate —
  it represents health signals on successfully-collected data, not collection failures.

**New dataclass in `models.py`:**
```python
@dataclass
class Warning:
    code: str           # e.g. 'OS_VERSION', 'DISK_SPACE', 'RENAME_REQUIRED'
    severity: str       # 'critical' | 'warning' | 'info'
    message: str        # Human-readable string for HTML display
    detail: str | None = None  # Optional sub-detail (e.g. current build number)
```

**New field on `AuditReport`:**
```python
warnings: list[Warning] = field(default_factory=list)
```

#### Warning evaluation: new `warnings.py` module

Warnings are not collected — they are derived from already-collected data. They belong in a
dedicated module, not in a collector or in main.py.

**New file:** `warnings.py` (project root, alongside `models.py`)

```python
# warnings.py
from models import AuditReport, Warning

_MIN_DISK_FREE_GB = 20.0    # threshold: warn below 20 GB free
_WIN11_BUILD = 22000         # threshold: warn below build 22000

def evaluate_warnings(report: AuditReport) -> None:
    """Evaluate health warnings from collected data. Mutates report.warnings in place.
    Called by main.py after collect_all(), before render_html().
    Never raises.
    """
    _check_os_version(report)
    _check_disk_space(report)
    _check_rename_required(report)

def _check_os_version(report: AuditReport) -> None:
    try:
        build = int(report.os_build or '0')
    except ValueError:
        return
    if 0 < build < _WIN11_BUILD:
        report.warnings.append(Warning(
            code='OS_VERSION',
            severity='warning',
            message=f'Device is running {report.os_version} — upgrade to Windows 11 required',
            detail=f'Build {report.os_build}',
        ))

def _check_disk_space(report: AuditReport) -> None:
    if report.disk_free_gb is not None and report.disk_free_gb < _MIN_DISK_FREE_GB:
        report.warnings.append(Warning(
            code='DISK_SPACE',
            severity='critical' if report.disk_free_gb < 5.0 else 'warning',
            message=f'Low disk space: {report.disk_free_gb:.0f} GB free',
            detail=f'{report.disk_free_gb:.1f} GB of {report.disk_total_gb:.0f} GB available',
        ))

def _check_rename_required(report: AuditReport) -> None:
    if report.parsed_hostname.device_type == 'Unknown':
        report.warnings.append(Warning(
            code='RENAME_REQUIRED',
            severity='warning',
            message=f'Device needs to be renamed — hostname "{report.hostname}" does not match naming convention',
        ))
```

**main.py change:** Add one call between `collect_all()` and `render_html()`:
```python
from warnings_module import evaluate_warnings  # named warnings_module to avoid stdlib clash
evaluate_warnings(report)
```

**renderer/__init__.py change:** Remove the inline `os_warning` and `rename_warning` derivation
from `_build_context()`. Add `'warnings': report.warnings` to the context dict.

**Template change:** Replace the current ad-hoc `{% if os_warning %}` and `{% if rename_warning %}`
blocks with a single loop over `report.warnings`. See Template section below.

#### Warning threshold location

Thresholds (`_MIN_DISK_FREE_GB = 20.0`, `_WIN11_BUILD = 22000`) live as module-level constants
in `warnings.py`. Do not put them in `models.py` (data contract) or in the template (logic-free).

---

### Feature 3: Mac Collectors

#### Directory structure

Create `collectors/mac/` with `__init__.py`, `hardware.py`, and `apps.py`. The `collectors/__init__.py`
platform dispatch already imports inside `collect_all()` — add the Darwin branch there.

```
collectors/
├── __init__.py          MODIFIED — add Darwin branch
├── base.py              MODIFIED — define BaseCollector ABC (now needed)
├── windows/
│   ├── hardware.py      unchanged
│   └── apps.py          modified (Company Portal only)
└── mac/                 NEW
    ├── __init__.py
    ├── hardware.py       NEW — implement collect_hardware, collect_profiles
    └── apps.py           NEW — implement detect_apps, collect_apps
```

#### Mac hardware collector

Mac hardware uses `subprocess` + `platform` stdlib + `psutil`. No WMI, no winreg.

| Field | Mac API |
|-------|---------|
| `os_version` | `platform.mac_ver()[0]` → "15.4.1" → "macOS 15" |
| `os_build` | `subprocess(['sw_vers', '-buildVersion'])` → e.g. "24E263" |
| `cpu_model` | `subprocess(['sysctl', '-n', 'machdep.cpu.brand_string'])` |
| `ram_gb` | `psutil.virtual_memory().total` (already cross-platform) |
| `disk_total_gb` | `psutil.disk_usage('/')` (use `/` not `C:\`) |
| `disk_free_gb` | `psutil.disk_usage('/')` |
| `serial_number` | `subprocess(['system_profiler', 'SPHardwareDataType'])` — parse "Serial Number" line |
| `current_user` | `os.environ.get('USER')` (macOS sets USER, not USERNAME) |
| `local_profiles` | `os.listdir('/Users/')` filtered by `os.path.isdir` + skip system names |

The mutation-in-place pattern (`collect_hardware(report)`) and error-envelope pattern are identical
to the Windows implementation. Use the same function signatures so `collectors/__init__.py` can call
both platforms identically.

**`current_user` on Mac:** `os.environ.get('USER')` works. `USERNAME` is not set on macOS. The
existing `hardware.py` already does `os.environ.get("USERNAME") or os.environ.get("USER")` — the
Mac version should do `os.environ.get("USER")` directly to avoid confusion.

#### Mac app detector

Mac app detection uses filesystem paths, not a registry. The `AppStatus` dataclass is the same
model — only `detection_method` changes to `'filesystem'`.

| App | Detection Strategy |
|-----|-------------------|
| NinjaOne | `/Library/NinjaRMM/` or `/Applications/NinjaRMM Agent.app` |
| CrowdStrike | `/Applications/Falcon.app` or `/Library/CS/` agent path |
| MERP | Not applicable on Mac (Windows-only ERP) |
| Microsoft 365 | `/Applications/Microsoft Word.app` (suite presence via Word) |
| Zoom | `/Applications/Zoom.us.app` |
| Google Chrome | `/Applications/Google Chrome.app` |
| Claude | `/Applications/Claude.app` |
| Company Portal | `/Applications/Company Portal.app` |

Version reading: open `{app_path}/Contents/Info.plist` using `plistlib.load()` and read
`CFBundleShortVersionString`. Wrap in try/except — some apps omit it.

The `APP_SPECS` table pattern can be adapted for Mac: add an optional `mac_path` key alongside
the existing `filesystem_path` (Windows) key. A shared helper `_check_app_bundle(path)` returns
`(installed, version)`.

**MERP on Mac:** Append an `AppStatus(name='MERP', installed=False, error='Windows only')` so
the renderer always has a complete app list regardless of platform. This preserves the invariant
that every configured app produces exactly one AppStatus entry.

#### Platform dispatch in `collectors/__init__.py`

```python
def collect_all(report: AuditReport) -> None:
    import platform as _platform
    os_name = _platform.system()
    if os_name == 'Windows':
        from collectors.windows.hardware import collect_hardware, collect_profiles
        from collectors.windows.apps import collect_apps
    elif os_name == 'Darwin':
        from collectors.mac.hardware import collect_hardware, collect_profiles
        from collectors.mac.apps import collect_apps
    else:
        report.collection_errors.append(f'Unsupported platform: {os_name}')
        return
    collect_hardware(report)
    collect_profiles(report)
    collect_apps(report)
```

---

### Feature 4: NinjaOne Compatibility (SYSTEM account)

NinjaOne executes scripts as `NT AUTHORITY\SYSTEM`. This breaks three things in `main.py`:

| Problem | Root cause | Fix |
|---------|-----------|-----|
| `os.startfile()` crashes | SYSTEM has no desktop/shell session; shell is not initialized | Wrap in `if not _is_system_context()` |
| `input("Press Enter...")` hangs forever | No TTY attached; stdin is a pipe or NUL | Same guard |
| `os.environ.get("USERNAME")` returns `"SYSTEM"` | Correct but misleading in output | No change needed — "SYSTEM" is informative |
| `USERPROFILE` absent or points to `C:\Windows\system32\config\systemprofile` | SYSTEM profile is non-standard | No output path issue — output uses `Path(sys.executable).parent`, not USERPROFILE |
| `Path(sys.executable).parent` still resolves correctly | PyInstaller sets `sys.executable` regardless of session context | Confirmed safe — no change needed |

**Detection of SYSTEM context:**
```python
def _is_system_context() -> bool:
    """Return True when running as NT AUTHORITY\SYSTEM (NinjaOne/service context)."""
    import os
    username = os.environ.get('USERNAME', '').upper()
    return username == 'SYSTEM'
```

**main.py changes:**
```python
_system_mode = _is_system_context()

# ... after write succeeds:
print(f"Saved: {output_path}")
if not _system_mode:
    try:
        os.startfile(str(output_path))
    except OSError:
        pass
    input("\nPress Enter to close this window, then eject the USB drive.")
else:
    print("[NinjaOne] Audit complete. HTML saved to USB logs/.")
    # Exit cleanly — NinjaOne reads stdout and exit code
```

**Stdout summary for NinjaOne:** NinjaOne collects script stdout as the activity result. The
existing `print()` calls in main.py already serve this purpose. Add a final structured summary
line that NinjaOne can parse or display:

```
StatusReport -- Master Electronics IT Audit Tool
Collecting hardware info...
Detecting installed apps...
Rendering character sheet...
Saved: D:\status_report\logs\status_PHX-SHP-001_2026-05-07.html
[SUMMARY] host=PHX-SHP-001 os=Windows 11 apps_installed=6/8 warnings=1
[NinjaOne] Audit complete. HTML saved to USB logs/.
```

The `[SUMMARY]` line lets NinjaOne scripts parse key fields without reading the HTML file.
Emit it unconditionally (not only in system mode) — it is useful for any automated caller.

**No network drive concern:** The tool writes to `Path(sys.executable).parent` (the USB drive),
not to any network path. SYSTEM can write to removable media. The `logs_dir.mkdir(parents=True,
exist_ok=True)` call already handles missing directory. No change needed here.

**Display/WMI concern:** WMI is a COM service that runs independently of the user session. SYSTEM
has full WMI access — typically more than a standard user. No WMI changes required.

---

## Template Changes

### Current warning rendering (v1.0)

The template has two separate ad-hoc warning blocks after the quest status section:

```html
{% if os_warning %}
<div class="rename-warning"> ... </div>
{% endif %}

{% if rename_warning %}
<div class="rename-warning"> ... </div>
{% endif %}
```

### v2.0 approach: single warnings loop

Remove both ad-hoc blocks. Add a `{% if warnings %}` section that iterates `report.warnings`:

```html
{% if warnings %}
<div class="section-card">
  <div class="section-title">Warnings ({{ warnings|length }})</div>
  <div class="warnings-list">
    {% for w in warnings %}
    <div class="warning-item warning-{{ w.severity }}">
      &#9888; {{ w.message }}
      {% if w.detail %}<span class="warning-detail">{{ w.detail }}</span>{% endif %}
    </div>
    {% endfor %}
  </div>
</div>
{% endif %}
```

**Single template file, no partials.** The template is already 460 lines with inline CSS. Adding
a collapsible warnings section does not warrant splitting into partials — the `{% if warnings %}`
guard keeps it optional and adding Jinja2 `include` tags with PyInstaller `importlib.resources`
creates unnecessary bundling complexity.

**`_build_context()` changes:**
- Remove `os_warning` and `rename_warning` derivation (moved to `warnings.py`)
- Add `'warnings': report.warnings` to returned dict

---

## Component Responsibility Map — v2.0

| Component | v1.0 Status | v2.0 Change |
|-----------|-------------|-------------|
| `main.py` | SHIPPED | MODIFIED — add `evaluate_warnings()` call; add SYSTEM-mode guard around `os.startfile` and `input()`; add `[SUMMARY]` print |
| `models.py` | SHIPPED | MODIFIED — add `Warning` dataclass; add `warnings: list[Warning]` field to `AuditReport` |
| `warnings.py` | DOES NOT EXIST | NEW — evaluate OS version, disk space, rename warnings from collected data |
| `collectors/__init__.py` | SHIPPED | MODIFIED — add Darwin platform branch |
| `collectors/windows/apps.py` | SHIPPED | MODIFIED — add Company Portal to `APP_SPECS` table |
| `collectors/windows/hardware.py` | SHIPPED | UNCHANGED |
| `collectors/mac/__init__.py` | DOES NOT EXIST | NEW (empty) |
| `collectors/mac/hardware.py` | DOES NOT EXIST | NEW — subprocess/psutil Mac collectors |
| `collectors/mac/apps.py` | DOES NOT EXIST | NEW — filesystem + plistlib Mac app detection |
| `renderer/__init__.py` | SHIPPED | MODIFIED — remove `os_warning`/`rename_warning` from `_build_context()`; add `warnings` to context |
| `renderer/templates/character_sheet.html` | SHIPPED | MODIFIED — replace two ad-hoc warning divs with structured `{% if warnings %}` loop section |
| `writers/__init__.py` | SHIPPED | UNCHANGED |
| `parsers/name_parser.py` | SHIPPED | UNCHANGED |
| `collectors/base.py` | SHIPPED (empty) | OPTIONAL — define `BaseCollector` ABC if desired; not strictly needed given the direct import dispatch pattern |

---

## Suggested Phase Build Order (v2.0)

Each phase produces something independently testable. Dependencies are noted.

### Phase 6: Models and Warnings Module

**Why first:** Everything else in v2.0 depends on `Warning` existing on `AuditReport`. Doing this
first means later phases can immediately write `report.warnings.append(...)` without conflicts.

**Files:**
- `models.py` — add `Warning` dataclass + `warnings` field on `AuditReport`
- `warnings.py` — new module with `evaluate_warnings()`, three check functions, thresholds as constants

**Dependencies:** None (pure data model + pure function).

**Testable immediately:** Unit tests for each warning check function with mock `AuditReport` objects.
No Windows APIs required.

---

### Phase 7: HTML Warnings Section

**Why second:** The warnings data model exists (Phase 6). Rendering and template changes can be
validated with mock data before any new collector work. This is the highest-visibility deliverable
of v2.0 — the HTML output changes.

**Files:**
- `renderer/templates/character_sheet.html` — replace ad-hoc blocks with `{% if warnings %}` loop
- `renderer/__init__.py` — remove old flags from `_build_context()`, add `warnings` key

**Dependencies:** Phase 6 (Warning dataclass must exist).

**Testable immediately:** Existing renderer tests pass mock `AuditReport` with `warnings=[]`
(no regressions). New tests pass reports with one or more `Warning` objects.

---

### Phase 8: NinjaOne Compatibility

**Why third:** Independent of Mac and Company Portal. Only touches `main.py`. Can be shipped to
NinjaOne users before Mac work is complete. The `_is_system_context()` check is a two-line
function; no new modules.

**Files:**
- `main.py` — SYSTEM-mode detection, conditional `os.startfile`/`input()`, `[SUMMARY]` line,
  `evaluate_warnings()` call wired in

**Dependencies:** Phase 6 (evaluate_warnings must exist to wire into main.py).

**Testable immediately:** Run the exe as a standard user — behavior unchanged. Run with USERNAME=SYSTEM
in environment — no `os.startfile`, no blocking `input()`.

---

### Phase 9: Company Portal Detection (Windows)

**Why fourth:** The simplest collector change — one dict added to `APP_SPECS`. Can be done any time
after Phase 6 (no dependency on warnings). Ordered here because Mac work is the largest chunk and
should not be blocked by this one-liner.

**Files:**
- `collectors/windows/apps.py` — add Company Portal entry to `APP_SPECS`

**Dependencies:** None (APP_SPECS is self-contained; AppStatus model unchanged).

**Testable immediately:** Run on a machine with Company Portal installed; verify AppStatus appears
in report.apps. Unit test with mocked registry data.

---

### Phase 10: Mac Collectors

**Why last:** Largest chunk of new code. Requires a Mac to validate. Not a dependency for any
Windows feature. Doing it last means Windows features (Phases 6-9) can be shipped and tested on
real machines before Mac work begins.

**Build order within Mac work:**
1. `collectors/mac/__init__.py` (empty, unblocks import)
2. `collectors/mac/hardware.py` — hardware facts first; validates psutil cross-platform behavior
3. `collectors/__init__.py` — add Darwin dispatch branch (unblocks end-to-end test on Mac)
4. `collectors/mac/apps.py` — app detection; requires validating bundle paths on a real Mac

**Files:**
- `collectors/mac/__init__.py` — NEW (empty)
- `collectors/mac/hardware.py` — NEW
- `collectors/mac/apps.py` — NEW
- `collectors/__init__.py` — MODIFIED (add Darwin branch)

**Dependencies:** Phase 6 (Warning dataclass on AuditReport); Phase 7 (HTML renders mac data correctly).

**Testable:** Run on macOS. The renderer, writers, and parsers require zero changes — cross-platform
correctness is enforced by the `AuditReport` contract.

---

## Data Model Changes Summary

```
models.py additions:

@dataclass
class Warning:                          # NEW
    code: str
    severity: str                       # 'critical' | 'warning' | 'info'
    message: str
    detail: str | None = None

@dataclass
class AuditReport:
    ...existing fields unchanged...
    warnings: list[Warning] = field(default_factory=list)   # NEW FIELD
```

No existing fields are removed or renamed. All v1.0 tests continue to pass because `warnings`
defaults to an empty list — existing test fixtures that construct `AuditReport()` without `warnings`
are unaffected.

---

## Error Handling Notes for New Features

| Scenario | Response |
|----------|----------|
| SYSTEM context, `os.startfile` called | Guard prevents the call; clean exit |
| SYSTEM context, `input()` called | Guard prevents the call; clean exit |
| Mac: `sw_vers` subprocess fails | `collect_hardware` catches, appends to `collection_errors`, `os_build` stays None |
| Mac: `plistlib.load` fails for an app | `detect_apps` catches per-app, appends `AppStatus(installed=False, error=...)` |
| Mac: `/Users/` unreadable | `collect_profiles` catches, appends to `collection_errors`, `local_profiles` stays `[]` |
| Company Portal not installed | Standard `AppStatus(installed=False)` — no change to error handling |
| `evaluate_warnings()` raises | Each check function is its own try/except; one failure does not suppress other warnings |

The core invariant is unchanged: the tool always produces HTML output, even if every collector fails.

---

## Anti-Patterns Added for v2.0

### Anti-Pattern 5: Warning Logic in the Template

**What:** Putting threshold comparisons (`{% if disk_free_gb < 20 %}`) in the Jinja2 template.

**Why bad:** Templates cannot be unit-tested. Thresholds buried in HTML are invisible to code review
and impossible to adjust without touching template markup.

**Instead:** All threshold evaluation in `warnings.py`. Template only iterates `report.warnings`.

### Anti-Pattern 6: Blocking Calls Without TTY Check

**What:** Leaving `input("Press Enter...")` in the code path that NinjaOne executes.

**Why bad:** NinjaOne script execution hangs indefinitely waiting for stdin input that never comes.
The activity never completes; the agent eventually times out.

**Instead:** `_is_system_context()` guard in `main.py`. Interactive pause only when a human is at
a keyboard.

### Anti-Pattern 7: `os.startfile` in Headless Context

**What:** Calling `os.startfile()` when running as SYSTEM.

**Why bad:** SYSTEM has no desktop shell. `os.startfile()` raises `OSError` with "no application
is associated" or silently fails and may spawn a zombie process in session 0.

**Instead:** Same `_is_system_context()` guard. The file is already saved; NinjaOne reads stdout.

---

## Sources

- v1.0 shipped source code (direct inspection): `main.py`, `models.py`, `collectors/windows/hardware.py`,
  `collectors/windows/apps.py`, `renderer/__init__.py`, `renderer/templates/character_sheet.html`
- Windows SYSTEM account constraints: https://learn.microsoft.com/en-us/windows/win32/services/localsystem-account
- Mac `system_profiler` and `sw_vers` APIs: https://developer.apple.com/documentation/
- `plistlib` (Python stdlib): https://docs.python.org/3/library/plistlib.html
- `psutil` cross-platform disk/memory: https://psutil.readthedocs.io/en/latest/
- Intune Company Portal MSIX package name: https://learn.microsoft.com/en-us/mem/intune/apps/apps-company-portal-macos

---

*Architecture research updated for: StatusReport v2.0 milestone*
*Researched: 2026-05-07*
