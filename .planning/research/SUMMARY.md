# Project Research Summary

**Project:** StatusReport
**Domain:** Windows IT audit executable - USB-portable, read-only PC inventory with D&D/RPG-themed HTML output
**Researched:** 2026-05-04
**Confidence:** HIGH

## Executive Summary

StatusReport is a self-contained Windows executable that runs from a USB flash drive, collects PC inventory data without installation or admin rights, and produces a D&D/RPG-styled HTML character sheet alongside a machine-readable JSON audit log - both written to the USB drive, leaving no artifacts on the host machine. Experts build tools of this type with Python + PyInstaller, using WMI for hardware detail and the Windows Registry for installed software detection. The key architectural insight is that the tool must never raise an exception to the user: every data collection call is wrapped in an error envelope that degrades gracefully to "unavailable" in the output, so the audit always completes even when running without elevation or on machines with partial WMI availability.

The recommended stack is Python 3.12 + psutil 6.x + wmi 1.5.1 + winreg (stdlib) + Jinja2 3.1.x, packaged with PyInstaller 6.x in --onedir mode. The --onedir decision is non-negotiable for this project: PyInstaller --onefile mode self-extracts to %TEMP% at runtime, which is behaviorally identical to malware dropper patterns and will be quarantined by CrowdStrike Falcon - the EDR installed on every target machine. The --onedir layout avoids this entirely, stays under the 50 MB size budget (~30-40 MB estimated), and is fully acceptable for USB distribution.

The primary product differentiator is the RPG theming layer, which maps IT data to D&D concepts: device type becomes Character Class, department becomes Guild, city becomes Realm, CPU cores drive Strength score, RAM drives Constitution, disk space is displayed as an HP bar. Three open questions must be resolved before or during implementation: (1) the exact registry path for MERP (the internal ERP), (2) whether CrowdStrike Falcon tenant policy blocks even --onedir binaries (requiring code-signing or a Nuitka fallback), and (3) whether code-signing budget is available for v1.

---

## Key Findings

### Recommended Stack

Python 3.12 is the correct runtime: it has the best current PyInstaller 6.x support, psutil 5.x has known Windows issues on 3.12 so psutil 6.x is required, and wmi 1.5.1 needs pywin32 >= 306 (auto-installed as a dependency). Do not use Python 3.13 until PyInstaller 7.x stabilizes hooks. Do not use a conda environment for the build - conda base pulls in hundreds of unrelated packages, ballooning the executable to 100-300 MB.

Software detection must use the Windows Registry exclusively for enumeration. WMI Win32_Product is explicitly prohibited: it triggers an MSI reconfiguration consistency check on every installed MSI package, taking 30-120 seconds per run and potentially re-enabling services IT deliberately disabled - a show-stopping side effect for a tool that must be read-only and fast. Registry reads via winreg are passive, require no elevation, and complete in milliseconds.

**Core technologies:**
- Python 3.12.x: Runtime - best PyInstaller 6.x compatibility; stdlib covers hostname, registry, OS info
- psutil 6.x: CPU, RAM, disk metrics - standard-user safe, 10-20x faster than WMI for same data, raises AccessDenied gracefully
- wmi 1.5.1: Hardware detail (CPU model, BIOS, OS build, services) - use only for hardware WMI classes, never Win32_Product
- winreg (stdlib): Installed software detection - no dependency, reads all four Uninstall key paths without elevation
- Jinja2 3.1.x: HTML template rendering - use importlib.resources to load the template; do NOT use FileSystemLoader with PyInstaller
- PyInstaller 6.x (--onedir): Packaging - onedir avoids the %TEMP% extraction pattern that triggers CrowdStrike behavioral detection
- platform / socket / ctypes (stdlib): OS version, hostname, elevation detection - zero dependency, standard-user safe

**What NOT to use (hard rules):**
- wmic via subprocess: Removed in Windows 11 24H2+ and Windows Server 2025
- Win32_Product WMI class: Triggers MSI reconfiguration, violates read-only contract
- PyInstaller --onefile: Quarantined by CrowdStrike Falcon on every target machine
- Conda as build environment: Executable size blows past 50 MB budget
- os.getcwd() for output path: Resolves to user home directory, not the USB drive

### Expected Features

**Must have (table stakes) - all in v1:**
- Hostname decode: converts naming convention (e.g., PHX-INV-003) to city + device type + department + station number
- Hardware stats: OS version + build, CPU model, RAM amount, disk capacity + free space, logged-in user
- App detection for 8 targets: NinjaRMM, M365 (Word/Excel/Outlook/Teams/OneDrive), Intune, CrowdStrike Falcon, Zoom, Chrome, Claude Desktop, MERP
- App presence + version from registry DisplayVersion field
- Compliance gaps list: explicit Missing Equipment section showing what needs to be installed
- D&D/RPG themed HTML character sheet - the core differentiator
- JSON audit log written to USB directory
- PyInstaller --onedir executable under 50 MB
- Graceful Unknown Adventurer fallback for hostnames that do not match the naming convention

**Should have (differentiators) - v1 where straightforward, v1.x otherwise:**
- Color-coded pass/fail/missing status per app (CSS only - trivial once detection is working)
- Elevation-aware output: notes which checks were limited by running as standard user
- Multiple detection methods per app: registry primary, file-system secondary, service check tertiary
- Audit timestamp + machine fingerprint in both HTML and JSON
- Auto-open HTML output in default browser after generation (os.startfile)

**Defer (v2+):**
- Local user profiles list - benefits from elevation; defer until IT staff request it
- BitLocker status - requires elevation on most machines
- Optional JSON upload to central log collector - breaks offline constraint
- Mac support - out of scope v1; Python abstraction layer makes it feasible later
- Remote scan mode - different product entirely

### RPG Theming Data Mapping

| IT Data | RPG Display | Label |
|---------|-------------|-------|
| Hostname (decoded) | Character Name + Class | PHX-INV-003 = Phoenix Inventory Workstation 3 |
| Device type | Character Class | WH=Warehouse WS, UL=User Laptop, DL=Dept Laptop, P3=P3 |
| Department code | Guild / Faction | Guild: Inventory |
| City code (21 codes) | Realm / Origin | Realm: Phoenix |
| Station number | Level / Rank | Level 3 |
| CPU model + core count | Strength (STR) | STR 16 - Intel Core i7 (8 cores) |
| RAM amount | Constitution (CON) | CON 14 - 16 GB |
| Disk free / total | HP Bar | HP 247/512 GB (visual bar showing fullness) |
| OS version + build | Era / Age | Era: Windows 11 (Build 22631) |
| Logged-in user | Bound Hero | Bound to: jsmith |
| NinjaRMM present | Guild Contract | Green: Enrolled in NinjaOne / Red: UNREGISTERED |
| CrowdStrike Falcon | Armor / Defense | Armor: CrowdStrike v7.x Active / UNARMORED |
| Intune / Company Portal | Realm Registry | Registered with Intune / Unmanaged |
| M365 apps | Spellbook / Abilities | List of installed apps as ability slots |
| MERP (ERP) | Ancient Tome | Ancient Tome: MERP - Installed |
| Claude Desktop | Arcane Intelligence | Easter egg framing |
| Missing required app | Missing Equipment | Red banner: MISSING: CrowdStrike Falcon - Critical Gap |
| Overall compliance | Quest Status | QUEST COMPLETE vs QUEST INCOMPLETE - 2 gaps |
| Audit timestamp | Chronicle Date | Chronicle: 2026-05-04 14:32 UTC |

HTML layout: Header (name/class/realm/guild/level) then Middle-left Core Stats block (STR/CON/HP bar/Era) then Middle-right Equipment/Abilities (app slots with pass/fail) then Bottom Missing Equipment warnings then Footer (Chronicle + tool version).

### Architecture Approach

The architecture follows a strict layered pipeline: Entry Point - Collector Layer - Parser - AuditReport dataclass - Render Layer - Output Layer. No layer bypasses this pipeline. All Windows-specific code is isolated inside collectors/windows/ behind an abstract BaseCollector interface - the renderer and writers are completely platform-agnostic. The AuditReport dataclass is the single data contract; raw WMI objects and registry handles never cross layer boundaries. Every collector method returns a CollectionResult envelope (value + optional error string) rather than raising exceptions, ensuring the audit always produces output even when individual checks fail.

**Major components:**
1. models.py: AuditReport, ParsedHostname, AppStatus, CollectionResult dataclasses; the data contract all layers share
2. parsers/name_parser.py: Pure function; hostname string to ParsedHostname; no Windows APIs; fully unit-testable on any machine
3. collectors/windows/sysinfo.py: WMI + psutil + winreg system facts; returns CollectionResult values; catches all exceptions internally
4. collectors/windows/appdetector.py: Registry enumeration across all four Uninstall key paths + filesystem fallbacks; never uses Win32_Product
5. renderer/html_renderer.py: Loads Jinja2 template via importlib.resources; renders AuditReport to HTML string
6. renderer/templates/character_sheet.html: D&D-styled Jinja2 template; bundled via --add-data in PyInstaller spec
7. writers/html_writer.py + writers/json_logger.py: Write to USB directory; all file opens specify encoding=utf-8
8. utils/path_helper.py: Resolves output dir from sys.executable when sys.frozen is set; never uses os.getcwd()

### Critical Pitfalls

1. CrowdStrike Falcon quarantines the binary - Use --onedir mode exclusively. The --onefile extract-to-%TEMP% pattern is behaviorally identical to malware droppers and will be blocked. Test on a CrowdStrike-enrolled machine before any distribution. Fallback: Nuitka (compiles to native C, far fewer AV flags) if onedir is also blocked by tenant policy.

2. Win32_Product triggers MSI reconfiguration - Never use this WMI class for software detection. Use the four registry Uninstall key paths instead. This pitfall alone causes 30-120 seconds of runtime per run and can re-enable services IT deliberately disabled. Enforce with a pre-ship grep check returning zero results.

3. os.getcwd() writes output to the host PC, not the USB - Always derive the output path from Path(sys.executable).parent when sys.frozen is set. Test by launching from cmd.exe in C:\ - output must appear on the USB drive, not on the host machine's filesystem.

4. Single registry hive misses 32-bit and per-user installs - Enumerate all four paths: HKLM 64-bit, HKLM Wow6432Node, HKCU 64-bit, HKCU Wow6432Node. Use KEY_READ | KEY_WOW64_64KEY flag when opening HKLM paths from a 64-bit Python process. Deduplicate by DisplayName + DisplayVersion after merging all four.

5. International encoding crashes on Arabic/Chinese/Dutch locales - Master Electronics operates in Jordan (AMM), Netherlands (AMS), Malaysia (KUL), Hong Kong (HKG). Use GetComputerNameW via ctypes for hostname retrieval (not socket.gethostname()). Set PYTHONUTF8=1 in the PyInstaller build. Always open files with encoding=utf-8. Include meta charset=UTF-8 as the first element in HTML head.

---

## Implications for Roadmap

Based on combined research, the natural build order follows data dependencies: define the contract first, then build the parts that populate it, then render and package. Five phases are suggested.

### Phase 1: Data Models and Hostname Parser

**Rationale:** Everything else imports from models.py. The AuditReport, ParsedHostname, AppStatus, and CollectionResult dataclasses are the data contract for all subsequent layers. The NameParser is the riskiest domain logic (the naming convention is internal and underdocumented), is purely testable without Windows APIs, and must be proven correct before hardware collection is built against it.

**Delivers:** models.py, parsers/name_parser.py, unit tests for all 4 device types and all 21 city codes, project scaffolding

**Addresses:** Hostname decode feature, Unknown Adventurer fallback, RPG Class/Guild/Realm/Level display fields

**Avoids:** Discovering naming convention logic is wrong after the renderer is built around it

**Research flag:** NEEDS VALIDATION - Complete city code list, department code list, and hostname regex must be confirmed with IT/Edgar before building the parser. Validate against real production hostnames from multiple offices.

---

### Phase 2: Hardware Collectors and Core Data Flow

**Rationale:** Once models exist, build the minimal collector pipeline end-to-end. Start with platform stdlib before WMI so there is a working data flow to test against. Establish PathHelper and the CollectionResult error envelope pattern here so all subsequent collection code follows the same discipline.

**Delivers:** collectors/windows/sysinfo.py (platform + WMI hardware), utils/path_helper.py, utils/error_handler.py, a console-printed AuditReport confirming end-to-end data flow, elevation detection

**Uses:** psutil 6.x (disk), wmi 1.5.1 (CPU model, RAM, OS build), platform/socket/ctypes stdlib

**Implements:** Collector Layer, CollectionResult error envelope, PathHelper (sys.executable-based output path)

**Avoids:** os.getcwd() output path pitfall (established once here, used everywhere); encoding pitfall (use GetComputerNameW via ctypes from day one)

**Research flag:** Standard patterns - WMI hardware queries are well-documented and stable. No deeper research needed.

---

### Phase 3: RPG-Themed HTML Renderer

**Rationale:** The HTML character sheet is the highest-visibility deliverable and the core differentiator. Building it with mock data decouples visual design from collection complexity. This is also the right time to get feedback on the RPG mapping before app detection is built, since the Equipment section drives what app detection needs to return.

**Delivers:** renderer/templates/character_sheet.html (full D&D layout with inline CSS), renderer/html_renderer.py (Jinja2 via importlib.resources), a visually complete character sheet rendered from mock AuditReport data

**Uses:** Jinja2 3.1.x loaded via importlib.resources; all RPG theming mappings from FEATURES.md

**Implements:** Full HTML layout (Header/Stats/Equipment/Gaps/Footer), HP bar for disk space, color-coded app status badges, Quest Status summary

**Avoids:** Template-as-Python-string anti-pattern; FileSystemLoader PyInstaller incompatibility; XSS from unescaped hostname data (Jinja2 autoescaping enabled)

**Research flag:** Standard patterns - Jinja2 + importlib.resources + PyInstaller --add-data is a known-good pattern. Needs visual design iteration, not research.

---

### Phase 4: App Detection and Compliance Engine

**Rationale:** App detection is the most Windows-specific and error-prone piece. Building it after the renderer is proven isolates failures to the detector module. All four registry paths must be enumerated from the first line. The tiered detection strategy (registry + file/service confirmation for the 5 priority apps) must be designed upfront.

**Delivers:** collectors/windows/appdetector.py covering all 8 target apps across all four registry paths, filesystem fallback checks, service state checks for NinjaRMM and CrowdStrike, AppStatus list in AuditReport, compliance gap calculation

**Uses:** winreg stdlib (all four Uninstall paths with WOW64 flags), os.path.exists for filesystem fallbacks, subprocess sc query for service state fallback

**Implements:** Detection for NinjaRMM, M365, Intune, CrowdStrike, Zoom, Chrome, Claude Desktop, MERP; tiered confidence model for top 5 apps; Missing Equipment gap list

**Avoids:** Win32_Product (explicit prohibition, grep enforced); single registry hive; stale registry false positives (file/service secondary confirmation)

**Research flag:** NEEDS CONFIRMATION - MERP registry path is unknown; must be confirmed with IT before this phase can complete. CrowdStrike detection path needs validation on an enrolled machine. M365 ClickToRun individual app detection needs testing on a provisioned machine.

---

### Phase 5: JSON Logger, Packaging, and Distribution

**Rationale:** Wire up JSON output and package everything once the data pipeline is proven end-to-end. PyInstaller packaging is last because the .spec file depends on all modules being stable.

**Delivers:** writers/json_logger.py (AuditReport to JSON with ensure_ascii=False), PyInstaller --onedir build, .spec file with --add-data for template, verified USB output path, auto-open HTML via os.startfile, VirusTotal scan result, runbook for SmartScreen bypass

**Uses:** PyInstaller 6.x, pyinstaller-hooks-contrib (bundled with PyInstaller 6.x), clean venv build (not conda)

**Implements:** Full distribution artifact; USB output for both HTML and JSON; graceful write-failure handling with user-facing error message

**Avoids:** --onefile mode; conda build environment; missing encoding=utf-8 on file opens; silent write failures

**Research flag:** NEEDS VALIDATION ON ENROLLED MACHINE - If --onedir is blocked by CrowdStrike tenant policy, the fallback to Nuitka or code-signing submission executes in this phase. Code-signing budget decision must be made before distribution begins.

---

### Phase Ordering Rationale

- Models before collectors: All collectors import CollectionResult; the renderer imports AuditReport; starting here prevents rework when the data shape changes.
- Hardware before apps: WMI hardware collection is better documented and more stable than registry app detection with locale and bitness edge cases.
- Renderer before full app detection: Gets visual feedback early; validates the RPG mapping before app detection drives the Equipment section design.
- App detection late: Most Windows-specific, most error-prone, most dependent on external validation (MERP path). Isolated phase limits blast radius when it needs iteration.
- Packaging last: Every packaging decision (template paths, frozen mode, output paths) depends on all source modules being stable.

### Research Flags

**Needs deeper research or external validation:**
- Phase 1 (Name Parser): Full city code list (21 codes), department codes, and hostname regex must be confirmed with IT/Edgar. Validate against real production hostnames from multiple offices including international locations.
- Phase 4 (App Detection - MERP): MERP registry key path is unknown. Must be confirmed with IT before the appdetector can be completed. This is the single largest open question in the project.
- Phase 5 (Packaging - CrowdStrike): Test --onedir binary on a CrowdStrike-enrolled machine early in the phase. If blocked, code-signing (EV certificate ~$300/year) or Nuitka fallback has budget and timeline implications that must be resolved.

**Standard patterns (skip deeper research):**
- Phase 2 (Hardware Collectors): WMI hardware queries (Win32_ComputerSystem, Win32_Processor, Win32_OperatingSystem) are stable and thoroughly documented.
- Phase 3 (HTML Renderer): Jinja2 + importlib.resources + PyInstaller --add-data is a known-good pattern documented in architecture research.
- Phase 5 (JSON Logger): json.dumps with ensure_ascii=False, indent=2 and encoding=utf-8 on file open is trivial.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core stack verified against official PyPI pages and PyInstaller docs. Version compatibility matrix confirmed. AV mitigation based on confirmed CrowdStrike behavior from community post-mortems and PyInstaller issue tracker. |
| Features | HIGH | Feature list derived directly from PROJECT.md requirements plus domain research confirming best practices. RPG mapping fully specified. Anti-features grounded in documented pitfalls and project constraints. |
| Architecture | HIGH | Layered pipeline is standard for this class of tool. CollectionResult envelope and importlib.resources loading are validated PyInstaller patterns. Component boundaries are clean and proven in similar tools. |
| Pitfalls | HIGH | All critical pitfalls verified against official docs (PyInstaller runtime docs, Microsoft TechCommunity Win32_Product warning, Registry Uninstall key docs) or confirmed community post-mortems. No speculative pitfalls included. |

**Overall confidence: HIGH**

### Gaps to Address

- MERP registry path: Unknown. Must be confirmed with IT before Phase 4 begins. If MERP is a silently-deployed XCOPY install with no registry key, detection requires a filesystem-only approach. Action: request MERP install path and any known service name from IT contact before roadmap execution begins.

- CrowdStrike tenant policy for --onedir: The research confirms --onefile will be blocked. Whether --onedir passes depends on Master Electronics' specific Falcon policy configuration. Action: test a minimal --onedir exe on an enrolled machine at the start of Phase 5, before building the full package.

- Code-signing decision: EV certificate (~$300/year) eliminates SmartScreen dialogs and reduces CrowdStrike friction. OV certificate reduces SmartScreen friction but does not eliminate it for zero-reputation binaries. No certificate means documenting the More info -> Run anyway bypass in the IT staff runbook. This is a business decision with budget implications. Action: confirm with stakeholder before Phase 5 begins.

- Hostname naming convention completeness: 4 device types and 21 city codes are assumed but the exact regex and all valid values must be validated against real production hostnames. Action: obtain sample hostnames from IT across multiple offices (including AMM, AMS, KUL, HKG) before Phase 1 parser development.

- M365 individual app detection: M365 ClickToRun installs apps under a shared configuration key rather than individual Uninstall keys. Detection via HKLM\SOFTWARE\Microsoft\Office\ClickToRun\Configuration plus file presence in the Office16 directory needs verification on an actual M365 machine. Action: test in Phase 4 against a provisioned machine before finalizing the detection logic.

---

## Sources

### Primary (HIGH confidence)
- Python docs: winreg (https://docs.python.org/3/library/winreg.html) - registry access, WOW64 flags
- Python docs: importlib.resources (https://docs.python.org/3/library/importlib.resources.html) - template bundling with PyInstaller
- Python docs: platform (https://docs.python.org/3/library/platform.html) - OS version retrieval
- PyInstaller docs: usage (https://pyinstaller.org/en/stable/usage.html) - onedir vs onefile behavior
- PyInstaller docs: runtime information (https://pyinstaller.org/en/stable/runtime-information.html) - sys.executable, sys.frozen
- PyPI: wmi 1.5.1 (https://pypi.org/project/WMI/) - current version confirmed
- PyPI: psutil 6.x (https://pypi.org/project/psutil/) - standard-user safety confirmed
- PyPI: PyInstaller 6.x (https://pypi.org/project/pyinstaller/) - current stable confirmed
- Microsoft TechCommunity: Win32_Product in GPO (https://techcommunity.microsoft.com/blog/askds/how-to-not-use-win32-product-in-group-policy-filtering/399983) - MSI reconfiguration confirmed by Microsoft
- Microsoft Learn: Registry Uninstall Key (https://learn.microsoft.com/en-us/windows/win32/msi/uninstall-registry-key) - authoritative on detection method
- xkln.net: Stop Using Win32_Product (https://xkln.net/blog/please-stop-using-win32product-to-find-installed-software-alternatives-inside/) - community consensus
- Win32_Product is Evil post-mortem (https://gregramsey.net/2012/02/20/win32_product-is-evil/) - MSI reconfiguration confirmed

### Secondary (MEDIUM confidence)
- PyInstaller GitHub issue 5360 (https://github.com/pyinstaller/pyinstaller/issues/5360) - Jinja2 bundling workaround confirmed
- PyInstaller GitHub issue 6754 (https://github.com/pyinstaller/pyinstaller/issues/6754) - CrowdStrike blocking pattern confirmed
- CrowdStrike blocking PyInstaller executables KB (https://uah.teamdynamix.com/TDClient/2075/Portal/KB/ArticleDet?ID=137260) - onefile quarantine confirmed
- PyInstaller AV false positives guide (https://www.pythonguis.com/faq/problems-with-antivirus-software-and-pyinstaller/) - AV mitigation strategies
- Nuitka vs PyInstaller comparison (https://coderslegacy.com/nuitka-vs-pyinstaller/) - Nuitka fallback rationale
- Advanced Installer: WOW6432Node (https://www.advancedinstaller.com/user-guide/registry-wow6432node.html) - 32/64-bit redirection confirmed
- Python UTF-8 mode on Windows (https://dev.to/methane/python-use-utf-8-mode-on-windows-212i) - PYTHONUTF8=1 behavior confirmed
- socket.gethostname() non-ASCII issue (https://github.com/mitogen-hq/mitogen/issues/687) - encoding bug confirmed
- Belarc Advisor product page (https://www.belarc.com/products/belarc-advisor) - closest competitor reference

---
*Research completed: 2026-05-04*
*Ready for roadmap: yes*
