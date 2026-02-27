"""MIDI output player — sends events to system synthesizer for audio preview.

Uses python-rtmidi to open a MIDI output port (typically Windows GS Wavetable Synth).
Plays MidiFileEvent list in a background thread with timing, progress, and stop support.

Qt-dependent class uses the lazy-definition pattern (same as midi_file_player.py)
to avoid module-level Qt imports.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .midi_file_player import MidiFileEvent

log = logging.getLogger(__name__)

# ── Lazy Qt class ──────────────────────────────────────────

_MidiOutputPlayerClass = None


def _ensure_qt_class():
    """Define the Qt-dependent MidiOutputPlayer on first use."""
    global _MidiOutputPlayerClass

    if _MidiOutputPlayerClass is not None:
        return

    from PyQt6.QtCore import QObject, pyqtSignal

    from .midi_file_player import PlaybackState

    class MidiOutputPlayer(QObject):
        """Play MidiFileEvent list through system MIDI synthesizer.

        Opens an rtmidi output port to the first available MIDI synth
        (Windows GS Wavetable Synth on Windows).  Plays events on a
        background thread with accurate timing.
        """

        progress_updated = pyqtSignal(float, float)  # current_sec, total_sec
        state_changed = pyqtSignal(int)  # PlaybackState value
        playback_finished = pyqtSignal()
        note_fired = pyqtSignal(str, int, int)  # event_type, note, velocity

        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self._midi_out = None
            self._port_name: str = ""
            self._events: list[MidiFileEvent] = []
            self._duration: float = 0.0
            self._speed: float = 1.0
            self._loop_enabled: bool = False
            self._state = PlaybackState.STOPPED
            self._stop_flag = threading.Event()
            self._pause_flag = threading.Event()
            self._pause_flag.set()  # Not paused initially
            self._thread: threading.Thread | None = None
            self._open_port()

        @property
        def state(self) -> PlaybackState:
            return self._state

        @property
        def available(self) -> bool:
            return self._midi_out is not None

        def _open_port(self) -> None:
            """Try to open the first available MIDI output port."""
            try:
                import rtmidi

                out = rtmidi.MidiOut()
                ports = out.get_ports()
                if not ports:
                    log.warning("No MIDI output ports available")
                    out.delete()
                    return
                # Prefer Windows GS Wavetable Synth if present
                target_idx = 0
                for i, name in enumerate(ports):
                    if "wavetable" in name.lower() or "gs" in name.lower():
                        target_idx = i
                        break
                out.open_port(target_idx)
                self._midi_out = out
                self._port_name = ports[target_idx]
                log.info("MIDI output opened: %s", self._port_name)
            except Exception:
                log.warning("Failed to open MIDI output port", exc_info=True)

        def preview_note(
            self,
            midi_note: int,
            velocity: int = 100,
            duration_ms: int = 200,
        ) -> None:
            """Play a short preview of a single note."""
            if self._midi_out is None:
                return
            note = midi_note & 0x7F
            vel = velocity & 0x7F
            self._midi_out.send_message([0x90, note, vel])

            def _off():
                if self._midi_out is not None:
                    try:
                        self._midi_out.send_message([0x80, note, 0])
                    except Exception:
                        pass

            threading.Timer(duration_ms / 1000.0, _off).start()

        def set_speed(self, speed: float) -> None:
            """Set playback speed multiplier (0.25x – 2.0x)."""
            self._speed = max(0.25, min(2.0, speed))

        def set_loop(self, enabled: bool) -> None:
            """Enable or disable loop playback."""
            self._loop_enabled = enabled

        def set_metronome(self, enabled: bool) -> None:
            """Enable or disable metronome count-in (no-op for output player)."""

        def load(self, events: list[MidiFileEvent], duration: float) -> None:
            """Store events for playback."""
            self.stop()
            self._events = list(events)
            self._duration = duration

        def play(self) -> None:
            """Start or resume playback on a background thread."""
            if self._midi_out is None:
                return
            if self._state == PlaybackState.PAUSED:
                # Resume from pause
                self._pause_flag.set()
                self._state = PlaybackState.PLAYING
                self.state_changed.emit(self._state)
                return
            if self._state == PlaybackState.PLAYING:
                return
            if not self._events:
                return
            self._join_thread()
            self._stop_flag.clear()
            self._pause_flag.set()
            self._state = PlaybackState.PLAYING
            self.state_changed.emit(self._state)
            self._thread = threading.Thread(
                target=self._run,
                daemon=True,
                name="midi-output-preview",
            )
            self._thread.start()

        def pause(self) -> None:
            """Pause playback (can be resumed with play())."""
            if self._state == PlaybackState.PLAYING:
                self._pause_flag.clear()
                self._state = PlaybackState.PAUSED
                self.state_changed.emit(self._state)

        def stop(self) -> None:
            """Stop playback, send all-notes-off."""
            if self._state == PlaybackState.STOPPED:
                return
            self._stop_flag.set()
            self._pause_flag.set()  # Unblock if paused so thread can exit
            self._join_thread()
            self._all_notes_off()
            self._state = PlaybackState.STOPPED
            self.state_changed.emit(self._state)

        def cleanup(self) -> None:
            """Stop and close the MIDI port."""
            self.stop()
            if self._midi_out is not None:
                try:
                    self._midi_out.close_port()
                    self._midi_out.delete()
                except Exception:
                    pass
                self._midi_out = None

        def _join_thread(self) -> None:
            if self._thread is not None and self._thread.is_alive():
                self._thread.join(timeout=3.0)
            self._thread = None

        def _all_notes_off(self) -> None:
            """Send CC 123 (all notes off) on all 16 channels."""
            if self._midi_out is None:
                return
            for ch in range(16):
                try:
                    self._midi_out.send_message([0xB0 | ch, 123, 0])
                except Exception:
                    pass

        def _run(self) -> None:
            """Blocking playback loop on background thread.

            Uses incremental timing so speed changes take effect immediately.
            Each event's wait is computed from the previous event using
            the *current* speed, not a stale snapshot.
            """
            while True:
                duration = self._duration
                prev_song_time = 0.0
                wall_cursor = time.perf_counter()

                for evt in self._events:
                    if self._stop_flag.is_set():
                        return

                    # Re-read speed for each event so mid-playback changes work
                    speed = self._speed
                    delta_song = evt.time_seconds - prev_song_time
                    target_wall = wall_cursor + delta_song / speed
                    now = time.perf_counter()
                    wait = target_wall - now

                    if wait > 0.002:
                        while wait > 0.03:
                            if self._stop_flag.wait(timeout=0.03):
                                return
                            # Pause gate within wait loop
                            if not self._pause_flag.is_set():
                                pause_start = time.perf_counter()
                                self._pause_flag.wait()
                                if self._stop_flag.is_set():
                                    return
                                paused_dur = time.perf_counter() - pause_start
                                wall_cursor += paused_dur
                                target_wall += paused_dur
                            # Re-read speed during wait (allows live speed change)
                            speed = self._speed
                            target_wall = wall_cursor + delta_song / speed
                            # Emit progress
                            self.progress_updated.emit(evt.time_seconds, duration)

                            now = time.perf_counter()
                            wait = target_wall - now

                        if wait > 0.002:
                            if self._stop_flag.wait(timeout=wait - 0.001):
                                return

                    # Busy-spin for the final sub-millisecond
                    while time.perf_counter() < target_wall:
                        if self._stop_flag.is_set():
                            return

                    # Pause gate — blocks here while paused
                    if not self._pause_flag.is_set():
                        pause_start = time.perf_counter()
                        self._pause_flag.wait()
                        if self._stop_flag.is_set():
                            return
                        wall_cursor += time.perf_counter() - pause_start

                    if self._midi_out is None:
                        return

                    ch = getattr(evt, "channel", 0) & 0x0F
                    if evt.event_type == "note_on":
                        self._midi_out.send_message(
                            [0x90 | ch, evt.note & 0x7F, evt.velocity & 0x7F],
                        )
                        self.note_fired.emit("note_on", evt.note, evt.velocity)
                    elif evt.event_type == "note_off":
                        self._midi_out.send_message(
                            [0x80 | ch, evt.note & 0x7F, 0],
                        )
                        self.note_fired.emit("note_off", evt.note, 0)

                    self.progress_updated.emit(evt.time_seconds, duration)

                    # Advance cursors for next iteration
                    prev_song_time = evt.time_seconds
                    wall_cursor = time.perf_counter()

                # Wait out any remaining duration (trailing rests)
                speed = self._speed
                elapsed_song = prev_song_time
                remaining_song = duration - elapsed_song
                if remaining_song > 0.01:
                    self._stop_flag.wait(timeout=remaining_song / speed)

                if not self._loop_enabled or self._stop_flag.is_set():
                    break

                # Loop: send all-notes-off before restarting
                self._all_notes_off()

            # Playback finished naturally (or was stopped during trailing wait)
            self._all_notes_off()
            self._state = PlaybackState.STOPPED
            self.state_changed.emit(self._state)
            if not self._stop_flag.is_set():
                self.playback_finished.emit()

    _MidiOutputPlayerClass = MidiOutputPlayer


def create_midi_output_player(parent=None):
    """Create a MidiOutputPlayer instance (requires running QApplication).

    Returns None if the MIDI output port could not be opened.
    """
    _ensure_qt_class()
    assert _MidiOutputPlayerClass is not None
    player = _MidiOutputPlayerClass(parent)
    if not player.available:
        player.cleanup()
        return None
    return player
