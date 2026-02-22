"""Simple WAV audio exporter using sine-wave synthesis.

No external dependencies — uses only ``math`` and ``struct`` from the
standard library.  Generates 16-bit PCM WAV files.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AudioExportConfig:
    """Configuration for audio export."""

    sample_rate: int = 44100
    amplitude: float = 0.5  # 0.0-1.0
    attack_ms: float = 10.0
    release_ms: float = 50.0


def _midi_to_freq(midi_note: int) -> float:
    """Convert MIDI note number to frequency in Hz (A4 = 440 Hz)."""
    return float(440.0 * (2.0 ** ((midi_note - 69) / 12.0)))


def _generate_tone(
    freq: float,
    duration_sec: float,
    sample_rate: int,
    amplitude: float,
    attack_ms: float,
    release_ms: float,
) -> list[float]:
    """Generate a sine tone with simple attack/release envelope."""
    num_samples = int(duration_sec * sample_rate)
    if num_samples <= 0:
        return []

    attack_samples = int(attack_ms / 1000.0 * sample_rate)
    release_samples = int(release_ms / 1000.0 * sample_rate)
    samples: list[float] = []

    for i in range(num_samples):
        # Envelope
        env = 1.0
        if i < attack_samples and attack_samples > 0:
            env = i / attack_samples
        elif i > num_samples - release_samples and release_samples > 0:
            remaining = num_samples - i
            env = remaining / release_samples

        # Sine wave
        t = i / sample_rate
        val = amplitude * env * math.sin(2.0 * math.pi * freq * t)
        samples.append(val)

    return samples


def _write_wav_header(
    f,
    num_samples: int,
    sample_rate: int,
    num_channels: int = 1,
    bits_per_sample: int = 16,
) -> None:
    """Write a WAV file header."""
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    # RIFF header
    f.write(b"RIFF")
    f.write(struct.pack("<I", 36 + data_size))
    f.write(b"WAVE")

    # fmt chunk
    f.write(b"fmt ")
    f.write(struct.pack("<I", 16))  # chunk size
    f.write(struct.pack("<H", 1))  # PCM format
    f.write(struct.pack("<H", num_channels))
    f.write(struct.pack("<I", sample_rate))
    f.write(struct.pack("<I", byte_rate))
    f.write(struct.pack("<H", block_align))
    f.write(struct.pack("<H", bits_per_sample))

    # data chunk
    f.write(b"data")
    f.write(struct.pack("<I", data_size))


def export_wav(
    beat_notes: list,
    output_path: str | Path,
    *,
    tempo_bpm: float = 120.0,
    config: AudioExportConfig | None = None,
) -> Path:
    """Export BeatNote list to a WAV file using sine-wave synthesis.

    Parameters
    ----------
    beat_notes : list[BeatNote]
        Notes from the editor sequence.
    output_path : str | Path
        Output file path.
    tempo_bpm : float
        Tempo for converting beats to seconds.
    config : AudioExportConfig | None
        Audio export settings.

    Returns
    -------
    Path
        The output file path.
    """
    if config is None:
        config = AudioExportConfig()

    output_path = Path(output_path)
    sec_per_beat = 60.0 / tempo_bpm

    # Calculate total duration
    if not beat_notes:
        total_sec = 1.0
    else:
        total_sec = (
            max((n.time_beats + n.duration_beats) * sec_per_beat for n in beat_notes) + 0.5
        )  # 0.5s tail

    total_samples = int(total_sec * config.sample_rate)
    buffer = [0.0] * total_samples

    # Mix all notes into the buffer
    for n in beat_notes:
        start_sec = n.time_beats * sec_per_beat
        dur_sec = n.duration_beats * sec_per_beat
        freq = _midi_to_freq(n.note)
        vel_scale = n.velocity / 127.0

        tone = _generate_tone(
            freq,
            dur_sec,
            config.sample_rate,
            config.amplitude * vel_scale,
            config.attack_ms,
            config.release_ms,
        )

        start_idx = int(start_sec * config.sample_rate)
        for i, val in enumerate(tone):
            idx = start_idx + i
            if 0 <= idx < total_samples:
                buffer[idx] += val

    # Normalise to prevent clipping
    peak = max(abs(s) for s in buffer) if buffer else 1.0
    if peak > 1.0:
        scale = 0.95 / peak
        buffer = [s * scale for s in buffer]

    # Write WAV
    with open(output_path, "wb") as f:
        _write_wav_header(f, total_samples, config.sample_rate)
        for sample in buffer:
            # Clamp and convert to 16-bit signed integer
            clamped = max(-1.0, min(1.0, sample))
            int_val = int(clamped * 32767)
            f.write(struct.pack("<h", int_val))

    return output_path


def export_wav_bytes(
    beat_notes: list,
    *,
    tempo_bpm: float = 120.0,
    config: AudioExportConfig | None = None,
) -> bytes:
    """Export BeatNote list to WAV bytes (for preview or in-memory use)."""
    import io

    if config is None:
        config = AudioExportConfig()

    sec_per_beat = 60.0 / tempo_bpm

    if not beat_notes:
        total_sec = 1.0
    else:
        total_sec = max((n.time_beats + n.duration_beats) * sec_per_beat for n in beat_notes) + 0.5

    total_samples = int(total_sec * config.sample_rate)
    buffer = [0.0] * total_samples

    for n in beat_notes:
        start_sec = n.time_beats * sec_per_beat
        dur_sec = n.duration_beats * sec_per_beat
        freq = _midi_to_freq(n.note)
        vel_scale = n.velocity / 127.0

        tone = _generate_tone(
            freq,
            dur_sec,
            config.sample_rate,
            config.amplitude * vel_scale,
            config.attack_ms,
            config.release_ms,
        )

        start_idx = int(start_sec * config.sample_rate)
        for i, val in enumerate(tone):
            idx = start_idx + i
            if 0 <= idx < total_samples:
                buffer[idx] += val

    peak = max(abs(s) for s in buffer) if buffer else 1.0
    if peak > 1.0:
        scale = 0.95 / peak
        buffer = [s * scale for s in buffer]

    buf = io.BytesIO()
    _write_wav_header(buf, total_samples, config.sample_rate)
    for sample in buffer:
        clamped = max(-1.0, min(1.0, sample))
        int_val = int(clamped * 32767)
        buf.write(struct.pack("<h", int_val))

    return buf.getvalue()
