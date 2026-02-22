"""Automation lanes — time-varying parameter curves for the editor.

Supports per-track automation of velocity, tempo, and other parameters
using linear interpolation between control points.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field


@dataclass
class AutomationPoint:
    """A single control point on an automation lane."""

    time_beats: float
    value: float  # 0.0 – 1.0 normalised


@dataclass
class AutomationLane:
    """A named automation curve made of sorted control points.

    Interpolation is piecewise-linear.  Values before the first point
    equal the first point's value; values after the last point equal
    the last point's value.
    """

    parameter: str  # e.g. "velocity", "tempo"
    points: list[AutomationPoint] = field(default_factory=list)

    # Range mapping: normalised 0–1 → real value
    value_min: float = 0.0
    value_max: float = 127.0

    def _sort(self) -> None:
        self.points.sort(key=lambda p: p.time_beats)

    def add_point(self, time_beats: float, value: float) -> None:
        """Add or replace a control point at *time_beats*."""
        value = max(0.0, min(1.0, value))
        # Replace if a point already exists at this time
        for p in self.points:
            if abs(p.time_beats - time_beats) < 1e-6:
                p.value = value
                return
        self.points.append(AutomationPoint(time_beats, value))
        self._sort()

    def remove_point(self, index: int) -> None:
        if 0 <= index < len(self.points):
            self.points.pop(index)

    def move_point(self, index: int, time_beats: float, value: float) -> None:
        if 0 <= index < len(self.points):
            self.points[index].time_beats = max(0.0, time_beats)
            self.points[index].value = max(0.0, min(1.0, value))
            self._sort()

    def value_at(self, time_beats: float) -> float:
        """Interpolated normalised value at *time_beats*."""
        if not self.points:
            return 0.5  # default mid-range
        if len(self.points) == 1:
            return self.points[0].value

        # Before first point
        if time_beats <= self.points[0].time_beats:
            return self.points[0].value
        # After last point
        if time_beats >= self.points[-1].time_beats:
            return self.points[-1].value

        # Binary search for surrounding points
        lo, hi = 0, len(self.points) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if self.points[mid].time_beats <= time_beats:
                lo = mid
            else:
                hi = mid

        p0 = self.points[lo]
        p1 = self.points[hi]
        dt = p1.time_beats - p0.time_beats
        if dt <= 0:
            return p0.value
        t = (time_beats - p0.time_beats) / dt
        return p0.value + (p1.value - p0.value) * t

    def real_value_at(self, time_beats: float) -> float:
        """Mapped value at *time_beats* in the real parameter range."""
        norm = self.value_at(time_beats)
        return self.value_min + norm * (self.value_max - self.value_min)

    def clear(self) -> None:
        self.points.clear()

    def to_dict(self) -> dict:
        return {
            "parameter": self.parameter,
            "value_min": self.value_min,
            "value_max": self.value_max,
            "points": [{"time": p.time_beats, "value": p.value} for p in self.points],
        }

    @classmethod
    def from_dict(cls, data: dict) -> AutomationLane:
        lane = cls(
            parameter=data.get("parameter", "velocity"),
            value_min=data.get("value_min", 0.0),
            value_max=data.get("value_max", 127.0),
        )
        for pd in data.get("points", []):
            lane.points.append(AutomationPoint(pd["time"], pd["value"]))
        lane._sort()
        return lane


class AutomationManager:
    """Manages multiple automation lanes per track."""

    def __init__(self) -> None:
        self._lanes: dict[str, AutomationLane] = {}

    @property
    def lanes(self) -> dict[str, AutomationLane]:
        return dict(self._lanes)

    def get_lane(self, parameter: str) -> AutomationLane | None:
        return self._lanes.get(parameter)

    def ensure_lane(
        self, parameter: str, value_min: float = 0.0, value_max: float = 127.0
    ) -> AutomationLane:
        """Get or create a lane for the given parameter."""
        if parameter not in self._lanes:
            self._lanes[parameter] = AutomationLane(
                parameter=parameter,
                value_min=value_min,
                value_max=value_max,
            )
        return self._lanes[parameter]

    def remove_lane(self, parameter: str) -> None:
        self._lanes.pop(parameter, None)

    def value_at(self, parameter: str, time_beats: float) -> float | None:
        """Get interpolated real value, or None if no lane exists."""
        lane = self._lanes.get(parameter)
        if lane is None:
            return None
        return lane.real_value_at(time_beats)

    def clear(self) -> None:
        self._lanes.clear()

    def deep_copy(self) -> AutomationManager:
        mgr = AutomationManager()
        for key, lane in self._lanes.items():
            mgr._lanes[key] = AutomationLane(
                parameter=lane.parameter,
                points=[copy.copy(p) for p in lane.points],
                value_min=lane.value_min,
                value_max=lane.value_max,
            )
        return mgr

    def to_dict(self) -> dict:
        return {key: lane.to_dict() for key, lane in self._lanes.items()}

    @classmethod
    def from_dict(cls, data: dict) -> AutomationManager:
        mgr = cls()
        for key, lane_data in data.items():
            mgr._lanes[key] = AutomationLane.from_dict(lane_data)
        return mgr
