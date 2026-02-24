"""Falling-note rhythm game display for practice mode — 60fps QPainter rendering."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from ...core.constants import Modifier
from ...core.practice_engine import HitGrade, PracticeNote

# Visual constants
_HIT_LINE_Y_RATIO = 0.85  # Hit line at 85% from top
_NOTE_WIDTH = 28
_NOTE_HEIGHT = 16
_FALL_SPEED = 300.0  # pixels per second (base)
_FEEDBACK_DURATION = 0.6  # seconds
_FLASH_DURATION = 0.15  # seconds — bright glow on hit

# Colors
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
    __slots__ = ("text", "color", "x", "y", "life")

    def __init__(self, text: str, color: QColor, x: float, y: float) -> None:
        self.text = text
        self.color = color
        self.x = x
        self.y = y
        self.life = _FEEDBACK_DURATION


class _FlashEffect:
    """Brief bright glow at the hit line when a note is hit."""

    __slots__ = ("x", "color", "life")

    def __init__(self, x: float, color: QColor) -> None:
        self.x = x
        self.color = color
        self.life = _FLASH_DURATION


class PracticeDisplay(QWidget):
    """Falling notes display with hit line and visual feedback."""

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

    def set_notes(self, notes: list[PracticeNote], tempo_bpm: float = 120.0) -> None:
        self._notes = sorted(notes, key=lambda n: n.time_seconds)
        self._tempo_bpm = tempo_bpm
        # Compute note range
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

    def show_feedback(self, grade: HitGrade, note: int) -> None:
        """Show hit grade visual feedback."""
        x = self._note_to_x(note)
        hit_y = self.height() * _HIT_LINE_Y_RATIO
        color = _GRADE_COLORS.get(grade, _MISS_COLOR)
        text = _GRADE_TEXT.get(grade, "")
        self._feedbacks.append(_FeedbackEffect(text, color, x, hit_y - 30))
        # Bright flash at hit line for non-miss hits
        if grade != HitGrade.MISS:
            self._flashes.append(_FlashEffect(x, color))

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

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.isAutoRepeat() or not self._playing or self._reverse_map is None:
            super().keyPressEvent(event)
            return

        # Use event.key() instead of event.text() so Ctrl+key works correctly
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

    def _note_to_x(self, midi_note: int) -> float:
        """Map MIDI note to x position."""
        w = self.width()
        margin = 40
        usable = w - 2 * margin
        note_range = max(1, self._note_max - self._note_min)
        return margin + ((midi_note - self._note_min) / note_range) * usable

    def _time_to_y(self, note_time: float) -> float:
        """Map note time to y position (falling from top)."""
        h = self.height()
        hit_y = h * _HIT_LINE_Y_RATIO
        # How far ahead (in seconds) the note is
        dt = note_time - self._current_time
        return hit_y - dt * _FALL_SPEED

    def _tick(self) -> None:
        if not self._playing:
            return
        # Song time scales with speed (0.5x → half as fast)
        self._current_time += 0.016 * self._speed

        # Update feedback effects (real-time, not scaled by speed)
        alive = []
        for fb in self._feedbacks:
            fb.life -= 0.016
            fb.y -= 30 * 0.016  # float upward
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

        # Check if all notes have passed
        if self._notes and self._current_time > self._notes[-1].time_seconds + 3.0:
            self._playing = False
            self._timer.stop()
            self.practice_finished.emit()

        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background gradient
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0.0, QColor("#0A0E1A"))
        bg_grad.setColorAt(1.0, QColor("#0D1520"))
        painter.fillRect(0, 0, w, h, bg_grad)

        hit_y = h * _HIT_LINE_Y_RATIO

        # Hit line
        painter.setPen(QPen(_HIT_LINE_COLOR, 2.0))
        painter.drawLine(0, int(hit_y), w, int(hit_y))

        # Hit line glow
        glow_color = QColor(_HIT_LINE_COLOR)
        glow_color.setAlphaF(0.15)
        painter.fillRect(QRectF(0, hit_y - 3, w, 6), glow_color)

        # Flash effects at hit line (bright circular glow on hit)
        for fl in self._flashes:
            alpha = fl.life / _FLASH_DURATION
            glow = QColor(fl.color)
            glow.setAlphaF(alpha * 0.6)
            radius = 30 * (1.0 + (1.0 - alpha) * 0.5)
            painter.setBrush(glow)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                QRectF(fl.x - radius, hit_y - radius, radius * 2, radius * 2),
            )

        # Falling notes
        for pn in self._notes:
            ny = self._time_to_y(pn.time_seconds)
            if ny > h + 30 or ny < -30:
                continue

            nx = self._note_to_x(pn.note)
            note_h = max(_NOTE_HEIGHT, pn.duration_seconds * _FALL_SPEED * 0.5)

            # Note body
            rect = QRectF(nx - _NOTE_WIDTH / 2, ny - note_h, _NOTE_WIDTH, note_h)
            path = QPainterPath()
            path.addRoundedRect(rect, 4, 4)

            # Color based on proximity to hit line
            dist = abs(ny - hit_y)
            if dist < 20:
                color = QColor(_HIT_LINE_COLOR)
                color.setAlphaF(0.9)
            else:
                color = QColor(_NOTE_COLOR)
                alpha = max(0.3, 1.0 - abs(ny - hit_y) / (h * 0.7))
                color.setAlphaF(alpha)

            painter.fillPath(path, color)
            painter.setPen(QPen(_NOTE_BORDER, 1.0))
            painter.drawPath(path)

        # Feedback effects (grade text floating upward)
        for fb in self._feedbacks:
            alpha = max(0, fb.life / _FEEDBACK_DURATION)
            color = QColor(fb.color)
            color.setAlphaF(alpha)
            painter.setPen(color)
            font_size = int(14 + (1.0 - alpha) * 6)
            painter.setFont(QFont("Microsoft JhengHei", font_size, QFont.Weight.Bold))
            painter.drawText(
                QRectF(fb.x - 60, fb.y, 120, 30),
                Qt.AlignmentFlag.AlignCenter,
                fb.text,
            )

        # Combo counter overlay (shown when combo > 5)
        if self._combo > 5:
            combo_alpha = min(1.0, self._combo / 20.0) * 0.8
            combo_color = QColor(_COMBO_COLOR)
            combo_color.setAlphaF(combo_alpha)
            painter.setPen(combo_color)
            painter.setFont(QFont("Microsoft JhengHei", 32, QFont.Weight.Bold))
            painter.drawText(
                QRectF(0, h * 0.3, w, 50),
                Qt.AlignmentFlag.AlignCenter,
                f"{self._combo} COMBO",
            )

        # Lane labels at bottom
        painter.setPen(QColor("#555555"))
        painter.setFont(QFont("Microsoft JhengHei", 7))
        if self._key_labels:
            for midi, label in self._key_labels.items():
                if self._note_min <= midi <= self._note_max:
                    x = self._note_to_x(midi)
                    painter.drawText(int(x - 15), int(hit_y + 16), label)
        else:
            note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            for midi in range(self._note_min, self._note_max + 1):
                if midi % 12 == 0 or midi == self._note_min:
                    x = self._note_to_x(midi)
                    name = note_names[midi % 12] + str(midi // 12 - 1)
                    painter.drawText(int(x - 10), int(hit_y + 16), name)

        painter.end()
