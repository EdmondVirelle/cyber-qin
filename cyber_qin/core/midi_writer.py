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
