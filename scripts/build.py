"""One-click build script for 賽博琴仙.

Auto-detects Python 3.13 → creates venv → installs deps → generates icon → runs PyInstaller.

Usage:
    python scripts/build.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / ".venv313"
SPEC_FILE = PROJECT_ROOT / "cyber_qin.spec"
ICON_FILE = PROJECT_ROOT / "assets" / "icon.ico"
ICON_SCRIPT = PROJECT_ROOT / "scripts" / "generate_icon.py"

# Minimum required Python version for build (PyQt6 compat)
REQUIRED_MAJOR = 3
REQUIRED_MINOR = 13


def find_python() -> str:
    """Find a Python 3.13 interpreter."""
    # Check if current interpreter qualifies
    if sys.version_info[:2] == (REQUIRED_MAJOR, REQUIRED_MINOR):
        return sys.executable

    # Try common names
    for name in ("python3.13", "python3", "python", "py"):
        path = shutil.which(name)
        if not path:
            continue
        try:
            result = subprocess.run(
                [path, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True, text=True, timeout=10,
            )
            if result.stdout.strip() == f"{REQUIRED_MAJOR}.{REQUIRED_MINOR}":
                return path
        except Exception:
            continue

    # Try py launcher (Windows)
    py = shutil.which("py")
    if py:
        try:
            result = subprocess.run(
                [py, f"-{REQUIRED_MAJOR}.{REQUIRED_MINOR}", "-c", "print('ok')"],
                capture_output=True, text=True, timeout=10,
            )
            if result.stdout.strip() == "ok":
                return f"{py} -{REQUIRED_MAJOR}.{REQUIRED_MINOR}"
        except Exception:
            pass

    return ""


def run(cmd: list[str], desc: str) -> None:
    """Run a command with description, exit on failure."""
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"{'='*60}")
    print(f"  $ {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"\nERROR: {desc} failed (exit code {result.returncode})")
        sys.exit(result.returncode)


def main() -> None:
    print("賽博琴仙 Build Script")
    print(f"Project root: {PROJECT_ROOT}")

    # 1. Find Python 3.13
    python = find_python()
    if not python:
        print(f"\nERROR: Python {REQUIRED_MAJOR}.{REQUIRED_MINOR} not found.")
        print("Install it from https://www.python.org/downloads/")
        sys.exit(1)
    print(f"Using Python: {python}")

    # 2. Create/reuse venv
    if not VENV_DIR.exists():
        run([python, "-m", "venv", str(VENV_DIR)], "Creating virtual environment")
    else:
        print(f"Reusing existing venv: {VENV_DIR}")

    # Determine pip/python paths inside venv
    if sys.platform == "win32":
        venv_python = str(VENV_DIR / "Scripts" / "python.exe")
        venv_pip = str(VENV_DIR / "Scripts" / "pip.exe")
    else:
        venv_python = str(VENV_DIR / "bin" / "python")
        venv_pip = str(VENV_DIR / "bin" / "pip")

    # 3. Install dependencies
    run([venv_pip, "install", "-e", ".[dev]"], "Installing project + dev dependencies")

    # 4. Generate icon
    if not ICON_FILE.exists():
        run([venv_python, str(ICON_SCRIPT)], "Generating application icon")
    else:
        print(f"\nIcon already exists: {ICON_FILE}")

    # 5. Run PyInstaller
    run(
        [venv_python, "-m", "PyInstaller", str(SPEC_FILE), "--clean", "-y"],
        "Building with PyInstaller",
    )

    dist_dir = PROJECT_ROOT / "dist" / "賽博琴仙"
    exe_path = dist_dir / "賽博琴仙.exe"
    if exe_path.exists():
        print("\nBuild successful!")
        print(f"Output: {dist_dir}")
        print(f"Executable: {exe_path}")
    else:
        print(f"\nWARNING: Expected exe not found at {exe_path}")
        print(f"Check {dist_dir} for output.")


if __name__ == "__main__":
    main()
