"""Unit tests for main.py Mac-specific behavior (Phase 10).

Tests verify:
1. On darwin, usb_root = Path(__file__).parent (not Path(sys.executable).parent)
2. On non-darwin, usb_root = Path(sys.executable).parent (unchanged)
3. On darwin with isatty(), subprocess.run(["open", str(output_path)]) is called
4. On non-darwin with isatty(), os.startfile(str(output_path)) is called (unchanged)
5. main.py imports subprocess at module level without error
"""
from __future__ import annotations

import ast
import importlib
import pathlib
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, call

import pytest

from models import AuditReport
from parsers.name_parser import parse_hostname


# ---------------------------------------------------------------------------
# Test 5 (static): subprocess is imported in main.py at module level
# ---------------------------------------------------------------------------

def test_subprocess_imported_in_main():
    """main.py must have 'import subprocess' in its stdlib imports block."""
    src = pathlib.Path("main.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imports = [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)]
    assert "subprocess" in imports, (
        f"'import subprocess' not found in main.py. Found imports: {imports}"
    )


# ---------------------------------------------------------------------------
# Shared helper — run main() patched for platform tests
# ---------------------------------------------------------------------------

@contextmanager
def _patched_main_platform(isatty_value: bool, platform_str: str):
    """Context manager that patches main()'s dependencies for platform tests.

    Yields (mock_startfile, mock_subprocess_run, mock_input, captured_output_path).
    """
    hostname = "PHX-INV-001"
    base_kwargs = dict(
        hostname=hostname,
        parsed_hostname=parse_hostname(hostname),
    )
    fixed_report = AuditReport(**base_kwargs)

    mock_startfile = MagicMock()
    mock_subprocess_run = MagicMock()
    mock_input = MagicMock()
    captured = {"output_path": None}

    def fake_collect_all(report):
        pass

    # Track which output_path was constructed
    original_write_text = pathlib.Path.write_text

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
        patch("main.subprocess.run", mock_subprocess_run),
        patch("builtins.input", mock_input),
        patch("sys.stdin") as mock_stdin,
        patch("sys.platform", platform_str),
    ):
        mock_stdin.isatty.return_value = isatty_value
        yield mock_startfile, mock_subprocess_run, mock_input


# ---------------------------------------------------------------------------
# Test 3: darwin + isatty → subprocess.run(["open", ...]) called
# ---------------------------------------------------------------------------

def test_darwin_interactive_calls_subprocess_open():
    """On darwin with isatty()=True, subprocess.run(['open', output_path]) must be called."""
    import main

    with _patched_main_platform(isatty_value=True, platform_str="darwin") as (
        mock_startfile, mock_subprocess_run, mock_input
    ):
        main.main()

    # subprocess.run should have been called with ["open", <some path>]
    assert mock_subprocess_run.call_count >= 1, (
        "subprocess.run must be called on darwin interactive run"
    )
    call_args = mock_subprocess_run.call_args_list[0][0][0]  # first positional arg of first call
    assert call_args[0] == "open", (
        f"First argument to subprocess.run must be 'open', got {call_args[0]!r}"
    )

    # os.startfile should NOT be called on darwin
    assert mock_startfile.call_count == 0, (
        f"os.startfile should NOT be called on darwin, called {mock_startfile.call_count} time(s)"
    )


# ---------------------------------------------------------------------------
# Test 4: non-darwin + isatty → os.startfile called (unchanged behavior)
# ---------------------------------------------------------------------------

def test_non_darwin_interactive_calls_startfile():
    """On non-darwin with isatty()=True, os.startfile must be called (unchanged Windows behavior)."""
    import main

    with _patched_main_platform(isatty_value=True, platform_str="win32") as (
        mock_startfile, mock_subprocess_run, mock_input
    ):
        main.main()

    assert mock_startfile.call_count == 1, (
        f"os.startfile must be called once on non-darwin interactive run, "
        f"called {mock_startfile.call_count} time(s)"
    )

    # subprocess.run should NOT be called for open on Windows
    open_calls = [
        c for c in mock_subprocess_run.call_args_list
        if c[0] and c[0][0] and c[0][0][0] == "open"
    ]
    assert len(open_calls) == 0, (
        f"subprocess.run(['open', ...]) should NOT be called on non-darwin"
    )


# ---------------------------------------------------------------------------
# Test 1+2: usb_root path — via static analysis of main.py source
# ---------------------------------------------------------------------------

def test_main_contains_darwin_usb_root_branch():
    """main.py must contain the darwin Path(__file__).parent branch for usb_root."""
    src = pathlib.Path("main.py").read_text(encoding="utf-8")
    assert 'sys.platform == "darwin"' in src, (
        "main.py must contain 'if sys.platform == \"darwin\":' for usb_root"
    )
    assert "Path(__file__).parent" in src, (
        "main.py must contain 'Path(__file__).parent' for darwin usb_root"
    )
    assert "Path(sys.executable).parent" in src, (
        "main.py must still contain 'Path(sys.executable).parent' for non-darwin"
    )
