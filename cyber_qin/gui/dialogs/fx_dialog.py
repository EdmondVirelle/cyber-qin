"""MIDI FX dialog — 4-tab dialog for Arpeggiator, Humanize, Quantize, Chord Generator."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.beat_sequence import BeatNote
from ...core.midi_fx import (
    CHORD_INTERVALS,
    ArpeggiatorConfig,
    ChordGenConfig,
    HumanizeConfig,
    QuantizeConfig,
    arpeggiate,
    generate_chords,
    humanize,
    quantize,
)
from ...core.translator import translator


class FxDialog(QDialog):
    """4-tab MIDI FX dialog."""

    def __init__(
        self,
        notes: list[BeatNote],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._input_notes = notes
        self._result_notes: list[BeatNote] | None = None
        self.setWindowTitle(translator.tr("editor.fx"))
        self.setMinimumSize(420, 350)
        self._build_ui()

    @property
    def result_notes(self) -> list[BeatNote] | None:
        return self._result_notes

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()

        # Tab 1: Arpeggiator
        self._arp_tab = QWidget()
        arp_layout = QVBoxLayout(self._arp_tab)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.arp.pattern")))
        self._arp_pattern = QComboBox()
        self._arp_pattern.addItems(["up", "down", "up_down", "random"])
        row.addWidget(self._arp_pattern)
        arp_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.arp.rate")))
        self._arp_rate = QDoubleSpinBox()
        self._arp_rate.setRange(0.0625, 2.0)
        self._arp_rate.setValue(0.25)
        self._arp_rate.setSingleStep(0.0625)
        row.addWidget(self._arp_rate)
        arp_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.arp.octave")))
        self._arp_octave = QSpinBox()
        self._arp_octave.setRange(0, 3)
        self._arp_octave.setValue(0)
        row.addWidget(self._arp_octave)
        arp_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.arp.gate")))
        self._arp_gate = QDoubleSpinBox()
        self._arp_gate.setRange(0.1, 1.0)
        self._arp_gate.setValue(0.9)
        self._arp_gate.setSingleStep(0.1)
        row.addWidget(self._arp_gate)
        arp_layout.addLayout(row)

        arp_layout.addStretch()
        self._tabs.addTab(self._arp_tab, translator.tr("fx.tab.arp"))

        # Tab 2: Humanize
        self._humanize_tab = QWidget()
        hum_layout = QVBoxLayout(self._humanize_tab)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.hum.timing")))
        self._hum_timing = QDoubleSpinBox()
        self._hum_timing.setRange(0.0, 0.2)
        self._hum_timing.setValue(0.03)
        self._hum_timing.setSingleStep(0.01)
        row.addWidget(self._hum_timing)
        hum_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.hum.velocity")))
        self._hum_velocity = QSpinBox()
        self._hum_velocity.setRange(0, 40)
        self._hum_velocity.setValue(10)
        row.addWidget(self._hum_velocity)
        hum_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.hum.duration")))
        self._hum_duration = QDoubleSpinBox()
        self._hum_duration.setRange(0.0, 0.1)
        self._hum_duration.setValue(0.0)
        self._hum_duration.setSingleStep(0.01)
        row.addWidget(self._hum_duration)
        hum_layout.addLayout(row)

        hum_layout.addStretch()
        self._tabs.addTab(self._humanize_tab, translator.tr("fx.tab.humanize"))

        # Tab 3: Quantize
        self._quantize_tab = QWidget()
        q_layout = QVBoxLayout(self._quantize_tab)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.q.grid")))
        self._q_grid = QComboBox()
        self._q_grid.addItem("1/4 (1.0)", 1.0)
        self._q_grid.addItem("1/8 (0.5)", 0.5)
        self._q_grid.addItem("1/16 (0.25)", 0.25)
        self._q_grid.addItem("1/32 (0.125)", 0.125)
        self._q_grid.setCurrentIndex(1)
        row.addWidget(self._q_grid)
        q_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.q.strength")))
        self._q_strength = QSlider(Qt.Orientation.Horizontal)
        self._q_strength.setRange(0, 100)
        self._q_strength.setValue(100)
        row.addWidget(self._q_strength)
        self._q_strength_lbl = QLabel("100%")
        self._q_strength.valueChanged.connect(lambda v: self._q_strength_lbl.setText(f"{v}%"))
        row.addWidget(self._q_strength_lbl)
        q_layout.addLayout(row)

        q_layout.addStretch()
        self._tabs.addTab(self._quantize_tab, translator.tr("fx.tab.quantize"))

        # Tab 4: Chord Generator
        self._chord_tab = QWidget()
        c_layout = QVBoxLayout(self._chord_tab)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.chord.type")))
        self._chord_type = QComboBox()
        self._chord_type.addItems(list(CHORD_INTERVALS.keys()))
        row.addWidget(self._chord_type)
        c_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.chord.voicing")))
        self._chord_voicing = QComboBox()
        self._chord_voicing.addItems(["close", "spread", "drop2"])
        row.addWidget(self._chord_voicing)
        c_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(translator.tr("fx.chord.vel_scale")))
        self._chord_vel = QDoubleSpinBox()
        self._chord_vel.setRange(0.1, 1.0)
        self._chord_vel.setValue(0.85)
        self._chord_vel.setSingleStep(0.05)
        row.addWidget(self._chord_vel)
        c_layout.addLayout(row)

        c_layout.addStretch()
        self._tabs.addTab(self._chord_tab, translator.tr("fx.tab.chords"))

        layout.addWidget(self._tabs)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        apply_btn = QPushButton(translator.tr("fx.apply"))
        apply_btn.setMinimumWidth(100)
        apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(apply_btn)

        cancel_btn = QPushButton(translator.tr("fx.cancel"))
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

    def _on_apply(self) -> None:
        tab = self._tabs.currentIndex()

        if tab == 0:  # Arpeggiator
            arp_config = ArpeggiatorConfig(
                pattern=self._arp_pattern.currentText(),
                rate=self._arp_rate.value(),
                octave_range=self._arp_octave.value(),
                gate=self._arp_gate.value(),
            )
            self._result_notes = arpeggiate(self._input_notes, arp_config)

        elif tab == 1:  # Humanize
            hum_config = HumanizeConfig(
                timing_jitter_beats=self._hum_timing.value(),
                velocity_jitter=self._hum_velocity.value(),
                duration_jitter_beats=self._hum_duration.value(),
            )
            self._result_notes = humanize(self._input_notes, hum_config)

        elif tab == 2:  # Quantize
            grid = self._q_grid.currentData()
            strength = self._q_strength.value() / 100.0
            q_config = QuantizeConfig(grid=grid, strength=strength)
            self._result_notes = quantize(self._input_notes, q_config)

        elif tab == 3:  # Chords
            chord_config = ChordGenConfig(
                chord_type=self._chord_type.currentText(),
                voicing=self._chord_voicing.currentText(),
                velocity_scale=self._chord_vel.value(),
            )
            self._result_notes = generate_chords(self._input_notes, chord_config)

        self.accept()
