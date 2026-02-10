"""Top-level application window with sidebar navigation, stacked views, and now-playing bar."""

from __future__ import annotations

import logging
import time

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.key_mapper import KeyMapper
from ..core.key_simulator import KeySimulator
from ..core.mapping_schemes import get_scheme
from ..core.midi_file_player import PlaybackState, create_player_controller
from ..core.midi_listener import MidiListener
from ..core.priority import set_thread_priority_realtime
from .views.library_view import LibraryView
from .views.live_mode_view import LiveModeView
from .widgets.now_playing_bar import NowPlayingBar
from .widgets.sidebar import Sidebar

log = logging.getLogger(__name__)


class MidiProcessor(QObject):
    """Bridge between rtmidi callback thread and Qt main thread.

    Key simulation happens directly on the callback thread for low latency.
    Signals are emitted to update the GUI on the main thread.
    """

    note_event = pyqtSignal(str, int, int)  # event_type, note, velocity
    latency_report = pyqtSignal(float)       # ms

    def __init__(
        self,
        mapper: KeyMapper,
        simulator: KeySimulator,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._mapper = mapper
        self._simulator = simulator
        self._priority_set = False

    def on_midi_event(self, event_type: str, note: int, velocity: int) -> None:
        """Called on the rtmidi callback thread. Must be fast."""
        # Set thread priority on first callback
        if not self._priority_set:
            set_thread_priority_realtime()
            self._priority_set = True

        t0 = time.perf_counter()

        if event_type == "note_on":
            mapping = self._mapper.lookup(note)
            if mapping is not None:
                self._simulator.press(note, mapping)
        elif event_type == "note_off":
            self._simulator.release(note)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.note_event.emit(event_type, note, velocity)
        self.latency_report.emit(elapsed_ms)


class AppShell(QMainWindow):
    """Main application window with Spotify-style layout.

    Layout:
    ┌──────────┬────────────────────────────────┐
    │ Sidebar  │  Content (QStackedWidget)       │
    │          │  [LiveModeView | LibraryView]   │
    ├──────────┴────────────────────────────────┤
    │  Now Playing Bar                           │
    └────────────────────────────────────────────┘
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("賽博琴仙 — Cyber Qin Xian")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        # --- Core objects (shared) ---
        self._mapper = KeyMapper()
        self._simulator = KeySimulator()
        self._listener = MidiListener()
        self._processor = MidiProcessor(self._mapper, self._simulator)
        self._player = create_player_controller(self._mapper, self._simulator)

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top area: sidebar + content
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)

        self._sidebar = Sidebar()
        top.addWidget(self._sidebar)

        self._stack = QStackedWidget()

        # View 0: Live Mode
        self._live_view = LiveModeView(
            self._mapper, self._simulator, self._listener,
        )

        # View 1: Library
        self._library_view = LibraryView()

        self._stack.addWidget(self._live_view)
        self._stack.addWidget(self._library_view)
        top.addWidget(self._stack, 1)

        root.addLayout(top, 1)

        # Bottom: Now Playing Bar
        self._now_playing = NowPlayingBar()
        root.addWidget(self._now_playing)

    def _connect_signals(self) -> None:
        # Sidebar navigation
        self._sidebar.navigation_changed.connect(self._stack.setCurrentIndex)

        # Live MIDI callback → processor
        self._live_view.set_midi_callback(self._processor.on_midi_event)

        # Live MIDI processor → GUI updates
        self._processor.note_event.connect(self._live_view.on_note_event)
        self._processor.note_event.connect(self._on_any_note_event)
        self._processor.latency_report.connect(self._live_view.on_latency)

        # Library → file playback
        self._library_view.play_requested.connect(self._on_play_file)

        # File player → GUI updates
        self._player.note_event.connect(self._on_any_note_event)
        self._player.progress_updated.connect(self._now_playing.update_progress)
        self._player.state_changed.connect(self._now_playing.set_state)
        self._player.state_changed.connect(self._on_player_state_changed)
        self._player.playback_finished.connect(self._on_playback_finished)
        self._player.countdown_tick.connect(self._on_countdown_tick)

        # Now Playing bar controls → player
        self._now_playing.play_pause_clicked.connect(self._on_play_pause)
        self._now_playing.stop_clicked.connect(self._on_stop)
        self._now_playing.seek_requested.connect(self._player.seek)
        self._now_playing.speed_changed.connect(self._player.set_speed)
        self._now_playing.speed_changed.connect(self._now_playing.on_speed_changed)

        # Scheme changes → update mini piano + preprocessor range
        self._live_view.scheme_changed.connect(self._on_scheme_changed)

    def _on_scheme_changed(self, scheme_id: str) -> None:
        """Update mini piano range and preprocessor when scheme changes."""
        try:
            scheme = get_scheme(scheme_id)
        except KeyError:
            return
        self._now_playing.mini_piano.set_midi_range(scheme.midi_range)

    def _on_play_file(self, file_path: str) -> None:
        """Load and play a MIDI file from the library."""
        try:
            # Pass scheme range to preprocessor
            scheme = self._mapper.scheme
            kwargs = {}
            if scheme is not None:
                kwargs["note_min"] = scheme.midi_range[0]
                kwargs["note_max"] = scheme.midi_range[1]
            info, stats = self._player.load_file(file_path, **kwargs)
            self._now_playing.set_track_info(info.name, info.duration_seconds)
            self._player.play()
            lo, hi = stats.original_range
            self._live_view.log_viewer.log(
                f"  Auto-play: {info.name} ({info.note_count} notes, {info.tempo_bpm} BPM)"
            )
            if stats.notes_shifted > 0:
                self._live_view.log_viewer.log(
                    f"  預處理: {stats.notes_shifted}/{stats.total_notes} 音符"
                    f"移調至可演奏範圍 (原始: {lo}-{hi})"
                )
        except Exception as e:
            self._live_view.log_viewer.log(f"  Failed to load: {e}")
            log.exception("Failed to play file %s", file_path)

    def _on_play_pause(self) -> None:
        if self._player.state == PlaybackState.PLAYING:
            self._player.pause()
        elif self._player.state == PlaybackState.PAUSED:
            self._player.play()
        elif self._player.state == PlaybackState.STOPPED:
            # If a file was loaded, replay from beginning
            self._player.play()

    def _on_stop(self) -> None:
        self._player.stop()
        self._now_playing.reset()

    def _on_any_note_event(self, event_type: str, note: int, velocity: int) -> None:
        """Update the mini piano from any source (live or file)."""
        mini = self._now_playing.mini_piano
        if event_type == "note_on":
            mini.note_on(note)
        else:
            mini.note_off(note)

    def _on_countdown_tick(self, remaining: int) -> None:
        """Show count-in beats on the now-playing bar and log."""
        self._now_playing.set_countdown(remaining)
        if remaining > 0:
            self._live_view.log_viewer.log(f"  倒數: {remaining}...")

    def _on_player_state_changed(self, state: int) -> None:
        if state == PlaybackState.STOPPED:
            self._now_playing.mini_piano.set_active_notes(set())

    def _on_playback_finished(self) -> None:
        self._now_playing.reset()
        self._live_view.log_viewer.log("  Auto-play finished")

    def _setup_shortcuts(self) -> None:
        """Register global keyboard shortcuts."""
        QShortcut(QKeySequence("Space"), self).activated.connect(
            self._on_play_pause,
        )
        QShortcut(QKeySequence("Ctrl+Right"), self).activated.connect(
            self._on_next_track,
        )
        QShortcut(QKeySequence("Ctrl+Left"), self).activated.connect(
            self._on_prev_track,
        )

    def _on_next_track(self) -> None:
        file_path = self._library_view.play_next()
        if file_path:
            self._on_play_file(file_path)

    def _on_prev_track(self) -> None:
        file_path = self._library_view.play_prev()
        if file_path:
            self._on_play_file(file_path)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._player.cleanup()
        self._live_view.cleanup()
        super().closeEvent(event)
