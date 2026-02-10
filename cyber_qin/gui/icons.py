"""QPainter-based vector icon drawing functions.

Replaces Unicode characters with crisp, resolution-independent icons.
All draw functions take (painter, rect, color) and render into the given QRectF.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen


def draw_play(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Equilateral triangle pointing right (play icon)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)

    # Inset slightly and shift right to visually center the triangle
    m = rect.width() * 0.22
    r = rect.adjusted(m + rect.width() * 0.05, m, -m + rect.width() * 0.05, -m)

    path = QPainterPath()
    path.moveTo(r.left(), r.top())
    path.lineTo(r.right(), r.center().y())
    path.lineTo(r.left(), r.bottom())
    path.closeSubpath()
    painter.drawPath(path)
    painter.restore()


def draw_pause(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Two rounded vertical bars (pause icon)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)

    m = rect.width() * 0.26
    r = rect.adjusted(m, m, -m, -m)
    bar_w = r.width() * 0.3
    gap = r.width() * 0.15
    radius = bar_w * 0.3

    x1 = r.center().x() - gap - bar_w
    x2 = r.center().x() + gap

    path = QPainterPath()
    path.addRoundedRect(QRectF(x1, r.top(), bar_w, r.height()), radius, radius)
    path.addRoundedRect(QRectF(x2, r.top(), bar_w, r.height()), radius, radius)
    painter.drawPath(path)
    painter.restore()


def draw_stop(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Rounded square (stop icon)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)

    m = rect.width() * 0.28
    r = rect.adjusted(m, m, -m, -m)
    radius = r.width() * 0.15

    path = QPainterPath()
    path.addRoundedRect(r, radius, radius)
    painter.drawPath(path)
    painter.restore()


def draw_refresh(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Circular arrow (refresh icon)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    m = rect.width() * 0.24
    r = rect.adjusted(m, m, -m, -m)
    cx, cy = r.center().x(), r.center().y()
    radius = r.width() / 2

    pen = QPen(color, rect.width() * 0.08)
    pen.setCapStyle(Qt.PenStyle.RoundCap if hasattr(Qt.PenStyle, 'RoundCap') else Qt.PenStyle.NoPen)
    pen.setCapStyle(Qt.PenStyle.NoPen)
    painter.setPen(QPen(color, rect.width() * 0.08, cap=Qt.PenStyle.NoPen))

    # Draw arc (270 degrees)
    arc_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
    pen = QPen(color, rect.width() * 0.08)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(arc_rect, 60 * 16, 270 * 16)  # Qt uses 1/16th degrees

    # Arrow head at end of arc
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    angle_rad = math.radians(60)
    tip_x = cx + radius * math.cos(angle_rad)
    tip_y = cy - radius * math.sin(angle_rad)
    arrow_size = rect.width() * 0.14

    arrow = QPainterPath()
    arrow.moveTo(tip_x, tip_y)
    arrow.lineTo(tip_x + arrow_size, tip_y + arrow_size * 0.6)
    arrow.lineTo(tip_x - arrow_size * 0.3, tip_y + arrow_size * 0.3)
    arrow.closeSubpath()
    painter.drawPath(arrow)
    painter.restore()


def draw_plus(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Plus sign (add icon)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    m = rect.width() * 0.26
    r = rect.adjusted(m, m, -m, -m)
    thickness = rect.width() * 0.08

    pen = QPen(color, thickness)
    pen.setCapStyle(Qt.PenStyle.NoPen)
    painter.setPen(QPen(color, thickness))

    # Horizontal
    painter.drawLine(
        QPointF(r.left(), r.center().y()),
        QPointF(r.right(), r.center().y()),
    )
    # Vertical
    painter.drawLine(
        QPointF(r.center().x(), r.top()),
        QPointF(r.center().x(), r.bottom()),
    )
    painter.restore()


def draw_remove(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """X mark (remove/close icon)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    m = rect.width() * 0.28
    r = rect.adjusted(m, m, -m, -m)
    thickness = rect.width() * 0.08

    painter.setPen(QPen(color, thickness))
    painter.drawLine(QPointF(r.left(), r.top()), QPointF(r.right(), r.bottom()))
    painter.drawLine(QPointF(r.right(), r.top()), QPointF(r.left(), r.bottom()))
    painter.restore()


def draw_music_note(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Music note icon (eighth note)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)

    m = rect.width() * 0.2
    r = rect.adjusted(m, m, -m, -m)

    # Note head (oval)
    head_w = r.width() * 0.45
    head_h = r.height() * 0.3
    head_x = r.left() + r.width() * 0.1
    head_y = r.bottom() - head_h

    painter.drawEllipse(QRectF(head_x, head_y, head_w, head_h))

    # Stem
    stem_x = head_x + head_w - r.width() * 0.04
    stem_bottom = head_y + head_h * 0.3
    stem_top = r.top() + r.height() * 0.1

    painter.setPen(QPen(color, r.width() * 0.08))
    painter.drawLine(QPointF(stem_x, stem_bottom), QPointF(stem_x, stem_top))

    # Flag
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    flag = QPainterPath()
    flag.moveTo(stem_x, stem_top)
    flag.cubicTo(
        stem_x + r.width() * 0.4, stem_top + r.height() * 0.1,
        stem_x + r.width() * 0.3, stem_top + r.height() * 0.35,
        stem_x, stem_top + r.height() * 0.4,
    )
    flag.lineTo(stem_x, stem_top)
    painter.drawPath(flag)
    painter.restore()


def draw_skip_next(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Skip-next icon: right-pointing triangle + vertical bar."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)

    m = rect.width() * 0.26
    r = rect.adjusted(m, m, -m, -m)

    # Triangle
    path = QPainterPath()
    path.moveTo(r.left(), r.top())
    path.lineTo(r.left() + r.width() * 0.65, r.center().y())
    path.lineTo(r.left(), r.bottom())
    path.closeSubpath()
    painter.drawPath(path)

    # Bar
    bar_w = r.width() * 0.15
    bar_x = r.right() - bar_w
    bar_path = QPainterPath()
    bar_path.addRoundedRect(QRectF(bar_x, r.top(), bar_w, r.height()), bar_w * 0.3, bar_w * 0.3)
    painter.drawPath(bar_path)
    painter.restore()


def draw_skip_prev(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Skip-prev icon: vertical bar + left-pointing triangle."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)

    m = rect.width() * 0.26
    r = rect.adjusted(m, m, -m, -m)

    # Bar
    bar_w = r.width() * 0.15
    bar_path = QPainterPath()
    bar_path.addRoundedRect(QRectF(r.left(), r.top(), bar_w, r.height()), bar_w * 0.3, bar_w * 0.3)
    painter.drawPath(bar_path)

    # Triangle (pointing left)
    path = QPainterPath()
    path.moveTo(r.right(), r.top())
    path.lineTo(r.left() + r.width() * 0.35, r.center().y())
    path.lineTo(r.right(), r.bottom())
    path.closeSubpath()
    painter.drawPath(path)
    painter.restore()


def draw_repeat(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Repeat icon: two arrows forming a loop."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    m = rect.width() * 0.24
    r = rect.adjusted(m, m, -m, -m)
    pen_w = rect.width() * 0.07
    painter.setPen(QPen(color, pen_w))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    # Top-right arrow path (right to left)
    rad = r.height() * 0.3
    top_y = r.top() + rad
    bot_y = r.bottom() - rad

    # Draw the loop path
    path = QPainterPath()
    path.moveTo(r.right() - r.width() * 0.2, r.top())
    path.lineTo(r.right() - rad, r.top())
    path.arcTo(QRectF(r.right() - rad * 2, r.top(), rad * 2, rad * 2), 90, -90)
    path.lineTo(r.right(), bot_y)
    path.arcTo(QRectF(r.right() - rad * 2, r.bottom() - rad * 2, rad * 2, rad * 2), 0, -90)
    path.lineTo(r.left() + r.width() * 0.2, r.bottom())
    painter.drawPath(path)

    path2 = QPainterPath()
    path2.moveTo(r.left() + r.width() * 0.2, r.bottom())
    path2.lineTo(r.left() + rad, r.bottom())
    path2.arcTo(QRectF(r.left(), r.bottom() - rad * 2, rad * 2, rad * 2), 270, -90)
    path2.lineTo(r.left(), top_y)
    path2.arcTo(QRectF(r.left(), r.top(), rad * 2, rad * 2), 180, -90)
    path2.lineTo(r.right() - r.width() * 0.2, r.top())
    painter.drawPath(path2)

    # Arrow heads
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    arr = rect.width() * 0.1

    # Top-left arrow (pointing right)
    ax = r.right() - r.width() * 0.2
    ay = r.top()
    arrow = QPainterPath()
    arrow.moveTo(ax + arr, ay)
    arrow.lineTo(ax - arr * 0.5, ay - arr)
    arrow.lineTo(ax - arr * 0.5, ay + arr)
    arrow.closeSubpath()
    painter.drawPath(arrow)

    # Bottom-right arrow (pointing left)
    bx = r.left() + r.width() * 0.2
    by = r.bottom()
    arrow2 = QPainterPath()
    arrow2.moveTo(bx - arr, by)
    arrow2.lineTo(bx + arr * 0.5, by - arr)
    arrow2.lineTo(bx + arr * 0.5, by + arr)
    arrow2.closeSubpath()
    painter.drawPath(arrow2)

    painter.restore()


def draw_repeat_one(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Repeat-one icon: repeat loop with a '1' in the center."""
    draw_repeat(painter, rect, color)

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw "1" in center
    painter.setPen(color)
    font = painter.font()
    font.setPixelSize(int(rect.width() * 0.32))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(rect.toRect(), Qt.AlignmentFlag.AlignCenter, "1")
    painter.restore()


def draw_live(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Waveform icon (live mode)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    m = rect.width() * 0.22
    r = rect.adjusted(m, m, -m, -m)
    pen = QPen(color, rect.width() * 0.07)
    painter.setPen(pen)

    bars = 5
    bar_w = r.width() / (bars * 2 - 1)
    heights = [0.4, 0.8, 1.0, 0.6, 0.3]

    for i, h_ratio in enumerate(heights):
        x = r.left() + i * bar_w * 2 + bar_w / 2
        bar_h = r.height() * h_ratio
        y_top = r.center().y() - bar_h / 2
        y_bot = r.center().y() + bar_h / 2
        painter.drawLine(QPointF(x, y_top), QPointF(x, y_bot))

    painter.restore()


def draw_library(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Grid/folder icon (library mode)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)

    m = rect.width() * 0.24
    r = rect.adjusted(m, m, -m, -m)
    gap = r.width() * 0.12
    cell = (r.width() - gap) / 2
    radius = cell * 0.2

    # 2x2 grid
    positions = [
        (r.left(), r.top()),
        (r.left() + cell + gap, r.top()),
        (r.left(), r.top() + cell + gap),
        (r.left() + cell + gap, r.top() + cell + gap),
    ]
    for x, y in positions:
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, cell, cell), radius, radius)
        painter.drawPath(path)

    painter.restore()
