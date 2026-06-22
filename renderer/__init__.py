"""HTML character sheet renderer. Phase 3.
render_html(report) returns the HTML string without writing (Phase 5 addition, D-01).
Never raises on None hardware fields — D-12/D-13 None handling is in _build_context().
"""
from __future__ import annotations

import importlib.resources as ir

from jinja2 import Environment

from models import AuditReport

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


def _format_uptime(seconds: int) -> str:
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''} {hours} hour{'s' if hours != 1 else ''}"
    if hours >= 1:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def render_html(report: AuditReport) -> str:
    """Return rendered HTML string without writing to disk.

    Phase 5 addition (Option A interface resolution — RESEARCH.md § Interface Conflict).
    main.py calls this to get the HTML string, then writes it directly to the
    dynamically-named output path (D-02/D-03: {date}_scry_{hostname}.html).
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

    other_profiles = [
        p for p in report.local_profiles
        if not p.lower().startswith('adm_') and p != report.current_user
    ]

    dept_codes = sorted(_DEPT_NAMES.items())

    # Uptime display — D-07 (Phase 13)
    uptime_display = _format_uptime(report.uptime_seconds) if report.uptime_seconds is not None else None

    # Pending updates display — D-16 (Phase 13)
    pending_updates_display = (
        f"{report.pending_updates} pending"
        if report.pending_updates is not None
        else "N/A"
    )

    # Dell DCU display — Phase 14 (D-07)
    if report.dell_dcu is not None:
        dcu = report.dell_dcu
        if not dcu.installed:
            # installed=False (not found) or installed=None (error) → "Not installed"
            dell_dcu_display: str | None = "Not installed"
        elif not dcu.scan_data_present:
            dell_dcu_display = "Unknown (no scan data)"
        elif dcu.pending_count is None:
            # scan_data_present=True but parse failed — still show as unknown
            dell_dcu_display = "Unknown (no scan data)"
        else:
            dell_dcu_display = f"{dcu.pending_count} pending"
    else:
        dell_dcu_display = None  # --updates absent; omit row entirely (D-05)

    # Lenovo LSU display — Phase 14 (D-08)
    if report.lenovo_lsu is not None:
        lsu = report.lenovo_lsu
        lenovo_lsu_display: str | None = "Not installed" if not lsu.installed else "Installed - Open Lenovo Vantage to see pending updates"
    else:
        lenovo_lsu_display = None  # --updates absent; omit row entirely (D-05)

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
        'warnings': report.warnings,
        'has_warnings': any(w.severity == 'WARN' for w in report.warnings),
        'timestamp': report.timestamp,
        'uptime_display': uptime_display,
        'pending_updates_display': pending_updates_display,
        'dell_dcu_display': dell_dcu_display,
        'lenovo_lsu_display': lenovo_lsu_display,
    }


def render_console(report: AuditReport) -> str:
    """Return a plain-text audit summary for --console mode.

    Covers the same data as the HTML sheet: identity, hardware, vendor updates,
    user profiles, apps, and health checks. Vendor section only appears when
    --updates was passed (dell_dcu / lenovo_lsu will be non-None).
    """
    ph = report.parsed_hostname
    SEP = "=" * 42
    lines: list[str] = []

    lines.append("SCRY — Master Electronics IT Audit")
    lines.append(SEP)
    lines.append(f"Hostname:    {report.hostname}")
    if ph.device_type:
        lines.append(f"Device Type: {ph.device_type}")
    if ph.city:
        lines.append(f"Location:    {ph.city}")
    guild = (_DEPT_NAMES.get(ph.department, ph.department) if ph.department else None) or ph.company_code
    if guild:
        lines.append(f"Guild:       {guild}")
    if ph.station is not None:
        lines.append(f"Station:     {ph.station}")
    lines.append(f"Timestamp:   {report.timestamp}")

    lines.append("")
    lines.append("--- Hardware ---")
    if report.os_version or report.os_build:
        os_str = report.os_version or ""
        if report.os_build:
            os_str = f"{os_str} — Build {report.os_build}" if os_str else f"Build {report.os_build}"
        lines.append(f"OS:          {os_str}")
    if report.cpu_model:
        lines.append(f"CPU:         {report.cpu_model}")
    if report.ram_gb is not None:
        nearest = _nearest_standard_ram(report.ram_gb)
        lines.append(f"RAM:         {report.ram_gb:.1f} GB ({nearest} GB)")
    if report.disk_total_gb and report.disk_free_gb is not None:
        pct = (report.disk_free_gb / report.disk_total_gb) * 100
        lines.append(f"Disk:        {report.disk_free_gb:.0f} GB free / {report.disk_total_gb:.0f} GB total ({pct:.0f}% free)")
    if report.serial_number:
        lines.append(f"Serial:      {report.serial_number}")
    if report.uptime_seconds is not None:
        lines.append(f"Uptime:      {_format_uptime(report.uptime_seconds)}")
    if report.pending_updates is not None:
        lines.append(f"Pending:     {report.pending_updates} update{'s' if report.pending_updates != 1 else ''}")

    if report.dell_dcu is not None or report.lenovo_lsu is not None:
        lines.append("")
        lines.append("--- Vendor Updates ---")
        if report.dell_dcu is not None:
            dcu = report.dell_dcu
            if not dcu.installed:
                dcu_str = "Not installed"
            elif not dcu.scan_data_present or dcu.pending_count is None:
                dcu_str = "Unknown (no scan data)"
            else:
                dcu_str = f"{dcu.pending_count} pending"
            lines.append(f"Dell DCU:    {dcu_str}")
        if report.lenovo_lsu is not None:
            lsu = report.lenovo_lsu
            lsu_str = "Not installed" if not lsu.installed else "Installed"
            lines.append(f"Lenovo LSU:  {lsu_str}")

    if report.current_user or report.local_profiles:
        lines.append("")
        lines.append("--- Users ---")
        if report.current_user:
            lines.append(f"Current:     {report.current_user}")
        others = [p for p in report.local_profiles if not p.lower().startswith('adm_') and p != report.current_user]
        if others:
            lines.append(f"Others:      {', '.join(others)}")

    if report.apps:
        lines.append("")
        lines.append("--- Apps ---")
        for app in report.apps:
            if app.sub_apps:
                lines.append(f"[+] {app.name}")
                for sub in app.sub_apps:
                    mark = "+" if sub.installed else "-"
                    ver = f" (v{sub.version})" if sub.version else ""
                    lines.append(f"     [{mark}] {sub.name}{ver}")
            else:
                mark = "+" if app.installed else "-"
                if app.installed:
                    suffix = f" (v{app.version})" if app.version else (f" ({app.service_state})" if app.service_state else "")
                else:
                    suffix = "  not installed"
                lines.append(f"[{mark}] {app.name}{suffix}")

    if report.warnings:
        lines.append("")
        lines.append("--- Health Checks ---")
        for w in report.warnings:
            if w.severity == "WARN" and w.level == "red":
                tag = "!!! "
            elif w.severity == "WARN":
                tag = "WARN"
            else:
                tag = "  OK"
            detail_str = f" — {w.detail}" if w.detail else ""
            lines.append(f"[{tag}]  {w.code:<18} {w.message}{detail_str}")

    if report.collection_errors:
        lines.append("")
        lines.append("--- Collection Errors ---")
        for err in report.collection_errors:
            lines.append(f"  {err}")

    lines.append(SEP)
    return "\n".join(lines)
