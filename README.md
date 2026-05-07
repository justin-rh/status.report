# StatusReport

A self-contained Windows tool that runs from a USB flash drive and audits a PC in seconds. Plug in, double-click, and get a full picture of the device — hardware specs, installed software, and compliance gaps — rendered as a D&D/RPG-styled HTML character sheet saved back to the drive.

Built for the Master Electronics IT department.

---

## What It Does

- **Decodes the hostname** using the Master Electronics naming convention → city, device type, department, station
- **Collects hardware info** — CPU model, RAM, disk capacity/free space, Windows version, local user profiles
- **Detects 11 target apps** — NinjaOne, CrowdStrike Falcon, Microsoft 365, Zoom, Google Chrome, Claude desktop, MERP
- **Renders an HTML character sheet** with color-coded pass/fail badges and a quest status banner
- **Writes output to the USB drive** — no files left on the host PC

---

## Requirements

- Windows 10 or 11 (standard user — no admin rights required)
- Run from a USB flash drive

No installation. No internet. No changes to the host PC.

---

## Running the Tool (IT Staff)

1. Copy `dist\status_report\` to a USB flash drive
2. On the target PC, open the USB drive and double-click `status_report.exe`
3. The tool runs, prints progress to the console, and opens the HTML report in the default browser
4. Press **Enter** to close the window, then eject the USB drive
5. The report is saved to `logs\status_{hostname}_{date}.html` on the USB drive

> The tool runs as a standard user. Some hardware fields (e.g., CPU model via WMI) require elevation — the tool degrades gracefully and shows `Unavailable` rather than crashing.

---

## Building from Source

### Prerequisites

- Python 3.12
- Git

### Setup

```bat
git clone https://github.com/justin-rh/status.report.git
cd status.report
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install -r requirements-dev.txt
```

### Build

```bat
build.bat
```

Output: `dist\status_report\` — copy this folder to the USB flash drive.

---

## Detected Applications

| App | Detection Method |
|-----|-----------------|
| NinjaRMM / NinjaOne | Registry — all 4 Uninstall key paths |
| CrowdStrike Falcon | Registry — DisplayName + SCM service state |
| Microsoft 365 | Registry — suite entry |
| Zoom | Registry — all 4 Uninstall key paths |
| Google Chrome | Registry — all 4 Uninstall key paths |
| Claude desktop | Registry — MSIX AppModel repo + Uninstall sweep |
| MERP (Master Electronics ERP) | Filesystem — PVX Plus install path |

All four registry Uninstall paths are checked: `HKLM`, `HKLM\Wow6432Node`, `HKCU`, `HKCU\Wow6432Node`.

---

## Hostname Convention

Master Electronics hostnames encode device identity:

| Format | Type |
|--------|------|
| `CITY-DEPT-###` | Warehouse Workstation |
| `CITY-SERIAL-CO` | User-Assigned Laptop (ME / ES / EC / AP / OL) |
| `CITY-DEPTLAP-###` | Department Laptop |
| `CITY-P3A/B/C-###` | P3 Warehouse Device |

City codes: AMM, AMS, CHI, EDE, GEO, GER, GUA, MIA, MON, NYC, PEO, PEN, PHX, ROC, SCL, SEA, SMO, TAM, TOR, TSU, VAN

Unrecognized hostnames display as `Unknown` — the tool never crashes on a non-conforming name.

---

## Development

### Running Tests

```bat
.venv\Scripts\pytest
```

85+ tests covering the hostname parser, hardware collectors, app detection, renderer, and file writer. All tests run without Windows API calls or a live registry.

### Project Structure

```
main.py                     # Entry point — orchestrates the full pipeline
models.py                   # Data contract: AuditReport, ParsedHostname, AppStatus, CollectionResult
parsers/
  name_parser.py            # Hostname decoder (pure function, no Windows dependencies)
collectors/
  windows/
    hardware.py             # WMI + psutil + winreg hardware and profile collectors
    apps.py                 # Registry-based app detection
renderer/
  __init__.py               # Jinja2 render pipeline
  templates/
    character_sheet.html    # D&D/RPG HTML template
writers/
  __init__.py               # File I/O layer (write_html)
tests/                      # pytest suite
build.bat                   # One-command PyInstaller build
status_report.spec          # PyInstaller --onedir build definition
```

### Key Constraints

- **Never use `--onefile`** — quarantined by CrowdStrike Falcon. Always `--onedir`.
- **Never use `Win32_Product`** — triggers MSI reconfiguration on production machines. Use `winreg` instead.
- **Output path from `Path(sys.executable).parent`** — `os.getcwd()` points to the host PC when double-clicked, not the USB drive.
- **No writes to the host PC** — all output stays on the flash drive.

---

## Output

The tool saves `logs\status_{hostname}_{date}.html` to the USB drive and opens it in the default browser. The character sheet includes:

- **Header** — hostname as character name, device class, realm (city), guild (department), station
- **Stat Block** — CPU (STR), RAM (CON), disk HP bar, OS version, current user
- **Equipment** — one row per app with a green `✓ Installed` or red `✗ Missing` badge
- **Quest Status** — `QUEST COMPLETE` or `MISSING SOFTWARE — N app(s)` banner

---

## License

Internal tool — Master Electronics IT.
