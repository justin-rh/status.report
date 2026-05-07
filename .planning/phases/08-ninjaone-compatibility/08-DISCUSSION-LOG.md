# Phase 8: NinjaOne Compatibility - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 08-ninjaone-compatibility
**Areas discussed:** HTML output path (headless), [SUMMARY] line format, HKCU → HKLM MSIX fallback

---

## HTML Output Path (Headless)

| Option | Description | Selected |
|--------|-------------|----------|
| C:\ProgramData\...\logs\ | SYSTEM-writable path; switch output path when isatty() is False | |
| Skip HTML when headless | stdout [SUMMARY] only — no HTML for NinjaOne-triggered runs | |
| exe_parent/logs/ always | Same path regardless of USB vs local deployment; no branching | ✓ |

**User's choice:** `exe_parent/logs/ always`
**Notes:** No path branching needed. NinjaOne deploys the exe to a local folder; HTML lands there. Same behavior as USB runs.

---

## [SUMMARY] Line Format

| Option | Description | Selected |
|--------|-------------|----------|
| Human-readable pipe-delimited | `[SUMMARY] PHX-INV-001 \| Windows 11 Build 26100 \| Intel Core i7 \| 16 GB RAM \| 42% disk used \| 0 warnings` | ✓ |
| Key=value pairs | `[SUMMARY] hostname=X os_build=Y cpu="Z" ram_gb=W disk_pct=V warnings=N` | |
| Compact / minimal | `[SUMMARY] PHX-INV-001 Win11/26100 16GB 42% 0warn` | |

**User's choice:** Human-readable pipe-delimited
**Notes:** Easy to read in NinjaOne activity log at a glance. Pipe-delimited stays scannable.

---

## HKCU → HKLM MSIX Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Accept "Not Found" | Current code already returns (False, None) cleanly on HKCU failure; SC4 satisfied | ✓ |
| Add HKLM AppModel fallback | Try HKLM AppModel Packages if HKCU fails; detects enterprise all-user MSIX installs | |

**User's choice:** Accept "Not Found"
**Notes:** Claude Desktop is per-user MSIX; SYSTEM legitimately can't see it. "Not Found" is the correct and honest result.

---

## Claude's Discretion

- Exact `[SUMMARY]` field formatting for None/unavailable values
- Unit test approach for `isatty()` mock
- Exact placement of `[SUMMARY]` print in `main.py`

## Deferred Ideas

None.
