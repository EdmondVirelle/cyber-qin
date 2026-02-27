"""Practice mode view — rhythm game with real-time scoring and song picker."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.beat_sequence import BeatNote
from ...core.key_mapper import KeyMapper
from ...core.mapping_schemes import get_scheme, list_schemes
from ...core.midi_file_player import MidiFileInfo
from ...core.practice_engine import PracticeScorer, PracticeStats, notes_to_practice
from ...core.translator import translator
from ..theme import (
    ACCENT,
    ACCENT_GOLD,
    ACCENT_GOLD_DIM,
    ACCENT_GOLD_GLOW,
    BG_INK,
    BG_PAPER,
    BG_SCROLL,
    BORDER_DIM,
    TEXT_DISABLED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from ..widgets.practice_display import PracticeDisplay
from ..widgets.speed_control import SpeedControl

# Green gradient for practice header
_PRACTICE_GRADIENT_START = "#0D4F2B"
_PRACTICE_GRADIENT_END = "#0A3F22"

# Grade colors for results page
_PERFECT_COLOR = "#D4AF37"
_GREAT_COLOR = "#33FF55"
_GOOD_COLOR = "#FFBB33"
_MISS_COLOR = "#FF4444"


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


# ── Mini track card for the empty-state library list ──────────────


class _MiniTrackCard(QWidget):
    """Compact clickable card representing one library track."""

    clicked = pyqtSignal(str)  # file_path

    def __init__(self, info: MidiFileInfo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._file_path = info.file_path
        self._hovered = False
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)

        name_lbl = QLabel(info.name)
        name_lbl.setFont(QFont("Microsoft JhengHei", 11))
        name_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(name_lbl)

        layout.addStretch()

        mins, secs = divmod(int(info.duration_seconds), 60)
        dur_lbl = QLabel(f"{mins}:{secs:02d}")
        dur_lbl.setFont(QFont("Microsoft JhengHei", 10))
        dur_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        layout.addWidget(dur_lbl)

        notes_lbl = QLabel(f"{info.note_count} notes")
        notes_lbl.setFont(QFont("Microsoft JhengHei", 10))
        notes_lbl.setStyleSheet(f"color: {TEXT_DISABLED}; background: transparent;")
        layout.addWidget(notes_lbl)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(BG_PAPER) if self._hovered else QColor(BG_SCROLL)
        painter.setBrush(bg)
        painter.setPen(QPen(QColor(BORDER_DIM), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)
        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._file_path)


# ── Empty state (page 0) ─────────────────────────────────────────


class _PracticeEmptyState(QWidget):
    """Song picker shown when no track is loaded."""

    file_open_clicked = pyqtSignal()
    track_clicked = pyqtSignal(str)  # file_path

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._track_cards: list[_MiniTrackCard] = []
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet(f"background-color: {BG_INK};")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Icon (music note drawn with QPainter in a small widget) ──
        icon_widget = _MusicNoteIcon()
        layout.addWidget(icon_widget, 0, Qt.AlignmentFlag.AlignCenter)

        # ── Title ──
        self._title_lbl = QLabel(translator.tr("practice.empty.title"))
        self._title_lbl.setFont(QFont("Microsoft JhengHei", 20, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_lbl)

        # ── Subtitle ──
        self._sub_lbl = QLabel(translator.tr("practice.empty.sub"))
        self._sub_lbl.setFont(QFont("Microsoft JhengHei", 12))
        self._sub_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._sub_lbl)

        layout.addSpacing(12)

        # ── Open File button (gold accent) ──
        self._open_btn = QPushButton(translator.tr("practice.open_file"))
        self._open_btn.setFont(QFont("Microsoft JhengHei", 12, QFont.Weight.Bold))
        self._open_btn.setMinimumWidth(220)
        self._open_btn.setFixedHeight(42)
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {ACCENT_GOLD};
                color: {BG_INK};
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {ACCENT_GOLD_GLOW}; }}
            QPushButton:pressed {{ background-color: {ACCENT_GOLD_DIM}; }}
            """
        )
        self._open_btn.clicked.connect(self.file_open_clicked.emit)
        layout.addWidget(self._open_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(24)

        # ── Library tracks section header ──
        self._section_lbl = QLabel(translator.tr("practice.library_tracks"))
        self._section_lbl.setFont(QFont("Microsoft JhengHei", 13, QFont.Weight.Bold))
        self._section_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self._section_lbl)

        # ── Track list container ──
        self._tracks_container = QVBoxLayout()
        self._tracks_container.setSpacing(4)
        layout.addLayout(self._tracks_container)

        # ── No-tracks placeholder ──
        self._no_tracks_lbl = QLabel(translator.tr("practice.no_tracks"))
        self._no_tracks_lbl.setFont(QFont("Microsoft JhengHei", 11))
        self._no_tracks_lbl.setStyleSheet(f"color: {TEXT_DISABLED};")
        self._no_tracks_lbl.setWordWrap(True)
        layout.addWidget(self._no_tracks_lbl)

        layout.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll)

    def set_tracks(self, tracks: list[MidiFileInfo]) -> None:
        """Populate the mini track list from library data."""
        # Clear old cards
        for card in self._track_cards:
            card.setParent(None)
            card.deleteLater()
        self._track_cards.clear()

        self._no_tracks_lbl.setVisible(len(tracks) == 0)

        for info in tracks:
            card = _MiniTrackCard(info)
            card.clicked.connect(self.track_clicked.emit)
            self._tracks_container.addWidget(card)
            self._track_cards.append(card)

    def update_text(self) -> None:
        self._title_lbl.setText(translator.tr("practice.empty.title"))
        self._sub_lbl.setText(translator.tr("practice.empty.sub"))
        self._open_btn.setText(translator.tr("practice.open_file"))
        self._section_lbl.setText(translator.tr("practice.library_tracks"))
        self._no_tracks_lbl.setText(translator.tr("practice.no_tracks"))


class _MusicNoteIcon(QWidget):
    """Simple music note icon drawn with QPainter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(64, 64)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(ACCENT_GOLD), 3)
        painter.setPen(pen)
        # Note head (filled ellipse)
        painter.setBrush(QColor(ACCENT_GOLD))
        painter.drawEllipse(14, 38, 18, 14)
        # Stem
        painter.drawLine(32, 42, 32, 12)
        # Flag
        painter.drawLine(32, 12, 44, 22)
        painter.drawLine(32, 18, 44, 28)
        painter.end()


# ── Results page (page 2) ────────────────────────────────────────


class _PracticeResultsPage(QWidget):
    """End-of-session results summary with grade breakdown."""

    retry_clicked = pyqtSignal()
    change_track_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background-color: {BG_INK};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        self._title_lbl = QLabel(translator.tr("practice.result"))
        self._title_lbl.setFont(QFont("Microsoft JhengHei", 28, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_lbl)

        layout.addSpacing(8)

        # Score (large gold number)
        self._score_lbl = QLabel("0")
        self._score_lbl.setFont(QFont("Microsoft JhengHei", 48, QFont.Weight.Bold))
        self._score_lbl.setStyleSheet(f"color: {ACCENT_GOLD};")
        self._score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._score_lbl)

        # Accuracy
        self._accuracy_lbl = QLabel("0%")
        self._accuracy_lbl.setFont(QFont("Microsoft JhengHei", 18))
        self._accuracy_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        self._accuracy_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._accuracy_lbl)

        layout.addSpacing(16)

        # Grade breakdown row
        grades_row = QHBoxLayout()
        grades_row.setSpacing(24)

        self._perfect_lbl = self._make_grade_label("PERFECT", _PERFECT_COLOR)
        self._great_lbl = self._make_grade_label("GREAT", _GREAT_COLOR)
        self._good_lbl = self._make_grade_label("GOOD", _GOOD_COLOR)
        self._miss_lbl = self._make_grade_label("MISS", _MISS_COLOR)

        grades_row.addStretch()
        grades_row.addWidget(self._perfect_lbl)
        grades_row.addWidget(self._great_lbl)
        grades_row.addWidget(self._good_lbl)
        grades_row.addWidget(self._miss_lbl)
        grades_row.addStretch()

        layout.addLayout(grades_row)

        layout.addSpacing(8)

        # Max combo + total notes
        self._combo_lbl = QLabel()
        self._combo_lbl.setFont(QFont("Microsoft JhengHei", 14))
        self._combo_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._combo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._combo_lbl)

        self._total_lbl = QLabel()
        self._total_lbl.setFont(QFont("Microsoft JhengHei", 12))
        self._total_lbl.setStyleSheet(f"color: {TEXT_DISABLED};")
        self._total_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._total_lbl)

        layout.addSpacing(24)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        btn_row.addStretch()

        self._retry_btn = QPushButton(translator.tr("practice.retry"))
        self._retry_btn.setFont(QFont("Microsoft JhengHei", 13, QFont.Weight.Bold))
        self._retry_btn.setFixedHeight(42)
        self._retry_btn.setMinimumWidth(140)
        self._retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._retry_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {ACCENT_GOLD};
                color: {BG_INK};
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {ACCENT_GOLD_GLOW}; }}
            QPushButton:pressed {{ background-color: {ACCENT_GOLD_DIM}; }}
            """
        )
        self._retry_btn.clicked.connect(self.retry_clicked.emit)
        btn_row.addWidget(self._retry_btn)

        self._change_btn = QPushButton(translator.tr("practice.change_track"))
        self._change_btn.setFont(QFont("Microsoft JhengHei", 12))
        self._change_btn.setFixedHeight(42)
        self._change_btn.setMinimumWidth(140)
        self._change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._change_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {ACCENT_GOLD};
                border: 1px solid {ACCENT_GOLD};
                border-radius: 6px;
                padding: 8px 24px;
            }}
            QPushButton:hover {{ background-color: rgba(212, 175, 55, 30); }}
            """
        )
        self._change_btn.clicked.connect(self.change_track_clicked.emit)
        btn_row.addWidget(self._change_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

    @staticmethod
    def _make_grade_label(name: str, color: str) -> QLabel:
        lbl = QLabel(f"{name}\n0")
        lbl.setFont(QFont("Microsoft JhengHei", 13, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {color};")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setMinimumWidth(80)
        return lbl

    def show_results(self, stats: PracticeStats) -> None:
        """Populate the results page with final session stats."""
        self._score_lbl.setText(str(stats.total_score))
        self._accuracy_lbl.setText(
            f"{translator.tr('practice.accuracy')}: {stats.accuracy * 100:.1f}%"
        )
        self._perfect_lbl.setText(f"{translator.tr('practice.perfect')}\n{stats.perfect}")
        self._great_lbl.setText(f"{translator.tr('practice.great')}\n{stats.great}")
        self._good_lbl.setText(f"{translator.tr('practice.good')}\n{stats.good}")
        self._miss_lbl.setText(f"{translator.tr('practice.miss')}\n{stats.missed}")
        self._combo_lbl.setText(f"{translator.tr('practice.max_combo')}: {stats.max_combo}")
        self._total_lbl.setText(f"{translator.tr('practice.total_notes')}: {stats.total_notes}")

    def update_text(self) -> None:
        self._title_lbl.setText(translator.tr("practice.result"))
        self._retry_btn.setText(translator.tr("practice.retry"))
        self._change_btn.setText(translator.tr("practice.change_track"))


# ── Main practice view ────────────────────────────────────────────


class PracticeView(QWidget):
    """Practice mode with falling notes, scoring, and built-in song picker."""

    file_open_requested = pyqtSignal()
    practice_track_requested = pyqtSignal(str)  # file_path

    # Lifecycle signals for AppShell to sync audio playback
    speed_changed = pyqtSignal(float)
    practice_started = pyqtSignal()  # practice session began
    practice_stopped = pyqtSignal()  # user stopped or changed track
    practice_finished = pyqtSignal()  # session ended naturally (all notes passed)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scorer: PracticeScorer | None = None
        self._notes: list[BeatNote] = []
        self._tempo_bpm: float = 120.0
        self._speed: float = 1.0
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

        # Row 1: title + [change_track_btn] + mode combo + scheme combo
        header_row = QHBoxLayout()

        self._title_lbl = QLabel(translator.tr("practice.title"))
        self._title_lbl.setFont(QFont("Microsoft JhengHei", 22, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet("background: transparent;")
        header_row.addWidget(self._title_lbl)

        header_row.addStretch()

        # Change Track button (hidden until a track is loaded)
        self._change_track_btn = QPushButton(translator.tr("practice.change_track"))
        self._change_track_btn.setFixedHeight(28)
        self._change_track_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._change_track_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {ACCENT_GOLD};
                border: 1px solid {ACCENT_GOLD};
                border-radius: 4px;
                padding: 2px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: rgba(212, 175, 55, 30); }}
            """
        )
        self._change_track_btn.clicked.connect(self._on_change_track)
        self._change_track_btn.setVisible(False)
        header_row.addWidget(self._change_track_btn)

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

        # Row 2: description / track name
        self._desc_lbl = QLabel(translator.tr("practice.desc"))
        self._desc_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        overlay_layout.addWidget(self._desc_lbl)
        overlay_layout.addStretch()

        header_overlay.setGeometry(0, 0, 800, 100)
        layout.addWidget(header_container)

        # ── Content stack (page 0: empty, page 1: practice, page 2: results) ──
        self._content_stack = QStackedWidget()

        # Page 0: Empty state / song picker
        self._empty_state = _PracticeEmptyState()
        self._empty_state.file_open_clicked.connect(self.file_open_requested.emit)
        self._empty_state.track_clicked.connect(self.practice_track_requested.emit)
        self._content_stack.addWidget(self._empty_state)

        # Page 1: Practice content (score bar + speed control + display)
        practice_content = QWidget()
        pc_layout = QVBoxLayout(practice_content)
        pc_layout.setContentsMargins(0, 0, 0, 0)
        pc_layout.setSpacing(0)

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

        # Speed control
        self._speed_control = SpeedControl()
        self._speed_control.speed_changed.connect(self._on_speed_changed)
        score_layout.addWidget(self._speed_control)

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

        pc_layout.addWidget(score_bar)

        # Main display
        self._display = PracticeDisplay()
        self._display.note_hit.connect(self._on_display_note_hit)
        self._display.practice_finished.connect(self._on_practice_ended)
        pc_layout.addWidget(self._display, 1)

        self._content_stack.addWidget(practice_content)

        # Page 2: Results summary
        self._results_page = _PracticeResultsPage()
        self._results_page.retry_clicked.connect(self._on_retry)
        self._results_page.change_track_clicked.connect(self._on_change_track)
        self._content_stack.addWidget(self._results_page)

        # Start on page 0 (empty state)
        self._content_stack.setCurrentIndex(0)

        layout.addWidget(self._content_stack, 1)

    # ── Public API ──

    def set_library_tracks(self, tracks: list[MidiFileInfo]) -> None:
        """Update the empty-state track list from library data."""
        self._empty_state.set_tracks(tracks)

    def set_current_track_name(self, name: str) -> None:
        """Show the current track name in the header description."""
        self._desc_lbl.setText(name)

    def start_practice(self, notes: list[BeatNote], tempo_bpm: float = 120.0) -> None:
        """Start practice session with given notes."""
        self._notes = notes
        self._tempo_bpm = tempo_bpm

        practice_notes = notes_to_practice(notes, tempo_bpm)
        self._scorer = PracticeScorer(practice_notes)
        self._scorer.start()
        self._display.set_speed(self._speed)
        self._display.set_notes(practice_notes, tempo_bpm)
        self._display.start()
        self._start_btn.setText(translator.tr("practice.stop"))

        # Switch to practice content (page 1)
        self._content_stack.setCurrentIndex(1)
        self._change_track_btn.setVisible(True)
        self.practice_started.emit()

    # ── Events ──

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_gradient_header"):
            for child in self._gradient_header.children():
                if isinstance(child, QWidget):
                    child.setGeometry(0, 0, self.width(), 100)

    # ── Slots ──

    def _on_change_track(self) -> None:
        """Stop practice and go back to song picker."""
        was_playing = self._display.is_playing
        if self._display.is_playing:
            self._display.stop()
        self._scorer = None
        self._notes = []
        self._content_stack.setCurrentIndex(0)
        self._change_track_btn.setVisible(False)
        self._desc_lbl.setText(translator.tr("practice.desc"))
        self._start_btn.setText(translator.tr("practice.start"))
        self._update_score_display()
        if was_playing or self._content_stack.currentIndex() != 0:
            self.practice_stopped.emit()

    def _on_start_stop(self) -> None:
        if self._display.is_playing:
            self._display.stop()
            self._start_btn.setText(translator.tr("practice.start"))
            self.practice_stopped.emit()
        elif self._notes:
            self.start_practice(self._notes, self._tempo_bpm)

    def on_user_note(self, note: int) -> None:
        """Called when user plays a note (from MIDI input or keyboard)."""
        if not self._scorer or not self._display.is_playing:
            return
        current_time = self._display.current_time
        hit = self._scorer.on_user_note(note, current_time)
        if hit is not None:
            self._display.show_feedback(hit.grade, note, hit.target_note.time_seconds)
            self._display.set_combo(self._scorer.stats.current_combo)
        self._update_score_display()

    def _on_display_note_hit(self, note: int, time: float) -> None:
        """Handle note hit from keyboard input in display."""
        self.on_user_note(note)

    def _on_practice_ended(self) -> None:
        """Session ended naturally (all notes passed)."""
        if self._scorer:
            stats = self._scorer.finalize()
            self._results_page.show_results(stats)
            self._content_stack.setCurrentIndex(2)
        self.practice_finished.emit()

    def _on_retry(self) -> None:
        """Restart practice with the same notes."""
        if self._notes:
            self.start_practice(self._notes, self._tempo_bpm)

    def _on_speed_changed(self, speed: float) -> None:
        self._speed = speed
        self._display.set_speed(speed)
        self.speed_changed.emit(speed)

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

    def _update_text(self) -> None:
        self._title_lbl.setText(translator.tr("practice.title"))
        self._change_track_btn.setText(translator.tr("practice.change_track"))
        # Only update desc if we're on page 0 (not showing track name)
        if self._content_stack.currentIndex() == 0:
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
        self._empty_state.update_text()
        self._results_page.update_text()

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
