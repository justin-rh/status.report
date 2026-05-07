"""Health checks — evaluates AuditReport fields and produces typed Warning objects.

Always returns exactly two Warning objects from evaluate_warnings() (D-06):
one for OS version (WARN-01) and one for disk space (WARN-02).
"""
from models import AuditReport, Warning

# ---------------------------------------------------------------------------
# Threshold constants — adjust here without touching function logic (D-09).
# ---------------------------------------------------------------------------
OS_WARN_BUILD: int = 22000
DISK_WARN_PCT: float = 0.15


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def evaluate_warnings(report: AuditReport) -> list[Warning]:
    """Pure function: AuditReport -> list[Warning]. Never raises.

    Always returns exactly two Warning objects — one per check — so the
    Phase 7 renderer can display a complete status table regardless of
    pass/fail outcome (D-06).
    """
    return [
        _check_os_version(report),
        _check_disk_space(report),
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
