"""MIDI file parser and timed playback engine.

Pure-Python data classes and parser are importable without Qt.
Qt-dependent playback classes are defined below and require a running QApplication.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import IntEnum, auto
from pathlib import Path
from typing import TYPE_CHECKING

import mido

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Pure Python (no Qt dependency)
# ──────────────────────────────────────────────


class PlaybackState(IntEnum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()


@dataclass(frozen=True, slots=True)
class MidiFileEvent:
    """A single timed note event from a MIDI file."""

    time_seconds: float
    event_type: str  # "note_on" or "note_off"
    note: int
    velocity: int
    track: int = 0
    channel: int = 0


@dataclass(frozen=True, slots=True)
class MidiTrackInfo:
    """Metadata about a single MIDI track."""

    index: int
    name: str
    channel: int  # primary channel (-1 if mixed/none)
    note_count: int
    is_percussion: bool  # True if channel == 9 (GM percussion)


@dataclass(frozen=True, slots=True)
class MidiFileInfo:
    """Metadata about a parsed MIDI file."""

    file_path: str
    name: str
    duration_seconds: float
    track_count: int
    note_count: int
    tempo_bpm: float
    tracks: tuple[MidiTrackInfo, ...] = ()


class MidiFileParser:
    """Parse .mid files into sorted event lists."""

    @staticmethod
    def _build_tempo_map(mid: mido.MidiFile) -> list[tuple[int, int]]:
        """Extract a global tempo map: list of (abs_tick, tempo_uspb).

        Scans ALL tracks for set_tempo events (some MIDIs put them
        outside the conductor track).
        """
        tempo_events: list[tuple[int, int]] = []
        for track in mid.tracks:
            abs_tick = 0
            for msg in track:
                abs_tick += msg.time
                if msg.type == "set_tempo":
                    tempo_events.append((abs_tick, msg.tempo))
        tempo_events.sort(key=lambda x: x[0])
        if not tempo_events or tempo_events[0][0] != 0:
            tempo_events.insert(0, (0, 500000))  # default 120 BPM
        return tempo_events

    @staticmethod
    def _tick_to_sec(abs_tick: int, tempo_map: list[tuple[int, int]], tpb: int) -> float:
        """Convert absolute tick to seconds using the tempo map."""
        seconds = 0.0
        prev_tick = 0
        prev_tempo = tempo_map[0][1]
        for map_tick, map_tempo in tempo_map:
            if map_tick >= abs_tick:
                break
            seconds += mido.tick2second(map_tick - prev_tick, tpb, prev_tempo)
            prev_tick = map_tick
            prev_tempo = map_tempo
        seconds += mido.tick2second(abs_tick - prev_tick, tpb, prev_tempo)
        return float(seconds)

    @staticmethod
    def parse(file_path: str) -> tuple[list[MidiFileEvent], MidiFileInfo]:
        """Parse a MIDI file into a list of timed events + metadata.

        Returns (events, info) where events are sorted by time_seconds.
        Preserves track index and MIDI channel for each event.
        """
        path = Path(file_path)
        mid = mido.MidiFile(str(path), clip=True)
        tpb = mid.ticks_per_beat
        tempo_map = MidiFileParser._build_tempo_map(mid)

        events: list[MidiFileEvent] = []
        track_infos: list[MidiTrackInfo] = []
        first_tempo = tempo_map[0][1]

        for track_idx, track in enumerate(mid.tracks):
            abs_tick = 0
            track_note_count = 0
            track_name = ""
            channels_seen: set[int] = set()

            for msg in track:
                abs_tick += msg.time

                if msg.type == "track_name":
                    track_name = msg.name
                elif msg.type == "note_on" and msg.velocity > 0:
                    t = MidiFileParser._tick_to_sec(abs_tick, tempo_map, tpb)
                    events.append(
                        MidiFileEvent(
                            time_seconds=t,
                            event_type="note_on",
                            note=msg.note,
                            velocity=msg.velocity,
                            track=track_idx,
                            channel=msg.channel,
                        )
                    )
                    track_note_count += 1
                    channels_seen.add(msg.channel)
                elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                    t = MidiFileParser._tick_to_sec(abs_tick, tempo_map, tpb)
                    events.append(
                        MidiFileEvent(
                            time_seconds=t,
                            event_type="note_off",
                            note=msg.note,
                            velocity=0,
                            track=track_idx,
                            channel=msg.channel,
                        )
                    )
                    channels_seen.add(msg.channel)

            # Determine primary channel for this track
            primary_ch = -1
            if len(channels_seen) == 1:
                primary_ch = next(iter(channels_seen))
            elif channels_seen:
                # Most common channel (excluding None)
                primary_ch = (
                    max(
                        channels_seen,
                        key=lambda c: sum(
                            1 for e in events if e.track == track_idx and e.channel == c
                        ),
                    )
                    if track_note_count > 0
                    else -1
                )

            track_infos.append(
                MidiTrackInfo(
                    index=track_idx,
                    name=track_name or f"Track {track_idx}",
                    channel=primary_ch,
                    note_count=track_note_count,
                    is_percussion=(primary_ch == 9),
                )
            )

        # Sort by time
        events.sort(key=lambda e: (e.time_seconds, 0 if e.event_type == "note_off" else 1))

        total_notes = sum(1 for e in events if e.event_type == "note_on")
        duration = events[-1].time_seconds if events else 0.0
        tempo_bpm = mido.tempo2bpm(first_tempo)

        info = MidiFileInfo(
            file_path=str(path),
            name=path.stem,
            duration_seconds=duration,
            track_count=len(mid.tracks),
            note_count=total_notes,
            tempo_bpm=round(tempo_bpm, 1),
            tracks=tuple(track_infos),
        )

        return events, info


# ──────────────────────────────────────────────
# Qt-dependent (requires running QApplication)
# ──────────────────────────────────────────────

# These classes use a pattern where the base class is resolved at definition time.
# To avoid module-level Qt import, we use a factory approach.

_PlaybackWorkerClass = None
_MidiFilePlayerControllerClass = None


def _ensure_qt_classes():
    """Define Qt-dependent classes on first use."""
    global _PlaybackWorkerClass, _MidiFilePlayerControllerClass

    if _PlaybackWorkerClass is not None:
        return

    from PyQt6.QtCore import QObject, pyqtSignal

    class PlaybackWorker(QObject):
        """Worker that plays MIDI file events with precise timing on a background thread.

        The playback loop runs on a dedicated ``threading.Thread`` so it never
        blocks the Qt event loop.  Pause / stop are controlled via
        ``threading.Event`` flags that the loop checks each iteration.
        Qt signals emitted from the playback thread are automatically queued
        to the main thread for safe GUI updates.
        """

        note_event = pyqtSignal(str, int, int)
        progress_updated = pyqtSignal(float, float)
        state_changed = pyqtSignal(int)
        playback_finished = pyqtSignal()
        countdown_tick = pyqtSignal(int)  # remaining beats (4, 3, 2, 1, 0)

        _COUNT_IN_BEATS = 4
        _COUNT_IN_INTERVAL = 1.0  # seconds between beats
        _TICK_FREQ = 800  # Hz
        _TICK_DURATION = 60  # ms

        def __init__(self, mapper, simulator) -> None:
            super().__init__()
            self._mapper = mapper
            self._simulator = simulator
            self._events: list[MidiFileEvent] = []
            self._info: MidiFileInfo | None = None
            self._state = PlaybackState.STOPPED
            self._speed = 1.0
            self._lock = threading.Lock()
            self._stop_flag = threading.Event()
            self._pause_flag = threading.Event()
            self._index = 0
            self._position = 0.0
            self._playback_thread: threading.Thread | None = None

        @property
        def state(self) -> PlaybackState:
            return self._state

        @property
        def info(self) -> MidiFileInfo | None:
            return self._info

        @property
        def position(self) -> float:
            return self._position

        def load(self, events: list[MidiFileEvent], info: MidiFileInfo) -> None:
            self.stop()
            self._events = events
            self._info = info
            self._index = 0
            self._position = 0.0

        def set_speed(self, speed: float) -> None:
            with self._lock:
                self._speed = max(0.25, min(2.0, speed))

        def play(self) -> None:
            if self._state == PlaybackState.PAUSED:
                # Resume — unblock the existing playback thread
                self._pause_flag.set()
                self._state = PlaybackState.PLAYING
                self.state_changed.emit(self._state)
                return
            if self._state == PlaybackState.PLAYING:
                return
            if not self._events:
                return
            # Wait for any previous playback thread to finish
            self._join_playback_thread()
            self._stop_flag.clear()
            self._pause_flag.set()
            self._state = PlaybackState.PLAYING
            self.state_changed.emit(self._state)
            # Launch playback on a dedicated thread (non-blocking)
            self._playback_thread = threading.Thread(
                target=self._run_playback,
                daemon=True,
                name="midi-playback",
            )
            self._playback_thread.start()

        def pause(self) -> None:
            if self._state == PlaybackState.PLAYING:
                self._pause_flag.clear()
                self._state = PlaybackState.PAUSED
                self.state_changed.emit(self._state)

        def stop(self) -> None:
            if self._state == PlaybackState.STOPPED:
                return
            self._stop_flag.set()
            self._pause_flag.set()  # unblock if paused
            self._join_playback_thread()
            self._simulator.release_all()
            self._state = PlaybackState.STOPPED
            self._index = 0
            self._position = 0.0
            self.state_changed.emit(self._state)

        def seek(self, position_seconds: float) -> None:
            self._simulator.release_all()
            position_seconds = max(0.0, position_seconds)
            self._position = position_seconds
            self._index = 0
            for i, evt in enumerate(self._events):
                if evt.time_seconds >= position_seconds:
                    self._index = i
                    break
            else:
                self._index = len(self._events)
            duration = self._info.duration_seconds if self._info else 0.0
            self.progress_updated.emit(self._position, duration)

        def _join_playback_thread(self) -> None:
            """Wait for the playback thread to finish (if running)."""
            if self._playback_thread is not None and self._playback_thread.is_alive():
                self._playback_thread.join(timeout=3.0)
            self._playback_thread = None

        def _play_tick(self) -> None:
            """Play a short metronome tick via winsound.Beep (Windows only)."""
            try:
                import winsound

                winsound.Beep(self._TICK_FREQ, self._TICK_DURATION)  # type: ignore[attr-defined, unused-ignore]  # Windows-only
            except Exception:
                pass  # Graceful fallback on non-Windows or error

        def _count_in(self) -> bool:
            """4-beat metronome count-in. Returns False if stopped during count-in."""
            for remaining in range(self._COUNT_IN_BEATS, 0, -1):
                if self._stop_flag.is_set():
                    self.countdown_tick.emit(0)
                    return False

                # Respect pause during count-in
                if not self._pause_flag.is_set():
                    self._pause_flag.wait()
                    if self._stop_flag.is_set():
                        self.countdown_tick.emit(0)
                        return False

                self.countdown_tick.emit(remaining)
                self._play_tick()

                # Wait ~1 second, interruptible by stop/pause
                deadline = time.perf_counter() + self._COUNT_IN_INTERVAL
                while time.perf_counter() < deadline:
                    if self._stop_flag.is_set():
                        self.countdown_tick.emit(0)
                        return False
                    if not self._pause_flag.is_set():
                        # Paused — wait for resume, then restart this beat's wait
                        self._pause_flag.wait()
                        if self._stop_flag.is_set():
                            self.countdown_tick.emit(0)
                            return False
                        deadline = time.perf_counter() + self._COUNT_IN_INTERVAL
                        self.countdown_tick.emit(remaining)
                        self._play_tick()
                    time.sleep(0.01)

            self.countdown_tick.emit(0)
            return True

        def _run_playback(self) -> None:
            """Blocking playback loop — runs on a dedicated thread."""
            from .priority import set_thread_priority_realtime

            set_thread_priority_realtime()

            # Count-in: 4 beats of metronome before actual playback
            if not self._count_in():
                return

            duration = self._info.duration_seconds if self._info else 0.0
            # Anchor interpolation timer right after count-in ends
            self.progress_updated.emit(0.0, duration)

            start_wall = time.perf_counter()
            start_position = self._position

            while self._index < len(self._events):
                if self._stop_flag.is_set():
                    return

                if not self._pause_flag.is_set():
                    self._pause_flag.wait()
                    if self._stop_flag.is_set():
                        return
                    start_wall = time.perf_counter()
                    start_position = self._position

                evt = self._events[self._index]

                with self._lock:
                    speed = self._speed
                target_wall = start_wall + (evt.time_seconds - start_position) / speed
                now = time.perf_counter()
                wait = target_wall - now

                if wait > 0.002:
                    time.sleep(wait - 0.001)
                while time.perf_counter() < target_wall:
                    if self._stop_flag.is_set():
                        return

                if evt.event_type == "note_on":
                    mapping = self._mapper.lookup(evt.note)
                    if mapping is not None:
                        self._simulator.press(evt.note, mapping)
                elif evt.event_type == "note_off":
                    self._simulator.release(evt.note)

                self._position = evt.time_seconds
                self._index += 1

                self.note_event.emit(evt.event_type, evt.note, evt.velocity)
                self.progress_updated.emit(self._position, duration)

            self._simulator.release_all()
            self._state = PlaybackState.STOPPED
            self._index = 0
            self._position = 0.0
            self.state_changed.emit(self._state)
            self.playback_finished.emit()

    class MidiFilePlayerController(QObject):
        """High-level playback controller — owns the worker, exposes signals."""

        note_event = pyqtSignal(str, int, int)
        progress_updated = pyqtSignal(float, float)
        state_changed = pyqtSignal(int)
        playback_finished = pyqtSignal()
        countdown_tick = pyqtSignal(int)

        def __init__(self, mapper, simulator, parent=None) -> None:
            super().__init__(parent)
            self._worker = PlaybackWorker(mapper, simulator)

            self._worker.note_event.connect(self.note_event)
            self._worker.progress_updated.connect(self.progress_updated)
            self._worker.state_changed.connect(self.state_changed)
            self._worker.playback_finished.connect(self.playback_finished)
            self._worker.countdown_tick.connect(self.countdown_tick)

        @property
        def worker(self):
            return self._worker

        @property
        def state(self) -> PlaybackState:
            return self._worker.state

        @property
        def info(self) -> MidiFileInfo | None:
            return self._worker.info

        def load_file(self, file_path: str, **preprocess_kwargs) -> tuple:
            from .midi_preprocessor import preprocess

            events, info = MidiFileParser.parse(file_path)
            events, stats = preprocess(events, **preprocess_kwargs)
            self._worker.load(events, info)
            return info, stats

        def play(self) -> None:
            self._worker.play()

        def pause(self) -> None:
            self._worker.pause()

        def stop(self) -> None:
            self._worker.stop()

        def seek(self, position: float) -> None:
            self._worker.seek(position)

        def set_speed(self, speed: float) -> None:
            self._worker.set_speed(speed)

        def cleanup(self) -> None:
            self._worker.stop()

    _PlaybackWorkerClass = PlaybackWorker
    _MidiFilePlayerControllerClass = MidiFilePlayerController


def get_playback_worker_class():
    """Get the PlaybackWorker class (requires running QApplication)."""
    _ensure_qt_classes()
    return _PlaybackWorkerClass


def get_player_controller_class():
    """Get the MidiFilePlayerController class (requires running QApplication)."""
    _ensure_qt_classes()
    return _MidiFilePlayerControllerClass


# Convenience aliases for use from GUI code that already has Qt running
def create_player_controller(mapper, simulator, parent=None):
    """Create a MidiFilePlayerController (requires running QApplication)."""
    cls = get_player_controller_class()
    return cls(mapper, simulator, parent)
