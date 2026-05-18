"""Collector orchestration. Selects platform implementation.
Phase 10: darwin → collectors.mac; anything else → collectors.windows.
collect_all(report) is the single entry point called by main.py.
"""
from __future__ import annotations
from models import AuditReport


def collect_all(report: AuditReport) -> None:
    """Run all collectors in order. Mutates report in place. Never raises.

    Platform dispatch: darwin → collectors.mac; anything else → collectors.windows.
    Imports are lazy inside the function body so this module is importable on
    non-native platforms (e.g. mac module importable on Windows CI).
    Phase 13: collect_pending_updates is called on Windows path only (WUA is Windows-only).
    All functions degrade gracefully — collection_errors accumulates failures.
    """
    import sys
    if sys.platform == "darwin":
        from collectors.mac.hardware import collect_hardware, collect_profiles
        from collectors.mac.apps import collect_apps
        collect_hardware(report)
        collect_profiles(report)
        collect_apps(report)
    else:
        from collectors.windows.hardware import collect_hardware, collect_profiles, collect_pending_updates
        from collectors.windows.apps import collect_apps
        collect_hardware(report)
        collect_profiles(report)
        collect_apps(report)
        collect_pending_updates(report)
