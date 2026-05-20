---
phase: 17-it-registry-path-confirmation
plan: "02"
subsystem: planning-artifacts
tags: [confirmation, evidence, registry, vendor, checkpoint]
dependency_graph:
  requires: [17-01]
  provides: [it-confirmation-skeleton, conf-01-evidence-slot, conf-02-evidence-slot]
  affects:
    - .planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md
tech_stack:
  added: []
  patterns: [human-in-the-loop-evidence-capture, negative-result-by-proxy]
key_files:
  created:
    - .planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md
  modified: []
decisions:
  - "17-IT-CONFIRMATION.md skeleton created; per-machine entries deferred to Task 2 (Edgar's run)"
  - "BY-PROXY path documented in skeleton — single machine of either vendor closes both CONF-IDs atomically per D-15/D-16"
  - "Plan stopped at Task 2 checkpoint:human-action — Edgar must run scry.exe --diag-vendor on at least one enrolled machine"
metrics:
  duration: "57 seconds"
  completed: "2026-05-20"
  tasks_completed: 1
  tasks_total: 2
  files_modified: 1
---

# Phase 17 Plan 02: IT Evidence Capture — Summary

**One-liner:** `17-IT-CONFIRMATION.md` skeleton created with Summary table, entry template (all D-06 fields), and Closing instructions; plan paused at Task 2 (human-action gate — Edgar must run `--diag-vendor` on enrolled fleet hardware).

## What Was Built

### Task 1: `17-IT-CONFIRMATION.md` skeleton (COMPLETE)

Created `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` with:

- **Summary table** — CONF-01 and CONF-02 rows with `_pending Edgar run_` status (ready for Edgar to fill in)
- **Disposition vocabulary** — CONFIRMED-MATCH, CONFIRMED-DIVERGENT, NEGATIVE-RESULT with definitions + BY-PROXY explanation
- **How-to-add instructions** — exact `cmd` capture command Edgar runs: `scry.exe --diag-vendor > diag-%COMPUTERNAME%.txt`
- **Entry template** — all D-06 required fields: hostname, date of run, operator, vendor under test, result, matched DisplayName(s), DisplayVersion(s), hive(s), DCU XML path observed, divergence notes, and raw `--diag-vendor` output block
- **Closing the phase instructions** — 3-step process for updating the Summary table and triggering Plan 17-03
- **No real per-machine entries** — template-only artifact as required by task constraints

Verified: all 5 required strings present (`CONF-01`, `CONF-02`, `CONFIRMED-MATCH`, `NEGATIVE-RESULT`, `--diag-vendor`). Committed as `576b130`.

### Task 2: Edgar's `--diag-vendor` runs (BLOCKED — human-action checkpoint)

Plan paused. See Checkpoint section below.

## Checkpoint: Task 2 — Edgar Runs `--diag-vendor` on Enrolled Fleet Hardware

**Type:** checkpoint:human-action
**Status:** PENDING — requires Edgar/IT involvement

**What automation has done:**
- Plan 17-01 shipped the `--diag-vendor` CLI flag and confirmed it with a PyInstaller smoke build (exit 0, all 4 hive headers + DCU XML probe section in stdout, `dist\scry_v3.1\scry_v3.1.exe`)
- Plan 17-02 Task 1 created the `17-IT-CONFIRMATION.md` fill-in skeleton Edgar will populate

**What the human must do:**

1. Copy `dist\scry_v3.1\scry_v3.1.exe` onto a flash drive
2. Give the flash drive to Edgar (or run yourself) on at least one enrolled Master Electronics machine
3. Run: `scry.exe --diag-vendor > diag-%COMPUTERNAME%.txt`
4. Paste the output into a new `### Machine: <HOSTNAME>` section of `17-IT-CONFIRMATION.md` using the entry template
5. Fill in the Summary table at the top with the final disposition for CONF-01 and CONF-02
6. Commit `17-IT-CONFIRMATION.md` with the populated entries

**BY-PROXY shortcut (D-15, D-16):** A SINGLE machine of either vendor closes BOTH CONF-IDs:
- Dell-only machine → CONF-01 positive + CONF-02 NEGATIVE-RESULT-by-proxy (empty Lenovo section in dump)
- Lenovo-only machine → CONF-02 positive + CONF-01 NEGATIVE-RESULT-by-proxy (empty Dell section in dump)

**Resume signal** — provide ONE of:
- `approved — both CONFIRMED-MATCH (no patches needed)`
- `approved — DCU CONFIRMED-DIVERGENT: <describe new DisplayName or new XML path>`
- `approved — DCU NEGATIVE-RESULT` / `approved — LSU NEGATIVE-RESULT`
- `approved — DCU CONFIRMED-MATCH, LSU NEGATIVE-RESULT-by-proxy on Dell-only machine <HOSTNAME>` (or inverse)
- or: describe what went wrong (e.g. "Edgar unavailable until next week — pausing phase 17")

**Plan 17-03 branches on this signal:**
- Both CONFIRMED-MATCH → no code changes, closes CONF-01 and CONF-02, removes blockers from STATE.md
- Any CONFIRMED-DIVERGENT → patches `vendor.py` keyword list and/or `DCU_XML_PATH` + adds parameterized tests (D-13, D-14)
- NEGATIVE-RESULT (including by-proxy) → closes that CONF-ID with negative result documented (D-15, D-16)

## Deviations from Plan

None — Task 1 executed exactly as written. Skeleton content matches the plan's verbatim specification.

## Known Stubs

`17-IT-CONFIRMATION.md` Summary table rows currently contain `_pending Edgar run_` — these are intentional placeholders for Task 2 (human-action gate). They will be replaced by Edgar when populating the file. This is not a stub that prevents the plan's goal — it is the designed state of the artifact at checkpoint.

## Threat Flags

No new attack surface. `17-IT-CONFIRMATION.md` is a markdown planning artifact. Per the plan's threat model: T-17-05 (hostnames + InstallLocation in committed markdown — accepted), T-17-06 (tampering via git audit trail — mitigated), T-17-07 (repudiation via Operator field + git commit author — mitigated).

## Self-Check: PASSED

Files verified:
- FOUND: `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md`
- FOUND: `.planning/phases/17-it-registry-path-confirmation/17-02-SUMMARY.md`

Commits verified:
- Task 1 commit `576b130`: docs(17-02): create 17-IT-CONFIRMATION.md skeleton template
