"""賽博琴仙 — MIDI-to-Keyboard mapper for 燕雲十六聲."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cyber-qin")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
