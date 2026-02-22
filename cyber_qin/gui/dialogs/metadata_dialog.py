"""Metadata editor dialog for library tracks."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.library_metadata import TrackMetadata
from ...core.translator import translator


class MetadataDialog(QDialog):
    """Dialog for editing track metadata (title, artist, game, tags, etc.)."""

    def __init__(
        self,
        metadata: TrackMetadata | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._metadata = metadata or TrackMetadata()
        self._result: TrackMetadata | None = None
        self.setWindowTitle(translator.tr("lib.metadata.title"))
        self.setMinimumSize(400, 350)
        self._build_ui()

    @property
    def metadata_result(self) -> TrackMetadata | None:
        return self._result

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Title
        row = QHBoxLayout()
        row.addWidget(QLabel("Title:"))
        self._title_edit = QLineEdit(self._metadata.title)
        row.addWidget(self._title_edit)
        layout.addLayout(row)

        # Artist
        row = QHBoxLayout()
        row.addWidget(QLabel("Artist:"))
        self._artist_edit = QLineEdit(self._metadata.artist)
        row.addWidget(self._artist_edit)
        layout.addLayout(row)

        # Game
        row = QHBoxLayout()
        row.addWidget(QLabel("Game:"))
        self._game_edit = QLineEdit(self._metadata.game)
        row.addWidget(self._game_edit)
        layout.addLayout(row)

        # Difficulty
        row = QHBoxLayout()
        row.addWidget(QLabel("Difficulty:"))
        self._diff_spin = QSpinBox()
        self._diff_spin.setRange(0, 5)
        self._diff_spin.setValue(self._metadata.difficulty)
        row.addWidget(self._diff_spin)
        row.addWidget(QLabel("/ 5"))
        row.addStretch()
        layout.addLayout(row)

        # Tags
        row = QHBoxLayout()
        row.addWidget(QLabel("Tags:"))
        self._tags_edit = QLineEdit(", ".join(self._metadata.tags))
        self._tags_edit.setPlaceholderText("comma-separated tags")
        row.addWidget(self._tags_edit)
        layout.addLayout(row)

        # Source URL
        row = QHBoxLayout()
        row.addWidget(QLabel("Source:"))
        self._url_edit = QLineEdit(self._metadata.source_url)
        self._url_edit.setPlaceholderText("https://...")
        row.addWidget(self._url_edit)
        layout.addLayout(row)

        # Description
        layout.addWidget(QLabel("Description:"))
        self._desc_edit = QTextEdit()
        self._desc_edit.setPlainText(self._metadata.description)
        self._desc_edit.setMaximumHeight(80)
        layout.addWidget(self._desc_edit)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setMinimumWidth(80)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

    def _on_save(self) -> None:
        tags_text = self._tags_edit.text().strip()
        tags = [t.strip() for t in tags_text.split(",") if t.strip()] if tags_text else []

        self._result = TrackMetadata(
            title=self._title_edit.text().strip(),
            artist=self._artist_edit.text().strip(),
            game=self._game_edit.text().strip(),
            difficulty=self._diff_spin.value(),
            tags=tags,
            source_url=self._url_edit.text().strip(),
            description=self._desc_edit.toPlainText().strip(),
        )
        self.accept()
