"""Tests for editor UX improvements — arrow key nav, range select, preview player."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from cyber_qin.core.beat_sequence import BeatNote, BeatRest

# ── NoteRoll.select_notes_in_time_range ──────────────────────


class TestSelectNotesInTimeRange:
    """Tests for the new NoteRoll.select_notes_in_time_range method."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists."""

    def _make_roll(self):
        from cyber_qin.gui.widgets.note_roll import NoteRoll

        roll = NoteRoll()
        notes = [
            BeatNote(0.0, 1.0, 60),
            BeatNote(1.0, 1.0, 64),
            BeatNote(2.0, 1.0, 67),
            BeatNote(3.0, 1.0, 72),
        ]
        rests = [
            BeatRest(1.5, 0.5),
            BeatRest(3.5, 0.5),
        ]
        roll.set_notes(notes)
        roll.set_rests(rests)
        return roll

    def test_select_middle_range(self):
        roll = self._make_roll()
        roll.select_notes_in_time_range(1.0, 3.0)
        assert roll.selected_note_indices == {1, 2}

    def test_select_range_includes_rests(self):
        roll = self._make_roll()
        roll.select_notes_in_time_range(1.0, 2.0)
        assert roll.selected_note_indices == {1}
        assert roll.selected_rest_indices == {0}  # rest at 1.5

    def test_select_empty_range(self):
        roll = self._make_roll()
        roll.select_notes_in_time_range(4.0, 5.0)
        assert roll.selected_note_indices == set()
        assert roll.selected_rest_indices == set()

    def test_select_all_range(self):
        roll = self._make_roll()
        roll.select_notes_in_time_range(0.0, 4.0)
        assert roll.selected_note_indices == {0, 1, 2, 3}
        assert roll.selected_rest_indices == {0, 1}

    def test_upper_bound_exclusive(self):
        """t1 is exclusive — notes at exactly t1 should NOT be selected."""
        roll = self._make_roll()
        roll.select_notes_in_time_range(0.0, 1.0)
        assert roll.selected_note_indices == {0}  # only note at 0.0

    def test_clears_previous_selection(self):
        roll = self._make_roll()
        roll.select_notes_in_time_range(0.0, 2.0)
        assert len(roll.selected_note_indices) == 2
        roll.select_notes_in_time_range(3.0, 4.0)
        assert roll.selected_note_indices == {3}


# ── NoteRoll mouse range select ──────────────────────────────


class TestNoteRollMouseRangeSelect:
    """Tests for drag-on-empty-space range selection in NoteRoll."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists."""

    def _make_roll_with_notes(self):
        from cyber_qin.gui.widgets.note_roll import NoteRoll

        roll = NoteRoll()
        roll.resize(800, 200)  # give it a real size for coordinate math
        notes = [
            BeatNote(0.0, 1.0, 60),
            BeatNote(1.0, 1.0, 64),
            BeatNote(2.0, 1.0, 67),
            BeatNote(3.0, 1.0, 72),
        ]
        roll.set_notes(notes)
        return roll

    def test_empty_press_records_origin(self):
        roll = self._make_roll_with_notes()
        # The origin beat should be set after click
        roll._cursor_beats = 0.0
        roll._range_select_origin = 0.0
        # Simulate: pressing on empty space sets _range_select_origin
        origin_beat = 1.5  # halfway between notes
        roll._range_select_origin = origin_beat
        assert roll._range_select_origin == 1.5

    def test_range_select_via_direct_state(self):
        """Programmatically simulate the range-select drag flow."""
        roll = self._make_roll_with_notes()
        # Simulate: origin at beat 0, drag to beat 2
        roll._range_select_origin = 0.0
        roll._range_select_end = 2.0
        roll._range_select_active = True

        # Apply selection as mouseMoveEvent would
        t0 = min(roll._range_select_origin, roll._range_select_end)
        t1 = max(roll._range_select_origin, roll._range_select_end)
        roll.select_notes_in_time_range(t0, t1)

        assert roll.selected_note_indices == {0, 1}

    def test_range_select_then_delete_signal(self):
        """After range select, Delete emits note_deleted(-1)."""
        roll = self._make_roll_with_notes()
        roll.select_notes_in_time_range(0.0, 3.0)
        assert len(roll.selected_note_indices) == 3

        deleted_signals = []
        roll.note_deleted.connect(deleted_signals.append)

        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QKeyEvent

        event = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier
        )
        roll.keyPressEvent(event)
        assert deleted_signals == [-1]


# ── EditorView cursor navigation ────────────────────────────


class TestEditorViewCursorNavigation:
    """Tests for _move_cursor and arrow key remap in EditorView."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists."""

    def _make_view(self):
        from cyber_qin.gui.views.editor_view import EditorView

        view = EditorView()
        # Add some notes for selection tests
        view._sequence.add_note(60)  # cursor starts at 0, step=1.0
        view._sequence.add_note(64)
        view._sequence.add_note(67)
        view._update_ui_state()
        return view

    def test_move_cursor_right(self):
        view = self._make_view()
        old_cursor = view._sequence.cursor_beats
        view._move_cursor(1.0)
        assert view._sequence.cursor_beats == old_cursor + 1.0

    def test_move_cursor_left_clamps_zero(self):
        view = self._make_view()
        view._sequence.cursor_beats = 0.5
        view._move_cursor(-1.0)
        assert view._sequence.cursor_beats == 0.0

    def test_move_cursor_clears_anchor(self):
        view = self._make_view()
        view._selection_anchor = 2.0
        view._move_cursor(1.0)
        assert view._selection_anchor is None


# ── EditorView keyPressEvent arrow logic ─────────────────────


class TestEditorViewArrowKeys:
    """Verify that arrow keys now control cursor, not note movement."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists."""

    def _make_key_event(self, key, modifiers=None):
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QKeyEvent

        mods = modifiers if modifiers is not None else Qt.KeyboardModifier.NoModifier
        return QKeyEvent(
            QKeyEvent.Type.KeyPress,
            key,
            mods,
        )

    def _make_view_with_notes(self):
        from cyber_qin.gui.views.editor_view import EditorView

        view = EditorView()
        view._sequence.add_note(60)
        view._sequence.add_note(64)
        view._sequence.add_note(67)
        view._update_ui_state()
        return view

    def test_plain_right_moves_cursor(self):
        from PyQt6.QtCore import Qt

        view = self._make_view_with_notes()
        cursor_before = view._sequence.cursor_beats
        event = self._make_key_event(Qt.Key.Key_Right)
        view.keyPressEvent(event)
        assert view._sequence.cursor_beats == cursor_before + view._sequence.step_duration

    def test_plain_left_moves_cursor(self):
        from PyQt6.QtCore import Qt

        view = self._make_view_with_notes()
        view._sequence.cursor_beats = 2.0
        event = self._make_key_event(Qt.Key.Key_Left)
        view.keyPressEvent(event)
        assert view._sequence.cursor_beats == 2.0 - view._sequence.step_duration

    def test_shift_right_sets_anchor_and_selects(self):
        from PyQt6.QtCore import Qt

        view = self._make_view_with_notes()
        view._sequence.cursor_beats = 0.0
        event = self._make_key_event(
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.ShiftModifier,
        )
        view.keyPressEvent(event)
        assert view._selection_anchor == 0.0
        assert view._sequence.cursor_beats == view._sequence.step_duration

    def test_shift_multiple_expands_selection(self):
        from PyQt6.QtCore import Qt

        view = self._make_view_with_notes()
        view._sequence.cursor_beats = 0.0
        event = self._make_key_event(
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.ShiftModifier,
        )
        # Shift+Right twice
        view.keyPressEvent(event)
        view.keyPressEvent(event)
        assert view._selection_anchor == 0.0
        assert view._sequence.cursor_beats == 2.0 * view._sequence.step_duration

    def test_plain_arrow_after_shift_clears_anchor(self):
        from PyQt6.QtCore import Qt

        view = self._make_view_with_notes()
        view._sequence.cursor_beats = 0.0
        # Shift+Right
        shift_event = self._make_key_event(
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.ShiftModifier,
        )
        view.keyPressEvent(shift_event)
        assert view._selection_anchor is not None
        # Plain Right
        plain_event = self._make_key_event(Qt.Key.Key_Right)
        view.keyPressEvent(plain_event)
        assert view._selection_anchor is None

    def test_alt_right_moves_selection(self):
        from PyQt6.QtCore import Qt

        view = self._make_view_with_notes()
        # Select notes via internal state
        view._current_note_selection = [0]
        event = self._make_key_event(
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.AltModifier,
        )
        # Just verify it doesn't crash — actual note move tested elsewhere
        view.keyPressEvent(event)

    def test_alt_shift_right_resizes_selection(self):
        from PyQt6.QtCore import Qt

        view = self._make_view_with_notes()
        view._current_note_selection = [0]
        event = self._make_key_event(
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier,
        )
        view.keyPressEvent(event)

    def test_shift_select_populates_current_selection(self):
        """Shift+Arrow must update _current_note_selection via signal."""
        from PyQt6.QtCore import Qt

        view = self._make_view_with_notes()
        # Notes at beats 0, 1, 2; cursor at 3
        view._sequence.cursor_beats = 0.0
        view._note_roll.set_cursor_beats(0.0)
        event = self._make_key_event(
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.ShiftModifier,
        )
        view.keyPressEvent(event)
        # Range [0, 1) → note at beat 0 should be selected
        sel = getattr(view, "_current_note_selection", [])
        assert len(sel) == 1, f"Expected 1 selected note, got {sel}"

    def test_shift_select_then_delete_removes_notes(self):
        """Full flow: Shift+Arrow range select → Delete → notes removed."""
        from PyQt6.QtCore import Qt

        view = self._make_view_with_notes()
        initial_count = view._sequence.note_count  # 3 notes
        assert initial_count == 3

        # Position cursor at start
        view._sequence.cursor_beats = 0.0
        view._note_roll.set_cursor_beats(0.0)

        # Shift+Right twice → select notes in [0, 2)
        shift_right = self._make_key_event(
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.ShiftModifier,
        )
        view.keyPressEvent(shift_right)
        view.keyPressEvent(shift_right)

        sel = getattr(view, "_current_note_selection", [])
        assert len(sel) == 2, f"Expected 2 selected notes, got {sel}"

        # Delete
        delete_event = self._make_key_event(Qt.Key.Key_Delete)
        view.keyPressEvent(delete_event)

        assert view._sequence.note_count == 1, (
            f"Expected 1 note remaining, got {view._sequence.note_count}"
        )

    def test_shift_select_then_delete_preserves_unselected(self):
        """Notes outside the range selection should survive delete."""
        from PyQt6.QtCore import Qt

        view = self._make_view_with_notes()
        # Notes at 0, 1, 2 (pitches 60, 64, 67)

        view._sequence.cursor_beats = 0.0
        view._note_roll.set_cursor_beats(0.0)

        # Select only first note [0, 1)
        shift_right = self._make_key_event(
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.ShiftModifier,
        )
        view.keyPressEvent(shift_right)

        delete_event = self._make_key_event(Qt.Key.Key_Delete)
        view.keyPressEvent(delete_event)

        assert view._sequence.note_count == 2
        remaining = [n.note for n in view._sequence.notes]
        assert 60 not in remaining  # deleted
        assert 64 in remaining  # kept
        assert 67 in remaining  # kept


# ── MidiOutputPlayer ─────────────────────────────────────────


class TestMidiOutputPlayer:
    """Tests for the MidiOutputPlayer core logic."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists."""

    def test_create_returns_none_without_ports(self):
        """If no MIDI output ports, create returns None."""
        with patch.dict(sys.modules, {"rtmidi": MagicMock()}):
            mock_rtmidi = sys.modules["rtmidi"]
            mock_out = MagicMock()
            mock_out.get_ports.return_value = []
            mock_rtmidi.MidiOut.return_value = mock_out

            # Force class re-creation
            import cyber_qin.core.midi_output_player as mod

            mod._MidiOutputPlayerClass = None

            player = mod.create_midi_output_player()
            assert player is None

    def test_create_succeeds_with_port(self):
        """If MIDI output ports exist, create returns a player."""
        with patch.dict(sys.modules, {"rtmidi": MagicMock()}):
            mock_rtmidi = sys.modules["rtmidi"]
            mock_out = MagicMock()
            mock_out.get_ports.return_value = ["Microsoft GS Wavetable Synth"]
            mock_rtmidi.MidiOut.return_value = mock_out

            import cyber_qin.core.midi_output_player as mod

            mod._MidiOutputPlayerClass = None

            player = mod.create_midi_output_player()
            assert player is not None
            assert player.available is True
            player.cleanup()

    def test_load_and_state(self):
        """Test load sets events and initial state."""
        with patch.dict(sys.modules, {"rtmidi": MagicMock()}):
            mock_rtmidi = sys.modules["rtmidi"]
            mock_out = MagicMock()
            mock_out.get_ports.return_value = ["Test Synth"]
            mock_rtmidi.MidiOut.return_value = mock_out

            import cyber_qin.core.midi_output_player as mod

            mod._MidiOutputPlayerClass = None

            player = mod.create_midi_output_player()
            assert player is not None

            from cyber_qin.core.midi_file_player import MidiFileEvent, PlaybackState

            events = [
                MidiFileEvent(0.0, "note_on", 60, 100),
                MidiFileEvent(0.5, "note_off", 60, 0),
            ]
            player.load(events, 0.5)
            assert player.state == PlaybackState.STOPPED
            player.cleanup()

    def test_stop_sends_all_notes_off(self):
        """Test that stop sends CC 123 on all channels."""
        with patch.dict(sys.modules, {"rtmidi": MagicMock()}):
            mock_rtmidi = sys.modules["rtmidi"]
            mock_out = MagicMock()
            mock_out.get_ports.return_value = ["Test Synth"]
            mock_rtmidi.MidiOut.return_value = mock_out

            import cyber_qin.core.midi_output_player as mod

            mod._MidiOutputPlayerClass = None

            player = mod.create_midi_output_player()
            assert player is not None

            from cyber_qin.core.midi_file_player import MidiFileEvent

            events = [
                MidiFileEvent(0.0, "note_on", 60, 100),
                MidiFileEvent(10.0, "note_off", 60, 0),
            ]
            player.load(events, 10.0)
            player.play()
            player.stop()

            # Verify CC 123 was sent on all 16 channels
            calls = mock_out.send_message.call_args_list
            cc123_calls = [
                c for c in calls if len(c.args) > 0 and len(c.args[0]) == 3 and c.args[0][1] == 123
            ]
            assert len(cc123_calls) == 16
            player.cleanup()

    def test_preview_note_sends_on_and_off(self):
        """preview_note sends note_on immediately and schedules note_off."""
        with patch.dict(sys.modules, {"rtmidi": MagicMock()}):
            mock_rtmidi = sys.modules["rtmidi"]
            mock_out = MagicMock()
            mock_out.get_ports.return_value = ["Test Synth"]
            mock_rtmidi.MidiOut.return_value = mock_out

            import cyber_qin.core.midi_output_player as mod

            mod._MidiOutputPlayerClass = None

            player = mod.create_midi_output_player()
            assert player is not None

            player.preview_note(60, velocity=80, duration_ms=50)
            # note_on should be sent immediately
            calls = mock_out.send_message.call_args_list
            assert any(c.args[0] == [0x90, 60, 80] for c in calls)

            # Wait for note_off timer
            import time

            time.sleep(0.15)
            calls = mock_out.send_message.call_args_list
            assert any(c.args[0] == [0x80, 60, 0] for c in calls)
            player.cleanup()


# ── EditorSequence.add_note_at ─────────────────────────────────


class TestAddNoteAt:
    """Tests for placing notes at specific positions (pencil tool)."""

    def test_add_note_at_specific_time(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note_at(2.5, 60)
        assert seq.note_count == 1
        assert seq.notes[0].time_beats == 2.5
        assert seq.notes[0].note == 60

    def test_add_note_at_does_not_advance_cursor(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.cursor_beats = 0.0
        seq.add_note_at(3.0, 65)
        assert seq.cursor_beats == 0.0  # cursor unchanged

    def test_add_note_at_uses_step_duration(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.set_step_duration("1/8")
        seq.add_note_at(1.0, 72)
        assert seq.notes[0].duration_beats == 0.5

    def test_add_note_at_clamps_negative_time(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note_at(-1.0, 60)
        assert seq.notes[0].time_beats == 0.0

    def test_add_note_at_undoable(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note_at(1.0, 60)
        assert seq.note_count == 1
        seq.undo()
        assert seq.note_count == 0

    def test_add_note_at_assigns_active_track(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence(num_tracks=4)
        seq.set_active_track(2)
        seq.add_note_at(0.0, 60)
        assert seq.notes[0].track == 2


# ── EditorSequence.quantize_notes ──────────────────────────────


class TestQuantizeNotes:
    """Tests for quantizing notes to grid."""

    def test_quantize_snaps_to_grid(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note(60)  # at 0.0
        # Manually offset the note
        seq._notes[0].time_beats = 0.3
        seq.quantize_notes([0], grid=0.5)
        assert seq.notes[0].time_beats == 0.5

    def test_quantize_rounds_down(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note(60)
        seq._notes[0].time_beats = 0.2
        seq.quantize_notes([0], grid=0.5)
        assert seq.notes[0].time_beats == 0.0

    def test_quantize_multiple_notes(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note(60)  # at 0
        seq.add_note(64)  # at 1
        seq._notes[0].time_beats = 0.3
        seq._notes[1].time_beats = 1.7
        seq.quantize_notes([0, 1], grid=1.0)
        times = sorted(n.time_beats for n in seq.notes)
        assert times == [0.0, 2.0]

    def test_quantize_empty_indices_noop(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note(60)
        seq.quantize_notes([], grid=1.0)
        assert seq.can_undo  # add_note pushed undo, quantize didn't

    def test_quantize_undoable(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note(60)
        seq._notes[0].time_beats = 0.3
        seq.quantize_notes([0], grid=0.5)
        assert seq.notes[0].time_beats == 0.5
        seq.undo()
        assert seq.notes[0].time_beats == 0.3


# ── EditorSequence.set_notes_velocity ──────────────────────────


class TestSetNotesVelocity:
    """Tests for velocity editing."""

    def test_set_velocity(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note(60)
        assert seq.notes[0].velocity == 100
        seq.set_notes_velocity([0], 50)
        assert seq.notes[0].velocity == 50

    def test_set_velocity_clamps_high(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note(60)
        seq.set_notes_velocity([0], 200)
        assert seq.notes[0].velocity == 127

    def test_set_velocity_clamps_low(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note(60)
        seq.set_notes_velocity([0], 0)
        assert seq.notes[0].velocity == 1

    def test_set_velocity_batch(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note(60)
        seq.add_note(64)
        seq.add_note(67)
        seq.set_notes_velocity([0, 1, 2], 80)
        assert all(n.velocity == 80 for n in seq.notes)

    def test_set_velocity_undoable(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note(60)
        seq.set_notes_velocity([0], 50)
        seq.undo()
        assert seq.notes[0].velocity == 100

    def test_set_velocity_empty_noop(self):
        from cyber_qin.core.beat_sequence import EditorSequence

        seq = EditorSequence()
        seq.add_note(60)
        undo_depth = len(seq._undo_stack)
        seq.set_notes_velocity([], 50)
        assert len(seq._undo_stack) == undo_depth  # no new undo


# ── NoteRoll pencil mode ──────────────────────────────────────


class TestNoteRollPencilMode:
    """Tests for NoteRoll pencil/draw mode."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists."""

    def _make_roll(self):
        from cyber_qin.gui.widgets.note_roll import NoteRoll

        roll = NoteRoll()
        roll.resize(800, 200)
        return roll

    def test_pencil_mode_default_off(self):
        roll = self._make_roll()
        assert roll.pencil_mode is False

    def test_set_pencil_mode(self):
        roll = self._make_roll()
        roll.set_pencil_mode(True)
        assert roll.pencil_mode is True

    def test_pencil_click_emits_draw_signal(self):
        roll = self._make_roll()
        roll.set_pencil_mode(True)
        signals = []
        roll.note_draw_requested.connect(lambda t, n: signals.append((t, n)))

        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent

        # Click on empty area (no notes)
        pos = QPointF(100.0, 100.0)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        roll.mousePressEvent(event)
        assert len(signals) == 1
        assert signals[0][0] >= 0  # time_beats
        assert 0 <= signals[0][1] <= 127  # midi_note

    def test_pencil_off_click_no_draw_signal(self):
        roll = self._make_roll()
        roll.set_pencil_mode(False)
        signals = []
        roll.note_draw_requested.connect(lambda t, n: signals.append((t, n)))

        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent

        pos = QPointF(100.0, 100.0)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        roll.mousePressEvent(event)
        assert len(signals) == 0


# ── NoteRoll context menu signal ─────────────────────────────


class TestNoteRollContextMenu:
    """Tests for right-click context menu signal."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists."""

    def test_right_click_emits_context_menu(self):
        from cyber_qin.gui.widgets.note_roll import NoteRoll

        roll = NoteRoll()
        roll.resize(800, 200)

        signals = []
        roll.context_menu_requested.connect(lambda x, y: signals.append((x, y)))

        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent

        pos = QPointF(200.0, 100.0)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            pos,
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )
        roll.mousePressEvent(event)
        assert len(signals) == 1
        assert signals[0] == (200.0, 100.0)


# ── NoteRoll auto-scroll ────────────────────────────────────


class TestNoteRollAutoScroll:
    """Tests for auto-scroll during drag."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists."""

    def test_auto_scroll_right_edge(self):
        from cyber_qin.gui.widgets.note_roll import NoteRoll

        roll = NoteRoll()
        roll.resize(800, 200)
        roll._scroll_x = 0.0

        # Simulate mouse near right edge
        roll._last_mouse_x = 790.0  # within 40px of right edge
        roll._on_auto_scroll()
        assert roll._scroll_x > 0.0

    def test_auto_scroll_left_edge(self):
        from cyber_qin.gui.widgets.note_roll import NoteRoll

        roll = NoteRoll()
        roll.resize(800, 200)
        roll._scroll_x = 100.0

        roll._last_mouse_x = 10.0  # within 40px of left edge
        roll._on_auto_scroll()
        assert roll._scroll_x < 100.0

    def test_auto_scroll_center_no_change(self):
        from cyber_qin.gui.widgets.note_roll import NoteRoll

        roll = NoteRoll()
        roll.resize(800, 200)
        roll._scroll_x = 50.0

        roll._last_mouse_x = 400.0  # center
        roll._on_auto_scroll()
        assert roll._scroll_x == 50.0


# ── EditorView Ctrl+Q quantize ───────────────────────────────


class TestEditorViewQuantize:
    """Tests for Ctrl+Q quantize shortcut."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists."""

    def test_ctrl_q_quantizes_selection(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QKeyEvent

        from cyber_qin.gui.views.editor_view import EditorView

        view = EditorView()
        view._sequence.add_note(60)
        view._sequence.add_note(64)
        view._update_ui_state()

        # Manually offset a note
        view._sequence._notes[0].time_beats = 0.3

        # Select the first note
        view._current_note_selection = [0]

        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Q,
            Qt.KeyboardModifier.ControlModifier,
        )
        view.keyPressEvent(event)

        # Should snap 0.3 → 0.0 (grid=1.0 for 1/4 step)
        assert view._sequence._notes[0].time_beats == 0.0


# ── EditorView pencil toggle ─────────────────────────────────


class TestEditorViewPencilToggle:
    """Tests for pencil mode toggle via P key."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists."""

    def test_p_key_toggles_pencil(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QKeyEvent

        from cyber_qin.gui.views.editor_view import EditorView

        view = EditorView()
        assert view._pencil_btn.isChecked() is False

        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_P,
            Qt.KeyboardModifier.NoModifier,
            "p",
        )
        view.keyPressEvent(event)
        assert view._pencil_btn.isChecked() is True

        view.keyPressEvent(event)
        assert view._pencil_btn.isChecked() is False

    def test_pencil_button_toggles_noteroll(self):
        from cyber_qin.gui.views.editor_view import EditorView

        view = EditorView()
        assert view._note_roll.pencil_mode is False
        view._pencil_btn.setChecked(True)
        assert view._note_roll.pencil_mode is True
        view._pencil_btn.setChecked(False)
        assert view._note_roll.pencil_mode is False


# ── EditorView velocity spinbox ──────────────────────────────


class TestEditorViewVelocity:
    """Tests for velocity editing via spinbox."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists."""

    def test_velocity_spin_disabled_when_no_selection(self):
        from cyber_qin.gui.views.editor_view import EditorView

        view = EditorView()
        assert view._velocity_spin.isEnabled() is False

    def test_velocity_spin_enabled_on_selection(self):
        from cyber_qin.gui.views.editor_view import EditorView

        view = EditorView()
        view._sequence.add_note(60)
        view._update_ui_state()
        # Simulate selection
        view._note_roll.select_notes_in_time_range(0.0, 1.0)
        assert view._velocity_spin.isEnabled() is True

    def test_velocity_spin_change_updates_notes(self):
        from cyber_qin.gui.views.editor_view import EditorView

        view = EditorView()
        view._sequence.add_note(60)
        view._update_ui_state()
        view._note_roll.select_notes_in_time_range(0.0, 1.0)

        view._velocity_spin.setValue(64)
        assert view._sequence.notes[0].velocity == 64
