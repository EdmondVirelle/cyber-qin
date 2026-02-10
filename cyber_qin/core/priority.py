"""Thread priority and timer resolution utilities for low-latency playback."""

from __future__ import annotations

import ctypes
import logging
import sys

log = logging.getLogger(__name__)

# Windows thread priority constants
_THREAD_PRIORITY_TIME_CRITICAL = 15


def set_thread_priority_realtime() -> bool:
    """Set the current thread to TIME_CRITICAL priority.

    Returns True on success, False on failure or non-Windows.
    """
    if sys.platform != "win32":
        return False
    try:
        handle = ctypes.windll.kernel32.GetCurrentThread()
        result = ctypes.windll.kernel32.SetThreadPriority(
            handle, _THREAD_PRIORITY_TIME_CRITICAL,
        )
        if result:
            log.debug("Thread priority set to TIME_CRITICAL")
        else:
            log.warning("SetThreadPriority failed")
        return bool(result)
    except Exception:
        log.warning("Failed to set thread priority", exc_info=True)
        return False


def begin_timer_period(period_ms: int = 1) -> bool:
    """Request high-resolution timer (timeBeginPeriod).

    Call end_timer_period() with the same value before exit.
    Returns True on success.
    """
    if sys.platform != "win32":
        return False
    try:
        result = ctypes.windll.winmm.timeBeginPeriod(period_ms)
        success = result == 0  # TIMERR_NOERROR
        if success:
            log.debug("timeBeginPeriod(%d) succeeded", period_ms)
        else:
            log.warning("timeBeginPeriod(%d) returned %d", period_ms, result)
        return success
    except Exception:
        log.warning("timeBeginPeriod failed", exc_info=True)
        return False


def end_timer_period(period_ms: int = 1) -> bool:
    """Release the high-resolution timer request (timeEndPeriod).

    Must be called with the same period_ms passed to begin_timer_period().
    Returns True on success.
    """
    if sys.platform != "win32":
        return False
    try:
        result = ctypes.windll.winmm.timeEndPeriod(period_ms)
        success = result == 0
        if success:
            log.debug("timeEndPeriod(%d) succeeded", period_ms)
        return success
    except Exception:
        log.warning("timeEndPeriod failed", exc_info=True)
        return False
