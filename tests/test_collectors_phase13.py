"""Tests for Phase 13 collector additions: uptime collection and WUA pending updates.

RED phase: these tests FAIL before the collector changes are applied.
Tests cover:
- _collect_uptime() in windows/hardware.py
- _collect_uptime() in mac/hardware.py
- collect_pending_updates() in windows/hardware.py (_WIN32COM_AVAILABLE guard)
- collect_all() wiring in collectors/__init__.py (Windows branch only)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))


# ---------------------------------------------------------------------------
# Windows _collect_uptime
# ---------------------------------------------------------------------------

class TestWindowsCollectUptime:
    """_collect_uptime in collectors/windows/hardware.py."""

    def test_collect_uptime_populates_uptime_seconds(self):
        """collect_hardware populates uptime_seconds as a positive integer."""
        from collectors.windows.hardware import collect_hardware
        import collectors.windows.hardware as hw_mod

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.return_value.total = 16 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.total = 500 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.free = 200 * (1024 ** 3)
        mock_psutil.boot_time.return_value = 1.0  # epoch seconds (old boot)

        with patch.object(hw_mod, "psutil", mock_psutil), \
             patch.object(hw_mod, "_WMI_AVAILABLE", False), \
             patch("time.time", return_value=86401.0):  # ~24 hours uptime
            report = make_report()
            collect_hardware(report)

        assert report.uptime_seconds is not None
        assert isinstance(report.uptime_seconds, int)
        assert report.uptime_seconds > 0

    def test_collect_uptime_degrades_on_exception(self):
        """_collect_uptime appends to collection_errors on exception; uptime_seconds stays None."""
        from collectors.windows.hardware import collect_hardware
        import collectors.windows.hardware as hw_mod

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.return_value.total = 16 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.total = 500 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.free = 200 * (1024 ** 3)
        mock_psutil.boot_time.side_effect = RuntimeError("boot_time unavailable")

        with patch.object(hw_mod, "psutil", mock_psutil), \
             patch.object(hw_mod, "_WMI_AVAILABLE", False):
            report = make_report()
            collect_hardware(report)

        assert report.uptime_seconds is None
        assert any("uptime" in e.lower() for e in report.collection_errors)

    def test_collect_uptime_is_last_call_in_collect_hardware(self):
        """_collect_uptime is called as part of collect_hardware (final step)."""
        import collectors.windows.hardware as hw_mod

        called_order = []

        def track(name):
            def inner(report):
                called_order.append(name)
            return inner

        with patch.object(hw_mod, "_collect_os", track("_collect_os")), \
             patch.object(hw_mod, "_collect_cpu_model", track("_collect_cpu_model")), \
             patch.object(hw_mod, "_collect_memory_and_disk", track("_collect_memory_and_disk")), \
             patch.object(hw_mod, "_collect_current_user", track("_collect_current_user")), \
             patch.object(hw_mod, "_collect_serial_number", track("_collect_serial_number")), \
             patch.object(hw_mod, "_collect_uptime", track("_collect_uptime")):
            report = make_report()
            hw_mod.collect_hardware(report)

        assert called_order[-1] == "_collect_uptime", f"Expected _collect_uptime last, got: {called_order}"
        assert "_collect_uptime" in called_order

    def test_win32com_available_guard_exists(self):
        """_WIN32COM_AVAILABLE module flag is defined."""
        import collectors.windows.hardware as hw_mod
        assert hasattr(hw_mod, "_WIN32COM_AVAILABLE")
        assert isinstance(hw_mod._WIN32COM_AVAILABLE, bool)


# ---------------------------------------------------------------------------
# Windows collect_pending_updates
# ---------------------------------------------------------------------------

class TestCollectPendingUpdates:
    """collect_pending_updates() in collectors/windows/hardware.py."""

    def test_collect_pending_updates_is_exported(self):
        """collect_pending_updates is importable from collectors.windows.hardware."""
        from collectors.windows.hardware import collect_pending_updates
        assert callable(collect_pending_updates)

    def test_collect_pending_updates_returns_none_when_guard_false(self):
        """When _WIN32COM_AVAILABLE is False, pending_updates stays None (CI path)."""
        from collectors.windows.hardware import collect_pending_updates
        import collectors.windows.hardware as hw_mod

        with patch.object(hw_mod, "_WIN32COM_AVAILABLE", False):
            report = make_report()
            collect_pending_updates(report)

        assert report.pending_updates is None
        assert len(report.collection_errors) == 0

    def test_collect_pending_updates_sets_count_when_com_available(self):
        """When _WIN32COM_AVAILABLE is True and COM succeeds, pending_updates is set."""
        from collectors.windows.hardware import collect_pending_updates
        import collectors.windows.hardware as hw_mod

        mock_updates = MagicMock()
        mock_updates.Count = 7

        mock_result = MagicMock()
        mock_result.Updates = mock_updates

        mock_searcher = MagicMock()
        mock_searcher.Search.return_value = mock_result

        mock_session = MagicMock()
        mock_session.CreateUpdateSearcher.return_value = mock_searcher

        mock_com = MagicMock()
        mock_com.Dispatch.return_value = mock_session

        with patch.object(hw_mod, "_WIN32COM_AVAILABLE", True), \
             patch.object(hw_mod, "_win32com_client", mock_com, create=True):
            report = make_report()
            collect_pending_updates(report)

        assert report.pending_updates == 7

    def test_collect_pending_updates_degrades_on_com_exception(self):
        """COM error appends to collection_errors; pending_updates stays None."""
        from collectors.windows.hardware import collect_pending_updates
        import collectors.windows.hardware as hw_mod

        mock_com = MagicMock()
        mock_com.Dispatch.side_effect = Exception("COMError: access denied")

        with patch.object(hw_mod, "_WIN32COM_AVAILABLE", True), \
             patch.object(hw_mod, "_win32com_client", mock_com, create=True):
            report = make_report()
            collect_pending_updates(report)

        assert report.pending_updates is None
        assert any("pending updates" in e.lower() for e in report.collection_errors)

    def test_collect_pending_updates_never_raises(self):
        """collect_pending_updates must not raise under any circumstances."""
        from collectors.windows.hardware import collect_pending_updates
        import collectors.windows.hardware as hw_mod

        mock_com = MagicMock()
        mock_com.Dispatch.side_effect = RuntimeError("total COM failure")

        with patch.object(hw_mod, "_WIN32COM_AVAILABLE", True), \
             patch.object(hw_mod, "_win32com_client", mock_com, create=True):
            report = make_report()
            try:
                collect_pending_updates(report)
            except Exception as exc:
                pytest.fail(f"collect_pending_updates raised: {exc}")


# ---------------------------------------------------------------------------
# Mac _collect_uptime
# ---------------------------------------------------------------------------

class TestMacCollectUptime:
    """_collect_uptime in collectors/mac/hardware.py."""

    def test_mac_collect_uptime_populates_uptime_seconds(self):
        """collect_hardware on Mac populates uptime_seconds as a positive integer."""
        import collectors.mac.hardware as mac_hw_mod

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.return_value.total = 16 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.total = 500 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.free = 200 * (1024 ** 3)
        mock_psutil.boot_time.return_value = 1.0

        with patch.object(mac_hw_mod, "psutil", mock_psutil), \
             patch("subprocess.run", side_effect=Exception("no subprocess in test")), \
             patch("time.time", return_value=86401.0):
            report = make_report()
            mac_hw_mod.collect_hardware(report)

        assert report.uptime_seconds is not None
        assert isinstance(report.uptime_seconds, int)
        assert report.uptime_seconds > 0

    def test_mac_collect_uptime_degrades_on_exception(self):
        """Mac _collect_uptime appends to collection_errors on exception."""
        import collectors.mac.hardware as mac_hw_mod

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.return_value.total = 16 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.total = 500 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.free = 200 * (1024 ** 3)
        mock_psutil.boot_time.side_effect = RuntimeError("boot_time failed")

        with patch.object(mac_hw_mod, "psutil", mock_psutil), \
             patch("subprocess.run", side_effect=Exception("no subprocess")):
            report = make_report()
            mac_hw_mod.collect_hardware(report)

        assert report.uptime_seconds is None
        assert any("uptime" in e.lower() for e in report.collection_errors)

    def test_mac_collect_uptime_is_last_call_in_collect_hardware(self):
        """_collect_uptime is called as the final step in Mac collect_hardware."""
        import collectors.mac.hardware as mac_hw_mod

        called_order = []

        def track(name):
            def inner(report):
                called_order.append(name)
            return inner

        with patch.object(mac_hw_mod, "_collect_os", track("_collect_os")), \
             patch.object(mac_hw_mod, "_collect_cpu_model", track("_collect_cpu_model")), \
             patch.object(mac_hw_mod, "_collect_memory_and_disk", track("_collect_memory_and_disk")), \
             patch.object(mac_hw_mod, "_collect_current_user", track("_collect_current_user")), \
             patch.object(mac_hw_mod, "_collect_uptime", track("_collect_uptime")):
            report = make_report()
            mac_hw_mod.collect_hardware(report)

        assert called_order[-1] == "_collect_uptime", f"Expected _collect_uptime last, got: {called_order}"


# ---------------------------------------------------------------------------
# collectors/__init__.py — Windows branch wiring
# ---------------------------------------------------------------------------

class TestCollectAllPhase13Wiring:
    """collect_all() in collectors/__init__.py calls collect_pending_updates on Windows only."""

    def test_collect_all_calls_collect_pending_updates_on_windows(self):
        """On Windows, collect_all calls collect_pending_updates after collect_apps."""
        import collectors

        mock_win_hw = MagicMock()
        mock_win_apps = MagicMock()

        with patch.dict("sys.modules", {
            "collectors.windows.hardware": mock_win_hw,
            "collectors.windows.apps": mock_win_apps,
        }), patch("sys.platform", "win32"):
            report = make_report()
            collectors.collect_all(report)

        mock_win_hw.collect_pending_updates.assert_called_once_with(report)

    def test_collect_all_does_not_call_collect_pending_updates_on_mac(self):
        """On darwin, collect_all does NOT call collect_pending_updates."""
        import collectors

        mock_mac_hw = MagicMock()
        mock_mac_apps = MagicMock()

        with patch.dict("sys.modules", {
            "collectors.mac.hardware": mock_mac_hw,
            "collectors.mac.apps": mock_mac_apps,
        }), patch("sys.platform", "darwin"):
            report = make_report()
            collectors.collect_all(report)

        # Mac hardware mock should NOT have collect_pending_updates called
        mock_mac_hw.collect_pending_updates.assert_not_called()

    def test_collect_all_windows_call_order(self):
        """On Windows: collect_hardware, collect_profiles, collect_apps, then collect_pending_updates."""
        import collectors

        call_order = []

        mock_win_hw = MagicMock()
        mock_win_hw.collect_hardware.side_effect = lambda r: call_order.append("collect_hardware")
        mock_win_hw.collect_profiles.side_effect = lambda r: call_order.append("collect_profiles")
        mock_win_hw.collect_pending_updates.side_effect = lambda r: call_order.append("collect_pending_updates")

        mock_win_apps = MagicMock()
        mock_win_apps.collect_apps.side_effect = lambda r: call_order.append("collect_apps")

        with patch.dict("sys.modules", {
            "collectors.windows.hardware": mock_win_hw,
            "collectors.windows.apps": mock_win_apps,
        }), patch("sys.platform", "win32"):
            report = make_report()
            collectors.collect_all(report)

        assert "collect_pending_updates" in call_order
        apps_idx = call_order.index("collect_apps")
        updates_idx = call_order.index("collect_pending_updates")
        assert updates_idx > apps_idx, "collect_pending_updates must come after collect_apps"
