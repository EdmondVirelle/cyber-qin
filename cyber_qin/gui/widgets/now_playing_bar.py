"""Bottom "Now Playing" transport bar with QPainter icons and gradient background."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ...core.midi_file_player import PlaybackState
from ..theme import BG_SURFACE, DIVIDER, TEXT_PRIMARY
from .animated_widgets import TransportButton
from .mini_piano import MiniPiano
from .progress_bar import ProgressBar
from .speed_control import SpeedControl


class NowPlayingBar(QWidget):
    """Persistent bottom bar with transport controls, progress, and mini visualizer."""

    play_pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    seek_requested = pyqtSignal(float)
    speed_changed = pyqtSignal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(90)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 8)
        root.setSpacing(4)

        # --- Top row: progress bar ---
        self._progress = ProgressBar()
        self._progress.seek_requested.connect(self.seek_requested)
        root.addWidget(self._progress)

        # --- Bottom row: info + controls + speed + piano ---
        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        # Track info (left)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        self._title_label = QLabel("未載入曲目")
        self._title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self._title_label.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        info_layout.addWidget(self._title_label)

        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setProperty("class", "secondary")
        self._time_label.setFont(QFont("Segoe UI", 10))
        info_layout.addWidget(self._time_label)
        bottom.addLayout(info_layout)

        bottom.addStretch()

        # Transport controls (center)
        transport = QHBoxLayout()
        transport.setSpacing(12)

        self._stop_btn = TransportButton("stop", size=36, accent=False)
        self._stop_btn.setToolTip("停止")
        self._stop_btn.clicked.connect(self.stop_clicked)
        transport.addWidget(self._stop_btn)

        self._play_btn = TransportButton("play", size=48, accent=True)
        self._play_btn.setToolTip("播放 / 暫停")
        self._play_btn.clicked.connect(self.play_pause_clicked)
        transport.addWidget(self._play_btn)

        bottom.addLayout(transport)

        bottom.addStretch()

        # Speed control
        self._speed = SpeedControl()
        self._speed.speed_changed.connect(self.speed_changed)
        bottom.addWidget(self._speed)

        # Mini piano (right)
        self._mini_piano = MiniPiano()
        self._mini_piano.setFixedWidth(200)
        bottom.addWidget(self._mini_piano)

        root.addLayout(bottom)

        self._state = PlaybackState.STOPPED

    def paintEvent(self, event) -> None:  # noqa: N802
        """Gradient background: slightly lighter top fading to BG_SURFACE."""
        painter = QPainter(self)
        rect = QRectF(0, 0, self.width(), self.height())

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(30, 30, 30))
        gradient.setColorAt(1.0, QColor(BG_SURFACE))
        painter.fillRect(rect, gradient)

        # Top border line
        painter.setPen(QColor(DIVIDER))
        painter.drawLine(0, 0, self.width(), 0)
        painter.end()

    @property
    def mini_piano(self) -> MiniPiano:
        return self._mini_piano

    def set_track_info(self, name: str, duration: float) -> None:
        self._title_label.setText(name)
        mins = int(duration) // 60
        secs = int(duration) % 60
        self._time_label.setText(f"0:00 / {mins}:{secs:02d}")

    def update_progress(self, current: float, total: float) -> None:
        self._progress.set_progress(current, total)
        c_min, c_sec = int(current) // 60, int(current) % 60
        t_min, t_sec = int(total) // 60, int(total) % 60
        self._time_label.setText(f"{c_min}:{c_sec:02d} / {t_min}:{t_sec:02d}")

    def set_state(self, state: int) -> None:
        self._state = PlaybackState(state)
        if self._state == PlaybackState.PLAYING:
            self._play_btn.icon_type = "pause"
            self._play_btn.setToolTip("暫停")
        else:
            self._play_btn.icon_type = "play"
            self._play_btn.setToolTip("播放")

    def reset(self) -> None:
        self._title_label.setText("未載入曲目")
        self._time_label.setText("0:00 / 0:00")
        self._progress.set_progress(0, 0)
        self._play_btn.icon_type = "play"
        self._state = PlaybackState.STOPPED
