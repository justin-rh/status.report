"""Windows hardware and profile collectors.
Implements COLL-02 (hardware stats) and COLL-03 (local user profiles).
Both functions mutate AuditReport in place and never raise (D-01, D-02).
"""
from __future__ import annotations

import os
import platform
import time
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

try:
    import win32com.client as _win32com_client  # type: ignore[import-untyped]
    _WIN32COM_AVAILABLE = True
except ImportError:
    _win32com_client = None  # type: ignore[assignment]
    _WIN32COM_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROFILE_LIST_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
SYSTEM_SIDS = {"S-1-5-18", "S-1-5-19", "S-1-5-20"}
_CPU_REGISTRY_PATH = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
_BIOS_PLACEHOLDER_VALUES = frozenset({
    '', 'to be filled by o.e.m.', 'default string', 'none', 'n/a',
})


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def collect_hardware(report: AuditReport) -> None:
    """Populate hardware fields on *report* in place.

    Calls six private helpers in order. No exception propagates out of this
    function under any circumstances (D-01, D-02).
    """
    _collect_os(report)
    _collect_cpu_model(report)
    _collect_memory_and_disk(report)
    _collect_current_user(report)
    _collect_serial_number(report)
    _collect_uptime(report)   # Phase 13 — D-05/D-06


def collect_profiles(report: AuditReport) -> None:
    """Populate local_profiles from HKLM ProfileList registry (D-08, D-03, D-04).

    Filters system SIDs. Extracts username from last path segment.
    Never raises; appends one error to collection_errors on failure.
    """
    try:
        report.local_profiles = _enumerate_profiles()
    except Exception as exc:
        report.collection_errors.append(f"Profile enumeration failed: {exc}")


def collect_pending_updates(report: AuditReport) -> None:
    """Populate pending_updates via WUA COM. Windows-only. Never raises.

    Degrades to pending_updates=None when _WIN32COM_AVAILABLE is False (CI)
    or when the caller lacks SYSTEM/Administrator privilege (D-09, D-10).
    """
    if not _WIN32COM_AVAILABLE:
        return
    try:
        session = _win32com_client.Dispatch("Microsoft.Update.Session")
        searcher = session.CreateUpdateSearcher()
        result = searcher.Search("IsInstalled=0 and Type='Software'")
        report.pending_updates = result.Updates.Count
    except Exception as exc:
        report.collection_errors.append(f"Pending updates collection failed: {exc}")


# ---------------------------------------------------------------------------
# Private helpers — hardware
# ---------------------------------------------------------------------------

def _collect_os(report: AuditReport) -> None:
    """Populate os_version and os_build from platform stdlib.

    platform.version() returns "10.0.BBBBB.R" on both Windows 10 and 11.
    Windows 11 is distinguished by build number >= 22000.
    os_build stores only the build number (e.g. "22621"); os_version stores
    the human-readable name ("Windows 11" or "Windows 10").
    """
    full = platform.version()           # e.g. "10.0.22621.3155"
    parts = full.split(".")
    build_str = parts[2] if len(parts) >= 3 else full
    try:
        build_int = int(build_str)
    except ValueError:
        build_int = 0
    report.os_build = build_str
    if build_int >= 22000:
        report.os_version = "Windows 11"
    else:
        release = platform.release()    # "10", "8", etc.
        report.os_version = f"Windows {release}" if release else "Windows"


def _collect_cpu_model(report: AuditReport) -> None:
    """Populate cpu_model via WMI Win32_Processor with registry fallback.

    Tries WMI first. On failure or unavailability, falls back to
    HKLM\\HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0 ProcessorNameString
    which works without WMI at any privilege level.
    """
    if _WMI_AVAILABLE:
        try:
            c = _wmi_module.WMI()
            processors = c.Win32_Processor()
            if processors:
                report.cpu_model = processors[0].Name.strip()
                return
        except Exception as exc:
            report.collection_errors.append(
                f"CPU model collection failed (WMI): {exc}"
            )
    # Registry fallback — always available on Windows, no elevation needed
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _CPU_REGISTRY_PATH) as key:
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            report.cpu_model = name.strip()
    except (FileNotFoundError, OSError):
        pass  # Both paths failed; cpu_model stays None


def _collect_serial_number(report: AuditReport) -> None:
    """Populate serial_number via WMI Win32_BIOS.SerialNumber with
    Win32_ComputerSystemProduct.IdentifyingNumber fallback.

    Some enterprise laptops report a placeholder in BIOS but a real S/N in
    ComputerSystemProduct. Ignores OEM placeholder strings. Degrades silently
    if WMI unavailable.
    """
    if not _WMI_AVAILABLE:
        return
    try:
        c = _wmi_module.WMI()
        bios_list = c.Win32_BIOS()
        if bios_list:
            sn = (bios_list[0].SerialNumber or '').strip()
            if sn.lower() not in _BIOS_PLACEHOLDER_VALUES:
                report.serial_number = sn
                return
        # Fallback: ComputerSystemProduct.IdentifyingNumber is more reliably
        # populated on enterprise laptops where BIOS serial is a placeholder.
        products = c.Win32_ComputerSystemProduct()
        if products:
            sn = (products[0].IdentifyingNumber or '').strip()
            if sn.lower() not in _BIOS_PLACEHOLDER_VALUES:
                report.serial_number = sn
    except Exception as exc:
        report.collection_errors.append(
            f"Serial number collection failed (WMI): {exc}"
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


def _collect_uptime(report: AuditReport) -> None:
    """Populate uptime_seconds via psutil.boot_time(). Never raises (D-05)."""
    try:
        report.uptime_seconds = int(time.time() - psutil.boot_time())
    except Exception as exc:
        report.collection_errors.append(f"Uptime collection failed: {exc}")


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
