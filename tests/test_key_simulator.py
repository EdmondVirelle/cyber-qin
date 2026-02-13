"""Tests for KeySimulator: press/release tracking, stuck-key detection.

These tests mock SendInput to avoid actual key events.
"""

import time
from unittest.mock import patch

import pytest

from cyber_qin.core.constants import SCAN, Modifier
from cyber_qin.core.key_mapper import KeyMapping
from cyber_qin.core.key_simulator import KeySimulator


@pytest.fixture
def sim():
    """Create a KeySimulator with SendInput mocked out."""
    with patch("cyber_qin.core.key_simulator._send") as mock_send:
        simulator = KeySimulator()
        simulator._mock_send = mock_send
        yield simulator


def _mapping(key: str, mod: Modifier = Modifier.NONE) -> KeyMapping:
    label = (
        key if mod == Modifier.NONE else f"{'Shift' if mod == Modifier.SHIFT else 'Ctrl'}+{key}"
    )
    return KeyMapping(scan_code=SCAN[key], modifier=mod, label=label)


class TestPressRelease:
    def test_press_natural_key(self, sim):
        mapping = _mapping("A")
        sim.press(60, mapping)
        assert 60 in sim.active_notes
        assert sim._mock_send.call_count == 1  # Only key down

    def test_press_shift_key(self, sim):
        mapping = _mapping("A", Modifier.SHIFT)
        sim.press(61, mapping)
        assert 61 in sim.active_notes
        # Modifier down + key down + modifier up = 1 batched call
        assert sim._mock_send.call_count == 1

    def test_press_ctrl_key(self, sim):
        mapping = _mapping("D", Modifier.CTRL)
        sim.press(63, mapping)
        assert 63 in sim.active_notes
        assert sim._mock_send.call_count == 1

    def test_release_returns_mapping(self, sim):
        mapping = _mapping("A")
        sim.press(60, mapping)
        result = sim.release(60)
        assert result == mapping
        assert 60 not in sim.active_notes

    def test_release_unknown_note_returns_none(self, sim):
        assert sim.release(99) is None

    def test_release_with_modifier(self, sim):
        mapping = _mapping("A", Modifier.SHIFT)
        sim.press(61, mapping)
        sim._mock_send.reset_mock()
        sim.release(61)
        # Only key up — modifier was already released in press()
        assert sim._mock_send.call_count == 1

    def test_multiple_notes(self, sim):
        sim.press(60, _mapping("A"))
        sim.press(64, _mapping("D"))
        assert sorted(sim.active_notes) == [60, 64]
        sim.release(60)
        assert sim.active_notes == [64]


class TestReleaseAll:
    def test_release_all_clears_active(self, sim):
        sim.press(60, _mapping("A"))
        sim.press(64, _mapping("D"))
        sim.press(67, _mapping("G"))
        sim.release_all()
        assert sim.active_notes == []


class TestStuckKeys:
    def test_no_stuck_keys(self, sim):
        sim.press(60, _mapping("A"))
        assert sim.check_stuck_keys() == []

    def test_stuck_key_detected(self, sim):
        mapping = _mapping("A")
        sim.press(60, mapping)
        # Manipulate the timestamp to simulate a stuck key
        sim._active[60] = (mapping, time.monotonic() - 15.0)
        stuck = sim.check_stuck_keys()
        assert 60 in stuck
        assert 60 not in sim.active_notes

    def test_stuck_key_only_old_keys(self, sim):
        old = _mapping("A")
        new = _mapping("D")
        sim.press(60, old)
        sim.press(64, new)
        # Only make note 60 old
        sim._active[60] = (old, time.monotonic() - 15.0)
        stuck = sim.check_stuck_keys()
        assert stuck == [60]
        assert 64 in sim.active_notes
