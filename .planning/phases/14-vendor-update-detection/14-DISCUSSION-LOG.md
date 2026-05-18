# Phase 14: Vendor Update Detection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-18
**Phase:** 14-vendor-update-detection
**Areas discussed:** Data model, Character sheet placement, Dell detection approach

---

## Data model

| Option | Description | Selected |
|--------|-------------|----------|
| New VendorUpdateStatus dataclass | installed / pending_count / scan_data_present; AuditReport gets dell_dcu and lenovo_lsu fields | ✓ |
| Flat fields on AuditReport | Individual fields following Phase 13 pattern | |
| Extend AppStatus / apps list | Pack pending count into service_state | |

**User's choice:** New VendorUpdateStatus dataclass

---

| Option | Description | Selected |
|--------|-------------|----------|
| Three states only | Errors go to collection_errors | ✓ |
| Include error field | Add error: str \| None to VendorUpdateStatus | |

**User's choice:** Three states only — no error field on the dataclass

---

| Option | Description | Selected |
|--------|-------------|----------|
| Bundle with --updates | Vendor detection runs only when --updates passed | ✓ |
| Always run | Sub-second passive reads, no flag needed | |

**User's choice:** Bundle with --updates
**Notes:** User raised the performance question themselves ("how long will vendor checks take?"). After clarifying that the checks are sub-second passive reads, user still chose to keep all update-related queries behind --updates for workflow consistency.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Rows omitted entirely | None values = omit vendor rows from character sheet | ✓ |
| Show "Not checked" | Vendor rows always appear with placeholder | |

**User's choice:** Rows omitted entirely when --updates not passed

---

## Character sheet placement

| Option | Description | Selected |
|--------|-------------|----------|
| Same "System Health" group | Fold vendor rows into Phase 13 reserved space | ✓ |
| New "Vendor Updates" section | Separate stat block group below System Health | |

**User's choice:** Same "System Health" group (Phase 13 D-15 reservation)

---

| Option | Description | Selected |
|--------|-------------|----------|
| "Unknown (no scan data)" | Phase 14 SC2 exact wording | ✓ |
| "Installed (not scanned)" | More concise alternative | |

**User's choice:** "Unknown (no scan data)"

---

## Dell detection approach

| Option | Description | Selected |
|--------|-------------|----------|
| Registry Uninstall sweep | display_name_keywords pattern from apps.py | ✓ |
| Filesystem path check | Check dcu.exe / install directory | |
| Registry + filesystem | Belt and suspenders | |

**User's choice:** Registry Uninstall sweep

---

| Option | Description | Selected |
|--------|-------------|----------|
| One known default path | C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml | ✓ |
| Ordered fallback list | Multiple candidate paths for version resilience | |

**User's choice:** One known default path — no fallback list

---

| Option | Description | Selected |
|--------|-------------|----------|
| Registry Uninstall sweep (LSU) | display_name_keywords: ["Lenovo System Update"] | ✓ |
| Filesystem path check | tvsu.exe at known install directory | |

**User's choice:** Registry Uninstall sweep — consistent with DCU detection

---

| Option | Description | Selected |
|--------|-------------|----------|
| New collectors/windows/vendor.py | Separate module per one-concern-per-file pattern | ✓ |
| Extend collectors/windows/hardware.py | Append alongside collect_pending_updates | |

**User's choice:** New collectors/windows/vendor.py

---

## Claude's Discretion

- Exact row label text for vendor rows in System Health section
- Whether UNINSTALL_PATHS is imported from apps.py or extracted to a shared helper
- DCUApplicableUpdates.xml element/attribute structure (researcher to confirm)
- Test fixture approach for "DCU installed but XML absent" and "DCU not installed" paths

## Deferred Ideas

None.
