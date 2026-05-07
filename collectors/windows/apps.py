"""Windows application detection collector.
Implements APP-01 through APP-07: detects 7 target applications via registry
enumeration across all 4 Uninstall key paths, filesystem fallback (MERP),
MSIX detection (Claude), and service state read (CrowdStrike).

All detection runs per-app. Never raises across the layer boundary — each app's
exceptions are caught individually and appended to report.collection_errors (D-16).
"""
from __future__ import annotations

import json
import os
import winreg
from pathlib import Path

from models import AuditReport, AppStatus

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

UNINSTALL_PATHS: list[tuple[int, str]] = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
]

_START_MAP: dict[int, str] = {2: "Automatic", 3: "Manual", 4: "Disabled"}

_MSIX_REPO_PATH = (
    r"Software\Classes\Local Settings\Software\Microsoft\Windows"
    r"\CurrentVersion\AppModel\Repository\Packages"
)

# ---------------------------------------------------------------------------
# APP_SPECS — config-driven detection table (D-10, D-13)
#
# Each entry declares:
#   name                  (str)       — AppStatus.name value
#   display_name_keywords (list[str]) — substring keywords matched against DisplayName
#   service_key           (str)       — optional; read HKLM Services\{key}\Start DWORD
#   filesystem_path       (str)       — optional; primary check via Path.exists()
#   msix_family_prefix    (str)       — optional; primary check via AppModel repository
#
# Keyword notes (from RESEARCH.md verified registry data):
#   CrowdStrike: MUST use "CrowdStrike Windows Sensor" / "CrowdStrike Sensor Platform"
#                — NOT "CrowdStrike Falcon" (Pitfall 1: not in live registry)
#   Zoom:        "Zoom Workplace" listed first — avoids matching "Zoom Outlook Plugin"
#                (Pitfall 2); plain "Zoom" is fallback for pre-rebranding installs
#   Claude:      msix_family_prefix is primary — MSIX apps are NOT in Uninstall keys
#                (Pitfall 3); display_name_keywords is fallback only
# ---------------------------------------------------------------------------

APP_SPECS: list[dict] = [
    {
        "name": "NinjaOne",
        "display_name_keywords": ["NinjaRMMAgent", "NinjaRMM", "NinjaOne Agent"],
    },
    {
        "name": "CrowdStrike Falcon",
        "display_name_keywords": ["CrowdStrike Windows Sensor", "CrowdStrike Sensor Platform"],
        "service_key": "CSFalconService",
    },
    {
        "name": "MERP",
        "display_name_keywords": ["WindX", "PVX Plus Technologies"],
        "filesystem_path": r"C:/PVX Plus Technologies/WindX Plugin-64 2022 Upd 1/WindX",
    },
    {
        "name": "Microsoft 365",
        "display_name_keywords": ["Microsoft 365", "Microsoft Office"],
    },
    {
        "name": "Zoom Workplace",
        "display_name_keywords": ["Zoom Workplace", "Zoom"],
        "display_name_excludes": ["Outlook Plugin"],
    },
    {
        "name": "Google Chrome",
        "display_name_keywords": ["Google Chrome"],
    },
    {
        "name": "Claude",
        "display_name_keywords": ["Claude"],
        "msix_family_prefix": "Claude_",
        "sub_apps": [
            {"name": "Claude Code", "npm_global_package": "@anthropic-ai/claude-code"},
            {"name": "Node.js", "display_name_keywords": ["Node.js"]},
        ],
    },
]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _search_uninstall_keys(
    keywords: list[str],
    excludes: list[str] | None = None,
) -> tuple[bool, str | None]:
    """Return (installed, version) for the first Uninstall subkey whose
    DisplayName contains any of *keywords* (case-insensitive substring)
    and none of *excludes* (also case-insensitive substring).

    Iterates all 4 UNINSTALL_PATHS. First match across all paths wins and
    returns immediately — no duplicate AppStatus entries (D-14, Pitfall 5).
    Unreadable root keys and subkeys are silently skipped (mirrors hardware.py).
    Returns (False, None) if all paths are exhausted with no match.
    """
    _excludes = [e.lower() for e in excludes] if excludes else []
    for hive, path in UNINSTALL_PATHS:
        try:
            with winreg.OpenKey(hive, path) as root:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root, i)
                        i += 1
                    except OSError:
                        break  # EnumKey raises OSError when index exhausted — normal end
                    try:
                        with winreg.OpenKey(root, subkey_name) as subkey:
                            display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            dn_lower = display_name.lower()
                            if any(kw.lower() in dn_lower for kw in keywords):
                                if any(ex in dn_lower for ex in _excludes):
                                    continue  # Excluded match (e.g. Zoom Outlook Plugin)
                                try:
                                    version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                                except (FileNotFoundError, OSError):
                                    version = None
                                return True, version
                    except (FileNotFoundError, OSError):
                        continue  # Skip unreadable subkey silently (mirrors hardware.py:152)
        except (FileNotFoundError, OSError):
            continue  # Path not present on this machine
    return False, None


def _read_service_start(service_name: str) -> str | None:
    """Return the start-type string for *service_name* from the Windows service registry.

    Opens HKLM\\SYSTEM\\CurrentControlSet\\Services\\{service_name}, reads the
    Start DWORD, and maps it via _START_MAP: 2→"Automatic", 3→"Manual",
    4→"Disabled". Returns None if the key is absent, unreadable, or the value
    does not map (D-08, D-09).
    """
    key_path = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            val, _ = winreg.QueryValueEx(key, "Start")
            return _START_MAP.get(int(val))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return None


def _detect_msix(family_prefix: str) -> tuple[bool, str | None]:
    """Return (installed, version) for an MSIX package matching *family_prefix*.

    Enumerates HKCU AppModel Repository\\Packages. Key names follow the pattern:
    {FamilyName}_{Version}_{arch}__{PublisherHash}. If any key name starts with
    *family_prefix*, splits on "_" and returns (True, parts[1]) as the version.
    Returns (False, None) if the repository path is absent or no key matches.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _MSIX_REPO_PATH) as root:
            i = 0
            while True:
                try:
                    pkg_key_name = winreg.EnumKey(root, i)
                    i += 1
                except OSError:
                    break  # EnumKey raises OSError when index exhausted — normal end
                if pkg_key_name.startswith(family_prefix):
                    parts = pkg_key_name.split("_")
                    version = parts[1] if len(parts) >= 2 else None
                    return True, version
    except (FileNotFoundError, OSError):
        pass
    return False, None


def _detect_npm_global(package: str) -> tuple[bool, str | None]:
    """Return (installed, version) for an npm global package.

    Checks %APPDATA%\\npm\\node_modules\\{package}\\package.json and reads
    the 'version' key. Scoped packages (e.g. '@scope/name') are split on '/'
    into separate path segments. Returns (False, None) if APPDATA is absent,
    the path does not exist, or the JSON is malformed.
    """
    appdata = os.environ.get('APPDATA')
    if not appdata:
        return False, None
    package_json = Path(appdata).joinpath(
        'npm', 'node_modules', *package.split('/'), 'package.json'
    )
    try:
        if not package_json.exists():
            return False, None
        data = json.loads(package_json.read_text(encoding='utf-8'))
        return True, data.get('version')
    except (OSError, ValueError):
        return False, None


def _detect_sub_app(spec: dict) -> AppStatus:
    """Run detection for a sub-app spec and return an AppStatus (no side effects).

    Supports two detection methods:
    - npm_global_package: filesystem check via %APPDATA%\\npm\\node_modules\\{pkg}\\package.json
    - display_name_keywords: standard 4-path Uninstall registry sweep
    """
    installed = False
    version: str | None = None
    detection_method = 'registry'

    if 'npm_global_package' in spec:
        installed, version = _detect_npm_global(spec['npm_global_package'])
        detection_method = 'filesystem'
    elif 'display_name_keywords' in spec:
        _excludes = spec.get('display_name_excludes')
        installed, version = _search_uninstall_keys(spec['display_name_keywords'], _excludes)

    return AppStatus(
        name=spec['name'],
        installed=installed,
        version=version,
        detection_method=detection_method,
    )


def _detect_one_app(spec: dict, report: AuditReport) -> None:
    """Run detection logic for a single app spec and append one AppStatus to report.apps.

    Detection precedence (D-02, D-03, D-07, D-08, D-11):
    1. MSIX detection first if msix_family_prefix present (Claude; Pitfall 3)
    2. Filesystem check if filesystem_path present and not yet installed (MERP; D-02)
       — on filesystem hit, also searches registry for version only (D-03)
    3. Standard 4-path Uninstall registry sweep if still not installed
    4. Service state read if installed and service_key present (CrowdStrike; D-08)

    Never raises — caller (detect_apps) wraps in try/except.
    """
    installed = False
    version: str | None = None
    service_state: str | None = None
    detection_method = "registry"

    # Step 1: MSIX detection (primary for Claude; standard keyword sweep is fallback)
    if "msix_family_prefix" in spec:
        msix_found, msix_version = _detect_msix(spec["msix_family_prefix"])
        if msix_found:
            installed = True
            version = msix_version
            # detection_method stays 'registry' — MSIX repo is still a registry path

    _excludes = spec.get("display_name_excludes")

    # Step 2: Filesystem check (primary for MERP; D-02)
    if not installed and "filesystem_path" in spec:
        if Path(spec["filesystem_path"]).exists():
            installed = True
            detection_method = "filesystem"
            # Attempt registry search for version only (D-03); ignore installed bool
            _, reg_version = _search_uninstall_keys(spec["display_name_keywords"], _excludes)
            version = reg_version  # None is acceptable if registry has no entry

    # Step 3: Standard Uninstall registry sweep (all other apps + fallbacks)
    if not installed:
        reg_found, reg_version = _search_uninstall_keys(spec["display_name_keywords"], _excludes)
        if reg_found:
            installed = True
            version = reg_version
            detection_method = "registry"

    # Step 4: Service state read (CrowdStrike; D-08)
    if installed and "service_key" in spec:
        service_state = _read_service_start(spec["service_key"])

    # Step 5: Sub-app detection — generic, per-spec, never raises (D-16 extended)
    sub_apps: list[AppStatus] = []
    for sub_spec in spec.get('sub_apps', []):
        try:
            sub_apps.append(_detect_sub_app(sub_spec))
        except Exception:
            pass  # Sub-app failure is silently swallowed; parent entry is still recorded

    report.apps.append(AppStatus(
        name=spec["name"],
        installed=installed,
        version=version,
        service_state=service_state,
        detection_method=detection_method,
        sub_apps=sub_apps,
    ))


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def detect_apps(report: AuditReport) -> None:
    """Populate report.apps with one AppStatus per target application.

    Iterates APP_SPECS. Each app's detection is wrapped in its own try/except
    so a failure in one app never blocks detection of subsequent apps (D-16).
    On exception: appends error message to report.collection_errors AND appends
    AppStatus(installed=False, error=...) to report.apps to preserve D-15
    (every app always produces one entry, even under failure).
    """
    for spec in APP_SPECS:
        try:
            _detect_one_app(spec, report)
        except Exception as exc:
            report.collection_errors.append(
                f"App detection failed for {spec['name']}: {exc}"
            )
            report.apps.append(AppStatus(
                name=spec["name"],
                installed=False,
                error=str(exc),
            ))


def collect_apps(report: AuditReport) -> None:
    """Public entry point for app detection. Calls detect_apps(report).

    This is what collectors/__init__.py imports and calls from collect_all()
    after collect_hardware and collect_profiles (D-12). Never raises.
    """
    detect_apps(report)
