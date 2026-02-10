"""MIDI preprocessing pipeline for 燕雲十六聲 (Where Winds Meet) 36-key mode.

Transforms raw MIDI events for optimal game playback:
1. Smart global transpose — find optimal ±12 shift to center notes in range
2. Octave normalization — fold remaining out-of-range notes by octave
3. Collision deduplication — remove duplicate notes at the same time+pitch
4. Velocity normalization — unify all note_on velocity to 127
5. Time quantization — snap to frame grid to eliminate micro-delays
"""

from __future__ import annotations

from dataclasses import dataclass

from .constants import MIDI_NOTE_MAX, MIDI_NOTE_MIN

# 60 FPS frame duration
_FRAME_SEC = 1.0 / 60.0  # ~16.67 ms


@dataclass(frozen=True, slots=True)
class PreprocessStats:
    """Statistics from the preprocessing pipeline."""

    total_notes: int
    notes_shifted: int
    original_range: tuple[int, int]  # (lowest, highest) MIDI note before shift
    global_transpose: int = 0        # semitones applied globally (multiple of 12)
    duplicates_removed: int = 0      # collisions removed after octave folding


def compute_optimal_transpose(
    events: list, *, note_min: int = MIDI_NOTE_MIN, note_max: int = MIDI_NOTE_MAX,
) -> int:
    """Find the best global transpose (multiple of 12) to maximize in-range notes.

    Tries shifts from -48 to +48 in steps of 12 and picks the one that puts
    the most note_on events inside [note_min, note_max].
    Returns 0 if no shift helps.
    """
    notes = [e.note for e in events if e.event_type == "note_on"]
    if not notes:
        return 0

    best_shift = 0
    best_in_range = sum(1 for n in notes if note_min <= n <= note_max)

    for shift in range(-48, 49, 12):
        if shift == 0:
            continue
        in_range = sum(1 for n in notes if note_min <= n + shift <= note_max)
        # Prefer more in-range; break ties by smallest absolute shift
        if in_range > best_in_range or (
            in_range == best_in_range and abs(shift) < abs(best_shift)
        ):
            best_in_range = in_range
            best_shift = shift

    return best_shift


def apply_global_transpose(events: list, *, semitones: int) -> list:
    """Shift all note events by a fixed number of semitones."""
    if semitones == 0:
        return events

    from .midi_file_player import MidiFileEvent

    return [
        MidiFileEvent(
            time_seconds=evt.time_seconds,
            event_type=evt.event_type,
            note=evt.note + semitones,
            velocity=evt.velocity,
            track=evt.track,
        )
        if evt.event_type in ("note_on", "note_off") else evt
        for evt in events
    ]


def normalize_octave(events: list, *, note_min: int = MIDI_NOTE_MIN, note_max: int = MIDI_NOTE_MAX) -> list:
    """Shift notes into the playable range (MIDI 48-83) by octave transposition.

    Notes above 83 are lowered by octaves; notes below 48 are raised.
    """
    from .midi_file_player import MidiFileEvent

    result: list = []
    for evt in events:
        note = evt.note
        while note > note_max:
            note -= 12
        while note < note_min:
            note += 12
        if note != evt.note:
            evt = MidiFileEvent(
                time_seconds=evt.time_seconds,
                event_type=evt.event_type,
                note=note,
                velocity=evt.velocity,
                track=evt.track,
            )
        result.append(evt)
    return result


def deduplicate_notes(events: list) -> tuple[list, int]:
    """Remove duplicate note events at the same (time, type, note).

    After octave folding, multiple notes can collapse to the same pitch.
    For note_off duplicates, keep only the last one (longest sustain).

    Returns (deduplicated_events, count_removed).
    """
    seen: set[tuple[float, str, int]] = set()
    result: list = []
    removed = 0

    for evt in events:
        if evt.event_type in ("note_on", "note_off"):
            key = (evt.time_seconds, evt.event_type, evt.note)
            if key in seen:
                removed += 1
                continue
            seen.add(key)
        result.append(evt)

    return result, removed


def normalize_velocity(events: list, *, target: int = 127) -> list:
    """Set all note_on velocities to *target* for consistent key simulation."""
    from .midi_file_player import MidiFileEvent

    result: list = []
    for evt in events:
        if evt.event_type == "note_on" and evt.velocity != target:
            evt = MidiFileEvent(
                time_seconds=evt.time_seconds,
                event_type=evt.event_type,
                note=evt.note,
                velocity=target,
                track=evt.track,
            )
        result.append(evt)
    return result


def quantize_timing(events: list, *, grid_sec: float = _FRAME_SEC) -> list:
    """Snap event times to a frame-aligned grid to remove micro-delays.

    Default grid matches 60 FPS (~16.67 ms).  Events within the same frame
    are collapsed to the same timestamp.
    """
    from .midi_file_player import MidiFileEvent

    result: list = []
    for evt in events:
        snapped = round(evt.time_seconds / grid_sec) * grid_sec
        if abs(snapped - evt.time_seconds) > 1e-9:
            evt = MidiFileEvent(
                time_seconds=snapped,
                event_type=evt.event_type,
                note=evt.note,
                velocity=evt.velocity,
                track=evt.track,
            )
        result.append(evt)
    return result


def preprocess(
    events: list,
    *,
    note_min: int = MIDI_NOTE_MIN,
    note_max: int = MIDI_NOTE_MAX,
) -> tuple[list, PreprocessStats]:
    """Apply the full preprocessing pipeline.

    Order: global transpose → octave fold → dedup → velocity → quantize → re-sort.
    Returns (processed_events, stats).

    Args:
        note_min: Lower bound of the playable MIDI range (default: 48).
        note_max: Upper bound of the playable MIDI range (default: 83).
    """
    if not events:
        return events, PreprocessStats(0, 0, (0, 0))

    # Gather pre-processing stats
    note_ons = [e for e in events if e.event_type == "note_on"]
    total = len(note_ons)
    if note_ons:
        lo = min(e.note for e in note_ons)
        hi = max(e.note for e in note_ons)
        out_of_range = sum(
            1 for e in note_ons
            if e.note < note_min or e.note > note_max
        )
    else:
        lo, hi, out_of_range = 0, 0, 0

    # 1. Smart global transpose
    transpose = compute_optimal_transpose(events, note_min=note_min, note_max=note_max)
    events = apply_global_transpose(events, semitones=transpose)

    # Recount after transpose (some notes now in range that weren't before)
    if transpose != 0:
        out_of_range = sum(
            1 for e in events
            if e.event_type == "note_on" and (e.note < note_min or e.note > note_max)
        )

    # 2. Octave fold remaining out-of-range notes
    events = normalize_octave(events, note_min=note_min, note_max=note_max)

    # 3. Deduplicate collisions from folding
    events, dupes = deduplicate_notes(events)

    # 4-5. Velocity + timing
    events = normalize_velocity(events)
    events = quantize_timing(events)

    # Re-sort: by time, then note_off before note_on (release before press)
    events.sort(key=lambda e: (e.time_seconds, 0 if e.event_type == "note_off" else 1))

    stats = PreprocessStats(
        total_notes=total,
        notes_shifted=out_of_range,
        original_range=(lo, hi),
        global_transpose=transpose,
        duplicates_removed=dupes,
    )

    return events, stats
