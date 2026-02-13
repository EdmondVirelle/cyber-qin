"""36-key mapping table and lookup for MIDI note → game key combination."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import SCAN, Modifier

if TYPE_CHECKING:
    from .mapping_schemes import MappingScheme


@dataclass(frozen=True, slots=True)
class KeyMapping:
    """A single game key action: base scan code + optional modifier."""

    scan_code: int
    modifier: Modifier
    label: str  # Human-readable label, e.g. "Shift+Z"


def _km(key: str, modifier: Modifier = Modifier.NONE) -> KeyMapping:
    """Helper to build a KeyMapping from key name and modifier."""
    scan = SCAN[key]
    if modifier == Modifier.SHIFT:
        label = f"Shift+{key}"
    elif modifier == Modifier.CTRL:
        label = f"Ctrl+{key}"
    else:
        label = key
    return KeyMapping(scan_code=scan, modifier=modifier, label=label)


# Complete 36-key mapping: MIDI note number → KeyMapping.
# Low octave (C3-B3): Z X C V B N M row
# Mid octave (C4-B4): A S D F G H J row
# High octave (C5-B5): Q W E R T Y U row
_BASE_MAP: dict[int, KeyMapping] = {
    # --- Low octave (MIDI 48-59) ---
    48: _km("Z"),  # C3
    49: _km("Z", Modifier.SHIFT),  # C#3
    50: _km("X"),  # D3
    51: _km("C", Modifier.CTRL),  # Eb3
    52: _km("C"),  # E3
    53: _km("V"),  # F3
    54: _km("V", Modifier.SHIFT),  # F#3
    55: _km("B"),  # G3
    56: _km("B", Modifier.SHIFT),  # G#3
    57: _km("N"),  # A3
    58: _km("M", Modifier.CTRL),  # Bb3
    59: _km("M"),  # B3
    # --- Mid octave (MIDI 60-71) ---
    60: _km("A"),  # C4
    61: _km("A", Modifier.SHIFT),  # C#4
    62: _km("S"),  # D4
    63: _km("D", Modifier.CTRL),  # Eb4
    64: _km("D"),  # E4
    65: _km("F"),  # F4
    66: _km("F", Modifier.SHIFT),  # F#4
    67: _km("G"),  # G4
    68: _km("G", Modifier.SHIFT),  # G#4
    69: _km("H"),  # A4
    70: _km("J", Modifier.CTRL),  # Bb4
    71: _km("J"),  # B4
    # --- High octave (MIDI 72-83) ---
    72: _km("Q"),  # C5
    73: _km("Q", Modifier.SHIFT),  # C#5
    74: _km("W"),  # D5
    75: _km("E", Modifier.CTRL),  # Eb5
    76: _km("E"),  # E5
    77: _km("R"),  # F5
    78: _km("R", Modifier.SHIFT),  # F#5
    79: _km("T"),  # G5
    80: _km("T", Modifier.SHIFT),  # G#5
    81: _km("Y"),  # A5
    82: _km("U", Modifier.CTRL),  # Bb5
    83: _km("U"),  # B5
}


class KeyMapper:
    """Translates MIDI note numbers to game key combinations.

    Supports octave-based transpose and switchable mapping schemes.
    Notes outside the valid range after transpose return None from lookup().
    """

    def __init__(self, transpose: int = 0, scheme: MappingScheme | None = None) -> None:
        self._transpose = transpose
        self._scheme: MappingScheme | None
        if scheme is not None:
            self._scheme = scheme
            self._mapping = scheme.mapping
        else:
            self._scheme = None
            self._mapping = _BASE_MAP

    @property
    def transpose(self) -> int:
        return self._transpose

    @transpose.setter
    def transpose(self, value: int) -> None:
        self._transpose = value

    @property
    def scheme(self) -> MappingScheme | None:
        """Return the currently active scheme, or None if using _BASE_MAP default."""
        return self._scheme

    def set_scheme(self, scheme: MappingScheme) -> None:
        """Atomically switch to a new mapping scheme.

        CPython's GIL guarantees that the dict reference swap is atomic,
        so rtmidi callbacks reading self._mapping won't see a torn pointer.
        """
        self._scheme = scheme
        self._mapping = scheme.mapping

    def lookup(self, midi_note: int) -> KeyMapping | None:
        """Map a MIDI note to a KeyMapping, applying transpose.

        Returns None if the transposed note is out of the mapping range.
        """
        mapped = midi_note + self._transpose
        return self._mapping.get(mapped)

    def current_mappings(self) -> dict[int, KeyMapping]:
        """Return a copy of the current mapping table."""
        return dict(self._mapping)

    @staticmethod
    def note_name(midi_note: int) -> str:
        """Return the note name (e.g. 'C4') for a MIDI note number."""
        names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]
        octave = (midi_note // 12) - 1
        return f"{names[midi_note % 12]}{octave}"

    @staticmethod
    def all_mappings() -> dict[int, KeyMapping]:
        """Return a copy of the full base mapping table."""
        return dict(_BASE_MAP)

    @staticmethod
    def build_reverse_map(scheme: MappingScheme) -> dict[tuple[str, Modifier], int]:
        """Build reverse mapping from (key_letter, modifier) to MIDI note.

        Used for keyboard input mode in practice view.
        Parses KeyMapping.label to extract the base key letter and modifier.
        """
        reverse: dict[tuple[str, Modifier], int] = {}
        for midi_note, km in scheme.mapping.items():
            label = km.label
            if label.startswith("Shift+"):
                key_letter = label[6:]
                mod = Modifier.SHIFT
            elif label.startswith("Ctrl+"):
                key_letter = label[5:]
                mod = Modifier.CTRL
            else:
                key_letter = label
                mod = Modifier.NONE
            reverse[(key_letter, mod)] = midi_note
        return reverse
