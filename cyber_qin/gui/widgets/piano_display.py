"""36-key visual piano display widget with glow effects and gradient background."""

from __future__ import annotations

import time

from PyQt6.QtCore import QRectF, Qt, QTimer
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

from ...core.constants import Modifier
from ...core.key_mapper import _BASE_MAP, KeyMapper

# Layout: 3 rows of 12 keys each
_ROWS = [
    list(range(72, 84)),  # High: C5-B5 (Q W E R T Y U)
    list(range(60, 72)),  # Mid:  C4-B4 (A S D F G H J)
    list(range(48, 60)),  # Low:  C3-B3 (Z X C V B N M)
]

_ROW_LABELS = ["High", "Mid", "Low"]

# Which semitones in the octave are "black keys" (sharps/flats)
_BLACK_SEMITONES = {1, 3, 6, 8, 10}

# Spotify-themed colors
_COLOR_NATURAL = QColor(40, 40, 40)        # #282828
_COLOR_SHARP = QColor(24, 24, 24)          # #181818
_COLOR_FLAT = QColor(30, 30, 48)           # Slight blue tint
_COLOR_ACTIVE = QColor(29, 185, 84)        # #1DB954 Spotify green
_COLOR_ACTIVE_DARK = QColor(22, 140, 64)   # Darker green
_COLOR_BORDER = QColor(50, 50, 50)
_COLOR_TEXT_LIGHT = QColor(255, 255, 255)
_COLOR_TEXT_DIM = QColor(180, 180, 180)
_GLOW_COLOR = QColor(29, 185, 84, 50)

_FLASH_DURATION = 0.15  # seconds — bright flash on note-on
_FADE_DURATION = 0.25   # seconds — fade after note-off


class PianoDisplay(QWidget):
    """Visual 36-key piano showing active notes with glow and flash effects."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active_notes: set[int] = set()
        self._flash_notes: dict[int, float] = {}  # midi_note -> note_on time
        self._fade_notes: dict[int, float] = {}   # midi_note -> note_off time
        self.setMinimumHeight(180)
        self.setMinimumWidth(480)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.setInterval(16)  # ~60fps

    def set_active_notes(self, notes: set[int]) -> None:
        self._active_notes = notes
        self._flash_notes.clear()
        self._fade_notes.clear()
        self.update()

    def note_on(self, midi_note: int) -> None:
        self._active_notes.add(midi_note)
        self._flash_notes[midi_note] = time.monotonic()
        self._fade_notes.pop(midi_note, None)
        if not self._anim_timer.isActive():
            self._anim_timer.start()
        self.update()

    def note_off(self, midi_note: int) -> None:
        self._active_notes.discard(midi_note)
        self._flash_notes.pop(midi_note, None)
        self._fade_notes[midi_note] = time.monotonic()
        if not self._anim_timer.isActive():
            self._anim_timer.start()
        self.update()

    def _tick(self) -> None:
        now = time.monotonic()
        # Clean expired flashes
        expired_flash = [n for n, t in self._flash_notes.items() if now - t > _FLASH_DURATION]
        for n in expired_flash:
            del self._flash_notes[n]
        # Clean expired fades
        expired_fade = [n for n, t in self._fade_notes.items() if now - t > _FADE_DURATION]
        for n in expired_fade:
            del self._fade_notes[n]
        if not self._flash_notes and not self._fade_notes:
            self._anim_timer.stop()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad = 2
        row_h = (h - pad * 2) / 3
        key_w = (w - pad * 2) / 12
        font = QFont("Segoe UI", max(8, int(key_w / 4.5)))
        font.setWeight(QFont.Weight.DemiBold)
        small_font = QFont("Segoe UI", max(6, int(key_w / 5.5)))

        now = time.monotonic()

        # Clip to rounded container
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), 10, 10)
        painter.setClipPath(clip)

        # Background gradient
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0, QColor(22, 22, 22))
        bg_grad.setColorAt(1, QColor(18, 18, 18))
        painter.fillRect(0, 0, w, h, bg_grad)

        for row_idx, row_notes in enumerate(_ROWS):
            for col, midi_note in enumerate(row_notes):
                x = pad + col * key_w
                y = pad + row_idx * row_h
                kw = key_w - 1
                kh = row_h - 1

                mapping = _BASE_MAP.get(midi_note)
                is_active = midi_note in self._active_notes
                semitone = midi_note % 12
                is_black = semitone in _BLACK_SEMITONES

                flash_t = self._flash_notes.get(midi_note)
                fade_t = self._fade_notes.get(midi_note)

                # Compute brightness multiplier for flash
                brightness = 1.0
                if is_active and flash_t is not None:
                    elapsed = now - flash_t
                    ratio = max(0.0, 1.0 - elapsed / _FLASH_DURATION)
                    brightness = 1.0 + 0.3 * ratio  # 1.3 -> 1.0

                # Background color
                if is_active:
                    base_bg = _COLOR_ACTIVE if not is_black else _COLOR_ACTIVE_DARK
                    bg = _brighten(base_bg, brightness)
                elif fade_t is not None:
                    elapsed = now - fade_t
                    ratio = max(0.0, 1.0 - elapsed / _FADE_DURATION)
                    off = _COLOR_SHARP if is_black else _COLOR_NATURAL
                    if is_black and mapping and mapping.modifier == Modifier.CTRL:
                        off = _COLOR_FLAT
                    bg = _lerp_color(off, _COLOR_ACTIVE, ratio * 0.5)
                elif is_black:
                    bg = _COLOR_FLAT if (mapping and mapping.modifier == Modifier.CTRL) else _COLOR_SHARP
                else:
                    bg = _COLOR_NATURAL

                key_rect = QRectF(x, y, kw, kh)

                # Draw key with subtle gradient for inactive natural keys
                path = QPainterPath()
                path.addRoundedRect(key_rect, 4, 4)

                if not is_active and fade_t is None and not is_black:
                    grad = QLinearGradient(x, y, x, y + kh)
                    grad.setColorAt(0, QColor(48, 48, 48))
                    grad.setColorAt(1, _COLOR_NATURAL)
                    painter.fillPath(path, grad)
                else:
                    painter.fillPath(path, QBrush(bg))

                # Glow effect for active keys
                if is_active:
                    glow_rect = QRectF(x - 2, y - 2, kw + 4, kh + 4)
                    glow_path = QPainterPath()
                    glow_path.addRoundedRect(glow_rect, 6, 6)
                    glow_alpha = int(50 * brightness)
                    painter.fillPath(glow_path, QColor(29, 185, 84, min(glow_alpha, 100)))
                    # Redraw key on top
                    painter.fillPath(path, QBrush(bg))
                    # Bright border
                    painter.setPen(QPen(QColor(29, 185, 84, int(120 * brightness)), 1.5))
                    painter.drawPath(path)
                else:
                    painter.setPen(QPen(_COLOR_BORDER, 0.5))
                    painter.drawPath(path)

                # Text
                text_color = (
                    _COLOR_TEXT_LIGHT if is_active
                    else (_COLOR_TEXT_DIM if not is_black else QColor(140, 140, 140))
                )
                painter.setPen(text_color)

                if mapping:
                    painter.setFont(font)
                    painter.drawText(
                        int(x), int(y), int(kw), int(kh * 0.6),
                        Qt.AlignmentFlag.AlignCenter, mapping.label,
                    )

                note_name = KeyMapper.note_name(midi_note)
                painter.setFont(small_font)
                painter.drawText(
                    int(x), int(y + kh * 0.5), int(kw), int(kh * 0.45),
                    Qt.AlignmentFlag.AlignCenter, note_name,
                )

        painter.end()


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
        int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )


def _brighten(c: QColor, factor: float) -> QColor:
    """Multiply RGB by factor (capped at 255)."""
    return QColor(
        min(255, int(c.red() * factor)),
        min(255, int(c.green() * factor)),
        min(255, int(c.blue() * factor)),
        c.alpha(),
    )
