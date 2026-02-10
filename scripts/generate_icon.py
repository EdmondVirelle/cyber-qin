"""Generate application icon (assets/icon.ico) using QPainter + Pillow.

Draws a circular background with a music note in 賽博琴仙 style,
then exports multi-resolution .ico via Pillow.

Usage:
    python scripts/generate_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath

    from cyber_qin.gui.icons import draw_music_note

    try:
        from PIL import Image
    except ImportError:
        print("ERROR: Pillow is required. Install with: pip install pillow")
        sys.exit(1)

    sizes = [16, 32, 48, 64, 128, 256]
    images: list[Image.Image] = []

    bg_color = QColor("#0A0E14")       # 墨黑底
    circle_color = QColor("#D4A853")   # 金墨
    note_color = QColor("#E8E0D0")     # 宣紙白

    for size in sizes:
        img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Circular background
        path = QPainterPath()
        margin = size * 0.04
        path.addEllipse(QRectF(margin, margin, size - margin * 2, size - margin * 2))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawPath(path)

        # Gold ring
        from PyQt6.QtGui import QPen

        ring_width = max(1, size * 0.06)
        pen = QPen(circle_color, ring_width)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inset = margin + ring_width / 2
        painter.drawEllipse(QRectF(inset, inset, size - inset * 2, size - inset * 2))

        # Music note
        note_margin = size * 0.2
        note_rect = QRectF(note_margin, note_margin, size - note_margin * 2, size - note_margin * 2)
        draw_music_note(painter, note_rect, note_color)

        painter.end()

        # Convert QImage → PIL Image
        bits = img.bits()
        bits.setsize(img.sizeInBytes())
        pil_img = Image.frombytes("RGBA", (size, size), bytes(bits), "raw", "BGRA")
        images.append(pil_img)

    # Save as .ico with all sizes
    out_path = PROJECT_ROOT / "assets" / "icon.ico"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    images[-1].save(str(out_path), format="ICO", sizes=[(s, s) for s in sizes], append_images=images[:-1])
    print(f"Icon saved to {out_path} ({', '.join(f'{s}x{s}' for s in sizes)})")


if __name__ == "__main__":
    # Need QApplication for QPainter
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    main()
