"""Unit tests for health_checks — evaluate_warnings function."""
from __future__ import annotations

import pytest

from models import AuditReport, Warning, ParsedHostname
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
# Always-three guarantee
# ---------------------------------------------------------------------------

def test_evaluate_warnings_always_returns_four():
    """evaluate_warnings must always return exactly 5 Warning objects (Phase 13 D-14, +WARN-06)."""
    report = make_report()
    warnings = evaluate_warnings(report)
    assert len(warnings) == 5, f'expected 5 warnings, got {len(warnings)}'
    assert warnings[0].code == 'OS_VERSION'
    assert warnings[1].code == 'DISK_SPACE'
    assert warnings[2].code == 'RENAME_REQUIRED'
    assert warnings[3].code in ('UPTIME', 'UPTIME_WARN', 'UPTIME_STALE')
    assert warnings[4].code == 'SECURITY_AGENTS'


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
        assert len(result) == 5
    except Exception as exc:
        pytest.fail(f'evaluate_warnings raised an exception with all-None fields: {exc}')


# ---------------------------------------------------------------------------
# Rename check — boundary cases (D-01)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('device_type,expected_severity', [
    ('Unknown',               'WARN'),   # unrecognized hostname — rename required
    ('Warehouse Workstation', 'OK'),     # valid type — no rename needed
    ('Department Laptop',     'OK'),     # valid type — no rename needed
])
def test_rename_check(device_type, expected_severity):
    ph = ParsedHostname(raw_hostname='TEST-PC', device_type=device_type)
    report = make_report(parsed_hostname=ph)
    warnings = evaluate_warnings(report)
    rename_warning = warnings[2]
    assert rename_warning.code == 'RENAME_REQUIRED', (
        f'device_type={device_type!r}: expected code=RENAME_REQUIRED, got {rename_warning.code!r}'
    )
    assert rename_warning.severity == expected_severity, (
        f'device_type={device_type!r}: expected severity={expected_severity!r}, '
        f'got {rename_warning.severity!r}'
    )


def test_rename_check_warn_has_detail():
    """RENAME_REQUIRED WARN includes a non-None detail with the raw hostname."""
    ph = ParsedHostname(raw_hostname='BADNAME', device_type='Unknown')
    report = make_report(parsed_hostname=ph)
    warnings = evaluate_warnings(report)
    rename_warning = warnings[2]
    assert rename_warning.detail is not None, 'RENAME_REQUIRED WARN must include detail'
    assert 'BADNAME' in rename_warning.detail, (
        f'detail should include raw_hostname "BADNAME", got: {rename_warning.detail!r}'
    )


def test_rename_check_ok_has_no_detail():
    """RENAME_REQUIRED OK has detail=None (no extra info needed when hostname is valid)."""
    ph = ParsedHostname(raw_hostname='PHX-INV-003', device_type='Warehouse Workstation')
    report = make_report(parsed_hostname=ph)
    warnings = evaluate_warnings(report)
    rename_warning = warnings[2]
    assert rename_warning.detail is None, (
        f'RENAME_REQUIRED OK should have detail=None, got: {rename_warning.detail!r}'
    )


# ---------------------------------------------------------------------------
# Uptime check — boundary cases (WARN-04, WARN-05, D-11)
# RED: these tests fail until _check_uptime() is implemented in health_checks.py
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('uptime_seconds,expected_code,expected_severity,expected_level', [
    (None,              'UPTIME',       'OK',   None),       # collection failed
    (0,                 'UPTIME',       'OK',   None),       # 0 seconds — well within OK
    (6 * 86400,         'UPTIME',       'OK',   None),       # 6 days — below warn threshold
    (7 * 86400,         'UPTIME',       'OK',   None),       # exactly 7 days — not yet WARN (> not >=)
    (7 * 86400 + 1,     'UPTIME',       'OK',   None),       # 7 days + 1 sec — floor div still 7d, not yet WARN
    (8 * 86400,         'UPTIME_WARN',  'WARN', 'yellow'),  # 8 days — within warn range
    (30 * 86400,        'UPTIME_WARN',  'WARN', 'yellow'),  # exactly 30 days — not yet stale
    (31 * 86400,        'UPTIME_STALE', 'WARN', 'red'),     # 31 days — stale
])
def test_uptime_check(uptime_seconds, expected_code, expected_severity, expected_level):
    """_check_uptime boundary cases: None, < 7d, = 7d, just over 7d, 8d, = 30d, 31d."""
    report = make_report(uptime_seconds=uptime_seconds)
    warnings = evaluate_warnings(report)
    uptime_warning = warnings[3]
    assert uptime_warning.code == expected_code, (
        f'uptime_seconds={uptime_seconds}: expected code {expected_code!r}, got {uptime_warning.code!r}'
    )
    assert uptime_warning.severity == expected_severity
    assert uptime_warning.level == expected_level


def test_uptime_stale_detail_mentions_hibernation():
    """UPTIME_STALE detail must mention hibernation time counting (REQUIREMENTS.md WARN-05)."""
    report = make_report(uptime_seconds=31 * 86400)
    warnings = evaluate_warnings(report)
    assert warnings[3].code == 'UPTIME_STALE'
    assert warnings[3].detail is not None
    assert 'hibernation' in warnings[3].detail.lower(), (
        f"UPTIME_STALE detail must mention 'hibernation'; got: {warnings[3].detail!r}"
    )
