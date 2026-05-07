"""Unit tests for collectors.windows.apps — collect_apps / detect_apps functions.

Mock pattern: patch.object(apps_mod.winreg, ...) patches the winreg reference
inside apps.py itself, not the stdlib module globally. This ensures no real
registry calls occur in CI.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname
import collectors.windows.apps as apps_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_report() -> AuditReport:
    return AuditReport(hostname="TEST-PC", parsed_hostname=parse_hostname("TEST-PC"))


def _make_fake_ctx() -> MagicMock:
    """Return a MagicMock that acts as a winreg key context manager."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _make_enum_fn(subkeys: list[str]):
    """Return an EnumKey side_effect that yields subkeys by index then raises OSError."""
    def enum_fn(key, index):
        if index < len(subkeys):
            return subkeys[index]
        raise OSError("exhausted")
    return enum_fn


def _make_query_fn(display_name: str, display_version: str | None = None):
    """Return a QueryValueEx side_effect for a single app subkey."""
    def query_fn(key, value_name):
        if value_name == "DisplayName":
            return (display_name, 1)
        if value_name == "DisplayVersion" and display_version is not None:
            return (display_version, 1)
        raise FileNotFoundError(f"no value {value_name!r}")
    return query_fn


# ---------------------------------------------------------------------------
# Test: registry hit — NinjaOne installed
# ---------------------------------------------------------------------------

def test_detect_ninjaone_installed():
    """Registry subkey with NinjaRMMAgent DisplayName → NinjaOne installed=True, version set."""
    subkeys = ["NinjaRMMAgent 5.8.9154"]
    fake_ctx = _make_fake_ctx()

    with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=_make_enum_fn(subkeys)), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=_make_query_fn("NinjaRMMAgent", "13.0.7346")):
        report = make_report()
        apps_mod.collect_apps(report)

    ninja = next(a for a in report.apps if a.name == "NinjaOne")
    assert ninja.installed is True
    assert ninja.version == "13.0.7346"
    assert ninja.detection_method == "registry"


# ---------------------------------------------------------------------------
# Test: registry miss — all apps not installed
# ---------------------------------------------------------------------------

def test_detect_app_registry_miss():
    """OpenKey raises OSError for all paths + Path.exists()=False → all 9 apps installed=False."""
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no registry")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)

    assert len(report.apps) == 9
    for app in report.apps:
        assert app.installed is False, f"{app.name} should be installed=False"


# ---------------------------------------------------------------------------
# Test: MERP filesystem detection — primary path, no registry
# ---------------------------------------------------------------------------

def test_merp_filesystem_primary():
    """MERP detected via filesystem path → installed=True, detection_method='filesystem'."""
    with patch("collectors.windows.apps.Path") as mock_path, \
         patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no reg")):
        mock_path.return_value.exists.return_value = True
        report = make_report()
        apps_mod.collect_apps(report)

    merp = next(a for a in report.apps if a.name == "MERP")
    assert merp.installed is True
    assert merp.detection_method == "filesystem"


# ---------------------------------------------------------------------------
# Test: MERP filesystem + registry version
# ---------------------------------------------------------------------------

def test_merp_filesystem_with_registry_version():
    """MERP filesystem hit + registry returns WindX version → installed, version populated."""
    subkeys = ["WindX 1.2.3"]
    fake_ctx = _make_fake_ctx()

    with patch("collectors.windows.apps.Path") as mock_path, \
         patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=_make_enum_fn(subkeys)), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=_make_query_fn("WindX", "1.2.3")):
        mock_path.return_value.exists.return_value = True
        report = make_report()
        apps_mod.collect_apps(report)

    merp = next(a for a in report.apps if a.name == "MERP")
    assert merp.installed is True
    assert merp.detection_method == "filesystem"
    assert merp.version == "1.2.3"


# ---------------------------------------------------------------------------
# Test: Claude MSIX detection
# ---------------------------------------------------------------------------

def test_claude_msix_detection():
    """Claude MSIX key in AppModel repo → installed=True, version from key name."""
    claude_pkg_key = "Claude_1.1617.0.0_x64__pzs8sxrjxfjjc"

    # Route OpenKey calls: the MSIX repo path gets a distinct context manager so
    # EnumKey can distinguish MSIX repo enumeration from Uninstall key enumeration.
    msix_ctx = _make_fake_ctx()   # returned only for the MSIX repo path
    other_ctx = _make_fake_ctx()  # returned for all other (Uninstall) paths

    def open_key_side(hive_or_key, path_or_subkey, *args, **kwargs):
        # Identify the MSIX repo open by its string path segment
        if isinstance(path_or_subkey, str) and "AppModel" in path_or_subkey:
            return msix_ctx
        return other_ctx

    def enum_fn(key, index):
        if key is msix_ctx:
            # MSIX repo enumeration — return the Claude package key at index 0
            if index == 0:
                return claude_pkg_key
            raise OSError("exhausted")
        # All other enumerations (Uninstall paths) → immediately exhausted
        raise OSError("exhausted")

    with patch.object(apps_mod.winreg, "OpenKey", side_effect=open_key_side), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=enum_fn), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=FileNotFoundError("no value")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    claude = next(a for a in report.apps if a.name == "Claude")
    assert claude.installed is True
    assert claude.version == "1.1617.0.0"
    assert claude.detection_method == "registry"


# ---------------------------------------------------------------------------
# Test: CrowdStrike service state — Automatic (Start DWORD = 2)
# ---------------------------------------------------------------------------

def test_crowdstrike_service_state_automatic():
    """CrowdStrike registry hit + service key Start=2 → service_state='Automatic'."""
    subkeys = ["CrowdStrike Windows Sensor"]
    fake_ctx = _make_fake_ctx()

    # We need two OpenKey behaviors:
    #   1. Uninstall path open → return fake_ctx for enumeration
    #   2. Service path open → return fake_ctx with QueryValueEx returning Start=2
    #
    # Strategy: track calls. The service key read happens after the registry sweep.
    # Use a call counter: all calls use fake_ctx, but QueryValueEx is routing-aware.

    query_call_count = [0]

    def query_fn(key, value_name):
        query_call_count[0] += 1
        if value_name == "DisplayName":
            return ("CrowdStrike Windows Sensor", 1)
        if value_name == "DisplayVersion":
            return ("7.14.17706.0", 1)
        if value_name == "Start":
            return (2, 4)  # REG_DWORD = 4
        raise FileNotFoundError(f"no value {value_name!r}")

    with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey",
                      side_effect=_make_enum_fn(subkeys)), \
         patch.object(apps_mod.winreg, "QueryValueEx", side_effect=query_fn), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    cs = next(a for a in report.apps if a.name == "CrowdStrike Falcon")
    assert cs.installed is True
    assert cs.service_state == "Automatic"


# ---------------------------------------------------------------------------
# Test: CrowdStrike service state absent — service key missing
# ---------------------------------------------------------------------------

def test_crowdstrike_service_state_none_when_key_absent():
    """CrowdStrike installed via registry but service key raises OSError → service_state=None."""
    subkeys = ["CrowdStrike Windows Sensor"]
    fake_uninstall_ctx = _make_fake_ctx()
    fake_service_ctx = _make_fake_ctx()

    open_call_count = [0]

    # Track whether we're opening a service key path
    def open_key_side(hive_or_key, path_or_subkey, *args, **kwargs):
        if isinstance(path_or_subkey, str) and "CSFalconService" in path_or_subkey:
            raise OSError("service key not found")
        return fake_uninstall_ctx

    def query_fn(key, value_name):
        if value_name == "DisplayName":
            return ("CrowdStrike Windows Sensor", 1)
        if value_name == "DisplayVersion":
            return ("7.14.17706.0", 1)
        raise FileNotFoundError(f"no value {value_name!r}")

    with patch.object(apps_mod.winreg, "OpenKey", side_effect=open_key_side), \
         patch.object(apps_mod.winreg, "EnumKey",
                      side_effect=_make_enum_fn(subkeys)), \
         patch.object(apps_mod.winreg, "QueryValueEx", side_effect=query_fn), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    cs = next(a for a in report.apps if a.name == "CrowdStrike Falcon")
    assert cs.installed is True
    assert cs.service_state is None


# ---------------------------------------------------------------------------
# Test: collect_apps never raises
# ---------------------------------------------------------------------------

def test_collect_apps_never_raises():
    """collect_apps must not propagate any exception — errors go to collection_errors."""
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=PermissionError("denied")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        try:
            report = make_report()
            apps_mod.collect_apps(report)
        except Exception as exc:
            pytest.fail(f"collect_apps raised unexpectedly: {exc}")

    # All 9 apps still present even under total registry failure
    assert len(report.apps) == 9


# ---------------------------------------------------------------------------
# Test: all 7 apps always present (D-15)
# ---------------------------------------------------------------------------

def test_all_apps_always_present():
    """D-15: every app produces one AppStatus entry even when nothing is installed."""
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no registry")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)

    app_names = [a.name for a in report.apps]
    expected_names = [
        "NinjaOne",
        "CrowdStrike Falcon",
        "Zscaler",
        "MERP",
        "Microsoft 365",
        "Zoom Workplace",
        "Google Chrome",
        "Claude",
        "Company Portal",
    ]
    for expected in expected_names:
        assert expected in app_names, f"Expected '{expected}' in report.apps but got: {app_names}"


# ---------------------------------------------------------------------------
# Tests: _detect_path_executable
# ---------------------------------------------------------------------------

def test_detect_path_executable_found():
    """node in PATH + --version succeeds → (True, version without leading 'v')."""
    mock_result = MagicMock()
    mock_result.stdout = 'v24.14.1'
    mock_result.stderr = ''

    with patch('collectors.windows.apps.shutil.which', return_value='C:\\nvm4w\\nodejs\\node.exe'), \
         patch('collectors.windows.apps.subprocess.run', return_value=mock_result):
        found, version = apps_mod._detect_path_executable('node')

    assert found is True
    assert version == '24.14.1'


def test_detect_path_executable_not_in_path():
    """node not in PATH → (False, None)."""
    with patch('collectors.windows.apps.shutil.which', return_value=None):
        found, version = apps_mod._detect_path_executable('node')

    assert found is False
    assert version is None


def test_detect_path_executable_version_timeout():
    """node in PATH but --version times out → (True, None)."""
    with patch('collectors.windows.apps.shutil.which', return_value='C:\\nvm4w\\nodejs\\node.exe'), \
         patch('collectors.windows.apps.subprocess.run',
               side_effect=__import__('subprocess').TimeoutExpired('node', 5)):
        found, version = apps_mod._detect_path_executable('node')

    assert found is True
    assert version is None


# ---------------------------------------------------------------------------
# Tests: _detect_npm_global
# ---------------------------------------------------------------------------

def test_detect_npm_global_found():
    """npm global package.json present with version → (True, version)."""
    import json as _json
    fake_data = _json.dumps({"name": "@anthropic-ai/claude-code", "version": "1.2.3"})

    with patch.dict('os.environ', {'APPDATA': 'C:\\Users\\test\\AppData\\Roaming'}), \
         patch('collectors.windows.apps.Path') as mock_path:
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.return_value = fake_data
        found, version = apps_mod._detect_npm_global('@anthropic-ai/claude-code')

    assert found is True
    assert version == '1.2.3'


def test_detect_npm_global_not_found():
    """npm global package.json absent → (False, None)."""
    with patch.dict('os.environ', {'APPDATA': 'C:\\Users\\test\\AppData\\Roaming'}), \
         patch('collectors.windows.apps.Path') as mock_path:
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        mock_path.return_value.exists.return_value = False
        found, version = apps_mod._detect_npm_global('@anthropic-ai/claude-code')

    assert found is False
    assert version is None


def test_detect_npm_global_no_prefix_source():
    """Neither APPDATA nor USERPROFILE present → (False, None) without touching filesystem."""
    env = {k: v for k, v in __import__('os').environ.items() if k not in ('APPDATA', 'USERPROFILE')}
    with patch.dict('os.environ', env, clear=True):
        found, version = apps_mod._detect_npm_global('@anthropic-ai/claude-code')

    assert found is False
    assert version is None


def test_detect_npm_global_npmrc_prefix():
    """npm global found via .npmrc custom prefix (e.g. ~/.npm-global) when APPDATA path is absent."""
    import json as _json
    fake_pkg = _json.dumps({"version": "2.0.0"})

    with patch.dict('os.environ', {'USERPROFILE': 'C:\\Users\\test', 'APPDATA': ''}), \
         patch('collectors.windows.apps._read_npmrc_prefix', return_value='C:\\Users\\test\\.npm-global'), \
         patch('collectors.windows.apps.Path') as mock_path:
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.return_value = fake_pkg
        found, version = apps_mod._detect_npm_global('@anthropic-ai/claude-code')

    assert found is True
    assert version == '2.0.0'


# ---------------------------------------------------------------------------
# Tests: Claude sub_apps
# ---------------------------------------------------------------------------

def test_claude_has_sub_apps_entries():
    """Claude AppStatus always has sub_apps list with Claude Code and Node.js entries."""
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no reg")), \
         patch('collectors.windows.apps.Path') as mock_path, \
         patch.dict('os.environ', {'APPDATA': 'C:\\fake'}):
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    claude = next(a for a in report.apps if a.name == "Claude")
    sub_names = [s.name for s in claude.sub_apps]
    assert "Claude Code" in sub_names
    assert "Node.js" in sub_names


def test_claude_code_sub_app_detected_via_npm():
    """Claude Code sub_app detected when npm package.json present."""
    import json as _json
    fake_pkg = _json.dumps({"version": "1.5.0"})

    def path_side(*args, **kwargs):
        m = MagicMock()
        m.joinpath.return_value = m
        # package.json for claude-code exists; MERP filesystem path does not
        m.exists.return_value = True
        m.read_text.return_value = fake_pkg
        return m

    with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no reg")), \
         patch('collectors.windows.apps.Path', side_effect=path_side), \
         patch.dict('os.environ', {'APPDATA': 'C:\\fake'}):
        report = make_report()
        apps_mod.collect_apps(report)

    claude = next(a for a in report.apps if a.name == "Claude")
    cc = next(s for s in claude.sub_apps if s.name == "Claude Code")
    assert cc.installed is True
    assert cc.version == "1.5.0"
    assert cc.detection_method == "filesystem"


def test_apps_without_sub_apps_spec_have_empty_list():
    """Apps with no sub_apps key in their spec produce an empty sub_apps list."""
    apps_with_sub_apps = {spec['name'] for spec in apps_mod.APP_SPECS if spec.get('sub_apps')}
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no reg")), \
         patch('collectors.windows.apps.Path') as mock_path, \
         patch.dict('os.environ', {'APPDATA': 'C:\\fake'}):
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        mock_path.return_value.exists.return_value = False
        report = make_report()
        apps_mod.collect_apps(report)

    for app in report.apps:
        if app.name not in apps_with_sub_apps:
            assert app.sub_apps == [], f"{app.name} should have no sub_apps"


# ---------------------------------------------------------------------------
# Tests: Zscaler detection
# ---------------------------------------------------------------------------

def test_zscaler_detected_via_registry():
    """Zscaler Client Connector in Uninstall registry → Zscaler installed=True."""
    subkeys = ["Zscaler Client Connector"]
    fake_ctx = _make_fake_ctx()

    with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=_make_enum_fn(subkeys)), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=_make_query_fn("Zscaler Client Connector", "4.2.0.190")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)

    zscaler = next(a for a in report.apps if a.name == "Zscaler")
    assert zscaler.installed is True
    assert zscaler.version == "4.2.0.190"


# ---------------------------------------------------------------------------
# Tests: _detect_chrome_extension
# ---------------------------------------------------------------------------

def test_detect_chrome_extension_found():
    """Chrome extension directory present with manifest → (True, version)."""
    import json as _json
    fake_manifest = _json.dumps({"name": "Keeper", "version": "16.8.0"})

    mock_manifest = MagicMock()
    mock_manifest.exists.return_value = True
    mock_manifest.read_text.return_value = fake_manifest

    mock_version_dir = MagicMock()
    mock_version_dir.joinpath.return_value = mock_manifest

    mock_ext_dir = MagicMock()
    mock_ext_dir.exists.return_value = True
    mock_ext_dir.iterdir.return_value = [mock_version_dir]

    with patch.dict('os.environ', {'LOCALAPPDATA': 'C:\\Users\\test\\AppData\\Local'}), \
         patch('collectors.windows.apps.Path') as mock_path:
        mock_path.return_value.joinpath.return_value = mock_ext_dir
        found, version = apps_mod._detect_chrome_extension('bfogiafebfohielmmehodmfbbebbbpei')

    assert found is True
    assert version == '16.8.0'


def test_detect_chrome_extension_not_found():
    """Chrome extension directory absent → (False, None)."""
    with patch.dict('os.environ', {'LOCALAPPDATA': 'C:\\Users\\test\\AppData\\Local'}), \
         patch('collectors.windows.apps.Path') as mock_path:
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        mock_path.return_value.exists.return_value = False
        found, version = apps_mod._detect_chrome_extension('bfogiafebfohielmmehodmfbbebbbpei')

    assert found is False
    assert version is None


def test_detect_chrome_extension_no_localappdata():
    """LOCALAPPDATA absent → (False, None) without touching filesystem."""
    import os as _os
    env = {k: v for k, v in _os.environ.items() if k != 'LOCALAPPDATA'}
    with patch.dict('os.environ', env, clear=True):
        found, version = apps_mod._detect_chrome_extension('bfogiafebfohielmmehodmfbbebbbpei')

    assert found is False
    assert version is None


# ---------------------------------------------------------------------------
# Tests: _detect_sub_app filesystem_path branch
# ---------------------------------------------------------------------------

def test_detect_sub_app_filesystem_path_found():
    """Sub-app with filesystem_path present → installed=True, method='filesystem', version=None."""
    with patch('collectors.windows.apps.Path') as mock_path:
        mock_path.return_value.exists.return_value = True
        result = apps_mod._detect_sub_app({
            'name': 'Word',
            'filesystem_path': r'C:/Program Files/Microsoft Office/root/Office16/WINWORD.EXE',
        })

    assert result.installed is True
    assert result.detection_method == 'filesystem'
    assert result.version is None


def test_detect_sub_app_filesystem_path_not_found():
    """Sub-app with filesystem_path absent → installed=False, method='filesystem'."""
    with patch('collectors.windows.apps.Path') as mock_path:
        mock_path.return_value.exists.return_value = False
        result = apps_mod._detect_sub_app({
            'name': 'Word',
            'filesystem_path': r'C:/Program Files/Microsoft Office/root/Office16/WINWORD.EXE',
        })

    assert result.installed is False
    assert result.detection_method == 'filesystem'


# ---------------------------------------------------------------------------
# Tests: Zoom Outlook Plugin and M365 Office sub-apps
# ---------------------------------------------------------------------------

def test_zoom_outlook_plugin_sub_app_detected():
    """Zoom Outlook Plugin in Uninstall registry → sub_app installed=True under Zoom Workplace."""
    subkeys = ["Zoom Outlook Plugin"]
    fake_ctx = _make_fake_ctx()

    with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=_make_enum_fn(subkeys)), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=_make_query_fn("Zoom Outlook Plugin", "5.17.0")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)

    zoom = next(a for a in report.apps if a.name == "Zoom Workplace")
    plugin = next(s for s in zoom.sub_apps if s.name == "Zoom Outlook Plugin")
    assert plugin.installed is True
    assert plugin.version == "5.17.0"


def test_m365_office_sub_apps_detected_via_filesystem():
    """Office executables present on disk → Word/Excel/PowerPoint/Outlook sub-apps installed=True."""
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no reg")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)

    m365 = next(a for a in report.apps if a.name == "Microsoft 365")
    sub_names = {s.name for s in m365.sub_apps}
    assert {"Word", "Excel", "PowerPoint", "Outlook", "Teams", "OneDrive"} == sub_names
    filesystem_apps = [s for s in m365.sub_apps if s.detection_method == "filesystem"]
    assert all(s.installed is True for s in filesystem_apps)


# ---------------------------------------------------------------------------
# Tests: Company Portal detection (Phase 9 — APP-V2-01)
# ---------------------------------------------------------------------------

def test_company_portal_msix_detected():
    """Company Portal MSIX key in AppModel repo → installed=True, version from key name."""
    cp_pkg_key = "Microsoft.CompanyPortal_11.5.1204.0_x64__8wekyb3d8bbwe"

    msix_ctx = _make_fake_ctx()
    other_ctx = _make_fake_ctx()

    def open_key_side(hive_or_key, path_or_subkey, *args, **kwargs):
        if isinstance(path_or_subkey, str) and "AppModel" in path_or_subkey:
            return msix_ctx
        if isinstance(path_or_subkey, str) and "Enrollments" in path_or_subkey:
            raise FileNotFoundError("no enrollments key")
        return other_ctx

    def enum_fn(key, index):
        if key is msix_ctx:
            if index == 0:
                return cp_pkg_key
            raise OSError("exhausted")
        raise OSError("exhausted")

    with patch.object(apps_mod.winreg, "OpenKey", side_effect=open_key_side), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=enum_fn), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=FileNotFoundError("no value")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)

    cp = next(a for a in report.apps if a.name == "Company Portal")
    assert cp.installed is True
    assert cp.version == "11.5.1204.0"
    assert cp.detection_method == "registry"


def test_company_portal_not_installed_but_enrolled():
    """D-01: HKCU absent (MSIX not found), HKLM Enrollments has UPN → installed=False, service_state set."""
    guid = "{12345678-1234-1234-1234-123456789012}"
    upn = "justin.rhoda@masterelectronics.com"
    enroll_root_ctx = _make_fake_ctx()
    guid_ctx = _make_fake_ctx()

    def open_key_side(hive_or_key, path_or_subkey, *args, **kwargs):
        if isinstance(path_or_subkey, str) and "AppModel" in path_or_subkey:
            raise OSError("HKCU absent — SYSTEM account")
        if isinstance(path_or_subkey, str) and "Enrollments" == path_or_subkey.split("\\")[-1]:
            return enroll_root_ctx
        if hive_or_key is enroll_root_ctx:
            return guid_ctx
        raise OSError("not found")

    def enum_fn(key, index):
        if key is enroll_root_ctx:
            if index == 0:
                return guid
            raise OSError("exhausted")
        raise OSError("exhausted")

    def query_fn(key, value_name):
        if key is guid_ctx and value_name == "UPN":
            return (upn, 1)
        raise FileNotFoundError(f"no value {value_name!r}")

    with patch.object(apps_mod.winreg, "OpenKey", side_effect=open_key_side), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=enum_fn), \
         patch.object(apps_mod.winreg, "QueryValueEx", side_effect=query_fn), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)

    cp = next(a for a in report.apps if a.name == "Company Portal")
    assert cp.installed is False
    assert cp.service_state == f"Enrolled: {upn}"


def test_company_portal_stale_guid_skipped():
    """D-06: GUID with empty UPN is skipped; second GUID with real UPN is returned."""
    guid1 = "{AAAAAA-stale}"
    guid2 = "{BBBBBB-active}"
    upn = "user@domain.com"
    enroll_root_ctx = _make_fake_ctx()
    guid1_ctx = _make_fake_ctx()
    guid2_ctx = _make_fake_ctx()

    def open_key_side(hive_or_key, path_or_subkey, *args, **kwargs):
        if isinstance(path_or_subkey, str) and "AppModel" in path_or_subkey:
            raise OSError("HKCU absent")
        if hive_or_key is enroll_root_ctx and path_or_subkey == guid1:
            return guid1_ctx
        if hive_or_key is enroll_root_ctx and path_or_subkey == guid2:
            return guid2_ctx
        if isinstance(path_or_subkey, str) and "Enrollments" in path_or_subkey:
            return enroll_root_ctx
        raise OSError("not found")

    def enum_fn(key, index):
        if key is enroll_root_ctx:
            guids = [guid1, guid2]
            if index < len(guids):
                return guids[index]
            raise OSError("exhausted")
        raise OSError("exhausted")

    def query_fn(key, value_name):
        if value_name == "UPN":
            if key is guid1_ctx:
                return ("", 1)          # Empty string → stale (D-06)
            if key is guid2_ctx:
                return (upn, 1)         # Non-empty → enrolled
        raise FileNotFoundError(f"no value {value_name!r}")

    with patch.object(apps_mod.winreg, "OpenKey", side_effect=open_key_side), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=enum_fn), \
         patch.object(apps_mod.winreg, "QueryValueEx", side_effect=query_fn), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)

    cp = next(a for a in report.apps if a.name == "Company Portal")
    assert cp.service_state == f"Enrolled: {upn}"


def test_company_portal_not_enrolled_returns_none():
    """D-02/D-04: Enrollments key has GUID but UPN is missing (FileNotFoundError) → service_state=None."""
    guid = "{CCCCCC-stale-only}"
    enroll_root_ctx = _make_fake_ctx()
    guid_ctx = _make_fake_ctx()

    def open_key_side(hive_or_key, path_or_subkey, *args, **kwargs):
        if isinstance(path_or_subkey, str) and "AppModel" in path_or_subkey:
            raise OSError("HKCU absent")
        if hive_or_key is enroll_root_ctx and path_or_subkey == guid:
            return guid_ctx
        if isinstance(path_or_subkey, str) and "Enrollments" in path_or_subkey:
            return enroll_root_ctx
        raise OSError("not found")

    def enum_fn(key, index):
        if key is enroll_root_ctx:
            if index == 0:
                return guid
            raise OSError("exhausted")
        raise OSError("exhausted")

    def query_fn(key, value_name):
        raise FileNotFoundError("UPN value absent — stale GUID")

    with patch.object(apps_mod.winreg, "OpenKey", side_effect=open_key_side), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=enum_fn), \
         patch.object(apps_mod.winreg, "QueryValueEx", side_effect=query_fn), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)

    cp = next(a for a in report.apps if a.name == "Company Portal")
    assert cp.installed is False
    assert cp.service_state is None


def test_company_portal_enrollment_exception_returns_none():
    """Safety: PermissionError on Enrollments key → service_state=None, no exception propagated."""
    def open_key_side(hive_or_key, path_or_subkey, *args, **kwargs):
        if isinstance(path_or_subkey, str) and "AppModel" in path_or_subkey:
            raise OSError("HKCU absent")
        if isinstance(path_or_subkey, str) and "Enrollments" in path_or_subkey:
            raise PermissionError("access denied to Enrollments")
        raise OSError("not found")

    with patch.object(apps_mod.winreg, "OpenKey", side_effect=open_key_side), \
         patch.object(apps_mod.winreg, "EnumKey", side_effect=OSError("not reached")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)   # Must not raise

    cp = next(a for a in report.apps if a.name == "Company Portal")
    assert cp.service_state is None


def test_company_portal_always_present():
    """Company Portal always produces one AppStatus entry (D-15 extended to 9 apps)."""
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=OSError("no registry")), \
         patch("collectors.windows.apps.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.joinpath.return_value = mock_path.return_value
        report = make_report()
        apps_mod.collect_apps(report)

    app_names = [a.name for a in report.apps]
    assert "Company Portal" in app_names
    assert len(report.apps) == 9
