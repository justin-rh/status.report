---
phase: 14-vendor-update-detection
plan: 01
subsystem: vendor-update-detection
tags: [models, collector, tdd, registry, xml-parse, windows]
dependency_graph:
  requires:
    - collectors/windows/apps.py (_search_uninstall_keys)
    - models.py (AuditReport, Warning — Phase 13)
  provides:
    - models.VendorUpdateStatus
    - models.AuditReport.dell_dcu
    - models.AuditReport.lenovo_lsu
    - collectors.windows.vendor.collect_vendor_updates
  affects:
    - main.py (two --updates gate blocks)
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN per task (test_models_phase14.py, test_vendor_collector.py)
    - lazy inline import (matching existing collect_pending_updates pattern)
    - never-raises collector (D-03 pattern from Phase 13)
    - registry-only detection (no CLI invocation)
    - passive XML parse for pending count
key_files:
  created:
    - models.py (VendorUpdateStatus dataclass + AuditReport fields)
    - collectors/windows/vendor.py
    - tests/test_models_phase14.py
    - tests/test_vendor_collector.py
  modified:
    - models.py
    - main.py
decisions:
  - "DCU_XML_PATH hardcoded per D-11 — passive read of Dell-written file, never written by SCRY"
  - "LSU pending_count always None per D-14 — no passive XML source exists for Lenovo System Update"
  - "VendorUpdateStatus has no error field per D-03 — errors set installed=None and append to collection_errors"
metrics:
  duration_seconds: 195
  completed_date: "2026-05-18"
  tasks_completed: 3
  files_changed: 5
---

# Phase 14 Plan 01: Vendor Update Detection Data Model and Collector Summary

VendorUpdateStatus dataclass with registry-only DCU/LSU detection and passive DCU XML parsing; 18 new tests; main.py wired at both --updates gate locations.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add VendorUpdateStatus tests | f437247 | tests/test_models_phase14.py |
| 1 (GREEN) | Add VendorUpdateStatus dataclass and AuditReport fields | 77bf291 | models.py |
| 2 (RED) | Add failing vendor collector tests | 78922cb | tests/test_vendor_collector.py |
| 2 (GREEN) | Create collectors/windows/vendor.py | 1440add | collectors/windows/vendor.py |
| 3 | Wire collect_vendor_updates into main.py | aa78757 | main.py |

## What Was Built

**Task 1 — models.py extensions:**
- `VendorUpdateStatus` dataclass with `installed: bool|None`, `pending_count: int|None`, `scan_data_present: bool`
- Inserted between `Warning` and `AuditReport` classes
- `AuditReport.dell_dcu` and `AuditReport.lenovo_lsu` fields (both `VendorUpdateStatus|None=None`)
- Field order: `pending_updates` → `dell_dcu` → `lenovo_lsu` → `local_profiles`

**Task 2 — collectors/windows/vendor.py (new file):**
- `collect_vendor_updates(report)` public function — entry point
- `_detect_dcu()`: registry search via `_search_uninstall_keys(["Dell Command Update", "Dell Command | Update"])`; if installed, reads `DCU_XML_PATH` with `xml.etree.ElementTree`; counts `<update>` child elements
- `_detect_lsu()`: registry search via `_search_uninstall_keys(["Lenovo System Update"])`; pending_count always None (no passive source)
- Never invokes CLI executables (dcu-cli.exe, tvsu.exe) — registry-only per VENDOR-01/VENDOR-02
- Never raises — exceptions set `installed=None` and append to `collection_errors`

**Task 3 — main.py wiring:**
- Two `--updates` guard blocks updated: `_run_cli()` (line 56–60) and `main()` (line 123–129)
- Lazy inline import style matching existing `collect_pending_updates` pattern
- Both retain `sys.platform != "darwin"` guard unchanged

## Test Results

- **test_models_phase14.py**: 8 tests — VendorUpdateStatus variants and AuditReport field order
- **test_vendor_collector.py**: 10 tests — DCU/LSU registry detection, XML parsing (2 updates, 0 updates, parse error, absent), never-raises, error appended to collection_errors
- **Full suite**: 274 passed (256 prior + 18 new); no regressions

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All fields are wired and populated by the collector. Plan 02 (renderer) will surface dell_dcu/lenovo_lsu in the character sheet.

## Threat Flags

No new threat surface beyond what was documented in the plan's threat model (T-14-01 through T-14-04). All mitigations implemented:
- T-14-01 (ET.ParseError caught, sets pending_count=None, scan_data_present=True)
- T-14-04 (no CLI invocation confirmed by grep acceptance criterion)

## Self-Check: PASSED

- [x] models.py contains VendorUpdateStatus (line 62)
- [x] models.py contains dell_dcu and lenovo_lsu after pending_updates
- [x] collectors/windows/vendor.py exists with collect_vendor_updates exported
- [x] tests/test_models_phase14.py exists (8 tests)
- [x] tests/test_vendor_collector.py exists (10 tests)
- [x] main.py has 4 occurrences of collect_vendor_updates
- [x] Commits f437247, 77bf291, 78922cb, 1440add, aa78757 all exist
- [x] 274 tests passing
