"""MusicXML to MIDI converter for importing .xml/.musicxml files."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class MusicXMLNote:
    """Parsed note from MusicXML."""

    pitch: int  # MIDI note number (0-127)
    start_time: float  # Start time in quarter notes
    duration: float  # Duration in quarter notes
    velocity: int = 100  # MIDI velocity (default 100)


class MusicXMLParser:
    """Parse MusicXML files and convert to MIDI-like note sequence."""

    # Pitch class to MIDI semitone offset
    PITCH_CLASS_TO_SEMITONE = {
        "C": 0,
        "D": 2,
        "E": 4,
        "F": 5,
        "G": 7,
        "A": 9,
        "B": 11,
    }

    def __init__(self) -> None:
        self.notes: list[MusicXMLNote] = []
        self.tempo_bpm: int = 120  # Default tempo
        self.time_signature: tuple[int, int] = (4, 4)  # Default 4/4

    def parse_file(self, file_path: str) -> tuple[list[MusicXMLNote], int, tuple[int, int]]:
        """Parse a MusicXML file and return (notes, tempo_bpm, time_signature)."""
        tree = ET.parse(file_path)
        root = tree.getroot()

        self.notes = []
        self.tempo_bpm = 120
        self.time_signature = (4, 4)

        # Parse tempo and time signature from the first measure
        self._parse_attributes(root)

        # Parse all notes from all parts
        for part in root.findall(".//part"):
            self._parse_part(part)

        return self.notes, self.tempo_bpm, self.time_signature

    def _parse_attributes(self, root: ET.Element) -> None:
        """Extract tempo and time signature from attributes."""
        # Find tempo (metronome marking)
        sound = root.find(".//sound[@tempo]")
        if sound is not None:
            tempo_str = sound.get("tempo")
            if tempo_str:
                self.tempo_bpm = int(float(tempo_str))

        # Find time signature
        time_elem = root.find(".//time")
        if time_elem is not None:
            beats = time_elem.find("beats")
            beat_type = time_elem.find("beat-type")
            if beats is not None and beat_type is not None:
                self.time_signature = (int(beats.text or "4"), int(beat_type.text or "4"))

    def _parse_part(self, part: ET.Element) -> None:
        """Parse all measures in a part."""
        current_time = 0.0  # Track current position in quarter notes
        divisions = 1  # Default divisions per quarter note

        for measure in part.findall("measure"):
            # Update divisions if specified in this measure
            attributes = measure.find("attributes")
            if attributes is not None:
                div_elem = attributes.find("divisions")
                if div_elem is not None and div_elem.text:
                    divisions = int(div_elem.text)

            # Parse all notes in this measure
            for note_elem in measure.findall("note"):
                note = self._parse_note(note_elem, current_time, divisions)
                if note is not None:
                    self.notes.append(note)

                # Advance time by note duration (even for rests)
                duration_elem = note_elem.find("duration")
                if duration_elem is not None and duration_elem.text:
                    duration_div = int(duration_elem.text)
                    # Only advance time if this is not a chord note
                    if note_elem.find("chord") is None:
                        current_time += duration_div / divisions

    def _parse_note(
        self, note_elem: ET.Element, current_time: float, divisions: int
    ) -> MusicXMLNote | None:
        """Parse a single note element."""
        # Skip rests
        if note_elem.find("rest") is not None:
            return None

        # Get pitch
        pitch_elem = note_elem.find("pitch")
        if pitch_elem is None:
            return None

        step = pitch_elem.find("step")
        octave = pitch_elem.find("octave")
        if step is None or octave is None or step.text is None or octave.text is None:
            return None

        pitch_class = step.text
        octave_num = int(octave.text)

        # Check for accidentals (alter element)
        alter_elem = pitch_elem.find("alter")
        alter = int(alter_elem.text) if (alter_elem is not None and alter_elem.text) else 0

        # Calculate MIDI note number: (octave + 1) * 12 + pitch_class + alter
        midi_note = (octave_num + 1) * 12 + self.PITCH_CLASS_TO_SEMITONE[pitch_class] + alter

        # Clamp to valid MIDI range
        midi_note = max(0, min(127, midi_note))

        # Get duration
        duration_elem = note_elem.find("duration")
        if duration_elem is None or duration_elem.text is None:
            return None

        duration_div = int(duration_elem.text)
        duration_quarters = duration_div / divisions

        # Get velocity (dynamics)
        velocity = 100  # Default
        dynamics = note_elem.find("notations/dynamics")
        if dynamics is not None:
            # MusicXML dynamics (pp, p, mp, mf, f, ff, etc.)
            # Map to MIDI velocity (approximation)
            if dynamics.find("pp") is not None:
                velocity = 40
            elif dynamics.find("p") is not None:
                velocity = 60
            elif dynamics.find("mp") is not None:
                velocity = 75
            elif dynamics.find("mf") is not None:
                velocity = 90
            elif dynamics.find("f") is not None:
                velocity = 105
            elif dynamics.find("ff") is not None:
                velocity = 120

        return MusicXMLNote(
            pitch=midi_note,
            start_time=current_time,
            duration=duration_quarters,
            velocity=velocity,
        )


def import_musicxml(file_path: str) -> tuple[list[MusicXMLNote], int, tuple[int, int]]:
    """Import a MusicXML file and return (notes, tempo_bpm, time_signature).

    Args:
        file_path: Path to .xml or .musicxml file

    Returns:
        Tuple of (notes, tempo_bpm, time_signature)

    Raises:
        ET.ParseError: If the XML file is malformed
        FileNotFoundError: If the file does not exist
    """
    parser = MusicXMLParser()
    return parser.parse_file(file_path)
