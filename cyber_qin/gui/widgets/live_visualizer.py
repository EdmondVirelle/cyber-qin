"""Live visualizer — particle effects and ripples for note events at 60fps."""

from __future__ import annotations

import math
import random

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget

from ..theme import BG_INK

# Octave color palette (C through B)
_OCTAVE_COLORS = [
    "#FF4444",  # C  - Red
    "#FF6B33",  # C# - Orange-red
    "#FFB033",  # D  - Orange
    "#FFE033",  # D# - Yellow
    "#AAFF33",  # E  - Yellow-green
    "#33FF55",  # F  - Green
    "#33FFCC",  # F# - Cyan
    "#33BBFF",  # G  - Blue
    "#3366FF",  # G# - Indigo
    "#7733FF",  # A  - Purple
    "#CC33FF",  # A# - Magenta
    "#FF33AA",  # B  - Pink
]

_MAX_PARTICLES = 200
_MAX_RIPPLES = 30


class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "color", "size")

    def __init__(self, x: float, y: float, color: QColor) -> None:
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(40, 160)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 30  # slight upward bias
        self.life = 1.0
        self.color = color
        self.size = random.uniform(2.0, 5.0)


class _Ripple:
    __slots__ = ("x", "y", "radius", "max_radius", "life", "color")

    def __init__(self, x: float, y: float, color: QColor, max_radius: float = 80) -> None:
        self.x = x
        self.y = y
        self.radius = 0.0
        self.max_radius = max_radius
        self.life = 1.0
        self.color = color


class _VelocityBar:
    __slots__ = ("note", "velocity", "decay")

    def __init__(self, note: int, velocity: int) -> None:
        self.note = note
        self.velocity = velocity
        self.decay = 1.0


class LiveVisualizer(QWidget):
    """Particle and ripple effect visualizer for live MIDI performance."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._particles: list[_Particle] = []
        self._ripples: list[_Ripple] = []
        self._velocity_bars: dict[int, _VelocityBar] = {}
        self._active_notes: set[int] = set()

        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60fps
        self._timer.timeout.connect(self._tick)

        self.setMinimumHeight(200)

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._particles.clear()
        self._ripples.clear()
        self._velocity_bars.clear()
        self._active_notes.clear()
        self.update()

    @property
    def is_running(self) -> bool:
        return self._timer.isActive()

    def on_note_event(self, event_type: str, note: int, velocity: int) -> None:
        """Called from note event signal."""
        if event_type == "note_on" and velocity > 0:
            self._active_notes.add(note)
            self._spawn_effects(note, velocity)
            self._velocity_bars[note] = _VelocityBar(note, velocity)
        elif event_type == "note_off" or (event_type == "note_on" and velocity == 0):
            self._active_notes.discard(note)

    def _note_color(self, note: int) -> QColor:
        return QColor(_OCTAVE_COLORS[note % 12])

    def _note_x(self, note: int) -> float:
        """Map MIDI note to horizontal position."""
        w = self.width()
        # Map 21-108 (piano range) to widget width
        return ((note - 21) / 87.0) * w

    def _note_y(self, note: int) -> float:
        """Map MIDI note to vertical position (higher pitch = higher position)."""
        h = self.height()
        return h * (1.0 - (note - 21) / 87.0) * 0.7 + h * 0.1

    def _spawn_effects(self, note: int, velocity: int) -> None:
        color = self._note_color(note)
        x = self._note_x(note)
        y = self._note_y(note)

        # Particles: more particles for higher velocity
        count = max(3, velocity // 12)
        for _ in range(count):
            if len(self._particles) < _MAX_PARTICLES:
                self._particles.append(_Particle(x, y, color))

        # Ripple
        if len(self._ripples) < _MAX_RIPPLES:
            radius = 40 + (velocity / 127.0) * 60
            self._ripples.append(_Ripple(x, y, color, radius))

    def _tick(self) -> None:
        dt = 0.016  # ~16ms

        # Update particles
        alive = []
        for p in self._particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 80 * dt  # gravity
            p.life -= dt * 1.8
            if p.life > 0:
                alive.append(p)
        self._particles = alive

        # Update ripples
        alive_ripples = []
        for r in self._ripples:
            r.radius += 120 * dt
            r.life -= dt * 2.0
            if r.life > 0:
                alive_ripples.append(r)
        self._ripples = alive_ripples

        # Decay velocity bars
        to_remove = []
        for note, bar in self._velocity_bars.items():
            if note not in self._active_notes:
                bar.decay -= dt * 2.0
                if bar.decay <= 0:
                    to_remove.append(note)
        for note in to_remove:
            del self._velocity_bars[note]

        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(BG_INK))

        # Velocity bars at bottom
        bar_h = h * 0.15
        bar_y = h - bar_h
        bar_w = max(3, w / 87.0 - 1)
        for bar in self._velocity_bars.values():
            bx = self._note_x(bar.note) - bar_w / 2
            bh = (bar.velocity / 127.0) * bar_h * bar.decay
            color = self._note_color(bar.note)
            color.setAlphaF(0.6 * bar.decay)
            painter.fillRect(QRectF(bx, bar_y + bar_h - bh, bar_w, bh), color)

        # Ripples
        for r in self._ripples:
            color = QColor(r.color)
            color.setAlphaF(0.3 * r.life)
            painter.setPen(QPen(color, 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(r.x, r.y), r.radius, r.radius)

        # Particles
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self._particles:
            color = QColor(p.color)
            color.setAlphaF(max(0, p.life * 0.8))
            painter.setBrush(color)
            size = p.size * p.life
            painter.drawEllipse(QPointF(p.x, p.y), size, size)

        # Active note glow indicators at bottom
        for note in self._active_notes:
            x = self._note_x(note)
            color = self._note_color(note)
            grad = QRadialGradient(x, h - 5, 15)
            grad.setColorAt(0, color)
            transparent = QColor(color)
            transparent.setAlphaF(0.0)
            grad.setColorAt(1, transparent)
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, h - 5), 15, 15)

        painter.end()
