# Phase 9: Company Portal Detection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 09-company-portal-detection
**Areas discussed:** Enrollment when CP absent, Enrollment label format, Multiple enrollment GUIDs

---

## Enrollment when CP absent

| Option | Description | Selected |
|--------|-------------|----------|
| CP row: 'Not Found' only | Enrollment hidden when CP not installed | |
| CP row: 'Not Found (Enrolled)' | Enrollment shown in service column even when CP absent | ✓ |
| Separate 'Intune MDM' row always | Dedicated enrollment row independent of CP | |

**User's choice:** Show enrollment in service column even when Company Portal is "Not Found"
**Notes:** Motivated by NinjaOne/SYSTEM context — HKCU MSIX is inaccessible so CP always shows "Not Found" under headless execution, but HKLM enrollment IS readable. This preserves enrollment visibility in the primary use case.

---

## Enrollment label format

| Option | Description | Selected |
|--------|-------------|----------|
| Just 'Enrolled' / 'Not Enrolled' | Clean, no PII in the HTML file | |
| 'Enrolled: user@domain.com' | Include UPN for confirming which account | ✓ |
| You decide | Claude picks the right balance | |

**User's choice:** Include UPN email in the service column string
**Notes:** IT staff benefit from seeing the enrolled account, not just enrollment state.

---

## Multiple enrollment GUIDs

| Option | Description | Selected |
|--------|-------------|----------|
| First with a UPN (Recommended) | Return first GUID subkey with non-empty UPN | ✓ |
| All UPNs, comma-joined | Collect all UPN values and join | |
| You decide | Claude picks safest approach | |

**User's choice:** First GUID with a non-empty UPN wins
**Notes:** Multiple active enrollments are rare; first-found is predictable and keeps the UI clean.

---

## Claude's Discretion

- Exact registry path enumeration implementation
- Error handling for malformed GUID keys
- Whether enrollment helper is a standalone function or wired via APP_SPECS service_key mechanism

## Deferred Ideas

None.
