"""Playback speed control widget — 賽博墨韻."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from ...core.constants import DEFAULT_PLAYBACK_SPEED, PLAYBACK_SPEED_PRESETS
from ..theme import TEXT_SECONDARY


class SpeedControl(QWidget):
    """Compact playback speed selector."""

    speed_changed = pyqtSignal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel("速度")
        label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        layout.addWidget(label)

        self._combo = QComboBox()
        self._combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for speed in PLAYBACK_SPEED_PRESETS:
            self._combo.addItem(f"{speed}x", speed)

        # Default to 1.0x
        default_idx = PLAYBACK_SPEED_PRESETS.index(DEFAULT_PLAYBACK_SPEED)
        self._combo.setCurrentIndex(default_idx)
        self._combo.currentIndexChanged.connect(self._on_changed)
        self._combo.setFixedWidth(70)
        layout.addWidget(self._combo)

    def _on_changed(self, index: int) -> None:
        speed = self._combo.itemData(index)
        if speed is not None:
            self.speed_changed.emit(float(speed))

    def set_speed(self, speed: float) -> None:
        for i in range(self._combo.count()):
            if abs(self._combo.itemData(i) - speed) < 0.01:
                self._combo.setCurrentIndex(i)
                return
