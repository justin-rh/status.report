"""Windows vendor update detection collector.
Detects Dell Command Update and Lenovo System Update installation status.
Reads pending update count passively from DCUApplicableUpdates.xml (never invokes CLI).
Never raises across the layer boundary — errors appended to report.collection_errors (D-03).
Phase 14.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from models import AuditReport, VendorUpdateStatus
from collectors.windows.apps import _search_uninstall_keys

# Fixed path per D-11. Never written; only read if present.
DCU_XML_PATH = r"C:\ProgramData\Dell\UpdateService\Temp\DCUApplicableUpdates.xml"


def collect_vendor_updates(report: AuditReport) -> None:
    """Populate report.dell_dcu and report.lenovo_lsu in place.

    Called only when --updates is passed (main.py, D-04). Never raises (D-03).
    Errors set fields to safe defaults and append to report.collection_errors.
    """
    _detect_dcu(report)
    _detect_lsu(report)


def _detect_dcu(report: AuditReport) -> None:
    """Detect Dell Command Update via registry; read pending count from XML if present."""
    try:
        installed, _version = _search_uninstall_keys(
            ["Dell Command Update", "Dell Command | Update"]
        )
        pending_count: int | None = None
        scan_data_present = False

        if installed:
            p = Path(DCU_XML_PATH)
            if p.exists():
                try:
                    root = ET.parse(p).getroot()
                    # Root element: <updates>, direct children: <update> per D-12 / RESEARCH.md
                    pending_count = len(root.findall("update"))
                    scan_data_present = True
                except ET.ParseError:
                    # File present but malformed (e.g. partial write during DCU scan)
                    scan_data_present = True
                    pending_count = None

        report.dell_dcu = VendorUpdateStatus(
            installed=installed,
            pending_count=pending_count,
            scan_data_present=scan_data_present,
        )
    except Exception as exc:
        report.collection_errors.append(f"DCU detection failed: {exc}")
        report.dell_dcu = VendorUpdateStatus(
            installed=None, pending_count=None, scan_data_present=False
        )


def _detect_lsu(report: AuditReport) -> None:
    """Detect Lenovo System Update via registry. No passive count source in v3.0 (D-14)."""
    try:
        installed, _version = _search_uninstall_keys([
            "Lenovo System Update",
            "Lenovo Vantage Service",
            "Lenovo Vantage",
            "Lenovo Commercial Vantage",
        ])
        report.lenovo_lsu = VendorUpdateStatus(
            installed=installed,
            pending_count=None,        # D-14: no passive source
            scan_data_present=False,   # D-14: always False for LSU
        )
    except Exception as exc:
        report.collection_errors.append(f"LSU detection failed: {exc}")
        report.lenovo_lsu = VendorUpdateStatus(
            installed=None, pending_count=None, scan_data_present=False
        )
