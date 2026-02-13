"""Settings dialog with tabbed interface for user preferences."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.config import get_config
from ...core.midi_listener import MidiListener
from ...core.translator import translator
from ..theme import BG_INK, BG_PAPER, TEXT_PRIMARY, TEXT_SECONDARY


class SettingsDialog(QDialog):
    """Settings dialog with 5 tabs: MIDI, Playback, Editor, UI, Advanced."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(translator.tr("settings.title"))
        self.setMinimumSize(600, 500)

        self._config = get_config()
        self._init_ui()
        self._load_settings()
        self._apply_theme()

    def _init_ui(self) -> None:
        """Initialize UI layout with tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_midi_tab(), translator.tr("settings.tab.midi"))
        self._tabs.addTab(self._create_playback_tab(), translator.tr("settings.tab.playback"))
        self._tabs.addTab(self._create_editor_tab(), translator.tr("settings.tab.editor"))
        self._tabs.addTab(self._create_ui_tab(), translator.tr("settings.tab.ui"))
        self._tabs.addTab(self._create_advanced_tab(), translator.tr("settings.tab.advanced"))

        layout.addWidget(self._tabs)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)

        apply_button = button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button:
            apply_button.clicked.connect(self._on_apply)

        layout.addWidget(button_box)

    def _create_midi_tab(self) -> QWidget:
        """Create MIDI settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        # Device selection group
        device_group = QGroupBox(translator.tr("settings.midi.device"))
        device_layout = QFormLayout()

        self._midi_device = QComboBox()
        self._midi_device.setToolTip(translator.tr("settings.midi.device.tooltip"))
        self._refresh_midi_devices()
        device_layout.addRow(
            translator.tr("settings.midi.device.label"), self._midi_device
        )

        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        # Auto-connect group
        connection_group = QGroupBox(translator.tr("settings.midi.connection"))
        connection_layout = QFormLayout()

        self._auto_connect = QCheckBox(translator.tr("settings.midi.auto_connect.label"))
        self._auto_connect.setToolTip(translator.tr("settings.midi.auto_connect.tooltip"))
        connection_layout.addRow(self._auto_connect)

        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)

        layout.addStretch()
        return widget

    def _create_playback_tab(self) -> QWidget:
        """Create Playback settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        # Transpose group
        group = QGroupBox(translator.tr("settings.playback.transpose"))
        group_layout = QFormLayout()

        self._transpose = QSpinBox()
        self._transpose.setMinimum(-24)
        self._transpose.setMaximum(24)
        self._transpose.setSuffix(" " + translator.tr("settings.playback.transpose.semitones"))
        self._transpose.setToolTip(translator.tr("settings.playback.transpose.tooltip"))
        group_layout.addRow(translator.tr("settings.playback.transpose.label"), self._transpose)

        group.setLayout(group_layout)
        layout.addWidget(group)

        layout.addStretch()
        return widget

    def _create_editor_tab(self) -> QWidget:
        """Create Editor settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        # Snap group
        snap_group = QGroupBox(translator.tr("settings.editor.snap"))
        snap_layout = QFormLayout()

        self._snap_enabled = QCheckBox(translator.tr("settings.editor.snap.enabled"))
        self._snap_enabled.setToolTip(translator.tr("settings.editor.snap.tooltip"))
        snap_layout.addRow(self._snap_enabled)

        self._grid_subdivision = QComboBox()
        self._grid_subdivision.addItem("1/4 " + translator.tr("settings.editor.note"), 4)
        self._grid_subdivision.addItem("1/8 " + translator.tr("settings.editor.note"), 8)
        self._grid_subdivision.addItem("1/16 " + translator.tr("settings.editor.note"), 16)
        self._grid_subdivision.addItem("1/32 " + translator.tr("settings.editor.note"), 32)
        snap_layout.addRow(translator.tr("settings.editor.grid"), self._grid_subdivision)

        snap_group.setLayout(snap_layout)
        layout.addWidget(snap_group)

        # Auto-save group
        autosave_group = QGroupBox(translator.tr("settings.editor.autosave"))
        autosave_layout = QFormLayout()

        self._auto_save = QCheckBox(translator.tr("settings.editor.autosave.enabled"))
        autosave_layout.addRow(self._auto_save)

        self._auto_save_interval = QSpinBox()
        self._auto_save_interval.setMinimum(10)
        self._auto_save_interval.setMaximum(600)
        self._auto_save_interval.setSuffix(" " + translator.tr("settings.editor.seconds"))
        autosave_layout.addRow(
            translator.tr("settings.editor.autosave.interval"), self._auto_save_interval
        )

        autosave_group.setLayout(autosave_layout)
        layout.addWidget(autosave_group)

        layout.addStretch()
        return widget

    def _create_ui_tab(self) -> QWidget:
        """Create UI settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        # Language group
        lang_group = QGroupBox(translator.tr("settings.ui.language"))
        lang_layout = QFormLayout()

        self._language = QComboBox()
        self._language.addItem(translator.tr("settings.ui.language.auto"), "auto")
        self._language.addItem("English", "en")
        self._language.addItem("繁體中文", "zh_TW")
        self._language.addItem("简体中文", "zh_CN")
        lang_layout.addRow(translator.tr("settings.ui.language.label"), self._language)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # Theme group (future)
        theme_group = QGroupBox(translator.tr("settings.ui.theme"))
        theme_layout = QFormLayout()

        self._theme = QComboBox()
        self._theme.addItem(translator.tr("settings.ui.theme.dark"), "dark")
        self._theme.addItem(
            translator.tr("settings.ui.theme.light") + " " + translator.tr("settings.coming_soon"),
            "light",
        )
        self._theme.setEnabled(False)  # Not implemented yet
        theme_layout.addRow(translator.tr("settings.ui.theme.label"), self._theme)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        layout.addStretch()
        return widget

    def _refresh_midi_devices(self) -> None:
        """Refresh the list of available MIDI devices."""
        self._midi_device.clear()
        self._midi_device.addItem(translator.tr("settings.midi.device.none"), "")

        try:
            devices = MidiListener.list_ports()
            for device in devices:
                self._midi_device.addItem(device, device)
        except Exception:
            pass  # If MIDI enumeration fails, just show "None" option

    def _create_advanced_tab(self) -> QWidget:
        """Create Advanced settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        # Config file location
        info_label = QLabel(translator.tr("settings.advanced.config_location"))
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {TEXT_SECONDARY}; padding: 8px;")
        layout.addWidget(info_label)

        config_path = QLabel(str(self._config.config_file))
        config_path.setWordWrap(True)
        config_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        config_path.setStyleSheet(
            f"color: {TEXT_PRIMARY}; padding: 8px; background: {BG_INK}; border-radius: 4px;"
        )
        layout.addWidget(config_path)

        layout.addStretch()
        return widget

    def _load_settings(self) -> None:
        """Load settings from config into UI controls."""
        # MIDI
        preferred_device = self._config.get("midi.preferred_device", "")
        device_index = self._midi_device.findData(preferred_device)
        if device_index >= 0:
            self._midi_device.setCurrentIndex(device_index)

        self._auto_connect.setChecked(self._config.get("midi.auto_connect", True))

        # Playback
        self._transpose.setValue(self._config.get("playback.transpose", 0))

        # Editor
        self._snap_enabled.setChecked(self._config.get("editor.snap_enabled", True))

        grid_sub = self._config.get("editor.grid_subdivision", 4)
        grid_index = self._grid_subdivision.findData(grid_sub)
        if grid_index >= 0:
            self._grid_subdivision.setCurrentIndex(grid_index)

        self._auto_save.setChecked(self._config.get("editor.auto_save", True))
        self._auto_save_interval.setValue(self._config.get("editor.auto_save_interval", 60))

        # UI
        language = self._config.get("ui.language", "auto")
        lang_index = self._language.findData(language)
        if lang_index >= 0:
            self._language.setCurrentIndex(lang_index)

        theme = self._config.get("ui.theme", "dark")
        theme_index = self._theme.findData(theme)
        if theme_index >= 0:
            self._theme.setCurrentIndex(theme_index)

    def _save_settings(self) -> None:
        """Save settings from UI controls to config."""
        # MIDI
        self._config.set("midi.preferred_device", self._midi_device.currentData() or "")
        self._config.set("midi.auto_connect", self._auto_connect.isChecked())

        # Playback
        self._config.set("playback.transpose", self._transpose.value())

        # Editor
        self._config.set("editor.snap_enabled", self._snap_enabled.isChecked())
        self._config.set("editor.grid_subdivision", self._grid_subdivision.currentData())
        self._config.set("editor.auto_save", self._auto_save.isChecked())
        self._config.set("editor.auto_save_interval", self._auto_save_interval.value())

        # UI
        self._config.set("ui.language", self._language.currentData())
        self._config.set("ui.theme", self._theme.currentData())

    def _on_apply(self) -> None:
        """Apply button clicked - save without closing."""
        self._save_settings()

    def _on_ok(self) -> None:
        """OK button clicked - save and close."""
        self._save_settings()
        self.accept()

    def _apply_theme(self) -> None:
        """Apply 賽博墨韻 theme to dialog."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_PAPER};
                color: {TEXT_PRIMARY};
            }}
            QTabWidget::pane {{
                border: 1px solid {BG_INK};
                background-color: {BG_PAPER};
            }}
            QTabBar::tab {{
                background-color: {BG_INK};
                color: {TEXT_SECONDARY};
                padding: 8px 16px;
                border: none;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {BG_PAPER};
                color: {TEXT_PRIMARY};
            }}
            QTabBar::tab:hover {{
                background-color: {BG_PAPER};
            }}
            QGroupBox {{
                border: 1px solid {BG_INK};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
                color: {TEXT_PRIMARY};
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
            }}
            QCheckBox {{
                color: {TEXT_PRIMARY};
            }}
            QSpinBox, QComboBox {{
                background-color: {BG_INK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BG_INK};
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 24px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {BG_INK};
                border: none;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QDialogButtonBox QPushButton {{
                background-color: {BG_INK};
                color: {TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }}
            QDialogButtonBox QPushButton:hover {{
                background-color: #1E2D3D;
            }}
        """)
