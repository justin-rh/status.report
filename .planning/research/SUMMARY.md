# Research Summary -- StatusReport v2.0

**Project:** StatusReport (Master Electronics IT Audit Tool)
**Domain:** Windows/macOS IT audit portable executable -- USB-deployed, read-only, RPG-themed HTML output
**Researched:** 2026-05-07
**Confidence:** HIGH (Windows/NinjaOne paths), MEDIUM (Mac-specific behavior -- no live Mac build yet)

---

## Executive Summary

StatusReport v2.0 extends a shipped v1.0 Windows tool with four additions: Company Portal / Intune enrollment detection, a structured HTML warnings system, Mac hardware and app collectors matching Windows parity, and NinjaOne remote-execution compatibility (SYSTEM account). No new pip dependencies are required. Every v2.0 feature uses Python stdlib (plistlib, subprocess, platform, pathlib) or extends existing patterns. The v1.0 stack (Python 3.12, psutil, wmi, winreg, Jinja2, PyInstaller --onedir) is unchanged.

The recommended build order is: data model changes first (Warning dataclass), then HTML rendering, then NinjaOne fixes in main.py, then Company Portal (one-liner APP_SPECS entry), then Mac collectors last. This order lets each phase ship to users independently and avoids the largest chunk of new code (Mac) blocking quick wins. The NinjaOne fixes are the most urgent -- an unguarded input() call silently hangs every remote NinjaOne run until the timeout kills it.

The core architectural principle from research: the existing AuditReport mutation-in-place pattern and CollectionResult error envelope hold for all four features. No new layers, no new abstractions -- just new files following established patterns. The one structural addition is warnings.py, inserted as a post-collection evaluation step between collect_all() and render_html() in main.py.

---

## 1. Stack Additions

**No new pip packages. Zero.**

| Module | Status | Use |
|--------|--------|-----|
| plistlib | stdlib (new import) | Mac .app bundle plist parsing |
| subprocess | already present | Extended for sysctl, dscl, sw_vers, system_profiler on Mac |
| platform | already imported | platform.system() for OS dispatch only |
| pathlib.Path | already used | Extended for /Applications glob on Mac |

What NOT to add: pyobjc/AppKit, system_profiler SPApplicationsDataType (Spotlight-dependent), ninjarmm-cli API calls, requests or any HTTP library.

---

## 2. Feature Table Stakes

### Company Portal / Intune Detection (Windows)

- MDM enrollment signal: HKLM\SOFTWARE\Microsoft\Enrollments\{GUID}\UPN -- presence of UPN value confirms enrollment; GUID without UPN is a stale artifact
- App presence signal: existing _detect_msix helper with prefix Microsoft.CompanyPortal_
- Two distinct signals -- conflating them creates false positives (user sideloaded CP without enrollment) and false negatives (Autopilot-enrolled without CP installed)
- Secondary service signal: IntuneManagementExtension at HKLM\SYSTEM\CurrentControlSet\Services\\

### HTML Warnings System

- OS EOL warning: Windows 10 (build < 22000) is past EOL as of October 14, 2025 -- flag every machine
- Disk warning: fire if free < 15% OR free < 10 GB (dual threshold; matches enterprise monitoring defaults)
- HTML pattern: collapsible box via details/summary elements -- zero JavaScript, pure HTML5
- Evaluate warnings in new warnings.py module -- not in the template, not in collectors
- Migrate existing ad-hoc os_warning and rename_warning booleans into the new Warning dataclass system

### Mac Collectors (parity goal -- same AuditReport fields, same HTML output)

- CPU: subprocess sysctl -n machdep.cpu.brand_string (covers Intel and Apple Silicon)
- RAM/Disk: psutil.virtual_memory() and psutil.disk_usage("/") -- already cross-platform
- OS version: subprocess sw_vers -productVersion -- NEVER platform.mac_ver() (returns 10.16 on macOS 11+ in some Python builds)
- Local profiles: dscl . -list /Users with name/UID filtering -- not raw /Users/ directory listing
- App detection: .app bundle filesystem check + plistlib; check BOTH /Applications/ and ~/Applications/
- MERP: Windows-only ERP; Mac must emit AppStatus(name=MERP, installed=False, error=Windows only) to preserve template invariant

### NinjaOne Remote Execution

- input() at end of main.py must be gated on sys.stdin.isatty() -- unguarded call hangs NinjaOne indefinitely
- os.startfile() must be gated on the same condition
- Output path under SYSTEM: write to C:\ProgramData\MasterElectronics\StatusReport\logs\ not USB
- Stdout buffering: sys.stdout.reconfigure(line_buffering=True) when not TTY -- otherwise summary line never appears in NinjaOne activity log
- MSIX detection under SYSTEM: enumerate HKEY_USERS (not HKCU) to find Claude and Company Portal

### Deferred to v2.x

- Code-signed .exe
- JSON log file output
- Remote access tool detection (TeamViewer, AnyDesk)
- macOS packaging (pkg/dmg) -- Mac users invoke Python directly for v2.0
- NinjaOne custom field integration (ninjarmm-cli)

---

## 3. Architecture Changes

### New Files

| File | Purpose |
|------|---------|
| warnings.py | Post-collection evaluation: evaluate_warnings(report), three check functions, threshold constants |
| collectors/mac/__init__.py | Empty init |
| collectors/mac/hardware.py | collect_hardware() and collect_profiles() via subprocess/psutil |
| collectors/mac/apps.py | detect_apps() / collect_apps() via filesystem + plistlib |

### Modified Files

| File | Change |
|------|--------|
| main.py | Wire evaluate_warnings(); guard os.startfile()/input() on isatty(); add [SUMMARY] stdout line; stdout line-buffering; SYSTEM-context output path branching |
| models.py | Add Warning dataclass; add warnings: list[Warning] field to AuditReport |
| collectors/__init__.py | Add Darwin platform branch alongside Windows branch |
| collectors/windows/apps.py | Add Company Portal entry to APP_SPECS table |
| renderer/__init__.py | Remove os_warning/rename_warning from _build_context(); add warnings key |
| renderer/templates/character_sheet.html | Replace two ad-hoc warning divs with single warnings loop |

### Data Model Additions (additive only -- no v1.0 breakage)

New Warning dataclass:
    code: str           # OS_VERSION, DISK_SPACE, RENAME_REQUIRED
    severity: str       # critical, warning, info
    message: str
    detail: str | None = None

New field on AuditReport:
    warnings: list[Warning] = field(default_factory=list)

All existing v1.0 tests remain valid -- warnings defaults to empty list.

---

## 4. Watch Out For -- Top 5 Most Dangerous Pitfalls

**1. Company Portal installed != Intune enrolled**
The MSIX package tells you the app is installed, not that the device is enrolled. MDM enrollment lives at HKLM\SOFTWARE\Microsoft\Enrollments\{GUID}\UPN. A GUID key without a UPN value is a stale artifact from a previous enrollment. Always require the UPN value. Use two distinct signals or label rows precisely.

**2. input() hangs NinjaOne scripts forever**
The input() at end of main.py blocks stdin forever when NinjaOne runs as SYSTEM. The script never exits. NinjaOne kills it after its timeout (default 10 min) and marks the run as failed even though HTML was written. Fix: if sys.stdin.isatty(): input(...). Use isatty() not USERNAME==SYSTEM -- isatty() also handles CI correctly.

**3. MSIX detection returns nothing under SYSTEM**
_detect_msix() opens HKEY_CURRENT_USER. Under NinjaOne SYSTEM account, HKCU is the SYSTEM hive -- no MSIX registrations. Claude and Company Portal always show Not Found on every NinjaOne run. Fix: enumerate HKEY_USERS across all loaded per-user hives. Required before NinjaOne testing produces meaningful app detection results.

**4. psutil.cpu_freq() returns None on all Apple Silicon**
Confirmed open psutil bug (issue 1892). Apple removed hw.cpufrequency on ARM. Calling cpu_freq() on any M1/M2/M3/M4 Mac silently returns None. Do not call it on macOS. Use system_profiler SPHardwareDataType -json, checking both chip_type (Apple Silicon) and cpu_type (Intel) keys -- mutually exclusive by architecture.

**5. platform.mac_ver() returns 10.16 on macOS 11+**
Confirmed Python bug (issue 35344). Reports Big Sur as version 10.16 in some Python builds. OS version checks built on this fire incorrectly on every modern Mac. Never use platform.mac_ver() in the Mac collector. Use subprocess sw_vers -productVersion.

---

## 5. Open Decisions -- Require IT/Stakeholder Input Before Implementation

| Decision | Needed For | Default If No Answer |
|----------|-----------|---------------------|
| NinjaOne output path -- confirm C:\ProgramData\MasterElectronics\StatusReport\logs\ | Phase 8 | Use that path -- SYSTEM-writable, IT-retrievable |
| Company Portal row naming -- enrollment vs app presence vs both | Phase 9 | Show both as separate signals, clearly labeled |
| NinjaOne Mac agent app path -- validate /Applications/NinjaRMMAgent/ against fleet Mac | Phase 10 | Use that path per NinjaOne official docs |
| OS warning threshold -- confirm minimum acceptable build | Phase 6/7 | Warn on any Win10 (build < 22000); informational for Win11 below 22631 |
| Disk space thresholds -- confirm 15% / 10 GB dual threshold | Phase 6/7 | Ship those defaults; constants in warnings.py, easy to adjust |

---

## Implications for Roadmap

v1.0 phases ended at Phase 5. v2.0 continues from Phase 6.

### Phase 6: Models and Warnings Module
**Rationale:** Warning dataclass is the shared dependency for all v2.0 phases. Pure Python, no OS APIs, no hardware required. Unblocks everything.
**Delivers:** Warning dataclass; warnings field on AuditReport; warnings.py with evaluate_warnings() and three check functions.
**Avoids:** Warning logic leaking into template (untestable) or collectors (wrong layer).
**Test signal:** Unit tests for each check function with mock AuditReport objects -- no Windows required.

### Phase 7: HTML Warnings Section
**Rationale:** Highest-visibility v2.0 deliverable. Data model ready from Phase 6. Validates with mock data before any collector changes. Cleans up existing ad-hoc warning flag tech debt.
**Delivers:** Template updated with warnings loop; renderer updated; evaluate_warnings() wired into main.py.
**Avoids:** Template-as-logic anti-pattern; scattered boolean flags on _build_context().
**Test signal:** Existing renderer tests pass with warnings=[] (no regression). New tests render reports with Warning objects.

### Phase 8: NinjaOne Compatibility
**Rationale:** Independent of Mac and Company Portal. Only main.py and _detect_msix(). Ships to NinjaOne users before Mac work begins. Blocking bugs must be resolved before NinjaOne testing yields reliable results.
**Delivers:** isatty() guards; HKEY_USERS MSIX enumeration; resolve_output_dir() with ProgramData path; stdout line-buffering; [SUMMARY] structured stdout line.
**Avoids:** input() hang; MSIX blind spot under SYSTEM; stdout buffer silence; output path writing to RMM cache.
**Open decision:** Confirm ProgramData output path with IT before implementation.

### Phase 9: Company Portal / Intune Detection
**Rationale:** One dict added to APP_SPECS plus a registry enumeration function. No Mac dependency. Ordered after Phase 8 so SYSTEM-context MSIX fix is in place before Company Portal is tested via NinjaOne.
**Delivers:** Company Portal MSIX detection; Intune enrollment registry check with UPN validation.
**Avoids:** Enrollment vs app conflation; stale GUID artifacts.
**Open decision:** Confirm row naming with IT before implementation.

### Phase 10: Mac Collectors
**Rationale:** Largest chunk of new code. Requires macOS hardware. Not a dependency for any Windows feature. Doing it last means Phases 6-9 ship before Mac work begins.
**Delivers:** collectors/mac/ module tree; Darwin dispatch in collectors/__init__.py; hardware and app collectors using subprocess/psutil/plistlib.
**Build order within phase:** (1) empty __init__.py, (2) hardware.py, (3) dispatch branch, (4) apps.py after validating bundle paths on real Mac.
**Avoids:** Apple Silicon cpu_freq bug; platform.mac_ver wrong version; /Applications-only detection missing Zoom; system account contamination in profile list.
**Open decision:** Validate NinjaOne Mac agent path against a fleet Mac before phase closes.

### No Deep Research Required for Any Phase
All four feature areas were researched with specific API paths, code patterns, and pitfall mitigations. Open items are stakeholder decisions, not technical unknowns.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new deps confirmed; all stdlib APIs validated against Python docs |
| Features | HIGH | Windows paths verified against official docs and live codebase; Mac paths from vendor docs |
| Architecture | HIGH | Based on direct inspection of shipped v1.0 source |
| Pitfalls (Windows/NinjaOne) | HIGH | Registry, SYSTEM context, WMI access verified against Microsoft docs |
| Pitfalls (Mac) | MEDIUM | psutil Apple Silicon bug confirmed open; platform.mac_ver bug confirmed in Python tracker; no live Mac build tested |

**Overall: HIGH for Windows/NinjaOne, MEDIUM for Mac**

### Gaps Requiring Live Validation

- Mac app bundle paths -- validate against a real Mac in the fleet before Phase 10 closes (NinjaOne agent and CrowdStrike legacy path especially)
- system_profiler chip_type vs cpu_type -- unit test fixtures needed from both Intel and Apple Silicon
- NinjaOne full bundle deployment -- confirm --onedir _internal/ directory is deployed alongside .exe
- Disk warning thresholds -- confirm with IT before Phase 6 closes

---

## Sources

**Primary (HIGH confidence):**
- Python docs: plistlib, platform, subprocess
- psutil docs 6.x -- cross-platform behavior
- Microsoft Learn: MDM enrollment registry paths
- Microsoft Support: Windows 10 EOL October 14, 2025
- NinjaOne docs: macOS Agent Installation (/Applications/NinjaRMMAgent/)
- Applivery: CrowdStrike Falcon on macOS (/Applications/Falcon.app)
- Apple Developer: CFBundleShortVersionString, CFBundleIdentifier
- Jamf Community: dscl UID filter for human accounts
- PyInstaller docs: sys.executable in --onedir mode
- v1.0 shipped source: direct inspection of main.py, models.py, collectors/, renderer/

**Secondary (MEDIUM confidence):**
- psutil GitHub issue 1892 -- cpu_freq() broken on Apple Silicon (confirmed open)
- Python bug tracker issue 35344 -- platform.mac_ver() returns 10.16 on macOS 11+
- NinjaOne community: SYSTEM context variable behavior
- Intune community: Enrollments GUID stale key behavior after unenrollment
- Paessler KB: dual threshold disk monitoring pattern

**Tertiary (requires live validation):**
- NinjaOne stdout buffering under SYSTEM -- inferred from Python docs
- CrowdStrike Mac /Library/CS/ legacy path -- community-sourced; validate against fleet

---

*Research completed: 2026-05-07*
*Ready for roadmap: yes*