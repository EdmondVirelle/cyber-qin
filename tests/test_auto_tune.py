"""Tests for auto-tune — quantization and pitch correction."""

from cyber_qin.core.auto_tune import (
    AutoTuneStats,
    QuantizeGrid,
    auto_tune,
    quantize_to_beat_grid,
    snap_to_scale,
)
from cyber_qin.core.midi_recorder import RecordedEvent


def _make_events(*times_notes: tuple[float, int]) -> list[RecordedEvent]:
    """Create note_on events at given (time, note) pairs."""
    return [
        RecordedEvent(timestamp=t, event_type="note_on", note=n, velocity=100)
        for t, n in times_notes
    ]


class TestQuantizeToBeatGrid:
    def test_exact_grid_no_change(self):
        """Events already on the grid should not move."""
        events = _make_events((0.0, 60), (0.5, 64), (1.0, 67))
        result = quantize_to_beat_grid(events, 120.0, QuantizeGrid.EIGHTH, 1.0)
        for orig, quant in zip(events, result):
            assert abs(orig.timestamp - quant.timestamp) < 1e-6

    def test_snap_to_nearest_eighth(self):
        """Events slightly off grid should snap."""
        events = _make_events((0.12, 60), (0.48, 64))
        result = quantize_to_beat_grid(events, 120.0, QuantizeGrid.EIGHTH, 1.0)
        # At 120 BPM, eighth = 0.25s. 0.12 snaps to 0.0 or 0.25.
        # nearest to 0.12 is 0.0
        assert abs(result[0].timestamp - 0.0) < 0.01
        # 0.48 snaps to 0.5
        assert abs(result[1].timestamp - 0.5) < 0.01

    def test_strength_zero_no_change(self):
        events = _make_events((0.12, 60), (0.48, 64))
        result = quantize_to_beat_grid(events, 120.0, QuantizeGrid.EIGHTH, 0.0)
        for orig, quant in zip(events, result):
            assert abs(orig.timestamp - quant.timestamp) < 1e-6

    def test_strength_partial(self):
        """Strength 0.5 should move halfway to grid."""
        events = _make_events((0.12, 60),)
        result = quantize_to_beat_grid(events, 120.0, QuantizeGrid.EIGHTH, 0.5)
        # Nearest grid to 0.12 at 0.25s grid = 0.0 (or 0.25)
        # 0.12 is closer to 0.0. new = 0.12 + (0.0 - 0.12) * 0.5 = 0.06
        assert abs(result[0].timestamp - 0.06) < 0.01

    def test_quarter_grid(self):
        events = _make_events((0.3, 60),)
        result = quantize_to_beat_grid(events, 120.0, QuantizeGrid.QUARTER, 1.0)
        # At 120 BPM, quarter = 0.5s. 0.3 snaps to 0.5.
        assert abs(result[0].timestamp - 0.5) < 0.01

    def test_sixteenth_grid(self):
        events = _make_events((0.13, 60),)
        result = quantize_to_beat_grid(events, 120.0, QuantizeGrid.SIXTEENTH, 1.0)
        # At 120 BPM, 16th = 0.125s. 0.13 snaps to 0.125.
        assert abs(result[0].timestamp - 0.125) < 0.01

    def test_empty_events(self):
        result = quantize_to_beat_grid([], 120.0, QuantizeGrid.EIGHTH, 1.0)
        assert result == []

    def test_preserves_note_data(self):
        events = [RecordedEvent(0.12, "note_on", 72, 90)]
        result = quantize_to_beat_grid(events, 120.0, QuantizeGrid.EIGHTH, 1.0)
        assert result[0].note == 72
        assert result[0].velocity == 90
        assert result[0].event_type == "note_on"

    def test_no_negative_timestamps(self):
        """Even with quantization, timestamps should never go negative."""
        events = _make_events((0.01, 60),)
        result = quantize_to_beat_grid(events, 120.0, QuantizeGrid.EIGHTH, 1.0)
        assert result[0].timestamp >= 0.0


class TestSnapToScale:
    def test_in_range_no_change(self):
        events = _make_events((0.0, 60), (0.5, 72))
        result = snap_to_scale(events, 48, 83)
        assert result[0].note == 60
        assert result[1].note == 72

    def test_above_range_folds_down(self):
        events = _make_events((0.0, 96),)  # C7 — well above range
        result = snap_to_scale(events, 48, 83)
        assert 48 <= result[0].note <= 83

    def test_below_range_folds_up(self):
        events = _make_events((0.0, 24),)  # C1 — well below range
        result = snap_to_scale(events, 48, 83)
        assert 48 <= result[0].note <= 83


class TestAutoTune:
    def test_combined_pipeline(self):
        events = _make_events((0.12, 60), (0.48, 96))
        result, stats = auto_tune(events, tempo_bpm=120.0)
        assert isinstance(stats, AutoTuneStats)
        assert stats.total_events == 2
        assert len(result) == 2

    def test_no_quantize(self):
        events = _make_events((0.12, 60),)
        result, stats = auto_tune(events, do_quantize=False)
        assert abs(result[0].timestamp - 0.12) < 1e-6
        assert stats.quantized_count == 0

    def test_no_pitch_correct(self):
        events = _make_events((0.0, 96),)
        result, stats = auto_tune(events, do_pitch_correct=False)
        assert result[0].note == 96
        assert stats.pitch_corrected_count == 0

    def test_stats_counts(self):
        events = _make_events((0.12, 96),)  # Off grid and out of range
        _, stats = auto_tune(events, tempo_bpm=120.0, note_min=48, note_max=83)
        assert stats.quantized_count > 0
        assert stats.pitch_corrected_count > 0
