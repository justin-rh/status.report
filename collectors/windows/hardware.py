"""Windows hardware and profile collectors.
Implements COLL-02 (hardware stats) and COLL-03 (local user profiles).
Both functions mutate AuditReport in place and never raise (D-01, D-02).
"""
from __future__ import annotations

import os
import platform
import winreg

import psutil

from models import AuditReport

# ---------------------------------------------------------------------------
# Module-level wmi import — allows tests to patch _wmi_module without
# requiring a real COM server installed in CI (D-06).
# ---------------------------------------------------------------------------
try:
    import wmi as _wmi_module  # type: ignore[import-untyped]
    _WMI_AVAILABLE = True
except ImportError:
    _wmi_module = None  # type: ignore[assignment]
    _WMI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROFILE_LIST_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
SYSTEM_SIDS = {"S-1-5-18", "S-1-5-19", "S-1-5-20"}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def collect_hardware(report: AuditReport) -> None:
    """Populate hardware fields on *report* in place.

    Calls four private helpers in order. No exception propagates out of this
    function under any circumstances (D-01, D-02).
    """
    _collect_os(report)
    _collect_cpu_model(report)
    _collect_memory_and_disk(report)
    _collect_current_user(report)


def collect_profiles(report: AuditReport) -> None:
    """Populate local_profiles from HKLM ProfileList registry (D-08, D-03, D-04).

    Filters system SIDs. Extracts username from last path segment.
    Never raises; appends one error to collection_errors on failure.
    """
    try:
        report.local_profiles = _enumerate_profiles()
    except Exception as exc:
        report.collection_errors.append(f"Profile enumeration failed: {exc}")


# ---------------------------------------------------------------------------
# Private helpers — hardware
# ---------------------------------------------------------------------------

def _collect_os(report: AuditReport) -> None:
    """Populate os_version and os_build from platform stdlib.

    platform.release() / platform.version() never fail on Windows Python 3.12.
    No try/except needed (D-07).
    """
    report.os_version = platform.release()   # "10" or "11"
    report.os_build = platform.version()     # "10.0.19045" (Windows 10 22H2)


def _collect_cpu_model(report: AuditReport) -> None:
    """Populate cpu_model via WMI Win32_Processor (D-06).

    The entire WMI import + instantiation + query is wrapped in one try/except.
    If any step fails, cpu_model stays None (model default) and one error is
    appended (D-02).
    """
    if not _WMI_AVAILABLE:
        return  # wmi not installed; degrade silently (not a runtime failure)
    try:
        c = _wmi_module.WMI()
        processors = c.Win32_Processor()
        if processors:
            report.cpu_model = processors[0].Name.strip()
    except Exception as exc:
        report.collection_errors.append(
            f"CPU model collection failed (WMI): {exc}"
        )


def _collect_memory_and_disk(report: AuditReport) -> None:
    """Populate ram_gb, disk_total_gb, disk_free_gb via psutil (D-05).

    RAM collection never fails at standard user privilege — no try/except.
    Disk is wrapped because unusual configurations (no C:\\, junction issues)
    can cause FileNotFoundError.
    """
    # RAM — always works at standard user privilege
    report.ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    # Disk — target C:\ primary volume
    try:
        disk = psutil.disk_usage("C:\\")
        report.disk_total_gb = round(disk.total / (1024 ** 3), 1)
        report.disk_free_gb = round(disk.free / (1024 ** 3), 1)
    except Exception as exc:
        report.collection_errors.append(f"Disk usage collection failed: {exc}")


def _collect_current_user(report: AuditReport) -> None:
    """Populate current_user from Windows session environment variables.

    os.environ.get() never raises. Falls back to None if both env vars absent.
    USERNAME is set by Windows for all interactive sessions (D-05).
    """
    report.current_user = os.environ.get("USERNAME") or os.environ.get("USER") or None


# ---------------------------------------------------------------------------
# Private helpers — profiles
# ---------------------------------------------------------------------------

def _enumerate_profiles() -> list[str]:
    """Read HKLM ProfileList, skip system SIDs, return list of usernames.

    Raises OSError if the ProfileList key itself cannot be opened — the caller
    (collect_profiles) catches this and logs it to collection_errors.
    Per-SID read failures are silently skipped (D-02: one message per subsystem).
    """
    profiles: list[str] = []
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, PROFILE_LIST_KEY) as key:
        i = 0
        while True:
            try:
                sid = winreg.EnumKey(key, i)
                i += 1
            except OSError:
                break  # EnumKey raises OSError when index exhausted — normal end
            if sid in SYSTEM_SIDS:
                continue
            try:
                with winreg.OpenKey(key, sid) as sid_key:
                    path, _ = winreg.QueryValueEx(sid_key, "ProfileImagePath")
                    expanded = winreg.ExpandEnvironmentStrings(path)
                    username = expanded.rstrip("\\").split("\\")[-1]
                    if username:
                        profiles.append(username)
            except (FileNotFoundError, OSError):
                continue  # Skip unreadable SID subkey silently
    return profiles
