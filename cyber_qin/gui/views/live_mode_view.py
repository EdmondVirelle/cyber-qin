"""Live MIDI input view — with gradient header and card containers — 賽博墨韻."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
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

from ...core.config import get_config
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
from ...core.translator import translator
from ...utils.admin import is_admin
from ..dialogs import KeyMappingViewer
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
        gradient.setColorAt(0, QColor(0, 240, 255, 40))  # 賽博青半透明
        gradient.setColorAt(1, QColor(10, 14, 20, 0))  # 透明
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
        self._config = get_config()
        self._reconnect_port: str | None = None
        self._is_recording: bool = False

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
        content.setSpacing(16)

        # Device selection card
        device_card = _CardContainer()
        device_card_layout = QVBoxLayout(device_card)
        device_card_layout.setContentsMargins(16, 12, 16, 12)
        device_card_layout.setSpacing(8)

        # Row 1: MIDI device + transpose
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self._midi_dev_lbl = QLabel()
        self._midi_dev_lbl.setStyleSheet("background: transparent;")
        row1.addWidget(self._midi_dev_lbl)

        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(250)
        row1.addWidget(self._port_combo)

        self._refresh_btn = QPushButton()
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.clicked.connect(self._refresh_ports)
        row1.addWidget(self._refresh_btn)

        self._connect_btn = QPushButton()
        self._connect_btn.setProperty("class", "accent")
        self._connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._connect_btn.clicked.connect(self._toggle_connection)
        row1.addWidget(self._connect_btn)

        row1.addStretch()

        self._transpose_lbl = QLabel()
        self._transpose_lbl.setStyleSheet("background: transparent;")
        row1.addWidget(self._transpose_lbl)
        self._transpose_spin = QSpinBox()
        self._transpose_spin.setRange(
            TRANSPOSE_MIN // TRANSPOSE_STEP,
            TRANSPOSE_MAX // TRANSPOSE_STEP,
        )
        self._transpose_spin.setValue(0)
        self._transpose_spin.setSuffix(translator.tr("live.transpose.suffix"))
        self._transpose_spin.valueChanged.connect(self._on_transpose_changed)
        row1.addWidget(self._transpose_spin)

        device_card_layout.addLayout(row1)

        # Row 2: Mapping scheme selector
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self._scheme_lbl = QLabel()
        self._scheme_lbl.setStyleSheet("background: transparent;")
        row2.addWidget(self._scheme_lbl)

        self._scheme_combo = QComboBox()
        self._scheme_combo.setMinimumWidth(250)
        for scheme in list_schemes():
            self._scheme_combo.addItem(scheme.translated_name(), scheme.id)
        self._scheme_combo.currentIndexChanged.connect(self._on_scheme_combo_changed)
        row2.addWidget(self._scheme_combo)

        self._view_mapping_btn = QPushButton()
        self._view_mapping_btn.setFixedHeight(28)
        self._view_mapping_btn.setMinimumWidth(100)
        self._view_mapping_btn.clicked.connect(self._on_view_mapping)
        row2.addWidget(self._view_mapping_btn)

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

        self._record_btn = QPushButton()
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

        self._log_title_lbl = QLabel()
        self._log_title_lbl.setFont(QFont("Microsoft JhengHei", 11, QFont.Weight.DemiBold))
        self._log_title_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        log_section.addWidget(self._log_title_lbl)

        self._log = LogViewer()
        self._log.setMaximumHeight(140)
        log_section.addWidget(self._log)

        content.addLayout(log_section)

        # Status bar
        self._status = StatusBar()
        content.addWidget(self._status)
        self._status.set_admin_warning(is_admin())

        root.addLayout(content, 1)

        translator.language_changed.connect(self._update_text)
        self._update_text()

    def _update_text(self) -> None:
        """Update UI text based on current language."""
        self._header_lbl.setText(translator.tr("live.title"))
        self._desc_lbl.setText(translator.tr("live.desc"))
        self._midi_dev_lbl.setText(translator.tr("live.midi_device") + ":")
        self._refresh_btn.setText(translator.tr("live.refresh"))
        # Only update connect btn text if we are not relying on state (handle in separate logic if needed, but here simple is fine for now)
        # Actually _toggle_connection updates text based on state.
        # We should update it here respecting current state if possible, or just update the "Connect" / "Disconnect" strings.
        # But _connect_btn text is stateful. Let's handle it carefully.
        if self._listener.connected:
            self._connect_btn.setText(translator.tr("live.disconnect"))
        else:
            self._connect_btn.setText(translator.tr("live.connect"))

        self._transpose_lbl.setText(translator.tr("live.transpose") + ":")
        self._scheme_lbl.setText(translator.tr("live.mapping") + ":")
        self._view_mapping_btn.setText(translator.tr("live.view_mapping"))

        # Record button stateful
        if self._record_btn.text() == "錄音" or self._record_btn.text() == translator.tr(
            "live.record", language="en"
        ):  # Check generic
            # Just relying on internal flags might be safer if we had them easily accessible here except button text
            pass
        # Better: use self._record_btn.property or just re-eval based on recording signal?
        # LiveModeView doesn't track recording state in a simple boolean accessible here easily?
        # Ah, self._toggle_recording toggles text.
        # Let's just reset generic text if not recording?
        # The button text toggle logic in `_toggle_recording` uses hardcoded strings. We need to update that too.

        # update dynamic labels
        self._auto_tune_check.setText(translator.tr("live.auto_tune"))
        self._log_title_lbl.setText(translator.tr("live.log"))
        self._transpose_spin.setSuffix(translator.tr("live.transpose.suffix"))

        # Re-populate scheme combo with translated names
        current_data = self._scheme_combo.currentData()
        self._scheme_combo.blockSignals(True)
        self._scheme_combo.clear()
        for scheme in list_schemes():
            self._scheme_combo.addItem(scheme.translated_name(), scheme.id)
        if current_data:
            for i in range(self._scheme_combo.count()):
                if self._scheme_combo.itemData(i) == current_data:
                    self._scheme_combo.setCurrentIndex(i)
                    break
        self._scheme_combo.blockSignals(False)
        self._update_scheme_description()

        # Trigger explicit update for stateful buttons
        self._update_stateful_text()

    def _update_stateful_text(self) -> None:
        """Update buttons that change text based on state."""
        if self._listener.connected:
            self._connect_btn.setText(translator.tr("live.disconnect"))
        else:
            self._connect_btn.setText(translator.tr("live.connect"))

        if self._is_recording:
            self._record_btn.setText(translator.tr("live.stop_record"))
            self._recording_status.setText(translator.tr("live.recording"))
        else:
            self._record_btn.setText(translator.tr("live.record"))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_gradient_header"):
            for child in self._gradient_header.children():
                if isinstance(child, QWidget):
                    child.setGeometry(0, 0, self.width(), 100)

    def _setup_timers(self) -> None:
        self._watchdog = QTimer(self)
        self._watchdog.timeout.connect(self._check_stuck_keys)
        self._watchdog.start(2000)

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.timeout.connect(self._try_reconnect)

        # Periodic device list refresh (every 5 seconds when disconnected)
        self._device_refresh_timer = QTimer(self)
        self._device_refresh_timer.timeout.connect(self._auto_refresh_devices)
        self._device_refresh_timer.start(5000)

    def _restore_settings(self) -> None:
        transpose = self._config.get("playback.transpose", 0)
        self._transpose_spin.setValue(transpose)
        self._mapper.transpose = transpose * TRANSPOSE_STEP

        # Restore scheme selection
        saved_scheme = self._config.get("playback.scheme_id", "")
        if saved_scheme:
            for i in range(self._scheme_combo.count()):
                if self._scheme_combo.itemData(i) == saved_scheme:
                    self._scheme_combo.setCurrentIndex(i)
                    break

        # Update description for initial selection
        self._update_scheme_description()

        # Try preferred device first, then fall back to last port
        preferred_device = self._config.get("midi.preferred_device", "")
        last_port = self._config.get("midi.last_port", "")
        self._refresh_ports()

        # Priority: preferred_device > last_port
        port_to_select = preferred_device or last_port
        if port_to_select:
            idx = self._port_combo.findText(port_to_select)
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
        self._config.set("playback.scheme_id", scheme_id)
        self._update_scheme_description()
        self.scheme_changed.emit(scheme_id)
        self._log.log(f"映射方案: {scheme.name} ({scheme.key_count} 鍵)")

    def _update_scheme_description(self) -> None:
        scheme_id = self._scheme_combo.currentData()
        if scheme_id:
            try:
                scheme = get_scheme(scheme_id)
                self._scheme_desc.setText(scheme.translated_desc())
            except KeyError:
                self._scheme_desc.setText("")
        else:
            self._scheme_desc.setText("")

    def _on_view_mapping(self) -> None:
        """Open the key mapping viewer dialog."""
        scheme_id = self._scheme_combo.currentData()
        if scheme_id:
            try:
                scheme = get_scheme(scheme_id)
                dialog = KeyMappingViewer(scheme, self)
                dialog.exec()
            except KeyError:
                log.warning("Failed to load scheme %s for mapping viewer", scheme_id)

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

    def _auto_refresh_devices(self) -> None:
        """Automatically refresh device list when disconnected (hot-plug support)."""
        if not self._listener.connected and not self._reconnect_timer.isActive():
            # Only refresh if disconnected and not currently trying to reconnect
            current_text = self._port_combo.currentText()
            ports = MidiListener.list_ports()

            # Only update if the device list changed
            current_ports = [
                self._port_combo.itemText(i)
                for i in range(self._port_combo.count())
                if not self._port_combo.itemText(i).startswith("(")
            ]

            if set(ports) != set(current_ports):
                # Detect newly added devices
                new_devices = set(ports) - set(current_ports)
                removed_devices = set(current_ports) - set(ports)

                self._port_combo.clear()
                if ports:
                    self._port_combo.addItems(ports)
                    # Try to restore previous selection
                    idx = self._port_combo.findText(current_text)
                    if idx >= 0:
                        self._port_combo.setCurrentIndex(idx)
                else:
                    self._port_combo.addItem("(未偵測到裝置)")

                # Log device changes
                if new_devices:
                    for device in new_devices:
                        self._log.log(f"偵測到新裝置: {device}")
                if removed_devices:
                    for device in removed_devices:
                        self._log.log(f"裝置已移除: {device}")

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
            callback = getattr(self, "_midi_callback", lambda n, s, v: None)
            self._listener.open(
                port_name,
                callback=callback,
                on_disconnect=self._on_disconnect,
            )
            self._update_stateful_text()
            self._status.set_connected(port_name)
            self._config.set("midi.last_port", port_name)
            self._reconnect_port = port_name
            self._reconnect_timer.stop()
            self._log.log(f"已連線: {port_name}")
        except OSError as e:
            # Specific OS errors (permission denied, device not found, etc.)
            error_msg = str(e).lower()
            if "permission" in error_msg or "access" in error_msg:
                self._log.log("連線失敗: 權限不足（請檢查裝置是否被其他程式佔用）")
            elif "not found" in error_msg or "no such" in error_msg:
                self._log.log(f"連線失敗: 裝置 '{port_name}' 不存在（請重新整理裝置列表）")
                self._refresh_ports()
            else:
                self._log.log(f"連線失敗: {e}")
            log.exception("Failed to connect to %s", port_name)
        except Exception as e:
            # Generic error handling
            self._log.log(f"連線失敗: {e}")
            log.exception("Failed to connect to %s", port_name)

    def _disconnect(self) -> None:
        self._simulator.release_all()
        self._listener.close()
        self._update_stateful_text()
        self._status.set_disconnected()
        self._reconnect_timer.stop()
        self._reconnect_port = None
        self._piano.set_active_notes(set())
        self._log.log("已斷線")

    def _on_disconnect(self) -> None:
        self._simulator.release_all()
        self._piano.set_active_notes(set())
        self._piano.set_active_notes(set())
        self._status.set_reconnecting()
        self._update_stateful_text()
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
        self._config.set("playback.transpose", value)
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
        if not self._is_recording:
            self._is_recording = True

            # Update style for recording state
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #ff4444; color: #0A0E14; "
                "border: none; border-radius: 16px; padding: 8px 20px; "
                "font-weight: 700; }"
                "QPushButton:hover { background-color: #ff6666; }"
            )
            self._recording_status.setText(translator.tr("live.recording"))
            self.recording_started.emit()
            self._update_stateful_text()
        else:
            self._is_recording = False

            # Update style for idle state
            self._record_btn.setStyleSheet(
                "QPushButton { background-color: #3a1a1a; color: #ff4444; "
                "border: 1px solid #ff4444; border-radius: 16px; padding: 8px 20px; "
                "font-weight: 600; }"
                "QPushButton:hover { background-color: #4a2020; }"
            )
            self._recording_status.setText("")
            self.recording_stopped.emit("")
            self._update_stateful_text()

    def on_recording_saved(self, file_path: str) -> None:
        """Called after recording is saved successfully."""
        from pathlib import Path

        name = Path(file_path).stem
        self._log.log(f"  錄音已儲存: {name}")

    def cleanup(self) -> None:
        self._simulator.release_all()
        self._listener.close()
