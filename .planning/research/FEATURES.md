# Feature Research

**Domain:** Windows IT audit executable — USB-portable, read-only PC inventory with RPG-themed HTML output
**Researched:** 2026-05-04
**Confidence:** HIGH

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any IT staff member doing a PC audit expects to find. Missing these makes the tool feel broken or incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Hostname display | First thing IT looks at — tells you what you're dealing with | LOW | Raw hostname always shown even if decode fails |
| Hostname decode (naming convention) | Master Electronics' convention encodes city + type + dept — this IS the audit context | MEDIUM | 4 device types: Warehouse WS, User Laptop, Dept Laptop, P3. 21 city codes. Must show unknown gracefully |
| OS version + build number | Required to assess patch status, upgrade eligibility, Win10 EOL risk (Oct 2025) | LOW | `platform.version()` or `wmi.Win32_OperatingSystem` — readable by standard user |
| CPU model | Identifies hardware tier; used when assessing upgrade suitability | LOW | `wmi.Win32_Processor` |
| RAM amount | Immediate triage signal: 4GB = problem, 16GB = fine | LOW | `wmi.Win32_ComputerSystem.TotalPhysicalMemory` |
| Disk capacity + free space | Is this machine full? Is it about to run out of space? | LOW | `shutil.disk_usage` or `wmi.Win32_LogicalDisk` — works without admin |
| Currently logged-in user | Who's on this machine right now? Essential for user-assigned laptop audits | LOW | `os.getlogin()` or `wmi.Win32_ComputerSystem.UserName` |
| Installed app detection — target list | Is NinjaRMM on here? CrowdStrike? M365? These are compliance questions | MEDIUM | Registry method preferred over WMI Win32_Product (see PITFALLS). Check HKLM\Software\...\Uninstall + WOW6432Node + file-system fallbacks |
| App presence + version | Not just present/absent — knowing version matters (outdated CrowdStrike is a risk) | MEDIUM | Pull DisplayVersion from registry Uninstall key |
| HTML output file | The deliverable — IT staff needs something to look at, share, or print | HIGH | D&D character sheet styling. Self-contained single file (inline CSS + data) |
| JSON log file written to USB | The audit trail — machine-readable, timestamped, lives on the flash drive | LOW | `json.dumps` with timestamp; writes to `os.path.dirname(sys.argv[0])` |
| No installation required | IT may run this on pre-enrollment, fresh-image, or unmanaged machines | HIGH | PyInstaller one-file .exe. Build from minimal venv to stay under 50MB |
| Graceful handling of unknown hostnames | Not every machine follows convention; tool must not crash or confuse | LOW | Show "Unknown Adventurer" class with raw hostname |

---

### Differentiators (Competitive Advantage)

Features that make this tool genuinely more useful than running `msinfo32` or `Get-ComputerInfo` manually.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| D&D/RPG character sheet HTML output | Memorable, scannable, actually fun — IT staff will show this to their teams; reduces cognitive load compared to raw data dumps | HIGH | This is the core product differentiator. See RPG Theming section below |
| Hostname decode with human-readable label | Turning "PHX-INV-003" into "Phoenix — Inventory Dept Warehouse Workstation #3" eliminates the lookup step that every technician currently does manually | MEDIUM | The convention was created internally (Edgar, 2025) — this tool gives it a UI |
| Compliance status at-a-glance | Color-coded PASS/FAIL/MISSING for each target app. IT sees in 3 seconds if a machine is fully provisioned | LOW | CSS color coding: green = present, red = missing, yellow = present but outdated |
| "Gaps" section | Explicit list of missing required apps — what needs to be installed — so IT doesn't have to mentally diff the app list | LOW | Derived from required app list vs detected list |
| Local user profiles list | Shows what accounts exist on the machine — important for decommission or user migration scenarios | MEDIUM | `wmi.Win32_UserAccount` or registry `ProfileList` — may need elevation for full list; degrade gracefully |
| Multiple detection methods per app | Registry-first, file-system fallback. More reliable than WMI Win32_Product alone | MEDIUM | NinjaOne: check service + registry. CrowdStrike: check C:\Program Files\CrowdStrike\CSFalconController.exe + registry. Intune: check "Company Portal" in registry + MDM enrollment status |
| Elevation-aware output | Notes which data points were limited by running without admin, so the technician knows if they got the full picture | LOW | Flag specific fields with "elevated required for full data" note in output |
| Audit timestamp + machine fingerprint | Every JSON log records when the audit ran, the machine hostname, and the auditing user — creates an audit trail without any server | LOW | `datetime.now(timezone.utc).isoformat()` + hostname + logged-in user |
| Self-describing output | The HTML explains what each field means — junior IT staff can use it without memorizing naming conventions | LOW | Tooltips or a legend section in the HTML; the "class" decode table |

---

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Write anything to the host PC | "It would be useful to auto-create a report shortcut on the desktop" | Violates the core constraint — tool must be read-only. Leaves artifacts. Creates IT policy questions. May trigger AV/DLP | All output goes to the USB directory only. Show the HTML path prominently at end of run |
| Require internet / phone home | "Could we upload results to a central dashboard automatically?" | Breaks the offline use case (pre-enrollment, air-gapped machines). Creates security/trust concerns. v1 scope specifically excludes this | JSON log on USB is the audit trail. A future milestone can add optional upload |
| Require admin / elevation | "We could get more data with admin rights" | Many target machines (especially pre-enrollment) won't have IT staff with local admin. Mandatory elevation breaks usability | Design for standard user; document and display which checks were limited by privilege level |
| Active Directory / LDAP queries | "We could pull department info from AD instead of just the hostname" | Adds network dependency. Fails on machines not yet domain-joined — exactly the machines most in need of auditing | Decode from hostname convention only. AD enrichment is a future milestone |
| Detect all installed software (full list) | "Show me every installed app" | Output becomes unreadably long. Slows down the tool. The value is the targeted app compliance check, not a general inventory | Show full app count as a number; only surface the target app list with pass/fail. MERP/proprietary detection matters more than generic inventory |
| Auto-update mechanism | "The tool should check for updates when it runs" | Requires internet. Adds complexity. The USB distribution model means IT controls which version is on the drive | Version-stamp the .exe and display it in the output. IT manually updates the USB |
| WMI Win32_Product for software detection | Common tutorial approach | Triggers consistency checks on every MSI-installed app — causes silent repairs, performance impact, and potential instability on production machines | Use registry Uninstall keys (HKLM\...\Uninstall + WOW6432Node) + targeted file-system checks |
| Network discovery / remote scan | "While I have this plugged in, could it scan other machines?" | Entirely different security profile. Requires network permissions. Breaks the USB-portable, single-machine model | This tool is intentionally single-machine. Remote auditing is a different product |

---

## RPG Theming Opportunities

This is the primary differentiator. The mapping is natural and should be leaned into fully.

| IT Concept | D&D/RPG Equivalent | Display Label | Notes |
|------------|--------------------|---------------|-------|
| Device type (from hostname) | Character Class | "Class: Warehouse Workstation" | Class icon per device type — shield for warehouse, scroll for laptop, etc. |
| Department code | Guild / Faction | "Guild: Inventory" | Show full department name alongside code |
| City code | Realm / Origin | "Realm: Phoenix" | Map all 21 city codes to readable names |
| Station number | Level or Rank | "Level 3" (station #3) | The sequence within a department |
| CPU model + core count | Strength | "STR 16 — Intel Core i7-12th Gen (8 cores)" | Higher cores = higher STR stat |
| RAM amount | Constitution | "CON 14 — 16 GB" | Low RAM = low CON; 4GB = CON 6 (sickly) |
| Free disk space | Endurance / HP | "HP 247/512 GB" | Disk as health bar — visually shows how full the drive is |
| Disk total capacity | Max HP | Part of HP bar display | |
| OS version | Age / Era | "Era: Windows 11 (Build 22631)" | Could show "ancient" for Win7, "seasoned" for Win10, "current" for Win11 |
| Logged-in user | Bound Hero | "Bound to: jsmith" | User-assigned laptops show who the device belongs to |
| Local user profiles | Known Companions | "Known Companions: [list]" | Secondary accounts on the machine |
| NinjaRMM present | Guild Contract (RMM) | Green checkmark "Enrolled in NinjaOne" | Missing = warning |
| Intune / Company Portal | Realm Registry | Green "Registered with Intune" | Missing = unmanaged — red flag |
| CrowdStrike Falcon | Armor / Defense | "Armor: CrowdStrike Falcon v7.x — Active" | Missing = "UNARMORED" in red |
| M365 apps | Spellbook / Abilities | "Abilities: Word, Excel, Outlook, Teams, OneDrive" | List which M365 apps are installed |
| Zoom | Communication Rune | "Communication Rune: Zoom v6.x" | |
| Chrome | Scout's Glass | "Scout's Glass: Chrome v124" | |
| MERP (ERP) | Ancient Tome | "Ancient Tome: MERP — Installed" | Proprietary = "Ancient" or "Legendary" item |
| Claude desktop | Arcane Intelligence | "Arcane Intelligence: Claude — Installed" | Fun Easter egg framing |
| Missing required app | "Missing Equipment" warning | Red banner: "MISSING: CrowdStrike Falcon — Critical Gap" | Drives action |
| Audit timestamp | Chronicle Date | "Chronicle: 2026-05-04 14:32 UTC" | |
| Overall compliance status | Quest Status | "QUEST COMPLETE" vs "QUEST INCOMPLETE — 2 gaps" | Top of sheet summary |

**Visual structure recommendation:**
- Top: Character header (name = hostname decoded, class = device type, realm = city, guild = department, level = station)
- Middle left: Core Stats block (CPU=STR, RAM=CON, Disk HP bar, OS era)
- Middle right: Equipment / Abilities (installed apps with pass/fail states, styled as inventory slots)
- Bottom: Gaps / warnings section ("Missing Equipment" list)
- Footer: Chronicle (audit timestamp, auditor username, tool version)

---

## Feature Dependencies

```
Hostname decode
    └──requires──> Hostname collection (wmi.Win32_ComputerSystem.Name)
    └──enables──>  Character Class display
    └──enables──>  Guild / Department display
    └──enables──>  Realm display

App detection
    └──requires──> Registry reader (winreg)
    └──enhances──> File-system fallback (os.path.exists)
    └──enables──>  Compliance status / gaps list
    └──enables──>  "Missing Equipment" RPG display

HTML output
    └──requires──> All data collection complete
    └──requires──> RPG theme mapping (concept above)
    └──enables──>  Shareable/printable audit artifact

JSON log
    └──requires──> All data collection complete
    └──requires──> USB write path resolution (dirname of sys.argv[0])
    └──enables──>  Future dashboard / aggregation

Elevation-aware behavior
    └──requires──> Privilege check at startup
    └──enhances──> Local user profile collection (more complete with admin)
    └──enhances──> Some WMI fields (more reliable with admin)

PyInstaller packaging
    └──requires──> Minimal venv build (not system Python — size constraint)
    └──requires──> All dependencies installable in isolation
    └──conflicts--> Conda/Anaconda build environment (produces 100-200MB+ binaries)
```

### Dependency Notes

- **App detection requires registry reader:** The preferred detection path is `winreg` → `HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall` (64-bit) and `WOW6432Node\...\Uninstall` (32-bit). This is readable by standard users. WMI Win32_Product is explicitly excluded due to consistency-check side effects.
- **File-system fallback enhances app detection:** For apps like CrowdStrike that also have a known install path (`C:\Program Files\CrowdStrike\CSFalconController.exe`), a file existence check is a reliable secondary signal.
- **HTML output requires all data collection:** The template renders once at the end; there is no streaming or partial output. This is fine — the whole audit runs in seconds.
- **JSON log requires USB write path:** Must resolve to `os.path.dirname(os.path.abspath(sys.argv[0]))`. Test this path: if it's a temp directory (PyInstaller --onefile extracts there), the logic needs to find the original .exe location via `sys.executable` instead.

---

## MVP Definition

### Launch With (v1)

These are in scope per PROJECT.md. Every item maps to an active requirement.

- [ ] Hostname collection + decode (all 4 device types, 21 cities, dept codes) — the product's core intelligence
- [ ] Hardware stats: OS version/build, CPU, RAM, disk capacity/free space, logged-in user — table stakes
- [ ] App detection for 8 target apps: NinjaRMM, M365 (Word/Excel/Outlook/Teams/OneDrive), Intune, CrowdStrike, Zoom, Chrome, Claude, MERP — the compliance check
- [ ] D&D/RPG themed HTML character sheet output — the differentiator
- [ ] JSON log written to USB directory — the audit trail
- [ ] PyInstaller one-file .exe packaging — the distribution method
- [ ] Graceful unknown hostname handling ("Unknown Adventurer" class) — robustness

### Add After Validation (v1.x)

Add once v1 is in field use and gathering feedback.

- [ ] Local user profiles list — useful for decommission audits; deferred because it benefits from elevation (which v1 is designed to not require)
- [ ] Elevation-aware output flag — show which fields had limited data due to running as standard user; useful once IT staff ask "why doesn't it show X?"
- [ ] Printer / peripheral detection — IT sometimes needs this for workstation audits
- [ ] BitLocker status — security-relevant; requires elevation on most machines

### Future Consideration (v2+)

Defer until v1 is validated in the field.

- [ ] Mac support — out of scope for v1 per PROJECT.md; Python abstraction in v1 should make this feasible
- [ ] Optional JSON upload to central log collector — useful for multi-machine fleet audits
- [ ] Aggregate dashboard across all USB-collected JSON logs — requires separate tooling
- [ ] Remote scan mode — entirely different security/permission profile; effectively a different product

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Hostname decode + RPG class display | HIGH | MEDIUM | P1 |
| Hardware stats (CPU, RAM, Disk, OS) | HIGH | LOW | P1 |
| Target app detection (registry method) | HIGH | MEDIUM | P1 |
| D&D HTML character sheet output | HIGH | HIGH | P1 |
| JSON log to USB | HIGH | LOW | P1 |
| PyInstaller .exe packaging | HIGH | MEDIUM | P1 |
| Unknown hostname graceful handling | MEDIUM | LOW | P1 |
| Compliance gaps / "Missing Equipment" section | HIGH | LOW | P1 — derived from detection results |
| App version display | MEDIUM | LOW | P1 — trivial add-on to detection |
| Color-coded pass/fail status | HIGH | LOW | P1 — CSS only |
| Local user profiles list | MEDIUM | MEDIUM | P2 |
| Elevation-aware degradation flags | MEDIUM | LOW | P2 |
| M365 individual app breakdown | MEDIUM | LOW | P1 — each app checked separately |

---

## Competitor Feature Analysis

| Feature | Belarc Advisor | EZ Audit (USB) | Free PC Audit | StatusReport (this tool) |
|---------|----------------|----------------|---------------|--------------------------|
| USB portable, no install | No (installer required) | Yes | Yes (portable .exe) | Yes (PyInstaller .exe) |
| Works offline / no network | Yes | Yes | Yes | Yes |
| Custom app detection list | No — generic inventory | Partial (configurable) | No | Yes — 8 named target apps |
| Naming convention decode | No | No | No | Yes — Master Electronics specific |
| HTML output | Yes (browser report) | Yes (report) | Yes | Yes — D&D/RPG themed |
| JSON structured log | No | No | No | Yes |
| No write to host PC | No — writes locally | No — installs | Yes | Yes — USB-only output |
| Standard user (no admin) | Partial | Requires admin for full scan | Partial | Designed for standard user |
| Compliance gap view | No | No | No | Yes — explicit gaps list |
| Memorable / shareable output | No — clinical | No — clinical | No — clinical | Yes — RPG framing |

The gap this tool fills: no existing portable tool combines targeted compliance detection, naming convention decode, and a genuinely readable output format. Belarc Advisor is the closest in concept (local HTML report) but requires installation, writes to the host PC, and produces a clinical data dump rather than an actionable compliance view.

---

## Sources

- [EZ Audit USB Portable Tool Features](https://www.ezaudit.net/network-inventory-audit-tool-for-support-team-features.asp) — competitor feature reference (MEDIUM confidence)
- [InvGate: IT Audit Software Tools Compared](https://blog.invgate.com/it-audit-software) — feature categories for IT audit tools (MEDIUM confidence)
- [Microsoft Learn: Registry Uninstall Key paths](https://learn.microsoft.com/en-us/answers/questions/179854/get-installed-software-list) — authoritative on detection method (HIGH confidence)
- [xkln.net: Stop Using Win32_Product](https://xkln.net/blog/please-stop-using-win32product-to-find-installed-software-alternatives-inside/) — critical guidance on WMI pitfall (HIGH confidence via community consensus)
- [Shelf.nu: Top PC Naming Conventions](https://www.shelf.nu/blog/top-pc-naming-conventions-for-system-admins) — naming convention patterns (MEDIUM confidence)
- [PyInstaller size reduction practices](https://coderslegacy.com/python/reduce-size-pyinstaller-exe/) — packaging constraint guidance (MEDIUM confidence)
- [GSDSolutions: PC Audit Checklist](https://gsdsolutions.io/a-pc-audit-checklist-from-an-it-services-provider/) — what IT staff actually check (MEDIUM confidence)
- [Belarc Advisor product page](https://www.belarc.com/products/belarc-advisor) — closest competitor reference (HIGH confidence)

---

*Feature research for: Windows IT audit USB executable (StatusReport)*
*Researched: 2026-05-04*
