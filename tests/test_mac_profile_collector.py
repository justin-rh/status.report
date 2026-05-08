"""Unit tests for collectors.mac.hardware — collect_profiles function.
pwd.getpwall() is patched at module level so no real POSIX calls occur.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname
import collectors.mac.hardware as hw_mod


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-MAC", parsed_hostname=parse_hostname("TEST-MAC"))


# ---------------------------------------------------------------------------
# Test 1: Human accounts (UID >= 501) are returned in local_profiles
# ---------------------------------------------------------------------------

def test_collect_profiles_returns_human_accounts():
    """UID 501 and 502 are included; UID 0 (root) and 1 (_daemon) are excluded."""
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

    assert "alice" in report.local_profiles
    assert "bob" in report.local_profiles
    assert "_daemon" not in report.local_profiles
    assert "root" not in report.local_profiles


# ---------------------------------------------------------------------------
# Test 2: UID threshold — only accounts with UID >= 501 included
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
    assert len(report.local_profiles) == 2


# ---------------------------------------------------------------------------
# Test 3: collect_profiles never raises — error logged in collection_errors
# ---------------------------------------------------------------------------

def test_collect_profiles_never_raises():
    """collect_profiles must not propagate any exception from getpwall()."""
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
# Test 4: pwd unavailable (Windows CI) — empty list + error logged
# ---------------------------------------------------------------------------

def test_collect_profiles_degrades_when_pwd_unavailable():
    """When _PWD_AVAILABLE is False (Windows CI), local_profiles=[] and error is logged."""
    with patch.object(hw_mod, "_PWD_AVAILABLE", False):
        report = make_report()
        hw_mod.collect_profiles(report)
    assert report.local_profiles == []
    assert len(report.collection_errors) >= 1


# ---------------------------------------------------------------------------
# Test 5: No human accounts present — local_profiles is empty list
# ---------------------------------------------------------------------------

def test_collect_profiles_empty_when_no_human_accounts():
    """When all entries have UID < 501, local_profiles returns empty list."""
    fake_entries = [
        MagicMock(pw_name="root", pw_uid=0),
        MagicMock(pw_name="_daemon", pw_uid=1),
        MagicMock(pw_name="_nobody", pw_uid=99),
        MagicMock(pw_name="_www", pw_uid=70),
    ]
    with patch.object(hw_mod, "_pwd_module") as mock_pwd, \
         patch.object(hw_mod, "_PWD_AVAILABLE", True):
        mock_pwd.getpwall.return_value = fake_entries
        report = make_report()
        hw_mod.collect_profiles(report)

    assert report.local_profiles == []
    assert len(report.collection_errors) == 0
