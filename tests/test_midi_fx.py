"""Tests for MIDI FX processors (Arpeggiator, Humanize, Quantize, Chord Generator).

All processors operate on ``list[BeatNote]`` and return new lists without mutation.
"""

import pytest

from cyber_qin.core.beat_sequence import BeatNote
from cyber_qin.core.midi_fx import (
    CHORD_INTERVALS,
    ArpeggiatorConfig,
    ChordGenConfig,
    HumanizeConfig,
    QuantizeConfig,
    arpeggiate,
    generate_chords,
    humanize,
    quantize,
)

# ── Arpeggiator Tests ─────────────────────────────────────────


class TestArpeggiator:
    """Tests for the arpeggiator effect."""

    def test_single_note_passthrough(self):
        """Single note at one time should pass through unchanged."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = arpeggiate(notes)
        assert len(result) == 1
        assert result[0].time_beats == 0.0
        assert result[0].note == 60

    def test_two_notes_same_time_spread(self):
        """Two notes at same time should be spread in sequence."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(rate=0.25))
        assert len(result) == 2
        assert result[0].time_beats == 0.0
        assert result[0].note == 60  # lower pitch first
        assert result[1].time_beats == 0.25
        assert result[1].note == 64

    def test_pattern_up_sorts_ascending(self):
        """Pattern "up" should sort notes by pitch ascending."""
        notes = [
            BeatNote(0.0, 0.5, 67, 100, 0),
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(pattern="up", rate=0.25))
        assert len(result) == 3
        assert result[0].note == 60
        assert result[1].note == 64
        assert result[2].note == 67

    def test_pattern_down_sorts_descending(self):
        """Pattern "down" should sort notes by pitch descending."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
            BeatNote(0.0, 0.5, 67, 100, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(pattern="down", rate=0.25))
        assert len(result) == 3
        assert result[0].note == 67
        assert result[1].note == 64
        assert result[2].note == 60

    def test_pattern_up_down_creates_there_and_back(self):
        """Pattern "up_down" should create up-then-down sequence."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
            BeatNote(0.0, 0.5, 67, 100, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(pattern="up_down", rate=0.25))
        # Should be: 60, 64, 67, 64 (middle notes reversed, excluding first and last)
        assert len(result) == 4
        assert result[0].note == 60
        assert result[1].note == 64
        assert result[2].note == 67
        assert result[3].note == 64

    def test_pattern_up_down_with_two_notes(self):
        """Pattern "up_down" with 2 notes should not create middle reversal."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(pattern="up_down", rate=0.25))
        # With 2 notes: [60, 64] + reversed([]) = [60, 64]
        assert len(result) == 2

    def test_pattern_random_with_seed_is_deterministic(self):
        """Pattern "random" with same seed should produce same output."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
            BeatNote(0.0, 0.5, 67, 100, 0),
        ]
        result1 = arpeggiate(notes, ArpeggiatorConfig(pattern="random"), seed=42)
        result2 = arpeggiate(notes, ArpeggiatorConfig(pattern="random"), seed=42)
        assert len(result1) == len(result2)
        assert [n.note for n in result1] == [n.note for n in result2]

    def test_pattern_random_different_seeds_differ(self):
        """Pattern "random" with different seeds should differ."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 62, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
            BeatNote(0.0, 0.5, 65, 100, 0),
            BeatNote(0.0, 0.5, 67, 100, 0),
        ]
        result1 = arpeggiate(notes, ArpeggiatorConfig(pattern="random"), seed=42)
        result2 = arpeggiate(notes, ArpeggiatorConfig(pattern="random"), seed=99)
        # With 5 notes and different seeds, very unlikely to be identical
        assert [n.note for n in result1] != [n.note for n in result2]

    def test_octave_range_adds_higher_octaves(self):
        """octave_range should add higher octave repetitions."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(octave_range=1, rate=0.25))
        # Should have: 60, 64, 72 (60+12), 76 (64+12)
        assert len(result) == 4
        notes_list = [n.note for n in result]
        assert 60 in notes_list
        assert 64 in notes_list
        assert 72 in notes_list
        assert 76 in notes_list

    def test_octave_range_respects_midi_127_limit(self):
        """octave_range should not exceed MIDI note 127."""
        notes = [
            BeatNote(0.0, 0.5, 120, 100, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(octave_range=2, rate=0.25))
        # 120, 132 (exceeds 127, should be skipped), 144 (also exceeds)
        # Only 120 should remain
        assert len(result) == 1
        assert result[0].note == 120

    def test_gate_controls_note_duration(self):
        """gate parameter should control note duration relative to rate."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(rate=0.5, gate=0.5))
        # duration = rate * gate = 0.5 * 0.5 = 0.25
        for note in result:
            assert note.duration_beats == 0.25

    def test_gate_minimum_duration(self):
        """gate should enforce minimum duration of 0.0625."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(rate=0.01, gate=0.1))
        # duration = 0.01 * 0.1 = 0.001, clamped to 0.0625
        for note in result:
            assert note.duration_beats == 0.0625

    def test_rate_controls_spacing(self):
        """rate parameter should control time spacing between notes."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
            BeatNote(0.0, 0.5, 67, 100, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(rate=0.5))
        assert result[0].time_beats == 0.0
        assert result[1].time_beats == 0.5
        assert result[2].time_beats == 1.0

    def test_multiple_groups_at_different_times(self):
        """Multiple chord groups at different times should be handled independently."""
        notes = [
            # Chord at beat 0
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
            # Chord at beat 2
            BeatNote(2.0, 0.5, 67, 100, 0),
            BeatNote(2.0, 0.5, 72, 100, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(rate=0.25))
        assert len(result) == 4
        # First chord
        assert result[0].time_beats == 0.0
        assert result[0].note == 60
        assert result[1].time_beats == 0.25
        assert result[1].note == 64
        # Second chord
        assert result[2].time_beats == 2.0
        assert result[2].note == 67
        assert result[3].time_beats == 2.25
        assert result[3].note == 72

    def test_notes_on_different_tracks_handled_separately(self):
        """Notes on different tracks at same time should not be arpeggiated together."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),  # track 0
            BeatNote(0.0, 0.5, 64, 100, 1),  # track 1
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(rate=0.25))
        assert len(result) == 2
        # Both should remain at time 0.0 since they're on different tracks
        assert result[0].time_beats == 0.0
        assert result[1].time_beats == 0.0

    def test_empty_input_returns_empty(self):
        """Empty input should return empty output."""
        result = arpeggiate([])
        assert len(result) == 0

    def test_preserves_velocity(self):
        """Arpeggiated notes should preserve the original velocity."""
        notes = [
            BeatNote(0.0, 0.5, 60, 80, 0),
            BeatNote(0.0, 0.5, 64, 80, 0),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(rate=0.25))
        assert all(n.velocity == 80 for n in result)

    def test_preserves_track(self):
        """Arpeggiated notes should preserve track number."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 3),
            BeatNote(0.0, 0.5, 64, 100, 3),
        ]
        result = arpeggiate(notes, ArpeggiatorConfig(rate=0.25))
        assert all(n.track == 3 for n in result)

    def test_default_config(self):
        """Should use default config when none provided."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
        ]
        result = arpeggiate(notes)
        assert len(result) == 2
        # Default rate is 0.25
        assert result[1].time_beats == 0.25


# ── Humanize Tests ────────────────────────────────────────────


class TestHumanize:
    """Tests for the humanize effect."""

    def test_default_config_applies_jitter(self):
        """Default config should apply timing and velocity jitter."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result1 = humanize(notes, seed=1)
        result2 = humanize(notes, seed=2)
        # Different seeds should produce different results
        assert result1[0].time_beats != result2[0].time_beats or result1[0].velocity != result2[0].velocity

    def test_seed_makes_output_deterministic(self):
        """Same seed should produce identical output."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(1.0, 0.5, 64, 100, 0),
        ]
        result1 = humanize(notes, HumanizeConfig(), seed=42)
        result2 = humanize(notes, HumanizeConfig(), seed=42)
        assert len(result1) == len(result2)
        for n1, n2 in zip(result1, result2):
            assert n1.time_beats == n2.time_beats
            assert n1.velocity == n2.velocity
            assert n1.duration_beats == n2.duration_beats

    def test_timing_jitter_zero_preserves_timing(self):
        """timing_jitter=0 should not change timing."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(1.0, 0.5, 64, 100, 0),
        ]
        result = humanize(notes, HumanizeConfig(timing_jitter_beats=0.0), seed=42)
        assert result[0].time_beats == 0.0
        assert result[1].time_beats == 1.0

    def test_velocity_jitter_zero_preserves_velocity(self):
        """velocity_jitter=0 should not change velocity."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(1.0, 0.5, 64, 80, 0),
        ]
        result = humanize(notes, HumanizeConfig(velocity_jitter=0), seed=42)
        assert result[0].velocity == 100
        assert result[1].velocity == 80

    def test_time_never_goes_negative(self):
        """Timing jitter should not produce negative time values."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        # Try multiple seeds to catch edge cases
        for seed in range(100):
            result = humanize(notes, HumanizeConfig(timing_jitter_beats=1.0), seed=seed)
            assert result[0].time_beats >= 0.0

    def test_velocity_stays_within_1_127(self):
        """Velocity should be clamped to valid MIDI range 1-127."""
        notes = [
            BeatNote(0.0, 0.5, 60, 1, 0),    # minimum velocity
            BeatNote(1.0, 0.5, 64, 127, 0),  # maximum velocity
        ]
        for seed in range(100):
            result = humanize(notes, HumanizeConfig(velocity_jitter=50), seed=seed)
            for note in result:
                assert 1 <= note.velocity <= 127

    def test_duration_jitter_works(self):
        """duration_jitter should vary note durations."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result1 = humanize(notes, HumanizeConfig(duration_jitter_beats=0.1), seed=1)
        result2 = humanize(notes, HumanizeConfig(duration_jitter_beats=0.1), seed=2)
        # Different seeds should produce different durations
        assert result1[0].duration_beats != result2[0].duration_beats

    def test_duration_minimum_enforced(self):
        """Duration should not fall below 0.0625 beats."""
        notes = [BeatNote(0.0, 0.1, 60, 100, 0)]
        for seed in range(100):
            result = humanize(notes, HumanizeConfig(duration_jitter_beats=1.0), seed=seed)
            assert result[0].duration_beats >= 0.0625

    def test_large_jitter_values_still_produce_valid_output(self):
        """Large jitter values should still produce valid notes."""
        notes = [BeatNote(2.0, 0.5, 60, 64, 0)]
        result = humanize(notes, HumanizeConfig(
            timing_jitter_beats=5.0,
            velocity_jitter=100,
            duration_jitter_beats=2.0,
        ), seed=42)
        assert len(result) == 1
        assert result[0].time_beats >= 0.0
        assert 1 <= result[0].velocity <= 127
        assert result[0].duration_beats >= 0.0625

    def test_empty_input_returns_empty(self):
        """Empty input should return empty output."""
        result = humanize([])
        assert len(result) == 0

    def test_notes_remain_sorted_by_time(self):
        """Output should be sorted by time even if jitter changes order."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.1, 0.5, 64, 100, 0),
            BeatNote(0.2, 0.5, 67, 100, 0),
        ]
        result = humanize(notes, HumanizeConfig(timing_jitter_beats=0.5), seed=42)
        for i in range(len(result) - 1):
            assert result[i].time_beats <= result[i + 1].time_beats

    def test_preserves_pitch(self):
        """Humanize should not change pitch."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(1.0, 0.5, 72, 100, 0),
        ]
        result = humanize(notes, HumanizeConfig(), seed=42)
        assert result[0].note == 60
        assert result[1].note == 72

    def test_preserves_track(self):
        """Humanize should preserve track numbers."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(1.0, 0.5, 64, 100, 2),
        ]
        result = humanize(notes, HumanizeConfig(), seed=42)
        assert result[0].track == 0
        assert result[1].track == 2

    def test_multiple_notes_get_different_jitter(self):
        """Each note should receive independent random jitter."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(1.0, 0.5, 64, 100, 0),
            BeatNote(2.0, 0.5, 67, 100, 0),
        ]
        result = humanize(notes, HumanizeConfig(
            timing_jitter_beats=0.1,
            velocity_jitter=10,
        ), seed=42)
        # Extremely unlikely all three get identical jitter
        times = {n.time_beats for n in result}
        velocities = {n.velocity for n in result}
        assert len(times) > 1 or len(velocities) > 1

    def test_default_config_values(self):
        """Should use default config when none provided."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = humanize(notes, seed=42)
        # Should apply jitter with default values
        assert result[0].time_beats != 0.0 or result[0].velocity != 100

    def test_all_jitter_zero_creates_copy(self):
        """All jitter set to zero should create exact copy."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(1.0, 0.25, 64, 80, 1),
        ]
        result = humanize(notes, HumanizeConfig(
            timing_jitter_beats=0.0,
            velocity_jitter=0,
            duration_jitter_beats=0.0,
        ), seed=42)
        assert result[0].time_beats == 0.0
        assert result[0].duration_beats == 0.5
        assert result[0].velocity == 100
        assert result[1].time_beats == 1.0
        assert result[1].duration_beats == 0.25
        assert result[1].velocity == 80

    def test_timing_jitter_range(self):
        """Timing jitter should be within specified range."""
        notes = [BeatNote(5.0, 0.5, 60, 100, 0)]
        jitter = 0.1
        results = []
        for seed in range(50):
            result = humanize(notes, HumanizeConfig(timing_jitter_beats=jitter), seed=seed)
            results.append(result[0].time_beats)
        # All results should be within [5.0 - jitter, 5.0 + jitter]
        assert all(5.0 - jitter <= t <= 5.0 + jitter for t in results)

    def test_velocity_jitter_range(self):
        """Velocity jitter should be within specified range."""
        notes = [BeatNote(0.0, 0.5, 60, 64, 0)]
        jitter = 10
        results = []
        for seed in range(50):
            result = humanize(notes, HumanizeConfig(velocity_jitter=jitter), seed=seed)
            results.append(result[0].velocity)
        # All results should be within [64 - jitter, 64 + jitter], clamped to [1, 127]
        assert all(max(1, 64 - jitter) <= v <= min(127, 64 + jitter) for v in results)


# ── Quantize Tests ────────────────────────────────────────────


class TestQuantize:
    """Tests for the quantize effect."""

    def test_already_on_grid_notes_unchanged(self):
        """Notes already on grid should remain unchanged."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(0.5, 0.5, 64, 100, 0),
            BeatNote(1.0, 0.5, 67, 100, 0),
        ]
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=1.0))
        assert result[0].time_beats == 0.0
        assert result[1].time_beats == 0.5
        assert result[2].time_beats == 1.0

    def test_off_grid_notes_snapped(self):
        """Notes off grid should be snapped to nearest grid point."""
        notes = [
            BeatNote(0.1, 0.5, 60, 100, 0),   # snap to 0.0
            BeatNote(0.6, 0.5, 64, 100, 0),   # snap to 0.5
            BeatNote(1.3, 0.5, 67, 100, 0),   # snap to 1.5
        ]
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=1.0))
        assert result[0].time_beats == 0.0
        assert result[1].time_beats == 0.5
        assert result[2].time_beats == 1.5

    def test_strength_zero_no_change(self):
        """strength=0.0 should not change timing."""
        notes = [
            BeatNote(0.1, 0.5, 60, 100, 0),
            BeatNote(0.7, 0.5, 64, 100, 0),
        ]
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=0.0))
        assert result[0].time_beats == 0.1
        assert result[1].time_beats == 0.7

    def test_strength_half_moves_halfway(self):
        """strength=0.5 should move halfway toward grid."""
        notes = [BeatNote(0.1, 0.5, 60, 100, 0)]  # grid point is 0.0, distance -0.1
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=0.5))
        # new_time = 0.1 + (-0.1) * 0.5 = 0.05
        assert result[0].time_beats == pytest.approx(0.05)

    def test_strength_full_snap(self):
        """strength=1.0 should fully snap to grid."""
        notes = [BeatNote(0.33, 0.5, 60, 100, 0)]
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=1.0))
        # 0.33 snaps to 0.5
        assert result[0].time_beats == pytest.approx(0.5)

    def test_grid_quarter_note(self):
        """grid=0.25 should snap to quarter note grid."""
        notes = [
            BeatNote(0.1, 0.5, 60, 100, 0),   # snap to 0.0
            BeatNote(0.3, 0.5, 64, 100, 0),   # snap to 0.25
            BeatNote(0.6, 0.5, 67, 100, 0),   # snap to 0.5
        ]
        result = quantize(notes, QuantizeConfig(grid=0.25, strength=1.0))
        assert result[0].time_beats == 0.0
        assert result[1].time_beats == 0.25
        assert result[2].time_beats == 0.5

    def test_grid_half_note(self):
        """grid=0.5 should snap to eighth note grid."""
        notes = [BeatNote(0.7, 0.5, 60, 100, 0)]
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=1.0))
        # 0.7 is closer to 0.5 than 1.0
        assert result[0].time_beats == pytest.approx(0.5)

    def test_grid_whole_note(self):
        """grid=1.0 should snap to whole note grid."""
        notes = [
            BeatNote(0.3, 0.5, 60, 100, 0),   # snap to 0.0
            BeatNote(0.8, 0.5, 64, 100, 0),   # snap to 1.0
            BeatNote(1.6, 0.5, 67, 100, 0),   # snap to 2.0
        ]
        result = quantize(notes, QuantizeConfig(grid=1.0, strength=1.0))
        assert result[0].time_beats == 0.0
        assert result[1].time_beats == 1.0
        assert result[2].time_beats == 2.0

    def test_grid_zero_returns_copy(self):
        """grid=0 should return copy without changes."""
        notes = [
            BeatNote(0.123, 0.5, 60, 100, 0),
            BeatNote(0.789, 0.5, 64, 100, 0),
        ]
        result = quantize(notes, QuantizeConfig(grid=0.0, strength=1.0))
        assert result[0].time_beats == 0.123
        assert result[1].time_beats == 0.789

    def test_notes_remain_sorted(self):
        """Output should remain sorted by time."""
        notes = [
            BeatNote(1.1, 0.5, 60, 100, 0),
            BeatNote(0.1, 0.5, 64, 100, 0),
            BeatNote(2.1, 0.5, 67, 100, 0),
        ]
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=1.0))
        for i in range(len(result) - 1):
            assert result[i].time_beats <= result[i + 1].time_beats

    def test_empty_input_returns_empty(self):
        """Empty input should return empty output."""
        result = quantize([])
        assert len(result) == 0

    def test_negative_time_prevention(self):
        """Quantization should not produce negative times."""
        notes = [BeatNote(0.1, 0.5, 60, 100, 0)]
        # Grid at 0.5, would snap 0.1 to 0.0 (safe), but test edge cases
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=1.0))
        assert result[0].time_beats >= 0.0

    def test_preserves_duration(self):
        """Quantize should not change duration."""
        notes = [
            BeatNote(0.1, 0.3, 60, 100, 0),
            BeatNote(0.6, 0.7, 64, 100, 0),
        ]
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=1.0))
        assert result[0].duration_beats == 0.3
        assert result[1].duration_beats == 0.7

    def test_preserves_pitch(self):
        """Quantize should not change pitch."""
        notes = [
            BeatNote(0.1, 0.5, 60, 100, 0),
            BeatNote(0.6, 0.5, 72, 100, 0),
        ]
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=1.0))
        assert result[0].note == 60
        assert result[1].note == 72

    def test_preserves_velocity(self):
        """Quantize should not change velocity."""
        notes = [
            BeatNote(0.1, 0.5, 60, 80, 0),
            BeatNote(0.6, 0.5, 64, 100, 0),
        ]
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=1.0))
        assert result[0].velocity == 80
        assert result[1].velocity == 100

    def test_preserves_track(self):
        """Quantize should preserve track numbers."""
        notes = [
            BeatNote(0.1, 0.5, 60, 100, 0),
            BeatNote(0.6, 0.5, 64, 100, 2),
        ]
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=1.0))
        assert result[0].track == 0
        assert result[1].track == 2

    def test_default_config(self):
        """Should use default config when none provided."""
        notes = [BeatNote(0.1, 0.5, 60, 100, 0)]
        result = quantize(notes)
        # Default grid is 0.5, strength is 1.0
        assert result[0].time_beats == 0.0

    def test_rounding_midpoint(self):
        """Midpoint between grid points should round to nearest even."""
        notes = [BeatNote(0.25, 0.5, 60, 100, 0)]  # exactly between 0.0 and 0.5
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=1.0))
        # Python's round() uses banker's rounding, 0.25/0.5 = 0.5, round(0.5) = 0
        assert result[0].time_beats == 0.0

    def test_negative_grid_returns_copy(self):
        """Negative grid should be treated as invalid and return copy."""
        notes = [BeatNote(0.123, 0.5, 60, 100, 0)]
        result = quantize(notes, QuantizeConfig(grid=-0.5, strength=1.0))
        assert result[0].time_beats == 0.123

    def test_negative_strength_returns_copy(self):
        """Negative strength should be treated as invalid and return copy."""
        notes = [BeatNote(0.123, 0.5, 60, 100, 0)]
        result = quantize(notes, QuantizeConfig(grid=0.5, strength=-0.5))
        assert result[0].time_beats == 0.123


# ── Chord Generator Tests ─────────────────────────────────────


class TestChordGenerator:
    """Tests for the chord generator effect."""

    def test_major_chord_adds_4_and_7_semitones(self):
        """Major chord should add notes at +4 and +7 semitones."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]  # C4
        result = generate_chords(notes, ChordGenConfig(chord_type="major"))
        assert len(result) == 3
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 64, 67]  # C, E, G

    def test_minor_chord_adds_3_and_7(self):
        """Minor chord should add notes at +3 and +7 semitones."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="minor"))
        assert len(result) == 3
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 63, 67]  # C, Eb, G

    def test_7th_chord_adds_4_7_10(self):
        """7th chord should add notes at +4, +7, +10 semitones."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="7th"))
        assert len(result) == 4
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 64, 67, 70]  # C, E, G, Bb

    def test_maj7_chord(self):
        """maj7 chord should have major 7th interval."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="maj7"))
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 64, 67, 71]  # C, E, G, B

    def test_min7_chord(self):
        """min7 chord should have minor 3rd and minor 7th."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="min7"))
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 63, 67, 70]  # C, Eb, G, Bb

    def test_dim_chord_adds_3_and_6(self):
        """Diminished chord should add notes at +3 and +6 semitones."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="dim"))
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 63, 66]  # C, Eb, Gb

    def test_aug_chord_adds_4_and_8(self):
        """Augmented chord should add notes at +4 and +8 semitones."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="aug"))
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 64, 68]  # C, E, G#

    def test_sus2_chord(self):
        """sus2 chord should add notes at +2 and +7 semitones."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="sus2"))
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 62, 67]  # C, D, G

    def test_sus4_chord(self):
        """sus4 chord should add notes at +5 and +7 semitones."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="sus4"))
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 65, 67]  # C, F, G

    def test_power_chord(self):
        """Power chord should only add +7 (perfect fifth)."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="power"))
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 67]  # C, G

    def test_voicing_close_default(self):
        """voicing="close" should keep all notes in close position."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="major", voicing="close"))
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 64, 67]

    def test_voicing_spread_shifts_even_intervals_up_octave(self):
        """voicing="spread" should shift even-indexed intervals up an octave."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="major", voicing="spread"))
        # intervals = (0, 4, 7), indices 0, 1, 2
        # idx 0: interval 0 (root) → not added (skipped)
        # idx 1: interval 4 → 64, idx=1 (odd) → no shift → 64
        # idx 2: interval 7 → 67, idx=2 (even) → +12 → 79
        pitches = sorted([n.note for n in result])
        assert 60 in pitches  # root
        assert 64 in pitches  # 3rd (odd index, no shift)
        assert 79 in pitches  # 5th + 12 (even index)

    def test_voicing_drop2_drops_2nd_voice_down_octave(self):
        """voicing="drop2" should drop the 2nd voice down an octave."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="major", voicing="drop2"))
        # intervals = (0, 4, 7), indices 0, 1, 2
        # idx 0: root (skipped from adding)
        # idx 1: interval 4 → 64 - 12 = 52 (drop2)
        # idx 2: interval 7 → 67 (no change)
        pitches = sorted([n.note for n in result])
        assert 60 in pitches  # root
        assert 52 in pitches  # 3rd - 12
        assert 67 in pitches  # 5th

    def test_velocity_scale_affects_added_tones(self):
        """velocity_scale should reduce velocity of added tones."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="major", velocity_scale=0.5))
        # Root should have original velocity
        root = [n for n in result if n.note == 60][0]
        assert root.velocity == 100
        # Added tones should have scaled velocity
        added = [n for n in result if n.note != 60]
        for note in added:
            assert note.velocity == 50  # 100 * 0.5

    def test_midi_clamping_upper_bound(self):
        """Generated notes should not exceed MIDI 127."""
        notes = [BeatNote(0.0, 0.5, 120, 100, 0)]  # High note
        result = generate_chords(notes, ChordGenConfig(chord_type="major"))
        for note in result:
            assert note.note <= 127

    def test_midi_clamping_lower_bound_with_drop2(self):
        """Generated notes should not go below MIDI 0."""
        notes = [BeatNote(0.0, 0.5, 5, 100, 0)]  # Very low note
        result = generate_chords(notes, ChordGenConfig(chord_type="major", voicing="drop2"))
        # drop2 would make 5 + 4 - 12 = -3, should clamp to 0
        for note in result:
            assert note.note >= 0

    def test_empty_input_returns_empty(self):
        """Empty input should return empty output."""
        result = generate_chords([])
        assert len(result) == 0

    def test_multiple_notes_each_get_chord(self):
        """Each input note should generate its own chord."""
        notes = [
            BeatNote(0.0, 0.5, 60, 100, 0),
            BeatNote(1.0, 0.5, 64, 100, 0),
        ]
        result = generate_chords(notes, ChordGenConfig(chord_type="major"))
        # Each note generates 3-note chord = 6 total
        assert len(result) == 6

    def test_preserves_duration(self):
        """Generated chord tones should have same duration as root."""
        notes = [BeatNote(0.0, 0.75, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="major"))
        for note in result:
            assert note.duration_beats == 0.75

    def test_preserves_time(self):
        """All chord tones should have same time as root."""
        notes = [BeatNote(2.5, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="major"))
        for note in result:
            assert note.time_beats == 2.5

    def test_preserves_track(self):
        """Generated chord tones should preserve track number."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 3)]
        result = generate_chords(notes, ChordGenConfig(chord_type="major"))
        for note in result:
            assert note.track == 3

    def test_unknown_chord_type_defaults_to_major(self):
        """Unknown chord type should fall back to major chord."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="unknown"))
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 64, 67]  # major chord

    def test_default_config(self):
        """Should use default config when none provided."""
        notes = [BeatNote(0.0, 0.5, 60, 100, 0)]
        result = generate_chords(notes)
        # Default is major chord
        pitches = sorted([n.note for n in result])
        assert pitches == [60, 64, 67]

    def test_output_sorted_by_time_then_pitch(self):
        """Output should be sorted by time, then by pitch."""
        notes = [
            BeatNote(1.0, 0.5, 60, 100, 0),
            BeatNote(0.0, 0.5, 64, 100, 0),
        ]
        result = generate_chords(notes, ChordGenConfig(chord_type="major"))
        # First chord should be at time 0.0
        first_chord = [n for n in result if n.time_beats == 0.0]
        assert len(first_chord) == 3
        # Second chord at time 1.0
        second_chord = [n for n in result if n.time_beats == 1.0]
        assert len(second_chord) == 3
        # Within each time, notes should be sorted by pitch
        first_pitches = [n.note for n in first_chord]
        assert first_pitches == sorted(first_pitches)

    def test_velocity_scale_minimum_velocity(self):
        """velocity_scale should not produce velocity below 1."""
        notes = [BeatNote(0.0, 0.5, 60, 10, 0)]
        result = generate_chords(notes, ChordGenConfig(chord_type="major", velocity_scale=0.01))
        # 10 * 0.01 = 0.1, int() = 0, max(1, 0) = 1
        for note in result:
            assert note.velocity >= 1

    def test_chord_intervals_constant_exists(self):
        """CHORD_INTERVALS constant should contain all expected chord types."""
        expected_types = {"major", "minor", "7th", "maj7", "min7", "dim", "aug", "sus2", "sus4", "power"}
        assert expected_types.issubset(set(CHORD_INTERVALS.keys()))
