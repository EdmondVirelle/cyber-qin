"""Standard notation renderer — MIDI to staff notation data model.

Converts MIDI note data into staff positions, note heads, stems, beams,
bar lines, and other notation primitives.  The GUI layer (ScoreViewWidget)
renders these via QPainter.  This module is pure Python (no Qt).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

# ── Enums ─────────────────────────────────────────────────


class NoteHeadType(IntEnum):
    WHOLE = 0  # 4 beats
    HALF = 1  # 2 beats
    QUARTER = 2  # 1 beat
    EIGHTH = 3  # 0.5 beats
    SIXTEENTH = 4  # 0.25 beats


class StemDirection(IntEnum):
    UP = 0
    DOWN = 1


class Accidental(IntEnum):
    NONE = 0
    SHARP = 1
    FLAT = 2
    NATURAL = 3


# ── Data classes ──────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class StaffPosition:
    """Position on the staff relative to the middle line (B4 = line 3).

    ``line`` is in half-staff-space units: 0 = bottom line (E4),
    increasing upward.  Negative = below staff, >8 = above staff.
    """

    line: int  # staff line/space index (0 = bottom line E4)
    accidental: Accidental = Accidental.NONE
    ledger_lines: int = 0  # positive = above, negative = below


@dataclass
class NotationNote:
    """A single rendered note on the staff."""

    x_beats: float  # horizontal position in beats
    staff_pos: StaffPosition
    head_type: NoteHeadType
    stem_dir: StemDirection
    duration_beats: float
    midi_note: int
    velocity: int = 100
    beam_group: int = -1  # -1 = no beam
    dot: bool = False  # dotted note
    tie_to_next: bool = False


@dataclass
class BarLine:
    """A bar line at a specific beat position."""

    x_beats: float
    is_double: bool = False


@dataclass
class NotationData:
    """Complete notation data for rendering."""

    notes: list[NotationNote] = field(default_factory=list)
    bar_lines: list[BarLine] = field(default_factory=list)
    key_signature: int = 0  # number of sharps (+) or flats (-)
    time_signature: tuple[int, int] = (4, 4)
    total_beats: float = 0.0


# ── Note name / staff mapping ─────────────────────────────

# MIDI note → (note_name, octave, needs_sharp)
# Using sharps by default; key signature handling can override
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Staff position mapping: C4 (MIDI 60) is one ledger line below the treble staff
# Treble clef bottom line = E4 (MIDI 64), line index 0
# Each step = 1 diatonic note = half a staff space
#
# Note name → diatonic offset within octave (C=0, D=1, E=2, F=3, G=4, A=5, B=6)
_DIATONIC_OFFSET = {
    0: 0,  # C
    1: 0,  # C#
    2: 1,  # D
    3: 1,  # D#
    4: 2,  # E
    5: 3,  # F
    6: 3,  # F#
    7: 4,  # G
    8: 4,  # G#
    9: 5,  # A
    10: 5,  # A#
    11: 6,  # B
}

# Sharps: pitch classes that need a sharp accidental in C major
_SHARP_PCS = {1, 3, 6, 8, 10}

# Key signature sharps/flats (number of sharps if positive, flats if negative)
# Maps to set of pitch classes that are altered
_KEY_SIG_SHARPS_ORDER = [6, 1, 8, 3, 10, 5, 0]  # F#, C#, G#, D#, A#, E#, B#
_KEY_SIG_FLATS_ORDER = [10, 3, 8, 1, 6, 11, 4]  # Bb, Eb, Ab, Db, Gb, Cb, Fb


def midi_to_staff_position(midi_note: int, key_sig: int = 0) -> StaffPosition:
    """Convert a MIDI note number to a treble clef staff position.

    Parameters
    ----------
    midi_note : int
        MIDI note number (0-127).
    key_sig : int
        Key signature: positive = sharps, negative = flats.

    Returns
    -------
    StaffPosition
    """
    pc = midi_note % 12
    octave = midi_note // 12 - 1  # MIDI octave convention: C4 = 60 → octave 4

    # Diatonic position relative to C in the same octave
    diatonic = _DIATONIC_OFFSET[pc]

    # Staff line: E4 (MIDI 64) = line 0 (bottom line of treble clef)
    # E4 = octave 4, diatonic 2
    # line = (octave - 4) * 7 + diatonic - 2
    line = (octave - 4) * 7 + diatonic - 2

    # Accidental
    accidental = Accidental.NONE
    if key_sig >= 0:
        # Sharp key: check if this PC needs a sharp
        key_sharps = set(_KEY_SIG_SHARPS_ORDER[:key_sig])
        if pc in _SHARP_PCS:
            if pc in key_sharps:
                accidental = Accidental.NONE  # in key signature
            else:
                accidental = Accidental.SHARP
    else:
        # Flat key: check if this PC needs a flat
        if pc in {p - 1 for p in _KEY_SIG_FLATS_ORDER[: abs(key_sig)]}:
            accidental = Accidental.NONE  # in key signature
        elif pc in _SHARP_PCS:
            accidental = Accidental.SHARP

    # Ledger lines
    ledger = 0
    if line < 0:
        ledger = (line - 1) // 2  # negative ledger lines below
    elif line > 8:
        ledger = (line - 8 + 1) // 2  # positive ledger lines above

    return StaffPosition(line=line, accidental=accidental, ledger_lines=ledger)


def duration_to_head_type(duration_beats: float) -> tuple[NoteHeadType, bool]:
    """Map a duration in beats to a note head type and dotted flag.

    Returns (head_type, is_dotted).
    """
    if duration_beats >= 3.0:
        return NoteHeadType.WHOLE, duration_beats >= 6.0
    if duration_beats >= 1.5:
        return NoteHeadType.HALF, duration_beats >= 3.0
    if duration_beats >= 0.75:
        return NoteHeadType.QUARTER, duration_beats >= 1.5
    if duration_beats >= 0.375:
        return NoteHeadType.EIGHTH, duration_beats >= 0.75
    return NoteHeadType.SIXTEENTH, duration_beats >= 0.375


def stem_direction(staff_line: int) -> StemDirection:
    """Determine stem direction: up if below B4 (line 3), down if above."""
    if staff_line < 4:  # below middle line
        return StemDirection.UP
    return StemDirection.DOWN


# ── Beam grouping ─────────────────────────────────────────


def _assign_beam_groups(notes: list[NotationNote], beats_per_bar: float) -> None:
    """Assign beam groups to eighth and sixteenth notes within beats."""
    group_id = 0
    i = 0
    while i < len(notes):
        n = notes[i]
        if n.head_type >= NoteHeadType.EIGHTH:
            # Start a beam group within the same beat
            beat_start = (n.x_beats // 1.0) * 1.0  # floor to beat
            beat_end = beat_start + 1.0
            group_notes = [i]
            j = i + 1
            while j < len(notes):
                m = notes[j]
                if m.head_type >= NoteHeadType.EIGHTH and m.x_beats < beat_end:
                    group_notes.append(j)
                    j += 1
                else:
                    break

            if len(group_notes) >= 2:
                for idx in group_notes:
                    # Mutate beam_group (NotationNote is not frozen)
                    notes[idx].beam_group = group_id
                group_id += 1

            i = j
        else:
            i += 1


# ── Main Renderer ─────────────────────────────────────────


def render_notation(
    beat_notes: list,
    *,
    tempo_bpm: float = 120.0,
    time_signature: tuple[int, int] = (4, 4),
    key_signature: int = 0,
) -> NotationData:
    """Convert a list of BeatNote objects to notation data.

    Parameters
    ----------
    beat_notes : list[BeatNote]
        Notes from the editor sequence.
    tempo_bpm : float
        Tempo (for display only; positions are in beats).
    time_signature : tuple[int, int]
        Time signature.
    key_signature : int
        Key signature (positive = sharps, negative = flats).

    Returns
    -------
    NotationData
    """
    num, denom = time_signature
    beats_per_bar = num * (4.0 / denom)

    notation_notes: list[NotationNote] = []
    max_beat = 0.0

    for bn in beat_notes:
        staff_pos = midi_to_staff_position(bn.note, key_signature)
        head_type, dotted = duration_to_head_type(bn.duration_beats)
        stem_dir = stem_direction(staff_pos.line)

        notation_notes.append(
            NotationNote(
                x_beats=bn.time_beats,
                staff_pos=staff_pos,
                head_type=head_type,
                stem_dir=stem_dir,
                duration_beats=bn.duration_beats,
                midi_note=bn.note,
                velocity=bn.velocity,
                dot=dotted,
            )
        )

        end = bn.time_beats + bn.duration_beats
        if end > max_beat:
            max_beat = end

    # Sort by time
    notation_notes.sort(key=lambda n: (n.x_beats, n.midi_note))

    # Assign beam groups
    _assign_beam_groups(notation_notes, beats_per_bar)

    # Generate bar lines
    bar_lines: list[BarLine] = []
    import math

    num_bars = math.ceil(max_beat / beats_per_bar) if beats_per_bar > 0 else 0
    for b in range(num_bars + 1):
        bar_lines.append(
            BarLine(
                x_beats=b * beats_per_bar,
                is_double=(b == num_bars),
            )
        )

    return NotationData(
        notes=notation_notes,
        bar_lines=bar_lines,
        key_signature=key_signature,
        time_signature=time_signature,
        total_beats=max_beat,
    )
