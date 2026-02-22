"""LilyPond notation parser and exporter (melodic subset).

Supports a subset of LilyPond notation for import/export:
- Note names: c d e f g a b (lowercase always)
- Octave: ' (up) , (down) — relative to c' = C4
- Accidentals: is (sharp), es (flat)
- Duration: 1 (whole), 2 (half), 4 (quarter), 8 (eighth), 16 (sixteenth)
- Dots: . after duration
- Rests: r
- Bar checks: |
- \\tempo, \\time headers
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .beat_sequence import BeatNote

# ── Note mapping ──────────────────────────────────────────

_LY_NOTE_MAP = {
    "c": 0,
    "d": 2,
    "e": 4,
    "f": 5,
    "g": 7,
    "a": 9,
    "b": 11,
}

# Duration number → beats
_LY_DUR_MAP = {
    "1": 4.0,
    "2": 2.0,
    "4": 1.0,
    "8": 0.5,
    "16": 0.25,
    "32": 0.125,
}


@dataclass
class LilyPondParseResult:
    """Result of parsing a LilyPond string."""

    notes: list[BeatNote]
    title: str = ""
    tempo_bpm: int = 120
    time_signature: tuple[int, int] = (4, 4)


# ── Tokenizer ─────────────────────────────────────────────

# Match: note_name + optional accidental + octave marks + optional duration + dots
_LY_NOTE_RE = re.compile(
    r"(?P<name>[a-g])"
    r"(?P<acc>is|es|isis|eses)?"
    r"(?P<oct>[',]*)"
    r"(?P<dur>\d{1,2})?"
    r"(?P<dot>\.?)"
)

_LY_REST_RE = re.compile(r"r(?P<dur>\d{1,2})?(?P<dot>\.?)")

_LY_TEMPO_RE = re.compile(r"\\tempo\s+(\d+)\s*=\s*(\d+)")
_LY_TIME_RE = re.compile(r"\\time\s+(\d+)/(\d+)")


def parse_lilypond(text: str) -> LilyPondParseResult:
    """Parse a LilyPond notation string into BeatNotes.

    Parameters
    ----------
    text : str
        LilyPond notation (may include \\tempo, \\time commands).

    Returns
    -------
    LilyPondParseResult
    """
    tempo_bpm = 120
    time_sig = (4, 4)
    title = ""

    # Extract commands
    tempo_match = _LY_TEMPO_RE.search(text)
    if tempo_match:
        try:
            tempo_bpm = int(tempo_match.group(2))
        except ValueError:
            pass

    time_match = _LY_TIME_RE.search(text)
    if time_match:
        try:
            time_sig = (int(time_match.group(1)), int(time_match.group(2)))
        except ValueError:
            pass

    # Extract title from \header block
    header_match = re.search(r'title\s*=\s*"([^"]*)"', text)
    if header_match:
        title = header_match.group(1)

    # Parse notes
    notes: list[BeatNote] = []
    current_beat = 0.0
    last_duration = 1.0  # default quarter note

    # Remove comments and commands we don't parse
    clean = re.sub(r"%.*$", "", text, flags=re.MULTILINE)
    clean = re.sub(r"\\[a-zA-Z]+\s*\{?", "", clean)
    clean = re.sub(r"[{}]", "", clean)

    pos = 0
    while pos < len(clean):
        ch = clean[pos]

        # Skip whitespace and bar checks
        if ch in " \t\n\r|":
            pos += 1
            continue

        # Rest
        rest_match = _LY_REST_RE.match(clean, pos)
        if rest_match:
            dur_str = rest_match.group("dur")
            dot = rest_match.group("dot")
            if dur_str and dur_str in _LY_DUR_MAP:
                last_duration = _LY_DUR_MAP[dur_str]
            dur = last_duration
            if dot:
                dur *= 1.5
            current_beat += dur
            pos = rest_match.end()
            continue

        # Note
        note_match = _LY_NOTE_RE.match(clean, pos)
        if note_match:
            name = note_match.group("name")
            acc = note_match.group("acc") or ""
            oct_str = note_match.group("oct") or ""
            dur_str = note_match.group("dur")
            dot = note_match.group("dot")

            if name not in _LY_NOTE_MAP:
                pos += 1
                continue

            # Base: c' = C4 = MIDI 60
            # LilyPond default octave: c (no marks) = C3 = MIDI 48
            base_octave = 3  # c = C3
            for ch_oct in oct_str:
                if ch_oct == "'":
                    base_octave += 1
                elif ch_oct == ",":
                    base_octave -= 1

            midi_note = (base_octave + 1) * 12 + _LY_NOTE_MAP[name]

            # Accidentals
            if acc == "is":
                midi_note += 1
            elif acc == "es":
                midi_note -= 1
            elif acc == "isis":
                midi_note += 2
            elif acc == "eses":
                midi_note -= 2

            midi_note = max(0, min(127, midi_note))

            # Duration
            if dur_str and dur_str in _LY_DUR_MAP:
                last_duration = _LY_DUR_MAP[dur_str]
            dur = last_duration
            if dot:
                dur *= 1.5

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

        # Unknown — skip
        pos += 1

    return LilyPondParseResult(
        notes=notes,
        title=title,
        tempo_bpm=tempo_bpm,
        time_signature=time_sig,
    )


# ── Export ────────────────────────────────────────────────

_MIDI_TO_LY_NAME: dict[int, str] = {
    0: "c",
    1: "cis",
    2: "d",
    3: "dis",
    4: "e",
    5: "f",
    6: "fis",
    7: "g",
    8: "gis",
    9: "a",
    10: "ais",
    11: "b",
}

_BEATS_TO_LY_DUR: list[tuple[float, str]] = [
    (4.0, "1"),
    (3.0, "2."),
    (2.0, "2"),
    (1.5, "4."),
    (1.0, "4"),
    (0.75, "8."),
    (0.5, "8"),
    (0.375, "16."),
    (0.25, "16"),
    (0.125, "32"),
]


def _beats_to_ly_duration(beats: float) -> str:
    """Find the closest LilyPond duration string."""
    best = "4"
    best_diff = float("inf")
    for dur_val, dur_str in _BEATS_TO_LY_DUR:
        diff = abs(beats - dur_val)
        if diff < best_diff:
            best_diff = diff
            best = dur_str
    return best


def _midi_to_ly_note(midi_note: int) -> str:
    """Convert MIDI note to LilyPond note name with octave marks."""
    pc = midi_note % 12
    octave = midi_note // 12 - 1  # C4 = 60 → octave 4
    name = _MIDI_TO_LY_NAME[pc]

    # LilyPond: c' = C4 (octave 4), c = C3 (octave 3)
    ly_base_octave = 3
    diff = octave - ly_base_octave
    if diff > 0:
        name += "'" * diff
    elif diff < 0:
        name += "," * (-diff)
    return name


def export_lilypond(
    notes: list[BeatNote],
    *,
    title: str = "Untitled",
    tempo_bpm: int = 120,
    time_signature: tuple[int, int] = (4, 4),
) -> str:
    """Export BeatNote list to LilyPond notation string."""
    lines = [
        '\\version "2.24.0"',
        "\\header {",
        f'  title = "{title}"',
        "}",
        "",
        "\\relative c' {",
        f"  \\time {time_signature[0]}/{time_signature[1]}",
        f"  \\tempo 4 = {tempo_bpm}",
    ]

    sorted_notes = sorted(notes, key=lambda n: n.time_beats)
    current_beat = 0.0
    last_dur_str = "4"
    body_parts: list[str] = []
    beats_per_bar = time_signature[0] * (4.0 / time_signature[1])

    for n in sorted_notes:
        # Insert rest for gap
        gap = n.time_beats - current_beat
        if gap > 0.01:
            rest_dur = _beats_to_ly_duration(gap)
            body_parts.append(f"r{rest_dur}")

        # Note
        ly_note = _midi_to_ly_note(n.note)
        dur_str = _beats_to_ly_duration(n.duration_beats)
        if dur_str == last_dur_str:
            body_parts.append(ly_note)
        else:
            body_parts.append(ly_note + dur_str)
            last_dur_str = dur_str

        current_beat = n.time_beats + n.duration_beats

        # Bar check
        if abs(current_beat % beats_per_bar) < 0.01 and current_beat > 0:
            body_parts.append("|")

    lines.append("  " + " ".join(body_parts))
    lines.append("}")
    return "\n".join(lines)
