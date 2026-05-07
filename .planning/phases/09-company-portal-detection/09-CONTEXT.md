# Phase 9: Company Portal Detection - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Add Company Portal (UWP/MSIX) detection and Intune MDM enrollment status to the equipment table. Two distinct signals in one row: whether the app is installed, and whether the device is enrolled in Intune MDM. No other app detection changes.

The MSIX detection follows the existing `_detect_msix()` + `APP_SPECS` pattern. MDM enrollment is read from HKLM (readable under SYSTEM account) via the Enrollments registry path. No new detection infrastructure needed.

</domain>

<decisions>
## Implementation Decisions

### Enrollment when Company Portal is not installed
- **D-01:** When Company Portal is NOT installed but the device IS enrolled in Intune, surface enrollment in the Service column of the "Not Found" CP row — e.g., `service_state = "Enrolled: user@domain.com"` even when `installed = False`. This makes enrollment visible when running under NinjaOne/SYSTEM, where HKCU MSIX is inaccessible so CP always appears as "Not Found" but HKLM enrollment data is still readable.
- **D-02:** When the device is not enrolled (no GUID with a non-empty UPN), the Service column for the CP row is empty/None (same behavior as other apps with no service key).

### Enrollment label format
- **D-03:** When enrolled, the Service column contains `"Enrolled: {UPN}"` where `{UPN}` is the UPN email value from the registry (e.g., `"Enrolled: justin.rhoda@masterelectronics.com"`). This gives IT the confirming detail of which account is enrolled, not just whether enrollment exists.
- **D-04:** When not enrolled (no non-empty UPN found), Service column is None — the template renders nothing for that cell, consistent with unenrolled apps.

### Multiple enrollment GUIDs
- **D-05:** Iterate all GUID subkeys under `HKLM\SOFTWARE\Microsoft\Enrollments`. Return the UPN from the FIRST subkey that has a non-empty UPN value. Multiple active enrollments are rare in practice; first-found is predictable and avoids a long comma-joined string in the UI.
- **D-06:** A GUID subkey with a missing or empty UPN is treated as a stale artifact — it does NOT count as enrollment (ROADMAP SC3). Only non-empty UPN values constitute enrollment evidence.

### MSIX detection
- **D-07:** Use `msix_family_prefix = "Microsoft.CompanyPortal_"` — the standard MSIX family name for the Intune Company Portal app. This uses the existing `_detect_msix()` function, same as Claude detection.
- **D-08:** Under SYSTEM account (NinjaOne), HKCU is absent so `_detect_msix()` returns `(False, None)` — Company Portal shows as "Not Found". This is expected and honest per Phase 8 D-09. The enrollment check still runs (it reads HKLM, which is accessible under SYSTEM).

### AppStatus model
- **D-09:** No model changes needed. `service_state: str | None` on `AppStatus` carries the enrollment string (e.g., `"Enrolled: user@domain.com"`). The existing template Service column logic already renders `service_state` — no template changes needed for the string itself.

### Claude's Discretion
- Exact registry path enumeration (iterating subkeys vs direct key access)
- Error handling for malformed GUID keys (missing expected subkey structure)
- Whether to add a `service_key`-like field to APP_SPECS or implement via a dedicated MDM enrollment helper function

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §APP-V2-01 — Company Portal detection + MDM enrollment status in Service column
- `.planning/ROADMAP.md` §Phase 9 — Success criteria SC1–SC4 (definitive acceptance bar)

### Source Files to Modify
- `collectors/windows/apps.py` — Add Company Portal to `APP_SPECS`; implement MDM enrollment helper; wire into `_detect_one_app()`
- `models.py` — Read-only verification that `AppStatus.service_state` is sufficient (no change expected)

### Prior Phase Context
- `.planning/phases/04-app-detection-and-compliance-engine/04-CONTEXT.md` — APP_SPECS pattern, MSIX detection, _detect_msix() design
- `.planning/phases/08-ninjaone-compatibility/08-CONTEXT.md` — D-08/D-09: HKCU inaccessible under SYSTEM, "Not Found" is honest result; HKLM IS accessible under SYSTEM

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_detect_msix(family_prefix)` in `collectors/windows/apps.py:159` — Direct reuse with `"Microsoft.CompanyPortal_"` prefix; already handles HKCU absence cleanly
- `_search_uninstall_keys()` — Standard Uninstall sweep; Company Portal is MSIX-only, so this is fallback/redundant (but no harm)
- `APP_SPECS` list — Add one dict entry for Company Portal; `_detect_one_app()` drives detection automatically
- `AppStatus.service_state: str | None` in `models.py:44` — Already present; will carry `"Enrolled: {UPN}"` or None

### Established Patterns
- All app detection is config-driven via `APP_SPECS`; no ad-hoc per-app code paths in `detect_apps()`
- MSIX detection is via `msix_family_prefix` key in the spec dict
- Service-column data comes from `service_state` field; `_read_service_start()` is the existing pattern for reading service registry — a parallel `_detect_mdm_enrollment()` helper follows the same shape
- Never raises across layer boundary — wrap enrollment lookup in try/except and return None on failure

### Integration Points
- `APP_SPECS` in `apps.py:55` — append one new dict entry
- `_detect_one_app()` in `apps.py:234` — enrollment hook runs after MSIX detection sets `installed`; sets `service_state` from enrollment result
- `detect_apps()` drives everything; no changes needed there

</code_context>

<specifics>
## Specific Details

- MSIX family prefix: `"Microsoft.CompanyPortal_"` (standard Intune Company Portal package family name)
- MDM enrollment registry path: `HKLM\SOFTWARE\Microsoft\Enrollments\{GUID}\UPN`
  - Enumerate all GUID subkeys under `HKLM\SOFTWARE\Microsoft\Enrollments`
  - For each GUID, attempt `QueryValueEx(subkey, "UPN")` — return first non-empty string as enrolled UPN
  - If no GUID has a non-empty UPN → not enrolled → `service_state = None`
- Service column content when enrolled: `"Enrolled: {UPN}"` (e.g., `"Enrolled: justin.rhoda@masterelectronics.com"`)
- Service column content when not enrolled: `None` (renders as empty in template)
- When CP not installed but enrolled: `AppStatus(name="Company Portal", installed=False, version=None, service_state="Enrolled: user@domain.com")`
- Stale GUID rule: `QueryValueEx` returns empty string or raises `FileNotFoundError` → skip that GUID, not enrolled

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-company-portal-detection*
*Context gathered: 2026-05-07*
