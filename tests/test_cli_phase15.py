"""Tests for Phase 15 Extended CLI Flags: --json, --output, --app."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from models import AuditReport, AppStatus
from parsers.name_parser import parse_hostname


# ---------------------------------------------------------------------------
# Shared helper — replicated from test_main.py to avoid import coupling
# ---------------------------------------------------------------------------

@contextmanager
def _patched_main(isatty_value: bool, report_overrides: dict | None = None):
    """Context manager that patches main()'s dependencies and yields
    (mock_startfile, mock_input).

    The caller should call main.main() inside the with block.

    report_overrides: keyword arguments forwarded to AuditReport() to control
    which hardware fields are populated.
    """
    hostname = "PHX-INV-001"

    base_kwargs = dict(
        hostname=hostname,
        parsed_hostname=parse_hostname(hostname),
    )
    if report_overrides:
        base_kwargs.update(report_overrides)
    fixed_report = AuditReport(**base_kwargs)

    mock_startfile = MagicMock()
    mock_input = MagicMock()

    def fake_collect_all(report):
        for field_name in (
            "os_version", "os_build", "serial_number", "cpu_model",
            "ram_gb", "disk_total_gb", "disk_free_gb", "current_user",
            "local_profiles", "apps", "collection_errors",
        ):
            setattr(report, field_name, getattr(fixed_report, field_name))

    with (
        patch("sys.argv", ["scry"]),
        patch("main.socket.gethostname", return_value=hostname),
        patch("main.collect_all", side_effect=fake_collect_all),
        patch("main.evaluate_warnings", return_value=[]),
        patch("main.render_html", return_value="<html></html>"),
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.write_text"),
        patch("pathlib.Path.exists", return_value=False),
        patch("main.os.startfile", mock_startfile),
        patch("builtins.input", mock_input),
        patch("sys.stdin") as mock_stdin,
    ):
        mock_stdin.isatty.return_value = isatty_value
        yield mock_startfile, mock_input


# ---------------------------------------------------------------------------
# Test 1: --app not installed (D-12)
# ---------------------------------------------------------------------------

def test_app_flag_not_installed(capsys):
    """--app ninjaone prints '<name>: not installed' when app is absent (D-12)."""
    import main
    def fake_detect(spec, report):
        report.apps.append(AppStatus(name="NinjaOne", installed=False))
    with (
        patch("sys.argv", ["scry", "--app", "ninjaone"]),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.apps._detect_one_app", side_effect=fake_detect),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "NinjaOne: not installed"


# ---------------------------------------------------------------------------
# Test 2: --app installed with version (D-12)
# ---------------------------------------------------------------------------

def test_app_flag_installed_with_version(capsys):
    """--app ninjaone prints '<name>: installed (v<version>)' when installed (D-12)."""
    import main
    def fake_detect(spec, report):
        report.apps.append(AppStatus(name="NinjaOne", installed=True, version="5.3.1"))
    with (
        patch("sys.argv", ["scry", "--app", "ninjaone"]),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.apps._detect_one_app", side_effect=fake_detect),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "NinjaOne: installed (v5.3.1)"


# ---------------------------------------------------------------------------
# Test 3: --app unknown name exits 1 (D-11)
# ---------------------------------------------------------------------------

def test_app_flag_unknown_exits_1(capsys):
    """--app with unrecognized name prints to stderr and exits 1 (D-11)."""
    import main
    with (
        patch("sys.argv", ["scry", "--app", "unknowntool"]),
        patch("main.sys.platform", "win32"),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Unknown app: unknowntool" in captured.err
    assert "Known apps:" in captured.err


# ---------------------------------------------------------------------------
# Test 4: --app --json to stdout, no files written (D-13)
# ---------------------------------------------------------------------------

def test_app_json_flag_prints_json_to_stdout(capsys):
    """--app ninjaone --json prints AppStatus dict as JSON to stdout; no files written (D-13)."""
    import main, json as _json
    def fake_detect(spec, report):
        report.apps.append(AppStatus(name="NinjaOne", installed=True, version="5.3.1"))
    mock_write = MagicMock()
    with (
        patch("sys.argv", ["scry", "--app", "ninjaone", "--json"]),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.apps._detect_one_app", side_effect=fake_detect),
        patch("pathlib.Path.write_text", mock_write),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    assert mock_write.call_count == 0, "No files should be written in --app --json mode"
    captured = capsys.readouterr()
    data = _json.loads(captured.out)
    assert data["name"] == "NinjaOne"
    assert data["installed"] is True


# ---------------------------------------------------------------------------
# Test 5: --json full pipeline writes JSON alongside HTML, [SUMMARY] present (D-04, D-06)
# ---------------------------------------------------------------------------

def test_json_flag_writes_json_alongside_html(capsys):
    """--json flag triggers full pipeline; JSON file written alongside HTML; [SUMMARY] in stdout (D-04, D-06)."""
    import main
    written_paths: list[str] = []
    with _patched_main(isatty_value=False):
        with (
            patch("sys.argv", ["scry", "--json"]),
            patch("pathlib.Path.write_text", lambda self, content, encoding="utf-8": written_paths.append(str(self))),
        ):
            main.main()
    json_paths = [p for p in written_paths if p.endswith(".json")]
    assert len(json_paths) == 1, f"Exactly one JSON file should be written; got: {written_paths}"
    captured = capsys.readouterr()
    assert "[SUMMARY]" in captured.out, "--json must still print [SUMMARY] (D-06)"


# ---------------------------------------------------------------------------
# Test 6: --output overrides logs_dir (D-01)
# ---------------------------------------------------------------------------

def test_output_flag_overrides_logs_dir():
    """--output <path> directs file output to provided path, not default logs/ (D-01)."""
    import main
    written_paths: list[str] = []
    with _patched_main(isatty_value=False):
        with (
            patch("sys.argv", ["scry", "--output", "/custom/audit_results"]),
            patch("pathlib.Path.write_text", lambda self, content, encoding="utf-8": written_paths.append(str(self))),
        ):
            main.main()
    assert any("/custom/audit_results" in p or "custom" in p or "audit_results" in p for p in written_paths), (
        f"Expected output under /custom/audit_results path; got: {written_paths}"
    )


# ---------------------------------------------------------------------------
# Test 7: --json overrides --name (full pipeline, not _run_cli) (D-05)
# ---------------------------------------------------------------------------

def test_json_overrides_cli_mode_flags(capsys):
    """--json overrides --name/--serial/--warnings — full pipeline runs, not _run_cli (D-05)."""
    import main
    with _patched_main(isatty_value=False):
        with (
            patch("sys.argv", ["scry", "--json", "--name"]),
            patch("pathlib.Path.write_text", MagicMock()),
        ):
            main.main()   # Must NOT raise SystemExit(0) from _run_cli
    captured = capsys.readouterr()
    assert "[SUMMARY]" in captured.out, "--json must run full pipeline even with --name present (D-05)"
