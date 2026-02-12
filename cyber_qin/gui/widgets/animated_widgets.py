"""Animated button widgets with QPainter-drawn icons and smooth transitions — 賽博墨韻 style."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    pyqtProperty,  # type: ignore[attr-defined]
)
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import QAbstractButton, QWidget

from ..icons import (
    draw_editor,
    draw_help,
    draw_library,
    draw_live,
    draw_music_note,
    draw_mute,
    draw_pause,
    draw_play,
    draw_plus,
    draw_record,
    draw_redo,
    draw_refresh,
    draw_remove,
    draw_repeat,
    draw_repeat_one,
    draw_save,
    draw_skip_next,
    draw_skip_prev,
    draw_solo,
    draw_stop,
    draw_undo,
)
from ..theme import (
    ACCENT,
    ACCENT_GLOW,
    ACCENT_GOLD,
    BG_WASH,
    TEXT_DISABLED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

_ICON_DRAWERS: dict[str, Callable] = {
    "play": draw_play,
    "pause": draw_pause,
    "stop": draw_stop,
    "refresh": draw_refresh,
    "plus": draw_plus,
    "remove": draw_remove,
    "music_note": draw_music_note,
    "live": draw_live,
    "library": draw_library,
    "editor": draw_editor,
    "record": draw_record,
    "skip_next": draw_skip_next,
    "skip_prev": draw_skip_prev,
    "redo": draw_redo,
    "repeat": draw_repeat,
    "repeat_one": draw_repeat_one,
    "undo": draw_undo,
    "mute": draw_mute,
    "solo": draw_solo,
    "save": draw_save,
    "help": draw_help,
}


class TransportButton(QAbstractButton):
    """Circular transport control button (play/pause/stop) with hover animation.

    Play button: cyan circle + dark icon.
    Stop button: transparent background + gray icon.
    """

    def __init__(
        self,
        icon_type: str = "play",
        size: int = 48,
        accent: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_type = icon_type
        self._size = size
        self._accent = accent
        self._hover_progress = 0.0

        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"hover_progress")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def hover_progress(self) -> float:
        return self._hover_progress

    @hover_progress.setter  # type: ignore[no-redef]
    def hover_progress(self, val: float) -> None:
        self._hover_progress = val
        self.update()

    @property
    def icon_type(self) -> str:
        return self._icon_type

    @icon_type.setter
    def icon_type(self, value: str) -> None:
        self._icon_type = value
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._size, self._size)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())

        if self._accent:
            # Cyan circle background with hover brightening
            base = QColor(ACCENT)
            hover = QColor(ACCENT_GLOW)
            bg = _lerp_color(base, hover, self._hover_progress)
            icon_color = QColor(0x0A, 0x0E, 0x14)  # Dark icon on cyan

            circle = QPainterPath()
            circle.addEllipse(rect)
            painter.fillPath(circle, bg)
        else:
            # Transparent with subtle hover background
            if self._hover_progress > 0.01:
                bg = QColor(BG_WASH)
                bg.setAlphaF(self._hover_progress * 0.8)
                circle = QPainterPath()
                circle.addEllipse(rect)
                painter.fillPath(circle, bg)

            base_c = QColor(TEXT_SECONDARY)
            hover_c = QColor(TEXT_PRIMARY)
            icon_color = _lerp_color(base_c, hover_c, self._hover_progress)

        # Draw icon
        drawer = _ICON_DRAWERS.get(self._icon_type)
        if drawer:
            drawer(painter, rect, icon_color)

        painter.end()


class IconButton(QAbstractButton):
    """Generic icon button with hover fade-in background."""

    def __init__(
        self,
        icon_type: str,
        size: int = 36,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_type = icon_type
        self._size = size
        self._hover_progress = 0.0

        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"hover_progress")
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def hover_progress(self) -> float:
        return self._hover_progress

    @hover_progress.setter  # type: ignore[no-redef]
    def hover_progress(self, val: float) -> None:
        self._hover_progress = val
        self.update()

    @property
    def icon_type(self) -> str:
        return self._icon_type

    @icon_type.setter
    def icon_type(self, value: str) -> None:
        self._icon_type = value
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._size, self._size)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())

        # Hover background
        if self._hover_progress > 0.01:
            bg = QColor(BG_WASH)
            bg.setAlphaF(self._hover_progress * 0.7)
            circle = QPainterPath()
            circle.addEllipse(rect)
            painter.fillPath(circle, bg)

        # Icon color (dim when disabled)
        if not self.isEnabled():
            icon_color = QColor(TEXT_DISABLED)
        else:
            base_c = QColor(TEXT_SECONDARY)
            hover_c = QColor(TEXT_PRIMARY)
            icon_color = _lerp_color(base_c, hover_c, self._hover_progress)

        drawer = _ICON_DRAWERS.get(self._icon_type)
        if drawer:
            drawer(painter, rect, icon_color)

        painter.end()


class AnimatedNavButton(QAbstractButton):
    """Navigation button with icon, text, active indicator, and hover animation."""

    def __init__(
        self,
        icon_type: str,
        text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_type = icon_type
        self._text = text
        self._active = False
        self._hover_progress = 0.0

        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"hover_progress")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def hover_progress(self) -> float:
        return self._hover_progress

    @hover_progress.setter  # type: ignore[no-redef]
    def hover_progress(self, val: float) -> None:
        self._hover_progress = val
        self.update()

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value
        self.update()

    def set_text(self, text: str) -> None:
        """Update the button label text (used for i18n)."""
        self._text = text
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(200, 44)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Hover background
        hover_alpha = self._hover_progress * 0.08 if not self._active else 0.0
        if hover_alpha > 0.001:
            bg = QColor(0x00, 0xF0, 0xFF)  # Cyan tinted hover
            bg.setAlphaF(hover_alpha)
            path = QPainterPath()
            path.addRoundedRect(QRectF(4, 0, w - 8, h), 6, 6)
            painter.fillPath(path, bg)

        # Active indicator (left gold bar — 金墨)
        if self._active:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(ACCENT_GOLD))
            indicator = QPainterPath()
            indicator.addRoundedRect(QRectF(0, h * 0.2, 3, h * 0.6), 1.5, 1.5)
            painter.drawPath(indicator)

        # Icon
        icon_rect = QRectF(16, (h - 22) / 2, 22, 22)
        if self._active:
            icon_color = QColor(TEXT_PRIMARY)
        else:
            base_c = QColor(TEXT_SECONDARY)
            hover_c = QColor(TEXT_PRIMARY)
            icon_color = _lerp_color(base_c, hover_c, self._hover_progress)

        drawer = _ICON_DRAWERS.get(self._icon_type)
        if drawer:
            drawer(painter, icon_rect, icon_color)

        # Text
        if self._active:
            text_color = QColor(TEXT_PRIMARY)
        else:
            base_t = QColor(TEXT_SECONDARY)
            hover_t = QColor(TEXT_PRIMARY)
            text_color = _lerp_color(base_t, hover_t, self._hover_progress)

        painter.setPen(text_color)
        font = painter.font()
        font.setFamily("Microsoft JhengHei")
        font.setPixelSize(14)
        font.setWeight(700 if self._active else 600)
        painter.setFont(font)

        text_x = 48
        painter.drawText(
            int(text_x), 0, int(w - text_x - 8), h,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._text,
        )

        painter.end()


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    """Linear interpolation between two colors."""
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
        int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )
