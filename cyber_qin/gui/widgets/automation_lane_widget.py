"""Automation lane widget — draggable control points synced to NoteRoll scroll/zoom."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from ...core.automation import AutomationLane
from ..theme import ACCENT, ACCENT_GOLD, BG_INK, DIVIDER, TEXT_SECONDARY

_POINT_RADIUS = 5.0
_LINE_WIDTH = 1.5
_LANE_HEIGHT = 100
_HEADER_HEIGHT = 20


class AutomationLaneWidget(QWidget):
    """Visual automation lane with draggable control points."""

    points_changed = pyqtSignal()  # Emitted when user edits points

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lane: AutomationLane | None = None
        self._scroll_x: float = 0.0
        self._zoom: float = 80.0  # pixels per beat, synced from NoteRoll
        self._dragging: bool = False
        self._drag_index: int = -1
        self._hover_index: int = -1
        self._parameter_name: str = "velocity"

        self.setMinimumHeight(_LANE_HEIGHT + _HEADER_HEIGHT)
        self.setFixedHeight(_LANE_HEIGHT + _HEADER_HEIGHT)
        self.setMouseTracking(True)

    # ── Data setters ────────────────────────────────────────

    def set_lane(self, lane: AutomationLane | None) -> None:
        self._lane = lane
        self._parameter_name = lane.parameter if lane else "velocity"
        self.update()

    def set_scroll_x(self, value: float) -> None:
        self._scroll_x = value
        self.update()

    def set_zoom(self, value: float) -> None:
        self._zoom = value
        self.update()

    @property
    def lane(self) -> AutomationLane | None:
        return self._lane

    # ── Coordinate helpers ──────────────────────────────────

    def _beat_to_x(self, beat: float) -> float:
        return (beat * self._zoom) - self._scroll_x

    def _x_to_beat(self, x: float) -> float:
        return (x + self._scroll_x) / self._zoom if self._zoom > 0 else 0.0

    def _value_to_y(self, value: float) -> float:
        """Map normalized value (0-1) to y coordinate."""
        body_h = self.height() - _HEADER_HEIGHT
        return _HEADER_HEIGHT + body_h * (1.0 - value)

    def _y_to_value(self, y: float) -> float:
        """Map y coordinate to normalized value (0-1)."""
        body_h = self.height() - _HEADER_HEIGHT
        if body_h <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (y - _HEADER_HEIGHT) / body_h))

    def _point_at(self, pos: QPointF) -> int:
        """Find point index near mouse position, or -1."""
        if not self._lane:
            return -1
        for i, pt in enumerate(self._lane.points):
            px = self._beat_to_x(pt.time_beats)
            py = self._value_to_y(pt.value)
            if abs(pos.x() - px) <= _POINT_RADIUS + 2 and abs(pos.y() - py) <= _POINT_RADIUS + 2:
                return i
        return -1

    # ── Mouse events ────────────────────────────────────────

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self._lane or event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position()
        idx = self._point_at(pos)

        if idx >= 0:
            self._dragging = True
            self._drag_index = idx
        else:
            # Add new point on double-click or plain click
            beat = max(0.0, self._x_to_beat(pos.x()))
            value = self._y_to_value(pos.y())
            self._lane.add_point(beat, value)
            self.points_changed.emit()
            self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()

        if self._dragging and self._lane and 0 <= self._drag_index < len(self._lane.points):
            beat = max(0.0, self._x_to_beat(pos.x()))
            value = self._y_to_value(pos.y())
            pt = self._lane.points[self._drag_index]
            pt.time_beats = beat
            pt.value = value
            self.update()
        else:
            old_hover = self._hover_index
            self._hover_index = self._point_at(pos)
            if old_hover != self._hover_index:
                self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._dragging:
            self._dragging = False
            if self._lane:
                self._lane.points.sort(key=lambda p: p.time_beats)
            self.points_changed.emit()
            self._drag_index = -1
            self.update()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        """Double-click on existing point to delete it."""
        if not self._lane or event.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._point_at(event.position())
        if idx >= 0:
            self._lane.remove_point(idx)
            self.points_changed.emit()
            self.update()

    # ── Paint ───────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(BG_INK))

        # Header
        painter.fillRect(0, 0, w, _HEADER_HEIGHT, QColor(DIVIDER))
        painter.setPen(QColor(TEXT_SECONDARY))
        painter.setFont(QFont("Microsoft JhengHei", 8))
        painter.drawText(4, _HEADER_HEIGHT - 4, self._parameter_name.capitalize())

        # Value grid lines (25%, 50%, 75%)
        body_h = h - _HEADER_HEIGHT
        pen = QPen(QColor(DIVIDER), 0.5, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        for frac in (0.25, 0.5, 0.75):
            y = _HEADER_HEIGHT + body_h * (1.0 - frac)
            painter.drawLine(0, int(y), w, int(y))

        if not self._lane or not self._lane.points:
            painter.end()
            return

        points = self._lane.points

        # Draw interpolation line
        line_pen = QPen(QColor(ACCENT), _LINE_WIDTH)
        painter.setPen(line_pen)

        if len(points) >= 2:
            path = QPainterPath()
            first_x = self._beat_to_x(points[0].time_beats)
            first_y = self._value_to_y(points[0].value)
            path.moveTo(first_x, first_y)
            for pt in points[1:]:
                px = self._beat_to_x(pt.time_beats)
                py = self._value_to_y(pt.value)
                path.lineTo(px, py)
            painter.drawPath(path)

        # Draw fill under line
        if len(points) >= 2:
            fill_path = QPainterPath()
            first_x = self._beat_to_x(points[0].time_beats)
            first_y = self._value_to_y(points[0].value)
            fill_path.moveTo(first_x, first_y)
            for pt in points[1:]:
                px = self._beat_to_x(pt.time_beats)
                py = self._value_to_y(pt.value)
                fill_path.lineTo(px, py)
            last_x = self._beat_to_x(points[-1].time_beats)
            fill_path.lineTo(last_x, h)
            fill_path.lineTo(first_x, h)
            fill_path.closeSubpath()
            fill_color = QColor(ACCENT)
            fill_color.setAlphaF(0.08)
            painter.fillPath(fill_path, fill_color)

        # Draw control points
        for i, pt in enumerate(points):
            px = self._beat_to_x(pt.time_beats)
            py = self._value_to_y(pt.value)
            r = _POINT_RADIUS + 1 if i == self._hover_index else _POINT_RADIUS

            # Outer ring
            painter.setPen(QPen(QColor(ACCENT_GOLD), 1.5))
            painter.setBrush(QColor(ACCENT) if i != self._drag_index else QColor(ACCENT_GOLD))
            painter.drawEllipse(QPointF(px, py), r, r)

        painter.end()
