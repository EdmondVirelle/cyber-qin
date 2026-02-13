"""武俠賽博水墨 dark theme — 墨韻 design system."""

from __future__ import annotations

import ctypes
import sys

from PyQt6.QtWidgets import QApplication

# --- Color Palette: 賽博墨韻 ---
BG_INK = "#0A0E14"  # 墨黑底（帶微藍）
BG_SCROLL = "#101820"  # 卷軸面
BG_PAPER = "#1A2332"  # 宣紙暗面
BG_WASH = "#243040"  # 墨染懸停
BG_MIST = "#2E3D50"  # 雲霧層
ACCENT = "#00F0FF"  # 賽博青（霓虹青）
ACCENT_GLOW = "#40FFFF"  # 青光暈
ACCENT_DIM = "#008B99"  # 青暗
ACCENT_GOLD = "#D4A853"  # 金墨（古風金）
TEXT_PRIMARY = "#E8E0D0"  # 宣紙白（暖白）
TEXT_SECONDARY = "#7A8899"  # 水墨灰
TEXT_DISABLED = "#4A5568"  # 淡墨
DIVIDER = "#1E2D3D"  # 墨痕
ERROR = "#FF4444"  # 硃紅
WARNING = "#E8A830"  # 琥珀金

# Legacy aliases (used by widgets that import the old names)
BG_DARK = BG_INK
BG_SURFACE = BG_SCROLL
BG_CARD = BG_PAPER
BG_HOVER = BG_WASH
BG_ELEVATED = BG_MIST
ACCENT_HOVER = ACCENT_GLOW
ACCENT_DARK = ACCENT_DIM

FONT_FAMILY = '"Microsoft JhengHei", "Noto Sans TC", sans-serif'
FONT_MONO = '"Cascadia Code", Consolas, monospace'


def get_stylesheet() -> str:
    return f"""
    /* ===== Global ===== */
    QMainWindow, QWidget {{
        background-color: {BG_INK};
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
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        border: none;
        border-radius: 16px;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {BG_WASH};
    }}
    QPushButton:pressed {{
        background-color: {BG_MIST};
    }}
    QPushButton:disabled {{
        color: {TEXT_DISABLED};
        background-color: {BG_PAPER};
    }}
    QPushButton[class="accent"] {{
        background-color: {ACCENT};
        color: {BG_INK};
        border-radius: 20px;
        padding: 8px 28px;
        font-weight: 700;
    }}
    QPushButton[class="accent"]:hover {{
        background-color: {ACCENT_GLOW};
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
        background-color: {BG_WASH};
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
        background-color: rgba(0, 240, 255, 0.05);
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
        background-color: {BG_PAPER};
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
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        selection-background-color: {BG_WASH};
        border: 1px solid {DIVIDER};
        border-radius: 4px;
        padding: 4px;
    }}

    /* ===== SpinBox ===== */
    QSpinBox {{
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        border: 1px solid {DIVIDER};
        border-radius: 8px;
        padding: 4px 8px;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: {BG_MIST};
        border: none;
        width: 16px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: {BG_WASH};
    }}

    /* ===== ScrollBar ===== */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BG_MIST};
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
        background: {BG_MIST};
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
        background-color: {BG_SCROLL};
        color: {TEXT_SECONDARY};
        border: 1px solid {DIVIDER};
        border-radius: 8px;
        padding: 8px;
        font-family: {FONT_MONO};
        font-size: 11px;
        selection-background-color: {BG_MIST};
    }}

    /* ===== Slider ===== */
    QSlider::groove:horizontal {{
        background: {BG_MIST};
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
        background-color: {BG_PAPER};
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
    """Apply the 賽博墨韻 dark theme to the application."""
    app.setStyle("Fusion")
    app.setStyleSheet(get_stylesheet())
