"""Virtual keyboard editor view — compose notes with click input and timeline.

Layout:
┌──────────────────────────────────────────────┐
│ Gradient header: "編曲器" (紫霧色)               │
├──────────────────────────────────────────────┤
│ Row 1: [●錄音][▶播放] | [↩][↪][✕]    [存檔][匯入][匯出] │
│ Row 2: 時值[1/4▾] 拍號[4/4▾] BPM[120] □Snap N音符 │
├──────────────────────────────────────────────┤
│ [TrackPanel | PitchRuler | NoteRoll (flex=1)]│
│ [           | spacer(48) | ClickablePiano    ]│
└──────────────────────────────────────────────┘
"""

from __future__ import annotations

import copy
import logging

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QLinearGradient, QPainter
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core import project_file
from ...core.beat_sequence import (
    DURATION_KEYS,
    DURATION_PRESETS,
    TIME_SIGNATURES,
    EditorSequence,
)
from ...core.midi_file_player import MidiFileParser
from ...core.midi_writer import MidiWriter
from ...core.musicxml_parser import import_musicxml
from ...core.translator import translator
from ..theme import BG_PAPER, DIVIDER, TEXT_SECONDARY
from ..widgets.animated_widgets import IconButton
from ..widgets.automation_lane_widget import AutomationLaneWidget
from ..widgets.clickable_piano import ClickablePiano
from ..widgets.editor_track_panel import EditorTrackPanel
from ..widgets.note_roll import FollowMode, NoteRoll
from ..widgets.pitch_ruler import PitchRuler
from ..widgets.score_view_widget import ScoreViewWidget
from ..widgets.speed_control import SpeedControl

log = logging.getLogger(__name__)


class _EditorGradientHeader(QWidget):
    """Gradient header with purple mist accent."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(100)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(160, 100, 220, 35))  # 紫霧半透明
        gradient.setColorAt(1, QColor(10, 14, 20, 0))  # 透明
        painter.fillRect(QRectF(0, 0, self.width(), self.height()), gradient)
        painter.end()


class _ToolbarCard(QWidget):
    """Rounded card container for toolbar controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"_ToolbarCard {{"
            f"  background-color: {BG_PAPER};"
            f"  border-radius: 12px;"
            f"  border: 1px solid {DIVIDER};"
            f"}}"
        )


class _VSeparator(QWidget):
    """Thin vertical divider line between button groups."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(1, 24)
        self.setStyleSheet(f"background-color: {DIVIDER};")


class EditorView(QWidget):
    """Virtual keyboard editor — compose music by clicking piano keys."""

    play_requested = pyqtSignal(list)  # list of MidiFileEvent
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sequence = EditorSequence()
        self._is_recording: bool = False
        self._project_path: str | None = None
        self._player = None  # set by set_player()
        self._preview_player = None  # lazy MidiOutputPlayer
        self._selection_anchor: float | None = None
        self._playback_speed: float = 1.0
        self._arrangement_ghost_notes: list = []

        self._build_ui()
        self._connect_signals()
        self._update_ui_state()

        # Autosave timer — 60s interval
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._on_autosave)
        self._autosave_timer.start(60_000)

        # Deferred autosave recovery check (after widget is shown)
        QTimer.singleShot(500, self._check_autosave_recovery)

    def set_player(self, player) -> None:
        """Set the player controller for playback cursor tracking."""
        self._player = player
        if player is not None:
            player.progress_updated.connect(self._on_playback_progress)
            player.state_changed.connect(self._on_playback_state_changed)
            player.countdown_tick.connect(self._on_countdown_tick)

    def _on_playback_progress(self, current: float, total: float) -> None:
        """Convert seconds to beats for playback cursor."""
        if self._sequence.tempo_bpm > 0:
            beats = current / (60.0 / self._sequence.tempo_bpm)
            self._note_roll.set_playback_beats(beats)

    def _on_playback_state_changed(self, state: int) -> None:
        from ...core.midi_file_player import PlaybackState

        if state == PlaybackState.STOPPED:
            self._note_roll.set_playback_beats(-1)

    def _on_countdown_tick(self, remaining: int) -> None:
        """Update countdown indicator during metronome count-in."""
        if remaining > 0:
            self._countdown_label.setText(str(remaining))
        else:
            self._countdown_label.setText("")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Gradient header
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        self._gradient_header = _EditorGradientHeader()
        header_layout.addWidget(self._gradient_header)

        # Overlay text
        header_overlay = QWidget(self._gradient_header)
        overlay_layout = QVBoxLayout(header_overlay)
        overlay_layout.setContentsMargins(24, 20, 24, 8)

        self._header_lbl = QLabel()
        self._header_lbl.setFont(QFont("Microsoft JhengHei", 22, QFont.Weight.Bold))
        self._header_lbl.setStyleSheet("background: transparent;")
        overlay_layout.addWidget(self._header_lbl)

        self._desc_lbl = QLabel()
        self._desc_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        overlay_layout.addWidget(self._desc_lbl)
        overlay_layout.addStretch()

        header_overlay.setGeometry(0, 0, 800, 100)
        root.addWidget(header_container)

        # Content area
        content = QVBoxLayout()
        content.setContentsMargins(24, 8, 24, 12)
        content.setSpacing(8)

        # Toolbar card
        toolbar_card = _ToolbarCard()
        toolbar_layout = QVBoxLayout(toolbar_card)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(6)

        # Row 1: Transport | Edit | File
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        # Transport group
        self._record_btn = QPushButton()
        self._record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._record_btn.setMinimumWidth(85)
        self._record_btn.setMinimumHeight(36)
        self._record_btn.setToolTip(
            "錄音模式：即時錄製 MIDI 輸入\n"
            "開啟後，彈奏 MIDI 鍵盤會自動記錄音符到編曲器\n"
            "Recording Mode: Real-time MIDI input recording"
        )
        self._record_btn.setStyleSheet(
            "QPushButton { background-color: #661111; color: #FF4444; font-weight: 700; "
            "padding: 6px 12px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #882222; }"
            "QPushButton:pressed { background-color: #AA3333; }"
        )
        row1.addWidget(self._record_btn)

        self._play_btn = QPushButton()
        self._play_btn.setProperty("class", "accent")
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.setMinimumWidth(70)
        self._play_btn.setMinimumHeight(36)
        self._play_btn.setToolTip(
            "播放/暫停：預覽編曲器中的音符\n"
            "空格鍵也可以控制播放\n"
            "Play/Pause: Preview notes in the editor"
        )
        self._play_btn.setStyleSheet(
            "QPushButton { padding: 6px 12px; border-radius: 4px; font-weight: 600; }"
        )
        row1.addWidget(self._play_btn)

        self._stop_btn = QPushButton()
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setMinimumWidth(70)
        self._stop_btn.setMinimumHeight(36)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(
            "QPushButton { padding: 6px 12px; border-radius: 4px; font-weight: 600; }"
            "QPushButton:disabled { color: #555; }"
        )
        row1.addWidget(self._stop_btn)

        # Countdown indicator (shows metronome count-in)
        self._countdown_label = QLabel("")
        self._countdown_label.setMinimumWidth(30)
        self._countdown_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #D4AF37; background: transparent;"
        )
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row1.addWidget(self._countdown_label)

        # Loop toggle button
        self._loop_btn = QPushButton("↻")
        self._loop_btn.setCheckable(True)
        self._loop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._loop_btn.setMinimumWidth(40)
        self._loop_btn.setMinimumHeight(36)
        self._loop_btn.setToolTip(translator.tr("editor.loop.tooltip") + "\n" + "Shortcut: L")
        self._loop_btn.setStyleSheet(
            "QPushButton { padding: 6px 12px; border-radius: 4px; font-weight: 600; background-color: #1A1A2E; }"
            "QPushButton:checked { background-color: #D4AF37; color: #0F0F23; }"
        )
        row1.addWidget(self._loop_btn)

        # Metronome toggle button
        self._metronome_btn = QPushButton("♩")
        self._metronome_btn.setCheckable(True)
        self._metronome_btn.setChecked(True)  # Enabled by default
        self._metronome_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._metronome_btn.setMinimumWidth(40)
        self._metronome_btn.setMinimumHeight(36)
        self._metronome_btn.setToolTip(
            translator.tr("editor.metronome.tooltip") + "\n" + "Shortcut: M"
        )
        self._metronome_btn.setStyleSheet(
            "QPushButton { padding: 6px 12px; border-radius: 4px; font-weight: 600; background-color: #1A1A2E; }"
            "QPushButton:checked { background-color: #D4AF37; color: #0F0F23; }"
        )
        row1.addWidget(self._metronome_btn)

        row1.addWidget(_VSeparator())

        # Edit group
        self._undo_btn = IconButton("undo", size=32)
        self._undo_btn.setToolTip("復原 (Ctrl+Z)")
        row1.addWidget(self._undo_btn)

        self._redo_btn = IconButton("redo", size=32)
        self._redo_btn.setToolTip("重做 (Ctrl+Y)")
        row1.addWidget(self._redo_btn)

        self._clear_btn = IconButton("remove", size=32)
        self._clear_btn.setToolTip("清除全部")
        row1.addWidget(self._clear_btn)

        row1.addWidget(_VSeparator())

        self._pencil_btn = QPushButton()
        self._pencil_btn.setCheckable(True)
        self._pencil_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pencil_btn.setMinimumWidth(70)
        self._pencil_btn.setMinimumHeight(36)
        self._pencil_btn.setToolTip(
            "繪圖模式：用滑鼠點擊編曲器新增音符\n"
            "啟用後可以直接在鋼琴卷軸上畫音符\n"
            "Drawing Mode: Click to add notes on the piano roll"
        )
        self._pencil_btn.setStyleSheet(
            "QPushButton { padding: 6px 10px; border-radius: 4px; font-weight: 600; }"
            "QPushButton:hover { background-color: #1A1F2E; }"
            "QPushButton:checked { background-color: #00F0FF; color: #0A0E14; font-weight: 700; }"
            "QPushButton:checked:hover { background-color: #33F3FF; }"
        )
        row1.addWidget(self._pencil_btn)

        row1.addWidget(_VSeparator())

        # Smart tools group
        self._arrange_btn = QPushButton("🎼 Arrange")
        self._arrange_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._arrange_btn.setMinimumHeight(36)
        self._arrange_btn.setToolTip(
            "智能編排：自動移調與折疊音符到可演奏範圍\n"
            "Smart Arrangement: Auto-transpose and fold notes"
        )
        self._arrange_btn.setStyleSheet(
            "QPushButton { padding: 6px 10px; border-radius: 4px; font-weight: 600; }"
            "QPushButton:hover { background-color: #1A1F2E; }"
        )
        row1.addWidget(self._arrange_btn)

        self._fx_btn = QPushButton()
        self._fx_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fx_btn.setMinimumHeight(36)
        self._fx_btn.setStyleSheet(
            "QPushButton { padding: 6px 10px; border-radius: 4px; font-weight: 600; }"
            "QPushButton:hover { background-color: #1A1F2E; }"
        )
        row1.addWidget(self._fx_btn)

        self._generate_btn = QPushButton()
        self._generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._generate_btn.setMinimumHeight(36)
        self._generate_btn.setStyleSheet(
            "QPushButton { padding: 6px 10px; border-radius: 4px; font-weight: 600; }"
            "QPushButton:hover { background-color: #1A1F2E; }"
        )
        row1.addWidget(self._generate_btn)

        row1.addWidget(_VSeparator())

        # Sidebar toggle
        self._sidebar_toggle_btn = IconButton("menu", size=32)
        self._sidebar_toggle_btn.setCheckable(True)
        self._sidebar_toggle_btn.setChecked(True)  # Default: visible
        row1.addWidget(self._sidebar_toggle_btn)

        row1.addStretch()

        # File group
        self._save_btn = QPushButton()
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setMinimumWidth(65)
        self._save_btn.setMinimumHeight(36)
        self._save_btn.setToolTip("Ctrl+S")
        self._save_btn.setStyleSheet(
            "QPushButton { padding: 6px 10px; border-radius: 4px; font-weight: 600; }"
            "QPushButton:hover { background-color: #1A1F2E; }"
        )
        row1.addWidget(self._save_btn)

        self._load_btn = QPushButton()
        self._load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_btn.setMinimumWidth(65)
        self._load_btn.setMinimumHeight(36)
        self._load_btn.setToolTip(
            "載入 MIDI 檔案到編曲器\n支援標準 MIDI 格式 (.mid)\nLoad MIDI file into the editor"
        )
        self._load_btn.setStyleSheet(
            "QPushButton { padding: 6px 10px; border-radius: 4px; font-weight: 600; }"
            "QPushButton:hover { background-color: #1A1F2E; }"
        )
        row1.addWidget(self._load_btn)

        self._export_btn = QPushButton()
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.setMinimumWidth(65)
        self._export_btn.setMinimumHeight(36)
        self._export_btn.setToolTip("Ctrl+E")
        self._export_btn.setStyleSheet(
            "QPushButton { padding: 6px 12px; border-radius: 4px; font-weight: 600; }"
            "QPushButton:hover { background-color: #1A1F2E; }"
        )
        row1.addWidget(self._export_btn)

        row1.addWidget(_VSeparator())

        self._help_btn = IconButton("help", size=32)
        self._help_btn.setToolTip("操作指南")
        row1.addWidget(self._help_btn)

        toolbar_layout.addLayout(row1)

        # Row 2: Duration | Time Sig | BPM | Snap | Stats
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self._dur_lbl = QLabel()
        row2.addWidget(self._dur_lbl)

        self._duration_combo = QComboBox()
        self._duration_combo.setToolTip(
            "預設音符時值：新增音符時的長度\n"
            "繪圖模式下會使用此時值\n"
            "Default Note Duration: Length of new notes"
        )
        for label in DURATION_PRESETS:
            self._duration_combo.addItem(label)
        self._duration_combo.setCurrentText("1/4")
        row2.addWidget(self._duration_combo)

        row2.addSpacing(8)

        self._ts_lbl = QLabel()
        row2.addWidget(self._ts_lbl)

        self._ts_combo = QComboBox()
        self._ts_combo.setToolTip(
            "拍號：每小節的拍數與拍值\n影響小節線與網格顯示\nTime Signature: Beats per measure"
        )
        for num, denom in TIME_SIGNATURES:
            self._ts_combo.addItem(f"{num}/{denom}")
        self._ts_combo.setCurrentText("4/4")
        row2.addWidget(self._ts_combo)

        row2.addSpacing(8)

        self._bpm_lbl = QLabel()
        row2.addWidget(self._bpm_lbl)

        self._tempo_spin = QSpinBox()
        self._tempo_spin.setRange(40, 300)
        self._tempo_spin.setValue(120)
        self._tempo_spin.setMinimumWidth(80)
        self._tempo_spin.setToolTip(
            "速度：每分鐘節拍數 (BPM)\n影響播放與匯出的速度\nTempo: Beats Per Minute (40-300)"
        )
        row2.addWidget(self._tempo_spin)

        row2.addSpacing(8)

        self._snap_cb = QCheckBox("Snap")
        self._snap_cb.setChecked(True)
        self._snap_cb.setToolTip(
            "網格對齊：移動音符時自動對齊到網格\n"
            "關閉後可以自由移動音符位置\n"
            "Grid Snap: Auto-align notes to grid when moving"
        )
        self._snap_cb.setStyleSheet("background: transparent;")
        row2.addWidget(self._snap_cb)

        # Grid precision selector
        self._grid_precision_combo = QComboBox()
        self._grid_precision_combo.addItem("1/4", 4)
        self._grid_precision_combo.addItem("1/8", 8)
        self._grid_precision_combo.addItem("1/16", 16)
        self._grid_precision_combo.addItem("1/32", 32)
        self._grid_precision_combo.addItem("1/64", 64)
        self._grid_precision_combo.addItem("1/128", 128)
        self._grid_precision_combo.setCurrentIndex(3)  # Default to 1/32
        self._grid_precision_combo.setToolTip(
            "網格精度：對齊到指定的音符時值\n"
            "1/128 = 超精細，1/4 = 粗糙\n"
            "Grid Precision: Snap to specified note value"
        )
        self._grid_precision_combo.setFixedWidth(70)
        self._grid_precision_combo.currentIndexChanged.connect(self._on_grid_precision_changed)
        row2.addWidget(self._grid_precision_combo)

        row2.addSpacing(8)

        # Zoom slider
        self._zoom_lbl = QLabel()
        self._zoom_lbl.setStyleSheet("background: transparent;")
        row2.addWidget(self._zoom_lbl)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(20, 400)  # _MIN_ZOOM to _MAX_ZOOM
        self._zoom_slider.setValue(80)  # _PIXELS_PER_BEAT
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.setToolTip(
            "水平縮放：調整時間軸顯示比例\n"
            "20 = 最遠, 80 = 預設, 400 = 最近\n"
            "Horizontal Zoom: Adjust timeline scale"
        )
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        row2.addWidget(self._zoom_slider)

        row2.addSpacing(8)

        self._auto_tune_cb = QCheckBox()
        self._auto_tune_cb.setToolTip(
            "自動音高校正：將音符對齊到黃色可用區域\n"
            "確保所有音符都在遊戲可彈奏範圍內\n"
            "Auto-Tune: Align notes to playable range"
        )
        self._auto_tune_cb.setStyleSheet("background: transparent;")
        row2.addWidget(self._auto_tune_cb)

        row2.addSpacing(8)

        self._vel_lbl = QLabel()
        row2.addWidget(self._vel_lbl)

        self._velocity_spin = QSpinBox()
        self._velocity_spin.setRange(1, 127)
        self._velocity_spin.setValue(100)
        self._velocity_spin.setToolTip("選取音符的力度 (1-127)")
        self._velocity_spin.setMinimumWidth(80)
        self._velocity_spin.setEnabled(False)
        row2.addWidget(self._velocity_spin)

        row2.addSpacing(8)

        # Follow mode combo
        follow_lbl = QLabel("跟隨 Follow")
        follow_lbl.setStyleSheet("background: transparent;")
        row2.addWidget(follow_lbl)

        self._follow_mode_combo = QComboBox()
        self._follow_mode_combo.addItem("關閉 OFF", 0)
        self._follow_mode_combo.addItem("翻頁 PAGE", 1)
        self._follow_mode_combo.addItem("居中 CONTINUOUS", 2)
        self._follow_mode_combo.addItem("智能 SMART", 3)
        self._follow_mode_combo.setCurrentIndex(3)  # Default to SMART
        self._follow_mode_combo.setFixedWidth(100)
        self._follow_mode_combo.setToolTip(
            "播放跟隨模式：\n"
            "關閉 = 不自動滾動\n"
            "翻頁 = 離開視野時跳頁\n"
            "居中 = 游標永遠居中\n"
            "智能 = 智能門檻跟隨（預設）"
        )
        self._follow_mode_combo.currentIndexChanged.connect(self._on_follow_mode_changed)
        row2.addWidget(self._follow_mode_combo)

        row2.addSpacing(8)

        self._speed_ctrl = SpeedControl()
        self._speed_ctrl.setToolTip(
            "播放速度：調整預覽播放的速度\n"
            "0.5x = 慢速, 1.0x = 正常, 2.0x = 快速\n"
            "Playback Speed: Adjust preview playback rate"
        )
        row2.addWidget(self._speed_ctrl)

        row2.addSpacing(8)

        row2.addSpacing(8)

        self._shortcuts_cb = QCheckBox()
        self._shortcuts_cb.setChecked(True)
        self._shortcuts_cb.setToolTip(
            "鍵盤快捷鍵：啟用編曲器快捷鍵操作\n"
            "空格=播放, Delete=刪除音符, Ctrl+Z/Y=復原/重做\n"
            "Keyboard Shortcuts: Enable editor keyboard shortcuts"
        )
        self._shortcuts_cb.setStyleSheet("background: transparent;")
        row2.addWidget(self._shortcuts_cb)

        row2.addSpacing(8)

        # Ghost notes toggle
        self._ghost_btn = QPushButton("👻 Ghost")
        self._ghost_btn.setCheckable(True)
        self._ghost_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ghost_btn.setMinimumHeight(28)
        self._ghost_btn.setToolTip(
            "幽靈音符：顯示編排前的原始位置\nGhost Notes: Show pre-arrangement positions"
        )
        self._ghost_btn.setStyleSheet(
            "QPushButton { padding: 4px 8px; border-radius: 4px; font-size: 11px; }"
            "QPushButton:checked { background-color: #A06BFF; color: #0A0E14; }"
        )
        row2.addWidget(self._ghost_btn)

        # Ghost opacity slider
        self._ghost_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._ghost_opacity_slider.setRange(10, 80)
        self._ghost_opacity_slider.setValue(40)
        self._ghost_opacity_slider.setFixedWidth(60)
        self._ghost_opacity_slider.setToolTip("Ghost note opacity")
        self._ghost_opacity_slider.setVisible(False)
        self._ghost_opacity_slider.valueChanged.connect(self._on_ghost_opacity_changed)
        row2.addWidget(self._ghost_opacity_slider)

        row2.addSpacing(4)

        # Automation toggle
        self._automation_btn = QPushButton("📈 Auto")
        self._automation_btn.setCheckable(True)
        self._automation_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._automation_btn.setMinimumHeight(28)
        self._automation_btn.setToolTip(
            "自動化曲線：調整力度/速度隨時間變化\n"
            "Automation Lane: Time-varying velocity/tempo curves"
        )
        self._automation_btn.setStyleSheet(
            "QPushButton { padding: 4px 8px; border-radius: 4px; font-size: 11px; }"
            "QPushButton:checked { background-color: #4ECDC4; color: #0A0E14; }"
        )
        row2.addWidget(self._automation_btn)

        row2.addSpacing(4)

        # Score view toggle
        self._score_btn = QPushButton("🎵 Score")
        self._score_btn.setCheckable(True)
        self._score_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._score_btn.setMinimumHeight(28)
        self._score_btn.setToolTip("樂譜顯示：標準五線譜視圖\nScore View: Standard music notation")
        self._score_btn.setStyleSheet(
            "QPushButton { padding: 4px 8px; border-radius: 4px; font-size: 11px; }"
            "QPushButton:checked { background-color: #D4A853; color: #0A0E14; }"
        )
        row2.addWidget(self._score_btn)

        row2.addStretch()

        self._note_count_lbl = QLabel("0 音符")
        self._note_count_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background: transparent; font-size: 12px;"
        )
        row2.addWidget(self._note_count_lbl)

        toolbar_layout.addLayout(row2)
        content.addWidget(toolbar_card)

        # ── Main editor area: [TrackPanel | PitchRuler | NoteRoll] ──
        editor_area = QHBoxLayout()
        editor_area.setSpacing(0)
        editor_area.setContentsMargins(0, 0, 0, 0)

        self._track_panel = EditorTrackPanel()
        editor_area.addWidget(self._track_panel)

        self._pitch_ruler = PitchRuler()
        editor_area.addWidget(self._pitch_ruler)

        self._note_roll = NoteRoll()
        editor_area.addWidget(self._note_roll, 1)

        content.addLayout(editor_area, 1)

        # Automation lane widget (hidden by default)
        self._automation_widget = AutomationLaneWidget()
        self._automation_widget.setVisible(False)
        content.addWidget(self._automation_widget)

        # Score view widget (hidden by default)
        self._score_widget = ScoreViewWidget()
        self._score_widget.setVisible(False)
        self._score_widget.setFixedHeight(180)
        content.addWidget(self._score_widget)

        # ── Piano row: [spacer | ClickablePiano] ──
        piano_row = QHBoxLayout()
        piano_row.setSpacing(0)
        piano_row.setContentsMargins(0, 0, 0, 0)

        # Spacer to align piano with NoteRoll (TrackPanel + PitchRuler widths)
        self._piano_spacer = QWidget()
        self._piano_spacer.setFixedWidth(160 + 48)  # _PANEL_WIDTH + _RULER_WIDTH
        piano_row.addWidget(self._piano_spacer)

        self._piano = ClickablePiano()
        piano_row.addWidget(self._piano, 1)

        content.addLayout(piano_row)

        root.addLayout(content, 1)

        translator.language_changed.connect(self._update_text)
        self._update_text()

    def _update_text(self) -> None:
        """Update UI text based on current language."""
        self._header_lbl.setText(translator.tr("editor.title"))
        self._desc_lbl.setText(translator.tr("editor.desc"))

        # Play button text is stateful — only reset when STOPPED
        from ...core.midi_file_player import PlaybackState

        if self._preview_player is None or self._preview_player.state == PlaybackState.STOPPED:
            self._play_btn.setText(translator.tr("editor.play"))
        elif self._preview_player.state == PlaybackState.PLAYING:
            self._play_btn.setText(translator.tr("editor.pause"))
        elif self._preview_player.state == PlaybackState.PAUSED:
            self._play_btn.setText(translator.tr("editor.resume"))
        self._stop_btn.setText(translator.tr("editor.stop"))
        self._undo_btn.setToolTip(translator.tr("editor.undo"))
        self._redo_btn.setToolTip(translator.tr("editor.redo"))
        self._clear_btn.setToolTip(translator.tr("editor.clear"))
        self._pencil_btn.setText(translator.tr("editor.pencil"))
        self._save_btn.setText(translator.tr("editor.save"))
        self._load_btn.setText(translator.tr("editor.import"))
        self._export_btn.setText(translator.tr("editor.export"))
        self._help_btn.setToolTip(translator.tr("editor.help"))

        self._arrange_btn.setText(translator.tr("editor.arrange"))
        self._fx_btn.setText(translator.tr("editor.fx.label"))
        self._fx_btn.setToolTip(translator.tr("editor.fx.tooltip"))
        self._generate_btn.setText(translator.tr("editor.generate.label"))
        self._generate_btn.setToolTip(translator.tr("editor.generate.tooltip"))
        self._sidebar_toggle_btn.setToolTip(translator.tr("editor.sidebar.tooltip"))
        self._ghost_btn.setText(translator.tr("editor.ghost"))
        self._automation_btn.setText(translator.tr("editor.automation"))
        self._score_btn.setText(translator.tr("editor.score"))

        self._dur_lbl.setText(translator.tr("editor.duration"))
        self._ts_lbl.setText(translator.tr("editor.time_sig"))
        self._bpm_lbl.setText(translator.tr("editor.bpm"))
        self._snap_cb.setText(translator.tr("editor.snap"))
        self._zoom_lbl.setText("縮放 Zoom")  # Simple label, no translation key yet
        self._auto_tune_cb.setText(translator.tr("live.auto_tune"))
        self._vel_lbl.setText(translator.tr("editor.velocity"))
        self._shortcuts_cb.setText(translator.tr("editor.shortcuts"))

        # Stateful record button
        if self._is_recording:
            self._record_btn.setText(
                translator.tr("live.stop_record")
            )  # Use generic stop or editor specific?
            # Editor doesn't have specific stop_record key, reuse live? Or create generic `stop`?
            # live.stop_record is "Stop Rec".
            self._record_btn.setText("■ " + translator.tr("live.stop_record"))
        else:
            self._record_btn.setText(translator.tr("editor.record"))

        # Update note count label format
        self._update_ui_state()

    def _connect_signals(self) -> None:
        self._piano.note_clicked.connect(self._on_note_clicked)
        self._piano.note_pressed.connect(self._on_piano_key_pressed)
        self._piano.note_released.connect(self._on_piano_key_released)
        self._load_btn.clicked.connect(self._on_load)
        self._export_btn.clicked.connect(self._on_export)
        self._save_btn.clicked.connect(self._on_save)
        self._record_btn.clicked.connect(self._on_record_toggle)
        self._play_btn.clicked.connect(self._on_play)
        self._stop_btn.clicked.connect(self._on_stop)
        self._loop_btn.toggled.connect(self._on_loop_toggled)
        self._metronome_btn.toggled.connect(self._on_metronome_toggled)
        self._undo_btn.clicked.connect(self._on_undo)
        self._redo_btn.clicked.connect(self._on_redo)
        self._clear_btn.clicked.connect(self._on_clear)
        self._pencil_btn.toggled.connect(self._on_pencil_toggled)
        self._help_btn.clicked.connect(self._on_help)
        self._sidebar_toggle_btn.toggled.connect(self._on_sidebar_toggled)
        self._arrange_btn.clicked.connect(self._on_arrange)
        self._fx_btn.clicked.connect(self._on_fx)
        self._generate_btn.clicked.connect(self._on_generate)
        self._ghost_btn.toggled.connect(self._on_ghost_toggled)
        self._automation_btn.toggled.connect(self._on_automation_toggled)
        self._score_btn.toggled.connect(self._on_score_toggled)
        self._duration_combo.currentTextChanged.connect(self._on_duration_changed)
        self._ts_combo.currentTextChanged.connect(self._on_ts_changed)
        self._tempo_spin.valueChanged.connect(self._on_tempo_changed)
        self._snap_cb.toggled.connect(self._note_roll.set_snap_enabled)
        self._velocity_spin.valueChanged.connect(self._on_velocity_changed)
        self._speed_ctrl.speed_changed.connect(self._on_speed_changed)

        # NoteRoll signals
        self._note_roll.note_deleted.connect(self._on_note_deleted)
        self._note_roll.note_moved.connect(self._on_note_moved)
        self._note_roll.note_selected.connect(self._on_note_selected_preview)
        self._note_roll.cursor_moved.connect(self._on_cursor_moved)
        self._note_roll.selection_changed.connect(self._on_selection_changed)
        self._note_roll.note_resized.connect(self._on_note_resized)
        self._note_roll.notes_moved.connect(self._on_notes_moved)
        self._note_roll.note_draw_requested.connect(self._on_note_draw)
        self._note_roll.context_menu_requested.connect(self._on_context_menu)
        self._note_roll.zoom_changed.connect(self._on_zoom_changed_from_noteroll)

        # Track panel signals
        self._track_panel.track_activated.connect(self._on_track_activated)
        self._track_panel.track_muted.connect(self._on_track_muted)
        self._track_panel.track_soloed.connect(self._on_track_soloed)
        self._track_panel.track_renamed.connect(self._on_track_renamed)
        self._track_panel.track_removed.connect(self._on_track_removed)
        self._track_panel.track_added.connect(self._on_track_added)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_gradient_header"):
            for child in self._gradient_header.children():
                if isinstance(child, QWidget):
                    child.setGeometry(0, 0, self.width(), 100)

    def _update_ui_state(self) -> None:
        """Sync UI with sequence state."""
        self._invalidate_index_cache()
        active = self._sequence.active_track
        track_notes = self._sequence.notes_in_track(active)
        track_rests = self._sequence.rests_in_track(active)

        # Ghost notes from other tracks
        ghost_notes = []
        for i, t in enumerate(self._sequence.tracks):
            if i != active and not t.muted:
                for n in self._sequence.notes_in_track(i):
                    gn = copy.copy(n)
                    gn._ghost_color = t.color  # type: ignore[attr-defined]
                    ghost_notes.append(gn)

        self._note_roll.set_notes(track_notes)
        self._note_roll.set_rests(track_rests)
        self._note_roll.set_ghost_notes(ghost_notes)
        self._note_roll.set_cursor_beats(self._sequence.cursor_beats)
        self._note_roll.set_tempo(self._sequence.tempo_bpm)
        self._note_roll.set_beats_per_bar(self._sequence.beats_per_bar)

        if active < len(self._sequence.tracks):
            self._note_roll.set_active_track_color(self._sequence.tracks[active].color)

        self._undo_btn.setEnabled(self._sequence.can_undo)
        self._redo_btn.setEnabled(self._sequence.can_redo)

        total = self._sequence.note_count
        bars = self._sequence.bar_count
        total = self._sequence.note_count
        bars = self._sequence.bar_count
        self._note_count_lbl.setText(translator.tr("editor.note_count", notes=total, bars=bars))

        # Update track panel
        self._track_panel.set_tracks(self._sequence.tracks, active)

    # ── Track panel handlers ─────────────────────────────────

    def _on_track_activated(self, index: int) -> None:
        self._sequence.set_active_track(index)
        self._update_ui_state()

    def _on_track_muted(self, index: int, muted: bool) -> None:
        self._sequence.set_track_muted(index, muted)
        self._update_ui_state()

    def _on_track_soloed(self, index: int, solo: bool) -> None:
        self._sequence.set_track_solo(index, solo)
        self._update_ui_state()

    def _on_track_renamed(self, index: int, name: str) -> None:
        self._sequence.rename_track(index, name)
        self._update_ui_state()

    def _on_track_removed(self, index: int) -> None:
        self._sequence.remove_track(index)
        self._update_ui_state()

    def _on_track_added(self) -> None:
        self._sequence.add_track()
        self._update_ui_state()

    # ── NoteRoll signal handlers ─────────────────────────────

    def _on_selection_changed(self, note_indices: list, rest_indices: list) -> None:
        # Store selection for copy/paste/delete
        self._current_note_selection = note_indices
        self._current_rest_selection = rest_indices

        # Update velocity spinbox
        if note_indices:
            self._velocity_spin.setEnabled(True)
            active_notes = self._sequence.notes_in_track(self._sequence.active_track)
            velocities = []
            for i in note_indices:
                if 0 <= i < len(active_notes):
                    velocities.append(active_notes[i].velocity)
            if velocities:
                self._velocity_spin.blockSignals(True)
                self._velocity_spin.setValue(velocities[0])
                self._velocity_spin.blockSignals(False)
        else:
            self._velocity_spin.setEnabled(False)

    def _on_note_resized(self, index: int, new_duration: float) -> None:
        """Handle note resize from NoteRoll."""
        global_idx = self._map_to_global_note_index(index)
        if global_idx >= 0:
            self._sequence.resize_note(global_idx, new_duration)
        self._update_ui_state()

    def _on_notes_moved(self, indices: list, time_delta: float, pitch_delta: int) -> None:
        """Handle batch move from NoteRoll."""
        global_indices = [self._map_to_global_note_index(i) for i in indices]
        global_indices = [gi for gi in global_indices if gi >= 0]
        if global_indices:
            self._sequence.move_notes(global_indices, time_delta, pitch_delta)
        self._update_ui_state()

    def _on_grid_precision_changed(self, index: int) -> None:
        """Handle grid precision selection change."""
        precision = self._grid_precision_combo.itemData(index)
        if precision:
            self._note_roll.set_grid_precision(precision)

    def _on_zoom_slider_changed(self, value: int) -> None:
        """Handle zoom slider value change."""
        # Block signals to prevent feedback loop
        self._note_roll.blockSignals(True)
        self._note_roll.set_zoom(float(value))
        self._note_roll.blockSignals(False)

    def _on_zoom_changed_from_noteroll(self, zoom: float) -> None:
        """Update slider when zoom changes via wheel/keyboard."""
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(int(zoom))
        self._zoom_slider.blockSignals(False)
        # Sync automation and score widgets
        self._automation_widget.set_zoom(zoom)
        self._score_widget.set_scroll_x(self._note_roll._scroll_x)

    def _on_follow_mode_changed(self, index: int) -> None:
        """Handle follow mode selection change."""
        mode_value = self._follow_mode_combo.itemData(index)
        if mode_value is not None:
            self._note_roll.set_follow_mode(FollowMode(mode_value))

    # ── Index mapping helpers ────────────────────────────────

    def _invalidate_index_cache(self) -> None:
        """Clear cached index maps — called on every UI refresh."""
        self._note_index_map: dict[int, int] | None = None
        self._rest_index_map: dict[int, int] | None = None

    def _ensure_note_index_map(self) -> dict[int, int]:
        """Build (or return cached) track-local → global note index mapping."""
        if self._note_index_map is not None:
            return self._note_index_map
        active = self._sequence.active_track
        local_idx = 0
        mapping: dict[int, int] = {}
        for gi, n in enumerate(self._sequence._notes):
            if n.track == active:
                mapping[local_idx] = gi
                local_idx += 1
        self._note_index_map = mapping
        return mapping

    def _ensure_rest_index_map(self) -> dict[int, int]:
        """Build (or return cached) track-local → global rest index mapping."""
        if self._rest_index_map is not None:
            return self._rest_index_map
        active = self._sequence.active_track
        local_idx = 0
        mapping: dict[int, int] = {}
        for gi, r in enumerate(self._sequence._rests):
            if r.track == active:
                mapping[local_idx] = gi
                local_idx += 1
        self._rest_index_map = mapping
        return mapping

    def _map_to_global_note_index(self, track_local_idx: int) -> int:
        """Map a track-local note index to a global index in sequence._notes."""
        return self._ensure_note_index_map().get(track_local_idx, -1)

    def _map_to_global_rest_index(self, track_local_idx: int) -> int:
        """Map a track-local rest index to a global index in sequence._rests."""
        return self._ensure_rest_index_map().get(track_local_idx, -1)

    # ── Note events ──────────────────────────────────────────

    def _on_note_clicked(self, midi_note: int) -> None:
        flash_beat = self._sequence.cursor_beats
        self._sequence.add_note(midi_note)
        self._update_ui_state()
        self._note_roll.flash_at_beat(flash_beat)
        self._preview_midi_note(midi_note)

    def _on_note_draw(self, time_beats: float, midi_note: int) -> None:
        """Handle pencil tool draw on NoteRoll."""
        self._sequence.add_note_at(time_beats, midi_note)
        self._update_ui_state()
        self._note_roll.flash_at_beat(time_beats)
        self._preview_midi_note(midi_note)

    def _on_pencil_toggled(self, checked: bool) -> None:
        self._note_roll.set_pencil_mode(checked)

    def _on_sidebar_toggled(self, checked: bool) -> None:
        """Toggle visibility of track panel and pitch ruler."""
        self._track_panel.setVisible(checked)
        self._pitch_ruler.setVisible(checked)
        # Adjust piano spacer width to match sidebar visibility
        self._piano_spacer.setFixedWidth((160 + 48) if checked else 0)

    def _on_velocity_changed(self, value: int) -> None:
        """Update velocity of all selected notes."""
        note_sel = getattr(self, "_current_note_selection", [])
        if not note_sel:
            return
        global_indices = [self._map_to_global_note_index(i) for i in note_sel]
        global_indices = [gi for gi in global_indices if gi >= 0]
        if global_indices:
            self._sequence.set_notes_velocity(global_indices, value)
            self._update_ui_state()

    def _on_note_selected_preview(self, index: int) -> None:
        """Play audio preview when a note is clicked in NoteRoll."""
        active_notes = self._sequence.notes_in_track(self._sequence.active_track)
        if 0 <= index < len(active_notes):
            self._preview_midi_note(active_notes[index].note)

    def _on_piano_key_pressed(self, midi_note: int) -> None:
        """Play audio preview when piano key is pressed."""
        player = self._ensure_preview_player()
        if player is not None:
            # Send note_on directly for held preview
            if player._midi_out is not None:
                player._midi_out.send_message([0x90, midi_note & 0x7F, 100])

    def _on_piano_key_released(self, midi_note: int) -> None:
        """Stop audio when piano key is released."""
        player = self._ensure_preview_player()
        if player is not None:
            if player._midi_out is not None:
                player._midi_out.send_message([0x80, midi_note & 0x7F, 0])

    def _preview_midi_note(self, midi_note: int) -> None:
        """Play a short preview of a MIDI note."""
        player = self._ensure_preview_player()
        if player is not None:
            player.preview_note(midi_note, velocity=80, duration_ms=150)

    def _quantize_selection(self) -> None:
        """Quantize selected notes to the current step grid."""
        note_sel = getattr(self, "_current_note_selection", [])
        if not note_sel:
            return
        global_indices = [self._map_to_global_note_index(i) for i in note_sel]
        global_indices = [gi for gi in global_indices if gi >= 0]
        if global_indices:
            self._sequence.quantize_notes(global_indices, self._sequence.step_duration)
            self._update_ui_state()

    def _on_context_menu(self, x: float, y: float) -> None:
        """Show context menu at NoteRoll position."""
        menu = QMenu(self)
        has_sel = bool(
            getattr(self, "_current_note_selection", [])
            or getattr(self, "_current_rest_selection", [])
        )
        has_clip = not self._sequence.clipboard_empty

        act_select_all = menu.addAction("全選\tCtrl+A")
        if act_select_all:
            act_select_all.triggered.connect(self._note_roll.select_all)

        menu.addSeparator()

        act_copy = menu.addAction("複製\tCtrl+C")
        if act_copy:
            act_copy.setEnabled(has_sel)
            act_copy.triggered.connect(self._copy_selection)

        act_cut = menu.addAction("剪下\tCtrl+X")
        if act_cut:
            act_cut.setEnabled(has_sel)
            act_cut.triggered.connect(self._cut_selection)

        act_paste = menu.addAction("貼上\tCtrl+V")
        if act_paste:
            act_paste.setEnabled(has_clip)
            act_paste.triggered.connect(self._paste)

        act_delete = menu.addAction("刪除\tDelete")
        if act_delete:
            act_delete.setEnabled(has_sel)
            act_delete.triggered.connect(self._delete_selection)

        menu.addSeparator()

        act_quantize = menu.addAction("量化對齊\tCtrl+Q")
        if act_quantize:
            act_quantize.setEnabled(has_sel)
            act_quantize.triggered.connect(self._quantize_selection)

        menu.addSeparator()

        act_pencil = menu.addAction("鉛筆模式\tP")
        if act_pencil:
            act_pencil.setCheckable(True)
            act_pencil.setChecked(self._pencil_btn.isChecked())
            act_pencil.triggered.connect(self._pencil_btn.setChecked)

        from PyQt6.QtCore import QPoint

        screen_pos = self._note_roll.mapToGlobal(QPoint(int(x), int(y)))
        menu.exec(screen_pos)

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "載入檔案",
            "",
            "All Supported Files (*.mid *.midi *.xml *.musicxml *.abc *.ly *.cqp);;"
            "MIDI Files (*.mid *.midi);;"
            "MusicXML Files (*.xml *.musicxml);;"
            "ABC Notation (*.abc);;"
            "LilyPond (*.ly);;"
            "CQP Projects (*.cqp);;"
            "All Files (*)",
        )
        if not path:
            return
        if path.endswith(".cqp"):
            self._load_project(path)
        else:
            self.load_file(path)

    def load_file(self, file_path: str) -> None:
        """Load a MIDI, MusicXML, ABC, or LilyPond file into the editor."""
        try:
            if file_path.endswith((".xml", ".musicxml")):
                self._load_musicxml(file_path)
            elif file_path.endswith(".abc"):
                self._load_abc(file_path)
            elif file_path.endswith(".ly"):
                self._load_lilypond(file_path)
            else:
                # Load as MIDI
                events, info = MidiFileParser.parse(file_path)
                self._sequence = EditorSequence.from_midi_file_events(
                    events,
                    tempo_bpm=info.tempo_bpm,
                )
                self._tempo_spin.blockSignals(True)
                self._tempo_spin.setValue(int(self._sequence.tempo_bpm))
                self._tempo_spin.blockSignals(False)
                self._project_path = None
                self._update_ui_state()
        except Exception:
            log.exception("Failed to load %s", file_path)

    def _load_project(self, path: str) -> None:
        """Load a .cqp project file."""
        try:
            self._sequence = project_file.load(path)
            self._project_path = path
            self._tempo_spin.blockSignals(True)
            self._tempo_spin.setValue(int(self._sequence.tempo_bpm))
            self._tempo_spin.blockSignals(False)
            self._update_ui_state()
        except Exception:
            log.exception("Failed to load project %s", path)

    def _load_musicxml(self, path: str) -> None:
        """Load a MusicXML file (.xml or .musicxml)."""
        try:
            from cyber_qin.core.beat_sequence import BeatNote

            notes, tempo_bpm, time_signature = import_musicxml(path)

            # Convert MusicXML notes to EditorSequence
            self._sequence = EditorSequence()
            self._sequence.tempo_bpm = tempo_bpm
            self._sequence.time_signature = time_signature

            # Add all notes directly to the internal list (no public API for custom duration)
            for xml_note in notes:
                beat_note = BeatNote(
                    time_beats=xml_note.start_time,
                    duration_beats=xml_note.duration,
                    note=xml_note.pitch,
                    velocity=xml_note.velocity,
                    track=0,
                )
                self._sequence._notes.append(beat_note)

            # Sort notes by time and invalidate cache
            self._sequence._notes.sort(key=lambda n: n.time_beats)
            self._sequence._invalidate_cache()

            self._tempo_spin.blockSignals(True)
            self._tempo_spin.setValue(int(self._sequence.tempo_bpm))
            self._tempo_spin.blockSignals(False)
            self._project_path = None
            self._update_ui_state()
        except Exception:
            log.exception("Failed to load MusicXML %s", path)

    def _load_abc(self, path: str) -> None:
        """Load an ABC notation file."""
        try:
            from pathlib import Path

            from ...core.abc_parser import parse_abc

            text = Path(path).read_text(encoding="utf-8")
            result = parse_abc(text)

            self._sequence = EditorSequence()
            self._sequence.tempo_bpm = result.tempo_bpm or 120.0
            for n in result.notes:
                self._sequence._notes.append(n)
            self._sequence._notes.sort(key=lambda n: n.time_beats)
            self._sequence._invalidate_cache()

            self._tempo_spin.blockSignals(True)
            self._tempo_spin.setValue(int(self._sequence.tempo_bpm))
            self._tempo_spin.blockSignals(False)
            self._project_path = None
            self._update_ui_state()
        except Exception:
            log.exception("Failed to load ABC %s", path)

    def _load_lilypond(self, path: str) -> None:
        """Load a LilyPond file."""
        try:
            from pathlib import Path

            from ...core.lilypond_parser import parse_lilypond

            text = Path(path).read_text(encoding="utf-8")
            result = parse_lilypond(text)

            self._sequence = EditorSequence()
            self._sequence.tempo_bpm = result.tempo_bpm or 120.0
            for n in result.notes:
                self._sequence._notes.append(n)
            self._sequence._notes.sort(key=lambda n: n.time_beats)
            self._sequence._invalidate_cache()

            self._tempo_spin.blockSignals(True)
            self._tempo_spin.setValue(int(self._sequence.tempo_bpm))
            self._tempo_spin.blockSignals(False)
            self._project_path = None
            self._update_ui_state()
        except Exception:
            log.exception("Failed to load LilyPond %s", path)

    def _on_export(self) -> None:
        if self._sequence.note_count == 0:
            return

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "匯出檔案",
            "",
            "MIDI Files (*.mid);;"
            "ABC Notation (*.abc);;"
            "LilyPond (*.ly);;"
            "WAV Audio (*.wav);;"
            "All Files (*)",
        )
        if not path:
            return

        try:
            if "*.abc" in selected_filter or path.endswith(".abc"):
                if not path.endswith(".abc"):
                    path += ".abc"
                self._export_abc(path)
            elif "*.ly" in selected_filter or path.endswith(".ly"):
                if not path.endswith(".ly"):
                    path += ".ly"
                self._export_lilypond(path)
            elif "*.wav" in selected_filter or path.endswith(".wav"):
                if not path.endswith(".wav"):
                    path += ".wav"
                self._export_wav(path)
            else:
                if not path.endswith(".mid"):
                    path += ".mid"
                midi_events = self._sequence.to_midi_file_events()
                tracks = self._sequence.tracks
                track_names = [t.name for t in tracks]
                track_channels = [t.channel for t in tracks]
                MidiWriter.save_multitrack(
                    midi_events,
                    path,
                    tempo_bpm=self._sequence.tempo_bpm,
                    track_names=track_names,
                    track_channels=track_channels,
                )
        except Exception:
            log.exception("Failed to export %s", path)

    def _export_abc(self, path: str) -> None:
        """Export notes as ABC notation."""
        from pathlib import Path

        from ...core.abc_parser import export_abc

        text = export_abc(self._sequence.notes, tempo_bpm=int(self._sequence.tempo_bpm))
        Path(path).write_text(text, encoding="utf-8")

    def _export_lilypond(self, path: str) -> None:
        """Export notes as LilyPond notation."""
        from pathlib import Path

        from ...core.lilypond_parser import export_lilypond

        text = export_lilypond(self._sequence.notes, tempo_bpm=int(self._sequence.tempo_bpm))
        Path(path).write_text(text, encoding="utf-8")

    def _export_wav(self, path: str) -> None:
        """Export notes as WAV audio."""
        from ...core.audio_exporter import export_wav

        export_wav(self._sequence.notes, path, tempo_bpm=self._sequence.tempo_bpm)

    def _on_save(self) -> None:
        """Save project (Ctrl+S). If no path, prompt save-as."""
        if self._project_path:
            try:
                project_file.save(self._project_path, self._sequence)
            except Exception:
                log.exception("Failed to save project")
        else:
            self._on_save_as()

    def _on_save_as(self) -> None:
        """Save project to a new path (Ctrl+Shift+S)."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "儲存專案",
            "",
            "CQP Projects (*.cqp);;All Files (*)",
        )
        if not path:
            return
        if not path.endswith(".cqp"):
            path += ".cqp"
        try:
            project_file.save(path, self._sequence)
            self._project_path = path
        except Exception:
            log.exception("Failed to save project %s", path)

    def _on_autosave(self) -> None:
        """Periodic autosave."""
        if self._sequence.note_count > 0 or self._sequence.rest_count > 0:
            try:
                project_file.autosave(self._sequence)
            except Exception:
                log.debug("Autosave failed", exc_info=True)

    def _check_autosave_recovery(self) -> None:
        """Check for autosave file and offer recovery."""
        if self._sequence.note_count > 0 or self._sequence.rest_count > 0:
            return  # Already has content, don't overwrite
        recovered = project_file.load_autosave()
        if recovered is None or (recovered.note_count == 0 and recovered.rest_count == 0):
            return
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "恢復自動存檔",
            f"偵測到自動存檔 ({recovered.note_count} 音符)。\n要恢復嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._sequence = recovered
            self._tempo_spin.blockSignals(True)
            self._tempo_spin.setValue(int(self._sequence.tempo_bpm))
            self._tempo_spin.blockSignals(False)
            self._update_ui_state()
            log.info("Recovered %d notes from autosave", recovered.note_count)

    def _on_record_toggle(self) -> None:
        if self._is_recording:
            self._is_recording = False
            self._record_btn.setText(translator.tr("editor.record"))
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #661111; color: #FF4444; font-weight: 700; }"
                "QPushButton:hover { background-color: #882222; }"
            )
            self._update_text()  # Enforce correct text
            self.recording_stopped.emit()
        else:
            self._is_recording = True
            self._record_btn.setText("■ " + translator.tr("live.stop_record"))
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #ff4444; color: #0A0E14; "
                "border: none; border-radius: 16px; padding: 8px 20px; "
                "font-weight: 700; }"
                "QPushButton:hover { background-color: #ff6666; }"
            )
            self._update_text()  # Enforce text
            self.recording_started.emit()

    def _on_note_moved(self, index: int, time_delta: float, pitch_delta: int) -> None:
        global_idx = self._map_to_global_note_index(index)
        if global_idx >= 0:
            self._sequence.move_note(global_idx, time_delta, pitch_delta)
        self._update_ui_state()

    # _on_note_right_click_delete removed — replaced by context menu

    @property
    def auto_tune_enabled(self) -> bool:
        return self._auto_tune_cb.isChecked()

    def set_recorded_events(self, events: list) -> None:
        """Merge recorded events into the current sequence."""
        recorded_seq = EditorSequence.from_midi_file_events(
            events,
            tempo_bpm=self._sequence.tempo_bpm,
        )
        self._sequence._push_undo()
        self._sequence._notes.extend(recorded_seq._notes)
        self._sequence._notes.sort(key=lambda n: n.time_beats)
        self._update_ui_state()

    def _ensure_preview_player(self):
        """Lazily create the MidiOutputPlayer for piano preview."""
        if self._preview_player is not None:
            return self._preview_player
        try:
            from ...core.midi_output_player import create_midi_output_player

            player = create_midi_output_player(self)
            if player is not None:
                player.progress_updated.connect(self._on_preview_progress)
                player.state_changed.connect(self._on_preview_state_changed)
                player.note_fired.connect(self._on_preview_note_fired)
                self._preview_player = player
                # Apply persisted speed
                player.set_speed(self._playback_speed)
        except Exception:
            log.debug("Failed to create preview player", exc_info=True)
        return self._preview_player

    def _on_preview_progress(self, current: float, total: float) -> None:
        if self._sequence.tempo_bpm > 0:
            beats = current / (60.0 / self._sequence.tempo_bpm)
            self._note_roll.set_playback_beats(beats)

    def _on_preview_state_changed(self, state: int) -> None:
        from ...core.midi_file_player import PlaybackState

        if state == PlaybackState.STOPPED:
            self._note_roll.set_playback_beats(-1)
            self._play_btn.setText(translator.tr("editor.play"))
            self._play_btn.setStyleSheet(
                "QPushButton { padding: 6px 12px; border-radius: 4px; font-weight: 600; }"
            )
            self._stop_btn.setEnabled(False)
            self._piano.set_active_notes(set())
            self._note_roll.set_active_notes(set())
        elif state == PlaybackState.PLAYING:
            self._play_btn.setText(translator.tr("editor.pause"))
            self._play_btn.setStyleSheet(
                "QPushButton { background-color: #00F0FF; color: #0A0E14; font-weight: 700; "
                "padding: 6px 12px; border-radius: 4px; }"
                "QPushButton:hover { background-color: #33F3FF; }"
            )
            self._stop_btn.setEnabled(True)
        elif state == PlaybackState.PAUSED:
            self._play_btn.setText(translator.tr("editor.resume"))
            self._play_btn.setStyleSheet(
                "QPushButton { background-color: #D4AF37; color: #0A0E14; font-weight: 700; "
                "padding: 6px 12px; border-radius: 4px; }"
                "QPushButton:hover { background-color: #E0C060; }"
            )
            self._stop_btn.setEnabled(True)

    def _on_preview_note_fired(self, event_type: str, note: int, velocity: int) -> None:
        """Handle real-time playback feedback."""
        # Update ClickablePiano
        if event_type == "note_on":
            self._piano.note_on(note)
            # Update NoteRoll active notes
            current_active = self._piano._active_notes
            self._note_roll.set_active_notes(current_active)
        elif event_type == "note_off":
            self._piano.note_off(note)
            # Update NoteRoll active notes
            current_active = self._piano._active_notes
            self._note_roll.set_active_notes(current_active)

    def _on_play(self) -> None:
        if self._sequence.note_count == 0:
            return

        player = self._ensure_preview_player()
        if player is not None:
            from ...core.midi_file_player import PlaybackState

            if player.state == PlaybackState.PLAYING:
                player.pause()
                return
            if player.state == PlaybackState.PAUSED:
                player.play()  # Resume
                return
            # STOPPED → load and start fresh
            events = self._sequence.to_midi_file_events()
            duration = self._sequence.duration_seconds
            player.load(events, duration)
            player.play()
            return

        # Fallback: SendInput player via app_shell
        events = self._sequence.to_midi_file_events()
        self.play_requested.emit(events)

    def _on_stop(self) -> None:
        if self._preview_player is not None:
            self._preview_player.stop()

    def _on_loop_toggled(self, checked: bool) -> None:
        """Handle loop button toggle."""
        player = self._ensure_preview_player()
        if player is not None:
            player.set_loop(checked)

    def _on_metronome_toggled(self, checked: bool) -> None:
        """Handle metronome button toggle."""
        player = self._ensure_preview_player()
        if player is not None:
            player.set_metronome(checked)

    def _on_undo(self) -> None:
        self._sequence.undo()
        self._update_ui_state()

    def _on_redo(self) -> None:
        self._sequence.redo()
        self._update_ui_state()

    def _on_clear(self) -> None:
        self._sequence.clear()
        self._update_ui_state()

    def _on_help(self) -> None:
        """Show editor help dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle("編曲器操作指南")
        dlg.resize(600, 700)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {BG_PAPER}; border: none; }}")

        content = QLabel()
        content.setWordWrap(True)
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        content.setContentsMargins(24, 20, 24, 20)
        content.setStyleSheet(
            f"QLabel {{"
            f"  background-color: {BG_PAPER};"
            f"  color: {TEXT_SECONDARY};"
            f"  font-family: 'Microsoft JhengHei';"
            f"  font-size: 13px;"
            f"}}"
        )

        html = (
            "<h2 style='color:#E8E0D0;'>編曲器操作指南</h2>"
            "<h3 style='color:#00F0FF;'>一、基本輸入</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>點擊底部琴鍵</td>"
            "<td>在游標位置插入音符</td></tr>"
            "<tr><td style='color:#E8E0D0;'>數字鍵 1-5</td>"
            "<td>切換時值（全音符～十六分音符）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>0 鍵</td>"
            "<td>插入休止符</td></tr>"
            "<tr><td style='color:#E8E0D0;'>← → 方向鍵</td>"
            "<td>移動游標</td></tr>"
            "</table>"
            "<h3 style='color:#00F0FF;'>二、鉛筆工具</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>P 鍵 或 工具列「✎鉛筆」</td>"
            "<td>切換鉛筆模式</td></tr>"
            "<tr><td style='color:#E8E0D0;'>鉛筆模式下點擊音符捲軸空白處</td>"
            "<td>直接放置音符</td></tr>"
            "</table>"
            "<h3 style='color:#00F0FF;'>三、選取與編輯</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>點擊音符</td>"
            "<td>選取單個音符</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+點擊</td>"
            "<td>加選／取消選取</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Shift+拖曳</td>"
            "<td>框選（矩形選取）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+A</td>"
            "<td>全選</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Delete</td>"
            "<td>刪除選取的音符</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Alt+方向鍵</td>"
            "<td>移動選取的音符（上下=音高，左右=時間）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Alt+Shift+左右</td>"
            "<td>調整選取音符的長度</td></tr>"
            "<tr><td style='color:#E8E0D0;'>拖曳音符右邊緣</td>"
            "<td>調整單個音符長度（6px 範圍）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Shift+左右</td>"
            "<td>游標範圍選取</td></tr>"
            "</table>"
            "<h3 style='color:#00F0FF;'>四、剪貼簿</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+C</td>"
            "<td>複製</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+X</td>"
            "<td>剪下</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+V</td>"
            "<td>貼上（在游標位置）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+D</td>"
            "<td>複製音符到游標位置</td></tr>"
            "</table>"
            "<h3 style='color:#00F0FF;'>五、編輯操作</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+Z</td>"
            "<td>復原</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+Y</td>"
            "<td>重做</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+Q</td>"
            "<td>量化對齊（對齊到目前的步長網格）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+S</td>"
            "<td>存檔（.cqp 專案）</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+Shift+S</td>"
            "<td>另存新檔</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+E</td>"
            "<td>匯出為 MIDI (.mid)</td></tr>"
            "</table>"
            "<h3 style='color:#00F0FF;'>六、音軌操作</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>點擊音軌</td>"
            "<td>切換作用中音軌</td></tr>"
            "<tr><td style='color:#E8E0D0;'>雙擊音軌名稱</td>"
            "<td>重新命名</td></tr>"
            "<tr><td style='color:#E8E0D0;'>M 按鈕 / S 按鈕</td>"
            "<td>靜音 / 獨奏</td></tr>"
            "<tr><td style='color:#E8E0D0;'>右鍵點擊音軌</td>"
            "<td>刪除音軌</td></tr>"
            "<tr><td style='color:#E8E0D0;'>＋ 按鈕</td>"
            "<td>新增音軌</td></tr>"
            "<tr><td style='color:#E8E0D0;'>其他音軌的音符</td>"
            "<td>以半透明「鬼影」顯示</td></tr>"
            "</table>"
            "<h3 style='color:#00F0FF;'>七、播放</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>Space</td>"
            "<td>播放／停止</td></tr>"
            "<tr><td style='color:#E8E0D0;'>需要 MIDI 輸出裝置</td>"
            "<td>（如 Microsoft GS Wavetable）</td></tr>"
            "</table>"
            "<h3 style='color:#00F0FF;'>八、右鍵選單</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>在音符捲軸上右鍵</td>"
            "<td>全選、複製、剪下、貼上、刪除、量化對齊、鉛筆模式</td></tr>"
            "</table>"
            "<h3 style='color:#00F0FF;'>九、其他</h3>"
            "<table cellpadding='4'>"
            "<tr><td style='color:#E8E0D0;'>滾輪</td>"
            "<td>水平捲動時間軸</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Ctrl+滾輪</td>"
            "<td>縮放時間軸</td></tr>"
            "<tr><td style='color:#E8E0D0;'>Snap 勾選框</td>"
            "<td>啟用／停用吸附到網格</td></tr>"
            "<tr><td style='color:#E8E0D0;'>力度欄位</td>"
            "<td>選取音符後可調整力度 (1-127)</td></tr>"
            "<tr><td style='color:#E8E0D0;'>自動校正勾選框</td>"
            "<td>錄音時自動校正音高</td></tr>"
            "<tr><td style='color:#E8E0D0;'>自動存檔</td>"
            "<td>每 60 秒自動存檔</td></tr>"
            "<tr><td style='color:#E8E0D0;'>速度選擇器</td>"
            "<td>播放速度 0.25x ~ 2.0x</td></tr>"
            "<tr><td style='color:#E8E0D0;'>⌨ 快捷鍵 勾選框</td>"
            "<td>啟用／停用單鍵快捷鍵（Ctrl+S/Z/Y 不受影響）</td></tr>"
            "</table>"
        )
        content.setText(html)

        scroll.setWidget(content)
        layout.addWidget(scroll)
        dlg.exec()

    def _on_duration_changed(self, label: str) -> None:
        self._sequence.set_step_duration(label)

    def _on_ts_changed(self, text: str) -> None:
        parts = text.split("/")
        if len(parts) == 2:
            try:
                num, denom = int(parts[0]), int(parts[1])
                self._sequence.time_signature = (num, denom)
                self._update_ui_state()
            except ValueError:
                pass

    def _on_tempo_changed(self, value: int) -> None:
        self._sequence.tempo_bpm = float(value)
        self._note_roll.set_tempo(self._sequence.tempo_bpm)

    def _on_speed_changed(self, speed: float) -> None:
        """Update playback speed on the preview player."""
        self._playback_speed = speed
        if self._preview_player is not None:
            self._preview_player.set_speed(speed)

    # ── Smart Tools ──────────────────────────────────────────

    def _on_arrange(self) -> None:
        """Apply smart arrangement to current track's notes."""
        from ...core.smart_arrangement import smart_arrange

        notes = self._sequence.notes
        if not notes:
            return

        # Store pre-arrangement as ghost reference
        self._arrangement_ghost_notes = [copy.copy(n) for n in notes]

        result = smart_arrange(notes)
        self._sequence._push_undo()

        # Replace notes
        self._sequence._notes = list(result.notes)
        self._sequence._notes.sort(key=lambda n: n.time_beats)
        self._sequence._invalidate_cache()
        self._update_ui_state()

        log.info(
            "Arranged: transpose=%+d, folded=%d, strategy=%s",
            result.transpose_semitones,
            result.notes_folded,
            result.strategy_used,
        )

    def _on_fx(self) -> None:
        """Open the MIDI FX dialog."""
        from ..dialogs.fx_dialog import FxDialog

        notes = self._sequence.notes
        if not notes:
            return

        dlg = FxDialog(notes, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result_notes = dlg.result_notes
            if result_notes is not None:
                self._sequence._push_undo()
                self._sequence._notes = list(result_notes)
                self._sequence._notes.sort(key=lambda n: n.time_beats)
                self._sequence._invalidate_cache()
                self._update_ui_state()

    def _on_generate(self) -> None:
        """Open the melody generator dialog."""
        from ..dialogs.melody_dialog import MelodyDialog

        dlg = MelodyDialog(
            tempo_bpm=self._sequence.tempo_bpm,
            time_signature=self._sequence.time_signature,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            generated = dlg.result_notes
            if generated:
                self._sequence._push_undo()
                for n in generated:
                    self._sequence._notes.append(n)
                self._sequence._notes.sort(key=lambda n: n.time_beats)
                self._sequence._invalidate_cache()
                self._update_ui_state()

    def _on_ghost_toggled(self, checked: bool) -> None:
        """Toggle arrangement ghost notes visibility."""
        self._ghost_opacity_slider.setVisible(checked)
        ghost = getattr(self, "_arrangement_ghost_notes", [])
        if checked and ghost:
            opacity = self._ghost_opacity_slider.value() / 100.0
            self._note_roll.set_arrangement_ghost_notes(ghost)
            self._note_roll.set_arrangement_ghost_opacity(opacity)
        else:
            self._note_roll.set_arrangement_ghost_notes([])

    def _on_ghost_opacity_changed(self, value: int) -> None:
        ghost = getattr(self, "_arrangement_ghost_notes", [])
        if self._ghost_btn.isChecked() and ghost:
            self._note_roll.set_arrangement_ghost_opacity(value / 100.0)

    def _on_automation_toggled(self, checked: bool) -> None:
        """Toggle automation lane visibility."""
        if hasattr(self, "_automation_widget"):
            self._automation_widget.setVisible(checked)

    def _on_score_toggled(self, checked: bool) -> None:
        """Toggle score view visibility."""
        if hasattr(self, "_score_widget"):
            self._score_widget.setVisible(checked)
            if checked:
                self._score_widget.set_notes(
                    self._sequence.notes,
                    tempo_bpm=self._sequence.tempo_bpm,
                    time_signature=self._sequence.time_signature,
                )
            else:
                self._score_widget.clear()

    def _on_note_deleted(self, index: int) -> None:
        if index == -1:
            # Delete entire selection (triggered by marquee-selected Delete)
            note_sel = getattr(self, "_current_note_selection", [])
            rest_sel = getattr(self, "_current_rest_selection", [])
            global_notes = [self._map_to_global_note_index(i) for i in note_sel]
            global_rests = [self._map_to_global_rest_index(i) for i in rest_sel]
            global_notes = [gi for gi in global_notes if gi >= 0]
            global_rests = [gi for gi in global_rests if gi >= 0]
            if global_notes or global_rests:
                self._sequence.delete_items(global_notes, global_rests)
        else:
            global_idx = self._map_to_global_note_index(index)
            if global_idx >= 0:
                self._sequence.delete_note(global_idx)
        self._update_ui_state()

    def _on_cursor_moved(self, t: float) -> None:
        self._sequence.cursor_beats = t
        self._note_roll.set_cursor_beats(t)

    # ── Copy / Paste / Duplicate ─────────────────────────────

    def _copy_selection(self) -> None:
        note_sel = getattr(self, "_current_note_selection", [])
        rest_sel = getattr(self, "_current_rest_selection", [])
        global_notes = [self._map_to_global_note_index(i) for i in note_sel]
        global_rests = [self._map_to_global_rest_index(i) for i in rest_sel]
        global_notes = [gi for gi in global_notes if gi >= 0]
        global_rests = [gi for gi in global_rests if gi >= 0]
        if global_notes or global_rests:
            self._sequence.copy_items(global_notes, global_rests)

    def _cut_selection(self) -> None:
        self._copy_selection()
        self._delete_selection()

    def _paste(self) -> None:
        self._sequence.paste_at_cursor()
        self._update_ui_state()

    def _duplicate_selection(self) -> None:
        """Duplicate selected notes at cursor position."""
        self._copy_selection()
        self._paste()

    def _delete_selection(self) -> None:
        note_sel = getattr(self, "_current_note_selection", [])
        rest_sel = getattr(self, "_current_rest_selection", [])
        global_notes = [self._map_to_global_note_index(i) for i in note_sel]
        global_rests = [self._map_to_global_rest_index(i) for i in rest_sel]
        global_notes = [gi for gi in global_notes if gi >= 0]
        global_rests = [gi for gi in global_rests if gi >= 0]
        if global_notes or global_rests:
            self._sequence.delete_items(global_notes, global_rests)
            self._update_ui_state()

    def _move_selection(self, time_delta: float = 0.0, pitch_delta: int = 0) -> None:
        """Move selected notes by delta."""
        note_sel = getattr(self, "_current_note_selection", [])
        if not note_sel:
            return
        global_indices = [self._map_to_global_note_index(i) for i in note_sel]
        global_indices = [gi for gi in global_indices if gi >= 0]
        if global_indices:
            self._sequence.move_notes(global_indices, time_delta, pitch_delta)
            self._update_ui_state()

    def _resize_selection(self, delta_beats: float) -> None:
        """Resize selected notes."""
        note_sel = getattr(self, "_current_note_selection", [])
        if not note_sel:
            return
        global_indices = [self._map_to_global_note_index(i) for i in note_sel]
        global_indices = [gi for gi in global_indices if gi >= 0]
        if global_indices:
            self._sequence.resize_notes(global_indices, delta_beats)
            self._update_ui_state()

    def _move_cursor(self, delta_beats: float) -> None:
        """Move cursor by delta, clear selection."""
        self._selection_anchor = None
        new_pos = max(0.0, self._sequence.cursor_beats + delta_beats)
        self._sequence.cursor_beats = new_pos
        self._note_roll.clear_selection()
        self._note_roll.set_cursor_beats(new_pos)

    # ── Keyboard shortcuts ──────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent | None) -> None:  # noqa: N802
        if event is None:
            return
        key = event.key()
        text = event.text()
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        # Keyboard shortcuts toggle — Ctrl combos always active for safety
        shortcuts_on = self._shortcuts_cb.isChecked()

        # Duration keys: 1-5
        if shortcuts_on and not ctrl and text in DURATION_KEYS:
            label = DURATION_KEYS[text]
            self._sequence.set_step_duration(label)
            self._duration_combo.setCurrentText(label)
            return

        # Rest key: 0
        if shortcuts_on and not ctrl and text == "0":
            flash_beat = self._sequence.cursor_beats
            self._sequence.add_rest()
            self._update_ui_state()
            self._note_roll.flash_at_beat(flash_beat)
            return

        # Pencil mode toggle: P
        if shortcuts_on and not ctrl and text.lower() == "p":
            self._pencil_btn.toggle()
            return

        # Ctrl shortcuts
        if ctrl:
            if key == Qt.Key.Key_Z:
                self._on_undo()
                return
            if key == Qt.Key.Key_Y:
                self._on_redo()
                return
            if key == Qt.Key.Key_A:
                self._note_roll.select_all()
                return
            if key == Qt.Key.Key_C:
                self._copy_selection()
                return
            if key == Qt.Key.Key_X:
                self._cut_selection()
                return
            if key == Qt.Key.Key_V:
                self._paste()
                return
            if key == Qt.Key.Key_D:
                self._duplicate_selection()
                return
            if key == Qt.Key.Key_Q:
                self._quantize_selection()
                return
            if key == Qt.Key.Key_S:
                if shift:
                    self._on_save_as()
                else:
                    self._on_save()
                return
            if key == Qt.Key.Key_E:
                self._on_export()
                return

        # Arrow keys — cursor navigation / note editing
        alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        step = self._sequence.step_duration

        if not shortcuts_on:
            # Only Ctrl combos were handled above; skip all other shortcuts
            super().keyPressEvent(event)
            return

        if alt and shift:
            # Alt+Shift+arrows: resize selected notes
            if key == Qt.Key.Key_Right:
                self._resize_selection(step)
                return
            if key == Qt.Key.Key_Left:
                self._resize_selection(-step)
                return
        elif alt:
            # Alt+arrows: move selected notes
            if key == Qt.Key.Key_Right:
                self._move_selection(time_delta=step)
                return
            if key == Qt.Key.Key_Left:
                self._move_selection(time_delta=-step)
                return
            if key == Qt.Key.Key_Up:
                self._move_selection(pitch_delta=1)
                return
            if key == Qt.Key.Key_Down:
                self._move_selection(pitch_delta=-1)
                return
        elif shift:
            # Shift+arrows: range selection
            if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                if self._selection_anchor is None:
                    self._selection_anchor = self._sequence.cursor_beats
                delta = step if key == Qt.Key.Key_Right else -step
                new_pos = max(0.0, self._sequence.cursor_beats + delta)
                self._sequence.cursor_beats = new_pos
                self._note_roll.set_cursor_beats(new_pos)
                t0 = min(self._selection_anchor, new_pos)
                t1 = max(self._selection_anchor, new_pos)
                self._note_roll.select_notes_in_time_range(t0, t1)
                return
        else:
            # Plain arrows: move cursor
            if key == Qt.Key.Key_Left:
                self._move_cursor(-step)
                return
            if key == Qt.Key.Key_Right:
                self._move_cursor(step)
                return

        # Delete key
        if key == Qt.Key.Key_Delete:
            self._delete_selection()
            return

        # Space → play
        if key == Qt.Key.Key_Space:
            self._on_play()
            return

        # L → toggle loop
        if key == Qt.Key.Key_L:
            self._loop_btn.setChecked(not self._loop_btn.isChecked())
            return

        # M → toggle metronome
        if key == Qt.Key.Key_M:
            self._metronome_btn.setChecked(not self._metronome_btn.isChecked())
            return

        super().keyPressEvent(event)
