# Cyber Qin

**Play a real piano, and the game character plays in sync.**

[![CI](https://github.com/EdmondVirelle/cyber-qin/actions/workflows/ci.yml/badge.svg)](https://github.com/EdmondVirelle/cyber-qin/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![Version](https://img.shields.io/badge/Version-0.8.0-green)
![Tests](https://img.shields.io/badge/Tests-180%20passed-brightgreen)

[中文說明 (Traditional Chinese)](README_TW.md)

---

## Introduction

**Cyber Qin** is a real-time MIDI-to-Keyboard mapping tool designed for games like *Where Winds Meet*. It converts signals from a USB MIDI keyboard (e.g., Roland FP-30X) into DirectInput scan codes with **< 2ms latency**, allowing your in-game character to perform in perfect sync with your real-world playing.

It supports both real-time performance and MIDI file auto-playback modes. Built-in features include an intelligent preprocessing pipeline for transposition, octave folding, and collision deduplication, along with 5 switchable key mapping schemes.

---

## Demo

> ![Demo Screenshot](docs/screenshot-placeholder.png)
>
> *Real-time Performance Mode — Visualized Piano Keyboard + Low-Latency Monitoring*

---

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Real-time MIDI Mapping** | MIDI callbacks trigger `SendInput` directly on the rtmidi thread, bypassing the Qt event queue for < 2ms latency. |
| **5 Key Schemes** | Includes *Where Winds Meet* (36-key), FF14 (32-key), and generic 24/48/88-key layouts, switchable at runtime. |
| **Smart Preprocessing** | 3-stage pipeline: Smart Transposition → Octave Folding → Collision Deduplication (see [Tech Deep Dive](#tech-deep-dive)). |
| **MIDI Auto-Playback** | Import `.mid` files with 0.25x - 2.0x speed control, draggable progress bar, and 4-beat countdown. |
| **Modifier Flash Tech** | Sends `Shift↓ → Key↓ → Shift↑` as a single batch to prevent modifier keys from polluting subsequent chords. |
| **Auto-Reconnect** | Polls every 3 seconds if the MIDI device disconnects and automatically restores connection upon reconnection. |
| **Anti-Stuck Watchdog** | Detects keys held for more than 10 seconds and automatically releases them to prevent in-game character lock-ups. |

### User Interface

| Feature | Description |
|---------|-------------|
| **Cyber Ink Theme** | Wuxia Cyberpunk dark theme featuring Neon Cyan (`#00F0FF`) + Rice Paper White warm tones. |
| **Vector Icons** | All icons drawn via `QPainter` with no external image dependencies, scaling perfectly at any resolution. |
| **Dynamic Piano** | Real-time key state visualization with neon glow animation effects. |
| **Library Management** | Import, search, and sort tracks by Name, BPM, Note Count, or Duration. |
| **Player Bar** | Spotify-style bottom bar with mini-piano, progress slider, and speed controls. |

---

## System Architecture

### Data Flow

```
                          Real-time Mode
┌─────────────┐    USB    ┌──────────────┐  callback  ┌───────────┐  lookup  ┌──────────────┐  SendInput  ┌──────┐
│ Roland FP-30X│─────────→│ python-rtmidi │──────────→│ KeyMapper │────────→│ KeySimulator │───────────→│ Game │
└─────────────┘           └──────────────┘            └───────────┘         └──────────────┘            └──────┘
                            (rtmidi thread)                                  (scan codes)
                                  │
                           Qt signals (async)
                                  │
                         Qt Main Thread → GUI Update


                          Auto-Playback Mode
┌───────────┐  parse  ┌─────────────────┐  preprocess  ┌──────────────────┐  timed events  ┌──────────────┐
│ .mid File │────────→│ MidiFileParser  │────────────→│ MidiPreprocessor │──────────────→│ PlaybackWorker│
└───────────┘         └─────────────────┘              └──────────────────┘               └──────┬───────┘
                                                                                                 │
                                                              lookup + SendInput                 │
                                                       ┌───────────┬──────────────┐←────────────┘
                                                       │ KeyMapper │ KeySimulator │→ Game
                                                       └───────────┴──────────────┘
```

### Latency Optimization Path

```
MIDI Note On Signal
    │
    ├── [rtmidi C++ thread] ← SetThreadPriority(TIME_CRITICAL)
    │       │
    │       ├── KeyMapper.lookup()        ~0.01ms  (dict lookup)
    │       ├── KeySimulator.press()      ~0.05ms  (SendInput syscall)
    │       └── Qt signal emit            ~0.00ms  (Cross-thread queue, async)
    │
    └── Total Latency: < 2ms (MIDI USB polling + callback + SendInput)

    ※ GUI updates use the Qt signal queue and do not block the critical path.
```

---

## Tech Stack

| Layer | Technology | Usage |
|-------|------------|-------|
| **MIDI I/O** | `mido` + `python-rtmidi` | MIDI device communication, `.mid` file parsing. |
| **Input Sim** | `ctypes` + Win32 `SendInput` | DirectInput scan code injection. |
| **GUI** | PyQt6 | Desktop interface, event loop, cross-thread signals. |
| **Build** | PyInstaller | Single-folder executable packaging. |
| **CI/CD** | GitHub Actions | Multi-version testing + automated tag releases. |
| **Quality** | Ruff + pytest | Linting + 180 tests. |

---

## Quick Start

### System Requirements

- **OS**: Windows 10 / 11 (DirectInput scan codes are Windows-only).
- **Python**: 3.11 or higher.
- **MIDI Device**: Any USB MIDI keyboard (tested with Roland FP-30X).
- **Permissions**: Must run as **Administrator** (`SendInput` requires elevation for DirectInput games).

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/EdmondVirelle/cyber-qin.git
cd cyber-qin

# 2. Install (with dev dependencies)
pip install -e .[dev]
```

### Usage

```bash
# Run as Administrator
cyber-qin
```

> **Tip**: If not run as Administrator, key injection into full-screen DirectInput games will fail silently.

### Build Standalone Executable

```bash
python scripts/build.py
# Output: dist/CyberQin/ (~95 MB)
```

---

## Development

### Testing

```bash
# Run all 180 tests (5 test files)
pytest

# Verbose output
pytest -v
```

Tests fully mock `ctypes.windll` and `rtmidi`, allowing execution without physical hardware.

### Linting

```bash
# Check
ruff check .

# Auto-fix
ruff check --fix .
```

### Project Stats

| Metric | Value |
|--------|-------|
| Source Lines | ~5,000 LOC |
| Modules | 26 |
| Tests | 180 |
| Test Files | 5 |
| Platforms | Python 3.11 / 3.12 / 3.13 |

---

## Project Structure

```
cyber_qin/
├── core/                        # Platform-agnostic core logic
│   ├── constants.py             # Win32 scan codes, MIDI ranges, timing constants
│   ├── key_mapper.py            # MIDI Note → Key Mapping lookup
│   ├── key_simulator.py         # ctypes SendInput wrapper (DirectInput scan codes)
│   ├── midi_listener.py         # python-rtmidi real-time input + auto-reconnect
│   ├── midi_file_player.py      # MIDI file playback engine (precision timing + countdown)
│   ├── midi_preprocessor.py     # Smart transposition + octave folding + deduplication pipeline
│   ├── mapping_schemes.py       # Registry for the 5 switchable key schemes
│   └── priority.py              # Thread priority + High-resolution timer
├── gui/                         # PyQt6 User Interface
│   ├── app_shell.py             # QMainWindow Main Frame (Spotify-style layout)
│   ├── icons.py                 # QPainter vector icon provider
│   ├── theme.py                 # "Cyber Ink" dark theme system
│   ├── views/
│   │   ├── live_mode_view.py    # Real-time performance view
│   │   └── library_view.py      # Library management view
│   └── widgets/
│       ├── piano_display.py     # Dynamic piano keyboard (Neon glow effects)
│       ├── mini_piano.py        # Bottom mini-piano visualization
│       ├── sidebar.py           # Sidebar navigation
│       ├── now_playing_bar.py   # Bottom playback control bar
│       ├── track_list.py        # Track list component
│       ├── progress_bar.py      # Draggable progress bar
│       ├── speed_control.py     # Playback speed controller
│       ├── log_viewer.py        # Real-time event log
│       ├── status_bar.py        # Status bar
│       └── animated_widgets.py  # Base animation components
└── utils/
    ├── admin.py                 # UAC elevation check
    └── ime.py                   # IME detection
```

---

## Tech Deep Dive

### 1. Latency Optimization: Why bypass the Qt Event Queue?

The core requirement for game performance is **low latency** — the imperceptible limit from key press to in-game sound is about 10ms.

Typical architectures pass MIDI events to the main thread via Qt signals, but the Qt event queue can introduce 5-15ms of extra latency when the GUI is busy (e.g., repainting animations).

This project executes keyboard simulation **directly on the rtmidi C++ callback thread**:

```python
# app_shell.py — MidiProcessor.on_midi_event()
# This function runs on the rtmidi callback thread

def on_midi_event(self, event_type, note, velocity):
    # 1. Boost thread priority on first call
    if not self._priority_set:
        set_thread_priority_realtime()  # TIME_CRITICAL
        self._priority_set = True

    # 2. Critical Path: Lookup + SendInput (< 0.1ms)
    if event_type == "note_on":
        mapping = self._mapper.lookup(note)      # dict lookup
        if mapping is not None:
            self._simulator.press(note, mapping)  # SendInput syscall

    # 3. GUI updates via async signal (Doesn't block critical path)
    self.note_event.emit(event_type, note, velocity)
```

Combined with `timeBeginPeriod(1)` to lower system timer resolution to 1ms and `SetThreadPriority(TIME_CRITICAL)` to boost scheduling priority, end-to-end latency is kept < 2ms.

### 2. Modifier Flash Technology

The game's 36-key mode uses Shift / Ctrl modifiers for sharps/flats. If Shift is pressed before the Key in a chord, Shift might "leak" to other notes pressed simultaneously, causing misinterpretation.

Solution: Wrap the press and release of the modifier key **in a single `SendInput` batch call**:

```python
# key_simulator.py — KeySimulator.press()

def press(self, midi_note, mapping):
    mod_scan = _modifier_scan(mapping.modifier)
    if mod_scan is not None:
        # Send three events as an atomic batch
        _send(
            _make_input(mod_scan, key_up=False),           # Shift ↓
            _make_input(mapping.scan_code, key_up=False),  # Key ↓
            _make_input(mod_scan, key_up=True),            # Shift ↑
        )
    else:
        _send(_make_input(mapping.scan_code, key_up=False))
```

`SendInput` guarantees that events in the same batch are not interleaved with input from other processes, ensuring the modifier's scope is precisely limited to a single key.

### 3. Smart MIDI Preprocessing Pipeline

Adapting arbitrary MIDI files to the game's limited range (e.g., 36 keys = C3-B5) requires an automated note conversion pipeline:

```
Raw MIDI Events
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Stage 1: Smart Transposition                           │
│ Try -48 ~ +48 semitones (multiples of 12). Select the  │
│ offset that fits the most notes into playable range.   │
│ Tie-break using smallest absolute offset.              │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Stage 2: Octave Folding                                │
│ Remaining out-of-range notes are folded ±12 semitones  │
│ until they fit within range.                           │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Stage 3: Collision Deduplication                       │
│ Folding may produce duplicate notes (same time/pitch). │
│ Remove duplicates, keeping the last note_off (sustain).│
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Stage 4: Velocity Normalization                        │
│ All note_on velocities set to 127 (game ignores vel).  │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Stage 5: 60fps Quantization                            │
│ Align events to ~16.67ms grid to eliminate micro-lag.  │
└──────────────────────────────────────────────────────┘
    │
    ▼
Processed Events (Sorted by time, note_off priority)
```

### 4. ctypes INPUT Structure Trap

The Windows `SendInput` API requires the `INPUT` structure size to be exactly 40 bytes (64-bit). The structure uses a union containing `MOUSEINPUT`, `KEYBDINPUT`, and `HARDWAREINPUT`.

If the union **omits the largest member `MOUSEINPUT`** (32 bytes), `sizeof(INPUT)` becomes 32 instead of 40, causing `SendInput` to **silently return 0** and send no input — no error, no exception, just completely ineffective.

```python
# Must include MOUSEINPUT as a union member
class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [
            ("mi", MOUSEINPUT),      # ← Largest member determines union size
            ("ki", KEYBDINPUT),
            ("hi", HARDWAREINPUT),
        ]
    _anonymous_ = ("_union",)
    _fields_ = [("type", ctypes.wintypes.DWORD), ("_union", _INPUT_UNION)]
```

---

## Mapping Schemes

| Scheme | Keys | MIDI Range | Layout | Target Game |
|--------|------|------------|--------|-------------|
| **Where Winds Meet 36-Key** | 36 | C3 - B5 | 3 x 12 (ZXC / ASD / QWE + Shift/Ctrl) | Where Winds Meet |
| **FF14 37-Key** | 37 | C3 - C6 | 3×12 Diatonic (Nums/QWER/ASDF) | Final Fantasy XIV |
| **Generic 24-Key** | 24 | C3 - B4 | 2 x 12 (ZXC / QWE + Shift/Ctrl) | Generic |
| **Generic 48-Key** | 48 | C2 - B5 | 4 x 12 (Num Row / ZXC / ASD / QWE) | Generic |
| **Generic 88-Key** | 88 | A0 - C8 | 8 x 11 (Multi-layer Shift/Ctrl combos) | Generic (Full Piano) |

---

## Acknowledgments

- [mido](https://github.com/mido/mido) — Python MIDI library
- [python-rtmidi](https://github.com/SpotlightKid/python-rtmidi) — Low-latency cross-platform MIDI I/O
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — Python Qt 6 bindings
- [PyInstaller](https://pyinstaller.org/) — Python application packaging tool
- [Ruff](https://github.com/astral-sh/ruff) — Extremely fast Python linter
- *Where Winds Meet* — Wuxia open-world game developed by Everstone Studio (NetEase)
