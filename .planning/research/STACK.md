# Stack Research

**Domain:** Windows IT audit / system inventory executable (USB-portable, no-install)
**Researched:** 2026-05-04
**Confidence:** HIGH (core stack) / MEDIUM (AV mitigation, packaging tradeoffs)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12.x | Runtime | Ships as self-contained exe via PyInstaller; standard library covers hostname, OS, registry, subprocess; same codebase extends to Mac later. 3.12 is the current stable release with best PyInstaller support. Avoid 3.13+ until PyInstaller hooks catch up. |
| psutil | 6.x (latest) | CPU, RAM, disk, process, user enumeration | Works at standard-user privilege for all system-wide metrics (cpu_percent, virtual_memory, disk_usage, users). Cross-platform. 10–20x faster than WMI for the same data. Raises AccessDenied gracefully on protected per-process calls rather than crashing. |
| wmi (Tim Golden) | 1.5.1 | WMI queries for hardware detail and service detection where psutil falls short | Needed for: CPU model/socket name (Win32_Processor), BIOS serial, detailed OS build info (Win32_OperatingSystem), installed services (Win32_Service). Most Win32 class queries succeed for standard users; those that do not will raise a COM error that you catch and mark as "elevation required". |
| winreg (stdlib) | built-in | Installed software detection via registry | Built into Python — no dependency. Reads HKLM and HKCU Uninstall keys without admin. Must query both 64-bit and 32-bit (Wow6432Node) hives and use KEY_READ | KEY_WOW64_64KEY / KEY_WOW64_32KEY flags to see all apps from a 64-bit process. |
| platform (stdlib) | built-in | OS version string, architecture | platform.win32_ver() returns release, version, CSD (service pack), type. Zero-dependency, standard-user safe, works offline. |
| socket (stdlib) | built-in | Hostname retrieval | socket.gethostname() — no admin, no network required, instant. |
| ctypes (stdlib) | built-in | Elevation detection | ctypes.windll.shell32.IsUserAnAdmin() — canonical Windows check; returns 0 for standard users. Use this to gate which collectors degrade gracefully. |
| PyInstaller | 6.x (latest stable) | Package to single .exe | Industry-standard bundler; largest ecosystem, most hooks. Use --onedir mode for AV friendliness (see packaging section). 6.x has improved hooks over 5.x and better Python 3.12 support. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Jinja2 | 3.1.x | HTML output generation | Use for the D&D character sheet. Load templates from inline Python strings (Environment().from_string() or DictLoader) — do NOT use FileSystemLoader with a templates/ directory, as PyInstaller --onefile won't bundle external files correctly without explicit --add-data flags. Avoids the known Jinja2/PyInstaller packaging issue. |
| json (stdlib) | built-in | JSON log file output | No dependency needed. json.dumps() with indent=2 is sufficient for the audit log. |
| datetime (stdlib) | built-in | Timestamps in log output | No dependency. datetime.now().isoformat() gives ISO 8601 timestamps. |
| os / pathlib (stdlib) | built-in | Output path resolution (write to exe's directory) | sys.executable gives the running .exe path; use Path(sys.executable).parent to resolve the USB drive write location whether running as --onefile or --onedir. |
| subprocess (stdlib) | built-in | Fallback PowerShell calls | Use only as a fallback when wmi raises COM errors. Call Get-CimInstance, not wmic — wmic is being removed in Windows 11 24H2+. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| PyInstaller 6.x | Build the distributable .exe | Run from a clean venv with only production deps installed — prevents accidental bundling of dev tools (pytest, black, etc.) that bloat the exe and add AV surface area |
| pyinstaller-hooks-contrib | Hook library for PyInstaller | Auto-installed with PyInstaller 6.x; provides hooks for wmi, psutil, Jinja2 so they bundle correctly |
| venv (stdlib) | Isolated build environment | Create a dedicated build venv; do not use conda — conda base envs pull in 100–200 MB of extra libs that balloon the exe to 100+ MB |
| UPX | Optional exe compression | Can reduce exe size 30–50%. Do NOT use with wmi/psutil — UPX compression of those binaries has triggered additional AV false positives. Test before shipping. |
| VirusTotal (manual check) | AV false-positive validation | Upload your built .exe before each release; check detection rate across 70+ engines. If >5 engines flag it, investigate before distributing. |

---

## Installation

```bash
# Create a clean build venv (IMPORTANT: do not use conda base)
python -m venv .venv
.venv\Scripts\activate

# Core runtime dependencies
pip install psutil==6.*
pip install wmi==1.5.1
pip install Jinja2==3.1.*

# Build tooling (dev only)
pip install pyinstaller==6.*

# Freeze deps for reproducible builds
pip freeze > requirements.txt
```

---

## Packaging — PyInstaller Decision Guide

### Recommended: --onedir mode

```bash
pyinstaller --onedir --name StatusReport --icon assets\icon.ico collector\main.py
```

**Why --onedir over --onefile:**

- --onefile extracts itself to `%TEMP%` on every run. This extraction-and-execute pattern is the primary trigger for AV heuristics (matches packer/dropper behavior). CrowdStrike Falcon and Windows Defender both flag this pattern.
- --onedir writes all files once to a folder; the launcher .exe is a thin shim that does not self-extract, making it far less suspicious to behavior-based AV.
- For USB distribution, a folder is acceptable: IT staff can still double-click `StatusReport\StatusReport.exe` and it runs. The entire folder fits on any USB drive.
- --onedir also starts faster (no extraction delay) and makes it easier to inspect what's bundled.

**If --onefile is required** (project constraint changes):
- Build the PyInstaller bootloader from source to get a unique binary hash — the stock bootloader hash is on many AV blocklists.
- Do not use UPX compression.
- Code-sign with an OV certificate (EV certificate gets SmartScreen immediate trust; OV costs ~$100–300/year).
- Submit to CrowdStrike's false-positive portal and Microsoft's MSRC portal before deploying.
- Budget 1–2 weeks for the AV whitelist process to propagate.

### Size budget

| Component | Estimated Size |
|-----------|---------------|
| Python 3.12 interpreter | ~8–10 MB |
| psutil | ~2 MB |
| wmi + pywin32 | ~10–15 MB |
| Jinja2 + MarkupSafe | ~1 MB |
| Misc stdlib | ~5–10 MB |
| **Total (onedir folder)** | **~30–40 MB** |

This is comfortably under the 50 MB budget stated in PROJECT.md.

---

## The WMI vs wmic vs PowerShell Decision

**Use wmi (Python library) as the primary Windows data source. Use subprocess + PowerShell as a fallback. Never call wmic.**

| Approach | Use? | Reason |
|----------|------|--------|
| `wmi` Python library | YES — primary | Direct COM access; no subprocess overhead; works on Windows 7–11; returns structured Python objects; standard-user accessible for most Win32 classes |
| `subprocess` + `Get-CimInstance` PowerShell | YES — fallback | When wmi raises COM errors; PowerShell is present on all modern Windows; use `Get-CimInstance` not `Get-WmiObject` (deprecated) |
| `subprocess wmic` | NO | Removed in Windows 11 24H2+ (build 26100+); disabled by default on Windows Server 2025; any machine the tool runs on after late 2025 may not have it |
| `subprocess powershell Get-WmiObject` | NO | `Get-WmiObject` is deprecated in PowerShell 7+; use `Get-CimInstance` instead |

**Standard-user accessible WMI queries (no elevation needed):**
- Win32_ComputerSystem — hostname, model, manufacturer, total RAM
- Win32_OperatingSystem — OS name, version, build number, architecture
- Win32_Processor — CPU name, cores, clock speed
- Win32_LogicalDisk — drive letters, size, free space
- Win32_Service — service name, display name, state, start mode
- Win32_UserProfile — local user profile paths (enumerate profiles)

**Queries that require elevation (degrade gracefully):**
- Win32_NetworkAdapterConfiguration with detailed IP binding (some configurations)
- Win32_ShadowCopy
- Certain security-namespace queries

---

## Installed Software Detection Strategy

Query all four registry locations. A complete audit requires all four because 32-bit apps on 64-bit Windows, per-user installs, and MSI-only installs each land in different places.

```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall          (64-bit apps, admin installs)
HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall  (32-bit apps on 64-bit OS)
HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall          (per-user installs)
HKCU\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall  (per-user 32-bit on 64-bit)
```

Use `winreg.OpenKey(hive, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)` for the first two from a 64-bit Python process to avoid registry reflection redirecting you. Read `DisplayName`, `DisplayVersion`, `Publisher`, `InstallDate` from each subkey.

For specific apps (NinjaOne, CrowdStrike, M365, etc.) also check known file system paths and service names — registry entries can be absent for silently-deployed tools:

| App | Primary Detection | Secondary Detection |
|-----|------------------|---------------------|
| NinjaRMM/NinjaOne | Registry uninstall key | Service: `NinjaRMMAgent`; path: `C:\Program Files (x86)\NinjaRMMAgent\` |
| CrowdStrike Falcon | Registry uninstall key | Service: `CSFalconService`; driver: `CrowdStrike\*` in `C:\Windows\System32\drivers\` |
| Microsoft 365 (Word, Excel, etc.) | Registry: `HKLM\SOFTWARE\Microsoft\Office\ClickToRun\Configuration` | File presence in `C:\Program Files\Microsoft Office\root\Office16\` |
| Microsoft Teams | Registry uninstall (HKCU for per-user install) | Path: `%LocalAppData%\Microsoft\Teams\` |
| Intune/Company Portal | Registry: `HKLM\SOFTWARE\Microsoft\Provisioning\` | Service: `IntuneManagementExtension` |
| Zoom | Registry uninstall (HKCU) | Path: `%AppData%\Zoom\bin\Zoom.exe` |
| Google Chrome | Registry: both HKLM and HKCU uninstall keys | Path: `C:\Program Files\Google\Chrome\Application\chrome.exe` |
| Claude Desktop | Registry HKCU uninstall | Path: `%LocalAppData%\AnthropicClaude\` |
| MERP | Registry uninstall | Known installation path (to be confirmed with IT) |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Packaging | PyInstaller 6.x (--onedir) | Nuitka | Nuitka compiles to C then native binary — fewer AV hits, faster startup. However: 10–100x slower to build, significantly more complex .spec equivalent, less mature hooks for wmi/psutil on Windows. Use if CrowdStrike blocks PyInstaller even after onedir + whitelist. |
| Packaging | PyInstaller 6.x (--onedir) | cx_Freeze | Faster startup than PyInstaller, lower AV hit rate than PyInstaller --onefile. Viable fallback if AV problems persist. Smaller community, fewer hooks. |
| System info | psutil + wmi | Pure subprocess + PowerShell | More portable but slower, harder to parse, requires PowerShell execution policy cooperation. Valid fallback, not first choice. |
| HTML generation | Jinja2 (inline string templates) | Python f-strings / string concat | f-strings work for a small output but become unmaintainable for a complex D&D character sheet with conditionals and loops. Jinja2 DictLoader keeps HTML readable without external file complexity. |
| HTML generation | Jinja2 (inline string templates) | Mako, Cheetah | Less commonly used, fewer PyInstaller hooks tested. Jinja2 has known-good PyInstaller integration. |
| Registry access | winreg (stdlib) | pywin32 win32api registry calls | winreg is the stdlib choice; pywin32 adds a large dependency (15+ MB) that's already partially pulled in by wmi. Don't add pywin32 solely for registry work. |
| Runtime | Python 3.12 | Python 3.11 | 3.11 is still maintained but 3.12 has better performance and is the current PyInstaller-recommended target. Avoid 3.13 until PyInstaller 7.x stabilizes hooks. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `wmic` CLI via subprocess | Removed in Windows 11 24H2+ (build 26100+) and Windows Server 2025; tool will silently fail on recent machines | `wmi` Python library or `subprocess` + `Get-CimInstance` PowerShell |
| `Get-WmiObject` PowerShell | Deprecated in PowerShell 7+; still present in Windows PowerShell 5.1 but will confuse future maintainers | `Get-CimInstance` (same data, same privilege requirements, supported path) |
| PyInstaller --onefile on CrowdStrike-managed machines | The self-extraction to %TEMP% at runtime triggers CrowdStrike's behavior-based detection; each rebuild changes the hash requiring re-whitelisting | PyInstaller --onedir; Nuitka if --onedir is blocked |
| UPX compression with wmi/psutil binaries | UPX-compressed Python extension DLLs (.pyd files) have higher AV detection rates than uncompressed; the size saving is not worth the risk for an internal IT tool | No UPX, or UPX only on pure-Python .pyc archives if tested clean |
| Conda as build environment | Conda base environment includes numpy, scipy, and hundreds of unrelated packages that all get bundled — exe balloons to 100–300 MB | Dedicated venv with only production deps |
| py2exe | Last meaningful release was 2022; unmaintained; Python 3.12 support is partial | PyInstaller 6.x |
| Requests library | Unnecessary for this project — no HTTP calls; bundling it adds AV surface area (commonly seen in malware) | Not needed; remove from requirements |
| Admin-required-only WMI calls without a graceful fallback | Tool must run on standard users; any uncaught COM error from an elevated-only query crashes collection | Wrap all wmi calls in try/except; set a `requires_elevation` flag on failed fields |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Python 3.12.x | PyInstaller 6.x | Full support; hooks stable. PyInstaller 5.x had Python 3.12 issues — use 6.x minimum. |
| Python 3.12.x | psutil 6.x | Full support; psutil 5.x has known issues on Python 3.12 with some Windows calls |
| Python 3.12.x | wmi 1.5.1 | Requires pywin32 >= 306; pywin32 is pulled in automatically as a wmi dependency |
| Python 3.12.x | Jinja2 3.1.x | Full support |
| PyInstaller 6.x | pyinstaller-hooks-contrib 2024.x | Auto-installed; do not pin separately — always use the version bundled with PyInstaller 6.x |
| wmi 1.5.1 | pywin32 >= 306 | pywin32 306+ is required for Python 3.12 compatibility; older pywin32 on 3.12 causes import errors at runtime |

---

## Stack Patterns by Variant

**If CrowdStrike Falcon blocks the --onedir exe anyway:**
- Switch packaging to Nuitka (--onefile or --standalone)
- Accept 10-100x longer build time
- Submit to CrowdStrike false-positive portal with the compiled binary
- Nuitka-compiled code looks like native C code to AV heuristics; significantly fewer behavioral flags

**If the project later expands to Mac support (per PROJECT.md "out of scope for v1"):**
- psutil is fully cross-platform — no changes needed
- wmi is Windows-only; abstract behind a `collectors/windows/` module boundary
- Replace wmi calls with `subprocess` + `system_profiler` on Mac
- platform, socket, winreg calls similarly isolated behind OS-specific collectors
- PyInstaller works on Mac but produces a .app bundle; consider Nuitka or briefcase for Mac

**If binary size exceeds 50 MB:**
- Audit bundled modules: `pyinstaller --debug=imports` to see what's included
- Explicitly exclude unused stdlib modules in the .spec file (tkinter, unittest, email, http are common bloat sources)
- Each excluded large module saves 1–5 MB; tkinter alone is ~15 MB

---

## Sources

- [PyPI: wmi 1.5.1](https://pypi.org/project/WMI/) — confirmed current version
- [PyPI: psutil](https://pypi.org/project/psutil/) — confirmed version 6.x, standard-user safe for system-wide metrics
- [PyPI: PyInstaller](https://pypi.org/project/pyinstaller/) — 6.x current stable
- [PyInstaller docs: usage](https://pyinstaller.org/en/stable/usage.html) — onedir vs onefile behavior
- [Python docs: winreg](https://docs.python.org/3/library/winreg.html) — HIGH confidence, stdlib
- [Python docs: platform](https://docs.python.org/3/library/platform.html) — HIGH confidence, stdlib
- [How to Re-enable WMIC on Windows Server 2025](https://www.joelcommon.com/blog/how-to-re-enable-wmic-on-windows-server-2025/) — WMIC deprecation confirmed
- [WMIC: The Forgotten Tool 2025](https://isosecu.com/blog/tools-wmic) — WMIC removal timeline confirmed
- [PyInstaller AV false positives guide](https://www.pythonguis.com/faq/problems-with-antivirus-software-and-pyinstaller/) — MEDIUM confidence
- [PyInstaller GitHub issue #6754](https://github.com/pyinstaller/pyinstaller/issues/6754) — CrowdStrike blocking pattern confirmed
- [Nuitka vs PyInstaller comparison](https://coderslegacy.com/nuitka-vs-pyinstaller/) — MEDIUM confidence
- [2026 Showdown: PyInstaller vs cx_Freeze vs Nuitka](https://ahmedsyntax.com/2026-comparison-pyinstaller-vs-cx-freeze-vs-nui/) — MEDIUM confidence
- [Jinja2 PyPI](https://pypi.org/project/Jinja2/) — 3.1.x confirmed current
- [PyInstaller + Jinja2 bundling issue #5360](https://github.com/pyinstaller/pyinstaller/issues/5360) — DictLoader/from_string workaround confirmed
- [Microsoft Q&A: Collecting system info with Python](https://learn.microsoft.com/en-us/answers/questions/1663906/collecting-system-information-using-python) — WMI standard user behavior

---
*Stack research for: Windows IT audit portable executable (StatusReport)*
*Researched: 2026-05-04*
