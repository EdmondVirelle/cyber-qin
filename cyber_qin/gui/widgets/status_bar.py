"""Status bar with indicator lights, latency color-coding, and QSS class properties — 賽博墨韻."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ...utils.ime import is_ime_active
from ..theme import ACCENT, ERROR, TEXT_DISABLED, WARNING


class _StatusDot(QWidget):
    """Small colored circle indicator."""

    def __init__(self, color: str = TEXT_DISABLED, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(10, 10)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(QRectF(1, 1, 8, 8))
        painter.end()


class StatusBar(QWidget):
    """Status bar widget with connection indicator, latency color-coding, and IME indicators."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Connection indicator
        self._conn_dot = _StatusDot(TEXT_DISABLED)
        layout.addWidget(self._conn_dot)
        layout.addSpacing(4)

        self._conn_label = QLabel("MIDI: 未連線")
        self._conn_label.setProperty("class", "status-off")
        layout.addWidget(self._conn_label)

        layout.addStretch()

        # Latency
        self._latency_dot = _StatusDot(TEXT_DISABLED)
        layout.addWidget(self._latency_dot)
        layout.addSpacing(4)

        self._latency_label = QLabel("")
        self._latency_label.setProperty("class", "secondary")
        layout.addWidget(self._latency_label)

        layout.addStretch()

        self._ime_label = QLabel("")
        layout.addWidget(self._ime_label)

        layout.addStretch()

        self._admin_label = QLabel("")
        layout.addWidget(self._admin_label)

        self._ime_timer = QTimer(self)
        self._ime_timer.timeout.connect(self._check_ime)
        self._ime_timer.start(2000)

    def set_connected(self, port_name: str) -> None:
        self._conn_label.setText(f"MIDI: {port_name}")
        self._conn_label.setProperty("class", "status-ok")
        self._conn_label.style().unpolish(self._conn_label)
        self._conn_label.style().polish(self._conn_label)
        self._conn_dot.set_color(ACCENT)

    def set_disconnected(self) -> None:
        self._conn_label.setText("MIDI: 未連線")
        self._conn_label.setProperty("class", "status-off")
        self._conn_label.style().unpolish(self._conn_label)
        self._conn_label.style().polish(self._conn_label)
        self._conn_dot.set_color(TEXT_DISABLED)

    def set_reconnecting(self) -> None:
        self._conn_label.setText("MIDI: 重新連線中...")
        self._conn_label.setProperty("class", "status-warn")
        self._conn_label.style().unpolish(self._conn_label)
        self._conn_label.style().polish(self._conn_label)
        self._conn_dot.set_color(WARNING)

    def set_latency(self, ms: float) -> None:
        self._latency_label.setText(f"延遲: {ms:.1f}ms")
        # Color-coded latency
        if ms < 5:
            color = ACCENT
        elif ms < 15:
            color = WARNING
        else:
            color = ERROR
        self._latency_dot.set_color(color)
        self._latency_label.setStyleSheet(f"color: {color}; background: transparent;")

    def set_admin_warning(self, is_admin: bool) -> None:
        if is_admin:
            self._admin_label.setText("管理員")
            self._admin_label.setProperty("class", "status-ok")
        else:
            self._admin_label.setText("非管理員 (建議提權)")
            self._admin_label.setProperty("class", "status-warn")
        self._admin_label.style().unpolish(self._admin_label)
        self._admin_label.style().polish(self._admin_label)

    def _check_ime(self) -> None:
        try:
            if is_ime_active():
                self._ime_label.setText("IME: 非英文")
                self._ime_label.setProperty("class", "status-warn")
            else:
                self._ime_label.setText("IME: EN")
                self._ime_label.setProperty("class", "status-ok")
            self._ime_label.style().unpolish(self._ime_label)
            self._ime_label.style().polish(self._ime_label)
        except Exception:
            self._ime_label.setText("")
