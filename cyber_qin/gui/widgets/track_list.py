"""Scrollable track list widget (Spotify playlist style) with icon buttons and hover reveal."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.midi_file_player import MidiFileInfo
from ..icons import draw_music_note
from ..theme import ACCENT, BG_HOVER, TEXT_PRIMARY, TEXT_SECONDARY
from .animated_widgets import IconButton

# Colors for track icons, rotated by index
_ICON_COLORS = [
    QColor("#1DB954"),  # Green
    QColor("#1E90FF"),  # Dodger blue
    QColor("#E91E63"),  # Pink
    QColor("#FF9800"),  # Orange
    QColor("#9C27B0"),  # Purple
    QColor("#00BCD4"),  # Cyan
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
    """Animated green music note for playing state."""

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
            f"TrackCard:hover {{ background-color: {BG_HOVER}; }}"
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
        name_label.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        info_layout.addWidget(name_label)

        details = f"{info.track_count} tracks  |  {info.note_count} notes  |  {info.tempo_bpm} BPM"
        detail_label = QLabel(details)
        detail_label.setFont(QFont("Segoe UI", 10))
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
    """Scrollable list of MIDI track cards."""

    play_requested = pyqtSignal(int)    # track index
    remove_requested = pyqtSignal(int)  # track index

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: list[TrackCard] = []
        self._playing_index: int = -1

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

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
        outer.addWidget(self._scroll)

    def add_track(self, info: MidiFileInfo) -> None:
        index = len(self._cards)
        card = TrackCard(index, info)
        card.play_clicked.connect(self.play_requested.emit)
        card.remove_clicked.connect(self._on_remove)
        self._cards.append(card)
        self._layout.insertWidget(self._layout.count() - 1, card)

    def _on_remove(self, index: int) -> None:
        if 0 <= index < len(self._cards):
            card = self._cards.pop(index)
            self._layout.removeWidget(card)
            card.deleteLater()
            # Re-index remaining cards
            for i, c in enumerate(self._cards):
                c._index = i
                c._index_label.setText(f"{i + 1}")
            self.remove_requested.emit(index)

    def set_playing(self, index: int) -> None:
        for i, card in enumerate(self._cards):
            card.set_playing(i == index)
        self._playing_index = index

    def clear(self) -> None:
        for card in self._cards:
            self._layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._playing_index = -1

    @property
    def count(self) -> int:
        return len(self._cards)
