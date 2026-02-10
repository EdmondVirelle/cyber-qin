# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 賽博琴仙 — onedir windowed bundle."""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # ── mido backend (dynamically loaded) ──
        "mido.backends.rtmidi",
        "rtmidi",
        # ── stdlib lazy import ──
        "winsound",
        # ── project lazy imports ──
        "cyber_qin.core.priority",
        "cyber_qin.core.midi_preprocessor",
        "cyber_qin.core.mapping_schemes",
        "cyber_qin.gui.theme",
        "cyber_qin.gui.app_shell",
        "cyber_qin.gui.icons",
        "cyber_qin.gui.views.library_view",
        "cyber_qin.gui.views.live_mode_view",
        "cyber_qin.gui.widgets.animated_widgets",
        "cyber_qin.gui.widgets.log_viewer",
        "cyber_qin.gui.widgets.mini_piano",
        "cyber_qin.gui.widgets.now_playing_bar",
        "cyber_qin.gui.widgets.piano_display",
        "cyber_qin.gui.widgets.progress_bar",
        "cyber_qin.gui.widgets.sidebar",
        "cyber_qin.gui.widgets.speed_control",
        "cyber_qin.gui.widgets.status_bar",
        "cyber_qin.gui.widgets.track_list",
        "cyber_qin.utils.admin",
        "cyber_qin.utils.ime",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Not needed at runtime
        "pytest",
        "ruff",
        "tkinter",
        "_tkinter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="賽博琴仙",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    icon="assets/icon.ico",
    console=False,       # windowed app, no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,      # request UAC elevation
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="賽博琴仙",
)
