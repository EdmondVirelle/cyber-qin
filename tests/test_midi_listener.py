"""Tests for cyber_qin.core.midi_listener — MidiListener with mocked mido."""

from __future__ import annotations

from unittest import mock

import pytest


class TestMidiListener:
    def _make_listener(self):
        from cyber_qin.core.midi_listener import MidiListener
        return MidiListener()

    def test_initial_state(self):
        listener = self._make_listener()
        assert listener.connected is False
        assert listener.port_name is None

    def test_list_ports(self):
        with mock.patch("mido.get_input_names", return_value=["Port A", "Port B"]):
            from cyber_qin.core.midi_listener import MidiListener
            ports = MidiListener.list_ports()
            assert ports == ["Port A", "Port B"]

    def test_open_success(self):
        listener = self._make_listener()
        fake_port = mock.MagicMock()
        fake_port.closed = False
        cb = mock.MagicMock()
        with mock.patch("mido.open_input", return_value=fake_port) as mock_open:
            listener.open("Test Port", cb)
            mock_open.assert_called_once()
            assert listener.connected is True
            assert listener.port_name == "Test Port"

    def test_open_failure(self):
        listener = self._make_listener()
        cb = mock.MagicMock()
        with mock.patch("mido.open_input", side_effect=OSError("nope")):
            with pytest.raises(OSError):
                listener.open("Bad Port", cb)
            assert listener.connected is False
            assert listener.port_name is None

    def test_close(self):
        listener = self._make_listener()
        fake_port = mock.MagicMock()
        fake_port.closed = False
        with mock.patch("mido.open_input", return_value=fake_port):
            listener.open("Port", mock.MagicMock())
        listener.close()
        fake_port.close.assert_called_once()
        assert listener.connected is False
        assert listener.port_name is None

    def test_close_when_not_open(self):
        listener = self._make_listener()
        listener.close()  # Should not raise

    def test_close_exception_swallowed(self):
        listener = self._make_listener()
        fake_port = mock.MagicMock()
        fake_port.closed = False
        fake_port.close.side_effect = OSError("fail")
        with mock.patch("mido.open_input", return_value=fake_port):
            listener.open("Port", mock.MagicMock())
        listener.close()  # Should not raise

    def test_on_message_note_on(self):
        listener = self._make_listener()
        cb = mock.MagicMock()
        fake_port = mock.MagicMock()
        fake_port.closed = False
        with mock.patch("mido.open_input", return_value=fake_port):
            listener.open("Port", cb)
        msg = mock.MagicMock()
        msg.type = "note_on"
        msg.note = 60
        msg.velocity = 100
        listener._on_message(msg)
        cb.assert_called_once_with("note_on", 60, 100)

    def test_on_message_note_off(self):
        listener = self._make_listener()
        cb = mock.MagicMock()
        fake_port = mock.MagicMock()
        fake_port.closed = False
        with mock.patch("mido.open_input", return_value=fake_port):
            listener.open("Port", cb)
        msg = mock.MagicMock()
        msg.type = "note_off"
        msg.note = 60
        msg.velocity = 0
        listener._on_message(msg)
        cb.assert_called_once_with("note_off", 60, 0)

    def test_on_message_note_on_velocity_zero(self):
        """note_on with velocity=0 should be treated as note_off."""
        listener = self._make_listener()
        cb = mock.MagicMock()
        fake_port = mock.MagicMock()
        fake_port.closed = False
        with mock.patch("mido.open_input", return_value=fake_port):
            listener.open("Port", cb)
        msg = mock.MagicMock()
        msg.type = "note_on"
        msg.note = 60
        msg.velocity = 0
        listener._on_message(msg)
        cb.assert_called_once_with("note_off", 60, 0)

    def test_on_message_ignored_type(self):
        """Non note_on/note_off types should be silently ignored."""
        listener = self._make_listener()
        cb = mock.MagicMock()
        fake_port = mock.MagicMock()
        fake_port.closed = False
        with mock.patch("mido.open_input", return_value=fake_port):
            listener.open("Port", cb)
        msg = mock.MagicMock()
        msg.type = "control_change"
        listener._on_message(msg)
        cb.assert_not_called()

    def test_on_message_no_callback(self):
        listener = self._make_listener()
        msg = mock.MagicMock()
        msg.type = "note_on"
        msg.note = 60
        msg.velocity = 100
        listener._on_message(msg)  # Should not raise

    def test_on_message_callback_exception(self):
        """Callback errors should be swallowed."""
        listener = self._make_listener()
        cb = mock.MagicMock(side_effect=ValueError("boom"))
        fake_port = mock.MagicMock()
        fake_port.closed = False
        with mock.patch("mido.open_input", return_value=fake_port):
            listener.open("Port", cb)
        msg = mock.MagicMock()
        msg.type = "note_on"
        msg.note = 60
        msg.velocity = 100
        listener._on_message(msg)  # Should not raise

    def test_reopen_closes_previous(self):
        """Opening again should close the previous port first."""
        listener = self._make_listener()
        port1 = mock.MagicMock()
        port1.closed = False
        port2 = mock.MagicMock()
        port2.closed = False
        with mock.patch("mido.open_input", side_effect=[port1, port2]):
            listener.open("Port1", mock.MagicMock())
            listener.open("Port2", mock.MagicMock())
        port1.close.assert_called_once()
        assert listener.port_name == "Port2"
