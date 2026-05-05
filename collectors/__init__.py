"""Collector orchestration. Selects platform implementation.
Phase 2: Windows implementation only. Mac stubs reserved for v2.
collect_all(report) is the single entry point called by main.py (Phase 3 wiring).
"""
from __future__ import annotations
from models import AuditReport


def collect_all(report: AuditReport) -> None:
    """Run all collectors in order. Mutates report in place. Never raises.

    Calls collect_hardware first (OS, CPU, RAM, disk, current user),
    then collect_profiles (local user profiles from registry),
    then collect_apps (installed application detection).
    All functions degrade gracefully — collection_errors accumulates failures.
    """
    from collectors.windows.hardware import collect_hardware, collect_profiles
    from collectors.windows.apps import collect_apps
    collect_hardware(report)
    collect_profiles(report)
    collect_apps(report)
