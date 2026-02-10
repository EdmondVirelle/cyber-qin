"""Virtual keyboard editor view — compose notes with click input and timeline.

Layout:
┌─────────────────────────────────────┐
│ Gradient header: "編曲器" (紫霧色)    │
├─────────────────────────────────────┤
│ Toolbar: [Import][Export][Record]    │
│ [Play][Undo][Redo][Clear]           │
│ [Step: 1/4|1/8|1/16] [BPM] [校正]   │
├─────────────────────────────────────┤
│ NoteRoll (timeline, flex=1)         │
├─────────────────────────────────────┤
│ ClickablePiano (input keyboard)     │
└─────────────────────────────────────┘
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter
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

from ...core.midi_file_player import MidiFileParser
from ...core.midi_writer import MidiWriter
from ...core.note_sequence import STEP_PRESETS, NoteSequence
from ..theme import BG_PAPER, DIVIDER, TEXT_SECONDARY
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


class EditorView(QWidget):
    """Virtual keyboard editor — compose music by clicking piano keys."""

    play_requested = pyqtSignal(list)       # list of MidiFileEvent
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sequence = NoteSequence()
        self._tempo_bpm: float = 120.0
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
        toolbar_layout.setContentsMargins(16, 10, 16, 10)
        toolbar_layout.setSpacing(6)

        # Row 1: File operations + recording
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self._load_btn = QPushButton("匯入 MIDI")
        self._load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._load_btn)

        self._export_btn = QPushButton("匯出 MIDI")
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._export_btn)

        self._record_btn = QPushButton("錄音")
        self._record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._record_btn.setStyleSheet(
            "QPushButton { background-color: #661111; color: #FF4444; font-weight: 700; }"
            "QPushButton:hover { background-color: #882222; }"
        )
        row1.addWidget(self._record_btn)

        self._play_btn = QPushButton("播放")
        self._play_btn.setProperty("class", "accent")
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._play_btn)

        self._undo_btn = QPushButton("復原")
        self._undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._undo_btn)

        self._redo_btn = QPushButton("重做")
        self._redo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._redo_btn)

        self._clear_btn = QPushButton("清除")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._clear_btn)

        row1.addStretch()

        # Step selector
        step_lbl = QLabel("步長:")
        step_lbl.setStyleSheet("background: transparent;")
        row1.addWidget(step_lbl)

        self._step_combo = QComboBox()
        for label in STEP_PRESETS:
            self._step_combo.addItem(label)
        self._step_combo.setCurrentText("1/8")
        row1.addWidget(self._step_combo)

        # Tempo
        tempo_lbl = QLabel("BPM:")
        tempo_lbl.setStyleSheet("background: transparent;")
        row1.addWidget(tempo_lbl)

        self._tempo_spin = QSpinBox()
        self._tempo_spin.setRange(40, 300)
        self._tempo_spin.setValue(120)
        row1.addWidget(self._tempo_spin)

        # Auto-correct checkbox
        self._auto_tune_cb = QCheckBox("自動校正")
        self._auto_tune_cb.setStyleSheet("background: transparent;")
        row1.addWidget(self._auto_tune_cb)

        # Note count
        self._note_count_lbl = QLabel("音符: 0")
        self._note_count_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background: transparent; font-size: 12px;"
        )
        row1.addWidget(self._note_count_lbl)

        toolbar_layout.addLayout(row1)
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
        self._step_combo.currentTextChanged.connect(self._on_step_changed)
        self._tempo_spin.valueChanged.connect(self._on_tempo_changed)
        self._note_roll.note_deleted.connect(self._on_note_deleted)
        self._note_roll.note_moved.connect(self._on_note_moved)
        self._note_roll.cursor_moved.connect(self._on_cursor_moved)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, '_gradient_header'):
            for child in self._gradient_header.children():
                if isinstance(child, QWidget):
                    child.setGeometry(0, 0, self.width(), 100)

    def _update_ui_state(self) -> None:
        """Sync UI with sequence state."""
        self._note_roll.set_notes(self._sequence.notes)
        self._note_roll.set_cursor_time(self._sequence.cursor_time)
        self._note_roll.set_tempo(self._tempo_bpm)
        self._undo_btn.setEnabled(self._sequence.can_undo)
        self._redo_btn.setEnabled(self._sequence.can_redo)
        self._note_count_lbl.setText(f"音符: {self._sequence.note_count}")

    def _on_note_clicked(self, midi_note: int) -> None:
        self._sequence.add_note(midi_note)
        self._update_ui_state()

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
            self._sequence = NoteSequence.from_midi_file_events(events)
            self._tempo_bpm = info.tempo_bpm
            self._tempo_spin.setValue(int(self._tempo_bpm))
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
            MidiWriter.save(recorded, path, tempo_bpm=self._tempo_bpm)
        except Exception:
            log.exception("Failed to export %s", path)

    def _on_record_toggle(self) -> None:
        if self._is_recording:
            self._is_recording = False
            self._record_btn.setText("錄音")
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #661111; color: #FF4444; font-weight: 700; }"
                "QPushButton:hover { background-color: #882222; }"
            )
            self.recording_stopped.emit()
        else:
            self._is_recording = True
            self._record_btn.setText("停止錄音")
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #FF4444; color: #0A0E14; font-weight: 700; }"
                "QPushButton:hover { background-color: #FF6666; }"
            )
            self.recording_started.emit()

    def _on_note_moved(self, index: int, time_delta: float, pitch_delta: int) -> None:
        self._sequence.move_note(index, time_delta, pitch_delta)
        self._update_ui_state()

    @property
    def auto_tune_enabled(self) -> bool:
        return self._auto_tune_cb.isChecked()

    def set_recorded_events(self, events: list) -> None:
        """Merge recorded events into the current sequence."""
        recorded_seq = NoteSequence.from_midi_file_events(events)
        self._sequence._push_undo()
        self._sequence._notes.extend(recorded_seq._notes)
        self._sequence._notes.sort(key=lambda n: n.time_seconds)
        self._update_ui_state()

    def _on_play(self) -> None:
        """Emit play_requested with the current note sequence as MidiFileEvents."""
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

    def _on_step_changed(self, label: str) -> None:
        self._sequence.set_step_duration(label)

    def _on_tempo_changed(self, value: int) -> None:
        self._tempo_bpm = float(value)
        self._note_roll.set_tempo(self._tempo_bpm)

    def _on_note_deleted(self, index: int) -> None:
        self._sequence.delete_note(index)
        self._update_ui_state()

    def _on_cursor_moved(self, t: float) -> None:
        self._sequence.cursor_time = t
        self._note_roll.set_cursor_time(t)
