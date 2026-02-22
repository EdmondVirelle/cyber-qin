"""Practice mode scoring engine.

Evaluates user MIDI input against a target sequence with configurable
timing windows.  Pure Python — no Qt dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, auto


class HitGrade(IntEnum):
    """Grading for a single note hit."""

    MISS = 0
    GOOD = auto()
    GREAT = auto()
    PERFECT = auto()


@dataclass(frozen=True, slots=True)
class PracticeNote:
    """A single note in the target practice sequence."""

    time_seconds: float
    note: int  # MIDI 0-127
    duration_seconds: float = 0.5


@dataclass(frozen=True, slots=True)
class HitResult:
    """Result of evaluating a single user input against a target note."""

    grade: HitGrade
    target_note: PracticeNote
    user_note: int
    timing_error_ms: float  # signed: negative = early, positive = late
    pitch_correct: bool


@dataclass
class PracticeStats:
    """Accumulated statistics for a practice session."""

    total_notes: int = 0
    perfect: int = 0
    great: int = 0
    good: int = 0
    missed: int = 0
    wrong_pitch: int = 0
    max_combo: int = 0
    current_combo: int = 0
    total_score: int = 0

    @property
    def accuracy(self) -> float:
        if self.total_notes == 0:
            return 0.0
        return (self.perfect + self.great + self.good) / self.total_notes

    @property
    def hit_count(self) -> int:
        return self.perfect + self.great + self.good

    def to_dict(self) -> dict:
        return {
            "total_notes": self.total_notes,
            "perfect": self.perfect,
            "great": self.great,
            "good": self.good,
            "missed": self.missed,
            "wrong_pitch": self.wrong_pitch,
            "max_combo": self.max_combo,
            "total_score": self.total_score,
            "accuracy": self.accuracy,
        }


# ── Timing Windows (in milliseconds) ─────────────────────

DEFAULT_PERFECT_MS = 30.0
DEFAULT_GREAT_MS = 80.0
DEFAULT_GOOD_MS = 150.0


@dataclass
class TimingWindows:
    """Configurable timing windows for hit grading."""

    perfect_ms: float = DEFAULT_PERFECT_MS
    great_ms: float = DEFAULT_GREAT_MS
    good_ms: float = DEFAULT_GOOD_MS


# ── Score Values ──────────────────────────────────────────

SCORE_PERFECT = 300
SCORE_GREAT = 200
SCORE_GOOD = 100
SCORE_MISS = 0


# ── Practice Scorer ───────────────────────────────────────


class PracticeScorer:
    """Stateful scorer for a practice session.

    Usage::

        scorer = PracticeScorer(target_notes)
        scorer.start()

        # On each MIDI input event:
        result = scorer.on_user_note(midi_note, current_time_seconds)
        if result is not None:
            # Display feedback
            ...

        # End of session:
        stats = scorer.stats
    """

    def __init__(
        self,
        target: list[PracticeNote],
        windows: TimingWindows | None = None,
    ) -> None:
        self._target = sorted(target, key=lambda n: n.time_seconds)
        self._windows = windows or TimingWindows()
        self._stats = PracticeStats(total_notes=len(self._target))
        self._next_idx = 0  # index of next unmatched target note
        self._matched: set[int] = set()  # indices already matched
        self._started = False

    @property
    def stats(self) -> PracticeStats:
        return self._stats

    @property
    def is_complete(self) -> bool:
        return self._next_idx >= len(self._target)

    @property
    def progress(self) -> float:
        """0.0 – 1.0 progress through the target sequence."""
        if not self._target:
            return 1.0
        return min(1.0, self._next_idx / len(self._target))

    def start(self) -> None:
        """Reset and start a new session."""
        self._stats = PracticeStats(total_notes=len(self._target))
        self._next_idx = 0
        self._matched.clear()
        self._started = True

    def on_user_note(self, midi_note: int, current_time: float) -> HitResult | None:
        """Evaluate a user note-on event against the target sequence.

        Returns ``None`` if no target note is close enough to evaluate.
        """
        if not self._started or not self._target:
            return None

        # Advance past notes that are too far in the past
        good_sec = self._windows.good_ms / 1000.0
        while self._next_idx < len(self._target):
            target = self._target[self._next_idx]
            if current_time - target.time_seconds > good_sec:
                # Missed this note
                if self._next_idx not in self._matched:
                    self._stats.missed += 1
                    self._stats.current_combo = 0
                self._next_idx += 1
            else:
                break

        if self._next_idx >= len(self._target):
            return None

        # Search nearby target notes for the best match
        best_result: HitResult | None = None
        best_abs_error = float("inf")

        search_start = max(0, self._next_idx - 1)
        search_end = min(len(self._target), self._next_idx + 3)

        for i in range(search_start, search_end):
            if i in self._matched:
                continue
            target = self._target[i]
            error_sec = current_time - target.time_seconds
            error_ms = error_sec * 1000.0
            abs_error = abs(error_ms)

            if abs_error > self._windows.good_ms:
                continue

            pitch_correct = midi_note == target.note

            # Grade based on timing
            if abs_error <= self._windows.perfect_ms:
                grade = HitGrade.PERFECT
            elif abs_error <= self._windows.great_ms:
                grade = HitGrade.GREAT
            elif abs_error <= self._windows.good_ms:
                grade = HitGrade.GOOD
            else:
                continue

            # Wrong pitch downgrades
            if not pitch_correct:
                grade = HitGrade.GOOD  # cap at GOOD for wrong pitch

            result = HitResult(grade, target, midi_note, error_ms, pitch_correct)
            if abs_error < best_abs_error:
                best_abs_error = abs_error
                best_result = result
                best_idx = i

        if best_result is None:
            return None

        # Record the match
        self._matched.add(best_idx)
        if best_idx == self._next_idx:
            # Advance past matched and any already-matched notes
            while self._next_idx < len(self._target) and self._next_idx in self._matched:
                self._next_idx += 1

        # Update stats
        if best_result.grade == HitGrade.PERFECT:
            self._stats.perfect += 1
            self._stats.total_score += SCORE_PERFECT
        elif best_result.grade == HitGrade.GREAT:
            self._stats.great += 1
            self._stats.total_score += SCORE_GREAT
        elif best_result.grade == HitGrade.GOOD:
            self._stats.good += 1
            self._stats.total_score += SCORE_GOOD

        if not best_result.pitch_correct:
            self._stats.wrong_pitch += 1

        # Combo
        if best_result.grade != HitGrade.MISS:
            self._stats.current_combo += 1
            if self._stats.current_combo > self._stats.max_combo:
                self._stats.max_combo = self._stats.current_combo
        else:
            self._stats.current_combo = 0

        return best_result

    def finalize(self) -> PracticeStats:
        """Mark all remaining unmatched notes as missed and return final stats."""
        for i in range(self._next_idx, len(self._target)):
            if i not in self._matched:
                self._stats.missed += 1
        self._next_idx = len(self._target)
        self._stats.current_combo = 0
        return self._stats


def notes_to_practice(
    beat_notes: list,
    tempo_bpm: float = 120.0,
) -> list[PracticeNote]:
    """Convert BeatNote list to PracticeNote list for the practice engine."""
    sec_per_beat = 60.0 / tempo_bpm
    return [
        PracticeNote(
            time_seconds=n.time_beats * sec_per_beat,
            note=n.note,
            duration_seconds=n.duration_beats * sec_per_beat,
        )
        for n in beat_notes
    ]
