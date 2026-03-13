"""Tests for the GlobalHotkey module."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from cyber_qin.core.global_hotkey import GlobalHotkey


class TestGlobalHotkey:
    """Tests for GlobalHotkey lifecycle and signal emission."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure QApplication exists for signal/slot."""

    def test_create_without_crash(self):
        """GlobalHotkey can be instantiated."""
        hotkey = GlobalHotkey()
        assert hotkey is not None

    def test_stop_before_start_is_safe(self):
        """Calling stop() before start() should not raise."""
        hotkey = GlobalHotkey()
        hotkey.stop()  # should be a no-op

    def test_stop_idempotent(self):
        """Calling stop() twice should not raise."""
        hotkey = GlobalHotkey()
        hotkey.stop()
        hotkey.stop()

    @pytest.mark.skipif(sys.platform != "win32", reason="Win32 only")
    def test_start_and_stop(self):
        """Start and stop the hotkey listener without crashing."""
        hotkey = GlobalHotkey()
        hotkey.start()
        assert hotkey._running is True
        assert hotkey._thread is not None
        hotkey.stop()
        assert hotkey._running is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Win32 only")
    def test_start_idempotent(self):
        """Calling start() twice should not spawn a second thread."""
        hotkey = GlobalHotkey()
        hotkey.start()
        thread1 = hotkey._thread
        hotkey.start()  # second call
        assert hotkey._thread is thread1  # same thread
        hotkey.stop()

    @pytest.mark.skipif(sys.platform == "win32", reason="Non-Windows test")
    def test_start_noop_on_non_windows(self):
        """On non-Windows, start() should be a no-op."""
        hotkey = GlobalHotkey()
        hotkey.start()
        assert hotkey._running is False
        assert hotkey._thread is None

    @pytest.mark.skipif(sys.platform != "win32", reason="Win32 only")
    def test_signal_emission_on_hotkey_message(self):
        """Verify triggered signal is emitted when WM_HOTKEY is received."""
        hotkey = GlobalHotkey()
        signals = []
        hotkey.triggered.connect(lambda: signals.append(True))

        # Directly call the signal to verify wiring (integration test
        # would require actually pressing F6, which we can't do in CI)
        hotkey.triggered.emit()
        assert len(signals) == 1
