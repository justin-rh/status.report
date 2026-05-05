# Phase 4: App Detection and Compliance Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 04-app-detection-and-compliance-engine
**Areas discussed:** MERP blocker handling, M365 detection strategy, CrowdStrike service state, Detector code architecture

---

## MERP Blocker Handling

| Option | Description | Selected |
|--------|-------------|----------|
| I have the path | Hardcode confirmed registry path | |
| Placeholder constant | MERP_REGISTRY_PATH = '' constant; skip if empty | |
| Skip MERP entirely | Leave out of Phase 4, revisit later | |
| Other (filesystem path known) | User knows typical install path, not registry path | ✓ |

**User's choice:** User provided the filesystem installation path: `C:\PVX Plus Technologies\WindX Plugin-64 2022 Upd 1\WindX`. Registry path unknown but install path known.

**Follow-up: MERP detection approach**

| Option | Description | Selected |
|--------|-------------|----------|
| Filesystem-first | Check known install path; registry search for version | ✓ |
| Registry-first | Search by DisplayName/Publisher; filesystem fallback | |

**User's choice:** Filesystem-first. Primary: path existence check. Secondary: registry search for version.

---

## M365 Detection Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| 5 individual AppStatus entries | One entry per M365 app; shows which specific app is missing | |
| 1 suite AppStatus entry | Single "Microsoft 365" entry; installed or not | ✓ |
| Suite check + per-app fallback | Suite-level first; individual checks if suite not found | |

**User's choice:** Single suite entry named "Microsoft 365". Simplest approach — IT needs to know if M365 is present, not which individual component is missing.

---

## CrowdStrike Service State

| Option | Description | Selected |
|--------|-------------|----------|
| winreg SYSTEM\Services key | Start DWORD → Automatic/Manual/Disabled | ✓ |
| wmi Win32_Service | Live Running/Stopped state via COM | |

**Notes:** Clarification was needed: pure winreg can only read the service start *type* (Automatic/Manual/Disabled), not live running state. User confirmed start type from winreg is sufficient — IT can infer that Automatic on a managed machine = running.

---

## Detector Code Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Config-driven table | APP_SPECS list; unified detect_apps() loop; DRY | ✓ |
| Per-app detector functions | Separate function per app; explicit but verbose | |

**User's choice:** Config-driven table in `collectors/windows/apps.py`. Adding a new app = one dict entry in APP_SPECS.

---

## Claude's Discretion

- NinjaOne DisplayName keyword selection (may appear as "NinjaRMM", "NinjaOne", "NinjaRMM Agent")
- Per-subkey error handling in registry enumeration loop
- De-duplication when same app found in multiple Uninstall paths

## Deferred Ideas

None raised during discussion.
