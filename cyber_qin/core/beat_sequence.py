"""Beat-based note sequence model for the editor (Phase 1).

Pure Python, no Qt dependency.  All time positions use *beats* (float)
rather than seconds so that BPM changes don't invalidate note positions.

Conversion to seconds:  ``time_seconds = time_beats * (60.0 / tempo_bpm)``
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

# ── Data classes ────────────────────────────────────────────


@dataclass
class BeatNote:
    """A single note on the beat timeline."""

    time_beats: float
    duration_beats: float
    note: int           # MIDI 0-127
    velocity: int = 100
    track: int = 0


@dataclass
class BeatRest:
    """An explicit rest (silence) on the beat timeline."""

    time_beats: float
    duration_beats: float
    track: int = 0


# Union type for items that can live on the timeline
BeatItem = BeatNote | BeatRest


@dataclass
class Track:
    """Per-track metadata."""

    name: str = ""
    color: str = "#00F0FF"
    channel: int = 0
    muted: bool = False
    solo: bool = False


# ── Presets ─────────────────────────────────────────────────

# label → duration in beats (always relative to a quarter note = 1 beat)
DURATION_PRESETS: dict[str, float] = {
    "1/1": 4.0,
    "1/2": 2.0,
    "1/4": 1.0,
    "1/8": 0.5,
    "1/16": 0.25,
}

# keyboard shortcut key → label
DURATION_KEYS: dict[str, str] = {
    "1": "1/1",
    "2": "1/2",
    "3": "1/4",
    "4": "1/8",
    "5": "1/16",
}

# Supported time signatures
TIME_SIGNATURES: list[tuple[int, int]] = [
    (4, 4),
    (3, 4),
    (2, 4),
    (6, 8),
    (4, 8),
]

DEFAULT_TRACK_COLORS = [
    "#00F0FF",  # 賽博青
    "#FF6B6B",  # 珊瑚紅
    "#4ECDC4",  # 薄荷綠
    "#D4A853",  # 金墨
    "#A06BFF",  # 紫霧
    "#FF9F43",  # 琥珀
    "#54A0FF",  # 天藍
    "#5F27CD",  # 深紫
    "#01A3A4",  # 深青
    "#F368E0",  # 粉紫
    "#10AC84",  # 翡翠
    "#EE5A24",  # 朱砂
]

_MAX_UNDO = 100
_MAX_TRACKS = 12


# ── Snapshot (for undo) ────────────────────────────────────


@dataclass
class _Snapshot:
    notes: list[BeatNote]
    rests: list[BeatRest]
    cursor_beats: float
    active_track: int
    tracks: list[Track] | None = None


# ── EditorSequence ─────────────────────────────────────────


class EditorSequence:
    """Multi-track, beat-based note sequence with undo support."""

    def __init__(
        self,
        tempo_bpm: float = 120.0,
        time_signature: tuple[int, int] = (4, 4),
        num_tracks: int = 4,
    ) -> None:
        self._notes: list[BeatNote] = []
        self._rests: list[BeatRest] = []
        self._cursor_beats: float = 0.0
        self._active_track: int = 0

        self._tempo_bpm: float = tempo_bpm
        self._time_signature: tuple[int, int] = time_signature
        self._step_label: str = "1/4"
        self._step_duration: float = DURATION_PRESETS["1/4"]

        self._tracks: list[Track] = []
        for i in range(min(num_tracks, _MAX_TRACKS)):
            color = DEFAULT_TRACK_COLORS[i % len(DEFAULT_TRACK_COLORS)]
            self._tracks.append(Track(
                name=f"Track {i + 1}",
                color=color,
                channel=i,
            ))

        self._undo_stack: list[_Snapshot] = []
        self._redo_stack: list[_Snapshot] = []

        # Clipboard for copy/paste
        self._clipboard: list[BeatItem] = []

    # ── Properties ──────────────────────────────────────────

    @property
    def notes(self) -> list[BeatNote]:
        return list(self._notes)

    @property
    def rests(self) -> list[BeatRest]:
        return list(self._rests)

    @property
    def all_items(self) -> list[BeatItem]:
        items: list[BeatItem] = [*self._notes, *self._rests]
        items.sort(key=lambda it: it.time_beats)
        return items

    @property
    def note_count(self) -> int:
        return len(self._notes)

    @property
    def rest_count(self) -> int:
        return len(self._rests)

    @property
    def cursor_beats(self) -> float:
        return self._cursor_beats

    @cursor_beats.setter
    def cursor_beats(self, value: float) -> None:
        self._cursor_beats = max(0.0, value)

    @property
    def active_track(self) -> int:
        return self._active_track

    @property
    def tracks(self) -> list[Track]:
        return list(self._tracks)

    @property
    def track_count(self) -> int:
        return len(self._tracks)

    @property
    def tempo_bpm(self) -> float:
        return self._tempo_bpm

    @tempo_bpm.setter
    def tempo_bpm(self, value: float) -> None:
        self._tempo_bpm = max(40.0, min(300.0, value))

    @property
    def time_signature(self) -> tuple[int, int]:
        return self._time_signature

    @time_signature.setter
    def time_signature(self, value: tuple[int, int]) -> None:
        self._time_signature = value

    @property
    def beats_per_bar(self) -> float:
        num, denom = self._time_signature
        # beats_per_bar = numerator * (4 / denominator)
        # e.g. 4/4 → 4, 3/4 → 3, 6/8 → 3
        return num * (4.0 / denom)

    @property
    def bar_count(self) -> int:
        if not self._notes and not self._rests:
            return 0
        max_beat = 0.0
        for n in self._notes:
            end = n.time_beats + n.duration_beats
            if end > max_beat:
                max_beat = end
        for r in self._rests:
            end = r.time_beats + r.duration_beats
            if end > max_beat:
                max_beat = end
        bpb = self.beats_per_bar
        if bpb <= 0:
            return 0
        import math
        return math.ceil(max_beat / bpb)

    @property
    def duration_beats(self) -> float:
        max_beat = 0.0
        for n in self._notes:
            end = n.time_beats + n.duration_beats
            if end > max_beat:
                max_beat = end
        for r in self._rests:
            end = r.time_beats + r.duration_beats
            if end > max_beat:
                max_beat = end
        return max_beat

    @property
    def duration_seconds(self) -> float:
        return self.duration_beats * (60.0 / self._tempo_bpm)

    @property
    def step_label(self) -> str:
        return self._step_label

    @property
    def step_duration(self) -> float:
        return self._step_duration

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def clipboard_empty(self) -> bool:
        return len(self._clipboard) == 0

    # ── Undo / Redo ─────────────────────────────────────────

    def _snapshot(self) -> _Snapshot:
        return _Snapshot(
            notes=[copy.copy(n) for n in self._notes],
            rests=[copy.copy(r) for r in self._rests],
            cursor_beats=self._cursor_beats,
            active_track=self._active_track,
            tracks=[copy.copy(t) for t in self._tracks],
        )

    def _restore(self, snap: _Snapshot) -> None:
        self._notes = snap.notes
        self._rests = snap.rests
        self._cursor_beats = snap.cursor_beats
        self._active_track = snap.active_track
        if snap.tracks is not None:
            self._tracks = snap.tracks

    def _push_undo(self) -> None:
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > _MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(self._snapshot())
        self._restore(self._undo_stack.pop())

    def redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(self._snapshot())
        self._restore(self._redo_stack.pop())

    # ── Step / Duration ─────────────────────────────────────

    def set_step_duration(self, label: str) -> None:
        if label in DURATION_PRESETS:
            self._step_label = label
            self._step_duration = DURATION_PRESETS[label]

    def advance_cursor(self) -> None:
        self._cursor_beats += self._step_duration

    # ── Track management ────────────────────────────────────

    def set_active_track(self, index: int) -> None:
        if 0 <= index < len(self._tracks):
            self._active_track = index

    def add_track(self, name: str = "") -> int:
        if len(self._tracks) >= _MAX_TRACKS:
            return -1
        idx = len(self._tracks)
        color = DEFAULT_TRACK_COLORS[idx % len(DEFAULT_TRACK_COLORS)]
        if not name:
            name = f"Track {idx + 1}"
        self._tracks.append(Track(name=name, color=color, channel=idx))
        return idx

    def rename_track(self, index: int, name: str) -> None:
        if 0 <= index < len(self._tracks):
            self._tracks[index].name = name

    def set_track_muted(self, index: int, muted: bool) -> None:
        if 0 <= index < len(self._tracks):
            self._tracks[index].muted = muted

    def set_track_solo(self, index: int, solo: bool) -> None:
        if 0 <= index < len(self._tracks):
            self._tracks[index].solo = solo

    def reorder_tracks(self, new_order: list[int]) -> None:
        """Reorder tracks by permutation. new_order[i] = old index for new position i."""
        if sorted(new_order) != list(range(len(self._tracks))):
            return
        self._push_undo()
        # Build reverse mapping: old_index → new_index
        old_to_new = {old: new for new, old in enumerate(new_order)}
        self._tracks = [self._tracks[i] for i in new_order]
        for n in self._notes:
            n.track = old_to_new.get(n.track, n.track)
        for r in self._rests:
            r.track = old_to_new.get(r.track, r.track)
        self._active_track = old_to_new.get(self._active_track, 0)

    def remove_track(self, index: int) -> None:
        if not (0 <= index < len(self._tracks)):
            return
        if len(self._tracks) <= 1:
            return  # must keep at least 1 track
        self._push_undo()
        self._tracks.pop(index)
        # Remove notes/rests on that track, shift higher indices
        self._notes = [
            BeatNote(n.time_beats, n.duration_beats, n.note, n.velocity,
                     n.track - 1 if n.track > index else n.track)
            for n in self._notes if n.track != index
        ]
        self._rests = [
            BeatRest(r.time_beats, r.duration_beats,
                     r.track - 1 if r.track > index else r.track)
            for r in self._rests if r.track != index
        ]
        if self._active_track >= len(self._tracks):
            self._active_track = len(self._tracks) - 1

    # ── Note / Rest editing ─────────────────────────────────

    def add_note(self, midi_note: int, velocity: int = 100) -> None:
        self._push_undo()
        note = BeatNote(
            time_beats=self._cursor_beats,
            duration_beats=self._step_duration,
            note=max(0, min(127, midi_note)),
            velocity=velocity,
            track=self._active_track,
        )
        self._notes.append(note)
        self._notes.sort(key=lambda n: n.time_beats)
        self.advance_cursor()

    def add_rest(self) -> None:
        self._push_undo()
        rest = BeatRest(
            time_beats=self._cursor_beats,
            duration_beats=self._step_duration,
            track=self._active_track,
        )
        self._rests.append(rest)
        self._rests.sort(key=lambda r: r.time_beats)
        self.advance_cursor()

    def delete_note(self, index: int) -> None:
        if 0 <= index < len(self._notes):
            self._push_undo()
            self._notes.pop(index)

    def delete_rest(self, index: int) -> None:
        if 0 <= index < len(self._rests):
            self._push_undo()
            self._rests.pop(index)

    def delete_notes(self, indices: list[int]) -> None:
        if not indices:
            return
        self._push_undo()
        to_remove = set(indices)
        self._notes = [n for i, n in enumerate(self._notes) if i not in to_remove]

    def delete_rests(self, indices: list[int]) -> None:
        if not indices:
            return
        self._push_undo()
        to_remove = set(indices)
        self._rests = [r for i, r in enumerate(self._rests) if i not in to_remove]

    def move_note(
        self, index: int, time_delta: float = 0.0, pitch_delta: int = 0,
    ) -> None:
        if not (0 <= index < len(self._notes)):
            return
        self._push_undo()
        n = self._notes[index]
        n.time_beats = max(0.0, n.time_beats + time_delta)
        n.note = max(0, min(127, n.note + pitch_delta))
        self._notes.sort(key=lambda n: n.time_beats)

    def move_notes(
        self, indices: list[int], time_delta: float = 0.0, pitch_delta: int = 0,
    ) -> None:
        if not indices:
            return
        self._push_undo()
        for i in indices:
            if 0 <= i < len(self._notes):
                n = self._notes[i]
                n.time_beats = max(0.0, n.time_beats + time_delta)
                n.note = max(0, min(127, n.note + pitch_delta))
        self._notes.sort(key=lambda n: n.time_beats)

    def resize_note(self, index: int, new_duration: float) -> None:
        if not (0 <= index < len(self._notes)):
            return
        self._push_undo()
        self._notes[index].duration_beats = max(0.25, new_duration)

    def resize_notes(self, indices: list[int], delta_beats: float) -> None:
        """Batch resize notes by delta, single undo step."""
        if not indices:
            return
        self._push_undo()
        for i in indices:
            if 0 <= i < len(self._notes):
                n = self._notes[i]
                n.duration_beats = max(0.25, n.duration_beats + delta_beats)

    def add_note_at(
        self, time_beats: float, midi_note: int, velocity: int = 100,
    ) -> None:
        """Add a note at a specific time position (for pencil tool)."""
        self._push_undo()
        note = BeatNote(
            time_beats=max(0.0, time_beats),
            duration_beats=self._step_duration,
            note=max(0, min(127, midi_note)),
            velocity=velocity,
            track=self._active_track,
        )
        self._notes.append(note)
        self._notes.sort(key=lambda n: n.time_beats)

    def quantize_notes(self, indices: list[int], grid: float) -> None:
        """Snap selected notes' time_beats to nearest grid multiple."""
        if not indices or grid <= 0:
            return
        self._push_undo()
        for i in indices:
            if 0 <= i < len(self._notes):
                n = self._notes[i]
                n.time_beats = round(n.time_beats / grid) * grid
        self._notes.sort(key=lambda n: n.time_beats)

    def set_notes_velocity(self, indices: list[int], velocity: int) -> None:
        """Set velocity of notes at given indices."""
        if not indices:
            return
        self._push_undo()
        vel = max(1, min(127, velocity))
        for i in indices:
            if 0 <= i < len(self._notes):
                self._notes[i].velocity = vel

    def delete_items(
        self, note_indices: list[int], rest_indices: list[int],
    ) -> None:
        """Delete notes and rests in one undo step."""
        if not note_indices and not rest_indices:
            return
        self._push_undo()
        if note_indices:
            to_remove = set(note_indices)
            self._notes = [n for i, n in enumerate(self._notes) if i not in to_remove]
        if rest_indices:
            to_remove = set(rest_indices)
            self._rests = [r for i, r in enumerate(self._rests) if i not in to_remove]

    def clear(self) -> None:
        if self._notes or self._rests:
            self._push_undo()
            self._notes.clear()
            self._rests.clear()
            self._cursor_beats = 0.0

    # ── Selection / Clipboard ───────────────────────────────

    def notes_in_track(self, track: int) -> list[BeatNote]:
        return [n for n in self._notes if n.track == track]

    def rests_in_track(self, track: int) -> list[BeatRest]:
        return [r for r in self._rests if r.track == track]

    def note_indices_in_rect(
        self, t0: float, t1: float, n0: int, n1: int,
    ) -> list[int]:
        """Return indices of notes within the given time and pitch rectangle."""
        result = []
        for i, n in enumerate(self._notes):
            if n.time_beats >= t0 and n.time_beats < t1 and n0 <= n.note <= n1:
                result.append(i)
        return result

    def rest_indices_in_rect(self, t0: float, t1: float) -> list[int]:
        """Return indices of rests within the given time rectangle."""
        result = []
        for i, r in enumerate(self._rests):
            if r.time_beats >= t0 and r.time_beats < t1:
                result.append(i)
        return result

    def copy_items(
        self, note_indices: list[int], rest_indices: list[int],
    ) -> None:
        """Copy mixed notes + rests to clipboard."""
        items: list[BeatItem] = []
        for i in note_indices:
            if 0 <= i < len(self._notes):
                items.append(copy.copy(self._notes[i]))
        for i in rest_indices:
            if 0 <= i < len(self._rests):
                items.append(copy.copy(self._rests[i]))
        if not items:
            return
        min_time = min(it.time_beats for it in items)
        for it in items:
            it.time_beats -= min_time
        self._clipboard = items

    def copy_notes(self, indices: list[int]) -> None:
        if not indices:
            return
        items = [copy.copy(self._notes[i]) for i in indices if 0 <= i < len(self._notes)]
        if not items:
            return
        # Normalize: make earliest note start at time 0
        min_time = min(it.time_beats for it in items)
        for it in items:
            it.time_beats -= min_time
        self._clipboard = items

    def paste_at_cursor(self) -> None:
        if not self._clipboard:
            return
        self._push_undo()
        for item in self._clipboard:
            new = copy.copy(item)
            new.time_beats += self._cursor_beats
            new.track = self._active_track
            if isinstance(new, BeatNote):
                self._notes.append(new)
            elif isinstance(new, BeatRest):
                self._rests.append(new)
        self._notes.sort(key=lambda n: n.time_beats)
        self._rests.sort(key=lambda r: r.time_beats)

    # ── Conversion ──────────────────────────────────────────

    def _beats_to_seconds(self, beats: float) -> float:
        return beats * (60.0 / self._tempo_bpm)

    def _seconds_to_beats(self, seconds: float) -> float:
        return seconds / (60.0 / self._tempo_bpm)

    def to_midi_file_events(self) -> list:
        """Convert all notes to MidiFileEvent list for playback."""
        from .midi_file_player import MidiFileEvent

        result = []
        for n in self._notes:
            # Skip muted tracks
            if self._tracks[n.track].muted:
                continue
            t = self._beats_to_seconds(n.time_beats)
            dur = self._beats_to_seconds(n.duration_beats)
            ch = self._tracks[n.track].channel if n.track < len(self._tracks) else 0
            result.append(MidiFileEvent(
                time_seconds=t,
                event_type="note_on",
                note=n.note,
                velocity=n.velocity,
                track=n.track,
                channel=ch,
            ))
            result.append(MidiFileEvent(
                time_seconds=t + dur,
                event_type="note_off",
                note=n.note,
                velocity=0,
                track=n.track,
                channel=ch,
            ))
        result.sort(key=lambda e: (e.time_seconds, 0 if e.event_type == "note_off" else 1))
        return result

    def to_recorded_events(self) -> list:
        """Convert to RecordedEvent list for MidiWriter."""
        from .midi_recorder import RecordedEvent

        result = []
        for n in self._notes:
            if self._tracks[n.track].muted:
                continue
            t = self._beats_to_seconds(n.time_beats)
            dur = self._beats_to_seconds(n.duration_beats)
            result.append(RecordedEvent(
                timestamp=t,
                event_type="note_on",
                note=n.note,
                velocity=n.velocity,
            ))
            result.append(RecordedEvent(
                timestamp=t + dur,
                event_type="note_off",
                note=n.note,
                velocity=0,
            ))
        result.sort(key=lambda e: e.timestamp)
        return result

    @classmethod
    def from_midi_file_events(
        cls,
        events: list,
        tempo_bpm: float = 120.0,
        time_signature: tuple[int, int] = (4, 4),
    ) -> EditorSequence:
        """Build an EditorSequence by pairing note_on/note_off events."""
        seq = cls(tempo_bpm=tempo_bpm, time_signature=time_signature, num_tracks=4)
        sec_per_beat = 60.0 / tempo_bpm

        # Pair note_on → note_off
        pending: dict[tuple[int, int], tuple[float, int, int]] = {}
        for evt in events:
            key = (evt.note, getattr(evt, "track", 0))
            if evt.event_type == "note_on" and evt.velocity > 0:
                pending[key] = (evt.time_seconds, evt.velocity, getattr(evt, "track", 0))
            elif evt.event_type == "note_off" or (
                evt.event_type == "note_on" and evt.velocity == 0
            ):
                if key in pending:
                    on_time, vel, track = pending.pop(key)
                    dur_sec = max(0.01, evt.time_seconds - on_time)
                    seq._notes.append(BeatNote(
                        time_beats=on_time / sec_per_beat,
                        duration_beats=dur_sec / sec_per_beat,
                        note=evt.note,
                        velocity=vel,
                        track=min(track, len(seq._tracks) - 1),
                    ))

        # Remaining unpaired note_on → default duration
        for (note, track), (t, vel, trk) in pending.items():
            seq._notes.append(BeatNote(
                time_beats=t / sec_per_beat,
                duration_beats=0.5,
                note=note,
                velocity=vel,
                track=min(trk, len(seq._tracks) - 1),
            ))

        seq._notes.sort(key=lambda n: n.time_beats)
        return seq

    # ── Project file serialization ──────────────────────────

    def to_project_dict(self) -> dict:
        return {
            "version": 1,
            "tempo_bpm": self._tempo_bpm,
            "time_signature": list(self._time_signature),
            "cursor_beats": self._cursor_beats,
            "active_track": self._active_track,
            "step_label": self._step_label,
            "tracks": [
                {
                    "name": t.name,
                    "color": t.color,
                    "channel": t.channel,
                    "muted": t.muted,
                    "solo": t.solo,
                }
                for t in self._tracks
            ],
            "notes": [
                {
                    "time": n.time_beats,
                    "duration": n.duration_beats,
                    "note": n.note,
                    "velocity": n.velocity,
                    "track": n.track,
                }
                for n in self._notes
            ],
            "rests": [
                {
                    "time": r.time_beats,
                    "duration": r.duration_beats,
                    "track": r.track,
                }
                for r in self._rests
            ],
        }

    @classmethod
    def from_project_dict(cls, data: dict) -> EditorSequence:
        ts = tuple(data.get("time_signature", [4, 4]))
        tracks_data = data.get("tracks", [])
        seq = cls(
            tempo_bpm=data.get("tempo_bpm", 120.0),
            time_signature=(ts[0], ts[1]),
            num_tracks=0,
        )
        for td in tracks_data:
            seq._tracks.append(Track(
                name=td.get("name", ""),
                color=td.get("color", "#00F0FF"),
                channel=td.get("channel", 0),
                muted=td.get("muted", False),
                solo=td.get("solo", False),
            ))
        if not seq._tracks:
            seq._tracks.append(Track(name="Track 1"))

        seq._cursor_beats = data.get("cursor_beats", 0.0)
        seq._active_track = data.get("active_track", 0)
        label = data.get("step_label", "1/4")
        seq.set_step_duration(label)

        for nd in data.get("notes", []):
            seq._notes.append(BeatNote(
                time_beats=nd["time"],
                duration_beats=nd["duration"],
                note=nd["note"],
                velocity=nd.get("velocity", 100),
                track=nd.get("track", 0),
            ))
        for rd in data.get("rests", []):
            seq._rests.append(BeatRest(
                time_beats=rd["time"],
                duration_beats=rd["duration"],
                track=rd.get("track", 0),
            ))

        seq._notes.sort(key=lambda n: n.time_beats)
        seq._rests.sort(key=lambda r: r.time_beats)
        return seq
