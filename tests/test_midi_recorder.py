"""Tests for MIDI recorder and writer — pure Python, no Qt dependency."""

import time
from pathlib import Path

import mido
import pytest

from cyber_qin.core.midi_recorder import MidiRecorder, RecordedEvent
from cyber_qin.core.midi_writer import MidiWriter

# ── MidiRecorder tests ─────────────────────────────────────


class TestMidiRecorder:
    def test_initial_state(self):
        rec = MidiRecorder()
        assert not rec.is_recording
        assert rec.event_count == 0
        assert rec.duration == 0.0

    def test_start_recording(self):
        rec = MidiRecorder()
        rec.start()
        assert rec.is_recording
        assert rec.event_count == 0

    def test_record_events(self):
        rec = MidiRecorder()
        rec.start()
        rec.record_event("note_on", 60, 100)
        rec.record_event("note_off", 60, 0)
        assert rec.event_count == 2

    def test_stop_returns_events(self):
        rec = MidiRecorder()
        rec.start()
        rec.record_event("note_on", 64, 90)
        events = rec.stop()
        assert not rec.is_recording
        assert len(events) == 1
        assert events[0].note == 64
        assert events[0].event_type == "note_on"

    def test_record_while_not_recording_ignored(self):
        rec = MidiRecorder()
        rec.record_event("note_on", 60, 100)
        assert rec.event_count == 0

    def test_timestamps_increase(self):
        rec = MidiRecorder()
        rec.start()
        rec.record_event("note_on", 60, 100)
        time.sleep(0.01)
        rec.record_event("note_off", 60, 0)
        events = rec.stop()
        assert events[1].timestamp > events[0].timestamp

    def test_start_clears_previous(self):
        rec = MidiRecorder()
        rec.start()
        rec.record_event("note_on", 60, 100)
        rec.stop()
        rec.start()
        assert rec.event_count == 0

    def test_events_property_returns_copy(self):
        rec = MidiRecorder()
        rec.start()
        rec.record_event("note_on", 60, 100)
        events = rec.events
        events.clear()
        assert rec.event_count == 1

    def test_duration_while_recording(self):
        rec = MidiRecorder()
        rec.start()
        time.sleep(0.02)
        assert rec.duration > 0.0
        rec.stop()

    def test_duration_after_stop(self):
        rec = MidiRecorder()
        rec.start()
        rec.record_event("note_on", 60, 100)
        time.sleep(0.01)
        rec.record_event("note_off", 60, 0)
        events = rec.stop()
        assert rec.duration == events[-1].timestamp


# ── RecordedEvent tests ────────────────────────────────────


class TestRecordedEvent:
    def test_dataclass_fields(self):
        evt = RecordedEvent(timestamp=1.5, event_type="note_on", note=72, velocity=80)
        assert evt.timestamp == 1.5
        assert evt.event_type == "note_on"
        assert evt.note == 72
        assert evt.velocity == 80

    def test_frozen(self):
        evt = RecordedEvent(timestamp=0.0, event_type="note_on", note=60, velocity=100)
        with pytest.raises(AttributeError):
            evt.note = 61


# ── MidiWriter tests ──────────────────────────────────────


class TestMidiWriter:
    def test_save_creates_file(self, tmp_path: Path):
        events = [
            RecordedEvent(0.0, "note_on", 60, 100),
            RecordedEvent(0.5, "note_off", 60, 0),
        ]
        path = str(tmp_path / "test.mid")
        MidiWriter.save(events, path)
        assert Path(path).exists()

    def test_save_empty_events(self, tmp_path: Path):
        path = str(tmp_path / "empty.mid")
        MidiWriter.save([], path)
        assert not Path(path).exists()

    def test_save_creates_directories(self, tmp_path: Path):
        path = str(tmp_path / "sub" / "dir" / "test.mid")
        events = [RecordedEvent(0.0, "note_on", 60, 100)]
        MidiWriter.save(events, path)
        assert Path(path).exists()

    def test_saved_file_is_valid_midi(self, tmp_path: Path):
        events = [
            RecordedEvent(0.0, "note_on", 60, 100),
            RecordedEvent(0.5, "note_off", 60, 0),
            RecordedEvent(0.5, "note_on", 64, 90),
            RecordedEvent(1.0, "note_off", 64, 0),
        ]
        path = str(tmp_path / "valid.mid")
        MidiWriter.save(events, path)

        mid = mido.MidiFile(path)
        assert len(mid.tracks) == 1
        note_msgs = [m for m in mid.tracks[0] if m.type in ("note_on", "note_off")]
        assert len(note_msgs) == 4

    def test_recorded_to_file_events(self):
        events = [
            RecordedEvent(0.0, "note_on", 60, 100),
            RecordedEvent(0.5, "note_off", 60, 0),
        ]
        file_events = MidiWriter.recorded_to_file_events(events)
        assert len(file_events) == 2
        assert file_events[0].time_seconds == 0.0
        assert file_events[0].event_type == "note_on"
        assert file_events[1].time_seconds == 0.5
        assert file_events[1].event_type == "note_off"
