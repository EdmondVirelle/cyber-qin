"""Pitch ruler widget — shows note names (C3..B5) aligned with NoteRoll Y-axis."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QWidget

from ..theme import BG_INK, BG_SCROLL, TEXT_PRIMARY, TEXT_SECONDARY

_RULER_WIDTH = 48
_HEADER_HEIGHT = 22  # Must match NoteRoll._HEADER_HEIGHT

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_BLACK_SEMITONES = {1, 3, 6, 8, 10}


class PitchRuler(QWidget):
    """Fixed-width vertical ruler showing note names aligned with the NoteRoll."""

    def __init__(
        self,
        midi_min: int = 48,
        midi_max: int = 83,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._midi_min = midi_min
        self._midi_max = midi_max
        self.setFixedWidth(_RULER_WIDTH)
        self.setMinimumHeight(120)

    def set_midi_range(self, midi_min: int, midi_max: int) -> None:
        self._midi_min = midi_min
        self._midi_max = midi_max
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(BG_INK))

        # Header background (aligns with NoteRoll header)
        painter.fillRect(0, 0, w, _HEADER_HEIGHT, QColor(BG_SCROLL))

        range_size = self._midi_max - self._midi_min + 1
        body_h = h - _HEADER_HEIGHT
        note_h = body_h / max(1, range_size)

        font = QFont("Microsoft JhengHei", max(7, min(9, int(note_h * 0.6))))
        painter.setFont(font)

        for i in range(range_size):
            midi_note = self._midi_max - i
            semitone = midi_note % 12
            is_black = semitone in _BLACK_SEMITONES
            octave = midi_note // 12 - 1
            name = _NOTE_NAMES[semitone]

            y = _HEADER_HEIGHT + i * note_h

            # Dark background stripe for black keys
            if is_black:
                painter.fillRect(
                    QRectF(0, y, w, note_h),
                    QColor(0x10, 0x14, 0x1E),
                )

            # Note name text
            if is_black:
                painter.setPen(QColor(TEXT_SECONDARY))
            else:
                painter.setPen(QColor(TEXT_PRIMARY))

            label = f"{name}{octave}"
            painter.drawText(
                QRectF(2, y, w - 4, note_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                label,
            )

        # Right border line
        painter.setPen(QColor(0x1E, 0x2D, 0x3D))
        painter.drawLine(w - 1, _HEADER_HEIGHT, w - 1, h)

        painter.end()
