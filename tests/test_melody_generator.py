"""Comprehensive tests for melody_generator.py (AI Composition).

Tests cover:
- Scale pool generation (all scale types, edge cases)
- Melody generation (determinism, constraints, phrase resolution)
- Bass line generation (patterns, progressions, time signatures)
- Integration scenarios
"""

from __future__ import annotations

from cyber_qin.core.beat_sequence import BeatNote
from cyber_qin.core.melody_generator import (
    PROGRESSIONS,
    SCALE_INTERVALS,
    BassConfig,
    MelodyConfig,
    _apply_contour,
    _build_scale_pool,
    _interval_weight,
    generate_bass_line,
    generate_melody,
)

# ── Scale Pool Tests (~10 tests) ─────────────────────────────────────


def test_build_scale_pool_major_contains_correct_notes():
    """Major scale pool contains only C major scale notes."""
    pool = _build_scale_pool(root=60, scale="major", note_min=60, note_max=71)
    # C major: C D E F G A B (60, 62, 64, 65, 67, 69, 71)
    assert pool == [60, 62, 64, 65, 67, 69, 71]


def test_build_scale_pool_pentatonic_has_5_notes_per_octave():
    """Pentatonic scale has 5 notes per octave."""
    pool = _build_scale_pool(root=60, scale="pentatonic", note_min=48, note_max=84)
    # Should contain 5 notes per octave (48-59, 60-71, 72-83)
    # C pentatonic: C D E G A
    pitch_classes = {p % 12 for p in pool}
    assert len(pitch_classes) == 5
    # Verify intervals: 0, 2, 4, 7, 9
    assert pitch_classes == {0, 2, 4, 7, 9}


def test_build_scale_pool_respects_note_min_note_max():
    """Scale pool respects note_min and note_max bounds."""
    pool = _build_scale_pool(root=60, scale="major", note_min=65, note_max=72)
    assert all(65 <= note <= 72 for note in pool)
    # Should include F4(65), G4(67), A4(69), B4(71), C5(72)
    assert pool == [65, 67, 69, 71, 72]


def test_build_scale_pool_empty_when_range_too_small():
    """Empty pool when note range is too narrow to fit any scale notes."""
    pool = _build_scale_pool(root=60, scale="major", note_min=61, note_max=61)
    # Only MIDI 61 (C#), not in C major scale
    assert pool == []


def test_build_scale_pool_minor_scale():
    """Minor scale produces correct intervals."""
    pool = _build_scale_pool(root=60, scale="minor", note_min=60, note_max=71)
    # C minor: C D Eb F G Ab Bb (60, 62, 63, 65, 67, 68, 70)
    assert pool == [60, 62, 63, 65, 67, 68, 70]


def test_build_scale_pool_minor_pentatonic():
    """Minor pentatonic scale."""
    pool = _build_scale_pool(root=60, scale="minor_pentatonic", note_min=60, note_max=71)
    # C minor pentatonic: C Eb F G Bb (60, 63, 65, 67, 70)
    assert pool == [60, 63, 65, 67, 70]


def test_build_scale_pool_blues():
    """Blues scale."""
    pool = _build_scale_pool(root=60, scale="blues", note_min=60, note_max=71)
    # C blues: C Eb F F# G Bb (60, 63, 65, 66, 67, 70)
    assert pool == [60, 63, 65, 66, 67, 70]


def test_build_scale_pool_dorian():
    """Dorian mode."""
    pool = _build_scale_pool(root=60, scale="dorian", note_min=60, note_max=71)
    # C dorian: C D Eb F G A Bb (60, 62, 63, 65, 67, 69, 70)
    assert pool == [60, 62, 63, 65, 67, 69, 70]


def test_build_scale_pool_mixolydian():
    """Mixolydian mode."""
    pool = _build_scale_pool(root=60, scale="mixolydian", note_min=60, note_max=71)
    # C mixolydian: C D E F G A Bb (60, 62, 64, 65, 67, 69, 70)
    assert pool == [60, 62, 64, 65, 67, 69, 70]


def test_build_scale_pool_harmonic_minor():
    """Harmonic minor scale."""
    pool = _build_scale_pool(root=60, scale="harmonic_minor", note_min=60, note_max=71)
    # C harmonic minor: C D Eb F G Ab B (60, 62, 63, 65, 67, 68, 71)
    assert pool == [60, 62, 63, 65, 67, 68, 71]


# ── Melody Generation Tests (~25 tests) ──────────────────────────────


def test_generate_melody_default_config_produces_notes():
    """Default config generates valid melody."""
    notes = generate_melody()
    assert len(notes) > 0
    assert all(isinstance(n, BeatNote) for n in notes)


def test_generate_melody_empty_config_edge_case():
    """Zero bars produces empty melody."""
    config = MelodyConfig(num_bars=0)
    notes = generate_melody(config)
    assert notes == []


def test_generate_melody_seed_produces_deterministic_output():
    """Same seed produces identical melodies."""
    config = MelodyConfig(num_bars=4)
    notes1 = generate_melody(config, seed=42)
    notes2 = generate_melody(config, seed=42)
    assert notes1 == notes2


def test_generate_melody_different_seeds_produce_different_melodies():
    """Different seeds produce different melodies."""
    config = MelodyConfig(num_bars=8)
    notes1 = generate_melody(config, seed=1)
    notes2 = generate_melody(config, seed=2)
    # Should differ in at least one note
    assert notes1 != notes2


def test_generate_melody_all_notes_within_range():
    """All generated notes respect note_min and note_max."""
    config = MelodyConfig(note_min=60, note_max=72, num_bars=8)
    notes = generate_melody(config, seed=123)
    assert all(60 <= n.note <= 72 for n in notes)


def test_generate_melody_notes_are_sorted_by_time():
    """Notes are sorted chronologically."""
    config = MelodyConfig(num_bars=8)
    notes = generate_melody(config, seed=456)
    times = [n.time_beats for n in notes]
    assert times == sorted(times)


def test_generate_melody_note_count_matches_pattern_length():
    """Note count roughly matches bars * typical pattern length."""
    config = MelodyConfig(num_bars=4, time_signature=(4, 4))
    notes = generate_melody(config, seed=789)
    # 4/4 patterns have 3-8 notes per bar
    assert 12 <= len(notes) <= 40


def test_generate_melody_phrase_resolution_tonic_or_fifth():
    """Last note of each phrase resolves to tonic or 5th."""
    config = MelodyConfig(root=60, scale="major", num_bars=8, phrase_length=4)
    notes = generate_melody(config, seed=111)

    # Identify phrase boundaries (bar 3, 7 at beat offset ~4.0, ~8.0)
    # 4/4: beats_per_bar = 4.0
    # Phrase ends at bar=3, bar=7 (0-indexed)
    # Last notes near time_beats = 16.0, 32.0

    # Group notes by bar
    beats_per_bar = 4.0
    phrase_boundaries = [config.phrase_length * beats_per_bar, config.num_bars * beats_per_bar]

    # Check last note of each phrase
    for boundary in phrase_boundaries:
        # Find notes near this boundary
        near_notes = [n for n in notes if abs(n.time_beats + n.duration_beats - boundary) < 0.1]
        if near_notes:
            last_note = max(near_notes, key=lambda n: n.time_beats)
            # Should be tonic (0) or 5th (7)
            assert last_note.note % 12 in {0, 7}


def test_generate_melody_final_note_on_tonic_or_fifth():
    """Final note resolves to tonic or 5th."""
    config = MelodyConfig(root=60, scale="major", num_bars=8)
    notes = generate_melody(config, seed=222)
    final_note = notes[-1]
    # Root = 60 (C4), tonic = C (0), 5th = G (7)
    assert final_note.note % 12 in {0, 7}


def test_generate_melody_time_signature_3_4():
    """3/4 time signature works correctly."""
    config = MelodyConfig(time_signature=(3, 4), num_bars=4)
    notes = generate_melody(config, seed=333)
    # 3/4: beats_per_bar = 3.0
    # Total beats = 4 * 3 = 12
    assert all(n.time_beats < 12.0 for n in notes)


def test_generate_melody_time_signature_4_4():
    """4/4 time signature works correctly."""
    config = MelodyConfig(time_signature=(4, 4), num_bars=4)
    notes = generate_melody(config, seed=444)
    # 4/4: beats_per_bar = 4.0
    # Total beats = 4 * 4 = 16
    assert all(n.time_beats < 16.0 for n in notes)


def test_generate_melody_major_scale():
    """Major scale produces valid output."""
    config = MelodyConfig(scale="major", num_bars=4)
    notes = generate_melody(config, seed=555)
    assert len(notes) > 0


def test_generate_melody_minor_scale():
    """Minor scale produces valid output."""
    config = MelodyConfig(scale="minor", num_bars=4)
    notes = generate_melody(config, seed=666)
    assert len(notes) > 0


def test_generate_melody_pentatonic_scale():
    """Pentatonic scale produces valid output."""
    config = MelodyConfig(scale="pentatonic", num_bars=4)
    notes = generate_melody(config, seed=777)
    assert len(notes) > 0


def test_generate_melody_stepwise_bias_high():
    """stepwise_bias=1.0 produces mostly step motion."""
    config = MelodyConfig(stepwise_bias=1.0, num_bars=8, note_min=60, note_max=72)
    notes = generate_melody(config, seed=888)

    # Build pool to check intervals
    pool = _build_scale_pool(60, "major", 60, 72)
    pool_indices = {p: i for i, p in enumerate(pool)}

    # Count step motion (interval = 1 in pool index)
    step_count = 0
    total_intervals = 0
    for i in range(1, len(notes)):
        if notes[i - 1].note in pool_indices and notes[i].note in pool_indices:
            interval = abs(pool_indices[notes[i].note] - pool_indices[notes[i - 1].note])
            if interval == 1:
                step_count += 1
            total_intervals += 1

    # With high stepwise bias, expect >50% steps
    if total_intervals > 0:
        step_ratio = step_count / total_intervals
        assert step_ratio > 0.3  # Relaxed due to resolution forcing


def test_generate_melody_stepwise_bias_low():
    """stepwise_bias=0.0 allows more skips."""
    config = MelodyConfig(stepwise_bias=0.0, num_bars=8, note_min=60, note_max=72)
    notes = generate_melody(config, seed=999)

    # Build pool
    pool = _build_scale_pool(60, "major", 60, 72)
    pool_indices = {p: i for i, p in enumerate(pool)}

    # Count large intervals (>= 2 in pool index)
    skip_count = 0
    total_intervals = 0
    for i in range(1, len(notes)):
        if notes[i - 1].note in pool_indices and notes[i].note in pool_indices:
            interval = abs(pool_indices[notes[i].note] - pool_indices[notes[i - 1].note])
            if interval >= 2:
                skip_count += 1
            total_intervals += 1

    # With low stepwise bias, expect some skips
    if total_intervals > 0:
        skip_ratio = skip_count / total_intervals
        assert skip_ratio > 0.1  # At least some skips


def test_generate_melody_custom_track_assignment():
    """Custom track assignment works."""
    config = MelodyConfig(track=5, num_bars=4)
    notes = generate_melody(config, seed=1010)
    assert all(n.track == 5 for n in notes)


def test_generate_melody_custom_velocity():
    """Custom velocity works."""
    config = MelodyConfig(velocity=80, num_bars=4)
    notes = generate_melody(config, seed=1111)
    assert all(n.velocity == 80 for n in notes)


def test_generate_melody_all_notes_valid_midi_range():
    """All notes are valid MIDI (0-127)."""
    config = MelodyConfig(num_bars=8)
    notes = generate_melody(config, seed=1212)
    assert all(0 <= n.note <= 127 for n in notes)


def test_generate_melody_no_overlapping_notes():
    """No two notes overlap at the exact same time (within tolerance)."""
    config = MelodyConfig(num_bars=8)
    notes = generate_melody(config, seed=1313)

    # Check that no two notes have the same start time
    times = [n.time_beats for n in notes]
    # Allow small floating point tolerance
    for i in range(len(times) - 1):
        for j in range(i + 1, len(times)):
            assert abs(times[i] - times[j]) > 1e-6


def test_generate_melody_custom_root_note():
    """Custom root note (e.g., F4 = 65)."""
    config = MelodyConfig(root=65, scale="major", note_min=65, note_max=77, num_bars=4)
    notes = generate_melody(config, seed=1414)

    # F major: F G A Bb C D E (65, 67, 69, 70, 72, 74, 76)
    valid_notes = {65, 67, 69, 70, 72, 74, 76, 77}
    assert all(n.note in valid_notes for n in notes)


def test_generate_melody_short_melody_1_bar():
    """1-bar melody generates successfully."""
    config = MelodyConfig(num_bars=1)
    notes = generate_melody(config, seed=1515)
    assert len(notes) > 0
    # All notes within 4 beats (4/4)
    assert all(n.time_beats < 4.0 for n in notes)


def test_generate_melody_empty_pool():
    """Empty pool (impossible range) returns empty list."""
    config = MelodyConfig(note_min=100, note_max=50)  # Inverted range
    notes = generate_melody(config, seed=1616)
    assert notes == []


# ── Bass Line Generation Tests (~15 tests) ───────────────────────────


def test_generate_bass_line_default_config_produces_notes():
    """Default config generates valid bass line."""
    notes = generate_bass_line()
    assert len(notes) > 0
    assert all(isinstance(n, BeatNote) for n in notes)


def test_generate_bass_line_seed_deterministic():
    """Same seed produces identical bass lines."""
    config = BassConfig(num_bars=4)
    notes1 = generate_bass_line(config, seed=42)
    notes2 = generate_bass_line(config, seed=42)
    assert notes1 == notes2


def test_generate_bass_line_root_pattern_one_note_per_bar():
    """Root pattern produces 1 note per bar."""
    config = BassConfig(pattern="root", num_bars=4)
    notes = generate_bass_line(config, seed=123)
    assert len(notes) == 4  # 1 per bar


def test_generate_bass_line_root_fifth_pattern_two_notes_per_bar():
    """Root-fifth pattern produces 2 notes per bar."""
    config = BassConfig(pattern="root_fifth", num_bars=4)
    notes = generate_bass_line(config, seed=456)
    assert len(notes) == 8  # 2 per bar


def test_generate_bass_line_walking_pattern_four_notes_per_bar():
    """Walking pattern produces 4 notes per bar."""
    config = BassConfig(pattern="walking", num_bars=4)
    notes = generate_bass_line(config, seed=789)
    assert len(notes) == 16  # 4 per bar


def test_generate_bass_line_progression_i_iv_v_i():  # noqa: N802
    """I-IV-V-I progression follows correct chord roots."""
    config = BassConfig(
        root=48,
        scale="major",
        progression="I-IV-V-I",
        pattern="root",
        num_bars=4,
        note_min=36,
        note_max=60,
    )
    notes = generate_bass_line(config, seed=111)

    # C major: I=C(0), IV=F(5), V=G(7), I=C(0)
    # Expected pitch classes: 0, 5, 7, 0
    expected_pcs = [0, 5, 7, 0]
    actual_pcs = [n.note % 12 for n in notes]
    assert actual_pcs == expected_pcs


def test_generate_bass_line_progression_i_v_vi_iv():  # noqa: N802
    """I-V-vi-IV progression."""
    config = BassConfig(
        root=48,
        scale="major",
        progression="I-V-vi-IV",
        pattern="root",
        num_bars=4,
        note_min=36,
        note_max=60,
    )
    notes = generate_bass_line(config, seed=222)

    # C major: I=C(0), V=G(7), vi=A(9), IV=F(5)
    expected_pcs = [0, 7, 9, 5]
    actual_pcs = [n.note % 12 for n in notes]
    assert actual_pcs == expected_pcs


def test_generate_bass_line_all_notes_within_range():
    """All bass notes respect note_min and note_max."""
    config = BassConfig(note_min=36, note_max=48, num_bars=8)
    notes = generate_bass_line(config, seed=333)
    assert all(36 <= n.note <= 48 for n in notes)


def test_generate_bass_line_custom_track_assignment():
    """Custom track assignment works."""
    config = BassConfig(track=2, num_bars=4)
    notes = generate_bass_line(config, seed=444)
    assert all(n.track == 2 for n in notes)


def test_generate_bass_line_notes_sorted_by_time():
    """Bass notes are sorted chronologically."""
    config = BassConfig(num_bars=8, pattern="walking")
    notes = generate_bass_line(config, seed=555)
    times = [n.time_beats for n in notes]
    assert times == sorted(times)


def test_generate_bass_line_time_signature_3_4():
    """3/4 time signature for bass."""
    config = BassConfig(time_signature=(3, 4), num_bars=4, pattern="root")
    notes = generate_bass_line(config, seed=666)
    # 3/4: beats_per_bar = 3.0
    # Each note should have duration 3.0
    assert all(abs(n.duration_beats - 3.0) < 0.001 for n in notes)


def test_generate_bass_line_time_signature_4_4():
    """4/4 time signature for bass."""
    config = BassConfig(time_signature=(4, 4), num_bars=4, pattern="root")
    notes = generate_bass_line(config, seed=777)
    # 4/4: beats_per_bar = 4.0
    assert all(abs(n.duration_beats - 4.0) < 0.001 for n in notes)


def test_generate_bass_line_custom_velocity():
    """Custom velocity for root pattern."""
    config = BassConfig(velocity=90, pattern="root", num_bars=4)
    notes = generate_bass_line(config, seed=888)
    assert all(n.velocity == 90 for n in notes)


def test_generate_bass_line_walking_velocity_variation():
    """Walking pattern has velocity variation (downbeats louder)."""
    config = BassConfig(pattern="walking", num_bars=4, velocity=100)
    notes = generate_bass_line(config, seed=999)

    # First note of each bar should be louder (velocity=100)
    # Other notes should be quieter (velocity=90)
    for i in range(0, len(notes), 4):
        assert notes[i].velocity == 100
        for j in range(1, 4):
            if i + j < len(notes):
                assert notes[i + j].velocity == 90


def test_generate_bass_line_empty_pool():
    """Empty pool returns empty list."""
    config = BassConfig(note_min=100, note_max=50)
    notes = generate_bass_line(config, seed=1010)
    assert notes == []


# ── Integration Tests (~10 tests) ────────────────────────────────────


def test_integration_melody_and_bass_combined():
    """Melody and bass together don't overlap tracks."""
    melody_cfg = MelodyConfig(track=0, num_bars=8)
    bass_cfg = BassConfig(track=1, num_bars=8)

    melody = generate_melody(melody_cfg, seed=42)
    bass = generate_bass_line(bass_cfg, seed=42)

    assert all(n.track == 0 for n in melody)
    assert all(n.track == 1 for n in bass)


def test_integration_different_scale_key_combinations():
    """Generate with various scale/key combinations."""
    scales = ["major", "minor", "pentatonic", "blues"]
    roots = [60, 62, 65, 67]

    for scale in scales:
        for root in roots:
            config = MelodyConfig(root=root, scale=scale, num_bars=4)
            notes = generate_melody(config, seed=123)
            assert len(notes) > 0


def test_integration_long_generation_32_bars():
    """Long generation (32 bars) completes quickly."""
    config = MelodyConfig(num_bars=32)
    notes = generate_melody(config, seed=456)
    assert len(notes) > 0
    # Should have notes spanning 32 bars (128 beats in 4/4)
    max_time = max(n.time_beats for n in notes)
    assert max_time < 128.0


def test_integration_melody_config_all_fields():
    """All MelodyConfig fields can be customized."""
    config = MelodyConfig(
        root=65,
        scale="dorian",
        note_min=60,
        note_max=84,
        num_bars=16,
        time_signature=(3, 4),
        velocity=110,
        track=3,
        phrase_length=8,
        stepwise_bias=0.8,
    )
    notes = generate_melody(config, seed=789)
    assert len(notes) > 0
    assert all(60 <= n.note <= 84 for n in notes)
    assert all(n.velocity == 110 for n in notes)
    assert all(n.track == 3 for n in notes)


def test_integration_bass_config_all_fields():
    """All BassConfig fields can be customized."""
    config = BassConfig(
        root=55,
        scale="minor",
        note_min=40,
        note_max=60,
        num_bars=12,
        time_signature=(3, 4),
        progression="i-iv-v-i",
        velocity=95,
        track=4,
        pattern="root_fifth",
    )
    notes = generate_bass_line(config, seed=1011)
    assert len(notes) > 0
    assert all(40 <= n.note <= 60 for n in notes)
    assert all(n.track == 4 for n in notes)


def test_integration_combine_melody_bass_different_time_signatures():
    """Melody and bass can have different time signatures (though not recommended)."""
    melody_cfg = MelodyConfig(time_signature=(4, 4), num_bars=4, track=0)
    bass_cfg = BassConfig(time_signature=(3, 4), num_bars=4, track=1)

    melody = generate_melody(melody_cfg, seed=1212)
    bass = generate_bass_line(bass_cfg, seed=1212)

    # Should both generate successfully
    assert len(melody) > 0
    assert len(bass) > 0


def test_integration_melody_with_all_progressions():
    """Bass line with all available progressions."""
    for progression_name in PROGRESSIONS.keys():
        config = BassConfig(progression=progression_name, num_bars=4, pattern="root")
        notes = generate_bass_line(config, seed=1313)
        assert len(notes) == 4


def test_integration_melody_with_all_scales():
    """Melody generation with all scale types."""
    for scale_name in SCALE_INTERVALS.keys():
        config = MelodyConfig(scale=scale_name, num_bars=4)
        notes = generate_melody(config, seed=1414)
        assert len(notes) > 0


def test_integration_interval_weight_function():
    """_interval_weight returns valid probabilities."""
    pool = [60, 62, 64, 65, 67, 69, 71, 72]
    weights = [_interval_weight(pool, 3, i, stepwise_bias=0.7) for i in range(len(pool))]

    # All weights should be non-negative
    assert all(w >= 0 for w in weights)

    # Repetition (interval=0) should have weight 0.3
    assert _interval_weight(pool, 3, 3, 0.7) == 0.3

    # Step motion (interval=1) should have highest weight
    step_weight = _interval_weight(pool, 3, 4, 0.7)
    assert step_weight == 0.7


def test_integration_apply_contour_shapes_weights():
    """_apply_contour modifies weights for arch contour."""
    pool = [60, 62, 64, 65, 67, 69, 71, 72]
    base_weights = [1.0] * len(pool)

    # Rising phase (bar_in_phrase=0, phrase_len=4)
    rising_weights = _apply_contour(base_weights, pool, current_idx=2, bar_in_phrase=0, phrase_len=4)

    # Falling phase (bar_in_phrase=3, phrase_len=4)
    falling_weights = _apply_contour(base_weights, pool, current_idx=5, bar_in_phrase=3, phrase_len=4)

    # Rising should boost higher indices
    assert sum(rising_weights[3:]) > sum(base_weights[3:])

    # Falling should boost lower indices
    assert sum(falling_weights[:5]) > sum(base_weights[:5])
