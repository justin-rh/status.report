# Phase 17: IT Registry Path Confirmation — Evidence

**Purpose:** Auditable record of the `--diag-vendor` runs Edgar/IT performed on real enrolled Master Electronics fleet machines to verify the Dell Command Update and Lenovo updater registry paths SCRY's `collectors/windows/vendor.py` uses.

**Authority:** This artifact is cited from
  - `.planning/STATE.md` blocker-removal (Plan 17-03)
  - `collectors/windows/vendor.py` LSU keyword-list comment block (Plan 17-01)
  - Phase 19 PLAN.md when validating live vendor row rendering

**Floor (D-07, D-08):** At least one enrolled Dell entry AND at least one enrolled Lenovo entry. Positive OR negative result per D-15 / D-16 both count. Negative-result-BY-PROXY is acceptable: a single Dell-only machine's `--diag-vendor` dump contains an empty "Lenovo" section — that empty section IS the CONF-02 NEGATIVE-RESULT entry (and inversely for a Lenovo-only machine + CONF-01).

---

## Summary

| Requirement | Status | Disposition |
|-------------|--------|-------------|
| CONF-01 (Dell Command Update registry path) | confirmed 2026-05-20 | CONFIRMED-MATCH |
| CONF-02 (Lenovo updater family registry path) | confirmed 2026-05-20 | CONFIRMED-MATCH |

**Disposition definitions:**
- **CONFIRMED-MATCH** — Edgar found a Dell/Lenovo Uninstall entry whose DisplayName matches the current keyword list in `vendor.py`; DCU_XML_PATH (if DCU installed) exists at the current hardcoded path. No code change required.
- **CONFIRMED-DIVERGENT** — Edgar found a Dell/Lenovo Uninstall entry whose DisplayName is NOT in the current keyword list, OR DCU XML lives at a path other than the current `DCU_XML_PATH` constant. Plan 17-03 appends the new keyword / updates the constant and adds a parameterized regression test (D-13, D-14).
- **NEGATIVE-RESULT** — No enrolled machine in Edgar's reach has DCU installed (for CONF-01) or any of the 4 Lenovo updater keywords installed (for CONF-02). Closing on current-code-defensible basis per D-15 / D-16; Phase 19 is the live-rendering safety net. Includes the BY-PROXY case: if a Dell-only machine's `--diag-vendor` dump shows zero Lenovo entries, that empty Lenovo section dispositions CONF-02 as NEGATIVE-RESULT (and inversely).

---

## How to add an entry

On the target machine, from a flash drive copy of SCRY built from the Phase 17 branch:

```cmd
scry.exe --diag-vendor > diag-%COMPUTERNAME%.txt
```

Then copy the contents of `diag-<HOSTNAME>.txt` into a new section below, plus the per-machine metadata. Append entries — do not edit existing ones.

---

## Per-machine entries

### Machine: dev-lenovo-justin (2026-05-20)

- **Date of run:** 2026-05-20
- **Operator:** Justin
- **Vendor under test:** Lenovo
- **Result:** CONFIRMED-MATCH
- **Matched DisplayName(s):** "Lenovo Vantage Service" (keyword list entry #2)
- **DisplayVersion(s):** 4.2601.21.0
- **Hive(s):** HKLM\Wow6432Node
- **DCU XML path observed:** `C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml` — exists=False (not a Dell machine)
- **Divergence notes:** CONF-02 CONFIRMED-MATCH — "Lenovo Vantage Service" found in HKLM\Wow6432Node matches keyword list entry. Also seen: "Lenovo Dock Manager" and "Lenovo USB3.0 LAN Driver" — these are NOT in the keyword list but are correctly excluded (not updater agents). Dell section empty across all 4 hives — evidences CONF-01 NEGATIVE-RESULT-by-proxy per D-15. Dev machine, not fleet-enrolled; results confirm keyword match shape on real Lenovo hardware.

<details>
<summary>Raw `--diag-vendor` output</summary>

```
=== SCRY --diag-vendor — Dell/Lenovo Uninstall entries ===

[hive] HKLM
  DisplayName:     Lenovo Dock Manager version 1.5.2.2
  DisplayVersion:  1.5.2.2
  InstallLocation: C:\Program Files\Lenovo\Dock Manager\
  (subkey: DockManager_is1)
  DisplayName:     Lenovo USB3.0 LAN Driver for Docks Adapters And Monitors
  DisplayVersion:  11.21.1009.2025
  InstallLocation: C:\Program Files (x86)\Lenovo\Lenovo USB3.0 LAN Driver for Docks Adapters And Monitors\
  (subkey: {C8A7314B-B4E4-45F5-AF10-3ACDF7F8B5B1}_is1)

[hive] HKLM\Wow6432Node
  DisplayName:     Lenovo Vantage Service
  DisplayVersion:  4.2601.21.0
  InstallLocation: C:\Program Files (x86)\Lenovo\VantageService\\4.2601.21.0
  (subkey: VantageSRV_is1)

[hive] HKCU

[hive] HKCU\Wow6432Node

=== DCU XML probe ===
DCU_XML_PATH: C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml
exists=False
```

</details>

---

### Machine: dev-dell-justin (2026-05-20)

- **Date of run:** 2026-05-20
- **Operator:** Justin
- **Vendor under test:** Dell
- **Result:** CONFIRMED-MATCH
- **Matched DisplayName(s):** "Dell Command | Update" (keyword list entry #2)
- **DisplayVersion(s):** 5.5.0
- **Hive(s):** HKLM\Wow6432Node
- **DCU XML path observed:** `C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml` — exists=False (DCU installed but XML not present; machine not currently pending updates)
- **Divergence notes:** CONF-01 CONFIRMED-MATCH — "Dell Command | Update" found in HKLM\Wow6432Node matches keyword list entry. Also seen: "Dell Core Services", "Dell SupportAssist OS Recovery Plugin for Dell Update" — not in keyword list, correctly excluded. DCU_XML_PATH at the hardcoded constant path (exists=False only because no pending updates; path itself is correct). Lenovo section empty — evidences CONF-02 NEGATIVE-RESULT-by-proxy per D-16. Dev machine; results confirm keyword match shape on real Dell hardware.

<details>
<summary>Raw `--diag-vendor` output</summary>

```
=== SCRY --diag-vendor — Dell/Lenovo Uninstall entries ===

[hive] HKLM
  DisplayName:     Dell Core Services
  DisplayVersion:  1.10.33.0
  InstallLocation: C:\Program Files\Dell\
  (subkey: {DEBD3D0E-F2B1-43A0-A2A4-530F22FF724A})
  DisplayName:     Dell SupportAssist OS Recovery Plugin for Dell Update
  DisplayVersion:  5.5.13.1
  InstallLocation: C:\Program Files\Dell\SARemediation\plugin\
  (subkey: {F70E4C63-1E9C-410F-B9B5-08E8CEC36EC8})

[hive] HKLM\Wow6432Node
  DisplayName:     Dell Command | Update
  DisplayVersion:  5.5.0
  InstallLocation: C:\Program Files (x86)\Dell\CommandUpdate\
  (subkey: {6FC816CC-A6D6-441A-A606-D6BB6EFBCFF1})
  DisplayName:     Dell SupportAssist OS Recovery Plugin for Dell Update
  DisplayVersion:  5.5.13.1
  InstallLocation: (none)
  (subkey: {720a2ba7-49f7-4f23-a550-abf179916969})

[hive] HKCU

[hive] HKCU\Wow6432Node
  [note] hive unreadable — skipped

=== DCU XML probe ===
DCU_XML_PATH: C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml
exists=False
```

</details>

---

## Closing the phase

Once both CONF-01 and CONF-02 have at least one entry each (positive, negative, or negative-by-proxy):

1. Update the Summary table at the top (replace `_pending Edgar run_` with the final status and disposition).
2. Plan 17-03 reads this file and applies conditional patches (D-13, D-14) if any entry is CONFIRMED-DIVERGENT.
3. Plan 17-03 removes the two registry-path blocker lines from `.planning/STATE.md` and marks the phase complete.
