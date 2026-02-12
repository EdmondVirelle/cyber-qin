# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 賽博琴仙 — onedir windowed bundle."""

import sys
from pathlib import Path

block_cipher = None

# Explicitly bundle VC runtime DLLs — CI runners have them as system DLLs,
# so PyInstaller's automatic collection may skip them.
_python_dir = Path(sys.executable).parent
_vcrt = [(str(p), ".") for p in _python_dir.glob("vcruntime*.dll")]
_vcrt += [(str(p), ".") for p in _python_dir.glob("python3*.dll")]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=_vcrt,
    datas=[('RELEASE.txt', '.')],
    hiddenimports=[
        # ── mido backend (dynamically loaded) ──
        "mido.backends.rtmidi",
        "rtmidi",
        # ── stdlib lazy import ──
        "winsound",
        # ── core: lazy Qt class pattern (CRITICAL) ──
        "cyber_qin.core.midi_output_player",
        "cyber_qin.core.midi_file_player",
        # ── core: imported at runtime ──
        "cyber_qin.core.constants",
        "cyber_qin.core.key_mapper",
        "cyber_qin.core.key_simulator",
        "cyber_qin.core.midi_listener",
        "cyber_qin.core.midi_recorder",
        "cyber_qin.core.midi_writer",
        "cyber_qin.core.midi_preprocessor",
        "cyber_qin.core.auto_tune",
        "cyber_qin.core.beat_sequence",
        "cyber_qin.core.note_sequence",
        "cyber_qin.core.project_file",
        "cyber_qin.core.mapping_schemes",
        "cyber_qin.core.priority",
        # ── gui ──
        "cyber_qin.gui.theme",
        "cyber_qin.gui.app_shell",
        "cyber_qin.gui.icons",
        # ── views ──
        "cyber_qin.gui.views.library_view",
        "cyber_qin.gui.views.live_mode_view",
        "cyber_qin.gui.views.editor_view",
        # ── widgets ──
        "cyber_qin.gui.widgets.animated_widgets",
        "cyber_qin.gui.widgets.clickable_piano",
        "cyber_qin.gui.widgets.editor_track_panel",
        "cyber_qin.gui.widgets.log_viewer",
        "cyber_qin.gui.widgets.mini_piano",
        "cyber_qin.gui.widgets.note_roll",
        "cyber_qin.gui.widgets.now_playing_bar",
        "cyber_qin.gui.widgets.piano_display",
        "cyber_qin.gui.widgets.pitch_ruler",
        "cyber_qin.gui.widgets.progress_bar",
        "cyber_qin.gui.widgets.sidebar",
        "cyber_qin.gui.widgets.speed_control",
        "cyber_qin.gui.widgets.status_bar",
        "cyber_qin.gui.widgets.track_list",
        # ── utils ──
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
