"""MIDI FX processors — Arpeggiator, Humanize, Quantize, Chord Generator.

All processors operate on ``list[BeatNote]`` → ``list[BeatNote]`` so they
compose cleanly with the editor's beat-based model.  None mutate the input;
they always return a new list.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .beat_sequence import BeatNote

# ── Arpeggiator ───────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ArpeggiatorConfig:
    """Configuration for the arpeggiator effect."""

    pattern: str = "up"  # up, down, up_down, random
    rate: float = 0.25  # note duration in beats for each arp step
    octave_range: int = 0  # extra octaves to span (0 = within chord only)
    gate: float = 0.9  # fraction of rate used as note duration (0-1)


def arpeggiate(notes: list[BeatNote], config: ArpeggiatorConfig | None = None, *, seed: int | None = None) -> list[BeatNote]:
    """Spread chords in time by arpeggiating overlapping notes.

    Groups notes by identical ``time_beats`` and ``track``, then spreads
    them according to the chosen pattern.
    """
    if config is None:
        config = ArpeggiatorConfig()

    rng = random.Random(seed)

    # Group notes by (time, track)
    groups: dict[tuple[float, int], list[BeatNote]] = {}
    singles: list[BeatNote] = []
    for n in notes:
        key = (n.time_beats, n.track)
        groups.setdefault(key, []).append(n)

    # Separate groups with 1 note (pass-through) from chords (>1 note)
    result: list[BeatNote] = []
    for key, group in groups.items():
        if len(group) == 1:
            singles.append(group[0])
            continue

        # Sort by pitch for up/down patterns
        sorted_notes = sorted(group, key=lambda n: n.note)

        # Build pitch sequence including extra octaves
        pitches: list[int] = [n.note for n in sorted_notes]
        if config.octave_range > 0:
            base_pitches = list(pitches)
            for octave in range(1, config.octave_range + 1):
                for p in base_pitches:
                    shifted = p + 12 * octave
                    if shifted <= 127:
                        pitches.append(shifted)

        # Apply pattern ordering
        if config.pattern == "down":
            pitches = list(reversed(pitches))
        elif config.pattern == "up_down":
            if len(pitches) > 1:
                pitches = pitches + list(reversed(pitches[1:-1]))
        elif config.pattern == "random":
            rng.shuffle(pitches)
        # else "up" — already sorted ascending

        base_time = key[0]
        track = key[1]
        vel = sorted_notes[0].velocity
        dur = config.rate * config.gate

        for i, pitch in enumerate(pitches):
            result.append(BeatNote(
                time_beats=base_time + i * config.rate,
                duration_beats=max(0.0625, dur),
                note=max(0, min(127, pitch)),
                velocity=vel,
                track=track,
            ))

    result.extend(singles)
    result.sort(key=lambda n: n.time_beats)
    return result


# ── Humanize ──────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class HumanizeConfig:
    """Configuration for the humanize effect."""

    timing_jitter_beats: float = 0.03  # max jitter in beats
    velocity_jitter: int = 10  # max velocity deviation
    duration_jitter_beats: float = 0.0  # max duration jitter


def humanize(notes: list[BeatNote], config: HumanizeConfig | None = None, *, seed: int | None = None) -> list[BeatNote]:
    """Add random timing and velocity variations for a more natural feel."""
    if config is None:
        config = HumanizeConfig()

    rng = random.Random(seed)
    result: list[BeatNote] = []

    for n in notes:
        t = n.time_beats
        if config.timing_jitter_beats > 0:
            t += rng.uniform(-config.timing_jitter_beats, config.timing_jitter_beats)
        t = max(0.0, t)

        v = n.velocity
        if config.velocity_jitter > 0:
            v += rng.randint(-config.velocity_jitter, config.velocity_jitter)
        v = max(1, min(127, v))

        d = n.duration_beats
        if config.duration_jitter_beats > 0:
            d += rng.uniform(-config.duration_jitter_beats, config.duration_jitter_beats)
        d = max(0.0625, d)

        result.append(BeatNote(t, d, n.note, v, n.track))

    result.sort(key=lambda n: n.time_beats)
    return result


# ── Quantize ──────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class QuantizeConfig:
    """Configuration for the quantize effect."""

    grid: float = 0.5  # grid size in beats (0.5 = eighth note)
    strength: float = 1.0  # 0.0 = no change, 1.0 = full snap


def quantize(notes: list[BeatNote], config: QuantizeConfig | None = None) -> list[BeatNote]:
    """Snap note timing to a grid with adjustable strength."""
    if config is None:
        config = QuantizeConfig()

    if config.grid <= 0 or config.strength <= 0:
        return [BeatNote(n.time_beats, n.duration_beats, n.note, n.velocity, n.track) for n in notes]

    result: list[BeatNote] = []
    for n in notes:
        snapped = round(n.time_beats / config.grid) * config.grid
        new_time = n.time_beats + (snapped - n.time_beats) * config.strength
        new_time = max(0.0, new_time)
        result.append(BeatNote(new_time, n.duration_beats, n.note, n.velocity, n.track))

    result.sort(key=lambda n: n.time_beats)
    return result


# ── Chord Generator ───────────────────────────────────────

# Intervals in semitones relative to root
CHORD_INTERVALS: dict[str, tuple[int, ...]] = {
    "major": (0, 4, 7),
    "minor": (0, 3, 7),
    "7th": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "min7": (0, 3, 7, 10),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "power": (0, 7),
}


@dataclass(frozen=True, slots=True)
class ChordGenConfig:
    """Configuration for the chord generator."""

    chord_type: str = "major"  # key into CHORD_INTERVALS
    voicing: str = "close"  # "close", "spread", "drop2"
    velocity_scale: float = 0.85  # velocity of added tones relative to root


def generate_chords(notes: list[BeatNote], config: ChordGenConfig | None = None) -> list[BeatNote]:
    """Add chord tones to each note based on the configured chord type."""
    if config is None:
        config = ChordGenConfig()

    intervals = CHORD_INTERVALS.get(config.chord_type, (0, 4, 7))
    result: list[BeatNote] = []

    for n in notes:
        # Root note — always keep
        result.append(BeatNote(n.time_beats, n.duration_beats, n.note, n.velocity, n.track))

        # Add chord tones (skip root interval 0)
        for idx, interval in enumerate(intervals):
            if interval == 0:
                continue

            pitch = n.note + interval

            # Voicing adjustments
            if config.voicing == "spread" and idx % 2 == 0:
                pitch += 12  # spread even intervals up an octave
            elif config.voicing == "drop2" and idx == 1:
                pitch -= 12  # drop the 2nd voice down an octave

            pitch = max(0, min(127, pitch))
            vel = max(1, int(n.velocity * config.velocity_scale))
            result.append(BeatNote(n.time_beats, n.duration_beats, pitch, vel, n.track))

    result.sort(key=lambda n: (n.time_beats, n.note))
    return result
