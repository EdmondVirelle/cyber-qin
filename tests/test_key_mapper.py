"""Tests for KeyMapper: 36-key mapping correctness, transpose, and bounds."""

import pytest

from cyber_qin.core.constants import MIDI_NOTE_MAX, MIDI_NOTE_MIN, SCAN, Modifier
from cyber_qin.core.key_mapper import _BASE_MAP, KeyMapper


class TestBaseMapping:
    """Verify all 36 notes are mapped correctly."""

    def test_all_36_notes_present(self):
        assert len(_BASE_MAP) == 36

    def test_midi_range_coverage(self):
        for note in range(MIDI_NOTE_MIN, MIDI_NOTE_MAX + 1):
            assert note in _BASE_MAP, f"MIDI note {note} missing from mapping"

    @pytest.mark.parametrize("midi,key,mod", [
        # Low octave naturals
        (48, "Z", Modifier.NONE),
        (50, "X", Modifier.NONE),
        (52, "C", Modifier.NONE),
        (53, "V", Modifier.NONE),
        (55, "B", Modifier.NONE),
        (57, "N", Modifier.NONE),
        (59, "M", Modifier.NONE),
        # Mid octave naturals
        (60, "A", Modifier.NONE),
        (62, "S", Modifier.NONE),
        (64, "D", Modifier.NONE),
        (65, "F", Modifier.NONE),
        (67, "G", Modifier.NONE),
        (69, "H", Modifier.NONE),
        (71, "J", Modifier.NONE),
        # High octave naturals
        (72, "Q", Modifier.NONE),
        (74, "W", Modifier.NONE),
        (76, "E", Modifier.NONE),
        (77, "R", Modifier.NONE),
        (79, "T", Modifier.NONE),
        (81, "Y", Modifier.NONE),
        (83, "U", Modifier.NONE),
    ])
    def test_natural_notes(self, midi, key, mod):
        m = _BASE_MAP[midi]
        assert m.scan_code == SCAN[key]
        assert m.modifier == mod

    @pytest.mark.parametrize("midi,key,mod", [
        # Sharps (Shift)
        (49, "Z", Modifier.SHIFT),   # C#3
        (54, "V", Modifier.SHIFT),   # F#3
        (56, "B", Modifier.SHIFT),   # G#3
        (61, "A", Modifier.SHIFT),   # C#4
        (66, "F", Modifier.SHIFT),   # F#4
        (68, "G", Modifier.SHIFT),   # G#4
        (73, "Q", Modifier.SHIFT),   # C#5
        (78, "R", Modifier.SHIFT),   # F#5
        (80, "T", Modifier.SHIFT),   # G#5
    ])
    def test_sharp_notes(self, midi, key, mod):
        m = _BASE_MAP[midi]
        assert m.scan_code == SCAN[key]
        assert m.modifier == mod

    @pytest.mark.parametrize("midi,key,mod", [
        # Flats (Ctrl)
        (51, "C", Modifier.CTRL),    # Eb3
        (58, "M", Modifier.CTRL),    # Bb3
        (63, "D", Modifier.CTRL),    # Eb4
        (70, "J", Modifier.CTRL),    # Bb4
        (75, "E", Modifier.CTRL),    # Eb5
        (82, "U", Modifier.CTRL),    # Bb5
    ])
    def test_flat_notes(self, midi, key, mod):
        m = _BASE_MAP[midi]
        assert m.scan_code == SCAN[key]
        assert m.modifier == mod


class TestKeyMapperLookup:
    """Test lookup with transpose and out-of-range handling."""

    def test_lookup_no_transpose(self):
        km = KeyMapper(transpose=0)
        result = km.lookup(60)
        assert result is not None
        assert result.scan_code == SCAN["A"]

    def test_lookup_transpose_up_one_octave(self):
        km = KeyMapper(transpose=12)
        # MIDI 48 + 12 = 60 → A
        result = km.lookup(48)
        assert result is not None
        assert result.scan_code == SCAN["A"]

    def test_lookup_transpose_down_one_octave(self):
        km = KeyMapper(transpose=-12)
        # MIDI 72 - 12 = 60 → A
        result = km.lookup(72)
        assert result is not None
        assert result.scan_code == SCAN["A"]

    def test_lookup_out_of_range_low(self):
        km = KeyMapper(transpose=0)
        assert km.lookup(20) is None

    def test_lookup_out_of_range_high(self):
        km = KeyMapper(transpose=0)
        assert km.lookup(100) is None

    def test_lookup_boundary_min(self):
        km = KeyMapper(transpose=0)
        result = km.lookup(48)
        assert result is not None
        assert result.scan_code == SCAN["Z"]

    def test_lookup_boundary_max(self):
        km = KeyMapper(transpose=0)
        result = km.lookup(83)
        assert result is not None
        assert result.scan_code == SCAN["U"]

    def test_transpose_property(self):
        km = KeyMapper()
        assert km.transpose == 0
        km.transpose = 12
        assert km.transpose == 12


class TestNoteName:
    def test_middle_c(self):
        assert KeyMapper.note_name(60) == "C4"

    def test_a440(self):
        assert KeyMapper.note_name(69) == "A4"

    def test_sharp(self):
        assert KeyMapper.note_name(61) == "C#4"

    def test_flat(self):
        assert KeyMapper.note_name(63) == "Eb4"


class TestAllMappings:
    def test_returns_dict_copy(self):
        m1 = KeyMapper.all_mappings()
        m2 = KeyMapper.all_mappings()
        assert m1 == m2
        assert m1 is not m2
