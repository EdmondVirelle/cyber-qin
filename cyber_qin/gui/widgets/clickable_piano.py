"""Interactive piano widget — click to input notes.

Same visual style as PianoDisplay but handles mouse clicks.
Emits signals for note input in the editor.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QWidget

from ...core.constants import MIDI_NOTE_MIN

# Which semitones in the octave are "black keys"
_BLACK_SEMITONES = {1, 3, 6, 8, 10}

# Colors matching PianoDisplay
_COLOR_NATURAL = QColor(0x1A, 0x23, 0x32)
_COLOR_SHARP = QColor(0x1A, 0x14, 0x28)
_COLOR_ACTIVE = QColor(0x00, 0xF0, 0xFF)
_COLOR_BORDER = QColor(0x2E, 0x3D, 0x50)
_COLOR_TEXT_LIGHT = QColor(0xE8, 0xE0, 0xD0)
_COLOR_TEXT_DIM = QColor(0x7A, 0x88, 0x99)

# Note names
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class ClickablePiano(QWidget):
    """Interactive piano keyboard for note input."""

    note_clicked = pyqtSignal(int)    # midi_note
    note_pressed = pyqtSignal(int)    # midi_note (mouse down)
    note_released = pyqtSignal(int)   # midi_note (mouse up)

    def __init__(
        self,
        midi_min: int = MIDI_NOTE_MIN,
        midi_max: int = 83,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._midi_min = midi_min
        self._midi_max = midi_max
        self._pressed_note: int | None = None
        self._hover_note: int | None = None
        self.setFixedHeight(80)
        self.setMinimumWidth(400)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def num_keys(self) -> int:
        return self._midi_max - self._midi_min + 1

    def _note_at_pos(self, x: float, y: float) -> int | None:
        """Hit-test: return MIDI note at pixel position, or None."""
        w = self.width()
        h = self.height()
        if x < 0 or x >= w or y < 0 or y >= h:
            return None

        n_keys = self.num_keys
        key_w = w / n_keys
        index = int(x / key_w)
        index = max(0, min(index, n_keys - 1))
        return self._midi_min + index

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            note = self._note_at_pos(event.position().x(), event.position().y())
            if note is not None:
                self._pressed_note = note
                self.note_pressed.emit(note)
                self.note_clicked.emit(note)
                self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._pressed_note is not None:
            self.note_released.emit(self._pressed_note)
            self._pressed_note = None
            self.update()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        note = self._note_at_pos(event.position().x(), event.position().y())
        if note != self._hover_note:
            self._hover_note = note
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover_note = None
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        n_keys = self.num_keys
        key_w = w / n_keys

        font_size = max(7, int(min(key_w / 3.5, h / 5.0)))
        font = QFont("Microsoft JhengHei", font_size)

        # Background
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), 8, 8)
        painter.setClipPath(clip)

        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0, QColor(0x10, 0x18, 0x20))
        bg_grad.setColorAt(1, QColor(0x0A, 0x0E, 0x14))
        painter.fillRect(0, 0, w, h, bg_grad)

        for i in range(n_keys):
            midi_note = self._midi_min + i
            x = i * key_w
            kw = key_w - 1
            kh = h - 1
            semitone = midi_note % 12
            is_black = semitone in _BLACK_SEMITONES
            is_pressed = midi_note == self._pressed_note
            is_hover = midi_note == self._hover_note

            # Background color
            if is_pressed:
                bg = _COLOR_ACTIVE
            elif is_hover:
                bg = QColor(0x00, 0xF0, 0xFF, 60)
            elif is_black:
                bg = _COLOR_SHARP
            else:
                bg = _COLOR_NATURAL

            key_rect = QRectF(x, 0, kw, kh)
            path = QPainterPath()
            path.addRoundedRect(key_rect, 3, 3)

            if is_pressed or is_hover:
                painter.fillPath(path, QBrush(bg))
            elif not is_black:
                grad = QLinearGradient(x, 0, x, kh)
                grad.setColorAt(0, QColor(0x24, 0x30, 0x40))
                grad.setColorAt(1, _COLOR_NATURAL)
                painter.fillPath(path, grad)
            else:
                painter.fillPath(path, QBrush(bg))

            # Border
            if is_pressed:
                painter.setPen(QPen(QColor(0, 240, 255, 150), 1.5))
            else:
                painter.setPen(QPen(_COLOR_BORDER, 0.5))
            painter.drawPath(path)

            # Note name
            text_color = _COLOR_TEXT_LIGHT if is_pressed else _COLOR_TEXT_DIM
            painter.setPen(text_color)
            painter.setFont(font)

            name = _NOTE_NAMES[semitone]
            octave = midi_note // 12 - 1
            label = f"{name}{octave}"

            painter.drawText(
                int(x), int(kh * 0.55), int(kw), int(kh * 0.4),
                Qt.AlignmentFlag.AlignCenter, label,
            )

        painter.end()
