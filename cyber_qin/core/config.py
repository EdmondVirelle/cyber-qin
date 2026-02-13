"""Configuration persistence using JSON format.

Replaces QSettings with a JSON-based config system stored at:
~/.cyber_qin/config.json

This allows easier backup, version control, and cross-platform portability.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


# Default configuration schema
DEFAULT_CONFIG = {
    "version": "1.0",
    "midi": {
        "last_port": "",
        "auto_connect": True,
    },
    "playback": {
        "transpose": 0,  # Octaves
        "scheme_id": "",  # Mapping scheme ID
    },
    "editor": {
        "snap_enabled": True,
        "grid_subdivision": 4,  # 1/4 notes
        "auto_save": True,
        "auto_save_interval": 60,  # seconds
    },
    "window": {
        "geometry": None,  # QByteArray base64 (saved separately)
        "last_view": "live",  # "live", "library", or "editor"
    },
    "ui": {
        "language": "auto",  # "auto", "en", "zh_TW"
        "theme": "dark",  # Future: support light theme
    },
    "library": {
        "last_directory": "",
        "sort_by": "modified",  # "name", "created", "modified"
        "sort_order": "desc",  # "asc", "desc"
    },
}


class ConfigManager:
    """Manages user configuration with JSON persistence."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize config manager.

        Args:
            config_dir: Custom config directory. If None, uses ~/.cyber_qin/
        """
        if config_dir is None:
            config_dir = Path.home() / ".cyber_qin"
        self.config_dir = config_dir
        self.config_file = config_dir / "config.json"
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load config from disk or create default."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if self.config_file.exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    loaded = json.load(f)
                # Merge with defaults (in case new keys were added)
                self._config = self._merge_defaults(loaded)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to load config: {e}. Using defaults.")
                self._config = copy.deepcopy(DEFAULT_CONFIG)
        else:
            self._config = copy.deepcopy(DEFAULT_CONFIG)
            self._save()

    def _merge_defaults(self, loaded: dict) -> dict:
        """Recursively merge loaded config with defaults."""
        def deep_merge(base: dict, override: dict) -> dict:
            merged = copy.deepcopy(base)
            for key, value in override.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = deep_merge(merged[key], value)
                else:
                    merged[key] = value
            return merged

        return deep_merge(DEFAULT_CONFIG, loaded)

    def _save(self) -> None:
        """Write config to disk."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"Warning: Failed to save config: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get config value using dot notation.

        Example:
            config.get("midi.last_port")
            config.get("editor.snap_enabled", True)
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value

    def set(self, key_path: str, value: Any) -> None:
        """Set config value using dot notation and save.

        Example:
            config.set("midi.last_port", "Roland FP-30X")
            config.set("editor.snap_enabled", False)
        """
        keys = key_path.split(".")
        target = self._config
        for key in keys[:-1]:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
        self._save()

    def get_all(self) -> dict[str, Any]:
        """Get entire config dictionary (for debugging)."""
        return copy.deepcopy(self._config)

    def reset(self) -> None:
        """Reset config to defaults."""
        self._config = copy.deepcopy(DEFAULT_CONFIG)
        self._save()

    # ── Migration helpers ───────────────────────────────

    @staticmethod
    def migrate_from_qsettings() -> None:
        """Migrate settings from QSettings to JSON config.

        Call this once during app startup to transfer old settings.
        """
        try:
            from PyQt6.QtCore import QSettings
        except ImportError:
            return  # QSettings not available (tests?)

        old_settings = QSettings("CyberQin", "CyberQin")
        config = ConfigManager()

        # Migrate known keys
        migrations = {
            "last_port": "midi.last_port",
            "transpose": "playback.transpose",
            "scheme_id": "playback.scheme_id",
        }

        for old_key, new_key in migrations.items():
            if old_settings.contains(old_key):
                value = old_settings.value(old_key)
                # QSettings stores everything as QVariant, convert to Python types
                if isinstance(value, str) and value.isdigit():
                    value = int(value)
                config.set(new_key, value)
                print(f"Migrated: {old_key} -> {new_key} = {value}")

        # Clear old settings after migration
        # old_settings.clear()  # Uncomment if you want to remove old QSettings


# Global singleton instance
_global_config: ConfigManager | None = None


def get_config() -> ConfigManager:
    """Get global config instance (singleton pattern)."""
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager()
    return _global_config
