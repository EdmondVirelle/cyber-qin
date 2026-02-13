"""Melody generator dialog — configure and generate melodies/bass lines."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
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
from ...core.melody_generator import (
    PROGRESSIONS,
    SCALE_INTERVALS,
    BassConfig,
    MelodyConfig,
    generate_bass_line,
    generate_melody,
)
from ...core.translator import translator

# Note names for root selection
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class MelodyDialog(QDialog):
    """Two-tab dialog for melody and bass line generation."""

    def __init__(
        self,
        tempo_bpm: float = 120.0,
        time_signature: tuple[int, int] = (4, 4),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tempo_bpm = tempo_bpm
        self._time_signature = time_signature
        self._result_notes: list[BeatNote] = []
        self.setWindowTitle(translator.tr("editor.generate"))
        self.setMinimumSize(420, 400)
        self._build_ui()

    @property
    def result_notes(self) -> list[BeatNote]:
        return self._result_notes

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()

        # Tab 1: Melody
        self._melody_tab = QWidget()
        m_layout = QVBoxLayout(self._melody_tab)

        row = QHBoxLayout()
        row.addWidget(QLabel("Root Note:"))
        self._mel_root = QComboBox()
        for i, name in enumerate(_NOTE_NAMES):
            self._mel_root.addItem(f"{name}4", 60 + i)
        row.addWidget(self._mel_root)
        m_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Scale:"))
        self._mel_scale = QComboBox()
        self._mel_scale.addItems(list(SCALE_INTERVALS.keys()))
        row.addWidget(self._mel_scale)
        m_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Bars:"))
        self._mel_bars = QSpinBox()
        self._mel_bars.setRange(1, 64)
        self._mel_bars.setValue(8)
        row.addWidget(self._mel_bars)
        m_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Note Range:"))
        self._mel_min = QSpinBox()
        self._mel_min.setRange(21, 108)
        self._mel_min.setValue(60)
        row.addWidget(self._mel_min)
        row.addWidget(QLabel("to"))
        self._mel_max = QSpinBox()
        self._mel_max.setRange(21, 108)
        self._mel_max.setValue(83)
        row.addWidget(self._mel_max)
        m_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Stepwise Bias:"))
        self._mel_bias = QSlider(Qt.Orientation.Horizontal)
        self._mel_bias.setRange(0, 100)
        self._mel_bias.setValue(70)
        row.addWidget(self._mel_bias)
        self._mel_bias_lbl = QLabel("70%")
        self._mel_bias.valueChanged.connect(
            lambda v: self._mel_bias_lbl.setText(f"{v}%")
        )
        row.addWidget(self._mel_bias_lbl)
        m_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Velocity:"))
        self._mel_vel = QSpinBox()
        self._mel_vel.setRange(1, 127)
        self._mel_vel.setValue(100)
        row.addWidget(self._mel_vel)
        m_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Seed:"))
        self._mel_seed = QSpinBox()
        self._mel_seed.setRange(0, 99999)
        self._mel_seed.setValue(42)
        row.addWidget(self._mel_seed)
        self._mel_random_seed = QCheckBox("Random")
        self._mel_random_seed.setChecked(True)
        row.addWidget(self._mel_random_seed)
        m_layout.addLayout(row)

        m_layout.addStretch()
        self._tabs.addTab(self._melody_tab, "Melody")

        # Tab 2: Bass Line
        self._bass_tab = QWidget()
        b_layout = QVBoxLayout(self._bass_tab)

        row = QHBoxLayout()
        row.addWidget(QLabel("Root Note:"))
        self._bass_root = QComboBox()
        for i, name in enumerate(_NOTE_NAMES):
            self._bass_root.addItem(f"{name}3", 48 + i)
        row.addWidget(self._bass_root)
        b_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Scale:"))
        self._bass_scale = QComboBox()
        self._bass_scale.addItems(list(SCALE_INTERVALS.keys()))
        row.addWidget(self._bass_scale)
        b_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Bars:"))
        self._bass_bars = QSpinBox()
        self._bass_bars.setRange(1, 64)
        self._bass_bars.setValue(8)
        row.addWidget(self._bass_bars)
        b_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Progression:"))
        self._bass_prog = QComboBox()
        self._bass_prog.addItems(list(PROGRESSIONS.keys()))
        row.addWidget(self._bass_prog)
        b_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Pattern:"))
        self._bass_pattern = QComboBox()
        self._bass_pattern.addItems(["root", "root_fifth", "walking"])
        row.addWidget(self._bass_pattern)
        b_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Track:"))
        self._bass_track = QSpinBox()
        self._bass_track.setRange(0, 11)
        self._bass_track.setValue(1)
        row.addWidget(self._bass_track)
        b_layout.addLayout(row)

        b_layout.addStretch()
        self._tabs.addTab(self._bass_tab, "Bass Line")

        layout.addWidget(self._tabs)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        generate_btn = QPushButton("Generate")
        generate_btn.setMinimumWidth(100)
        generate_btn.clicked.connect(self._on_generate)
        btn_row.addWidget(generate_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

    def _on_generate(self) -> None:
        import random

        tab = self._tabs.currentIndex()

        if tab == 0:  # Melody
            seed = None if self._mel_random_seed.isChecked() else self._mel_seed.value()
            if seed is None:
                seed = random.randint(0, 99999)

            config = MelodyConfig(
                root=self._mel_root.currentData(),
                scale=self._mel_scale.currentText(),
                note_min=self._mel_min.value(),
                note_max=self._mel_max.value(),
                num_bars=self._mel_bars.value(),
                time_signature=self._time_signature,
                velocity=self._mel_vel.value(),
                track=0,
                stepwise_bias=self._mel_bias.value() / 100.0,
            )
            self._result_notes = generate_melody(config, seed=seed)

        elif tab == 1:  # Bass Line
            config = BassConfig(
                root=self._bass_root.currentData(),
                scale=self._bass_scale.currentText(),
                num_bars=self._bass_bars.value(),
                time_signature=self._time_signature,
                progression=self._bass_prog.currentText(),
                track=self._bass_track.value(),
                pattern=self._bass_pattern.currentText(),
            )
            self._result_notes = generate_bass_line(config)

        self.accept()
