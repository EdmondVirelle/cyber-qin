"""Tests for frontend GUI components (PianoDisplay, ClickablePiano, EditorView integration)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent

# ── PianoDisplay Tests ───────────────────────────────────────

class TestPianoDisplay:
    """Tests for PianoDisplay widget logic."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        pass

    def test_set_active_notes(self):
        from cyber_qin.gui.widgets.piano_display import PianoDisplay
        piano = PianoDisplay()
        notes = {60, 64, 67}
        piano.set_active_notes(notes)
        assert piano._active_notes == notes

    def test_note_on_off_updates_state(self):
        from cyber_qin.gui.widgets.piano_display import PianoDisplay
        piano = PianoDisplay()
        piano.note_on(60)
        assert 60 in piano._active_notes
        assert 60 in piano._flash_notes

        piano.note_off(60)
        assert 60 not in piano._active_notes
        assert 60 in piano._fade_notes

    def test_scheme_change_clears_state(self):
        from cyber_qin.gui.widgets.piano_display import PianoDisplay
        piano = PianoDisplay()
        piano.note_on(60)

        # Mock mapper
        mock_mapper = MagicMock()
        mock_mapper.scheme = None # default
        piano._mapper = mock_mapper

        piano.on_scheme_changed()
        assert len(piano._active_notes) == 0
        assert len(piano._flash_notes) == 0
        assert len(piano._fade_notes) == 0


# ── ClickablePiano Tests ─────────────────────────────────────

class TestClickablePiano:
    """Tests for ClickablePiano interaction and feedback."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        pass

    def test_click_emits_signals(self):
        from cyber_qin.gui.widgets.clickable_piano import ClickablePiano
        piano = ClickablePiano(midi_min=0, midi_max=127)
        piano.resize(1280, 100) # 10px per key approx

        pressed_signals = []
        clicked_signals = []
        piano.note_pressed.connect(pressed_signals.append)
        piano.note_clicked.connect(clicked_signals.append)

        # Click on first key (MIDI 0)
        # x=5 should be within first key
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(5.0, 50.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        piano.mousePressEvent(event)

        assert len(pressed_signals) == 1
        assert pressed_signals[0] == 0
        assert len(clicked_signals) == 1
        assert clicked_signals[0] == 0

    def test_visual_feedback_methods(self):
        """Verify note_on/off methods ported from PianoDisplay work."""
        from cyber_qin.gui.widgets.clickable_piano import ClickablePiano
        piano = ClickablePiano()

        # Should not crash and should update state
        piano.note_on(60)
        assert 60 in piano._active_notes
        assert 60 in piano._flash_notes

        piano.note_off(60)
        assert 60 not in piano._active_notes
        assert 60 in piano._fade_notes


# ── EditorView Integration Tests ─────────────────────────────

class TestEditorViewIntegration:
    """Tests for EditorView wiring, specifically playback feedback."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        pass

    def test_preview_note_fired_updates_widgets(self):
        """Verify the fix for AttributeError: _on_preview_note_fired calls _piano.note_on."""
        from cyber_qin.gui.views.editor_view import EditorView
        view = EditorView()

        # Mock the child widgets to verify calls
        view._piano = MagicMock()
        view._note_roll = MagicMock()

        # Simulate note_on signal from player
        view._on_preview_note_fired("note_on", 60, 100)

        # Check PianoDisplay update
        view._piano.note_on.assert_called_with(60)

        # Check NoteRoll update (gets set from piano's active notes)
        # We need to mock _piano._active_notes property access if it was read
        # In the code: current_active = self._piano._active_notes
        # Since _piano is a MagicMock, accessing ._active_notes returns another MagicMock
        assert view._note_roll.set_active_notes.called

    def test_preview_state_changed_updates_ui(self):
        """Verify play button and state reset on stop."""
        from cyber_qin.core.midi_file_player import PlaybackState
        from cyber_qin.gui.views.editor_view import EditorView

        view = EditorView()
        view._piano = MagicMock()
        view._note_roll = MagicMock()
        view._play_btn = MagicMock()

        # Simulate Stop
        view._on_preview_state_changed(PlaybackState.STOPPED)

        view._note_roll.set_playback_beats.assert_called_with(-1)
        view._play_btn.setText.assert_called_with("▶ 播放")
        view._piano.set_active_notes.assert_called_with(set())
        view._note_roll.set_active_notes.assert_called_with(set())

        # Simulate Play
        view._on_preview_state_changed(PlaybackState.PLAYING)
        view._play_btn.setText.assert_called_with("■ 停止")
