"""HTML character sheet renderer. Phase 3.
render_report(report, output_path) is the single public entry point.
Never raises on None hardware fields — D-12/D-13 None handling is in _build_context().
"""
from __future__ import annotations

import importlib.resources as ir
from pathlib import Path

from jinja2 import Environment

from models import AuditReport
from writers import write_html


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

    # Guild — D-03: warehouse=department, laptop=company_code, both None -> None -> '—'
    guild = ph.department or ph.company_code

    # Disk HP bar — D-07, D-13: falsy guard catches both None and 0.0
    if report.disk_total_gb and report.disk_free_gb is not None:
        pct = (report.disk_free_gb / report.disk_total_gb) * 100
        hp_class = 'hp-green' if pct > 50 else ('hp-amber' if pct > 20 else 'hp-red')
    else:
        pct = 100.0
        hp_class = 'hp-none'

    # RAM display — D-06
    ram_display = f'{report.ram_gb:.1f} GB' if report.ram_gb is not None else None

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
        'current_user': report.current_user,
        'apps': report.apps,
        'quest_complete': len(missing) == 0,
        'missing_count': len(missing),
        'timestamp': report.timestamp,
    }
