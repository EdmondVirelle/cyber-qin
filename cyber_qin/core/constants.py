"""Scan codes, MIDI range constants, and Modifier enum."""

from enum import IntEnum, auto


class Modifier(IntEnum):
    """Modifier key type for game key combinations."""
    NONE = auto()
    SHIFT = auto()
    CTRL = auto()


# Windows scan codes (Set 1) for keys used by the game.
# Reference: https://www.win.tue.nl/~aeb/linux/kbd/scancodes-1.html
SCAN = {
    # Low octave row
    "Z": 0x2C,
    "X": 0x2D,
    "C": 0x2E,
    "V": 0x2F,
    "B": 0x30,
    "N": 0x31,
    "M": 0x32,
    # Mid octave row
    "A": 0x1E,
    "S": 0x1F,
    "D": 0x20,
    "F": 0x21,
    "G": 0x22,
    "H": 0x23,
    "J": 0x24,
    # High octave row
    "Q": 0x10,
    "W": 0x11,
    "E": 0x12,
    "R": 0x13,
    "T": 0x14,
    "Y": 0x15,
    "U": 0x16,
    # Modifiers
    "LSHIFT": 0x2A,
    "LCTRL": 0x1D,
    # Special
    "ESCAPE": 0x01,
}

# MIDI note range the game maps to (before transpose)
MIDI_NOTE_MIN = 48  # C3
MIDI_NOTE_MAX = 83  # B5
MIDI_RANGE = range(MIDI_NOTE_MIN, MIDI_NOTE_MAX + 1)

# Transpose step size (one octave)
TRANSPOSE_STEP = 12
TRANSPOSE_MIN = -24
TRANSPOSE_MAX = 24

# Stuck-key watchdog timeout in seconds
STUCK_KEY_TIMEOUT = 10.0

# Reconnect polling interval in seconds
RECONNECT_INTERVAL = 3.0

# SendInput constants
INPUT_KEYBOARD = 1
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002

# File playback
DEFAULT_PLAYBACK_SPEED = 1.0
MIN_PLAYBACK_SPEED = 0.25
MAX_PLAYBACK_SPEED = 2.0
PLAYBACK_SPEED_PRESETS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
