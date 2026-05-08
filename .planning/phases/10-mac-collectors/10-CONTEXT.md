# Phase 10: Mac Collectors - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement macOS collectors that populate AuditReport with hardware stats, user profiles, and app detection results, then produce the same D&D HTML character sheet as Windows. The tool is invoked as `python3 main.py` (no PyInstaller Mac packaging — deferred to v3). Windows packaging, HTML rendering, and the warning system are already complete and unchanged by this phase.

</domain>

<decisions>
## Implementation Decisions

### Mac Execution Context
- **D-01:** Tool is invoked as `python3 main.py` from the project directory on Mac. No Mac PyInstaller binary in v2.
- **D-02:** Output path on Mac: `Path(__file__).parent / "logs"` (relative to main.py). Windows keeps `Path(sys.executable).parent / "logs"`. The platform split lives inline in `main.py` as a two-line `if sys.platform == "darwin":` / `else:` block — no helper function.
- **D-03:** Mac interactive auto-open: `subprocess.run(["open", str(output_path)])` to open the HTML in the default browser. `sys.stdin.isatty()` guard already in place applies to Mac too.

### Collector Architecture
- **D-04:** New `collectors/mac/` directory parallel to `collectors/windows/`. Contains `hardware.py` (CPU, RAM, disk, macOS version, current user, profiles) and `apps.py` (7 target apps). Same in-place mutation interface: `collect_hardware(report)`, `collect_profiles(report)`, `collect_apps(report)`.
- **D-05:** `collectors/__init__.py` dispatches by `sys.platform`: `"darwin"` imports from `collectors.mac`, anything else imports from `collectors.windows`. Same `collect_all(report)` entry point, no changes to callers.

### Mac Hardware Collection
- **D-06:** macOS version: `subprocess.run(["sw_vers", "-productVersion"])` → `os_version` (e.g., "macOS 14.4.1"). Build: `subprocess.run(["sw_vers", "-buildVersion"])` → `os_build`.
- **D-07:** CPU model — platform-aware two-branch detection:
  - Apple Silicon (`platform.machine() == "arm64"`): `subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"])` may be unavailable; fall back to `system_profiler SPHardwareDataType` JSON for `chip_type` (e.g., "Apple M3 Pro").
  - Intel (`platform.machine() == "x86_64"`): `subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"])` returns the full model string.
- **D-08:** RAM: `psutil.virtual_memory().total` — same as Windows (psutil is cross-platform). No new dependency.
- **D-09:** Disk: `psutil.disk_usage("/")` — root partition on Mac. Same psutil call as Windows.
- **D-10:** Current user: `os.environ.get("USER")` or `os.getlogin()` on Mac. `psutil.users()` is acceptable fallback.

### Mac User Profile Enumeration
- **D-11:** Enumerate human user accounts using the `pwd` stdlib module: `pwd.getpwall()` returns all accounts. Filter to UID >= 501 (human accounts on macOS). Extract `pw_name` for the username. Matches the Windows behavior of listing all human local profiles, not just the current user.

### Mac App Detection
- **D-12:** Primary detection: check if the `.app` bundle exists in `/Applications/`. Parse `Info.plist` inside the bundle (via `plistlib` stdlib) for `CFBundleShortVersionString` → `version`.
- **D-13:** `collectors/mac/apps.py` contains a `MAC_APP_SPECS` table (parallel to Windows `APP_SPECS`). Each entry declares `name`, `app_bundle` (e.g., `"Google Chrome.app"`), and optional `launchdaemon_plist` for service-type apps.
- **D-14:** All 7 target apps on Mac: NinjaOne (RMM), CrowdStrike Falcon, Microsoft 365, Zoom, Google Chrome, Claude Desktop, Company Portal. MERP is excluded on Mac (Windows-only ERP, per REQUIREMENTS.md out-of-scope table).
- **D-15:** CrowdStrike fallback: if `/Applications/Falcon.app` does not exist, check `/Library/LaunchDaemons/com.crowdstrike.falcond.plist`. If plist exists, `installed=True`. Version from app bundle if present, else `None`.
- **D-16:** Same `detect_apps(report: AuditReport) -> None` interface — mutates `report.apps` in place, always appends one `AppStatus` per app (even `installed=False`), catches per-app exceptions into `report.collection_errors`.

### Service State on Mac
- **D-17:** CrowdStrike and NinjaOne service state populated via `launchctl list <daemon-label>`. Exit code 0 → `service_state = "Running"`, non-zero → `service_state = "Stopped"`. Daemon labels to use: `com.crowdstrike.falcond` (CrowdStrike), NinjaOne label resolved at research time.
- **D-18:** All other Mac apps: `service_state = None` (no LaunchDaemon to query).

### Claude's Discretion
- Exact `system_profiler` JSON key names for Apple Silicon chip type — Claude reads current macOS docs or uses `SPHardwareDataType` output and selects the right key.
- NinjaOne LaunchDaemon label on Mac (may be `com.ninjarmm.agent` or similar) — Claude verifies at research time.
- Whether `pwd.getpwall()` requires elevation to see all accounts, and fallback if restricted.
- Company Portal on Mac: may be at `/Applications/Company Portal.app` or `/Applications/Microsoft Company Portal.app` — Claude picks the correct bundle path at research time.
- Microsoft 365 on Mac: may be `/Applications/Microsoft 365.app` or suite of individual apps (`Word.app`, etc.) — Claude selects the detection strategy that best mirrors the Windows single-suite intent.
- How to mock `plistlib.load()` in unit tests — Claude picks the cleanest approach.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §PLAT-V2-01 through PLAT-V2-04 — Mac hardware, profile, app, and output requirements. These are the acceptance criteria.
- `.planning/REQUIREMENTS.md` §Out of Scope — Mac PyInstaller packaging and MERP on Mac are explicitly out of scope.

### Data Contract
- `models.py` — AuditReport, AppStatus, Warning dataclasses. All fields Mac collectors populate must match existing field names and types. No new fields added to AuditReport in this phase.

### Existing Collector Pattern
- `collectors/windows/hardware.py` — Reference implementation for the in-place mutation pattern, degradation behavior, and `collection_errors` usage. Mac collectors must mirror this interface.
- `collectors/windows/apps.py` — Reference for `APP_SPECS` table structure, `detect_apps()` interface, per-app exception handling, and `AppStatus` population. `MAC_APP_SPECS` should parallel this design.
- `collectors/__init__.py` — Platform dispatch point. Phase 10 adds `sys.platform == "darwin"` branch here.

### Technical Constraints
- `CLAUDE.md` — Constraints: `Win32_Product` prohibited (Windows-only, irrelevant on Mac but noted for context), `sys.executable` path behavior in frozen vs script contexts.

### Prior Phase Context
- `.planning/phases/02-system-collectors/02-CONTEXT.md` — D-01 through D-11: degradation pattern, never-raise rule, `collection_errors` contract. All apply to Mac collectors.
- `.planning/phases/04-app-detection-and-compliance-engine/04-CONTEXT.md` — D-10 through D-16: `APP_SPECS` table design, config-driven detection, detection_method values, always-append rule. Mac app detection mirrors this pattern.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `psutil` — Already a dependency. `virtual_memory().total` and `disk_usage("/")` work on Mac with no changes.
- `plistlib` — Python stdlib. No new dependency for parsing `Info.plist` version strings.
- `pwd` — Python stdlib. Available on Mac for user enumeration. Not available on Windows (no change needed to existing Windows code).
- `models.py` — AuditReport already has all needed fields. Mac collectors populate the same fields as Windows collectors.
- `health_checks.py` — `evaluate_warnings()` uses `os_build` and disk fields already. Works on Mac once collectors populate those fields.

### Established Patterns
- In-place mutation: `collect_*(report: AuditReport) -> None`. Never raises. All failures go to `report.collection_errors`.
- `_wmi_module` / `_WMI_AVAILABLE` guard pattern (Windows) → Mac equivalent: guard each subprocess call with try/except, degrade to `None` + error log.
- `AppStatus(installed=False, ...)` always appended — even for undetected apps. Renderer relies on this.

### Integration Points
- `collectors/__init__.py`: add `if sys.platform == "darwin":` branch importing from `collectors.mac`.
- `main.py`: add `sys.platform == "darwin"` check for output path (`Path(__file__).parent`) and for `open` auto-launch.
- No changes needed to `renderer/`, `health_checks.py`, `parsers/`, or `models.py` — they're already platform-agnostic.

</code_context>

<specifics>
## Specific Ideas

- The tool should feel identical to the Windows version from the IT perspective — same HTML sheet, same fields populated, same "Not Found" for missing apps. Mac-specific values (e.g., "macOS 14.4.1" instead of "Windows 11") simply flow through the existing renderer fields.
- STATE.md callout: "Mac app bundle paths require live Mac validation — no Mac build tested yet." The planner should note that MAC_APP_SPECS bundle names need to be verified against real macOS installs, not just assumed.
- CPU fixture note from STATE.md: "system_profiler chip_type vs cpu_type — unit test fixtures needed from both Intel and Apple Silicon." Tests must parametrize across both hardware generations.

</specifics>

<deferred>
## Deferred Ideas

- Mac PyInstaller packaging (.app bundle + Gatekeeper notarization) — v3. Requires Apple Developer account.
- macOS-specific health warnings (e.g., SIP disabled, Gatekeeper disabled) — out of scope for v2. Phase 10 reuses the existing Windows health checks as-is; they degrade cleanly (no Windows-only API calls in health_checks.py).
- MERP detection on Mac — explicitly out of scope (Windows-only ERP).
- GitHub Actions macOS CI runner for integration tests — deferred. Phase 10 uses mocked tests only for CI.

</deferred>

---

*Phase: 10-mac-collectors*
*Context gathered: 2026-05-08*
