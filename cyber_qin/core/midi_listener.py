"""MIDI device enumeration and callback-based event capture using mido/rtmidi."""

from __future__ import annotations

import logging
from collections.abc import Callable

import mido

log = logging.getLogger(__name__)

# Only process these MIDI message types
_ACCEPTED_TYPES = {"note_on", "note_off"}


class MidiListener:
    """Enumerates MIDI input ports and delivers note events via callback.

    The callback runs on the rtmidi C++ thread for minimum latency.
    """

    def __init__(self) -> None:
        self._port: mido.ports.BaseInput | None = None
        self._port_name: str | None = None
        self._callback: Callable[[str, int, int], None] | None = None
        self._on_disconnect: Callable[[], None] | None = None

    @staticmethod
    def list_ports() -> list[str]:
        """Return available MIDI input port names."""
        return mido.get_input_names()  # type: ignore[no-any-return]

    @property
    def connected(self) -> bool:
        return self._port is not None and not getattr(self._port, "closed", True)

    @property
    def port_name(self) -> str | None:
        return self._port_name

    def open(
        self,
        port_name: str,
        callback: Callable[[str, int, int], None],
        on_disconnect: Callable[[], None] | None = None,
    ) -> None:
        """Open a MIDI port and register a callback.

        Args:
            port_name: The MIDI input port name to open.
            callback: Called with (event_type, note, velocity) on the rtmidi thread.
                      event_type is 'note_on' or 'note_off'.
            on_disconnect: Called when the port is unexpectedly closed.
        """
        self.close()
        self._callback = callback
        self._on_disconnect = on_disconnect
        self._port_name = port_name
        try:
            self._port = mido.open_input(port_name, callback=self._on_message)
            log.info("Opened MIDI port: %s", port_name)
        except (OSError, RuntimeError):
            self._port = None
            self._port_name = None
            raise

    def close(self) -> None:
        """Close the current MIDI port if open."""
        if self._port is not None:
            try:
                self._port.close()
            except Exception:
                pass
            self._port = None
            self._port_name = None
            log.info("MIDI port closed")

    def _on_message(self, msg: mido.Message) -> None:
        """Internal callback from rtmidi thread. Filters and dispatches."""
        if self._callback is None:
            return
        try:
            if msg.type == "note_on" and msg.velocity > 0:
                self._callback("note_on", msg.note, msg.velocity)
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                self._callback("note_off", msg.note, 0)
            # Silently ignore all other message types (aftertouch, sysex, etc.)
        except (AttributeError, IndexError, TypeError, ValueError):
            log.exception("Error in MIDI callback")
