"""Unit tests for renderer helpers — _build_context and _load_template_source.
RED phase: Tests written against the public interface before implementation.
Task 1 TDD gate tests — these are superseded by test_renderer.py in Task 3.
"""
from __future__ import annotations

import pytest

from models import AuditReport, ParsedHostname, AppStatus
from parsers.name_parser import parse_hostname


def make_report(**kwargs) -> AuditReport:
    """Return a minimal AuditReport for unit testing. Override fields with kwargs."""
    defaults = dict(
        hostname='TEST-PC',
        parsed_hostname=parse_hostname('TEST-PC'),
    )
    defaults.update(kwargs)
    return AuditReport(**defaults)


# ---------------------------------------------------------------------------
# _load_template_source — importlib.resources path
# ---------------------------------------------------------------------------

def test_load_template_source_returns_string():
    """_load_template_source returns a non-empty string."""
    from renderer import _load_template_source
    result = _load_template_source()
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# _build_context — None field handling (D-12, D-13)
# ---------------------------------------------------------------------------

def test_build_context_all_none_hardware():
    """All None hardware fields produce hp-none, 100.0 pct, None display values."""
    from renderer import _build_context
    report = make_report()
    ctx = _build_context(report)
    assert ctx['hp_class'] == 'hp-none'
    assert ctx['disk_pct'] == 100.0
    assert ctx['ram_display'] is None
    assert ctx['disk_total_display'] is None
    assert ctx['disk_label'] is None
    assert ctx['os_combined'] is None


def test_build_context_disk_zero_produces_hp_none():
    """disk_total_gb=0.0 produces hp_class='hp-none' (Pitfall 3 guard)."""
    from renderer import _build_context
    report = make_report(disk_total_gb=0.0)
    ctx = _build_context(report)
    assert ctx['hp_class'] == 'hp-none'
    assert ctx['disk_pct'] == 100.0


def test_build_context_hp_green():
    """disk_total_gb=100.0, disk_free_gb=60.0 -> hp_class='hp-green' (60% free)."""
    from renderer import _build_context
    report = make_report(disk_total_gb=100.0, disk_free_gb=60.0)
    ctx = _build_context(report)
    assert ctx['hp_class'] == 'hp-green'


def test_build_context_hp_amber():
    """disk_total_gb=100.0, disk_free_gb=35.0 -> hp_class='hp-amber' (35% free)."""
    from renderer import _build_context
    report = make_report(disk_total_gb=100.0, disk_free_gb=35.0)
    ctx = _build_context(report)
    assert ctx['hp_class'] == 'hp-amber'


def test_build_context_hp_red():
    """disk_total_gb=476.0, disk_free_gb=38.0 -> hp_class='hp-red' (~8% free)."""
    from renderer import _build_context
    report = make_report(disk_total_gb=476.0, disk_free_gb=38.0)
    ctx = _build_context(report)
    assert ctx['hp_class'] == 'hp-red'


def test_build_context_guild_warehouse():
    """Guild shows department for warehouse device."""
    from renderer import _build_context
    ph = ParsedHostname(raw_hostname='PHX-INV-003', department='INV', company_code=None)
    report = make_report(parsed_hostname=ph)
    ctx = _build_context(report)
    assert ctx['guild'] == 'Inventory'


def test_build_context_guild_laptop():
    """Guild shows company_code for user-assigned laptop."""
    from renderer import _build_context
    ph = ParsedHostname(raw_hostname='PHX-ME12345-ME', department=None, company_code='ME')
    report = make_report(parsed_hostname=ph)
    ctx = _build_context(report)
    assert ctx['guild'] == 'ME'


def test_build_context_guild_none_when_both_none():
    """Guild is None when both department and company_code are None."""
    from renderer import _build_context
    ph = ParsedHostname(raw_hostname='TEST-PC', department=None, company_code=None)
    report = make_report(parsed_hostname=ph)
    ctx = _build_context(report)
    assert ctx['guild'] is None
