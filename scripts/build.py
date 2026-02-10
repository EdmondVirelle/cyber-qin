"""One-click build script for 賽博琴仙.

Auto-detects Python 3.13 → creates venv → installs deps → generates icon
→ runs PyInstaller → signs executable.

Usage:
    python scripts/build.py
    python scripts/build.py --skip-sign   # Skip code signing
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / ".venv313"
SPEC_FILE = PROJECT_ROOT / "cyber_qin.spec"
ICON_FILE = PROJECT_ROOT / "assets" / "icon.ico"
ICON_SCRIPT = PROJECT_ROOT / "scripts" / "generate_icon.py"
DIST_DIR = PROJECT_ROOT / "dist" / "賽博琴仙"
EXE_PATH = DIST_DIR / "賽博琴仙.exe"

CERT_SUBJECT = "CN=CyberQin, O=CyberQin"
TIMESTAMP_SERVER = "http://timestamp.digicert.com"

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


def sign_executable() -> bool:
    """Sign the exe with a self-signed certificate via PowerShell.

    Creates the certificate if it doesn't exist yet.
    Returns True on success, False if signing is unavailable.
    """
    if sys.platform != "win32":
        print("Code signing is only available on Windows.")
        return False

    if not EXE_PATH.exists():
        print(f"Executable not found: {EXE_PATH}")
        return False

    # PowerShell script: find or create cert, then sign
    ps_script = f"""
$ErrorActionPreference = 'Stop'

# Look for existing CyberQin code signing cert
$cert = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert |
    Where-Object {{ $_.Subject -eq '{CERT_SUBJECT}' }} |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if (-not $cert) {{
    Write-Host 'Creating self-signed code signing certificate...'
    $cert = New-SelfSignedCertificate `
        -Subject '{CERT_SUBJECT}' `
        -Type CodeSigningCert `
        -CertStoreLocation Cert:\\CurrentUser\\My `
        -NotAfter (Get-Date).AddYears(3)
    Write-Host "Certificate created: $($cert.Thumbprint)"
}} else {{
    Write-Host "Using existing certificate: $($cert.Thumbprint)"
}}

# Sign the executable
Set-AuthenticodeSignature `
    -FilePath '{EXE_PATH}' `
    -Certificate $cert `
    -TimestampServer '{TIMESTAMP_SERVER}'

Write-Host 'Signing complete.'
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        print("\nWARNING: Code signing failed. The exe will still work but may trigger AV warnings.")
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 賽博琴仙")
    parser.add_argument("--skip-sign", action="store_true", help="Skip code signing step")
    args = parser.parse_args()

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

    # 6. Code signing
    if not args.skip_sign and EXE_PATH.exists():
        print(f"\n{'='*60}")
        print("  Code signing")
        print(f"{'='*60}")
        sign_executable()

    # Summary
    if EXE_PATH.exists():
        print("\nBuild successful!")
        print(f"Output: {DIST_DIR}")
        print(f"Executable: {EXE_PATH}")
    else:
        print(f"\nWARNING: Expected exe not found at {EXE_PATH}")
        print(f"Check {DIST_DIR} for output.")


if __name__ == "__main__":
    main()
