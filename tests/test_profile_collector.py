"""Unit tests for collectors.windows.hardware — collect_profiles function.
RED phase: Written against the collect_profiles interface specification.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import winreg

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))


# ---------------------------------------------------------------------------
# Helper: build a mock winreg context that simulates ProfileList subkeys
# ---------------------------------------------------------------------------

def _make_mock_registry(sid_path_map: dict[str, str], fail_open: bool = False):
    """Return a mock suitable for patching winreg.OpenKey.

    sid_path_map: { SID: ProfileImagePath } for non-system SIDs.
    fail_open: if True, raise OSError when opening the ProfileList root key.
    """
    # Build ordered SID list
    all_sids = list(sid_path_map.keys())

    def open_key_side_effect(hive, path, *args, **kwargs):
        if fail_open and path == r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList":
            raise OSError("Access denied")

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)

        if path == r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList":
            # This is the root key — EnumKey iterates SIDs
            call_count = [0]

            def enum_key(key, index):
                if index < len(all_sids):
                    return all_sids[index]
                raise OSError("No more subkeys")

            ctx.__enter__.return_value.__class__ = type(
                "FakeKey",
                (),
                {"EnumKey": staticmethod(enum_key)},
            )
            # Return a key object that supports EnumKey via winreg.EnumKey patch
            return ctx

        # Opening a SID subkey
        sid = path  # path is the SID string in nested OpenKey(key, sid)
        if sid in sid_path_map:
            profile_path = sid_path_map[sid]
            sid_ctx = MagicMock()
            sid_ctx.__enter__ = MagicMock(return_value=sid_ctx)
            sid_ctx.__exit__ = MagicMock(return_value=False)
            return sid_ctx

        raise FileNotFoundError(f"SID not found: {sid}")

    return open_key_side_effect


# ---------------------------------------------------------------------------
# collect_profiles — normal operation
# ---------------------------------------------------------------------------

def test_collect_profiles_populates_local_profiles():
    """local_profiles is a list of username strings after collect_profiles."""
    report = make_report()

    # On a real Windows machine the registry will have real profiles
    from collectors.windows.hardware import collect_profiles
    collect_profiles(report)

    assert isinstance(report.local_profiles, list)


def test_collect_profiles_excludes_system_sids():
    """System SIDs S-1-5-18, S-1-5-19, S-1-5-20 must not appear in local_profiles."""
    from collectors.windows import hardware as hw_mod
    from collectors.windows.hardware import collect_profiles

    system_sids = ["S-1-5-18", "S-1-5-19", "S-1-5-20"]
    user_sids = ["S-1-5-21-111-222-333-1001", "S-1-5-21-111-222-333-1002"]

    # Map all SIDs to profile paths
    sid_paths = {
        "S-1-5-18": r"C:\Windows\system32\config\systemprofile",
        "S-1-5-19": r"C:\Windows\ServiceProfiles\LocalService",
        "S-1-5-20": r"C:\Windows\ServiceProfiles\NetworkService",
        "S-1-5-21-111-222-333-1001": r"C:\Users\john.doe",
        "S-1-5-21-111-222-333-1002": r"C:\Users\jane.smith",
    }
    all_sids = list(sid_paths.keys())

    # Patch at the winreg module level within hardware
    with patch.object(hw_mod.winreg, "OpenKey") as mock_open, \
         patch.object(hw_mod.winreg, "EnumKey") as mock_enum, \
         patch.object(hw_mod.winreg, "QueryValueEx") as mock_query, \
         patch.object(hw_mod.winreg, "ExpandEnvironmentStrings", side_effect=lambda p: p):

        # EnumKey returns each SID by index, then raises OSError
        def enum_key_fn(key, index):
            if index < len(all_sids):
                return all_sids[index]
            raise OSError("exhausted")
        mock_enum.side_effect = enum_key_fn

        # OpenKey returns a context manager for any path
        fake_ctx = MagicMock()
        fake_ctx.__enter__ = MagicMock(return_value=fake_ctx)
        fake_ctx.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = fake_ctx

        # QueryValueEx returns the path for the given sid key
        sid_key_to_sid: dict = {}

        def query_fn(key, value_name):
            # We can't easily correlate the key mock to the SID here,
            # so use a counter approach — queries happen in all_sids order
            # but system SIDs are skipped, so only user SIDs are queried
            return (sid_paths[user_sids[query_fn.call_count]], 1)

        query_fn.call_count = 0
        original_query = query_fn

        def query_side(key, value_name):
            path = sid_paths[user_sids[query_side.i]]
            query_side.i += 1
            return (path, 1)

        query_side.i = 0
        mock_query.side_effect = query_side

        report = make_report()
        collect_profiles(report)

    assert "john.doe" in report.local_profiles
    assert "jane.smith" in report.local_profiles
    # System profile usernames must not appear
    assert "systemprofile" not in report.local_profiles
    assert "LocalService" not in report.local_profiles
    assert "NetworkService" not in report.local_profiles


def test_collect_profiles_extracts_last_path_segment():
    """Username is the last backslash-separated segment of ProfileImagePath."""
    from collectors.windows import hardware as hw_mod
    from collectors.windows.hardware import collect_profiles

    sids = ["S-1-5-21-111-222-333-1001"]
    profile_path = r"C:\Users\alice.wonderland"

    with patch.object(hw_mod.winreg, "OpenKey") as mock_open, \
         patch.object(hw_mod.winreg, "EnumKey") as mock_enum, \
         patch.object(hw_mod.winreg, "QueryValueEx") as mock_query, \
         patch.object(hw_mod.winreg, "ExpandEnvironmentStrings", side_effect=lambda p: p):

        def enum_fn(key, index):
            if index < len(sids):
                return sids[index]
            raise OSError("done")
        mock_enum.side_effect = enum_fn

        fake_ctx = MagicMock()
        fake_ctx.__enter__ = MagicMock(return_value=fake_ctx)
        fake_ctx.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = fake_ctx

        mock_query.return_value = (profile_path, 1)

        report = make_report()
        collect_profiles(report)

    assert report.local_profiles == ["alice.wonderland"]


def test_collect_profiles_expands_environment_strings():
    """ExpandEnvironmentStrings is called on ProfileImagePath before splitting."""
    from collectors.windows import hardware as hw_mod
    from collectors.windows.hardware import collect_profiles

    sids = ["S-1-5-21-111-222-333-1001"]
    raw_path = r"%SystemDrive%\Users\bob.builder"
    expanded_path = r"C:\Users\bob.builder"

    with patch.object(hw_mod.winreg, "OpenKey") as mock_open, \
         patch.object(hw_mod.winreg, "EnumKey") as mock_enum, \
         patch.object(hw_mod.winreg, "QueryValueEx") as mock_query, \
         patch.object(hw_mod.winreg, "ExpandEnvironmentStrings") as mock_expand:

        def enum_fn(key, index):
            if index < len(sids):
                return sids[index]
            raise OSError("done")
        mock_enum.side_effect = enum_fn

        fake_ctx = MagicMock()
        fake_ctx.__enter__ = MagicMock(return_value=fake_ctx)
        fake_ctx.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = fake_ctx

        mock_query.return_value = (raw_path, 1)
        mock_expand.return_value = expanded_path

        report = make_report()
        collect_profiles(report)

    mock_expand.assert_called_once_with(raw_path)
    assert report.local_profiles == ["bob.builder"]


def test_collect_profiles_strips_trailing_backslash():
    """Username extraction handles paths with trailing backslash."""
    from collectors.windows import hardware as hw_mod
    from collectors.windows.hardware import collect_profiles

    sids = ["S-1-5-21-111-222-333-1001"]
    profile_path = r"C:\Users\carol.danvers\ "[:-1]  # ensure no trailing space

    with patch.object(hw_mod.winreg, "OpenKey") as mock_open, \
         patch.object(hw_mod.winreg, "EnumKey") as mock_enum, \
         patch.object(hw_mod.winreg, "QueryValueEx") as mock_query, \
         patch.object(hw_mod.winreg, "ExpandEnvironmentStrings", side_effect=lambda p: p):

        def enum_fn(key, index):
            if index < len(sids):
                return sids[index]
            raise OSError("done")
        mock_enum.side_effect = enum_fn

        fake_ctx = MagicMock()
        fake_ctx.__enter__ = MagicMock(return_value=fake_ctx)
        fake_ctx.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = fake_ctx

        mock_query.return_value = (profile_path, 1)

        report = make_report()
        collect_profiles(report)

    assert "carol.danvers" in report.local_profiles


# ---------------------------------------------------------------------------
# collect_profiles — error paths
# ---------------------------------------------------------------------------

def test_collect_profiles_logs_error_when_profile_list_inaccessible():
    """When ProfileList key cannot be opened, local_profiles stays [] and error logged."""
    from collectors.windows import hardware as hw_mod
    from collectors.windows.hardware import collect_profiles

    with patch.object(hw_mod.winreg, "OpenKey", side_effect=OSError("Access denied")):
        report = make_report()
        collect_profiles(report)

    assert report.local_profiles == []
    assert len(report.collection_errors) >= 1
    assert any("profile" in e.lower() for e in report.collection_errors)


def test_collect_profiles_silently_skips_unreadable_sid():
    """If a single SID subkey cannot be read, it is skipped; no error logged."""
    from collectors.windows import hardware as hw_mod
    from collectors.windows.hardware import collect_profiles

    sids = ["S-1-5-21-111-222-333-1001", "S-1-5-21-111-222-333-1002"]

    call_count_open = [0]

    def open_key_side(hive_or_key, path_or_sid, *args, **kwargs):
        fake_ctx = MagicMock()
        fake_ctx.__enter__ = MagicMock(return_value=fake_ctx)
        fake_ctx.__exit__ = MagicMock(return_value=False)
        return fake_ctx

    def query_side(key, value_name):
        # First SID raises, second returns a valid path
        if query_side.i == 0:
            query_side.i += 1
            raise FileNotFoundError("no ProfileImagePath")
        query_side.i += 1
        return (r"C:\Users\good.user", 1)
    query_side.i = 0

    with patch.object(hw_mod.winreg, "OpenKey", side_effect=open_key_side), \
         patch.object(hw_mod.winreg, "EnumKey") as mock_enum, \
         patch.object(hw_mod.winreg, "QueryValueEx", side_effect=query_side), \
         patch.object(hw_mod.winreg, "ExpandEnvironmentStrings", side_effect=lambda p: p):

        def enum_fn(key, index):
            if index < len(sids):
                return sids[index]
            raise OSError("done")
        mock_enum.side_effect = enum_fn

        report = make_report()
        collect_profiles(report)

    # good.user is included, no error logged for the skipped SID
    assert "good.user" in report.local_profiles
    assert len(report.collection_errors) == 0


def test_collect_profiles_never_raises():
    """collect_profiles must not propagate any exception."""
    from collectors.windows import hardware as hw_mod
    from collectors.windows.hardware import collect_profiles

    with patch.object(hw_mod.winreg, "OpenKey", side_effect=PermissionError("denied")):
        try:
            report = make_report()
            collect_profiles(report)
        except Exception as exc:
            pytest.fail(f"collect_profiles raised: {exc}")

    assert report.local_profiles == []
