"""Compact mini piano visualizer for the Now Playing bar — with glow and fade effects."""

from __future__ import annotations

import time

from PyQt6.QtCore import QRectF, QTimer
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PyQt6.QtWidgets import QWidget

from ...core.constants import MIDI_NOTE_MAX, MIDI_NOTE_MIN

_BLACK_SEMITONES = {1, 3, 6, 8, 10}

# 賽博墨韻 colors
_COLOR_OFF = QColor(0x2E, 0x3D, 0x50)  # 雲霧層
_COLOR_OFF_BLACK = QColor(0x1A, 0x23, 0x32)  # 宣紙暗面
_COLOR_ON = QColor(0x00, 0xF0, 0xFF)  # 賽博青
_COLOR_ON_BRIGHT = QColor(0x40, 0xFF, 0xFF)  # 青光暈
_GLOW_COLOR = QColor(0, 240, 255, 60)  # 青 glow
_FADE_DURATION = 0.2  # seconds


class MiniPiano(QWidget):
    """Single-row mini piano visualizer with glow and fade effects."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active_notes: set[int] = set()
        self._fade_notes: dict[int, float] = {}  # midi_note -> release_time
        self._midi_min = MIDI_NOTE_MIN
        self._midi_max = MIDI_NOTE_MAX
        self._total_keys = self._midi_max - self._midi_min + 1
        self.setFixedHeight(36)
        self.setMinimumWidth(180)

        # Fade animation timer
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._tick_fade)
        self._fade_timer.setInterval(16)  # ~60fps

    def set_midi_range(self, midi_range: tuple[int, int]) -> None:
        """Update the displayed MIDI note range."""
        self._midi_min, self._midi_max = midi_range
        self._total_keys = self._midi_max - self._midi_min + 1
        self._active_notes.clear()
        self._fade_notes.clear()
        self.update()

    def set_active_notes(self, notes: set[int]) -> None:
        self._active_notes = notes
        self._fade_notes.clear()
        self.update()

    def note_on(self, midi_note: int) -> None:
        self._active_notes.add(midi_note)
        self._fade_notes.pop(midi_note, None)
        self.update()

    def note_off(self, midi_note: int) -> None:
        self._active_notes.discard(midi_note)
        self._fade_notes[midi_note] = time.monotonic()
        if not self._fade_timer.isActive():
            self._fade_timer.start()
        self.update()

    def _tick_fade(self) -> None:
        now = time.monotonic()
        expired = [n for n, t in self._fade_notes.items() if now - t > _FADE_DURATION]
        for n in expired:
            del self._fade_notes[n]
        if not self._fade_notes:
            self._fade_timer.stop()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        total = self._total_keys
        if total <= 0:
            painter.end()
            return

        key_w = max(2, w / total)
        gap = 1
        now = time.monotonic()

        # Clip to rounded rect container
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), 6, 6)
        painter.setClipPath(clip)

        # Background — 墨黑
        painter.fillRect(0, 0, w, h, QColor(0x0A, 0x0E, 0x14))

        for i in range(total):
            midi_note = self._midi_min + i
            x = i * key_w
            is_active = midi_note in self._active_notes
            is_black = (midi_note % 12) in _BLACK_SEMITONES
            fade_t = self._fade_notes.get(midi_note)

            if is_active:
                color = _COLOR_ON_BRIGHT if is_black else _COLOR_ON
            elif fade_t is not None:
                elapsed = now - fade_t
                ratio = max(0.0, 1.0 - elapsed / _FADE_DURATION)
                off_color = _COLOR_OFF_BLACK if is_black else _COLOR_OFF
                color = _lerp_color(off_color, _COLOR_ON, ratio)
            else:
                if is_black:
                    color = _COLOR_OFF_BLACK
                else:
                    color = _COLOR_OFF

            key_rect = QRectF(x, 0, key_w - gap, h)
            path = QPainterPath()
            path.addRoundedRect(key_rect, 2, 2)

            if not is_active and fade_t is None and not is_black:
                grad = QLinearGradient(x, 0, x, h)
                grad.setColorAt(0, QColor(0x36, 0x48, 0x5A))
                grad.setColorAt(1, _COLOR_OFF)
                painter.fillPath(path, grad)
            else:
                painter.fillPath(path, color)

            # Glow for active keys
            if is_active:
                glow_rect = QRectF(x - 1, -2, key_w - gap + 2, h + 4)
                glow_path = QPainterPath()
                glow_path.addRoundedRect(glow_rect, 3, 3)
                painter.fillPath(glow_path, _GLOW_COLOR)
                painter.fillPath(path, color)

        painter.end()


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
        int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )
