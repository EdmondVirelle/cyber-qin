"""Event log viewer widget."""

from __future__ import annotations

from PyQt6.QtWidgets import QPlainTextEdit, QWidget


class LogViewer(QPlainTextEdit):
    """Read-only scrolling log display for MIDI events.

    Styling is handled by the global QSS theme.
    """

    MAX_LINES = 500

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(self.MAX_LINES)

    def log(self, message: str) -> None:
        """Append a message to the log."""
        self.appendPlainText(message)
