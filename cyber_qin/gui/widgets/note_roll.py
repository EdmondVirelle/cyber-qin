"""Beat-based piano roll timeline for the editor.

Displays notes as colored rounded rectangles, rests as red translucent bars,
ghost notes from inactive tracks, cursor as a cyan vertical line,
beat grid with bar lines, horizontal scroll and zoom.

Supports multi-select (Shift+drag marquee, Ctrl+click), batch drag,
note resize (right-edge drag), note labels, and snap-to-grid.
"""

from __future__ import annotations

import bisect
from enum import Enum

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QWheelEvent
from PyQt6.QtWidgets import QWidget

from ...core.constants import (
    EDITOR_MIDI_MAX,
    EDITOR_MIDI_MIN,
    PLAYABLE_MIDI_MAX,
    PLAYABLE_MIDI_MIN,
)
from ..theme import (
    ACCENT,
    ACCENT_GLOW,
    ACCENT_GOLD,
    BG_INK,
    BG_SCROLL,
    DIVIDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

# Visual constants
_PIXELS_PER_BEAT = 80.0  # default zoom (pixels per beat)
_MIN_ZOOM = 20.0
_MAX_ZOOM = 400.0
_NOTE_RADIUS = 2.5
_CURSOR_WIDTH = 2.0
_HEADER_HEIGHT = 22  # bar number header
_RESIZE_THRESHOLD = 6  # pixels from right edge to trigger resize
_VELOCITY_LANE_HEIGHT = 80  # velocity lane height in pixels
_MINIMAP_HEIGHT = 30  # timeline minimap height in pixels

# Pitch (vertical) zoom constants
_MIN_PITCH_RANGE = 12  # Minimum visible range (1 octave)
_MAX_PITCH_RANGE = 88  # Maximum visible range (full piano)

# Grid line colors
_BAR_LINE_COLOR = "#3A4050"
_BEAT_LINE_COLOR = "#2A3040"
_SUB_LINE_COLOR = "#1E2530"

# Rest color
_REST_COLOR = QColor(0xFF, 0x44, 0x44, 64)  # red 25% alpha
_REST_SELECTED_COLOR = QColor(0xFF, 0x66, 0x66, 128)  # red 50% alpha

# Selection marquee (Gold accent)
_MARQUEE_COLOR = QColor(0xD4, 0xAF, 0x37, 40)  # Gold 15% alpha
_MARQUEE_BORDER = QColor(0xD4, 0xAF, 0x37, 180)  # Gold 70% alpha

# Note names for labels
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class FollowMode(Enum):
    """Playback cursor auto-follow behavior modes."""

    OFF = 0  # No auto-scroll
    PAGE = 1  # Jump by page when cursor leaves view
    CONTINUOUS = 2  # Keep cursor centered (timeline scrolls)
    SMART = 3  # Current 80%/20% threshold mode (default)


class NoteRoll(QWidget):
    """Beat-based horizontal timeline showing notes, rests, and cursor."""

    note_selected = pyqtSignal(int)  # note index
    note_deleted = pyqtSignal(int)  # note index
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

    # Zoom changed
    zoom_changed = pyqtSignal(float)  # new zoom level (pixels per beat)

    # Notes changed (for velocity batch editing, etc.)
    notes_changed = pyqtSignal()  # notes have been modified

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._notes: list = []  # list of BeatNote
        self._rests: list = []  # list of BeatRest
        self._ghost_notes: list = []  # notes from other tracks (BeatNote with .color)
        self._cursor_beats: float = 0.0
        self._playback_beats: float = -1.0  # playback cursor, -1 = hidden
        self._scroll_x: float = 0.0
        self._zoom: float = _PIXELS_PER_BEAT
        self._pitch_range: int = _MAX_PITCH_RANGE  # Visible MIDI note range (88 = all keys)
        self._midi_min: int = EDITOR_MIDI_MIN  # 21 (A0)
        self._midi_max: int = EDITOR_MIDI_MAX  # 108 (C8)
        self._tempo_bpm: float = 120.0
        self._beats_per_bar: float = 4.0
        self._active_track_color: str = "#D4AF37"  # Qin Gold (Cyber Ink theme)

        # Multi-select state
        self._selected_note_indices: set[int] = set()
        self._selected_rest_indices: set[int] = set()

        # Active notes (for playback feedback)
        self._active_notes: set[int] = set()  # set of MIDI pitch values

        # Snap
        self._snap_enabled: bool = True
        self._grid_precision: int = 32  # 1/32 note precision (4, 8, 16, or 32)

        # Playback follow mode
        self._follow_mode: FollowMode = FollowMode.SMART  # Default to smart mode

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
        self._range_select_origin: float = 0.0  # beat of initial click
        self._range_select_end: float = 0.0  # beat of current drag
        self._empty_press_pos: QPointF = QPointF()

        # Pencil (draw) mode
        self._pencil_mode: bool = False

        # Velocity lane drag state
        self._velocity_dragging: bool = False
        self._velocity_drag_index: int = -1
        self._velocity_drag_start_y: float = 0.0

        # Velocity batch editing state (Shift+drag to draw curves)
        self._velocity_batch_editing: bool = False
        self._velocity_batch_start_x: float = 0.0
        self._velocity_batch_start_y: float = 0.0
        self._velocity_batch_end_x: float = 0.0
        self._velocity_batch_end_y: float = 0.0

        # Auto-scroll during drag
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.setInterval(50)
        self._auto_scroll_timer.timeout.connect(self._on_auto_scroll)
        self._last_mouse_x: float = 0.0

        self.setMinimumHeight(120)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Tooltip for playable zone
        self.setToolTip(
            "黃色區域：燕雲十六聲 36 鍵可用範圍 (C4-B5)\n"
            "在此範圍內的音符可以在遊戲中彈奏\n"
            "Yellow Zone: WWM 36-key playable range (C4-B5)\n\n"
            "操作：\n"
            "- 左鍵拖曳：選取音符\n"
            "- 鉛筆模式：點擊新增音符\n"
            "- Delete：刪除選取的音符\n"
            "- 滾輪：垂直捲動 / Shift+滾輪：水平捲動"
        )

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

    def set_grid_precision(self, precision: int) -> None:
        """Set grid precision: 4=1/4 note, 8=1/8, 16=1/16, 32=1/32, 64=1/64, 128=1/128."""
        if precision in (4, 8, 16, 32, 64, 128):
            self._grid_precision = precision
            self.update()

    def set_zoom(self, zoom: float) -> None:
        """Set horizontal zoom level (pixels per beat)."""
        self._zoom = max(_MIN_ZOOM, min(_MAX_ZOOM, zoom))
        self.update()

    def set_follow_mode(self, mode: FollowMode) -> None:
        """Set playback cursor auto-follow mode."""
        self._follow_mode = mode

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
        """Auto-scroll to keep cursor visible based on follow mode."""
        if self._follow_mode == FollowMode.OFF:
            # No auto-scroll
            return

        cursor_px = self._cursor_beats * self._zoom
        visible_w = self.width()

        if self._follow_mode == FollowMode.PAGE:
            # Jump by page when cursor leaves view
            if cursor_px < self._scroll_x or cursor_px > self._scroll_x + visible_w:
                self._scroll_x = max(0, cursor_px - visible_w * 0.2)

        elif self._follow_mode == FollowMode.CONTINUOUS:
            # Keep cursor centered (timeline scrolls continuously)
            self._scroll_x = max(0, cursor_px - visible_w * 0.5)

        elif self._follow_mode == FollowMode.SMART:
            # Original 80%/20% threshold mode
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
        body_h = self.height() - _MINIMAP_HEIGHT - _HEADER_HEIGHT - _VELOCITY_LANE_HEIGHT
        note_h = body_h / max(1, range_size)
        offset = self._midi_max - midi_note
        return _MINIMAP_HEIGHT + _HEADER_HEIGHT + offset * note_h

    def _y_to_note(self, y: float) -> int:
        """Convert Y pixel position to MIDI note number."""
        range_size = self._midi_max - self._midi_min + 1
        body_h = self.height() - _MINIMAP_HEIGHT - _HEADER_HEIGHT - _VELOCITY_LANE_HEIGHT
        note_h = body_h / max(1, range_size)
        offset = (y - _MINIMAP_HEIGHT - _HEADER_HEIGHT) / max(1.0, note_h)
        return max(self._midi_min, min(self._midi_max, int(self._midi_max - offset)))

    def _update_pitch_bounds(self, center: int) -> None:
        """Update visible MIDI range based on pitch zoom centered on given note."""
        half_range = self._pitch_range // 2
        new_min = max(EDITOR_MIDI_MIN, center - half_range)
        new_max = min(EDITOR_MIDI_MAX, center + half_range)

        # Adjust if we hit the boundaries
        if new_max - new_min + 1 < self._pitch_range:
            if new_min == EDITOR_MIDI_MIN:
                new_max = min(EDITOR_MIDI_MAX, new_min + self._pitch_range - 1)
            elif new_max == EDITOR_MIDI_MAX:
                new_min = max(EDITOR_MIDI_MIN, new_max - self._pitch_range + 1)

        self._midi_min = new_min
        self._midi_max = new_max

    def _note_height(self) -> float:
        range_size = self._midi_max - self._midi_min + 1
        body_h = self.height() - _MINIMAP_HEIGHT - _HEADER_HEIGHT - _VELOCITY_LANE_HEIGHT
        return max(4.0, body_h / max(1, range_size) * 0.85)

    def _snap_beat(self, beat: float) -> float:
        """Snap beat to grid if snap is enabled."""
        if not self._snap_enabled:
            return beat
        # Snap to nearest sub-beat based on user-selected precision.
        # Grid precision is fixed and does not change with zoom level.
        #   precision=4  → 1/4 note   (1.0 beats)
        #   precision=8  → 1/8 note   (0.5 beats)
        #   precision=16 → 1/16 note  (0.25 beats)
        #   precision=32 → 1/32 note  (0.125 beats)
        grid = 4.0 / self._grid_precision  # Convert precision to beat fraction
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
            # Check if clicking in minimap
            if pos.y() < _MINIMAP_HEIGHT:
                self._handle_minimap_click(pos)
                return

            # Check if clicking in velocity lane
            h = self.height()
            lane_top = h - _VELOCITY_LANE_HEIGHT
            if pos.y() >= lane_top:
                if shift:
                    # Shift+drag: batch velocity editing (draw curves)
                    self._velocity_batch_editing = True
                    self._velocity_batch_start_x = pos.x()
                    self._velocity_batch_start_y = pos.y()
                    self._velocity_batch_end_x = pos.x()
                    self._velocity_batch_end_y = pos.y()
                else:
                    # Normal click: single note velocity editing
                    self._handle_velocity_lane_press(pos)
                return

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

        # Velocity batch editing (Shift+drag to draw curves)
        if self._velocity_batch_editing:
            self._velocity_batch_end_x = pos.x()
            self._velocity_batch_end_y = pos.y()
            self.update()
            return

        # Velocity drag
        if self._velocity_dragging:
            h = self.height()
            lane_top = h - _VELOCITY_LANE_HEIGHT
            y_rel = pos.y() - lane_top
            # Calculate new velocity (inverted: top = 127, bottom = 1)
            new_velocity = int(127 * (1 - y_rel / _VELOCITY_LANE_HEIGHT))
            new_velocity = max(1, min(127, new_velocity))
            # Update note velocity
            if 0 <= self._velocity_drag_index < len(self._notes):
                self._notes[self._velocity_drag_index].velocity = new_velocity
                self.notes_changed.emit()
            self.update()
            return

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
        if (
            not self._dragging
            and not self._resizing
            and not self._marquee_active
            and self._drag_index < 0
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
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
            # Velocity batch editing release
            if self._velocity_batch_editing:
                self._apply_velocity_gradient()
                self._velocity_batch_editing = False
                self.update()
                return

            # Velocity drag release
            if self._velocity_dragging:
                self._velocity_dragging = False
                self._velocity_drag_index = -1
                self.update()
                return

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
                            sorted(self._selected_note_indices),
                            time_delta,
                            pitch_delta,
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

        body_h = self.height() - _MINIMAP_HEIGHT - _HEADER_HEIGHT - _VELOCITY_LANE_HEIGHT
        for i, rest in enumerate(self._rests):
            rx = self._beat_to_x(rest.time_beats)
            rw = max(4.0, rest.duration_beats * self._zoom)
            rest_rect = QRectF(rx, _MINIMAP_HEIGHT + _HEADER_HEIGHT, rw, body_h)
            if rest_rect.intersects(sel_rect):
                self._selected_rest_indices.add(i)

        self._emit_selection_changed()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        key = event.key()

        # Zoom shortcuts
        if ctrl and shift:
            # Vertical pitch zoom (Ctrl+Shift+=/-, Ctrl+Shift+0)
            if key in (Qt.Key.Key_Equal, Qt.Key.Key_Plus):
                # Zoom in vertically (reduce range)
                new_range = int(self._pitch_range * 0.85)
                new_range = max(_MIN_PITCH_RANGE, new_range)
                if new_range != self._pitch_range:
                    center = (self._midi_min + self._midi_max) // 2
                    self._pitch_range = new_range
                    self._update_pitch_bounds(center)
                    self.update()
                return
            if key == Qt.Key.Key_Minus:
                # Zoom out vertically (increase range)
                new_range = int(self._pitch_range / 0.85)
                new_range = min(_MAX_PITCH_RANGE, new_range)
                if new_range != self._pitch_range:
                    center = (self._midi_min + self._midi_max) // 2
                    self._pitch_range = new_range
                    self._update_pitch_bounds(center)
                    self.update()
                return
            if key == Qt.Key.Key_0:
                # Reset vertical zoom
                if self._pitch_range != _MAX_PITCH_RANGE:
                    self._pitch_range = _MAX_PITCH_RANGE
                    self._midi_min = EDITOR_MIDI_MIN
                    self._midi_max = EDITOR_MIDI_MAX
                    self.update()
                return
        elif ctrl:
            # Horizontal zoom (Ctrl+=/-, Ctrl+0)
            if key in (Qt.Key.Key_Equal, Qt.Key.Key_Plus):
                # Zoom in
                self._zoom = min(_MAX_ZOOM, self._zoom * 1.15)
                self.zoom_changed.emit(self._zoom)
                self.update()
                return
            if key == Qt.Key.Key_Minus:
                # Zoom out
                self._zoom = max(_MIN_ZOOM, self._zoom / 1.15)
                self.zoom_changed.emit(self._zoom)
                self.update()
                return
            if key == Qt.Key.Key_0:
                # Reset zoom
                self._zoom = _PIXELS_PER_BEAT
                self.zoom_changed.emit(self._zoom)
                self.update()
                return

        # Scroll shortcuts (Ctrl+arrows)
        if ctrl:
            if key == Qt.Key.Key_Left:
                # Scroll left
                self._scroll_x = max(0, self._scroll_x - 40)
                self.update()
                return
            if key == Qt.Key.Key_Right:
                # Scroll right
                self._scroll_x += 40
                self.update()
                return

        # Home/End navigation
        if key == Qt.Key.Key_Home:
            self._scroll_x = 0
            self.update()
            return
        if key == Qt.Key.Key_End:
            if self._notes:
                last_beat = max(n.time_beats + n.duration_beats for n in self._notes)
                self._scroll_x = max(0, last_beat * self._zoom - self.width() * 0.8)
            self.update()
            return

        # Delete key
        if key == Qt.Key.Key_Delete:
            if self._selected_note_indices or self._selected_rest_indices:
                # Delete all selected — handled by EditorView via selection_changed
                self.note_deleted.emit(-1)  # signal to EditorView to delete selection
            elif len(self._selected_note_indices) == 0:
                pass

        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent | None) -> None:  # noqa: N802, type: ignore[override]
        if event is None:
            return

        delta = event.angleDelta().y()
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if ctrl and shift:
            # Vertical pitch zoom (Ctrl+Shift+Wheel)
            # Zoom in = smaller range, zoom out = larger range
            zoom_factor = 0.85 if delta > 0 else 1 / 0.85
            new_range = int(self._pitch_range * zoom_factor)
            new_range = max(_MIN_PITCH_RANGE, min(_MAX_PITCH_RANGE, new_range))

            if new_range != self._pitch_range:
                # Calculate center note based on mouse Y position
                mouse_note = self._y_to_note(event.position().y())
                self._pitch_range = new_range
                self._update_pitch_bounds(mouse_note)
        elif ctrl:
            # Horizontal zoom (Ctrl+Wheel)
            factor = 1.15 if delta > 0 else 1 / 1.15
            mouse_beat = self._x_to_beat(event.position().x())
            old_zoom = self._zoom
            self._zoom = max(_MIN_ZOOM, min(_MAX_ZOOM, self._zoom * factor))
            new_x = mouse_beat * self._zoom - event.position().x()
            self._scroll_x = max(0.0, new_x)
            if abs(self._zoom - old_zoom) > 0.1:
                self.zoom_changed.emit(self._zoom)
        else:
            # Horizontal scroll (plain Wheel)
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

        # ── Minimap ─────────────────────────────────────────
        self._draw_minimap(painter, w, h)

        # Header background
        painter.fillRect(0, _MINIMAP_HEIGHT, w, _HEADER_HEIGHT, QColor(BG_SCROLL))

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
            painter.drawLine(int(x), _MINIMAP_HEIGHT + _HEADER_HEIGHT, int(x), h)

            if is_bar and bpb > 0:
                painter.setPen(QColor(TEXT_SECONDARY))
                bar_num = int(beat_num / bpb) + 1
                painter.drawText(
                    int(x + 3),
                    _MINIMAP_HEIGHT + 2,
                    40,
                    _HEADER_HEIGHT - 2,
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
                    painter.drawLine(int(sx), _MINIMAP_HEIGHT + _HEADER_HEIGHT, int(sx), h)

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
            gc = QColor(getattr(gn, "_ghost_color", "#888888"))
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
                i == self._drag_index
                or (len(self._selected_note_indices) > 1 and i in self._selected_note_indices)
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
                if self._is_note_playable(
                    note.note + pitch_offset if i == self._drag_index else note.note
                ):
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
                glow_path.addRoundedRect(
                    note_rect.adjusted(-2, -2, 2, 2), _NOTE_RADIUS + 2, _NOTE_RADIUS + 2
                )
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
                # Alpha encodes velocity (64-255 range for visibility)
                velocity_alpha = int(64 + (note.velocity / 127.0) * 191)

                if self._is_note_playable(note.note):
                    # Playable zone: use track color with velocity-based brightness
                    fill = QColor(track_color)
                    fill.setAlpha(velocity_alpha)
                else:
                    # Out-of-range: dim with TEXT_SECONDARY, still velocity-aware
                    fill = QColor(TEXT_SECONDARY)
                    fill.setAlpha(int(velocity_alpha * 0.6))  # 60% of velocity alpha

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
            painter.drawLine(int(cx), _MINIMAP_HEIGHT + _HEADER_HEIGHT, int(cx), h)

        # ── Playback cursor ─────────────────────────────────
        if self._playback_beats >= 0:
            px = self._beat_to_x(self._playback_beats)
            if 0 <= px <= w:
                painter.setPen(QPen(QColor(0xFF, 0xFF, 0xFF, 200), 1.5))
                painter.drawLine(int(px), _MINIMAP_HEIGHT + _HEADER_HEIGHT, int(px), h)

        # ── Range-select highlight ─────────────────────────
        if self._range_select_active:
            rs0 = self._beat_to_x(min(self._range_select_origin, self._range_select_end))
            rs1 = self._beat_to_x(max(self._range_select_origin, self._range_select_end))
            body_top = _MINIMAP_HEIGHT + _HEADER_HEIGHT
            rs_rect = QRectF(rs0, body_top, rs1 - rs0, h - body_top)
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

        # ── Velocity Lane ───────────────────────────────────
        self._draw_velocity_lane(painter, w, h)

        painter.end()

    def _draw_velocity_lane(self, painter: QPainter, w: int, h: int) -> None:
        """Draw velocity bars in dedicated lane below piano roll."""
        lane_top = h - _VELOCITY_LANE_HEIGHT

        # Background
        painter.fillRect(0, lane_top, w, _VELOCITY_LANE_HEIGHT, QColor(BG_SCROLL))

        # Top separator line
        painter.setPen(QPen(QColor(DIVIDER), 1))
        painter.drawLine(0, lane_top, w, lane_top)

        # Grid lines (match main grid)
        bpb = self._beats_per_bar if self._beats_per_bar > 0 else 4.0
        first_beat = max(0, int(self._scroll_x / self._zoom) - 1)
        last_beat = int((self._scroll_x + w) / self._zoom) + 2

        for beat_num in range(first_beat, last_beat):
            x = self._beat_to_x(float(beat_num))
            if x < -10 or x > w + 10:
                continue

            is_bar = abs(beat_num % bpb) < 0.001
            if is_bar:
                painter.setPen(QPen(QColor(_BAR_LINE_COLOR), 0.8))
            else:
                painter.setPen(QPen(QColor(_BEAT_LINE_COLOR), 0.3))
            painter.drawLine(int(x), lane_top, int(x), h)

        # Draw velocity bars for visible notes (with binary search optimization)
        track_color = QColor(self._active_track_color)

        # Calculate visible beat range
        first_visible_beat = self._x_to_beat(0)
        last_visible_beat = self._x_to_beat(w)

        # Binary search: find first note that starts before or at last_visible_beat
        # Notes are sorted by time_beats, so we can use bisect
        if not self._notes:
            return

        # Find the insertion point for first_visible_beat
        # We need to check notes starting a bit earlier to catch long notes
        search_beat = max(0, first_visible_beat - 16)  # Look back up to 16 beats
        start_idx = bisect.bisect_left(
            self._notes, search_beat, key=lambda n: n.time_beats + n.duration_beats
        )

        # Iterate only through potentially visible notes
        for i in range(start_idx, len(self._notes)):
            note = self._notes[i]

            # Early exit: if note starts after visible range, we're done
            if note.time_beats > last_visible_beat:
                break

            x = self._beat_to_x(note.time_beats)
            nw = max(4.0, note.duration_beats * self._zoom)

            if x + nw < 0 or x > w:  # Additional pixel-level culling
                continue

            # Bar height = velocity ratio
            bar_height = (note.velocity / 127.0) * (_VELOCITY_LANE_HEIGHT - 10)
            bar_y = lane_top + _VELOCITY_LANE_HEIGHT - bar_height - 5

            # Color: track color with alpha based on velocity
            color = QColor(track_color)
            color.setAlpha(int(100 + (note.velocity / 127.0) * 155))

            # Draw bar
            bar_width = max(3, nw - 1)
            painter.fillRect(QRectF(x, bar_y, bar_width, bar_height), color)

            # Selected note: add gold border
            if i in self._selected_note_indices:
                painter.setPen(QPen(QColor(ACCENT_GOLD), 2))
                painter.drawRect(QRectF(x, bar_y, bar_width, bar_height))

            # Velocity label (show when wide enough)
            if nw > 25:
                painter.setFont(QFont("Microsoft JhengHei", 7))
                painter.setPen(QColor(TEXT_SECONDARY))
                painter.drawText(
                    QRectF(x, lane_top + 2, bar_width, 12),
                    Qt.AlignmentFlag.AlignCenter,
                    str(note.velocity),
                )

        # Draw batch editing gradient line preview
        if self._velocity_batch_editing:
            painter.setPen(QPen(QColor(ACCENT_GOLD), 3))
            painter.drawLine(
                int(self._velocity_batch_start_x),
                int(self._velocity_batch_start_y),
                int(self._velocity_batch_end_x),
                int(self._velocity_batch_end_y),
            )
            # Draw circles at start/end points
            painter.setBrush(QColor(ACCENT_GOLD))
            painter.drawEllipse(
                QRectF(
                    self._velocity_batch_start_x - 4,
                    self._velocity_batch_start_y - 4,
                    8,
                    8,
                )
            )
            painter.drawEllipse(
                QRectF(
                    self._velocity_batch_end_x - 4,
                    self._velocity_batch_end_y - 4,
                    8,
                    8,
                )
            )

    def _draw_minimap(self, painter: QPainter, w: int, h: int) -> None:
        """Draw timeline minimap showing overview of all notes."""
        # Background
        painter.fillRect(0, 0, w, _MINIMAP_HEIGHT, QColor(BG_SCROLL))

        # Bottom border
        painter.setPen(QPen(QColor(DIVIDER), 1))
        painter.drawLine(0, _MINIMAP_HEIGHT - 1, w, _MINIMAP_HEIGHT - 1)

        if not self._notes:
            return

        # Calculate total duration to fit all notes
        max_beat = max(n.time_beats + n.duration_beats for n in self._notes)
        if max_beat <= 0:
            return

        # Minimap zoom: fit all content into width
        minimap_zoom = (w - 4) / max_beat  # 2px margin on each side

        # Draw all notes in compressed form
        track_color = QColor(self._active_track_color)
        track_color.setAlpha(180)

        for note in self._notes:
            mx = 2 + note.time_beats * minimap_zoom
            mw = max(1, note.duration_beats * minimap_zoom)

            # Simplified pitch: map MIDI range to minimap height
            pitch_ratio = (note.note - EDITOR_MIDI_MIN) / max(1, EDITOR_MIDI_MAX - EDITOR_MIDI_MIN)
            my = 2 + (_MINIMAP_HEIGHT - 6) * (1 - pitch_ratio)
            mh = 2  # Fixed height for minimap notes

            painter.fillRect(QRectF(mx, my, mw, mh), track_color)

        # Draw viewport indicator (current visible range)
        viewport_start = self._scroll_x / self._zoom
        viewport_end = (self._scroll_x + w) / self._zoom
        vx_start = 2 + viewport_start * minimap_zoom
        vx_end = 2 + viewport_end * minimap_zoom
        vx_width = vx_end - vx_start

        # Viewport rectangle (semi-transparent white overlay)
        viewport_rect = QRectF(vx_start, 1, vx_width, _MINIMAP_HEIGHT - 2)
        painter.fillRect(viewport_rect, QColor(255, 255, 255, 30))
        painter.setPen(QPen(QColor(ACCENT_GOLD), 1.5))
        painter.drawRect(viewport_rect)

    def _apply_velocity_gradient(self) -> None:
        """Apply velocity gradient to notes in the batch edit range."""
        if not self._notes:
            return

        h = self.height()
        lane_top = h - _VELOCITY_LANE_HEIGHT

        # Calculate start and end velocities from Y positions
        start_vel = int(127 * (1 - (self._velocity_batch_start_y - lane_top) / _VELOCITY_LANE_HEIGHT))
        end_vel = int(127 * (1 - (self._velocity_batch_end_y - lane_top) / _VELOCITY_LANE_HEIGHT))
        start_vel = max(1, min(127, start_vel))
        end_vel = max(1, min(127, end_vel))

        # Calculate time range
        start_beat = self._x_to_beat(min(self._velocity_batch_start_x, self._velocity_batch_end_x))
        end_beat = self._x_to_beat(max(self._velocity_batch_start_x, self._velocity_batch_end_x))

        # Find notes in range and apply gradient
        notes_in_range = []
        for i, note in enumerate(self._notes):
            note_center = note.time_beats + note.duration_beats * 0.5
            if start_beat <= note_center <= end_beat:
                notes_in_range.append((i, note_center))

        if not notes_in_range:
            return

        # Apply linear gradient
        for i, note_center in notes_in_range:
            # Calculate interpolation factor (0 to 1)
            if abs(end_beat - start_beat) > 0.001:
                t = (note_center - start_beat) / (end_beat - start_beat)
            else:
                t = 0.5

            # Linear interpolation
            new_velocity = int(start_vel + (end_vel - start_vel) * t)
            new_velocity = max(1, min(127, new_velocity))
            self._notes[i].velocity = new_velocity

        # Emit signal to notify sequence of changes
        self.notes_changed.emit()

    def _handle_minimap_click(self, pos: QPointF) -> None:
        """Handle mouse click in minimap to jump to position."""
        if not self._notes:
            return

        # Calculate total duration
        max_beat = max(n.time_beats + n.duration_beats for n in self._notes)
        if max_beat <= 0:
            return

        # Convert click X to beat position (account for 2px margin)
        w = self.width()
        minimap_zoom = (w - 4) / max_beat
        click_beat = (pos.x() - 2) / minimap_zoom

        # Center viewport on clicked beat
        viewport_width_beats = w / self._zoom
        target_scroll_x = (click_beat - viewport_width_beats * 0.5) * self._zoom
        self._scroll_x = max(0, target_scroll_x)
        self.update()

    def _handle_velocity_lane_press(self, pos: QPointF) -> None:
        """Handle mouse press in velocity lane."""
        beat = self._x_to_beat(pos.x())

        # Find note at this beat position
        for i, note in enumerate(self._notes):
            if note.time_beats <= beat < note.time_beats + note.duration_beats:
                # Start velocity drag
                self._velocity_dragging = True
                self._velocity_drag_index = i
                self._velocity_drag_start_y = pos.y()
                # Select this note
                self._selected_note_indices = {i}
                self._selected_rest_indices.clear()
                self._emit_selection_changed()
                return
