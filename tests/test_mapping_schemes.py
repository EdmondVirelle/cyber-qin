"""Tests for mapping scheme registry and scheme definitions."""

import pytest

from cyber_qin.core.key_mapper import _BASE_MAP
from cyber_qin.core.mapping_schemes import (
    MappingScheme,
    default_scheme_id,
    get_scheme,
    list_schemes,
)


class TestRegistry:
    def test_list_schemes_returns_list(self):
        schemes = list_schemes()
        assert isinstance(schemes, list)
        assert len(schemes) >= 6

    def test_all_schemes_are_mapping_scheme(self):
        for scheme in list_schemes():
            assert isinstance(scheme, MappingScheme)

    def test_get_scheme_by_id(self):
        scheme = get_scheme("wwm_36")
        assert scheme.id == "wwm_36"

    def test_get_scheme_unknown_raises(self):
        with pytest.raises(KeyError):
            get_scheme("nonexistent_scheme")

    def test_default_scheme_id(self):
        sid = default_scheme_id()
        assert sid == "wwm_36"
        # Must be retrievable
        scheme = get_scheme(sid)
        assert scheme is not None

    def test_unique_ids(self):
        schemes = list_schemes()
        ids = [s.id for s in schemes]
        assert len(ids) == len(set(ids))


class TestSchemeIntegrity:
    """Each scheme's key_count should match the mapping dict size."""

    @pytest.mark.parametrize("scheme", list_schemes(), ids=lambda s: s.id)
    def test_key_count_matches_mapping(self, scheme: MappingScheme):
        assert scheme.key_count == len(scheme.mapping), (
            f"{scheme.id}: key_count={scheme.key_count} but mapping has {len(scheme.mapping)} entries"
        )

    @pytest.mark.parametrize("scheme", list_schemes(), ids=lambda s: s.id)
    def test_midi_range_matches_mapping(self, scheme: MappingScheme):
        midi_min, midi_max = scheme.midi_range
        for note in scheme.mapping:
            assert midi_min <= note <= midi_max, (
                f"{scheme.id}: note {note} outside range ({midi_min}, {midi_max})"
            )

    @pytest.mark.parametrize("scheme", list_schemes(), ids=lambda s: s.id)
    def test_rows_times_keys_equals_key_count(self, scheme: MappingScheme):
        if scheme.id == "ff14_37":
            return
        assert scheme.rows * scheme.keys_per_row == scheme.key_count, (
            f"{scheme.id}: {scheme.rows}×{scheme.keys_per_row} != {scheme.key_count}"
        )


class TestWWM36MatchesBaseMap:
    """The wwm_36 scheme should match _BASE_MAP exactly."""

    def test_same_keys(self):
        scheme = get_scheme("wwm_36")
        assert set(scheme.mapping.keys()) == set(_BASE_MAP.keys())

    def test_same_values(self):
        scheme = get_scheme("wwm_36")
        for note, km in _BASE_MAP.items():
            assert scheme.mapping[note] == km, f"Mismatch at MIDI {note}"


class TestFf14Scheme:
    def test_key_count(self):
        scheme = get_scheme("ff14_37")
        assert scheme.key_count == 37

    def test_midi_range(self):
        scheme = get_scheme("ff14_37")
        assert scheme.midi_range == (48, 84)


class TestGeneric24:
    def test_key_count(self):
        scheme = get_scheme("generic_24")
        assert scheme.key_count == 24

    def test_midi_range(self):
        scheme = get_scheme("generic_24")
        assert scheme.midi_range == (48, 71)


class TestGeneric48:
    def test_key_count(self):
        scheme = get_scheme("generic_48")
        assert scheme.key_count == 48

    def test_midi_range(self):
        scheme = get_scheme("generic_48")
        assert scheme.midi_range == (36, 83)


class TestBeginner36:
    def test_key_count(self):
        scheme = get_scheme("beginner_36")
        assert scheme.key_count == 36

    def test_midi_range(self):
        scheme = get_scheme("beginner_36")
        assert scheme.midi_range == (48, 83)

    def test_no_modifiers(self):
        """Beginner scheme must use only Modifier.NONE."""
        from cyber_qin.core.constants import Modifier

        scheme = get_scheme("beginner_36")
        for note, km in scheme.mapping.items():
            assert km.modifier == Modifier.NONE, (
                f"MIDI {note} uses modifier {km.modifier}, expected NONE"
            )

    def test_all_keys_unique(self):
        """Each key should map to exactly one MIDI note (no duplicates)."""
        scheme = get_scheme("beginner_36")
        labels = [km.label for km in scheme.mapping.values()]
        assert len(labels) == len(set(labels)), "Duplicate key labels found"


class TestGeneric88:
    def test_key_count(self):
        scheme = get_scheme("generic_88")
        assert scheme.key_count == 88

    def test_midi_range(self):
        scheme = get_scheme("generic_88")
        assert scheme.midi_range == (21, 108)
