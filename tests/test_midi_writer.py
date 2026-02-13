"""Tests for cyber_qin.core.midi_writer — MidiWriter save / save_multitrack."""

from __future__ import annotations

import mido

from cyber_qin.core.midi_file_player import MidiFileEvent
from cyber_qin.core.midi_recorder import RecordedEvent
from cyber_qin.core.midi_writer import MidiWriter

# ── Helpers ─────────────────────────────────────────────────


def _make_note(t: float, note: int = 60, vel: int = 100, track: int = 0, ch: int = 0):
    """Create a note_on + note_off pair."""
    return [
        MidiFileEvent(
            time_seconds=t, event_type="note_on", note=note, velocity=vel, track=track, channel=ch
        ),
        MidiFileEvent(
            time_seconds=t + 0.5,
            event_type="note_off",
            note=note,
            velocity=0,
            track=track,
            channel=ch,
        ),
    ]


# ── MidiWriter.save ─────────────────────────────────────────


class TestSave:
    def test_save_empty_events(self, tmp_path):
        path = tmp_path / "empty.mid"
        MidiWriter.save([], str(path))
        assert not path.exists()  # empty → no file

    def test_save_basic(self, tmp_path):
        events = [
            RecordedEvent(timestamp=0.0, event_type="note_on", note=60, velocity=100),
            RecordedEvent(timestamp=0.5, event_type="note_off", note=60, velocity=0),
        ]
        path = tmp_path / "basic.mid"
        MidiWriter.save(events, str(path), tempo_bpm=120.0)
        assert path.exists()
        mid = mido.MidiFile(str(path))
        assert len(mid.tracks) == 1
        note_msgs = [m for m in mid.tracks[0] if m.type in ("note_on", "note_off")]
        assert len(note_msgs) == 2

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "out.mid"
        events = [
            RecordedEvent(timestamp=0.0, event_type="note_on", note=60, velocity=80),
            RecordedEvent(timestamp=0.5, event_type="note_off", note=60, velocity=0),
        ]
        MidiWriter.save(events, str(path))
        assert path.exists()


# ── MidiWriter.save_multitrack ──────────────────────────────


class TestSaveMultitrack:
    def test_empty_events(self, tmp_path):
        path = tmp_path / "empty.mid"
        MidiWriter.save_multitrack([], str(path))
        assert not path.exists()

    def test_single_track_type0(self, tmp_path):
        """Single-track produces a valid file with one track of music."""
        events = _make_note(0.0, note=60, track=0)
        path = tmp_path / "type0.mid"
        MidiWriter.save_multitrack(events, str(path), tempo_bpm=120.0, track_names=["Piano"])
        mid = mido.MidiFile(str(path))
        # Should have exactly 1 track with notes in it
        note_tracks = [t for t in mid.tracks if any(m.type in ("note_on", "note_off") for m in t)]
        assert len(note_tracks) == 1
        # Check track name
        names = [m for m in mid.tracks[0] if m.type == "track_name"]
        assert len(names) == 1
        assert names[0].name == "Piano"

    def test_multi_track_type1(self, tmp_path):
        """Multi-track produces Type 1 with conductor + per-track."""
        events = _make_note(0.0, note=60, track=0) + _make_note(0.0, note=72, track=1)
        path = tmp_path / "type1.mid"
        MidiWriter.save_multitrack(
            events,
            str(path),
            tempo_bpm=90.0,
            track_names=["Melody", "Bass"],
            track_channels=[0, 1],
        )
        mid = mido.MidiFile(str(path))
        assert mid.type == 1
        assert len(mid.tracks) == 3  # conductor + 2 tracks

        # Conductor has tempo
        tempos = [m for m in mid.tracks[0] if m.type == "set_tempo"]
        assert len(tempos) == 1

        # Track names
        for i, name in enumerate(["Melody", "Bass"]):
            names = [m for m in mid.tracks[i + 1] if m.type == "track_name"]
            assert len(names) == 1
            assert names[0].name == name

    def test_multi_track_channels(self, tmp_path):
        """Per-track channel assignment is respected."""
        events = _make_note(0.0, note=60, track=0) + _make_note(0.0, note=48, track=1)
        path = tmp_path / "ch.mid"
        MidiWriter.save_multitrack(events, str(path), track_channels=[3, 5])
        mid = mido.MidiFile(str(path))
        # Track 1 (index 1) should use channel 3
        note_msgs = [m for m in mid.tracks[1] if m.type == "note_on"]
        assert all(m.channel == 3 for m in note_msgs)
        # Track 2 (index 2) should use channel 5
        note_msgs = [m for m in mid.tracks[2] if m.type == "note_on"]
        assert all(m.channel == 5 for m in note_msgs)

    def test_no_track_names(self, tmp_path):
        """Works without providing track_names or track_channels."""
        events = _make_note(0.0, track=0) + _make_note(0.5, track=1)
        path = tmp_path / "nonames.mid"
        MidiWriter.save_multitrack(events, str(path))
        mid = mido.MidiFile(str(path))
        assert mid.type == 1
        assert len(mid.tracks) == 3

    def test_single_track_no_names(self, tmp_path):
        """Single track with no names doesn't crash."""
        events = _make_note(0.0, track=0)
        path = tmp_path / "single_noname.mid"
        MidiWriter.save_multitrack(events, str(path))
        assert path.exists()


# ── MidiWriter.recorded_to_file_events ──────────────────────


class TestRecordedToFileEvents:
    def test_conversion(self):
        recorded = [
            RecordedEvent(timestamp=0.0, event_type="note_on", note=60, velocity=100),
            RecordedEvent(timestamp=0.5, event_type="note_off", note=60, velocity=0),
            RecordedEvent(timestamp=0.2, event_type="note_on", note=64, velocity=80),
        ]
        result = MidiWriter.recorded_to_file_events(recorded)
        assert len(result) == 3
        # Should be sorted by time
        assert result[0].time_seconds == 0.0
        assert result[1].time_seconds == 0.2
        assert result[2].time_seconds == 0.5
        # All on track/channel 0
        assert all(e.track == 0 for e in result)
        assert all(e.channel == 0 for e in result)

    def test_note_off_before_note_on_at_same_time(self):
        """note_off should sort before note_on at the same timestamp."""
        recorded = [
            RecordedEvent(timestamp=1.0, event_type="note_on", note=60, velocity=100),
            RecordedEvent(timestamp=1.0, event_type="note_off", note=64, velocity=0),
        ]
        result = MidiWriter.recorded_to_file_events(recorded)
        assert result[0].event_type == "note_off"
        assert result[1].event_type == "note_on"
