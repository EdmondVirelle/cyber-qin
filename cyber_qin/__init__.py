"""賽博琴仙 — MIDI-to-Keyboard mapper for 燕雲十六聲."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cyber-qin")
except PackageNotFoundError:
    # Dev environment or PyInstaller without metadata — read pyproject.toml directly
    try:
        import tomllib
        from pathlib import Path

        _toml = Path(__file__).resolve().parent.parent / "pyproject.toml"
        with open(_toml, "rb") as f:
            __version__ = tomllib.load(f)["project"]["version"]
    except Exception:
        __version__ = "0.0.0-dev"
