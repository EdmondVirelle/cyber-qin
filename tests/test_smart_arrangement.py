"""Test smart_arrangement module — auto-transpose and fold notes into playable range.

Covers all public APIs and internal helpers, including strategy selection,
voice-leading, deduplication, and edge cases.
"""

import pytest

from cyber_qin.core.beat_sequence import BeatNote
from cyber_qin.core.smart_arrangement import (
    ArrangementResult,
    arrange_beat_sequence,
    smart_arrange,
)

# ── Fixtures ────────────────────────────────────────────────


@pytest.fixture
def empty_notes() -> list[BeatNote]:
    """Empty input."""
    return []


@pytest.fixture
def notes_in_range() -> list[BeatNote]:
    """All notes already in default playable range (48-83)."""
    return [
        BeatNote(0.0, 1.0, 60, 100, 0),  # C4
        BeatNote(1.0, 1.0, 64, 100, 0),  # E4
        BeatNote(2.0, 1.0, 67, 100, 0),  # G4
        BeatNote(3.0, 1.0, 72, 100, 0),  # C5
    ]


@pytest.fixture
def notes_above_range() -> list[BeatNote]:
    """All notes above playable range."""
    return [
        BeatNote(0.0, 1.0, 96, 100, 0),  # C7
        BeatNote(1.0, 1.0, 100, 100, 0),  # E7
        BeatNote(2.0, 1.0, 103, 100, 0),  # G7
    ]


@pytest.fixture
def notes_below_range() -> list[BeatNote]:
    """All notes below playable range."""
    return [
        BeatNote(0.0, 1.0, 24, 100, 0),  # C1
        BeatNote(1.0, 1.0, 28, 100, 0),  # E1
        BeatNote(2.0, 1.0, 31, 100, 0),  # G1
    ]


@pytest.fixture
def notes_mixed_distribution() -> list[BeatNote]:
    """Wide span requiring folding."""
    return [
        BeatNote(0.0, 1.0, 36, 100, 0),  # C2
        BeatNote(1.0, 1.0, 60, 100, 0),  # C4
        BeatNote(2.0, 1.0, 84, 100, 0),  # C6
        BeatNote(3.0, 1.0, 96, 100, 0),  # C7
    ]


@pytest.fixture
def notes_with_duplicates() -> list[BeatNote]:
    """Same time/pitch/track but different velocities."""
    return [
        BeatNote(0.0, 1.0, 60, 50, 0),
        BeatNote(0.0, 1.0, 60, 100, 0),  # Highest velocity should be kept
        BeatNote(0.0, 1.0, 60, 75, 0),
        BeatNote(1.0, 1.0, 64, 80, 0),
    ]


# ── Basic functionality tests ────────────────────────────────


def test_empty_input_returns_empty_result(empty_notes):
    """Empty input returns empty result with sensible defaults."""
    result = smart_arrange(empty_notes)
    assert result.notes == []
    assert result.transpose_semitones == 0
    assert result.notes_folded == 0
    assert result.strategy_used == "global_transpose"


def test_notes_already_in_range_no_modification(notes_in_range):
    """Notes already in range should not be transposed or folded."""
    result = smart_arrange(notes_in_range)
    assert len(result.notes) == 4
    assert result.transpose_semitones == 0
    assert result.notes_folded == 0
    # All notes should remain unchanged
    for orig, res in zip(notes_in_range, result.notes):
        assert res.note == orig.note
        assert res.time_beats == orig.time_beats


def test_notes_above_range_transpose_down(notes_above_range):
    """Notes all above range should be transposed down by octaves."""
    result = smart_arrange(notes_above_range, note_min=48, note_max=83)
    # Should transpose down to bring into range
    assert result.transpose_semitones < 0
    assert result.transpose_semitones % 12 == 0  # Multiple of octave
    # All resulting notes should be in range
    for note in result.notes:
        assert 48 <= note.note <= 83


def test_notes_below_range_transpose_up(notes_below_range):
    """Notes all below range should be transposed up by octaves."""
    result = smart_arrange(notes_below_range, note_min=48, note_max=83)
    # Should transpose up to bring into range
    assert result.transpose_semitones > 0
    assert result.transpose_semitones % 12 == 0  # Multiple of octave
    # All resulting notes should be in range
    for note in result.notes:
        assert 48 <= note.note <= 83


def test_mixed_distribution_applies_strategy(notes_mixed_distribution):
    """Wide span should trigger appropriate strategy."""
    result = smart_arrange(notes_mixed_distribution)
    # Should pick hybrid or flowing_fold strategy
    assert result.strategy_used in ["hybrid", "flowing_fold"]
    # All notes should end up in range
    for note in result.notes:
        assert 48 <= note.note <= 83


# ── Explicit strategy tests ────────────────────────────────


def test_explicit_strategy_global_transpose(notes_above_range):
    """Explicit global_transpose strategy."""
    result = smart_arrange(notes_above_range, strategy="global_transpose")
    assert result.strategy_used == "global_transpose"
    assert result.transpose_semitones != 0


def test_explicit_strategy_flowing_fold(notes_mixed_distribution):
    """Explicit flowing_fold strategy."""
    result = smart_arrange(notes_mixed_distribution, strategy="flowing_fold")
    assert result.strategy_used == "flowing_fold"


def test_explicit_strategy_hybrid(notes_mixed_distribution):
    """Explicit hybrid strategy."""
    result = smart_arrange(notes_mixed_distribution, strategy="hybrid")
    assert result.strategy_used == "hybrid"


def test_auto_strategy_picks_appropriate(notes_in_range):
    """Auto strategy selects based on distribution."""
    result = smart_arrange(notes_in_range, strategy="auto")
    # Should pick global_transpose for notes already mostly in range
    assert result.strategy_used == "global_transpose"


# ── _compute_best_transpose tests ────────────────────────────


def test_compute_best_transpose_notes_in_range(notes_in_range):
    """Best transpose for notes already in range is zero."""
    from cyber_qin.core.smart_arrangement import _compute_best_transpose

    shift = _compute_best_transpose(notes_in_range, 48, 83)
    assert shift == 0


def test_compute_best_transpose_notes_one_octave_above():
    """Notes exactly one octave above should transpose down -12."""
    from cyber_qin.core.smart_arrangement import _compute_best_transpose

    notes = [
        BeatNote(0.0, 1.0, 72, 100, 0),  # C5
        BeatNote(1.0, 1.0, 76, 100, 0),  # E5
        BeatNote(2.0, 1.0, 79, 100, 0),  # G5
    ]
    shift = _compute_best_transpose(notes, 48, 71)
    assert shift == -12


def test_compute_best_transpose_notes_two_octaves_below():
    """Notes two octaves below should transpose up +24."""
    from cyber_qin.core.smart_arrangement import _compute_best_transpose

    notes = [
        BeatNote(0.0, 1.0, 24, 100, 0),  # C1
        BeatNote(1.0, 1.0, 28, 100, 0),  # E1
    ]
    shift = _compute_best_transpose(notes, 48, 83)
    assert shift == 24


def test_compute_best_transpose_prefers_smaller_shift():
    """When multiple transposes give same in-range count, prefer smaller shift."""
    from cyber_qin.core.smart_arrangement import _compute_best_transpose

    # Notes that work equally well at 0, +12, -12
    notes = [BeatNote(0.0, 1.0, 60, 100, 0)]  # C4 works in 48-83
    shift = _compute_best_transpose(notes, 48, 83)
    assert shift == 0  # Prefer no shift when already in range


def test_compute_best_transpose_empty_returns_zero():
    """Empty note list returns zero transpose."""
    from cyber_qin.core.smart_arrangement import _compute_best_transpose

    shift = _compute_best_transpose([], 48, 83)
    assert shift == 0


# ── _apply_transpose tests ────────────────────────────────


def test_apply_transpose_zero_creates_copies():
    """Zero transpose creates new BeatNote objects (immutability)."""
    from cyber_qin.core.smart_arrangement import _apply_transpose

    notes = [BeatNote(0.0, 1.0, 60, 100, 0)]
    result = _apply_transpose(notes, 0)
    assert result[0] is not notes[0]  # Different object
    assert result[0].note == 60


def test_apply_transpose_shifts_notes():
    """Positive/negative transpose shifts notes correctly."""
    from cyber_qin.core.smart_arrangement import _apply_transpose

    notes = [
        BeatNote(0.0, 1.0, 60, 100, 0),
        BeatNote(1.0, 1.0, 64, 100, 0),
    ]
    result = _apply_transpose(notes, 12)
    assert result[0].note == 72
    assert result[1].note == 76


def test_apply_transpose_clamps_to_midi_range():
    """Transpose clamps to MIDI 0-127."""
    from cyber_qin.core.smart_arrangement import _apply_transpose

    notes = [
        BeatNote(0.0, 1.0, 120, 100, 0),  # High note
        BeatNote(1.0, 1.0, 5, 100, 0),  # Low note
    ]
    result = _apply_transpose(notes, 12)
    assert result[0].note == 127  # Clamped to max

    result2 = _apply_transpose(notes, -10)
    assert result2[1].note == 0  # Clamped to min


def test_apply_transpose_preserves_other_fields():
    """Transpose preserves time, duration, velocity, track."""
    from cyber_qin.core.smart_arrangement import _apply_transpose

    notes = [BeatNote(2.5, 0.75, 60, 80, 3)]
    result = _apply_transpose(notes, 5)
    assert result[0].time_beats == 2.5
    assert result[0].duration_beats == 0.75
    assert result[0].velocity == 80
    assert result[0].track == 3


# ── _fold_into_range tests ────────────────────────────────


def test_fold_into_range_basic_octave_wrap():
    """Notes fold by octaves into range."""
    from cyber_qin.core.smart_arrangement import _fold_into_range

    notes = [
        BeatNote(0.0, 1.0, 96, 100, 0),  # C7 → should fold down to C5/C4
    ]
    folded, count = _fold_into_range(notes, 48, 83)
    assert 48 <= folded[0].note <= 83
    assert count == 1


def test_fold_into_range_notes_already_in_range():
    """Notes already in range are not modified."""
    from cyber_qin.core.smart_arrangement import _fold_into_range

    notes = [BeatNote(0.0, 1.0, 60, 100, 0)]
    folded, count = _fold_into_range(notes, 48, 83)
    assert folded[0].note == 60
    assert count == 0


def test_fold_into_range_narrow_range_clamps():
    """When range < 12 semitones, clamp to boundaries."""
    from cyber_qin.core.smart_arrangement import _fold_into_range

    notes = [
        BeatNote(0.0, 1.0, 50, 100, 0),  # Below range
        BeatNote(1.0, 1.0, 65, 100, 0),  # Above range
    ]
    # Range: 55-60 (only 5 semitones)
    folded, count = _fold_into_range(notes, 55, 60)
    assert 55 <= folded[0].note <= 60
    assert 55 <= folded[1].note <= 60
    assert count == 2


def test_fold_into_range_multiple_octaves_below():
    """Notes multiple octaves below fold up correctly."""
    from cyber_qin.core.smart_arrangement import _fold_into_range

    notes = [BeatNote(0.0, 1.0, 12, 100, 0)]  # C0
    folded, count = _fold_into_range(notes, 48, 83)
    # C0 = 12, fold up: 24, 36, 48
    assert folded[0].note == 48
    assert count == 1


def test_fold_into_range_multiple_octaves_above():
    """Notes multiple octaves above fold down correctly."""
    from cyber_qin.core.smart_arrangement import _fold_into_range

    notes = [BeatNote(0.0, 1.0, 108, 100, 0)]  # C8
    folded, count = _fold_into_range(notes, 48, 83)
    # C8 = 108, fold down: 96, 84, 72, 60, 48
    assert 48 <= folded[0].note <= 83
    assert count == 1


# ── _flowing_fold tests ────────────────────────────────────


def test_flowing_fold_voice_leading_small_intervals():
    """Flowing fold prefers small interval jumps."""
    from cyber_qin.core.smart_arrangement import _flowing_fold

    # Sequence that could fold to multiple octaves
    notes = [
        BeatNote(0.0, 1.0, 60, 100, 0),  # C4 (in range)
        BeatNote(1.0, 1.0, 96, 100, 0),  # C7 (could fold to C4, C5, or C6 within range)
    ]
    folded, _ = _flowing_fold(notes, 48, 83)
    # Second note should fold to octave closest to previous (C4=60)
    # C7=96 can fold to: 48, 60, 72
    # Closest to 60 is 60
    assert folded[1].note == 60 or folded[1].note == 72  # 72 is also close


def test_flowing_fold_preserves_in_range_notes():
    """Flowing fold keeps notes already in range unchanged."""
    from cyber_qin.core.smart_arrangement import _flowing_fold

    notes = [
        BeatNote(0.0, 1.0, 60, 100, 0),
        BeatNote(1.0, 1.0, 64, 100, 0),
        BeatNote(2.0, 1.0, 67, 100, 0),
    ]
    folded, count = _flowing_fold(notes, 48, 83)
    assert folded[0].note == 60
    assert folded[1].note == 64
    assert folded[2].note == 67
    assert count == 0


def test_flowing_fold_handles_no_valid_candidates():
    """Flowing fold handles edge case where no candidates exist in range."""
    from cyber_qin.core.smart_arrangement import _flowing_fold

    notes = [BeatNote(0.0, 1.0, 100, 100, 0)]
    # Very narrow range where C might not fit
    folded, _ = _flowing_fold(notes, 49, 50)
    assert 49 <= folded[0].note <= 50


def test_flowing_fold_tracks_previous_note():
    """Flowing fold uses previous note position for voice-leading."""
    from cyber_qin.core.smart_arrangement import _flowing_fold

    notes = [
        BeatNote(0.0, 1.0, 48, 100, 0),  # C3 (low in range)
        BeatNote(1.0, 1.0, 96, 100, 0),  # C7 (could fold to 48, 60, 72)
        BeatNote(2.0, 1.0, 100, 100, 0),  # E7
    ]
    folded, _ = _flowing_fold(notes, 48, 83)
    # First note stays at 48
    assert folded[0].note == 48
    # Second note should fold to 48 (closest to previous 48)
    assert folded[1].note == 48 or folded[1].note == 60


# ── _deduplicate tests ────────────────────────────────────


def test_deduplicate_removes_duplicates(notes_with_duplicates):
    """Deduplicate removes notes at same time/pitch/track."""
    from cyber_qin.core.smart_arrangement import _deduplicate

    result = _deduplicate(notes_with_duplicates)
    # Three duplicates at (0.0, 60, 0) → keep only one
    # One unique at (1.0, 64, 0)
    assert len(result) == 2


def test_deduplicate_keeps_highest_velocity(notes_with_duplicates):
    """Deduplicate keeps note with highest velocity."""
    from cyber_qin.core.smart_arrangement import _deduplicate

    result = _deduplicate(notes_with_duplicates)
    # Find the note at time 0, pitch 60
    note_60 = [n for n in result if n.time_beats == 0.0 and n.note == 60][0]
    assert note_60.velocity == 100  # Highest among 50, 100, 75


def test_deduplicate_preserves_different_tracks():
    """Deduplicate treats different tracks as distinct."""
    from cyber_qin.core.smart_arrangement import _deduplicate

    notes = [
        BeatNote(0.0, 1.0, 60, 100, 0),  # Track 0
        BeatNote(0.0, 1.0, 60, 100, 1),  # Track 1 (different track)
    ]
    result = _deduplicate(notes)
    assert len(result) == 2  # Both kept


def test_deduplicate_preserves_different_times():
    """Deduplicate treats different times as distinct."""
    from cyber_qin.core.smart_arrangement import _deduplicate

    notes = [
        BeatNote(0.0, 1.0, 60, 100, 0),
        BeatNote(0.5, 1.0, 60, 100, 0),  # Different time
    ]
    result = _deduplicate(notes)
    assert len(result) == 2


def test_deduplicate_empty_input():
    """Deduplicate handles empty input."""
    from cyber_qin.core.smart_arrangement import _deduplicate

    result = _deduplicate([])
    assert result == []


# ── _pick_strategy tests ────────────────────────────────


def test_pick_strategy_returns_global_transpose_for_high_in_range_ratio():
    """Pick strategy returns global_transpose when >80% notes in range after transpose."""
    from cyber_qin.core.smart_arrangement import _pick_strategy

    # Notes that are 90% in range after optimal transpose
    notes = [
        BeatNote(0.0, 1.0, 60, 100, 0),
        BeatNote(1.0, 1.0, 64, 100, 0),
        BeatNote(2.0, 1.0, 67, 100, 0),
        BeatNote(3.0, 1.0, 72, 100, 0),
        BeatNote(4.0, 1.0, 76, 100, 0),
        BeatNote(5.0, 1.0, 79, 100, 0),
        BeatNote(6.0, 1.0, 83, 100, 0),
        BeatNote(7.0, 1.0, 48, 100, 0),
        BeatNote(8.0, 1.0, 52, 100, 0),
        BeatNote(9.0, 1.0, 96, 100, 0),  # Only 1 out of 10 out of range
    ]
    strategy = _pick_strategy(notes, 48, 83)
    assert strategy == "global_transpose"


def test_pick_strategy_returns_hybrid_for_wide_span():
    """Pick strategy returns hybrid when span > 36 semitones."""
    from cyber_qin.core.smart_arrangement import _pick_strategy

    notes = [
        BeatNote(0.0, 1.0, 36, 100, 0),  # C2
        BeatNote(1.0, 1.0, 96, 100, 0),  # C7
    ]
    # Span = 96 - 36 = 60 semitones > 36
    strategy = _pick_strategy(notes, 48, 83)
    assert strategy == "hybrid"


def test_pick_strategy_returns_flowing_fold_for_moderate_distribution():
    """Pick strategy returns flowing_fold for moderate distributions."""
    from cyber_qin.core.smart_arrangement import _pick_strategy

    # To trigger flowing_fold, need:
    # 1. Span ≤ 36 (not hybrid)
    # 2. < 80% notes in range even after optimal transpose (not global_transpose)
    #
    # Strategy: Create notes at edges of different octaves such that
    # no single octave transpose can bring 80%+ into range 48-83.
    # Use 5 notes (need <4 in range, so max 3/5 = 60%)
    notes = [
        BeatNote(0.0, 1.0, 47, 100, 0),  # B2 - just below min (48)
        BeatNote(1.0, 1.0, 59, 100, 0),  # B3 - in range
        BeatNote(2.0, 1.0, 71, 100, 0),  # B4 - in range
        BeatNote(3.0, 1.0, 83, 100, 0),  # B5 - at max
        BeatNote(4.0, 1.0, 84, 100, 0),  # C6 - just above max
    ]
    # Span = 84 - 47 = 37 > 36 - triggers hybrid! Reduce by 1.
    notes = [
        BeatNote(0.0, 1.0, 47, 100, 0),  # B2 - just below min (48)
        BeatNote(1.0, 1.0, 59, 100, 0),  # B3 - in range
        BeatNote(2.0, 1.0, 71, 100, 0),  # B4 - in range
        BeatNote(3.0, 1.0, 83, 100, 0),  # B5 - at max (in range)
    ]
    # Span = 83 - 47 = 36 - EXACTLY 36, triggers hybrid (condition is span > 36, so 36 is OK)
    # Wait, the code says "if span > 36", so 36 should not trigger hybrid.
    # At shift 0: 3/4 = 75% < 80% ✓
    # At shift +12: [59, 71, 83, 95] → 95 out, so 3/4 = 75% < 80% ✓
    # At shift -12: [35, 47, 59, 71] → 35, 47 out, so 2/4 = 50%
    # Best is 75% at shift 0 or +12, which is < 80% ✓
    # Span = 36, not > 36, so not hybrid ✓
    # This should trigger flowing_fold!
    strategy = _pick_strategy(notes, 48, 83)
    assert strategy == "flowing_fold"


def test_pick_strategy_empty_returns_global_transpose():
    """Pick strategy returns global_transpose for empty input."""
    from cyber_qin.core.smart_arrangement import _pick_strategy

    strategy = _pick_strategy([], 48, 83)
    assert strategy == "global_transpose"


# ── arrange_beat_sequence alias tests ────────────────────


def test_arrange_beat_sequence_is_alias_for_smart_arrange(notes_in_range):
    """arrange_beat_sequence is identical to smart_arrange."""
    result1 = smart_arrange(notes_in_range)
    result2 = arrange_beat_sequence(notes_in_range)

    assert result1.transpose_semitones == result2.transpose_semitones
    assert result1.notes_folded == result2.notes_folded
    assert result1.strategy_used == result2.strategy_used
    assert len(result1.notes) == len(result2.notes)


# ── Custom range tests ────────────────────────────────────


def test_custom_note_min_and_max():
    """Custom note_min and note_max are respected."""
    notes = [
        BeatNote(0.0, 1.0, 40, 100, 0),
        BeatNote(1.0, 1.0, 60, 100, 0),
        BeatNote(2.0, 1.0, 80, 100, 0),
    ]
    # Custom range: 50-70
    result = smart_arrange(notes, note_min=50, note_max=70)
    for note in result.notes:
        assert 50 <= note.note <= 70


def test_very_narrow_custom_range():
    """Very narrow custom range (< 12 semitones) works."""
    notes = [
        BeatNote(0.0, 1.0, 40, 100, 0),
        BeatNote(1.0, 1.0, 60, 100, 0),
        BeatNote(2.0, 1.0, 80, 100, 0),
    ]
    # Range of only 5 semitones
    result = smart_arrange(notes, note_min=58, note_max=62)
    for note in result.notes:
        assert 58 <= note.note <= 62


def test_custom_range_one_octave():
    """Custom range of exactly one octave."""
    notes = [BeatNote(i, 1.0, 60 + i, 100, 0) for i in range(24)]
    result = smart_arrange(notes, note_min=60, note_max=71)
    for note in result.notes:
        assert 60 <= note.note <= 71


# ── Performance tests ────────────────────────────────────


def test_large_note_count_performance():
    """Large note count processes in reasonable time."""
    import time

    # Create 10,000 notes
    notes = [BeatNote(i * 0.1, 0.5, 48 + (i % 36), 100, i % 4) for i in range(10000)]

    start = time.time()
    result = smart_arrange(notes)
    elapsed = time.time() - start

    # Should complete in under 5 seconds (generous threshold)
    assert elapsed < 5.0
    assert len(result.notes) > 0


# ── Edge case tests ────────────────────────────────────────


def test_all_notes_same_pitch():
    """All notes at same pitch."""
    notes = [BeatNote(i * 1.0, 1.0, 60, 100, 0) for i in range(10)]
    result = smart_arrange(notes)
    assert all(n.note == 60 for n in result.notes)


def test_extreme_midi_values():
    """Notes at extreme MIDI boundaries (0, 127)."""
    notes = [
        BeatNote(0.0, 1.0, 0, 100, 0),
        BeatNote(1.0, 1.0, 127, 100, 0),
    ]
    result = smart_arrange(notes, note_min=48, note_max=83)
    # Should fold into range
    for note in result.notes:
        assert 48 <= note.note <= 83


def test_single_note():
    """Single note input."""
    notes = [BeatNote(0.0, 1.0, 96, 100, 0)]
    result = smart_arrange(notes, note_min=48, note_max=83)
    assert len(result.notes) == 1
    assert 48 <= result.notes[0].note <= 83


def test_notes_at_range_boundaries():
    """Notes exactly at range boundaries."""
    notes = [
        BeatNote(0.0, 1.0, 48, 100, 0),  # Min
        BeatNote(1.0, 1.0, 83, 100, 0),  # Max
    ]
    result = smart_arrange(notes, note_min=48, note_max=83)
    assert result.notes[0].note == 48
    assert result.notes[1].note == 83
    assert result.notes_folded == 0


def test_zero_duration_notes():
    """Notes with zero duration are preserved."""
    notes = [BeatNote(0.0, 0.0, 60, 100, 0)]
    result = smart_arrange(notes)
    assert result.notes[0].duration_beats == 0.0


def test_negative_time_beats():
    """Notes with negative time (edge case) are preserved."""
    notes = [BeatNote(-1.0, 1.0, 60, 100, 0)]
    result = smart_arrange(notes)
    assert result.notes[0].time_beats == -1.0


# ── Result object tests ────────────────────────────────────


def test_result_is_immutable():
    """ArrangementResult is frozen dataclass."""
    result = ArrangementResult([], 0, 0, "global_transpose")
    with pytest.raises(AttributeError):
        result.transpose_semitones = 12  # type: ignore


def test_result_notes_are_new_objects():
    """Result notes are new BeatNote objects (immutability)."""
    notes = [BeatNote(0.0, 1.0, 60, 100, 0)]
    result = smart_arrange(notes)
    assert result.notes[0] is not notes[0]


def test_result_contains_all_fields():
    """ArrangementResult contains all expected fields."""
    notes = [BeatNote(0.0, 1.0, 96, 100, 0)]
    result = smart_arrange(notes)
    assert hasattr(result, "notes")
    assert hasattr(result, "transpose_semitones")
    assert hasattr(result, "notes_folded")
    assert hasattr(result, "strategy_used")
    assert isinstance(result.notes, list)
    assert isinstance(result.transpose_semitones, int)
    assert isinstance(result.notes_folded, int)
    assert isinstance(result.strategy_used, str)
