"""Supplementary beat_sequence tests targeting uncovered lines."""

from __future__ import annotations

import copy

import pytest

from cyber_qin.core.beat_sequence import (
    BeatNote, BeatRest, EditorSequence, Track, _MAX_UNDO,
)


class TestBeatSequenceEdgeCases:
    # ── Undo / Redo empty ────────────────────────────────────

    def test_undo_empty(self):
        seq = EditorSequence()
        seq.undo()  # line 299 — should not raise

    def test_redo_empty(self):
        seq = EditorSequence()
        seq.redo()  # line 305 — should not raise

    # ── time_signature setter ────────────────────────────────

    def test_time_signature_setter(self):
        seq = EditorSequence()
        seq.time_signature = (3, 4)  # line 207
        assert seq.time_signature == (3, 4)

    # ── bar_count with rests ─────────────────────────────────

    def test_bar_count_with_rests_only(self):
        seq = EditorSequence()
        seq.add_rest()  # at cursor (0.0)
        # lines 226-228 — rest contributes to max_beat
        assert seq.bar_count >= 1

    def test_bar_count_with_notes_and_rests(self):
        seq = EditorSequence()
        seq.add_note_at(0.0, 60)
        seq._cursor_beats = 5.0
        seq.add_rest()
        bc = seq.bar_count
        assert bc >= 2  # 5 beats + rest duration → at least 2 bars in 4/4

    def test_bar_count_beats_per_bar_zero(self):
        """bpb <= 0 should return 0 (line 231)."""
        seq = EditorSequence()
        seq.add_note_at(0.0, 60)
        seq.time_signature = (0, 4)  # degenerate → bpb = 0
        assert seq.bar_count == 0

    # ── reorder_tracks covers rests (line 358) ───────────────

    def test_reorder_tracks_reassigns_rests(self):
        seq = EditorSequence(num_tracks=1)
        seq.add_track("B")  # now tracks 0 and 1
        seq.add_rest()  # rest on track 0
        seq.set_active_track(1)
        seq._cursor_beats = 0.0
        seq.add_rest()  # rest on track 1
        seq.reorder_tracks([1, 0])  # swap
        # After reorder, original track 0 rests should be on track 1
        rests_t0 = seq.rests_in_track(0)
        rests_t1 = seq.rests_in_track(1)
        assert len(rests_t0) == 1
        assert len(rests_t1) == 1

    # ── remove_track guards (lines 362-363) ──────────────────

    def test_remove_track_out_of_range(self):
        seq = EditorSequence(num_tracks=2)
        seq.remove_track(99)  # line 363 — should not raise
        assert len(seq.tracks) == 2

    def test_remove_track_last_track(self):
        seq = EditorSequence(num_tracks=1)
        seq.remove_track(0)  # Can't remove last track
        assert len(seq.tracks) == 1

    # ── delete_notes / delete_rests (lines 420, 426-430) ─────

    def test_delete_notes_empty_list(self):
        seq = EditorSequence()
        seq.add_note_at(0.0, 60)
        seq.delete_notes([])  # line 420 — no-op
        assert seq.note_count == 1

    def test_delete_rests_empty_list(self):
        seq = EditorSequence()
        seq.add_rest()
        seq.delete_rests([])  # line 426 — no-op

    def test_delete_rests_batch(self):
        seq = EditorSequence()
        seq.add_rest()  # at cursor 0.0
        seq.add_rest()  # cursor advanced, so at next step
        seq.delete_rests([0, 1])  # lines 428-430
        assert len(seq.rests_in_track(0)) == 0

    # ── move_note out of range (line 436) ────────────────────

    def test_move_note_out_of_range(self):
        seq = EditorSequence()
        seq.add_note_at(0.0, 60)
        seq.move_note(99, time_delta=1.0)  # line 436 — no-op

    # ── move_notes empty (line 447) ──────────────────────────

    def test_move_notes_empty(self):
        seq = EditorSequence()
        seq.add_note_at(0.0, 60)
        seq.move_notes([], 1.0, 0)  # line 447 — no-op

    # ── resize_note out of range (line 458) ──────────────────

    def test_resize_note_out_of_range(self):
        seq = EditorSequence()
        seq.resize_note(99, 2.0)  # line 458 — no-op

    # ── resize_notes empty (line 465) ────────────────────────

    def test_resize_notes_empty(self):
        seq = EditorSequence()
        seq.add_note_at(0.0, 60)
        seq.resize_notes([], 1.0)  # line 465 — no-op

    # ── copy_items empty result (line 567) ───────────────────

    def test_copy_items_out_of_range(self):
        seq = EditorSequence()
        seq.copy_items([99], [])  # line 567 — no items copied

    def test_copy_notes_empty(self):
        seq = EditorSequence()
        seq.copy_notes([])  # line 575 — no-op

    def test_copy_notes_out_of_range(self):
        seq = EditorSequence()
        seq.copy_notes([99])  # line 578 — no valid items

    # ── to_recorded_events with solo/mute (lines 606, 619, 657, 659, 665) ─

    def test_to_recorded_events_muted(self):
        seq = EditorSequence()
        seq.add_note_at(0.0, 60)
        seq.set_track_muted(0, True)  # line 657
        events = seq.to_recorded_events()
        assert len(events) == 0  # muted track excluded

    def test_to_recorded_events_solo(self):
        seq = EditorSequence()
        seq.add_track("B")
        seq.add_note_at(0.0, 60)  # track 0
        seq.set_active_track(1)
        seq.add_note_at(0.0, 72)  # track 1
        seq.set_track_solo(1, True)  # line 659
        events = seq.to_recorded_events()
        # Only track 1 notes should appear
        note_ons = [e for e in events if e.event_type == "note_on"]
        assert len(note_ons) == 1
        assert note_ons[0].note == 72

    def test_to_midi_file_events_solo_excludes_unsoloed(self):
        seq = EditorSequence()
        seq.add_track("B")
        seq.add_note_at(0.0, 60)  # track 0
        seq.set_active_track(1)
        seq.add_note_at(0.0, 72)  # track 1
        seq.set_track_solo(0, True)  # only track 0 soloed (line 619)
        events = seq.to_midi_file_events()
        note_ons = [e for e in events if e.event_type == "note_on"]
        assert len(note_ons) == 1
        assert note_ons[0].note == 60

    # ── from_project_dict empty tracks (line 785) ────────────

    def test_from_project_dict_no_tracks(self):
        """Loading a project with no tracks should create default track (line 785)."""
        data = {
            "tempo_bpm": 120,
            "time_signature": [4, 4],
            "tracks": [],
            "notes": [],
            "rests": [],
        }
        seq = EditorSequence.from_project_dict(data)
        assert len(seq.tracks) == 1  # default track created
        assert seq.tracks[0].name == "Track 1"
