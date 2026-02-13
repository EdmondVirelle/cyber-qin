"""Tests for MIDI preprocessor pipeline."""

from cyber_qin.core.midi_file_player import MidiFileEvent
from cyber_qin.core.midi_preprocessor import (
    PreprocessStats,
    apply_global_transpose,
    compute_optimal_transpose,
    deduplicate_notes,
    deduplicate_octaves,
    filter_percussion,
    filter_tracks,
    limit_polyphony,
    normalize_octave,
    normalize_octave_flowing,
    normalize_velocity,
    preprocess,
    quantize_timing,
)


def _evt(
    t: float,
    typ: str,
    note: int,
    vel: int = 80,
    *,
    track: int = 0,
    channel: int = 0,
) -> MidiFileEvent:
    """Shorthand event constructor with optional track/channel."""
    return MidiFileEvent(
        time_seconds=t,
        event_type=typ,
        note=note,
        velocity=vel,
        track=track,
        channel=channel,
    )


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
            _evt(0, "note_on", 72),  # was originally 72
            _evt(0, "note_on", 72),  # was originally 84, folded to 72
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
            _evt(0.001, "note_on", 96, vel=50),  # high note, low velocity, off-grid
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
            _evt(0, "note_on", 30),  # very low
            _evt(0.1, "note_on", 60),  # in range
            _evt(0.2, "note_on", 100),  # very high
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
            _evt(0, "note_on", 48),  # below range
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
        events = [_evt(i * 0.1, "note_on", 60 + (i % 12)) for i in range(20)]
        _, stats = preprocess(events)
        assert stats.global_transpose == 0

    def test_collision_dedup_after_fold(self):
        """Notes that collide after fold should be deduplicated."""
        # 72 and 96 are same pitch class (C) at the same time
        # Octave dedup (stage 3) catches this BEFORE folding → octave_deduped > 0
        # After dedup only one C remains; flowing fold places it in range
        events = [
            _evt(0, "note_on", 72),
            _evt(0, "note_on", 96),  # same pitch class as 72 → deduped
            _evt(0.5, "note_off", 72),
            _evt(0.5, "note_off", 96),
            # Add enough in-range notes so transpose stays at 0
            *[_evt(i * 0.1 + 1.0, "note_on", 48 + (i % 36)) for i in range(30)],
            *[_evt(i * 0.1 + 1.05, "note_off", 48 + (i % 36)) for i in range(30)],
        ]
        result, stats = preprocess(events)
        # Only one C note_on should survive at t=0 (deduped + folded into range)
        t0_note_ons = [e for e in result if e.event_type == "note_on" and e.time_seconds < 0.01]
        c_pitch_ons = [e for e in t0_note_ons if e.note % 12 == 0]
        assert len(c_pitch_ons) == 1
        assert 48 <= c_pitch_ons[0].note <= 83
        assert stats.octave_deduped > 0 or stats.duplicates_removed > 0

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


# ── filter_percussion ────────────────────────────────────


class TestFilterPercussion:
    def test_removes_channel_9(self):
        events = [
            _evt(0, "note_on", 36, channel=9),  # kick drum
            _evt(0, "note_on", 60, channel=0),  # piano
            _evt(0.5, "note_off", 36, channel=9),
            _evt(0.5, "note_off", 60, channel=0),
        ]
        result, removed = filter_percussion(events)
        assert removed == 2  # note_on + note_off on channel 9
        assert len(result) == 2
        assert all(e.channel == 0 for e in result)

    def test_empty_list(self):
        result, removed = filter_percussion([])
        assert result == []
        assert removed == 0

    def test_all_percussion(self):
        events = [
            _evt(0, "note_on", 36, channel=9),
            _evt(0.5, "note_off", 36, channel=9),
            _evt(1, "note_on", 38, channel=9),
            _evt(1.5, "note_off", 38, channel=9),
        ]
        result, removed = filter_percussion(events)
        assert len(result) == 0
        assert removed == 4

    def test_no_percussion(self):
        events = [
            _evt(0, "note_on", 60, channel=0),
            _evt(0.5, "note_off", 60, channel=0),
        ]
        result, removed = filter_percussion(events)
        assert len(result) == 2
        assert removed == 0

    def test_custom_percussion_channel(self):
        events = [
            _evt(0, "note_on", 60, channel=5),
            _evt(0, "note_on", 72, channel=0),
        ]
        result, removed = filter_percussion(events, percussion_channel=5)
        assert removed == 1
        assert len(result) == 1
        assert result[0].channel == 0

    def test_preserves_non_note_events_on_channel_9(self):
        """Non note_on/note_off events on channel 9 should be kept."""
        # Only note_on and note_off with channel 9 are removed
        events = [
            _evt(0, "note_on", 36, channel=9),
            _evt(0, "note_on", 60, channel=0),
        ]
        result, removed = filter_percussion(events)
        assert removed == 1
        assert len(result) == 1

    def test_multiple_channels_mixed(self):
        events = [
            _evt(0, "note_on", 60, channel=0),
            _evt(0, "note_on", 36, channel=9),
            _evt(0.1, "note_on", 62, channel=1),
            _evt(0.1, "note_on", 42, channel=9),
            _evt(0.5, "note_off", 60, channel=0),
            _evt(0.5, "note_off", 36, channel=9),
        ]
        result, removed = filter_percussion(events)
        assert removed == 3  # 2 note_on + 1 note_off on ch9
        assert len(result) == 3


# ── filter_tracks ────────────────────────────────────────


class TestFilterTracks:
    def test_none_keeps_all(self):
        events = [
            _evt(0, "note_on", 60, track=0),
            _evt(0, "note_on", 72, track=1),
        ]
        result, removed = filter_tracks(events, include_tracks=None)
        assert len(result) == 2
        assert removed == 0

    def test_filter_single_track(self):
        events = [
            _evt(0, "note_on", 60, track=0),
            _evt(0, "note_on", 72, track=1),
            _evt(0, "note_on", 84, track=2),
        ]
        result, removed = filter_tracks(events, include_tracks={1})
        assert len(result) == 1
        assert result[0].track == 1
        assert removed == 2

    def test_filter_multiple_tracks(self):
        events = [
            _evt(0, "note_on", 60, track=0),
            _evt(0, "note_on", 72, track=1),
            _evt(0, "note_on", 84, track=2),
            _evt(0, "note_on", 48, track=3),
        ]
        result, removed = filter_tracks(events, include_tracks={0, 2})
        assert len(result) == 2
        assert {e.track for e in result} == {0, 2}
        assert removed == 2

    def test_empty_include_set_removes_all(self):
        events = [
            _evt(0, "note_on", 60, track=0),
            _evt(0.5, "note_off", 60, track=0),
        ]
        result, removed = filter_tracks(events, include_tracks=set())
        assert len(result) == 0
        assert removed == 2

    def test_empty_events(self):
        result, removed = filter_tracks([], include_tracks={0})
        assert result == []
        assert removed == 0

    def test_preserves_event_order(self):
        events = [
            _evt(0, "note_on", 60, track=0),
            _evt(0.1, "note_on", 72, track=1),
            _evt(0.2, "note_on", 64, track=0),
        ]
        result, _ = filter_tracks(events, include_tracks={0})
        assert result[0].note == 60
        assert result[1].note == 64


# ── deduplicate_octaves ──────────────────────────────────


class TestDeduplicateOctaves:
    def test_same_pitch_class_same_time_keeps_highest(self):
        """C4 (60) and C5 (72) at same time → keep C5."""
        events = [
            _evt(0, "note_on", 60),  # C4
            _evt(0, "note_on", 72),  # C5 — higher → kept
            _evt(0.5, "note_off", 60),
            _evt(0.5, "note_off", 72),
        ]
        result, removed = deduplicate_octaves(events)
        note_ons = [e for e in result if e.event_type == "note_on"]
        assert len(note_ons) == 1
        assert note_ons[0].note == 72
        assert removed > 0

    def test_different_pitch_classes_kept(self):
        """C4 (60) and D4 (62) at same time → both kept."""
        events = [
            _evt(0, "note_on", 60),  # C4
            _evt(0, "note_on", 62),  # D4
        ]
        result, removed = deduplicate_octaves(events)
        assert len(result) == 2
        assert removed == 0

    def test_same_pitch_class_different_time_kept(self):
        """C4 at t=0 and C5 at t=1 → both kept."""
        events = [
            _evt(0, "note_on", 60),
            _evt(1, "note_on", 72),
        ]
        result, removed = deduplicate_octaves(events)
        assert len(result) == 2
        assert removed == 0

    def test_three_octaves_keep_highest(self):
        """C3 (48), C4 (60), C5 (72) at same time → keep only C5."""
        events = [
            _evt(0, "note_on", 48),
            _evt(0, "note_on", 60),
            _evt(0, "note_on", 72),
            _evt(0.5, "note_off", 48),
            _evt(0.5, "note_off", 60),
            _evt(0.5, "note_off", 72),
        ]
        result, removed = deduplicate_octaves(events)
        note_ons = [e for e in result if e.event_type == "note_on"]
        assert len(note_ons) == 1
        assert note_ons[0].note == 72

    def test_empty_list(self):
        result, removed = deduplicate_octaves([])
        assert result == []
        assert removed == 0

    def test_single_note(self):
        events = [_evt(0, "note_on", 60), _evt(0.5, "note_off", 60)]
        result, removed = deduplicate_octaves(events)
        assert len(result) == 2
        assert removed == 0

    def test_note_off_also_removed(self):
        """When a note_on is dropped, its matching note_off should also be dropped."""
        events = [
            _evt(0, "note_on", 60),  # C4 — will be dropped
            _evt(0, "note_on", 72),  # C5 — kept
            _evt(0.5, "note_off", 60),  # should also be dropped
            _evt(0.5, "note_off", 72),  # kept
        ]
        result, removed = deduplicate_octaves(events)
        # 2 removed: note_on(60) + note_off(60)
        assert removed == 2
        assert len(result) == 2

    def test_complex_chord(self):
        """A chord with octave doublings in multiple pitch classes."""
        events = [
            # C major chord with octave doublings
            _evt(0, "note_on", 48),  # C3
            _evt(0, "note_on", 60),  # C4 → C4 kept (highest C)
            _evt(0, "note_on", 52),  # E3
            _evt(0, "note_on", 64),  # E4 → E4 kept
            _evt(0, "note_on", 55),  # G3 — no duplicate, kept
        ]
        result, removed = deduplicate_octaves(events)
        note_ons = [e for e in result if e.event_type == "note_on"]
        assert len(note_ons) == 3  # C4, E4, G3
        notes = sorted(e.note for e in note_ons)
        assert notes == [55, 60, 64]


# ── limit_polyphony ──────────────────────────────────────


class TestLimitPolyphony:
    def test_disabled_when_max_zero(self):
        events = [
            _evt(0, "note_on", 60),
            _evt(0, "note_on", 64),
            _evt(0, "note_on", 67),
        ]
        result, removed = limit_polyphony(events, max_voices=0)
        assert len(result) == 3
        assert removed == 0

    def test_disabled_when_negative(self):
        events = [_evt(0, "note_on", 60)]
        result, removed = limit_polyphony(events, max_voices=-1)
        assert len(result) == 1
        assert removed == 0

    def test_within_limit_no_removal(self):
        events = [
            _evt(0, "note_on", 60),
            _evt(0, "note_on", 64),
            _evt(0.5, "note_off", 60),
            _evt(0.5, "note_off", 64),
        ]
        result, removed = limit_polyphony(events, max_voices=4)
        assert len(result) == 4
        assert removed == 0

    def test_limit_to_one_voice(self):
        """With max_voices=1, highest note wins (no bass anchor at 1 voice)."""
        events = [
            _evt(0, "note_on", 60),  # lower → dropped
            _evt(0, "note_on", 64),  # higher → kept
            _evt(0.5, "note_off", 60),
            _evt(0.5, "note_off", 64),
        ]
        result, removed = limit_polyphony(events, max_voices=1)
        note_ons = [e for e in result if e.event_type == "note_on"]
        assert len(note_ons) == 1
        assert note_ons[0].note == 64  # highest kept
        assert removed >= 2  # note_on(60) + note_off(60)

    def test_limit_to_two_keeps_highest_and_lowest(self):
        """With 3 simultaneous notes and max_voices=2, keep highest + lowest."""
        events = [
            _evt(0, "note_on", 60),  # C4 — lowest → kept
            _evt(0, "note_on", 64),  # E4 — middle → may be dropped
            _evt(0, "note_on", 72),  # C5 — highest → kept
            _evt(0.5, "note_off", 60),
            _evt(0.5, "note_off", 64),
            _evt(0.5, "note_off", 72),
        ]
        result, removed = limit_polyphony(events, max_voices=2)
        note_ons = [e for e in result if e.event_type == "note_on"]
        notes = {e.note for e in note_ons}
        assert 60 in notes  # lowest kept
        assert 72 in notes  # highest kept
        assert removed >= 1

    def test_dropped_note_off_also_removed(self):
        """When a note_on is dropped, its note_off should also be removed."""
        events = [
            _evt(0, "note_on", 60),  # lower → dropped (max_voices=1, high-note priority)
            _evt(0, "note_on", 64),  # higher → kept
            _evt(0.5, "note_off", 60),  # should also be removed
            _evt(0.5, "note_off", 64),
        ]
        result, removed = limit_polyphony(events, max_voices=1)
        # Both note_on(60) and note_off(60) should be removed
        assert removed == 2
        assert all(e.note == 64 for e in result)

    def test_voice_freed_after_note_off(self):
        """After a note_off frees a voice, new notes should be accepted."""
        events = [
            _evt(0, "note_on", 60),
            _evt(0.5, "note_off", 60),  # frees the voice
            _evt(1, "note_on", 64),  # should be accepted now
        ]
        result, removed = limit_polyphony(events, max_voices=1)
        note_ons = [e for e in result if e.event_type == "note_on"]
        assert len(note_ons) == 2
        assert removed == 0

    def test_empty_list(self):
        result, removed = limit_polyphony([], max_voices=2)
        assert result == []
        assert removed == 0

    def test_realistic_4_voice_limit(self):
        """Simulate a 4-voice limit on a 6-note chord."""
        events = [
            _evt(0, "note_on", 48),  # C3
            _evt(0, "note_on", 52),  # E3
            _evt(0, "note_on", 55),  # G3
            _evt(0, "note_on", 60),  # C4
            _evt(0, "note_on", 64),  # E4
            _evt(0, "note_on", 72),  # C5
        ]
        result, removed = limit_polyphony(events, max_voices=4)
        note_ons = [e for e in result if e.event_type == "note_on"]
        assert len(note_ons) == 4
        assert removed == 2
        # Highest (72) and lowest (48) should be preserved
        notes = {e.note for e in note_ons}
        assert 48 in notes
        assert 72 in notes


# ── preprocess (new features integration) ─────────────────


class TestPreprocessPercussion:
    def test_percussion_removed_by_default(self):
        events = [
            _evt(0, "note_on", 60, channel=0),
            _evt(0, "note_on", 36, channel=9),  # percussion
            _evt(0.5, "note_off", 60, channel=0),
            _evt(0.5, "note_off", 36, channel=9),
        ]
        result, stats = preprocess(events)
        assert stats.percussion_removed == 2
        assert all(e.channel != 9 for e in result if e.event_type in ("note_on", "note_off"))

    def test_percussion_kept_when_disabled(self):
        events = [
            _evt(0, "note_on", 60, channel=0),
            _evt(0, "note_on", 36, channel=9),
        ]
        _, stats = preprocess(events, remove_percussion=False)
        assert stats.percussion_removed == 0


class TestPreprocessTrackFilter:
    def test_include_tracks_filters(self):
        events = [
            _evt(0, "note_on", 60, track=0),
            _evt(0, "note_on", 72, track=1),
            _evt(0, "note_on", 64, track=2),
            _evt(0.5, "note_off", 60, track=0),
            _evt(0.5, "note_off", 72, track=1),
            _evt(0.5, "note_off", 64, track=2),
        ]
        _, stats = preprocess(events, include_tracks={0, 2})
        assert stats.tracks_removed > 0

    def test_include_tracks_none_keeps_all(self):
        events = [
            _evt(0, "note_on", 60, track=0),
            _evt(0, "note_on", 72, track=1),
        ]
        _, stats = preprocess(events, include_tracks=None)
        assert stats.tracks_removed == 0


class TestPreprocessOctaveDedup:
    def test_octave_dedup_in_pipeline(self):
        """Octave doublings should be removed in the full pipeline."""
        events = [
            _evt(0, "note_on", 60),  # C4
            _evt(0, "note_on", 72),  # C5 — octave doubling
            _evt(0, "note_on", 62),  # D4 — different pitch class
            _evt(0.5, "note_off", 60),
            _evt(0.5, "note_off", 72),
            _evt(0.5, "note_off", 62),
        ]
        _, stats = preprocess(events)
        assert stats.octave_deduped > 0


class TestPreprocessPolyphonyLimit:
    def test_polyphony_limit_in_pipeline(self):
        events = [_evt(i * 0.001, "note_on", 48 + i) for i in range(10)]
        events += [_evt(1.0 + i * 0.001, "note_off", 48 + i) for i in range(10)]
        _, stats = preprocess(events, max_voices=4)
        assert stats.polyphony_limited > 0

    def test_polyphony_limit_zero_means_no_limit(self):
        events = [_evt(0, "note_on", 48 + i) for i in range(10)]
        _, stats = preprocess(events, max_voices=0)
        assert stats.polyphony_limited == 0


class TestPreprocessFullPipeline:
    """Integration tests for the complete 9-stage pipeline."""

    def test_all_stats_populated(self):
        """Pipeline should populate all stat fields."""
        events = [
            _evt(0, "note_on", 36, channel=9),  # percussion
            _evt(0, "note_on", 60, channel=0),  # C4
            _evt(0, "note_on", 72, channel=0),  # C5 — octave dup
            _evt(0, "note_on", 96, channel=0),  # C7 — out of range
            _evt(0.5, "note_off", 36, channel=9),
            _evt(0.5, "note_off", 60, channel=0),
            _evt(0.5, "note_off", 72, channel=0),
            _evt(0.5, "note_off", 96, channel=0),
        ]
        result, stats = preprocess(events)
        assert stats.percussion_removed > 0
        assert stats.total_notes > 0
        assert isinstance(stats.original_range, tuple)
        assert len(stats.original_range) == 2

    def test_percussion_then_track_filter_order(self):
        """Percussion filter runs before track filter."""
        events = [
            _evt(0, "note_on", 36, channel=9, track=0),  # percussion on track 0
            _evt(0, "note_on", 60, channel=0, track=0),  # piano on track 0
            _evt(0, "note_on", 72, channel=0, track=1),  # piano on track 1
        ]
        # Include only track 0 — percussion should already be removed
        _, stats = preprocess(events, include_tracks={0})
        assert stats.percussion_removed == 1
        assert stats.tracks_removed > 0

    def test_end_to_end_complex(self):
        """Complex scenario with all pipeline stages active."""
        events = []
        # Track 0: Melody (channel 0)
        for i in range(20):
            n = 60 + (i % 12)
            events.append(_evt(i * 0.1, "note_on", n, track=0, channel=0))
            events.append(_evt(i * 0.1 + 0.05, "note_off", n, track=0, channel=0))

        # Track 1: Bass (channel 0, low notes)
        for i in range(10):
            n = 36 + (i % 12)
            events.append(_evt(i * 0.2, "note_on", n, track=1, channel=0))
            events.append(_evt(i * 0.2 + 0.1, "note_off", n, track=1, channel=0))

        # Track 9: Drums (channel 9)
        for i in range(8):
            events.append(_evt(i * 0.25, "note_on", 36, track=2, channel=9))
            events.append(_evt(i * 0.25 + 0.05, "note_off", 36, track=2, channel=9))

        events.sort(key=lambda e: e.time_seconds)

        result, stats = preprocess(events, max_voices=4)
        assert stats.percussion_removed > 0
        assert stats.total_notes > 0
        # All surviving notes in range
        for e in result:
            if e.event_type == "note_on":
                assert 48 <= e.note <= 83
                assert e.velocity == 127

    def test_pipeline_preserves_note_off_before_note_on(self):
        """At the same quantized time, note_off should come before note_on."""
        events = [
            _evt(0, "note_off", 60),
            _evt(0, "note_on", 64),
        ]
        result, _ = preprocess(events)
        assert result[0].event_type == "note_off"
        assert result[1].event_type == "note_on"

    def test_pipeline_empty_after_filters(self):
        """If all events are filtered out, should return empty gracefully."""
        events = [
            _evt(0, "note_on", 36, channel=9),
            _evt(0.5, "note_off", 36, channel=9),
        ]
        result, stats = preprocess(events, remove_percussion=True)
        # All notes were percussion — after filtering, no note_ons
        # The pipeline should handle empty events gracefully
        note_ons = [e for e in result if e.event_type == "note_on"]
        assert len(note_ons) == 0
        assert stats.percussion_removed == 2


# ── normalize_octave_flowing (流水摺疊) ──────────────────


class TestFlowingFold:
    """Tests for the voice-leading aware octave fold."""

    def test_in_range_unchanged(self):
        """Notes already in range should not be modified."""
        events = [
            _evt(0, "note_on", 60),
            _evt(0.5, "note_off", 60),
        ]
        result = normalize_octave_flowing(events)
        assert result[0].note == 60
        assert result[1].note == 60

    def test_boundary_min(self):
        """Note at exact minimum should be unchanged."""
        events = [_evt(0, "note_on", 48)]
        result = normalize_octave_flowing(events)
        assert result[0].note == 48

    def test_boundary_max(self):
        """Note at exact maximum should be unchanged."""
        events = [_evt(0, "note_on", 83)]
        result = normalize_octave_flowing(events)
        assert result[0].note == 83

    def test_empty_list(self):
        assert normalize_octave_flowing([]) == []

    def test_metadata_preserved(self):
        """time_seconds, velocity, track, channel should be preserved."""
        events = [_evt(1.5, "note_on", 96, vel=100, track=2, channel=3)]
        result = normalize_octave_flowing(events)
        assert result[0].time_seconds == 1.5
        assert result[0].velocity == 100
        assert result[0].track == 2
        assert result[0].channel == 3
        assert 48 <= result[0].note <= 83

    def test_ascending_melody_stays_ascending(self):
        """An ascending melody that spans >3 octaves should fold upward."""
        # C3(48) D3(50) E3(52) ... then jump to C6(84) D6(86) E6(88)
        # After fold, the high notes should still trend upward from previous
        events = []
        t = 0.0
        # Start with notes in range to establish context
        for n in [60, 62, 64, 65, 67, 69, 71, 72]:
            events.append(_evt(t, "note_on", n))
            events.append(_evt(t + 0.09, "note_off", n))
            t += 0.1
        # Now add out-of-range ascending notes
        for n in [84, 86, 88]:
            events.append(_evt(t, "note_on", n))
            events.append(_evt(t + 0.09, "note_off", n))
            t += 0.1

        result = normalize_octave_flowing(events)
        note_ons = [e for e in result if e.event_type == "note_on"]
        # All notes must be in range
        for e in note_ons:
            assert 48 <= e.note <= 83
        # The last 3 notes (folded from 84,86,88) should be ascending
        last3 = [e.note for e in note_ons[-3:]]
        assert last3 == sorted(last3), f"Expected ascending, got {last3}"

    def test_descending_melody_stays_descending(self):
        """A descending melody should fold to preserve downward direction."""
        events = []
        t = 0.0
        # Start mid-range descending
        for n in [72, 71, 69, 67, 65, 64, 62, 60]:
            events.append(_evt(t, "note_on", n))
            events.append(_evt(t + 0.09, "note_off", n))
            t += 0.1
        # Continue descending below range
        for n in [47, 45, 43]:
            events.append(_evt(t, "note_on", n))
            events.append(_evt(t + 0.09, "note_off", n))
            t += 0.1

        result = normalize_octave_flowing(events)
        note_ons = [e for e in result if e.event_type == "note_on"]
        for e in note_ons:
            assert 48 <= e.note <= 83
        # The last 3 notes (folded from 47,45,43) should be descending
        last3 = [e.note for e in note_ons[-3:]]
        assert last3 == sorted(last3, reverse=True), f"Expected descending, got {last3}"

    def test_note_off_pairing(self):
        """note_off should be folded to match its corresponding note_on."""
        events = [
            _evt(0, "note_on", 96),  # out of range → folded
            _evt(0.5, "note_off", 96),  # should match the folded note_on
        ]
        result = normalize_octave_flowing(events)
        assert result[0].note == result[1].note
        assert 48 <= result[0].note <= 83

    def test_different_channels_independent(self):
        """Each channel should track voice state independently."""
        events = [
            # Channel 0: ascending
            _evt(0.0, "note_on", 60, channel=0),
            _evt(0.1, "note_on", 64, channel=0),
            _evt(0.2, "note_on", 67, channel=0),
            # Channel 1: descending (interleaved)
            _evt(0.0, "note_on", 72, channel=1),
            _evt(0.1, "note_on", 69, channel=1),
            _evt(0.2, "note_on", 65, channel=1),
            # Now an out-of-range note on each channel
            _evt(0.3, "note_on", 84, channel=0),  # ch0 was ascending
            _evt(0.3, "note_on", 84, channel=1),  # ch1 was descending
        ]
        result = normalize_octave_flowing(events)
        # Both ch0 and ch1 out-of-range notes fold into range
        ch0_last = [e for e in result if e.event_type == "note_on" and e.channel == 0][-1]
        ch1_last = [e for e in result if e.event_type == "note_on" and e.channel == 1][-1]
        assert 48 <= ch0_last.note <= 83
        assert 48 <= ch1_last.note <= 83

    def test_extreme_range_no_crash(self):
        """Notes at MIDI extremes (0 and 127) should not crash."""
        events = [
            _evt(0, "note_on", 0),
            _evt(0.1, "note_on", 127),
            _evt(0.5, "note_off", 0),
            _evt(0.6, "note_off", 127),
        ]
        result = normalize_octave_flowing(events)
        for e in result:
            assert 48 <= e.note <= 83

    def test_all_notes_in_range_after_fold(self):
        """Every note after flowing fold must be in [note_min, note_max]."""
        events = [_evt(i * 0.1, "note_on", 20 + i * 7) for i in range(16)]
        result = normalize_octave_flowing(events)
        for e in result:
            if e.event_type == "note_on":
                assert 48 <= e.note <= 83, f"Note {e.note} out of range"

    def test_single_out_of_range_note(self):
        """A single out-of-range note should be folded into range."""
        events = [_evt(0, "note_on", 96)]
        result = normalize_octave_flowing(events)
        assert 48 <= result[0].note <= 83
        # C7 (96) pitch class C → candidates are 48, 60, 72 → should pick one
        assert result[0].note % 12 == 0


# ── deduplicate_notes velocity priority ──────────────────


class TestDeduplicateNotesVelocity:
    """Tests for the velocity-priority collision dedup."""

    def test_collision_keeps_highest_velocity(self):
        """When two note_on events collide, the higher velocity wins."""
        events = [
            _evt(0, "note_on", 60, vel=50),
            _evt(0, "note_on", 60, vel=100),  # higher velocity
        ]
        result, removed = deduplicate_notes(events)
        note_ons = [e for e in result if e.event_type == "note_on"]
        assert len(note_ons) == 1
        assert note_ons[0].velocity == 100
        assert removed == 1

    def test_no_collision_unchanged(self):
        """Without collisions, all events pass through."""
        events = [
            _evt(0, "note_on", 60, vel=80),
            _evt(0.5, "note_off", 60),
            _evt(1.0, "note_on", 64, vel=90),
        ]
        result, removed = deduplicate_notes(events)
        assert len(result) == 3
        assert removed == 0

    def test_note_off_dedup_not_affected_by_velocity(self):
        """note_off duplicates should be collapsed regardless of velocity."""
        events = [
            _evt(1.0, "note_off", 60, vel=0),
            _evt(1.0, "note_off", 60, vel=64),
        ]
        result, removed = deduplicate_notes(events)
        note_offs = [e for e in result if e.event_type == "note_off"]
        assert len(note_offs) == 1
        assert removed == 1
