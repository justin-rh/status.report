"""Unit tests for writers — write_html function (D-17).
RED phase: Tests written against the public interface before implementation exists.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# write_html — file creation and path return
# ---------------------------------------------------------------------------

def test_write_html_creates_file():
    """write_html creates scry.html in the given directory."""
    from writers import write_html

    with tempfile.TemporaryDirectory() as tmp:
        write_html('<html>test</html>', Path(tmp))
        assert (Path(tmp) / 'scry.html').exists()


def test_write_html_returns_full_path():
    """write_html returns a Path equal to output_path / 'scry.html'."""
    from writers import write_html

    with tempfile.TemporaryDirectory() as tmp:
        result = write_html('<html>test</html>', Path(tmp))
        expected = Path(tmp) / 'scry.html'
        assert result == expected


def test_write_html_returned_path_exists():
    """The Path returned by write_html points to an existing file."""
    from writers import write_html

    with tempfile.TemporaryDirectory() as tmp:
        result = write_html('<html>test</html>', Path(tmp))
        assert result.exists()


def test_write_html_returned_path_name():
    """Returned Path has name 'scry.html'."""
    from writers import write_html

    with tempfile.TemporaryDirectory() as tmp:
        result = write_html('<html>test</html>', Path(tmp))
        assert result.name == 'scry.html'


# ---------------------------------------------------------------------------
# write_html — content correctness
# ---------------------------------------------------------------------------

def test_write_html_content_matches():
    """File contents match the html argument exactly when read as utf-8."""
    from writers import write_html

    html = '<html><body>Hello world</body></html>'
    with tempfile.TemporaryDirectory() as tmp:
        result = write_html(html, Path(tmp))
        assert result.read_text(encoding='utf-8') == html


def test_write_html_unicode_roundtrip():
    """write_html round-trips Unicode characters (em-dash u2014) correctly."""
    from writers import write_html

    html = '<html><body>Em—dash and café</body></html>'
    with tempfile.TemporaryDirectory() as tmp:
        result = write_html(html, Path(tmp))
        assert result.read_text(encoding='utf-8') == html
