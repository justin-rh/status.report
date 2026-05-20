"""Unit tests for collectors.windows.vendor — collect_vendor_updates function.

Mock pattern: patch.object(apps_mod.winreg, ...) patches the winreg reference
inside apps.py (where _search_uninstall_keys lives), not the stdlib module globally.
XML path: patch.object(vendor_mod, 'DCU_XML_PATH', str(tmp_path_file)) to avoid
reading real filesystem in CI.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname
import collectors.windows.vendor as vendor_mod
import collectors.windows.apps as apps_mod


def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))


# --- registry mock helpers (copied from test_app_collector.py) ---

def _make_fake_ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx

def _make_enum_fn(subkeys: list[str]):
    def enum_fn(key, index):
        if index < len(subkeys):
            return subkeys[index]
        raise OSError("exhausted")
    return enum_fn

def _make_query_fn(display_name: str, display_version: str | None = None):
    def query_fn(key, value_name):
        if value_name == "DisplayName":
            return (display_name, 1)
        if value_name == "DisplayVersion" and display_version is not None:
            return (display_version, 1)
        raise FileNotFoundError(f"no value {value_name!r}")
    return query_fn


class TestCollectVendorUpdates:
    """collect_vendor_updates() in collectors/windows/vendor.py."""

    def test_collect_vendor_updates_is_exported(self):
        assert hasattr(vendor_mod, "collect_vendor_updates")
        assert callable(vendor_mod.collect_vendor_updates)

    def test_dcu_not_installed_when_registry_miss(self):
        with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no key")):
            report = make_report()
            vendor_mod.collect_vendor_updates(report)
        assert report.dell_dcu is not None
        assert report.dell_dcu.installed is False
        assert report.dell_dcu.pending_count is None
        assert report.dell_dcu.scan_data_present is False

    def test_dcu_installed_xml_absent(self):
        fake_ctx = _make_fake_ctx()
        with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
             patch.object(apps_mod.winreg, "EnumKey",
                          side_effect=_make_enum_fn(["DCU key"])), \
             patch.object(apps_mod.winreg, "QueryValueEx",
                          side_effect=_make_query_fn("Dell Command | Update", "5.5.0")), \
             patch.object(vendor_mod, "DCU_XML_PATH", "/nonexistent/path/DCUApplicableUpdates.xml"):
            report = make_report()
            vendor_mod.collect_vendor_updates(report)
        assert report.dell_dcu.installed is True
        assert report.dell_dcu.pending_count is None
        assert report.dell_dcu.scan_data_present is False

    def test_dcu_installed_xml_present_two_updates(self, tmp_path):
        xml_content = """<updates>
  <update><name>Driver A</name><urgency>Recommended</urgency></update>
  <update><name>BIOS 1.5</name><urgency>Urgent</urgency></update>
</updates>"""
        xml_file = tmp_path / "DCUApplicableUpdates.xml"
        xml_file.write_text(xml_content)
        fake_ctx = _make_fake_ctx()
        with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
             patch.object(apps_mod.winreg, "EnumKey",
                          side_effect=_make_enum_fn(["DCU key"])), \
             patch.object(apps_mod.winreg, "QueryValueEx",
                          side_effect=_make_query_fn("Dell Command | Update", "5.5.0")), \
             patch.object(vendor_mod, "DCU_XML_PATH", str(xml_file)):
            report = make_report()
            vendor_mod.collect_vendor_updates(report)
        assert report.dell_dcu.installed is True
        assert report.dell_dcu.pending_count == 2
        assert report.dell_dcu.scan_data_present is True

    def test_dcu_installed_xml_present_zero_updates(self, tmp_path):
        xml_file = tmp_path / "DCUApplicableUpdates.xml"
        xml_file.write_text("<updates/>")
        fake_ctx = _make_fake_ctx()
        with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
             patch.object(apps_mod.winreg, "EnumKey",
                          side_effect=_make_enum_fn(["DCU key"])), \
             patch.object(apps_mod.winreg, "QueryValueEx",
                          side_effect=_make_query_fn("Dell Command Update", "5.4.0")), \
             patch.object(vendor_mod, "DCU_XML_PATH", str(xml_file)):
            report = make_report()
            vendor_mod.collect_vendor_updates(report)
        assert report.dell_dcu.pending_count == 0
        assert report.dell_dcu.scan_data_present is True

    def test_dcu_xml_parse_error_sets_pending_count_none_scan_data_true(self, tmp_path):
        xml_file = tmp_path / "DCUApplicableUpdates.xml"
        xml_file.write_text("<<not valid xml>>")
        fake_ctx = _make_fake_ctx()
        with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
             patch.object(apps_mod.winreg, "EnumKey",
                          side_effect=_make_enum_fn(["DCU key"])), \
             patch.object(apps_mod.winreg, "QueryValueEx",
                          side_effect=_make_query_fn("Dell Command | Update", "5.5.0")), \
             patch.object(vendor_mod, "DCU_XML_PATH", str(xml_file)):
            report = make_report()
            vendor_mod.collect_vendor_updates(report)
        assert report.dell_dcu.pending_count is None
        assert report.dell_dcu.scan_data_present is True

    def test_lsu_not_installed_when_registry_miss(self):
        with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no key")):
            report = make_report()
            vendor_mod.collect_vendor_updates(report)
        assert report.lenovo_lsu is not None
        assert report.lenovo_lsu.installed is False
        assert report.lenovo_lsu.pending_count is None
        assert report.lenovo_lsu.scan_data_present is False

    def test_lsu_installed_pending_count_always_none(self):
        fake_ctx = _make_fake_ctx()
        with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
             patch.object(apps_mod.winreg, "EnumKey",
                          side_effect=_make_enum_fn(["TVSU_is1"])), \
             patch.object(apps_mod.winreg, "QueryValueEx",
                          side_effect=_make_query_fn("Lenovo System Update", "5.8.0")):
            report = make_report()
            vendor_mod.collect_vendor_updates(report)
        assert report.lenovo_lsu.installed is True
        assert report.lenovo_lsu.pending_count is None
        assert report.lenovo_lsu.scan_data_present is False

    def test_never_raises_on_exception(self):
        with patch.object(apps_mod.winreg, "OpenKey", side_effect=RuntimeError("total failure")):
            report = make_report()
            try:
                vendor_mod.collect_vendor_updates(report)
            except Exception as exc:
                pytest.fail(f"collect_vendor_updates raised: {exc}")

    def test_appends_to_collection_errors_on_exception(self):
        with patch.object(apps_mod.winreg, "OpenKey", side_effect=RuntimeError("catastrophic")):
            report = make_report()
            vendor_mod.collect_vendor_updates(report)
        # At minimum the DCU error should be appended
        assert any("DCU" in e for e in report.collection_errors)


class TestDiagVendorPaths:
    """diag_vendor_paths() in collectors/windows/vendor.py."""

    def test_hive_labels_printed_for_all_4_hives(self):
        """Test 1: output contains all 4 hive labels even when hives fail to open."""
        import io
        buf = io.StringIO()
        with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no key")):
            vendor_mod.diag_vendor_paths(stream=buf)
        out = buf.getvalue()
        assert "HKLM" in out
        assert r"HKLM\Wow6432Node" in out
        assert "HKCU" in out
        assert r"HKCU\Wow6432Node" in out

    def test_dell_match_shows_displayname_version_and_hive(self, tmp_path):
        """Test 2: Dell entry output contains DisplayName, DisplayVersion, hive label, 'DisplayName' field name."""
        import io
        buf = io.StringIO()
        fake_ctx = _make_fake_ctx()

        current_subkey = {"name": None}

        def open_key_side_effect(key, subkey_name):
            current_subkey["name"] = subkey_name
            return _make_fake_ctx()

        def query_dell(key, value_name):
            if value_name == "DisplayName":
                return ("Dell Command | Update", 1)
            if value_name == "DisplayVersion":
                return ("5.5.0", 1)
            raise FileNotFoundError(f"no value {value_name!r}")

        with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
             patch.object(apps_mod.winreg, "EnumKey", side_effect=_make_enum_fn(["DCU subkey"])), \
             patch.object(apps_mod.winreg, "QueryValueEx", side_effect=query_dell), \
             patch.object(vendor_mod, "DCU_XML_PATH", str(tmp_path / "nonexistent.xml")):
            vendor_mod.diag_vendor_paths(stream=buf)
        out = buf.getvalue()
        assert "Dell Command | Update" in out
        assert "5.5.0" in out
        assert "DisplayName" in out
        # At least one hive label present
        assert any(label in out for label in ["HKLM", "HKCU"])

    def test_discovery_property_unknown_lenovo_entry(self, tmp_path):
        """Test 3 (D-12): unknown Lenovo* DisplayName appears, unrelated entries do not.

        Note: diag_vendor_paths uses vendor_mod.winreg directly (its own import),
        so we patch vendor_mod.winreg for the OpenKey/EnumKey/QueryValueEx used
        in the diagnostic function, while apps_mod.winreg is patched for the
        UNINSTALL_PATHS iteration (which vendor_mod iterates using winreg.OpenKey).
        """
        import io
        import winreg as _winreg
        buf = io.StringIO()

        subkey_displaynames = {
            "Lenovo subkey": "Lenovo Hotkey Driver",
            "Edge subkey": "Microsoft Edge",
        }
        current_subkey = {"name": None}

        def open_key_side_effect(hive_or_key, subkey_name_or_path=None, *args, **kwargs):
            # When called with 2 args: (root_key_handle, subkey_name) — track subkey name
            if subkey_name_or_path is not None:
                current_subkey["name"] = subkey_name_or_path
            return _make_fake_ctx()

        def query_per_subkey(key, value_name):
            if value_name == "DisplayName":
                name = current_subkey["name"]
                if name in subkey_displaynames:
                    return (subkey_displaynames[name], 1)
                raise FileNotFoundError(f"no displayname for {name!r}")
            raise FileNotFoundError(f"no value {value_name!r}")

        with patch.object(vendor_mod.winreg, "OpenKey", side_effect=open_key_side_effect), \
             patch.object(vendor_mod.winreg, "EnumKey",
                          side_effect=_make_enum_fn(["Lenovo subkey", "Edge subkey"])), \
             patch.object(vendor_mod.winreg, "QueryValueEx", side_effect=query_per_subkey), \
             patch.object(vendor_mod, "DCU_XML_PATH", str(tmp_path / "nonexistent.xml")):
            vendor_mod.diag_vendor_paths(stream=buf)
        out = buf.getvalue()
        assert "Lenovo Hotkey Driver" in out
        assert "Microsoft Edge" not in out

    def test_no_match_prints_no_matching_entries(self, tmp_path):
        """Test 4: when no Dell or Lenovo entries exist, prints a 'no matching entries' note."""
        import io
        buf = io.StringIO()
        fake_ctx = _make_fake_ctx()

        def query_notepad(key, value_name):
            if value_name == "DisplayName":
                return ("Notepad++", 1)
            raise FileNotFoundError(f"no value {value_name!r}")

        with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
             patch.object(apps_mod.winreg, "EnumKey",
                          side_effect=_make_enum_fn(["Notepad++ subkey"])), \
             patch.object(apps_mod.winreg, "QueryValueEx", side_effect=query_notepad), \
             patch.object(vendor_mod, "DCU_XML_PATH", str(tmp_path / "nonexistent.xml")):
            vendor_mod.diag_vendor_paths(stream=buf)
        out = buf.getvalue()
        assert "no matching entries" in out
        assert "Notepad++" not in out

    def test_dcu_xml_present_two_updates(self, tmp_path):
        """Test 5: DCU XML section shows exists=True, size, update count: 2."""
        import io
        buf = io.StringIO()
        xml_content = """<updates>
  <update><name>Driver A</name></update>
  <update><name>BIOS 1.5</name></update>
</updates>"""
        xml_file = tmp_path / "DCUApplicableUpdates.xml"
        xml_file.write_text(xml_content)

        with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no key")), \
             patch.object(vendor_mod, "DCU_XML_PATH", str(xml_file)):
            vendor_mod.diag_vendor_paths(stream=buf)
        out = buf.getvalue()
        assert "exists=True" in out
        assert "size=" in out
        assert "update count: 2" in out

    def test_dcu_xml_missing_shows_exists_false_no_size_no_count(self, tmp_path):
        """Test 6: DCU XML absent: exists=False, no size, no update count."""
        import io
        buf = io.StringIO()

        with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no key")), \
             patch.object(vendor_mod, "DCU_XML_PATH", str(tmp_path / "nonexistent.xml")):
            vendor_mod.diag_vendor_paths(stream=buf)
        out = buf.getvalue()
        assert "exists=False" in out
        assert "size=" not in out
        assert "update count" not in out

    def test_dcu_xml_malformed_shows_unparseable(self, tmp_path):
        """Test 7: malformed XML shows exists=True and unparseable note, does not raise."""
        import io
        buf = io.StringIO()
        xml_file = tmp_path / "bad.xml"
        xml_file.write_text("<<bad>>")

        with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no key")), \
             patch.object(vendor_mod, "DCU_XML_PATH", str(xml_file)):
            vendor_mod.diag_vendor_paths(stream=buf)
        out = buf.getvalue()
        assert "exists=True" in out
        assert "unparseable" in out

    def test_never_raises_on_registry_runtime_error(self):
        """Test 8: RuntimeError from OpenKey does not propagate; output notes skipped."""
        import io
        buf = io.StringIO()
        with patch.object(apps_mod.winreg, "OpenKey", side_effect=RuntimeError("total failure")):
            try:
                vendor_mod.diag_vendor_paths(stream=buf)
            except Exception as exc:
                pytest.fail(f"diag_vendor_paths raised: {exc}")
        out = buf.getvalue()
        assert "skipped" in out

    def test_lsu_keyword_list_has_phase17_comment_block(self):
        """Test 9: vendor.py LSU keyword list is preceded by a comment block with 7 required substrings."""
        import os
        vendor_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "collectors", "windows", "vendor.py",
        )
        with open(vendor_path, encoding="utf-8") as f:
            source = f.read()
        required_substrings = [
            "Edgar-confirmed",
            "defensive",
            "17-IT-CONFIRMATION.md",
            "Lenovo Vantage",
            "Lenovo Commercial Vantage",
            "Lenovo System Update",
            "Lenovo Vantage Service",
        ]
        for substr in required_substrings:
            assert substr in source, (
                f"vendor.py LSU comment block missing required substring: {substr!r}"
            )
