"""Practice mode view — rhythm game with real-time scoring."""

from __future__ import annotations

from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.beat_sequence import BeatNote
from ...core.key_mapper import KeyMapper
from ...core.mapping_schemes import get_scheme, list_schemes
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


class _PracticeGradientHeader(QWidget):
    """Green gradient background only — text is in overlay widgets."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(100)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        w, h = self.width(), self.height()
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(_PRACTICE_GRADIENT_START))
        grad.setColorAt(1.0, QColor(_PRACTICE_GRADIENT_END))
        painter.fillRect(0, 0, w, h, grad)
        painter.end()


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

        # ── Header (100px gradient + widget overlay) ──
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        self._gradient_header = _PracticeGradientHeader()
        header_layout.addWidget(self._gradient_header)

        header_overlay = QWidget(self._gradient_header)
        overlay_layout = QVBoxLayout(header_overlay)
        overlay_layout.setContentsMargins(24, 20, 24, 8)

        # Row 1: title + mode combo + scheme combo
        header_row = QHBoxLayout()

        self._title_lbl = QLabel(translator.tr("practice.title"))
        self._title_lbl.setFont(QFont("Microsoft JhengHei", 22, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet("background: transparent;")
        header_row.addWidget(self._title_lbl)

        header_row.addStretch()

        self._mode_combo = QComboBox()
        self._mode_combo.addItem(translator.tr("practice.mode.midi"), "midi")
        self._mode_combo.addItem(translator.tr("practice.mode.keyboard"), "keyboard")
        self._mode_combo.setFixedWidth(150)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        header_row.addWidget(self._mode_combo)

        self._scheme_combo = QComboBox()
        for scheme in list_schemes():
            self._scheme_combo.addItem(scheme.translated_name(), scheme.id)
        self._scheme_combo.setFixedWidth(200)
        self._scheme_combo.setVisible(False)
        self._scheme_combo.currentIndexChanged.connect(self._on_scheme_changed)
        header_row.addWidget(self._scheme_combo)

        overlay_layout.addLayout(header_row)

        # Row 2: description
        self._desc_lbl = QLabel(translator.tr("practice.desc"))
        self._desc_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        overlay_layout.addWidget(self._desc_lbl)
        overlay_layout.addStretch()

        header_overlay.setGeometry(0, 0, 800, 100)
        layout.addWidget(header_container)

        # ── Score bar ──
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

        # ── Main display ──
        self._display = PracticeDisplay()
        self._display.note_hit.connect(self._on_display_note_hit)
        layout.addWidget(self._display, 1)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_gradient_header"):
            for child in self._gradient_header.children():
                if isinstance(child, QWidget):
                    child.setGeometry(0, 0, self.width(), 100)

    def _update_text(self) -> None:
        self._title_lbl.setText(translator.tr("practice.title"))
        self._desc_lbl.setText(translator.tr("practice.desc"))
        self._mode_combo.setItemText(0, translator.tr("practice.mode.midi"))
        self._mode_combo.setItemText(1, translator.tr("practice.mode.keyboard"))
        for i, scheme in enumerate(list_schemes()):
            self._scheme_combo.setItemText(i, scheme.translated_name())
        self._start_btn.setText(
            translator.tr("practice.stop")
            if self._display.is_playing
            else translator.tr("practice.start")
        )
        self._update_score_display()

    def _update_score_display(self) -> None:
        if self._scorer:
            stats = self._scorer.stats
            self._score_label.setText(f"{translator.tr('practice.score')}: {stats.total_score}")
            self._accuracy_label.setText(
                f"{translator.tr('practice.accuracy')}: {stats.accuracy * 100:.0f}%"
            )
            self._combo_label.setText(f"{translator.tr('practice.combo')}: {stats.current_combo}")
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
        """Called when user plays a note (from MIDI input or keyboard)."""
        if not self._scorer or not self._display.is_playing:
            return
        current_time = self._display.current_time
        hit = self._scorer.on_user_note(note, current_time)
        if hit is not None:
            self._display.show_feedback(hit.grade, note)
        self._update_score_display()

    def _on_display_note_hit(self, note: int, time: float) -> None:
        """Handle note hit from keyboard input in display."""
        self.on_user_note(note)

    def _on_mode_changed(self, index: int) -> None:
        is_keyboard = self._mode_combo.currentData() == "keyboard"
        self._scheme_combo.setVisible(is_keyboard)
        if is_keyboard:
            self._update_keyboard_mapping()
        else:
            self._display.set_keyboard_mapping(None)
            self._display.set_key_labels(None)

    def _on_scheme_changed(self, index: int) -> None:
        if self._mode_combo.currentData() == "keyboard":
            self._update_keyboard_mapping()

    def _update_keyboard_mapping(self) -> None:
        scheme_id = self._scheme_combo.currentData()
        if scheme_id:
            scheme = get_scheme(scheme_id)
            reverse_map = KeyMapper.build_reverse_map(scheme)
            key_labels = {note: km.label for note, km in scheme.mapping.items()}
            self._display.set_keyboard_mapping(reverse_map)
            self._display.set_key_labels(key_labels)
