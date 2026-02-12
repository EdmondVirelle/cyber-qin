"""Bottom "Now Playing" transport bar with QPainter icons and gradient background — 賽博墨韻."""

from __future__ import annotations

import time
from enum import IntEnum, auto

from PyQt6.QtCore import QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ...core.midi_file_player import PlaybackState
from ...core.translator import translator
from ..theme import ACCENT, BG_SCROLL, DIVIDER, TEXT_PRIMARY, TEXT_SECONDARY
from .animated_widgets import TransportButton
from .mini_piano import MiniPiano
from .progress_bar import ProgressBar
from .speed_control import SpeedControl


class RepeatMode(IntEnum):
    """Playback repeat modes."""
    OFF = auto()
    REPEAT_ALL = auto()    # 循環播放 — loop through playlist
    REPEAT_ONE = auto()    # 重複播放 — repeat current track


class NowPlayingBar(QWidget):
    """Persistent bottom bar with transport controls, progress, and mini visualizer."""

    play_pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    repeat_clicked = pyqtSignal()
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
        self._title_label = QLabel(translator.tr("player.no_track"))
        self._title_label.setFont(QFont("Microsoft JhengHei", 12, QFont.Weight.DemiBold))
        self._title_label.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        info_layout.addWidget(self._title_label)

        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setProperty("class", "secondary")
        self._time_label.setFont(QFont("Microsoft JhengHei", 10))
        info_layout.addWidget(self._time_label)
        bottom.addLayout(info_layout)

        bottom.addStretch()

        # Transport controls (center)
        transport = QHBoxLayout()
        transport.setSpacing(8)

        self._repeat_btn = TransportButton("repeat", size=32, accent=False)
        self._repeat_btn.setToolTip(translator.tr("player.repeat.mode.off"))
        self._repeat_btn.clicked.connect(self.repeat_clicked)
        transport.addWidget(self._repeat_btn)

        self._prev_btn = TransportButton("skip_prev", size=36, accent=False)
        self._prev_btn.setToolTip(translator.tr("player.prev"))
        self._prev_btn.clicked.connect(self.prev_clicked)
        transport.addWidget(self._prev_btn)

        self._stop_btn = TransportButton("stop", size=36, accent=False)
        self._stop_btn.setToolTip(translator.tr("player.stop"))
        self._stop_btn.clicked.connect(self.stop_clicked)
        transport.addWidget(self._stop_btn)

        self._play_btn = TransportButton("play", size=48, accent=True)
        self._play_btn.setToolTip(translator.tr("player.play"))
        self._play_btn.clicked.connect(self.play_pause_clicked)
        transport.addWidget(self._play_btn)

        self._next_btn = TransportButton("skip_next", size=36, accent=False)
        self._next_btn.setToolTip(translator.tr("player.next"))
        self._next_btn.clicked.connect(self.next_clicked)
        transport.addWidget(self._next_btn)

        bottom.addLayout(transport)

        bottom.addStretch()

        # Speed control
        self._speed_ctrl = SpeedControl()
        self._speed_ctrl.speed_changed.connect(self.speed_changed)
        bottom.addWidget(self._speed_ctrl)

        # Mini piano (right)
        self._mini_piano = MiniPiano()
        self._mini_piano.setFixedWidth(200)
        bottom.addWidget(self._mini_piano)

        root.addLayout(bottom)

        self._state = PlaybackState.STOPPED
        self._repeat_mode = RepeatMode.OFF

        # --- Interpolation timer for smooth progress updates (30 fps) ---
        self._last_position = 0.0
        self._last_update_wall = time.perf_counter()
        self._duration = 0.0
        self._speed = 1.0
        self._is_playing = False

        self._interp_timer = QTimer(self)
        self._interp_timer.setInterval(33)  # ~30 fps
        self._interp_timer.timeout.connect(self._on_interpolation_tick)

        translator.language_changed.connect(self._update_text)

    def paintEvent(self, event) -> None:  # noqa: N802
        """Gradient background: 墨色 top fading to BG_SCROLL."""
        painter = QPainter(self)
        rect = QRectF(0, 0, self.width(), self.height())

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(0x1A, 0x23, 0x32))
        gradient.setColorAt(1.0, QColor(BG_SCROLL))
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
        """Called from the player on MIDI events — anchors interpolation."""
        self._last_position = current
        self._last_update_wall = time.perf_counter()
        self._duration = total
        # Use animated transition for smooth bar movement
        self._progress.set_progress_animated(current, total)
        c_min, c_sec = int(current) // 60, int(current) % 60
        t_min, t_sec = int(total) // 60, int(total) % 60
        self._time_label.setText(f"{c_min}:{c_sec:02d} / {t_min}:{t_sec:02d}")

    def set_state(self, state: int) -> None:
        self._state = PlaybackState(state)
        if self._state == PlaybackState.PLAYING:
            self._play_btn.icon_type = "pause"
            self._play_btn.setToolTip(translator.tr("player.pause"))
            self._is_playing = True
            self._last_update_wall = time.perf_counter()
            self._interp_timer.start()
        else:
            self._play_btn.icon_type = "play"
            self._play_btn.setToolTip(translator.tr("player.play"))
            self._is_playing = False
            self._interp_timer.stop()

    def set_countdown(self, remaining: int) -> None:
        """Show count-in beats: 4, 3, 2, 1 then restore title."""
        if remaining > 0:
            if not hasattr(self, "_saved_time") or self._saved_time is None:
                self._saved_title = self._title_label.text()
                self._saved_time = self._time_label.text()
            self._title_label.setText(translator.tr("player.countdown", n=remaining))
            self._time_label.setText(translator.tr("player.switch_window"))
        else:
            # Count-in done — restore the saved title AND time label
            saved = getattr(self, "_saved_title", None)
            if saved:
                self._title_label.setText(saved)
                self._time_label.setText(
                    getattr(self, "_saved_time", None) or "0:00 / 0:00"
                )
                self._saved_title = None
                self._saved_time = None

    def on_speed_changed(self, speed: float) -> None:
        """Track current playback speed for interpolation."""
        self._speed = speed

    def _on_interpolation_tick(self) -> None:
        """30 fps timer tick — linearly interpolate progress between MIDI events."""
        if not self._is_playing or self._duration <= 0:
            return
        now = time.perf_counter()
        elapsed = (now - self._last_update_wall) * self._speed
        pos = min(self._last_position + elapsed, self._duration)

        self._progress.set_progress_animated(pos, self._duration)
        c_min, c_sec = int(pos) // 60, int(pos) % 60
        t_min, t_sec = int(self._duration) // 60, int(self._duration) % 60
        self._time_label.setText(f"{c_min}:{c_sec:02d} / {t_min}:{t_sec:02d}")

    @property
    def repeat_mode(self) -> RepeatMode:
        return self._repeat_mode

    def set_repeat_mode(self, mode: RepeatMode) -> None:
        """Update the repeat button icon and tooltip to reflect *mode*."""
        self._repeat_mode = mode
        _labels = {
            RepeatMode.OFF: ("repeat", translator.tr("player.repeat.mode.off"), TEXT_SECONDARY),
            RepeatMode.REPEAT_ALL: ("repeat", translator.tr("player.repeat.mode.all"), ACCENT),
            RepeatMode.REPEAT_ONE: ("repeat_one", translator.tr("player.repeat.mode.one"), ACCENT),
        }
        icon, tip, _color = _labels[mode]
        self._repeat_btn.icon_type = icon
        self._repeat_btn.setToolTip(tip)
        # Use accent styling when active
        self._repeat_btn._accent = mode != RepeatMode.OFF
        self._repeat_btn.update()

    def _update_text(self) -> None:
        """Refresh all translatable labels and tooltips."""
        # Only update title if no track is loaded (playing track name is data, not i18n)
        if self._state == PlaybackState.STOPPED and self._duration == 0.0:
            self._title_label.setText(translator.tr("player.no_track"))
        # Tooltips
        self._prev_btn.setToolTip(translator.tr("player.prev"))
        self._next_btn.setToolTip(translator.tr("player.next"))
        self._stop_btn.setToolTip(translator.tr("player.stop"))
        if self._state == PlaybackState.PLAYING:
            self._play_btn.setToolTip(translator.tr("player.pause"))
        else:
            self._play_btn.setToolTip(translator.tr("player.play"))
        # Re-apply repeat tooltip
        self.set_repeat_mode(self._repeat_mode)

    def reset(self) -> None:
        self._title_label.setText(translator.tr("player.no_track"))
        self._time_label.setText("0:00 / 0:00")
        self._progress.set_progress(0, 0)
        self._play_btn.icon_type = "play"
        self._state = PlaybackState.STOPPED
        self._is_playing = False
        self._interp_timer.stop()
        self._last_position = 0.0
        self._duration = 0.0
        self._saved_title = None
        self._saved_time = None
