"""MIDI file library view with gradient header and empty state illustration — 賽博墨韻."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PyQt6.QtCore import QRectF, QStandardPaths, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.midi_file_player import MidiFileInfo, MidiFileParser
from ..icons import draw_library
from ..theme import TEXT_SECONDARY
from ..widgets.track_list import TrackList

log = logging.getLogger(__name__)


class _LibraryGradientHeader(QWidget):
    """Gradient header for library with 暗金 accent."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(100)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(212, 168, 83, 35))   # 金墨半透明
        gradient.setColorAt(1, QColor(10, 14, 20, 0))       # 透明
        painter.fillRect(QRectF(0, 0, self.width(), self.height()), gradient)
        painter.end()


class _EmptyStateWidget(QWidget):
    """Large empty state illustration with music icon."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2

        # Large library icon
        icon_size = 80
        icon_rect = QRectF(cx - icon_size / 2, h * 0.2, icon_size, icon_size)
        draw_library(painter, icon_rect, QColor(TEXT_SECONDARY))

        # Text
        painter.setPen(QColor(TEXT_SECONDARY))
        font = QFont("Microsoft JhengHei", 16)
        painter.setFont(font)
        text_y = h * 0.2 + icon_size + 20
        painter.drawText(
            0, int(text_y), w, 30,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "尚未匯入任何 MIDI 檔案",
        )

        sub_font = QFont("Microsoft JhengHei", 12)
        painter.setFont(sub_font)
        painter.drawText(
            0, int(text_y + 35), w, 25,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "點擊「+ 匯入 MIDI」開始",
        )

        painter.end()


class LibraryView(QWidget):
    """MIDI file library with import and track list."""

    play_requested = pyqtSignal(str)  # Emits file path
    edit_requested = pyqtSignal(str)  # Emits file path (for editor)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tracks: list[MidiFileInfo] = []

        self._build_ui()
        self._load_library()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Gradient header
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        self._gradient_header = _LibraryGradientHeader()
        header_layout.addWidget(self._gradient_header)

        # Overlay on header
        header_overlay = QWidget(self._gradient_header)
        overlay_layout = QVBoxLayout(header_overlay)
        overlay_layout.setContentsMargins(24, 20, 24, 8)

        header_row = QHBoxLayout()

        title = QLabel("曲庫")
        title.setFont(QFont("Microsoft JhengHei", 22, QFont.Weight.Bold))
        title.setStyleSheet("background: transparent;")
        header_row.addWidget(title)

        header_row.addStretch()

        self._import_btn = QPushButton("+ 匯入 MIDI")
        self._import_btn.setProperty("class", "accent")
        self._import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._import_btn.clicked.connect(self._on_import)
        header_row.addWidget(self._import_btn)

        overlay_layout.addLayout(header_row)

        desc = QLabel("匯入 MIDI 檔案，雙擊或按播放鍵自動演奏")
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        overlay_layout.addWidget(desc)
        overlay_layout.addStretch()

        header_overlay.setGeometry(0, 0, 800, 100)
        root.addWidget(header_container)

        # Content area
        content = QVBoxLayout()
        content.setContentsMargins(24, 8, 24, 12)
        content.setSpacing(8)

        # Column headers
        cols = QHBoxLayout()
        cols.setContentsMargins(12 + 40 + 12, 0, 12, 0)  # Account for track icon
        col_num = QLabel("#")
        col_num.setFixedWidth(24)
        col_num.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        cols.addWidget(col_num)
        col_title = QLabel("標題")
        col_title.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        cols.addWidget(col_title, 1)
        col_dur = QLabel("時長")
        col_dur.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        cols.addWidget(col_dur)
        cols.addSpacing(80)  # Space for buttons
        content.addLayout(cols)

        # Track list
        self._track_list = TrackList()
        self._track_list.play_requested.connect(self._on_play)
        self._track_list.remove_requested.connect(self._on_remove)
        if hasattr(self._track_list, 'edit_requested'):
            self._track_list.edit_requested.connect(self._on_edit)
        content.addWidget(self._track_list, 1)

        # Empty state
        self._empty_state = _EmptyStateWidget()
        content.addWidget(self._empty_state)

        root.addLayout(content, 1)
        self._update_empty_state()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, '_gradient_header'):
            for child in self._gradient_header.children():
                if isinstance(child, QWidget):
                    child.setGeometry(0, 0, self.width(), 100)

    def _on_import(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "匯入 MIDI 檔案",
            "",
            "MIDI Files (*.mid *.midi);;All Files (*)",
        )
        failed: list[str] = []
        for fpath in files:
            try:
                _, info = MidiFileParser.parse(fpath)
                self._tracks.append(info)
                self._track_list.add_track(info)
            except Exception:
                log.exception("Failed to parse %s", fpath)
                failed.append(Path(fpath).name)
        if failed:
            QMessageBox.warning(
                self,
                "匯入失敗",
                "以下檔案無法匯入：\n\n" + "\n".join(f"• {name}" for name in failed),
            )
        self._save_library()
        self._update_empty_state()

    def _on_play(self, index: int) -> None:
        if 0 <= index < len(self._tracks):
            info = self._tracks[index]
            self._track_list.set_playing(index)
            self.play_requested.emit(info.file_path)

    def _on_remove(self, index: int) -> None:
        if 0 <= index < len(self._tracks):
            self._tracks.pop(index)
            self._save_library()
            self._update_empty_state()

    def set_playing(self, index: int) -> None:
        self._track_list.set_playing(index)

    @property
    def playing_index(self) -> int:
        return self._track_list._playing_index

    @property
    def track_count(self) -> int:
        return len(self._tracks)

    def play_next(self) -> str | None:
        """Advance to next track. Returns file_path or None if at end."""
        idx = self._track_list._playing_index + 1
        if 0 <= idx < len(self._tracks):
            self._track_list.set_playing(idx)
            return self._tracks[idx].file_path
        return None

    def play_prev(self) -> str | None:
        """Go to previous track. Returns file_path or None if at start."""
        idx = self._track_list._playing_index - 1
        if 0 <= idx < len(self._tracks):
            self._track_list.set_playing(idx)
            return self._tracks[idx].file_path
        return None

    def play_first(self) -> str | None:
        """Jump to the first track. Returns file_path or None if empty."""
        if self._tracks:
            self._track_list.set_playing(0)
            return self._tracks[0].file_path
        return None

    def play_last(self) -> str | None:
        """Jump to the last track. Returns file_path or None if empty."""
        if self._tracks:
            idx = len(self._tracks) - 1
            self._track_list.set_playing(idx)
            return self._tracks[idx].file_path
        return None

    def add_file(self, file_path: str) -> None:
        """Add a MIDI file to the library programmatically (e.g., from recorder)."""
        try:
            _, info = MidiFileParser.parse(file_path)
            self._tracks.append(info)
            self._track_list.add_track(info)
            self._save_library()
            self._update_empty_state()
        except Exception:
            log.exception("Failed to add %s to library", file_path)

    def _on_edit(self, index: int) -> None:
        if 0 <= index < len(self._tracks):
            self.edit_requested.emit(self._tracks[index].file_path)

    def _update_empty_state(self) -> None:
        has_tracks = len(self._tracks) > 0
        self._track_list.setVisible(has_tracks)
        self._empty_state.setVisible(not has_tracks)

    # --- Persistence ---

    def _library_path(self) -> Path:
        data_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        p = Path(data_dir) / "CyberQin"
        p.mkdir(parents=True, exist_ok=True)
        return p / "library.json"

    def _save_library(self) -> None:
        try:
            data = [
                {
                    "file_path": t.file_path,
                    "name": t.name,
                    "duration_seconds": t.duration_seconds,
                    "track_count": t.track_count,
                    "note_count": t.note_count,
                    "tempo_bpm": t.tempo_bpm,
                }
                for t in self._tracks
            ]
            self._library_path().write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            log.exception("Failed to save library")

    def _load_library(self) -> None:
        path = self._library_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data:
                # Verify file still exists
                if not Path(item["file_path"]).exists():
                    continue
                info = MidiFileInfo(**item)
                self._tracks.append(info)
                self._track_list.add_track(info)
        except Exception:
            log.exception("Failed to load library")
        self._update_empty_state()
