"""Unit tests for collectors.windows.hardware — collect_hardware function.
RED phase: These tests fail before implementation exists.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))


# ---------------------------------------------------------------------------
# Module import guard — wmi is not available in CI; test that the module
# still imports cleanly without real wmi.
# ---------------------------------------------------------------------------

def test_module_imports_without_real_wmi():
    """collectors.windows.hardware must import even if wmi is unavailable."""
    # Simply importing should not raise
    from collectors.windows import hardware  # noqa: F401


# ---------------------------------------------------------------------------
# _collect_os helpers
# ---------------------------------------------------------------------------

def test_collect_hardware_populates_os_version():
    """os_version is a non-empty string after collect_hardware."""
    from collectors.windows.hardware import collect_hardware

    report = make_report()
    collect_hardware(report)

    assert report.os_version is not None
    assert isinstance(report.os_version, str)
    assert len(report.os_version) > 0


def test_collect_hardware_populates_os_build():
    """os_build is a non-empty string after collect_hardware."""
    from collectors.windows.hardware import collect_hardware

    report = make_report()
    collect_hardware(report)

    assert report.os_build is not None
    assert isinstance(report.os_build, str)
    assert len(report.os_build) > 0


# ---------------------------------------------------------------------------
# _collect_cpu_model — WMI path
# ---------------------------------------------------------------------------

def test_collect_hardware_populates_cpu_model_when_wmi_works():
    """cpu_model is populated from Win32_Processor.Name when WMI succeeds."""
    from collectors.windows.hardware import collect_hardware
    import collectors.windows.hardware as hw_mod

    mock_proc = MagicMock()
    mock_proc.Name = "Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz"

    mock_wmi_instance = MagicMock()
    mock_wmi_instance.Win32_Processor.return_value = [mock_proc]

    mock_wmi_cls = MagicMock(return_value=mock_wmi_instance)

    # Patch the module-level _wmi_module so the function calls our mock
    with patch.object(hw_mod, "_wmi_module", create=True) as mock_mod:
        mock_mod.WMI = mock_wmi_cls
        with patch.object(hw_mod, "_WMI_AVAILABLE", True):
            report = make_report()
            collect_hardware(report)

    assert report.cpu_model == "Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz"


def test_collect_hardware_degrades_when_wmi_raises():
    """WMI error is logged and registry fallback is attempted; if registry also
    fails cpu_model stays None."""
    from collectors.windows.hardware import collect_hardware
    import collectors.windows.hardware as hw_mod

    mock_wmi_cls = MagicMock(side_effect=Exception("COM unavailable"))

    with patch.object(hw_mod, "_wmi_module", create=True) as mock_mod, \
         patch.object(hw_mod, "_WMI_AVAILABLE", True), \
         patch.object(hw_mod.winreg, "OpenKey", side_effect=OSError):
        mock_mod.WMI = mock_wmi_cls
        report = make_report()
        collect_hardware(report)

    assert report.cpu_model is None
    assert len(report.collection_errors) >= 1
    error_text = " ".join(report.collection_errors).lower()
    assert any(kw in error_text for kw in ("cpu", "wmi", "processor"))


def test_collect_hardware_skips_wmi_when_unavailable():
    """When _WMI_AVAILABLE is False, registry fallback is used; if registry also
    fails cpu_model stays None with no crash and no error logged."""
    from collectors.windows.hardware import collect_hardware
    import collectors.windows.hardware as hw_mod

    with patch.object(hw_mod, "_WMI_AVAILABLE", False), \
         patch.object(hw_mod.winreg, "OpenKey", side_effect=OSError):
        report = make_report()
        collect_hardware(report)

    assert report.cpu_model is None
    # No error logged — missing wmi + unreachable registry is silent degradation


# ---------------------------------------------------------------------------
# _collect_memory_and_disk — psutil path
# ---------------------------------------------------------------------------

def test_collect_hardware_populates_ram_gb():
    """ram_gb is a positive float after collect_hardware."""
    from collectors.windows.hardware import collect_hardware

    report = make_report()
    collect_hardware(report)

    assert report.ram_gb is not None
    assert isinstance(report.ram_gb, float)
    assert report.ram_gb > 0


def test_collect_hardware_populates_disk_fields():
    """disk_total_gb and disk_free_gb are positive floats."""
    from collectors.windows.hardware import collect_hardware

    report = make_report()
    collect_hardware(report)

    assert report.disk_total_gb is not None
    assert report.disk_free_gb is not None
    assert report.disk_total_gb > 0
    assert report.disk_free_gb >= 0


def test_collect_hardware_degrades_on_disk_error():
    """disk_total_gb and disk_free_gb stay None and error is logged when disk_usage raises."""
    from collectors.windows.hardware import collect_hardware
    import collectors.windows.hardware as hw_mod

    with patch.object(hw_mod, "psutil") as mock_psutil:
        mock_psutil.virtual_memory.return_value.total = 16 * (1024 ** 3)
        mock_psutil.disk_usage.side_effect = FileNotFoundError("C:\\ not found")

        report = make_report()
        collect_hardware(report)

    assert report.disk_total_gb is None
    assert report.disk_free_gb is None
    assert any("disk" in e.lower() for e in report.collection_errors)


# ---------------------------------------------------------------------------
# _collect_current_user
# ---------------------------------------------------------------------------

def test_collect_hardware_populates_current_user_from_username():
    """current_user is populated from USERNAME env var."""
    from collectors.windows.hardware import collect_hardware

    report = make_report()
    with patch.dict("os.environ", {"USERNAME": "test.user"}, clear=False):
        collect_hardware(report)

    assert report.current_user == "test.user"


def test_collect_hardware_falls_back_to_user_env():
    """current_user falls back to USER env var when USERNAME absent."""
    from collectors.windows.hardware import collect_hardware

    env = {k: v for k, v in __import__("os").environ.items() if k != "USERNAME"}
    env["USER"] = "fallback.user"

    with patch.dict("os.environ", env, clear=True):
        report = make_report()
        collect_hardware(report)

    assert report.current_user == "fallback.user"


def test_collect_hardware_current_user_none_when_both_absent():
    """current_user stays None when neither USERNAME nor USER is set."""
    from collectors.windows.hardware import collect_hardware

    env = {k: v for k, v in __import__("os").environ.items()
           if k not in ("USERNAME", "USER")}

    with patch.dict("os.environ", env, clear=True):
        report = make_report()
        collect_hardware(report)

    assert report.current_user is None


# ---------------------------------------------------------------------------
# No-raise guarantee
# ---------------------------------------------------------------------------

def test_collect_hardware_never_raises():
    """collect_hardware must not propagate any exception under any circumstances."""
    from collectors.windows.hardware import collect_hardware
    import collectors.windows.hardware as hw_mod

    # Make everything fail simultaneously
    with patch.object(hw_mod, "_WMI_AVAILABLE", True), \
         patch.object(hw_mod, "_wmi_module", create=True) as mock_mod, \
         patch.object(hw_mod, "psutil") as mock_psutil:
        mock_mod.WMI = MagicMock(side_effect=RuntimeError("WMI exploded"))
        mock_psutil.virtual_memory.return_value.total = 8 * (1024 ** 3)
        mock_psutil.disk_usage.side_effect = Exception("disk gone")

        try:
            report = make_report()
            collect_hardware(report)
        except Exception as exc:
            pytest.fail(f"collect_hardware raised an exception: {exc}")


# ---------------------------------------------------------------------------
# Phase 13 — Uptime collection tests
# ---------------------------------------------------------------------------

def test_collect_uptime_populates_uptime_seconds():
    """uptime_seconds is a positive integer after collect_hardware() runs."""
    import collectors.windows.hardware as hw_mod
    from collectors.windows.hardware import collect_hardware

    report = make_report()
    collect_hardware(report)
    assert report.uptime_seconds is not None, "uptime_seconds should not be None after collect_hardware"
    assert isinstance(report.uptime_seconds, int)
    assert report.uptime_seconds > 0


def test_collect_uptime_degrades_on_psutil_error():
    """uptime_seconds stays None and error is logged when psutil.boot_time raises."""
    import collectors.windows.hardware as hw_mod
    from collectors.windows.hardware import collect_hardware

    with patch.object(hw_mod, "psutil") as mock_psutil:
        # Preserve psutil behaviour for RAM and disk so collect_hardware completes
        mock_psutil.virtual_memory.return_value.total = 16 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.total = 512 * (1024 ** 3)
        mock_psutil.disk_usage.return_value.free = 100 * (1024 ** 3)
        mock_psutil.boot_time.side_effect = Exception("boot_time unavailable")

        report = make_report()
        collect_hardware(report)

    assert report.uptime_seconds is None
    assert any("uptime" in e.lower() for e in report.collection_errors), (
        f"Expected uptime error in collection_errors; got: {report.collection_errors}"
    )


# ---------------------------------------------------------------------------
# Phase 13 — Pending updates (WUA COM) collection tests
# ---------------------------------------------------------------------------

def test_collect_pending_updates_skipped_when_win32com_unavailable():
    """pending_updates stays None when _WIN32COM_AVAILABLE is False (CI path)."""
    import collectors.windows.hardware as hw_mod
    from collectors.windows.hardware import collect_pending_updates

    with patch.object(hw_mod, "_WIN32COM_AVAILABLE", False):
        report = make_report()
        collect_pending_updates(report)

    assert report.pending_updates is None
    assert report.collection_errors == [], (
        f"No errors expected on guarded skip; got: {report.collection_errors}"
    )


def test_collect_pending_updates_populates_count_when_com_available():
    """pending_updates is set to integer count from WUA COM mock."""
    import collectors.windows.hardware as hw_mod
    from collectors.windows.hardware import collect_pending_updates

    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_searcher = MagicMock()
    mock_result = MagicMock()
    mock_result.Updates.Count = 3
    mock_searcher.Search.return_value = mock_result
    mock_session.CreateUpdateSearcher.return_value = mock_searcher
    mock_client.Dispatch.return_value = mock_session

    with patch.object(hw_mod, "_WIN32COM_AVAILABLE", True), \
         patch.object(hw_mod, "_win32com_client", mock_client):
        report = make_report()
        collect_pending_updates(report)

    assert report.pending_updates == 3
    mock_client.Dispatch.assert_called_once_with("Microsoft.Update.Session")
    mock_searcher.Search.assert_called_once_with("IsInstalled=0 and Type='Software'")


def test_collect_pending_updates_degrades_on_com_error():
    """pending_updates stays None and error is logged when COM raises (standard user)."""
    import collectors.windows.hardware as hw_mod
    from collectors.windows.hardware import collect_pending_updates

    mock_client = MagicMock()
    mock_client.Dispatch.side_effect = Exception("Access denied (standard user)")

    with patch.object(hw_mod, "_WIN32COM_AVAILABLE", True), \
         patch.object(hw_mod, "_win32com_client", mock_client):
        report = make_report()
        collect_pending_updates(report)

    assert report.pending_updates is None
    assert any("pending updates" in e.lower() for e in report.collection_errors), (
        f"Expected pending updates error in collection_errors; got: {report.collection_errors}"
    )
