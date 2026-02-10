"""Horizontal note timeline (simplified piano roll) for the editor.

Displays notes as colored rounded rectangles, cursor as a cyan vertical line,
beat grid lines, with horizontal scroll and zoom.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QWheelEvent
from PyQt6.QtWidgets import QWidget

from ..theme import ACCENT, BG_INK, BG_SCROLL, DIVIDER, TEXT_SECONDARY

# Visual constants
_NOTE_HEIGHT = 4          # pixels per semitone
_PIXELS_PER_SEC = 200.0   # default zoom
_MIN_ZOOM = 50.0
_MAX_ZOOM = 800.0
_NOTE_RADIUS = 2.0
_CURSOR_WIDTH = 2.0
_HEADER_HEIGHT = 20       # beat number header


class NoteRoll(QWidget):
    """Horizontal timeline showing notes and cursor."""

    note_selected = pyqtSignal(int)   # note index
    note_deleted = pyqtSignal(int)    # note index
    note_moved = pyqtSignal(int, float, int)  # index, time_delta, pitch_delta
    cursor_moved = pyqtSignal(float)  # time in seconds

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._notes: list = []  # list of EditableNote
        self._cursor_time: float = 0.0
        self._scroll_x: float = 0.0
        self._zoom: float = _PIXELS_PER_SEC
        self._selected_index: int = -1
        self._midi_min: int = 48
        self._midi_max: int = 83
        self._tempo_bpm: float = 120.0

        # Drag state
        self._dragging: bool = False
        self._drag_index: int = -1
        self._drag_start_pos: QPointF = QPointF()
        self._drag_original_time: float = 0.0
        self._drag_original_note: int = 0
        self._drag_preview_time: float = 0.0
        self._drag_preview_note: int = 0

        self.setMinimumHeight(120)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_notes(self, notes: list) -> None:
        """Set the notes to display (list of EditableNote)."""
        self._notes = notes
        self.update()

    def set_cursor_time(self, t: float) -> None:
        self._cursor_time = t
        self._ensure_cursor_visible()
        self.update()

    def set_tempo(self, bpm: float) -> None:
        self._tempo_bpm = bpm
        self.update()

    def set_midi_range(self, midi_min: int, midi_max: int) -> None:
        self._midi_min = midi_min
        self._midi_max = midi_max
        self.update()

    def _ensure_cursor_visible(self) -> None:
        cursor_px = self._cursor_time * self._zoom
        visible_w = self.width()
        if cursor_px - self._scroll_x > visible_w * 0.8:
            self._scroll_x = cursor_px - visible_w * 0.5
        elif cursor_px < self._scroll_x:
            self._scroll_x = max(0, cursor_px - visible_w * 0.2)

    def _time_to_x(self, t: float) -> float:
        return t * self._zoom - self._scroll_x

    def _y_for_note(self, midi_note: int) -> float:
        """Map MIDI note to Y coordinate (higher note = higher on screen)."""
        range_size = self._midi_max - self._midi_min + 1
        body_h = self.height() - _HEADER_HEIGHT
        note_h = body_h / max(1, range_size)
        # Invert: highest note at top
        offset = self._midi_max - midi_note
        return _HEADER_HEIGHT + offset * note_h

    def _note_height(self) -> float:
        range_size = self._midi_max - self._midi_min + 1
        body_h = self.height() - _HEADER_HEIGHT
        return max(2.0, body_h / max(1, range_size) - 1)

    def _note_index_at(self, x: float, y: float) -> int:
        """Return index of note at pixel position, or -1."""
        nh = self._note_height()
        for i, note in enumerate(self._notes):
            nx = self._time_to_x(note.time_seconds)
            nw = max(4.0, note.duration_seconds * self._zoom)
            ny = self._y_for_note(note.note)
            if nx <= x <= nx + nw and ny <= y <= ny + nh:
                return i
        return -1

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self._note_index_at(event.position().x(), event.position().y())
            if idx >= 0:
                self._selected_index = idx
                self.note_selected.emit(idx)
                # Prepare for potential drag
                note = self._notes[idx]
                self._drag_index = idx
                self._drag_start_pos = event.position()
                self._drag_original_time = note.time_seconds
                self._drag_original_note = note.note
                self._drag_preview_time = note.time_seconds
                self._drag_preview_note = note.note
            else:
                # Click on empty space → move cursor
                t = (event.position().x() + self._scroll_x) / self._zoom
                self._cursor_time = max(0.0, t)
                self._selected_index = -1
                self._drag_index = -1
                self.cursor_moved.emit(self._cursor_time)
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_index >= 0 and event.buttons() & Qt.MouseButton.LeftButton:
            dx = event.position().x() - self._drag_start_pos.x()
            dy = event.position().y() - self._drag_start_pos.y()
            # Start drag after a small threshold (4px)
            if not self._dragging and (abs(dx) > 4 or abs(dy) > 4):
                self._dragging = True
            if self._dragging:
                # Horizontal → time offset
                time_delta = dx / self._zoom
                self._drag_preview_time = max(0.0, self._drag_original_time + time_delta)
                # Vertical → pitch offset (up = higher pitch)
                nh = self._note_height()
                pitch_delta = -int(round(dy / max(1.0, nh)))
                self._drag_preview_note = max(0, min(127, self._drag_original_note + pitch_delta))
                self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            time_delta = self._drag_preview_time - self._drag_original_time
            pitch_delta = self._drag_preview_note - self._drag_original_note
            if abs(time_delta) > 1e-6 or pitch_delta != 0:
                self.note_moved.emit(self._drag_index, time_delta, pitch_delta)
            self._dragging = False
            self._drag_index = -1
            self.update()
        elif event.button() == Qt.MouseButton.LeftButton:
            self._drag_index = -1
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Delete and self._selected_index >= 0:
            self.note_deleted.emit(self._selected_index)
            self._selected_index = -1
        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoom
            delta = event.angleDelta().y()
            factor = 1.15 if delta > 0 else 1 / 1.15
            self._zoom = max(_MIN_ZOOM, min(_MAX_ZOOM, self._zoom * factor))
        else:
            # Scroll
            delta = event.angleDelta().y()
            self._scroll_x = max(0, self._scroll_x - delta * 0.5)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(BG_INK))

        # Beat grid header
        painter.fillRect(0, 0, w, _HEADER_HEIGHT, QColor(BG_SCROLL))

        beat_sec = 60.0 / self._tempo_bpm if self._tempo_bpm > 0 else 0.5
        if beat_sec > 0:
            # Draw beat lines
            first_beat = int(self._scroll_x / (beat_sec * self._zoom))
            max_beats = int((self._scroll_x + w) / (beat_sec * self._zoom)) + 2

            painter.setFont(QFont("Microsoft JhengHei", 8))

            for beat_num in range(max(0, first_beat), max_beats):
                t = beat_num * beat_sec
                x = self._time_to_x(t)
                if x < -10 or x > w + 10:
                    continue

                is_bar = beat_num % 4 == 0
                if is_bar:
                    painter.setPen(QPen(QColor(DIVIDER), 1.0))
                else:
                    painter.setPen(QPen(QColor(DIVIDER), 0.5))
                painter.drawLine(int(x), _HEADER_HEIGHT, int(x), h)

                # Beat number in header
                if is_bar:
                    painter.setPen(QColor(TEXT_SECONDARY))
                    bar_num = beat_num // 4 + 1
                    painter.drawText(int(x + 3), 2, 40, _HEADER_HEIGHT - 2,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                     str(bar_num))

        # Draw notes
        nh = self._note_height()
        for i, note in enumerate(self._notes):
            is_dragged = self._dragging and i == self._drag_index
            if is_dragged:
                # Use preview position for the dragged note
                x = self._time_to_x(self._drag_preview_time)
                y = self._y_for_note(self._drag_preview_note)
            else:
                x = self._time_to_x(note.time_seconds)
                y = self._y_for_note(note.note)

            nw = max(4.0, note.duration_seconds * self._zoom)

            if x + nw < 0 or x > w:
                continue  # off-screen

            is_selected = i == self._selected_index
            note_rect = QRectF(x, y, nw, nh)
            path = QPainterPath()
            path.addRoundedRect(note_rect, _NOTE_RADIUS, _NOTE_RADIUS)

            if is_dragged:
                # Semi-transparent highlight while dragging
                painter.fillPath(path, QColor(0x00, 0xF0, 0xFF, 140))
                painter.setPen(QPen(QColor(ACCENT), 1.5))
                painter.drawPath(path)
            elif is_selected:
                painter.fillPath(path, QColor(0x40, 0xFF, 0xFF))
                painter.setPen(QPen(QColor(ACCENT), 1.5))
                painter.drawPath(path)
            else:
                painter.fillPath(path, QColor(0x00, 0xC0, 0xD0))
                painter.setPen(Qt.PenStyle.NoPen)

        # Cursor line
        cx = self._time_to_x(self._cursor_time)
        if 0 <= cx <= w:
            painter.setPen(QPen(QColor(ACCENT), _CURSOR_WIDTH))
            painter.drawLine(int(cx), _HEADER_HEIGHT, int(cx), h)

        painter.end()
