"""Practice mode view — rhythm game with real-time scoring."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.beat_sequence import BeatNote
from ...core.practice_engine import PracticeScorer, notes_to_practice
from ...core.translator import translator
from ..theme import (
    ACCENT,
    ACCENT_GOLD,
    BG_INK,
    BG_SCROLL,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from ..widgets.practice_display import PracticeDisplay

# Green gradient for practice header
_PRACTICE_GRADIENT_START = "#0D4F2B"
_PRACTICE_GRADIENT_END = "#0A3F22"


class PracticeView(QWidget):
    """Practice mode with falling notes and scoring."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scorer: PracticeScorer | None = None
        self._notes: list[BeatNote] = []
        self._tempo_bpm: float = 120.0
        self._build_ui()

        translator.language_changed.connect(self._update_text)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._header = _GradientHeader()
        layout.addWidget(self._header)

        # Score bar
        score_bar = QWidget()
        score_bar.setFixedHeight(40)
        score_bar.setStyleSheet(f"background-color: {BG_SCROLL};")
        score_layout = QHBoxLayout(score_bar)
        score_layout.setContentsMargins(16, 4, 16, 4)

        self._score_label = QLabel(translator.tr("practice.score") + ": 0")
        self._score_label.setFont(QFont("Microsoft JhengHei", 12, QFont.Weight.Bold))
        self._score_label.setStyleSheet(f"color: {ACCENT_GOLD};")
        score_layout.addWidget(self._score_label)

        self._accuracy_label = QLabel(translator.tr("practice.accuracy") + ": 0%")
        self._accuracy_label.setFont(QFont("Microsoft JhengHei", 12))
        self._accuracy_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        score_layout.addWidget(self._accuracy_label)

        self._combo_label = QLabel(translator.tr("practice.combo") + ": 0")
        self._combo_label.setFont(QFont("Microsoft JhengHei", 12))
        self._combo_label.setStyleSheet(f"color: {ACCENT};")
        score_layout.addWidget(self._combo_label)

        score_layout.addStretch()

        self._start_btn = QPushButton(translator.tr("practice.start"))
        self._start_btn.setMinimumWidth(100)
        self._start_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {ACCENT};
                color: {BG_INK};
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #00D4E0; }}
            """
        )
        self._start_btn.clicked.connect(self._on_start_stop)
        score_layout.addWidget(self._start_btn)

        layout.addWidget(score_bar)

        # Main display
        self._display = PracticeDisplay()
        layout.addWidget(self._display, 1)

    def _update_text(self) -> None:
        self._header.update()
        self._start_btn.setText(
            translator.tr("practice.stop") if self._display.is_playing else translator.tr("practice.start")
        )
        self._update_score_display()

    def _update_score_display(self) -> None:
        if self._scorer:
            stats = self._scorer.stats
            self._score_label.setText(
                f"{translator.tr('practice.score')}: {stats.total_score}"
            )
            self._accuracy_label.setText(
                f"{translator.tr('practice.accuracy')}: {stats.accuracy_percent:.0f}%"
            )
            self._combo_label.setText(
                f"{translator.tr('practice.combo')}: {stats.current_combo}"
            )
        else:
            self._score_label.setText(f"{translator.tr('practice.score')}: 0")
            self._accuracy_label.setText(f"{translator.tr('practice.accuracy')}: 0%")
            self._combo_label.setText(f"{translator.tr('practice.combo')}: 0")

    def start_practice(self, notes: list[BeatNote], tempo_bpm: float = 120.0) -> None:
        """Start practice session with given notes."""
        self._notes = notes
        self._tempo_bpm = tempo_bpm

        practice_notes = notes_to_practice(notes, tempo_bpm)
        self._scorer = PracticeScorer(practice_notes)
        self._display.set_notes(practice_notes, tempo_bpm)
        self._display.start()
        self._start_btn.setText(translator.tr("practice.stop"))

    def _on_start_stop(self) -> None:
        if self._display.is_playing:
            self._display.stop()
            self._start_btn.setText(translator.tr("practice.start"))
        elif self._notes:
            self.start_practice(self._notes, self._tempo_bpm)

    def on_user_note(self, note: int) -> None:
        """Called when user plays a note (from MIDI input)."""
        if not self._scorer or not self._display.is_playing:
            return
        current_time = self._display.current_time
        grade = self._scorer.on_user_note(note, current_time)
        self._display.show_feedback(grade, note)
        self._update_score_display()


class _GradientHeader(QWidget):
    """Green gradient header for practice mode."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(60)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        w, h = self.width(), self.height()
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(_PRACTICE_GRADIENT_START))
        grad.setColorAt(1.0, QColor(_PRACTICE_GRADIENT_END))
        painter.fillRect(0, 0, w, h, grad)

        painter.setPen(QColor(TEXT_PRIMARY))
        painter.setFont(QFont("Microsoft JhengHei", 18, QFont.Weight.Bold))
        painter.drawText(QRectF(20, 0, w, h), Qt.AlignmentFlag.AlignVCenter, translator.tr("practice.title"))

        painter.setPen(QColor(TEXT_SECONDARY))
        painter.setFont(QFont("Microsoft JhengHei", 10))
        desc = translator.tr("practice.desc")
        painter.drawText(QRectF(20, 28, w, h), Qt.AlignmentFlag.AlignVCenter, desc)

        painter.end()
