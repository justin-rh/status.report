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
