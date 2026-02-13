"""Score view widget — standard music notation rendering with QPainter."""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from ...core.beat_sequence import BeatNote
from ...core.notation_renderer import (
    NotationData,
    NoteHeadType,
    render_notation,
)
from ..theme import BG_INK, DIVIDER, TEXT_PRIMARY, TEXT_SECONDARY

# Layout constants
_STAFF_LINE_SPACING = 10  # pixels between staff lines
_STAFF_TOP_MARGIN = 60
_LEFT_MARGIN = 60
_BAR_WIDTH = 200  # base width per bar
_CLEF_WIDTH = 30
_NOTE_HEAD_RX = 5.5  # note head ellipse radii
_NOTE_HEAD_RY = 4.0
_STEM_HEIGHT = 35
_BEAM_THICKNESS = 3
_LEDGER_EXTENSION = 6


class ScoreViewWidget(QWidget):
    """Read-only standard notation view of BeatNote sequences."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._notation: NotationData | None = None
        self._notes: list[BeatNote] = []
        self._tempo_bpm: float = 120.0
        self._time_signature: tuple[int, int] = (4, 4)
        self._key_signature: int = 0
        self._scroll_x: float = 0.0
        self.setMinimumHeight(200)

    def set_notes(
        self,
        notes: list[BeatNote],
        *,
        tempo_bpm: float = 120.0,
        time_signature: tuple[int, int] = (4, 4),
        key_signature: int = 0,
    ) -> None:
        self._notes = notes
        self._tempo_bpm = tempo_bpm
        self._time_signature = time_signature
        self._key_signature = key_signature
        self._notation = render_notation(
            notes,
            tempo_bpm=tempo_bpm,
            time_signature=time_signature,
            key_signature=key_signature,
        )
        self.update()

    def set_scroll_x(self, value: float) -> None:
        self._scroll_x = value
        self.update()

    def clear(self) -> None:
        self._notation = None
        self._notes = []
        self.update()

    # ── Coordinate helpers ──────────────────────────────────

    def _staff_y(self, staff_line: float) -> float:
        """Convert staff line number to y coordinate.

        Line 0 = bottom line (E4), line 4 = top line (F5).
        """
        return _STAFF_TOP_MARGIN + (4 - staff_line) * _STAFF_LINE_SPACING

    # ── Paint ───────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(BG_INK))

        if not self._notation or not self._notation.notes:
            painter.setPen(QColor(TEXT_SECONDARY))
            painter.setFont(QFont("Microsoft JhengHei", 10))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "No notes to display")
            painter.end()
            return

        # Draw staff lines
        self._draw_staff(painter, w)

        # Draw clef
        self._draw_treble_clef(painter)

        # Draw notes
        self._draw_notes(painter, w)

        # Draw bar lines
        self._draw_bar_lines(painter, w, h)

        painter.end()

    def _draw_staff(self, painter: QPainter, width: float) -> None:
        """Draw 5 staff lines."""
        pen = QPen(QColor(DIVIDER), 1.0)
        painter.setPen(pen)
        for line in range(5):
            y = self._staff_y(line)
            painter.drawLine(0, int(y), int(width), int(y))

    def _draw_treble_clef(self, painter: QPainter) -> None:
        """Draw a simplified treble clef symbol."""
        painter.setPen(QColor(TEXT_PRIMARY))
        font = QFont("Times New Roman", 36)
        painter.setFont(font)
        # Unicode treble clef
        y = self._staff_y(2) + 18
        painter.drawText(int(8 - self._scroll_x), int(y), "\U0001D11E")

    def _draw_notes(self, painter: QPainter, width: float) -> None:
        """Draw note heads, stems, and ledger lines."""
        if not self._notation:
            return

        beats_per_bar = self._time_signature[0] * (4.0 / self._time_signature[1])
        px_per_beat = _BAR_WIDTH / beats_per_bar if beats_per_bar > 0 else _BAR_WIDTH / 4

        for rn in self._notation.notes:
            x = _LEFT_MARGIN + _CLEF_WIDTH + rn.time_beats * px_per_beat - self._scroll_x
            if x + 20 < 0 or x - 20 > width:
                continue

            y = self._staff_y(rn.staff_position)

            # Ledger lines
            if rn.staff_position < 0:
                painter.setPen(QPen(QColor(TEXT_SECONDARY), 1.0))
                for ll in range(0, int(rn.staff_position) - 1, -2):
                    ly = self._staff_y(ll)
                    painter.drawLine(
                        int(x - _NOTE_HEAD_RX - _LEDGER_EXTENSION),
                        int(ly),
                        int(x + _NOTE_HEAD_RX + _LEDGER_EXTENSION),
                        int(ly),
                    )
            elif rn.staff_position > 8:
                painter.setPen(QPen(QColor(TEXT_SECONDARY), 1.0))
                for ll in range(10, int(rn.staff_position) + 2, 2):
                    ly = self._staff_y(ll)
                    painter.drawLine(
                        int(x - _NOTE_HEAD_RX - _LEDGER_EXTENSION),
                        int(ly),
                        int(x + _NOTE_HEAD_RX + _LEDGER_EXTENSION),
                        int(ly),
                    )

            # Middle C ledger line
            if rn.staff_position == -2:
                painter.setPen(QPen(QColor(TEXT_SECONDARY), 1.0))
                ly = self._staff_y(-2)
                painter.drawLine(
                    int(x - _NOTE_HEAD_RX - _LEDGER_EXTENSION),
                    int(ly),
                    int(x + _NOTE_HEAD_RX + _LEDGER_EXTENSION),
                    int(ly),
                )

            # Note head
            filled = rn.head_type in (NoteHeadType.QUARTER, NoteHeadType.EIGHTH, NoteHeadType.SIXTEENTH)
            painter.setPen(QPen(QColor(TEXT_PRIMARY), 1.2))
            if filled:
                painter.setBrush(QColor(TEXT_PRIMARY))
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)

            head_path = QPainterPath()
            head_path.addEllipse(QPointF(x, y), _NOTE_HEAD_RX, _NOTE_HEAD_RY)
            painter.drawPath(head_path)

            # Dot for dotted notes
            if rn.dotted:
                painter.setBrush(QColor(TEXT_PRIMARY))
                painter.drawEllipse(QPointF(x + _NOTE_HEAD_RX + 4, y), 1.5, 1.5)

            # Stem (not for whole notes)
            if rn.head_type != NoteHeadType.WHOLE:
                stem_up = rn.stem_up
                if stem_up:
                    sx = x + _NOTE_HEAD_RX - 0.5
                    painter.drawLine(int(sx), int(y), int(sx), int(y - _STEM_HEIGHT))
                else:
                    sx = x - _NOTE_HEAD_RX + 0.5
                    painter.drawLine(int(sx), int(y), int(sx), int(y + _STEM_HEIGHT))

            # Flag for eighth/sixteenth notes (simplified)
            if rn.head_type == NoteHeadType.EIGHTH and not rn.beam_group:
                self._draw_flag(painter, x, y, rn.stem_up, 1)
            elif rn.head_type == NoteHeadType.SIXTEENTH and not rn.beam_group:
                self._draw_flag(painter, x, y, rn.stem_up, 2)

            # Accidental
            if rn.accidental:
                painter.setPen(QColor(TEXT_PRIMARY))
                painter.setFont(QFont("Times New Roman", 12))
                acc_symbol = {"sharp": "#", "flat": "b", "natural": "\u266E"}.get(rn.accidental, "")
                painter.drawText(int(x - _NOTE_HEAD_RX - 12), int(y + 4), acc_symbol)

    def _draw_flag(self, painter: QPainter, x: float, y: float, stem_up: bool, count: int) -> None:
        """Draw note flag(s)."""
        painter.setPen(QPen(QColor(TEXT_PRIMARY), 1.5))
        if stem_up:
            sx = x + _NOTE_HEAD_RX - 0.5
            sy = y - _STEM_HEIGHT
            for i in range(count):
                fy = sy + i * 8
                path = QPainterPath()
                path.moveTo(sx, fy)
                path.cubicTo(sx + 8, fy + 6, sx + 4, fy + 12, sx + 2, fy + 16)
                painter.drawPath(path)
        else:
            sx = x - _NOTE_HEAD_RX + 0.5
            sy = y + _STEM_HEIGHT
            for i in range(count):
                fy = sy - i * 8
                path = QPainterPath()
                path.moveTo(sx, fy)
                path.cubicTo(sx - 8, fy - 6, sx - 4, fy - 12, sx - 2, fy - 16)
                painter.drawPath(path)

    def _draw_bar_lines(self, painter: QPainter, width: float, height: float) -> None:
        """Draw vertical bar lines."""
        if not self._notation:
            return

        beats_per_bar = self._time_signature[0] * (4.0 / self._time_signature[1])
        if beats_per_bar <= 0:
            return

        px_per_beat = _BAR_WIDTH / beats_per_bar
        total_beats = self._notation.total_beats
        num_bars = math.ceil(total_beats / beats_per_bar) + 1

        painter.setPen(QPen(QColor(TEXT_SECONDARY), 1.0))
        top_y = self._staff_y(4)
        bottom_y = self._staff_y(0)

        for bar in range(num_bars + 1):
            x = _LEFT_MARGIN + _CLEF_WIDTH + bar * beats_per_bar * px_per_beat - self._scroll_x
            if 0 <= x <= width:
                painter.drawLine(int(x), int(top_y), int(x), int(bottom_y))
