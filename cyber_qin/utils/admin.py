"""Administrator privilege detection and UAC elevation."""

from __future__ import annotations

import ctypes
import logging
import sys

log = logging.getLogger(__name__)


def is_admin() -> bool:
    """Check if the current process has administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def request_elevation() -> bool:
    """Request UAC elevation by re-launching the current script as admin.

    Returns True if the elevation request was sent (the current process
    should then exit). Returns False if elevation failed.
    """
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join(sys.argv),
            None,
            1,  # SW_SHOWNORMAL
        )
        # ShellExecuteW returns >32 on success
        return int(ret) > 32
    except Exception:
        log.exception("Failed to request UAC elevation")
        return False
