"""macOS hardware and profile collectors.
Implements PLAT-V2-01 (hardware stats) and PLAT-V2-02 (local user profiles).
Both functions mutate AuditReport in place and never raise (D-01, D-02 from 02-CONTEXT.md).
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import time

import psutil

from models import AuditReport

# ---------------------------------------------------------------------------
# Module-level pwd import — allows tests to patch _pwd_module without
# requiring a POSIX OS in CI (mirrors _wmi_module guard in windows/hardware.py).
# pwd is POSIX-only; this guard prevents ImportError on Windows CI (RESEARCH Pitfall 4).
# ---------------------------------------------------------------------------
try:
    import pwd as _pwd_module
    _PWD_AVAILABLE = True
except ImportError:
    _pwd_module = None  # type: ignore[assignment]
    _PWD_AVAILABLE = False


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def collect_hardware(report: AuditReport) -> None:
    """Populate hardware fields on *report* in place.

    Calls five private helpers in order. No exception propagates out of this
    function under any circumstances (D-01, D-02).
    """
    _collect_os(report)
    _collect_cpu_model(report)
    _collect_memory_and_disk(report)
    _collect_current_user(report)
    _collect_uptime(report)   # Phase 13 — D-05/D-06


def collect_profiles(report: AuditReport) -> None:
    """Populate local_profiles from pwd database (D-11).

    Filters accounts with UID < 501 (system accounts on macOS).
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
    """Populate os_version and os_build from sw_vers subprocess calls (D-06).

    Two separate subprocess.run calls — each individually guarded.
    os_version is prefixed with 'macOS ' (e.g. 'macOS 14.4.1').
    os_build is the raw build string (e.g. '23E224').
    """
    try:
        result = subprocess.run(
            ["sw_vers", "-productVersion"],
            capture_output=True, text=True, timeout=5,
        )
        version_str = result.stdout.strip()
        if version_str:
            report.os_version = f"macOS {version_str}"
    except Exception as exc:
        report.collection_errors.append(f"OS version collection failed: {exc}")
    try:
        result = subprocess.run(
            ["sw_vers", "-buildVersion"],
            capture_output=True, text=True, timeout=5,
        )
        build_str = result.stdout.strip()
        if build_str:
            report.os_build = build_str
    except Exception as exc:
        report.collection_errors.append(f"OS build collection failed: {exc}")


def _collect_cpu_model(report: AuditReport) -> None:
    """Populate cpu_model — Intel via sysctl, Apple Silicon via system_profiler (D-07).

    Two-branch detection based on platform.machine():
    - x86_64 (Intel): sysctl -n machdep.cpu.brand_string
    - arm64 (Apple Silicon): system_profiler SPHardwareDataType -json
      key chain: hw.get("chip_type") or hw.get("cpu_type") or None

    NOTE: sysctl machdep.cpu.brand_string is Intel-specific — do NOT call on arm64
    (RESEARCH Pitfall 1). On Apple Silicon, machdep.cpu namespace may be absent.
    """
    arch = platform.machine()  # "arm64" on Apple Silicon, "x86_64" on Intel
    if arch == "x86_64":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5,
            )
            report.cpu_model = result.stdout.strip() or None
            return
        except Exception as exc:
            report.collection_errors.append(f"CPU model (sysctl) failed: {exc}")
    # Apple Silicon (arm64) — or Intel sysctl fallback:
    # system_profiler SPHardwareDataType -json key is "chip_type" on Apple Silicon
    # (e.g. "Apple M3 Pro"), "cpu_type" on Intel. Use fallback chain (RESEARCH A1).
    try:
        result = subprocess.run(
            ["system_profiler", "SPHardwareDataType", "-json"],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(result.stdout)
        hw = data["SPHardwareDataType"][0]
        report.cpu_model = hw.get("chip_type") or hw.get("cpu_type") or None
    except Exception as exc:
        report.collection_errors.append(f"CPU model (system_profiler) failed: {exc}")


def _collect_memory_and_disk(report: AuditReport) -> None:
    """Populate ram_gb, disk_total_gb, disk_free_gb via psutil (D-08, D-09).

    RAM collection never fails at standard user privilege — no try/except.
    Disk is wrapped because unusual configurations can cause errors.
    Uses '/' (root partition on macOS), not 'C:\\' (Windows-only).
    """
    # RAM — always works at standard user privilege
    report.ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    # Disk — target "/" root partition on macOS
    try:
        disk = psutil.disk_usage("/")
        report.disk_total_gb = round(disk.total / (1024 ** 3), 1)
        report.disk_free_gb = round(disk.free / (1024 ** 3), 1)
    except Exception as exc:
        report.collection_errors.append(f"Disk usage collection failed: {exc}")


def _collect_current_user(report: AuditReport) -> None:
    """Populate current_user from macOS session environment variables (D-10).

    os.environ.get() never raises. Mac uses USER env var (not USERNAME).
    Falls back to None if both env vars absent.
    """
    report.current_user = os.environ.get("USER") or os.environ.get("USERNAME") or None


def _collect_uptime(report: AuditReport) -> None:
    """Populate uptime_seconds via psutil.boot_time(). Never raises (D-05)."""
    try:
        report.uptime_seconds = int(time.time() - psutil.boot_time())
    except Exception as exc:
        report.collection_errors.append(f"Uptime collection failed: {exc}")


# ---------------------------------------------------------------------------
# Private helpers — profiles
# ---------------------------------------------------------------------------

def _enumerate_profiles() -> list[str]:
    """Return list of human account usernames (UID >= 501) from pwd database (D-11).

    macOS assigns UID 501 to the first human account created during setup.
    UIDs below 501 are reserved for system accounts (root=0, daemon=1, etc.).

    Raises RuntimeError if pwd module not available (Windows CI guard).
    Raises if pwd.getpwall() raises — the caller (collect_profiles) catches this
    and logs to collection_errors.
    """
    if not _PWD_AVAILABLE or _pwd_module is None:
        raise RuntimeError("pwd module not available on this platform")
    profiles: list[str] = []
    for entry in _pwd_module.getpwall():
        if entry.pw_uid >= 501:
            profiles.append(entry.pw_name)
    return profiles
