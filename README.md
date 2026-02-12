# Cyber Qin

**Play a real piano, and your game character plays in sync.**

[![CI](https://github.com/EdmondVirelle/cyber-qin/actions/workflows/ci.yml/badge.svg)](https://github.com/EdmondVirelle/cyber-qin/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![Version](https://img.shields.io/badge/Version-0.9.0-green)
![Tests](https://img.shields.io/badge/Tests-180%20passed-brightgreen)

[中文版 (Traditional Chinese)](README_TW.md)

---

## Introduction

**Cyber Qin** is a real-time MIDI-to-Keyboard mapping tool designed for games. It converts signals from a USB MIDI keyboard into DirectInput scan codes with **< 2ms latency**, allowing your in-game character to perform in perfect sync with your real-world playing.

Supported games include:
- **Where Winds Meet** (燕雲十六聲) — 36 keys
- **Final Fantasy XIV** (FF14) — 37 keys
- **Other Games** — Generic 24 / 48 / 88 keys schemes

Beyond live performance, it also supports **Automatic MIDI Playback** and an integrated **MIDI Editor (Sequencer)**.

---

## Features

### Live Mode
| Feature | Description |
|------|------|
| **Real-time MIDI Mapping** | Direct MIDI-to-SendInput injection on rtmidi C++ thread for < 2ms latency |
| **5 Mapping Schemes** | WWM 36 / FF14 37 / Generic 24 / 48 / 88 schemes, switchable on the fly |
| **Smart Preprocessing** | Auto Transpose → Octave Folding → Collision Deduplication |
| **Auto Reconnect** | Detects and reconnects MIDI devices every 3 seconds if disconnected |
| **Watchdog** | Automatically releases keys stuck for more than 10 seconds |

### Library (MIDI Playback)
| Feature | Description |
|------|------|
| **Import MIDI** | Drag and drop or import .mid files into the library |
| **Speed Control** | Adjustable playback speed from 0.25x to 2.0x |
| **Seek Bar** | Jump to any position in the track |
| **4-Beat Countdown** | Countdown before playback to allow switching to the game window |
| **Sort & Search** | Sort by Name/BPM/Notes/Duration with search functionality |

### Sequencer (MIDI Editor)
| Feature | Description |
|------|------|
| **Piano Roll Editing** | Intuitive piano roll for drawing, selecting, and deleting notes |
| **Playback Cursor** | Smooth cursor (30ms refresh) with dynamic glow feedback |
| **Multi-track Export** | Supports Type 1 multi-track MIDI file export |
| **Shortcuts** | Full hotkey support (with built-in help dialog) |

### UI
| Feature | Description |
|------|------|
| **Cyber-Ink Theme** | Dark theme: Neon Cyan (#00F0FF) mixed with warm paper-white tones |
| **Vector Icons** | All icons drawn via QPainter for perfect scaling at any resolution |
| **Dynamic Piano** | Real-time key state visualization with neon glow animations |
| **Multi-Language** | Switch between Traditional Chinese / Simplified Chinese / English / Japanese / Korean |
| **Spotify-style Bar** | Bottom transport bar with mini-piano, progress seek, and speed control |

---

## Usage

### System Requirements
- **OS**: Windows 10 / 11
- **Python**: 3.11+
- **MIDI Device**: Any USB MIDI keyboard (Tested with Roland FP-30X)
- **Privileges**: Must run as **Administrator** (SendInput requires elevated permissions)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/EdmondVirelle/cyber-qin.git
cd cyber-qin

# 2. Install dependencies
pip install -e .[dev]
```

### Starting

```bash
# Run as Administrator
cyber-qin
```

> **Tip**: If not running as Administrator, key injection in games will silently fail.

### Workflow

1. **Connect Keyboard** — Select your MIDI device in "Live Mode" after startup
2. **Select Scheme** — Choose the scheme corresponding to your game (WWM/FF14/Generic)
3. **Perform** — Switch to your game window and start playing
4. **Library** — Go to "Library" to import .mid files and play with speed control
5. **Sequencer** — Go to "Sequencer" to edit notes and export modified MIDI

### Building Executable

```bash
python scripts/build.py
# Output: dist/CyberQin/ (~95 MB)
```

---

## Mapping Schemes

| Scheme | Keys | MIDI Range | Layout | Target Game |
|--------|------|------------|--------|-------------|
| **WWM 36-Key** | 36 | C3 - B5 | 3×12 (ZXC / ASD / QWE + Shift/Ctrl) | Where Winds Meet |
| **FF14 37-Key** | 37 | C3 - C6 | 3×12 Diatonic (Nums/QWER/ASDF) | Final Fantasy XIV |
| **Generic 24-Key** | 24 | C3 - B4 | 2×12 (ZXC row + QWE row, Shift/Ctrl for accidentals) | Generic |
| **Generic 48-Key** | 48 | C2 - B5 | 4×12 (Numbers / ZXC / ASD / QWE) | Generic |
| **Generic 88-Key** | 88 | A0 - C8 | 8×11 (Layered Shift/Ctrl combos, full range) | Generic (Full Piano) |

---

## Architecture

### Data Flow

```
                          Live Mode
┌─────────────┐    USB    ┌──────────────┐  callback  ┌───────────┐  lookup  ┌──────────────┐  SendInput  ┌──────┐
│ MIDI Keyboard│─────────→│ python-rtmidi │──────────→│ KeyMapper │────────→│ KeySimulator │───────────→│ Game │
└─────────────┘           └──────────────┘            └───────────┘         └──────────────┘            └──────┘
                            (rtmidi thread)                                  (scan codes)


                          Playback Mode
┌───────────┐  parse  ┌─────────────────┐  preprocess  ┌──────────────────┐  timed events  ┌──────────────┐
│ .mid File │────────→│ MidiFileParser  │────────────→│ MidiPreprocessor │──────────────→│ PlaybackWorker│
└───────────┘         └─────────────────┘              └──────────────────┘               └──────┬───────┘
                                                                                                 │
                                                               lookup + SendInput                 │
                                                       ┌───────────┬──────────────┐←────────────┘
                                                       │ KeyMapper │ KeySimulator │→ Game
                                                       └───────────┴──────────────┘
```

---

## Development

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on code style, testing, and contribution workflow.


### Testing

```bash
# Run all 180 tests
pytest

# Verbose output
pytest -v
```

### Linting

```bash
ruff check .
ruff check --fix .
```

### Statistics

| Metric | Value |
|------|------|
| Lines of Code | ~5,000 LOC |
| Modules | 26 |
| Tests | 180 |
| Python Support | 3.11 / 3.12 / 3.13 |

---

## Tech Stack

| Layer | Technology | Purpose |
|------|------|------|
| **MIDI I/O** | `mido` + `python-rtmidi` | Device communication & MIDI parsing |
| **Simulation** | `ctypes` + Win32 `SendInput` | DirectInput scan code injection |
| **GUI** | PyQt6 | Desktop interface, event loop, cross-thread signals |
| **Bundling** | PyInstaller | Single-folder executable packaging |
| **CI/CD** | GitHub Actions | Automated tagging & multi-platform testing |
| **Quality** | Ruff + pytest | Linting & 180 unit/integration tests |

---

## Acknowledgments

- [mido](https://github.com/mido/mido) — Python MIDI library
- [python-rtmidi](https://github.com/SpotlightKid/python-rtmidi) — Low-latency cross-platform MIDI I/O
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — Python Qt 6 bindings
- [PyInstaller](https://pyinstaller.org/) — Python application packaging tool
- [Ruff](https://github.com/astral-sh/ruff) — Extremely fast Python linter
- *Where Winds Meet* — 燕雲十六聲 (Everstone Studio / NetEase)
- *Final Fantasy XIV* — FF14 (Square Enix)

---

## Disclaimer

This tool is an open-source personal project for MIDI music performance enthusiasts.
Using third-party tools in games may violate the game's Terms of Service. Please use at your own risk.
The developer is not responsible for any account penalties or losses resulting from the use of this tool.

---

**Sponsor**: [Ko-fi](https://ko-fi.com/virelleedmond)
