"""Falling-note rhythm game display for practice mode — 60fps QPainter rendering.

Features a 3D perspective "highway" effect where notes approach the hit line
from a vanishing point, similar to Guitar Hero / Rock Band.
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
_LANE_MARGIN = 40  # Horizontal margin at hit line level

# ── Note Sizing (at hit line, full scale) ────────────────────
_NOTE_WIDTH = 36
_NOTE_HEIGHT = 18
_FALL_SPEED = 300.0  # pixels per second (base)

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

    __slots__ = ("x", "color", "life")

    def __init__(self, x: float, color: QColor) -> None:
        self.x = x
        self.color = color
        self.life = _FLASH_DURATION


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
    """Falling notes display with 3D perspective highway effect."""

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

        # Note range for x-mapping
        self._note_min: int = 60
        self._note_max: int = 83

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
        if notes:
            pitches = [n.note for n in notes]
            self._note_min = max(21, min(pitches) - 2)
            self._note_max = min(108, max(pitches) + 2)
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
            self._flashes.append(_FlashEffect(x, color))
            # Mark note consumed + burst effect
            if target_time is not None:
                self._hit_note_times.add(target_time)
                self._consumed_effects.append(
                    _ConsumedNoteEffect(x, hit_y, color, _NOTE_WIDTH),
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

    # ── Coordinate Mapping ──────────────────────────────────

    def _note_to_x(self, midi_note: int) -> float:
        """Map MIDI note to base x position (flat, at hit line level)."""
        w = self.width()
        usable = w - 2 * _LANE_MARGIN
        note_range = max(1, self._note_max - self._note_min)
        return _LANE_MARGIN + ((midi_note - self._note_min) / note_range) * usable

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
        # Allow slight overshoot past hit line for notes below it
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

        # ── Background gradient ──
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0.0, QColor("#050810"))
        bg_grad.setColorAt(0.5, QColor("#0A1020"))
        bg_grad.setColorAt(1.0, QColor("#0D1828"))
        painter.fillRect(0, 0, w, h, bg_grad)

        # ── Highway surface (darker trapezoid) ──
        highway_path = QPainterPath()
        lt = self._apply_perspective_x(_LANE_MARGIN, vanish_y)
        rt = self._apply_perspective_x(w - _LANE_MARGIN, vanish_y)
        highway_path.moveTo(lt, vanish_y)
        highway_path.lineTo(rt, vanish_y)
        highway_path.lineTo(w - _LANE_MARGIN, hit_y + 30)
        highway_path.lineTo(_LANE_MARGIN, hit_y + 30)
        highway_path.closeSubpath()
        painter.fillPath(highway_path, QColor(8, 14, 24, 180))

        # ── Highway rail lines (perspective edges) ──
        rail_pen = QPen(QColor(25, 40, 60, 120), 1.5)
        painter.setPen(rail_pen)
        painter.drawLine(int(lt), int(vanish_y), int(_LANE_MARGIN), int(hit_y + 30))
        painter.drawLine(int(rt), int(vanish_y), int(w - _LANE_MARGIN), int(hit_y + 30))

        # ── Center guide line ──
        painter.setPen(QPen(QColor(20, 35, 55, 60), 0.5))
        painter.drawLine(int(center_x), int(vanish_y), int(center_x), int(hit_y + 30))

        # ── Horizontal grid lines (perspective-spaced for depth) ──
        num_grid = 14
        for i in range(1, num_grid):
            t = i / num_grid
            # Power curve: denser near vanishing point, sparser near hit
            grid_y = vanish_y + (hit_y - vanish_y) * (t ** 1.4)
            scale = self._perspective_at_y(grid_y)
            gx_l = self._apply_perspective_x(_LANE_MARGIN, grid_y)
            gx_r = self._apply_perspective_x(w - _LANE_MARGIN, grid_y)
            grid_alpha = int(scale * 25)
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

        # ── Flash effects (radial glow at hit line on successful hit) ──
        for fl in self._flashes:
            alpha = fl.life / _FLASH_DURATION
            px = self._apply_perspective_x(fl.x, hit_y)
            radius = 50 * (1.0 + (1.0 - alpha) * 0.8)
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

        # ── Falling notes (3D perspective) ──
        for pn in self._notes:
            # Skip consumed (successfully hit) notes
            if pn.time_seconds in self._hit_note_times:
                continue

            ny = self._time_to_y(pn.time_seconds)
            # Cull off-screen notes
            if ny > h + 40 or ny < vanish_y - 10:
                continue

            scale = self._perspective_at_y(ny)
            if scale < 0.05:
                continue  # Too small to render

            base_x = self._note_to_x(pn.note)
            px = self._apply_perspective_x(base_x, ny)

            # Scale note dimensions with perspective
            nw = _NOTE_WIDTH * scale
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

            # Note border (fades with distance)
            border = QColor(_NOTE_BORDER)
            border.setAlphaF(min(1.0, scale * 1.5))
            painter.setPen(QPen(border, max(0.5, scale)))
            painter.drawPath(path)

            # Subtle glow for notes approaching the hit zone
            if dist_to_hit < 80:
                glow_a = (1.0 - dist_to_hit / 80) * 0.25
                note_glow = QColor(_NOTE_COLOR)
                note_glow.setAlphaF(glow_a)
                gr = QRectF(px - nw / 2 - 3, ny - nh - 3, nw + 6, nh + 6)
                gp = QPainterPath()
                gp.addRoundedRect(gr, corner + 2, corner + 2)
                painter.fillPath(gp, note_glow)

        # ── Consumed note burst effects (expanding bright ring) ──
        for ce in self._consumed_effects:
            progress = 1.0 - ce.life / _CONSUMED_DURATION
            alpha = max(0, 1.0 - progress)
            expand = 1.0 + progress * 2.5  # expand to 3.5x size
            px = self._apply_perspective_x(ce.x, ce.y)
            rw = ce.width * expand
            rh = _NOTE_HEIGHT * expand
            burst_color = QColor(ce.color)
            burst_color.setAlphaF(alpha * 0.7)
            burst_rect = QRectF(px - rw / 2, ce.y - rh / 2, rw, rh)
            burst_path = QPainterPath()
            burst_path.addRoundedRect(burst_rect, 6, 6)
            painter.fillPath(burst_path, burst_color)
            # Bright white core
            if progress < 0.5:
                core_alpha = (1.0 - progress * 2) * 0.8
                core = QColor(255, 255, 255, int(core_alpha * 255))
                core_rect = QRectF(px - rw / 4, ce.y - rh / 4, rw / 2, rh / 2)
                core_path = QPainterPath()
                core_path.addRoundedRect(core_rect, 4, 4)
                painter.fillPath(core_path, core)

        # ── Feedback text (large, centered, with glow) ──
        for fb in self._feedbacks:
            progress = 1.0 - fb.life / fb.initial_life  # 0→1 over lifetime

            # Alpha: hold steady for 60%, then fade out
            if progress < 0.6:
                alpha = 1.0
            else:
                alpha = max(0, 1.0 - (progress - 0.6) / 0.4)

            # Pop-in scale: start at 1.8x, settle to 1.0x over first 15%
            if progress < 0.15:
                pop_scale = 1.8 - 0.8 * (progress / 0.15)
            else:
                pop_scale = 1.0

            base_size = 42
            font_size = max(12, int(base_size * pop_scale))
            text_rect = QRectF(center_x - 220, fb.y, 440, 70)

            # Shadow/glow layer behind text
            glow_c = QColor(fb.color)
            glow_c.setAlphaF(alpha * 0.35)
            painter.setPen(glow_c)
            painter.setFont(QFont("Microsoft JhengHei", font_size + 3, QFont.Weight.Bold))
            painter.drawText(
                QRectF(text_rect.x(), text_rect.y() + 2, text_rect.width(), text_rect.height()),
                Qt.AlignmentFlag.AlignCenter,
                fb.text,
            )

            # Main text
            main_c = QColor(fb.color)
            main_c.setAlphaF(alpha)
            painter.setPen(main_c)
            painter.setFont(QFont("Microsoft JhengHei", font_size, QFont.Weight.Bold))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, fb.text)

        # ── Combo counter (shown when combo > 5) ──
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

        # ── Lane labels at bottom ──
        painter.setPen(QColor("#666666"))
        painter.setFont(QFont("Microsoft JhengHei", 8))
        label_y = int(hit_y + 22)
        if self._key_labels:
            for midi, label in self._key_labels.items():
                if self._note_min <= midi <= self._note_max:
                    x = self._note_to_x(midi)
                    painter.drawText(int(x - 15), label_y, label)
        else:
            note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            for midi in range(self._note_min, self._note_max + 1):
                if midi % 12 == 0 or midi == self._note_min:
                    x = self._note_to_x(midi)
                    name = note_names[midi % 12] + str(midi // 12 - 1)
                    painter.drawText(int(x - 10), label_y, name)

        painter.end()
