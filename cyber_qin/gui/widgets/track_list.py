"""Scrollable track list widget with search, sort, and hover-reveal buttons — 賽博墨韻."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.midi_file_player import MidiFileInfo
from ..icons import draw_music_note
from ..theme import ACCENT, BG_PAPER, BG_WASH, DIVIDER, TEXT_PRIMARY, TEXT_SECONDARY
from .animated_widgets import IconButton

# 水墨配色 icon colors, rotated by index
_ICON_COLORS = [
    QColor("#00F0FF"),  # 賽博青
    QColor("#D4A853"),  # 金墨
    QColor("#FF4444"),  # 硃紅
    QColor("#4488CC"),  # 靛
    QColor("#E8A830"),  # 琥珀
    QColor("#2DB87A"),  # 翠
]

# Sort options: (display_name, key_func, reverse)
_SORT_OPTIONS: list[tuple[str, str]] = [
    ("預設順序", "default"),
    ("名稱", "name"),
    ("BPM", "bpm"),
    ("音符數", "notes"),
    ("時長", "duration"),
]


class _TrackIcon(QWidget):
    """40x40 MIDI file icon with QPainter-drawn music note."""

    def __init__(self, color: QColor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(40, 40)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Rounded background
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, 40, 40), 8, 8)
        bg = QColor(self._color)
        bg.setAlpha(30)
        painter.fillPath(path, bg)

        # Music note icon
        draw_music_note(painter, QRectF(4, 4, 32, 32), self._color)
        painter.end()


class _PlayingIndicator(QWidget):
    """Animated cyan music note for playing state."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(24, 24)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_music_note(painter, QRectF(0, 0, 24, 24), QColor(ACCENT))
        painter.end()


class TrackCard(QWidget):
    """Single track entry in the list with hover-reveal buttons."""

    play_clicked = pyqtSignal(int)    # index
    remove_clicked = pyqtSignal(int)  # index

    def __init__(self, index: int, info: MidiFileInfo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._index = index
        self._info = info
        self._is_playing = False

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(60)
        self.setStyleSheet(
            f"TrackCard {{ background-color: transparent; border-radius: 4px; }}"
            f"TrackCard:hover {{ background-color: {BG_WASH}; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(12)

        # Track icon (colored music note)
        icon_color = _ICON_COLORS[index % len(_ICON_COLORS)]
        self._track_icon = _TrackIcon(icon_color)
        layout.addWidget(self._track_icon)

        # Index / playing indicator
        self._index_label = QLabel(f"{index + 1}")
        self._index_label.setFixedWidth(24)
        self._index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._index_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; background: transparent;")
        layout.addWidget(self._index_label)

        self._playing_indicator = _PlayingIndicator()
        self._playing_indicator.setVisible(False)
        layout.addWidget(self._playing_indicator)

        # Track info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(info.name)
        name_label.setFont(QFont("Microsoft JhengHei", 13, QFont.Weight.DemiBold))
        name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        info_layout.addWidget(name_label)

        details = f"{info.track_count} tracks  |  {info.note_count} notes  |  {info.tempo_bpm} BPM"
        detail_label = QLabel(details)
        detail_label.setFont(QFont("Microsoft JhengHei", 10))
        detail_label.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        info_layout.addWidget(detail_label)

        layout.addLayout(info_layout, 1)

        # Duration
        mins = int(info.duration_seconds) // 60
        secs = int(info.duration_seconds) % 60
        dur_label = QLabel(f"{mins}:{secs:02d}")
        dur_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        layout.addWidget(dur_label)

        # Action buttons (hidden until hover)
        self._play_btn = IconButton("play", size=32)
        self._play_btn.setToolTip("播放")
        self._play_btn.clicked.connect(lambda: self.play_clicked.emit(self._index))
        self._play_btn.setVisible(False)
        layout.addWidget(self._play_btn)

        self._rm_btn = IconButton("remove", size=32)
        self._rm_btn.setToolTip("移除")
        self._rm_btn.clicked.connect(lambda: self.remove_clicked.emit(self._index))
        self._rm_btn.setVisible(False)
        layout.addWidget(self._rm_btn)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._play_btn.setVisible(True)
        self._rm_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._play_btn.setVisible(False)
        self._rm_btn.setVisible(False)
        super().leaveEvent(event)

    def set_playing(self, playing: bool) -> None:
        self._is_playing = playing
        self._index_label.setVisible(not playing)
        self._playing_indicator.setVisible(playing)
        if playing:
            self._index_label.setStyleSheet(f"color: {ACCENT}; font-size: 14px; background: transparent;")
        else:
            self._index_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; background: transparent;")

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.play_clicked.emit(self._index)


class TrackList(QWidget):
    """Scrollable list of MIDI track cards with search and sort."""

    play_requested = pyqtSignal(int)    # track index (in _all_cards)
    remove_requested = pyqtSignal(int)  # track index (in _all_cards)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._all_cards: list[TrackCard] = []
        self._visible_cards: list[TrackCard] = []
        self._playing_index: int = -1
        self._current_sort: str = "default"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        # Search + sort toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜尋曲名…")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setFixedHeight(32)
        self._search_input.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {BG_PAPER}; color: {TEXT_PRIMARY}; border: 1px solid {DIVIDER};"
            f"  border-radius: 6px; padding: 4px 10px; font-size: 12px;"
            f"}}"
            f"QLineEdit:focus {{ border-color: {ACCENT}; }}"
        )
        self._search_input.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self._search_input, 1)

        self._sort_combo = QComboBox()
        self._sort_combo.setFixedHeight(32)
        self._sort_combo.setFixedWidth(120)
        for display_name, _key in _SORT_OPTIONS:
            self._sort_combo.addItem(display_name)
        self._sort_combo.setStyleSheet(
            f"QComboBox {{"
            f"  background: {BG_PAPER}; color: {TEXT_PRIMARY}; border: 1px solid {DIVIDER};"
            f"  border-radius: 6px; padding: 4px 8px; font-size: 12px;"
            f"}}"
            f"QComboBox:focus {{ border-color: {ACCENT}; }}"
            f"QComboBox::drop-down {{ border: none; width: 20px; }}"
            f"QComboBox QAbstractItemView {{"
            f"  background: {BG_PAPER}; color: {TEXT_PRIMARY}; border: 1px solid {DIVIDER};"
            f"  selection-background-color: {BG_WASH};"
            f"}}"
        )
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        toolbar.addWidget(self._sort_combo)

        outer.addLayout(toolbar)

        # Scrollable card area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._layout.addStretch()

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll, 1)

    def add_track(self, info: MidiFileInfo) -> None:
        index = len(self._all_cards)
        card = TrackCard(index, info)
        card.play_clicked.connect(self.play_requested.emit)
        card.remove_clicked.connect(self._on_remove)
        self._all_cards.append(card)
        self._apply_filter()

    def _on_remove(self, index: int) -> None:
        if 0 <= index < len(self._all_cards):
            card = self._all_cards.pop(index)
            self._layout.removeWidget(card)
            card.deleteLater()
            # Re-index remaining cards
            for i, c in enumerate(self._all_cards):
                c._index = i
                c._index_label.setText(f"{i + 1}")
            self._apply_filter()
            self.remove_requested.emit(index)

    def set_playing(self, index: int) -> None:
        for i, card in enumerate(self._all_cards):
            card.set_playing(i == index)
        self._playing_index = index

    def clear(self) -> None:
        for card in self._all_cards:
            self._layout.removeWidget(card)
            card.deleteLater()
        self._all_cards.clear()
        self._visible_cards.clear()
        self._playing_index = -1

    @property
    def count(self) -> int:
        return len(self._all_cards)

    # ── Search & Sort ──

    def _on_sort_changed(self, combo_index: int) -> None:
        if 0 <= combo_index < len(_SORT_OPTIONS):
            self._current_sort = _SORT_OPTIONS[combo_index][1]
            self._apply_filter()

    def _apply_filter(self) -> None:
        """Rebuild visible card list based on search text and sort order."""
        query = self._search_input.text().strip().lower()

        # Filter
        filtered = [
            card for card in self._all_cards
            if not query or query in card._info.name.lower()
        ]

        # Sort
        if self._current_sort == "name":
            filtered.sort(key=lambda c: c._info.name.lower())
        elif self._current_sort == "bpm":
            filtered.sort(key=lambda c: c._info.tempo_bpm, reverse=True)
        elif self._current_sort == "notes":
            filtered.sort(key=lambda c: c._info.note_count, reverse=True)
        elif self._current_sort == "duration":
            filtered.sort(key=lambda c: c._info.duration_seconds, reverse=True)
        # "default" keeps insertion order

        # Remove all cards from layout (except the trailing stretch)
        for card in self._visible_cards:
            self._layout.removeWidget(card)
            card.setVisible(False)

        # Re-add filtered cards
        self._visible_cards = filtered
        for i, card in enumerate(filtered):
            self._layout.insertWidget(i, card)
            card.setVisible(True)

    # Alias for backwards compatibility
    @property
    def _cards(self) -> list[TrackCard]:
        return self._all_cards
