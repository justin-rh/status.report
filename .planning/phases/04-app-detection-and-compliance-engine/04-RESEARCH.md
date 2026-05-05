# Phase 4: App Detection and Compliance Engine - Research

**Researched:** 2026-05-05
**Domain:** Windows registry (winreg), app detection, compliance
**Confidence:** HIGH — all app names and registry paths verified against live registry on a machine running all 7 target apps

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**MERP Detection**
- D-01: MERP is built on PVX Plus Technologies WindX. Registry path is unknown; use filesystem-first detection.
- D-02: Primary check: `Path("C:/PVX Plus Technologies/WindX Plugin-64 2022 Upd 1/WindX").exists()`. If found: `installed=True`, `detection_method='filesystem'`.
- D-03: After filesystem hit, attempt a registry search across all 4 Uninstall key paths for DisplayName or Publisher containing "WindX" or "PVX Plus Technologies" to capture the version string. If registry found: populate `version`; if not: `version=None` is acceptable.
- D-04: If filesystem path does not exist and registry search finds nothing: `installed=False`. No exception raised.

**Microsoft 365 Detection**
- D-05: Detect M365 as a single suite entry — one `AppStatus` entry named `"Microsoft 365"`. No per-app individual entries.
- D-06: Detection target: Click-to-Run suite registry key. Search all 4 Uninstall paths for DisplayName containing `"Microsoft 365"` or `"Microsoft Office"` (Click-to-Run installs typically use one of these). First match wins; `version` from `DisplayVersion`.

**CrowdStrike Falcon Service State**
- D-07: CrowdStrike is detected via the standard 4 Uninstall paths (DisplayName: see Standard Stack — both `"CrowdStrike Windows Sensor"` and `"CrowdStrike Sensor Platform"` resolve to the same agent). Version from `DisplayVersion`.
- D-08: `service_state` is populated from `HKLM\SYSTEM\CurrentControlSet\Services\CSFalconService` Start DWORD. Mapping: `2 → "Automatic"`, `3 → "Manual"`, `4 → "Disabled"`. If the key doesn't exist, `service_state=None`.
- D-09: Service key read uses winreg only — no wmi, no subprocess.

**Detector Code Architecture**
- D-10: Config-driven table: `APP_SPECS` list of dicts in `collectors/windows/apps.py`. Each entry declares `name`, `display_name_keywords`, optional `publisher_keywords`, optional `filesystem_path`, and optional `service_key`.
- D-11: A single `detect_apps(report: AuditReport) -> None` function iterates `APP_SPECS`, runs the unified registry search (all 4 paths) per app, applies filesystem/service fallbacks where flagged. Mutates `report.apps` in place.
- D-12: `collect_all()` in `collectors/__init__.py` calls `collect_apps(report)` after `collect_hardware` and `collect_profiles`.
- D-13: Each app spec entry in `APP_SPECS` is independent. Adding a new app is one dict entry.

**General Detection Rules**
- D-14: All 4 Uninstall paths enumerated for every app, per CLAUDE.md constraint.
- D-15: Every app always produces one `AppStatus` entry appended to `report.apps`, even if `installed=False`.
- D-16: Errors during detection are caught per-app, `AppStatus.error` is set, message appended to `report.collection_errors`. Never raises.
- D-17: `detection_method` values: `'registry'` for standard registry hits, `'filesystem'` for path-based detection (MERP primary).

### Claude's Discretion
- Exact DisplayName keyword matching for NinjaOne (may appear as "NinjaRMM", "NinjaOne", "NinjaRMM Agent")
- Exact registry key iteration pattern (open subkey, read DisplayName value, compare, close — error handling per subkey)
- Whether to de-duplicate when the same app appears in multiple paths — pick highest-privilege match

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| APP-01 | Detect NinjaRMM / NinjaOne agent (registry, all 4 Uninstall paths) | DisplayName `"NinjaRMMAgent"`, Publisher `"NinjaRMM LLC"`, found in HKLM\Wow6432Node only on this machine |
| APP-02 | Detect CrowdStrike Falcon and capture service state | Two DisplayName variants: `"CrowdStrike Windows Sensor"` (Wow6432Node) and `"CrowdStrike Sensor Platform"` (HKLM 64-bit); service via `CSFalconService\Start` DWORD |
| APP-03 | Detect MERP (Master Electronics ERP / WindX) | Filesystem-first at known path; registry fallback for version via publisher/name keywords |
| APP-04 | Detect Microsoft 365 | DisplayName `"Microsoft 365 Apps for enterprise - en-us"` (or similar locale variant); keyword match on `"Microsoft 365"` covers all variants |
| APP-05 | Detect Zoom | `"Zoom Workplace"` in HKCU; `"Zoom Outlook Plugin"` in HKLM (Outlook integration only — not the main client); search all 4 paths |
| APP-06 | Detect Google Chrome | DisplayName `"Google Chrome"`, Publisher `"Google LLC"`, in HKLM 64-bit |
| APP-07 | Detect Claude desktop app | MSIX-packaged; NOT in standard Uninstall keys — requires separate HKCU MSIX package path enumeration |
</phase_requirements>

---

## Summary

Phase 4 implements app detection for 7 target applications by enumerating all 4 Windows Uninstall registry paths via `winreg` and populating `report.apps` with one `AppStatus` per app. All 7 apps are verified against a live registry on a fully provisioned machine running NinjaOne, CrowdStrike, Microsoft 365, Zoom, Chrome, and Claude Desktop.

**Key findings from live registry inspection:**
- NinjaRMM appears exclusively in `HKLM\SOFTWARE\WOW6432Node\...\Uninstall` as `"NinjaRMMAgent"` (not in the 64-bit path)
- CrowdStrike appears under TWO different DisplayName values: `"CrowdStrike Windows Sensor"` in Wow6432Node and `"CrowdStrike Sensor Platform"` in the 64-bit HKLM path — both represent the same agent and must be matched
- Zoom installs per-user as `"Zoom Workplace"` in HKCU; the HKLM entry `"Zoom Outlook Plugin"` is an Outlook add-in, not the main client
- Claude Desktop is an MSIX package and **does NOT register in the standard Uninstall keys** — detection requires reading `HKCU\Software\Classes\Local Settings\...\AppModel\Repository\Packages` or checking `HKCU\Software\Classes\AppX{hash}\Application`
- Microsoft 365 DisplayName includes locale suffix: `"Microsoft 365 Apps for enterprise - en-us"` — keyword match on `"Microsoft 365"` handles all locale variants

**Primary recommendation:** Use keyword substring matching (`keyword in display_name`) rather than exact-string matching for all apps except NinjaRMM (where `"NinjaRMMAgent"` is the literal key name itself, so exact match on DisplayName is safe). For Claude Desktop, add a separate MSIX detection path as a fallback.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Registry enumeration | Collector (Python) | — | Pure winreg reads, no UI, no network |
| Service state query | Collector (Python) | — | winreg read of CSFalconService\Start DWORD |
| Filesystem fallback (MERP) | Collector (Python) | — | pathlib.Path.exists(), no OS API needed |
| MSIX package detection (Claude) | Collector (Python) | — | winreg HKCU AppModel path; no subprocess |
| AuditReport population | Collector (Python) | — | In-place mutation, same pattern as hardware.py |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| winreg | stdlib | Read/enumerate Uninstall registry keys | Project constraint; always available on Windows Python 3.12 |
| pathlib | stdlib | MERP filesystem detection | Zero deps, cross-platform safe for Path.exists() |
| models.AppStatus | project | Data contract for each detected app | Already defined; no schema changes needed |

### Supporting (dev/test only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unittest.mock | stdlib | Patch winreg.OpenKey, EnumKey, QueryValueEx | Unit tests — no real registry needed |
| pytest | 8.x (already installed) | Test runner | Existing project standard |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| winreg | fake-winreg (PyPI) | fake-winreg enables cross-platform testing but adds a non-stdlib dependency; the established project pattern (mock.patch.object on hw_mod.winreg) handles this without a new dep |
| keyword substring | exact DisplayName match | Exact match is brittle (locale suffixes, minor renames across versions); substring preferred except where the key name itself is the GUID/fixed string |

---

## Architecture Patterns

### System Architecture Diagram

```
detect_apps(report: AuditReport)
        |
        v
  for spec in APP_SPECS:
        |
        +--[has filesystem_path?]--> Path(spec['filesystem_path']).exists()
        |       yes: installed=True, detection_method='filesystem'
        |            still search registry for version (D-03)
        |       no:  continue to registry search
        |
        +--[registry search: all 4 UNINSTALL_PATHS]
        |   for each path:
        |     OpenKey(hive, path) --> EnumKey(i) --> OpenKey(subkey) --> QueryValueEx('DisplayName')
        |     if keyword in display_name: version = QueryValueEx('DisplayVersion')
        |                                 installed = True, detection_method = 'registry'
        |                                 break (first match wins; skip remaining paths)
        |
        +--[has service_key? AND installed?]--> read HKLM\SYSTEM\...\Services\{key}\Start
        |   DWORD 2 -> "Automatic", 3 -> "Manual", 4 -> "Disabled"
        |   KeyError/OSError -> service_state = None
        |
        +--[has msix_family?]--> HKCU\...\AppModel\Repository\Packages enumerate
        |   key starts with spec['msix_family']: installed=True, version from key name
        |
        v
  report.apps.append(AppStatus(
      name=spec['name'],
      installed=installed,
      version=version,
      service_state=service_state,
      detection_method=detection_method,
      error=error_msg or None
  ))
```

### Recommended Project Structure

```
collectors/
└── windows/
    ├── hardware.py     # existing
    └── apps.py         # new: APP_SPECS + detect_apps()

tests/
└── test_app_collector.py   # new
```

### Pattern 1: Uninstall Key Enumeration Loop

The established project pattern (from `hardware.py` `_enumerate_profiles`) uses `winreg.EnumKey` with an index counter that breaks on `OSError`. The same pattern applies here:

```python
# Source: collectors/windows/hardware.py _enumerate_profiles (existing codebase)
UNINSTALL_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
]

def _search_uninstall_keys(keywords: list[str]) -> tuple[bool, str | None]:
    """Return (installed, version) for first subkey whose DisplayName contains any keyword."""
    for hive, path in UNINSTALL_PATHS:
        try:
            with winreg.OpenKey(hive, path) as root:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root, i)
                        i += 1
                    except OSError:
                        break  # exhausted
                    try:
                        with winreg.OpenKey(root, subkey_name) as subkey:
                            display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            if any(kw.lower() in display_name.lower() for kw in keywords):
                                try:
                                    version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                                except (FileNotFoundError, OSError):
                                    version = None
                                return True, version
                    except (FileNotFoundError, OSError):
                        continue  # skip unreadable subkey silently
        except (FileNotFoundError, OSError):
            continue  # path not present on this machine
    return False, None
```

### Pattern 2: Service Start DWORD Read

```python
# Source: CONTEXT.md D-08, verified against live registry on this machine
# HKLM\SYSTEM\CurrentControlSet\Services\CSFalconService\Start = REG_DWORD 0x2 (Automatic)
_START_MAP = {2: "Automatic", 3: "Manual", 4: "Disabled"}

def _read_service_start(service_name: str) -> str | None:
    key_path = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            start_val, _ = winreg.QueryValueEx(key, "Start")
            return _START_MAP.get(int(start_val))
    except (FileNotFoundError, OSError, ValueError):
        return None
```

### Pattern 3: Claude MSIX Detection

Claude Desktop is an MSIX/Appx package. It does NOT register in the standard Uninstall key. Two winreg-accessible detection approaches:

**Approach A — AppModel Repository (primary, gives version):**
```python
# Verified on this machine: key exists at:
# HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\
#   AppModel\Repository\Packages\Claude_1.1617.0.0_x64__pzs8sxrjxfjjc
# Key name format: {FamilyName}_{Version}_x64__{PublisherHash}
# Family name prefix: "Claude_"

MSIX_REPO_PATH = (
    r"Software\Classes\Local Settings\Software\Microsoft\Windows"
    r"\CurrentVersion\AppModel\Repository\Packages"
)

def _detect_msix_app(family_prefix: str) -> tuple[bool, str | None]:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, MSIX_REPO_PATH) as root:
            i = 0
            while True:
                try:
                    pkg_key_name = winreg.EnumKey(root, i)
                    i += 1
                except OSError:
                    break
                if pkg_key_name.startswith(family_prefix):
                    # Version is embedded in the key name: FamilyName_VERSION_arch__hash
                    parts = pkg_key_name.split("_")
                    version = parts[1] if len(parts) >= 2 else None
                    return True, version
    except (FileNotFoundError, OSError):
        pass
    return False, None
```

**Approach B — AppX Classes (simpler, no version):**
```python
# HKCU\Software\Classes\AppX{hash}\Application\ApplicationCompany = "Anthropic, PBC"
# Less stable (hash changes across installs) — Approach A preferred
```

### Pattern 4: APP_SPECS Table Structure

```python
# Source: CONTEXT.md D-10, informed by verified registry data
APP_SPECS: list[dict] = [
    {
        "name": "NinjaOne",
        "display_name_keywords": ["NinjaRMMAgent", "NinjaRMM", "NinjaOne"],
        "publisher_keywords": ["NinjaRMM"],
    },
    {
        "name": "CrowdStrike Falcon",
        "display_name_keywords": ["CrowdStrike Windows Sensor", "CrowdStrike Sensor Platform"],
        "service_key": "CSFalconService",
    },
    {
        "name": "MERP",
        "display_name_keywords": ["WindX", "PVX Plus Technologies"],
        "publisher_keywords": ["PVX Plus Technologies"],
        "filesystem_path": r"C:/PVX Plus Technologies/WindX Plugin-64 2022 Upd 1/WindX",
    },
    {
        "name": "Microsoft 365",
        "display_name_keywords": ["Microsoft 365", "Microsoft Office"],
    },
    {
        "name": "Zoom",
        "display_name_keywords": ["Zoom Workplace", "Zoom"],
        # NOTE: "Zoom Outlook Plugin" is an Outlook add-in, not the main client.
        # Keyword "Zoom Workplace" should match first; plain "Zoom" is fallback.
    },
    {
        "name": "Google Chrome",
        "display_name_keywords": ["Google Chrome"],
    },
    {
        "name": "Claude",
        "display_name_keywords": ["Claude"],  # fallback: standard paths unlikely to match
        "msix_family_prefix": "Claude_",      # primary: MSIX AppModel repository
    },
]
```

### Anti-Patterns to Avoid

- **Win32_Product enumeration:** Explicitly prohibited (CLAUDE.md). Triggers MSI consistency checks on all installed apps — causes side effects on production machines.
- **subprocess + reg.exe:** Prohibited (CLAUDE.md winreg-only constraint). Also slow and error-prone.
- **Exact DisplayName match:** Do not use `display_name == "Microsoft 365 Apps for enterprise - en-us"`. The locale suffix (`-en-us`) and edition name (`for enterprise` vs `for Business`) vary. Use keyword substring.
- **First-path-only enumeration:** Must enumerate all 4 paths. NinjaRMM is only in Wow6432Node; CrowdStrike is in both (different names). Stopping at HKLM 64-bit misses both.
- **Assuming Zoom is in HKLM:** Zoom Workplace is a per-user install and registers in HKCU. The HKLM entry "Zoom Outlook Plugin" is only the Outlook integration, not the main client.
- **Assuming Claude is in Uninstall keys:** Claude Desktop MSIX does not appear in any of the 4 standard Uninstall paths. A standard keyword search returns nothing — MSIX detection is required.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-platform registry testing | Custom fake registry | `unittest.mock.patch.object(mod.winreg, ...)` | Established project pattern in test_profile_collector.py; no new deps |
| MSIX version detection | Parse AppData folder names | `winreg` HKCU AppModel repository | Key name encodes version; stable API; no filesystem crawl |
| Service start value text mapping | Custom Start DWORD lookup | Inline `_START_MAP` dict | Trivial; no external library needed |

**Key insight:** The project already has a working mock pattern for winreg (test_profile_collector.py). Follow it exactly — mock `winreg.OpenKey`, `winreg.EnumKey`, `winreg.QueryValueEx` as `patch.object(mod.winreg, ...)`.

---

## Verified App Registry Data

> All entries verified against live registry on this machine (2026-05-05).
> Machine has: NinjaOne 13.0.7346, CrowdStrike 7.35.20709.0, M365 16.0.19822.20180, Zoom 6.7.8, Chrome 147.0.7727.138, Claude 1.1617.0.0

### NinjaOne (APP-01)
| Property | Value |
|----------|-------|
| DisplayName | `"NinjaRMMAgent"` |
| Publisher | `"NinjaRMM LLC"` |
| Hive/Path | HKLM\SOFTWARE\WOW6432Node\...\Uninstall\ |
| Subkey examples | `NinjaRMMAgent 5.8.9154`, `{8B2F821E-B424-4D13-9891-2BC759F8BAA5}` |
| DisplayVersion format | `"13.0.7346"` (semver-like) |
| NOT in | HKLM 64-bit Uninstall (absent on this machine) |

**Keyword recommendation:** `["NinjaRMMAgent", "NinjaRMM", "NinjaOne Agent"]` — use all three to handle rebranding. "NinjaRMM" alone avoids false positives from "NinjaRMM LLC" publisher substring.

**Stale key risk:** Old NinjaRMM installs may leave orphaned subkeys with the same DisplayName but no valid UninstallString. Since we only read DisplayName and DisplayVersion (not execute anything), a stale key still reports correctly as "installed" — the field team must verify if they see ghost detections.

### CrowdStrike Falcon (APP-02)
| Property | Value |
|----------|-------|
| DisplayName (Wow6432Node) | `"CrowdStrike Windows Sensor"` |
| DisplayName (HKLM 64-bit) | `"CrowdStrike Sensor Platform"` |
| Publisher | `"CrowdStrike, Inc."` |
| DisplayVersion | `"7.35.20709.0"` (same in both paths) |
| Additional entries | `"CrowdStrike Firmware Analysis"`, `"CrowdStrike Device Control"` — these are separate components; do not use them for primary detection |
| Service key | `HKLM\SYSTEM\CurrentControlSet\Services\CSFalconService` |
| Service DisplayName | `"CrowdStrike Falcon Sensor Service"` |
| Service Start | `REG_DWORD 0x2` (Automatic) on this machine |

**Keyword recommendation:** `["CrowdStrike Windows Sensor", "CrowdStrike Sensor Platform"]` — both are the main agent. The first match in the 4-path sweep wins and returns the version.

### MERP / WindX (APP-03)
| Property | Value |
|----------|-------|
| Primary detection | Filesystem: `Path("C:/PVX Plus Technologies/WindX Plugin-64 2022 Upd 1/WindX").exists()` |
| Version source | Registry search for `"WindX"` or `"PVX Plus Technologies"` in DisplayName/Publisher |
| Not installed on this machine | MERP not present — cannot verify registry path |

**MERP registry path is unconfirmed.** Per CONTEXT.md blocker, this is acknowledged — filesystem detection is the reliable primary path. Version may be `None` until IT confirms the registry key.

### Microsoft 365 (APP-04)
| Property | Value |
|----------|-------|
| DisplayName (this machine) | `"Microsoft 365 Apps for enterprise - en-us"` |
| Publisher | `"Microsoft Corporation"` |
| Hive/Path | HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall |
| DisplayVersion | `"16.0.19822.20180"` (Click-to-Run build number) |
| Locale variants | `-en-us`, `-es-es`, `-fr-fr` etc. — keyword match handles all |
| Edition variants | `for enterprise`, `for Business`, `for Education` — keyword match handles all |

**Keyword recommendation:** `["Microsoft 365", "Microsoft Office"]` per D-06. "Microsoft 365" alone matches all Click-to-Run editions. "Microsoft Office" catches older perpetual licenses if IT ever encounters a non-C2R install.

### Zoom (APP-05)
| Property | Value |
|----------|-------|
| DisplayName (main client) | `"Zoom Workplace"` |
| Publisher | `"Zoom Communications, Inc."` |
| Hive/Path | HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall |
| DisplayVersion | `"6.7.8 (32670)"` (version + build in parens) |
| SEPARATE entry | `"Zoom Outlook Plugin"` in HKLM Wow6432Node — NOT the main client |

**Critical:** Zoom is a HKCU per-user installation. The 4-path sweep covers HKCU, so detection works. But running as SYSTEM (e.g., from a service context) would not see HKCU for the logged-in user. The tool runs interactively from USB, so the current user's HKCU is the correct context.

**Keyword recommendation:** `["Zoom Workplace"]` as the primary keyword. If a machine has an older Zoom install (pre-Workplace rebranding, when it was just "Zoom"), add `"Zoom"` as a secondary keyword — but only match it if Publisher contains "Zoom" to avoid false positives from "Zoom Outlook Plugin".

### Google Chrome (APP-06)
| Property | Value |
|----------|-------|
| DisplayName | `"Google Chrome"` |
| Publisher | `"Google LLC"` |
| Hive/Path | HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall |
| DisplayVersion | `"147.0.7727.138"` (4-part version) |

**Keyword recommendation:** `["Google Chrome"]`. Enterprise per-machine install is in HKLM. Per-user installs would be in HKCU — covered by the 4-path sweep.

### Claude Desktop (APP-07)
| Property | Value |
|----------|-------|
| Installation type | MSIX package |
| Package family | `Claude_pzs8sxrjxfjjc` |
| Uninstall key present? | NO — not in any of the 4 standard Uninstall paths |
| MSIX AppModel key | `HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages` |
| Key name format | `Claude_{VERSION}_x64__pzs8sxrjxfjjc` |
| DisplayName in MSIX key | `"Claude"` |
| Version on this machine | `1.1617.0.0` |

**Detection strategy:** Two-phase approach:
1. Try MSIX AppModel repository path (primary, gives version) — enumerate keys starting with `"Claude_"`
2. If MSIX path inaccessible, fall back to keyword search in standard 4 paths for `"Claude"` DisplayName (future-proof if Anthropic ships a non-MSIX version)

---

## Common Pitfalls

### Pitfall 1: CrowdStrike DisplayName is Not "CrowdStrike Falcon"
**What goes wrong:** Code searches for `"CrowdStrike Falcon"` and finds nothing, reporting CrowdStrike as Missing on machines where it is installed.
**Why it happens:** The CONTEXT.md D-07 says DisplayName is `"CrowdStrike Falcon"` but the live registry shows `"CrowdStrike Windows Sensor"` (Wow6432Node) and `"CrowdStrike Sensor Platform"` (HKLM 64-bit). Neither matches `"CrowdStrike Falcon"`.
**How to avoid:** Use keywords `["CrowdStrike Windows Sensor", "CrowdStrike Sensor Platform"]`. Both strings contain `"CrowdStrike"` as a prefix — matching on `"CrowdStrike"` alone would also match `"CrowdStrike Firmware Analysis"` and `"CrowdStrike Device Control"`, which are separate components.
**Warning signs:** Test returns `installed=False` for CrowdStrike on a machine with CSFalconService running.

### Pitfall 2: Zoom Workplace vs Zoom Outlook Plugin
**What goes wrong:** Detection matches "Zoom Outlook Plugin" in HKLM and reports Zoom as installed — but the user doesn't have the Zoom desktop app, just the Outlook add-in.
**Why it happens:** `"Zoom"` as a keyword substring matches both entries.
**How to avoid:** Prefer keyword `"Zoom Workplace"` for the primary match. Add `"Zoom"` with publisher constraint as fallback. Do not treat "Zoom Outlook Plugin" as the main client.
**Warning signs:** `AppStatus.name="Zoom"` shows `installed=True` but user cannot launch a Zoom meeting.

### Pitfall 3: Claude Desktop Is Not in Uninstall Keys
**What goes wrong:** Standard 4-path sweep finds nothing for Claude, reports `installed=False` on machines where Claude Desktop is installed.
**Why it happens:** Claude Desktop is distributed as an MSIX package. MSIX apps are NOT registered in `...\Uninstall`. The package lives in `C:\Program Files\WindowsApps\` and its registry presence is in the AppModel path.
**How to avoid:** Add MSIX detection as a primary path for Claude, with standard 4-path sweep as fallback.
**Warning signs:** `installed=False` for Claude even though `get-appxpackage -name '*claude*'` shows it installed.

### Pitfall 4: NinjaRMM Stale/Orphaned Registry Entries
**What goes wrong:** A machine that had NinjaRMM but was manually uninstalled (without going through Programs & Features) may still have a registry subkey with the DisplayName `"NinjaRMMAgent"` but no running agent.
**Why it happens:** Incomplete uninstalls leave Uninstall key orphans. Reading DisplayName still returns the string.
**How to avoid:** Per D-14/D-15, the detector reports what the registry says. A stale key reports `installed=True`. This is expected behavior — the tool reads the registry, not the running process. Document this in tool output if needed. Do NOT check for running processes (would require subprocess/wmi).
**Warning signs:** NinjaRMM shows installed but machine is known to be off-boarded.

### Pitfall 5: De-duplication Across Registry Paths
**What goes wrong:** NinjaRMM has two entries in Wow6432Node (both with the same DisplayName, different GUIDs). Without de-duplication, the detector finds both and could append two hits before `break`.
**Why it happens:** MSI installs sometimes register multiple GUID-based subkeys alongside a named subkey.
**How to avoid:** The `break` after first match per app (first-match-wins pattern) handles this correctly. The loop breaks on the first matching subkey in the first matching path. No duplicate `AppStatus` entries.

### Pitfall 6: QueryValueEx Raises FileNotFoundError vs OSError
**What goes wrong:** Code catches only `OSError` when reading `DisplayVersion` but not `FileNotFoundError`. On some installs, `DisplayVersion` value is absent — `FileNotFoundError` is raised.
**Why it happens:** `FileNotFoundError` is a subclass of `OSError` in Python 3, so `except OSError` catches both. But explicitly catching `FileNotFoundError` makes intent clear and matches the pattern in `hardware.py`.
**How to avoid:** Always catch `(FileNotFoundError, OSError)` when reading optional values like `DisplayVersion`.

### Pitfall 7: M365 Has No Entry on Non-C2R Installs
**What goes wrong:** On older machines with MSI-based Office 2019 or perpetual Office 2021, the DisplayName is `"Microsoft Office Professional Plus 2019"` — neither `"Microsoft 365"` nor `"Microsoft Office"` substring matches.
**Why it happens:** MSI-based installs use a different product name. The keyword `"Microsoft Office"` catches most but not all variants.
**How to avoid:** Per D-06, this is accepted behavior. The tool is auditing for Microsoft 365 subscription installs specifically. MSI Office 2019/2021 would show `installed=False`. Document this limitation — it is within scope.

---

## Code Examples

### Complete winreg iteration (reference from existing codebase)

```python
# Source: collectors/windows/hardware.py _enumerate_profiles — established project pattern
with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, PROFILE_LIST_KEY) as key:
    i = 0
    while True:
        try:
            sid = winreg.EnumKey(key, i)
            i += 1
        except OSError:
            break  # EnumKey raises OSError when index exhausted — normal end
        try:
            with winreg.OpenKey(key, sid) as sid_key:
                path, _ = winreg.QueryValueEx(sid_key, "ProfileImagePath")
                # ... process path
        except (FileNotFoundError, OSError):
            continue  # Skip unreadable SID subkey silently
```

### Mock pattern for winreg tests (reference from existing codebase)

```python
# Source: tests/test_profile_collector.py — established project mock pattern
from unittest.mock import MagicMock, patch
import collectors.windows.apps as apps_mod

def test_detect_ninja_installed():
    all_subkeys = ["NinjaRMMAgent 5.8.9154"]

    def enum_fn(key, index):
        if index < len(all_subkeys):
            return all_subkeys[index]
        raise OSError("exhausted")

    fake_ctx = MagicMock()
    fake_ctx.__enter__ = MagicMock(return_value=fake_ctx)
    fake_ctx.__exit__ = MagicMock(return_value=False)

    query_responses = {
        "DisplayName": ("NinjaRMMAgent", 1),
        "DisplayVersion": ("13.0.7346", 1),
    }

    def query_fn(key, value_name):
        if value_name in query_responses:
            return query_responses[value_name]
        raise FileNotFoundError(f"no value {value_name}")

    with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=enum_fn), \
         patch.object(apps_mod.winreg, "QueryValueEx", side_effect=query_fn):
        report = make_report()
        apps_mod.detect_apps(report)

    ninja = next(a for a in report.apps if a.name == "NinjaOne")
    assert ninja.installed is True
    assert ninja.version == "13.0.7346"
    assert ninja.detection_method == "registry"
```

### Service Start DWORD read with verified values

```python
# Source: live registry verification (2026-05-05)
# HKLM\SYSTEM\CurrentControlSet\Services\CSFalconService\Start = REG_DWORD 0x2

_START_MAP = {2: "Automatic", 3: "Manual", 4: "Disabled"}

def _read_service_start(service_name: str) -> str | None:
    try:
        key_path = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            val, _ = winreg.QueryValueEx(key, "Start")
            return _START_MAP.get(int(val))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Win32_Product WMI | winreg Uninstall keys | Explicitly prohibited in CLAUDE.md | Win32_Product triggers MSI consistency checks on every installed app — never use |
| subprocess + reg.exe | winreg stdlib | Project constraint | subprocess adds overhead; winreg is direct and testable |
| Fixed DisplayName match | Keyword substring match | This phase | Locale suffixes and edition names make exact matching fragile |

**App naming changes:**
- NinjaRMM → NinjaOne (company rebranded ~2023): registry still shows `"NinjaRMMAgent"` DisplayName on this machine with agent 13.0 — keywords should cover both names
- Zoom → Zoom Workplace (renamed 2024): registry shows `"Zoom Workplace"` for current installs; older installs may show `"Zoom"` — cover both

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | MERP (WindX) registry path is unknown — filesystem detection used as primary | Standard Stack, App Data | Low risk — filesystem path confirmed in D-02; registry version read is optional per D-03 |
| A2 | Claude MSIX package family prefix is stable (`"Claude_"`) across future versions | Code Examples | Low risk — MSIX family name is set at publish time and does not change across updates |
| A3 | Zoom Workplace DisplayName remains `"Zoom Workplace"` (not reverted to `"Zoom"`) on current enterprise installs | App Data | Medium risk — if Zoom renames again, keyword `"Zoom"` fallback catches it but may also match Zoom Outlook Plugin |
| A4 | NinjaRMM agent still registers in WOW6432Node on new installs (not yet migrated to 64-bit) | App Data | Low risk — observed on current agent version 13.0; unlikely to silently move to 64-bit path |

---

## Open Questions

1. **MERP registry path (known blocker)**
   - What we know: Filesystem path confirmed per D-02. Registry path unknown.
   - What's unclear: Whether any standard Uninstall key exists for WindX, and what its exact DisplayName/Publisher values are.
   - Recommendation: Implement filesystem-first per D-02, registry search by publisher keyword per D-03. Mark as explicitly deferred to IT validation per STATE.md blocker entry.

2. **Claude Desktop: MSIX only vs dual-distribution**
   - What we know: Current distribution is MSIX (verified). Anthropic also distributes via `install.ps1` which installs the Claude Code CLI (Node.js binary), not the Claude Desktop app.
   - What's unclear: Whether a future non-MSIX native installer exists or will exist for Claude Desktop.
   - Recommendation: Primary MSIX detection + standard 4-path sweep fallback covers both scenarios at minimal cost.

3. **Zoom per-user context when running as SYSTEM**
   - What we know: Zoom Workplace is in HKCU of the interactive user. The tool runs interactively from USB as the current user.
   - What's unclear: If the tool is ever invoked from a scheduled task or elevated context, HKCU may point to SYSTEM's hive.
   - Recommendation: Non-issue for this phase — tool always runs as the logged-in user per USB execution model. Document as Phase 5 consideration.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 4 is pure code and no external tools, services, or non-stdlib packages are required. `winreg` is Python stdlib, always available on Windows 3.12.

---

## Security Domain

> security_enforcement not explicitly set to false — including section.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Keywords are hardcoded strings — no user input |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Registry read returning attacker-controlled values | Tampering | winreg is read-only here; all values treated as strings, never executed |
| Path traversal via MERP filesystem path | Tampering | Path is hardcoded string in APP_SPECS; `Path.exists()` does not execute the path |
| Exception leakage exposing system info | Info Disclosure | All exceptions caught per-app; only message string appended to `collection_errors` |

**No novel security concerns.** The collector reads from the registry and filesystem but never writes, never executes, and never sends data off-machine. All registry reads are sandboxed within the four standard Uninstall paths plus two well-known service/MSIX paths.

---

## Sources

### Primary (HIGH confidence — verified on live machine)
- Live registry inspection via PowerShell Get-ItemProperty on this machine (2026-05-05) — all 7 app DisplayName values, hive locations, and version formats verified
- `collectors/windows/hardware.py` — reference implementation for EnumKey/QueryValueEx pattern
- `tests/test_profile_collector.py` — reference for mock.patch.object(mod.winreg, ...) test pattern
- `models.py` — AppStatus data contract (no changes needed)
- `04-CONTEXT.md` — locked decisions D-01 through D-17

### Secondary (MEDIUM confidence)
- [BU CrowdStrike Removal](https://www.bu.edu/tech/services/cccs/desktop/device-security/endpoint-protection/endpoint-protection-crowdstrike-removal/) — confirmed DisplayName "CrowdStrike Windows Sensor" in Add/Remove Programs
- [Automox CrowdStrike worklet](https://www.automox.com/worklets/crowdstrike-falcon-sensor-service) — confirmed CSFalconService service name
- [imabdk Uninstall-EverythingZoom.ps1](https://github.com/imabdk/Powershell/blob/master/Uninstall-EverythingZoom.ps1) — confirmed Zoom uses HKCU for per-user installs, Publisher "Zoom*"
- [Automox Zoom install worklet](https://www.automox.com/worklets/install-zoom-windows) — confirmed per-machine installs use HKLM Wow6432Node

### Tertiary (LOW confidence — training knowledge, backed by live verification)
- NinjaRMM registry location: training knowledge confirmed by live registry observation
- M365 Click-to-Run registry location: training knowledge confirmed by live registry observation

---

## Metadata

**Confidence breakdown:**
- App DisplayNames and registry paths: HIGH — verified against live registry
- EnumKey/QueryValueEx iteration pattern: HIGH — mirrors existing codebase pattern
- MSIX Claude detection: HIGH — verified registry path on this machine
- MERP detection: MEDIUM — filesystem path confirmed; registry path unknown (IT blocker)
- Test mock strategy: HIGH — mirrors existing test_profile_collector.py pattern

**Research date:** 2026-05-05
**Valid until:** 2026-08-05 (30 days for display names; MSIX family name is stable until Anthropic changes it)
