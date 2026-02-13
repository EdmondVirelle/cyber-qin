"""Tests for cyber_qin.core.priority — thread priority & timer utilities."""

from __future__ import annotations

import sys
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _reset_module():
    """Re-import priority module fresh for each test to reset global state."""
    mod_name = "cyber_qin.core.priority"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    yield
    if mod_name in sys.modules:
        del sys.modules[mod_name]


class TestSetThreadPriorityRealtime:
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_success(self):
        with mock.patch("sys.platform", "win32"):
            kernel32 = mock.MagicMock()
            kernel32.GetCurrentThread.return_value = 42
            kernel32.SetThreadPriority.return_value = 1  # success
            with mock.patch("ctypes.windll") as windll:
                windll.kernel32 = kernel32
                from cyber_qin.core.priority import set_thread_priority_realtime

                assert set_thread_priority_realtime() is True
                kernel32.SetThreadPriority.assert_called_once_with(42, 15)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_failure(self):
        with mock.patch("sys.platform", "win32"):
            kernel32 = mock.MagicMock()
            kernel32.GetCurrentThread.return_value = 42
            kernel32.SetThreadPriority.return_value = 0  # failure
            with mock.patch("ctypes.windll") as windll:
                windll.kernel32 = kernel32
                from cyber_qin.core.priority import set_thread_priority_realtime

                assert set_thread_priority_realtime() is False

    def test_non_windows(self):
        with mock.patch("sys.platform", "linux"):
            from cyber_qin.core.priority import set_thread_priority_realtime

            assert set_thread_priority_realtime() is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_exception(self):
        with mock.patch("sys.platform", "win32"):
            with mock.patch("ctypes.windll") as windll:
                windll.kernel32.GetCurrentThread.side_effect = OSError("fail")
                from cyber_qin.core.priority import set_thread_priority_realtime

                assert set_thread_priority_realtime() is False


class TestBeginTimerPeriod:
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_success(self):
        with mock.patch("sys.platform", "win32"):
            winmm = mock.MagicMock()
            winmm.timeBeginPeriod.return_value = 0  # TIMERR_NOERROR
            with mock.patch("ctypes.windll") as windll:
                windll.winmm = winmm
                from cyber_qin.core.priority import begin_timer_period

                assert begin_timer_period(1) is True

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_failure(self):
        with mock.patch("sys.platform", "win32"):
            winmm = mock.MagicMock()
            winmm.timeBeginPeriod.return_value = 97  # error
            with mock.patch("ctypes.windll") as windll:
                windll.winmm = winmm
                from cyber_qin.core.priority import begin_timer_period

                assert begin_timer_period(1) is False

    def test_non_windows(self):
        with mock.patch("sys.platform", "linux"):
            from cyber_qin.core.priority import begin_timer_period

            assert begin_timer_period() is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_exception(self):
        with mock.patch("sys.platform", "win32"):
            with mock.patch("ctypes.windll") as windll:
                windll.winmm.timeBeginPeriod.side_effect = OSError
                from cyber_qin.core.priority import begin_timer_period

                assert begin_timer_period() is False


class TestEndTimerPeriod:
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_success(self):
        with mock.patch("sys.platform", "win32"):
            winmm = mock.MagicMock()
            winmm.timeEndPeriod.return_value = 0
            with mock.patch("ctypes.windll") as windll:
                windll.winmm = winmm
                from cyber_qin.core.priority import end_timer_period

                assert end_timer_period(1) is True

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_failure(self):
        with mock.patch("sys.platform", "win32"):
            winmm = mock.MagicMock()
            winmm.timeEndPeriod.return_value = 97
            with mock.patch("ctypes.windll") as windll:
                windll.winmm = winmm
                from cyber_qin.core.priority import end_timer_period

                assert end_timer_period(1) is False

    def test_non_windows(self):
        with mock.patch("sys.platform", "linux"):
            from cyber_qin.core.priority import end_timer_period

            assert end_timer_period() is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_exception(self):
        with mock.patch("sys.platform", "win32"):
            with mock.patch("ctypes.windll") as windll:
                windll.winmm.timeEndPeriod.side_effect = OSError
                from cyber_qin.core.priority import end_timer_period

                assert end_timer_period() is False
