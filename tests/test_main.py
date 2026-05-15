"""Tests for main.py — NINJA-01 (headless guard) and NINJA-02 ([SUMMARY] stdout line).

Patches the full pipeline so tests run without Windows APIs, a real filesystem,
or an interactive terminal.

Patch targets use the main module namespace because main.py imports with:
    from collectors import collect_all
    from health_checks import evaluate_warnings
    from renderer import render_html
    import socket, os, sys
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname


# ---------------------------------------------------------------------------
# Shared helper — run main() with all heavy dependencies patched out
# ---------------------------------------------------------------------------

@contextmanager
def _patched_main(isatty_value: bool, report_overrides: dict | None = None):
    """Context manager that patches main()'s dependencies and yields
    (mock_startfile, mock_input).

    The caller should call main.main() inside the with block.

    report_overrides: keyword arguments forwarded to AuditReport() to control
    which hardware fields are populated. Used by test_summary_none_safety.
    """
    hostname = "PHX-INV-001"

    # Build the AuditReport that collect_all will leave behind.
    # We patch collect_all to a no-op so the report stays at its constructor defaults
    # (all hardware fields None) UNLESS the caller supplies overrides.
    base_kwargs = dict(
        hostname=hostname,
        parsed_hostname=parse_hostname(hostname),
    )
    if report_overrides:
        base_kwargs.update(report_overrides)
    fixed_report = AuditReport(**base_kwargs)

    mock_startfile = MagicMock()
    mock_input = MagicMock()

    # collect_all mutates report in place — we replace it with a function that
    # swaps out the mutable report fields with our pre-built object's values.
    def fake_collect_all(report):
        # Copy hardware fields from fixed_report onto the live report object
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
# Test 1: headless — isatty() returns False
# ---------------------------------------------------------------------------

def test_headless_skips_startfile_and_input():
    """When isatty()=False, os.startfile and input must not be called (NINJA-01)."""
    import main

    with _patched_main(isatty_value=False) as (mock_startfile, mock_input):
        main.main()

    assert mock_startfile.call_count == 0, (
        f"os.startfile should NOT be called in headless mode, "
        f"but was called {mock_startfile.call_count} time(s)"
    )
    assert mock_input.call_count == 0, (
        f"input() should NOT be called in headless mode, "
        f"but was called {mock_input.call_count} time(s)"
    )


# ---------------------------------------------------------------------------
# Test 2: interactive — isatty() returns True
# ---------------------------------------------------------------------------

def test_interactive_calls_startfile_and_input():
    """When isatty()=True, os.startfile and input must each be called once (NINJA-01)."""
    import main

    with _patched_main(isatty_value=True) as (mock_startfile, mock_input):
        main.main()

    assert mock_startfile.call_count == 1, (
        f"os.startfile should be called exactly once in interactive mode, "
        f"but was called {mock_startfile.call_count} time(s)"
    )
    assert mock_input.call_count == 1, (
        f"input() should be called exactly once in interactive mode, "
        f"but was called {mock_input.call_count} time(s)"
    )


# ---------------------------------------------------------------------------
# Test 3: [SUMMARY] appears in stdout on every run
# ---------------------------------------------------------------------------

def test_summary_line_in_stdout(capsys):
    """[SUMMARY] line is printed to stdout on every run, including headless (NINJA-02)."""
    import main

    with _patched_main(isatty_value=False):
        main.main()

    captured = capsys.readouterr()
    assert "[SUMMARY]" in captured.out, (
        f"Expected '[SUMMARY]' token in stdout. Got:\n{captured.out}"
    )
    assert "disk used" in captured.out, (
        f"Expected 'disk used' in [SUMMARY] line. Got:\n{captured.out}"
    )
    assert "warnings" in captured.out, (
        f"Expected 'warnings' in [SUMMARY] line. Got:\n{captured.out}"
    )


# ---------------------------------------------------------------------------
# Test 4: None-value safety in [SUMMARY] builder
# ---------------------------------------------------------------------------

def test_summary_none_safety(capsys):
    """None hardware fields produce readable fallbacks in [SUMMARY] — no TypeError (NINJA-02)."""
    import main

    # All hardware fields left at None (AuditReport constructor defaults).
    # fake_collect_all in _patched_main copies these None values onto the live report.
    with _patched_main(isatty_value=False, report_overrides={}):
        main.main()

    captured = capsys.readouterr()
    assert "Unknown CPU" in captured.out, (
        f"Expected 'Unknown CPU' for cpu_model=None. Got:\n{captured.out}"
    )
    assert "Unknown RAM" in captured.out, (
        f"Expected 'Unknown RAM' for ram_gb=None. Got:\n{captured.out}"
    )
    assert "0% disk used" in captured.out, (
        f"Expected '0% disk used' for disk_total_gb=None. Got:\n{captured.out}"
    )


# ---------------------------------------------------------------------------
# CLI flag tests (Phase 11: Steve)
# ---------------------------------------------------------------------------

def test_name_flag_prints_hostname(capsys):
    """--name prints the hostname and exits 0 (D-08: no collect_all needed)."""
    import main
    with (
        patch("sys.argv", ["scry", "--name"]),
        patch("main.socket.gethostname", return_value="PHX-INV-001"),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "PHX-INV-001"


def test_serial_flag_prints_serial(capsys):
    """--serial runs hardware collection and prints serial_number (D-09)."""
    import main
    def fake_collect_hardware(report):
        report.serial_number = "SN-ABC-12345"
    with (
        patch("sys.argv", ["scry", "--serial"]),
        patch("main.socket.gethostname", return_value="PHX-INV-001"),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.hardware.collect_hardware", side_effect=fake_collect_hardware),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "SN-ABC-12345"


def test_serial_flag_unknown_when_none(capsys):
    """--serial prints 'Unknown' when serial_number is None (D-07)."""
    import main
    def fake_collect_hardware(report):
        report.serial_number = None
    with (
        patch("sys.argv", ["scry", "--serial"]),
        patch("main.socket.gethostname", return_value="PHX-INV-001"),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.hardware.collect_hardware", side_effect=fake_collect_hardware),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "Unknown"


def test_warnings_flag_prints_warn_messages(capsys):
    """--warnings prints WARN-severity message strings one per line (D-04)."""
    from models import Warning
    import main
    warn_warnings = [
        Warning(code="OS_VERSION", severity="WARN", message="Windows 10 or earlier detected"),
        Warning(code="DISK_SPACE", severity="OK", message="Disk space is adequate"),
        Warning(code="RENAME_REQUIRED", severity="OK", message="Hostname matches naming convention"),
    ]
    with (
        patch("sys.argv", ["scry", "--warnings"]),
        patch("main.socket.gethostname", return_value="PHX-INV-001"),
        patch("main.collect_all"),
        patch("main.evaluate_warnings", return_value=warn_warnings),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    lines = [l for l in captured.out.splitlines() if l]
    assert lines == ["Windows 10 or earlier detected"], (
        f"Expected only WARN messages; got: {lines}"
    )


def test_warnings_flag_empty_when_all_ok(capsys):
    """--warnings prints nothing when all checks pass (D-05)."""
    from models import Warning
    import main
    ok_warnings = [
        Warning(code="OS_VERSION", severity="OK", message="OS version is current"),
        Warning(code="DISK_SPACE", severity="OK", message="Disk space is adequate"),
        Warning(code="RENAME_REQUIRED", severity="OK", message="Hostname matches naming convention"),
    ]
    with (
        patch("sys.argv", ["scry", "--warnings"]),
        patch("main.socket.gethostname", return_value="PHX-INV-001"),
        patch("main.collect_all"),
        patch("main.evaluate_warnings", return_value=ok_warnings),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "", (
        f"Expected empty stdout for all-OK warnings; got: {captured.out!r}"
    )


def test_name_serial_combined_output_order(capsys):
    """--name --serial prints name then serial in fixed order regardless of CLI order (D-02)."""
    import main
    def fake_collect_hardware(report):
        report.serial_number = "SN-ORDER-TEST"
    with (
        patch("sys.argv", ["scry", "--serial", "--name"]),  # reversed CLI order
        patch("main.socket.gethostname", return_value="PHX-INV-001"),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.hardware.collect_hardware", side_effect=fake_collect_hardware),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    lines = [l for l in captured.out.splitlines() if l]
    assert lines == ["PHX-INV-001", "SN-ORDER-TEST"], (
        f"Expected name before serial; got: {lines}"
    )


def test_cli_mode_suppresses_summary_line(capsys):
    """CLI flag mode must not emit [SUMMARY] line (targeted output only)."""
    import main
    with (
        patch("sys.argv", ["scry", "--name"]),
        patch("main.socket.gethostname", return_value="PHX-INV-001"),
    ):
        with pytest.raises(SystemExit):
            main.main()
    captured = capsys.readouterr()
    assert "[SUMMARY]" not in captured.out, (
        f"[SUMMARY] must not appear in CLI flag mode output; got:\n{captured.out}"
    )


def test_no_flags_runs_full_pipeline(capsys):
    """No flags -> full pipeline runs and emits [SUMMARY] (D-03, regression guard)."""
    import main
    with (
        patch("sys.argv", ["scry"]),
    ):
        with _patched_main(isatty_value=False):
            main.main()
    captured = capsys.readouterr()
    assert "[SUMMARY]" in captured.out, (
        f"No-flags mode must still emit [SUMMARY]; got:\n{captured.out}"
    )
