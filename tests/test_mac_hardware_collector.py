"""Unit tests for collectors.mac.hardware — collect_hardware and collect_profiles.
All Mac-specific calls are patched at the module level; no real Mac subprocess calls occur.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname

import collectors.mac.hardware as hw_mod


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-MAC", parsed_hostname=parse_hostname("TEST-MAC"))


# ---------------------------------------------------------------------------
# Test 9: Import guard — file must import on Windows CI (pwd unavailable)
# ---------------------------------------------------------------------------

def test_module_imports_without_real_pwd():
    """collectors.mac.hardware must import even if pwd is unavailable (CI guard)."""
    from collectors.mac import hardware  # noqa: F401


# ---------------------------------------------------------------------------
# Test 4: OS version and build from sw_vers
# ---------------------------------------------------------------------------

def test_collect_hardware_populates_os_version_and_build():
    """collect_hardware() populates os_version = 'macOS 14.4.1' and os_build = '23E224'."""
    def fake_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        if "-productVersion" in cmd:
            mock.stdout = "14.4.1\n"
        elif "-buildVersion" in cmd:
            mock.stdout = "23E224\n"
        else:
            mock.stdout = ""
        return mock

    with patch.object(hw_mod, "subprocess") as mock_sub, \
         patch.object(hw_mod, "psutil") as mock_psutil, \
         patch.object(hw_mod, "platform") as mock_platform:
        mock_sub.run.side_effect = fake_run
        mock_sub.TimeoutExpired = __import__("subprocess").TimeoutExpired
        mock_psutil.virtual_memory.return_value.total = 16 * (1024 ** 3)
        mock_psutil.disk_usage.return_value = MagicMock(
            total=500 * (1024 ** 3), free=100 * (1024 ** 3)
        )
        mock_platform.machine.return_value = "x86_64"
        mock_sub.run.side_effect = fake_run

        report = make_report()
        hw_mod.collect_hardware(report)

    assert report.os_version == "macOS 14.4.1"
    assert report.os_build == "23E224"


# ---------------------------------------------------------------------------
# Test 1: Intel Mac CPU model via sysctl
# ---------------------------------------------------------------------------

INTEL_SYSCTL_OUTPUT = "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz\n"
APPLE_SILICON_SP_JSON = json.dumps({
    "SPHardwareDataType": [{"chip_type": "Apple M3 Pro", "_name": "hardware_overview"}]
})


@pytest.mark.parametrize("machine,sysctl_out,sp_json,expected_cpu", [
    ("x86_64", INTEL_SYSCTL_OUTPUT, "", "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz"),
    ("arm64", "", APPLE_SILICON_SP_JSON, "Apple M3 Pro"),
])
def test_cpu_model_collection(machine, sysctl_out, sp_json, expected_cpu):
    """collect_hardware() sets cpu_model correctly for Intel and Apple Silicon."""
    def fake_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        if "machdep.cpu.brand_string" in cmd:
            mock.stdout = sysctl_out
        elif "system_profiler" in cmd:
            mock.stdout = sp_json
        elif "-productVersion" in cmd:
            mock.stdout = "14.4.1\n"
        elif "-buildVersion" in cmd:
            mock.stdout = "23E224\n"
        else:
            mock.stdout = ""
        return mock

    with patch.object(hw_mod, "subprocess") as mock_sub, \
         patch.object(hw_mod, "psutil") as mock_psutil, \
         patch.object(hw_mod, "platform") as mock_platform:
        mock_sub.run.side_effect = fake_run
        mock_sub.TimeoutExpired = __import__("subprocess").TimeoutExpired
        mock_psutil.virtual_memory.return_value.total = 16 * (1024 ** 3)
        mock_psutil.disk_usage.return_value = MagicMock(
            total=500 * (1024 ** 3), free=100 * (1024 ** 3)
        )
        mock_platform.machine.return_value = machine

        report = make_report()
        hw_mod.collect_hardware(report)

    assert report.cpu_model == expected_cpu


# ---------------------------------------------------------------------------
# Test 3: All subprocess calls failing — cpu_model = None, errors logged
# ---------------------------------------------------------------------------

def test_collect_hardware_all_subprocess_fails():
    """collect_hardware() with all subprocess calls failing sets cpu_model=None and logs errors."""
    with patch.object(hw_mod, "subprocess") as mock_sub, \
         patch.object(hw_mod, "psutil") as mock_psutil, \
         patch.object(hw_mod, "platform") as mock_platform:
        mock_sub.run.side_effect = OSError("subprocess not available")
        mock_sub.TimeoutExpired = __import__("subprocess").TimeoutExpired
        mock_psutil.virtual_memory.return_value.total = 16 * (1024 ** 3)
        mock_psutil.disk_usage.return_value = MagicMock(
            total=500 * (1024 ** 3), free=100 * (1024 ** 3)
        )
        mock_platform.machine.return_value = "x86_64"

        report = make_report()
        hw_mod.collect_hardware(report)

    assert report.cpu_model is None
    assert len(report.collection_errors) >= 1


# ---------------------------------------------------------------------------
# Test 5: collect_hardware never raises even when subprocess + psutil both throw
# ---------------------------------------------------------------------------

def test_collect_hardware_never_raises():
    """collect_hardware must not propagate any exception under any circumstances."""
    with patch.object(hw_mod, "subprocess") as mock_sub, \
         patch.object(hw_mod, "psutil") as mock_psutil, \
         patch.object(hw_mod, "platform") as mock_platform:
        mock_sub.run.side_effect = RuntimeError("subprocess exploded")
        mock_sub.TimeoutExpired = __import__("subprocess").TimeoutExpired
        mock_psutil.virtual_memory.return_value.total = 8 * (1024 ** 3)
        mock_psutil.disk_usage.side_effect = Exception("disk gone")
        mock_platform.machine.return_value = "arm64"
        try:
            report = make_report()
            hw_mod.collect_hardware(report)
        except Exception as exc:
            pytest.fail(f"collect_hardware raised an exception: {exc}")


# ---------------------------------------------------------------------------
# Test 6: collect_profiles with 4 entries — only UID >= 501 returned
# ---------------------------------------------------------------------------

def test_collect_profiles_excludes_system_accounts():
    """Accounts with UID < 501 are excluded (macOS system account threshold)."""
    fake_entries = [
        MagicMock(pw_name="alice", pw_uid=501),
        MagicMock(pw_name="bob", pw_uid=502),
        MagicMock(pw_name="_daemon", pw_uid=1),
        MagicMock(pw_name="root", pw_uid=0),
    ]
    with patch.object(hw_mod, "_pwd_module") as mock_pwd, \
         patch.object(hw_mod, "_PWD_AVAILABLE", True):
        mock_pwd.getpwall.return_value = fake_entries
        report = make_report()
        hw_mod.collect_profiles(report)

    assert report.local_profiles == ["alice", "bob"]


# ---------------------------------------------------------------------------
# Test 7: collect_profiles never raises — error goes to collection_errors
# ---------------------------------------------------------------------------

def test_collect_profiles_never_raises():
    """collect_profiles must not propagate any exception."""
    with patch.object(hw_mod, "_pwd_module") as mock_pwd, \
         patch.object(hw_mod, "_PWD_AVAILABLE", True):
        mock_pwd.getpwall.side_effect = RuntimeError("Open Directory failure")
        try:
            report = make_report()
            hw_mod.collect_profiles(report)
        except Exception as exc:
            pytest.fail(f"collect_profiles raised: {exc}")
    assert report.local_profiles == []
    assert len(report.collection_errors) >= 1


# ---------------------------------------------------------------------------
# Test 8: collect_profiles when _PWD_AVAILABLE=False — empty list + error logged
# ---------------------------------------------------------------------------

def test_collect_profiles_degrades_when_pwd_unavailable():
    """When _PWD_AVAILABLE is False (Windows CI), local_profiles=[] and error is logged."""
    with patch.object(hw_mod, "_PWD_AVAILABLE", False):
        report = make_report()
        hw_mod.collect_profiles(report)
    assert report.local_profiles == []
    assert len(report.collection_errors) >= 1
