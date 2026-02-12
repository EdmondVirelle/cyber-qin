"""Save recorded MIDI events as .mid files.

Converts RecordedEvent lists to standard MIDI files via mido.
"""

from __future__ import annotations

from pathlib import Path

import mido

from .constants import DEFAULT_RECORDING_TEMPO, RECORDING_TICKS_PER_BEAT
from .midi_recorder import RecordedEvent


class MidiWriter:
    """Write RecordedEvent sequences to .mid files."""

    @staticmethod
    def save(
        events: list[RecordedEvent],
        file_path: str,
        tempo_bpm: float = DEFAULT_RECORDING_TEMPO,
    ) -> None:
        """Save recorded events as a Type 0 MIDI file.

        Args:
            events: List of RecordedEvent from MidiRecorder.
            file_path: Output .mid file path.
            tempo_bpm: Tempo in BPM (default 120).
        """
        if not events:
            return

        mid = mido.MidiFile(ticks_per_beat=RECORDING_TICKS_PER_BEAT)
        track = mido.MidiTrack()
        mid.tracks.append(track)

        tempo = mido.bpm2tempo(tempo_bpm)
        track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

        # Convert timestamps to delta ticks
        prev_tick = 0
        for evt in sorted(events, key=lambda e: e.timestamp):
            abs_tick = mido.second2tick(
                evt.timestamp, RECORDING_TICKS_PER_BEAT, tempo,
            )
            delta = max(0, int(abs_tick) - prev_tick)

            if evt.event_type == "note_on":
                track.append(mido.Message(
                    "note_on", note=evt.note, velocity=evt.velocity, time=delta,
                ))
            elif evt.event_type == "note_off":
                track.append(mido.Message(
                    "note_off", note=evt.note, velocity=0, time=delta,
                ))

            prev_tick = int(abs_tick)

        track.append(mido.MetaMessage("end_of_track", time=0))

        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        mid.save(file_path)

    @staticmethod
    def recorded_to_file_events(events: list[RecordedEvent]) -> list:
        """Convert RecordedEvent list to MidiFileEvent list for preview/preprocessing.

        Returns a list of MidiFileEvent sorted by time.
        """
        from .midi_file_player import MidiFileEvent

        result: list[MidiFileEvent] = []
        for evt in events:
            result.append(MidiFileEvent(
                time_seconds=evt.timestamp,
                event_type=evt.event_type,
                note=evt.note,
                velocity=evt.velocity,
                track=0,
                channel=0,
            ))
        result.sort(key=lambda e: (e.time_seconds, 0 if e.event_type == "note_off" else 1))
        return result

    @staticmethod
    def save_multitrack(
        events: list,
        file_path: str,
        tempo_bpm: float = DEFAULT_RECORDING_TEMPO,
        track_names: list[str] | None = None,
        track_channels: list[int] | None = None,
    ) -> None:
        """Save MidiFileEvent list as a Type 1 (multi-track) MIDI file.

        Args:
            events: List of MidiFileEvent with track/channel fields.
            file_path: Output .mid file path.
            tempo_bpm: Tempo in BPM.
            track_names: Optional list of track names for metadata.
            track_channels: Optional list of MIDI channels per track.
        """
        if not events:
            return

        from collections import defaultdict

        tpb = RECORDING_TICKS_PER_BEAT
        tempo = mido.bpm2tempo(tempo_bpm)

        # Group events by track index
        by_track: dict[int, list] = defaultdict(list)
        for evt in sorted(events, key=lambda e: (e.time_seconds, 0 if e.event_type == "note_off" else 1)):
            by_track[getattr(evt, "track", 0)].append(evt)

        track_indices = sorted(by_track.keys())

        # If only one track, fall back to Type 0
        if len(track_indices) <= 1:
            mid = mido.MidiFile(ticks_per_beat=tpb)
            trk = mido.MidiTrack()
            mid.tracks.append(trk)
            trk.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

            name = (track_names[track_indices[0]] if track_names and track_indices
                    and track_indices[0] < len(track_names) else "")
            if name:
                trk.append(mido.MetaMessage("track_name", name=name, time=0))

            prev_tick = 0
            for evt in by_track.get(track_indices[0] if track_indices else 0, []):
                abs_tick = int(mido.second2tick(evt.time_seconds, tpb, tempo))
                delta = max(0, abs_tick - prev_tick)
                ch = getattr(evt, "channel", 0) & 0x0F
                if evt.event_type == "note_on":
                    trk.append(mido.Message("note_on", note=evt.note, velocity=evt.velocity, time=delta, channel=ch))
                elif evt.event_type == "note_off":
                    trk.append(mido.Message("note_off", note=evt.note, velocity=0, time=delta, channel=ch))
                prev_tick = abs_tick

            trk.append(mido.MetaMessage("end_of_track", time=0))
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            mid.save(file_path)
            return

        # Type 1: conductor track + one track per instrument
        mid = mido.MidiFile(type=1, ticks_per_beat=tpb)

        # Track 0: conductor (tempo only)
        conductor = mido.MidiTrack()
        mid.tracks.append(conductor)
        conductor.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
        conductor.append(mido.MetaMessage("end_of_track", time=0))

        # One track per instrument
        for ti in track_indices:
            trk = mido.MidiTrack()
            mid.tracks.append(trk)

            name = track_names[ti] if track_names and ti < len(track_names) else ""
            if name:
                trk.append(mido.MetaMessage("track_name", name=name, time=0))

            ch = (track_channels[ti] if track_channels and ti < len(track_channels) else ti) & 0x0F

            prev_tick = 0
            for evt in by_track[ti]:
                abs_tick = int(mido.second2tick(evt.time_seconds, tpb, tempo))
                delta = max(0, abs_tick - prev_tick)
                if evt.event_type == "note_on":
                    trk.append(mido.Message("note_on", note=evt.note, velocity=evt.velocity, time=delta, channel=ch))
                elif evt.event_type == "note_off":
                    trk.append(mido.Message("note_off", note=evt.note, velocity=0, time=delta, channel=ch))
                prev_tick = abs_tick

            trk.append(mido.MetaMessage("end_of_track", time=0))

        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        mid.save(file_path)

