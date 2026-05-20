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
| CONF-01 (Dell Command Update registry path) | _pending Edgar run_ | _TBD: CONFIRMED-MATCH / CONFIRMED-DIVERGENT / NEGATIVE-RESULT_ |
| CONF-02 (Lenovo updater family registry path) | _pending Edgar run_ | _TBD: CONFIRMED-MATCH / CONFIRMED-DIVERGENT / NEGATIVE-RESULT_ |

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

<!-- Add one section per machine. Floor: 1 Dell + 1 Lenovo (positive or negative). -->
<!-- Each section MUST contain: hostname, date, and either (a) matched DisplayName/Version/hive OR (b) explicit negative-result note. -->

### Entry template (copy for each new entry)

```markdown
### Machine: <HOSTNAME>

- **Date of run:** YYYY-MM-DD
- **Operator:** Edgar (or name)
- **Vendor under test:** Dell | Lenovo | both
- **Result:** CONFIRMED-MATCH | CONFIRMED-DIVERGENT | NEGATIVE-RESULT
- **Matched DisplayName(s):** e.g. "Dell Command | Update", "Lenovo Vantage" — or "none" for negative result
- **DisplayVersion(s):** e.g. "5.5.0" — or "n/a" for negative result
- **Hive(s):** HKLM | HKLM\Wow6432Node | HKCU | HKCU\Wow6432Node — or "n/a"
- **DCU XML path observed:** path string from `--diag-vendor` output, exists=true/false, size, update count — or "n/a" if not Dell or not installed
- **Divergence notes:** any DisplayName seen in the dump that is NOT in the current keyword list, or any unexpected DCU_XML_PATH location — or "none". For NEGATIVE-RESULT-by-proxy: state which CONF-ID this section evidences as negative (e.g. "this Dell-only machine's empty Lenovo section evidences CONF-02 NEGATIVE-RESULT per D-16").

<details>
<summary>Raw `--diag-vendor` output</summary>

```
<paste full stdout of `scry.exe --diag-vendor` here>
```

</details>
```

---

## Closing the phase

Once both CONF-01 and CONF-02 have at least one entry each (positive, negative, or negative-by-proxy):

1. Update the Summary table at the top (replace `_pending Edgar run_` with the final status and disposition).
2. Plan 17-03 reads this file and applies conditional patches (D-13, D-14) if any entry is CONFIRMED-DIVERGENT.
3. Plan 17-03 removes the two registry-path blocker lines from `.planning/STATE.md` and marks the phase complete.
