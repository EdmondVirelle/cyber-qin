"""Entry point: admin check + QApplication startup."""

from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from .utils.admin import is_admin, request_elevation


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("賽博琴仙")
    app.setOrganizationName("CyberQin")

    # Admin check — warn but don't block
    if not is_admin():
        reply = QMessageBox.warning(
            None,
            "權限提醒",
            "目前以非管理員身份執行。\n"
            "部分遊戲可能無法接收模擬按鍵。\n\n"
            "是否以管理員身份重新啟動？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if request_elevation():
                sys.exit(0)

    # Request 1ms timer resolution for low-latency playback
    from .core.priority import begin_timer_period, end_timer_period
    begin_timer_period(1)

    # Apply 賽博墨韻 theme
    from .gui.theme import apply_theme
    apply_theme(app)

    # Import and launch the main shell
    from .gui.app_shell import AppShell

    window = AppShell()

    # Enable Windows dark title bar
    if sys.platform == "win32":
        from .gui.theme import enable_dark_title_bar
        hwnd = int(window.winId())
        enable_dark_title_bar(hwnd)

    window.show()
    exit_code = app.exec()
    end_timer_period(1)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
