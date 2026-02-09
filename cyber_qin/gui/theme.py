"""Spotify-inspired dark theme for the application."""

from __future__ import annotations

import ctypes
import sys

from PyQt6.QtWidgets import QApplication

# --- Color Palette ---
BG_DARK = "#121212"
BG_SURFACE = "#181818"
BG_CARD = "#282828"
BG_HOVER = "#333333"
BG_ELEVATED = "#3E3E3E"
ACCENT = "#1DB954"
ACCENT_HOVER = "#1ED760"
ACCENT_DARK = "#168D40"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#B3B3B3"
TEXT_DISABLED = "#727272"
DIVIDER = "#404040"
ERROR = "#E74C3C"
WARNING = "#F39C12"

FONT_FAMILY = '"Segoe UI", "Microsoft JhengHei", sans-serif'


def get_stylesheet() -> str:
    return f"""
    /* ===== Global ===== */
    QMainWindow, QWidget {{
        background-color: {BG_DARK};
        color: {TEXT_PRIMARY};
        font-family: {FONT_FAMILY};
        font-size: 13px;
    }}

    /* ===== Labels ===== */
    QLabel {{
        background: transparent;
        color: {TEXT_PRIMARY};
    }}
    QLabel[class="secondary"] {{
        color: {TEXT_SECONDARY};
    }}
    QLabel[class="title"] {{
        font-size: 22px;
        font-weight: bold;
    }}
    QLabel[class="subtitle"] {{
        font-size: 14px;
        color: {TEXT_SECONDARY};
    }}
    QLabel[class="status-ok"] {{
        color: {ACCENT};
        font-weight: bold;
    }}
    QLabel[class="status-warn"] {{
        color: {WARNING};
        font-weight: bold;
    }}
    QLabel[class="status-off"] {{
        color: {TEXT_DISABLED};
        font-weight: bold;
    }}

    /* ===== Buttons ===== */
    QPushButton {{
        background-color: {BG_CARD};
        color: {TEXT_PRIMARY};
        border: none;
        border-radius: 16px;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {BG_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {BG_ELEVATED};
    }}
    QPushButton:disabled {{
        color: {TEXT_DISABLED};
        background-color: {BG_CARD};
    }}
    QPushButton[class="accent"] {{
        background-color: {ACCENT};
        color: {BG_DARK};
        border-radius: 20px;
        padding: 8px 28px;
        font-weight: 700;
    }}
    QPushButton[class="accent"]:hover {{
        background-color: {ACCENT_HOVER};
    }}
    QPushButton[class="icon"] {{
        background: transparent;
        border-radius: 20px;
        padding: 6px;
        min-width: 36px;
        max-width: 36px;
        min-height: 36px;
        max-height: 36px;
        font-size: 16px;
    }}
    QPushButton[class="icon"]:hover {{
        background-color: {BG_HOVER};
    }}

    /* ===== Nav Buttons (Sidebar) ===== */
    QPushButton[class="nav"] {{
        background: transparent;
        color: {TEXT_SECONDARY};
        border-radius: 4px;
        padding: 10px 16px;
        text-align: left;
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton[class="nav"]:hover {{
        color: {TEXT_PRIMARY};
        background-color: rgba(255, 255, 255, 0.05);
    }}
    QPushButton[class="nav-active"] {{
        background: transparent;
        color: {TEXT_PRIMARY};
        border-radius: 4px;
        padding: 10px 16px;
        text-align: left;
        font-size: 14px;
        font-weight: 700;
    }}

    /* ===== ComboBox ===== */
    QComboBox {{
        background-color: {BG_CARD};
        color: {TEXT_PRIMARY};
        border: 1px solid {DIVIDER};
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 13px;
    }}
    QComboBox:hover {{
        border-color: {TEXT_SECONDARY};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_CARD};
        color: {TEXT_PRIMARY};
        selection-background-color: {BG_HOVER};
        border: 1px solid {DIVIDER};
        border-radius: 4px;
        padding: 4px;
    }}

    /* ===== SpinBox ===== */
    QSpinBox {{
        background-color: {BG_CARD};
        color: {TEXT_PRIMARY};
        border: 1px solid {DIVIDER};
        border-radius: 8px;
        padding: 4px 8px;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: {BG_ELEVATED};
        border: none;
        width: 16px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: {BG_HOVER};
    }}

    /* ===== ScrollBar ===== */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BG_ELEVATED};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {TEXT_DISABLED};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
    }}
    QScrollBar::handle:horizontal {{
        background: {BG_ELEVATED};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {TEXT_DISABLED};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ===== PlainTextEdit (Log) ===== */
    QPlainTextEdit {{
        background-color: {BG_SURFACE};
        color: {TEXT_SECONDARY};
        border: 1px solid {DIVIDER};
        border-radius: 8px;
        padding: 8px;
        font-family: Consolas, "Cascadia Code", monospace;
        font-size: 11px;
        selection-background-color: {BG_ELEVATED};
    }}

    /* ===== Slider ===== */
    QSlider::groove:horizontal {{
        background: {BG_ELEVATED};
        height: 4px;
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {TEXT_PRIMARY};
        width: 12px;
        height: 12px;
        margin: -4px 0;
        border-radius: 6px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {ACCENT};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::sub-page:horizontal {{
        background: {ACCENT};
        border-radius: 2px;
    }}

    /* ===== ToolTip ===== */
    QToolTip {{
        background-color: {BG_CARD};
        color: {TEXT_PRIMARY};
        border: 1px solid {DIVIDER};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    """


def enable_dark_title_bar(hwnd: int) -> None:
    """Enable Windows 10/11 dark title bar via DwmSetWindowAttribute."""
    if sys.platform != "win32":
        return
    try:
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1)),
            4,
        )
    except Exception:
        pass  # Graceful fallback on older Windows


def apply_theme(app: QApplication) -> None:
    """Apply the Spotify dark theme to the application."""
    app.setStyle("Fusion")
    app.setStyleSheet(get_stylesheet())
