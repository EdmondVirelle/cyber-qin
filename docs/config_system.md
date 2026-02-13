# Configuration System

**Version:** 1.0
**Location:** `~/.cyber_qin/config.json`

---

## Overview

The configuration system provides JSON-based persistent storage for user preferences, replacing Qt's QSettings for better portability and version control.

## Features

- ✅ **JSON Format** — Human-readable, easy to backup and share
- ✅ **Dot Notation** — Access nested config with `config.get("midi.last_port")`
- ✅ **Auto-Save** — Changes persist immediately to disk
- ✅ **Type-Safe** — Default values preserve types
- ✅ **Migration** — Automatically merges new defaults in future versions
- ✅ **QSettings Migration** — One-time migration from old QSettings

---

## Usage

### Basic Example

```python
from cyber_qin.core.config import get_config

# Get global config instance
config = get_config()

# Get values (with defaults)
last_port = config.get("midi.last_port", "")
transpose = config.get("playback.transpose", 0)

# Set values (auto-saves to disk)
config.set("midi.last_port", "Roland FP-30X")
config.set("playback.transpose", 2)
```

### In PyQt6 Widgets

Replace QSettings usage:

**Old code (QSettings):**
```python
class MyWidget(QWidget):
    def __init__(self):
        self._settings = QSettings("CyberQin", "CyberQin")

    def save_preference(self):
        self._settings.setValue("my_key", "my_value")

    def load_preference(self):
        return self._settings.value("my_key", "", type=str)
```

**New code (ConfigManager):**
```python
from cyber_qin.core.config import get_config

class MyWidget(QWidget):
    def __init__(self):
        self._config = get_config()

    def save_preference(self):
        self._config.set("my_section.my_key", "my_value")

    def load_preference(self):
        return self._config.get("my_section.my_key", "")
```

---

## Configuration Schema

Default `~/.cyber_qin/config.json`:

```json
{
  "version": "1.0",
  "midi": {
    "last_port": "",
    "auto_connect": true
  },
  "playback": {
    "transpose": 0,
    "scheme_id": ""
  },
  "editor": {
    "snap_enabled": true,
    "grid_subdivision": 4,
    "auto_save": true,
    "auto_save_interval": 60
  },
  "window": {
    "geometry": null,
    "last_view": "live"
  },
  "ui": {
    "language": "auto",
    "theme": "dark"
  },
  "library": {
    "last_directory": "",
    "sort_by": "modified",
    "sort_order": "desc"
  }
}
```

### Schema Documentation

#### `midi`
- `last_port` (str) — Last connected MIDI port name
- `auto_connect` (bool) — Auto-reconnect to last port on startup

#### `playback`
- `transpose` (int) — Transpose in octaves (-2 to +2)
- `scheme_id` (str) — Active mapping scheme ID (e.g., "default_36")

#### `editor`
- `snap_enabled` (bool) — Enable snap-to-grid in editor
- `grid_subdivision` (int) — Grid subdivision (1=whole, 4=quarter, etc.)
- `auto_save` (bool) — Enable auto-save for projects
- `auto_save_interval` (int) — Auto-save interval in seconds

#### `window`
- `geometry` (null/str) — Window geometry state (QByteArray base64)
- `last_view` (str) — Last active view ("live", "library", "editor")

#### `ui`
- `language` (str) — UI language ("auto", "en", "zh_TW")
- `theme` (str) — UI theme ("dark", future: "light")

#### `library`
- `last_directory` (str) — Last opened directory in file picker
- `sort_by` (str) — Sort order ("name", "created", "modified")
- `sort_order` (str) — Sort direction ("asc", "desc")

---

## API Reference

### `ConfigManager`

#### `get(key_path: str, default: Any = None) -> Any`
Get config value using dot notation.

**Example:**
```python
port = config.get("midi.last_port")
transpose = config.get("playback.transpose", 0)
```

#### `set(key_path: str, value: Any) -> None`
Set config value and save to disk.

**Example:**
```python
config.set("midi.last_port", "Roland FP-30X")
config.set("editor.snap_enabled", False)
```

#### `get_all() -> dict`
Get entire config dictionary (for debugging/export).

#### `reset() -> None`
Reset all config to default values.

---

## Migration from QSettings

On first run with the new system, call the migration helper in `main.py`:

```python
from cyber_qin.core.config import ConfigManager

# Migrate old QSettings to new JSON config (run once)
ConfigManager.migrate_from_qsettings()
```

This will transfer:
- `last_port` → `midi.last_port`
- `transpose` → `playback.transpose`
- `scheme_id` → `playback.scheme_id`

---

## Testing

Run config system tests:

```bash
.venv313/Scripts/python -m pytest tests/test_config.py -v
```

All 15 tests should pass:
- ✅ Config initialization
- ✅ Get/set with dot notation
- ✅ Persistence across instances
- ✅ Default merging
- ✅ Invalid JSON handling

---

## File Locations

- **Config:** `~/.cyber_qin/config.json`
- **Auto-save:** `~/.cyber_qin/autosave.cqp`
- **Library cache:** `~/.cyber_qin/library_cache.json` (future)

On Windows: `C:\Users\<username>\.cyber_qin\`

---

## Future Enhancements

- [ ] Schema versioning with automatic migrations
- [ ] Config validation (e.g., transpose range -2 to +2)
- [ ] Import/export config for backup
- [ ] Cloud sync support
