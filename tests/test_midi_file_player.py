"""Tests for MIDI file parser — pure Python, no Qt dependency."""

from pathlib import Path

import mido
import pytest

from cyber_qin.core.midi_file_player import (
    MidiFileEvent,
    MidiFileInfo,
    MidiFileParser,
    PlaybackState,
)


@pytest.fixture
def simple_midi_file(tmp_path: Path) -> str:
    """Create a simple MIDI file with known content."""
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage("set_tempo", tempo=500000))  # 120 BPM
    track.append(mido.Message("note_on", note=60, velocity=80, time=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=480))
    track.append(mido.Message("note_on", note=64, velocity=90, time=0))
    track.append(mido.Message("note_off", note=64, velocity=0, time=480))
    track.append(mido.Message("note_on", note=67, velocity=100, time=0))
    track.append(mido.Message("note_off", note=67, velocity=0, time=480))
    track.append(mido.MetaMessage("end_of_track", time=0))

    path = str(tmp_path / "test.mid")
    mid.save(path)
    return path


@pytest.fixture
def velocity_zero_midi(tmp_path: Path) -> str:
    """MIDI file where note_off is encoded as note_on with velocity=0."""
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.Message("note_on", note=72, velocity=64, time=0))
    track.append(mido.Message("note_on", note=72, velocity=0, time=480))
    track.append(mido.MetaMessage("end_of_track", time=0))

    path = str(tmp_path / "vel0.mid")
    mid.save(path)
    return path


@pytest.fixture
def multi_track_midi(tmp_path: Path) -> str:
    """MIDI file with multiple tracks."""
    mid = mido.MidiFile()

    track1 = mido.MidiTrack()
    track1.append(mido.Message("note_on", note=60, velocity=80, time=0))
    track1.append(mido.Message("note_off", note=60, velocity=0, time=480))
    track1.append(mido.MetaMessage("end_of_track", time=0))
    mid.tracks.append(track1)

    track2 = mido.MidiTrack()
    track2.append(mido.Message("note_on", note=64, velocity=80, time=240))
    track2.append(mido.Message("note_off", note=64, velocity=0, time=480))
    track2.append(mido.MetaMessage("end_of_track", time=0))
    mid.tracks.append(track2)

    path = str(tmp_path / "multi.mid")
    mid.save(path)
    return path


@pytest.fixture
def empty_midi(tmp_path: Path) -> str:
    """MIDI file with no notes."""
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("end_of_track", time=0))
    mid.tracks.append(track)

    path = str(tmp_path / "empty.mid")
    mid.save(path)
    return path


class TestMidiFileParser:
    def test_parse_basic(self, simple_midi_file):
        events, info = MidiFileParser.parse(simple_midi_file)
        assert isinstance(events, list)
        assert isinstance(info, MidiFileInfo)
        assert info.note_count == 3
        assert info.track_count == 1

    def test_events_sorted_by_time(self, simple_midi_file):
        events, _ = MidiFileParser.parse(simple_midi_file)
        times = [e.time_seconds for e in events]
        assert times == sorted(times)

    def test_event_types(self, simple_midi_file):
        events, _ = MidiFileParser.parse(simple_midi_file)
        types = {e.event_type for e in events}
        assert types == {"note_on", "note_off"}

    def test_note_on_count(self, simple_midi_file):
        events, _ = MidiFileParser.parse(simple_midi_file)
        note_ons = [e for e in events if e.event_type == "note_on"]
        assert len(note_ons) == 3

    def test_note_off_count(self, simple_midi_file):
        events, _ = MidiFileParser.parse(simple_midi_file)
        note_offs = [e for e in events if e.event_type == "note_off"]
        assert len(note_offs) == 3

    def test_velocity_zero_as_note_off(self, velocity_zero_midi):
        events, _ = MidiFileParser.parse(velocity_zero_midi)
        note_offs = [e for e in events if e.event_type == "note_off"]
        assert len(note_offs) == 1
        assert note_offs[0].note == 72

    def test_multi_track(self, multi_track_midi):
        events, info = MidiFileParser.parse(multi_track_midi)
        assert info.track_count == 2
        assert info.note_count == 2

    def test_info_name(self, simple_midi_file):
        _, info = MidiFileParser.parse(simple_midi_file)
        assert info.name == "test"

    def test_info_duration_positive(self, simple_midi_file):
        _, info = MidiFileParser.parse(simple_midi_file)
        assert info.duration_seconds > 0

    def test_info_tempo(self, simple_midi_file):
        _, info = MidiFileParser.parse(simple_midi_file)
        assert abs(info.tempo_bpm - 120.0) < 0.1

    def test_midi_notes_correct(self, simple_midi_file):
        events, _ = MidiFileParser.parse(simple_midi_file)
        note_ons = [e for e in events if e.event_type == "note_on"]
        notes = [e.note for e in note_ons]
        assert notes == [60, 64, 67]

    def test_velocities_correct(self, simple_midi_file):
        events, _ = MidiFileParser.parse(simple_midi_file)
        note_ons = [e for e in events if e.event_type == "note_on"]
        vels = [e.velocity for e in note_ons]
        assert vels == [80, 90, 100]

    def test_empty_midi(self, empty_midi):
        events, info = MidiFileParser.parse(empty_midi)
        assert len(events) == 0
        assert info.note_count == 0
        assert info.duration_seconds == 0.0

    def test_note_on_off_pairing(self, simple_midi_file):
        events, _ = MidiFileParser.parse(simple_midi_file)
        on_notes = [e.note for e in events if e.event_type == "note_on"]
        off_notes = [e.note for e in events if e.event_type == "note_off"]
        assert sorted(on_notes) == sorted(off_notes)


class TestMidiFileEvent:
    def test_frozen(self):
        evt = MidiFileEvent(1.0, "note_on", 60, 80)
        with pytest.raises(AttributeError):
            evt.time_seconds = 2.0

    def test_fields(self):
        evt = MidiFileEvent(1.5, "note_off", 72, 0, track=1)
        assert evt.time_seconds == 1.5
        assert evt.event_type == "note_off"
        assert evt.note == 72
        assert evt.velocity == 0
        assert evt.track == 1

    def test_default_track(self):
        evt = MidiFileEvent(0.0, "note_on", 60, 80)
        assert evt.track == 0


class TestMidiFileInfo:
    def test_fields(self):
        info = MidiFileInfo(
            file_path="/test.mid",
            name="test",
            duration_seconds=3.0,
            track_count=1,
            note_count=10,
            tempo_bpm=120.0,
        )
        assert info.name == "test"
        assert info.duration_seconds == 3.0
        assert info.tempo_bpm == 120.0


class TestPlaybackState:
    def test_states_exist(self):
        assert PlaybackState.STOPPED
        assert PlaybackState.PLAYING
        assert PlaybackState.PAUSED

    def test_states_are_distinct(self):
        assert PlaybackState.STOPPED != PlaybackState.PLAYING
        assert PlaybackState.PLAYING != PlaybackState.PAUSED
