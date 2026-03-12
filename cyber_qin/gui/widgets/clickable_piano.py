"""Interactive piano widget — click to input notes.

Scheme-aware multi-row layout with game key labels.
When a KeyMapper is provided, renders the same 3×12 grid as PianoDisplay
(for WWM 36-key) with keybinding labels and note names.
Falls back to a flat single-row layout when no mapper is set.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
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

from ...core.constants import MIDI_NOTE_MIN, Modifier
from ...core.key_mapper import KeyMapper

if TYPE_CHECKING:
    from ...core.key_mapper import KeyMapping

# Which semitones in the octave are "black keys"
_BLACK_SEMITONES = {1, 3, 6, 8, 10}

# Colors matching PianoDisplay
_COLOR_NATURAL = QColor(0x1A, 0x23, 0x32)
_COLOR_SHARP = QColor(0x1A, 0x14, 0x28)
_COLOR_FLAT = QColor(0x14, 0x1A, 0x2E)
_COLOR_ACTIVE = QColor(0x00, 0xF0, 0xFF)
_COLOR_ACTIVE_DARK = QColor(0x00, 0x8B, 0x99)
_COLOR_BORDER = QColor(0x2E, 0x3D, 0x50)
_COLOR_TEXT_LIGHT = QColor(0xE8, 0xE0, 0xD0)
_COLOR_TEXT_DIM = QColor(0x7A, 0x88, 0x99)
_COLOR_TEXT_BLACK_KEY = QColor(0x5A, 0x68, 0x78)

_FLASH_DURATION = 0.15
_FADE_DURATION = 0.25

# Note names
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Label abbreviation map (same as PianoDisplay)
_MODIFIER_ABBREV = {
    "Shift+": "\u21e7",  # ⇧
    "Ctrl+": "^",
}


def _abbreviate_label(label: str) -> str:
    """Shorten modifier labels: 'Shift+Q' -> '⇧Q', 'Ctrl+E' -> '^E'."""
    for prefix, abbrev in _MODIFIER_ABBREV.items():
        if label.startswith(prefix):
            return abbrev + label[len(prefix):]
    return label


class ClickablePiano(QWidget):
    """Interactive piano keyboard for note input.

    Supports two modes:
    - With mapper: multi-row grid layout matching the scheme (3×12 for WWM 36-key)
      with game keybinding labels.
    - Without mapper: flat single-row layout (legacy).
    """

    note_clicked = pyqtSignal(int)  # midi_note
    note_pressed = pyqtSignal(int)  # midi_note (mouse down)
    note_released = pyqtSignal(int)  # midi_note (mouse up)

    def __init__(
        self,
        mapper: KeyMapper | None = None,
        midi_min: int = MIDI_NOTE_MIN,
        midi_max: int = 83,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mapper = mapper
        self._midi_min = midi_min
        self._midi_max = midi_max
        self._pressed_note: int | None = None
        self._hover_note: int | None = None
        self.setMinimumWidth(400)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Multi-row layout
        self._rows: list[list[int]] = []
        self._keys_per_row: int = 12
        self._rebuild_layout()

        # Visual feedback state
        self._active_notes: set[int] = set()
        self._flash_notes: dict[int, float] = {}
        self._fade_notes: dict[int, float] = {}

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.setInterval(16)

    def set_mapper(self, mapper: KeyMapper | None) -> None:
        """Set or update the key mapper and rebuild layout."""
        self._mapper = mapper
        self._pressed_note = None
        self._hover_note = None
        self._rebuild_layout()
        self.update()

    def _rebuild_layout(self) -> None:
        """Recompute row layout from the current mapper scheme.

        Derives rows from the actual mapping keys so that schemes with
        variable-length rows (e.g. beginner_36: 7+9+10+10) work correctly.
        """
        scheme = self._mapper.scheme if self._mapper else None

        if scheme is not None:
            all_notes = sorted(scheme.mapping.keys())
            kpr = scheme.keys_per_row
            self._keys_per_row = kpr
            self._rows = []
            # Chunk notes into rows of `kpr` each
            chunks = [all_notes[i : i + kpr] for i in range(0, len(all_notes), kpr)]
            # Highest notes at top (row 0) → reverse
            for chunk in reversed(chunks):
                self._rows.append(chunk)
            self.setFixedHeight(max(120, 50 * len(self._rows)))
        else:
            # Flat single-row fallback
            self._rows = [list(range(self._midi_min, self._midi_max + 1))]
            self._keys_per_row = self._midi_max - self._midi_min + 1
            self.setFixedHeight(80)

    def on_scheme_changed(self) -> None:
        """Rebuild layout when the mapping scheme changes."""
        self._pressed_note = None
        self._hover_note = None
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

    def _note_at_pos(self, x: float, y: float) -> int | None:
        """Hit-test: return MIDI note at pixel position, or None."""
        w = self.width()
        h = self.height()
        pad = 2
        num_rows = len(self._rows)
        if num_rows == 0 or x < pad or x >= w - pad or y < pad or y >= h - pad:
            return None

        row_h = (h - pad * 2) / num_rows
        key_w = (w - pad * 2) / self._keys_per_row

        row_idx = int((y - pad) / row_h)
        row_idx = max(0, min(row_idx, num_rows - 1))

        col_idx = int((x - pad) / key_w)
        row_notes = self._rows[row_idx]
        if col_idx >= len(row_notes):
            return None
        col_idx = max(0, min(col_idx, len(row_notes) - 1))
        return row_notes[col_idx]

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
        pad = 2
        num_rows = len(self._rows)
        if num_rows == 0:
            painter.end()
            return

        row_h = (h - pad * 2) / num_rows
        key_w = (w - pad * 2) / self._keys_per_row

        # Adaptive fonts
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

        # Background gradient
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
                is_pressed = midi_note == self._pressed_note
                is_hover = midi_note == self._hover_note
                semitone = midi_note % 12
                is_black = semitone in _BLACK_SEMITONES

                flash_t = self._flash_notes.get(midi_note)
                fade_t = self._fade_notes.get(midi_note)

                # Brightness for flash
                brightness = 1.0
                if is_active and flash_t is not None:
                    elapsed = now - flash_t
                    ratio = max(0.0, 1.0 - elapsed / _FLASH_DURATION)
                    brightness = 1.0 + 0.3 * ratio

                # Background color
                if is_pressed:
                    bg = _COLOR_ACTIVE
                elif is_active:
                    base_bg = _COLOR_ACTIVE if not is_black else _COLOR_ACTIVE_DARK
                    bg = _brighten(base_bg, brightness)
                elif is_hover:
                    bg = QColor(0x00, 0xF0, 0xFF, 60)
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

                if not (is_pressed or is_active or is_hover) and fade_t is None and not is_black:
                    grad = QLinearGradient(x, y, x, y + kh)
                    grad.setColorAt(0, QColor(0x24, 0x30, 0x40))
                    grad.setColorAt(1, _COLOR_NATURAL)
                    painter.fillPath(path, grad)
                else:
                    painter.fillPath(path, QBrush(bg))

                # Glow / border
                if is_pressed or is_active:
                    glow_rect = QRectF(x - 2, y - 2, kw + 4, kh + 4)
                    glow_path = QPainterPath()
                    glow_path.addRoundedRect(glow_rect, 6, 6)
                    glow_alpha = int(50 * brightness)
                    painter.fillPath(glow_path, QColor(0, 240, 255, min(glow_alpha, 100)))
                    painter.setPen(QPen(QColor(0, 240, 255, int(120 * brightness)), 1.5))
                    painter.drawPath(path)
                else:
                    painter.setPen(QPen(_COLOR_BORDER, 0.5))
                    painter.drawPath(path)

                # Text
                text_color = (
                    _COLOR_TEXT_LIGHT
                    if (is_pressed or is_active)
                    else (_COLOR_TEXT_DIM if not is_black else _COLOR_TEXT_BLACK_KEY)
                )
                painter.setPen(text_color)

                # Keybinding label (upper half)
                if mapping:
                    label = _abbreviate_label(mapping.label)

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

                # Note name (lower half)
                note_name = _NOTE_NAMES[semitone]
                octave = midi_note // 12 - 1
                note_label = f"{note_name}{octave}"
                painter.setFont(small_font)
                painter.drawText(
                    int(x),
                    int(y + kh * 0.55),
                    int(kw),
                    int(kh * 0.42),
                    Qt.AlignmentFlag.AlignCenter,
                    note_label,
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
    return QColor(
        min(255, int(c.red() * factor)),
        min(255, int(c.green() * factor)),
        min(255, int(c.blue() * factor)),
        c.alpha(),
    )
