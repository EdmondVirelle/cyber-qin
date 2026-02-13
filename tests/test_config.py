"""Tests for configuration persistence system."""

import json

import pytest

from cyber_qin.core.config import ConfigManager


@pytest.fixture
def temp_config_dir(tmp_path):
    """Provide a temporary config directory for testing."""
    return tmp_path / "test_config"


@pytest.fixture
def config(temp_config_dir):
    """Provide a ConfigManager instance with temporary storage."""
    return ConfigManager(config_dir=temp_config_dir)


class TestConfigInit:
    """Test configuration initialization."""

    def test_creates_default_config_if_not_exists(self, config, temp_config_dir):
        """Should create default config.json if it doesn't exist."""
        assert (temp_config_dir / "config.json").exists()
        loaded = json.loads((temp_config_dir / "config.json").read_text(encoding="utf-8"))
        assert loaded["version"] == "1.0"
        assert "midi" in loaded
        assert "playback" in loaded

    def test_creates_config_directory(self, temp_config_dir):
        """Should create config directory if it doesn't exist."""
        assert not temp_config_dir.exists()
        ConfigManager(config_dir=temp_config_dir)
        assert temp_config_dir.exists()


class TestConfigGet:
    """Test getting config values."""

    def test_get_top_level_key(self, config):
        """Should get top-level config section."""
        midi = config.get("midi")
        assert isinstance(midi, dict)
        assert "last_port" in midi

    def test_get_nested_key(self, config):
        """Should get nested config value using dot notation."""
        transpose = config.get("playback.transpose")
        assert transpose == 0

    def test_get_nonexistent_key_returns_default(self, config):
        """Should return default value for nonexistent keys."""
        value = config.get("nonexistent.key", "default")
        assert value == "default"

    def test_get_nonexistent_key_returns_none(self, config):
        """Should return None for nonexistent keys without default."""
        value = config.get("nonexistent.key")
        assert value is None


class TestConfigSet:
    """Test setting config values."""

    def test_set_nested_key(self, config, temp_config_dir):
        """Should set nested config value and persist to disk."""
        config.set("midi.last_port", "Test Port")
        assert config.get("midi.last_port") == "Test Port"

        # Verify persistence
        reloaded = ConfigManager(config_dir=temp_config_dir)
        assert reloaded.get("midi.last_port") == "Test Port"

    def test_set_creates_missing_intermediate_keys(self, config):
        """Should create missing intermediate keys when setting deep path."""
        config.set("new.deep.nested.key", 42)
        assert config.get("new.deep.nested.key") == 42

    def test_set_updates_existing_key(self, config):
        """Should update existing config values."""
        config.set("playback.transpose", 2)
        assert config.get("playback.transpose") == 2

        config.set("playback.transpose", -1)
        assert config.get("playback.transpose") == -1


class TestConfigPersistence:
    """Test config persistence across instances."""

    def test_config_persists_across_instances(self, temp_config_dir):
        """Should persist config changes across multiple instances."""
        config1 = ConfigManager(config_dir=temp_config_dir)
        config1.set("playback.transpose", 5)
        config1.set("midi.last_port", "Persistent Port")

        config2 = ConfigManager(config_dir=temp_config_dir)
        assert config2.get("playback.transpose") == 5
        assert config2.get("midi.last_port") == "Persistent Port"

    def test_json_format_is_valid(self, temp_config_dir):
        """Should write valid JSON to disk."""
        config = ConfigManager(config_dir=temp_config_dir)
        config.set("test.key", "test value")

        config_file = temp_config_dir / "config.json"
        with open(config_file, encoding="utf-8") as f:
            loaded = json.load(f)  # Should not raise JSONDecodeError

        assert loaded["test"]["key"] == "test value"


class TestConfigMerge:
    """Test merging loaded config with defaults."""

    def test_merges_new_defaults_with_old_config(self, temp_config_dir):
        """Should add new default keys when config version is older."""
        # Create old config missing some keys
        old_config = {
            "version": "1.0",
            "midi": {
                "last_port": "Old Port",
            },
            # Missing "playback", "editor", etc.
        }
        config_file = temp_config_dir / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps(old_config, indent=2), encoding="utf-8")

        # Load with new defaults
        config = ConfigManager(config_dir=temp_config_dir)

        # Old values preserved
        assert config.get("midi.last_port") == "Old Port"

        # New defaults added
        assert config.get("playback.transpose") == 0
        assert config.get("editor.snap_enabled") is True


class TestConfigReset:
    """Test resetting config to defaults."""

    def test_reset_restores_defaults(self, config):
        """Should reset all config values to defaults."""
        config.set("midi.last_port", "Custom Port")
        config.set("playback.transpose", 10)

        config.reset()

        assert config.get("midi.last_port") == ""
        assert config.get("playback.transpose") == 0


class TestConfigGetAll:
    """Test getting entire config dictionary."""

    def test_get_all_returns_copy(self, config):
        """Should return a copy of config (not reference)."""
        all_config = config.get_all()
        all_config["midi"]["last_port"] = "Modified"

        # Original should be unchanged
        assert config.get("midi.last_port") == ""


class TestInvalidConfig:
    """Test handling of invalid config files."""

    def test_loads_defaults_on_corrupted_json(self, temp_config_dir):
        """Should load defaults if config.json is corrupted."""
        config_file = temp_config_dir / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("{ invalid json }", encoding="utf-8")

        config = ConfigManager(config_dir=temp_config_dir)

        # Should fallback to defaults
        assert config.get("playback.transpose") == 0
