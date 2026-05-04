# Phase 1: Models and Hostname Parser - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 01-models-and-hostname-parser
**Areas discussed:** Partial match handling, City code strictness, Dept code policy, Unknown data preservation

---

## Partial Match Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Treat as Warehouse Workstation | Device type inferred from structure; dept=NEWDEPT preserved as-is | ✓ |
| Fall through to Unknown | Only recognized dept codes produce a typed device_type | |
| Partial: type determined, dept flagged | device_type set, dept_known=False flag added | |

**User's choice:** Treat as Warehouse Workstation  
**Notes:** Structure determines device type, not code whitelists. Applied consistently to both dept codes (warehouse) and company codes (user laptops).

### User-Assigned Laptop partial match

| Option | Description | Selected |
|--------|-------------|----------|
| User-Assigned Laptop, company preserved | Pattern match wins; company_code preserved | ✓ |
| Unknown — must be recognized company code | Strict: only ME/ES/EC/AP/OL map to User-Assigned Laptop | |

**User's choice:** User-Assigned Laptop, company preserved  
**Notes:** Consistent with warehouse partial match decision above.

---

## City Code Strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Unknown — unrecognized city = Unknown | Strict; city prefix must be in 21-code list | ✓ |
| Attempt device type from structure anyway | Even with unrecognized city, parse device type from segments | |
| Unknown, but city preserved as raw string | Unrecognized city → device_type=Unknown, city_raw preserved | |

**User's choice:** Unknown — unrecognized city = Unknown  
**Notes:** City is the first gate. Unrecognized city → don't attempt further parsing. This is the opposite policy from dept codes (which are accepted even when unknown) — the distinction is that city code is the root identifier; dept code is a sub-classification within an already-valid hostname.

### City code failure mode

| Option | Description | Selected |
|--------|-------------|----------|
| Silent Unknown — show device type as Unknown in sheet | Tool renders Unknown class; IT knows to update list | ✓ |
| Preserve raw hostname prominently | Prominently surfaces full raw hostname when city unrecognized | |

**User's choice:** Silent Unknown  
**Notes:** Raw hostname is always preserved (per ROADMAP success criterion SC-3); the "silent" refers to no special error state or warning beyond Unknown device type.

---

## Department Code Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Pattern-based — any short uppercase segment valid | Structure determines type; dept code accepted regardless | ✓ |
| Whitelist — only known codes produce Warehouse Workstation | Unknown dept → Unknown device type | |

**User's choice:** Pattern-based  
**Notes:** Consistent with partial match handling decision. Future IT dept additions work without parser updates.

### Test coverage approach

| Option | Description | Selected |
|--------|-------------|----------|
| Pattern + representative sample | Test pattern with INV, SHP, REC + one unrecognized code | ✓ |
| All 20 known codes individually | One test per known dept code | |

**User's choice:** Pattern + representative sample  
**Notes:** The roadmap success criterion says "all known dept codes covered" — this will be interpreted as the pattern covering all known codes, verified with a representative sample, not 20 near-identical tests.

---

## Unknown Hostname Data Preservation

| Option | Description | Selected |
|--------|-------------|----------|
| device_type=Unknown, raw_hostname set, all other fields None | Clean contract; callers check device_type first | ✓ |
| device_type=Unknown, try to extract partial segment data | Split on hyphens even for malformed hostnames | |

**User's choice:** device_type=Unknown, raw_hostname, all other fields None  
**Notes:** Applies to fully unrecognized hostnames (e.g., DESKTOP-XYZ123).

### Near-miss data preservation

| Option | Description | Selected |
|--------|-------------|----------|
| city=Phoenix preserved, device_type=Unknown | City prefix matched; preserve it | ✓ |
| Fully Unknown — all fields None except raw_hostname | Simpler contract | |

**User's choice:** city preserved, device_type=Unknown  
**Notes:** If city parsed successfully before structure parsing failed, that partial result is surfaced. Gives IT staff useful context about which office the machine belongs to.

---

## Claude's Discretion

- CollectionResult generic typing (`CollectionResult[T]` vs. plain)
- AppStatus field design (installed, version, service_state shape)
- Exact module/file layout within models.py

## Deferred Ideas

None.
