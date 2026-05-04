"""File writer — writes rendered HTML to flash drive output path.
write_html(html, output_path) is the single entry point (D-17).
"""
from __future__ import annotations

from pathlib import Path


def write_html(html: str, output_path: Path) -> Path:
    """Write HTML string to output_path / 'status_report.html'. Returns full path.

    Uses pathlib.Path.write_text (project convention).
    Caller (renderer/__init__.py) is responsible for resolving output_path
    from Path(sys.executable).parent — D-16.
    """
    dest = output_path / 'status_report.html'
    dest.write_text(html, encoding='utf-8')
    return dest
