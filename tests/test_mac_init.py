"""Unit tests for collectors.mac package marker.
Verifies that collectors.mac is importable as a Python package.
"""
from __future__ import annotations


def test_collectors_mac_package_importable():
    """collectors.mac must be importable as a Python package."""
    import collectors.mac  # noqa: F401
