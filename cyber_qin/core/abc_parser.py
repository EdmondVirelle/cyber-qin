"""ABC notation parser and exporter.

Supports a subset of ABC notation for import/export of simple melodies.
Reference: https://abcnotation.com/wiki/abc:standard:v2.1

Subset supported:
- Note names: C D E F G A B c d e f g a b
- Octave modifiers: , (down) and ' (up)
- Accidentals: ^ (sharp), _ (flat), = (natural)
- Duration: number after note (2 = double, /2 = half)
- Rests: z
- Bar lines: |
- Headers: X (index), T (title), M (meter), L (default length), K (key), Q (tempo)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .beat_sequence import BeatNote

# ── Note mapping ──────────────────────────────────────────

# ABC note → MIDI offset from C in the reference octave
_ABC_NOTE_MAP = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
    "c": 0,
    "d": 2,
    "e": 4,
    "f": 5,
    "g": 7,
    "a": 9,
    "b": 11,
}


@dataclass
class AbcParseResult:
    """Result of parsing an ABC notation string."""

    notes: list[BeatNote]
    title: str = ""
    tempo_bpm: int = 120
    time_signature: tuple[int, int] = (4, 4)
    key: str = "C"
    default_length: float = 0.125  # 1/8 note in beats relative to quarter


# ── Key signature → accidentals ───────────────────────────

_KEY_SHARPS: dict[str, set[str]] = {
    "C": set(),
    "Am": set(),
    "G": {"F"},
    "Em": {"F"},
    "D": {"F", "C"},
    "Bm": {"F", "C"},
    "A": {"F", "C", "G"},
    "F#m": {"F", "C", "G"},
    "E": {"F", "C", "G", "D"},
    "C#m": {"F", "C", "G", "D"},
    "B": {"F", "C", "G", "D", "A"},
    "G#m": {"F", "C", "G", "D", "A"},
    "F#": {"F", "C", "G", "D", "A", "E"},
    "D#m": {"F", "C", "G", "D", "A", "E"},
}

_KEY_FLATS: dict[str, set[str]] = {
    "F": {"B"},
    "Dm": {"B"},
    "Bb": {"B", "E"},
    "Gm": {"B", "E"},
    "Eb": {"B", "E", "A"},
    "Cm": {"B", "E", "A"},
    "Ab": {"B", "E", "A", "D"},
    "Fm": {"B", "E", "A", "D"},
    "Db": {"B", "E", "A", "D", "G"},
    "Bbm": {"B", "E", "A", "D", "G"},
}


def _key_accidentals(key: str) -> dict[str, int]:
    """Return note-name → semitone adjustment for the given key."""
    acc: dict[str, int] = {}
    sharps = _KEY_SHARPS.get(key)
    if sharps:
        for n in sharps:
            acc[n] = 1
    flats = _KEY_FLATS.get(key)
    if flats:
        for n in flats:
            acc[n] = -1
    return acc


# ── Parser ────────────────────────────────────────────────

# Regex for a single ABC note token
_NOTE_RE = re.compile(
    r"(?P<acc>[_^=]?)"  # accidental
    r"(?P<note>[a-gA-G])"  # note letter
    r"(?P<octave>[',]*)"  # octave modifiers
    r"(?P<dur>[0-9]*/?[0-9]*)"  # duration modifier
)

_REST_RE = re.compile(r"z(?P<dur>[0-9]*/?[0-9]*)")


def _parse_duration(dur_str: str, default_length: float) -> float:
    """Parse ABC duration modifier into beats."""
    if not dur_str:
        return default_length
    if "/" in dur_str:
        parts = dur_str.split("/")
        num = int(parts[0]) if parts[0] else 1
        den = int(parts[1]) if len(parts) > 1 and parts[1] else 2
        return default_length * num / den
    return default_length * int(dur_str)


def parse_abc(text: str) -> AbcParseResult:
    """Parse an ABC notation string into BeatNotes.

    Parameters
    ----------
    text : str
        ABC notation text (may include headers).

    Returns
    -------
    AbcParseResult
    """
    title = ""
    tempo_bpm = 120
    time_sig = (4, 4)
    key = "C"
    default_length = 0.5  # L:1/8 → 0.5 beats (eighth note = half a quarter)

    body_lines: list[str] = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        if len(line) > 1 and line[1] == ":":
            header = line[0].upper()
            value = line[2:].strip()
            if header == "T":
                title = value
            elif header == "M":
                parts = value.split("/")
                if len(parts) == 2:
                    try:
                        time_sig = (int(parts[0]), int(parts[1]))
                    except ValueError:
                        pass
            elif header == "L":
                parts = value.split("/")
                if len(parts) == 2:
                    try:
                        num, den = int(parts[0]), int(parts[1])
                        # Convert L:1/8 → beats: (1/8) / (1/4) = 0.5
                        default_length = (num / den) * 4.0
                    except (ValueError, ZeroDivisionError):
                        pass
            elif header == "K":
                key = value.split()[0] if value else "C"
            elif header == "Q":
                # Q:1/4=120 or Q:120
                if "=" in value:
                    tempo_str = value.split("=")[-1].strip()
                else:
                    tempo_str = value.strip()
                try:
                    tempo_bpm = int(tempo_str)
                except ValueError:
                    pass
        else:
            body_lines.append(line)

    # Parse body
    body = " ".join(body_lines)
    key_acc = _key_accidentals(key)
    notes: list[BeatNote] = []
    current_beat = 0.0

    # Tokenize: notes, rests, bar lines
    pos = 0
    while pos < len(body):
        ch = body[pos]

        # Skip whitespace and bar lines
        if ch in " \t|[]":
            pos += 1
            continue

        # Rest
        rest_match = _REST_RE.match(body, pos)
        if rest_match:
            dur = _parse_duration(rest_match.group("dur"), default_length)
            current_beat += dur
            pos = rest_match.end()
            continue

        # Note
        note_match = _NOTE_RE.match(body, pos)
        if note_match:
            acc_str = note_match.group("acc")
            note_letter = note_match.group("note")
            octave_str = note_match.group("octave")
            dur_str = note_match.group("dur")

            # Base octave: uppercase = octave 4 (C4=60), lowercase = octave 5
            base_octave = 4 if note_letter.isupper() else 5
            note_name = note_letter.upper()

            # Octave modifiers
            for ch_oct in octave_str:
                if ch_oct == "'":
                    base_octave += 1
                elif ch_oct == ",":
                    base_octave -= 1

            # MIDI note
            midi_note = (base_octave + 1) * 12 + _ABC_NOTE_MAP[note_name]

            # Accidentals
            if acc_str == "^":
                midi_note += 1
            elif acc_str == "_":
                midi_note -= 1
            elif acc_str == "=":
                pass  # natural — no key sig adjustment
            elif note_name in key_acc:
                midi_note += key_acc[note_name]

            midi_note = max(0, min(127, midi_note))

            dur = _parse_duration(dur_str, default_length)
            notes.append(
                BeatNote(
                    time_beats=current_beat,
                    duration_beats=dur,
                    note=midi_note,
                    velocity=100,
                    track=0,
                )
            )
            current_beat += dur
            pos = note_match.end()
            continue

        # Unknown character — skip
        pos += 1

    return AbcParseResult(
        notes=notes,
        title=title,
        tempo_bpm=tempo_bpm,
        time_signature=time_sig,
        key=key,
        default_length=default_length,
    )


# ── Export ────────────────────────────────────────────────

_MIDI_TO_ABC: dict[int, str] = {}
for _oct in range(0, 10):
    for _i, _name in enumerate(["C", "^C", "D", "^D", "E", "F", "^F", "G", "^G", "A", "^A", "B"]):
        _midi = (_oct + 1) * 12 + _i
        if 0 <= _midi <= 127:
            if _oct < 4:
                _abc = (
                    _name.replace("^", "^") + ("," * (4 - _oct - 1))
                    if _name[0].isupper()
                    else _name
                )
                if len(_name) > 1 and _name[0] == "^":
                    _base = _name[1]
                    _abc = "^" + _base + ("," * (4 - _oct - 1))
                else:
                    _abc = _name + ("," * (4 - _oct - 1))
            elif _oct == 4:
                _abc = _name
            elif _oct == 5:
                if len(_name) > 1 and _name[0] == "^":
                    _abc = "^" + _name[1].lower()
                else:
                    _abc = _name.lower()
            else:
                if len(_name) > 1 and _name[0] == "^":
                    _abc = "^" + _name[1].lower() + ("'" * (_oct - 5))
                else:
                    _abc = _name.lower() + ("'" * (_oct - 5))
            _MIDI_TO_ABC[_midi] = _abc


def export_abc(
    notes: list[BeatNote],
    *,
    title: str = "Untitled",
    tempo_bpm: int = 120,
    time_signature: tuple[int, int] = (4, 4),
    key: str = "C",
) -> str:
    """Export BeatNote list to ABC notation string."""
    lines = [
        "X:1",
        f"T:{title}",
        f"M:{time_signature[0]}/{time_signature[1]}",
        "L:1/8",
        f"Q:1/4={tempo_bpm}",
        f"K:{key}",
    ]

    default_length = 0.5  # L:1/8 = 0.5 beats
    body_parts: list[str] = []
    num, denom = time_signature
    beats_per_bar = num * (4.0 / denom)

    sorted_notes = sorted(notes, key=lambda n: n.time_beats)
    current_beat = 0.0

    for n in sorted_notes:
        # Insert rests for gaps
        gap = n.time_beats - current_beat
        if gap > 0.01:
            rest_dur = gap / default_length
            if rest_dur == int(rest_dur):
                body_parts.append(f"z{int(rest_dur)}" if rest_dur != 1 else "z")
            else:
                body_parts.append(f"z{gap:.0f}/" if gap < default_length else f"z{int(rest_dur)}")

        # Note
        abc_note = _MIDI_TO_ABC.get(n.note, "C")
        dur_ratio = n.duration_beats / default_length
        if abs(dur_ratio - 1.0) < 0.01:
            dur_str = ""
        elif abs(dur_ratio - round(dur_ratio)) < 0.01 and dur_ratio >= 1:
            dur_str = str(int(round(dur_ratio)))
        elif abs(dur_ratio - 0.5) < 0.01:
            dur_str = "/2"
        else:
            dur_str = str(int(round(dur_ratio))) if dur_ratio >= 1 else "/2"

        body_parts.append(abc_note + dur_str)
        current_beat = n.time_beats + n.duration_beats

        # Add bar line
        if current_beat > 0 and abs(current_beat % beats_per_bar) < 0.01:
            body_parts.append("|")

    lines.append(" ".join(body_parts))
    return "\n".join(lines)
