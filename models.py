"""SCRY data contract. All layers import from this module.
ROADMAP SC5: AuditReport, ParsedHostname, AppStatus, CollectionResult importable here.
Phase 13: Warning.level field added (D-01); AuditReport.uptime_seconds and .pending_updates added (D-04).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar('T')


@dataclass
class CollectionResult(Generic[T]):
    """Error envelope for all collector return values.
    Never raise across layer boundaries — return CollectionResult instead.
    """
    value: T | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return not self.error


@dataclass
class ParsedHostname:
    """Decoded Master Electronics hostname.
    All fields except raw_hostname are None if parsing fails (D-08).
    """
    raw_hostname: str               # Always preserved (D-05)
    city: str | None = None         # Full city name (e.g., "Phoenix") or None (D-04)
    device_type: str | None = None  # One of four types or "Unknown"
    department: str | None = None   # Warehouse dept code; preserved even if unrecognized (D-02)
    company_code: str | None = None # Laptop company code; preserved even if unrecognized (D-03)
    station: int | None = None      # Station number as int (e.g., 3 not '003')


@dataclass
class AppStatus:
    """Detection result for a single target application."""
    name: str
    installed: bool
    version: str | None = None
    service_state: str | None = None    # 'Running' | 'Stopped' | None
    detection_method: str = 'registry'  # 'registry' | 'filesystem' | 'service'
    error: str | None = None
    sub_apps: list[AppStatus] = field(default_factory=list)


@dataclass
class Warning:
    """A single health check result produced by evaluate_warnings()."""
    code: str           # Short identifier: 'OS_VERSION' | 'DISK_SPACE'
    severity: str       # 'OK' or 'WARN' — plain str per D-03
    message: str        # Human-readable one-line summary
    detail: str | None = None  # Extended info or skip reason; None when not needed
    level: str | None = None   # 'yellow' | 'red' | None — D-01 (Phase 13)


@dataclass
class AuditReport:
    """The single normalized data container passed between all layers."""
    hostname: str
    parsed_hostname: ParsedHostname
    # Hardware — populated by Phase 2 collectors
    os_version: str | None = None
    os_build: str | None = None
    serial_number: str | None = None
    cpu_model: str | None = None
    ram_gb: float | None = None
    disk_total_gb: float | None = None
    disk_free_gb: float | None = None
    current_user: str | None = None
    # System health — populated by Phase 13 collectors
    uptime_seconds: int | None = None    # seconds since last reboot; None if collection fails (D-04/D-05)
    pending_updates: int | None = None   # Windows update count from WUA COM; None when inaccessible (D-04/D-08)
    local_profiles: list[str] = field(default_factory=list)
    # Apps — populated by Phase 4
    apps: list[AppStatus] = field(default_factory=list)
    # Error accumulation — never raises; collectors populate this list
    collection_errors: list[str] = field(default_factory=list)
    # Health checks — populated by Phase 6
    warnings: list[Warning] = field(default_factory=list)
    timestamp: str = ''
