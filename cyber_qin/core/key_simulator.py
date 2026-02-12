"""Win32 SendInput wrapper for scan-code keyboard simulation."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import time
from typing import TYPE_CHECKING

from .constants import (
    INPUT_KEYBOARD,
    KEYEVENTF_KEYUP,
    KEYEVENTF_SCANCODE,
    SCAN,
    STUCK_KEY_TIMEOUT,
    Modifier,
)

if TYPE_CHECKING:
    from .key_mapper import KeyMapping

# --- ctypes structures for SendInput ---
# The union must include MOUSEINPUT (the largest member) so that
# sizeof(INPUT) == 40 on 64-bit Windows.  Without it the struct is
# only 32 bytes and SendInput silently rejects every call (returns 0).


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.wintypes.DWORD),
        ("wParamL", ctypes.wintypes.WORD),
        ("wParamH", ctypes.wintypes.WORD),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    _anonymous_ = ("_union",)
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("_union", _INPUT_UNION),
    ]


_SendInput = ctypes.windll.user32.SendInput  # type: ignore[attr-defined]
_SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int]
_SendInput.restype = ctypes.c_uint


def _make_input(scan_code: int, key_up: bool = False) -> INPUT:
    """Create an INPUT struct for a scan-code key event."""
    flags = KEYEVENTF_SCANCODE
    if key_up:
        flags |= KEYEVENTF_KEYUP
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = 0
    inp.ki.wScan = scan_code
    inp.ki.dwFlags = flags
    inp.ki.time = 0
    inp.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
    return inp


def _send(*inputs: INPUT) -> None:
    """Send an array of INPUT events via SendInput."""
    arr = (INPUT * len(inputs))(*inputs)
    _SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


def _modifier_scan(mod: Modifier) -> int | None:
    if mod == Modifier.SHIFT:
        return SCAN["LSHIFT"]
    if mod == Modifier.CTRL:
        return SCAN["LCTRL"]
    return None


class KeySimulator:
    """Manages key press/release sequences with modifier support.

    Thread-safe for concurrent calls from the rtmidi callback thread.
    Tracks active keys for proper Note_Off handling and stuck-key watchdog.
    """

    def __init__(self) -> None:
        # midi_note → (KeyMapping, press_time)
        self._active: dict[int, tuple[KeyMapping, float]] = {}

    def press(self, midi_note: int, mapping: KeyMapping) -> None:
        """Execute key-down for a MIDI note.

        Sequence for modified keys: modifier_down → key_down → modifier_up
        The modifier is "flashed" — only held for the instant of the key press.
        This prevents Shift/Ctrl from leaking into subsequent chord notes.
        """
        mod_scan = _modifier_scan(mapping.modifier)
        if mod_scan is not None:
            _send(
                _make_input(mod_scan, key_up=False),
                _make_input(mapping.scan_code, key_up=False),
                _make_input(mod_scan, key_up=True),
            )
        else:
            _send(_make_input(mapping.scan_code, key_up=False))
        self._active[midi_note] = (mapping, time.monotonic())

    def release(self, midi_note: int) -> KeyMapping | None:
        """Execute key-up for a MIDI note.

        Only releases the base key — modifier was already released in press().
        Returns the released KeyMapping, or None if the note wasn't active.
        """
        entry = self._active.pop(midi_note, None)
        if entry is None:
            return None
        mapping, _ = entry
        _send(_make_input(mapping.scan_code, key_up=True))
        return mapping

    def release_all(self) -> None:
        """Release all currently held keys. Used on disconnect or panic."""
        for midi_note in list(self._active):
            self.release(midi_note)

    def check_stuck_keys(self) -> list[int]:
        """Release keys held longer than STUCK_KEY_TIMEOUT.

        Returns list of MIDI notes that were force-released.
        """
        now = time.monotonic()
        stuck = [
            note for note, (_, t) in self._active.items()
            if now - t > STUCK_KEY_TIMEOUT
        ]
        for note in stuck:
            self.release(note)
        return stuck

    @property
    def active_notes(self) -> list[int]:
        """Return list of currently held MIDI notes."""
        return list(self._active)
