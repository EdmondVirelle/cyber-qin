"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for the entire test session."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
