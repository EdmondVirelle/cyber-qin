"""Smart arrangement — auto-transpose and fold notes into playable range.

Builds on existing preprocessor functions to provide a high-level API for
the editor view.  Operates on ``BeatNote`` lists (beat-based) rather than
``MidiFileEvent`` lists (seconds-based) so it can be applied directly to
the editor sequence.
"""

from __future__ import annotations

from dataclasses import dataclass

from .beat_sequence import BeatNote
from .constants import PLAYABLE_MIDI_MAX, PLAYABLE_MIDI_MIN

# ── Result ────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ArrangementResult:
    """Outcome of a smart arrangement operation."""

    notes: list[BeatNote]
    transpose_semitones: int
    notes_folded: int
    strategy_used: str  # "global_transpose", "flowing_fold", "hybrid"


# ── Helpers ───────────────────────────────────────────────


def _count_in_range(notes: list[BeatNote], lo: int, hi: int) -> int:
    return sum(1 for n in notes if lo <= n.note <= hi)


def _compute_best_transpose(
    notes: list[BeatNote],
    note_min: int,
    note_max: int,
) -> int:
    """Find the best global transpose (multiple of 12) to maximise in-range notes."""
    if not notes:
        return 0

    pitches = [n.note for n in notes]
    best_shift = 0
    best_in_range = sum(1 for p in pitches if note_min <= p <= note_max)

    for shift in range(-48, 49, 12):
        if shift == 0:
            continue
        in_range = sum(1 for p in pitches if note_min <= p + shift <= note_max)
        if in_range > best_in_range or (
            in_range == best_in_range and abs(shift) < abs(best_shift)
        ):
            best_in_range = in_range
            best_shift = shift

    return best_shift


def _apply_transpose(notes: list[BeatNote], semitones: int) -> list[BeatNote]:
    if semitones == 0:
        return [BeatNote(n.time_beats, n.duration_beats, n.note, n.velocity, n.track) for n in notes]
    return [
        BeatNote(n.time_beats, n.duration_beats, max(0, min(127, n.note + semitones)), n.velocity, n.track)
        for n in notes
    ]


def _fold_into_range(
    notes: list[BeatNote],
    note_min: int,
    note_max: int,
) -> tuple[list[BeatNote], int]:
    """Fold notes into [note_min, note_max] by octave shifts.

    Returns (folded_notes, count_folded).
    """
    result: list[BeatNote] = []
    folded = 0
    for n in notes:
        pitch = n.note
        if pitch < note_min or pitch > note_max:
            orig = pitch
            while pitch > note_max:
                pitch -= 12
            while pitch < note_min:
                pitch += 12
            # If still out of range (range < 12 semitones), clamp
            pitch = max(note_min, min(note_max, pitch))
            if pitch != orig:
                folded += 1
        result.append(BeatNote(n.time_beats, n.duration_beats, pitch, n.velocity, n.track))
    return result, folded


def _flowing_fold(
    notes: list[BeatNote],
    note_min: int,
    note_max: int,
) -> tuple[list[BeatNote], int]:
    """Voice-leading aware fold — picks octave position that minimises jumps."""
    mid = (note_min + note_max) / 2.0
    prev_note: float = mid
    folded_count = 0
    result: list[BeatNote] = []

    for n in notes:
        if note_min <= n.note <= note_max:
            result.append(BeatNote(n.time_beats, n.duration_beats, n.note, n.velocity, n.track))
            prev_note = float(n.note)
            continue

        # Generate octave candidates
        pc = n.note % 12
        candidates: list[int] = []
        base = note_min + ((pc - note_min % 12) % 12)
        c = base
        while c <= note_max:
            candidates.append(c)
            c += 12

        if not candidates:
            # Fallback: simple fold
            pitch = n.note
            while pitch > note_max:
                pitch -= 12
            while pitch < note_min:
                pitch += 12
            candidates = [max(note_min, min(note_max, pitch))]

        # Pick candidate closest to previous note (voice-leading)
        chosen = min(candidates, key=lambda c: abs(c - prev_note))
        folded_count += 1
        prev_note = float(chosen)
        result.append(BeatNote(n.time_beats, n.duration_beats, chosen, n.velocity, n.track))

    return result, folded_count


def _deduplicate(notes: list[BeatNote]) -> list[BeatNote]:
    """Remove duplicate notes at the same (time, pitch, track), keep highest velocity."""
    seen: dict[tuple[float, int, int], int] = {}  # (time, note, track) → index of best
    for i, n in enumerate(notes):
        key = (n.time_beats, n.note, n.track)
        if key not in seen or notes[seen[key]].velocity < n.velocity:
            seen[key] = i
    keep = set(seen.values())
    return [n for i, n in enumerate(notes) if i in keep]


# ── Strategy Selection ────────────────────────────────────


def _pick_strategy(
    notes: list[BeatNote],
    note_min: int,
    note_max: int,
) -> str:
    """Choose arrangement strategy based on note distribution."""
    if not notes:
        return "global_transpose"

    # After optimal transpose, how many are already in range?
    shift = _compute_best_transpose(notes, note_min, note_max)
    shifted = [n.note + shift for n in notes]
    in_range = sum(1 for p in shifted if note_min <= p <= note_max)
    ratio = in_range / len(notes) if notes else 0

    if ratio >= 0.80:
        return "global_transpose"

    # Check if range spans more than 2 octaves
    lo = min(n.note for n in notes)
    hi = max(n.note for n in notes)
    span = hi - lo
    if span > 36:
        return "hybrid"

    return "flowing_fold"


# ── Public API ────────────────────────────────────────────


def smart_arrange(
    notes: list[BeatNote],
    *,
    note_min: int = PLAYABLE_MIDI_MIN,
    note_max: int = PLAYABLE_MIDI_MAX,
    strategy: str = "auto",
) -> ArrangementResult:
    """Arrange notes into the playable range using the best strategy.

    Parameters
    ----------
    notes : list[BeatNote]
        Input notes (not mutated).
    note_min, note_max : int
        Target MIDI range.
    strategy : str
        ``"auto"`` (default), ``"global_transpose"``, ``"flowing_fold"``,
        or ``"hybrid"``.

    Returns
    -------
    ArrangementResult
    """
    if not notes:
        return ArrangementResult([], 0, 0, strategy if strategy != "auto" else "global_transpose")

    if strategy == "auto":
        strategy = _pick_strategy(notes, note_min, note_max)

    if strategy == "global_transpose":
        shift = _compute_best_transpose(notes, note_min, note_max)
        shifted = _apply_transpose(notes, shift)
        folded, fold_count = _fold_into_range(shifted, note_min, note_max)
        deduped = _deduplicate(folded)
        return ArrangementResult(deduped, shift, fold_count, "global_transpose")

    if strategy == "flowing_fold":
        shift = _compute_best_transpose(notes, note_min, note_max)
        shifted = _apply_transpose(notes, shift)
        folded, fold_count = _flowing_fold(shifted, note_min, note_max)
        deduped = _deduplicate(folded)
        return ArrangementResult(deduped, shift, fold_count, "flowing_fold")

    # hybrid: transpose first, then flowing fold for remaining out-of-range
    shift = _compute_best_transpose(notes, note_min, note_max)
    shifted = _apply_transpose(notes, shift)
    folded, fold_count = _flowing_fold(shifted, note_min, note_max)
    deduped = _deduplicate(folded)
    return ArrangementResult(deduped, shift, fold_count, "hybrid")


def arrange_beat_sequence(
    notes: list[BeatNote],
    *,
    note_min: int = PLAYABLE_MIDI_MIN,
    note_max: int = PLAYABLE_MIDI_MAX,
    strategy: str = "auto",
) -> ArrangementResult:
    """Convenience wrapper — identical to ``smart_arrange``.

    Exists so the editor can call a clearly-named function.
    """
    return smart_arrange(notes, note_min=note_min, note_max=note_max, strategy=strategy)
