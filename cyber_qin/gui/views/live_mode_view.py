"""Live MIDI input view — with gradient header and card containers — 賽博墨韻."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QRectF, QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.constants import (
    RECONNECT_INTERVAL,
    TRANSPOSE_MAX,
    TRANSPOSE_MIN,
    TRANSPOSE_STEP,
)
from ...core.key_mapper import KeyMapper
from ...core.key_simulator import KeySimulator
from ...core.mapping_schemes import get_scheme, list_schemes
from ...core.midi_listener import MidiListener
from ...utils.admin import is_admin
from ..theme import BG_PAPER, DIVIDER, TEXT_SECONDARY
from ..widgets.log_viewer import LogViewer
from ..widgets.piano_display import PianoDisplay
from ..widgets.status_bar import StatusBar

log = logging.getLogger(__name__)


class _GradientHeader(QWidget):
    """Gradient header with 暗青 accent fade."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(100)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(0, 240, 255, 40))   # 賽博青半透明
        gradient.setColorAt(1, QColor(10, 14, 20, 0))      # 透明
        painter.fillRect(QRectF(0, 0, self.width(), self.height()), gradient)
        painter.end()


class _CardContainer(QFrame):
    """Rounded card container for grouping controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"_CardContainer {{"
            f"  background-color: {BG_PAPER};"
            f"  border-radius: 12px;"
            f"  border: 1px solid {DIVIDER};"
            f"}}"
        )


class LiveModeView(QWidget):
    """Live MIDI input mode — connect a MIDI device and play in real-time."""

    scheme_changed = pyqtSignal(str)  # scheme_id
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(str)  # file_path

    def __init__(
        self,
        mapper: KeyMapper,
        simulator: KeySimulator,
        listener: MidiListener,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mapper = mapper
        self._simulator = simulator
        self._listener = listener
        self._settings = QSettings("CyberQin", "CyberQin")
        self._reconnect_port: str | None = None

        self._build_ui()
        self._setup_timers()
        self._restore_settings()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Gradient header
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        self._gradient_header = _GradientHeader()
        header_layout.addWidget(self._gradient_header)

        # Overlay text on top of gradient
        header_overlay = QWidget(self._gradient_header)
        overlay_layout = QVBoxLayout(header_overlay)
        overlay_layout.setContentsMargins(24, 20, 24, 8)

        header = QLabel("演奏模式")
        header.setFont(QFont("Microsoft JhengHei", 22, QFont.Weight.Bold))
        header.setStyleSheet("background: transparent;")
        overlay_layout.addWidget(header)

        desc = QLabel("連接 MIDI 裝置，即時演奏映射到遊戲按鍵")
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        overlay_layout.addWidget(desc)
        overlay_layout.addStretch()

        header_overlay.setGeometry(0, 0, 800, 100)
        root.addWidget(header_container)

        # Content area
        content = QVBoxLayout()
        content.setContentsMargins(24, 8, 24, 12)
        content.setSpacing(16)

        # Device selection card
        device_card = _CardContainer()
        device_card_layout = QVBoxLayout(device_card)
        device_card_layout.setContentsMargins(16, 12, 16, 12)
        device_card_layout.setSpacing(8)

        # Row 1: MIDI device + transpose
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        lbl = QLabel("MIDI 裝置:")
        lbl.setStyleSheet("background: transparent;")
        row1.addWidget(lbl)

        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(250)
        row1.addWidget(self._port_combo)

        self._refresh_btn = QPushButton("重新整理")
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.clicked.connect(self._refresh_ports)
        row1.addWidget(self._refresh_btn)

        self._connect_btn = QPushButton("連線")
        self._connect_btn.setProperty("class", "accent")
        self._connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._connect_btn.clicked.connect(self._toggle_connection)
        row1.addWidget(self._connect_btn)

        row1.addStretch()

        transpose_lbl = QLabel("移調:")
        transpose_lbl.setStyleSheet("background: transparent;")
        row1.addWidget(transpose_lbl)
        self._transpose_spin = QSpinBox()
        self._transpose_spin.setRange(
            TRANSPOSE_MIN // TRANSPOSE_STEP,
            TRANSPOSE_MAX // TRANSPOSE_STEP,
        )
        self._transpose_spin.setValue(0)
        self._transpose_spin.setSuffix(" 八度")
        self._transpose_spin.valueChanged.connect(self._on_transpose_changed)
        row1.addWidget(self._transpose_spin)

        device_card_layout.addLayout(row1)

        # Row 2: Mapping scheme selector
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        scheme_lbl = QLabel("映射方案:")
        scheme_lbl.setStyleSheet("background: transparent;")
        row2.addWidget(scheme_lbl)

        self._scheme_combo = QComboBox()
        self._scheme_combo.setMinimumWidth(250)
        for scheme in list_schemes():
            self._scheme_combo.addItem(scheme.name, scheme.id)
        self._scheme_combo.currentIndexChanged.connect(self._on_scheme_combo_changed)
        row2.addWidget(self._scheme_combo)

        row2.addStretch()

        self._scheme_desc = QLabel("")
        self._scheme_desc.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background: transparent; font-size: 12px;"
        )
        row2.addWidget(self._scheme_desc)

        device_card_layout.addLayout(row2)

        # Row 3: Recording controls
        row3 = QHBoxLayout()
        row3.setSpacing(8)

        self._record_btn = QPushButton("錄音")
        self._record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._record_btn.setStyleSheet(
            "QPushButton { background-color: #3a1a1a; color: #ff4444; "
            "border: 1px solid #ff4444; border-radius: 16px; padding: 8px 20px; "
            "font-weight: 600; }"
            "QPushButton:hover { background-color: #4a2020; }"
        )
        self._record_btn.clicked.connect(self._toggle_recording)
        row3.addWidget(self._record_btn)

        self._auto_tune_check = QCheckBox("自動校正")
        self._auto_tune_check.setStyleSheet("background: transparent;")
        self._auto_tune_check.setToolTip("錄音結束後自動量化節奏與修正音高")
        row3.addWidget(self._auto_tune_check)

        row3.addStretch()

        self._recording_status = QLabel("")
        self._recording_status.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background: transparent; font-size: 12px;"
        )
        row3.addWidget(self._recording_status)

        device_card_layout.addLayout(row3)

        content.addWidget(device_card)

        # Piano display
        self._piano = PianoDisplay(mapper=self._mapper)
        content.addWidget(self._piano, 1)

        # Log viewer with title
        log_section = QVBoxLayout()
        log_section.setSpacing(4)

        log_title = QLabel("Event Log")
        log_title.setFont(QFont("Microsoft JhengHei", 11, QFont.Weight.DemiBold))
        log_title.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        log_section.addWidget(log_title)

        self._log = LogViewer()
        self._log.setMaximumHeight(140)
        log_section.addWidget(self._log)

        content.addLayout(log_section)

        # Status bar
        self._status = StatusBar()
        content.addWidget(self._status)
        self._status.set_admin_warning(is_admin())

        root.addLayout(content, 1)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, '_gradient_header'):
            for child in self._gradient_header.children():
                if isinstance(child, QWidget):
                    child.setGeometry(0, 0, self.width(), 100)

    def _setup_timers(self) -> None:
        self._watchdog = QTimer(self)
        self._watchdog.timeout.connect(self._check_stuck_keys)
        self._watchdog.start(2000)

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.timeout.connect(self._try_reconnect)

    def _restore_settings(self) -> None:
        transpose = self._settings.value("transpose", 0, type=int)
        self._transpose_spin.setValue(transpose)
        self._mapper.transpose = transpose * TRANSPOSE_STEP

        # Restore scheme selection
        saved_scheme = self._settings.value("scheme_id", "", type=str)
        if saved_scheme:
            for i in range(self._scheme_combo.count()):
                if self._scheme_combo.itemData(i) == saved_scheme:
                    self._scheme_combo.setCurrentIndex(i)
                    break

        # Update description for initial selection
        self._update_scheme_description()

        last_port = self._settings.value("last_port", "", type=str)
        self._refresh_ports()
        if last_port:
            idx = self._port_combo.findText(last_port)
            if idx >= 0:
                self._port_combo.setCurrentIndex(idx)

    @property
    def piano(self) -> PianoDisplay:
        return self._piano

    @property
    def log_viewer(self) -> LogViewer:
        return self._log

    # --- Scheme management ---

    def _on_scheme_combo_changed(self, index: int) -> None:
        scheme_id = self._scheme_combo.itemData(index)
        if scheme_id is None:
            return
        self._apply_scheme(scheme_id)

    def _apply_scheme(self, scheme_id: str) -> None:
        try:
            scheme = get_scheme(scheme_id)
        except KeyError:
            return
        self._mapper.set_scheme(scheme)
        self._piano.on_scheme_changed()
        self._settings.setValue("scheme_id", scheme_id)
        self._update_scheme_description()
        self.scheme_changed.emit(scheme_id)
        self._log.log(f"映射方案: {scheme.name} ({scheme.key_count} 鍵)")

    def _update_scheme_description(self) -> None:
        scheme_id = self._scheme_combo.currentData()
        if scheme_id:
            try:
                scheme = get_scheme(scheme_id)
                self._scheme_desc.setText(scheme.description)
            except KeyError:
                self._scheme_desc.setText("")
        else:
            self._scheme_desc.setText("")

    # --- MIDI connection management ---

    def set_midi_callback(self, callback) -> None:
        """Set the callback for MIDI events (from MidiProcessor)."""
        self._midi_callback = callback

    def _refresh_ports(self) -> None:
        self._port_combo.clear()
        ports = MidiListener.list_ports()
        if ports:
            self._port_combo.addItems(ports)
        else:
            self._port_combo.addItem("(未偵測到裝置)")
        self._log.log(f"偵測到 {len(ports)} 個 MIDI 裝置")

    def _toggle_connection(self) -> None:
        if self._listener.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self) -> None:
        port_name = self._port_combo.currentText()
        if not port_name or port_name.startswith("("):
            return
        try:
            callback = getattr(self, "_midi_callback", None)
            self._listener.open(
                port_name,
                callback=callback,
                on_disconnect=self._on_disconnect,
            )
            self._connect_btn.setText("斷線")
            self._status.set_connected(port_name)
            self._settings.setValue("last_port", port_name)
            self._reconnect_port = port_name
            self._reconnect_timer.stop()
            self._log.log(f"已連線: {port_name}")
        except Exception as e:
            self._log.log(f"連線失敗: {e}")
            log.exception("Failed to connect to %s", port_name)

    def _disconnect(self) -> None:
        self._simulator.release_all()
        self._listener.close()
        self._connect_btn.setText("連線")
        self._status.set_disconnected()
        self._reconnect_timer.stop()
        self._reconnect_port = None
        self._piano.set_active_notes(set())
        self._log.log("已斷線")

    def _on_disconnect(self) -> None:
        self._simulator.release_all()
        self._piano.set_active_notes(set())
        self._status.set_reconnecting()
        self._connect_btn.setText("連線")
        self._log.log("MIDI 裝置斷線，嘗試重新連線...")
        self._reconnect_timer.start(int(RECONNECT_INTERVAL * 1000))

    def _try_reconnect(self) -> None:
        if self._reconnect_port is None:
            self._reconnect_timer.stop()
            return
        ports = MidiListener.list_ports()
        if self._reconnect_port in ports:
            self._log.log(f"偵測到裝置，重新連線: {self._reconnect_port}")
            self._port_combo.clear()
            self._port_combo.addItems(ports)
            idx = self._port_combo.findText(self._reconnect_port)
            if idx >= 0:
                self._port_combo.setCurrentIndex(idx)
            self._connect()

    def _on_transpose_changed(self, value: int) -> None:
        self._mapper.transpose = value * TRANSPOSE_STEP
        self._settings.setValue("transpose", value)
        self._log.log(f"移調: {value:+d} 八度 (MIDI offset {value * TRANSPOSE_STEP:+d})")

    # --- Event handlers called from AppShell ---

    def on_note_event(self, event_type: str, note: int, velocity: int) -> None:
        name = KeyMapper.note_name(note)
        mapping = self._mapper.lookup(note)
        key_label = mapping.label if mapping else "(超出範圍)"

        if event_type == "note_on":
            self._piano.note_on(note)
            self._log.log(f"  {name} (MIDI {note}, vel={velocity})  ->  {key_label}")
        else:
            self._piano.note_off(note)

    def on_latency(self, ms: float) -> None:
        self._status.set_latency(ms)

    def _check_stuck_keys(self) -> None:
        stuck = self._simulator.check_stuck_keys()
        for note in stuck:
            name = KeyMapper.note_name(note)
            self._log.log(f"  Stuck key released: {name} (MIDI {note})")
            self._piano.note_off(note)

    @property
    def auto_tune_enabled(self) -> bool:
        return self._auto_tune_check.isChecked()

    def _toggle_recording(self) -> None:
        """Toggle recording state — delegates actual logic to AppShell."""
        if self._record_btn.text() == "錄音":
            self._record_btn.setText("停止錄音")
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #ff4444; color: #0A0E14; "
                "border: none; border-radius: 16px; padding: 8px 20px; "
                "font-weight: 700; }"
                "QPushButton:hover { background-color: #ff6666; }"
            )
            self._recording_status.setText("錄音中...")
            self.recording_started.emit()
        else:
            self._record_btn.setText("錄音")
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #3a1a1a; color: #ff4444; "
                "border: 1px solid #ff4444; border-radius: 16px; padding: 8px 20px; "
                "font-weight: 600; }"
                "QPushButton:hover { background-color: #4a2020; }"
            )
            self._recording_status.setText("")
            self.recording_stopped.emit("")

    def on_recording_saved(self, file_path: str) -> None:
        """Called after recording is saved successfully."""
        from pathlib import Path
        name = Path(file_path).stem
        self._log.log(f"  錄音已儲存: {name}")

    def cleanup(self) -> None:
        self._simulator.release_all()
        self._listener.close()
