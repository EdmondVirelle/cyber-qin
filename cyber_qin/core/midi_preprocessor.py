"""MIDI preprocessing pipeline for 燕雲十六聲 (Where Winds Meet).

Transforms raw MIDI events for optimal game playback:
1. Percussion filter — remove GM channel 10 drum events
2. Track filter — keep only user-selected tracks
3. Octave deduplication — same pitch class at same time → keep highest
4. Smart global transpose — find optimal ±12 shift to center notes in range
5. 流水摺疊 (Flowing Fold) — voice-leading aware octave fold per channel
6. Collision deduplication — velocity-priority duplicate removal
7. Polyphony limiter — cap simultaneous notes, keep highest + lowest
8. Velocity normalization — unify all note_on velocity to 127
9. Time quantization — snap to frame grid to eliminate micro-delays
"""

from __future__ import annotations

from dataclasses import dataclass

from .constants import MIDI_NOTE_MAX, MIDI_NOTE_MIN

# 60 FPS frame duration
_FRAME_SEC = 1.0 / 60.0  # ~16.67 ms

# GM percussion channel (0-indexed)
_GM_PERCUSSION_CHANNEL = 9


@dataclass(frozen=True, slots=True)
class PreprocessStats:
    """Statistics from the preprocessing pipeline."""

    total_notes: int
    notes_shifted: int
    original_range: tuple[int, int]  # (lowest, highest) MIDI note before shift
    global_transpose: int = 0        # semitones applied globally (multiple of 12)
    duplicates_removed: int = 0      # collisions removed after octave folding
    percussion_removed: int = 0      # percussion channel events removed
    tracks_removed: int = 0          # events removed by track filter
    octave_deduped: int = 0          # octave-duplicate events removed
    polyphony_limited: int = 0       # events removed by polyphony limiter


# ── Stage 1: Percussion Filter ─────────────────────────────


def filter_percussion(
    events: list, *, percussion_channel: int = _GM_PERCUSSION_CHANNEL,
) -> tuple[list, int]:
    """Remove events on the GM percussion channel (default: channel 10 / 0-indexed 9).

    Returns (filtered_events, count_removed).
    """
    result: list = []
    removed = 0
    for evt in events:
        if evt.event_type in ("note_on", "note_off") and evt.channel == percussion_channel:
            removed += 1
            continue
        result.append(evt)
    return result, removed


# ── Stage 2: Track Filter ──────────────────────────────────


def filter_tracks(
    events: list, *, include_tracks: set[int] | None = None,
) -> tuple[list, int]:
    """Keep only events from the specified track indices.

    If include_tracks is None, all events are kept (no filtering).
    Returns (filtered_events, count_removed).
    """
    if include_tracks is None:
        return events, 0

    result: list = []
    removed = 0
    for evt in events:
        if evt.event_type in ("note_on", "note_off") and evt.track not in include_tracks:
            removed += 1
            continue
        result.append(evt)
    return result, removed


# ── Stage 3: Octave Deduplication ──────────────────────────


def deduplicate_octaves(events: list) -> tuple[list, int]:
    """Remove octave-duplicate notes: same pitch class at the same time, keep highest.

    For example, if C4 (60) and C5 (72) occur at the same time, keep C5.
    This reduces collisions before octave folding.

    Returns (deduplicated_events, count_removed).
    """
    # Group note_on events by (time, pitch_class) → keep highest note
    # First pass: find which notes to keep
    time_pc_best: dict[tuple[float, int], int] = {}  # (time, pitch_class) → highest note
    for evt in events:
        if evt.event_type == "note_on":
            key = (evt.time_seconds, evt.note % 12)
            if key not in time_pc_best or evt.note > time_pc_best[key]:
                time_pc_best[key] = evt.note

    # Second pass: mark note pitches to drop (track by note value)
    drop_pitches: set[int] = set()  # note values whose note_on was dropped
    removed = 0

    for evt in events:
        if evt.event_type == "note_on":
            key = (evt.time_seconds, evt.note % 12)
            best = time_pc_best[key]
            if evt.note != best:
                drop_pitches.add(evt.note)
                removed += 1

    # Third pass: filter events, also drop matching note_offs for dropped pitches
    result: list = []
    for evt in events:
        if evt.event_type == "note_on" and evt.note in drop_pitches:
            key = (evt.time_seconds, evt.note % 12)
            best = time_pc_best.get(key)
            if best is not None and evt.note != best:
                continue
        elif evt.event_type == "note_off" and evt.note in drop_pitches:
            removed += 1
            drop_pitches.discard(evt.note)  # consume: one note_off per dropped note_on
            continue
        result.append(evt)

    return result, removed


# ── Stage 4: Smart Global Transpose ───────────────────────


def compute_optimal_transpose(
    events: list, *, note_min: int = MIDI_NOTE_MIN, note_max: int = MIDI_NOTE_MAX,
) -> int:
    """Find the best global transpose (multiple of 12) to maximize in-range notes.

    Tries shifts from -48 to +48 in steps of 12 and picks the one that puts
    the most note_on events inside [note_min, note_max].
    Returns 0 if no shift helps.
    """
    notes = [e.note for e in events if e.event_type == "note_on"]
    if not notes:
        return 0

    best_shift = 0
    best_in_range = sum(1 for n in notes if note_min <= n <= note_max)

    for shift in range(-48, 49, 12):
        if shift == 0:
            continue
        in_range = sum(1 for n in notes if note_min <= n + shift <= note_max)
        # Prefer more in-range; break ties by smallest absolute shift
        if in_range > best_in_range or (
            in_range == best_in_range and abs(shift) < abs(best_shift)
        ):
            best_in_range = in_range
            best_shift = shift

    return best_shift


def apply_global_transpose(events: list, *, semitones: int) -> list:
    """Shift all note events by a fixed number of semitones."""
    if semitones == 0:
        return events

    from .midi_file_player import MidiFileEvent

    return [
        MidiFileEvent(
            time_seconds=evt.time_seconds,
            event_type=evt.event_type,
            note=evt.note + semitones,
            velocity=evt.velocity,
            track=evt.track,
            channel=evt.channel,
        )
        if evt.event_type in ("note_on", "note_off") else evt
        for evt in events
    ]


# ── Stage 5: Octave Fold ──────────────────────────────────


def normalize_octave(events: list, *, note_min: int = MIDI_NOTE_MIN, note_max: int = MIDI_NOTE_MAX) -> list:
    """Shift notes into the playable range by octave transposition.

    Notes above max are lowered by octaves; notes below min are raised.
    """
    from .midi_file_player import MidiFileEvent

    result: list = []
    for evt in events:
        note = evt.note
        while note > note_max:
            note -= 12
        while note < note_min:
            note += 12
        if note != evt.note:
            evt = MidiFileEvent(
                time_seconds=evt.time_seconds,
                event_type=evt.event_type,
                note=note,
                velocity=evt.velocity,
                track=evt.track,
                channel=evt.channel,
            )
        result.append(evt)
    return result


# ── Stage 5b: 流水摺疊 (Flowing Fold) ────────────────────


@dataclass(slots=True)
class _VoiceState:
    """Per-channel voice-leading state for flowing fold."""

    prev_note: float  # previous folded note (float for center EMA)
    prev_prev_note: float
    center: float  # exponential moving average of recent notes


def _get_octave_candidates(note: int, note_min: int, note_max: int) -> list[int]:
    """Return all octave positions of *note*'s pitch class within [note_min, note_max]."""
    pc = note % 12
    candidates: list[int] = []
    # Start from the lowest octave position of this pitch class at or above note_min
    base = note_min + ((pc - note_min % 12) % 12)
    n = base
    while n <= note_max:
        candidates.append(n)
        n += 12
    return candidates


def _score_candidate(
    candidate: int,
    state: _VoiceState,
    note_min: int,
    note_max: int,
) -> float:
    """Score a candidate octave position based on voice-leading context."""
    mid = (note_min + note_max) / 2.0
    score = 0.0

    # (a) Voice-leading distance — prefer small intervals
    score -= 2.0 * abs(candidate - state.prev_note)

    # (b) Direction continuity — reward continuing the same direction
    prev_direction = state.prev_note - state.prev_prev_note
    curr_direction = candidate - state.prev_note
    if prev_direction != 0 and curr_direction != 0:
        # Same sign → same direction
        if (prev_direction > 0) == (curr_direction > 0):
            score += 4.0
        elif abs(curr_direction) <= 5:
            # Smooth reversal (small interval)
            score += 1.5

    # (c) Gravity center — stay near recent activity
    score -= 0.5 * abs(candidate - state.center)

    # (d) Range preference — mild bias toward center of range
    score -= 0.1 * abs(candidate - mid)

    return score


def normalize_octave_flowing(
    events: list,
    *,
    note_min: int = MIDI_NOTE_MIN,
    note_max: int = MIDI_NOTE_MAX,
) -> list:
    """Voice-leading aware octave fold (流水摺疊).

    Instead of blindly folding each note with modulo, this algorithm picks
    the octave position that best preserves melodic direction per channel.
    Uses per-channel tracking so bass and melody lines don't interfere.
    """
    from .midi_file_player import MidiFileEvent

    mid = (note_min + note_max) / 2.0
    # Per-channel voice state
    states: dict[int, _VoiceState] = {}
    # note_off pairing: (channel, original_note) → stack of folded notes
    off_map: dict[tuple[int, int], list[int]] = {}

    result: list = []
    for evt in events:
        if evt.event_type == "note_on":
            ch = evt.channel
            candidates = _get_octave_candidates(evt.note, note_min, note_max)
            if not candidates:
                # Shouldn't happen if note_min/note_max span ≥12, but be safe
                # Fall back to simple modulo fold
                n = evt.note
                while n > note_max:
                    n -= 12
                while n < note_min:
                    n += 12
                candidates = [n]

            if len(candidates) == 1:
                chosen = candidates[0]
            elif ch not in states:
                # First note on this channel — no voice-leading context.
                # Keep original if in range; otherwise pick closest to center.
                if note_min <= evt.note <= note_max:
                    chosen = evt.note
                else:
                    chosen = min(candidates, key=lambda c: abs(c - mid))
                states[ch] = _VoiceState(
                    prev_note=float(chosen),
                    prev_prev_note=float(chosen),
                    center=float(chosen),
                )
            else:
                st = states[ch]
                best_score = float("-inf")
                chosen = candidates[0]
                for c in candidates:
                    s = _score_candidate(c, st, note_min, note_max)
                    if s > best_score:
                        best_score = s
                        chosen = c

            # Update voice state (skip if just initialized above)
            if ch not in states:
                states[ch] = _VoiceState(
                    prev_note=float(chosen),
                    prev_prev_note=float(chosen),
                    center=float(chosen),
                )
            st = states[ch]
            st.prev_prev_note = st.prev_note
            st.prev_note = float(chosen)
            st.center = st.center * 0.85 + float(chosen) * 0.15

            # Record for note_off pairing
            key = (ch, evt.note)
            off_map.setdefault(key, []).append(chosen)

            if chosen != evt.note:
                evt = MidiFileEvent(
                    time_seconds=evt.time_seconds,
                    event_type=evt.event_type,
                    note=chosen,
                    velocity=evt.velocity,
                    track=evt.track,
                    channel=evt.channel,
                )

        elif evt.event_type == "note_off":
            key = (evt.channel, evt.note)
            stack = off_map.get(key)
            if stack:
                folded = stack.pop(0)
            else:
                # No matching note_on — fallback to simple fold
                folded = evt.note
                while folded > note_max:
                    folded -= 12
                while folded < note_min:
                    folded += 12

            if folded != evt.note:
                evt = MidiFileEvent(
                    time_seconds=evt.time_seconds,
                    event_type=evt.event_type,
                    note=folded,
                    velocity=evt.velocity,
                    track=evt.track,
                    channel=evt.channel,
                )

        result.append(evt)
    return result


# ── Stage 6: Collision Deduplication (velocity priority) ──


def deduplicate_notes(events: list) -> tuple[list, int]:
    """Remove duplicate note events at the same (time, type, note).

    After octave folding, multiple notes can collapse to the same pitch.
    Uses velocity priority: when note_on events with the same (time, note)
    collide, the one with the highest velocity is kept. For note_off events,
    duplicates are simply collapsed (first seen wins).

    Returns (deduplicated_events, count_removed).
    """
    # Pre-scan: find max velocity for each (time, note) collision among note_on
    max_vel: dict[tuple[float, int], int] = {}
    for evt in events:
        if evt.event_type == "note_on":
            key = (evt.time_seconds, evt.note)
            if key not in max_vel or evt.velocity > max_vel[key]:
                max_vel[key] = evt.velocity

    seen_on: set[tuple[float, int]] = set()
    seen_off: set[tuple[float, int]] = set()
    result: list = []
    removed = 0

    for evt in events:
        if evt.event_type == "note_on":
            key = (evt.time_seconds, evt.note)
            if key in seen_on:
                removed += 1
                continue
            # Keep the one with max velocity, skip others
            if evt.velocity < max_vel[key]:
                removed += 1
                continue
            seen_on.add(key)
        elif evt.event_type == "note_off":
            key = (evt.time_seconds, evt.note)
            if key in seen_off:
                removed += 1
                continue
            seen_off.add(key)
        result.append(evt)

    return result, removed


# ── Stage 7: Polyphony Limiter ─────────────────────────────


def limit_polyphony(events: list, *, max_voices: int = 0) -> tuple[list, int]:
    """Limit the number of simultaneously sounding notes.

    Groups note_on events by time, then selects at most *max_voices*
    from all active notes at each time point.  Priority: keep the
    highest and lowest (bass anchor), fill remaining slots from the
    top.  Dropped notes have their corresponding note_off also removed.

    If max_voices <= 0, no limiting is applied.

    Returns (limited_events, count_removed).
    """
    if max_voices <= 0:
        return events, 0

    # Two-pass approach: first decide which notes to drop at which times,
    # then filter events.

    # Pass 1: simulate playback and record drop decisions.
    # We record the original note_on time for each dropped note.
    active: dict[int, float] = {}  # note → time of its note_on
    drop_set: set[tuple[float, int]] = set()  # (original_time, note) of dropped note_ons

    for evt in events:
        if evt.event_type == "note_off":
            active.pop(evt.note, None)
        elif evt.event_type == "note_on":
            active[evt.note] = evt.time_seconds
            if len(active) > max_voices:
                # Too many voices — decide which to keep
                candidates = sorted(active)
                keepers: set[int] = set()
                if max_voices >= 2:
                    keepers.add(candidates[0])  # always keep lowest (bass)
                # Fill from highest down
                for n in reversed(candidates):
                    if len(keepers) >= max_voices:
                        break
                    keepers.add(n)
                # Drop active notes not in keepers, using their original times
                for n in list(active):
                    if n not in keepers:
                        drop_set.add((active[n], n))
                        del active[n]

    # Pass 2: filter events
    pending_drops: set[int] = set()  # notes whose note_offs should also be removed
    result: list = []
    removed = 0

    for evt in events:
        if evt.event_type == "note_on":
            if (evt.time_seconds, evt.note) in drop_set:
                pending_drops.add(evt.note)
                removed += 1
                continue
        elif evt.event_type == "note_off":
            if evt.note in pending_drops:
                pending_drops.discard(evt.note)
                removed += 1
                continue
        result.append(evt)

    return result, removed


# ── Stage 8-9: Velocity + Timing ──────────────────────────


def normalize_velocity(events: list, *, target: int = 127) -> list:
    """Set all note_on velocities to *target* for consistent key simulation."""
    from .midi_file_player import MidiFileEvent

    result: list = []
    for evt in events:
        if evt.event_type == "note_on" and evt.velocity != target:
            evt = MidiFileEvent(
                time_seconds=evt.time_seconds,
                event_type=evt.event_type,
                note=evt.note,
                velocity=target,
                track=evt.track,
                channel=evt.channel,
            )
        result.append(evt)
    return result


def quantize_timing(events: list, *, grid_sec: float = _FRAME_SEC) -> list:
    """Snap event times to a frame-aligned grid to remove micro-delays.

    Default grid matches 60 FPS (~16.67 ms).  Events within the same frame
    are collapsed to the same timestamp.
    """
    from .midi_file_player import MidiFileEvent

    result: list = []
    for evt in events:
        snapped = round(evt.time_seconds / grid_sec) * grid_sec
        if abs(snapped - evt.time_seconds) > 1e-9:
            evt = MidiFileEvent(
                time_seconds=snapped,
                event_type=evt.event_type,
                note=evt.note,
                velocity=evt.velocity,
                track=evt.track,
                channel=evt.channel,
            )
        result.append(evt)
    return result


# ── Full Pipeline ──────────────────────────────────────────


def preprocess(
    events: list,
    *,
    note_min: int = MIDI_NOTE_MIN,
    note_max: int = MIDI_NOTE_MAX,
    remove_percussion: bool = True,
    include_tracks: set[int] | None = None,
    max_voices: int = 0,
) -> tuple[list, PreprocessStats]:
    """Apply the full preprocessing pipeline.

    Order:
        1. Percussion filter (if remove_percussion)
        2. Track filter (if include_tracks specified)
        3. Octave dedup (remove octave doublings, keep highest)
        4. Smart global transpose
        5. 流水摺疊 — voice-leading aware octave fold
        6. Collision dedup (velocity priority)
        7. Polyphony limit (if max_voices > 0)
        8. Velocity normalize
        9. Time quantize
        10. Re-sort

    Returns (processed_events, stats).
    """
    if not events:
        return events, PreprocessStats(0, 0, (0, 0))

    # Gather pre-processing stats
    note_ons = [e for e in events if e.event_type == "note_on"]
    total = len(note_ons)
    if note_ons:
        lo = min(e.note for e in note_ons)
        hi = max(e.note for e in note_ons)
    else:
        lo, hi = 0, 0

    # 1. Percussion filter
    perc_removed = 0
    if remove_percussion:
        events, perc_removed = filter_percussion(events)

    # 2. Track filter
    trk_removed = 0
    if include_tracks is not None:
        events, trk_removed = filter_tracks(events, include_tracks=include_tracks)

    # 3. Octave dedup (before folding — reduces collisions)
    events, oct_deduped = deduplicate_octaves(events)

    # 4. Smart global transpose
    transpose = compute_optimal_transpose(events, note_min=note_min, note_max=note_max)
    events = apply_global_transpose(events, semitones=transpose)

    # Count out-of-range after transpose
    out_of_range = sum(
        1 for e in events
        if e.event_type == "note_on" and (e.note < note_min or e.note > note_max)
    )

    # 5. 流水摺疊 — voice-leading aware octave fold
    events = normalize_octave_flowing(events, note_min=note_min, note_max=note_max)

    # 6. Collision dedup (high-note priority)
    events, dupes = deduplicate_notes(events)

    # 7. Polyphony limit
    poly_removed = 0
    if max_voices > 0:
        events, poly_removed = limit_polyphony(events, max_voices=max_voices)

    # 8-9. Velocity + timing
    events = normalize_velocity(events)
    events = quantize_timing(events)

    # Re-sort: by time, then note_off before note_on (release before press)
    events.sort(key=lambda e: (e.time_seconds, 0 if e.event_type == "note_off" else 1))

    stats = PreprocessStats(
        total_notes=total,
        notes_shifted=out_of_range,
        original_range=(lo, hi),
        global_transpose=transpose,
        duplicates_removed=dupes,
        percussion_removed=perc_removed,
        tracks_removed=trk_removed,
        octave_deduped=oct_deduped,
        polyphony_limited=poly_removed,
    )

    return events, stats
