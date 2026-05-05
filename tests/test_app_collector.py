"""Unit tests for collectors.windows.apps — collect_apps / detect_apps functions.

Mock pattern: patch.object(apps_mod.winreg, ...) patches the winreg reference
inside apps.py itself, not the stdlib module globally. This ensures no real
registry calls occur in CI.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname
import collectors.windows.apps as apps_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))


def _make_fake_ctx() -> MagicMock:
    """Return a MagicMock that acts as a winreg key context manager."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _make_enum_fn(subkeys: list[str]):
    """Return an EnumKey side_effect that yields subkeys by index then raises OSError."""
    def enum_fn(key, index):
        if index < len(subkeys):
            return subkeys[index]
        raise OSError("exhausted")
    return enum_fn


def _make_query_fn(display_name: str, display_version: str | None = None):
    """Return a QueryValueEx side_effect for a single app subkey."""
    def query_fn(key, value_name):
        if value_name == "DisplayName":
            return (display_name, 1)
        if value_name == "DisplayVersion" and display_version is not None:
            return (display_version, 1)
        raise FileNotFoundError(f"no value {value_name!r}")
    return query_fn


# ---------------------------------------------------------------------------
# Test: registry hit — NinjaOne installed
# ---------------------------------------------------------------------------

def test_detect_ninjaone_installed():
    """Registry subkey with NinjaRMMAgent DisplayName → NinjaOne installed=True, version set."""
    subkeys = ["NinjaRMMAgent 5.8.9154"]
    fake_ctx = _make_fake_ctx()

    with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=_make_enum_fn(subkeys)), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=_make_query_fn("NinjaRMMAgent", "13.0.7346")):
        report = make_report()
        apps_mod.collect_apps(report)

    ninja = next(a for a in report.apps if a.name == "NinjaOne")
    assert ninja.installed is True
    assert ninja.version == "13.0.7346"
    assert ninja.detection_method == "registry"


# ---------------------------------------------------------------------------
# Test: registry miss — all apps not installed
# ---------------------------------------------------------------------------

def test_detect_app_registry_miss():
    """OpenKey raises OSError for all paths + Path.exists()=False → all 7 apps installed=False."""
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no registry")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    assert len(report.apps) == 7
    for app in report.apps:
        assert app.installed is False, f"{app.name} should be installed=False"


# ---------------------------------------------------------------------------
# Test: MERP filesystem detection — primary path, no registry
# ---------------------------------------------------------------------------

def test_merp_filesystem_primary():
    """MERP detected via filesystem path → installed=True, detection_method='filesystem'."""
    with patch("collectors.windows.apps.Path") as mock_path, \
         patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no reg")):
        mock_path.return_value.exists.return_value = True
        report = make_report()
        apps_mod.collect_apps(report)

    merp = next(a for a in report.apps if a.name == "MERP")
    assert merp.installed is True
    assert merp.detection_method == "filesystem"


# ---------------------------------------------------------------------------
# Test: MERP filesystem + registry version
# ---------------------------------------------------------------------------

def test_merp_filesystem_with_registry_version():
    """MERP filesystem hit + registry returns WindX version → installed, version populated."""
    subkeys = ["WindX 1.2.3"]
    fake_ctx = _make_fake_ctx()

    with patch("collectors.windows.apps.Path") as mock_path, \
         patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=_make_enum_fn(subkeys)), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=_make_query_fn("WindX", "1.2.3")):
        mock_path.return_value.exists.return_value = True
        report = make_report()
        apps_mod.collect_apps(report)

    merp = next(a for a in report.apps if a.name == "MERP")
    assert merp.installed is True
    assert merp.detection_method == "filesystem"
    assert merp.version == "1.2.3"


# ---------------------------------------------------------------------------
# Test: Claude MSIX detection
# ---------------------------------------------------------------------------

def test_claude_msix_detection():
    """Claude MSIX key in AppModel repo → installed=True, version from key name."""
    claude_pkg_key = "Claude_1.1617.0.0_x64__pzs8sxrjxfjjc"

    # Route OpenKey calls: the MSIX repo path gets a distinct context manager so
    # EnumKey can distinguish MSIX repo enumeration from Uninstall key enumeration.
    msix_ctx = _make_fake_ctx()   # returned only for the MSIX repo path
    other_ctx = _make_fake_ctx()  # returned for all other (Uninstall) paths

    def open_key_side(hive_or_key, path_or_subkey, *args, **kwargs):
        # Identify the MSIX repo open by its string path segment
        if isinstance(path_or_subkey, str) and "AppModel" in path_or_subkey:
            return msix_ctx
        return other_ctx

    def enum_fn(key, index):
        if key is msix_ctx:
            # MSIX repo enumeration — return the Claude package key at index 0
            if index == 0:
                return claude_pkg_key
            raise OSError("exhausted")
        # All other enumerations (Uninstall paths) → immediately exhausted
        raise OSError("exhausted")

    with patch.object(apps_mod.winreg, "OpenKey", side_effect=open_key_side), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=enum_fn), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=FileNotFoundError("no value")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    claude = next(a for a in report.apps if a.name == "Claude")
    assert claude.installed is True
    assert claude.version == "1.1617.0.0"
    assert claude.detection_method == "registry"


# ---------------------------------------------------------------------------
# Test: CrowdStrike service state — Automatic (Start DWORD = 2)
# ---------------------------------------------------------------------------

def test_crowdstrike_service_state_automatic():
    """CrowdStrike registry hit + service key Start=2 → service_state='Automatic'."""
    subkeys = ["CrowdStrike Windows Sensor"]
    fake_ctx = _make_fake_ctx()

    # We need two OpenKey behaviors:
    #   1. Uninstall path open → return fake_ctx for enumeration
    #   2. Service path open → return fake_ctx with QueryValueEx returning Start=2
    #
    # Strategy: track calls. The service key read happens after the registry sweep.
    # Use a call counter: all calls use fake_ctx, but QueryValueEx is routing-aware.

    query_call_count = [0]

    def query_fn(key, value_name):
        query_call_count[0] += 1
        if value_name == "DisplayName":
            return ("CrowdStrike Windows Sensor", 1)
        if value_name == "DisplayVersion":
            return ("7.14.17706.0", 1)
        if value_name == "Start":
            return (2, 4)  # REG_DWORD = 4
        raise FileNotFoundError(f"no value {value_name!r}")

    with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey",
                      side_effect=_make_enum_fn(subkeys)), \
         patch.object(apps_mod.winreg, "QueryValueEx", side_effect=query_fn), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    cs = next(a for a in report.apps if a.name == "CrowdStrike Falcon")
    assert cs.installed is True
    assert cs.service_state == "Automatic"


# ---------------------------------------------------------------------------
# Test: CrowdStrike service state absent — service key missing
# ---------------------------------------------------------------------------

def test_crowdstrike_service_state_none_when_key_absent():
    """CrowdStrike installed via registry but service key raises OSError → service_state=None."""
    subkeys = ["CrowdStrike Windows Sensor"]
    fake_uninstall_ctx = _make_fake_ctx()
    fake_service_ctx = _make_fake_ctx()

    open_call_count = [0]

    # Track whether we're opening a service key path
    def open_key_side(hive_or_key, path_or_subkey, *args, **kwargs):
        if isinstance(path_or_subkey, str) and "CSFalconService" in path_or_subkey:
            raise OSError("service key not found")
        return fake_uninstall_ctx

    def query_fn(key, value_name):
        if value_name == "DisplayName":
            return ("CrowdStrike Windows Sensor", 1)
        if value_name == "DisplayVersion":
            return ("7.14.17706.0", 1)
        raise FileNotFoundError(f"no value {value_name!r}")

    with patch.object(apps_mod.winreg, "OpenKey", side_effect=open_key_side), \
         patch.object(apps_mod.winreg, "EnumKey",
                      side_effect=_make_enum_fn(subkeys)), \
         patch.object(apps_mod.winreg, "QueryValueEx", side_effect=query_fn), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    cs = next(a for a in report.apps if a.name == "CrowdStrike Falcon")
    assert cs.installed is True
    assert cs.service_state is None


# ---------------------------------------------------------------------------
# Test: collect_apps never raises
# ---------------------------------------------------------------------------

def test_collect_apps_never_raises():
    """collect_apps must not propagate any exception — errors go to collection_errors."""
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=PermissionError("denied")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        try:
            report = make_report()
            apps_mod.collect_apps(report)
        except Exception as exc:
            pytest.fail(f"collect_apps raised unexpectedly: {exc}")

    # All 7 apps still present even under total registry failure
    assert len(report.apps) == 7


# ---------------------------------------------------------------------------
# Test: all 7 apps always present (D-15)
# ---------------------------------------------------------------------------

def test_all_apps_always_present():
    """D-15: every app produces one AppStatus entry even when nothing is installed."""
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no registry")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    app_names = [a.name for a in report.apps]
    expected_names = [
        "NinjaOne",
        "CrowdStrike Falcon",
        "MERP",
        "Microsoft 365",
        "Zoom",
        "Google Chrome",
        "Claude",
    ]
    for expected in expected_names:
        assert expected in app_names, f"Expected '{expected}' in report.apps but got: {app_names}"
