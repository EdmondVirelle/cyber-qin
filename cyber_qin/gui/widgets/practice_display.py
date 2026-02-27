"""Falling-note rhythm game display for practice mode — 60fps QPainter rendering.

Features a lane-based layout like osu!mania / DJMAX where each unique note
in the song gets its own column. Notes fall down their lane toward the hit line.
3D perspective effect converges lanes toward a vanishing point.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import QWidget

from ...core.constants import Modifier
from ...core.practice_engine import HitGrade, PracticeNote

# ── Perspective Geometry ─────────────────────────────────────
_HIT_LINE_Y_RATIO = 0.85  # Hit line at 85% from top
_VANISH_Y_RATIO = 0.06  # Vanishing point at 6% from top
_LANE_MARGIN = 30  # Horizontal margin at hit line level

# ── Note Sizing ──────────────────────────────────────────────
_NOTE_HEIGHT = 18
_NOTE_LANE_FILL = 0.72  # Note width = lane_width * this ratio
_FALL_SPEED = 300.0  # pixels per second (base)

# ── Lane visuals ─────────────────────────────────────────────
_LANE_BG_EVEN = QColor(10, 16, 28, 140)
_LANE_BG_ODD = QColor(14, 22, 36, 140)
_LANE_DIVIDER_COLOR = QColor(30, 50, 75, 100)
_LANE_LABEL_BG = QColor(8, 14, 24, 200)
_LANE_LABEL_HEIGHT = 36  # pixels below hit line for label area

# ── Timing & Effects ────────────────────────────────────────
_FEEDBACK_DURATION = 1.0  # seconds — grade text display time
_FLASH_DURATION = 0.25  # seconds — bright glow on hit
_HIT_ZONE_HEIGHT = 20  # Glowing hit zone half-height

# ── Colors ──────────────────────────────────────────────────
_NOTE_COLOR = QColor("#00F0FF")
_NOTE_BORDER = QColor("#00A0B0")
_HIT_LINE_COLOR = QColor("#D4AF37")
_MISS_COLOR = QColor("#FF4444")
_GOOD_COLOR = QColor("#FFBB33")
_GREAT_COLOR = QColor("#33FF55")
_PERFECT_COLOR = QColor("#D4AF37")
_COMBO_COLOR = QColor("#D4AF37")

_GRADE_COLORS = {
    HitGrade.MISS: _MISS_COLOR,
    HitGrade.GOOD: _GOOD_COLOR,
    HitGrade.GREAT: _GREAT_COLOR,
    HitGrade.PERFECT: _PERFECT_COLOR,
}

_GRADE_TEXT = {
    HitGrade.MISS: "MISS",
    HitGrade.GOOD: "GOOD",
    HitGrade.GREAT: "GREAT!",
    HitGrade.PERFECT: "PERFECT!",
}

# ── Note name helper ─────────────────────────────────────────
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _midi_note_name(midi: int) -> str:
    return _NOTE_NAMES[midi % 12] + str(midi // 12 - 1)


class _FeedbackEffect:
    """Floating grade text that pops in and fades out."""

    __slots__ = ("text", "color", "x", "y", "life", "initial_life")

    def __init__(self, text: str, color: QColor, x: float, y: float) -> None:
        self.text = text
        self.color = color
        self.x = x
        self.y = y
        self.life = _FEEDBACK_DURATION
        self.initial_life = _FEEDBACK_DURATION


class _FlashEffect:
    """Brief bright glow at the hit line when a note is hit."""

    __slots__ = ("x", "color", "life", "lane_left", "lane_right")

    def __init__(
        self, x: float, color: QColor, lane_left: float = 0, lane_right: float = 0
    ) -> None:
        self.x = x
        self.color = color
        self.life = _FLASH_DURATION
        self.lane_left = lane_left
        self.lane_right = lane_right


_CONSUMED_DURATION = 0.3  # seconds — consumed note burst animation


class _ConsumedNoteEffect:
    """Expanding bright burst when a note is successfully hit."""

    __slots__ = ("x", "y", "color", "life", "width")

    def __init__(self, x: float, y: float, color: QColor, width: float) -> None:
        self.x = x
        self.y = y
        self.color = color
        self.life = _CONSUMED_DURATION
        self.width = width


class PracticeDisplay(QWidget):
    """Lane-based falling notes display (osu!mania style) with 3D perspective."""

    note_hit = pyqtSignal(int, float)  # note, time_seconds — emitted on user input
    practice_finished = pyqtSignal()  # emitted when all notes have passed

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._notes: list[PracticeNote] = []
        self._current_time: float = 0.0
        self._playing: bool = False
        self._tempo_bpm: float = 120.0
        self._speed: float = 1.0
        self._feedbacks: list[_FeedbackEffect] = []
        self._flashes: list[_FlashEffect] = []
        self._consumed_effects: list[_ConsumedNoteEffect] = []
        self._hit_note_times: set[float] = set()
        self._combo: int = 0

        # Lane system: only notes that appear in the song get lanes
        self._lane_notes: list[int] = []  # sorted unique MIDI notes
        self._lane_index: dict[int, int] = {}  # MIDI note → lane index

        # Keyboard input mode
        self._reverse_map: dict[tuple[str, Modifier], int] | None = None
        self._key_labels: dict[int, str] | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60fps
        self._timer.timeout.connect(self._tick)

        self.setMinimumHeight(300)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ── Public API ──────────────────────────────────────────

    def set_notes(self, notes: list[PracticeNote], tempo_bpm: float = 120.0) -> None:
        self._notes = sorted(notes, key=lambda n: n.time_seconds)
        self._tempo_bpm = tempo_bpm
        # Build lane system from unique notes in the song
        if notes:
            unique = sorted({n.note for n in notes})
            self._lane_notes = unique
            self._lane_index = {note: i for i, note in enumerate(unique)}
        else:
            self._lane_notes = []
            self._lane_index = {}
        self.update()

    def set_speed(self, speed: float) -> None:
        """Set playback speed multiplier (affects song-time advancement)."""
        self._speed = speed

    def set_combo(self, combo: int) -> None:
        """Update the current combo count for overlay display."""
        self._combo = combo

    def start(self) -> None:
        self._current_time = -1.0  # 1 second lead-in
        self._playing = True
        self._feedbacks.clear()
        self._flashes.clear()
        self._consumed_effects.clear()
        self._hit_note_times.clear()
        self._combo = 0
        self._timer.start()

    def stop(self) -> None:
        self._playing = False
        self._timer.stop()
        self.update()

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def current_time(self) -> float:
        return self._current_time

    def show_feedback(
        self,
        grade: HitGrade,
        note: int,
        target_time: float | None = None,
    ) -> None:
        """Show hit grade visual feedback and mark note as consumed."""
        x = self._note_to_x(note)
        hit_y = self.height() * _HIT_LINE_Y_RATIO
        color = _GRADE_COLORS.get(grade, _MISS_COLOR)
        text = _GRADE_TEXT.get(grade, "")
        self._feedbacks.append(_FeedbackEffect(text, color, x, hit_y - 60))
        # Bright flash at hit line for non-miss hits
        if grade != HitGrade.MISS:
            ll, lr = self._lane_edges(note)
            self._flashes.append(_FlashEffect(x, color, ll, lr))
            # Mark note consumed + burst effect
            note_w = self._lane_width() * _NOTE_LANE_FILL if self._lane_notes else 36
            if target_time is not None:
                self._hit_note_times.add(target_time)
                self._consumed_effects.append(
                    _ConsumedNoteEffect(x, hit_y, color, note_w),
                )

    def set_keyboard_mapping(self, reverse_map: dict[tuple[str, Modifier], int] | None) -> None:
        """Enable or disable keyboard input for practice."""
        self._reverse_map = reverse_map
        if reverse_map is not None:
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.setFocus()

    def set_key_labels(self, labels: dict[int, str] | None) -> None:
        """Set key label overlay (e.g. 'Z', 'Shift+A') for lane display."""
        self._key_labels = labels
        self.update()

    # ── Keyboard Input ──────────────────────────────────────

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.isAutoRepeat() or not self._playing or self._reverse_map is None:
            super().keyPressEvent(event)
            return

        key_code = event.key()
        if 65 <= key_code <= 90:  # A-Z
            key_letter = chr(key_code)
        elif 48 <= key_code <= 57:  # 0-9
            key_letter = chr(key_code)
        else:
            super().keyPressEvent(event)
            return

        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ShiftModifier:
            mod = Modifier.SHIFT
        elif mods & Qt.KeyboardModifier.ControlModifier:
            mod = Modifier.CTRL
        else:
            mod = Modifier.NONE

        midi_note = self._reverse_map.get((key_letter, mod))
        if midi_note is not None:
            self.note_hit.emit(midi_note, self._current_time)

    # ── Lane Geometry ─────────────────────────────────────────

    def _lane_width(self) -> float:
        """Width of a single lane at hit-line level."""
        n = len(self._lane_notes)
        if n == 0:
            return 60.0
        usable = self.width() - 2 * _LANE_MARGIN
        return usable / n

    def _note_to_x(self, midi_note: int) -> float:
        """Map MIDI note to the center x of its lane (at hit-line level)."""
        idx = self._lane_index.get(midi_note)
        if idx is None:
            # Fallback: spread unknown notes across width
            w = self.width()
            return w / 2.0
        lw = self._lane_width()
        return _LANE_MARGIN + (idx + 0.5) * lw

    def _lane_edges(self, midi_note: int) -> tuple[float, float]:
        """Return (left_x, right_x) of the lane at hit-line level."""
        idx = self._lane_index.get(midi_note, 0)
        lw = self._lane_width()
        left = _LANE_MARGIN + idx * lw
        return left, left + lw

    def _time_to_y(self, note_time: float) -> float:
        """Map note time to y position (falling from top)."""
        h = self.height()
        hit_y = h * _HIT_LINE_Y_RATIO
        dt = note_time - self._current_time
        return hit_y - dt * _FALL_SPEED

    def _perspective_at_y(self, y: float) -> float:
        """Return perspective scale 0..1 for given y (0=vanish, 1=hit line)."""
        h = self.height()
        vanish_y = h * _VANISH_Y_RATIO
        hit_y = h * _HIT_LINE_Y_RATIO
        if hit_y <= vanish_y:
            return 1.0
        ratio = (y - vanish_y) / (hit_y - vanish_y)
        return max(0.0, min(1.3, ratio))

    def _apply_perspective_x(self, base_x: float, y: float) -> float:
        """Apply perspective convergence to an x coordinate."""
        w = self.width()
        center_x = w / 2.0
        scale = self._perspective_at_y(y)
        return center_x + (base_x - center_x) * scale

    # ── Game Loop ───────────────────────────────────────────

    def _tick(self) -> None:
        if not self._playing:
            return
        self._current_time += 0.016 * self._speed

        # Update feedback effects (real-time, not scaled by speed)
        alive = []
        for fb in self._feedbacks:
            fb.life -= 0.016
            fb.y -= 40 * 0.016  # float upward
            if fb.life > 0:
                alive.append(fb)
        self._feedbacks = alive

        # Update flash effects (real-time)
        alive_flashes = []
        for fl in self._flashes:
            fl.life -= 0.016
            if fl.life > 0:
                alive_flashes.append(fl)
        self._flashes = alive_flashes

        # Update consumed-note burst effects
        alive_consumed = []
        for ce in self._consumed_effects:
            ce.life -= 0.016
            if ce.life > 0:
                alive_consumed.append(ce)
        self._consumed_effects = alive_consumed

        # Check if all notes have passed
        if self._notes and self._current_time > self._notes[-1].time_seconds + 3.0:
            self._playing = False
            self._timer.stop()
            self.practice_finished.emit()

        self.update()

    # ── Rendering ───────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        hit_y = h * _HIT_LINE_Y_RATIO
        vanish_y = h * _VANISH_Y_RATIO
        center_x = w / 2.0
        n_lanes = len(self._lane_notes)
        lw = self._lane_width() if n_lanes > 0 else 60.0

        # ── Background gradient ──
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0.0, QColor("#050810"))
        bg_grad.setColorAt(0.5, QColor("#0A1020"))
        bg_grad.setColorAt(1.0, QColor("#0D1828"))
        painter.fillRect(0, 0, w, h, bg_grad)

        # ── Highway surface (darker trapezoid) ──
        highway_left = _LANE_MARGIN
        highway_right = w - _LANE_MARGIN
        lt = self._apply_perspective_x(highway_left, vanish_y)
        rt = self._apply_perspective_x(highway_right, vanish_y)
        highway_path = QPainterPath()
        highway_path.moveTo(lt, vanish_y)
        highway_path.lineTo(rt, vanish_y)
        highway_path.lineTo(highway_right, hit_y + _LANE_LABEL_HEIGHT + 10)
        highway_path.lineTo(highway_left, hit_y + _LANE_LABEL_HEIGHT + 10)
        highway_path.closeSubpath()
        painter.fillPath(highway_path, QColor(8, 14, 24, 180))

        # ── Lane backgrounds (alternating) ──
        if n_lanes > 0:
            for i in range(n_lanes):
                lane_left = _LANE_MARGIN + i * lw
                lane_right = lane_left + lw
                bg_color = _LANE_BG_EVEN if i % 2 == 0 else _LANE_BG_ODD

                # Build perspective trapezoid for this lane
                tl = self._apply_perspective_x(lane_left, vanish_y)
                tr = self._apply_perspective_x(lane_right, vanish_y)
                lane_path = QPainterPath()
                lane_path.moveTo(tl, vanish_y)
                lane_path.lineTo(tr, vanish_y)
                lane_path.lineTo(lane_right, hit_y + _LANE_LABEL_HEIGHT + 10)
                lane_path.lineTo(lane_left, hit_y + _LANE_LABEL_HEIGHT + 10)
                lane_path.closeSubpath()
                painter.fillPath(lane_path, bg_color)

        # ── Lane dividers (perspective lines) ──
        if n_lanes > 1:
            divider_pen = QPen(_LANE_DIVIDER_COLOR, 1.0)
            painter.setPen(divider_pen)
            for i in range(n_lanes + 1):
                base_x = _LANE_MARGIN + i * lw
                top_x = self._apply_perspective_x(base_x, vanish_y)
                painter.drawLine(
                    int(top_x),
                    int(vanish_y),
                    int(base_x),
                    int(hit_y + _LANE_LABEL_HEIGHT + 10),
                )

        # ── Highway rail lines (outer edges) ──
        rail_pen = QPen(QColor(30, 50, 70, 150), 1.5)
        painter.setPen(rail_pen)
        painter.drawLine(
            int(lt), int(vanish_y), int(highway_left), int(hit_y + _LANE_LABEL_HEIGHT + 10)
        )
        painter.drawLine(
            int(rt), int(vanish_y), int(highway_right), int(hit_y + _LANE_LABEL_HEIGHT + 10)
        )

        # ── Horizontal grid lines (perspective-spaced for depth) ──
        num_grid = 12
        for i in range(1, num_grid):
            t = i / num_grid
            grid_y = vanish_y + (hit_y - vanish_y) * (t**1.4)
            gx_l = self._apply_perspective_x(highway_left, grid_y)
            gx_r = self._apply_perspective_x(highway_right, grid_y)
            scale = self._perspective_at_y(grid_y)
            grid_alpha = int(scale * 20)
            painter.setPen(QPen(QColor(20, 40, 65, grid_alpha), 0.5))
            painter.drawLine(int(gx_l), int(grid_y), int(gx_r), int(grid_y))

        # ── Hit zone glow ──
        hit_glow = QLinearGradient(0, hit_y - _HIT_ZONE_HEIGHT, 0, hit_y + _HIT_ZONE_HEIGHT)
        hit_glow.setColorAt(0.0, QColor(212, 175, 55, 0))
        hit_glow.setColorAt(0.35, QColor(212, 175, 55, 30))
        hit_glow.setColorAt(0.5, QColor(212, 175, 55, 70))
        hit_glow.setColorAt(0.65, QColor(212, 175, 55, 30))
        hit_glow.setColorAt(1.0, QColor(212, 175, 55, 0))
        painter.fillRect(
            QRectF(0, hit_y - _HIT_ZONE_HEIGHT, w, _HIT_ZONE_HEIGHT * 2),
            hit_glow,
        )

        # Hit line
        painter.setPen(QPen(_HIT_LINE_COLOR, 2.5))
        painter.drawLine(0, int(hit_y), w, int(hit_y))

        # ── Flash effects (lane column highlight on successful hit) ──
        for fl in self._flashes:
            alpha = fl.life / _FLASH_DURATION
            # Column highlight: glow the entire lane column
            if fl.lane_left < fl.lane_right:
                col_color = QColor(fl.color)
                col_color.setAlphaF(alpha * 0.15)
                col_top = vanish_y + (hit_y - vanish_y) * 0.3
                tl = self._apply_perspective_x(fl.lane_left, col_top)
                tr = self._apply_perspective_x(fl.lane_right, col_top)
                col_path = QPainterPath()
                col_path.moveTo(tl, col_top)
                col_path.lineTo(tr, col_top)
                col_path.lineTo(fl.lane_right, hit_y + 5)
                col_path.lineTo(fl.lane_left, hit_y + 5)
                col_path.closeSubpath()
                painter.fillPath(col_path, col_color)

            # Radial glow at hit point
            px = self._apply_perspective_x(fl.x, hit_y)
            radius = 40 * (1.0 + (1.0 - alpha) * 0.8)
            glow_grad = QRadialGradient(px, hit_y, radius)
            gc = QColor(fl.color)
            gc.setAlphaF(alpha * 0.5)
            glow_grad.setColorAt(0.0, gc)
            gc_out = QColor(fl.color)
            gc_out.setAlphaF(0)
            glow_grad.setColorAt(1.0, gc_out)
            painter.setBrush(glow_grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                QRectF(px - radius, hit_y - radius, radius * 2, radius * 2),
            )

        # ── Falling notes (lane-based, 3D perspective) ──
        note_w_base = lw * _NOTE_LANE_FILL if n_lanes > 0 else 36
        for pn in self._notes:
            if pn.time_seconds in self._hit_note_times:
                continue

            ny = self._time_to_y(pn.time_seconds)
            if ny > h + 40 or ny < vanish_y - 10:
                continue

            scale = self._perspective_at_y(ny)
            if scale < 0.05:
                continue

            base_x = self._note_to_x(pn.note)
            px = self._apply_perspective_x(base_x, ny)

            # Scale note dimensions with perspective
            nw = note_w_base * scale
            nh = max(
                _NOTE_HEIGHT * scale,
                pn.duration_seconds * _FALL_SPEED * 0.5 * scale,
            )

            # Note body (rounded rect)
            rect = QRectF(px - nw / 2, ny - nh, nw, nh)
            path = QPainterPath()
            corner = max(2, 4 * scale)
            path.addRoundedRect(rect, corner, corner)

            # Color intensifies near hit line
            dist_to_hit = abs(ny - hit_y)
            if dist_to_hit < 30:
                color = QColor(_HIT_LINE_COLOR)
                color.setAlphaF(0.95)
            else:
                color = QColor(_NOTE_COLOR)
                color.setAlphaF(max(0.2, min(1.0, scale * 1.2)))

            painter.fillPath(path, color)

            # Note border
            border = QColor(_NOTE_BORDER)
            border.setAlphaF(min(1.0, scale * 1.5))
            painter.setPen(QPen(border, max(0.5, scale)))
            painter.drawPath(path)

            # Glow for notes approaching the hit zone
            if dist_to_hit < 80:
                glow_a = (1.0 - dist_to_hit / 80) * 0.25
                note_glow = QColor(_NOTE_COLOR)
                note_glow.setAlphaF(glow_a)
                gr = QRectF(px - nw / 2 - 3, ny - nh - 3, nw + 6, nh + 6)
                gp = QPainterPath()
                gp.addRoundedRect(gr, corner + 2, corner + 2)
                painter.fillPath(gp, note_glow)

        # ── Consumed note burst effects ──
        for ce in self._consumed_effects:
            progress = 1.0 - ce.life / _CONSUMED_DURATION
            alpha = max(0, 1.0 - progress)
            expand = 1.0 + progress * 2.5
            px = self._apply_perspective_x(ce.x, ce.y)
            rw = ce.width * expand
            rh = _NOTE_HEIGHT * expand
            burst_color = QColor(ce.color)
            burst_color.setAlphaF(alpha * 0.7)
            burst_rect = QRectF(px - rw / 2, ce.y - rh / 2, rw, rh)
            burst_path = QPainterPath()
            burst_path.addRoundedRect(burst_rect, 6, 6)
            painter.fillPath(burst_path, burst_color)
            if progress < 0.5:
                core_alpha = (1.0 - progress * 2) * 0.8
                core = QColor(255, 255, 255, int(core_alpha * 255))
                core_rect = QRectF(px - rw / 4, ce.y - rh / 4, rw / 2, rh / 2)
                core_path = QPainterPath()
                core_path.addRoundedRect(core_rect, 4, 4)
                painter.fillPath(core_path, core)

        # ── Feedback text (large, centered, with glow) ──
        for fb in self._feedbacks:
            progress = 1.0 - fb.life / fb.initial_life

            if progress < 0.6:
                alpha = 1.0
            else:
                alpha = max(0, 1.0 - (progress - 0.6) / 0.4)

            if progress < 0.15:
                pop_scale = 1.8 - 0.8 * (progress / 0.15)
            else:
                pop_scale = 1.0

            base_size = 42
            font_size = max(12, int(base_size * pop_scale))
            text_rect = QRectF(center_x - 220, fb.y, 440, 70)

            glow_c = QColor(fb.color)
            glow_c.setAlphaF(alpha * 0.35)
            painter.setPen(glow_c)
            painter.setFont(QFont("Microsoft JhengHei", font_size + 3, QFont.Weight.Bold))
            painter.drawText(
                QRectF(
                    text_rect.x(),
                    text_rect.y() + 2,
                    text_rect.width(),
                    text_rect.height(),
                ),
                Qt.AlignmentFlag.AlignCenter,
                fb.text,
            )

            main_c = QColor(fb.color)
            main_c.setAlphaF(alpha)
            painter.setPen(main_c)
            painter.setFont(QFont("Microsoft JhengHei", font_size, QFont.Weight.Bold))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, fb.text)

        # ── Combo counter ──
        if self._combo > 5:
            combo_alpha = min(1.0, self._combo / 20.0) * 0.8
            combo_color = QColor(_COMBO_COLOR)
            combo_color.setAlphaF(combo_alpha)
            painter.setPen(combo_color)
            painter.setFont(QFont("Microsoft JhengHei", 36, QFont.Weight.Bold))
            painter.drawText(
                QRectF(0, h * 0.25, w, 60),
                Qt.AlignmentFlag.AlignCenter,
                f"{self._combo} COMBO",
            )

        # ── Lane key labels (below hit line) ──
        if n_lanes > 0:
            label_top = int(hit_y + 4)

            # Background strip for labels
            painter.fillRect(
                QRectF(_LANE_MARGIN, label_top, w - 2 * _LANE_MARGIN, _LANE_LABEL_HEIGHT),
                _LANE_LABEL_BG,
            )

            # Determine font size based on lane width
            max_font = 14
            min_font = 8
            font_size = max(min_font, min(max_font, int(lw * 0.35)))
            painter.setFont(QFont("Microsoft JhengHei", font_size, QFont.Weight.Bold))

            for i, midi in enumerate(self._lane_notes):
                lane_center = _LANE_MARGIN + (i + 0.5) * lw
                label_rect = QRectF(
                    lane_center - lw / 2 + 2,
                    label_top,
                    lw - 4,
                    _LANE_LABEL_HEIGHT,
                )

                # Get label text: prefer keyboard key label, fallback to note name
                if self._key_labels and midi in self._key_labels:
                    label = self._key_labels[midi]
                else:
                    label = _midi_note_name(midi)

                # Draw label centered in lane
                painter.setPen(QColor(180, 200, 220, 200))
                painter.drawText(
                    label_rect,
                    Qt.AlignmentFlag.AlignCenter,
                    label,
                )

        painter.end()
