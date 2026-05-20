"""Windows vendor update detection collector.
Detects Dell Command Update and Lenovo System Update installation status.
Reads pending update count passively from DCUApplicableUpdates.xml (never invokes CLI).
Never raises across the layer boundary — errors appended to report.collection_errors (D-03).
Phase 14.
"""
from __future__ import annotations

import sys
import winreg
import xml.etree.ElementTree as ET
from pathlib import Path

from models import AuditReport, VendorUpdateStatus
from collectors.windows.apps import UNINSTALL_PATHS, _search_uninstall_keys

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
        # Lenovo updater family keyword list — formalized in Phase 17 D-10
        # (canonical: any of the 4 matching keywords means installed=True).
        #
        # Edgar-confirmed entries (Phase 17 D-09, evidence in
        # .planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md):
        #   - "Lenovo Vantage"
        #   - "Lenovo Commercial Vantage"
        #
        # defensive entries — kept for older / mixed-fleet machines, NOT
        # Edgar-confirmed against current fleet (Phase 17 D-09):
        #   - "Lenovo System Update"   (retroactively amends Phase 14 D-13)
        #   - "Lenovo Vantage Service"
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


def diag_vendor_paths(stream=None) -> None:
    """Diagnostic dump of Dell/Lenovo Uninstall entries + DCU XML state.

    Used by --diag-vendor (main.py). Reuses UNINSTALL_PATHS so Edgar sees
    what the production _search_uninstall_keys sees (D-01).

    Walks all 4 hives, surfaces every subkey whose DisplayName contains
    'dell' or 'lenovo' (case-insensitive substring) — D-02. Then probes
    DCU_XML_PATH (existence, size, <update> element count) — D-03.

    Never raises; per-hive failures print a one-line note (D-04, PATTERNS
    section "Never raise across the layer boundary"). Writes to `stream`
    (default sys.stdout); caller controls redirection (--diag-vendor
    short-circuits before any file output — see main.py).

    NO subprocess invocation. NO writes to host PC. Registry + file
    passive reads only (CLAUDE.md, PROJECT.md standing constraints).
    """
    if stream is None:
        stream = sys.stdout

    def _hive_label(hive: int, path: str) -> str:
        root = "HKLM" if hive == winreg.HKEY_LOCAL_MACHINE else "HKCU"
        if "WOW6432Node" in path:
            return rf"{root}\Wow6432Node"
        return root

    print("=== SCRY --diag-vendor — Dell/Lenovo Uninstall entries ===", file=stream)
    any_match = False
    for hive, path in UNINSTALL_PATHS:
        label = _hive_label(hive, path)
        print(f"\n[hive] {label}", file=stream)
        try:
            with winreg.OpenKey(hive, path) as root_key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root_key, i)
                        i += 1
                    except OSError:
                        break  # exhausted (matches _search_uninstall_keys pattern)
                    try:
                        with winreg.OpenKey(root_key, subkey_name) as subkey:
                            try:
                                display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            except (FileNotFoundError, OSError):
                                continue
                            dn_lower = display_name.lower()
                            if "dell" not in dn_lower and "lenovo" not in dn_lower:
                                continue
                            try:
                                display_version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                            except (FileNotFoundError, OSError):
                                display_version = "(none)"
                            try:
                                install_location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                            except (FileNotFoundError, OSError):
                                install_location = "(none)"
                            any_match = True
                            print(f"  DisplayName:     {display_name}", file=stream)
                            print(f"  DisplayVersion:  {display_version}", file=stream)
                            print(f"  InstallLocation: {install_location}", file=stream)
                            print(f"  (subkey: {subkey_name})", file=stream)
                    except (FileNotFoundError, OSError):
                        continue
        except (FileNotFoundError, OSError):
            print(f"  [note] hive unreadable — skipped", file=stream)
            continue
        except Exception as exc:
            print(f"  [note] hive enumeration error: {exc} — skipped", file=stream)
            continue

    if not any_match:
        print(
            "\n(no matching entries — no Dell or Lenovo Uninstall subkeys found across all 4 hives)",
            file=stream,
        )

    print("\n=== DCU XML probe ===", file=stream)
    print(f"DCU_XML_PATH: {DCU_XML_PATH}", file=stream)
    try:
        p = Path(DCU_XML_PATH)
        exists = p.exists()
        print(f"exists={exists}", file=stream)
        if exists:
            try:
                size = p.stat().st_size
                print(f"size={size} bytes", file=stream)
            except OSError as exc:
                print(f"size=unknown ({exc})", file=stream)
            try:
                root_el = ET.parse(p).getroot()
                count = len(root_el.findall("update"))
                print(f"update count: {count}", file=stream)
            except ET.ParseError as exc:
                print(f"update count: unparseable ({exc})", file=stream)
    except Exception as exc:
        print(f"[note] DCU XML probe error: {exc}", file=stream)
