"""Top-level application window with sidebar navigation, stacked views, and now-playing bar."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, QStandardPaths, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.auto_tune import auto_tune
from ..core.config import get_config
from ..core.key_mapper import KeyMapper
from ..core.key_simulator import KeySimulator
from ..core.mapping_schemes import get_scheme
from ..core.midi_file_player import PlaybackState, create_player_controller
from ..core.midi_listener import MidiListener
from ..core.midi_recorder import MidiRecorder
from ..core.midi_writer import MidiWriter
from ..core.priority import set_thread_priority_realtime
from ..core.translator import translator
from .views.editor_view import EditorView
from .views.library_view import LibraryView
from .views.live_mode_view import LiveModeView
from .widgets.now_playing_bar import NowPlayingBar, RepeatMode
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
        self._recorder: MidiRecorder | None = None

    def set_recorder(self, recorder: MidiRecorder | None) -> None:
        """Attach/detach a recorder. Called from the main thread."""
        self._recorder = recorder

    def on_midi_event(self, event_type: str, note: int, velocity: int) -> None:
        """Called on the rtmidi callback thread. Must be fast."""
        # Set thread priority on first callback
        if not self._priority_set:
            set_thread_priority_realtime()
            self._priority_set = True

        t0 = time.perf_counter()

        # Record event (thread-safe: list.append is GIL-atomic)
        recorder = self._recorder
        if recorder is not None and recorder.is_recording:
            recorder.record_event(event_type, note, velocity)

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
    ┌──────────┬──────────────────────────────────────────┐
    │ Sidebar  │  Content (QStackedWidget)                 │
    │          │  [LiveModeView | LibraryView | EditorView]│
    ├──────────┴──────────────────────────────────────────┤
    │  Now Playing Bar                                     │
    └──────────────────────────────────────────────────────┘
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(translator.tr("app.title") + " — " + translator.tr("app.subtitle"))
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        # --- Core objects (shared) ---
        self._mapper = KeyMapper()
        self._simulator = KeySimulator()
        self._listener = MidiListener()
        self._processor = MidiProcessor(self._mapper, self._simulator)
        self._player = create_player_controller(self._mapper, self._simulator)
        self._recorder = MidiRecorder()
        self._config = get_config()

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()
        self._restore_window_state()

        translator.language_changed.connect(self._update_text)

    def _update_text(self) -> None:
        """Update window title and other shell elements."""
        self.setWindowTitle(translator.tr("app.title") + " — " + translator.tr("app.subtitle"))

    def _restore_window_state(self) -> None:
        """Restore window geometry and last view from config."""
        from PyQt6.QtCore import QByteArray

        # Restore window geometry (stored as base64 string)
        geometry_b64 = self._config.get("window.geometry")
        if geometry_b64 is not None:
            geometry = QByteArray.fromBase64(geometry_b64.encode("ascii"))
            self.restoreGeometry(geometry)

        # Restore last active view
        last_view = self._config.get("window.last_view", "live")
        view_index = {"live": 0, "library": 1, "editor": 2}.get(last_view, 0)
        self._stack.setCurrentIndex(view_index)
        self._sidebar._set_active(view_index)  # noqa: SLF001

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

        # View 2: Editor
        self._editor_view = EditorView()

        self._stack.addWidget(self._live_view)
        self._stack.addWidget(self._library_view)
        self._stack.addWidget(self._editor_view)
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

        # Library → editor
        self._library_view.edit_requested.connect(self._on_edit_file)

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
        self._now_playing.prev_clicked.connect(self._on_prev_track)
        self._now_playing.next_clicked.connect(self._on_next_track)
        self._now_playing.repeat_clicked.connect(self._on_repeat_toggle)
        self._now_playing.seek_requested.connect(self._player.seek)
        self._now_playing.speed_changed.connect(self._player.set_speed)
        self._now_playing.speed_changed.connect(self._now_playing.on_speed_changed)

        # Scheme changes → update mini piano + preprocessor range
        self._live_view.scheme_changed.connect(self._on_scheme_changed)

        # Recording signals
        self._live_view.recording_started.connect(self._on_recording_started)
        self._live_view.recording_stopped.connect(self._on_recording_stopped)

        # Editor recording + play → preview
        self._editor_view.recording_started.connect(self._on_editor_recording_started)
        self._editor_view.recording_stopped.connect(self._on_editor_recording_stopped)
        self._editor_view.play_requested.connect(self._on_editor_play)

        # Pass player to editor for playback cursor tracking
        self._editor_view.set_player(self._player)

    # --- Recording ---

    def _on_recording_started(self) -> None:
        """Start recording MIDI events."""
        self._recorder.start()
        self._processor.set_recorder(self._recorder)
        self._live_view.log_viewer.log("  錄音開始")

    def _on_recording_stopped(self, _file_path: str) -> None:
        """Stop recording and save to file."""
        self._processor.set_recorder(None)
        events = self._recorder.stop()

        if not events:
            self._live_view.log_viewer.log("  錄音結束 (無音符)")
            return

        # Apply auto-tune if enabled
        if self._live_view.auto_tune_enabled:
            events, stats = auto_tune(events)
            self._live_view.log_viewer.log(
                f"  自動校正: {stats.quantized_count} 量化, "
                f"{stats.pitch_corrected_count} 修正"
            )

        # Save to file
        data_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        rec_dir = Path(data_dir) / "CyberQin" / "recordings"
        rec_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = str(rec_dir / f"recording_{timestamp}.mid")

        try:
            MidiWriter.save(events, file_path)
            note_count = sum(1 for e in events if e.event_type == "note_on")
            self._live_view.log_viewer.log(
                f"  錄音已儲存: recording_{timestamp}.mid ({note_count} 音符)"
            )
            # Add to library
            self._library_view.add_file(file_path)
            self._live_view.on_recording_saved(file_path)
        except Exception as e:
            self._live_view.log_viewer.log(f"  儲存錄音失敗: {e}")
            log.exception("Failed to save recording")

    # --- Editor ---

    def _on_editor_recording_started(self) -> None:
        """Start recording into the editor."""
        self._recorder.start()
        self._processor.set_recorder(self._recorder)
        self._live_view.log_viewer.log("  編曲器錄音開始")

    def _on_editor_recording_stopped(self) -> None:
        """Stop recording and merge events into the editor sequence."""
        self._processor.set_recorder(None)
        events = self._recorder.stop()

        if not events:
            self._live_view.log_viewer.log("  編曲器錄音結束 (無音符)")
            return

        # Apply auto-tune if enabled
        if self._editor_view.auto_tune_enabled:
            events, stats = auto_tune(events)
            self._live_view.log_viewer.log(
                f"  自動校正: {stats.quantized_count} 量化, "
                f"{stats.pitch_corrected_count} 修正"
            )

        # Convert RecordedEvents → MidiFileEvents for set_recorded_events
        from ..core.midi_file_player import MidiFileEvent

        file_events = [
            MidiFileEvent(
                time_seconds=e.timestamp,
                event_type=e.event_type,
                note=e.note,
                velocity=e.velocity,
            )
            for e in events
        ]
        note_count = sum(1 for e in events if e.event_type == "note_on")
        self._editor_view.set_recorded_events(file_events)
        self._live_view.log_viewer.log(
            f"  編曲器錄音完成: {note_count} 音符已合併"
        )

    def _on_edit_file(self, file_path: str) -> None:
        """Open a file in the editor view."""
        self._editor_view.load_file(file_path)
        self._stack.setCurrentIndex(2)
        self._sidebar._set_active(2)

    def _on_editor_play(self, events: list) -> None:
        """Play the editor's note sequence through the existing player."""
        from ..core.midi_file_player import MidiFileInfo

        if not events:
            return
        duration = max(e.time_seconds for e in events) if events else 0.0
        note_count = sum(1 for e in events if e.event_type == "note_on")
        info = MidiFileInfo(
            file_path="",
            name="編曲器預覽",
            duration_seconds=duration,
            track_count=1,
            note_count=note_count,
            tempo_bpm=120.0,
        )
        self._player.stop()
        self._player.worker.load(events, info)
        self._now_playing.set_track_info(info.name, info.duration_seconds)
        self._player.play()
        self._live_view.log_viewer.log(
            f"  編曲器播放: {note_count} 音符, {duration:.1f}s"
        )

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
            # Pass scheme range + preprocessing options to preprocessor
            scheme = self._mapper.scheme
            kwargs: dict = {"remove_percussion": True}
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
            if stats.percussion_removed > 0:
                self._live_view.log_viewer.log(
                    f"  打擊軌過濾: 移除 {stats.percussion_removed} 個打擊音符"
                )
            if stats.octave_deduped > 0:
                self._live_view.log_viewer.log(
                    f"  八度去重: 移除 {stats.octave_deduped} 個重複八度音"
                )
            if stats.global_transpose != 0:
                direction = "↑" if stats.global_transpose > 0 else "↓"
                octaves = abs(stats.global_transpose) // 12
                self._live_view.log_viewer.log(
                    f"  智慧移調: 全曲{direction}{octaves} 個八度 (原始: {lo}-{hi})"
                )
            if stats.notes_shifted > 0:
                self._live_view.log_viewer.log(
                    f"  八度摺疊: {stats.notes_shifted}/{stats.total_notes} 音符"
                    f"收納至可演奏範圍"
                )
            if stats.duplicates_removed > 0:
                self._live_view.log_viewer.log(
                    f"  碰撞去重: 移除 {stats.duplicates_removed} 個重複音符"
                )
            if stats.polyphony_limited > 0:
                self._live_view.log_viewer.log(
                    f"  聲部限制: 移除 {stats.polyphony_limited} 個過密音符"
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
        mode = self._now_playing.repeat_mode
        if mode == RepeatMode.REPEAT_ONE:
            # Repeat the same track
            self._player.seek(0)
            self._player.play()
            self._live_view.log_viewer.log("  單曲重複")
            return
        if mode == RepeatMode.REPEAT_ALL:
            # Advance to next; wrap around to first if at end
            file_path = self._library_view.play_next()
            if file_path is None:
                # Wrap to first track
                file_path = self._library_view.play_first()
            if file_path:
                self._on_play_file(file_path)
                self._live_view.log_viewer.log("  循環播放: 下一首")
                return
        # RepeatMode.OFF or no more tracks
        self._now_playing.reset()
        self._live_view.log_viewer.log("  Auto-play finished")

    def _on_repeat_toggle(self) -> None:
        """Cycle repeat mode: OFF → REPEAT_ALL → REPEAT_ONE → OFF."""
        mode = self._now_playing.repeat_mode
        cycle = {
            RepeatMode.OFF: RepeatMode.REPEAT_ALL,
            RepeatMode.REPEAT_ALL: RepeatMode.REPEAT_ONE,
            RepeatMode.REPEAT_ONE: RepeatMode.OFF,
        }
        new_mode = cycle[mode]
        self._now_playing.set_repeat_mode(new_mode)
        labels = {
            RepeatMode.OFF: "關閉",
            RepeatMode.REPEAT_ALL: "全部循環",
            RepeatMode.REPEAT_ONE: "單曲重複",
        }
        self._live_view.log_viewer.log(f"  循環模式: {labels[new_mode]}")

    def _setup_shortcuts(self) -> None:
        """Register global keyboard shortcuts."""
        space_shortcut = QShortcut(QKeySequence("Space"), self)
        space_shortcut.activated.connect(self._on_space_key)
        QShortcut(QKeySequence("Ctrl+Right"), self).activated.connect(
            self._on_next_track,
        )
        QShortcut(QKeySequence("Ctrl+Left"), self).activated.connect(
            self._on_prev_track,
        )

    def _on_space_key(self) -> None:
        """Handle Space: let EditorView handle it when active, else play/pause."""
        if self._stack.currentIndex() == 2:
            # Editor view is active — it handles Space via keyPressEvent
            return
        self._on_play_pause()

    def _on_next_track(self) -> None:
        file_path = self._library_view.play_next()
        if file_path is None and self._now_playing.repeat_mode == RepeatMode.REPEAT_ALL:
            file_path = self._library_view.play_first()
        if file_path:
            self._on_play_file(file_path)

    def _on_prev_track(self) -> None:
        file_path = self._library_view.play_prev()
        if file_path is None and self._now_playing.repeat_mode == RepeatMode.REPEAT_ALL:
            file_path = self._library_view.play_last()
        if file_path:
            self._on_play_file(file_path)

    def closeEvent(self, event) -> None:  # noqa: N802
        # Save window state to config (geometry as base64 string for JSON compatibility)
        geometry_b64 = self.saveGeometry().toBase64().data().decode("ascii")
        self._config.set("window.geometry", geometry_b64)
        current_view = {0: "live", 1: "library", 2: "editor"}.get(
            self._stack.currentIndex(), "live"
        )
        self._config.set("window.last_view", current_view)

        # Stop any in-progress recording (live or editor)
        if self._recorder.is_recording:
            self._processor.set_recorder(None)
            self._recorder.stop()
        self._player.cleanup()
        self._live_view.cleanup()
        super().closeEvent(event)
