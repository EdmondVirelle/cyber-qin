"""Mutable note sequence model for the virtual keyboard editor.

Pure Python, no Qt dependency. Provides add/delete/move operations,
cursor management, undo stack, and conversion to/from MIDI event formats.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass


@dataclass
class EditableNote:
    """A single editable note in the sequence."""

    time_seconds: float
    duration_seconds: float
    note: int  # MIDI note number (0-127)
    velocity: int = 100


# Step duration presets: label → fraction of a beat at 120 BPM
STEP_PRESETS: dict[str, float] = {
    "1/1": 2.0,
    "1/2": 1.0,
    "1/4": 0.5,
    "1/8": 0.25,
    "1/16": 0.125,
}

_MAX_UNDO = 50


class NoteSequence:
    """Mutable sequence of notes with cursor and undo support."""

    def __init__(self) -> None:
        self._notes: list[EditableNote] = []
        self._cursor_time: float = 0.0
        self._step_label: str = "1/8"
        self._step_duration: float = STEP_PRESETS["1/8"]
        self._undo_stack: list[list[EditableNote]] = []
        self._redo_stack: list[list[EditableNote]] = []

    # --- Properties ---

    @property
    def notes(self) -> list[EditableNote]:
        return list(self._notes)

    @property
    def note_count(self) -> int:
        return len(self._notes)

    @property
    def cursor_time(self) -> float:
        return self._cursor_time

    @cursor_time.setter
    def cursor_time(self, value: float) -> None:
        self._cursor_time = max(0.0, value)

    @property
    def step_label(self) -> str:
        return self._step_label

    @property
    def step_duration(self) -> float:
        return self._step_duration

    @property
    def duration(self) -> float:
        """Total duration of the sequence (end of last note)."""
        if not self._notes:
            return 0.0
        return max(n.time_seconds + n.duration_seconds for n in self._notes)

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    # --- Undo / Redo ---

    def _push_undo(self) -> None:
        snapshot = [copy.copy(n) for n in self._notes]
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > _MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> None:
        if not self._undo_stack:
            return
        # Save current state to redo
        self._redo_stack.append([copy.copy(n) for n in self._notes])
        self._notes = self._undo_stack.pop()

    def redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append([copy.copy(n) for n in self._notes])
        self._notes = self._redo_stack.pop()

    # --- Editing ---

    def add_note(self, midi_note: int, velocity: int = 100) -> None:
        """Add a note at the cursor position and advance cursor."""
        self._push_undo()
        note = EditableNote(
            time_seconds=self._cursor_time,
            duration_seconds=self._step_duration,
            note=midi_note,
            velocity=velocity,
        )
        self._notes.append(note)
        self._notes.sort(key=lambda n: n.time_seconds)
        self.advance_cursor()

    def delete_note(self, index: int) -> None:
        """Delete note at index."""
        if 0 <= index < len(self._notes):
            self._push_undo()
            self._notes.pop(index)

    def move_note(self, index: int, time_delta: float = 0.0, pitch_delta: int = 0) -> None:
        """Move a note in time and/or pitch."""
        if not (0 <= index < len(self._notes)):
            return
        self._push_undo()
        n = self._notes[index]
        n.time_seconds = max(0.0, n.time_seconds + time_delta)
        n.note = max(0, min(127, n.note + pitch_delta))
        self._notes.sort(key=lambda n: n.time_seconds)

    def clear(self) -> None:
        """Clear all notes."""
        if self._notes:
            self._push_undo()
            self._notes.clear()
            self._cursor_time = 0.0

    # --- Cursor ---

    def advance_cursor(self) -> None:
        """Advance cursor by current step duration."""
        self._cursor_time += self._step_duration

    def set_step_duration(self, label: str) -> None:
        """Set step duration by preset label (e.g. '1/8')."""
        if label in STEP_PRESETS:
            self._step_label = label
            self._step_duration = STEP_PRESETS[label]

    # --- Conversion ---

    @classmethod
    def from_midi_file_events(cls, events: list) -> NoteSequence:
        """Build a NoteSequence from MidiFileEvent list.

        Pairs note_on/note_off events to determine durations.
        """
        seq = cls()
        # Pair note_on → note_off
        pending: dict[int, tuple[float, int]] = {}  # note → (time, velocity)
        for evt in events:
            if evt.event_type == "note_on":
                pending[evt.note] = (evt.time_seconds, evt.velocity)
            elif evt.event_type == "note_off" and evt.note in pending:
                on_time, vel = pending.pop(evt.note)
                dur = max(0.01, evt.time_seconds - on_time)
                seq._notes.append(
                    EditableNote(
                        time_seconds=on_time,
                        duration_seconds=dur,
                        note=evt.note,
                        velocity=vel,
                    )
                )
        # Any remaining on events without off — give default duration
        for note, (t, vel) in pending.items():
            seq._notes.append(
                EditableNote(
                    time_seconds=t,
                    duration_seconds=0.25,
                    note=note,
                    velocity=vel,
                )
            )
        seq._notes.sort(key=lambda n: n.time_seconds)
        return seq

    def to_midi_file_events(self) -> list:
        """Convert to MidiFileEvent list for playback/saving."""
        from .midi_file_player import MidiFileEvent

        result: list[MidiFileEvent] = []
        for n in self._notes:
            result.append(
                MidiFileEvent(
                    time_seconds=n.time_seconds,
                    event_type="note_on",
                    note=n.note,
                    velocity=n.velocity,
                )
            )
            result.append(
                MidiFileEvent(
                    time_seconds=n.time_seconds + n.duration_seconds,
                    event_type="note_off",
                    note=n.note,
                    velocity=0,
                )
            )
        result.sort(key=lambda e: (e.time_seconds, 0 if e.event_type == "note_off" else 1))
        return result

    def to_recorded_events(self) -> list:
        """Convert to RecordedEvent list for saving via MidiWriter."""
        from .midi_recorder import RecordedEvent

        result: list[RecordedEvent] = []
        for n in self._notes:
            result.append(
                RecordedEvent(
                    timestamp=n.time_seconds,
                    event_type="note_on",
                    note=n.note,
                    velocity=n.velocity,
                )
            )
            result.append(
                RecordedEvent(
                    timestamp=n.time_seconds + n.duration_seconds,
                    event_type="note_off",
                    note=n.note,
                    velocity=0,
                )
            )
        result.sort(key=lambda e: e.timestamp)
        return result
