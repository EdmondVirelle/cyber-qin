"""MIDI preprocessing pipeline for 燕雲十六聲 (Where Winds Meet) 36-key mode.

Transforms raw MIDI events for optimal game playback:
1. Octave normalization — shift out-of-range notes into the 3-octave range
2. Velocity normalization — unify all note_on velocity to 127
3. Time quantization — snap to frame grid to eliminate micro-delays
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

    Order: octave → velocity → quantize → re-sort.
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

    stats = PreprocessStats(
        total_notes=total,
        notes_shifted=out_of_range,
        original_range=(lo, hi),
    )

    # Pipeline
    events = normalize_octave(events, note_min=note_min, note_max=note_max)
    events = normalize_velocity(events)
    events = quantize_timing(events)

    # Re-sort: by time, then note_off before note_on (release before press)
    events.sort(key=lambda e: (e.time_seconds, 0 if e.event_type == "note_off" else 1))

    return events, stats
