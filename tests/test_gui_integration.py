"""Integration tests for GUI views using pytest-qt.

Tests the Settings dialog and other GUI components with full Qt application context.
"""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QApplication

from cyber_qin.core.config import ConfigManager, get_config
from cyber_qin.core.translator import translator
from cyber_qin.gui.dialogs import SettingsDialog


@pytest.fixture(scope="function")
def clean_config_for_gui(tmp_path, monkeypatch):
    """Provide a clean ConfigManager for GUI tests."""
    config_dir = tmp_path / "test_config"
    config_dir.mkdir()

    # Clear any existing global config
    from cyber_qin.core import config as config_module

    config_module._global_config = None

    # Create new config in test directory
    config = ConfigManager(config_dir)
    monkeypatch.setattr("cyber_qin.core.config._global_config", config)

    yield config

    # Cleanup
    config_module._global_config = None


class TestSettingsDialog:
    """Integration tests for SettingsDialog."""

    def test_dialog_creation(self, qtbot, clean_config_for_gui):
        """Test that SettingsDialog can be created and shown."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == translator.tr("settings.title")
        assert dialog.minimumWidth() == 600
        assert dialog.minimumHeight() == 500

    def test_tab_switching(self, qtbot, clean_config_for_gui):
        """Test switching between tabs."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Check all 5 tabs are present
        assert dialog._tabs.count() == 5

        # Switch to each tab
        for i in range(5):
            dialog._tabs.setCurrentIndex(i)
            QApplication.processEvents()
            assert dialog._tabs.currentIndex() == i

    def test_midi_auto_connect_toggle(self, qtbot, clean_config_for_gui):
        """Test toggling MIDI auto-connect setting."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Initial state (default True)
        assert dialog._auto_connect.isChecked() is True

        # Toggle off (use setChecked for reliable testing)
        dialog._auto_connect.setChecked(False)
        QApplication.processEvents()
        assert dialog._auto_connect.isChecked() is False

        # Save settings
        dialog._save_settings()
        config = get_config()
        assert config.get("midi.auto_connect") is False

        # Toggle back on
        dialog._auto_connect.setChecked(True)
        QApplication.processEvents()
        assert dialog._auto_connect.isChecked() is True

    def test_playback_transpose_spinbox(self, qtbot, clean_config_for_gui):
        """Test changing playback transpose value."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Navigate to Playback tab
        dialog._tabs.setCurrentIndex(1)  # Playback tab

        # Initial value should be 0
        assert dialog._transpose.value() == 0

        # Change to +12 (one octave up)
        dialog._transpose.setValue(12)
        QApplication.processEvents()
        assert dialog._transpose.value() == 12

        # Save and verify persistence
        dialog._save_settings()
        config = get_config()
        assert config.get("playback.transpose") == 12

        # Test bounds
        dialog._transpose.setValue(-24)  # Minimum
        assert dialog._transpose.value() == -24

        dialog._transpose.setValue(24)  # Maximum
        assert dialog._transpose.value() == 24

    def test_editor_snap_enabled_toggle(self, qtbot, clean_config_for_gui):
        """Test toggling snap-to-grid setting."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Navigate to Editor tab
        dialog._tabs.setCurrentIndex(2)  # Editor tab

        # Initial state (default True)
        assert dialog._snap_enabled.isChecked() is True

        # Toggle off (use setChecked for reliable testing)
        dialog._snap_enabled.setChecked(False)
        QApplication.processEvents()
        assert dialog._snap_enabled.isChecked() is False

        # Save and verify
        dialog._save_settings()
        config = get_config()
        assert config.get("editor.snap_enabled") is False

    def test_grid_subdivision_combobox(self, qtbot, clean_config_for_gui):
        """Test changing grid subdivision."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Navigate to Editor tab
        dialog._tabs.setCurrentIndex(2)

        # Initial value should be 1/4 note (4)
        assert dialog._grid_subdivision.currentData() == 4

        # Change to 1/8 note
        dialog._grid_subdivision.setCurrentIndex(1)
        QApplication.processEvents()
        assert dialog._grid_subdivision.currentData() == 8

        # Save and verify
        dialog._save_settings()
        config = get_config()
        assert config.get("editor.grid_subdivision") == 8

        # Test all subdivisions
        subdivisions = [4, 8, 16, 32]
        for i, expected in enumerate(subdivisions):
            dialog._grid_subdivision.setCurrentIndex(i)
            assert dialog._grid_subdivision.currentData() == expected

    def test_auto_save_interval_spinbox(self, qtbot, clean_config_for_gui):
        """Test changing auto-save interval."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Navigate to Editor tab
        dialog._tabs.setCurrentIndex(2)

        # Initial value should be 60 seconds
        assert dialog._auto_save_interval.value() == 60

        # Change to 120 seconds
        dialog._auto_save_interval.setValue(120)
        QApplication.processEvents()
        assert dialog._auto_save_interval.value() == 120

        # Save and verify
        dialog._save_settings()
        config = get_config()
        assert config.get("editor.auto_save_interval") == 120

        # Test bounds
        dialog._auto_save_interval.setValue(10)  # Minimum
        assert dialog._auto_save_interval.value() == 10

        dialog._auto_save_interval.setValue(600)  # Maximum
        assert dialog._auto_save_interval.value() == 600

    def test_language_selection(self, qtbot, clean_config_for_gui):
        """Test changing interface language."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Navigate to UI tab
        dialog._tabs.setCurrentIndex(3)

        # Initial value should be "auto"
        assert dialog._language.currentData() == "auto"

        # Change to English
        dialog._language.setCurrentIndex(1)
        QApplication.processEvents()
        assert dialog._language.currentData() == "en"

        # Save and verify
        dialog._save_settings()
        config = get_config()
        assert config.get("ui.language") == "en"

        # Test all language options
        languages = ["auto", "en", "zh_TW", "zh_CN"]
        for i, expected in enumerate(languages):
            dialog._language.setCurrentIndex(i)
            assert dialog._language.currentData() == expected

    def test_ok_button_saves_and_closes(self, qtbot, clean_config_for_gui):
        """Test OK button saves settings and closes dialog."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Make a change
        dialog._auto_connect.setChecked(False)

        # Click OK button (directly call the slot)
        dialog._on_ok()

        # Verify setting was saved
        config = get_config()
        assert config.get("midi.auto_connect") is False

    def test_apply_button_saves_without_closing(self, qtbot, clean_config_for_gui):
        """Test Apply button saves settings without closing dialog."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Make a change
        dialog._transpose.setValue(5)

        # Call apply
        dialog._on_apply()

        # Verify setting was saved
        config = get_config()
        assert config.get("playback.transpose") == 5

    def test_cancel_button_discards_changes(self, qtbot, clean_config_for_gui):
        """Test Cancel button discards unsaved changes."""
        config = get_config()
        config.set("midi.auto_connect", True)

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Make a change but don't save
        dialog._auto_connect.setChecked(False)

        # Close without saving
        dialog.reject()

        # Verify setting was NOT saved
        assert config.get("midi.auto_connect") is True

    def test_load_existing_settings(self, qtbot, clean_config_for_gui):
        """Test that existing settings are loaded correctly on dialog open."""
        config = get_config()
        config.set("midi.auto_connect", False)
        config.set("playback.transpose", -5)
        config.set("editor.snap_enabled", False)
        config.set("editor.grid_subdivision", 16)
        config.set("editor.auto_save_interval", 180)
        config.set("ui.language", "zh_TW")

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Verify all settings were loaded
        assert dialog._auto_connect.isChecked() is False
        assert dialog._transpose.value() == -5
        assert dialog._snap_enabled.isChecked() is False
        assert dialog._grid_subdivision.currentData() == 16
        assert dialog._auto_save_interval.value() == 180
        assert dialog._language.currentData() == "zh_TW"

    def test_config_file_path_display(self, qtbot, clean_config_for_gui):
        """Test that config file path is displayed in Advanced tab."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Navigate to Advanced tab
        dialog._tabs.setCurrentIndex(4)

        # Find the config path label (it's the second QLabel in the Advanced tab)
        from PyQt6.QtWidgets import QLabel

        labels = dialog._tabs.currentWidget().findChildren(QLabel)
        config_path_label = labels[1]  # Second label contains the path

        # Verify path is displayed
        assert str(get_config().config_file) in config_path_label.text()
