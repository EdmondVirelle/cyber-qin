# 賽博琴仙

MIDI-to-Keyboard mapper for 燕雲十六聲 (Where Winds Meet) 36-key performance mode.

Connect a MIDI keyboard (e.g. Roland FP-30X) and play the in-game instrument system with real piano keys. The app translates MIDI note events into DirectInput keystrokes with < 10 ms latency, including Shift/Ctrl modifier combos for sharps and flats.

## Features

- **36-key mapping** — three octaves (C3–B5) covering naturals, sharps, and flats
- **Live mode** — real-time MIDI-to-keystroke with on-screen piano display
- **Library mode** — load and auto-play MIDI files
- **Transpose** — shift octaves on the fly
- **Auto-reconnect** — recovers when the MIDI device is unplugged

## Requirements

- Windows 10/11 (DirectInput)
- Python 3.11+
- A USB-MIDI keyboard

## Install

```bash
pip install -e .[dev]
```

## Usage

Run as administrator (required for DirectInput injection):

```bash
cyber-qin
```

## Development

```bash
# Run tests
pytest

# Lint
ruff check .
```

## License

[MIT](LICENSE)
