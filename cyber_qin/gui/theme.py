"""墨韻賽博 (Cyber Ink) Theme — Spotify × 武俠墨韻風格

Design System: Fusion of modern music app (Spotify) + Chinese ink painting aesthetic
"""

from __future__ import annotations

import ctypes
import sys

from PyQt6.QtWidgets import QApplication

# ═══════════════════════════════════════════════════════════════
# 🎨 墨韻賽博配色方案 (Cyber Ink Color Palette)
# ═══════════════════════════════════════════════════════════════

# --- 主色調 (Primary Colors) ---
BG_INK = "#0A0E14"  # 墨韻深黑 (Ink Black) - Main background
BG_SCROLL = "#15191F"  # 墨卷灰 (Scroll Gray) - Secondary background
BG_PAPER = "#1A1F2E"  # 宣紙暗面 (Dark Paper) - Card background
BG_WASH = "#1A1F2E"  # 墨染懸停 (Ink Wash Hover) - Hover state
BG_MIST = "#2C3444"  # 墨淡 (Light Ink) - Elevated elements
PAPER_WHITE = "#E8E6E3"  # 宣紙白 (Paper White) - Light elements

# --- 強調色 (Accent Colors) ---
ACCENT_GOLD = "#D4AF37"  # 琴弦金 (Qin Gold) - Primary accent
ACCENT_GOLD_GLOW = "#E5C158"  # 金光暈 (Gold Glow) - Hover glow
ACCENT_GOLD_DIM = "#B8941F"  # 金暗 (Gold Dim) - Pressed state
ACCENT_GREEN = "#5C9C7D"  # 青銅綠 (Bronze Green) - Success
ACCENT_RED = "#C84B31"  # 朱砂紅 (Cinnabar Red) - Warning/Error
ACCENT_BLUE = "#4A90E2"  # 墨藍 (Ink Blue) - Info

# --- 灰階漸層 (Grayscale) ---
INK_DEEP = "#1A1F2E"  # 墨濃 (Deep Ink)
INK_LIGHT = "#2C3444"  # 墨淡 (Light Ink)
INK_TRACE = "#404759"  # 墨痕 (Ink Trace)
MIST_GRAY = "#5A6270"  # 霧灰 (Mist Gray)
SMOKE_GRAY = "#8B95A5"  # 煙灰 (Smoke Gray)

# --- 文字顏色 (Text Colors) ---
TEXT_PRIMARY = "#E8E6E3"  # 主文字 (Primary Text)
TEXT_SECONDARY = "#A0A8B8"  # 次要文字 (Secondary Text)
TEXT_DISABLED = "#5A6270"  # 禁用文字 (Disabled Text)
TEXT_ACCENT = ACCENT_GOLD  # 強調文字 (Accent Text)

# --- 語義顏色 (Semantic Colors) ---
SUCCESS = ACCENT_GREEN  # 成功 (Success)
WARNING = "#E5A84B"  # 警告 (Warning)
ERROR = ACCENT_RED  # 錯誤 (Error)
INFO = ACCENT_BLUE  # 資訊 (Info)

# --- 分隔線與邊框 (Dividers & Borders) ---
DIVIDER = "#1E2D3D"  # 墨痕 (Ink Trace)
BORDER_GOLD = "#D4AF37"  # 金色邊框 (Gold Border)
BORDER_DIM = "#404759"  # 暗邊框 (Dim Border)

# --- Legacy aliases (for backward compatibility) ---
BG_DARK = BG_INK
BG_SURFACE = BG_SCROLL
BG_CARD = BG_PAPER
BG_HOVER = BG_WASH
BG_ELEVATED = BG_MIST
ACCENT = ACCENT_GOLD
ACCENT_HOVER = ACCENT_GOLD_GLOW
ACCENT_DARK = ACCENT_GOLD_DIM
ACCENT_DIM = ACCENT_GOLD_DIM
ACCENT_GLOW = ACCENT_GOLD_GLOW

# --- 字體系統 (Typography) ---
FONT_FAMILY = '"Microsoft JhengHei", "Noto Sans TC", "Inter", sans-serif'
FONT_MONO = '"Cascadia Code", Consolas, monospace'

# ═══════════════════════════════════════════════════════════════
# 🎭 樣式表 (Stylesheet)
# ═══════════════════════════════════════════════════════════════


def get_stylesheet() -> str:
    """Generate the complete stylesheet for the Cyber Ink theme."""
    return f"""
    /* ═════════════════════════════════════════════════
       Global Base Styles
       ═════════════════════════════════════════════════ */
    QMainWindow, QWidget {{
        background-color: {BG_INK};
        color: {TEXT_PRIMARY};
        font-family: {FONT_FAMILY};
        font-size: 14px;
    }}

    /* ═════════════════════════════════════════════════
       Labels
       ═════════════════════════════════════════════════ */
    QLabel {{
        background: transparent;
        color: {TEXT_PRIMARY};
    }}
    QLabel[class="secondary"] {{
        color: {TEXT_SECONDARY};
    }}
    QLabel[class="title"] {{
        font-size: 24px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
    }}
    QLabel[class="subtitle"] {{
        font-size: 14px;
        color: {TEXT_SECONDARY};
    }}
    QLabel[class="accent"] {{
        color: {ACCENT_GOLD};
        font-weight: 600;
    }}
    QLabel[class="status-ok"] {{
        color: {SUCCESS};
        font-weight: 600;
    }}
    QLabel[class="status-warn"] {{
        color: {WARNING};
        font-weight: 600;
    }}
    QLabel[class="status-off"] {{
        color: {TEXT_DISABLED};
        font-weight: 600;
    }}

    /* ═════════════════════════════════════════════════
       Buttons
       ═════════════════════════════════════════════════ */
    QPushButton {{
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_DIM};
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {BG_WASH};
        border-color: {ACCENT_GOLD};
    }}
    QPushButton:pressed {{
        background-color: {BG_MIST};
        border-color: {ACCENT_GOLD_DIM};
    }}
    QPushButton:disabled {{
        color: {TEXT_DISABLED};
        background-color: {BG_PAPER};
        border-color: {DIVIDER};
    }}

    /* Primary Accent Button (Gold) */
    QPushButton[class="accent"] {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 {ACCENT_GOLD},
            stop:1 {ACCENT_GOLD_DIM}
        );
        color: {BG_INK};
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 700;
        font-size: 14px;
    }}
    QPushButton[class="accent"]:hover {{
        background: {ACCENT_GOLD_GLOW};
    }}
    QPushButton[class="accent"]:pressed {{
        background: {ACCENT_GOLD_DIM};
    }}

    /* Icon Buttons */
    QPushButton[class="icon"] {{
        background: transparent;
        border: none;
        border-radius: 16px;
        padding: 8px;
        min-width: 32px;
        max-width: 32px;
        min-height: 32px;
        max-height: 32px;
        font-size: 16px;
    }}
    QPushButton[class="icon"]:hover {{
        background-color: {BG_WASH};
        border: 1px solid {ACCENT_GOLD};
    }}

    /* Navigation Buttons (Sidebar) */
    QPushButton[class="nav"] {{
        background: transparent;
        color: {TEXT_SECONDARY};
        border: none;
        border-radius: 6px;
        padding: 12px 16px;
        text-align: left;
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton[class="nav"]:hover {{
        color: {TEXT_PRIMARY};
        background-color: rgba(212, 175, 55, 0.1);
    }}
    QPushButton[class="nav-active"] {{
        background: rgba(212, 175, 55, 0.15);
        color: {ACCENT_GOLD};
        border: none;
        border-left: 3px solid {ACCENT_GOLD};
        border-radius: 6px;
        padding: 12px 16px;
        text-align: left;
        font-size: 14px;
        font-weight: 700;
    }}

    /* ═════════════════════════════════════════════════
       ComboBox (Dropdowns)
       ═════════════════════════════════════════════════ */
    QComboBox {{
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_DIM};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 14px;
    }}
    QComboBox:hover {{
        border-color: {ACCENT_GOLD};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        selection-background-color: rgba(212, 175, 55, 0.2);
        selection-color: {ACCENT_GOLD};
        border: 1px solid {ACCENT_GOLD};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}

    /* ═════════════════════════════════════════════════
       SpinBox (Number Input)
       ═════════════════════════════════════════════════ */
    QSpinBox {{
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_DIM};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 14px;
    }}
    QSpinBox:hover {{
        border-color: {ACCENT_GOLD};
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: {BG_MIST};
        border: none;
        width: 18px;
        border-radius: 3px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: {ACCENT_GOLD};
    }}

    /* ═════════════════════════════════════════════════
       CheckBox
       ═════════════════════════════════════════════════ */
    QCheckBox {{
        color: {TEXT_PRIMARY};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {BORDER_DIM};
        border-radius: 4px;
        background: {BG_PAPER};
    }}
    QCheckBox::indicator:hover {{
        border-color: {ACCENT_GOLD};
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT_GOLD};
        border-color: {ACCENT_GOLD};
    }}

    /* ═════════════════════════════════════════════════
       ScrollBar
       ═════════════════════════════════════════════════ */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BG_MIST};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {ACCENT_GOLD};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {BG_MIST};
        border-radius: 5px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {ACCENT_GOLD};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ═════════════════════════════════════════════════
       PlainTextEdit (Log / Code Display)
       ═════════════════════════════════════════════════ */
    QPlainTextEdit {{
        background-color: {BG_SCROLL};
        color: {TEXT_SECONDARY};
        border: 1px solid {DIVIDER};
        border-radius: 6px;
        padding: 10px;
        font-family: {FONT_MONO};
        font-size: 12px;
        selection-background-color: {BG_MIST};
        selection-color: {TEXT_PRIMARY};
    }}

    /* ═════════════════════════════════════════════════
       Slider
       ═════════════════════════════════════════════════ */
    QSlider::groove:horizontal {{
        background: {BG_MIST};
        height: 4px;
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {TEXT_PRIMARY};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {ACCENT_GOLD};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    QSlider::sub-page:horizontal {{
        background: {ACCENT_GOLD};
        border-radius: 2px;
    }}

    /* ═════════════════════════════════════════════════
       ToolTip
       ═════════════════════════════════════════════════ */
    QToolTip {{
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        border: 1px solid {ACCENT_GOLD};
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* ═════════════════════════════════════════════════
       MenuBar & Menu
       ═════════════════════════════════════════════════ */
    QMenuBar {{
        background-color: {BG_SCROLL};
        color: {TEXT_PRIMARY};
        border-bottom: 1px solid {DIVIDER};
    }}
    QMenuBar::item:selected {{
        background-color: {BG_WASH};
    }}
    QMenu {{
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        border: 1px solid {ACCENT_GOLD};
        border-radius: 6px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 20px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: rgba(212, 175, 55, 0.2);
        color: {ACCENT_GOLD};
    }}

    /* ═════════════════════════════════════════════════
       TabWidget
       ═════════════════════════════════════════════════ */
    QTabWidget::pane {{
        border: 1px solid {DIVIDER};
        border-radius: 6px;
        background-color: {BG_PAPER};
    }}
    QTabBar::tab {{
        background-color: {BG_SCROLL};
        color: {TEXT_SECONDARY};
        padding: 10px 20px;
        border: 1px solid {DIVIDER};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }}
    QTabBar::tab:selected {{
        background-color: {BG_PAPER};
        color: {ACCENT_GOLD};
        border-color: {ACCENT_GOLD};
        border-bottom: 2px solid {ACCENT_GOLD};
        font-weight: 700;
    }}
    QTabBar::tab:hover {{
        color: {TEXT_PRIMARY};
    }}

    /* ═════════════════════════════════════════════════
       LineEdit (Text Input)
       ═════════════════════════════════════════════════ */
    QLineEdit {{
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_DIM};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 14px;
    }}
    QLineEdit:hover {{
        border-color: {ACCENT_GOLD};
    }}
    QLineEdit:focus {{
        border-color: {ACCENT_GOLD};
        border-width: 2px;
    }}
    """


# ═══════════════════════════════════════════════════════════════
# 🪟 Platform-Specific Utilities
# ═══════════════════════════════════════════════════════════════


def enable_dark_title_bar(hwnd: int) -> None:
    """Enable Windows 10/11 dark title bar via DwmSetWindowAttribute.

    Args:
        hwnd: Window handle (HWND) from QWidget.winId()
    """
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
    """Apply the 墨韻賽博 (Cyber Ink) theme to the application.

    Args:
        app: QApplication instance
    """
    app.setStyle("Fusion")
    app.setStyleSheet(get_stylesheet())
