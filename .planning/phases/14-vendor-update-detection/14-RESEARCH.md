# Phase 14: Vendor Update Detection — Research

**Researched:** 2026-05-18
**Domain:** Windows registry detection, XML parsing, dataclass extension, Jinja2 template rendering
**Confidence:** HIGH (codebase reads verified; DCU XML structure MEDIUM — no live file confirmed)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `VendorUpdateStatus` dataclass: `installed: bool | None`, `pending_count: int | None`, `scan_data_present: bool`
- **D-02:** Two new fields on `AuditReport` after `pending_updates`: `dell_dcu: VendorUpdateStatus | None = None`, `lenovo_lsu: VendorUpdateStatus | None = None`
- **D-03:** No `error` field on `VendorUpdateStatus`. Errors set fields to `None`, append to `report.collection_errors`
- **D-04:** `collect_vendor_updates(report)` called only when `--updates` is passed, alongside `collect_pending_updates(report)` in `main.py`
- **D-05:** When `--updates` absent, `dell_dcu` and `lenovo_lsu` remain `None`; renderer omits rows entirely — no placeholder
- **D-06:** Vendor rows live inside existing **System Health** stat block group (Phase 13 D-15 reserved space). No new section header
- **D-07:** Dell display values: Not installed → `"Not installed"` | installed, XML absent → `"Unknown (no scan data)"` | installed, XML present → `"{N} pending"`
- **D-08:** Lenovo display values: Not installed → `"Not installed"` | Installed → `"N/A"`
- **D-09:** Row label text is Claude's discretion
- **D-10:** DCU detection via registry Uninstall sweep with `display_name_keywords: ["Dell Command Update", "Dell Command | Update"]`
- **D-11:** DCU XML probed at one fixed path: `C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml`
- **D-12:** Parse XML to extract pending update count (researcher to confirm structure — see below)
- **D-13:** LSU detection via registry Uninstall sweep with `display_name_keywords: ["Lenovo System Update"]`
- **D-14:** LSU: `scan_data_present` always `False`, `pending_count` always `None`
- **D-15:** New module: `collectors/windows/vendor.py` — exports `collect_vendor_updates(report: AuditReport) -> None`
- **D-16:** Import `UNINSTALL_PATHS` from `collectors/windows/apps.py` (or move to shared location)

### Claude's Discretion

- Exact row label text for vendor rows in System Health section
- Whether `UNINSTALL_PATHS` is imported from `apps.py` or extracted to a shared `collectors/windows/_registry.py`
- DCUApplicableUpdates.xml element/attribute structure for pending count (researcher to confirm)
- Test fixture approach for "DCU installed but XML absent" and "DCU not installed" paths

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VENDOR-01 | User can see Dell Command Update installation status and pending update count in character sheet; count read passively from DCUApplicableUpdates.xml (never invokes dcu-cli.exe); shows "Not installed" when absent | D-10, D-11, D-12: registry detection + XML parse confirmed viable; XML structure documented below |
| VENDOR-02 | User can see Lenovo System Update installation status in character sheet; pending count shown as N/A (no passive source in v3.0); never invokes tvsu.exe | D-13, D-14: registry detection confirmed; DisplayName "Lenovo System Update" verified by external sources |
</phase_requirements>

---

## Summary

Phase 14 adds passive vendor update detection for Dell Command Update (DCU) and Lenovo System Update (LSU). "Passive" means the tool reads pre-existing scan artifacts rather than invoking any vendor CLI. The entire feature is gated behind `--updates` — when absent, the character sheet renders identically to Phase 13 output.

The implementation is straightforward: one new module (`collectors/windows/vendor.py`) with two detection functions that reuse the `_search_uninstall_keys()` pattern already proven in `apps.py`. For Dell, a secondary step reads `DCUApplicableUpdates.xml` if present. The System Health section in `character_sheet.html` gains two conditional rows.

The primary research question was the XML structure of `DCUApplicableUpdates.xml`. Multiple independent sources (PowerShell community scripts) confirm the structure: root element `<updates>`, child elements `<update>`, each `<update>` having properties including `name`, `version`, `date`, `urgency`, `type`, `category`. The pending count is `len($xml.updates.update)` — count of `<update>` child elements. This is a LOW-confidence finding because it comes from community scripts, not Dell official documentation; a real file has never been observed in this project.

The character sheet integration slot is already prepared: Phase 13 placed a `<!-- System Health — Phase 13 -->` comment with two rows (Uptime, Pending Updates) and closed the `stat-block` div immediately after. Vendor rows insert before that closing `</div>`, conditioned on `dell_dcu is not none` / `lenovo_lsu is not none`.

**Primary recommendation:** Implement `vendor.py` using the `_search_uninstall_keys()` import pattern; parse DCUApplicableUpdates.xml counting `<update>` child elements via `xml.etree.ElementTree`; insert vendor rows in the System Health block conditioned on `--updates` gate.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Registry detection (installed bool) | Collector (Windows) | — | winreg reads happen at collection time; result stored in AuditReport |
| XML file read + parse | Collector (Windows) | — | Filesystem access at collection time; result stored in AuditReport |
| Pending count computation | Collector (Windows) | — | Count of `<update>` elements computed once at collection; stored as `int | None` |
| Display string formatting | Renderer (`_build_context`) | — | Pattern matches existing `pending_updates_display` — renderer turns raw field into display string |
| Conditional row rendering | Template (`character_sheet.html`) | Renderer | Template checks `dell_dcu is not none`; no row rendered when `--updates` absent |
| CLI gate (`--updates`) | `main.py` | — | Existing flag; `collect_vendor_updates` added alongside `collect_pending_updates` in both `--updates` blocks |

---

## Standard Stack

No new dependencies for this phase. All required tools are stdlib or already installed.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `winreg` | stdlib | Registry Uninstall sweep for DCU/LSU detection | Already used in `apps.py`; no new import |
| `xml.etree.ElementTree` | stdlib | Parse `DCUApplicableUpdates.xml` | Stdlib; no pip dep; sufficient for simple element-count parse |
| `pathlib.Path` | stdlib | Probe XML file at fixed path | Already used throughout project |

### No New Dependencies
`pywin32`, `psutil`, `wmi`, `Jinja2` — all already installed. Phase 14 adds zero pip dependencies.

**Installation:** none required.

---

## Architecture Patterns

### System Architecture Diagram

```
main.py (--updates flag)
  |
  +-- collect_pending_updates(report)      [existing, hardware.py]
  |
  +-- collect_vendor_updates(report)       [NEW, vendor.py]
        |
        +-- _detect_dcu(report)
        |     |
        |     +-- _search_uninstall_keys(["Dell Command Update","Dell Command | Update"])
        |     |     --> sets report.dell_dcu.installed
        |     |
        |     +-- [if installed] Path(DCU_XML_PATH).exists() ?
        |           |
        |           YES --> xml.etree.ElementTree.parse() --> count <update> elements
        |           |       --> sets report.dell_dcu.pending_count, scan_data_present=True
        |           |
        |           NO  --> scan_data_present=False, pending_count=None
        |
        +-- _detect_lsu(report)
              |
              +-- _search_uninstall_keys(["Lenovo System Update"])
                    --> sets report.lenovo_lsu.installed
                    --> scan_data_present=False, pending_count=None (always)

AuditReport.dell_dcu:  VendorUpdateStatus | None
AuditReport.lenovo_lsu: VendorUpdateStatus | None

renderer/_build_context(report)
  |
  +-- dell_dcu_display: str | None   (computed if dell_dcu is not None)
  +-- lenovo_lsu_display: str | None (computed if lenovo_lsu is not None)

character_sheet.html
  <!-- System Health — Phase 13 -->
  [Uptime row]
  [Pending Updates row]
  {% if dell_dcu_display is not none %}  <-- NEW
    [Dell Cmd Update row]
  {% endif %}
  {% if lenovo_lsu_display is not none %}  <-- NEW
    [Lenovo Sys Update row]
  {% endif %}
```

### Recommended Project Structure

No structural changes beyond adding one file:

```
collectors/
  windows/
    apps.py         # UNINSTALL_PATHS + _search_uninstall_keys() live here (unchanged)
    hardware.py     # collect_pending_updates() lives here (unchanged)
    vendor.py       # NEW — collect_vendor_updates(report) exports
models.py           # Add VendorUpdateStatus dataclass; add two fields to AuditReport
renderer/
  __init__.py       # Add dell_dcu_display, lenovo_lsu_display to _build_context()
  templates/
    character_sheet.html  # Add two conditional rows in System Health block
tests/
  test_vendor_collector.py  # NEW — covers vendor.py
  test_models_phase14.py    # NEW — covers VendorUpdateStatus and AuditReport fields
  test_renderer_phase14.py  # NEW — covers _build_context() vendor display values
```

### Pattern 1: Import UNINSTALL_PATHS from apps.py (D-16 as-is)

**What:** Import the existing constant directly rather than duplicating.

**When to use:** When apps.py is not being refactored. Clean path with zero risk of constant drift.

**Example:**
```python
# Source: VERIFIED — collectors/windows/apps.py lines 25-30
from collectors.windows.apps import UNINSTALL_PATHS, _search_uninstall_keys

def _detect_dcu(report: AuditReport) -> None:
    try:
        installed, _version = _search_uninstall_keys(
            ["Dell Command Update", "Dell Command | Update"]
        )
        ...
    except Exception as exc:
        report.collection_errors.append(f"DCU detection failed: {exc}")
        report.dell_dcu = VendorUpdateStatus(installed=None, pending_count=None, scan_data_present=False)
```

**Tradeoff vs shared `_registry.py`:** Extracting `UNINSTALL_PATHS` and `_search_uninstall_keys` to `collectors/windows/_registry.py` is cleaner for the long term but is a refactor with test surface impact. The planner must choose; both are valid.

### Pattern 2: DCU XML Parse

**What:** Read `DCUApplicableUpdates.xml`, count `<update>` child elements under root `<updates>`.

**When to use:** When `scan_data_present = True` (file exists and is readable).

**Example:**
```python
# Source: [CITED: community scripts at cyberdrain.com + automox.com + ajh0912/Useful-PowerShell]
import xml.etree.ElementTree as ET

DCU_XML_PATH = r"C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml"

def _read_dcu_pending_count() -> tuple[int | None, bool]:
    """Return (pending_count, scan_data_present).
    scan_data_present=False when file absent or unreadable.
    pending_count=None on parse error; 0 is a valid (no pending updates) result.
    """
    p = Path(DCU_XML_PATH)
    if not p.exists():
        return None, False
    try:
        tree = ET.parse(p)
        root = tree.getroot()
        # root tag expected: "updates"; children are <update> elements
        count = len(root.findall("update"))
        return count, True
    except ET.ParseError:
        return None, True  # file present but unparseable — scan_data_present=True
```

**Note on ParseError edge case:** If the file exists but is partially written (DCU scan in progress), `ET.ParseError` is raised. Setting `scan_data_present=True, pending_count=None` in this case is correct — the file was present but unreadable.

### Pattern 3: VendorUpdateStatus Dataclass

```python
# Source: VERIFIED — models.py pattern; mirrors AppStatus / Warning dataclass style
@dataclass
class VendorUpdateStatus:
    """Detection result for a vendor update tool.
    No error field — errors set installed/pending_count to None
    and append to report.collection_errors (D-03).
    """
    installed: bool | None       # True=found; False=not found; None=collection error
    pending_count: int | None    # int from XML; None when not installed, XML absent, or parse error
    scan_data_present: bool      # True only when XML file exists and was readable
```

**Placement:** Insert before `AuditReport` in `models.py`. The current last dataclass before `AuditReport` is `Warning` (line 52). Insert `VendorUpdateStatus` between `Warning` and `AuditReport`.

### Pattern 4: AuditReport Field Insertion

**Exact insertion point:** After `pending_updates` (line 77 in current `models.py`).

Current state around line 77:
```python
    pending_updates: int | None = None   # Windows update count from WUA COM; None when inaccessible (D-04/D-08)
    local_profiles: list[str] = field(default_factory=list)
```

New state:
```python
    pending_updates: int | None = None   # Windows update count from WUA COM (D-04/D-08)
    dell_dcu: VendorUpdateStatus | None = None    # D-02 (Phase 14)
    lenovo_lsu: VendorUpdateStatus | None = None  # D-02 (Phase 14)
    local_profiles: list[str] = field(default_factory=list)
```

### Pattern 5: Renderer `_build_context()` Extension

**What:** Add two display-value keys to the context dict, conditioned on field presence.

**When to use:** Always — matches `pending_updates_display` pattern in current renderer.

```python
# Source: VERIFIED — renderer/__init__.py lines 159-164 (pending_updates_display pattern)

# Dell DCU display
if report.dell_dcu is not None:
    dcu = report.dell_dcu
    if not dcu.installed:
        dell_dcu_display = "Not installed"
    elif not dcu.scan_data_present:
        dell_dcu_display = "Unknown (no scan data)"
    else:
        dell_dcu_display = f"{dcu.pending_count} pending"
else:
    dell_dcu_display = None  # omit row entirely (D-05)

# Lenovo LSU display
if report.lenovo_lsu is not None:
    lsu = report.lenovo_lsu
    lenovo_lsu_display = "Not installed" if not lsu.installed else "N/A"
else:
    lenovo_lsu_display = None  # omit row entirely (D-05)
```

**Return dict additions:**
```python
'dell_dcu_display': dell_dcu_display,
'lenovo_lsu_display': lenovo_lsu_display,
```

### Pattern 6: Character Sheet Template

**Exact insertion point:** Lines 428-429 in `character_sheet.html` — the two blank lines after the `Pending Updates` row and before `</div>`.

Current state (verified via Grep):
```html
        <div class="stat-label">Pending Updates</div>
        <div class="stat-value{% if pending_updates_display == 'N/A' %} muted{% endif %}">{{ pending_updates_display }}</div>

      </div>
    </div>
```

New state:
```html
        <div class="stat-label">Pending Updates</div>
        <div class="stat-value{% if pending_updates_display == 'N/A' %} muted{% endif %}">{{ pending_updates_display }}</div>

        {% if dell_dcu_display is not none %}
        <div class="stat-label">Dell Cmd Update</div>
        <div class="stat-value{% if dell_dcu_display == 'Not installed' or dell_dcu_display == 'Unknown (no scan data)' %} muted{% endif %}">{{ dell_dcu_display }}</div>
        {% endif %}

        {% if lenovo_lsu_display is not none %}
        <div class="stat-label">Lenovo Sys Update</div>
        <div class="stat-value{% if lenovo_lsu_display == 'Not installed' or lenovo_lsu_display == 'N/A' %} muted{% endif %}">{{ lenovo_lsu_display }}</div>
        {% endif %}

      </div>
    </div>
```

**Note on row labels:** "Dell Cmd Update" and "Lenovo Sys Update" are within the Claude's Discretion scope; they fit the abbreviated style of other labels ("Serial Number", "Current User").

### Pattern 7: main.py Wiring

Two insertion points (both verified via Read of `main.py`):

**Location 1 — CLI path (`_run_cli`, lines 56-58):**
```python
        if args.updates and sys.platform != "darwin":
            from collectors.windows.hardware import collect_pending_updates
            collect_pending_updates(report)
            # ADD:
            from collectors.windows.vendor import collect_vendor_updates
            collect_vendor_updates(report)
```

**Location 2 — Full pipeline path (lines 123-125):**
```python
    if args.updates and sys.platform != "darwin":
        from collectors.windows.hardware import collect_pending_updates
        collect_pending_updates(report)
        # ADD:
        from collectors.windows.vendor import collect_vendor_updates
        collect_vendor_updates(report)
```

### Anti-Patterns to Avoid

- **Calling `dcu-cli.exe` or `tvsu.exe`:** Prohibited by VENDOR-01/VENDOR-02 and CLAUDE.md (side effects on production machines). Detection is registry-only; pending count is XML-only.
- **Duplicating `UNINSTALL_PATHS`:** The constant is already defined in `apps.py`. Duplicating it risks silent drift if paths change.
- **Raising exceptions across the layer boundary:** All exceptions in `collect_vendor_updates` must be caught and appended to `report.collection_errors` — same contract as all other collectors.
- **Treating `pending_count=0` as "no data":** Zero is a valid result meaning "DCU found no pending updates." Only `None` means "we don't know."
- **Using `Win32_Product` for detection:** Prohibited by CLAUDE.md (triggers MSI consistency checks). Registry sweep only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Registry Uninstall sweep | Custom registry walker | `_search_uninstall_keys()` from `apps.py` | Already handles all 4 paths, OSError skipping, DisplayName matching, first-match semantics |
| XML parsing | Custom string search / regex on XML | `xml.etree.ElementTree` (stdlib) | ET handles encoding, whitespace, malformed content; regex on XML is fragile |
| App detection via WMI | WMI query for installed apps | winreg sweep | WMI Win32_Product prohibited (CLAUDE.md); WMI Win32_InstalledSoftware unreliable |

**Key insight:** The registry detection infrastructure (`_search_uninstall_keys`) was purpose-built for exactly this kind of detection and already handles the edge cases (missing paths, permission errors, 32-bit vs 64-bit keys). Using it for vendor detection is the intended reuse path.

---

## DCU XML Structure (Critical Research Finding)

### Confirmed Structure [CITED: multiple community PowerShell scripts]

```xml
<updates>
  <update>
    <name>Intel HD Graphics Driver</name>
    <version>27.20.0.0</version>
    <date>2023-01-15</date>
    <urgency>Recommended</urgency>
    <type>Driver</type>
    <category>Video</category>
    <file>...</file>
    <LocalName>...</LocalName>
    <bytes>...</bytes>
  </update>
  <update>
    ...
  </update>
</updates>
```

**Pending count:** Count of direct `<update>` children of root `<updates>` element.

```python
root = ET.parse(path).getroot()  # root.tag == "updates"
count = len(root.findall("update"))
```

**When the file is empty (zero pending updates):**
```xml
<updates/>
```
or
```xml
<updates>
</updates>
```
Both yield `count = 0` from `root.findall("update")` — correct behavior.

**Sources:**
- [CITED: cyberdrain.com/monitoring-with-powershell-monitoring-dell-driver-updates-dcu-3-1/] — `$XMLReport.updates.update`, type/urgency attributes
- [CITED: community.automox.com/find-share-worklets-12/basic-dell-command-update-worklet-2278] — `$updates.updates.update` loop, `$update.urgency`, `$update.date`, `$update.name`
- [CITED: github.com/ajh0912/Useful-PowerShell/blob/main/Get-DellUpdates.ps1] — `$dcuReport.updates.update | Select-Object -Property name, version, date, urgency, type, category, file, LocalName, bytes`

**Confidence:** MEDIUM — corroborated by three independent community scripts all showing identical structure. No live Dell machine in this project confirms it. `[ASSUMED]`: Root element is exactly `updates` with child elements exactly named `update` (no namespace, no wrapper element between root and updates). If this assumption is wrong, `root.findall("update")` returns `[]`, and `pending_count` would be 0 instead of the true count — a silent bug. The planner should include a note that IT confirmation on a real Dell machine is the Phase 14 closure gate.

### Handling Unknown Structure Gracefully

If the actual XML structure differs from the expected `<updates><update>` pattern, `root.findall("update")` returns `[]`, setting `pending_count = 0`. This produces a display value of `"0 pending"` instead of the correct count — a silent wrong answer rather than a crash. This is acceptable for the IT audit use case (IT knows DCU found updates), but is worth flagging. The planner may want to add a test that verifies the counted value against a known fixture.

---

## Existing Code: Key Verified Findings

### `_search_uninstall_keys()` Signature and Return
[VERIFIED: codebase read of `collectors/windows/apps.py` lines 134-174]

```python
def _search_uninstall_keys(
    keywords: list[str],
    excludes: list[str] | None = None,
) -> tuple[bool, str | None]:
```

- Returns `(True, version_str_or_None)` on first match across all 4 paths
- Returns `(False, None)` if no match found across all 4 paths
- **Never raises** — all `(FileNotFoundError, OSError)` are silently skipped
- First match wins — no duplicate detection

**Usage for vendor detection:**
```python
installed, _version = _search_uninstall_keys(["Dell Command Update", "Dell Command | Update"])
```
The version is not needed for `VendorUpdateStatus` — discard it.

### `UNINSTALL_PATHS` Constant
[VERIFIED: codebase read of `collectors/windows/apps.py` lines 25-30]

```python
UNINSTALL_PATHS: list[tuple[int, str]] = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
]
```

All 4 paths required — 32-bit DCU/LSU installs go to `WOW6432Node` (CLAUDE.md constraint).

### AuditReport Current Field Order
[VERIFIED: codebase read of `models.py` lines 62-85]

```
hostname, parsed_hostname, os_version, os_build, serial_number, cpu_model,
ram_gb, disk_total_gb, disk_free_gb, current_user,
uptime_seconds,       ← line 76 (Phase 13)
pending_updates,      ← line 77 (Phase 13)
*** INSERT dell_dcu and lenovo_lsu HERE ***
local_profiles,
apps, collection_errors, warnings, timestamp
```

### main.py `--updates` Gate Wiring
[VERIFIED: codebase read of `main.py` lines 55-58 and 123-125]

Both blocks follow the same pattern — `if args.updates and sys.platform != "darwin":`. `collect_vendor_updates` is Windows-only (no Mac path) so the `sys.platform != "darwin"` guard is already correct.

### System Health Template Slot
[VERIFIED: Grep of `character_sheet.html` — System Health section]

The Phase 13 comment `<!-- System Health — Phase 13 -->` marks the start of the section. The section currently has two stat rows (Uptime, Pending Updates) before the closing `</div>`. Vendor rows insert immediately before that closing `</div>`.

### Character Sheet Template Notes
The template uses Jinja2's `autoescape=True` (set in `renderer/__init__.py`). Display strings like `"Dell Cmd Update"` and `"Unknown (no scan data)"` contain no HTML special characters — no escaping issue. The `muted` CSS class is the existing pattern for N/A / not-available values.

### `collect_pending_updates` Pattern (reference for vendor.py shape)
[VERIFIED: codebase read of `collectors/windows/hardware.py` lines 76-91]

```python
def collect_pending_updates(report: AuditReport) -> None:
    """..."""
    if not _WIN32COM_AVAILABLE:
        return
    try:
        ...
        report.pending_updates = result.Updates.Count
    except Exception as exc:
        report.collection_errors.append(f"Pending updates collection failed: {exc}")
```

`collect_vendor_updates` follows the same shape: guard → try → mutate report fields → except → append error.

---

## Common Pitfalls

### Pitfall 1: Pipe Character in Dell DisplayName
**What goes wrong:** Dell registers the product as `"Dell Command | Update"` (with pipe) in some versions, and `"Dell Command Update"` (without pipe) in others.
**Why it happens:** Dell renamed the product and different installer versions use different display names.
**How to avoid:** Use both keywords: `["Dell Command Update", "Dell Command | Update"]`. The `_search_uninstall_keys()` function uses substring matching — `"Dell Command | Update"` as a keyword matches `"Dell Command | Update 5.5.0"` correctly.
**Warning signs:** Test passes on one machine (one version) but fails on another. Always use both keywords.
**Confidence:** MEDIUM [CITED: multiple PowerShell community scripts and Dell forum posts referencing both forms]

### Pitfall 2: `_search_uninstall_keys` is Private
**What goes wrong:** `_search_uninstall_keys` is a module-private function (underscore prefix). Importing it from another module breaks the encapsulation convention.
**Why it happens:** `apps.py` was not designed as a shared library.
**How to avoid:** Two valid approaches: (A) import directly (`from collectors.windows.apps import _search_uninstall_keys`) — acceptable since this is the same package, not an external consumer; or (B) extract to `_registry.py` (the cleaner long-term approach). The planner must choose. Both work correctly.
**Warning signs:** If `apps.py` is later refactored, vendor.py import breaks silently. Prefer (B) if any future phases also need registry sweep.

### Pitfall 3: XML File May Be Stale or Absent
**What goes wrong:** IT staff expects to see a pending count, but the XML file is absent because DCU has never been run, or it was deleted, or it contains a 6-month-old scan.
**Why it happens:** `DCUApplicableUpdates.xml` is only written after a DCU scan. On a freshly imaged machine or one where DCU was just installed, the file will not exist.
**How to avoid:** `scan_data_present=False` when file absent → display `"Unknown (no scan data)"`. This is correct behavior per D-07. The requirements doc notes: "IT must run DCU at least once for the count to appear."
**Warning signs:** `pending_count=None` when IT expects a number — they need to run DCU first.

### Pitfall 4: VendorUpdateStatus `installed=None` vs `installed=False`
**What goes wrong:** Using `installed=None` to mean "not found" instead of "collection error."
**Why it happens:** `_search_uninstall_keys()` returns `(False, None)` — not `(None, None)` — on a clean miss.
**How to avoid:** Only set `installed=None` on exception; set `installed=False` on a clean registry miss.

### Pitfall 5: `pending_count=0` is Not an Error
**What goes wrong:** Treating `pending_count=0` as "XML parse failed" or "no data."
**Why it happens:** Zero updates pending is a valid state (everything is up to date).
**How to avoid:** Only `pending_count=None` means "we couldn't determine the count." `pending_count=0` with `scan_data_present=True` means "DCU scanned and found 0 pending updates."

### Pitfall 6: Missing `--updates` Gate in Renderer
**What goes wrong:** Vendor rows appear in the character sheet even when `--updates` was not passed.
**Why it happens:** Renderer condition added incorrectly — checking `dell_dcu` fields instead of `dell_dcu is not none`.
**How to avoid:** When `--updates` is absent, `report.dell_dcu` stays `None`. The renderer condition `{% if dell_dcu_display is not none %}` (derived from `report.dell_dcu is not None`) correctly omits the row.

---

## UNINSTALL_PATHS Refactoring Decision

The planner must choose one of two approaches:

**Option A: Import from `apps.py` directly**
- Pro: Zero code change in `apps.py`; no refactoring risk
- Con: `vendor.py` imports a private helper from a sibling module; `apps.py` is not a "shared library"
- Test impact: None — existing `test_app_collector.py` patches `apps_mod.winreg` directly

**Option B: Extract to `collectors/windows/_registry.py`**
- Pro: Clean shared library; vendor.py and apps.py both import from `_registry.py`
- Con: Refactors `apps.py`; must update all `test_app_collector.py` mocks that patch `apps_mod.winreg` to patch `_registry.winreg` or the import path changes
- Test impact: `test_app_collector.py` patches `apps_mod.winreg` — this would break if `winreg` is now used via `_registry.py`

**Recommendation:** Option A for Phase 14. Option B is a good candidate for a dedicated refactor plan (e.g., Phase 14 Plan 0 or a standalone task). The risk of breaking 9+ `test_app_collector.py` tests during a feature phase is not worth taking without explicit scope.

---

## Registry Display Names: Confidence Assessment

### Dell Command Update
- **Keywords used:** `["Dell Command Update", "Dell Command | Update"]`
- **Confidence:** MEDIUM [CITED: forum.powershell.org and community scripts referencing both forms]
- **Risk:** If Dell uses a third form (e.g., "Dell Command | Update Application") the substring match still succeeds because "Dell Command | Update" is a substring
- **IT confirmation:** Locked decision; IT confirmed Dell machines in the fleet use DCU (STATE.md: "registry path uncertain — IT confirmation gate")

### Lenovo System Update
- **Keyword used:** `["Lenovo System Update"]`
- **Confidence:** MEDIUM [CITED: silentinstallhq.com detection script using exact match; Lenovo registry key `TVSU_is1` confirmed; DisplayName = "Lenovo System Update"]
- **Subkey:** `TVSU_is1` under the standard Uninstall paths (verified by multiple sources)
- **Risk:** Low — "Lenovo System Update" is a unique enough string; no known variants with different DisplayNames

---

## Test Patterns for This Phase

### No XML Fixture Files Exist
[VERIFIED: codebase search — no .xml files in `tests/`]

All Phase 4/13 tests for registry and file access use `unittest.mock.patch` — no fixture files on disk. The same pattern must be used for vendor.py tests.

### Pattern for XML Fixture (via mock or tmp_path)

Two valid approaches:

**Option A: `tmp_path` pytest fixture (preferred for XML content tests)**
```python
def test_dcu_xml_present_with_updates(tmp_path):
    xml_content = """<updates>
  <update><name>Driver A</name><urgency>Recommended</urgency></update>
  <update><name>BIOS 1.5</name><urgency>Urgent</urgency></update>
</updates>"""
    xml_file = tmp_path / "DCUApplicableUpdates.xml"
    xml_file.write_text(xml_content)
    # patch DCU_XML_PATH constant in vendor module
    with patch.object(vendor_mod, "DCU_XML_PATH", str(xml_file)):
        report = make_report()
        vendor_mod.collect_vendor_updates(report)
    assert report.dell_dcu.pending_count == 2
    assert report.dell_dcu.scan_data_present is True
```

**Option B: `patch("pathlib.Path.exists")` + `patch("xml.etree.ElementTree.parse")`**
```python
with patch.object(vendor_mod.Path, "exists", return_value=False):
    # test "XML absent" path
```

**Recommendation:** Use `tmp_path` for XML content tests (cleaner, tests actual ET parsing). Use `patch` for path-probe-only tests (installed=True, XML absent).

### Mock Pattern for Registry (same as test_app_collector.py)
[VERIFIED: test_app_collector.py lines 26-55]

```python
import collectors.windows.vendor as vendor_mod

with patch.object(vendor_mod.winreg, "OpenKey", return_value=fake_ctx), \
     patch.object(vendor_mod.winreg, "EnumKey", side_effect=_make_enum_fn(["DCU key"])), \
     patch.object(vendor_mod.winreg, "QueryValueEx",
                  side_effect=_make_query_fn("Dell Command | Update", "5.5.0")):
    ...
```

Note: If using Option A (import from apps.py), the mock target is `apps_mod.winreg` — the winreg reference used inside `_search_uninstall_keys`. If `vendor.py` imports `_search_uninstall_keys` directly, tests should patch `apps_mod.winreg` or patch `_search_uninstall_keys` itself.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Detect apps via WMI Win32_Product | Registry Uninstall sweep (winreg) | Phase 4 (v1.0) | Win32_Product triggers MSI reconfiguration — permanently prohibited |
| Per-app detection logic duplicated | Config-driven `APP_SPECS` table + `_search_uninstall_keys()` | Phase 4 refactor | All new detections reuse the same registry sweep infrastructure |
| No vendor update data | Passive XML read from DCU scan artifact | Phase 14 (v3.0) | Zero side effects; no CLI invoked; no admin privilege required |

**No deprecated patterns introduced by this phase.**

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | DCUApplicableUpdates.xml root element is `<updates>` with direct `<update>` children (no namespace, no wrapper element) | DCU XML Structure | `root.findall("update")` returns `[]`; pending_count=0 instead of true count — silent wrong answer |
| A2 | Both "Dell Command Update" (no pipe) and "Dell Command | Update" (with pipe) appear as registry DisplayName values across DCU versions | Common Pitfalls / Standard Stack | If neither matches on a machine, installed=False when DCU actually is installed |
| A3 | Dell Command Update is installed to the 64-bit registry path (HKLM, not Wow6432Node) on current Dell machines | Standard Stack | 32-bit DCU would only be found by the Wow6432Node path; the sweep covers all 4 so this is low risk |

**All three assumptions are low-to-medium risk.** A1 is the highest risk and requires IT confirmation on a real Dell machine before Phase 14 closes (this is already documented in STATE.md as a known blocker).

---

## Open Questions

1. **DCUApplicableUpdates.xml structure on live Dell machines in the fleet**
   - What we know: Three independent community scripts confirm `<updates><update>` structure
   - What's unclear: Whether the Master Electronics Dell fleet uses a DCU version that matches this structure; whether the file is present on any Dell machines
   - Recommendation: Mark Phase 14 acceptance criteria as "IT must verify on a real Dell machine"; plan should include a human UAT step

2. **Dell registry DisplayName variant: does the fleet use pipe or no-pipe form?**
   - What we know: Both forms exist across versions
   - What's unclear: Which form appears on Master Electronics Dell hardware specifically
   - Recommendation: Using both keywords in the sweep handles both cases; no action needed before planning

3. **`UNINSTALL_PATHS` / `_registry.py` refactor scope**
   - What we know: Both options (import from apps.py vs extract) are technically valid
   - What's unclear: Whether future phases (15+) will also need registry sweep, making extraction more worthwhile
   - Recommendation: The planner should choose Option A (import from apps.py) for Phase 14 and log Option B as a future refactor

---

## Environment Availability

Step 2.6: SKIPPED — Phase 14 is a pure code/config change. No new external tools, services, or CLIs are required. All runtime dependencies (`winreg`, `pathlib`, `xml.etree.ElementTree`) are Python stdlib. No new pip packages.

---

## Project Constraints (from CLAUDE.md)

All directives from `CLAUDE.md` relevant to this phase:

| Directive | Impact on Phase 14 |
|-----------|-------------------|
| NEVER use PyInstaller `--onefile` | Not applicable (no packaging changes) |
| NEVER use `Win32_Product` for app detection | Vendor detection uses winreg sweep only — compliant |
| ALWAYS enumerate all 4 registry Uninstall paths | `_search_uninstall_keys()` already does this; reuse is compliant |
| ALWAYS derive output path from `Path(sys.executable).parent` | Not applicable (vendor.py reads, does not write) |
| NEVER write to the host PC | vendor.py reads only (`DCUApplicableUpdates.xml` is read, not written) — compliant |
| Python 3.12, psutil 6.x, wmi 1.5.1, winreg, Jinja2 3.1.x, PyInstaller 6.x `--onedir` | No new dependencies; compliant |

---

## Sources

### Primary (HIGH confidence)
- `collectors/windows/apps.py` — VERIFIED codebase read: `UNINSTALL_PATHS`, `_search_uninstall_keys()` signature, return type, never-raises contract
- `collectors/windows/hardware.py` — VERIFIED codebase read: `collect_pending_updates()` shape, `_WIN32COM_AVAILABLE` guard pattern
- `models.py` — VERIFIED codebase read: current dataclass field order, `Warning`/`AppStatus` naming convention
- `main.py` — VERIFIED codebase read: `--updates` flag wiring locations (lines 56-58 and 123-125)
- `renderer/__init__.py` — VERIFIED codebase read: `_build_context()` pattern, `pending_updates_display` computation
- `renderer/templates/character_sheet.html` — VERIFIED Grep: System Health section structure, exact insertion point
- `tests/test_app_collector.py`, `tests/test_hardware_collector.py` — VERIFIED codebase read: mock patterns for registry and COM

### Secondary (MEDIUM confidence)
- [cyberdrain.com — Monitoring Dell Driver Updates DCU 3.1](https://www.cyberdrain.com/monitoring-with-powershell-monitoring-dell-driver-updates-dcu-3-1/) — DCU XML structure: `$XMLReport.updates.update`, type/urgency attributes confirmed
- [community.automox.com — Basic Dell Command Update Worklet](https://community.automox.com/find-share-worklets-12/basic-dell-command-update-worklet-2278) — confirmed `<updates><update>` root/child structure
- [github.com/ajh0912 — Get-DellUpdates.ps1](https://github.com/ajh0912/Useful-PowerShell/blob/main/Get-DellUpdates.ps1) — confirmed element properties: name, version, date, urgency, type, category, file, LocalName, bytes
- [silentinstallhq.com — Lenovo System Update detection](https://silentinstallhq.com/create-a-custom-detection-script-for-lenovo-system-update-powershell/) — DisplayName = "Lenovo System Update"; subkey TVSU_is1 confirmed
- [forums.powershell.org — DCU uninstall script](https://forums.powershell.org/t/any-version-of-dell-command-update-remove-script/18740) — confirmed both "Dell Command Update" and "Dell Command | Update" DisplayName forms exist

### Tertiary (LOW confidence — marked ASSUMED)
- A1 (XML structure): Three community scripts agree, but no live Dell machine in this project has been checked
- A2 (DCU DisplayName variants): Community forum discussion, not confirmed against ME fleet hardware

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools are stdlib, already imported in project
- Architecture: HIGH — all patterns verified directly from codebase reads
- DCU XML structure: MEDIUM — corroborated by 3 independent sources; no live file confirmed
- Registry DisplayNames: MEDIUM — multiple community sources; both keyword variants covered by sweep
- Pitfalls: HIGH — all derived from verified codebase analysis or MEDIUM-confidence sources

**Research date:** 2026-05-18
**Valid until:** 2026-06-18 (stable stdlib + winreg patterns; DCU XML format may change with major DCU version upgrade)
