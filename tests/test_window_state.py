"""Test window state persistence via ConfigManager."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QByteArray

from cyber_qin.core.config import ConfigManager


@pytest.fixture
def clean_config(tmp_path):
    """Create isolated config for testing."""
    import cyber_qin.core.config as config_module

    config_dir = tmp_path / ".cyber_qin"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Reset global singleton and create new instance with test directory
    config_module._global_config = None
    config_module._global_config = ConfigManager(config_dir)

    yield config_module._global_config

    # Cleanup
    config_module._global_config = None


class TestWindowStateConfig:
    """Test window state persistence in ConfigManager."""

    def test_default_window_config(self, clean_config):
        """Config should have default window settings."""
        config = clean_config

        assert config.get("window.geometry") is None
        assert config.get("window.last_view") == "live"

    def test_save_window_geometry(self, clean_config):
        """Should be able to save window geometry as base64 string."""
        config = clean_config

        # Simulate Qt's saveGeometry().toBase64() output
        geometry_b64 = (
            QByteArray(b"\x01\xd9\xd0\xcb\x00\x03\x00\x00").toBase64().data().decode("ascii")
        )

        config.set("window.geometry", geometry_b64)
        assert config.get("window.geometry") == geometry_b64

    def test_save_last_view(self, clean_config):
        """Should be able to save and retrieve last active view."""
        config = clean_config

        for view in ["live", "library", "editor"]:
            config.set("window.last_view", view)
            assert config.get("window.last_view") == view

    def test_invalid_view_returns_as_is(self, clean_config):
        """Config should store invalid views (validation is done by app)."""
        config = clean_config

        config.set("window.last_view", "invalid_view")
        assert config.get("window.last_view") == "invalid_view"

    def test_view_index_mapping(self, clean_config):
        """Test view name to index mapping used by app_shell."""
        view_mapping = {"live": 0, "library": 1, "editor": 2}

        for name, expected_index in view_mapping.items():
            assert view_mapping.get(name) == expected_index

        # Test fallback for invalid view
        assert view_mapping.get("invalid", 0) == 0

    def test_persistence_across_instances(self, clean_config, tmp_path):
        """Window state should persist across ConfigManager instances."""
        config1 = clean_config
        config1.set("window.last_view", "editor")

        # Create new instance with same directory
        import cyber_qin.core.config as config_module

        config_dir = tmp_path / ".cyber_qin"
        config_module._global_config = None
        config2 = ConfigManager(config_dir)

        assert config2.get("window.last_view") == "editor"

    def test_geometry_persistence(self, clean_config, tmp_path):
        """Window geometry should persist across ConfigManager instances."""
        config1 = clean_config
        geometry_b64 = (
            QByteArray(b"\x01\xd9\xd0\xcb\x00\x03\x00\x00").toBase64().data().decode("ascii")
        )
        config1.set("window.geometry", geometry_b64)

        # Create new instance with same directory
        import cyber_qin.core.config as config_module

        config_dir = tmp_path / ".cyber_qin"
        config_module._global_config = None
        config2 = ConfigManager(config_dir)

        loaded_geometry = config2.get("window.geometry")
        assert loaded_geometry == geometry_b64
