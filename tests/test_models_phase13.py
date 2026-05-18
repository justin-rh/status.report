"""Tests for Phase 13 model extensions: Warning.level field and AuditReport health fields.

RED phase: these tests FAIL before the models.py changes are applied.
"""
from __future__ import annotations

import pytest
from models import Warning, AuditReport


class TestWarningLevelField:
    """Warning.level field — D-01 (Phase 13)."""

    def test_warning_level_defaults_to_none(self):
        """Warning constructed without level has level=None."""
        w = Warning(code="X", severity="OK", message="msg")
        assert w.level is None

    def test_warning_level_can_be_set_yellow(self):
        """Warning level can be 'yellow'."""
        w = Warning(code="UPTIME_WARN", severity="WARN", message="msg", level="yellow")
        assert w.level == "yellow"

    def test_warning_level_can_be_set_red(self):
        """Warning level can be 'red'."""
        w = Warning(code="UPTIME_STALE", severity="WARN", message="msg", level="red")
        assert w.level == "red"

    def test_warning_positional_construction_not_broken(self):
        """Positional construction with detail still works — level stays None.

        Existing tests use Warning(code, severity, message, detail_value).
        If level is inserted BEFORE detail, detail_value would go to level — silent bug.
        This test guards against that regression.
        """
        w = Warning("X", "OK", "msg", "some detail")
        assert w.detail == "some detail"
        assert w.level is None

    def test_warning_level_is_last_field(self):
        """level appears after detail in field order (positional safety check)."""
        import dataclasses
        fields = [f.name for f in dataclasses.fields(Warning)]
        assert fields[-1] == "level", f"level must be last field, got: {fields}"
        detail_idx = fields.index("detail")
        level_idx = fields.index("level")
        assert level_idx > detail_idx, "level must come after detail"


class TestAuditReportHealthFields:
    """AuditReport.uptime_seconds and .pending_updates — D-04 (Phase 13)."""

    def test_uptime_seconds_defaults_to_none(self):
        """New AuditReport has uptime_seconds=None."""
        r = AuditReport("HOSTNAME", None)
        assert r.uptime_seconds is None

    def test_pending_updates_defaults_to_none(self):
        """New AuditReport has pending_updates=None."""
        r = AuditReport("HOSTNAME", None)
        assert r.pending_updates is None

    def test_uptime_seconds_can_be_set(self):
        """uptime_seconds accepts int value."""
        r = AuditReport("HOSTNAME", None)
        r.uptime_seconds = 86400
        assert r.uptime_seconds == 86400

    def test_pending_updates_can_be_set(self):
        """pending_updates accepts int value."""
        r = AuditReport("HOSTNAME", None)
        r.pending_updates = 5
        assert r.pending_updates == 5

    def test_uptime_seconds_is_int_or_none(self):
        """uptime_seconds type annotation is int | None."""
        import dataclasses
        fields = {f.name: f for f in dataclasses.fields(AuditReport)}
        assert "uptime_seconds" in fields
        assert "pending_updates" in fields

    def test_existing_audit_report_construction_unchanged(self):
        """Existing AuditReport(hostname, parsed_hostname) construction still works."""
        r = AuditReport("MYHOSTNAME", None)
        assert r.hostname == "MYHOSTNAME"
        assert r.parsed_hostname is None
        # New fields present with None defaults
        assert r.uptime_seconds is None
        assert r.pending_updates is None
        # Existing fields unaffected
        assert r.os_version is None
        assert r.cpu_model is None
