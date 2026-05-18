"""Unit tests for renderer._build_context() — vendor display values.
Phase 14: VendorUpdateStatus display string computation for dell_dcu_display
and lenovo_lsu_display context keys.
"""
from __future__ import annotations

import pytest
from models import AuditReport, VendorUpdateStatus
from parsers.name_parser import parse_hostname
from renderer import _build_context


def _make_report(**kwargs) -> AuditReport:
    """Minimal AuditReport for renderer tests."""
    return AuditReport(
        hostname="TEST-PC",
        parsed_hostname=parse_hostname("TEST-PC"),
        **kwargs,
    )


class TestVendorDisplayValues:
    """_build_context() vendor display values (D-07, D-08)."""

    # --- dell_dcu_display ---

    def test_dell_dcu_none_when_updates_not_passed(self):
        report = _make_report()  # dell_dcu=None by default
        ctx = _build_context(report)
        assert ctx["dell_dcu_display"] is None

    def test_dell_dcu_not_installed(self):
        report = _make_report(
            dell_dcu=VendorUpdateStatus(installed=False, pending_count=None, scan_data_present=False)
        )
        ctx = _build_context(report)
        assert ctx["dell_dcu_display"] == "Not installed"

    def test_dell_dcu_error_state_shows_not_installed(self):
        # installed=None means collection error — display as "Not installed" (safe fallback)
        report = _make_report(
            dell_dcu=VendorUpdateStatus(installed=None, pending_count=None, scan_data_present=False)
        )
        ctx = _build_context(report)
        assert ctx["dell_dcu_display"] == "Not installed"

    def test_dell_dcu_installed_xml_absent(self):
        report = _make_report(
            dell_dcu=VendorUpdateStatus(installed=True, pending_count=None, scan_data_present=False)
        )
        ctx = _build_context(report)
        assert ctx["dell_dcu_display"] == "Unknown (no scan data)"

    def test_dell_dcu_installed_xml_present_pending_count(self):
        report = _make_report(
            dell_dcu=VendorUpdateStatus(installed=True, pending_count=3, scan_data_present=True)
        )
        ctx = _build_context(report)
        assert ctx["dell_dcu_display"] == "3 pending"

    def test_dell_dcu_installed_xml_present_zero_updates(self):
        report = _make_report(
            dell_dcu=VendorUpdateStatus(installed=True, pending_count=0, scan_data_present=True)
        )
        ctx = _build_context(report)
        assert ctx["dell_dcu_display"] == "0 pending"

    def test_dell_dcu_installed_xml_parse_error_scan_data_true(self):
        # scan_data_present=True but pending_count=None (parse error) → unknown
        report = _make_report(
            dell_dcu=VendorUpdateStatus(installed=True, pending_count=None, scan_data_present=True)
        )
        ctx = _build_context(report)
        assert ctx["dell_dcu_display"] == "Unknown (no scan data)"

    # --- lenovo_lsu_display ---

    def test_lenovo_lsu_none_when_updates_not_passed(self):
        report = _make_report()  # lenovo_lsu=None by default
        ctx = _build_context(report)
        assert ctx["lenovo_lsu_display"] is None

    def test_lenovo_lsu_not_installed(self):
        report = _make_report(
            lenovo_lsu=VendorUpdateStatus(installed=False, pending_count=None, scan_data_present=False)
        )
        ctx = _build_context(report)
        assert ctx["lenovo_lsu_display"] == "Not installed"

    def test_lenovo_lsu_installed_shows_na(self):
        report = _make_report(
            lenovo_lsu=VendorUpdateStatus(installed=True, pending_count=None, scan_data_present=False)
        )
        ctx = _build_context(report)
        assert ctx["lenovo_lsu_display"] == "N/A"
