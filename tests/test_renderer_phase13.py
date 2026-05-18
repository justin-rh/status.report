"""Unit tests for Phase 13 renderer additions — uptime/pending_updates display.
TDD RED phase: These tests are written before the implementation.
"""
from __future__ import annotations

import pytest

from models import AuditReport
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
# _build_context — uptime_display and pending_updates_display
# ---------------------------------------------------------------------------

def test_build_context_uptime_display_none_when_uptime_seconds_none():
    """uptime_display is None when uptime_seconds is None."""
    from renderer import _build_context
    ctx = _build_context(make_report())
    assert ctx['uptime_display'] is None


def test_build_context_pending_updates_display_na_when_none():
    """pending_updates_display is 'N/A' when pending_updates is None."""
    from renderer import _build_context
    ctx = _build_context(make_report())
    assert ctx['pending_updates_display'] == 'N/A'


def test_build_context_uptime_display_days_hours():
    """12 days 4 hours = 12*86400+4*3600 seconds."""
    from renderer import _build_context
    ctx = _build_context(make_report(uptime_seconds=12 * 86400 + 4 * 3600))
    assert ctx['uptime_display'] == '12 days 4 hours'


def test_build_context_uptime_display_one_day_zero_hours():
    """1 day 0 hours — singular day, plural hours edge case."""
    from renderer import _build_context
    ctx = _build_context(make_report(uptime_seconds=1 * 86400))
    assert ctx['uptime_display'] == '1 day 0 hours'


def test_build_context_uptime_display_singular_day_singular_hour():
    """1 day 1 hour — both singular."""
    from renderer import _build_context
    ctx = _build_context(make_report(uptime_seconds=1 * 86400 + 1 * 3600))
    assert ctx['uptime_display'] == '1 day 1 hour'


def test_build_context_uptime_display_hours_only():
    """3 hours when days == 0 and hours >= 1."""
    from renderer import _build_context
    ctx = _build_context(make_report(uptime_seconds=3 * 3600))
    assert ctx['uptime_display'] == '3 hours'


def test_build_context_uptime_display_one_hour():
    """1 hour — singular."""
    from renderer import _build_context
    ctx = _build_context(make_report(uptime_seconds=1 * 3600))
    assert ctx['uptime_display'] == '1 hour'


def test_build_context_uptime_display_minutes_only():
    """45 minutes when days == 0 and hours == 0."""
    from renderer import _build_context
    ctx = _build_context(make_report(uptime_seconds=45 * 60))
    assert ctx['uptime_display'] == '45 minutes'


def test_build_context_uptime_display_one_minute():
    """1 minute — singular."""
    from renderer import _build_context
    ctx = _build_context(make_report(uptime_seconds=60))
    assert ctx['uptime_display'] == '1 minute'


def test_build_context_uptime_display_zero_seconds():
    """0 seconds -> 0 minutes (T-13-11 threat mitigation — no division by zero)."""
    from renderer import _build_context
    ctx = _build_context(make_report(uptime_seconds=0))
    assert ctx['uptime_display'] == '0 minutes'


def test_build_context_pending_updates_display_count():
    """pending_updates=3 -> '3 pending'."""
    from renderer import _build_context
    ctx = _build_context(make_report(pending_updates=3))
    assert ctx['pending_updates_display'] == '3 pending'


def test_build_context_pending_updates_display_zero():
    """pending_updates=0 -> '0 pending' (not 'N/A')."""
    from renderer import _build_context
    ctx = _build_context(make_report(pending_updates=0))
    assert ctx['pending_updates_display'] == '0 pending'


def test_build_context_has_warnings_unchanged():
    """has_warnings computation is unchanged: uses severity == 'WARN'."""
    from renderer import _build_context
    from models import Warning
    ctx = _build_context(make_report(warnings=[Warning('UPTIME_WARN', 'WARN', 'warn msg', level='yellow')]))
    assert ctx['has_warnings'] is True
