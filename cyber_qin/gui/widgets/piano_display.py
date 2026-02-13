"""Visual piano display widget with glow effects and dynamic scheme-based layout."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QWidget

from ...core.constants import Modifier
from ...core.key_mapper import KeyMapper

if TYPE_CHECKING:
    from ...core.key_mapper import KeyMapping

# Which semitones in the octave are "black keys" (sharps/flats)
_BLACK_SEMITONES = {1, 3, 6, 8, 10}

# 賽博墨韻 colors
_COLOR_NATURAL = QColor(0x1A, 0x23, 0x32)  # #1A2332 宣紙暗面
_COLOR_SHARP = QColor(0x1A, 0x14, 0x28)  # #1A1428 深紫墨
_COLOR_FLAT = QColor(0x14, 0x1A, 0x2E)  # #141A2E 深藍墨
_COLOR_ACTIVE = QColor(0x00, 0xF0, 0xFF)  # #00F0FF 賽博青
_COLOR_ACTIVE_DARK = QColor(0x00, 0x8B, 0x99)  # #008B99 暗青
_COLOR_BORDER = QColor(0x2E, 0x3D, 0x50)  # #2E3D50 雲霧層
_COLOR_TEXT_LIGHT = QColor(0xE8, 0xE0, 0xD0)  # #E8E0D0 宣紙白
_COLOR_TEXT_DIM = QColor(0x7A, 0x88, 0x99)  # #7A8899 水墨灰

_FLASH_DURATION = 0.15  # seconds — bright flash on note-on
_FADE_DURATION = 0.25  # seconds — fade after note-off

# Label abbreviation map
_MODIFIER_ABBREV = {
    "Shift+": "\u21e7",  # ⇧
    "Ctrl+": "^",
}


def _abbreviate_label(label: str) -> str:
    """Shorten modifier labels: 'Shift+Q' → '⇧Q', 'Ctrl+E' → '^E'."""
    for prefix, abbrev in _MODIFIER_ABBREV.items():
        if label.startswith(prefix):
            return abbrev + label[len(prefix) :]
    return label


class PianoDisplay(QWidget):
    """Visual piano showing active notes with glow and flash effects.

    Dynamically adapts layout to the current mapping scheme.
    """

    def __init__(
        self,
        mapper: KeyMapper | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mapper = mapper
        self._active_notes: set[int] = set()
        self._flash_notes: dict[int, float] = {}  # midi_note -> note_on time
        self._fade_notes: dict[int, float] = {}  # midi_note -> note_off time
        self.setMinimumHeight(180)
        self.setMinimumWidth(480)

        self._rows: list[list[int]] = []
        self._keys_per_row: int = 12
        self._rebuild_layout()

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.setInterval(16)  # ~60fps

    def _rebuild_layout(self) -> None:
        """Recompute row layout from the current mapper scheme."""
        scheme = self._mapper.scheme if self._mapper else None

        if scheme is not None:
            rows_count = scheme.rows
            kpr = scheme.keys_per_row
            midi_min = scheme.midi_range[0]
            self._keys_per_row = kpr
            self._rows = []
            # Build rows from top (highest) to bottom (lowest)
            for row_idx in range(rows_count):
                # Rows go top=highest, bottom=lowest
                inv = rows_count - 1 - row_idx
                start = midi_min + inv * kpr
                self._rows.append(list(range(start, start + kpr)))
        else:
            # Default 36-key layout: 3×12
            self._keys_per_row = 12
            self._rows = [
                list(range(72, 84)),  # High: C5-B5
                list(range(60, 72)),  # Mid:  C4-B4
                list(range(48, 60)),  # Low:  C3-B3
            ]

    def on_scheme_changed(self) -> None:
        """Rebuild layout when the mapping scheme changes."""
        self._rebuild_layout()
        self._active_notes.clear()
        self._flash_notes.clear()
        self._fade_notes.clear()
        self.update()

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
        expired_flash = [n for n, t in self._flash_notes.items() if now - t > _FLASH_DURATION]
        for n in expired_flash:
            del self._flash_notes[n]
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
        num_rows = len(self._rows)
        if num_rows == 0:
            painter.end()
            return

        row_h = (h - pad * 2) / num_rows
        key_w = (w - pad * 2) / self._keys_per_row

        # Adaptive base font size
        base_font_size = max(7, int(min(key_w / 4.0, row_h / 4.0)))
        font = QFont("Microsoft JhengHei", base_font_size)
        font.setWeight(QFont.Weight.DemiBold)
        small_font = QFont("Microsoft JhengHei", max(6, base_font_size - 2))

        now = time.monotonic()
        mapping_dict = self._mapper.current_mappings() if self._mapper else {}

        # Clip to rounded container
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), 10, 10)
        painter.setClipPath(clip)

        # Background gradient — 墨色
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0, QColor(0x10, 0x18, 0x20))
        bg_grad.setColorAt(1, QColor(0x0A, 0x0E, 0x14))
        painter.fillRect(0, 0, w, h, bg_grad)

        for row_idx, row_notes in enumerate(self._rows):
            for col, midi_note in enumerate(row_notes):
                x = pad + col * key_w
                y = pad + row_idx * row_h
                kw = key_w - 1
                kh = row_h - 1

                mapping: KeyMapping | None = mapping_dict.get(midi_note)
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
                    brightness = 1.0 + 0.3 * ratio

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
                    bg = (
                        _COLOR_FLAT
                        if (mapping and mapping.modifier == Modifier.CTRL)
                        else _COLOR_SHARP
                    )
                else:
                    bg = _COLOR_NATURAL

                key_rect = QRectF(x, y, kw, kh)

                path = QPainterPath()
                path.addRoundedRect(key_rect, 4, 4)

                if not is_active and fade_t is None and not is_black:
                    grad = QLinearGradient(x, y, x, y + kh)
                    grad.setColorAt(0, QColor(0x24, 0x30, 0x40))
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
                    painter.fillPath(glow_path, QColor(0, 240, 255, min(glow_alpha, 100)))
                    painter.fillPath(path, QBrush(bg))
                    painter.setPen(QPen(QColor(0, 240, 255, int(120 * brightness)), 1.5))
                    painter.drawPath(path)
                else:
                    painter.setPen(QPen(_COLOR_BORDER, 0.5))
                    painter.drawPath(path)

                # Text
                text_color = (
                    _COLOR_TEXT_LIGHT
                    if is_active
                    else (_COLOR_TEXT_DIM if not is_black else QColor(0x5A, 0x68, 0x78))
                )
                painter.setPen(text_color)

                if mapping:
                    label = _abbreviate_label(mapping.label)

                    # Adaptive font: shrink if label is too wide
                    label_font = QFont(font)
                    fm = QFontMetrics(label_font)
                    max_label_w = int(kw * 0.9)
                    while fm.horizontalAdvance(label) > max_label_w and label_font.pointSize() > 6:
                        label_font.setPointSize(label_font.pointSize() - 1)
                        fm = QFontMetrics(label_font)

                    painter.setFont(label_font)
                    painter.drawText(
                        int(x),
                        int(y),
                        int(kw),
                        int(kh * 0.55),
                        Qt.AlignmentFlag.AlignCenter,
                        label,
                    )

                note_name = KeyMapper.note_name(midi_note)
                painter.setFont(small_font)
                painter.drawText(
                    int(x),
                    int(y + kh * 0.55),
                    int(kw),
                    int(kh * 0.42),
                    Qt.AlignmentFlag.AlignCenter,
                    note_name,
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
