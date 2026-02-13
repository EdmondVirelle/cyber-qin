"""Tests for beat_sequence — beat-based editor data model."""

from __future__ import annotations

from cyber_qin.core.beat_sequence import (
    DEFAULT_TRACK_COLORS,
    DURATION_PRESETS,
    BeatNote,
    BeatRest,
    EditorSequence,
    Track,
)

# ── BeatNote / BeatRest ────────────────────────────────────


class TestBeatNote:
    def test_create(self):
        n = BeatNote(time_beats=0.0, duration_beats=1.0, note=60)
        assert n.time_beats == 0.0
        assert n.duration_beats == 1.0
        assert n.note == 60
        assert n.velocity == 100
        assert n.track == 0

    def test_create_with_track(self):
        n = BeatNote(0.5, 0.25, 72, velocity=80, track=3)
        assert n.track == 3
        assert n.velocity == 80

    def test_mutable(self):
        n = BeatNote(0.0, 1.0, 60)
        n.time_beats = 2.0
        n.note = 72
        assert n.time_beats == 2.0
        assert n.note == 72


class TestBeatRest:
    def test_create(self):
        r = BeatRest(time_beats=1.0, duration_beats=0.5)
        assert r.time_beats == 1.0
        assert r.duration_beats == 0.5
        assert r.track == 0

    def test_create_with_track(self):
        r = BeatRest(2.0, 1.0, track=2)
        assert r.track == 2


class TestTrack:
    def test_defaults(self):
        t = Track()
        assert t.name == ""
        assert t.color == "#00F0FF"
        assert t.channel == 0
        assert t.muted is False
        assert t.solo is False


# ── EditorSequence basics ──────────────────────────────────


class TestEditorSequenceInit:
    def test_default_init(self):
        seq = EditorSequence()
        assert seq.tempo_bpm == 120.0
        assert seq.time_signature == (4, 4)
        assert seq.track_count == 4
        assert seq.note_count == 0
        assert seq.rest_count == 0
        assert seq.cursor_beats == 0.0
        assert seq.active_track == 0

    def test_custom_init(self):
        seq = EditorSequence(tempo_bpm=90.0, time_signature=(3, 4), num_tracks=2)
        assert seq.tempo_bpm == 90.0
        assert seq.time_signature == (3, 4)
        assert seq.track_count == 2

    def test_track_colors_assigned(self):
        seq = EditorSequence(num_tracks=4)
        for i, t in enumerate(seq.tracks):
            assert t.color == DEFAULT_TRACK_COLORS[i]

    def test_max_tracks_capped(self):
        seq = EditorSequence(num_tracks=20)
        assert seq.track_count == 12


class TestBeatsPerBar:
    def test_4_4(self):
        seq = EditorSequence(time_signature=(4, 4))
        assert seq.beats_per_bar == 4.0

    def test_3_4(self):
        seq = EditorSequence(time_signature=(3, 4))
        assert seq.beats_per_bar == 3.0

    def test_6_8(self):
        seq = EditorSequence(time_signature=(6, 8))
        assert seq.beats_per_bar == 3.0

    def test_2_4(self):
        seq = EditorSequence(time_signature=(2, 4))
        assert seq.beats_per_bar == 2.0


# ── Step duration ──────────────────────────────────────────


class TestStepDuration:
    def test_default_step(self):
        seq = EditorSequence()
        assert seq.step_label == "1/4"
        assert seq.step_duration == 1.0

    def test_set_step(self):
        seq = EditorSequence()
        seq.set_step_duration("1/8")
        assert seq.step_label == "1/8"
        assert seq.step_duration == 0.5

    def test_set_invalid_step_ignored(self):
        seq = EditorSequence()
        seq.set_step_duration("invalid")
        assert seq.step_label == "1/4"

    def test_all_presets(self):
        seq = EditorSequence()
        for label, dur in DURATION_PRESETS.items():
            seq.set_step_duration(label)
            assert seq.step_duration == dur


# ── Add note / rest ────────────────────────────────────────


class TestAddNote:
    def test_add_note(self):
        seq = EditorSequence()
        seq.add_note(60)
        assert seq.note_count == 1
        n = seq.notes[0]
        assert n.note == 60
        assert n.time_beats == 0.0
        assert n.duration_beats == 1.0  # default 1/4 = 1 beat
        assert n.track == 0

    def test_add_note_advances_cursor(self):
        seq = EditorSequence()
        seq.add_note(60)
        assert seq.cursor_beats == 1.0  # advanced by 1/4

    def test_add_note_to_active_track(self):
        seq = EditorSequence()
        seq.set_active_track(2)
        seq.add_note(60)
        assert seq.notes[0].track == 2

    def test_add_multiple_notes_sorted(self):
        seq = EditorSequence()
        seq.set_step_duration("1/8")
        seq.add_note(60)
        seq.add_note(64)
        seq.add_note(67)
        assert [n.note for n in seq.notes] == [60, 64, 67]
        assert seq.notes[0].time_beats < seq.notes[1].time_beats

    def test_add_note_clamps_midi(self):
        seq = EditorSequence()
        seq.add_note(200)
        assert seq.notes[0].note == 127
        seq.add_note(-5)
        # Second note at beat 1.0, clamped to 0
        assert seq.notes[1].note == 0


class TestAddRest:
    def test_add_rest(self):
        seq = EditorSequence()
        seq.add_rest()
        assert seq.rest_count == 1
        assert seq.rests[0].time_beats == 0.0
        assert seq.rests[0].duration_beats == 1.0

    def test_add_rest_advances_cursor(self):
        seq = EditorSequence()
        seq.add_rest()
        assert seq.cursor_beats == 1.0

    def test_add_rest_to_active_track(self):
        seq = EditorSequence()
        seq.set_active_track(1)
        seq.add_rest()
        assert seq.rests[0].track == 1


# ── Delete ─────────────────────────────────────────────────


class TestDelete:
    def test_delete_note(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.delete_note(0)
        assert seq.note_count == 0

    def test_delete_note_invalid_index(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.delete_note(5)  # no crash
        assert seq.note_count == 1

    def test_delete_rest(self):
        seq = EditorSequence()
        seq.add_rest()
        seq.delete_rest(0)
        assert seq.rest_count == 0

    def test_delete_notes_batch(self):
        seq = EditorSequence()
        seq.set_step_duration("1/8")
        for note in [60, 62, 64, 65, 67]:
            seq.add_note(note)
        seq.delete_notes([1, 3])  # delete 62, 65
        assert seq.note_count == 3
        assert [n.note for n in seq.notes] == [60, 64, 67]


# ── Move ───────────────────────────────────────────────────


class TestMove:
    def test_move_note_time(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.move_note(0, time_delta=2.0)
        assert seq.notes[0].time_beats == 2.0

    def test_move_note_pitch(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.move_note(0, pitch_delta=5)
        assert seq.notes[0].note == 65

    def test_move_note_clamps_time(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.move_note(0, time_delta=-10.0)
        assert seq.notes[0].time_beats == 0.0

    def test_move_note_clamps_pitch(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.move_note(0, pitch_delta=200)
        assert seq.notes[0].note == 127

    def test_move_notes_batch(self):
        seq = EditorSequence()
        seq.set_step_duration("1/8")
        seq.add_note(60)
        seq.add_note(64)
        seq.move_notes([0, 1], time_delta=4.0, pitch_delta=2)
        assert seq.notes[0].time_beats == 4.0
        assert seq.notes[0].note == 62


# ── Resize ─────────────────────────────────────────────────


class TestResize:
    def test_resize_note(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.resize_note(0, 2.0)
        assert seq.notes[0].duration_beats == 2.0

    def test_resize_clamps_minimum(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.resize_note(0, 0.01)
        assert seq.notes[0].duration_beats == 0.25  # min


# ── Undo / Redo ────────────────────────────────────────────


class TestUndoRedo:
    def test_undo_add(self):
        seq = EditorSequence()
        seq.add_note(60)
        assert seq.note_count == 1
        seq.undo()
        assert seq.note_count == 0

    def test_redo_add(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.undo()
        seq.redo()
        assert seq.note_count == 1

    def test_undo_delete(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.delete_note(0)
        seq.undo()
        assert seq.note_count == 1

    def test_undo_move(self):
        seq = EditorSequence()
        seq.add_note(60)
        original_time = seq.notes[0].time_beats
        seq.move_note(0, time_delta=5.0)
        seq.undo()
        assert seq.notes[0].time_beats == original_time

    def test_can_undo_redo_flags(self):
        seq = EditorSequence()
        assert not seq.can_undo
        assert not seq.can_redo
        seq.add_note(60)
        assert seq.can_undo
        seq.undo()
        assert seq.can_redo

    def test_undo_restores_cursor(self):
        seq = EditorSequence()
        assert seq.cursor_beats == 0.0
        seq.add_note(60)
        assert seq.cursor_beats == 1.0
        seq.undo()
        assert seq.cursor_beats == 0.0

    def test_undo_stack_limit(self):
        seq = EditorSequence()
        for i in range(150):
            seq.add_note(60 + (i % 12))
        # Should have 100 undo steps, not 150
        count = 0
        while seq.can_undo:
            seq.undo()
            count += 1
        assert count == 100

    def test_new_edit_clears_redo(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.undo()
        assert seq.can_redo
        seq.add_note(64)
        assert not seq.can_redo


# ── Clear ──────────────────────────────────────────────────


class TestClear:
    def test_clear(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.add_rest()
        seq.clear()
        assert seq.note_count == 0
        assert seq.rest_count == 0
        assert seq.cursor_beats == 0.0

    def test_clear_undo(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.clear()
        seq.undo()
        assert seq.note_count == 1

    def test_clear_empty_no_undo(self):
        seq = EditorSequence()
        seq.clear()
        assert not seq.can_undo


# ── Track management ───────────────────────────────────────


class TestTrackManagement:
    def test_set_active_track(self):
        seq = EditorSequence()
        seq.set_active_track(2)
        assert seq.active_track == 2

    def test_set_invalid_active_track(self):
        seq = EditorSequence()
        seq.set_active_track(99)
        assert seq.active_track == 0

    def test_add_track(self):
        seq = EditorSequence(num_tracks=2)
        idx = seq.add_track("Bass")
        assert idx == 2
        assert seq.track_count == 3
        assert seq.tracks[2].name == "Bass"

    def test_add_track_max(self):
        seq = EditorSequence(num_tracks=12)
        idx = seq.add_track()
        assert idx == -1
        assert seq.track_count == 12

    def test_remove_track(self):
        seq = EditorSequence(num_tracks=3)
        seq.set_active_track(1)
        seq.add_note(60)  # note on track 1
        seq.set_active_track(2)
        seq.add_note(72)  # note on track 2
        seq.remove_track(1)  # remove middle track
        assert seq.track_count == 2
        # Note on track 1 removed, track 2 note shifted to track 1
        assert seq.note_count == 1
        assert seq.notes[0].track == 1
        assert seq.notes[0].note == 72

    def test_remove_last_track_prevented(self):
        seq = EditorSequence(num_tracks=1)
        seq.remove_track(0)
        assert seq.track_count == 1

    def test_notes_in_track(self):
        seq = EditorSequence()
        seq.set_active_track(0)
        seq.add_note(60)
        seq.set_active_track(1)
        seq.add_note(72)
        assert len(seq.notes_in_track(0)) == 1
        assert seq.notes_in_track(0)[0].note == 60
        assert len(seq.notes_in_track(1)) == 1


# ── Copy / Paste ───────────────────────────────────────────


class TestCopyPaste:
    def test_copy_paste(self):
        seq = EditorSequence()
        seq.set_step_duration("1/8")
        seq.add_note(60)
        seq.add_note(64)
        seq.copy_notes([0, 1])
        seq.cursor_beats = 4.0
        seq.paste_at_cursor()
        assert seq.note_count == 4
        # Pasted notes at beat 4.0 and 4.5
        pasted = [n for n in seq.notes if n.time_beats >= 4.0]
        assert len(pasted) == 2

    def test_paste_empty_clipboard(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.paste_at_cursor()  # no crash, clipboard empty
        assert seq.note_count == 1

    def test_clipboard_empty(self):
        seq = EditorSequence()
        assert seq.clipboard_empty
        seq.add_note(60)
        seq.copy_notes([0])
        assert not seq.clipboard_empty

    def test_paste_to_active_track(self):
        seq = EditorSequence()
        seq.set_active_track(0)
        seq.add_note(60)
        seq.copy_notes([0])
        seq.set_active_track(2)
        seq.cursor_beats = 4.0
        seq.paste_at_cursor()
        pasted = [n for n in seq.notes if n.time_beats >= 4.0]
        assert pasted[0].track == 2


# ── Duration / bar count ───────────────────────────────────


class TestDuration:
    def test_duration_beats(self):
        seq = EditorSequence()
        seq.set_step_duration("1/4")
        seq.add_note(60)  # 0..1
        seq.add_note(64)  # 1..2
        assert seq.duration_beats == 2.0

    def test_duration_seconds(self):
        seq = EditorSequence(tempo_bpm=120.0)
        seq.add_note(60)  # 1 beat = 0.5s at 120 BPM
        assert abs(seq.duration_seconds - 0.5) < 0.001

    def test_bar_count_4_4(self):
        seq = EditorSequence(time_signature=(4, 4))
        seq.set_step_duration("1/4")
        for _ in range(8):  # 8 quarter notes = 2 bars
            seq.add_note(60)
        assert seq.bar_count == 2

    def test_bar_count_3_4(self):
        seq = EditorSequence(time_signature=(3, 4))
        seq.set_step_duration("1/4")
        for _ in range(6):  # 6 quarter notes = 2 bars in 3/4
            seq.add_note(60)
        assert seq.bar_count == 2

    def test_empty_bar_count(self):
        seq = EditorSequence()
        assert seq.bar_count == 0


# ── Note index in rect ─────────────────────────────────────


class TestNoteRect:
    def test_basic_rect(self):
        seq = EditorSequence()
        seq.set_step_duration("1/4")
        seq.add_note(60)  # at beat 0
        seq.add_note(72)  # at beat 1
        seq.add_note(60)  # at beat 2
        # rect: time [0, 2), note [58, 62]
        indices = seq.note_indices_in_rect(0.0, 2.0, 58, 62)
        assert indices == [0]  # only the first C4 at beat 0

    def test_empty_rect(self):
        seq = EditorSequence()
        seq.add_note(60)
        indices = seq.note_indices_in_rect(10.0, 20.0, 60, 72)
        assert indices == []


# ── Conversion ─────────────────────────────────────────────


class TestConversion:
    def test_to_midi_file_events(self):
        seq = EditorSequence(tempo_bpm=120.0)
        seq.add_note(60)
        events = seq.to_midi_file_events()
        assert len(events) == 2  # note_on + note_off
        on = [e for e in events if e.event_type == "note_on"]
        off = [e for e in events if e.event_type == "note_off"]
        assert len(on) == 1
        assert len(off) == 1
        # At 120 BPM, 1 beat = 0.5s
        assert abs(on[0].time_seconds - 0.0) < 0.001
        assert abs(off[0].time_seconds - 0.5) < 0.001

    def test_to_midi_file_events_muted_track(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq._tracks[0].muted = True
        events = seq.to_midi_file_events()
        assert len(events) == 0

    def test_to_recorded_events(self):
        seq = EditorSequence(tempo_bpm=60.0)
        seq.add_note(60)  # 1 beat = 1.0s at 60 BPM
        events = seq.to_recorded_events()
        assert len(events) == 2
        on = [e for e in events if e.event_type == "note_on"]
        assert abs(on[0].timestamp - 0.0) < 0.001

    def test_from_midi_file_events(self):
        from cyber_qin.core.midi_file_player import MidiFileEvent

        events = [
            MidiFileEvent(0.0, "note_on", 60, 100, track=0, channel=0),
            MidiFileEvent(0.5, "note_off", 60, 0, track=0, channel=0),
            MidiFileEvent(0.5, "note_on", 64, 80, track=0, channel=0),
            MidiFileEvent(1.0, "note_off", 64, 0, track=0, channel=0),
        ]
        seq = EditorSequence.from_midi_file_events(events, tempo_bpm=120.0)
        assert seq.note_count == 2
        assert seq.notes[0].note == 60
        assert abs(seq.notes[0].time_beats - 0.0) < 0.01
        assert abs(seq.notes[0].duration_beats - 1.0) < 0.01
        assert seq.notes[1].note == 64

    def test_from_midi_file_events_unpaired(self):
        from cyber_qin.core.midi_file_player import MidiFileEvent

        events = [
            MidiFileEvent(0.0, "note_on", 60, 100),
            # No note_off — should get default duration
        ]
        seq = EditorSequence.from_midi_file_events(events, tempo_bpm=120.0)
        assert seq.note_count == 1
        assert seq.notes[0].duration_beats == 0.5  # default


# ── Project serialization ──────────────────────────────────


class TestProjectSerialization:
    def test_roundtrip(self):
        seq = EditorSequence(tempo_bpm=90.0, time_signature=(3, 4), num_tracks=3)
        seq.set_step_duration("1/8")
        seq.add_note(60)
        seq.add_note(64)
        seq.add_rest()
        seq.set_active_track(1)
        seq.add_note(72)

        data = seq.to_project_dict()
        restored = EditorSequence.from_project_dict(data)

        assert restored.tempo_bpm == 90.0
        assert restored.time_signature == (3, 4)
        assert restored.track_count == 3
        assert restored.note_count == 3
        assert restored.rest_count == 1
        assert restored.step_label == "1/8"

    def test_version_field(self):
        seq = EditorSequence()
        data = seq.to_project_dict()
        assert data["version"] == 1

    def test_empty_roundtrip(self):
        seq = EditorSequence()
        data = seq.to_project_dict()
        restored = EditorSequence.from_project_dict(data)
        assert restored.note_count == 0
        assert restored.track_count == 4


# ── Tempo property ─────────────────────────────────────────


class TestTempo:
    def test_tempo_clamp_low(self):
        seq = EditorSequence()
        seq.tempo_bpm = 10.0
        assert seq.tempo_bpm == 40.0

    def test_tempo_clamp_high(self):
        seq = EditorSequence()
        seq.tempo_bpm = 500.0
        assert seq.tempo_bpm == 300.0


# ── All items ──────────────────────────────────────────────


class TestAllItems:
    def test_sorted_by_time(self):
        seq = EditorSequence()
        seq.set_step_duration("1/4")
        seq.add_note(60)  # beat 0
        seq.add_rest()  # beat 1
        seq.add_note(64)  # beat 2
        items = seq.all_items
        assert len(items) == 3
        assert items[0].time_beats < items[1].time_beats < items[2].time_beats


# ── Snapshot with tracks ──────────────────────────────────


class TestSnapshotTracks:
    def test_undo_remove_track_restores_tracks(self):
        seq = EditorSequence(num_tracks=3)
        seq.set_active_track(1)
        seq.add_note(60)
        seq.remove_track(1)
        assert seq.track_count == 2
        seq.undo()
        assert seq.track_count == 3
        assert seq.note_count == 1
        assert seq.notes[0].track == 1

    def test_undo_preserves_track_metadata(self):
        seq = EditorSequence(num_tracks=2)
        seq._tracks[0].name = "Lead"
        seq._tracks[0].muted = True
        seq.add_note(60)
        seq.undo()
        assert seq._tracks[0].name == "Lead"
        assert seq._tracks[0].muted is True


# ── Reorder tracks ────────────────────────────────────────


class TestReorderTracks:
    def test_reorder_basic(self):
        seq = EditorSequence(num_tracks=3)
        seq.set_active_track(0)
        seq.add_note(60)
        seq.set_active_track(2)
        seq.add_note(72)
        # Swap track 0 and 2: new_order = [2, 1, 0]
        seq.reorder_tracks([2, 1, 0])
        # Old track 0 is now track 2, old track 2 is now track 0
        assert seq.notes_in_track(2)[0].note == 60
        assert seq.notes_in_track(0)[0].note == 72

    def test_reorder_active_track_follows(self):
        seq = EditorSequence(num_tracks=3)
        seq.set_active_track(0)
        seq.reorder_tracks([2, 1, 0])
        assert seq.active_track == 2

    def test_reorder_undo(self):
        seq = EditorSequence(num_tracks=3)
        original_names = [t.name for t in seq.tracks]
        seq.reorder_tracks([2, 1, 0])
        seq.undo()
        assert [t.name for t in seq.tracks] == original_names

    def test_reorder_invalid_permutation_ignored(self):
        seq = EditorSequence(num_tracks=3)
        seq.reorder_tracks([0, 0, 1])  # invalid — not a permutation
        assert seq.track_count == 3  # unchanged


# ── Delete items ──────────────────────────────────────────


class TestDeleteItems:
    def test_delete_mixed(self):
        seq = EditorSequence()
        seq.set_step_duration("1/8")
        seq.add_note(60)
        seq.add_note(64)
        seq.add_rest()
        seq.add_note(67)
        seq.delete_items([0, 2], [0])
        assert seq.note_count == 1
        assert seq.notes[0].note == 64
        assert seq.rest_count == 0

    def test_delete_items_undo(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.add_rest()
        seq.delete_items([0], [0])
        seq.undo()
        assert seq.note_count == 1
        assert seq.rest_count == 1

    def test_delete_items_empty(self):
        seq = EditorSequence()
        seq.delete_items([], [])
        assert not seq.can_undo  # no undo pushed for empty delete


# ── Resize notes batch ────────────────────────────────────


class TestResizeNotes:
    def test_resize_batch(self):
        seq = EditorSequence()
        seq.set_step_duration("1/4")
        seq.add_note(60)
        seq.add_note(64)
        seq.resize_notes([0, 1], 1.0)
        assert seq.notes[0].duration_beats == 2.0
        assert seq.notes[1].duration_beats == 2.0

    def test_resize_clamps_minimum(self):
        seq = EditorSequence()
        seq.add_note(60)
        seq.resize_notes([0], -10.0)
        assert seq.notes[0].duration_beats == 0.25

    def test_resize_undo(self):
        seq = EditorSequence()
        seq.add_note(60)
        original_dur = seq.notes[0].duration_beats
        seq.resize_notes([0], 2.0)
        seq.undo()
        assert seq.notes[0].duration_beats == original_dur


# ── Rest rect query ───────────────────────────────────────


class TestRestRect:
    def test_basic(self):
        seq = EditorSequence()
        seq.set_step_duration("1/4")
        seq.add_rest()  # beat 0
        seq.add_rest()  # beat 1
        seq.add_rest()  # beat 2
        indices = seq.rest_indices_in_rect(0.0, 2.0)
        assert indices == [0, 1]

    def test_empty(self):
        seq = EditorSequence()
        seq.add_rest()
        assert seq.rest_indices_in_rect(10.0, 20.0) == []


# ── Copy items ────────────────────────────────────────────


class TestCopyItems:
    def test_copy_mixed(self):
        seq = EditorSequence()
        seq.set_step_duration("1/4")
        seq.add_note(60)
        seq.add_rest()
        seq.copy_items([0], [0])
        assert not seq.clipboard_empty
        seq.cursor_beats = 4.0
        seq.paste_at_cursor()
        assert seq.note_count == 2
        assert seq.rest_count == 2

    def test_copy_items_normalizes_time(self):
        seq = EditorSequence()
        seq.set_step_duration("1/4")
        seq.add_note(60)  # beat 0
        seq.add_note(64)  # beat 1
        seq.copy_items([1], [])
        seq.cursor_beats = 0.0
        seq.paste_at_cursor()
        # Pasted note should be at beat 0, not beat 1
        pasted = [n for n in seq.notes if n.time_beats < 0.01]
        assert len(pasted) == 2  # original + pasted


# ── Track management extras ───────────────────────────────


class TestTrackExtras:
    def test_rename_track(self):
        seq = EditorSequence()
        seq.rename_track(0, "Melody")
        assert seq.tracks[0].name == "Melody"

    def test_set_track_muted(self):
        seq = EditorSequence()
        seq.set_track_muted(0, True)
        assert seq.tracks[0].muted is True

    def test_set_track_solo(self):
        seq = EditorSequence()
        seq.set_track_solo(1, True)
        assert seq.tracks[1].solo is True


# ── Rest + note playback conversion ──────────────────────


class TestRestNotePlayback:
    """Verify MIDI event generation when rests are mixed with notes."""

    def test_rest_before_notes_timing(self):
        """Events after rests should have correct time_seconds."""
        seq = EditorSequence(tempo_bpm=120.0)
        seq.set_step_duration("1/4")  # 1 beat = 0.5s at 120 BPM
        seq.add_rest()  # beat 0–1 (rest)
        seq.add_rest()  # beat 1–2 (rest)
        seq.add_note(60)  # beat 2–3 (note)
        events = seq.to_midi_file_events()
        # Should have 2 events: note_on, note_off
        assert len(events) == 2
        # note starts at beat 2 = 1.0s at 120 BPM
        assert abs(events[0].time_seconds - 1.0) < 0.001
        # note ends at beat 3 = 1.5s
        assert abs(events[1].time_seconds - 1.5) < 0.001

    def test_duration_includes_trailing_rest(self):
        """duration_seconds should include rests at the end."""
        seq = EditorSequence(tempo_bpm=120.0)
        seq.set_step_duration("1/4")
        seq.add_note(60)  # beat 0–1
        seq.add_rest()  # beat 1–2
        # duration should be 2 beats = 1.0s
        assert abs(seq.duration_seconds - 1.0) < 0.001
        # but MIDI events only go to beat 1 = 0.5s
        events = seq.to_midi_file_events()
        max_event_time = max(e.time_seconds for e in events)
        assert abs(max_event_time - 0.5) < 0.001

    def test_rest_only_sequence_has_no_events(self):
        """A sequence with only rests should produce no MIDI events."""
        seq = EditorSequence()
        seq.add_rest()
        seq.add_rest()
        events = seq.to_midi_file_events()
        assert len(events) == 0
        # But duration should still reflect the rests
        assert seq.duration_beats > 0
