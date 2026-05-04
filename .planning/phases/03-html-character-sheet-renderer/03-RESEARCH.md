# Phase 3: HTML Character Sheet Renderer - Research

**Researched:** 2026-05-04
**Domain:** Jinja2 HTML rendering, importlib.resources, PyInstaller data files, pure HTML/CSS
**Confidence:** HIGH

---

## Summary

Phase 3 builds a Jinja2 renderer that converts an `AuditReport` dataclass into a self-contained HTML file styled as a D&D character sheet. The full visual contract is already locked in `03-UI-SPEC.md` — no design decisions remain open. All field mappings, color values, spacing tokens, typography rules, and component specs are specified down to the pixel.

The primary technical challenge is the **template loading strategy**: Jinja2's built-in `PackageLoader` does not work reliably inside PyInstaller bundles because it requires packages to be installed as materialized directories, which is incompatible with how PyInstaller's frozen importer works. The project constraint (CLAUDE.md) mandates `importlib.resources.files()` for template loading. In `--onedir` mode (which this project uses), the template file lives on disk in the bundle directory alongside the executable, so `importlib.resources.files('renderer').joinpath('templates/character_sheet.html').read_text()` is the correct and verified approach. No third-party loader package is needed.

The second significant area is the **mock AuditReport construction** (D-10): Phase 3 uses hardcoded mock data instead of live collectors. The mock must exercise both installed and missing app states across all 11 apps, the None-field degradation paths, and the Quest Incomplete status path.

**Primary recommendation:** Implement `render_report()` using a `jinja2.Environment` with a custom `BaseLoader` (or `DictLoader`) that reads the template source via `importlib.resources.files('renderer').joinpath('templates/character_sheet.html').read_text(encoding='utf-8')`. This is 10 lines of code and is PyInstaller `--onedir` safe. Do not use `PackageLoader` — it is unreliable in frozen environments.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- D-01: "class" field = `device_type` verbatim. No fantasy renaming.
- D-02: "realm" field = parsed city name verbatim.
- D-03: "guild" field = `department` (warehouse) or `company_code` (user laptop) or `—` when both None.
- D-04: "station" field = raw int station number or `—` when None.
- D-05: Stat labels: CPU, RAM, Disk — no D&D renaming (STR/CON/HP).
- D-06: Stat values: CPU model string, RAM as `X.X GB`, disk as `X GB total`.
- D-07: Disk HP bar = `disk_free_gb / disk_total_gb` as percentage. Green >50% free, amber 20-50%, red ≤20%. Low HP = disk almost full.
- D-08: Each app slot: name + installed/missing badge (✓/✗) + version string when installed.
- D-09: Apps with `service_state` (e.g., CrowdStrike) show service state as supplementary label beside version.
- D-10: Mock AuditReport uses all 11 apps in mixed state: NinjaOne, CrowdStrike Falcon, MERP, Word, Excel, Outlook, Teams, OneDrive, Zoom, Chrome, Claude desktop app.
- D-11: Quest Status footer = "QUEST COMPLETE" (green) when all installed; "QUEST INCOMPLETE — X app(s) missing" (red) with count.
- D-12: Any None hardware field renders as `—` (em-dash) in muted grey. No row omitted, no "Unavailable".
- D-13: `disk_total_gb` None → grey empty bar with `—` text. No crash, no 0%.
- D-14: Dark panel aesthetic: `#1a1a2e` background, light text, green/red/amber semantic accents. No parchment, no serif.
- D-15: Template at `renderer/templates/character_sheet.html`, loaded via `importlib.resources.files('renderer').joinpath('templates/character_sheet.html')`.
- D-16: `renderer/__init__.py` exposes `render_report(report: AuditReport, output_path: Path) -> Path`. Writes to `output_path / "status_report.html"`. Does not call `sys.executable`.
- D-17: `writers/__init__.py` exposes `write_html(html: str, output_path: Path) -> Path`. Renderer calls writer.

### Claude's Discretion

- Exact CSS approach: inline styles vs `<style>` block vs external (pick most PyInstaller-safe — UI-SPEC locks this as embedded `<style>` block).
- Exact dark colour palette values beyond general direction (locked in UI-SPEC).
- Jinja2 filter/macro design for HP bar, badge rendering, None → `—` substitution.
- Whether OS version and OS build render as separate rows or combined.
- Whether `local_profiles` renders in Phase 3 (UI-SPEC omits it from layout, Claude can include/omit).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OUT-01 | HTML character sheet with RPG/D&D aesthetic — stat block layout for hardware, class/guild/realm fields, equipment list — remains functionally readable as IT data | Jinja2 Environment + custom loader renders template; UI-SPEC provides all visual specs; mock AuditReport provides test data |
| OUT-02 | HTML file saved to `sys.executable` parent directory (flash drive), derived from `sys.executable` not `os.getcwd()` | `render_report()` receives `output_path` as argument (D-16); `write_html()` writes to `output_path / "status_report.html"` (D-17); caller resolves path from `sys.executable` |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Template loading | `renderer/` package | `importlib.resources` (stdlib) | D-15 locks this; renderer owns template lifecycle |
| HTML rendering / variable substitution | `renderer/__init__.py` | Jinja2 `Environment` | Renderer prepares context dict, calls `env.from_string()` or equivalent |
| Disk write | `writers/__init__.py` | `pathlib.Path.write_text()` | D-17 separates file I/O from rendering concern |
| HP bar color logic | Python (renderer), not template | Jinja2 inlines CSS class | Percentage computed in Python; class name passed to template |
| Quest status logic | Python (renderer), not template | Jinja2 receives `quest_complete: bool`, `missing_count: int` | Logic in Python keeps template logic-free |
| None → em-dash substitution | Jinja2 `default` filter | Python pre-processing optional | UI-SPEC mandates `{{ value \| default('—') }}` pattern |
| Output path resolution | Caller (`main.py` in Phase 5) | Not in renderer | D-16 explicitly: renderer receives path, does not call `sys.executable` |
| Mock data construction | Test file / standalone script | Not in renderer module | D-10 mock is Phase 3 dev/test artifact |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1.6 | HTML template rendering with variable substitution, filters, conditionals | Project constraint (CLAUDE.md); verified installed in venv |
| importlib.resources | stdlib (Python 3.12) | Load template file from `renderer` package without filesystem path | PyInstaller `--onedir` safe; mandated by CLAUDE.md and D-15 |
| pathlib.Path | stdlib | Write HTML to output directory | Cross-platform, already used in project |

**Version verification:** Jinja2 3.1.6 confirmed via `.venv/Scripts/python -c "import jinja2; print(jinja2.__version__)"` [VERIFIED: venv inspection]

Python 3.12.10 confirmed in venv. [VERIFIED: venv inspection]

**Jinja2 is NOT yet installed in the venv.** It must be added to requirements before any renderer code can run. [VERIFIED: venv pip list shows only pytest, colorama, iniconfig, packaging, pluggy, Pygments]

**Installation:**
```bash
pip install jinja2==3.1.6
```
Also add to a `requirements.txt` (or equivalent) for the project.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom `BaseLoader` + `importlib.resources` | `jinja2.PackageLoader` | PackageLoader fails in PyInstaller frozen environments; custom loader is 10 lines and guaranteed to work with `--onedir` |
| Custom `BaseLoader` + `importlib.resources` | `jinja2-embedded` (third-party) | `jinja2-embedded` solves the same problem but adds a dependency; for `--onedir` (not `--onefile`) a simple `read_text()` approach suffices since templates stay on disk |
| Embedded `<style>` block | External CSS file | External CSS files are a PyInstaller risk (must be separately bundled); embedded `<style>` is self-contained and zero-risk (UI-SPEC locks this choice) |
| `pathlib.Path.write_text()` | `open()` built-in | Equivalent; `pathlib` is already the project convention |

---

## Architecture Patterns

### System Architecture Diagram

```
[mock AuditReport]
       |
       v
render_report(report, output_path)       <- renderer/__init__.py
       |
       |-- 1. load template source via importlib.resources.files('renderer')
       |          .joinpath('templates/character_sheet.html').read_text()
       |
       |-- 2. build context dict from report fields
       |       { hostname, device_type, city, guild, station,
       |         cpu_model, ram_gb, disk_total_gb, disk_free_gb,
       |         disk_pct, hp_class, os_combined, current_user,
       |         apps, quest_complete, missing_count, timestamp }
       |
       |-- 3. env.from_string(template_source).render(**ctx)
       |                                                      |
       |                               [character_sheet.html] |
       |                                 (Jinja2 template)    |
       |                                       |              |
       |                               {{ value | default('—') }}
       |                               {% if hp_class == 'hp-green' %}
       |                               {% for app in apps %}
       |
       |-- 4. write_html(html_str, output_path)  <- writers/__init__.py
                   |
                   v
          output_path / "status_report.html"     <- flash drive
               (Path.write_text, encoding='utf-8')
```

### Recommended Project Structure

```
renderer/
├── __init__.py          # render_report(report, output_path) -> Path
└── templates/
    └── character_sheet.html   # Jinja2 template (embedded <style> block)

writers/
└── __init__.py          # write_html(html, output_path) -> Path

tests/
└── test_renderer.py     # Phase 3 test suite (mock AuditReport)
```

Note: `renderer/templates/` does NOT need an `__init__.py`. The `importlib.resources.files('renderer').joinpath(...)` approach traverses subdirectories without requiring them to be Python packages. [VERIFIED: Python 3.12 docs — `files()` returns a `Traversable`; `joinpath()` navigates subdirectories]

### Pattern 1: Template Loading via importlib.resources (PyInstaller-safe)

**What:** Read the template file as a string using `importlib.resources.files()`, then pass it to Jinja2's `Environment.from_string()`. This avoids `PackageLoader` entirely.

**When to use:** Always — this is the only approach that works both in development (normal install) and inside a PyInstaller `--onedir` bundle.

```python
# Source: Python 3.12 importlib.resources docs + CLAUDE.md D-15
import importlib.resources as ir
from jinja2 import Environment

def _load_template_source() -> str:
    template_ref = ir.files('renderer').joinpath('templates/character_sheet.html')
    return template_ref.read_text(encoding='utf-8')

def render_report(report: AuditReport, output_path: Path) -> Path:
    template_source = _load_template_source()
    env = Environment(autoescape=True)
    template = env.from_string(template_source)
    ctx = _build_context(report)
    html = template.render(**ctx)
    return write_html(html, output_path)
```

[CITED: https://docs.python.org/3/library/importlib.resources.html]

### Pattern 2: Context Dict Construction (None-safe)

**What:** Build the template context dict in Python, pre-computing all derived values (disk percentage, HP class, guild, quest status) so the template stays logic-free.

**When to use:** Always — separates business logic from presentation.

```python
# Source: derived from models.py field types and UI-SPEC component specs
def _build_context(report: AuditReport) -> dict:
    ph = report.parsed_hostname

    # Guild: D-03
    guild = ph.department or ph.company_code  # warehouse uses dept, laptop uses company_code
    # If both None (Unknown type), guild remains None -> template renders —

    # Disk HP bar: D-07, D-13
    if report.disk_total_gb and report.disk_free_gb:
        pct = (report.disk_free_gb / report.disk_total_gb) * 100
        if pct > 50:
            hp_class = 'hp-green'
        elif pct > 20:
            hp_class = 'hp-amber'
        else:
            hp_class = 'hp-red'
    else:
        pct = 100  # grey bar, full width
        hp_class = 'hp-none'

    # RAM: D-06 — format as "X.X GB"
    ram_display = f'{report.ram_gb:.1f} GB' if report.ram_gb is not None else None

    # Disk total: D-06
    disk_total_display = f'{int(report.disk_total_gb)} GB total' if report.disk_total_gb is not None else None
    disk_label = (
        f'{report.disk_free_gb:.0f} GB free / {report.disk_total_gb:.0f} GB total'
        if report.disk_total_gb and report.disk_free_gb else None
    )

    # OS combined: UI-SPEC
    os_combined = None
    if report.os_version and report.os_build:
        os_combined = f'{report.os_version} — Build {report.os_build}'
    elif report.os_version:
        os_combined = report.os_version

    # Quest status: D-11
    missing = [app for app in report.apps if not app.installed]
    quest_complete = len(missing) == 0

    return {
        'hostname': report.hostname,
        'device_type': ph.device_type,
        'city': ph.city,
        'guild': guild,
        'station': ph.station,
        'cpu_model': report.cpu_model,
        'ram_display': ram_display,
        'disk_total_display': disk_total_display,
        'disk_pct': round(pct, 1),
        'hp_class': hp_class,
        'disk_label': disk_label,
        'os_combined': os_combined,
        'current_user': report.current_user,
        'apps': report.apps,
        'quest_complete': quest_complete,
        'missing_count': len(missing),
        'timestamp': report.timestamp,
    }
```

### Pattern 3: Jinja2 Template — None-safe Field Rendering

**What:** Use the `default` filter for all nullable fields. Use CSS classes (not inline styles) for semantic colors, except for the HP bar fill width which requires an inline `style`.

```html
{# Source: UI-SPEC Jinja2 Template Conventions table #}

{# None → em-dash for any nullable field #}
{{ city | default('—') }}
{{ guild | default('—') }}
{{ station | default('—') }}
{{ cpu_model | default('—') }}
{{ ram_display | default('—') }}

{# HP bar — only permitted inline style in template #}
<div class="hp-track">
  <div class="hp-fill {{ hp_class }}" style="width: {{ disk_pct }}%"></div>
</div>
<div class="hp-label">{{ disk_label | default('—') }}</div>

{# App badge #}
{% for app in apps %}
<tr class="{{ loop.index is even and 'row-alt' or '' }}">
  <td>{{ app.name }}</td>
  <td>
    {% if app.installed %}
      <span class="badge badge-installed">&#10003; Installed</span>
    {% else %}
      <span class="badge badge-missing">&#10007; Missing</span>
    {% endif %}
  </td>
  <td>{{ app.version or '' }}</td>
  <td>{{ app.service_state or '' }}</td>
</tr>
{% endfor %}

{# Quest status #}
{% if quest_complete %}
<div class="quest-status quest-complete">QUEST COMPLETE</div>
{% else %}
<div class="quest-status quest-incomplete">QUEST INCOMPLETE — {{ missing_count }} app(s) missing</div>
{% endif %}
```

### Pattern 4: Mock AuditReport (D-10)

**What:** Hardcoded `AuditReport` instance used in Phase 3 for development and testing. Exercises all badge states, Quest Incomplete path, None field degradation.

```python
# Source: CONTEXT.md D-10 + models.py fields
from models import AuditReport, ParsedHostname, AppStatus
from parsers.name_parser import parse_hostname

MOCK_REPORT = AuditReport(
    hostname='PHX-INV-003',
    parsed_hostname=parse_hostname('PHX-INV-003'),
    os_version='Windows 10 Pro',
    os_build='19045',
    cpu_model='Intel Core i7-10700',
    ram_gb=16.0,
    disk_total_gb=476.0,
    disk_free_gb=38.0,   # ~8% free → red bar (≤20%)
    current_user='jsmith',
    local_profiles=['C:\\Users\\jsmith', 'C:\\Users\\admin'],
    apps=[
        AppStatus('NinjaOne', installed=True, version='5.8.1234'),
        AppStatus('CrowdStrike Falcon', installed=True, version='7.14.17608', service_state='Running'),
        AppStatus('MERP', installed=False),
        AppStatus('Word', installed=True, version='16.0.17628'),
        AppStatus('Excel', installed=True, version='16.0.17628'),
        AppStatus('Outlook', installed=True, version='16.0.17628'),
        AppStatus('Teams', installed=False),
        AppStatus('OneDrive', installed=True, version='24.021.0201'),
        AppStatus('Zoom', installed=False),
        AppStatus('Chrome', installed=True, version='124.0.6367.60'),
        AppStatus('Claude desktop app', installed=False),
    ],
    timestamp='2026-05-04 22:10:00',
)
```

### Anti-Patterns to Avoid

- **Using `PackageLoader`:** `jinja2.PackageLoader('renderer', 'templates')` raises `ValueError: The 'renderer' package was not installed in a way that PackageLoader understands` in PyInstaller frozen environments. [CITED: https://github.com/pallets/jinja/issues/1512]
- **Using `FileSystemLoader` with absolute path:** Breaks portability across machines and in bundles.
- **Calling `sys.executable` inside `render_report()`:** D-16 explicitly forbids this — caller resolves the path.
- **Logic in Jinja2 template:** Keep percentage computation, guild resolution, and quest counting in Python.
- **External CSS files:** No `<link>` tags — all styles must be in the embedded `<style>` block. [UI-SPEC]
- **Inline `style=""` attributes:** Only one permitted — the HP bar fill `width` property. All other styling via CSS classes. [UI-SPEC]
- **`autoescape=False`:** Template receives user-controlled strings (hostname, cpu_model). Always set `autoescape=True` on the Environment.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Template variable substitution | String `.format()` or f-strings | Jinja2 Environment | f-strings don't handle None gracefully, no loop/conditional support, XSS risk |
| None → fallback value | `value if value is not None else '—'` in template | Jinja2 `default` filter | Declarative, consistent, readable; works inline in template |
| HTML escaping | Manual `str.replace('<', '&lt;')` | Jinja2 `autoescape=True` | Comprehensive, handles all special chars including `"`, `'`, `&` |
| Zebra-stripe row alternation | Manual `index % 2` tracking | CSS `:nth-child(even)` | Zero Python code, pure CSS, UI-SPEC-mandated approach |

---

## Common Pitfalls

### Pitfall 1: `PackageLoader` in a Frozen Bundle
**What goes wrong:** `jinja2.PackageLoader('renderer', 'templates')` raises `ValueError` or silently falls back to `None` when the `renderer` package is in a PyInstaller `_MEIPASS` directory rather than a standard site-packages install.
**Why it happens:** `PackageLoader` uses Python's package introspection APIs which are incompatible with PyInstaller's `FrozenImporter`.
**How to avoid:** Use `importlib.resources.files('renderer').joinpath('templates/character_sheet.html').read_text()` and pass the string to `env.from_string()`.
**Warning signs:** `ValueError: The 'renderer' package was not installed in a way that PackageLoader understands.`
[CITED: https://github.com/pallets/jinja/issues/1512, https://github.com/GPla/jinja2-embedded]

### Pitfall 2: Jinja2 `autoescape` Off — XSS in HTML Report
**What goes wrong:** With `autoescape=False` (Jinja2 default for non-.html extensions when using `from_string()`), characters like `<`, `>`, `&` in CPU model strings or hostnames appear broken in the HTML or create injection vectors.
**Why it happens:** `Environment(autoescape=False)` is the default. `from_string()` does not auto-detect the output format.
**How to avoid:** Always instantiate with `Environment(autoescape=True)` when rendering HTML.
**Warning signs:** `<` in CPU model string renders as literal less-than sign breaking the HTML structure.

### Pitfall 3: `disk_total_gb` Division by Zero / ZeroDivisionError
**What goes wrong:** If `disk_total_gb` is `0.0` (not `None` but zero), the percentage computation `disk_free_gb / disk_total_gb` raises `ZeroDivisionError`.
**Why it happens:** The guard `if report.disk_total_gb` is `False` for `0.0`, so the None-path runs correctly. But if a collector returns `0.0` rather than `None`, the guard still catches it (Python treats `0.0` as falsy). This is actually correct — document it explicitly.
**How to avoid:** Use `if report.disk_total_gb` (not `is not None`) as the guard — this handles both `None` and `0.0` as "no disk data" cases. Matches D-13 intent.

### Pitfall 4: Guild Logic for Unknown Device Type
**What goes wrong:** For `device_type='Unknown'`, both `parsed_hostname.department` and `parsed_hostname.company_code` are `None`. Incorrect guild logic might show one of them when both are None or crash on attribute access.
**Why it happens:** D-03 says: warehouse → `department`, user laptop → `company_code`, both None → `—`. If implementation does `ph.department or ph.company_code`, this correctly returns `None` when both are `None`. The Jinja2 `default('—')` filter then handles it.
**How to avoid:** Python-side guild resolution: `guild = ph.department or ph.company_code`. Pass `guild` to template. Template: `{{ guild | default('—') }}`.

### Pitfall 5: `importlib.resources` Template Path — Subdirectory vs Package
**What goes wrong:** `ir.files('renderer').joinpath('templates', 'character_sheet.html')` works if `renderer/templates/` is a regular directory. Adding `__init__.py` to `renderer/templates/` would make it a Python package, which is unnecessary and could cause import confusion.
**Why it happens:** Developers sometimes follow `jinja2-embedded` patterns which require `__init__.py` in the templates dir. This project does NOT use `jinja2-embedded` and does not need it.
**How to avoid:** Do NOT put `__init__.py` in `renderer/templates/`. The directory is a data directory, not a Python package.

### Pitfall 6: Template Not Included in PyInstaller Bundle
**What goes wrong:** The HTML template file is missing from the `--onedir` bundle because PyInstaller doesn't automatically bundle non-Python files from packages.
**Why it happens:** PyInstaller collects `.py` files; data files require explicit `--add-data` or `datas` in the spec file.
**How to avoid:** Phase 5 (packaging) must add `datas=[('renderer/templates/character_sheet.html', 'renderer/templates')]` to the PyInstaller spec. **This is a Phase 5 concern**, but Phase 3 must place the template at the correct path (`renderer/templates/character_sheet.html`) so Phase 5 can reference it.
**Warning signs:** `FileNotFoundError` or empty template rendered when running the bundled exe.
[CITED: https://pyinstaller.org/en/stable/usage.html]

---

## Code Examples

### Environment Instantiation (correct pattern)
```python
# Source: Jinja2 3.1.x docs — https://jinja.palletsprojects.com/en/stable/api/
from jinja2 import Environment

env = Environment(autoescape=True)
template = env.from_string(template_source)
html = template.render(**context)
```

### importlib.resources Template Read (Python 3.12)
```python
# Source: https://docs.python.org/3/library/importlib.resources.html
import importlib.resources as ir

def _load_template() -> str:
    return (
        ir.files('renderer')
        .joinpath('templates/character_sheet.html')
        .read_text(encoding='utf-8')
    )
```

### writers/\_\_init\_\_.py — write_html (D-17)
```python
# Source: CONTEXT.md D-17
from pathlib import Path

def write_html(html: str, output_path: Path) -> Path:
    """Write HTML string to output_path / 'status_report.html'. Returns full path."""
    dest = output_path / 'status_report.html'
    dest.write_text(html, encoding='utf-8')
    return dest
```

### HP Bar Color Logic (D-07, D-13)
```python
# Source: CONTEXT.md D-07 / D-13, UI-SPEC color table
if report.disk_total_gb and report.disk_free_gb is not None:
    pct = (report.disk_free_gb / report.disk_total_gb) * 100
    hp_class = 'hp-green' if pct > 50 else ('hp-amber' if pct > 20 else 'hp-red')
else:
    pct = 100.0
    hp_class = 'hp-none'
```

### CSS Color Variables (from UI-SPEC)
```css
/* Source: 03-UI-SPEC.md Color section */
:root {
  --bg-dominant:   #1a1a2e;  /* 60% — page/outer background */
  --bg-secondary:  #16213e;  /* 30% — section cards */
  --bg-accent:     #0f3460;  /* section header rows */
  --text-body:     #e0e0e0;
  --text-muted:    #6b7280;  /* em-dash fields */
  --text-heading:  #a8b2d8;  /* section titles */
  --border:        #2d3561;
  --green:         #22c55e;  /* installed badge, HP healthy, quest complete */
  --amber:         #f59e0b;  /* HP warning */
  --red:           #ef4444;  /* missing badge, HP critical, quest incomplete */
  --hp-track:      #374151;
  --hp-none:       #4b5563;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pkg_resources` for package data | `importlib.resources` | Python 3.9+ | `pkg_resources` is deprecated; `importlib.resources` is stdlib |
| `PackageLoader` for Jinja2 in bundles | Custom loader + `importlib.resources.files()` | PyInstaller 5+ era | PackageLoader unreliable in frozen environments |
| `importlib.resources.read_text(package, name)` | `importlib.resources.files(anchor).joinpath(name).read_text()` | Python 3.12 (3.9 introduced `files()`) | Old `read_text()` top-level function deprecated in 3.11, removed in 3.13 |

[CITED: https://docs.python.org/3/library/importlib.resources.html]

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Renderer implementation | Yes | 3.12.10 | — |
| Jinja2 | Template rendering | NO — not installed | — | Must install: `pip install jinja2==3.1.6` |
| pytest | Test suite | Yes | 8.4.2 | — |
| importlib.resources | Template loading | Yes (stdlib) | Python 3.12 | — |

**Missing dependencies with no fallback:**
- **Jinja2** — not installed in the venv. Wave 0 of Phase 3 must run `pip install jinja2==3.1.6`. This is a hard blocker for any renderer code.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `importlib.resources.files('renderer').joinpath('templates/character_sheet.html').read_text()` works in PyInstaller `--onedir` because templates stay as real files on disk (not extracted from a zip) | Standard Stack, Pitfall 6 | If PyInstaller `--onedir` somehow doesn't materialize the template file, renderer fails at runtime. Mitigation: Phase 5 must explicitly test this path before distribution. |
| A2 | `env.from_string()` with `autoescape=True` correctly HTML-escapes all template variables | Code Examples | If autoescape doesn't work as expected with `from_string()`, XSS or malformed HTML. Mitigation: verify in test that `<` in cpu_model is escaped to `&lt;` |

---

## Open Questions

1. **Should `local_profiles` appear in the character sheet?**
   - What we know: `local_profiles: list[str]` is on `AuditReport`. UI-SPEC omits it from the layout skeleton. D-discretion says Claude can include or omit.
   - What's unclear: Whether IT staff find it useful in the output.
   - Recommendation: Omit it from Phase 3. The field will be populated by Phase 2 and can be added to the template in a future iteration without breaking any interface.

2. **OS row combined vs. separate?**
   - What we know: UI-SPEC `Stat Block` table shows `OS | {os_version} — Build {os_build}`. This is one row, combined.
   - What's unclear: Nothing — UI-SPEC is definitive.
   - Recommendation: Single OS row, combined format as specified in UI-SPEC.

---

## Sources

### Primary (HIGH confidence)
- Python 3.12 importlib.resources docs — `files()`, `joinpath()`, `read_text()` API — https://docs.python.org/3/library/importlib.resources.html
- Jinja2 3.1.x API docs — Environment, from_string, autoescape, BaseLoader — https://jinja.palletsprojects.com/en/stable/api/
- `.venv/Scripts/python` — Verified Jinja2 3.1.6 installed; Python 3.12.10 confirmed; pip list shows Jinja2 not in venv [VERIFIED: direct venv inspection]
- `03-UI-SPEC.md` — Full visual contract; all colors, spacing, component specs [VERIFIED: file read]
- `03-CONTEXT.md` — All D-01 through D-17 decisions [VERIFIED: file read]
- `models.py` — AuditReport, AppStatus, ParsedHostname field types [VERIFIED: file read]

### Secondary (MEDIUM confidence)
- jinja2-embedded PyPI / GitHub — Confirms PackageLoader fails in frozen environments; identifies `importlib` ResourceReader as the correct path — https://pypi.org/project/jinja2-embedded/, https://github.com/GPla/jinja2-embedded
- Jinja2 GitHub issue #1512 — PackageLoader ValueError in non-standard installs — https://github.com/pallets/jinja/issues/1512

### Tertiary (LOW confidence)
- PyInstaller docs (operating-mode, usage) — Data file bundling mechanism; `--onedir` keeps files on disk. Specific `importlib.resources` + `--onedir` interaction was not fully documented in fetched content. [ASSUMED: A1 above]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Jinja2 3.1.6 verified in venv; importlib.resources API verified against Python 3.12 docs
- Architecture: HIGH — D-15/D-16/D-17 fully lock the module interfaces; UI-SPEC locks all visual behavior
- Template loading pattern: HIGH — `from_string()` + `importlib.resources.files()` approach verified; PackageLoader incompatibility confirmed by multiple official sources
- PyInstaller `--onedir` template materialization: MEDIUM — behavior described in PyInstaller docs but not directly verified in this session (Phase 5 concern)
- Pitfalls: HIGH — All pitfalls derived from official documentation or locked project decisions

**Research date:** 2026-05-04
**Valid until:** 2026-06-04 (Jinja2 3.1.x is stable; Python 3.12 stdlib stable)
