"""Beat-based piano roll timeline for the editor.

Displays notes as colored rounded rectangles, rests as red translucent bars,
ghost notes from inactive tracks, cursor as a cyan vertical line,
beat grid with bar lines, horizontal scroll and zoom.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QWheelEvent
from PyQt6.QtWidgets import QWidget

from ..theme import ACCENT, ACCENT_GLOW, BG_INK, BG_SCROLL, TEXT_SECONDARY

# Visual constants
_PIXELS_PER_BEAT = 80.0    # default zoom (pixels per beat)
_MIN_ZOOM = 20.0
_MAX_ZOOM = 400.0
_NOTE_RADIUS = 2.5
_CURSOR_WIDTH = 2.0
_HEADER_HEIGHT = 22        # bar number header

# Grid line colors
_BAR_LINE_COLOR = "#3A4050"
_BEAT_LINE_COLOR = "#2A3040"
_SUB_LINE_COLOR = "#1E2530"

# Rest color
_REST_COLOR = QColor(0xFF, 0x44, 0x44, 64)   # red 25% alpha
_REST_SELECTED_COLOR = QColor(0xFF, 0x66, 0x66, 128)  # red 50% alpha


class NoteRoll(QWidget):
    """Beat-based horizontal timeline showing notes, rests, and cursor."""

    note_selected = pyqtSignal(int)   # note index
    note_deleted = pyqtSignal(int)    # note index
    note_moved = pyqtSignal(int, float, int)  # index, time_delta_beats, pitch_delta
    cursor_moved = pyqtSignal(float)  # time in beats
    # Right-click on note
    note_right_clicked = pyqtSignal(int)  # note index

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._notes: list = []          # list of BeatNote
        self._rests: list = []          # list of BeatRest
        self._ghost_notes: list = []    # notes from other tracks (BeatNote with .color)
        self._cursor_beats: float = 0.0
        self._scroll_x: float = 0.0
        self._zoom: float = _PIXELS_PER_BEAT
        self._selected_index: int = -1
        self._midi_min: int = 48
        self._midi_max: int = 83
        self._tempo_bpm: float = 120.0
        self._beats_per_bar: float = 4.0
        self._active_track_color: str = "#00F0FF"

        # Flash state
        self._flash_beat: float = -1.0

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

    # ── Data setters ────────────────────────────────────────

    def set_notes(self, notes: list) -> None:
        self._notes = notes
        self.repaint()

    def set_rests(self, rests: list) -> None:
        self._rests = rests
        self.update()

    def set_ghost_notes(self, notes: list) -> None:
        self._ghost_notes = notes
        self.update()

    def set_cursor_beats(self, t: float) -> None:
        self._cursor_beats = t
        self._ensure_cursor_visible()
        self.update()

    def set_tempo(self, bpm: float) -> None:
        self._tempo_bpm = bpm
        self.update()

    def set_beats_per_bar(self, bpb: float) -> None:
        self._beats_per_bar = bpb
        self.update()

    def set_midi_range(self, midi_min: int, midi_max: int) -> None:
        self._midi_min = midi_min
        self._midi_max = midi_max
        self.update()

    def set_active_track_color(self, color: str) -> None:
        self._active_track_color = color
        self.update()

    def flash_at_beat(self, t: float) -> None:
        self._flash_beat = t
        self.repaint()
        QTimer.singleShot(350, self._clear_flash)

    def _clear_flash(self) -> None:
        self._flash_beat = -1.0
        self.update()

    # ── Coordinate helpers ──────────────────────────────────

    def _ensure_cursor_visible(self) -> None:
        cursor_px = self._cursor_beats * self._zoom
        visible_w = self.width()
        if cursor_px - self._scroll_x > visible_w * 0.8:
            self._scroll_x = cursor_px - visible_w * 0.5
        elif cursor_px < self._scroll_x:
            self._scroll_x = max(0, cursor_px - visible_w * 0.2)

    def _beat_to_x(self, beat: float) -> float:
        return beat * self._zoom - self._scroll_x

    def _x_to_beat(self, x: float) -> float:
        return (x + self._scroll_x) / self._zoom

    def _y_for_note(self, midi_note: int) -> float:
        range_size = self._midi_max - self._midi_min + 1
        body_h = self.height() - _HEADER_HEIGHT
        note_h = body_h / max(1, range_size)
        offset = self._midi_max - midi_note
        return _HEADER_HEIGHT + offset * note_h

    def _note_height(self) -> float:
        range_size = self._midi_max - self._midi_min + 1
        body_h = self.height() - _HEADER_HEIGHT
        return max(4.0, body_h / max(1, range_size) * 0.85)

    def _note_index_at(self, x: float, y: float) -> int:
        nh = self._note_height()
        for i, note in enumerate(self._notes):
            nx = self._beat_to_x(note.time_beats)
            nw = max(4.0, note.duration_beats * self._zoom)
            ny = self._y_for_note(note.note)
            if nx <= x <= nx + nw and ny <= y <= ny + nh:
                return i
        return -1

    # ── Mouse interaction (single-tool mode) ────────────────

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self._note_index_at(event.position().x(), event.position().y())
            if idx >= 0:
                self._selected_index = idx
                self.note_selected.emit(idx)
                note = self._notes[idx]
                self._drag_index = idx
                self._drag_start_pos = event.position()
                self._drag_original_time = note.time_beats
                self._drag_original_note = note.note
                self._drag_preview_time = note.time_beats
                self._drag_preview_note = note.note
            else:
                t = self._x_to_beat(event.position().x())
                self._cursor_beats = max(0.0, t)
                self._selected_index = -1
                self._drag_index = -1
                self.cursor_moved.emit(self._cursor_beats)
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            idx = self._note_index_at(event.position().x(), event.position().y())
            if idx >= 0:
                self.note_right_clicked.emit(idx)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_index >= 0 and event.buttons() & Qt.MouseButton.LeftButton:
            dx = event.position().x() - self._drag_start_pos.x()
            dy = event.position().y() - self._drag_start_pos.y()
            if not self._dragging and (abs(dx) > 4 or abs(dy) > 4):
                self._dragging = True
            if self._dragging:
                time_delta = dx / self._zoom
                self._drag_preview_time = max(0.0, self._drag_original_time + time_delta)
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
            delta = event.angleDelta().y()
            factor = 1.15 if delta > 0 else 1 / 1.15
            # Zoom centered on mouse position
            mouse_beat = self._x_to_beat(event.position().x())
            self._zoom = max(_MIN_ZOOM, min(_MAX_ZOOM, self._zoom * factor))
            # Adjust scroll to keep mouse_beat under cursor
            new_x = mouse_beat * self._zoom - event.position().x()
            self._scroll_x = max(0.0, new_x)
        else:
            delta = event.angleDelta().y()
            self._scroll_x = max(0, self._scroll_x - delta * 0.5)
        self.update()

    # ── Painting ────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(BG_INK))

        # Header background
        painter.fillRect(0, 0, w, _HEADER_HEIGHT, QColor(BG_SCROLL))

        # ── Grid lines ──────────────────────────────────────
        bpb = self._beats_per_bar if self._beats_per_bar > 0 else 4.0

        # Determine visible beat range
        first_beat = max(0, int(self._scroll_x / self._zoom) - 1)
        last_beat = int((self._scroll_x + w) / self._zoom) + 2

        painter.setFont(QFont("Microsoft JhengHei", 8))

        for beat_num in range(first_beat, last_beat):
            x = self._beat_to_x(float(beat_num))
            if x < -10 or x > w + 10:
                continue

            is_bar = abs(beat_num % bpb) < 0.001
            if is_bar:
                painter.setPen(QPen(QColor(_BAR_LINE_COLOR), 1.5))
            else:
                painter.setPen(QPen(QColor(_BEAT_LINE_COLOR), 0.5))
            painter.drawLine(int(x), _HEADER_HEIGHT, int(x), h)

            # Bar number in header
            if is_bar and bpb > 0:
                painter.setPen(QColor(TEXT_SECONDARY))
                bar_num = int(beat_num / bpb) + 1
                painter.drawText(
                    int(x + 3), 2, 40, _HEADER_HEIGHT - 2,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    str(bar_num),
                )

        # Sub-beat lines (1/8 or 1/16 depending on zoom)
        if self._zoom >= 60:
            sub_div = 0.5 if self._zoom < 150 else 0.25
            sub_pen = QPen(QColor(_SUB_LINE_COLOR), 0.3)
            first_sub = max(0, int(self._scroll_x / self._zoom / sub_div) - 1)
            last_sub = int((self._scroll_x + w) / self._zoom / sub_div) + 2
            for si in range(first_sub, last_sub):
                sb = si * sub_div
                if abs(sb - round(sb)) < 0.001:
                    continue  # skip whole beats (already drawn)
                sx = self._beat_to_x(sb)
                if 0 <= sx <= w:
                    painter.setPen(sub_pen)
                    painter.drawLine(int(sx), _HEADER_HEIGHT, int(sx), h)

        nh = self._note_height()

        # ── Ghost notes (inactive tracks) ───────────────────
        for gn in self._ghost_notes:
            gx = self._beat_to_x(gn.time_beats)
            gw = max(4.0, gn.duration_beats * self._zoom)
            if gx + gw < 0 or gx > w:
                continue
            gy = self._y_for_note(gn.note)
            ghost_rect = QRectF(gx, gy, gw, nh)
            ghost_path = QPainterPath()
            ghost_path.addRoundedRect(ghost_rect, _NOTE_RADIUS, _NOTE_RADIUS)
            gc = QColor(getattr(gn, '_ghost_color', '#888888'))
            gc.setAlphaF(0.2)
            painter.fillPath(ghost_path, gc)

        # ── Rests (red translucent bars) ────────────────────
        body_h = h - _HEADER_HEIGHT
        for ri, rest in enumerate(self._rests):
            rx = self._beat_to_x(rest.time_beats)
            rw = max(4.0, rest.duration_beats * self._zoom)
            if rx + rw < 0 or rx > w:
                continue
            rest_rect = QRectF(rx, _HEADER_HEIGHT, rw, body_h)
            rest_path = QPainterPath()
            rest_path.addRoundedRect(rest_rect, 1.0, 1.0)
            painter.fillPath(rest_path, _REST_COLOR)

        # ── Notes ───────────────────────────────────────────
        track_color = QColor(self._active_track_color)
        for i, note in enumerate(self._notes):
            is_dragged = self._dragging and i == self._drag_index
            if is_dragged:
                x = self._beat_to_x(self._drag_preview_time)
                y = self._y_for_note(self._drag_preview_note)
            else:
                x = self._beat_to_x(note.time_beats)
                y = self._y_for_note(note.note)

            nw = max(4.0, note.duration_beats * self._zoom)

            if x + nw < 0 or x > w:
                continue

            is_selected = i == self._selected_index
            note_rect = QRectF(x, y, nw, nh)
            path = QPainterPath()
            path.addRoundedRect(note_rect, _NOTE_RADIUS, _NOTE_RADIUS)

            is_flash = (
                not is_dragged
                and not is_selected
                and self._flash_beat >= 0
                and abs(note.time_beats - self._flash_beat) < 0.001
            )

            if is_dragged:
                drag_c = QColor(track_color)
                drag_c.setAlpha(140)
                painter.fillPath(path, drag_c)
                painter.setPen(QPen(QColor(ACCENT), 1.5))
                painter.drawPath(path)
            elif is_flash:
                painter.fillPath(path, QColor(ACCENT_GLOW))
                painter.setPen(QPen(QColor(0xFF, 0xFF, 0xFF, 180), 2.0))
                painter.drawPath(path)
            elif is_selected:
                painter.fillPath(path, QColor(0x40, 0xFF, 0xFF))
                painter.setPen(QPen(QColor(ACCENT), 1.5))
                painter.drawPath(path)
            else:
                fill = QColor(track_color)
                fill.setAlpha(200)
                painter.fillPath(path, fill)
                painter.setPen(Qt.PenStyle.NoPen)

        # ── Cursor line ─────────────────────────────────────
        cx = self._beat_to_x(self._cursor_beats)
        if 0 <= cx <= w:
            painter.setPen(QPen(QColor(ACCENT), _CURSOR_WIDTH))
            painter.drawLine(int(cx), _HEADER_HEIGHT, int(cx), h)

        painter.end()
