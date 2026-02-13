"""Editor track panel — multi-track management sidebar for the editor."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.beat_sequence import Track
from ..theme import (
    ACCENT_GOLD,
    BG_INK,
    BG_PAPER,
    BG_SCROLL,
    BG_WASH,
    DIVIDER,
    TEXT_DISABLED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

_PANEL_WIDTH = 160
_TRACK_HEIGHT = 36
_HEADER_HEIGHT = 22  # Match NoteRoll/PitchRuler


class _TrackItem(QWidget):
    """Single track row in the panel."""

    activated = pyqtSignal(int)
    mute_toggled = pyqtSignal(int, bool)
    solo_toggled = pyqtSignal(int, bool)
    rename_requested = pyqtSignal(int)
    remove_requested = pyqtSignal(int)

    def __init__(
        self,
        index: int,
        track: Track,
        is_active: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._index = index
        self._track = track
        self._is_active = is_active
        self.setFixedHeight(_TRACK_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def index(self) -> int:
        return self._index

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self.update()

    def set_track(self, track: Track) -> None:
        self._track = track
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self._index)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.rename_requested.emit(self._index)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self.remove_requested.emit(self._index)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Active background
        if self._is_active:
            painter.fillRect(0, 0, w, h, QColor(BG_WASH))
            # Gold indicator bar on left
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(ACCENT_GOLD))
            indicator = QPainterPath()
            indicator.addRoundedRect(QRectF(0, 4, 3, h - 8), 1.5, 1.5)
            painter.drawPath(indicator)

        # Color dot
        dot_x = 10
        dot_y = h / 2
        dot_r = 5
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._track.color))
        painter.drawEllipse(QRectF(dot_x - dot_r, dot_y - dot_r, dot_r * 2, dot_r * 2))

        # Track name
        font = QFont("Microsoft JhengHei", 10)
        if self._is_active:
            font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(TEXT_PRIMARY) if self._is_active else QColor(TEXT_SECONDARY))
        name = self._track.name or f"Track {self._index + 1}"
        painter.drawText(
            QRectF(24, 0, w - 70, h),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            name,
        )

        # Mute indicator
        mx = w - 40
        if self._track.muted:
            painter.setPen(QPen(QColor(TEXT_DISABLED), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawText(
                QRectF(mx, 0, 18, h),
                Qt.AlignmentFlag.AlignCenter,
                "M",
            )
        else:
            painter.setPen(QColor(TEXT_SECONDARY))
            font.setPixelSize(10)
            painter.setFont(font)
            painter.drawText(
                QRectF(mx, 0, 18, h),
                Qt.AlignmentFlag.AlignCenter,
                "M",
            )

        # Solo indicator
        sx = w - 20
        if self._track.solo:
            painter.setPen(QPen(QColor(ACCENT_GOLD), 1.5))
        else:
            painter.setPen(QColor(TEXT_SECONDARY))
        painter.drawText(
            QRectF(sx, 0, 18, h),
            Qt.AlignmentFlag.AlignCenter,
            "S",
        )

        # Bottom divider
        painter.setPen(QColor(DIVIDER))
        painter.drawLine(8, h - 1, w - 8, h - 1)

        painter.end()


class EditorTrackPanel(QWidget):
    """Track management panel for the editor."""

    track_activated = pyqtSignal(int)
    track_muted = pyqtSignal(int, bool)
    track_soloed = pyqtSignal(int, bool)
    track_renamed = pyqtSignal(int, str)
    track_removed = pyqtSignal(int)
    track_added = pyqtSignal()
    tracks_reordered = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tracks: list[Track] = []
        self._active_index: int = 0
        self._track_items: list[_TrackItem] = []
        self.setFixedWidth(_PANEL_WIDTH)

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header (aligns with NoteRoll header height)
        header = QWidget()
        header.setFixedHeight(_HEADER_HEIGHT)
        header.setStyleSheet(f"background-color: {BG_SCROLL};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 8, 0)
        lbl = QLabel("音軌")
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; background: transparent;")
        header_layout.addWidget(lbl)
        header_layout.addStretch()
        root.addWidget(header)

        # Scroll area for track items
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {BG_INK}; border: none; }}"
            f"QWidget#trackContainer {{ background-color: {BG_INK}; }}"
        )

        self._container = QWidget()
        self._container.setObjectName("trackContainer")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)
        self._container_layout.addStretch()

        self._scroll.setWidget(self._container)
        root.addWidget(self._scroll, 1)

        # Add track button
        self._add_btn = QPushButton("+ 新增音軌")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setStyleSheet(
            f"QPushButton {{ background-color: {BG_PAPER}; color: {TEXT_SECONDARY};"
            f"  border: 1px dashed {DIVIDER}; border-radius: 6px;"
            f"  padding: 6px; font-size: 11px; }}"
            f"QPushButton:hover {{ color: {TEXT_PRIMARY}; background-color: {BG_WASH}; }}"
        )
        self._add_btn.clicked.connect(lambda: self.track_added.emit())
        root.addWidget(self._add_btn)

    def set_tracks(self, tracks: list[Track], active_index: int) -> None:
        """Rebuild track items from data."""
        self._tracks = tracks
        self._active_index = active_index

        # Remove old items
        for item in self._track_items:
            self._container_layout.removeWidget(item)
            item.deleteLater()
        self._track_items.clear()

        # Insert new items before the stretch
        for i, track in enumerate(tracks):
            item = _TrackItem(i, track, is_active=(i == active_index))
            item.activated.connect(self._on_item_activated)
            item.mute_toggled.connect(self.track_muted.emit)
            item.solo_toggled.connect(self.track_soloed.emit)
            item.rename_requested.connect(self._on_rename_requested)
            item.remove_requested.connect(self.track_removed.emit)
            self._container_layout.insertWidget(
                self._container_layout.count() - 1,
                item,
            )
            self._track_items.append(item)

    def _on_item_activated(self, index: int) -> None:
        self._active_index = index
        for item in self._track_items:
            item.set_active(item.index == index)
        self.track_activated.emit(index)

    def _on_rename_requested(self, index: int) -> None:
        if 0 <= index < len(self._tracks):
            current_name = self._tracks[index].name
            text, ok = QInputDialog.getText(
                self,
                "重新命名音軌",
                "名稱:",
                text=current_name,
            )
            if ok and text:
                self.track_renamed.emit(index, text)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        # Click on mute/solo areas
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            for item in self._track_items:
                item_rect = item.geometry()
                if item_rect.contains(int(pos.x()), int(pos.y())):
                    # Check if click is in mute/solo area
                    local_x = pos.x() - item_rect.x()
                    w = item.width()
                    if local_x >= w - 40 and local_x < w - 20:
                        # Mute toggle
                        new_muted = not self._tracks[item.index].muted
                        self.track_muted.emit(item.index, new_muted)
                        return
                    elif local_x >= w - 20:
                        # Solo toggle
                        new_solo = not self._tracks[item.index].solo
                        self.track_soloed.emit(item.index, new_solo)
                        return
        super().mousePressEvent(event)
