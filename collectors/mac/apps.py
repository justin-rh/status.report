"""macOS application detection collector.
Detects 7 target applications via .app bundle existence in /Applications/,
Info.plist version parsing, LaunchDaemon plist fallback, and launchctl service state.

All detection runs per-app. Never raises across the layer boundary — each app's
exceptions are caught individually and appended to report.collection_errors (D-16).
"""
from __future__ import annotations

import plistlib
import subprocess
from pathlib import Path

from models import AuditReport, AppStatus

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

APPLICATIONS_DIR = Path("/Applications")
LAUNCH_DAEMONS_DIR = Path("/Library/LaunchDaemons")

# ---------------------------------------------------------------------------
# MAC_APP_SPECS — config-driven detection table (D-13, D-14)
#
# Each entry declares:
#   name                (str)       — AppStatus.name value
#   app_dir             (str)       — optional; directory check via APPLICATIONS_DIR / app_dir
#   app_bundle          (str)       — optional; .app bundle check via APPLICATIONS_DIR / app_bundle
#   fallback_bundles    (list[str]) — optional; tried in order if app_bundle not found (M365)
#   launchdaemon_plist  (str)       — optional; plist filename in LAUNCH_DAEMONS_DIR (CrowdStrike D-15)
#   launchdaemon_label  (str)       — optional; label for launchctl list call (D-17)
#
# Detection notes:
#   NinjaOne: directory check (NOT .app bundle) — /Applications/NinjaRMMAgent/ (Pitfall 5)
#   CrowdStrike: bundle + LaunchDaemon plist fallback + service state (D-15, D-17)
#   Microsoft 365: no monolithic bundle on Mac — Word sentinel + fallbacks (RESEARCH)
#   Zoom: bundle is "zoom.us.app" NOT "Zoom.app" — Pitfall 3
# ---------------------------------------------------------------------------

MAC_APP_SPECS: list[dict] = [
    {
        "name": "NinjaOne",
        "app_dir": "NinjaRMMAgent",          # Directory check — NOT .app bundle (Pitfall 5)
        "launchdaemon_label": "com.ninjarmm.agent",  # TODO: verify on live Mac (LOW confidence)
    },
    {
        "name": "CrowdStrike Falcon",
        "app_bundle": "Falcon.app",
        "launchdaemon_plist": "com.crowdstrike.falcond.plist",
        "launchdaemon_label": "com.crowdstrike.falcond",
    },
    {
        "name": "Microsoft 365",
        "app_bundle": "Microsoft Word.app",  # Primary sentinel — no monolithic bundle on Mac
        "fallback_bundles": [
            "Microsoft Excel.app",
            "Microsoft PowerPoint.app",
            "Microsoft Outlook.app",
        ],
    },
    {
        "name": "Zoom",
        "app_bundle": "zoom.us.app",         # NOT "Zoom.app" — Pitfall 3
    },
    {
        "name": "Google Chrome",
        "app_bundle": "Google Chrome.app",
    },
    {
        "name": "Claude",
        "app_bundle": "Claude.app",
    },
    {
        "name": "Company Portal",
        "app_bundle": "Company Portal.app",
    },
]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _detect_bundle(app_bundle: str) -> tuple[bool, str | None]:
    """Return (installed, version) for an /Applications/ .app bundle.

    Opens Info.plist in binary mode — plistlib.load() requires 'rb' (Pitfall 2).
    Returns (True, None) if bundle exists but version is unreadable.
    Returns (False, None) if bundle does not exist.
    """
    bundle_path = APPLICATIONS_DIR / app_bundle
    if not bundle_path.exists():
        return False, None
    plist_path = bundle_path / "Contents" / "Info.plist"
    try:
        with plist_path.open("rb") as f:
            data = plistlib.load(f)
        return True, data.get("CFBundleShortVersionString")
    except (OSError, plistlib.InvalidFileException, KeyError, Exception):
        return True, None  # Bundle exists, version unknown


def _query_launchd(label: str) -> str:
    """Return 'Running' if launchctl reports the daemon loaded, else 'Stopped'.

    Exit code 0 = daemon found in launchd registry (may or may not have active PID).
    This is best-effort — standard user cannot reliably query system daemons on
    macOS Monterey+ without sudo. See RESEARCH.md Pitfall 6.
    Treats "Stopped" as the safe fallback for any error or non-zero exit.
    """
    try:
        result = subprocess.run(
            ["launchctl", "list", label],
            capture_output=True, text=True, timeout=5,
        )
        return "Running" if result.returncode == 0 else "Stopped"
    except (OSError, subprocess.TimeoutExpired):
        return "Stopped"


def _detect_one_app(spec: dict, report: AuditReport) -> None:
    """Run detection for a single app spec and append one AppStatus to report.apps.

    Detection precedence:
    1. Directory check if app_dir present (NinjaOne — no .app bundle)
    2. Bundle check (app_bundle) with fallback_bundles for Microsoft 365
    3. LaunchDaemon plist fallback for CrowdStrike if bundle absent (D-15)
    4. Service state via launchctl if launchdaemon_label present and installed (D-17)

    Never raises — caller (detect_apps) wraps in try/except.
    """
    installed = False
    version: str | None = None
    service_state: str | None = None
    detection_method = "filesystem"  # Mac detection is always filesystem-based

    # Step 1: Directory check (NinjaOne special case — no .app bundle)
    if "app_dir" in spec:
        app_dir_path = APPLICATIONS_DIR / spec["app_dir"]
        if app_dir_path.is_dir():
            installed = True
            version = None  # No Info.plist in NinjaRMMAgent directory

    # Step 2: Bundle check (standard .app bundles)
    if not installed and "app_bundle" in spec:
        installed, version = _detect_bundle(spec["app_bundle"])
        # Microsoft 365: try fallback bundles if primary sentinel missing
        if not installed and "fallback_bundles" in spec:
            for fb in spec["fallback_bundles"]:
                fb_installed, fb_version = _detect_bundle(fb)
                if fb_installed:
                    installed = True
                    version = fb_version
                    break

    # Step 3: LaunchDaemon plist fallback (CrowdStrike — D-15)
    if not installed and "launchdaemon_plist" in spec:
        plist_path = LAUNCH_DAEMONS_DIR / spec["launchdaemon_plist"]
        if plist_path.exists():
            installed = True
            version = None  # Plist existence only — no version available here

    # Step 4: Service state via launchctl (CrowdStrike + NinjaOne — D-17)
    if installed and "launchdaemon_label" in spec:
        service_state = _query_launchd(spec["launchdaemon_label"])

    report.apps.append(AppStatus(
        name=spec["name"],
        installed=installed,
        version=version,
        service_state=service_state,
        detection_method=detection_method,
    ))


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def detect_apps(report: AuditReport) -> None:
    """Populate report.apps with one AppStatus per target application.

    Iterates MAC_APP_SPECS. Each app's detection is wrapped in its own try/except
    so a failure in one app never blocks detection of subsequent apps (D-16).
    On exception: appends error to collection_errors AND appends
    AppStatus(installed=False, error=...) to preserve always-append rule (D-16).
    """
    for spec in MAC_APP_SPECS:
        try:
            _detect_one_app(spec, report)
        except Exception as exc:
            report.collection_errors.append(
                f"App detection failed for {spec['name']}: {exc}"
            )
            report.apps.append(AppStatus(
                name=spec["name"],
                installed=False,
                error=str(exc),
            ))


def collect_apps(report: AuditReport) -> None:
    """Public entry point for app detection. Calls detect_apps(report).
    Never raises.
    """
    detect_apps(report)
