"""HTML character sheet renderer. Phase 3.
render_report(report, output_path) writes HTML to a directory (existing interface).
render_html(report) returns the HTML string without writing (Phase 5 addition, D-01).
Never raises on None hardware fields — D-12/D-13 None handling is in _build_context().
"""
from __future__ import annotations

import importlib.resources as ir
from pathlib import Path

from jinja2 import Environment

from models import AuditReport
from writers import write_html

_STANDARD_RAM_SIZES = (2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128)


def _nearest_standard_ram(gb: float) -> int:
    return min(_STANDARD_RAM_SIZES, key=lambda s: abs(s - gb))


_DEPT_NAMES: dict[str, str] = {
    'AGG': 'Aggregation',
    'ASI': 'Autostore Induction',
    'ASP': 'Autostore Picking',
    'DCC': 'DC Connect',
    'FLX': 'Flex',
    'INV': 'Inventory',
    'LTL': 'Less than Truckload',
    'PAK': 'Packaging',
    'PAR': 'Inside Packaging',
    'QCD': 'Quality Control',
    'REC': 'Receiving',
    'RMA': 'Return Merchandise',
    'SHP': 'Shipping',
    'STK': 'Stocking',
    'REV': 'Revitalization',
    'VAD': 'Value Add',
    'RLT': 'Reel Table',
    'P3A': 'Pull to Pick',
    'P3B': 'Pull to Pick',
    'PBT': 'Packaging Big and Tall',
}


def render_report(report: AuditReport, output_path: Path) -> Path:
    """Render AuditReport to HTML character sheet and write to output_path.

    Returns the full path of the written file.
    Caller resolves output_path from Path(sys.executable).parent — D-16.
    Never raises on None hardware fields — all None values pre-processed in
    _build_context() before template render (D-12, D-13).
    """
    template_source = _load_template_source()
    env = Environment(autoescape=True)
    template = env.from_string(template_source)
    ctx = _build_context(report)
    html = template.render(**ctx)
    return write_html(html, output_path)


def render_html(report: AuditReport) -> str:
    """Return rendered HTML string without writing to disk.

    Phase 5 addition (Option A interface resolution — RESEARCH.md § Interface Conflict).
    main.py calls this to get the HTML string, then writes it directly to the
    dynamically-named output path (D-02/D-03: status_{hostname}_{date}.html).
    render_report() is unchanged — no breakage to existing 94 tests.
    """
    template_source = _load_template_source()
    env = Environment(autoescape=True)
    template = env.from_string(template_source)
    ctx = _build_context(report)
    return template.render(**ctx)


def _load_template_source() -> str:
    """Load Jinja2 template source via importlib.resources (D-15, PyInstaller-safe).

    ir.files('renderer').joinpath() works in --onedir bundles where templates
    stay as real files on disk. Do NOT use jinja2.PackageLoader — it fails in
    frozen environments (RESEARCH.md Pitfall 1).
    """
    return (
        ir.files('renderer')
        .joinpath('templates/character_sheet.html')
        .read_text(encoding='utf-8')
    )


def _build_context(report: AuditReport) -> dict:
    """Build Jinja2 template context from AuditReport. All None handling here.

    Pre-computes all derived values (disk pct, hp_class, guild, quest status)
    so the template stays logic-free. None fields become None in the dict;
    the template's {{ value | default('—') }} filter handles display (D-12).
    """
    ph = report.parsed_hostname

    # Guild — D-03: warehouse=department (resolved to full name), laptop=company_code
    dept_name = _DEPT_NAMES.get(ph.department, ph.department) if ph.department else None
    guild = dept_name or ph.company_code

    # Disk HP bar — D-07, D-13: falsy guard catches both None and 0.0
    if report.disk_total_gb and report.disk_free_gb is not None:
        pct = (report.disk_free_gb / report.disk_total_gb) * 100
        hp_class = 'hp-green' if pct > 50 else ('hp-amber' if pct > 20 else 'hp-red')
    else:
        pct = 100.0
        hp_class = 'hp-none'

    # RAM display — D-06
    if report.ram_gb is not None:
        nearest = _nearest_standard_ram(report.ram_gb)
        ram_display = f'{report.ram_gb:.1f} GB ({nearest} GB)'
    else:
        ram_display = None

    # Disk total display — D-06
    disk_total_display = (
        f'{int(report.disk_total_gb)} GB total'
        if report.disk_total_gb is not None else None
    )
    disk_label = (
        f'{report.disk_free_gb:.0f} GB free / {report.disk_total_gb:.0f} GB total ({pct:.0f}% free)'
        if report.disk_total_gb and report.disk_free_gb is not None else None
    )

    # OS combined — UI-SPEC Stat Block table
    if report.os_version and report.os_build:
        os_combined = f'{report.os_version} — Build {report.os_build}'
    else:
        os_combined = report.os_version  # may be None -> template renders '—'

    # Quest status — D-11
    missing = [app for app in report.apps if not app.installed]

    # Rename warning — shown when hostname could not be parsed
    rename_warning = ph.device_type == 'Unknown'

    # OS upgrade warning — Windows 10 or earlier (build < 22000)
    try:
        _build_int = int(report.os_build or '0')
    except ValueError:
        _build_int = 0
    os_warning = 0 < _build_int < 22000

    other_profiles = [
        p for p in report.local_profiles
        if not p.lower().startswith('adm_') and p != report.current_user
    ]

    dept_codes = sorted(_DEPT_NAMES.items())

    return {
        'hostname': report.hostname,
        'device_type': ph.device_type,
        'city': ph.city,
        'guild': guild,
        'station': ph.station,
        'cpu_model': report.cpu_model,
        'ram_display': ram_display,
        'disk_total_display': disk_total_display,
        'disk_pct': round(pct, 1),
        'hp_class': hp_class,
        'disk_label': disk_label,
        'os_combined': os_combined,
        'serial_number': report.serial_number,
        'current_user': report.current_user,
        'other_profiles': other_profiles,
        'dept_codes': dept_codes,
        'apps': report.apps,
        'quest_complete': len(missing) == 0,
        'missing_count': len(missing),
        'rename_warning': rename_warning,
        'os_warning': os_warning,
        'timestamp': report.timestamp,
    }
