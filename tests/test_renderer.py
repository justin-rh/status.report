"""Unit tests for renderer — render_report function and helpers.
Full test suite covering _build_context logic, render_report integration,
write_html, template loading, and no-raise guarantee.
"""
from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from models import AuditReport, ParsedHostname, AppStatus
from parsers.name_parser import parse_hostname
from health_checks import evaluate_warnings


def make_report(**kwargs) -> AuditReport:
    """Return a minimal AuditReport for unit testing. Override fields with kwargs."""
    defaults = dict(
        hostname='TEST-PC',
        parsed_hostname=parse_hostname('TEST-PC'),
    )
    defaults.update(kwargs)
    return AuditReport(**defaults)


# MOCK_REPORT exercises: both badge states, service_state, Quest Incomplete path,
# None field degradation. All 11 required apps. Disk ~8% free -> hp-red.
MOCK_REPORT = AuditReport(
    hostname='PHX-INV-003',
    parsed_hostname=parse_hostname('PHX-INV-003'),
    os_version='Windows 10 Pro',
    os_build='19045',
    cpu_model='Intel Core i7-10700',
    ram_gb=16.0,
    disk_total_gb=476.0,
    disk_free_gb=38.0,
    current_user='jsmith',
    local_profiles=['C:\\Users\\jsmith', 'C:\\Users\\admin'],
    apps=[
        AppStatus('NinjaOne', installed=True, version='5.8.1234'),
        AppStatus('CrowdStrike Falcon', installed=True, version='7.14.17608', service_state='Running'),
        AppStatus('MERP', installed=False),
        AppStatus('Word', installed=True, version='16.0.17628'),
        AppStatus('Excel', installed=True, version='16.0.17628'),
        AppStatus('Outlook', installed=True, version='16.0.17628'),
        AppStatus('Teams', installed=False),
        AppStatus('OneDrive', installed=True, version='24.021.0201'),
        AppStatus('Zoom', installed=False),
        AppStatus('Chrome', installed=True, version='124.0.6367.60'),
        AppStatus('Claude desktop app', installed=False),
    ],
    timestamp='2026-05-04 22:10:00',
)
MOCK_REPORT.warnings = evaluate_warnings(MOCK_REPORT)


# ---------------------------------------------------------------------------
# _load_template_source — importlib.resources path
# ---------------------------------------------------------------------------

def test_load_template_source_returns_string():
    """_load_template_source returns a non-empty string."""
    from renderer import _load_template_source
    result = _load_template_source()
    assert isinstance(result, str)
    assert len(result) > 0


def test_load_template_source_contains_html_landmarks():
    """Template source contains expected HTML/Jinja2 landmarks."""
    from renderer import _load_template_source
    result = _load_template_source()
    assert '<!DOCTYPE html>' in result
    assert '{{ hostname }}' in result
    assert '{% for app in apps %}' in result


# ---------------------------------------------------------------------------
# _build_context — None field handling (D-12, D-13)
# ---------------------------------------------------------------------------

def test_build_context_all_none_hardware():
    """All None hardware fields produce hp-none, 100.0 pct, and None display values."""
    from renderer import _build_context
    report = make_report()
    ctx = _build_context(report)
    assert ctx['hp_class'] == 'hp-none'
    assert ctx['disk_pct'] == 100.0
    assert ctx['ram_display'] is None
    assert ctx['disk_total_display'] is None
    assert ctx['disk_label'] is None
    assert ctx['os_combined'] is None


def test_build_context_disk_none_produces_hp_none():
    """disk_total_gb=None produces hp_class='hp-none' and disk_pct=100.0."""
    from renderer import _build_context
    report = make_report(disk_total_gb=None)
    ctx = _build_context(report)
    assert ctx['hp_class'] == 'hp-none'
    assert ctx['disk_pct'] == 100.0


def test_build_context_disk_zero_produces_hp_none():
    """disk_total_gb=0.0 produces hp_class='hp-none' (Pitfall 3 falsy guard)."""
    from renderer import _build_context
    report = make_report(disk_total_gb=0.0)
    ctx = _build_context(report)
    assert ctx['hp_class'] == 'hp-none'
    assert ctx['disk_pct'] == 100.0


def test_build_context_hp_green():
    """disk_total_gb=100.0, disk_free_gb=60.0 -> hp_class='hp-green' (60% free > 50%)."""
    from renderer import _build_context
    report = make_report(disk_total_gb=100.0, disk_free_gb=60.0)
    ctx = _build_context(report)
    assert ctx['hp_class'] == 'hp-green'


def test_build_context_hp_amber():
    """disk_total_gb=100.0, disk_free_gb=35.0 -> hp_class='hp-amber' (35% free, 20-50%)."""
    from renderer import _build_context
    report = make_report(disk_total_gb=100.0, disk_free_gb=35.0)
    ctx = _build_context(report)
    assert ctx['hp_class'] == 'hp-amber'


def test_build_context_hp_red():
    """disk_total_gb=476.0, disk_free_gb=38.0 -> hp_class='hp-red' (~8% free <= 20%)."""
    from renderer import _build_context
    report = make_report(disk_total_gb=476.0, disk_free_gb=38.0)
    ctx = _build_context(report)
    assert ctx['hp_class'] == 'hp-red'


def test_build_context_guild_warehouse():
    """Guild shows department for warehouse device (D-03)."""
    from renderer import _build_context
    ph = ParsedHostname(raw_hostname='PHX-INV-003', department='INV', company_code=None)
    report = make_report(parsed_hostname=ph)
    ctx = _build_context(report)
    assert ctx['guild'] == 'Inventory'


def test_build_context_guild_laptop():
    """Guild shows company_code for user-assigned laptop (D-03)."""
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


# ---------------------------------------------------------------------------
# _build_context — quest status (D-11)
# ---------------------------------------------------------------------------

def test_build_context_quest_complete_when_all_installed():
    """quest_complete=True and missing_count=0 when all apps are installed."""
    from renderer import _build_context
    report = make_report(apps=[
        AppStatus('NinjaOne', installed=True),
        AppStatus('CrowdStrike Falcon', installed=True),
    ])
    ctx = _build_context(report)
    assert ctx['quest_complete'] is True
    assert ctx['missing_count'] == 0


def test_build_context_quest_incomplete_mock_report():
    """MOCK_REPORT has 4 missing apps -> quest_complete=False, missing_count=4."""
    from renderer import _build_context
    ctx = _build_context(MOCK_REPORT)
    assert ctx['quest_complete'] is False
    assert ctx['missing_count'] == 4


# ---------------------------------------------------------------------------
# render_report — integration (writes real file to tempfile.TemporaryDirectory)
# ---------------------------------------------------------------------------

def test_render_report_writes_file():
    """render_report writes status_report.html to output_path."""
    from renderer import render_report
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        assert out.exists()
        assert out.name == 'status_report.html'


def test_render_report_returns_existing_path():
    """render_report returns a Path that exists and is a file."""
    from renderer import render_report
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        assert out.is_file()


def test_render_report_html_contains_hostname():
    """Rendered HTML contains the hostname from MOCK_REPORT."""
    from renderer import render_report
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        html = out.read_text(encoding='utf-8')
        assert 'PHX-INV-003' in html


def test_render_report_html_contains_installed_badge():
    """Rendered HTML contains installed badge character for installed apps."""
    from renderer import render_report
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        html = out.read_text(encoding='utf-8')
        # autoescape=True converts ✓ to &#10003; in the rendered output
        assert '&#10003;' in html or '✓' in html


def test_render_report_html_contains_missing_badge():
    """Rendered HTML contains missing badge character for missing apps."""
    from renderer import render_report
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        html = out.read_text(encoding='utf-8')
        # autoescape=True converts ✗ to &#10007; in the rendered output
        assert '&#10007;' in html or '✗' in html


def test_render_report_html_quest_incomplete():
    """Rendered HTML contains MISSING SOFTWARE banner for MOCK_REPORT (4 missing apps)."""
    from renderer import render_report
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        html = out.read_text(encoding='utf-8')
        assert 'MISSING SOFTWARE' in html


def test_render_report_none_cpu_model_renders_emdash():
    """None cpu_model renders as em-dash, not the string 'None'."""
    from renderer import render_report
    report = make_report(cpu_model=None)
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(report, Path(tmp))
        html = out.read_text(encoding='utf-8')
        assert '—' in html  # em-dash U+2014
        # 'None' must not appear as standalone token — use word-boundary check
        # Avoid false positive from 'NinjaOne' substring by checking for ' None' or '>None'
        assert ' None' not in html
        assert '>None<' not in html


# ---------------------------------------------------------------------------
# write_html (writers/__init__.py)
# ---------------------------------------------------------------------------

def test_write_html_creates_file():
    """write_html creates status_report.html in the given directory."""
    from writers import write_html
    with tempfile.TemporaryDirectory() as tmp:
        write_html('<html>x</html>', Path(tmp))
        assert (Path(tmp) / 'status_report.html').exists()


def test_write_html_contents_match():
    """File content written by write_html matches the html argument exactly."""
    from writers import write_html
    html = '<html><body>test content</body></html>'
    with tempfile.TemporaryDirectory() as tmp:
        dest = write_html(html, Path(tmp))
        assert dest.read_text(encoding='utf-8') == html


# ---------------------------------------------------------------------------
# No-raise guarantee
# ---------------------------------------------------------------------------

def test_render_report_never_raises_on_all_none_report():
    """render_report must not raise when all optional AuditReport fields are None."""
    from renderer import render_report
    report = AuditReport(
        hostname='NULL-PC',
        parsed_hostname=parse_hostname('NULL-PC'),
        os_version=None,
        os_build=None,
        cpu_model=None,
        ram_gb=None,
        disk_total_gb=None,
        disk_free_gb=None,
        current_user=None,
        apps=[],
        timestamp='',
    )
    try:
        with tempfile.TemporaryDirectory() as tmp:
            render_report(report, Path(tmp))
    except Exception as exc:
        pytest.fail(f"render_report raised an exception on all-None report: {exc}")


# ---------------------------------------------------------------------------
# Warnings box — HTML output tests (Phase 7, WARN-03)
# ---------------------------------------------------------------------------

def test_render_report_html_contains_warnings_box():
    """Rendered HTML contains the warnings box element for any report."""
    from renderer import render_report
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        html = out.read_text(encoding='utf-8')
        assert 'warnings-box' in html, 'warnings-box class not found in rendered HTML'


def test_render_report_warnings_box_open_when_warn():
    """Warnings box has open attribute when MOCK_REPORT has WARN-severity warnings."""
    from renderer import render_report
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(MOCK_REPORT, Path(tmp))
        html = out.read_text(encoding='utf-8')
        # MOCK_REPORT has OS_VERSION WARN and DISK_SPACE WARN -> has_warnings=True -> open attr
        assert 'warnings-box' in html
        # The <details> tag must carry the open attribute
        assert '<details class="section-card warnings-box" open>' in html or \
               'warnings-box" open' in html, \
               'Expected open attribute on details element when warnings present'


def test_render_report_warnings_box_closed_when_all_ok():
    """Warnings box does not carry open attribute when all warnings are OK severity."""
    from renderer import render_report
    # Build a report where all three checks are OK:
    # os_build='22621' (Win11, OS_VERSION OK), disk 60% free (DISK_SPACE OK),
    # valid hostname parsed as non-Unknown device_type (RENAME_REQUIRED OK)
    report = make_report(
        hostname='PHX-INV-005',
        parsed_hostname=parse_hostname('PHX-INV-005'),
        os_build='22621',
        disk_total_gb=100.0,
        disk_free_gb=60.0,
    )
    report.warnings = evaluate_warnings(report)
    with tempfile.TemporaryDirectory() as tmp:
        out = render_report(report, Path(tmp))
        html = out.read_text(encoding='utf-8')
        assert 'warnings-box' in html, 'warnings-box should always be present'
        assert '<details class="section-card warnings-box" open>' not in html, \
               'open attribute must be absent when all warnings are OK'
        assert 'warnings-box" open' not in html, \
               'open attribute must be absent when all warnings are OK'


def test_render_report_no_old_warning_banners():
    """_build_context does not contain os_warning or rename_warning keys (D-02)."""
    from renderer import _build_context
    report = make_report()
    ctx = _build_context(report)
    assert 'os_warning' not in ctx, (
        "'os_warning' key found in _build_context output — should have been removed in Phase 7"
    )
    assert 'rename_warning' not in ctx, (
        "'rename_warning' key found in _build_context output — should have been removed in Phase 7"
    )


def test_build_context_warnings_keys_present():
    """_build_context returns 'warnings' list and 'has_warnings' bool (D-08)."""
    from renderer import _build_context
    report = make_report()
    ctx = _build_context(report)
    assert 'warnings' in ctx, "'warnings' key missing from _build_context output"
    assert 'has_warnings' in ctx, "'has_warnings' key missing from _build_context output"
    assert isinstance(ctx['warnings'], list), (
        f"'warnings' must be a list, got {type(ctx['warnings']).__name__}"
    )
    assert isinstance(ctx['has_warnings'], bool), (
        f"'has_warnings' must be a bool, got {type(ctx['has_warnings']).__name__}"
    )
