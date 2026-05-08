# Phase 10: Mac Collectors - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 10-mac-collectors
**Areas discussed:** Mac execution context, App detection approach, Service state on Mac, Test strategy

---

## Mac Execution Context

| Option | Description | Selected |
|--------|-------------|----------|
| python main.py from USB/dir | `Path(__file__).parent / "logs"` for output; IT runs as script | ✓ |
| Frozen binary via PyInstaller | Build Mac binary in v2 despite no notarization | |
| Same sys.executable, document the quirk | Keep sys.executable everywhere; output lands in Python install dir | |

**User's choice:** `python3 main.py` from project directory. Output path: `Path(__file__).parent / "logs"` on Mac.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in main.py | Two-line if/else in main.py for the platform split | ✓ |
| Helper function in utils module | Extract get_output_root() to a separate module | |

**User's choice:** Inline `sys.platform == "darwin"` check in main.py.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Print path + pause, skip open | Just print path; IT cmd-clicks in Terminal | |
| open via subprocess on Mac | `subprocess.run(["open", str(output_path)])` | ✓ |
| You decide | Claude picks safest approach | |

**User's choice:** `subprocess.run(["open", str(output_path)])` in Mac interactive mode.

---

## App Detection Approach

| Option | Description | Selected |
|--------|-------------|----------|
| /Applications/ check + plistlib version | Filesystem check + CFBundleShortVersionString from Info.plist | ✓ |
| system_profiler SPApplicationsDataType | One subprocess call for all apps; slow (~5–10s) | |
| /Applications/ check only, no version | Fastest; version=None always | |

**User's choice:** `/Applications/` check + `plistlib` version parsing.

---

| Option | Description | Selected |
|--------|-------------|----------|
| collectors/mac/ parallel to windows/ | New directory; dispatch in __init__.py | ✓ |
| Shared file with platform branches | Single collectors/hardware.py with if blocks | |

**User's choice:** `collectors/mac/` parallel to `collectors/windows/`.

---

| Option | Description | Selected |
|--------|-------------|----------|
| LaunchDaemon plist check | /Library/LaunchDaemons/com.crowdstrike.falcond.plist as fallback | ✓ |
| /Applications/ only, mark as Not Found if missing | No LaunchDaemon fallback | |
| You decide | Claude handles CrowdStrike specifics | |

**User's choice:** LaunchDaemon plist as CrowdStrike fallback if no .app bundle.

---

## Service State on Mac

| Option | Description | Selected |
|--------|-------------|----------|
| Populate service_state via launchctl | launchctl list <label>; exit 0 = Running | ✓ |
| Presence only — no service_state | installed=True/False, service_state=None | |
| LaunchDaemon plist only (no launchctl) | Plist exists → service_state='Loaded' | |

**User's choice:** `launchctl list <daemon-label>`. Exit 0 → `"Running"`, non-zero → `"Stopped"`.

---

| Option | Description | Selected |
|--------|-------------|----------|
| 'Running' / 'Stopped' | launchctl exit 0 = Running, non-zero = Stopped | ✓ |
| You decide | Claude picks Mac service_state values | |

**User's choice:** `"Running"` / `"Stopped"` as service_state values on Mac.

---

## Test Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Mock subprocess + patch Path.exists() | Portable; runs on Windows CI | ✓ |
| pytest skip markers for Mac-only | Skip on Windows; run only with macOS runner | |
| Both: mocked unit tests + macOS CI runner | Most thorough; requires CI pipeline changes | |

**User's choice:** Mock `subprocess.run` + patch `Path.exists()`. All Mac tests run on Windows CI.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Parametrize for Intel and Apple Silicon | Two fixture sets; both CPU branches tested | ✓ |
| Apple Silicon only | Intel aging out; only M-series fixtures | |
| You decide | Claude writes whatever fixtures cover branches | |

**User's choice:** Parametrize with both Intel and Apple Silicon fixture sets.

---

## Claude's Discretion

- Exact `system_profiler` JSON key for Apple Silicon chip type
- NinjaOne LaunchDaemon label on Mac
- Company Portal and Microsoft 365 exact bundle paths on Mac
- Whether `pwd.getpwall()` requires elevation and how to degrade
- How to mock `plistlib.load()` in unit tests

## Deferred Ideas

- Mac PyInstaller packaging — v3
- macOS-specific health warnings (SIP, Gatekeeper) — out of scope for v2
- GitHub Actions macOS CI runner — deferred; mocked tests only for now
