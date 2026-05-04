# Phase 2: System Collectors - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 02-system-collectors
**Areas discussed:** Degradation pattern, User profile format, Library-to-field split, Collector structure

---

## Degradation Pattern

| Option | Description | Selected |
|--------|-------------|----------|
| None + error log | Field stays None; error goes into collection_errors; renderer handles display | ✓ |
| String sentinel in str fields | String fields get "Unavailable"; float fields stay None | |
| You decide | Claude picks pattern | |

**User's choice:** None + error log
**Notes:** Cleanest separation — data model stays typed, display is the renderer's job.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Degrade all fields silently | All fields stay None, one error in collection_errors | ✓ |
| One error per failed field | Each failed field gets its own collection_errors entry | |
| You decide | Claude picks granularity | |

**User's choice:** Degrade all fields silently
**Notes:** One message per failed subsystem (e.g., wmi can't import → one error, all wmi fields → None).

---

## User Profile Format

| Option | Description | Selected |
|--------|-------------|----------|
| Profile paths | Full C:\Users\john.doe strings from registry | |
| Usernames only | Last path segment (john.doe) | ✓ |

**User's choice:** Usernames only
**Notes:** More readable for IT staff viewing the character sheet.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Filter system SIDs | Skip S-1-5-18, S-1-5-19, S-1-5-20; keep Default and Public | ✓ |
| Filter system + template profiles | Also skip Default, Public, All Users paths | |
| No filtering | Include all SIDs | |

**User's choice:** Filter system SIDs (S-1-5-18, S-1-5-19, S-1-5-20 only)
**Notes:** Retain human-visible profiles including Default and Public.

---

## Library-to-Field Split

| Option | Description | Selected |
|--------|-------------|----------|
| psutil primary, wmi for model name only | psutil handles RAM/disk; wmi only for cpu_model | ✓ |
| wmi primary, psutil fallback | wmi leads; psutil fills in on failure | |
| You decide | Claude picks per-field split | |

**User's choice:** psutil primary, wmi for model name only
**Notes:** Maximizes standard-user reliability; wmi used only where psutil can't provide the data (CPU model string).

---

| Option | Description | Selected |
|--------|-------------|----------|
| platform.version() + platform.release() | stdlib, no elevation, always works | ✓ |
| WMI Win32_OperatingSystem | More detail but degrades if wmi unavailable | |

**User's choice:** platform stdlib
**Notes:** Zero dependencies for OS version/build.

---

## Collector Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Two functions, one file | collect_hardware() + collect_profiles() in hardware.py | ✓ |
| One function per field | Granular get_cpu_model() etc. | |

**User's choice:** Two functions, one file
**Notes:** collect_hardware(report) and collect_profiles(report) both mutate AuditReport in place.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Collectors only | Phase 2 delivers collectors; main.py wired later | ✓ |
| Wire main.py now | Minimal main.py for early validation | |

**User's choice:** Collectors only
**Notes:** main.py wiring deferred until full pipeline (collect → render → write) is ready.

---

## Claude's Discretion

- Exact `platform` API calls for OS version/build
- `current_user` source (`os.environ` vs `psutil.users()`)
- Test mocking strategy for WMI and winreg

## Deferred Ideas

- Minimal main.py for early end-to-end validation — considered, deferred
- Per-field error granularity — considered, rejected (one message per subsystem preferred)
