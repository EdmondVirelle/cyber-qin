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


@dataclass(frozen=True, slots=True)
class MidiFileInfo:
    """Metadata about a parsed MIDI file."""
    file_path: str
    name: str
    duration_seconds: float
    track_count: int
    note_count: int
    tempo_bpm: float


class MidiFileParser:
    """Parse .mid files into sorted event lists."""

    @staticmethod
    def parse(file_path: str) -> tuple[list[MidiFileEvent], MidiFileInfo]:
        """Parse a MIDI file into a list of timed events + metadata.

        Returns (events, info) where events are sorted by time_seconds.
        Handles velocity-0 note_on as note_off.
        Correctly converts tick-based delta times to seconds using tempo map.
        """
        path = Path(file_path)
        mid = mido.MidiFile(str(path))
        tpb = mid.ticks_per_beat

        # Build timed event list, tracking tempo changes
        events: list[MidiFileEvent] = []
        abs_time_sec = 0.0
        tempo = 500000  # Default 120 BPM (microseconds per beat)
        note_count = 0
        first_tempo = tempo

        for msg in mido.merge_tracks(mid.tracks):
            # Convert delta ticks to seconds
            abs_time_sec += mido.tick2second(msg.time, tpb, tempo)

            if msg.type == "set_tempo":
                tempo = msg.tempo
                if note_count == 0:
                    first_tempo = tempo
            elif msg.type == "note_on" and msg.velocity > 0:
                events.append(MidiFileEvent(
                    time_seconds=abs_time_sec,
                    event_type="note_on",
                    note=msg.note,
                    velocity=msg.velocity,
                ))
                note_count += 1
            elif msg.type == "note_off" or (
                msg.type == "note_on" and msg.velocity == 0
            ):
                events.append(MidiFileEvent(
                    time_seconds=abs_time_sec,
                    event_type="note_off",
                    note=msg.note,
                    velocity=0,
                ))

        duration = events[-1].time_seconds if events else 0.0
        tempo_bpm = mido.tempo2bpm(first_tempo)

        info = MidiFileInfo(
            file_path=str(path),
            name=path.stem,
            duration_seconds=duration,
            track_count=len(mid.tracks),
            note_count=note_count,
            tempo_bpm=round(tempo_bpm, 1),
        )

        return events, info


# ──────────────────────────────────────────────
# Qt-dependent (requires running QApplication)
# ──────────────────────────────────────────────

def _import_qt():
    """Lazy import of PyQt6 classes."""
    from PyQt6.QtCore import QObject, QThread, pyqtSignal
    return QObject, QThread, pyqtSignal


# These classes use a pattern where the base class is resolved at definition time.
# To avoid module-level Qt import, we use a factory approach.

_PlaybackWorkerClass = None
_MidiFilePlayerControllerClass = None


def _ensure_qt_classes():
    """Define Qt-dependent classes on first use."""
    global _PlaybackWorkerClass, _MidiFilePlayerControllerClass

    if _PlaybackWorkerClass is not None:
        return

    from PyQt6.QtCore import QObject, QThread, pyqtSignal

    class PlaybackWorker(QObject):
        """Worker that runs on a QThread to play MIDI file events with precise timing."""

        note_event = pyqtSignal(str, int, int)
        progress_updated = pyqtSignal(float, float)
        state_changed = pyqtSignal(int)
        playback_finished = pyqtSignal()

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
                self._pause_flag.set()
                self._state = PlaybackState.PLAYING
                self.state_changed.emit(self._state)
                return
            if self._state == PlaybackState.PLAYING:
                return
            if not self._events:
                return
            self._stop_flag.clear()
            self._pause_flag.set()
            self._state = PlaybackState.PLAYING
            self.state_changed.emit(self._state)
            self._run_playback()

        def pause(self) -> None:
            if self._state == PlaybackState.PLAYING:
                self._pause_flag.clear()
                self._state = PlaybackState.PAUSED
                self.state_changed.emit(self._state)

        def stop(self) -> None:
            if self._state == PlaybackState.STOPPED:
                return
            self._stop_flag.set()
            self._pause_flag.set()
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

        def _run_playback(self) -> None:
            duration = self._info.duration_seconds if self._info else 0.0
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
        """Manages the playback thread lifecycle."""

        note_event = pyqtSignal(str, int, int)
        progress_updated = pyqtSignal(float, float)
        state_changed = pyqtSignal(int)
        playback_finished = pyqtSignal()

        def __init__(self, mapper, simulator, parent=None) -> None:
            super().__init__(parent)
            self._thread = QThread()
            self._worker = PlaybackWorker(mapper, simulator)
            self._worker.moveToThread(self._thread)

            self._worker.note_event.connect(self.note_event)
            self._worker.progress_updated.connect(self.progress_updated)
            self._worker.state_changed.connect(self.state_changed)
            self._worker.playback_finished.connect(self.playback_finished)

            self._thread.start()

        @property
        def worker(self):
            return self._worker

        @property
        def state(self) -> PlaybackState:
            return self._worker.state

        @property
        def info(self) -> MidiFileInfo | None:
            return self._worker.info

        def load_file(self, file_path: str) -> MidiFileInfo:
            events, info = MidiFileParser.parse(file_path)
            self._worker.load(events, info)
            return info

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
            self._thread.quit()
            self._thread.wait(3000)

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
