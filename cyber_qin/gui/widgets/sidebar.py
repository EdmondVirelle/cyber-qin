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

from ...core.translator import translator
from ..icons import draw_music_note
from ..theme import ACCENT_GOLD, BG_SCROLL, DIVIDER, TEXT_SECONDARY
from .animated_widgets import AnimatedNavButton
from .language_selector import LanguageSelector


class Sidebar(QWidget):
    """Navigation sidebar with animated icon buttons and brand logo."""

    navigation_changed = pyqtSignal(int)  # 0=Live, 1=Library, 2=Editor

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 10)
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

        layout.addSpacing(16)

        # Language Selector
        self._lang_selector = LanguageSelector()
        layout.addWidget(self._lang_selector)

        layout.addStretch()

        # Bottom divider
        bottom_div = QFrame()
        bottom_div.setFixedHeight(1)
        bottom_div.setStyleSheet(
            f"background-color: {DIVIDER}; border-radius: 0.5px;"
            f"margin-left: 16px; margin-right: 16px;"
        )
        layout.addWidget(bottom_div)
        layout.addSpacing(2)

        # Credit + Ko-fi + version labels
        from PyQt6.QtWidgets import QLabel

        from cyber_qin import __version__

        self._credit = QLabel(translator.tr("sidebar.credit"))
        self._credit.setFont(QFont("Microsoft JhengHei", 8))
        self._credit.setWordWrap(True)
        self._credit.setContentsMargins(12, 0, 12, 0)
        self._credit.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        self._credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._credit.setToolTip(translator.tr("sidebar.credit"))
        layout.addWidget(self._credit)

        self._ff14 = QLabel(translator.tr("sidebar.ff14"))
        self._ff14.setFont(QFont("Microsoft JhengHei", 8))
        self._ff14.setWordWrap(True)
        self._ff14.setContentsMargins(12, 0, 12, 0)
        self._ff14.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        self._ff14.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._ff14)

        self._wwm = QLabel(translator.tr("sidebar.wwm"))
        self._wwm.setFont(QFont("Microsoft JhengHei", 8))
        self._wwm.setWordWrap(True)
        self._wwm.setContentsMargins(12, 0, 12, 0)
        self._wwm.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        self._wwm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._wwm)

        self._vtuber = QLabel(translator.tr("sidebar.vtuber"))
        self._vtuber.setFont(QFont("Microsoft JhengHei", 8))
        self._vtuber.setWordWrap(True)
        self._vtuber.setContentsMargins(12, 0, 12, 0)
        self._vtuber.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        self._vtuber.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._vtuber)
        layout.addSpacing(2)

        self._kofi = QLabel(
            f'<a href="https://ko-fi.com/virelleedmond" style="color: #D4A853; text-decoration: none;">{translator.tr("sidebar.support")}</a>'
        )
        self._kofi.setFont(QFont("Microsoft JhengHei", 8))
        self._kofi.setContentsMargins(12, 0, 12, 0)
        self._kofi.setStyleSheet("background: transparent;")
        self._kofi.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._kofi.setOpenExternalLinks(True)
        layout.addWidget(self._kofi)
        layout.addSpacing(2)

        self._ver = QLabel(translator.tr("sidebar.version", version=__version__))
        self._ver.setFont(QFont("Microsoft JhengHei", 8))
        self._ver.setContentsMargins(12, 0, 12, 0)
        self._ver.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        self._ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._ver)

        # Drop shadow on right edge
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(4, 0)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

        # Set initial active
        self._set_active(0)

        # Connect translation signal
        translator.language_changed.connect(self._update_text)
        self._update_text()

    def _update_text(self) -> None:
        """Update UI text based on current language."""
        self._live_btn.set_text(translator.tr("nav.live"))
        self._library_btn.set_text(translator.tr("nav.library"))
        self._editor_btn.set_text(translator.tr("nav.editor"))
        credit_text = translator.tr("sidebar.credit")
        self._credit.setText(credit_text)
        self._credit.setToolTip(credit_text)
        self._ff14.setText(translator.tr("sidebar.ff14"))
        self._wwm.setText(translator.tr("sidebar.wwm"))
        self._vtuber.setText(translator.tr("sidebar.vtuber"))
        self._kofi.setText(
            f'<a href="https://ko-fi.com/virelleedmond" style="color: #D4A853; text-decoration: none;">{translator.tr("sidebar.support")}</a>'
        )
        from cyber_qin import __version__

        self._ver.setText(translator.tr("sidebar.version", version=__version__))

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
            54,
            8,
            self.width() - 62,
            28,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "賽博琴仙",
        )

        # Subtitle
        painter.setPen(QColor(TEXT_SECONDARY))
        sub_font = QFont("Microsoft JhengHei", 9)
        painter.setFont(sub_font)
        painter.drawText(
            54,
            34,
            self.width() - 62,
            18,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "Cyber Qin Xian",
        )

        painter.end()
