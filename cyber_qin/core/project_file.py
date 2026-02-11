"""Project file save/load for the editor — .cqp format (JSON + gzip)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from .beat_sequence import EditorSequence

_AUTOSAVE_DIR = Path.home() / ".cyber_qin"
_AUTOSAVE_FILE = _AUTOSAVE_DIR / "autosave.cqp"


def save(path: str | Path, seq: EditorSequence) -> None:
    """Save an EditorSequence to a .cqp file (gzipped JSON)."""
    data = seq.to_project_dict()
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as f:
        f.write(raw)


def load(path: str | Path) -> EditorSequence:
    """Load an EditorSequence from a .cqp file."""
    path = Path(path)
    with gzip.open(path, "rb") as f:
        raw = f.read()
    data = json.loads(raw.decode("utf-8"))
    return EditorSequence.from_project_dict(data)


def autosave(seq: EditorSequence) -> None:
    """Write autosave to ~/.cyber_qin/autosave.cqp."""
    save(_AUTOSAVE_FILE, seq)


def load_autosave() -> EditorSequence | None:
    """Load autosave if it exists, else return None."""
    if not _AUTOSAVE_FILE.exists():
        return None
    try:
        return load(_AUTOSAVE_FILE)
    except Exception:
        return None


def get_autosave_path() -> Path:
    """Return the autosave file path."""
    return _AUTOSAVE_FILE
