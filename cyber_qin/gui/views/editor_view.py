"""Virtual keyboard editor view — compose notes with click input and timeline.

Layout:
┌──────────────────────────────────────────────┐
│ Gradient header: "編曲器" (紫霧色)               │
├──────────────────────────────────────────────┤
│ Row 1: [●錄音][▶播放] | [↩][↪][✕]    [存檔][匯入][匯出] │
│ Row 2: 時值[1/4▾] 拍號[4/4▾] BPM[120] □Snap N音符 │
├──────────────────────────────────────────────┤
│ [TrackPanel | PitchRuler | NoteRoll (flex=1)]│
│ [           | spacer(48) | ClickablePiano    ]│
└──────────────────────────────────────────────┘
"""

from __future__ import annotations

import copy
import logging

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QLinearGradient, QPainter
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core import project_file
from ...core.beat_sequence import (
    DURATION_KEYS,
    DURATION_PRESETS,
    TIME_SIGNATURES,
    EditorSequence,
)
from ...core.midi_file_player import MidiFileParser
from ...core.midi_writer import MidiWriter
from ..theme import BG_PAPER, DIVIDER, TEXT_SECONDARY
from ..widgets.animated_widgets import IconButton
from ..widgets.clickable_piano import ClickablePiano
from ...core.translator import translator
from ..widgets.editor_track_panel import EditorTrackPanel
from ..widgets.note_roll import NoteRoll
from ..widgets.pitch_ruler import PitchRuler
from ..widgets.speed_control import SpeedControl

log = logging.getLogger(__name__)


class _EditorGradientHeader(QWidget):
    """Gradient header with purple mist accent."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(100)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(160, 100, 220, 35))  # 紫霧半透明
        gradient.setColorAt(1, QColor(10, 14, 20, 0))       # 透明
        painter.fillRect(QRectF(0, 0, self.width(), self.height()), gradient)
        painter.end()


class _ToolbarCard(QWidget):
    """Rounded card container for toolbar controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"_ToolbarCard {{"
            f"  background-color: {BG_PAPER};"
            f"  border-radius: 12px;"
            f"  border: 1px solid {DIVIDER};"
            f"}}"
        )


class _VSeparator(QWidget):
    """Thin vertical divider line between button groups."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(1, 24)
        self.setStyleSheet(f"background-color: {DIVIDER};")


class EditorView(QWidget):
    """Virtual keyboard editor — compose music by clicking piano keys."""

    play_requested = pyqtSignal(list)       # list of MidiFileEvent
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sequence = EditorSequence()
        self._is_recording: bool = False
        self._project_path: str | None = None
        self._player = None  # set by set_player()
        self._preview_player = None  # lazy MidiOutputPlayer
        self._selection_anchor: float | None = None
        self._playback_speed: float = 1.0

        self._build_ui()
        self._connect_signals()
        self._update_ui_state()

        # Autosave timer — 60s interval
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._on_autosave)
        self._autosave_timer.start(60_000)

        # Deferred autosave recovery check (after widget is shown)
        QTimer.singleShot(500, self._check_autosave_recovery)

    def set_player(self, player) -> None:
        """Set the player controller for playback cursor tracking."""
        self._player = player
        if player is not None:
            player.progress_updated.connect(self._on_playback_progress)
            player.state_changed.connect(self._on_playback_state_changed)

    def _on_playback_progress(self, current: float, total: float) -> None:
        """Convert seconds to beats for playback cursor."""
        if self._sequence.tempo_bpm > 0:
            beats = current / (60.0 / self._sequence.tempo_bpm)
            self._note_roll.set_playback_beats(beats)

    def _on_playback_state_changed(self, state: int) -> None:
        from ...core.midi_file_player import PlaybackState
        if state == PlaybackState.STOPPED:
            self._note_roll.set_playback_beats(-1)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Gradient header
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        self._gradient_header = _EditorGradientHeader()
        header_layout.addWidget(self._gradient_header)

        # Overlay text
        header_overlay = QWidget(self._gradient_header)
        overlay_layout = QVBoxLayout(header_overlay)
        overlay_layout.setContentsMargins(24, 20, 24, 8)

        self._header_lbl = QLabel()
        self._header_lbl.setFont(QFont("Microsoft JhengHei", 22, QFont.Weight.Bold))
        self._header_lbl.setStyleSheet("background: transparent;")
        overlay_layout.addWidget(self._header_lbl)

        self._desc_lbl = QLabel()
        self._desc_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        overlay_layout.addWidget(self._desc_lbl)
        overlay_layout.addStretch()

        header_overlay.setGeometry(0, 0, 800, 100)
        root.addWidget(header_container)

        # Content area
        content = QVBoxLayout()
        content.setContentsMargins(24, 8, 24, 12)
        content.setSpacing(8)

        # Toolbar card
        toolbar_card = _ToolbarCard()
        toolbar_layout = QVBoxLayout(toolbar_card)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(6)

        # Row 1: Transport | Edit | File
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        # Transport group
        self._record_btn = QPushButton()
        self._record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._record_btn.setStyleSheet(
            "QPushButton { background-color: #661111; color: #FF4444; font-weight: 700; }"
            "QPushButton:hover { background-color: #882222; }"
        )
        row1.addWidget(self._record_btn)

        self._play_btn = QPushButton()
        self._play_btn.setProperty("class", "accent")
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._play_btn)

        row1.addWidget(_VSeparator())

        # Edit group
        self._undo_btn = IconButton("undo", size=32)
        self._undo_btn.setToolTip("復原 (Ctrl+Z)")
        row1.addWidget(self._undo_btn)

        self._redo_btn = IconButton("redo", size=32)
        self._redo_btn.setToolTip("重做 (Ctrl+Y)")
        row1.addWidget(self._redo_btn)

        self._clear_btn = IconButton("remove", size=32)
        self._clear_btn.setToolTip("清除全部")
        row1.addWidget(self._clear_btn)

        row1.addWidget(_VSeparator())

        row1.addWidget(_VSeparator())

        self._pencil_btn = QPushButton()
        self._pencil_btn.setCheckable(True)
        self._pencil_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pencil_btn.setStyleSheet(
            "QPushButton { padding: 4px 8px; }"
            "QPushButton:checked { background-color: #00F0FF; color: #0A0E14; font-weight: 700; }"
        )
        row1.addWidget(self._pencil_btn)

        row1.addStretch()

        # File group
        self._save_btn = QPushButton()
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setToolTip("Ctrl+S")
        row1.addWidget(self._save_btn)

        self._load_btn = QPushButton()
        self._load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._load_btn)

        self._export_btn = QPushButton()
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.setToolTip("Ctrl+E")
        row1.addWidget(self._export_btn)

        row1.addWidget(_VSeparator())

        self._help_btn = IconButton("help", size=32)
        self._help_btn.setToolTip("操作指南")
        row1.addWidget(self._help_btn)

        toolbar_layout.addLayout(row1)

        # Row 2: Duration | Time Sig | BPM | Snap | Stats
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self._dur_lbl = QLabel()
        row2.addWidget(self._dur_lbl)

        self._duration_combo = QComboBox()
        for label in DURATION_PRESETS:
            self._duration_combo.addItem(label)
        self._duration_combo.setCurrentText("1/4")
        row2.addWidget(self._duration_combo)

        row2.addSpacing(8)

        self._ts_lbl = QLabel()
        row2.addWidget(self._ts_lbl)

        self._ts_combo = QComboBox()
        for num, denom in TIME_SIGNATURES:
            self._ts_combo.addItem(f"{num}/{denom}")
        self._ts_combo.setCurrentText("4/4")
        row2.addWidget(self._ts_combo)

        row2.addSpacing(8)

        self._bpm_lbl = QLabel()
        row2.addWidget(self._bpm_lbl)

        self._tempo_spin = QSpinBox()
        self._tempo_spin.setRange(40, 300)
        self._tempo_spin.setValue(120)
        row2.addWidget(self._tempo_spin)

        row2.addSpacing(8)

        self._snap_cb = QCheckBox("Snap")
        self._snap_cb.setChecked(True)
        self._snap_cb.setStyleSheet("background: transparent;")
        row2.addWidget(self._snap_cb)

        self._auto_tune_cb = QCheckBox()
        self._auto_tune_cb.setStyleSheet("background: transparent;")
        row2.addWidget(self._auto_tune_cb)

        row2.addSpacing(8)

        self._vel_lbl = QLabel()
        row2.addWidget(self._vel_lbl)

        self._velocity_spin = QSpinBox()
        self._velocity_spin.setRange(1, 127)
        self._velocity_spin.setValue(100)
        self._velocity_spin.setToolTip("選取音符的力度 (1-127)")
        self._velocity_spin.setFixedWidth(60)
        self._velocity_spin.setEnabled(False)
        row2.addWidget(self._velocity_spin)

        row2.addSpacing(8)

        self._speed_ctrl = SpeedControl()
        row2.addWidget(self._speed_ctrl)

        row2.addSpacing(8)

        row2.addSpacing(8)

        self._shortcuts_cb = QCheckBox()
        self._shortcuts_cb.setChecked(True)
        self._shortcuts_cb.setStyleSheet("background: transparent;")
        row2.addWidget(self._shortcuts_cb)

        row2.addStretch()

        self._note_count_lbl = QLabel("0 音符")
        self._note_count_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background: transparent; font-size: 12px;"
        )
        row2.addWidget(self._note_count_lbl)

        toolbar_layout.addLayout(row2)
        content.addWidget(toolbar_card)

        # ── Main editor area: [TrackPanel | PitchRuler | NoteRoll] ──
        editor_area = QHBoxLayout()
        editor_area.setSpacing(0)
        editor_area.setContentsMargins(0, 0, 0, 0)

        self._track_panel = EditorTrackPanel()
        editor_area.addWidget(self._track_panel)

        self._pitch_ruler = PitchRuler()
        editor_area.addWidget(self._pitch_ruler)

        self._note_roll = NoteRoll()
        editor_area.addWidget(self._note_roll, 1)

        content.addLayout(editor_area, 1)

        # ── Piano row: [spacer | ClickablePiano] ──
        piano_row = QHBoxLayout()
        piano_row.setSpacing(0)
        piano_row.setContentsMargins(0, 0, 0, 0)

        # Spacer to align piano with NoteRoll (TrackPanel + PitchRuler widths)
        piano_spacer = QWidget()
        piano_spacer.setFixedWidth(160 + 48)  # _PANEL_WIDTH + _RULER_WIDTH
        piano_row.addWidget(piano_spacer)

        self._piano = ClickablePiano()
        piano_row.addWidget(self._piano, 1)

        content.addLayout(piano_row)

        root.addLayout(content, 1)
        
        translator.language_changed.connect(self._update_text)
        self._update_text()
        
    def _update_text(self) -> None:
        """Update UI text based on current language."""
        self._header_lbl.setText(translator.tr("editor.title"))
        self._desc_lbl.setText(translator.tr("editor.desc"))
        
        self._play_btn.setText(translator.tr("editor.play"))
        self._undo_btn.setToolTip(translator.tr("editor.undo"))
        self._redo_btn.setToolTip(translator.tr("editor.redo"))
        self._clear_btn.setToolTip(translator.tr("editor.clear"))
        self._pencil_btn.setText(translator.tr("editor.pencil"))
        self._save_btn.setText(translator.tr("editor.save"))
        self._load_btn.setText(translator.tr("editor.import"))
        self._export_btn.setText(translator.tr("editor.export"))
        self._help_btn.setToolTip(translator.tr("editor.help"))
        
        self._dur_lbl.setText(translator.tr("editor.duration"))
        self._ts_lbl.setText(translator.tr("editor.time_sig"))
        self._bpm_lbl.setText(translator.tr("editor.bpm"))
        self._snap_cb.setText(translator.tr("editor.snap"))
        self._auto_tune_cb.setText(translator.tr("live.auto_tune"))
        self._vel_lbl.setText(translator.tr("editor.velocity"))
        self._shortcuts_cb.setText(translator.tr("editor.shortcuts"))
        
        # Stateful record button
        if self._is_recording:
             self._record_btn.setText(translator.tr("live.stop_record")) # Use generic stop or editor specific? 
             # Editor doesn't have specific stop_record key, reuse live? Or create generic `stop`?
             # live.stop_record is "Stop Rec". 
             self._record_btn.setText("■ " + translator.tr("live.stop_record"))
        else:
             self._record_btn.setText(translator.tr("editor.record"))

        # Update note count label format
        self._update_ui_state()

    def _connect_signals(self) -> None:
        self._piano.note_clicked.connect(self._on_note_clicked)
        self._piano.note_pressed.connect(self._on_piano_key_pressed)
        self._piano.note_released.connect(self._on_piano_key_released)
        self._load_btn.clicked.connect(self._on_load)
        self._export_btn.clicked.connect(self._on_export)
        self._save_btn.clicked.connect(self._on_save)
        self._record_btn.clicked.connect(self._on_record_toggle)
        self._play_btn.clicked.connect(self._on_play)
        self._undo_btn.clicked.connect(self._on_undo)
        self._redo_btn.clicked.connect(self._on_redo)
        self._clear_btn.clicked.connect(self._on_clear)
        self._pencil_btn.toggled.connect(self._on_pencil_toggled)
        self._help_btn.clicked.connect(self._on_help)
        self._duration_combo.currentTextChanged.connect(self._on_duration_changed)
        self._ts_combo.currentTextChanged.connect(self._on_ts_changed)
        self._tempo_spin.valueChanged.connect(self._on_tempo_changed)
        self._snap_cb.toggled.connect(self._note_roll.set_snap_enabled)
        self._velocity_spin.valueChanged.connect(self._on_velocity_changed)
        self._speed_ctrl.speed_changed.connect(self._on_speed_changed)

        # NoteRoll signals
        self._note_roll.note_deleted.connect(self._on_note_deleted)
        self._note_roll.note_moved.connect(self._on_note_moved)
        self._note_roll.note_selected.connect(self._on_note_selected_preview)
        self._note_roll.cursor_moved.connect(self._on_cursor_moved)
        self._note_roll.selection_changed.connect(self._on_selection_changed)
        self._note_roll.note_resized.connect(self._on_note_resized)
        self._note_roll.notes_moved.connect(self._on_notes_moved)
        self._note_roll.note_draw_requested.connect(self._on_note_draw)
        self._note_roll.context_menu_requested.connect(self._on_context_menu)

        # Track panel signals
        self._track_panel.track_activated.connect(self._on_track_activated)
        self._track_panel.track_muted.connect(self._on_track_muted)
        self._track_panel.track_soloed.connect(self._on_track_soloed)
        self._track_panel.track_renamed.connect(self._on_track_renamed)
        self._track_panel.track_removed.connect(self._on_track_removed)
        self._track_panel.track_added.connect(self._on_track_added)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, '_gradient_header'):
            for child in self._gradient_header.children():
                if isinstance(child, QWidget):
                    child.setGeometry(0, 0, self.width(), 100)

    def _update_ui_state(self) -> None:
        """Sync UI with sequence state."""
        self._invalidate_index_cache()
        active = self._sequence.active_track
        track_notes = self._sequence.notes_in_track(active)
        track_rests = self._sequence.rests_in_track(active)

        # Ghost notes from other tracks
        ghost_notes = []
        for i, t in enumerate(self._sequence.tracks):
            if i != active and not t.muted:
                for n in self._sequence.notes_in_track(i):
                    gn = copy.copy(n)
                    gn._ghost_color = t.color
                    ghost_notes.append(gn)

        self._note_roll.set_notes(track_notes)
        self._note_roll.set_rests(track_rests)
        self._note_roll.set_ghost_notes(ghost_notes)
        self._note_roll.set_cursor_beats(self._sequence.cursor_beats)
        self._note_roll.set_tempo(self._sequence.tempo_bpm)
        self._note_roll.set_beats_per_bar(self._sequence.beats_per_bar)

        if active < len(self._sequence.tracks):
            self._note_roll.set_active_track_color(self._sequence.tracks[active].color)

        self._undo_btn.setEnabled(self._sequence.can_undo)
        self._redo_btn.setEnabled(self._sequence.can_redo)

        total = self._sequence.note_count
        bars = self._sequence.bar_count
        total = self._sequence.note_count
        bars = self._sequence.bar_count
        self._note_count_lbl.setText(translator.tr("editor.note_count", notes=total, bars=bars))

        # Update track panel
        self._track_panel.set_tracks(self._sequence.tracks, active)

    # ── Track panel handlers ─────────────────────────────────

    def _on_track_activated(self, index: int) -> None:
        self._sequence.set_active_track(index)
        self._update_ui_state()

    def _on_track_muted(self, index: int, muted: bool) -> None:
        self._sequence.set_track_muted(index, muted)
        self._update_ui_state()

    def _on_track_soloed(self, index: int, solo: bool) -> None:
        self._sequence.set_track_solo(index, solo)
        self._update_ui_state()

    def _on_track_renamed(self, index: int, name: str) -> None:
        self._sequence.rename_track(index, name)
        self._update_ui_state()

    def _on_track_removed(self, index: int) -> None:
        self._sequence.remove_track(index)
        self._update_ui_state()

    def _on_track_added(self) -> None:
        self._sequence.add_track()
        self._update_ui_state()

    # ── NoteRoll signal handlers ─────────────────────────────

    def _on_selection_changed(self, note_indices: list, rest_indices: list) -> None:
        # Store selection for copy/paste/delete
        self._current_note_selection = note_indices
        self._current_rest_selection = rest_indices

        # Update velocity spinbox
        if note_indices:
            self._velocity_spin.setEnabled(True)
            active_notes = self._sequence.notes_in_track(self._sequence.active_track)
            velocities = []
            for i in note_indices:
                if 0 <= i < len(active_notes):
                    velocities.append(active_notes[i].velocity)
            if velocities:
                self._velocity_spin.blockSignals(True)
                self._velocity_spin.setValue(velocities[0])
                self._velocity_spin.blockSignals(False)
        else:
            self._velocity_spin.setEnabled(False)

    def _on_note_resized(self, index: int, new_duration: float) -> None:
        """Handle note resize from NoteRoll."""
        global_idx = self._map_to_global_note_index(index)
        if global_idx >= 0:
            self._sequence.resize_note(global_idx, new_duration)
        self._update_ui_state()

    def _on_notes_moved(self, indices: list, time_delta: float, pitch_delta: int) -> None:
        """Handle batch move from NoteRoll."""
        global_indices = [self._map_to_global_note_index(i) for i in indices]
        global_indices = [gi for gi in global_indices if gi >= 0]
        if global_indices:
            self._sequence.move_notes(global_indices, time_delta, pitch_delta)
        self._update_ui_state()

    # ── Index mapping helpers ────────────────────────────────

    def _invalidate_index_cache(self) -> None:
        """Clear cached index maps — called on every UI refresh."""
        self._note_index_map: dict[int, int] | None = None
        self._rest_index_map: dict[int, int] | None = None

    def _ensure_note_index_map(self) -> dict[int, int]:
        """Build (or return cached) track-local → global note index mapping."""
        if self._note_index_map is not None:
            return self._note_index_map
        active = self._sequence.active_track
        local_idx = 0
        mapping: dict[int, int] = {}
        for gi, n in enumerate(self._sequence._notes):
            if n.track == active:
                mapping[local_idx] = gi
                local_idx += 1
        self._note_index_map = mapping
        return mapping

    def _ensure_rest_index_map(self) -> dict[int, int]:
        """Build (or return cached) track-local → global rest index mapping."""
        if self._rest_index_map is not None:
            return self._rest_index_map
        active = self._sequence.active_track
        local_idx = 0
        mapping: dict[int, int] = {}
        for gi, r in enumerate(self._sequence._rests):
            if r.track == active:
                mapping[local_idx] = gi
                local_idx += 1
        self._rest_index_map = mapping
        return mapping

    def _map_to_global_note_index(self, track_local_idx: int) -> int:
        """Map a track-local note index to a global index in sequence._notes."""
        return self._ensure_note_index_map().get(track_local_idx, -1)

    def _map_to_global_rest_index(self, track_local_idx: int) -> int:
        """Map a track-local rest index to a global index in sequence._rests."""
        return self._ensure_rest_index_map().get(track_local_idx, -1)


    # ── Note events ──────────────────────────────────────────

    def _on_note_clicked(self, midi_note: int) -> None:
        flash_beat = self._sequence.cursor_beats
        self._sequence.add_note(midi_note)
        self._update_ui_state()
        self._note_roll.flash_at_beat(flash_beat)
        self._preview_midi_note(midi_note)

    def _on_note_draw(self, time_beats: float, midi_note: int) -> None:
        """Handle pencil tool draw on NoteRoll."""
        self._sequence.add_note_at(time_beats, midi_note)
        self._update_ui_state()
        self._note_roll.flash_at_beat(time_beats)
        self._preview_midi_note(midi_note)

    def _on_pencil_toggled(self, checked: bool) -> None:
        self._note_roll.set_pencil_mode(checked)

    def _on_velocity_changed(self, value: int) -> None:
        """Update velocity of all selected notes."""
        note_sel = getattr(self, '_current_note_selection', [])
        if not note_sel:
            return
        global_indices = [self._map_to_global_note_index(i) for i in note_sel]
        global_indices = [gi for gi in global_indices if gi >= 0]
        if global_indices:
            self._sequence.set_notes_velocity(global_indices, value)
            self._update_ui_state()

    def _on_note_selected_preview(self, index: int) -> None:
        """Play audio preview when a note is clicked in NoteRoll."""
        active_notes = self._sequence.notes_in_track(self._sequence.active_track)
        if 0 <= index < len(active_notes):
            self._preview_midi_note(active_notes[index].note)

    def _on_piano_key_pressed(self, midi_note: int) -> None:
        """Play audio preview when piano key is pressed."""
        player = self._ensure_preview_player()
        if player is not None:
            # Send note_on directly for held preview
            if player._midi_out is not None:
                player._midi_out.send_message([0x90, midi_note & 0x7F, 100])

    def _on_piano_key_released(self, midi_note: int) -> None:
        """Stop audio when piano key is released."""
        player = self._ensure_preview_player()
        if player is not None:
            if player._midi_out is not None:
                player._midi_out.send_message([0x80, midi_note & 0x7F, 0])

    def _preview_midi_note(self, midi_note: int) -> None:
        """Play a short preview of a MIDI note."""
        player = self._ensure_preview_player()
        if player is not None:
            player.preview_note(midi_note, velocity=80, duration_ms=150)

    def _quantize_selection(self) -> None:
        """Quantize selected notes to the current step grid."""
        note_sel = getattr(self, '_current_note_selection', [])
        if not note_sel:
            return
        global_indices = [self._map_to_global_note_index(i) for i in note_sel]
        global_indices = [gi for gi in global_indices if gi >= 0]
        if global_indices:
            self._sequence.quantize_notes(global_indices, self._sequence.step_duration)
            self._update_ui_state()

    def _on_context_menu(self, x: float, y: float) -> None:
        """Show context menu at NoteRoll position."""
        menu = QMenu(self)
        has_sel = bool(getattr(self, '_current_note_selection', [])
                       or getattr(self, '_current_rest_selection', []))
        has_clip = not self._sequence.clipboard_empty

        act_select_all = menu.addAction("全選\tCtrl+A")
        act_select_all.triggered.connect(self._note_roll.select_all)

        menu.addSeparator()

        act_copy = menu.addAction("複製\tCtrl+C")
        act_copy.setEnabled(has_sel)
        act_copy.triggered.connect(self._copy_selection)

        act_cut = menu.addAction("剪下\tCtrl+X")
        act_cut.setEnabled(has_sel)
        act_cut.triggered.connect(self._cut_selection)

        act_paste = menu.addAction("貼上\tCtrl+V")
        act_paste.setEnabled(has_clip)
        act_paste.triggered.connect(self._paste)

        act_delete = menu.addAction("刪除\tDelete")
        act_delete.setEnabled(has_sel)
        act_delete.triggered.connect(self._delete_selection)

        menu.addSeparator()

        act_quantize = menu.addAction("量化對齊\tCtrl+Q")
        act_quantize.setEnabled(has_sel)
        act_quantize.triggered.connect(self._quantize_selection)

        menu.addSeparator()

        act_pencil = menu.addAction("鉛筆模式\tP")
        act_pencil.setCheckable(True)
        act_pencil.setChecked(self._pencil_btn.isChecked())
        act_pencil.triggered.connect(self._pencil_btn.setChecked)

        from PyQt6.QtCore import QPoint
        screen_pos = self._note_roll.mapToGlobal(QPoint(int(x), int(y)))
        menu.exec(screen_pos)

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "載入 MIDI 檔案", "",
            "MIDI Files (*.mid *.midi);;CQP Projects (*.cqp);;All Files (*)",
        )
        if not path:
            return
        if path.endswith(".cqp"):
            self._load_project(path)
        else:
            self.load_file(path)

    def load_file(self, file_path: str) -> None:
        """Load a MIDI file into the editor."""
        try:
            events, info = MidiFileParser.parse(file_path)
            self._sequence = EditorSequence.from_midi_file_events(
                events, tempo_bpm=info.tempo_bpm,
            )
            self._tempo_spin.setValue(int(self._sequence.tempo_bpm))
            self._project_path = None
            self._update_ui_state()
        except Exception:
            log.exception("Failed to load %s", file_path)

    def _load_project(self, path: str) -> None:
        """Load a .cqp project file."""
        try:
            self._sequence = project_file.load(path)
            self._project_path = path
            self._tempo_spin.setValue(int(self._sequence.tempo_bpm))
            self._update_ui_state()
        except Exception:
            log.exception("Failed to load project %s", path)

    def _on_export(self) -> None:
        if self._sequence.note_count == 0:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "匯出 MIDI 檔案", "",
            "MIDI Files (*.mid);;All Files (*)",
        )
        if not path:
            return
        if not path.endswith(".mid"):
            path += ".mid"

        try:
            midi_events = self._sequence.to_midi_file_events()
            tracks = self._sequence.tracks
            track_names = [t.name for t in tracks]
            track_channels = [t.channel for t in tracks]
            MidiWriter.save_multitrack(
                midi_events, path,
                tempo_bpm=self._sequence.tempo_bpm,
                track_names=track_names,
                track_channels=track_channels,
            )
        except Exception:
            log.exception("Failed to export %s", path)

    def _on_save(self) -> None:
        """Save project (Ctrl+S). If no path, prompt save-as."""
        if self._project_path:
            try:
                project_file.save(self._project_path, self._sequence)
            except Exception:
                log.exception("Failed to save project")
        else:
            self._on_save_as()

    def _on_save_as(self) -> None:
        """Save project to a new path (Ctrl+Shift+S)."""
        path, _ = QFileDialog.getSaveFileName(
            self, "儲存專案", "",
            "CQP Projects (*.cqp);;All Files (*)",
        )
        if not path:
            return
        if not path.endswith(".cqp"):
            path += ".cqp"
        try:
            project_file.save(path, self._sequence)
            self._project_path = path
        except Exception:
            log.exception("Failed to save project %s", path)

    def _on_autosave(self) -> None:
        """Periodic autosave."""
        if self._sequence.note_count > 0 or self._sequence.rest_count > 0:
            try:
                project_file.autosave(self._sequence)
            except Exception:
                log.debug("Autosave failed", exc_info=True)

    def _check_autosave_recovery(self) -> None:
        """Check for autosave file and offer recovery."""
        if self._sequence.note_count > 0 or self._sequence.rest_count > 0:
            return  # Already has content, don't overwrite
        recovered = project_file.load_autosave()
        if recovered is None or (recovered.note_count == 0 and recovered.rest_count == 0):
            return
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "恢復自動存檔",
            f"偵測到自動存檔 ({recovered.note_count} 音符)。\n要恢復嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._sequence = recovered
            self._tempo_spin.setValue(int(self._sequence.tempo_bpm))
            self._update_ui_state()
            log.info("Recovered %d notes from autosave", recovered.note_count)

    def _on_record_toggle(self) -> None:
        if self._is_recording:
            self._is_recording = False
            self._record_btn.setText(translator.tr("editor.record"))
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #661111; color: #FF4444; font-weight: 700; }"
                "QPushButton:hover { background-color: #882222; }"
            )
            self._update_text() # Enforce correct text
            self.recording_stopped.emit()
        else:
            self._is_recording = True
            self._record_btn.setText("■ " + translator.tr("live.stop_record"))
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #ff4444; color: #0A0E14; "
                "border: none; border-radius: 16px; padding: 8px 20px; "
                "font-weight: 700; }"
                "QPushButton:hover { background-color: #ff6666; }"
            )
            self._update_text() # Enforce text
            self.recording_started.emit()

    def _on_note_moved(self, index: int, time_delta: float, pitch_delta: int) -> None:
        global_idx = self._map_to_global_note_index(index)
        if global_idx >= 0:
            self._sequence.move_note(global_idx, time_delta, pitch_delta)
        self._update_ui_state()

    # _on_note_right_click_delete removed — replaced by context menu

    @property
    def auto_tune_enabled(self) -> bool:
        return self._auto_tune_cb.isChecked()

    def set_recorded_events(self, events: list) -> None:
        """Merge recorded events into the current sequence."""
        recorded_seq = EditorSequence.from_midi_file_events(
            events, tempo_bpm=self._sequence.tempo_bpm,
        )
        self._sequence._push_undo()
        self._sequence._notes.extend(recorded_seq._notes)
        self._sequence._notes.sort(key=lambda n: n.time_beats)
        self._update_ui_state()

    def _ensure_preview_player(self):
        """Lazily create the MidiOutputPlayer for piano preview."""
        if self._preview_player is not None:
            return self._preview_player
        try:
            from ...core.midi_output_player import create_midi_output_player
            player = create_midi_output_player(self)
            if player is not None:
                player.progress_updated.connect(self._on_preview_progress)
                player.state_changed.connect(self._on_preview_state_changed)
                player.note_fired.connect(self._on_preview_note_fired)
                self._preview_player = player
                # Apply persisted speed
                player.set_speed(self._playback_speed)
        except Exception:
            log.debug("Failed to create preview player", exc_info=True)
        return self._preview_player

    def _on_preview_progress(self, current: float, total: float) -> None:
        if self._sequence.tempo_bpm > 0:
            beats = current / (60.0 / self._sequence.tempo_bpm)
            self._note_roll.set_playback_beats(beats)

    def _on_preview_state_changed(self, state: int) -> None:
        from ...core.midi_file_player import PlaybackState
        if state == PlaybackState.STOPPED:
            self._note_roll.set_playback_beats(-1)
            self._play_btn.setText("▶ 播放")
            self._play_btn.setStyleSheet("")
            self._piano.set_active_notes(set())
            self._note_roll.set_active_notes(set())
        elif state == PlaybackState.PLAYING:
            self._play_btn.setText("■ 停止")
            self._play_btn.setStyleSheet(
                "QPushButton { background-color: #FF4444; color: #0A0E14; font-weight: 700; }"
                "QPushButton:hover { background-color: #FF6666; }"
            )

    def _on_preview_note_fired(self, event_type: str, note: int, velocity: int) -> None:
        """Handle real-time playback feedback."""
        # Update ClickablePiano
        if event_type == "note_on":
            self._piano.note_on(note)
            # Update NoteRoll active notes
            current_active = self._piano._active_notes
            self._note_roll.set_active_notes(current_active)
        elif event_type == "note_off":
            self._piano.note_off(note)
            # Update NoteRoll active notes
            current_active = self._piano._active_notes
            self._note_roll.set_active_notes(current_active)

    def _on_play(self) -> None:
        if self._sequence.note_count == 0:
            return

        player = self._ensure_preview_player()
        if player is not None:
            from ...core.midi_file_player import PlaybackState
            if player.state == PlaybackState.PLAYING:
                player.stop()
                return
            events = self._sequence.to_midi_file_events()
            duration = self._sequence.duration_seconds
            player.load(events, duration)
            player.play()
            return

        # Fallback: SendInput player via app_shell
        events = self._sequence.to_midi_file_events()
        self.play_requested.emit(events)

    def _on_undo(self) -> None:
        self._sequence.undo()
        self._update_ui_state()

    def _on_redo(self) -> None:
        self._sequence.redo()
        self._update_ui_state()

    def _on_clear(self) -> None:
        self._sequence.clear()
        self._update_ui_state()

    def _on_help(self) -> None:
        """Show editor help dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle("編曲器操作指南")
        dlg.resize(600, 700)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {BG_PAPER}; border: none; }}"
        )

        content = QLabel()
        content.setWordWrap(True)
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        content.setContentsMargins(24, 20, 24, 20)
        content.setStyleSheet(
            f"QLabel {{"
            f"  background-color: {BG_PAPER};"
            f"  color: {TEXT_SECONDARY};"
            f"  font-family: 'Microsoft JhengHei';"
            f"  font-size: 13px;"
            f"}}"
        )

        html = (
            "<h2 style='color:#E8E0D0;'>編曲器操作指南</h2>"

            "<h3 style='color:#00F0FF;'>一、基本輸入</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>點擊底部琴鍵</td>"
            "<td>在游標位置插入音符</td></tr>"
            "<tr><td style='color:#E8E0D0;'>數字鍵 1-5</td>"
            "<td>切換時值（全音符～十六分音符）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>0 鍵</td>"
            "<td>插入休止符</td></tr>"
            "<tr><td style='color:#E8E0D0;'>← → 方向鍵</td>"
            "<td>移動游標</td></tr>"
            "</table>"

            "<h3 style='color:#00F0FF;'>二、鉛筆工具</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>P 鍵 或 工具列「✎鉛筆」</td>"
            "<td>切換鉛筆模式</td></tr>"
            "<tr><td style='color:#E8E0D0;'>鉛筆模式下點擊音符捲軸空白處</td>"
            "<td>直接放置音符</td></tr>"
            "</table>"

            "<h3 style='color:#00F0FF;'>三、選取與編輯</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>點擊音符</td>"
            "<td>選取單個音符</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+點擊</td>"
            "<td>加選／取消選取</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Shift+拖曳</td>"
            "<td>框選（矩形選取）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+A</td>"
            "<td>全選</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Delete</td>"
            "<td>刪除選取的音符</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Alt+方向鍵</td>"
            "<td>移動選取的音符（上下=音高，左右=時間）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Alt+Shift+左右</td>"
            "<td>調整選取音符的長度</td></tr>"
            "<tr><td style='color:#E8E0D0;'>拖曳音符右邊緣</td>"
            "<td>調整單個音符長度（6px 範圍）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Shift+左右</td>"
            "<td>游標範圍選取</td></tr>"
            "</table>"

            "<h3 style='color:#00F0FF;'>四、剪貼簿</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+C</td>"
            "<td>複製</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+X</td>"
            "<td>剪下</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+V</td>"
            "<td>貼上（在游標位置）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+D</td>"
            "<td>複製音符到游標位置</td></tr>"
            "</table>"

            "<h3 style='color:#00F0FF;'>五、編輯操作</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+Z</td>"
            "<td>復原</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+Y</td>"
            "<td>重做</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+Q</td>"
            "<td>量化對齊（對齊到目前的步長網格）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+S</td>"
            "<td>存檔（.cqp 專案）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+Shift+S</td>"
            "<td>另存新檔</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+E</td>"
            "<td>匯出為 MIDI (.mid)</td></tr>"
            "</table>"

            "<h3 style='color:#00F0FF;'>六、音軌操作</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>點擊音軌</td>"
            "<td>切換作用中音軌</td></tr>"
            "<tr><td style='color:#E8E0D0;'>雙擊音軌名稱</td>"
            "<td>重新命名</td></tr>"
            "<tr><td style='color:#E8E0D0;'>M 按鈕 / S 按鈕</td>"
            "<td>靜音 / 獨奏</td></tr>"
            "<tr><td style='color:#E8E0D0;'>右鍵點擊音軌</td>"
            "<td>刪除音軌</td></tr>"
            "<tr><td style='color:#E8E0D0;'>＋ 按鈕</td>"
            "<td>新增音軌</td></tr>"
            "<tr><td style='color:#E8E0D0;'>其他音軌的音符</td>"
            "<td>以半透明「鬼影」顯示</td></tr>"
            "</table>"

            "<h3 style='color:#00F0FF;'>七、播放</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>Space</td>"
            "<td>播放／停止</td></tr>"
            "<tr><td style='color:#E8E0D0;'>需要 MIDI 輸出裝置</td>"
            "<td>（如 Microsoft GS Wavetable）</td></tr>"
            "</table>"

            "<h3 style='color:#00F0FF;'>八、右鍵選單</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>在音符捲軸上右鍵</td>"
            "<td>全選、複製、剪下、貼上、刪除、量化對齊、鉛筆模式</td></tr>"
            "</table>"

            "<h3 style='color:#00F0FF;'>九、其他</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>滾輪</td>"
            "<td>水平捲動時間軸</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+滾輪</td>"
            "<td>縮放時間軸</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Snap 勾選框</td>"
            "<td>啟用／停用吸附到網格</td></tr>"
            "<tr><td style='color:#E8E0D0;'>力度欄位</td>"
            "<td>選取音符後可調整力度 (1-127)</td></tr>"
            "<tr><td style='color:#E8E0D0;'>自動校正勾選框</td>"
            "<td>錄音時自動校正音高</td></tr>"
            "<tr><td style='color:#E8E0D0;'>自動存檔</td>"
            "<td>每 60 秒自動存檔</td></tr>"
            "<tr><td style='color:#E8E0D0;'>速度選擇器</td>"
            "<td>播放速度 0.25x ~ 2.0x</td></tr>"
            "<tr><td style='color:#E8E0D0;'>⌨ 快捷鍵 勾選框</td>"
            "<td>啟用／停用單鍵快捷鍵（Ctrl+S/Z/Y 不受影響）</td></tr>"
            "</table>"
        )
        content.setText(html)

        scroll.setWidget(content)
        layout.addWidget(scroll)
        dlg.exec()

    def _on_duration_changed(self, label: str) -> None:
        self._sequence.set_step_duration(label)

    def _on_ts_changed(self, text: str) -> None:
        parts = text.split("/")
        if len(parts) == 2:
            try:
                num, denom = int(parts[0]), int(parts[1])
                self._sequence.time_signature = (num, denom)
                self._update_ui_state()
            except ValueError:
                pass

    def _on_tempo_changed(self, value: int) -> None:
        self._sequence.tempo_bpm = float(value)
        self._note_roll.set_tempo(self._sequence.tempo_bpm)

    def _on_speed_changed(self, speed: float) -> None:
        """Update playback speed on the preview player."""
        self._playback_speed = speed
        if self._preview_player is not None:
            self._preview_player.set_speed(speed)

    def _on_note_deleted(self, index: int) -> None:
        if index == -1:
            # Delete entire selection (triggered by marquee-selected Delete)
            note_sel = getattr(self, '_current_note_selection', [])
            rest_sel = getattr(self, '_current_rest_selection', [])
            global_notes = [self._map_to_global_note_index(i) for i in note_sel]
            global_rests = [self._map_to_global_rest_index(i) for i in rest_sel]
            global_notes = [gi for gi in global_notes if gi >= 0]
            global_rests = [gi for gi in global_rests if gi >= 0]
            if global_notes or global_rests:
                self._sequence.delete_items(global_notes, global_rests)
        else:
            global_idx = self._map_to_global_note_index(index)
            if global_idx >= 0:
                self._sequence.delete_note(global_idx)
        self._update_ui_state()

    def _on_cursor_moved(self, t: float) -> None:
        self._sequence.cursor_beats = t
        self._note_roll.set_cursor_beats(t)

    # ── Copy / Paste / Duplicate ─────────────────────────────

    def _copy_selection(self) -> None:
        note_sel = getattr(self, '_current_note_selection', [])
        rest_sel = getattr(self, '_current_rest_selection', [])
        global_notes = [self._map_to_global_note_index(i) for i in note_sel]
        global_rests = [self._map_to_global_rest_index(i) for i in rest_sel]
        global_notes = [gi for gi in global_notes if gi >= 0]
        global_rests = [gi for gi in global_rests if gi >= 0]
        if global_notes or global_rests:
            self._sequence.copy_items(global_notes, global_rests)

    def _cut_selection(self) -> None:
        self._copy_selection()
        self._delete_selection()

    def _paste(self) -> None:
        self._sequence.paste_at_cursor()
        self._update_ui_state()

    def _duplicate_selection(self) -> None:
        """Duplicate selected notes at cursor position."""
        self._copy_selection()
        self._paste()

    def _delete_selection(self) -> None:
        note_sel = getattr(self, '_current_note_selection', [])
        rest_sel = getattr(self, '_current_rest_selection', [])
        global_notes = [self._map_to_global_note_index(i) for i in note_sel]
        global_rests = [self._map_to_global_rest_index(i) for i in rest_sel]
        global_notes = [gi for gi in global_notes if gi >= 0]
        global_rests = [gi for gi in global_rests if gi >= 0]
        if global_notes or global_rests:
            self._sequence.delete_items(global_notes, global_rests)
            self._update_ui_state()

    def _move_selection(self, time_delta: float = 0.0, pitch_delta: int = 0) -> None:
        """Move selected notes by delta."""
        note_sel = getattr(self, '_current_note_selection', [])
        if not note_sel:
            return
        global_indices = [self._map_to_global_note_index(i) for i in note_sel]
        global_indices = [gi for gi in global_indices if gi >= 0]
        if global_indices:
            self._sequence.move_notes(global_indices, time_delta, pitch_delta)
            self._update_ui_state()

    def _resize_selection(self, delta_beats: float) -> None:
        """Resize selected notes."""
        note_sel = getattr(self, '_current_note_selection', [])
        if not note_sel:
            return
        global_indices = [self._map_to_global_note_index(i) for i in note_sel]
        global_indices = [gi for gi in global_indices if gi >= 0]
        if global_indices:
            self._sequence.resize_notes(global_indices, delta_beats)
            self._update_ui_state()

    def _move_cursor(self, delta_beats: float) -> None:
        """Move cursor by delta, clear selection."""
        self._selection_anchor = None
        new_pos = max(0.0, self._sequence.cursor_beats + delta_beats)
        self._sequence.cursor_beats = new_pos
        self._note_roll.clear_selection()
        self._note_roll.set_cursor_beats(new_pos)

    # ── Keyboard shortcuts ──────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        text = event.text()
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        # Keyboard shortcuts toggle — Ctrl combos always active for safety
        shortcuts_on = self._shortcuts_cb.isChecked()

        # Duration keys: 1-5
        if shortcuts_on and not ctrl and text in DURATION_KEYS:
            label = DURATION_KEYS[text]
            self._sequence.set_step_duration(label)
            self._duration_combo.setCurrentText(label)
            return

        # Rest key: 0
        if shortcuts_on and not ctrl and text == "0":
            flash_beat = self._sequence.cursor_beats
            self._sequence.add_rest()
            self._update_ui_state()
            self._note_roll.flash_at_beat(flash_beat)
            return

        # Pencil mode toggle: P
        if shortcuts_on and not ctrl and text.lower() == "p":
            self._pencil_btn.toggle()
            return

        # Ctrl shortcuts
        if ctrl:
            if key == Qt.Key.Key_Z:
                self._on_undo()
                return
            if key == Qt.Key.Key_Y:
                self._on_redo()
                return
            if key == Qt.Key.Key_A:
                self._note_roll.select_all()
                return
            if key == Qt.Key.Key_C:
                self._copy_selection()
                return
            if key == Qt.Key.Key_X:
                self._cut_selection()
                return
            if key == Qt.Key.Key_V:
                self._paste()
                return
            if key == Qt.Key.Key_D:
                self._duplicate_selection()
                return
            if key == Qt.Key.Key_Q:
                self._quantize_selection()
                return
            if key == Qt.Key.Key_S:
                if shift:
                    self._on_save_as()
                else:
                    self._on_save()
                return
            if key == Qt.Key.Key_E:
                self._on_export()
                return

        # Arrow keys — cursor navigation / note editing
        alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        step = self._sequence.step_duration

        if not shortcuts_on:
            # Only Ctrl combos were handled above; skip all other shortcuts
            super().keyPressEvent(event)
            return

        if alt and shift:
            # Alt+Shift+arrows: resize selected notes
            if key == Qt.Key.Key_Right:
                self._resize_selection(step)
                return
            if key == Qt.Key.Key_Left:
                self._resize_selection(-step)
                return
        elif alt:
            # Alt+arrows: move selected notes
            if key == Qt.Key.Key_Right:
                self._move_selection(time_delta=step)
                return
            if key == Qt.Key.Key_Left:
                self._move_selection(time_delta=-step)
                return
            if key == Qt.Key.Key_Up:
                self._move_selection(pitch_delta=1)
                return
            if key == Qt.Key.Key_Down:
                self._move_selection(pitch_delta=-1)
                return
        elif shift:
            # Shift+arrows: range selection
            if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                if self._selection_anchor is None:
                    self._selection_anchor = self._sequence.cursor_beats
                delta = step if key == Qt.Key.Key_Right else -step
                new_pos = max(0.0, self._sequence.cursor_beats + delta)
                self._sequence.cursor_beats = new_pos
                self._note_roll.set_cursor_beats(new_pos)
                t0 = min(self._selection_anchor, new_pos)
                t1 = max(self._selection_anchor, new_pos)
                self._note_roll.select_notes_in_time_range(t0, t1)
                return
        else:
            # Plain arrows: move cursor
            if key == Qt.Key.Key_Left:
                self._move_cursor(-step)
                return
            if key == Qt.Key.Key_Right:
                self._move_cursor(step)
                return

        # Delete key
        if key == Qt.Key.Key_Delete:
            self._delete_selection()
            return

        # Space → play
        if key == Qt.Key.Key_Space:
            self._on_play()
            return

        super().keyPressEvent(event)
