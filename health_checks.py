"""Health checks — evaluates AuditReport fields and produces typed Warning objects.

Always returns exactly five Warning objects from evaluate_warnings() (D-06,
extended to 4 in Phase 13 D-14, extended to 5 for WARN-06): one for OS version
(WARN-01), one for disk space (WARN-02), one for rename required (WARN-03), one
for uptime (WARN-04/WARN-05), and one for security agents (WARN-06).
"""
from models import AuditReport, Warning

# ---------------------------------------------------------------------------
# Threshold constants — adjust here without touching function logic (D-09).
# ---------------------------------------------------------------------------
OS_WARN_BUILD: int = 22000
DISK_WARN_PCT: float = 0.15
UPTIME_WARN_DAYS: int = 7   # WARN-04: caution threshold (yellow)
UPTIME_STALE_DAYS: int = 30  # WARN-05: critical threshold (red); hibernation time counted


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def evaluate_warnings(report: AuditReport) -> list[Warning]:
    """Pure function: AuditReport -> list[Warning]. Never raises.

    Always returns exactly five Warning objects — one per check — so the
    Phase 7 renderer can display a complete status table regardless of
    pass/fail outcome (D-06, extended to 4 in Phase 13 D-14, 5 for WARN-06).
    """
    return [
        _check_os_version(report),
        _check_disk_space(report),
        _check_rename(report),
        _check_uptime(report),
        _check_security_agents(report),
    ]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _check_os_version(report: AuditReport) -> Warning:
    """Return OS_VERSION Warning. WARN when os_build < OS_WARN_BUILD (22000 = Win11)."""
    if report.os_build is None:
        return Warning(
            code='OS_VERSION',
            severity='OK',
            message='OS version check skipped',
            detail='os_build not collected',
        )
    try:
        build_int = int(report.os_build)
    except ValueError:
        return Warning(
            code='OS_VERSION',
            severity='OK',
            message='OS version check skipped',
            detail=f'os_build value not numeric: {report.os_build!r}',
        )
    if build_int < OS_WARN_BUILD:
        return Warning(
            code='OS_VERSION',
            severity='WARN',
            message='Windows 10 or earlier detected',
            detail=f'Build {report.os_build} is below minimum {OS_WARN_BUILD} (Windows 11)',
        )
    return Warning(
        code='OS_VERSION',
        severity='OK',
        message='OS version is current',
        detail=f'Build {report.os_build}',
    )


def _check_disk_space(report: AuditReport) -> Warning:
    """Return DISK_SPACE Warning. WARN when free/total <= DISK_WARN_PCT (0.15)."""
    free = report.disk_free_gb
    total = report.disk_total_gb
    if free is None or total is None:
        return Warning(
            code='DISK_SPACE',
            severity='OK',
            message='Disk space check skipped',
            detail='disk_free_gb or disk_total_gb not collected',
        )
    if total == 0:
        return Warning(
            code='DISK_SPACE',
            severity='OK',
            message='Disk space check skipped',
            detail='disk_total_gb is zero',
        )
    pct_free = free / total
    if pct_free <= DISK_WARN_PCT:
        free_pct_display = f'{pct_free * 100:.1f}'
        return Warning(
            code='DISK_SPACE',
            severity='WARN',
            message='Low disk space',
            detail=f'{free:.1f} GB free of {total:.1f} GB ({free_pct_display}% free)',
        )
    free_pct_display = f'{pct_free * 100:.1f}'
    return Warning(
        code='DISK_SPACE',
        severity='OK',
        message='Disk space is adequate',
        detail=f'{free:.1f} GB free of {total:.1f} GB ({free_pct_display}% free)',
    )


def _check_rename(report: AuditReport) -> Warning:
    """Return RENAME_REQUIRED Warning. WARN when device_type is 'Unknown' (D-01)."""
    if report.parsed_hostname.device_type == 'Unknown':
        return Warning(
            code='RENAME_REQUIRED',
            severity='WARN',
            message='Device needs to be renamed',
            detail=(
                f'Hostname "{report.parsed_hostname.raw_hostname}" does not match '
                'the Master Electronics naming convention'
            ),
        )
    return Warning(
        code='RENAME_REQUIRED',
        severity='OK',
        message='Hostname matches naming convention',
        detail=None,
    )


def _check_uptime(report: AuditReport) -> Warning:
    """Return UPTIME Warning. Escalates: OK -> UPTIME_WARN (yellow) -> UPTIME_STALE (red).

    Boundary rules (D-11):
      uptime_seconds is None -> OK / level=None (collection skipped)
      days <= UPTIME_WARN_DAYS  -> OK / level=None
      days > UPTIME_WARN_DAYS and <= UPTIME_STALE_DAYS -> WARN / level='yellow' (WARN-04)
      days > UPTIME_STALE_DAYS  -> WARN / level='red'   (WARN-05)
    """
    if report.uptime_seconds is None:
        return Warning(
            code='UPTIME',
            severity='OK',
            message='Uptime check skipped',
            detail='uptime_seconds not collected',
        )
    days = report.uptime_seconds // 86400
    if days > UPTIME_STALE_DAYS:
        return Warning(
            code='UPTIME_STALE',
            severity='WARN',
            message=f'Uptime is {days} days — reboot required',
            detail='Hibernation time is counted on Windows',
            level='red',
        )
    if days > UPTIME_WARN_DAYS:
        return Warning(
            code='UPTIME_WARN',
            severity='WARN',
            message=f'Uptime is {days} days',
            detail=f'Uptime exceeds {UPTIME_WARN_DAYS}-day caution threshold',
            level='yellow',
        )
    return Warning(
        code='UPTIME',
        severity='OK',
        message='Uptime is within normal range',
        detail=None,
    )


_REQUIRED_SECURITY_AGENTS = ("NinjaOne", "CrowdStrike Falcon")


def _check_security_agents(report: AuditReport) -> Warning:
    """Return SECURITY_AGENTS Warning. WARN (red) if NinjaOne or CrowdStrike Falcon
    is present in the app list but not installed. Skipped when app collection
    did not run (report.apps is empty).
    """
    if not report.apps:
        return Warning(
            code='SECURITY_AGENTS',
            severity='OK',
            message='Security agent check skipped',
            detail='app collection did not run',
        )

    app_index = {app.name: app for app in report.apps}
    missing = [
        name for name in _REQUIRED_SECURITY_AGENTS
        if name in app_index and not app_index[name].installed
    ]

    if missing:
        names = " and ".join(missing)
        return Warning(
            code='SECURITY_AGENTS',
            severity='WARN',
            message=f'{names} {"is" if len(missing) == 1 else "are"} not installed',
            detail='Security agents must be present on all devices',
            level='red',
        )

    return Warning(
        code='SECURITY_AGENTS',
        severity='OK',
        message='Security agents are installed',
        detail=None,
    )
