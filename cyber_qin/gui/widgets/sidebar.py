"""Left navigation sidebar widget with QPainter icons and animations — 賽博墨韻 style."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QVBoxLayout,
    QWidget,
)

from ..icons import draw_music_note
from ..theme import ACCENT_GOLD, BG_SCROLL, DIVIDER, TEXT_SECONDARY
from .animated_widgets import AnimatedNavButton


class Sidebar(QWidget):
    """Navigation sidebar with animated icon buttons and brand logo."""

    navigation_changed = pyqtSignal(int)  # 0=Live, 1=Library, 2=Editor

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(4)

        # Logo area
        self._logo = _BrandLogo()
        layout.addWidget(self._logo)

        layout.addSpacing(12)

        # Rounded divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(
            f"background-color: {DIVIDER}; border-radius: 0.5px;"
            f"margin-left: 16px; margin-right: 16px;"
        )
        layout.addWidget(div)

        layout.addSpacing(8)

        # Navigation buttons
        self._buttons: list[AnimatedNavButton] = []

        self._live_btn = AnimatedNavButton("live", "演奏模式")
        self._live_btn.clicked.connect(lambda: self._on_nav_click(0))
        layout.addWidget(self._live_btn)
        self._buttons.append(self._live_btn)

        self._library_btn = AnimatedNavButton("library", "曲庫")
        self._library_btn.clicked.connect(lambda: self._on_nav_click(1))
        layout.addWidget(self._library_btn)
        self._buttons.append(self._library_btn)

        self._editor_btn = AnimatedNavButton("editor", "編曲器")
        self._editor_btn.clicked.connect(lambda: self._on_nav_click(2))
        layout.addWidget(self._editor_btn)
        self._buttons.append(self._editor_btn)

        layout.addStretch()

        # Bottom divider
        bottom_div = QFrame()
        bottom_div.setFixedHeight(1)
        bottom_div.setStyleSheet(
            f"background-color: {DIVIDER}; border-radius: 0.5px;"
            f"margin-left: 16px; margin-right: 16px;"
        )
        layout.addWidget(bottom_div)
        layout.addSpacing(4)

        # Version label
        from PyQt6.QtWidgets import QLabel

        from cyber_qin import __version__

        ver = QLabel(f"v{__version__}")
        ver.setFont(QFont("Microsoft JhengHei", 9))
        ver.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        # Drop shadow on right edge
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(4, 0)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

        # Set initial active
        self._set_active(0)

    def paintEvent(self, event) -> None:  # noqa: N802
        """Custom paint for sidebar background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(BG_SCROLL))
        painter.end()

    def _on_nav_click(self, index: int) -> None:
        self._set_active(index)
        self.navigation_changed.emit(index)

    def _set_active(self, index: int) -> None:
        for i, btn in enumerate(self._buttons):
            btn.active = i == index


class _BrandLogo(QWidget):
    """Brand logo widget with QPainter music note icon + text — 金墨 accent."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(60)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Music note icon — 金墨
        icon_rect = QRectF(16, 8, 32, 32)
        draw_music_note(painter, icon_rect, QColor(ACCENT_GOLD))

        # Title text — 金墨
        painter.setPen(QColor(ACCENT_GOLD))
        font = QFont("Microsoft JhengHei", 16)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            54, 8, self.width() - 62, 28,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "賽博琴仙",
        )

        # Subtitle
        painter.setPen(QColor(TEXT_SECONDARY))
        sub_font = QFont("Microsoft JhengHei", 9)
        painter.setFont(sub_font)
        painter.drawText(
            54, 34, self.width() - 62, 18,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "Cyber Qin Xian",
        )

        painter.end()
