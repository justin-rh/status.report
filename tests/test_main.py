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
        patch("sys.argv", ["status_report"]),
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
