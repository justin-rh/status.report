"""Tests for Phase 17 --diag-vendor CLI flag.

Tests the --diag-vendor short-circuit dispatcher, its exit-0 contract,
the stderr warning when --output is combined, the Darwin platform gate,
the --help output, and the dispatcher-ordering contract (--diag-vendor
before --app).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Test 1: --diag-vendor exits 0 and calls diag_vendor_paths
# ---------------------------------------------------------------------------

def test_diag_vendor_short_circuits_and_exits_0(capsys):
    """--diag-vendor exits 0 and calls diag_vendor_paths (not full pipeline)."""
    import main
    with (
        patch("sys.argv", ["scry", "--diag-vendor"]),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.vendor.diag_vendor_paths") as mock_diag,
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    assert mock_diag.called


# ---------------------------------------------------------------------------
# Test 2: --diag-vendor --output PATH warns to stderr
# ---------------------------------------------------------------------------

def test_diag_vendor_with_output_warns_to_stderr(capsys):
    """--diag-vendor combined with --output warns on stderr (DEBT-03 shape)."""
    import main
    with (
        patch("sys.argv", ["scry", "--diag-vendor", "--output", r"C:\tmp\x"]),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.vendor.diag_vendor_paths"),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "WARNING: --output is ignored in --diag-vendor mode" in captured.err


# ---------------------------------------------------------------------------
# Test 3: --diag-vendor does not invoke full pipeline
# ---------------------------------------------------------------------------

def test_diag_vendor_does_not_invoke_full_pipeline(capsys):
    """--diag-vendor does not call collect_all or render_html."""
    import main
    with (
        patch("sys.argv", ["scry", "--diag-vendor"]),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.vendor.diag_vendor_paths"),
        patch("main.collect_all") as mock_collect_all,
        patch("main.render_html") as mock_render,
    ):
        with pytest.raises(SystemExit):
            main.main()
    assert not mock_collect_all.called
    assert not mock_render.called


# ---------------------------------------------------------------------------
# Test 4: --diag-vendor is dispatched before --warnings (cli_mode gate)
# ---------------------------------------------------------------------------

def test_diag_vendor_dispatched_before_cli_mode(capsys):
    """--diag-vendor --warnings routes to diag handler, not _run_cli."""
    import main
    with (
        patch("sys.argv", ["scry", "--diag-vendor", "--warnings"]),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.vendor.diag_vendor_paths") as mock_diag,
        patch("main._run_cli") as mock_run_cli,
    ):
        with pytest.raises(SystemExit):
            main.main()
    assert mock_diag.called
    assert not mock_run_cli.called


# ---------------------------------------------------------------------------
# Test 5: --diag-vendor on Darwin exits 0 with stderr note
# ---------------------------------------------------------------------------

def test_diag_vendor_on_darwin_exits_with_note(capsys):
    """On Darwin --diag-vendor exits 0 with a stderr note and no import of vendor."""
    import main
    with (
        patch("sys.argv", ["scry", "--diag-vendor"]),
        patch("main.sys.platform", "darwin"),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--diag-vendor is Windows-only" in captured.err


# ---------------------------------------------------------------------------
# Test 6: --diag-vendor appears in --help output
# ---------------------------------------------------------------------------

def test_diag_vendor_flag_in_help(capsys):
    """--diag-vendor is registered in argparse and appears in --help."""
    import main
    with patch("sys.argv", ["scry", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--diag-vendor" in captured.out


# ---------------------------------------------------------------------------
# Test 7 (B1): dispatcher ordering — --diag-vendor beats --app
# ---------------------------------------------------------------------------

def test_diag_vendor_dispatched_before_app(capsys):
    """--diag-vendor --app chrome routes to diag handler, not _run_cli_app.

    Enforces the dispatcher-ordering contract: --diag-vendor MUST appear
    ABOVE the --app block in main.py. A future refactor that swaps the order
    would fail this test (the only mechanical safeguard against silent drift).
    """
    import main
    with (
        patch("sys.argv", ["scry", "--diag-vendor", "--app", "chrome"]),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.vendor.diag_vendor_paths") as mock_diag,
        patch("main._run_cli_app") as mock_run_cli_app,
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    assert mock_diag.called, "Expected --diag-vendor to short-circuit BEFORE --app"
    assert not mock_run_cli_app.called, (
        "Expected --app NOT to run when --diag-vendor is also set (ordering contract)"
    )
