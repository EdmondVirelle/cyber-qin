"""Beat-based piano roll timeline for the editor.

Displays notes as colored rounded rectangles, rests as red translucent bars,
ghost notes from inactive tracks, cursor as a cyan vertical line,
beat grid with bar lines, horizontal scroll and zoom.

Supports multi-select (Shift+drag marquee, Ctrl+click), batch drag,
note resize (right-edge drag), note labels, and snap-to-grid.
"""

from __future__ import annotations

import bisect

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QWheelEvent
from PyQt6.QtWidgets import QWidget

from ...core.constants import EDITOR_MIDI_MAX, EDITOR_MIDI_MIN, PLAYABLE_MIDI_MAX, PLAYABLE_MIDI_MIN
from ..theme import ACCENT, ACCENT_GLOW, ACCENT_GOLD, BG_INK, BG_SCROLL, TEXT_PRIMARY, TEXT_SECONDARY

# Visual constants
_PIXELS_PER_BEAT = 80.0    # default zoom (pixels per beat)
_MIN_ZOOM = 20.0
_MAX_ZOOM = 400.0
_NOTE_RADIUS = 2.5
_CURSOR_WIDTH = 2.0
_HEADER_HEIGHT = 22        # bar number header
_RESIZE_THRESHOLD = 6      # pixels from right edge to trigger resize

# Grid line colors
_BAR_LINE_COLOR = "#3A4050"
_BEAT_LINE_COLOR = "#2A3040"
_SUB_LINE_COLOR = "#1E2530"

# Rest color
_REST_COLOR = QColor(0xFF, 0x44, 0x44, 64)   # red 25% alpha
_REST_SELECTED_COLOR = QColor(0xFF, 0x66, 0x66, 128)  # red 50% alpha

# Selection marquee
_MARQUEE_COLOR = QColor(0x00, 0xF0, 0xFF, 40)
_MARQUEE_BORDER = QColor(0x00, 0xF0, 0xFF, 180)

# Note names for labels
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class NoteRoll(QWidget):
    """Beat-based horizontal timeline showing notes, rests, and cursor."""

    note_selected = pyqtSignal(int)   # note index
    note_deleted = pyqtSignal(int)    # note index
    note_moved = pyqtSignal(int, float, int)  # index, time_delta_beats, pitch_delta
    cursor_moved = pyqtSignal(float)  # time in beats
    note_right_clicked = pyqtSignal(int)  # note index

    # Multi-select
    selection_changed = pyqtSignal(list, list)  # note_indices, rest_indices
    note_resized = pyqtSignal(int, float)  # index, new_duration_beats
    notes_moved = pyqtSignal(list, float, int)  # indices, time_delta, pitch_delta

    # Pencil draw
    note_draw_requested = pyqtSignal(float, int)  # time_beats, midi_note

    # Context menu
    context_menu_requested = pyqtSignal(float, float)  # widget x, y

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._notes: list = []          # list of BeatNote
        self._rests: list = []          # list of BeatRest
        self._ghost_notes: list = []    # notes from other tracks (BeatNote with .color)
        self._cursor_beats: float = 0.0
        self._playback_beats: float = -1.0  # playback cursor, -1 = hidden
        self._scroll_x: float = 0.0
        self._zoom: float = _PIXELS_PER_BEAT
        self._midi_min: int = EDITOR_MIDI_MIN  # 21 (A0)
        self._midi_max: int = EDITOR_MIDI_MAX  # 108 (C8)
        self._tempo_bpm: float = 120.0
        self._beats_per_bar: float = 4.0
        self._active_track_color: str = "#00F0FF"

        # Multi-select state
        self._selected_note_indices: set[int] = set()
        self._selected_rest_indices: set[int] = set()

        # Active notes (for playback feedback)
        self._active_notes: set[int] = set()  # set of MIDI pitch values


        # Snap
        self._snap_enabled: bool = True

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

        # Resize state
        self._resizing: bool = False
        self._resize_index: int = -1
        self._resize_original_dur: float = 0.0
        self._resize_start_x: float = 0.0

        # Marquee state
        self._marquee_active: bool = False
        self._marquee_start: QPointF = QPointF()
        self._marquee_end: QPointF = QPointF()

        # Range-select state (drag on empty space)
        self._range_select_active: bool = False
        self._range_select_origin: float = 0.0    # beat of initial click
        self._range_select_end: float = 0.0       # beat of current drag
        self._empty_press_pos: QPointF = QPointF()

        # Pencil (draw) mode
        self._pencil_mode: bool = False

        # Auto-scroll during drag
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.setInterval(50)
        self._auto_scroll_timer.timeout.connect(self._on_auto_scroll)
        self._last_mouse_x: float = 0.0

        self.setMinimumHeight(120)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ── Data setters ────────────────────────────────────────

    def set_notes(self, notes: list) -> None:
        self._notes = notes
        self._selected_note_indices.clear()
        self._selected_rest_indices.clear()
        self.repaint()

    def set_rests(self, rests: list) -> None:
        self._rests = rests
        self.update()

    def set_ghost_notes(self, notes: list) -> None:
        self._ghost_notes = notes
        self.update()

    def set_active_notes(self, notes: set[int]) -> None:
        """Set currently playing notes (MIDI pitches) for visualization."""
        self._active_notes = notes
        self.update()

    def set_cursor_beats(self, t: float) -> None:
        self._cursor_beats = t
        self._ensure_cursor_visible()
        self.update()

    def set_playback_beats(self, t: float) -> None:
        """Set playback cursor position. Use -1 to hide."""
        self._playback_beats = t
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

    def set_snap_enabled(self, enabled: bool) -> None:
        self._snap_enabled = enabled

    def _is_note_playable(self, midi_note: int) -> bool:
        """Check if note is in the playable game zone (60-83)."""
        return PLAYABLE_MIDI_MIN <= midi_note <= PLAYABLE_MIDI_MAX

    def flash_at_beat(self, t: float) -> None:
        self._flash_beat = t
        self.repaint()
        QTimer.singleShot(350, self._clear_flash)

    def _clear_flash(self) -> None:
        self._flash_beat = -1.0
        self.update()

    def set_pencil_mode(self, enabled: bool) -> None:
        self._pencil_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    @property
    def pencil_mode(self) -> bool:
        return self._pencil_mode

    def _on_auto_scroll(self) -> None:
        """Auto-scroll when mouse is near left/right edges during drag."""
        margin = 40.0
        speed_factor = 0.15  # beats per tick
        w = self.width()
        x = self._last_mouse_x

        if x < margin:
            # Scroll left
            amount = (margin - x) / margin * speed_factor * self._zoom
            self._scroll_x = max(0.0, self._scroll_x - amount)
            self.update()
        elif x > w - margin:
            # Scroll right
            amount = (x - (w - margin)) / margin * speed_factor * self._zoom
            self._scroll_x += amount
            self.update()

    # ── Selection API ────────────────────────────────────────

    @property
    def selected_note_indices(self) -> set[int]:
        return set(self._selected_note_indices)

    @property
    def selected_rest_indices(self) -> set[int]:
        return set(self._selected_rest_indices)

    def select_all(self) -> None:
        self._selected_note_indices = set(range(len(self._notes)))
        self._selected_rest_indices = set(range(len(self._rests)))
        self._emit_selection_changed()
        self.update()

    def clear_selection(self) -> None:
        self._selected_note_indices.clear()
        self._selected_rest_indices.clear()
        self._emit_selection_changed()
        self.update()

    def select_notes_in_time_range(self, t0: float, t1: float) -> None:
        """Select all notes/rests whose time_beats falls in [t0, t1)."""
        self._selected_note_indices.clear()
        self._selected_rest_indices.clear()
        for i, note in enumerate(self._notes):
            if t0 <= note.time_beats < t1:
                self._selected_note_indices.add(i)
        for i, rest in enumerate(self._rests):
            if t0 <= rest.time_beats < t1:
                self._selected_rest_indices.add(i)
        self._emit_selection_changed()
        self.update()

    def _emit_selection_changed(self) -> None:
        self.selection_changed.emit(
            sorted(self._selected_note_indices),
            sorted(self._selected_rest_indices),
        )

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

    def _y_to_note(self, y: float) -> int:
        """Convert Y pixel position to MIDI note number."""
        range_size = self._midi_max - self._midi_min + 1
        body_h = self.height() - _HEADER_HEIGHT
        note_h = body_h / max(1, range_size)
        offset = (y - _HEADER_HEIGHT) / max(1.0, note_h)
        return max(self._midi_min, min(self._midi_max, int(self._midi_max - offset)))

    def _note_height(self) -> float:
        range_size = self._midi_max - self._midi_min + 1
        body_h = self.height() - _HEADER_HEIGHT
        return max(4.0, body_h / max(1, range_size) * 0.85)

    def _snap_beat(self, beat: float) -> float:
        """Snap beat to grid if snap is enabled."""
        if not self._snap_enabled:
            return beat
        # Snap to nearest sub-beat based on zoom level.
        # Grid resolution increases as the user zooms in:
        #   zoom >= 200  → 1/32 (0.125 beats)
        #   zoom >= 80   → 1/16 (0.25 beats)  — default zoom
        #   zoom >= 40   → 1/8  (0.5 beats)
        #   zoom <  40   → 1/4  (1.0 beat)
        if self._zoom >= 200:
            grid = 0.125
        elif self._zoom >= 80:
            grid = 0.25
        elif self._zoom >= 40:
            grid = 0.5
        else:
            grid = 1.0
        return round(beat / grid) * grid

    def _note_index_at(self, x: float, y: float) -> int:
        nh = self._note_height()
        for i, note in enumerate(self._notes):
            nx = self._beat_to_x(note.time_beats)
            nw = max(4.0, note.duration_beats * self._zoom)
            ny = self._y_for_note(note.note)
            if nx <= x <= nx + nw and ny <= y <= ny + nh:
                return i
        return -1

    def _is_on_right_edge(self, x: float, y: float) -> int:
        """Return note index if x,y is on the right edge (for resize), else -1."""
        nh = self._note_height()
        for i, note in enumerate(self._notes):
            nx = self._beat_to_x(note.time_beats)
            nw = max(4.0, note.duration_beats * self._zoom)
            ny = self._y_for_note(note.note)
            right_x = nx + nw
            if abs(x - right_x) <= _RESIZE_THRESHOLD and ny <= y <= ny + nh:
                return i
        return -1

    # ── Mouse interaction ────────────────────────────────────

    def mousePressEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if event.button() == Qt.MouseButton.LeftButton:
            # Check resize first
            resize_idx = self._is_on_right_edge(pos.x(), pos.y())
            if resize_idx >= 0:
                self._resizing = True
                self._resize_index = resize_idx
                self._resize_original_dur = self._notes[resize_idx].duration_beats
                self._resize_start_x = pos.x()
                return

            idx = self._note_index_at(pos.x(), pos.y())

            if shift and idx < 0:
                # Start marquee selection
                self._marquee_active = True
                self._marquee_start = pos
                self._marquee_end = pos
                return

            if idx >= 0:
                if ctrl:
                    # Ctrl+click toggles individual selection
                    if idx in self._selected_note_indices:
                        self._selected_note_indices.discard(idx)
                    else:
                        self._selected_note_indices.add(idx)
                    self._emit_selection_changed()
                else:
                    # If clicking on an already-selected note, keep selection for batch drag
                    if idx not in self._selected_note_indices:
                        self._selected_note_indices = {idx}
                        self._selected_rest_indices.clear()
                        self._emit_selection_changed()

                self.note_selected.emit(idx)
                note = self._notes[idx]
                self._drag_index = idx
                self._drag_start_pos = pos
                self._drag_original_time = note.time_beats
                self._drag_original_note = note.note
                self._drag_preview_time = note.time_beats
                self._drag_preview_note = note.note
            else:
                # Click on empty space
                t = self._x_to_beat(pos.x())
                t = max(0.0, self._snap_beat(t))

                if self._pencil_mode:
                    # Pencil: draw note at clicked position
                    midi_note = self._y_to_note(pos.y())
                    self.note_draw_requested.emit(t, midi_note)
                    self._drag_index = -1
                else:
                    # Select mode: move cursor, clear selection
                    self._cursor_beats = t
                    self._selected_note_indices.clear()
                    self._selected_rest_indices.clear()
                    self._drag_index = -1
                    self._range_select_active = False
                    self._range_select_origin = t
                    self._empty_press_pos = pos
                    self._emit_selection_changed()
                    self.cursor_moved.emit(self._cursor_beats)
            self.update()

        elif event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(pos.x(), pos.y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        self._last_mouse_x = pos.x()

        # Marquee drag
        if self._marquee_active:
            self._marquee_end = pos
            if not self._auto_scroll_timer.isActive():
                self._auto_scroll_timer.start()
            self.update()
            return

        # Resize drag
        if self._resizing:
            dx = pos.x() - self._resize_start_x
            delta_beats = dx / self._zoom
            new_dur = max(0.25, self._resize_original_dur + delta_beats)
            if self._snap_enabled:
                note = self._notes[self._resize_index]
                end = note.time_beats + new_dur
                end = self._snap_beat(end)
                new_dur = max(0.25, end - note.time_beats)
            self._notes[self._resize_index].duration_beats = new_dur
            self.update()
            return

        # Note drag
        if self._drag_index >= 0 and event.buttons() & Qt.MouseButton.LeftButton:
            dx = pos.x() - self._drag_start_pos.x()
            dy = pos.y() - self._drag_start_pos.y()
            if not self._dragging and (abs(dx) > 4 or abs(dy) > 4):
                self._dragging = True
            if self._dragging:
                time_delta = dx / self._zoom
                preview_t = max(0.0, self._drag_original_time + time_delta)
                if self._snap_enabled:
                    preview_t = self._snap_beat(preview_t)
                self._drag_preview_time = preview_t
                nh = self._note_height()
                pitch_delta = -int(round(dy / max(1.0, nh)))
                self._drag_preview_note = max(0, min(127, self._drag_original_note + pitch_delta))
                if not self._auto_scroll_timer.isActive():
                    self._auto_scroll_timer.start()
                self.update()
                return

        # Range select (drag on empty space)
        if (not self._dragging and not self._resizing and not self._marquee_active
                and self._drag_index < 0
                and event.buttons() & Qt.MouseButton.LeftButton):
            dx = abs(pos.x() - self._empty_press_pos.x())
            if dx > 6:
                self._range_select_active = True
            if self._range_select_active:
                current_beat = max(0.0, self._snap_beat(self._x_to_beat(pos.x())))
                self._range_select_end = current_beat
                t0 = min(self._range_select_origin, current_beat)
                t1 = max(self._range_select_origin, current_beat)
                self._selected_note_indices.clear()
                self._selected_rest_indices.clear()
                for i, note in enumerate(self._notes):
                    if t0 <= note.time_beats < t1:
                        self._selected_note_indices.add(i)
                for i, rest in enumerate(self._rests):
                    if t0 <= rest.time_beats < t1:
                        self._selected_rest_indices.add(i)
                self._emit_selection_changed()
                if not self._auto_scroll_timer.isActive():
                    self._auto_scroll_timer.start()
                self.update()
                return

        # Cursor shape based on hover position
        resize_idx = self._is_on_right_edge(pos.x(), pos.y())
        note_idx = self._note_index_at(pos.x(), pos.y())
        if resize_idx >= 0:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif note_idx >= 0:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif self._pencil_mode:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._auto_scroll_timer.stop()

        if event.button() == Qt.MouseButton.LeftButton:
            # Range-select release
            if self._range_select_active:
                self._range_select_active = False
                self.update()
                return

            # Marquee release
            if self._marquee_active:
                self._marquee_active = False
                self._apply_marquee_selection()
                self.update()
                return

            # Resize release
            if self._resizing:
                new_dur = self._notes[self._resize_index].duration_beats
                # Restore original for undo and emit signal
                self._notes[self._resize_index].duration_beats = self._resize_original_dur
                self.note_resized.emit(self._resize_index, new_dur)
                self._resizing = False
                self._resize_index = -1
                self.update()
                return

            # Drag release
            if self._dragging:
                time_delta = self._drag_preview_time - self._drag_original_time
                pitch_delta = self._drag_preview_note - self._drag_original_note
                if abs(time_delta) > 1e-6 or pitch_delta != 0:
                    if len(self._selected_note_indices) > 1:
                        # Batch drag
                        self.notes_moved.emit(
                            sorted(self._selected_note_indices), time_delta, pitch_delta,
                        )
                    else:
                        self.note_moved.emit(self._drag_index, time_delta, pitch_delta)
                self._dragging = False
                self._drag_index = -1
                self.update()
                return

            self._drag_index = -1

        super().mouseReleaseEvent(event)

    def _apply_marquee_selection(self) -> None:
        """Compute notes/rests within the marquee rectangle."""
        x0 = min(self._marquee_start.x(), self._marquee_end.x())
        x1 = max(self._marquee_start.x(), self._marquee_end.x())
        y0 = min(self._marquee_start.y(), self._marquee_end.y())
        y1 = max(self._marquee_start.y(), self._marquee_end.y())

        self._selected_note_indices.clear()
        self._selected_rest_indices.clear()

        sel_rect = QRectF(x0, y0, x1 - x0, y1 - y0)
        nh = self._note_height()
        for i, note in enumerate(self._notes):
            nx = self._beat_to_x(note.time_beats)
            nw = max(4.0, note.duration_beats * self._zoom)
            ny = self._y_for_note(note.note)
            note_rect = QRectF(nx, ny, nw, nh)
            if note_rect.intersects(sel_rect):
                self._selected_note_indices.add(i)

        body_h = self.height() - _HEADER_HEIGHT
        for i, rest in enumerate(self._rests):
            rx = self._beat_to_x(rest.time_beats)
            rw = max(4.0, rest.duration_beats * self._zoom)
            rest_rect = QRectF(rx, _HEADER_HEIGHT, rw, body_h)
            if rest_rect.intersects(sel_rect):
                self._selected_rest_indices.add(i)

        self._emit_selection_changed()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Delete:
            if self._selected_note_indices or self._selected_rest_indices:
                # Delete all selected — handled by EditorView via selection_changed
                self.note_deleted.emit(-1)  # signal to EditorView to delete selection
            elif len(self._selected_note_indices) == 0:
                pass
        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent | None) -> None:  # noqa: N802, type: ignore[override]
        if event is None:
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.15 if delta > 0 else 1 / 1.15
            mouse_beat = self._x_to_beat(event.position().x())
            self._zoom = max(_MIN_ZOOM, min(_MAX_ZOOM, self._zoom * factor))
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

            if is_bar and bpb > 0:
                painter.setPen(QColor(TEXT_SECONDARY))
                bar_num = int(beat_num / bpb) + 1
                painter.drawText(
                    int(x + 3), 2, 40, _HEADER_HEIGHT - 2,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    str(bar_num),
                )

        # Sub-beat lines
        if self._zoom >= 40:
            if self._zoom >= 200:
                sub_div = 0.125
            elif self._zoom >= 80:
                sub_div = 0.25
            else:
                sub_div = 0.5
            sub_pen = QPen(QColor(_SUB_LINE_COLOR), 0.3)
            first_sub = max(0, int(self._scroll_x / self._zoom / sub_div) - 1)
            last_sub = int((self._scroll_x + w) / self._zoom / sub_div) + 2
            for si in range(first_sub, last_sub):
                sb = si * sub_div
                if abs(sb - round(sb)) < 0.001:
                    continue
                sx = self._beat_to_x(sb)
                if 0 <= sx <= w:
                    painter.setPen(sub_pen)
                    painter.drawLine(int(sx), _HEADER_HEIGHT, int(sx), h)

        nh = self._note_height()

        # ── Playable zone borders ───────────────────────────
        # Draw horizontal lines at C4 (MIDI 60) and B5 (MIDI 83) boundaries
        playable_top_y = self._y_for_note(PLAYABLE_MIDI_MAX)
        playable_bottom_y = self._y_for_note(PLAYABLE_MIDI_MIN - 1) + nh  # Bottom of MIDI 60

        # Top border (above B5)
        painter.setPen(QPen(QColor(ACCENT_GOLD), 1.5))
        painter.drawLine(0, int(playable_top_y), w, int(playable_top_y))

        # Bottom border (below C4)
        painter.setPen(QPen(QColor(ACCENT_GOLD), 1.5))
        painter.drawLine(0, int(playable_bottom_y), w, int(playable_bottom_y))

        # ── Ghost notes ─────────────────────────────────────
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

        # ── Rests ───────────────────────────────────────────
        body_h = h - _HEADER_HEIGHT
        for ri, rest in enumerate(self._rests):
            rx = self._beat_to_x(rest.time_beats)
            rw = max(4.0, rest.duration_beats * self._zoom)
            if rx + rw < 0 or rx > w:
                continue
            rest_rect = QRectF(rx, _HEADER_HEIGHT, rw, body_h)
            rest_path = QPainterPath()
            rest_path.addRoundedRect(rest_rect, 1.0, 1.0)
            is_rest_selected = ri in self._selected_rest_indices
            painter.fillPath(rest_path, _REST_SELECTED_COLOR if is_rest_selected else _REST_COLOR)

        # ── Notes ───────────────────────────────────────────
        track_color = QColor(self._active_track_color)
        label_font = QFont("Microsoft JhengHei", max(7, int(nh * 0.5)))

        # Binary search optimization: only render visible notes (O(log n + k) instead of O(n))
        # Calculate visible time range with buffer for note widths
        visible_start_beat = self._x_to_beat(0.0) - 2.0  # Buffer for wide notes
        visible_end_beat = self._x_to_beat(w) + 2.0

        # Find indices of first and last potentially visible notes
        if self._notes:
            note_times = [n.time_beats for n in self._notes]
            start_idx = bisect.bisect_left(note_times, visible_start_beat)
            end_idx = bisect.bisect_right(note_times, visible_end_beat)
        else:
            start_idx = 0
            end_idx = 0

        # Iterate only through visible notes (preserving original indices for selection tracking)
        for i in range(start_idx, end_idx):
            note = self._notes[i]
            is_dragged = self._dragging and (
                i == self._drag_index or
                (len(self._selected_note_indices) > 1 and i in self._selected_note_indices)
            )
            if is_dragged:
                # Compute preview offset from drag anchor
                time_offset = self._drag_preview_time - self._drag_original_time
                pitch_offset = self._drag_preview_note - self._drag_original_note
                if i == self._drag_index:
                    x = self._beat_to_x(self._drag_preview_time)
                    y = self._y_for_note(self._drag_preview_note)
                else:
                    x = self._beat_to_x(note.time_beats + time_offset)
                    y = self._y_for_note(max(0, min(127, note.note + pitch_offset)))
            else:
                x = self._beat_to_x(note.time_beats)
                y = self._y_for_note(note.note)

            nw = max(4.0, note.duration_beats * self._zoom)

            if x + nw < 0 or x > w:
                continue

            is_selected = i in self._selected_note_indices
            note_rect = QRectF(x, y, nw, nh)
            path = QPainterPath()
            path.addRoundedRect(note_rect, _NOTE_RADIUS, _NOTE_RADIUS)

            is_flash = (
                not is_dragged
                and not is_selected
                and self._flash_beat >= 0
                and abs(note.time_beats - self._flash_beat) < 0.001
            )
            is_active = (
                not is_dragged
                and note.note in self._active_notes
                and self._playback_beats >= 0
                and note.time_beats <= self._playback_beats
                # Add a small buffer for release tolerance or overlapping notes
                and self._playback_beats < (note.time_beats + note.duration_beats + 0.1)
            )

            if is_dragged:
                # Apply zone-based coloring to dragged notes too
                if self._is_note_playable(note.note + pitch_offset if i == self._drag_index else note.note):
                    drag_c = QColor(track_color)
                else:
                    drag_c = QColor(TEXT_SECONDARY)
                drag_c.setAlpha(140)
                painter.fillPath(path, drag_c)
                painter.setPen(QPen(QColor(ACCENT), 1.5))
                painter.drawPath(path)
            elif is_active:
                # Active note glow
                painter.fillPath(path, QColor(0xFF, 0xFF, 0xFF))  # Bright white center

                # Outer glow
                glow_path = QPainterPath()
                glow_path.addRoundedRect(note_rect.adjusted(-2, -2, 2, 2), _NOTE_RADIUS+2, _NOTE_RADIUS+2)
                painter.fillPath(glow_path, QColor(ACCENT_GLOW))
            elif is_flash:
                painter.fillPath(path, QColor(ACCENT_GLOW))
                painter.setPen(QPen(QColor(0xFF, 0xFF, 0xFF, 180), 2.0))
                painter.drawPath(path)
            elif is_selected:
                painter.fillPath(path, QColor(0x40, 0xFF, 0xFF))
                painter.setPen(QPen(QColor(ACCENT), 1.5))
                painter.drawPath(path)
            else:
                # Zone-based coloring: playable (60-83) vs out-of-range
                if self._is_note_playable(note.note):
                    # Playable zone: use track color at full brightness
                    fill = QColor(track_color)
                    fill.setAlpha(200)
                else:
                    # Out-of-range: dim with TEXT_SECONDARY at 60% opacity
                    fill = QColor(TEXT_SECONDARY)
                    fill.setAlpha(int(255 * 0.6))  # 60% opacity

                painter.fillPath(path, fill)
                painter.setPen(Qt.PenStyle.NoPen)

            # Note label (render name when note is wide enough)
            if nw > 30 and nh > 8:
                semitone = note.note % 12
                octave = note.note // 12 - 1
                label = f"{_NOTE_NAMES[semitone]}{octave}"
                painter.setFont(label_font)
                if is_selected or is_dragged:
                    painter.setPen(QColor(0x0A, 0x0E, 0x14))
                else:
                    lbl_c = QColor(TEXT_PRIMARY)
                    lbl_c.setAlpha(180)
                    painter.setPen(lbl_c)
                painter.drawText(
                    note_rect.adjusted(3, 0, -1, 0),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    label,
                )

        # ── Cursor line ─────────────────────────────────────
        cx = self._beat_to_x(self._cursor_beats)
        if 0 <= cx <= w:
            painter.setPen(QPen(QColor(ACCENT), _CURSOR_WIDTH))
            painter.drawLine(int(cx), _HEADER_HEIGHT, int(cx), h)

        # ── Playback cursor ─────────────────────────────────
        if self._playback_beats >= 0:
            px = self._beat_to_x(self._playback_beats)
            if 0 <= px <= w:
                painter.setPen(QPen(QColor(0xFF, 0xFF, 0xFF, 200), 1.5))
                painter.drawLine(int(px), _HEADER_HEIGHT, int(px), h)

        # ── Range-select highlight ─────────────────────────
        if self._range_select_active:
            rs0 = self._beat_to_x(min(self._range_select_origin, self._range_select_end))
            rs1 = self._beat_to_x(max(self._range_select_origin, self._range_select_end))
            rs_rect = QRectF(rs0, _HEADER_HEIGHT, rs1 - rs0, h - _HEADER_HEIGHT)
            painter.fillRect(rs_rect, _MARQUEE_COLOR)
            painter.setPen(QPen(_MARQUEE_BORDER, 1.0, Qt.PenStyle.DashLine))
            painter.drawRect(rs_rect)

        # ── Marquee rectangle ───────────────────────────────
        if self._marquee_active:
            mx0 = min(self._marquee_start.x(), self._marquee_end.x())
            my0 = min(self._marquee_start.y(), self._marquee_end.y())
            mx1 = max(self._marquee_start.x(), self._marquee_end.x())
            my1 = max(self._marquee_start.y(), self._marquee_end.y())
            m_rect = QRectF(mx0, my0, mx1 - mx0, my1 - my0)
            painter.fillRect(m_rect, _MARQUEE_COLOR)
            painter.setPen(QPen(_MARQUEE_BORDER, 1.0, Qt.PenStyle.DashLine))
            painter.drawRect(m_rect)

        painter.end()
