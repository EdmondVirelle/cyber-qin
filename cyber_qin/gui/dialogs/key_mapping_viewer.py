"""Key mapping viewer dialog - displays MIDI note → keyboard key mapping table."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.mapping_schemes import MappingScheme
from ...core.translator import translator
from ..theme import BG_INK, BG_PAPER, TEXT_PRIMARY, TEXT_SECONDARY


class KeyMappingViewer(QDialog):
    """Read-only viewer for key mapping schemes."""

    def __init__(self, scheme: MappingScheme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scheme = scheme
        self.setWindowTitle(translator.tr("mapping_viewer.title"))
        self.setMinimumSize(800, 600)

        self._init_ui()
        self._populate_table()
        self._apply_theme()

    def _init_ui(self) -> None:
        """Initialize UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header with scheme info
        header = QHBoxLayout()

        scheme_name = QLabel(self._scheme.translated_name())
        scheme_name.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TEXT_PRIMARY};")
        header.addWidget(scheme_name)

        header.addStretch()

        key_count_label = QLabel(f"{self._scheme.key_count} {translator.tr('mapping_viewer.keys')}")
        key_count_label.setStyleSheet(f"font-size: 14px; color: {TEXT_SECONDARY};")
        header.addWidget(key_count_label)

        layout.addLayout(header)

        # Description
        desc = QLabel(self._scheme.translated_desc())
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; padding: 8px 0;")
        layout.addWidget(desc)

        # Mapping table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels([
            translator.tr("mapping_viewer.midi_note"),
            translator.tr("mapping_viewer.note_name"),
            translator.tr("mapping_viewer.keyboard_key"),
            translator.tr("mapping_viewer.modifier"),
        ])

        # Configure table appearance
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)

        # Auto-resize columns
        header_view = self._table.horizontalHeader()
        if header_view:
            header_view.setStretchLastSection(True)
            header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _populate_table(self) -> None:
        """Populate the table with mapping data."""
        # Get sorted MIDI notes from the scheme
        midi_notes = sorted(self._scheme.mapping.keys())
        self._table.setRowCount(len(midi_notes))

        for row, midi_note in enumerate(midi_notes):
            mapping = self._scheme.mapping[midi_note]

            # Column 0: MIDI note number
            midi_item = QTableWidgetItem(str(midi_note))
            midi_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, midi_item)

            # Column 1: Note name (e.g., "C4", "F#5")
            note_name = self._midi_to_note_name(midi_note)
            note_item = QTableWidgetItem(note_name)
            note_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 1, note_item)

            # Column 2: Keyboard key (base key without modifier)
            key_name = mapping.label.split("+")[-1]  # Extract base key from "Shift+Z" → "Z"
            key_item = QTableWidgetItem(key_name)
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            key_item.setFont(self._table.font())  # Use monospace-like display
            self._table.setItem(row, 2, key_item)

            # Column 3: Modifier (Shift, Ctrl, or None)
            modifier_text = ""
            if "Shift" in mapping.label:
                modifier_text = "Shift"
            elif "Ctrl" in mapping.label:
                modifier_text = "Ctrl"
            else:
                modifier_text = translator.tr("mapping_viewer.none")

            modifier_item = QTableWidgetItem(modifier_text)
            modifier_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 3, modifier_item)

    @staticmethod
    def _midi_to_note_name(midi_note: int) -> str:
        """Convert MIDI note number to note name (e.g., 60 → C4)."""
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = (midi_note // 12) - 1
        note = note_names[midi_note % 12]
        return f"{note}{octave}"

    def _apply_theme(self) -> None:
        """Apply 賽博墨韻 theme to dialog."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_PAPER};
                color: {TEXT_PRIMARY};
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
            }}
            QTableWidget {{
                background-color: {BG_PAPER};
                color: {TEXT_PRIMARY};
                gridline-color: {BG_INK};
                border: 1px solid {BG_INK};
                border-radius: 4px;
            }}
            QTableWidget::item {{
                padding: 6px 12px;
            }}
            QTableWidget::item:selected {{
                background-color: {BG_INK};
            }}
            QHeaderView::section {{
                background-color: {BG_INK};
                color: {TEXT_PRIMARY};
                padding: 8px;
                border: none;
                font-weight: bold;
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
