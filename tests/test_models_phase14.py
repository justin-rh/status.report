"""Tests for Phase 14 model additions: VendorUpdateStatus dataclass and AuditReport fields.
RED phase tests — written before implementation.
"""
from __future__ import annotations

import pytest
from models import VendorUpdateStatus, AuditReport
from parsers.name_parser import parse_hostname


class TestVendorUpdateStatus:
    """VendorUpdateStatus dataclass (Phase 14, D-02)."""

    def test_installed_true_variant(self):
        v = VendorUpdateStatus(installed=True, pending_count=2, scan_data_present=True)
        assert v.installed is True
        assert v.pending_count == 2
        assert v.scan_data_present is True

    def test_not_installed_variant(self):
        v = VendorUpdateStatus(installed=False, pending_count=None, scan_data_present=False)
        assert v.installed is False
        assert v.pending_count is None
        assert v.scan_data_present is False

    def test_collection_error_variant(self):
        v = VendorUpdateStatus(installed=None, pending_count=None, scan_data_present=False)
        assert v.installed is None
        assert v.pending_count is None
        assert v.scan_data_present is False


class TestAuditReportVendorFields:
    """AuditReport.dell_dcu and .lenovo_lsu fields (Phase 14, D-02)."""

    def test_audit_report_has_dell_dcu_default_none(self):
        r = AuditReport(hostname="TEST", parsed_hostname=None)
        assert r.dell_dcu is None

    def test_audit_report_has_lenovo_lsu_default_none(self):
        r = AuditReport(hostname="TEST", parsed_hostname=None)
        assert r.lenovo_lsu is None

    def test_dell_dcu_can_be_set(self):
        r = AuditReport(hostname="TEST", parsed_hostname=None)
        r.dell_dcu = VendorUpdateStatus(installed=True, pending_count=3, scan_data_present=True)
        assert r.dell_dcu.installed is True
        assert r.dell_dcu.pending_count == 3

    def test_lenovo_lsu_can_be_set(self):
        r = AuditReport(hostname="TEST", parsed_hostname=None)
        r.lenovo_lsu = VendorUpdateStatus(installed=True, pending_count=None, scan_data_present=False)
        assert r.lenovo_lsu.installed is True
        assert r.lenovo_lsu.pending_count is None

    def test_dell_dcu_and_lenovo_lsu_field_order(self):
        """dell_dcu and lenovo_lsu must appear after pending_updates in field order."""
        import dataclasses
        fields = [f.name for f in dataclasses.fields(AuditReport)]
        pending_idx = fields.index("pending_updates")
        dell_idx = fields.index("dell_dcu")
        lenovo_idx = fields.index("lenovo_lsu")
        local_profiles_idx = fields.index("local_profiles")
        assert pending_idx < dell_idx < lenovo_idx < local_profiles_idx
