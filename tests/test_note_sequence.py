"""Tests for note sequence editor model."""

from cyber_qin.core.midi_file_player import MidiFileEvent
from cyber_qin.core.note_sequence import STEP_PRESETS, NoteSequence


class TestNoteSequence:
    def test_initial_state(self):
        seq = NoteSequence()
        assert seq.note_count == 0
        assert seq.cursor_time == 0.0
        assert seq.duration == 0.0
        assert seq.step_label == "1/8"

    def test_add_note(self):
        seq = NoteSequence()
        seq.add_note(60)
        assert seq.note_count == 1
        assert seq.notes[0].note == 60
        assert seq.notes[0].time_seconds == 0.0

    def test_add_note_advances_cursor(self):
        seq = NoteSequence()
        seq.add_note(60)
        assert seq.cursor_time == STEP_PRESETS["1/8"]

    def test_delete_note(self):
        seq = NoteSequence()
        seq.add_note(60)
        seq.delete_note(0)
        assert seq.note_count == 0

    def test_delete_out_of_range(self):
        seq = NoteSequence()
        seq.delete_note(5)  # Should not raise
        assert seq.note_count == 0

    def test_move_note_time(self):
        seq = NoteSequence()
        seq.add_note(60)
        seq.move_note(0, time_delta=1.0)
        assert seq.notes[0].time_seconds == 1.0

    def test_move_note_pitch(self):
        seq = NoteSequence()
        seq.add_note(60)
        seq.move_note(0, pitch_delta=5)
        assert seq.notes[0].note == 65

    def test_move_note_clamps(self):
        seq = NoteSequence()
        seq.add_note(60)
        seq.move_note(0, time_delta=-999.0, pitch_delta=-999)
        assert seq.notes[0].time_seconds == 0.0
        assert seq.notes[0].note == 0

    def test_undo_add(self):
        seq = NoteSequence()
        seq.add_note(60)
        assert seq.can_undo
        seq.undo()
        assert seq.note_count == 0

    def test_redo(self):
        seq = NoteSequence()
        seq.add_note(60)
        seq.undo()
        assert seq.can_redo
        seq.redo()
        assert seq.note_count == 1

    def test_undo_redo_after_new_edit(self):
        seq = NoteSequence()
        seq.add_note(60)
        seq.undo()
        seq.add_note(72)  # New edit clears redo
        assert not seq.can_redo
        assert seq.notes[0].note == 72

    def test_clear(self):
        seq = NoteSequence()
        seq.add_note(60)
        seq.add_note(64)
        seq.clear()
        assert seq.note_count == 0
        assert seq.cursor_time == 0.0

    def test_set_step_duration(self):
        seq = NoteSequence()
        seq.set_step_duration("1/4")
        assert seq.step_label == "1/4"
        assert seq.step_duration == STEP_PRESETS["1/4"]

    def test_set_step_duration_invalid(self):
        seq = NoteSequence()
        seq.set_step_duration("invalid")
        assert seq.step_label == "1/8"  # unchanged

    def test_from_midi_file_events(self):
        events = [
            MidiFileEvent(0.0, "note_on", 60, 100),
            MidiFileEvent(0.5, "note_off", 60, 0),
            MidiFileEvent(0.5, "note_on", 64, 90),
            MidiFileEvent(1.0, "note_off", 64, 0),
        ]
        seq = NoteSequence.from_midi_file_events(events)
        assert seq.note_count == 2
        assert seq.notes[0].note == 60
        assert abs(seq.notes[0].duration_seconds - 0.5) < 0.01
        assert seq.notes[1].note == 64

    def test_to_midi_file_events(self):
        seq = NoteSequence()
        seq.add_note(60)
        seq.add_note(64)
        events = seq.to_midi_file_events()
        note_ons = [e for e in events if e.event_type == "note_on"]
        assert len(note_ons) == 2

    def test_to_recorded_events(self):
        seq = NoteSequence()
        seq.add_note(60)
        events = seq.to_recorded_events()
        assert len(events) == 2  # note_on + note_off
        assert events[0].event_type == "note_on"
        assert events[1].event_type == "note_off"

    def test_duration(self):
        seq = NoteSequence()
        seq.add_note(60)  # at 0.0, duration 0.25
        assert seq.duration == 0.25

    def test_notes_sorted_by_time(self):
        seq = NoteSequence()
        seq.cursor_time = 1.0
        seq.add_note(60)
        seq.cursor_time = 0.0
        seq.add_note(72)
        assert seq.notes[0].note == 72
        assert seq.notes[1].note == 60
