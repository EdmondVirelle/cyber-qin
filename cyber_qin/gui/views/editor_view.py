"""Virtual keyboard editor view — compose notes with click input and timeline.

Layout:
┌──────────────────────────────────────────────┐
│ Gradient header: "編曲器" (紫霧色)               │
├──────────────────────────────────────────────┤
│ Row 1: [●錄音][▶播放] | [↩][↪][✕]    [匯入][匯出] │
│ Row 2: 時值[1/4▾] 拍號[4/4▾] BPM[120] □Snap N音符 │
├──────────────────────────────────────────────┤
│ NoteRoll (timeline, flex=1)                  │
├──────────────────────────────────────────────┤
│ ClickablePiano (input keyboard)              │
└──────────────────────────────────────────────┘
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QLinearGradient, QPainter
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

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
from ..widgets.note_roll import NoteRoll

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

        self._build_ui()
        self._connect_signals()
        self._update_ui_state()

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

        header = QLabel("編曲器")
        header.setFont(QFont("Microsoft JhengHei", 22, QFont.Weight.Bold))
        header.setStyleSheet("background: transparent;")
        overlay_layout.addWidget(header)

        desc = QLabel("點擊琴鍵輸入音符，拖曳時間軸編輯旋律")
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        overlay_layout.addWidget(desc)
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
        self._record_btn = QPushButton("● 錄音")
        self._record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._record_btn.setStyleSheet(
            "QPushButton { background-color: #661111; color: #FF4444; font-weight: 700; }"
            "QPushButton:hover { background-color: #882222; }"
        )
        row1.addWidget(self._record_btn)

        self._play_btn = QPushButton("▶ 播放")
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

        row1.addStretch()

        # File group
        self._load_btn = QPushButton("匯入")
        self._load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._load_btn)

        self._export_btn = QPushButton("匯出")
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._export_btn)

        toolbar_layout.addLayout(row1)

        # Row 2: Duration | Time Sig | BPM | Snap | Stats
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        dur_lbl = QLabel("時值")
        row2.addWidget(dur_lbl)

        self._duration_combo = QComboBox()
        for label in DURATION_PRESETS:
            self._duration_combo.addItem(label)
        self._duration_combo.setCurrentText("1/4")
        row2.addWidget(self._duration_combo)

        row2.addSpacing(8)

        ts_lbl = QLabel("拍號")
        row2.addWidget(ts_lbl)

        self._ts_combo = QComboBox()
        for num, denom in TIME_SIGNATURES:
            self._ts_combo.addItem(f"{num}/{denom}")
        self._ts_combo.setCurrentText("4/4")
        row2.addWidget(self._ts_combo)

        row2.addSpacing(8)

        tempo_lbl = QLabel("BPM")
        row2.addWidget(tempo_lbl)

        self._tempo_spin = QSpinBox()
        self._tempo_spin.setRange(40, 300)
        self._tempo_spin.setValue(120)
        row2.addWidget(self._tempo_spin)

        row2.addSpacing(8)

        self._snap_cb = QCheckBox("Snap")
        self._snap_cb.setChecked(True)
        self._snap_cb.setStyleSheet("background: transparent;")
        row2.addWidget(self._snap_cb)

        self._auto_tune_cb = QCheckBox("自動校正")
        self._auto_tune_cb.setStyleSheet("background: transparent;")
        row2.addWidget(self._auto_tune_cb)

        row2.addStretch()

        self._note_count_lbl = QLabel("0 音符")
        self._note_count_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background: transparent; font-size: 12px;"
        )
        row2.addWidget(self._note_count_lbl)

        toolbar_layout.addLayout(row2)
        content.addWidget(toolbar_card)

        # Note roll (timeline)
        self._note_roll = NoteRoll()
        content.addWidget(self._note_roll, 1)

        # Clickable piano
        self._piano = ClickablePiano()
        content.addWidget(self._piano)

        root.addLayout(content, 1)

    def _connect_signals(self) -> None:
        self._piano.note_clicked.connect(self._on_note_clicked)
        self._load_btn.clicked.connect(self._on_load)
        self._export_btn.clicked.connect(self._on_export)
        self._record_btn.clicked.connect(self._on_record_toggle)
        self._play_btn.clicked.connect(self._on_play)
        self._undo_btn.clicked.connect(self._on_undo)
        self._redo_btn.clicked.connect(self._on_redo)
        self._clear_btn.clicked.connect(self._on_clear)
        self._duration_combo.currentTextChanged.connect(self._on_duration_changed)
        self._ts_combo.currentTextChanged.connect(self._on_ts_changed)
        self._tempo_spin.valueChanged.connect(self._on_tempo_changed)
        self._note_roll.note_deleted.connect(self._on_note_deleted)
        self._note_roll.note_moved.connect(self._on_note_moved)
        self._note_roll.cursor_moved.connect(self._on_cursor_moved)
        self._note_roll.note_right_clicked.connect(self._on_note_right_click_delete)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, '_gradient_header'):
            for child in self._gradient_header.children():
                if isinstance(child, QWidget):
                    child.setGeometry(0, 0, self.width(), 100)

    def _update_ui_state(self) -> None:
        """Sync UI with sequence state."""
        active = self._sequence.active_track
        track_notes = self._sequence.notes_in_track(active)
        track_rests = self._sequence.rests_in_track(active)

        # Ghost notes from other tracks
        ghost_notes = []
        for i, t in enumerate(self._sequence.tracks):
            if i != active and not t.muted:
                for n in self._sequence.notes_in_track(i):
                    n._ghost_color = t.color
                    ghost_notes.append(n)

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
        stats = f"{total} 音符"
        if bars > 0:
            stats += f" · {bars} 小節"
        self._note_count_lbl.setText(stats)

    def _on_note_clicked(self, midi_note: int) -> None:
        flash_beat = self._sequence.cursor_beats
        self._sequence.add_note(midi_note)
        self._update_ui_state()
        self._note_roll.flash_at_beat(flash_beat)

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "載入 MIDI 檔案", "",
            "MIDI Files (*.mid *.midi);;All Files (*)",
        )
        if not path:
            return
        self.load_file(path)

    def load_file(self, file_path: str) -> None:
        """Load a MIDI file into the editor."""
        try:
            events, info = MidiFileParser.parse(file_path)
            self._sequence = EditorSequence.from_midi_file_events(
                events, tempo_bpm=info.tempo_bpm,
            )
            self._tempo_spin.setValue(int(self._sequence.tempo_bpm))
            self._update_ui_state()
        except Exception:
            log.exception("Failed to load %s", file_path)

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
            recorded = self._sequence.to_recorded_events()
            MidiWriter.save(recorded, path, tempo_bpm=self._sequence.tempo_bpm)
        except Exception:
            log.exception("Failed to export %s", path)

    def _on_record_toggle(self) -> None:
        if self._is_recording:
            self._is_recording = False
            self._record_btn.setText("● 錄音")
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #661111; color: #FF4444; font-weight: 700; }"
                "QPushButton:hover { background-color: #882222; }"
            )
            self.recording_stopped.emit()
        else:
            self._is_recording = True
            self._record_btn.setText("■ 停止")
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #FF4444; color: #0A0E14; font-weight: 700; }"
                "QPushButton:hover { background-color: #FF6666; }"
            )
            self.recording_started.emit()

    def _on_note_moved(self, index: int, time_delta: float, pitch_delta: int) -> None:
        # index is relative to active track's notes — map to global
        active_notes = self._sequence.notes_in_track(self._sequence.active_track)
        if 0 <= index < len(active_notes):
            target = active_notes[index]
            # Find global index
            for gi, n in enumerate(self._sequence._notes):
                if n is target:
                    self._sequence.move_note(gi, time_delta, pitch_delta)
                    break
        self._update_ui_state()

    def _on_note_right_click_delete(self, index: int) -> None:
        active_notes = self._sequence.notes_in_track(self._sequence.active_track)
        if 0 <= index < len(active_notes):
            target = active_notes[index]
            for gi, n in enumerate(self._sequence._notes):
                if n is target:
                    self._sequence.delete_note(gi)
                    break
        self._update_ui_state()

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

    def _on_play(self) -> None:
        if self._sequence.note_count == 0:
            return
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

    def _on_note_deleted(self, index: int) -> None:
        active_notes = self._sequence.notes_in_track(self._sequence.active_track)
        if 0 <= index < len(active_notes):
            target = active_notes[index]
            for gi, n in enumerate(self._sequence._notes):
                if n is target:
                    self._sequence.delete_note(gi)
                    break
        self._update_ui_state()

    def _on_cursor_moved(self, t: float) -> None:
        self._sequence.cursor_beats = t
        self._note_roll.set_cursor_beats(t)

    # ── Keyboard shortcuts ──────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        text = event.text()

        # Duration keys: 1-5
        if text in DURATION_KEYS:
            label = DURATION_KEYS[text]
            self._sequence.set_step_duration(label)
            self._duration_combo.setCurrentText(label)
            return

        # Rest key: 0
        if text == "0":
            flash_beat = self._sequence.cursor_beats
            self._sequence.add_rest()
            self._update_ui_state()
            self._note_roll.flash_at_beat(flash_beat)
            return

        # Ctrl+Z / Ctrl+Y
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Z:
                self._on_undo()
                return
            if key == Qt.Key.Key_Y:
                self._on_redo()
                return

        # Space → play
        if key == Qt.Key.Key_Space:
            self._on_play()
            return

        super().keyPressEvent(event)
