"""Unit tests for collectors.mac.apps — collect_apps / detect_apps functions.

Mock pattern: patch("collectors.mac.apps.Path") patches the Path reference inside
apps.py itself. patch("collectors.mac.apps.plistlib") patches plistlib module-level
reference — same pattern as apps_mod.winreg in Windows tests.

All 10 behaviors from the plan are tested here (Tests 1-10).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest
import plistlib

from models import AuditReport
from parsers.name_parser import parse_hostname
import collectors.mac.apps as apps_mod


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-MAC", parsed_hostname=parse_hostname("TEST-MAC"))


# ---------------------------------------------------------------------------
# Test 1: detect_apps() produces exactly 7 AppStatus entries when nothing installed
# ---------------------------------------------------------------------------

def test_all_apps_always_present():
    """D-16: every app produces one AppStatus entry even when nothing is installed."""
    with patch("collectors.mac.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.is_dir.return_value = False
        mock_path.return_value.__truediv__ = lambda self, other: self
        report = make_report()
        apps_mod.collect_apps(report)

    app_names = [a.name for a in report.apps]
    expected_names = [
        "NinjaOne",
        "CrowdStrike Falcon",
        "Microsoft 365",
        "Zoom",
        "Google Chrome",
        "Claude",
        "Company Portal",
    ]
    assert len(report.apps) == 7, f"Expected 7 apps, got {len(report.apps)}"
    for expected in expected_names:
        assert expected in app_names, f"Missing app: {expected}"


# ---------------------------------------------------------------------------
# Test 2: CrowdStrike with Falcon.app missing but plist present → installed=True
# ---------------------------------------------------------------------------

def test_crowdstrike_falls_back_to_launchdaemon_plist():
    """CrowdStrike falls back to /Library/LaunchDaemons/com.crowdstrike.falcond.plist
    when Falcon.app is absent."""
    def path_factory(p):
        obj = MagicMock()
        obj.__truediv__ = lambda self, other: path_factory(f"{p}/{other}")
        p_str = str(p)
        # Falcon.app bundle does not exist
        if "Falcon.app" in p_str and "LaunchDaemons" not in p_str:
            obj.exists.return_value = False
            obj.is_dir.return_value = False
        # LaunchDaemon plist exists
        elif "com.crowdstrike.falcond.plist" in p_str:
            obj.exists.return_value = True
            obj.is_dir.return_value = False
        else:
            obj.exists.return_value = False
            obj.is_dir.return_value = False
        return obj

    with patch("collectors.mac.apps.Path", side_effect=path_factory), \
         patch.object(apps_mod, "subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(returncode=0)
        mock_sub.TimeoutExpired = __import__("subprocess").TimeoutExpired
        report = make_report()
        apps_mod.collect_apps(report)

    cs = next(a for a in report.apps if a.name == "CrowdStrike Falcon")
    assert cs.installed is True
    assert cs.version is None


# ---------------------------------------------------------------------------
# Test 3: Microsoft 365 — Word missing but Excel present → installed=True
# ---------------------------------------------------------------------------

def test_m365_fallback_bundle_detected():
    """Microsoft 365 fallback: Word.app missing but Excel.app present → installed=True."""
    def path_factory(p):
        obj = MagicMock()
        obj.__truediv__ = lambda self, other: path_factory(f"{p}/{other}")
        p_str = str(p)
        if "Microsoft Word.app" in p_str and "Contents" not in p_str:
            obj.exists.return_value = False
            obj.is_dir.return_value = False
        elif "Microsoft Excel.app" in p_str and "Contents" not in p_str:
            obj.exists.return_value = True
            obj.is_dir.return_value = True
        else:
            obj.exists.return_value = False
            obj.is_dir.return_value = False
        return obj

    with patch("collectors.mac.apps.Path", side_effect=path_factory), \
         patch("collectors.mac.apps.plistlib") as mock_plib:
        mock_plib.load.return_value = {"CFBundleShortVersionString": "16.82.0"}
        mock_plib.InvalidFileException = plistlib.InvalidFileException
        report = make_report()
        apps_mod.collect_apps(report)

    m365 = next(a for a in report.apps if a.name == "Microsoft 365")
    assert m365.installed is True


# ---------------------------------------------------------------------------
# Test 4: NinjaOne — /Applications/NinjaRMMAgent/ directory exists → installed=True
# ---------------------------------------------------------------------------

def test_ninjaone_detected_via_directory():
    """/Applications/NinjaRMMAgent/ directory exists → NinjaOne installed=True, version=None."""
    def path_factory(p):
        obj = MagicMock()
        obj.__truediv__ = lambda self, other: path_factory(f"{p}/{other}")
        p_str = str(p)
        if "NinjaRMMAgent" in p_str:
            obj.is_dir.return_value = True
            obj.exists.return_value = True
        else:
            obj.is_dir.return_value = False
            obj.exists.return_value = False
        return obj

    with patch("collectors.mac.apps.Path", side_effect=path_factory), \
         patch.object(apps_mod, "subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(returncode=0)
        mock_sub.TimeoutExpired = __import__("subprocess").TimeoutExpired
        report = make_report()
        apps_mod.collect_apps(report)

    ninja = next(a for a in report.apps if a.name == "NinjaOne")
    assert ninja.installed is True
    assert ninja.version is None


# ---------------------------------------------------------------------------
# Test 5: Zoom with zoom.us.app and valid plistlib version → installed=True, version set
# ---------------------------------------------------------------------------

def test_zoom_detected_with_version():
    """Zoom detected via zoom.us.app with plistlib returning version '5.17.0'."""
    def path_factory(p):
        obj = MagicMock()
        obj.__truediv__ = lambda self, other: path_factory(f"{p}/{other}")
        p_str = str(p)
        if "zoom.us.app" in p_str and "Contents" not in p_str:
            obj.exists.return_value = True
            obj.is_dir.return_value = True
        else:
            obj.exists.return_value = False
            obj.is_dir.return_value = False
        return obj

    with patch("collectors.mac.apps.Path", side_effect=path_factory), \
         patch("collectors.mac.apps.plistlib") as mock_plib:
        mock_plib.load.return_value = {"CFBundleShortVersionString": "5.17.0"}
        mock_plib.InvalidFileException = plistlib.InvalidFileException
        report = make_report()
        apps_mod.collect_apps(report)

    zoom = next(a for a in report.apps if a.name == "Zoom")
    assert zoom.installed is True
    assert zoom.version == "5.17.0"


# ---------------------------------------------------------------------------
# Test 6: CrowdStrike installed=True + launchdaemon_label → launchctl called → service_state
# ---------------------------------------------------------------------------

def test_crowdstrike_service_state_populated_when_installed():
    """CrowdStrike with installed=True: launchctl called → service_state='Running' or 'Stopped'."""
    def path_factory(p):
        obj = MagicMock()
        obj.__truediv__ = lambda self, other: path_factory(f"{p}/{other}")
        p_str = str(p)
        if "Falcon.app" in p_str and "Contents" not in p_str:
            obj.exists.return_value = True
            obj.is_dir.return_value = True
        else:
            obj.exists.return_value = False
            obj.is_dir.return_value = False
        return obj

    with patch("collectors.mac.apps.Path", side_effect=path_factory), \
         patch("collectors.mac.apps.plistlib") as mock_plib, \
         patch.object(apps_mod, "subprocess") as mock_sub:
        mock_plib.load.return_value = {"CFBundleShortVersionString": "7.10.0"}
        mock_plib.InvalidFileException = plistlib.InvalidFileException
        mock_sub.run.return_value = MagicMock(returncode=0)
        mock_sub.TimeoutExpired = __import__("subprocess").TimeoutExpired
        report = make_report()
        apps_mod.collect_apps(report)

    cs = next(a for a in report.apps if a.name == "CrowdStrike Falcon")
    assert cs.installed is True
    assert cs.service_state in ("Running", "Stopped")


# ---------------------------------------------------------------------------
# Test 7: Chrome, Claude, Company Portal with bundles present → installed=True + version
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("app_name,bundle_name,version", [
    ("Google Chrome", "Google Chrome.app", "124.0.0"),
    ("Claude", "Claude.app", "0.40.0"),
    ("Company Portal", "Company Portal.app", "5.2.0"),
])
def test_standard_bundle_apps_detected(app_name, bundle_name, version):
    """Chrome, Claude, Company Portal detected via .app bundle with version from plist."""
    def path_factory(p):
        obj = MagicMock()
        obj.__truediv__ = lambda self, other: path_factory(f"{p}/{other}")
        p_str = str(p)
        if bundle_name in p_str and "Contents" not in p_str:
            obj.exists.return_value = True
            obj.is_dir.return_value = True
        else:
            obj.exists.return_value = False
            obj.is_dir.return_value = False
        return obj

    with patch("collectors.mac.apps.Path", side_effect=path_factory), \
         patch("collectors.mac.apps.plistlib") as mock_plib:
        mock_plib.load.return_value = {"CFBundleShortVersionString": version}
        mock_plib.InvalidFileException = plistlib.InvalidFileException
        report = make_report()
        apps_mod.collect_apps(report)

    app = next(a for a in report.apps if a.name == app_name)
    assert app.installed is True
    assert app.version == version


# ---------------------------------------------------------------------------
# Test 8: per-app exception → AppStatus(installed=False, error=...) AND collection_errors
# ---------------------------------------------------------------------------

def test_per_app_exception_still_appends_app_status():
    """Per-app exception: AppStatus(installed=False, error=str(exc)) appended AND collection_errors updated."""
    # Force _detect_one_app to raise for ALL apps
    with patch.object(apps_mod, "_detect_one_app", side_effect=RuntimeError("forced failure")):
        report = make_report()
        apps_mod.collect_apps(report)

    # All 7 apps must still have an AppStatus entry
    assert len(report.apps) == 7
    for app in report.apps:
        assert app.installed is False
        assert app.error is not None
    # collection_errors must have entries
    assert len(report.collection_errors) == 7


# ---------------------------------------------------------------------------
# Test 9: plistlib.load() is always called with "rb" mode
# ---------------------------------------------------------------------------

def test_plistlib_load_called_with_binary_mode():
    """plistlib.load() is always called with a file opened in 'rb' mode."""
    open_calls = []

    def path_factory(p):
        obj = MagicMock()
        p_str = str(p)

        def truediv(self, other):
            return path_factory(f"{p}/{other}")

        obj.__truediv__ = truediv

        # Only Claude.app will be present to keep things simple
        if "Claude.app" in p_str and "Contents" not in p_str:
            obj.exists.return_value = True
            obj.is_dir.return_value = True
        else:
            obj.exists.return_value = False
            obj.is_dir.return_value = False

        # Track open() calls with mode
        def mock_open(mode="r"):
            open_calls.append(mode)
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=MagicMock())
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        obj.open = mock_open
        return obj

    with patch("collectors.mac.apps.Path", side_effect=path_factory), \
         patch("collectors.mac.apps.plistlib") as mock_plib:
        mock_plib.load.return_value = {"CFBundleShortVersionString": "1.0.0"}
        mock_plib.InvalidFileException = plistlib.InvalidFileException
        report = make_report()
        apps_mod.collect_apps(report)

    # At least one open call should have used "rb" mode
    assert any(mode == "rb" for mode in open_calls), \
        f"Expected 'rb' mode open call, got: {open_calls}"


# ---------------------------------------------------------------------------
# Test 10: NinjaOne and CrowdStrike get service_state; others get None
# ---------------------------------------------------------------------------

def test_service_state_only_for_ninja_and_crowdstrike():
    """NinjaOne and CrowdStrike get service_state populated; all other apps get service_state=None."""
    # Everything not installed — service_state should be None for all (not installed → no launchctl call)
    with patch("collectors.mac.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.is_dir.return_value = False
        mock_path.return_value.__truediv__ = lambda self, other: mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)

    # When nothing is installed, service_state is None for all apps
    for app in report.apps:
        assert app.service_state is None, \
            f"Expected service_state=None for {app.name} when not installed, got {app.service_state!r}"

    # Now test with NinjaOne installed — it should get service_state
    def path_factory_ninja(p):
        obj = MagicMock()
        obj.__truediv__ = lambda self, other: path_factory_ninja(f"{p}/{other}")
        p_str = str(p)
        if "NinjaRMMAgent" in p_str:
            obj.is_dir.return_value = True
            obj.exists.return_value = True
        else:
            obj.is_dir.return_value = False
            obj.exists.return_value = False
        return obj

    with patch("collectors.mac.apps.Path", side_effect=path_factory_ninja), \
         patch.object(apps_mod, "subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(returncode=0)
        mock_sub.TimeoutExpired = __import__("subprocess").TimeoutExpired
        report2 = make_report()
        apps_mod.collect_apps(report2)

    ninja = next(a for a in report2.apps if a.name == "NinjaOne")
    assert ninja.service_state is not None, "NinjaOne must get service_state when installed"

    # Apps without launchdaemon_label must have service_state=None
    non_service_apps = ["Zoom", "Google Chrome", "Claude", "Company Portal", "Microsoft 365"]
    for app in report2.apps:
        if app.name in non_service_apps:
            assert app.service_state is None, \
                f"{app.name} must have service_state=None (no launchdaemon_label)"
