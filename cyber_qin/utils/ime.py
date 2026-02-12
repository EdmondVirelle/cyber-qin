"""Input method (IME) state detection for Windows."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging

log = logging.getLogger(__name__)

_imm32 = ctypes.windll.imm32  # type: ignore[attr-defined]
_user32 = ctypes.windll.user32  # type: ignore[attr-defined]


def is_ime_active() -> bool:
    """Check if a non-English IME is currently active.

    Returns True if an IME conversion mode is enabled on the foreground window,
    which could intercept keystrokes before they reach the game.
    """
    try:
        hwnd = _user32.GetForegroundWindow()
        himc = _imm32.ImmGetContext(hwnd)
        if not himc:
            return False
        try:
            conversion = ctypes.wintypes.DWORD()
            sentence = ctypes.wintypes.DWORD()
            result = _imm32.ImmGetConversionStatus(
                himc,
                ctypes.byref(conversion),
                ctypes.byref(sentence),
            )
            if not result:
                return False
            # IME_CMODE_NATIVE (0x1) means the IME is in native (non-English) mode
            return bool(conversion.value & 0x1)
        finally:
            _imm32.ImmReleaseContext(hwnd, himc)
    except Exception:
        log.exception("Failed to check IME status")
        return False
