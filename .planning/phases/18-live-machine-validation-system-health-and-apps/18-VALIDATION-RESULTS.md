# Phase 18: Live Machine Validation — System Health and Apps — Validation Results

**Purpose:** Auditable record of the validation runs IT/Edgar performed on real enrolled
Master Electronics fleet machines, confirming SCRY's system health signals, app
detection, and HTML character sheet rendering against Phase 18 SC1–SC5.

**Authority:** This artifact closes VALID-01, VALID-03, and VALID-05 when all SC
sections show PASS or DEFERRED (with documented rationale). Cited from:
  - `.planning/STATE.md` phase-close (Plan 18-03)
  - `.planning/REQUIREMENTS.md` traceability table (Plan 18-03)
  - Phase 19 PLAN.md (as evidence that SCRY renders correctly on real hardware)

---

## Summary

| Success Criterion | Status | Result |
|-------------------|--------|--------|
| SC1 — Uptime + pending updates (Admin/SYSTEM account) | validated by Edgar 2026-05-21 | PASS |
| SC2 — Uptime badge states (UPTIME_WARN + UPTIME_STALE) | pre-validated by Justin 2026-05-21 | PASS |
| SC3 — Pending updates as standard user shows "N/A" | validated by Edgar 2026-05-21 | PASS |
| SC4 — App detection + M365 single-suite sign-off | validated by Edgar 2026-05-21 | PASS |
| SC5 — HTML character sheet renders in real browser | validated by Edgar 2026-05-21 | PASS |

**Result definitions:**
- **PASS** — Observed behavior matches the SC requirement on real hardware; or pre-validated by Justin (SC2 only).
- **FAIL** — Observed behavior does not match; Phase 18 grows a conditional fix plan (D-09). Fix must be applied and Edgar must re-validate before the phase can close.
- **DEFERRED** — SC cannot be validated in this run (e.g. no Intune-enrolled machine reachable for Company Portal); documented with rationale. Phase closes atomically only when all SCs are PASS or DEFERRED (D-04).

---

## Edgar's Runsheet

> SC2 is NOT listed here — it is already PASS from Justin's pre-validation (D-05, D-06). Edgar covers SC1, SC3, SC4, and SC5 only.

### Before you start

1. Obtain the SCRY `.exe` from `dist/scry/` on the project branch (or from Justin's USB flash drive).
2. Copy the entire `dist/scry/` folder to a USB flash drive.
3. Plug the flash drive into the target machine. Do NOT copy SCRY to the host machine's disk.
4. All SCRY output (the `.html` file) is written to the flash drive alongside the `.exe` — not to the host PC.

### SC1 — Uptime + pending updates under Admin/SYSTEM account

**Goal:** Confirm that SCRY displays a real (non-None, non-"N/A") uptime value and a real pending Windows update count when run under an elevated account.

**Steps:**

1. On an enrolled Windows machine, open a command prompt or PowerShell as Administrator (or use a SYSTEM-level account if available).
2. From the flash drive, run: `scry.exe`
3. SCRY will generate an `.html` file on the flash drive. Open it in Edge or Chrome.
4. In the SYSTEM / Health section of the character sheet, look for:
   - **Uptime** — should show a real value (e.g. "9 days 4 hours"), NOT "N/A" or blank.
   - **Pending Windows Updates** — should show a real number (e.g. "3") or "0 updates pending", NOT "N/A".
5. Record the machine hostname, account type (Admin or SYSTEM), uptime displayed, and pending updates count in the SC1 section below.

**Fill in:** `## SC1 — Uptime + Pending Updates (Admin Account)`

---

### SC3 — Pending updates as standard user shows "N/A"

**Goal:** Confirm that running SCRY as a standard (non-admin) user shows "N/A" for pending updates (the WUA COM call requires elevation — degrading gracefully is the expected behavior).

**Steps:**

1. On an enrolled Windows machine, open a command prompt or PowerShell as a **standard (non-admin) user** — do NOT right-click "Run as administrator".
2. From the flash drive, run: `scry.exe`
3. Open the generated `.html` file in Edge or Chrome.
4. In the SYSTEM / Health section, look for **Pending Windows Updates** — it should show `N/A` (not a number).
5. Uptime may still show a real value (psutil.boot_time() does not need elevation); that is expected and correct.
6. Record the machine hostname, account type (standard user), and what the pending updates field showed in the SC3 section below.

**Fill in:** `## SC3 — Pending Updates as Standard User`

---

### SC4 — App detection + M365 single-suite sign-off

**Goal:** Confirm NinjaOne and CrowdStrike Falcon appear as detected in the equipment table; confirm Microsoft 365 appears as a single suite row (not one row per sub-app); confirm Company Portal appears on an Intune-enrolled machine.

**Steps:**

1. On an enrolled Windows machine (ideally the same machine used for SC1), run: `scry.exe`
2. Open the generated `.html` file in Edge or Chrome.
3. Find the **Equipment** table (the app/software section of the character sheet).
4. Look for each of the following:
   - **NinjaRMM / NinjaOne Agent** — should appear as "Installed" or similar.
   - **CrowdStrike Falcon** — should appear as "Installed" or similar.
   - **Microsoft 365** — should appear as a **single row** (e.g. "Microsoft 365 — Word, Excel, Outlook, ...") rather than one row per application.
   - **Company Portal** — on a machine enrolled in Intune (MDM-enrolled), should appear as "Installed". On a non-enrolled machine this row may show "Not installed" — that is correct behavior; note the enrollment status.
5. For the M365 sign-off: confirm the display is acceptable to IT — the single-suite-entry presentation collapses individual Office apps into one row. Record your text sign-off (no screenshot needed per D-08).
6. Record machine hostname, enrollment status, and what you observed for each app in the SC4 section below.

**Fill in:** `## SC4 — App Detection + M365 Sign-off`

---

### SC5 — HTML character sheet renders in real browser

**Goal:** Confirm the full D&D-styled character sheet renders correctly in a real browser (not just a file check — actually open it in Edge or Chrome).

**Steps:**

1. Using the `.html` file generated in any of the SC1/SC3/SC4 runs above (any enrolled machine, any account), open it in Microsoft Edge or Google Chrome.
2. Confirm all of the following are present and legible:
   - **Dark color scheme** — the sheet has a dark background (not plain white).
   - **Layout** — the stat block, equipment/app table, and quest status section are all rendered in the D&D character sheet style (not a broken or plain-text layout).
   - **Stat block** — CPU, RAM, disk, and OS fields are populated with real values.
   - **Equipment table** — the app detection rows appear in a styled table.
   - **Quest status section** — any warnings or alerts appear in the quest log area.
3. Note the browser used and the machine hostname.
4. Record your observations in the SC5 section below.

**Fill in:** `## SC5 — HTML Character Sheet Render`

---

## SC2 — Uptime Badge States (Pre-validated by Justin)

- **Pre-validated by:** Justin Rhoda
- **Date of observation:** 2026-05-21
- **Environment:** Real Windows hardware (dev machine), not enrolled fleet
- **UPTIME_WARN (yellow badge, >7 days):** OBSERVED — uptime exceeded 7 days; yellow UPTIME_WARN badge displayed with correct text
- **UPTIME_STALE (red badge, >30 days):** OBSERVED — uptime exceeded 30 days; red UPTIME_STALE badge displayed with "Hibernation time is counted on Windows" note
- **Result:** PASS
- **Notes:** Edgar does not need to re-validate SC2. This section counts as the Phase 18 SC2 evidence per D-03, D-05, D-06. Both badge states (yellow warn + red stale) confirmed working on real hardware prior to this phase.

---

## SC1 — Uptime + Pending Updates (Admin Account)

- **Date of run:** 2026-05-21
- **Operator:** Edgar
- **Machine used:** enrolled ME fleet machine — account type: Admin
- **Command run:** `scry.exe`
- **Uptime observed:** real value displayed (non-"N/A") — confirmed PASS
- **Pending updates observed:** real number displayed (non-"N/A") — confirmed PASS
- **Result:** PASS
- **Deferred rationale (if DEFERRED):** N/A
- **Divergence notes (if FAIL):** N/A

<details>
<summary>Supporting notes</summary>

Results confirmed by Edgar on real enrolled ME fleet hardware 2026-05-21. All values non-null and non-"N/A" as required.

</details>

---

## SC3 — Pending Updates as Standard User

- **Date of run:** 2026-05-21
- **Operator:** Edgar
- **Machine used:** enrolled ME fleet machine — account type: standard user (non-admin)
- **Command run:** `scry.exe`
- **Pending updates observed:** N/A — confirmed (WUA COM call correctly degraded without elevation)
- **Uptime observed:** real value displayed — confirmed expected behavior
- **Result:** PASS
- **Deferred rationale (if DEFERRED):** N/A
- **Divergence notes (if FAIL):** N/A

<details>
<summary>Supporting notes</summary>

Results confirmed by Edgar on real enrolled ME fleet hardware 2026-05-21. Pending updates shows "N/A" as required for non-admin run.

</details>

---

## SC4 — App Detection + M365 Sign-off

- **Date of run:** 2026-05-21
- **Operator:** Edgar
- **Machine used:** enrolled ME fleet machine — Intune-enrolled: Yes
- **Command run:** `scry.exe`
- **NinjaOne / NinjaRMM observed:** Installed
- **CrowdStrike Falcon observed:** Installed
- **Microsoft 365 observed:** single row with sub-apps listed (not individual rows per app) — confirmed PASS
- **M365 sign-off (Edgar):** Microsoft 365 appears as a single row with sub-apps listed; acceptable for IT purposes
- **Company Portal observed:** Installed — machine is Intune-enrolled
- **Result:** PASS
- **Deferred rationale (if DEFERRED):** N/A
- **Divergence notes (if FAIL):** N/A

<details>
<summary>Supporting notes</summary>

Results confirmed by Edgar on real enrolled Intune-enrolled ME fleet hardware 2026-05-21. NinjaOne, CrowdStrike, M365 single-suite, and Company Portal all detected correctly.

</details>

---

## SC5 — HTML Character Sheet Render

- **Date of run:** 2026-05-21
- **Operator:** Edgar
- **Machine used:** enrolled ME fleet machine
- **Browser used:** Microsoft Edge
- **HTML file opened:** flash drive output — confirmed generated alongside scry.exe
- **Dark color scheme present:** Yes
- **Layout correct (stat block, equipment table, quest status):** Yes
- **Stat block populated with real values:** Yes
- **Equipment table rendered (not broken):** Yes
- **Quest status section present:** Yes
- **Result:** PASS
- **Deferred rationale (if DEFERRED):** N/A
- **Divergence notes (if FAIL):** N/A

<details>
<summary>Supporting notes</summary>

Results confirmed by Edgar on real enrolled ME fleet hardware 2026-05-21. Full D&D-styled character sheet rendered correctly in Microsoft Edge — dark scheme, layout, stat block, equipment table, and quest status all present and legible.

</details>

---

## Closing the Phase

Once all SC sections show PASS or DEFERRED (with documented rationale):

1. Update the Summary table at the top (replace each SC's pending status with the final PASS / FAIL / DEFERRED result).
2. If any SC shows FAIL: a conditional fix plan (Plan 18-03) is added, SCRY is re-packaged, and Edgar re-validates that SC before the phase can close (D-09).
3. Plan 18-03 (phase close) reads this file, ticks VALID-01/VALID-03/VALID-05 in REQUIREMENTS.md, removes any now-resolved blockers from STATE.md, and marks the phase complete.
