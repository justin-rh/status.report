"""Unit tests for collectors/__init__.py — platform dispatch in collect_all().

Tests verify:
1. On darwin, collect_all() dispatches to collectors.mac.hardware and collectors.mac.apps
2. On non-darwin, collect_all() dispatches to collectors.windows.hardware and collectors.windows.apps
3. collectors/__init__.py is importable without triggering platform-specific imports
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))


# ---------------------------------------------------------------------------
# Test 1: darwin → collectors.mac dispatch
# ---------------------------------------------------------------------------

def test_collect_all_dispatches_to_mac_on_darwin():
    """When sys.platform is 'darwin', collect_all() must import from collectors.mac."""
    import collectors

    mock_mac_hw = MagicMock()
    mock_mac_apps = MagicMock()

    with patch.dict("sys.modules", {
        "collectors.mac.hardware": mock_mac_hw,
        "collectors.mac.apps": mock_mac_apps,
    }), patch("sys.platform", "darwin"):
        report = make_report()
        collectors.collect_all(report)

    # The mac hardware and app collectors should have been called
    mock_mac_hw.collect_hardware.assert_called_once_with(report)
    mock_mac_hw.collect_profiles.assert_called_once_with(report)
    mock_mac_apps.collect_apps.assert_called_once_with(report)


# ---------------------------------------------------------------------------
# Test 2: non-darwin → collectors.windows dispatch
# ---------------------------------------------------------------------------

def test_collect_all_dispatches_to_windows_on_non_darwin():
    """When sys.platform is not 'darwin', collect_all() must import from collectors.windows."""
    import collectors

    mock_win_hw = MagicMock()
    mock_win_apps = MagicMock()

    with patch.dict("sys.modules", {
        "collectors.windows.hardware": mock_win_hw,
        "collectors.windows.apps": mock_win_apps,
    }), patch("sys.platform", "win32"):
        report = make_report()
        collectors.collect_all(report)

    mock_win_hw.collect_hardware.assert_called_once_with(report)
    mock_win_hw.collect_profiles.assert_called_once_with(report)
    mock_win_apps.collect_apps.assert_called_once_with(report)


# ---------------------------------------------------------------------------
# Test 3: module importable without triggering platform-specific imports
# ---------------------------------------------------------------------------

def test_collectors_init_importable_without_platform_imports():
    """collectors/__init__.py must be importable without running darwin or windows imports."""
    # Simply importing should not raise on any platform
    import collectors  # noqa: F401
    from collectors import collect_all  # noqa: F401
    assert callable(collect_all)
