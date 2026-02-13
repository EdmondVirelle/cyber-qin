"""Auto-tune: post-recording quantization and pitch correction.

Provides beat-grid quantization and scale snapping for recorded MIDI events.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .constants import MIDI_NOTE_MAX, MIDI_NOTE_MIN
from .midi_preprocessor import normalize_octave
from .midi_recorder import RecordedEvent


class QuantizeGrid(Enum):
    """Musical grid divisions for quantization."""

    QUARTER = 1.0  # 1/4 note
    EIGHTH = 0.5  # 1/8 note
    SIXTEENTH = 0.25  # 1/16 note
    TRIPLET_8 = 1.0 / 3  # 1/8 triplet


@dataclass(frozen=True, slots=True)
class AutoTuneStats:
    """Statistics from the auto-tune pipeline."""

    total_events: int
    quantized_count: int  # events whose time was adjusted
    pitch_corrected_count: int  # events whose pitch was adjusted


def quantize_to_beat_grid(
    events: list[RecordedEvent],
    tempo_bpm: float,
    grid: QuantizeGrid = QuantizeGrid.EIGHTH,
    strength: float = 0.75,
) -> list[RecordedEvent]:
    """Snap note timestamps to a beat grid.

    Args:
        events: Input events.
        tempo_bpm: Tempo in BPM.
        grid: Grid division (quarter, eighth, etc.).
        strength: 0.0 = no change, 1.0 = full snap. Default 0.75.

    Returns:
        New list with quantized timestamps.
    """
    if not events or tempo_bpm <= 0:
        return list(events)

    strength = max(0.0, min(1.0, strength))
    beat_sec = 60.0 / tempo_bpm
    grid_sec = beat_sec * grid.value

    result: list[RecordedEvent] = []
    for evt in events:
        nearest_grid = round(evt.timestamp / grid_sec) * grid_sec
        new_time = evt.timestamp + (nearest_grid - evt.timestamp) * strength
        result.append(
            RecordedEvent(
                timestamp=max(0.0, new_time),
                event_type=evt.event_type,
                note=evt.note,
                velocity=evt.velocity,
            )
        )
    return result


def snap_to_scale(
    events: list[RecordedEvent],
    note_min: int = MIDI_NOTE_MIN,
    note_max: int = MIDI_NOTE_MAX,
) -> list[RecordedEvent]:
    """Fold out-of-range notes into the playable range by octave transposition.

    Reuses the same octave-fold logic as the preprocessor's normalize_octave,
    but operates on RecordedEvent objects.
    """
    from .midi_file_player import MidiFileEvent

    # Convert to MidiFileEvent for normalize_octave
    file_events = [
        MidiFileEvent(
            time_seconds=evt.timestamp,
            event_type=evt.event_type,
            note=evt.note,
            velocity=evt.velocity,
        )
        for evt in events
    ]

    folded = normalize_octave(file_events, note_min=note_min, note_max=note_max)

    # Convert back to RecordedEvent
    return [
        RecordedEvent(
            timestamp=fe.time_seconds,
            event_type=fe.event_type,
            note=fe.note,
            velocity=fe.velocity,
        )
        for fe in folded
    ]


def auto_tune(
    events: list[RecordedEvent],
    *,
    tempo_bpm: float = 120.0,
    grid: QuantizeGrid = QuantizeGrid.EIGHTH,
    strength: float = 0.75,
    note_min: int = MIDI_NOTE_MIN,
    note_max: int = MIDI_NOTE_MAX,
    do_quantize: bool = True,
    do_pitch_correct: bool = True,
) -> tuple[list[RecordedEvent], AutoTuneStats]:
    """Combined auto-tune pipeline: quantize timing + pitch correction.

    Returns (corrected_events, stats).
    """
    total = len(events)
    quantized_count = 0
    pitch_corrected_count = 0

    if do_quantize:
        quantized = quantize_to_beat_grid(events, tempo_bpm, grid, strength)
        for orig, q in zip(events, quantized):
            if abs(orig.timestamp - q.timestamp) > 1e-6:
                quantized_count += 1
        events = quantized

    if do_pitch_correct:
        corrected = snap_to_scale(events, note_min, note_max)
        for orig, c in zip(events, corrected):
            if orig.note != c.note:
                pitch_corrected_count += 1
        events = corrected

    stats = AutoTuneStats(
        total_events=total,
        quantized_count=quantized_count,
        pitch_corrected_count=pitch_corrected_count,
    )
    return events, stats
