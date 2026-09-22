"""Smoke test for Phase 1: the package installs and imports cleanly."""

import vectorx


def test_package_has_version():
    assert vectorx.__version__ == "0.1.0"
