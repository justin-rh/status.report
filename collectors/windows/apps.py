"""Windows application detection collector.
Detects 9 target applications via registry enumeration across all 4 Uninstall
key paths, filesystem fallback (MERP, Office), MSIX detection (Claude, Company Portal),
Chrome extension filesystem check (Keeper), service state read (CrowdStrike), and
MDM enrollment detection (Company Portal / Intune).

All detection runs per-app. Never raises across the layer boundary — each app's
exceptions are caught individually and appended to report.collection_errors (D-16).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
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
#   sub_apps              (list[dict]) — optional child entries (same spec keys apply)
#
# Sub-app detection keys (first matching key wins):
#   npm_global_package    (str)       — path via npm global node_modules + package.json
#   chrome_extension_id   (str)       — path via %LOCALAPPDATA%\Google\Chrome\...\Extensions\{id}
#   filesystem_path       (str)       — Path.exists() only; version is always None
#   display_name_keywords (list[str]) — standard 4-path Uninstall registry sweep
#
# Keyword notes (from RESEARCH.md verified registry data):
#   CrowdStrike: MUST use "CrowdStrike Windows Sensor" / "CrowdStrike Sensor Platform"
#                — NOT "CrowdStrike Falcon" (Pitfall 1: not in live registry)
#   Zoom:        "Zoom Workplace" listed first — avoids matching "Zoom Outlook Plugin"
#                (Pitfall 2); plain "Zoom" is fallback for pre-rebranding installs
#   Claude:      msix_family_prefix is primary — MSIX apps are NOT in Uninstall keys
#                (Pitfall 3); display_name_keywords is fallback only
#   Office apps: filesystem_path used — C2R installs don't register individual apps
#                in standard Uninstall keys; version is None (exe exists = installed)
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
        "name": "Zscaler",
        "display_name_keywords": ["Zscaler Client Connector", "Zscaler"],
    },
    {
        "name": "MERP",
        "display_name_keywords": ["WindX", "PVX Plus Technologies"],
        "filesystem_path": r"C:/PVX Plus Technologies/WindX Plugin-64 2022 Upd 1/WindX",
    },
    {
        "name": "Microsoft 365",
        "display_name_keywords": ["Microsoft 365", "Microsoft Office"],
        "sub_apps": [
            {"name": "Word",       "filesystem_path": r"C:/Program Files/Microsoft Office/root/Office16/WINWORD.EXE"},
            {"name": "Excel",      "filesystem_path": r"C:/Program Files/Microsoft Office/root/Office16/EXCEL.EXE"},
            {"name": "PowerPoint", "filesystem_path": r"C:/Program Files/Microsoft Office/root/Office16/POWERPNT.EXE"},
            {"name": "Outlook",    "filesystem_path": r"C:/Program Files/Microsoft Office/root/Office16/OUTLOOK.EXE"},
            {"name": "Teams",      "display_name_keywords": ["Microsoft Teams"]},
            {"name": "OneDrive",   "display_name_keywords": ["Microsoft OneDrive"]},
        ],
    },
    {
        "name": "Zoom Workplace",
        "display_name_keywords": ["Zoom Workplace", "Zoom"],
        "display_name_excludes": ["Outlook Plugin"],
        "sub_apps": [
            {"name": "Zoom Outlook Plugin", "display_name_keywords": ["Zoom Outlook Plugin"]},
        ],
    },
    {
        "name": "Google Chrome",
        "display_name_keywords": ["Google Chrome"],
        "sub_apps": [
            {"name": "Keeper", "chrome_extension_id": "bfogiafebfohielmmehodmfbbebbbpei"},
        ],
    },
    {
        "name": "Claude",
        "display_name_keywords": ["Claude"],
        "msix_family_prefix": "Claude_",
        "sub_apps": [
            {"name": "Claude Code", "npm_global_package": "@anthropic-ai/claude-code"},
            {"name": "Node.js", "path_executable": "node"},
        ],
    },
    {
        "name": "Company Portal",
        "display_name_keywords": ["Company Portal", "Microsoft Intune Company Portal"],
        "msix_family_prefix": "Microsoft.CompanyPortal_",
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


_MDM_ENROLLMENTS_PATH = r"SOFTWARE\Microsoft\Enrollments"


def _detect_mdm_enrollment() -> str | None:
    """Return 'Enrolled: {UPN}' if any GUID subkey under HKLM Enrollments has a
    non-empty UPN value, or None if the device is not enrolled or the key is absent.

    Enumerates all GUID subkeys under HKLM\\SOFTWARE\\Microsoft\\Enrollments.
    For each subkey, reads the UPN value. Returns the first non-empty UPN as
    'Enrolled: {upn}'. Stale GUIDs (missing or empty UPN) are skipped (D-06).
    Returns None on any exception — never raises across layer boundary.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _MDM_ENROLLMENTS_PATH) as root:
            i = 0
            while True:
                try:
                    guid = winreg.EnumKey(root, i)
                    i += 1
                except OSError:
                    break  # EnumKey raises OSError when index exhausted — normal end
                try:
                    with winreg.OpenKey(root, guid) as subkey:
                        upn, _ = winreg.QueryValueEx(subkey, "UPN")
                        if upn:  # Non-empty string → valid enrollment (D-06)
                            return f"Enrolled: {upn}"
                except (FileNotFoundError, OSError):
                    continue  # Stale GUID — skip silently (D-06)
    except (FileNotFoundError, OSError):
        pass  # Enrollments key absent — not enrolled
    except Exception:
        pass  # Any other failure — return None, never raise
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


def _read_npmrc_prefix() -> str | None:
    """Return the npm global prefix from %USERPROFILE%\\.npmrc, or None.

    Reads the first 'prefix=' line from the user npmrc file. Returns None if
    USERPROFILE is absent, the file does not exist, or no prefix line is found.
    """
    userprofile = os.environ.get('USERPROFILE')
    if not userprofile:
        return None
    npmrc = Path(userprofile).joinpath('.npmrc')
    try:
        for line in npmrc.read_text(encoding='utf-8').splitlines():
            if line.startswith('prefix='):
                return line[len('prefix='):].strip()
    except (OSError, ValueError):
        pass
    return None


def _detect_npm_global(package: str) -> tuple[bool, str | None]:
    """Return (installed, version) for an npm global package.

    Probes node_modules under the npm global prefix, in order:
    1. prefix from %USERPROFILE%\\.npmrc (user-configured custom prefix)
    2. %APPDATA%\\npm (Windows npm default)

    Scoped packages (e.g. '@scope/name') are split on '/' into separate path
    segments. Returns (False, None) if no prefix is found, the package path does
    not exist, or the JSON is malformed.
    """
    candidates: list[Path] = []

    prefix = _read_npmrc_prefix()
    if prefix:
        candidates.append(Path(prefix).joinpath('node_modules'))

    appdata = os.environ.get('APPDATA')
    if appdata:
        candidates.append(Path(appdata).joinpath('npm', 'node_modules'))

    parts = package.split('/')
    for node_modules in candidates:
        package_json = node_modules.joinpath(*parts, 'package.json')
        try:
            if not package_json.exists():
                continue
            data = json.loads(package_json.read_text(encoding='utf-8'))
            return True, data.get('version')
        except (OSError, ValueError):
            continue

    return False, None


def _detect_path_executable(executable: str) -> tuple[bool, str | None]:
    """Return (installed, version) by locating *executable* in PATH.

    Uses shutil.which() so it works regardless of install method (standard
    installer, nvm, chocolatey, winget, etc.). Runs '{exe} --version' with a
    5-second timeout to read the version string; strips a leading 'v' prefix.
    Returns (True, None) if the exe is found but the version call fails.
    """
    exe_path = shutil.which(executable)
    if not exe_path:
        return False, None
    try:
        result = subprocess.run(
            [exe_path, '--version'],
            capture_output=True, text=True, timeout=5,
        )
        raw = (result.stdout.strip() or result.stderr.strip())
        return True, raw.lstrip('v') if raw else None
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        return True, None


def _detect_chrome_extension(extension_id: str) -> tuple[bool, str | None]:
    """Return (installed, version) for a Chrome extension by ID.

    Checks %LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Extensions\\{id}\\ and
    reads 'version' from the manifest.json in the first versioned subdirectory.
    Returns (False, None) if LOCALAPPDATA is absent or the extension directory does
    not exist. Returns (True, None) if the directory exists but version is unreadable.
    """
    localappdata = os.environ.get('LOCALAPPDATA')
    if not localappdata:
        return False, None
    ext_dir = Path(localappdata).joinpath(
        'Google', 'Chrome', 'User Data', 'Default', 'Extensions', extension_id
    )
    if not ext_dir.exists():
        return False, None
    try:
        for version_dir in ext_dir.iterdir():
            manifest = version_dir.joinpath('manifest.json')
            if manifest.exists():
                data = json.loads(manifest.read_text(encoding='utf-8'))
                return True, data.get('version')
    except (OSError, ValueError):
        pass
    return True, None


def _detect_sub_app(spec: dict) -> AppStatus:
    """Run detection for a sub-app spec and return an AppStatus (no side effects).

    Supported detection methods (first matching key wins):
    - npm_global_package:    npm global node_modules filesystem check
    - chrome_extension_id:   Chrome extension directory filesystem check
    - filesystem_path:       Path.exists() only; version is always None
    - display_name_keywords: standard 4-path Uninstall registry sweep
    """
    installed = False
    version: str | None = None
    detection_method = 'registry'

    if 'npm_global_package' in spec:
        installed, version = _detect_npm_global(spec['npm_global_package'])
        detection_method = 'filesystem'
    elif 'path_executable' in spec:
        installed, version = _detect_path_executable(spec['path_executable'])
        detection_method = 'filesystem'
    elif 'chrome_extension_id' in spec:
        installed, version = _detect_chrome_extension(spec['chrome_extension_id'])
        detection_method = 'filesystem'
    elif 'filesystem_path' in spec:
        installed = Path(spec['filesystem_path']).exists()
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

    # Step 4b: MDM enrollment check (Company Portal only — D-01, D-03, D-09)
    # Runs unconditionally: enrollment is readable under SYSTEM even when HKCU is absent.
    if spec.get("name") == "Company Portal":
        service_state = _detect_mdm_enrollment()

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
