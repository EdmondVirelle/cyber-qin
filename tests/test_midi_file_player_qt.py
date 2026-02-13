"""Tests for PlaybackWorker and MidiFilePlayerController — requires Qt."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import Mock

import mido
import pytest
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

from cyber_qin.core.key_mapper import KeyMapper
from cyber_qin.core.key_simulator import KeySimulator
from cyber_qin.core.midi_file_player import (
    MidiFileEvent,
    MidiFileInfo,
    PlaybackState,
    create_player_controller,
    get_playback_worker_class,
)


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for Qt-dependent tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mapper():
    """Create KeyMapper instance."""
    return KeyMapper()


@pytest.fixture
def simulator():
    """Create KeySimulator instance."""
    return KeySimulator()


@pytest.fixture
def simple_events():
    """Create simple test events."""
    return [
        MidiFileEvent(0.0, "note_on", 60, 80),
        MidiFileEvent(0.5, "note_off", 60, 0),
        MidiFileEvent(0.5, "note_on", 64, 90),
        MidiFileEvent(1.0, "note_off", 64, 0),
    ]


@pytest.fixture
def simple_info():
    """Create simple MidiFileInfo."""
    return MidiFileInfo(
        file_path="/test.mid",
        name="test",
        duration_seconds=1.0,
        track_count=1,
        note_count=2,
        tempo_bpm=120.0,
    )


@pytest.fixture
def test_midi_file(tmp_path: Path) -> str:
    """Create a simple MIDI file for integration tests."""
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage("set_tempo", tempo=500000))  # 120 BPM
    track.append(mido.Message("note_on", note=60, velocity=80, time=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=240))  # 0.25s at 120 BPM
    track.append(mido.Message("note_on", note=64, velocity=90, time=0))
    track.append(mido.Message("note_off", note=64, velocity=0, time=240))  # 0.25s
    track.append(mido.MetaMessage("end_of_track", time=0))

    path = str(tmp_path / "test_playback.mid")
    mid.save(path)
    return path


class TestPlaybackWorker:
    """Test PlaybackWorker (Qt-dependent class)."""

    @pytest.fixture
    def worker(self, qapp, mapper, simulator):
        """Create PlaybackWorker instance."""
        worker_class = get_playback_worker_class()
        return worker_class(mapper, simulator)

    def test_initial_state(self, worker):
        """Worker should start in STOPPED state."""
        assert worker.state == PlaybackState.STOPPED
        assert worker.info is None
        assert worker.position == 0.0

    def test_load_events(self, worker, simple_events, simple_info):
        """Should load events and info."""
        worker.load(simple_events, simple_info)

        assert worker.info == simple_info
        assert worker.position == 0.0

    def test_load_resets_position(self, worker, simple_events, simple_info):
        """Loading new events should reset playback position."""
        worker.load(simple_events, simple_info)
        worker._position = 0.5
        worker._index = 2

        # Load again
        worker.load(simple_events, simple_info)

        assert worker.position == 0.0
        assert worker._index == 0

    def test_set_speed_clamps(self, worker):
        """Speed should be clamped to 0.25-2.0 range."""
        worker.set_speed(0.1)
        assert worker._speed == 0.25

        worker.set_speed(5.0)
        assert worker._speed == 2.0

        worker.set_speed(1.5)
        assert worker._speed == 1.5

    def test_stop_when_already_stopped(self, worker):
        """Stopping when already stopped should be a no-op."""
        assert worker.state == PlaybackState.STOPPED
        worker.stop()  # Should not raise
        assert worker.state == PlaybackState.STOPPED

    def test_play_empty_events(self, worker):
        """Playing with no events should be a no-op."""
        worker.play()
        assert worker.state == PlaybackState.STOPPED

    def test_play_when_already_playing(self, worker, simple_events, simple_info):
        """Playing when already playing should be a no-op."""
        worker.load(simple_events, simple_info)
        worker.play()
        initial_state = worker.state

        worker.play()  # Call again

        assert worker.state == initial_state

    def test_state_signal_emission(self, worker, simple_events, simple_info, qapp):
        """State changes should emit state_changed signal."""
        worker.load(simple_events, simple_info)

        states_emitted = []

        def on_state_changed(state):
            states_emitted.append(state)

        worker.state_changed.connect(on_state_changed)

        worker.play()
        QApplication.processEvents()
        assert PlaybackState.PLAYING in states_emitted

        worker.pause()
        QApplication.processEvents()
        assert PlaybackState.PAUSED in states_emitted

        worker.stop()
        QApplication.processEvents()
        assert PlaybackState.STOPPED in states_emitted

    def test_pause_while_stopped(self, worker):
        """Pausing while stopped should have no effect."""
        worker.pause()
        assert worker.state == PlaybackState.STOPPED

    def test_seek_updates_position(self, worker, simple_events, simple_info):
        """Seek should update position."""
        worker.load(simple_events, simple_info)

        worker.seek(0.7)

        assert worker.position == 0.7
        # Index should advance to event at or after 0.7s
        assert worker._index >= 2  # Events at 0.5s passed

    def test_seek_clamps_negative(self, worker, simple_events, simple_info):
        """Seek should clamp negative values to 0."""
        worker.load(simple_events, simple_info)

        worker.seek(-1.0)

        assert worker.position == 0.0

    def test_seek_beyond_end(self, worker, simple_events, simple_info):
        """Seek beyond end should set index to end of events."""
        worker.load(simple_events, simple_info)

        worker.seek(10.0)

        assert worker._index == len(simple_events)

    def test_seek_emits_progress(self, worker, simple_events, simple_info, qapp):
        """Seek should emit progress_updated signal."""
        worker.load(simple_events, simple_info)

        progress_emitted = []

        def on_progress(position, duration):
            progress_emitted.append((position, duration))

        worker.progress_updated.connect(on_progress)

        worker.seek(0.5)
        QApplication.processEvents()

        assert len(progress_emitted) > 0
        assert progress_emitted[-1][0] == 0.5
        assert progress_emitted[-1][1] == 1.0

    def test_resume_from_pause(self, worker, simple_events, simple_info, qapp):
        """Playing after pause should resume playback."""
        worker.load(simple_events, simple_info)

        states = []

        def on_state_changed(state):
            states.append(state)

        worker.state_changed.connect(on_state_changed)

        worker.play()
        QApplication.processEvents()

        worker.pause()
        QApplication.processEvents()

        worker.play()  # Resume
        QApplication.processEvents()

        # Should see: PLAYING -> PAUSED -> PLAYING
        assert states == [PlaybackState.PLAYING, PlaybackState.PAUSED, PlaybackState.PLAYING]

    def test_stop_resets_position(self, worker, simple_events, simple_info, qapp):
        """Stop should reset position and index to 0."""
        worker.load(simple_events, simple_info)
        worker.play()  # Start playing so stop() will actually run
        QApplication.processEvents()

        # Set position manually to simulate mid-playback
        worker._position = 0.5
        worker._index = 2

        worker.stop()

        assert worker.position == 0.0
        assert worker._index == 0
        assert worker.state == PlaybackState.STOPPED


class TestMidiFilePlayerController:
    """Test MidiFilePlayerController high-level API."""

    @pytest.fixture
    def controller(self, qapp, mapper, simulator):
        """Create MidiFilePlayerController instance."""
        return create_player_controller(mapper, simulator)

    def test_initial_state(self, controller):
        """Controller should start in STOPPED state."""
        assert controller.state == PlaybackState.STOPPED
        assert controller.info is None

    def test_load_file(self, controller, test_midi_file):
        """Should load and parse MIDI file."""
        info, stats = controller.load_file(test_midi_file)

        assert info is not None
        assert info.note_count > 0
        assert controller.info == info
        assert controller.state == PlaybackState.STOPPED

    def test_play_delegates_to_worker(self, controller, test_midi_file):
        """Play should delegate to worker."""
        controller.load_file(test_midi_file)

        controller.play()

        assert controller.worker.state == PlaybackState.PLAYING

    def test_pause_delegates_to_worker(self, controller, test_midi_file):
        """Pause should delegate to worker."""
        controller.load_file(test_midi_file)
        controller.play()

        controller.pause()

        assert controller.worker.state == PlaybackState.PAUSED

    def test_stop_delegates_to_worker(self, controller, test_midi_file):
        """Stop should delegate to worker."""
        controller.load_file(test_midi_file)
        controller.play()

        controller.stop()

        assert controller.worker.state == PlaybackState.STOPPED

    def test_seek_delegates_to_worker(self, controller, test_midi_file):
        """Seek should delegate to worker."""
        controller.load_file(test_midi_file)
        initial_pos = controller.worker.position

        controller.seek(0.3)

        assert controller.worker.position != initial_pos

    def test_set_speed_delegates_to_worker(self, controller):
        """Set speed should delegate to worker."""
        controller.set_speed(1.5)

        assert controller.worker._speed == 1.5

    def test_cleanup_stops_playback(self, controller, test_midi_file):
        """Cleanup should stop playback."""
        controller.load_file(test_midi_file)
        controller.play()

        controller.cleanup()

        assert controller.worker.state == PlaybackState.STOPPED

    def test_signals_forwarded_state_changed(self, controller, test_midi_file, qapp):
        """Controller should forward worker's state_changed signal."""
        controller.load_file(test_midi_file)

        states = []

        def on_state_changed(state):
            states.append(state)

        controller.state_changed.connect(on_state_changed)

        controller.play()
        QApplication.processEvents()

        controller.stop()
        QApplication.processEvents()

        assert PlaybackState.PLAYING in states
        assert PlaybackState.STOPPED in states

    def test_signals_forwarded_progress(self, controller, test_midi_file, qapp):
        """Controller should forward worker's progress_updated signal."""
        controller.load_file(test_midi_file)

        progress_events = []

        def on_progress(position, duration):
            progress_events.append((position, duration))

        controller.progress_updated.connect(on_progress)

        controller.seek(0.2)
        QApplication.processEvents()

        assert len(progress_events) > 0

    def test_load_file_with_preprocessing(self, controller, test_midi_file):
        """Should apply preprocessing when loading file."""
        # Load with custom preprocessing parameters
        info, stats = controller.load_file(test_midi_file, note_min=48, note_max=83)

        assert info is not None
        # Stats should indicate preprocessing occurred
        assert stats is not None
        assert hasattr(stats, "total_notes")
        assert stats.total_notes >= 0


class TestPlaybackIntegration:
    """Integration tests for full playback workflow."""

    @pytest.fixture
    def controller(self, qapp, mapper, simulator):
        """Create controller with mock simulator to track calls."""
        mock_simulator = Mock(spec=KeySimulator)
        return create_player_controller(mapper, mock_simulator)

    def test_full_playback_cycle(self, controller, test_midi_file, qapp):
        """Test complete playback: load -> play -> pause -> resume -> stop."""
        controller.load_file(test_midi_file)

        # Play
        controller.play()
        assert controller.state == PlaybackState.PLAYING

        # Give playback thread time to start
        time.sleep(0.1)
        QApplication.processEvents()

        # Pause
        controller.pause()
        assert controller.state == PlaybackState.PAUSED

        # Resume
        controller.play()
        assert controller.state == PlaybackState.PLAYING

        # Stop
        controller.stop()
        assert controller.state == PlaybackState.STOPPED
        assert controller.worker.position == 0.0

    def test_playback_emits_events(self, controller, test_midi_file, qapp):
        """Playback should emit note_event signals."""
        controller.load_file(test_midi_file)

        note_events = []

        def on_note_event(event_type, note, velocity):
            note_events.append((event_type, note, velocity))

        controller.note_event.connect(on_note_event)

        controller.play()

        # Wait for count-in (4 beats * 1 second = 4 seconds) + some playback
        # Use QEventLoop with timeout to process signals
        loop = QEventLoop()
        QTimer.singleShot(5500, loop.quit)  # 5.5 seconds
        loop.exec()

        controller.stop()

        # Should have emitted note events
        assert len(note_events) > 0
        # Should have both note_on and note_off
        event_types = {evt[0] for evt in note_events}
        assert "note_on" in event_types
        assert "note_off" in event_types

    def test_countdown_tick_emission(self, controller, test_midi_file, qapp):
        """Playback should emit countdown ticks before playing."""
        controller.load_file(test_midi_file)

        countdown_ticks = []

        def on_countdown(remaining):
            countdown_ticks.append(remaining)

        controller.countdown_tick.connect(on_countdown)

        controller.play()

        # Wait for count-in to complete
        loop = QEventLoop()
        QTimer.singleShot(4500, loop.quit)  # 4.5 seconds (slightly more than 4-beat count-in)
        loop.exec()

        controller.stop()

        # Should have received countdown from 4 to 0
        assert len(countdown_ticks) > 0
        assert 4 in countdown_ticks  # Started at 4
        assert 0 in countdown_ticks  # Ended at 0

    def test_playback_finished_signal(self, controller, qapp):
        """Should emit playback_finished when playback completes."""
        # Create very short MIDI file to test completion
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            mid = mido.MidiFile()
            track = mido.MidiTrack()
            mid.tracks.append(track)
            track.append(mido.MetaMessage("set_tempo", tempo=500000))
            track.append(mido.Message("note_on", note=60, velocity=80, time=0))
            track.append(mido.Message("note_off", note=60, velocity=0, time=48))  # Very short
            track.append(mido.MetaMessage("end_of_track", time=0))

            path = str(Path(tmpdir) / "short.mid")
            mid.save(path)

            controller.load_file(path)

            finished_emitted = []

            def on_finished():
                finished_emitted.append(True)

            controller.playback_finished.connect(on_finished)

            controller.play()

            # Wait for count-in + short playback
            loop = QEventLoop()
            QTimer.singleShot(5000, loop.quit)
            loop.exec()

            # Should have finished
            assert len(finished_emitted) > 0

    def test_speed_control(self, controller, test_midi_file):
        """Should apply speed multiplier to playback."""
        controller.load_file(test_midi_file)

        # Test different speeds
        for speed in [0.25, 0.5, 1.0, 1.5, 2.0]:
            controller.set_speed(speed)
            assert controller.worker._speed == speed

        # Test clamping
        controller.set_speed(0.1)
        assert controller.worker._speed == 0.25

        controller.set_speed(5.0)
        assert controller.worker._speed == 2.0
