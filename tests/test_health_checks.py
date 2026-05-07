"""Unit tests for health_checks — evaluate_warnings function."""
from __future__ import annotations

import pytest

from models import AuditReport, Warning
from parsers.name_parser import parse_hostname
from health_checks import evaluate_warnings


def make_report(**kwargs) -> AuditReport:
    defaults = dict(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))
    defaults.update(kwargs)
    return AuditReport(**defaults)


# ---------------------------------------------------------------------------
# OS version check — boundary cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('os_build,expected_severity', [
    ('21999', 'WARN'),   # one below threshold — Windows 10
    ('22000', 'OK'),     # exactly at threshold — Windows 11
    ('22621', 'OK'),     # well above threshold — Windows 11 22H2
    (None,    'OK'),     # missing data — check skipped, not a warning
    ('abc',   'OK'),     # non-numeric — check skipped, not a warning
])
def test_os_version_check(os_build, expected_severity):
    report = make_report(os_build=os_build)
    warnings = evaluate_warnings(report)
    os_warning = warnings[0]
    assert os_warning.code == 'OS_VERSION', (
        f'os_build={os_build!r}: expected code=OS_VERSION, got {os_warning.code!r}'
    )
    assert os_warning.severity == expected_severity, (
        f'os_build={os_build!r}: expected severity={expected_severity!r}, got {os_warning.severity!r}'
    )


def test_os_version_skip_has_detail():
    """None os_build returns OK with a non-None detail explaining the skip."""
    report = make_report(os_build=None)
    warnings = evaluate_warnings(report)
    assert warnings[0].detail is not None, 'skipped OS check must include detail'


def test_os_version_nonnumeric_has_detail():
    """Non-numeric os_build returns OK with a non-None detail explaining the skip."""
    report = make_report(os_build='abc')
    warnings = evaluate_warnings(report)
    assert warnings[0].detail is not None, 'non-numeric OS check must include detail'


# ---------------------------------------------------------------------------
# Disk space check — boundary cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('disk_free_gb,disk_total_gb,expected_severity', [
    (1.5,  10.0, 'WARN'),  # exactly 15% — at threshold, WARN
    (1.51, 10.0, 'OK'),    # just above 15% — above threshold, OK
    (0.0,  10.0, 'WARN'),  # 0% free — well below threshold, WARN
    (10.0, 10.0, 'OK'),    # 100% free — fully available, OK
    (None, None, 'OK'),    # both None — check skipped, not a warning
    (None, 10.0, 'OK'),    # free None — partial data, skip
    (1.0,  None, 'OK'),    # total None — partial data, skip
])
def test_disk_space_check(disk_free_gb, disk_total_gb, expected_severity):
    report = make_report(disk_free_gb=disk_free_gb, disk_total_gb=disk_total_gb)
    warnings = evaluate_warnings(report)
    disk_warning = warnings[1]
    assert disk_warning.code == 'DISK_SPACE', (
        f'free={disk_free_gb}, total={disk_total_gb}: expected code=DISK_SPACE, got {disk_warning.code!r}'
    )
    assert disk_warning.severity == expected_severity, (
        f'free={disk_free_gb}, total={disk_total_gb}: expected severity={expected_severity!r}, '
        f'got {disk_warning.severity!r}'
    )


def test_disk_space_skip_has_detail():
    """None disk fields return OK with a non-None detail explaining the skip."""
    report = make_report(disk_free_gb=None, disk_total_gb=None)
    warnings = evaluate_warnings(report)
    assert warnings[1].detail is not None, 'skipped disk check must include detail'


# ---------------------------------------------------------------------------
# Always-two guarantee
# ---------------------------------------------------------------------------

def test_evaluate_warnings_always_returns_two():
    """evaluate_warnings must always return exactly 2 Warning objects (D-06)."""
    report = make_report()
    warnings = evaluate_warnings(report)
    assert len(warnings) == 2, f'expected 2 warnings, got {len(warnings)}'
    assert warnings[0].code == 'OS_VERSION'
    assert warnings[1].code == 'DISK_SPACE'


# ---------------------------------------------------------------------------
# No-raise guarantee
# ---------------------------------------------------------------------------

def test_evaluate_warnings_never_raises():
    """evaluate_warnings must not raise for any AuditReport field combination."""
    all_none_report = make_report(
        os_version=None,
        os_build=None,
        serial_number=None,
        cpu_model=None,
        ram_gb=None,
        disk_total_gb=None,
        disk_free_gb=None,
        current_user=None,
    )
    try:
        result = evaluate_warnings(all_none_report)
        assert len(result) == 2
    except Exception as exc:
        pytest.fail(f'evaluate_warnings raised an exception with all-None fields: {exc}')
