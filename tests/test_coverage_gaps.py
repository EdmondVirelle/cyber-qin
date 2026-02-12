"""Supplementary tests to improve coverage for modules with minor gaps."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from unittest import mock

import pytest

# ── note_sequence.py edge cases ─────────────────────────────

from cyber_qin.core.note_sequence import NoteSequence, _MAX_UNDO


class TestNoteSequenceEdgeCases:
    def test_undo_stack_cap(self):
        """_push_undo should cap the stack at _MAX_UNDO."""
        seq = NoteSequence()
        for i in range(_MAX_UNDO + 10):
            seq.add_note(60 + (i % 12))
        assert len(seq._undo_stack) <= _MAX_UNDO

    def test_undo_empty(self):
        """Undo on empty stack should do nothing."""
        seq = NoteSequence()
        seq.undo()  # should not raise
        assert seq.note_count == 0

    def test_redo_empty(self):
        """Redo on empty stack should do nothing."""
        seq = NoteSequence()
        seq.redo()  # should not raise
        assert seq.note_count == 0

    def test_move_out_of_range(self):
        """Move with out-of-range index should do nothing."""
        seq = NoteSequence()
        seq.add_note(60)
        seq.move_note(99, time_delta=1.0)  # Should not raise
        seq.move_note(-1, time_delta=1.0)  # Should not raise
        assert seq.note_count == 1

    def test_from_midi_orphaned_note_on(self):
        """note_on without matching note_off should get default duration."""
        from cyber_qin.core.midi_file_player import MidiFileEvent
        events = [
            MidiFileEvent(time_seconds=0.0, event_type="note_on", note=60, velocity=100),
            # No matching note_off for note 60
        ]
        seq = NoteSequence.from_midi_file_events(events)
        assert seq.note_count == 1
        assert seq.notes[0].duration_seconds == 0.25  # default


# ── mapping_schemes.py edge cases ───────────────────────────

from cyber_qin.core.mapping_schemes import (
    get_scheme, list_schemes, default_scheme_id,
    _build_generic_88,
)


class TestMappingSchemeEdgeCases:
    def test_generic_88_covers_full_range(self):
        """88-key scheme should cover MIDI 21-108."""
        scheme = _build_generic_88()
        assert scheme.key_count == 88
        assert scheme.midi_range == (21, 108)
        # Should have mappings for all 88 keys
        assert len(scheme.mapping) == 88
        # MIDI 219 and 230-231 lines exercise the inner break conditions
        for note in range(21, 109):
            assert note in scheme.mapping


# ── project_file.py error path ──────────────────────────────

from cyber_qin.core import project_file


class TestProjectFileEdgeCases:
    def test_load_autosave_corrupt_file(self, tmp_path):
        """load_autosave should return None if file is corrupt."""
        with mock.patch.object(project_file, "_AUTOSAVE_FILE", tmp_path / "autosave.cqp"):
            # Write garbage
            (tmp_path / "autosave.cqp").write_bytes(b"not a gzip file")
            result = project_file.load_autosave()
            assert result is None


# ── midi_preprocessor.py missing lines ──────────────────────

from cyber_qin.core.midi_file_player import MidiFileEvent
from cyber_qin.core.midi_preprocessor import (
    normalize_octave_flowing,
    preprocess,
    _get_octave_candidates,
)


class TestMidiPreprocessorEdgeCases:
    def test_flowing_fold_empty_candidates(self):
        """When pitch has no valid candidate in range, fallback fold is used."""
        # Use a very narrow range that no pitch class can fit into
        events = [
            MidiFileEvent(time_seconds=0.0, event_type="note_on",
                          note=130, velocity=100, track=0, channel=0),
            MidiFileEvent(time_seconds=0.5, event_type="note_off",
                          note=130, velocity=0, track=0, channel=0),
        ]
        # Range 48-83 — note 130 has no valid octave position via _get_octave_candidates
        # if we constrain range to, say, note_min=60, note_max=60 (only one note)
        # But 130 % 12 = 10, and 60 % 12 = 0, so no candidates in range [60, 60]
        result = normalize_octave_flowing(events, note_min=60, note_max=60)
        # Should still produce events (fallback)
        assert len(result) == 2

    def test_flowing_fold_note_off_no_pair(self):
        """note_off without matching note_on should use simple fold."""
        events = [
            MidiFileEvent(time_seconds=0.0, event_type="note_off",
                          note=96, velocity=0, track=0, channel=0),
        ]
        result = normalize_octave_flowing(events, note_min=48, note_max=83)
        assert len(result) == 1
        assert result[0].note <= 83

    def test_preprocess_empty(self):
        """Empty events should return empty stats."""
        result, stats = preprocess([])
        assert stats.total_notes == 0
        assert result == []

    def test_preprocess_no_note_ons(self):
        """Events without note_on should handle gracefully."""
        events = [
            MidiFileEvent(time_seconds=0.0, event_type="note_off",
                          note=60, velocity=0, track=0, channel=0),
        ]
        result, stats = preprocess(events, remove_percussion=False)
        assert stats.total_notes == 0


# Note: MidiOutputPlayer uses a lazy Qt class pattern (_ensure_qt_class)
# and cannot be tested without a running QApplication. Those lines (81% → ~90%)
# would require integration tests with Qt event loop.

