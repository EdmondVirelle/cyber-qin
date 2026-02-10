"""MIDI recording engine — captures live MIDI events with timestamps.

Pure Python, no Qt dependency. Thread-safe: called from rtmidi callback thread.
Uses time.perf_counter() for high-resolution timestamps and list.append() (GIL-atomic).
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecordedEvent:
    """A single recorded MIDI event with timestamp."""

    timestamp: float       # seconds since recording start (perf_counter based)
    event_type: str        # "note_on" or "note_off"
    note: int              # MIDI note number (0-127)
    velocity: int          # velocity (0-127)


class MidiRecorder:
    """Records live MIDI events with precise timing.

    Thread-safe: ``record_event`` is called from the rtmidi callback thread.
    ``list.append()`` is GIL-atomic on CPython, so no explicit lock is needed.
    """

    def __init__(self) -> None:
        self._events: list[RecordedEvent] = []
        self._recording = False
        self._start_time: float = 0.0

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def duration(self) -> float:
        """Duration in seconds since start, or total if stopped."""
        if self._recording:
            return time.perf_counter() - self._start_time
        if not self._events:
            return 0.0
        return self._events[-1].timestamp

    @property
    def events(self) -> list[RecordedEvent]:
        """Return a copy of recorded events."""
        return list(self._events)

    def start(self) -> None:
        """Start a new recording, clearing any previous data."""
        self._events.clear()
        self._start_time = time.perf_counter()
        self._recording = True

    def stop(self) -> list[RecordedEvent]:
        """Stop recording and return the captured events."""
        self._recording = False
        return list(self._events)

    def record_event(self, event_type: str, note: int, velocity: int) -> None:
        """Record a MIDI event. Called from rtmidi callback thread."""
        if not self._recording:
            return
        timestamp = time.perf_counter() - self._start_time
        self._events.append(RecordedEvent(
            timestamp=timestamp,
            event_type=event_type,
            note=note,
            velocity=velocity,
        ))
