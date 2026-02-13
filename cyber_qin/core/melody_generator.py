"""Rule-based melody generator (AI Composition).

Uses first-order Markov chain with music theory constraints to generate
melodies, bass lines, and rhythmic patterns.  Operates on ``BeatNote``
lists so output plugs directly into the editor.

All generation is deterministic when a *seed* is provided, enabling
reproducible tests.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .beat_sequence import BeatNote

# ── Scale definitions ─────────────────────────────────────

# Intervals from root (semitones)
SCALE_INTERVALS: dict[str, tuple[int, ...]] = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "pentatonic": (0, 2, 4, 7, 9),
    "minor_pentatonic": (0, 3, 5, 7, 10),
    "blues": (0, 3, 5, 6, 7, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11),
}


def _build_scale_pool(root: int, scale: str, note_min: int, note_max: int) -> list[int]:
    """Build all scale notes within [note_min, note_max]."""
    intervals = SCALE_INTERVALS.get(scale, SCALE_INTERVALS["major"])
    pool: list[int] = []
    for octave_base in range(0, 128, 12):
        for iv in intervals:
            pitch = octave_base + (root % 12) + iv
            if note_min <= pitch <= note_max:
                pool.append(pitch)
    return sorted(set(pool))


# ── Rhythm patterns ───────────────────────────────────────

# Each pattern is a list of (beat_offset, duration) within one bar
# for 4/4 time signature (4 beats per bar)
RHYTHM_PATTERNS_4_4: list[list[tuple[float, float]]] = [
    # Simple quarter notes
    [(0, 1.0), (1, 1.0), (2, 1.0), (3, 1.0)],
    # Quarter + eighth variation
    [(0, 1.0), (1, 0.5), (1.5, 0.5), (2, 1.0), (3, 1.0)],
    # Syncopated
    [(0, 1.5), (1.5, 0.5), (2, 1.0), (3, 0.5), (3.5, 0.5)],
    # Eighth note flow
    [(0, 0.5), (0.5, 0.5), (1, 0.5), (1.5, 0.5), (2, 0.5), (2.5, 0.5), (3, 0.5), (3.5, 0.5)],
    # Half note + quarters
    [(0, 2.0), (2, 1.0), (3, 1.0)],
    # Dotted quarter + eighth
    [(0, 1.5), (1.5, 0.5), (2, 1.5), (3.5, 0.5)],
]

RHYTHM_PATTERNS_3_4: list[list[tuple[float, float]]] = [
    [(0, 1.0), (1, 1.0), (2, 1.0)],
    [(0, 1.5), (1.5, 0.5), (2, 1.0)],
    [(0, 0.5), (0.5, 0.5), (1, 1.0), (2, 1.0)],
    [(0, 2.0), (2, 1.0)],
]


# ── Melody Generation ─────────────────────────────────────


@dataclass(frozen=True, slots=True)
class MelodyConfig:
    """Configuration for melody generation."""

    root: int = 60  # MIDI root note (C4)
    scale: str = "major"
    note_min: int = 60  # lowest allowed MIDI note
    note_max: int = 83  # highest allowed MIDI note
    num_bars: int = 8
    time_signature: tuple[int, int] = (4, 4)
    velocity: int = 100
    track: int = 0
    phrase_length: int = 4  # bars per phrase (for contour shaping)
    stepwise_bias: float = 0.7  # probability of step (vs skip) motion


def _interval_weight(pool: list[int], current_idx: int, target_idx: int, stepwise_bias: float) -> float:
    """Weight for transitioning from pool[current] to pool[target]."""
    interval = abs(target_idx - current_idx)
    if interval == 0:
        return 0.3  # repetition
    if interval == 1:
        return stepwise_bias  # step
    if interval == 2:
        return (1.0 - stepwise_bias) * 0.6  # third
    if interval <= 4:
        return (1.0 - stepwise_bias) * 0.3  # medium skip
    return (1.0 - stepwise_bias) * 0.1  # large skip


def _apply_contour(weights: list[float], pool: list[int], current_idx: int, bar_in_phrase: int, phrase_len: int) -> list[float]:
    """Shape weights to produce an arch contour across the phrase."""
    if phrase_len <= 1:
        return weights

    # Normalised position 0..1 within phrase
    pos = bar_in_phrase / max(1, phrase_len - 1)

    # Arch: prefer higher notes in the middle of the phrase
    adjusted = list(weights)
    for i in range(len(pool)):
        if pos < 0.5:
            # Rising: prefer notes above current
            if i > current_idx:
                adjusted[i] *= 1.3
        else:
            # Falling: prefer notes below or at current
            if i <= current_idx:
                adjusted[i] *= 1.3
    return adjusted


def generate_melody(config: MelodyConfig | None = None, *, seed: int | None = None) -> list[BeatNote]:
    """Generate a melody using first-order Markov chain with music theory.

    Steps:
    1. Build scale note pool within range
    2. Select notes with stepwise motion preference
    3. Apply rhythmic patterns per time signature
    4. Force phrase resolution on tonic/5th at bar boundaries
    5. Contour shaping (arch across phrases)
    """
    if config is None:
        config = MelodyConfig()

    rng = random.Random(seed)
    pool = _build_scale_pool(config.root, config.scale, config.note_min, config.note_max)
    if not pool:
        return []

    # Choose rhythm patterns based on time signature
    num, denom = config.time_signature
    beats_per_bar = num * (4.0 / denom)
    if num == 3:
        patterns = RHYTHM_PATTERNS_3_4
    else:
        patterns = RHYTHM_PATTERNS_4_4

    # Start near the middle of the pool
    current_idx = len(pool) // 2
    notes: list[BeatNote] = []

    # Tonic and 5th indices for resolution
    tonic_pc = config.root % 12
    fifth_pc = (config.root + 7) % 12
    resolution_pcs = {tonic_pc, fifth_pc}

    for bar in range(config.num_bars):
        bar_offset = bar * beats_per_bar
        phrase_bar = bar % config.phrase_length

        # Pick a rhythm pattern for this bar
        pattern = rng.choice(patterns)

        # Scale pattern to fit time signature if needed
        for beat_off, duration in pattern:
            if beat_off >= beats_per_bar:
                continue

            # Force resolution on phrase boundaries (last beat of last bar)
            is_phrase_end = (phrase_bar == config.phrase_length - 1 and beat_off >= beats_per_bar - 1)
            is_final_bar = (bar == config.num_bars - 1 and beat_off >= beats_per_bar - 1)

            if is_phrase_end or is_final_bar:
                # Resolve to tonic or 5th
                resolution_candidates = [i for i, p in enumerate(pool) if p % 12 in resolution_pcs]
                if resolution_candidates:
                    # Pick closest to current position
                    current_idx = min(resolution_candidates, key=lambda i: abs(i - current_idx))
            else:
                # Normal Markov transition
                weights = [_interval_weight(pool, current_idx, j, config.stepwise_bias) for j in range(len(pool))]
                weights = _apply_contour(weights, pool, current_idx, phrase_bar, config.phrase_length)

                total = sum(weights)
                if total > 0:
                    weights = [w / total for w in weights]
                    r = rng.random()
                    cumulative = 0.0
                    for j, w in enumerate(weights):
                        cumulative += w
                        if r <= cumulative:
                            current_idx = j
                            break

            # Clamp duration to not exceed bar
            actual_dur = min(duration, beats_per_bar - beat_off)
            notes.append(BeatNote(
                time_beats=bar_offset + beat_off,
                duration_beats=actual_dur,
                note=pool[current_idx],
                velocity=config.velocity,
                track=config.track,
            ))

    return notes


# ── Bass Line Generation ──────────────────────────────────

# Common chord progressions (scale degrees, 0-indexed)
PROGRESSIONS: dict[str, list[int]] = {
    "I-IV-V-I": [0, 3, 4, 0],
    "I-V-vi-IV": [0, 4, 5, 3],
    "I-vi-IV-V": [0, 5, 3, 4],
    "i-iv-v-i": [0, 3, 4, 0],
    "i-VI-III-VII": [0, 5, 2, 6],
    "I-IV-I-V": [0, 3, 0, 4],
}


@dataclass(frozen=True, slots=True)
class BassConfig:
    """Configuration for bass line generation."""

    root: int = 48  # C3
    scale: str = "major"
    note_min: int = 36
    note_max: int = 60
    num_bars: int = 8
    time_signature: tuple[int, int] = (4, 4)
    progression: str = "I-IV-V-I"
    velocity: int = 100
    track: int = 1
    pattern: str = "root"  # "root", "root_fifth", "walking"


def generate_bass_line(config: BassConfig | None = None, *, seed: int | None = None) -> list[BeatNote]:
    """Generate a bass line following a chord progression."""
    if config is None:
        config = BassConfig()

    pool = _build_scale_pool(config.root, config.scale, config.note_min, config.note_max)
    if not pool:
        return []

    intervals = SCALE_INTERVALS.get(config.scale, SCALE_INTERVALS["major"])
    progression = PROGRESSIONS.get(config.progression, [0, 3, 4, 0])

    num, denom = config.time_signature
    beats_per_bar = num * (4.0 / denom)

    notes: list[BeatNote] = []

    for bar in range(config.num_bars):
        bar_offset = bar * beats_per_bar
        degree = progression[bar % len(progression)]

        # Find the root note for this degree
        degree_semitones = intervals[degree % len(intervals)]
        target_pc = (config.root + degree_semitones) % 12

        # Find closest pool note to config.root with this pitch class
        degree_notes = [p for p in pool if p % 12 == target_pc]
        if not degree_notes:
            degree_notes = [pool[0]]
        bass_note = min(degree_notes, key=lambda p: abs(p - config.root))

        if config.pattern == "root":
            notes.append(BeatNote(
                time_beats=bar_offset,
                duration_beats=beats_per_bar,
                note=bass_note,
                velocity=config.velocity,
                track=config.track,
            ))

        elif config.pattern == "root_fifth":
            fifth_pc = (target_pc + 7) % 12
            fifth_notes = [p for p in pool if p % 12 == fifth_pc]
            fifth_note = min(fifth_notes, key=lambda p: abs(p - bass_note)) if fifth_notes else bass_note

            half = beats_per_bar / 2
            notes.append(BeatNote(bar_offset, half, bass_note, config.velocity, config.track))
            notes.append(BeatNote(bar_offset + half, half, fifth_note, config.velocity, config.track))

        elif config.pattern == "walking":
            # Simple walking bass: root, passing tone, 5th, approach
            steps = [0, 2, 4, 6]  # scale degrees relative to chord root
            step_dur = beats_per_bar / len(steps)
            for i, deg_off in enumerate(steps):
                actual_deg = (degree + deg_off) % len(intervals)
                semi = intervals[actual_deg]
                pitch = config.root + semi
                # Find closest in pool
                candidates = [p for p in pool if p % 12 == pitch % 12]
                if candidates:
                    walk_note = min(candidates, key=lambda p: abs(p - bass_note))
                else:
                    walk_note = bass_note
                vel = config.velocity if i == 0 else max(1, config.velocity - 10)
                notes.append(BeatNote(bar_offset + i * step_dur, step_dur, walk_note, vel, config.track))

    return notes
