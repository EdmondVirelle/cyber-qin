"""Generate application icon (assets/icon.ico) from icon.png.

Resizes the source PNG to multiple resolutions and exports as .ico via Pillow.

Usage:
    python scripts/generate_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    try:
        from PIL import Image
    except ImportError:
        print("ERROR: Pillow is required. Install with: pip install pillow")
        sys.exit(1)

    src_path = PROJECT_ROOT / "icon.png"
    if not src_path.exists():
        print(f"ERROR: Source image not found: {src_path}")
        sys.exit(1)

    src = Image.open(src_path).convert("RGBA")
    print(f"Source: {src.size[0]}x{src.size[1]}")

    sizes = [16, 32, 48, 64, 128, 256]
    images = [src.resize((s, s), Image.Resampling.LANCZOS) for s in sizes]

    out_path = PROJECT_ROOT / "assets" / "icon.ico"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    images[-1].save(
        str(out_path),
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1],
    )
    print(f"Icon saved to {out_path} ({', '.join(f'{s}x{s}' for s in sizes)})")


if __name__ == "__main__":
    main()
