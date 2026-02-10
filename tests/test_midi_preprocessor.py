"""Tests for MIDI preprocessor pipeline."""

from cyber_qin.core.midi_file_player import MidiFileEvent
from cyber_qin.core.midi_preprocessor import (
    PreprocessStats,
    apply_global_transpose,
    compute_optimal_transpose,
    deduplicate_notes,
    normalize_octave,
    normalize_velocity,
    preprocess,
    quantize_timing,
)


def _evt(t: float, typ: str, note: int, vel: int = 80) -> MidiFileEvent:
    """Shorthand event constructor."""
    return MidiFileEvent(time_seconds=t, event_type=typ, note=note, velocity=vel)


# ── normalize_octave ──────────────────────────────────────


class TestNormalizeOctave:
    def test_in_range_unchanged(self):
        events = [_evt(0, "note_on", 60), _evt(0.5, "note_off", 60)]
        result = normalize_octave(events)
        assert [e.note for e in result] == [60, 60]

    def test_high_note_shifted_down(self):
        events = [_evt(0, "note_on", 84)]  # C6 → C5 (72)
        result = normalize_octave(events)
        assert result[0].note == 72

    def test_very_high_note_shifted_down_multiple_octaves(self):
        events = [_evt(0, "note_on", 96)]  # C7 → C5 (72)
        result = normalize_octave(events)
        assert result[0].note == 72

    def test_low_note_shifted_up(self):
        events = [_evt(0, "note_on", 36)]  # C2 → C3 (48)
        result = normalize_octave(events)
        assert result[0].note == 48

    def test_very_low_note_shifted_up_multiple_octaves(self):
        events = [_evt(0, "note_on", 24)]  # C1 → C3 (48)
        result = normalize_octave(events)
        assert result[0].note == 48

    def test_boundary_min(self):
        events = [_evt(0, "note_on", 48)]  # C3 — exactly at min
        result = normalize_octave(events)
        assert result[0].note == 48

    def test_boundary_max(self):
        events = [_evt(0, "note_on", 83)]  # B5 — exactly at max
        result = normalize_octave(events)
        assert result[0].note == 83

    def test_note_off_also_shifted(self):
        events = [_evt(0, "note_on", 96), _evt(0.5, "note_off", 96)]
        result = normalize_octave(events)
        assert result[0].note == result[1].note == 72

    def test_preserves_time(self):
        events = [_evt(1.5, "note_on", 90)]
        result = normalize_octave(events)
        assert result[0].time_seconds == 1.5

    def test_empty_list(self):
        assert normalize_octave([]) == []

    def test_note_47_shifted_up(self):
        # B2 (47) → B3 (59)
        events = [_evt(0, "note_on", 47)]
        result = normalize_octave(events)
        assert result[0].note == 59

    def test_note_84_shifted_down(self):
        # C6 (84) → C5 (72)
        events = [_evt(0, "note_on", 84)]
        result = normalize_octave(events)
        assert result[0].note == 72


# ── compute_optimal_transpose ────────────────────────────


class TestComputeOptimalTranspose:
    def test_all_in_range_no_shift(self):
        events = [_evt(0, "note_on", 60), _evt(0.1, "note_on", 72)]
        assert compute_optimal_transpose(events) == 0

    def test_high_notes_shift_down(self):
        # Notes 84-95 → shift by -12 puts them at 72-83 (in range)
        events = [_evt(i * 0.1, "note_on", 84 + i) for i in range(12)]
        shift = compute_optimal_transpose(events)
        assert shift == -12

    def test_low_notes_shift_up(self):
        # Notes 36-47 → shift by +12 puts them at 48-59 (in range)
        events = [_evt(i * 0.1, "note_on", 36 + i) for i in range(12)]
        shift = compute_optimal_transpose(events)
        assert shift == 12

    def test_very_high_notes_shift_multiple_octaves(self):
        # Notes 96-107 → shift by -24 puts them at 72-83
        events = [_evt(i * 0.1, "note_on", 96 + i) for i in range(12)]
        shift = compute_optimal_transpose(events)
        assert shift == -24

    def test_empty_events(self):
        assert compute_optimal_transpose([]) == 0

    def test_no_note_on(self):
        events = [_evt(0, "note_off", 60)]
        assert compute_optimal_transpose(events) == 0

    def test_mixed_favors_majority(self):
        # 8 notes at 84-91 (out of range), 2 notes at 60-61 (in range)
        # Shift -12: 8 become 72-79 (in) + 2 become 48-49 (in) = 10 in range
        # No shift: 2 in range
        events = [_evt(i * 0.1, "note_on", 84 + i) for i in range(8)]
        events += [_evt(1.0, "note_on", 60), _evt(1.1, "note_on", 61)]
        shift = compute_optimal_transpose(events)
        assert shift == -12

    def test_already_optimal_no_shift(self):
        # Most notes in range, a few outside — shift wouldn't help
        events = [_evt(i * 0.1, "note_on", 48 + i) for i in range(36)]
        assert compute_optimal_transpose(events) == 0


# ── apply_global_transpose ───────────────────────────────


class TestApplyGlobalTranspose:
    def test_zero_shift_no_change(self):
        events = [_evt(0, "note_on", 60)]
        result = apply_global_transpose(events, semitones=0)
        assert result[0].note == 60

    def test_shift_down(self):
        events = [_evt(0, "note_on", 72), _evt(0.5, "note_off", 72)]
        result = apply_global_transpose(events, semitones=-12)
        assert result[0].note == 60
        assert result[1].note == 60

    def test_shift_up(self):
        events = [_evt(0, "note_on", 48)]
        result = apply_global_transpose(events, semitones=12)
        assert result[0].note == 60

    def test_preserves_time_and_velocity(self):
        events = [_evt(1.5, "note_on", 60, vel=100)]
        result = apply_global_transpose(events, semitones=12)
        assert result[0].time_seconds == 1.5
        assert result[0].velocity == 100


# ── deduplicate_notes ────────────────────────────────────


class TestDeduplicateNotes:
    def test_no_duplicates(self):
        events = [_evt(0, "note_on", 60), _evt(0.5, "note_off", 60)]
        result, removed = deduplicate_notes(events)
        assert len(result) == 2
        assert removed == 0

    def test_same_time_same_note_deduped(self):
        events = [
            _evt(0, "note_on", 60),
            _evt(0, "note_on", 60),  # duplicate
        ]
        result, removed = deduplicate_notes(events)
        assert len(result) == 1
        assert removed == 1

    def test_same_time_different_notes_kept(self):
        events = [_evt(0, "note_on", 60), _evt(0, "note_on", 72)]
        result, removed = deduplicate_notes(events)
        assert len(result) == 2
        assert removed == 0

    def test_different_time_same_note_kept(self):
        events = [_evt(0, "note_on", 60), _evt(0.5, "note_on", 60)]
        result, removed = deduplicate_notes(events)
        assert len(result) == 2
        assert removed == 0

    def test_note_off_also_deduped(self):
        events = [
            _evt(1.0, "note_off", 60),
            _evt(1.0, "note_off", 60),
        ]
        result, removed = deduplicate_notes(events)
        assert len(result) == 1
        assert removed == 1

    def test_empty(self):
        result, removed = deduplicate_notes([])
        assert result == []
        assert removed == 0

    def test_realistic_collision_scenario(self):
        """Two notes an octave apart collapse after folding → dedup."""
        # Simulate post-fold: both became note 72 at time 0
        events = [
            _evt(0, "note_on", 72),   # was originally 72
            _evt(0, "note_on", 72),   # was originally 84, folded to 72
            _evt(0.5, "note_off", 72),
            _evt(0.5, "note_off", 72),
        ]
        result, removed = deduplicate_notes(events)
        assert len(result) == 2  # one note_on + one note_off
        assert removed == 2


# ── normalize_velocity ────────────────────────────────────


class TestNormalizeVelocity:
    def test_note_on_velocity_set_to_127(self):
        events = [_evt(0, "note_on", 60, vel=64)]
        result = normalize_velocity(events)
        assert result[0].velocity == 127

    def test_already_127_unchanged(self):
        events = [_evt(0, "note_on", 60, vel=127)]
        result = normalize_velocity(events)
        assert result[0].velocity == 127

    def test_note_off_velocity_unchanged(self):
        events = [_evt(0, "note_off", 60, vel=0)]
        result = normalize_velocity(events)
        assert result[0].velocity == 0

    def test_mixed(self):
        events = [
            _evt(0, "note_on", 60, vel=50),
            _evt(0.5, "note_off", 60, vel=0),
            _evt(1.0, "note_on", 64, vel=90),
        ]
        result = normalize_velocity(events)
        assert result[0].velocity == 127
        assert result[1].velocity == 0
        assert result[2].velocity == 127

    def test_empty_list(self):
        assert normalize_velocity([]) == []

    def test_custom_target(self):
        events = [_evt(0, "note_on", 60, vel=50)]
        result = normalize_velocity(events, target=100)
        assert result[0].velocity == 100


# ── quantize_timing ───────────────────────────────────────


class TestQuantizeTiming:
    def test_already_on_grid(self):
        grid = 1.0 / 60
        events = [_evt(grid * 3, "note_on", 60)]
        result = quantize_timing(events)
        assert abs(result[0].time_seconds - grid * 3) < 1e-9

    def test_micro_delay_snapped(self):
        grid = 1.0 / 60  # ~0.01667
        events = [_evt(grid * 3 + 0.002, "note_on", 60)]  # 2ms off grid
        result = quantize_timing(events)
        assert abs(result[0].time_seconds - grid * 3) < 1e-6

    def test_time_zero_stays_zero(self):
        events = [_evt(0.0, "note_on", 60)]
        result = quantize_timing(events)
        assert result[0].time_seconds == 0.0

    def test_preserves_note(self):
        events = [_evt(0.003, "note_on", 72, vel=100)]
        result = quantize_timing(events)
        assert result[0].note == 72
        assert result[0].velocity == 100

    def test_custom_grid(self):
        events = [_evt(0.030, "note_on", 60)]
        result = quantize_timing(events, grid_sec=0.050)
        assert abs(result[0].time_seconds - 0.050) < 1e-9

    def test_empty_list(self):
        assert quantize_timing([]) == []

    def test_close_events_collapsed(self):
        """Two events 3ms apart should snap to the same frame."""
        grid = 1.0 / 60
        t0 = grid * 10
        events = [_evt(t0, "note_on", 60), _evt(t0 + 0.003, "note_on", 64)]
        result = quantize_timing(events)
        assert abs(result[0].time_seconds - result[1].time_seconds) < 1e-9


# ── preprocess (full pipeline) ────────────────────────────


class TestPreprocess:
    def test_returns_tuple(self):
        events = [_evt(0, "note_on", 60), _evt(0.5, "note_off", 60)]
        result, stats = preprocess(events)
        assert isinstance(result, list)
        assert isinstance(stats, PreprocessStats)

    def test_empty(self):
        result, stats = preprocess([])
        assert result == []
        assert stats.total_notes == 0

    def test_all_transforms_applied(self):
        events = [
            _evt(0.001, "note_on", 96, vel=50),   # high note, low velocity, off-grid
            _evt(0.501, "note_off", 96, vel=0),
        ]
        result, stats = preprocess(events)

        # After smart transpose (-12) + fold: 96 → 84 → 72
        # Or direct fold: 96 → 72
        assert 48 <= result[0].note <= 83
        # Velocity: 50 → 127
        assert result[0].velocity == 127
        # Timing: snapped to grid
        grid = 1.0 / 60
        assert abs(result[0].time_seconds - round(0.001 / grid) * grid) < 1e-6

    def test_sorted_after_quantize(self):
        grid = 1.0 / 60
        # Two events that swap order after quantization
        events = [
            _evt(grid * 5 + 0.008, "note_on", 60),
            _evt(grid * 5 - 0.001, "note_off", 64),
        ]
        result, _ = preprocess(events)
        times = [e.time_seconds for e in result]
        assert times == sorted(times)

    def test_note_off_before_note_on_at_same_time(self):
        """At the same time, note_off should precede note_on."""
        events = [
            _evt(0, "note_on", 60),
            _evt(0, "note_off", 64),
        ]
        result, _ = preprocess(events)
        assert result[0].event_type == "note_off"
        assert result[1].event_type == "note_on"

    def test_stats_no_shift_needed(self):
        events = [
            _evt(0, "note_on", 60),
            _evt(0.5, "note_off", 60),
        ]
        _, stats = preprocess(events)
        assert stats.notes_shifted == 0
        assert stats.total_notes == 1
        assert stats.original_range == (60, 60)
        assert stats.global_transpose == 0

    def test_multiple_shifts(self):
        events = [
            _evt(0, "note_on", 30),     # very low
            _evt(0.1, "note_on", 60),    # in range
            _evt(0.2, "note_on", 100),   # very high
        ]
        _, stats = preprocess(events)
        assert stats.total_notes == 3
        assert stats.original_range == (30, 100)

    def test_stats_has_new_fields(self):
        events = [_evt(0, "note_on", 60)]
        _, stats = preprocess(events)
        assert hasattr(stats, "global_transpose")
        assert hasattr(stats, "duplicates_removed")


class TestPreprocessCustomRange:
    """Test preprocess with custom note_min/note_max parameters."""

    def test_custom_range_shifts_notes(self):
        # Range 36-83 (generic_48 scheme)
        events = [_evt(0, "note_on", 30)]  # below 36
        result, stats = preprocess(events, note_min=36, note_max=83)
        # 30 → shifted into range
        assert result[0].note >= 36
        assert stats.original_range == (30, 30)

    def test_custom_range_wider(self):
        # Range 21-108 (generic_88 scheme) — everything in range
        events = [
            _evt(0, "note_on", 21),
            _evt(0.1, "note_on", 60),
            _evt(0.2, "note_on", 108),
        ]
        _, stats = preprocess(events, note_min=21, note_max=108)
        assert stats.notes_shifted == 0

    def test_custom_range_narrow(self):
        # Range 60-71 — only one octave
        events = [
            _evt(0, "note_on", 48),   # below range
            _evt(0.1, "note_on", 60),  # in range
            _evt(0.2, "note_on", 72),  # above range
        ]
        result, stats = preprocess(events, note_min=60, note_max=71)
        for e in result:
            if e.event_type == "note_on":
                assert 60 <= e.note <= 71

    def test_default_range_unchanged(self):
        """Calling preprocess with defaults should fold notes into 48-83."""
        events = [_evt(0, "note_on", 96)]
        result, _ = preprocess(events)
        assert 48 <= result[0].note <= 83


class TestPreprocessSmartTranspose:
    """Test the smart global transpose in the full pipeline."""

    def test_high_cluster_shifted_down(self):
        """A song with most notes at 84-95 should auto-transpose down."""
        events = []
        for i in range(20):
            n = 84 + (i % 12)
            events.append(_evt(i * 0.1, "note_on", n))
            events.append(_evt(i * 0.1 + 0.05, "note_off", n))
        _, stats = preprocess(events)
        assert stats.global_transpose < 0  # shifted down

    def test_low_cluster_shifted_up(self):
        """A song with most notes at 36-47 should auto-transpose up."""
        events = []
        for i in range(20):
            n = 36 + (i % 12)
            events.append(_evt(i * 0.1, "note_on", n))
            events.append(_evt(i * 0.1 + 0.05, "note_off", n))
        _, stats = preprocess(events)
        assert stats.global_transpose > 0  # shifted up

    def test_centered_no_transpose(self):
        """Notes already centered in range should not be transposed."""
        events = [
            _evt(i * 0.1, "note_on", 60 + (i % 12))
            for i in range(20)
        ]
        _, stats = preprocess(events)
        assert stats.global_transpose == 0

    def test_collision_dedup_after_fold(self):
        """Notes that collide after fold should be deduplicated."""
        # Three notes spanning 3 octaves at the same time — two must collide after fold
        # 48 (in range), 60 (in range), 96 (folds to 72)
        # Plus a note at 72 — will collide with 96 after fold
        events = [
            _evt(0, "note_on", 72),
            _evt(0, "note_on", 96),    # folds to 72 → collision
            _evt(0.5, "note_off", 72),
            _evt(0.5, "note_off", 96),
            # Add enough in-range notes so transpose stays at 0
            *[_evt(i * 0.1 + 1.0, "note_on", 48 + (i % 36)) for i in range(30)],
            *[_evt(i * 0.1 + 1.05, "note_off", 48 + (i % 36)) for i in range(30)],
        ]
        result, stats = preprocess(events)
        # The 96→72 collision should be deduplicated
        t0_note_ons = [e for e in result if e.event_type == "note_on" and e.time_seconds < 0.01]
        # At most one note_on for pitch 72 at time 0
        pitch_72_ons = [e for e in t0_note_ons if e.note == 72]
        assert len(pitch_72_ons) == 1
        assert stats.duplicates_removed > 0

    def test_wide_range_song_all_notes_playable(self):
        """A song spanning 5 octaves should have all notes in range after processing."""
        events = []
        # C2 (36) to C7 (96) — 5 octaves
        for i, note in enumerate(range(36, 97, 2)):
            events.append(_evt(i * 0.2, "note_on", note))
            events.append(_evt(i * 0.2 + 0.1, "note_off", note))
        result, _ = preprocess(events)
        for e in result:
            if e.event_type == "note_on":
                assert 48 <= e.note <= 83, f"Note {e.note} out of range"
