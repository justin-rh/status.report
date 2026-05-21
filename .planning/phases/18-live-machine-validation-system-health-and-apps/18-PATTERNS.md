# Phase 18: Live Machine Validation — System Health and Apps - Pattern Map

**Mapped:** 2026-05-21
**Files analyzed:** 4 (1 new planning artifact, 1 STATE.md update, 1 REQUIREMENTS.md update, 0 new code files — conditional code fix only if a SC fails)
**Analogs found:** 3 / 4 (1 new planning artifact has a direct prior-phase analog; planning doc edits have exact analogs; conditional code fix has no analog until triggered)

---

## File Classification

| New/Modified File | New/Modify | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------------|------|-----------|----------------|---------------|
| `18-VALIDATION-RESULTS.md` | New | planning artifact (IT-authored execution evidence) | n/a — human-authored doc | `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` | exact — same role, same purpose (IT run evidence), same section structure |
| `.planning/STATE.md` | Modify | GSD state document | n/a — YAML+markdown | Phase 17 Plan 17-03 Task 3 STATE.md edit (git commit applying `status: phase-complete`, advancing phase pointer, updating blockers) | exact |
| `.planning/REQUIREMENTS.md` | Modify | GSD requirements tracking | n/a — markdown tables + checkboxes | Phase 17 Plan 17-03 Task 3 REQUIREMENTS.md edit (ticking CONF-01/CONF-02 checkboxes, updating traceability table) | exact |
| `collectors/windows/hardware.py` (conditional) | Modify | collector | registry read + WUA COM + psutil | self — existing `collect_pending_updates()` and `_collect_uptime()` | exact (self-extension if SC1/SC3 fail) |
| `collectors/windows/apps.py` (conditional) | Modify | collector | registry read (4 hives) | self — existing `_search_uninstall_keys`, NinjaOne/CrowdStrike/M365/Company Portal specs | exact (self-extension if SC4 fails) |
| `health_checks.py` (conditional) | Modify | business logic | transform | self — existing `check_uptime_warning()` at lines 132–161 | exact (self-extension if SC2 fails — unlikely given pre-validation) |
| `renderer/__init__.py` (conditional) | Modify | renderer | request-response (report → HTML) | self — existing `render_html()` | exact (self-extension if SC5 fails) |

---

## Pattern Assignments

### `18-VALIDATION-RESULTS.md` (new planning artifact)

**Analog:** `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md`

This is the primary deliverable of Phase 18 Plan 18-01. The structure is derived directly from `17-IT-CONFIRMATION.md`, adapted to the per-SC (success-criterion) structure dictated by CONTEXT.md D-02 rather than per-CONF-ID.

**Top-level header block pattern** (from `17-IT-CONFIRMATION.md` lines 1–10):
```markdown
# Phase 18: Live Machine Validation — System Health and Apps — Validation Results

**Purpose:** Auditable record of the validation runs IT/Edgar performed on real enrolled
Master Electronics fleet machines, confirming SCRY's system health signals, app
detection, and HTML character sheet rendering against Phases 18 SC1–SC5.

**Authority:** This artifact closes VALID-01, VALID-03, and VALID-05 when all SC
sections show PASS or DEFERRED. Cited from:
  - `.planning/STATE.md` phase-close (Plan 18-03)
  - `.planning/REQUIREMENTS.md` traceability table (Plan 18-03)
  - Phase 19 PLAN.md (as evidence that SCRY renders correctly on real hardware)
```

**Summary table pattern** (from `17-IT-CONFIRMATION.md` lines 16–26):
```markdown
## Summary

| Success Criterion | Status | Result |
|-------------------|--------|--------|
| SC1 — Uptime + pending updates (Admin/SYSTEM account) | _pending Edgar run_ | PASS / FAIL / DEFERRED |
| SC2 — Uptime badge states (UPTIME_WARN + UPTIME_STALE) | pre-validated by Justin 2026-05-21 | PASS |
| SC3 — Pending updates as standard user shows "N/A" | _pending Edgar run_ | PASS / FAIL / DEFERRED |
| SC4 — App detection + M365 single-suite sign-off | _pending Edgar run_ | PASS / FAIL / DEFERRED |
| SC5 — HTML character sheet renders in real browser | _pending Edgar run_ | PASS / FAIL / DEFERRED |

**Result definitions:**
- **PASS** — Edgar observed the expected behavior on real hardware; or pre-validated by Justin (SC2 only).
- **FAIL** — Edgar observed incorrect behavior; Phase 18 grows a conditional fix plan (D-09).
- **DEFERRED** — SC cannot be validated in this run (e.g. no Intune-enrolled machine reachable for Company
  Portal); documented with rationale. Phase closes atomically only when all SCs are PASS or DEFERRED (D-04).
```

**Pre-populated SC2 section pattern** (CONTEXT.md D-03/D-05 mandate this is filled in before Edgar's run):
```markdown
## SC2 — Uptime Badge States (Pre-validated by Justin)

- **Pre-validated by:** Justin Rhoda
- **Date of observation:** 2026-05-21
- **Environment:** Real Windows hardware (dev machine), not enrolled fleet
- **UPTIME_WARN (yellow badge, >7 days):** OBSERVED — uptime exceeded 7 days; yellow badge displayed
  with correct text
- **UPTIME_STALE (red badge, >30 days):** OBSERVED — uptime exceeded 30 days; red badge displayed
  with "Hibernation time is counted on Windows" note
- **Result:** PASS
- **Notes:** Edgar does not need to re-validate SC2. This section counts as the Phase 18 SC2 evidence
  (D-03, D-05, D-06).
```

**Per-SC section template** (all other SCs follow this shape; adapts from `17-IT-CONFIRMATION.md` per-machine entry template at lines 127–149):
```markdown
## SC<N> — <Short Title>

- **Date of run:** YYYY-MM-DD
- **Operator:** Edgar (or name)
- **Machine(s) used:** <HOSTNAME(s)> — account type (Admin / SYSTEM / standard user)
- **Command run:** `scry.exe` (or with specific flags if needed)
- **What was observed:** <Edgar's text description of what appeared in the HTML character sheet or stdout>
- **Result:** PASS | FAIL | DEFERRED
- **Deferred rationale (if DEFERRED):** <reason, e.g. "No Intune-enrolled machine reachable this run">
- **Divergence notes (if FAIL):** <exact symptom; Plan 18-03 conditional fix reads this>

<details>
<summary>Supporting notes / screenshot description</summary>

<paste any supporting observations here; no screenshot required per D-08>

</details>
```

**Phase-close instructions section pattern** (from `17-IT-CONFIRMATION.md` lines 142–148):
```markdown
## Closing the Phase

Once all SC sections show PASS or DEFERRED (with documented rationale):

1. Update the Summary table at the top (replace `_pending Edgar run_` with final result).
2. If any SC shows FAIL: a conditional fix plan (Plan 18-03) is added, SCRY is re-packaged,
   and Edgar re-validates that SC before the phase can close (D-09).
3. Plan 18-03 (phase close) reads this file, ticks VALID-01/VALID-03/VALID-05 in REQUIREMENTS.md,
   removes any now-resolved blockers from STATE.md, and marks the phase complete.
```

---

### Plan 18-01 structure (runsheet creation + artifact skeleton)

**Analog:** Phase 17 Plan 17-02 Task 1 (`Create 17-IT-CONFIRMATION.md skeleton template`)

**Plan frontmatter pattern** (from `17-02-PLAN.md` lines 1–16):
```yaml
---
phase: 18-live-machine-validation-system-health-and-apps
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/18-live-machine-validation-system-health-and-apps/18-VALIDATION-RESULTS.md
autonomous: true
requirements: [VALID-01, VALID-03, VALID-05]
requirements_addressed: []   # none closed yet — artifact only
user_setup: []
---
```

**Skeleton-template task action pattern** (from `17-02-PLAN.md` lines 77–163, Task 1):
- Create the artifact with all section headers, the pre-populated SC2 section, and fill-in templates for SC1/SC3/SC4/SC5.
- Constraints mirror `17-02-PLAN.md` Task 1 constraints: do NOT prefill real Edgar entries; the skeleton + Justin's SC2 pre-validation are the only content.
- Verify with: `python -c "import pathlib; p = pathlib.Path('...18-VALIDATION-RESULTS.md'); assert p.exists() and 'SC1' in p.read_text() and 'SC4' in p.read_text() and 'PASS' in p.read_text()"`

---

### Plan 18-02 structure (human-action checkpoint — Edgar runs SCRY)

**Analog:** Phase 17 Plan 17-02 Task 2 (`checkpoint:human-action`, `gate: blocking`)

**Checkpoint task pattern** (from `17-02-PLAN.md` lines 176–228):
```xml
<task type="checkpoint:human-action" gate="blocking">
  <name>Task 2: Edgar runs SCRY on enrolled Windows machines + populates 18-VALIDATION-RESULTS.md</name>
  <what-built>
    Plan 18-01 created the 18-VALIDATION-RESULTS.md skeleton. This checkpoint hands off to
    Edgar/IT to:
      1. Copy the SCRY .exe to a flash drive.
      2. Run `scry.exe` (Admin/SYSTEM for SC1/SC3 admin path; standard user for SC3 standard path;
         enrolled machine for SC4 Company Portal).
      3. Fill in one section per SC in 18-VALIDATION-RESULTS.md using the template.
      4. Fill in the Summary table with PASS / FAIL / DEFERRED for each SC.
      5. Commit 18-VALIDATION-RESULTS.md.
  </what-built>
  <how-to-verify>
    1. Open 18-VALIDATION-RESULTS.md. Confirm Summary table has no `_pending Edgar run_` rows.
    2. Each SC section has a non-empty **Date of run:**, **Operator:**, and **Result:** field.
    3. SC2 is already PASS (pre-populated); Edgar only fills SC1/SC3/SC4/SC5.
    4. Phase closes atomically — all SCs must be PASS or DEFERRED before this checkpoint resumes.
  </how-to-verify>
  <resume-signal>
    Type one of:
      - `approved — all SCs PASS`
      - `approved — SC<N> DEFERRED: <rationale>`
      - `blocked — SC<N> FAIL: <symptom description>` (triggers Plan 18-03 conditional fix)
  </resume-signal>
</task>
```

**IT runsheet wording pattern** (what Edgar is instructed to run — from `17-02-PLAN.md` Task 2 `what-built` section's concrete-steps list):

The plan must include explicit step-by-step runsheet instructions for Edgar covering:
- SC1/SC3: Run `scry.exe` from the flash drive under Admin/SYSTEM (SC1) and again as standard user (SC3); observe the pending updates field in the HTML.
- SC4: Run `scry.exe` on an Intune-enrolled machine; observe NinjaOne, CrowdStrike Falcon, and Company Portal rows in the equipment table; confirm M365 appears as a single row with sub-apps listed.
- SC5: Open the generated `.html` file in Edge/Chrome; confirm D&D layout, dark color scheme, stat block, equipment table, and quest status section all render.

Note (from CONTEXT.md D-06): Edgar covers SC1/SC3/SC4/SC5 only. SC2 is already PASS from Justin's pre-validation and is NOT listed in Edgar's runsheet items.

---

### Plan 18-03 structure (conditional fix plan OR phase-close plan)

**Analog A (conditional code fix path):** Phase 17 Plan 17-03 Tasks 1–2 (decision checkpoint + conditional patch)

**Conditional decision task pattern** (from `17-03-PLAN.md` lines 106–155, `checkpoint:decision`):
```xml
<task type="checkpoint:decision" gate="blocking">
  <name>Task 1: Read 18-VALIDATION-RESULTS.md Summary table and confirm disposition</name>
  <decision>Which SCs, if any, show FAIL and require a code fix?</decision>
  <options>
    <option id="option-no-changes">
      All SCs PASS or DEFERRED — no code changes needed. Skip Task 2; proceed to Task 3 (phase close).
    </option>
    <option id="option-fix-sc<N>">
      SC<N> FAIL — apply targeted fix to the relevant module:
        - SC1/SC3: collectors/windows/hardware.py collect_pending_updates()
        - SC2: health_checks.py (extremely unlikely — pre-validated by Justin)
        - SC4: collectors/windows/apps.py (NinjaOne/CrowdStrike/M365/Company Portal specs)
        - SC5: renderer/__init__.py render_html()
    </option>
  </options>
  <resume-signal>
    Type one of:
      - `option-no-changes` (skip Task 2; proceed to Task 3 phase close)
      - `option-fix-sc<N>: <symptom from 18-VALIDATION-RESULTS.md>`
  </resume-signal>
</task>
```

**Conditional code fix task pattern** (from `17-03-PLAN.md` lines 158–291, Task 2):
```xml
<task type="auto" tdd="true">
  <name>Task 2: (Conditional) Apply code fix per Task 1 decision + add regression test</name>
  <action>
    SKIP THIS TASK ENTIRELY if Task 1's resume signal was `option-no-changes`.

    Otherwise, for each failing SC:
      - Read the failing collector/renderer module in full.
      - Apply the targeted fix reproducing the observed symptom from 18-VALIDATION-RESULTS.md.
      - Add a regression test that exercises the fixed behavior (TDD: RED first, then GREEN).
      - Every code change paired with a test (mirrors D-13 pairing discipline from Phase 17).
  </action>
  <verify>
    <automated>python -m pytest -x -q</automated>
  </verify>
</task>
```

**Analog B (phase-close path — all SCs PASS/DEFERRED):** Phase 17 Plan 17-03 Task 3

**Phase-close task pattern** (from `17-03-PLAN.md` lines 294–416, Task 3):

STATE.md frontmatter edits (same shape as Phase 17 close):
```diff
-status: context-gathered
+status: phase-complete
-stopped_at: Phase 18 planned — N plans, N waves
+stopped_at: Phase 18 complete — N/N plans, VALID-01/VALID-03/VALID-05 closed
-last_activity: 2026-05-XX — Phase 18 planned; ...
+last_activity: 2026-05-XX — Phase 18 executed; ...
-  completed_phases: 2
+  completed_phases: 3
-  Phase: 18 of 19 (Live Machine Validation — System Health and Apps)
+  Phase: 19 of 19 (Live Machine Validation — Vendor and Mac)
```

REQUIREMENTS.md traceability table edits (same shape as Phase 17 CONF-01/CONF-02 row closure):
```markdown
| VALID-01 | Phase 18 | 18-01, 18-02, 18-03 | complete |
| VALID-03 | Phase 18 | 18-01, 18-02, 18-03 | complete |
| VALID-05 | Phase 18 | 18-01, 18-02, 18-03 | complete |
```
Plus checkbox ticks:
```diff
-- [ ] **VALID-01**:
+- [x] **VALID-01**:
-- [ ] **VALID-03**:
+- [x] **VALID-03**:
-- [ ] **VALID-05**:
+- [x] **VALID-05**:
```

Verify command (from `17-03-PLAN.md` Task 3 verify):
```bash
python -m pytest -x -q
```

---

### Conditional code fix analogs (if a SC fails)

These files are unchanged in the happy path (all SCs PASS). If triggered by a FAIL, the executor self-reads the file before editing (existing pattern in every prior phase plan).

**`collectors/windows/hardware.py`** — `collect_pending_updates()` and `_collect_uptime()`

Relevant code paths per CONTEXT.md `<canonical_refs>`:
- `collect_pending_updates()` — WUA COM call; returns `None` when `_WIN32COM_AVAILABLE` is False or privilege insufficient. If SC1/SC3 produce wrong behavior on real hardware, the fix is targeted here.
- `_collect_uptime()` — `psutil.boot_time()` path. Pre-validated by Justin (SC2 PASS); extremely unlikely to require a fix.
- `CollectionResult` envelope: all fixes must preserve `(value, error)` return shape — never raise across layer boundary.

**`collectors/windows/apps.py`** — app detection for SC4

Relevant constants per CONTEXT.md `<canonical_refs>` and `<code_context>`:
- `_search_uninstall_keys()` — already enumerates all 4 hives (HKLM, HKLM\Wow6432Node, HKCU, HKCU\Wow6432Node). No new hive enumeration needed.
- NinjaOne keywords: `NinjaRMMAgent` / `NinjaRMM` / `NinjaOne Agent`
- CrowdStrike keywords: `CrowdStrike Windows Sensor` / `CrowdStrike Sensor Platform` + service state read
- M365 single-suite collapse — the display that Edgar confirms in SC4
- Company Portal: MSIX + MDM Enrollment check (reads MDM Enrollment registry path, not a COM call — works at standard-user privilege)

**`health_checks.py`** — uptime badge logic

Pre-validated by Justin; included only as a safety net. Current constants from CONTEXT.md `<canonical_refs>`:
- `UPTIME_WARN_DAYS = 7` (lines 132–161)
- `UPTIME_STALE_DAYS = 30` (lines 132–161)
- Test coverage: `tests/test_health_checks.py` lines 182–205

**`renderer/__init__.py`** — `render_html()` for SC5

Test coverage: `tests/test_renderer.py`. If SC5 fails on real hardware, the fix targets template rendering, Jinja2 context passing, or CSS (loaded via `importlib.resources`).

---

## Shared Patterns

### Pattern: CollectionResult envelope — never raise across layer boundary
**Source:** `collectors/windows/hardware.py` and `collectors/windows/apps.py` (all collectors)
**Apply to:** Any conditional fix to collectors
```python
# All collectors return CollectionResult(value, error) — never raise
try:
    # ... real work ...
    return CollectionResult(value=result, error=None)
except Exception as exc:
    return CollectionResult(value=None, error=str(exc))
```
A failing SC that surfaces as `None` / "N/A" (rather than a crash) means the error-handling envelope is working; the fix is in the data-gathering logic, not the error boundary.

### Pattern: Phase-close STATE.md + REQUIREMENTS.md edit
**Source:** Phase 17 Plan 17-03 Task 3 (lines 294–416 of `17-03-PLAN.md`)
**Apply to:** Plan 18-03 Task 3 (phase close)

Deterministic edit shape: frontmatter `status → phase-complete`, `completed_phases` increment, phase pointer advance, VALID-XX checkboxes ticked, traceability rows added. See Pattern Assignments section "Plan 18-03 structure" above for the exact diff excerpts.

### Pattern: Atomic phase close — all SCs must be PASS or DEFERRED
**Source:** Phase 17 CONTEXT.md D-08 + Phase 18 CONTEXT.md D-04
**Apply to:** Plan 18-02 checkpoint resume logic and Plan 18-03 Task 1

A FAIL result blocks phase close. The conditional fix path (Plan 18-03 Task 2) must complete and Edgar must re-validate the fixed SC before Plan 18-03 Task 3 (phase close) runs.

### Pattern: Pre-populated human-action section (Justin SC2 pre-validation)
**Source:** Phase 18 CONTEXT.md D-03/D-05 — "SC2 is pre-populated with Justin's direct observation before Edgar's run"
**Apply to:** Plan 18-01 Task 1 (skeleton creation)

Unlike Phase 17's completely empty per-machine template, `18-VALIDATION-RESULTS.md` ships with SC2 already filled in and marked PASS. The Plan 18-01 executor must write this content — it is not left for Edgar. Template structure mirrors the per-machine entry in `17-IT-CONFIRMATION.md` (operator name, date, what was observed, result).

### Pattern: IT runsheet embedded in plan (not a separate README)
**Source:** Phase 17 Plan 17-02 Task 2 `what-built` section (concrete steps list at lines 181–193)
**Apply to:** Plan 18-02 Task 2

Instructions for Edgar are embedded directly in the plan's `<what-built>` block — not in a separate IT-facing README (CONTEXT.md "Claude's Discretion" says "whether the plan includes an IT-facing README or embeds instructions directly in the plan file" is at Claude's discretion; Phase 17 pattern is to embed).

### Pattern: 4-hive registry enumeration (no shortcuts)
**Source:** `collectors/windows/apps.py` `UNINSTALL_PATHS` (all 4 hives per CLAUDE.md critical constraint)
**Apply to:** Any conditional SC4 app-detection fix

CLAUDE.md constraint: ALWAYS enumerate all 4 registry Uninstall paths — `HKLM`, `HKLM\Wow6432Node`, `HKCU`, `HKCU\Wow6432Node`. Missing 32-bit entries is a silent bug.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `18-VALIDATION-RESULTS.md` (per-SC structure) | planning artifact | n/a | Phase 17's `17-IT-CONFIRMATION.md` is the closest analog — same role, same purpose — but it uses per-CONF-ID sections while Phase 18 uses per-SC sections. The per-SC structure is new to this project. Pattern Assignments section above provides the concrete section template derived from adapting the Phase 17 model to the Phase 18 SC structure. |

---

## Metadata

**Analog search scope:** `.planning/phases/17-it-registry-path-confirmation/` (all 3 plan files + `17-IT-CONFIRMATION.md` + `17-PATTERNS.md`), `.planning/ROADMAP.md` Phase 18 success criteria (SC1–SC5), `18-CONTEXT.md` decisions D-01 through D-10.
**Files scanned:** 7 (`17-CONTEXT.md`, `17-IT-CONFIRMATION.md`, `17-01-PLAN.md`, `17-02-PLAN.md`, `17-03-PLAN.md`, `17-PATTERNS.md`, `ROADMAP.md` Phase 18 section).
**Pattern extraction date:** 2026-05-21.

**Key insight:** Phase 18 is structurally identical to Phase 17 in its 3-plan shape — (1) create artifact skeleton, (2) human-action checkpoint, (3) conditional fix + phase close. The only structural difference is:
- Phase 17 used **per-CONF-ID sections** (CONF-01, CONF-02) in its confirmation artifact; Phase 18 uses **per-SC sections** (SC1–SC5) in its validation artifact.
- Phase 18 has a **pre-populated section** (SC2 PASS from Justin's observation) that Phase 17 did not have — the skeleton is not completely empty when it ships.
- Phase 18's conditional fix (Plan 18-03 Task 2) may touch collectors, health_checks, or renderer rather than vendor.py keyword lists — the fix target depends on which SC fails. The Phase 17 D-13/D-14 model (every code change paired with a regression test) applies equally here.
