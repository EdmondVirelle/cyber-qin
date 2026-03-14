"""System-wide hotkey listener using Win32 RegisterHotKey.

Registers F6 as a global panic-stop key that works even when the game
window has focus.  Runs a dedicated daemon thread that pumps the Windows
message loop.  On non-Windows platforms the class is a harmless no-op.
"""

from __future__ import annotations

import logging
import sys
import threading

from PyQt6.QtCore import QObject, pyqtSignal

log = logging.getLogger(__name__)

# Win32 constants
_MOD_NOREPEAT = 0x4000
_VK_F6 = 0x75
_WM_HOTKEY = 0x0312
_HOTKEY_ID = 1  # arbitrary unique ID for our single hotkey


class GlobalHotkey(QObject):
    """Register a system-wide F6 hotkey and emit *triggered* when pressed.

    Usage::

        hotkey = GlobalHotkey()
        hotkey.triggered.connect(my_stop_function)
        hotkey.start()
        # ... later ...
        hotkey.stop()

    The hotkey works even when the application window does not have focus,
    which is essential for stopping playback while a game is in the foreground.
    """

    triggered = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: threading.Thread | None = None
        self._running = False
        self._thread_id: int | None = None  # Win32 thread ID for PostThreadMessage

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start listening for the global F6 hotkey."""
        if sys.platform != "win32":
            log.info("GlobalHotkey: skipping on non-Windows platform")
            return
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._message_loop,
            name="GlobalHotkey-F6",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Unregister the hotkey and stop the listener thread."""
        if not self._running:
            return
        self._running = False

        # Post WM_QUIT to unblock GetMessage in the worker thread
        if self._thread_id is not None:
            try:
                import ctypes

                ctypes.windll.user32.PostThreadMessageW(  # type: ignore[attr-defined]
                    self._thread_id,
                    0x0012,
                    0,
                    0,  # WM_QUIT
                )
            except Exception:
                pass

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._thread_id = None

    # ------------------------------------------------------------------
    # Internal: runs on the dedicated thread
    # ------------------------------------------------------------------

    def _message_loop(self) -> None:
        """Register the hotkey and pump the Win32 message loop."""
        import ctypes
        import ctypes.wintypes

        user32 = ctypes.windll.user32      # type: ignore[attr-defined]
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

        self._thread_id = kernel32.GetCurrentThreadId()

        # Register F6 as a global hotkey (MOD_NOREPEAT prevents auto-repeat)
        if not user32.RegisterHotKey(None, _HOTKEY_ID, _MOD_NOREPEAT, _VK_F6):
            log.warning(
                "GlobalHotkey: failed to register F6 (error %d). "
                "Another application may have claimed it.",
                kernel32.GetLastError(),
            )
            self._running = False
            return

        log.info("GlobalHotkey: F6 registered as panic-stop key")

        msg = ctypes.wintypes.MSG()
        try:
            while self._running:
                # GetMessage blocks until a message arrives; returns 0 for WM_QUIT
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result <= 0:
                    break  # WM_QUIT or error
                if msg.message == _WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                    log.info("GlobalHotkey: F6 pressed — panic stop!")
                    self.triggered.emit()
        finally:
            user32.UnregisterHotKey(None, _HOTKEY_ID)
            log.info("GlobalHotkey: F6 unregistered")
