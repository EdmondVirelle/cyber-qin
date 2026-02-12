"""Language selector widget for the sidebar."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QPushButton, QWidget

from ...core.translator import LANGUAGES, translator
from ..theme import ACCENT_GOLD, BG_HOVER, TEXT_PRIMARY, TEXT_SECONDARY


class LanguageSelector(QPushButton):
    """A prominent button to switch languages."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)

        # Setup menu
        self._menu = QMenu(self)
        self._menu.setStyleSheet(f"""
            QMenu {{
                background-color: #1E1E1E;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                color: {TEXT_PRIMARY};
                padding: 8px 16px;
                border-radius: 4px;
                font-family: "Microsoft JhengHei";
            }}
            QMenu::item:selected {{
                background-color: {BG_HOVER};
            }}
            QMenu::item:checked {{
                color: {ACCENT_GOLD};
                font-weight: bold;
            }}
        """)

        # Add actions
        self._actions = {}
        for code, name in LANGUAGES.items():
            action = QAction(name, self)
            action.setCheckable(True)
            action.setData(code)
            action.triggered.connect(lambda checked, c=code: translator.set_language(c))
            self._menu.addAction(action)
            self._actions[code] = action

        self.setMenu(self._menu)

        # Initial update
        self._update_display()

        # Connect signals
        translator.language_changed.connect(self._update_display)

    def _update_display(self) -> None:
        """Update button text and menu state based on current language."""
        current = translator.current_language

        # Update button text
        lang_name = LANGUAGES.get(current, "English")
        self.setText(f"🌐 {lang_name}")

        # Update menu selection
        for code, action in self._actions.items():
            action.setChecked(code == current)

        # Update styling (Dynamic border color based on accent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {TEXT_SECONDARY};
                border-radius: 20px;
                color: {TEXT_PRIMARY};
                font-family: "Microsoft JhengHei";
                font-size: 14px;
                text-align: left;
                padding-left: 16px;
            }}
            QPushButton:hover {{
                border-color: {ACCENT_GOLD};
                color: {ACCENT_GOLD};
                background-color: {BG_HOVER};
            }}
            QPushButton::menu-indicator {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                padding-right: 16px;
                image: none; /* Hide default triangle, verified cleanest look */
            }}
        """)
