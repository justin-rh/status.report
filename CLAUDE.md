# StatusReport — Project Guide

## What This Is

A self-contained Windows .exe (PyInstaller --onedir) that runs from a USB flash drive and audits a Windows PC. It decodes the hostname using the Master Electronics naming convention, collects hardware stats and user profiles, detects a specific list of installed apps, and generates a D&D/RPG-styled HTML character sheet saved back to the flash drive.

## GSD Workflow

This project uses the GSD framework for spec-driven, phase-based development.

- **State**: `.planning/STATE.md`
- **Roadmap**: `.planning/ROADMAP.md`
- **Requirements**: `.planning/REQUIREMENTS.md`
- **Research**: `.planning/research/`

### Current Status
Phase 1 is next. Run `/gsd-discuss-phase 1` or `/gsd-plan-phase 1` to begin.

## Critical Technical Constraints

- **NEVER use PyInstaller `--onefile`** — quarantined by CrowdStrike Falcon on every target machine. Use `--onedir` only.
- **NEVER use `Win32_Product` for app detection** — triggers MSI consistency checks on production machines. Use `winreg` Uninstall key paths.
- **ALWAYS enumerate all 4 registry Uninstall paths** — `HKLM`, `HKLM\Wow6432Node`, `HKCU`, `HKCU\Wow6432Node`. Missing 32-bit entries is a silent bug.
- **ALWAYS derive output path from `Path(sys.executable).parent`** — `os.getcwd()` points to the host PC when double-clicked, not the flash drive.
- **NEVER write to the host PC** — no C:\, %TEMP%, %APPDATA%, or registry writes. Audit trail stays on the flash drive only.

## Stack

- Python 3.12
- psutil 6.x (CPU, RAM, disk — standard user)
- wmi 1.5.1 (CPU model name, OS detail, service detection)
- winreg (stdlib — app detection via registry)
- Jinja2 3.1.x (HTML rendering — load via `importlib.resources`, not filesystem)
- PyInstaller 6.x `--onedir` (packaging)

## Architecture

```
main.py → collectors/ → models.AuditReport → renderer/ → writers/
               ↑ platform-swappable (windows/ vs mac/ stubs)
```

Each collector returns a `CollectionResult(value, error)` envelope — never raises across layer boundaries.

## Open Blockers

- **MERP registry path unknown** — must be confirmed with IT before Phase 4 can complete.
- **CrowdStrike --onedir test** — must be run on an enrolled machine at Phase 5 start.
- **Hostname convention** — confirm all 21 city codes and department codes with IT/Edgar before shipping Phase 1 parser.

## Naming Convention Reference

| Format | Type |
|--------|------|
| `CITY-DEPT-###` | Warehouse Workstation |
| `CITY-SERIAL-COMPANY` | User-Assigned Laptop (ME/ES/EC/AP/OL) |
| `CITY-DEPTLAP-###` | Department Laptop (contains "LAP") |
| `CITY-P3A/B/C-###` | P3 Warehouse Device |

City codes: AMM, AMS, CHI, EDE, GEO, GER, GUA, MIA, MON, NYC, PEO, PEN, PHX, ROC, SCL, SEA, SMO, TAM, TOR, TSU, VAN
