"""Custom-painted progress/seek bar widget with animated interactions — 賽博墨韻."""

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    pyqtProperty,  # type: ignore[attr-defined]
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath
from PyQt6.QtWidgets import QToolTip, QWidget

from ..theme import ACCENT, BG_MIST, TEXT_PRIMARY


class ProgressBar(QWidget):
    """Horizontal progress bar with click-to-seek, animated height, and time tooltip."""

    seek_requested = pyqtSignal(float)  # Position in seconds

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = 0.0       # 0.0 - 1.0
        self._anim_value = 0.0  # Animated display value 0.0 - 1.0
        self._duration = 0.0    # Total seconds
        self._hover_pos: float | None = None
        self._bar_height = 4.0
        self.setFixedHeight(20)
        self.setMinimumWidth(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        # Bar height animation
        self._height_anim = QPropertyAnimation(self, b"bar_height")
        self._height_anim.setDuration(120)
        self._height_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Handle opacity animation
        self._handle_opacity = 0.0
        self._handle_anim = QPropertyAnimation(self, b"handle_opacity")
        self._handle_anim.setDuration(150)
        self._handle_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Progress value animation (for smooth interpolation ticks)
        self._value_anim = QPropertyAnimation(self, b"anim_value")
        self._value_anim.setDuration(100)
        self._value_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def bar_height(self) -> float:
        return self._bar_height

    @bar_height.setter  # type: ignore[no-redef]
    def bar_height(self, val: float) -> None:
        self._bar_height = val
        self.update()

    @pyqtProperty(float)
    def handle_opacity(self) -> float:
        return self._handle_opacity

    @handle_opacity.setter  # type: ignore[no-redef]
    def handle_opacity(self, val: float) -> None:
        self._handle_opacity = val
        self.update()

    @pyqtProperty(float)
    def anim_value(self) -> float:
        return self._anim_value

    @anim_value.setter  # type: ignore[no-redef]
    def anim_value(self, val: float) -> None:
        self._anim_value = val
        self.update()

    def set_progress(self, current: float, total: float) -> None:
        """Direct jump — used for seek and reset (no animation)."""
        self._duration = total
        self._value = current / total if total > 0 else 0.0
        self._anim_value = self._value
        self._value_anim.stop()
        self.update()

    def set_progress_animated(self, current: float, total: float) -> None:
        """Smooth transition — used by interpolation timer."""
        self._duration = total
        self._value = current / total if total > 0 else 0.0
        self._value_anim.stop()
        self._value_anim.setStartValue(self._anim_value)
        self._value_anim.setEndValue(self._value)
        self._value_anim.start()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_h = self._bar_height
        bar_y = (h - bar_h) / 2

        # Track background
        track = QPainterPath()
        track.addRoundedRect(QRectF(0, bar_y, w, bar_h), bar_h / 2, bar_h / 2)
        painter.fillPath(track, QColor(BG_MIST))

        # Hover preview
        if self._hover_pos is not None:
            preview = QPainterPath()
            pw = self._hover_pos * w
            preview.addRoundedRect(QRectF(0, bar_y, pw, bar_h), bar_h / 2, bar_h / 2)
            painter.fillPath(preview, QColor(ACCENT + "40"))  # 25% opacity

        # Filled portion — 賽博青
        filled_w = self._anim_value * w
        if filled_w > 0:
            filled = QPainterPath()
            filled.addRoundedRect(QRectF(0, bar_y, filled_w, bar_h), bar_h / 2, bar_h / 2)
            painter.fillPath(filled, QColor(ACCENT))

        # Handle circle (with animated opacity)
        if self._handle_opacity > 0.01:
            cx = filled_w
            cy = h / 2
            handle_color = QColor(TEXT_PRIMARY)
            handle_color.setAlphaF(self._handle_opacity)
            painter.setBrush(handle_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(cx - 6), int(cy - 6), 12, 12)

        painter.end()

    def enterEvent(self, event) -> None:  # noqa: N802
        # Animate bar height 4 -> 6
        self._height_anim.stop()
        self._height_anim.setStartValue(self._bar_height)
        self._height_anim.setEndValue(6.0)
        self._height_anim.start()
        # Animate handle in
        self._handle_anim.stop()
        self._handle_anim.setStartValue(self._handle_opacity)
        self._handle_anim.setEndValue(1.0)
        self._handle_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover_pos = None
        # Animate bar height 6 -> 4
        self._height_anim.stop()
        self._height_anim.setStartValue(self._bar_height)
        self._height_anim.setEndValue(4.0)
        self._height_anim.start()
        # Animate handle out
        self._handle_anim.stop()
        self._handle_anim.setStartValue(self._handle_opacity)
        self._handle_anim.setEndValue(0.0)
        self._handle_anim.start()
        self.update()

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        if event and event.button() == Qt.MouseButton.LeftButton and self._duration > 0:
            ratio = max(0.0, min(1.0, event.position().x() / self.width()))
            self.seek_requested.emit(ratio * self._duration)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        if event is None:
            return
        self._hover_pos = max(0.0, min(1.0, event.position().x() / self.width()))

        # Show time tooltip
        if self._duration > 0:
            hover_time = self._hover_pos * self._duration
            mins = int(hover_time) // 60
            secs = int(hover_time) % 60
            QToolTip.showText(
                event.globalPosition().toPoint(),
                f"{mins}:{secs:02d}",
                self,
            )

        self.update()
