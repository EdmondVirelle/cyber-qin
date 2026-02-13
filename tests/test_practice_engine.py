"""Tests for practice_engine module.

Covers HitGrade, PracticeNote, HitResult, PracticeStats, TimingWindows,
PracticeScorer, and notes_to_practice conversion function.
"""

from __future__ import annotations

import pytest

from cyber_qin.core.beat_sequence import BeatNote
from cyber_qin.core.practice_engine import (
    DEFAULT_GOOD_MS,
    DEFAULT_GREAT_MS,
    DEFAULT_PERFECT_MS,
    SCORE_GOOD,
    SCORE_GREAT,
    SCORE_PERFECT,
    HitGrade,
    HitResult,
    PracticeNote,
    PracticeScorer,
    PracticeStats,
    TimingWindows,
    notes_to_practice,
)

# ── HitGrade Enum Tests ──────────────────────────────────────


def test_hitgrade_ordering():
    """Grade ordering: MISS < GOOD < GREAT < PERFECT."""
    assert HitGrade.MISS < HitGrade.GOOD
    assert HitGrade.GOOD < HitGrade.GREAT
    assert HitGrade.GREAT < HitGrade.PERFECT


def test_hitgrade_all_values_distinct():
    """All values are distinct."""
    values = [HitGrade.MISS, HitGrade.GOOD, HitGrade.GREAT, HitGrade.PERFECT]
    assert len(set(values)) == 4


def test_hitgrade_intenum_comparison():
    """IntEnum comparison works."""
    assert HitGrade.PERFECT == 3
    assert HitGrade.MISS == 0
    assert HitGrade.GOOD > 0


# ── PracticeNote Tests ───────────────────────────────────────


def test_practicenote_basic_creation():
    """Basic creation with defaults."""
    note = PracticeNote(time_seconds=1.0, note=60)
    assert note.time_seconds == 1.0
    assert note.note == 60
    assert note.duration_seconds == 0.5  # default


def test_practicenote_custom_duration():
    """Custom duration."""
    note = PracticeNote(time_seconds=2.0, note=64, duration_seconds=1.5)
    assert note.duration_seconds == 1.5


def test_practicenote_frozen():
    """Frozen (immutable)."""
    note = PracticeNote(time_seconds=1.0, note=60)
    with pytest.raises(Exception):  # FrozenInstanceError
        note.note = 61  # type: ignore


# ── HitResult Tests ──────────────────────────────────────────


def test_hitresult_basic_creation():
    """Basic creation."""
    target = PracticeNote(time_seconds=1.0, note=60)
    result = HitResult(
        grade=HitGrade.PERFECT,
        target_note=target,
        user_note=60,
        timing_error_ms=-5.0,
        pitch_correct=True,
    )
    assert result.grade == HitGrade.PERFECT
    assert result.target_note == target
    assert result.user_note == 60


def test_hitresult_pitch_correct_flag():
    """pitch_correct flag."""
    target = PracticeNote(time_seconds=1.0, note=60)
    result = HitResult(
        grade=HitGrade.GOOD,
        target_note=target,
        user_note=62,
        timing_error_ms=0.0,
        pitch_correct=False,
    )
    assert result.pitch_correct is False


def test_hitresult_timing_error_sign_convention():
    """Timing error sign convention (negative=early, positive=late)."""
    target = PracticeNote(time_seconds=1.0, note=60)

    # Early hit (user time < target time) → negative error
    early = HitResult(
        grade=HitGrade.PERFECT,
        target_note=target,
        user_note=60,
        timing_error_ms=-10.0,
        pitch_correct=True,
    )
    assert early.timing_error_ms < 0

    # Late hit (user time > target time) → positive error
    late = HitResult(
        grade=HitGrade.GREAT,
        target_note=target,
        user_note=60,
        timing_error_ms=20.0,
        pitch_correct=True,
    )
    assert late.timing_error_ms > 0


# ── PracticeStats Tests ──────────────────────────────────────


def test_practicestats_default_values():
    """Default values all zero."""
    stats = PracticeStats()
    assert stats.total_notes == 0
    assert stats.perfect == 0
    assert stats.great == 0
    assert stats.good == 0
    assert stats.missed == 0
    assert stats.wrong_pitch == 0
    assert stats.max_combo == 0
    assert stats.current_combo == 0
    assert stats.total_score == 0


def test_practicestats_accuracy_zero_when_total_zero():
    """accuracy = 0 when total_notes=0."""
    stats = PracticeStats(total_notes=0)
    assert stats.accuracy == 0.0


def test_practicestats_accuracy_calculation():
    """accuracy calculation: (perfect+great+good)/total."""
    stats = PracticeStats(
        total_notes=10,
        perfect=3,
        great=2,
        good=1,
        missed=4,
    )
    expected = (3 + 2 + 1) / 10
    assert stats.accuracy == pytest.approx(expected)


def test_practicestats_hit_count():
    """hit_count = perfect+great+good."""
    stats = PracticeStats(
        perfect=5,
        great=3,
        good=2,
        missed=1,
    )
    assert stats.hit_count == 10


def test_practicestats_to_dict_includes_all_fields():
    """to_dict includes all fields."""
    stats = PracticeStats(
        total_notes=10,
        perfect=3,
        great=2,
        good=1,
        missed=4,
        wrong_pitch=1,
        max_combo=5,
        total_score=1400,
    )
    d = stats.to_dict()
    assert d["total_notes"] == 10
    assert d["perfect"] == 3
    assert d["great"] == 2
    assert d["good"] == 1
    assert d["missed"] == 4
    assert d["wrong_pitch"] == 1
    assert d["max_combo"] == 5
    assert d["total_score"] == 1400
    assert "accuracy" in d


def test_practicestats_max_combo_tracking():
    """max_combo tracking."""
    stats = PracticeStats(max_combo=10, current_combo=5)
    assert stats.max_combo == 10
    assert stats.current_combo == 5


def test_practicestats_accuracy_partial():
    """accuracy with partial hits."""
    stats = PracticeStats(total_notes=5, perfect=2, great=1, good=0, missed=2)
    assert stats.accuracy == pytest.approx(0.6)


def test_practicestats_accuracy_full_perfect():
    """accuracy with all perfect."""
    stats = PracticeStats(total_notes=5, perfect=5)
    assert stats.accuracy == 1.0


# ── TimingWindows Tests ──────────────────────────────────────


def test_timingwindows_default_values():
    """Default values: perfect=30, great=80, good=150."""
    windows = TimingWindows()
    assert windows.perfect_ms == DEFAULT_PERFECT_MS
    assert windows.great_ms == DEFAULT_GREAT_MS
    assert windows.good_ms == DEFAULT_GOOD_MS
    assert windows.perfect_ms == 30.0
    assert windows.great_ms == 80.0
    assert windows.good_ms == 150.0


def test_timingwindows_custom_values():
    """Custom values."""
    windows = TimingWindows(perfect_ms=20.0, great_ms=60.0, good_ms=120.0)
    assert windows.perfect_ms == 20.0
    assert windows.great_ms == 60.0
    assert windows.good_ms == 120.0


def test_timingwindows_can_be_modified():
    """Custom values can be set."""
    windows = TimingWindows()
    windows.perfect_ms = 25.0
    assert windows.perfect_ms == 25.0


# ── PracticeScorer Tests ─────────────────────────────────────


def test_scorer_empty_target_is_complete_immediately():
    """Empty target → is_complete immediately."""
    scorer = PracticeScorer(target=[])
    assert scorer.is_complete


def test_scorer_single_note_perfect_timing():
    """Single note, perfect timing → PERFECT grade."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    result = scorer.on_user_note(60, 1.0)

    assert result is not None
    assert result.grade == HitGrade.PERFECT
    assert result.pitch_correct is True
    assert result.timing_error_ms == pytest.approx(0.0)


def test_scorer_single_note_50ms_late_great():
    """Single note, 50ms late → GREAT grade."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    result = scorer.on_user_note(60, 1.05)  # 50ms late

    assert result is not None
    assert result.grade == HitGrade.GREAT
    assert result.timing_error_ms == pytest.approx(50.0)


def test_scorer_single_note_100ms_late_good():
    """Single note, 100ms late → GOOD grade."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    result = scorer.on_user_note(60, 1.1)  # 100ms late

    assert result is not None
    assert result.grade == HitGrade.GOOD
    assert result.timing_error_ms == pytest.approx(100.0)


def test_scorer_single_note_200ms_late_miss():
    """Single note, 200ms late → MISS (no result)."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    result = scorer.on_user_note(60, 1.2)  # 200ms late (outside good window)

    # Should auto-advance past the missed note and return None
    assert result is None


def test_scorer_single_note_20ms_early_perfect():
    """Single note, 20ms early → PERFECT."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    result = scorer.on_user_note(60, 0.98)  # 20ms early

    assert result is not None
    assert result.grade == HitGrade.PERFECT
    assert result.timing_error_ms == pytest.approx(-20.0)


def test_scorer_wrong_pitch_caps_at_good():
    """Wrong pitch → caps at GOOD."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    result = scorer.on_user_note(62, 1.0)  # Wrong note, perfect timing

    assert result is not None
    assert result.grade == HitGrade.GOOD
    assert result.pitch_correct is False


def test_scorer_wrong_pitch_with_perfect_timing_good():
    """Wrong pitch with perfect timing → GOOD."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    result = scorer.on_user_note(61, 1.0)

    assert result is not None
    assert result.grade == HitGrade.GOOD


def test_scorer_correct_pitch_tracking():
    """Correct pitch tracking in result."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    correct = scorer.on_user_note(60, 1.0)
    assert correct is not None
    assert correct.pitch_correct is True

    scorer.start()  # Reset
    wrong = scorer.on_user_note(61, 1.0)
    assert wrong is not None
    assert wrong.pitch_correct is False


def test_scorer_timing_error_negative_when_early():
    """timing_error_ms is negative when early."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    result = scorer.on_user_note(60, 0.95)  # 50ms early

    assert result is not None
    assert result.timing_error_ms < 0
    assert result.timing_error_ms == pytest.approx(-50.0)


def test_scorer_timing_error_positive_when_late():
    """timing_error_ms is positive when late."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    result = scorer.on_user_note(60, 1.03)  # 30ms late

    assert result is not None
    assert result.timing_error_ms > 0
    assert result.timing_error_ms == pytest.approx(30.0)


def test_scorer_score_accumulation():
    """Score accumulation: PERFECT=300, GREAT=200, GOOD=100."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
        PracticeNote(time_seconds=3.0, note=64),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.0)  # PERFECT
    scorer.on_user_note(62, 2.05)  # GREAT (50ms late)
    scorer.on_user_note(64, 3.1)  # GOOD (100ms late)

    assert scorer.stats.total_score == SCORE_PERFECT + SCORE_GREAT + SCORE_GOOD


def test_scorer_combo_increases_on_hits():
    """Combo increases on hits."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.0)
    assert scorer.stats.current_combo == 1

    scorer.on_user_note(62, 2.0)
    assert scorer.stats.current_combo == 2


def test_scorer_combo_resets_on_miss():
    """Combo resets on miss."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.0)
    assert scorer.stats.current_combo == 1

    # Miss the second note by being too late
    scorer.on_user_note(62, 2.5)  # Far too late
    # Current combo should be reset when we advance past the missed note
    assert scorer.stats.current_combo == 0


def test_scorer_max_combo_tracks_highest_streak():
    """max_combo tracks highest streak."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
        PracticeNote(time_seconds=3.0, note=64),
        PracticeNote(time_seconds=5.0, note=65),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.0)
    scorer.on_user_note(62, 2.0)
    assert scorer.stats.max_combo == 2

    # Miss third note
    scorer.on_user_note(64, 4.0)  # Too late
    assert scorer.stats.current_combo == 0

    # Hit fourth note
    scorer.on_user_note(65, 5.0)
    assert scorer.stats.current_combo == 1
    assert scorer.stats.max_combo == 2  # Still the highest


def test_scorer_progress_advances():
    """progress 0→1 as notes are hit."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    assert scorer.progress == 0.0

    scorer.on_user_note(60, 1.0)
    assert scorer.progress == pytest.approx(0.5)

    scorer.on_user_note(62, 2.0)
    assert scorer.progress == 1.0


def test_scorer_multiple_notes_in_sequence():
    """Multiple notes in sequence."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
        PracticeNote(time_seconds=3.0, note=64),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    r1 = scorer.on_user_note(60, 1.0)
    r2 = scorer.on_user_note(62, 2.0)
    r3 = scorer.on_user_note(64, 3.0)

    assert r1 is not None
    assert r2 is not None
    assert r3 is not None
    assert scorer.stats.perfect == 3


def test_scorer_notes_auto_advance_past_missed():
    """Notes auto-advance past missed ones."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    # Miss first note, hit second
    result = scorer.on_user_note(62, 2.0)

    assert result is not None
    assert result.target_note.note == 62
    assert scorer.stats.missed == 1


def test_scorer_finalize_marks_remaining_as_missed():
    """finalize marks remaining as missed."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
        PracticeNote(time_seconds=3.0, note=64),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.0)  # Hit first

    stats = scorer.finalize()

    assert stats.perfect == 1
    assert stats.missed == 2  # Two remaining notes marked as missed


def test_scorer_start_resets_all_state():
    """start() resets all state."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.0)
    assert scorer.stats.perfect == 1

    scorer.start()  # Reset
    assert scorer.stats.perfect == 0
    assert scorer.stats.total_notes == 1
    assert scorer.progress == 0.0


def test_scorer_custom_timing_windows_wider():
    """Custom timing windows (wider)."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    windows = TimingWindows(perfect_ms=50.0, great_ms=100.0, good_ms=200.0)
    scorer = PracticeScorer(target, windows=windows)
    scorer.start()

    # 60ms late should be GREAT with custom windows (would be GOOD with default)
    result = scorer.on_user_note(60, 1.06)

    assert result is not None
    assert result.grade == HitGrade.GREAT


def test_scorer_custom_timing_windows_tighter():
    """Custom timing windows (tighter)."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    windows = TimingWindows(perfect_ms=10.0, great_ms=30.0, good_ms=60.0)
    scorer = PracticeScorer(target, windows=windows)
    scorer.start()

    # 25ms late should be GREAT with tight windows (would be PERFECT with default)
    result = scorer.on_user_note(60, 1.025)

    assert result is not None
    assert result.grade == HitGrade.GREAT


def test_scorer_notes_out_of_order_match_nearest():
    """Notes out of order still match nearest."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    # Hit second note first (within timing window)
    result = scorer.on_user_note(62, 1.95)

    assert result is not None
    assert result.target_note.note == 62


def test_scorer_duplicate_user_inputs_dont_double_count():
    """Duplicate user inputs don't double-count."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    r1 = scorer.on_user_note(60, 1.0)
    r2 = scorer.on_user_note(60, 1.01)  # Same note again

    assert r1 is not None
    assert r2 is None  # Already matched


def test_scorer_very_fast_sequence():
    """Very fast sequence of notes."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=1.1, note=62),
        PracticeNote(time_seconds=1.2, note=64),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.0)
    scorer.on_user_note(62, 1.1)
    scorer.on_user_note(64, 1.2)

    assert scorer.stats.perfect == 3


def test_scorer_is_complete_after_all_matched():
    """is_complete after all notes matched."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    assert not scorer.is_complete

    scorer.on_user_note(60, 1.0)
    assert not scorer.is_complete

    scorer.on_user_note(62, 2.0)
    assert scorer.is_complete


def test_scorer_stats_accuracy_after_full_session():
    """Stats accuracy after full session."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
        PracticeNote(time_seconds=3.0, note=64),
        PracticeNote(time_seconds=4.0, note=65),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.0)  # PERFECT
    scorer.on_user_note(62, 2.05)  # GREAT
    scorer.on_user_note(64, 3.1)  # GOOD
    # Miss last note

    stats = scorer.finalize()

    assert stats.perfect == 1
    assert stats.great == 1
    assert stats.good == 1
    assert stats.missed == 1
    assert stats.accuracy == pytest.approx(0.75)


def test_scorer_on_user_note_no_target_nearby():
    """on_user_note returns None when no target nearby."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    # Input far away from any target
    result = scorer.on_user_note(60, 5.0)

    assert result is None


def test_scorer_on_user_note_before_start():
    """on_user_note before start returns None."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)

    result = scorer.on_user_note(60, 1.0)

    assert result is None


def test_scorer_multiple_start_calls_reset_properly():
    """Multiple calls to start reset properly."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)

    scorer.start()
    scorer.on_user_note(60, 1.0)
    assert scorer.stats.perfect == 1

    scorer.start()
    assert scorer.stats.perfect == 0
    assert not scorer.is_complete

    scorer.start()
    scorer.on_user_note(60, 1.0)
    assert scorer.stats.perfect == 1


def test_scorer_finalize_resets_current_combo():
    """finalize resets current_combo."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.0)
    assert scorer.stats.current_combo == 1

    scorer.finalize()
    assert scorer.stats.current_combo == 0


def test_scorer_finalize_sets_is_complete():
    """finalize sets is_complete."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    assert not scorer.is_complete

    scorer.finalize()
    assert scorer.is_complete


def test_scorer_progress_empty_sequence():
    """progress returns 1.0 for empty sequence."""
    scorer = PracticeScorer(target=[])
    assert scorer.progress == 1.0


def test_scorer_wrong_pitch_increments_wrong_pitch_count():
    """Wrong pitch increments wrong_pitch count."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(62, 1.0)  # Wrong note

    assert scorer.stats.wrong_pitch == 1


def test_scorer_correct_pitch_does_not_increment_wrong_pitch():
    """Correct pitch does not increment wrong_pitch."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.0)

    assert scorer.stats.wrong_pitch == 0


def test_scorer_combo_continues_on_good_grade():
    """Combo continues on GOOD grade."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.1)  # GOOD
    assert scorer.stats.current_combo == 1

    scorer.on_user_note(62, 2.0)  # PERFECT
    assert scorer.stats.current_combo == 2


def test_scorer_stats_total_notes_preserved():
    """Stats total_notes is preserved from target length."""
    target = [
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
        PracticeNote(time_seconds=3.0, note=64),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    assert scorer.stats.total_notes == 3

    scorer.on_user_note(60, 1.0)
    assert scorer.stats.total_notes == 3


def test_scorer_progress_caps_at_one():
    """progress caps at 1.0."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    scorer.on_user_note(60, 1.0)
    assert scorer.progress == 1.0

    # Additional inputs don't push progress beyond 1.0
    scorer.on_user_note(62, 2.0)
    assert scorer.progress == 1.0


# ── notes_to_practice Tests ──────────────────────────────────


def test_notes_to_practice_converts_beatnote_correctly():
    """Converts BeatNote to PracticeNote correctly."""
    beat_notes = [BeatNote(time_beats=2.0, duration_beats=1.0, note=60)]

    practice_notes = notes_to_practice(beat_notes, tempo_bpm=120.0)

    assert len(practice_notes) == 1
    assert practice_notes[0].note == 60


def test_notes_to_practice_time_conversion_with_different_tempos():
    """Time conversion with different tempos."""
    beat_notes = [BeatNote(time_beats=4.0, duration_beats=1.0, note=60)]

    # At 120 BPM: 1 beat = 0.5 seconds
    practice_120 = notes_to_practice(beat_notes, tempo_bpm=120.0)
    assert practice_120[0].time_seconds == pytest.approx(2.0)

    # At 60 BPM: 1 beat = 1.0 second
    practice_60 = notes_to_practice(beat_notes, tempo_bpm=60.0)
    assert practice_60[0].time_seconds == pytest.approx(4.0)


def test_notes_to_practice_duration_conversion():
    """Duration conversion."""
    beat_notes = [BeatNote(time_beats=2.0, duration_beats=2.0, note=60)]

    # At 120 BPM: 1 beat = 0.5 seconds, so 2 beats = 1.0 seconds
    practice_notes = notes_to_practice(beat_notes, tempo_bpm=120.0)

    assert practice_notes[0].duration_seconds == pytest.approx(1.0)


def test_notes_to_practice_empty_list():
    """Empty list returns empty."""
    practice_notes = notes_to_practice([], tempo_bpm=120.0)
    assert practice_notes == []


def test_notes_to_practice_multiple_notes():
    """Multiple notes."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=1.0, note=60),
        BeatNote(time_beats=2.0, duration_beats=0.5, note=62),
        BeatNote(time_beats=4.0, duration_beats=2.0, note=64),
    ]

    practice_notes = notes_to_practice(beat_notes, tempo_bpm=120.0)

    assert len(practice_notes) == 3
    assert practice_notes[0].time_seconds == pytest.approx(0.0)
    assert practice_notes[1].time_seconds == pytest.approx(1.0)
    assert practice_notes[2].time_seconds == pytest.approx(2.0)
    assert practice_notes[0].duration_seconds == pytest.approx(0.5)
    assert practice_notes[1].duration_seconds == pytest.approx(0.25)
    assert practice_notes[2].duration_seconds == pytest.approx(1.0)


def test_notes_to_practice_default_tempo():
    """Default tempo is 120 BPM."""
    beat_notes = [BeatNote(time_beats=2.0, duration_beats=1.0, note=60)]

    # Should default to 120 BPM
    practice_notes = notes_to_practice(beat_notes)

    assert practice_notes[0].time_seconds == pytest.approx(1.0)


def test_scorer_edge_case_exact_good_window_boundary():
    """Note at exact good window boundary."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    windows = TimingWindows(perfect_ms=30.0, great_ms=80.0, good_ms=150.0)
    scorer = PracticeScorer(target, windows=windows)
    scorer.start()

    # Exactly at good window (150ms late)
    result = scorer.on_user_note(60, 1.15)

    assert result is not None
    assert result.grade == HitGrade.GOOD


def test_scorer_edge_case_just_outside_good_window():
    """Note just outside good window is missed."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    windows = TimingWindows(perfect_ms=30.0, great_ms=80.0, good_ms=150.0)
    scorer = PracticeScorer(target, windows=windows)
    scorer.start()

    # Just outside good window (151ms late)
    result = scorer.on_user_note(60, 1.151)

    # Should auto-advance and return None
    assert result is None


def test_scorer_finalize_returns_stats():
    """finalize returns final stats."""
    target = [PracticeNote(time_seconds=1.0, note=60)]
    scorer = PracticeScorer(target)
    scorer.start()

    stats = scorer.finalize()

    assert isinstance(stats, PracticeStats)
    assert stats.total_notes == 1
    assert stats.missed == 1


def test_scorer_target_sorted_by_time():
    """Target notes are sorted by time internally."""
    target = [
        PracticeNote(time_seconds=3.0, note=64),
        PracticeNote(time_seconds=1.0, note=60),
        PracticeNote(time_seconds=2.0, note=62),
    ]
    scorer = PracticeScorer(target)
    scorer.start()

    # Should match in sorted order
    r1 = scorer.on_user_note(60, 1.0)
    r2 = scorer.on_user_note(62, 2.0)
    r3 = scorer.on_user_note(64, 3.0)

    assert r1 is not None
    assert r2 is not None
    assert r3 is not None
    assert scorer.stats.perfect == 3
