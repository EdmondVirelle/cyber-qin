# CLAUDE.md — 賽博琴仙 Development Guide

## Project Overview

MIDI-to-Keyboard mapper for 燕雲十六聲 (Where Winds Meet) 36-key mode.
Stack: Python 3.11+ / PyQt6 / mido + python-rtmidi / ctypes SendInput.

## Commands

```bash
# Install (editable with dev deps)
pip install -e .[dev]

# Run the app (needs admin for DirectInput)
cyber-qin

# Tests
pytest

# Lint
ruff check .
ruff check --fix .
```

## Architecture

```
cyber_qin/
├── core/           # Platform-independent logic
│   ├── constants.py        # MIDI ranges, timing, scan codes
│   ├── key_mapper.py       # 36-key MIDI→keystroke mapping
│   ├── key_simulator.py    # ctypes SendInput (DirectInput scan codes)
│   ├── midi_listener.py    # python-rtmidi wrapper with auto-reconnect
│   └── midi_file_player.py # MIDI file playback engine
├── gui/            # PyQt6 UI
│   ├── app_shell.py        # QMainWindow with sidebar navigation
│   ├── icons.py            # SVG icon provider
│   ├── theme.py            # Dark theme QSS
│   ├── views/              # Full-page views (live_mode, library)
│   └── widgets/            # Reusable widgets (piano, sidebar, etc.)
├── utils/
│   ├── admin.py            # UAC elevation check
│   └── ime.py              # Input method detection
└── main.py         # Entry point
```

## Key Conventions

- **Latency-critical path**: MIDI callback → KeySimulator runs on the rtmidi thread directly, NOT through Qt signals. Only GUI updates go through signals.
- **Scan codes**: Always use `KEYEVENTF_SCANCODE` for DirectInput games, never virtual key codes.
- **ctypes INPUT struct**: The union MUST include `MOUSEINPUT` (largest member) so `sizeof(INPUT)` is 40 on 64-bit. Without it, `SendInput` silently fails.
- **Qt lazy imports**: Qt-dependent classes can't be at module level if the module may be imported before `QApplication` exists. Use lazy definition.
- **MIDI time**: `mido.merge_tracks()` returns ticks, not seconds. Always convert with `mido.tick2second()`.

## Testing

- 82 tests across 3 files in `tests/`
- Tests mock `ctypes.windll` and `rtmidi` — no hardware needed
- Run `pytest` from project root

## Platform

Windows-only (ctypes.windll / DirectInput). CI runs on `windows-latest`.
