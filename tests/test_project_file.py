"""Tests for project_file — .cqp save/load."""

from __future__ import annotations

import tempfile
from pathlib import Path

from cyber_qin.core.beat_sequence import EditorSequence
from cyber_qin.core.project_file import (
    autosave,
    get_autosave_path,
    load,
    load_autosave,
    save,
)


class TestSaveLoad:
    def test_roundtrip(self, tmp_path: Path):
        seq = EditorSequence(tempo_bpm=90.0, time_signature=(3, 4), num_tracks=3)
        seq.set_step_duration("1/8")
        seq.add_note(60)
        seq.add_note(64)
        seq.add_rest()
        seq.set_active_track(1)
        seq.add_note(72)
        seq._tracks[0].muted = True
        seq._tracks[1].name = "Bass"

        path = tmp_path / "test.cqp"
        save(path, seq)
        assert path.exists()

        restored = load(path)
        assert restored.tempo_bpm == 90.0
        assert restored.time_signature == (3, 4)
        assert restored.track_count == 3
        assert restored.note_count == 3
        assert restored.rest_count == 1
        assert restored.step_label == "1/8"
        assert restored.tracks[0].muted is True
        assert restored.tracks[1].name == "Bass"

    def test_empty_sequence(self, tmp_path: Path):
        seq = EditorSequence()
        path = tmp_path / "empty.cqp"
        save(path, seq)
        restored = load(path)
        assert restored.note_count == 0
        assert restored.track_count == 4

    def test_save_creates_directory(self, tmp_path: Path):
        seq = EditorSequence()
        path = tmp_path / "sub" / "dir" / "test.cqp"
        save(path, seq)
        assert path.exists()

    def test_gzip_compressed(self, tmp_path: Path):
        seq = EditorSequence()
        for i in range(50):
            seq.add_note(60 + (i % 12))
        path = tmp_path / "big.cqp"
        save(path, seq)
        # gzip file should start with magic bytes 1f 8b
        with open(path, "rb") as f:
            magic = f.read(2)
        assert magic == b"\x1f\x8b"


class TestAutosave:
    def test_autosave_path(self):
        path = get_autosave_path()
        assert path.name == "autosave.cqp"
        assert ".cyber_qin" in str(path)

    def test_load_autosave_missing(self, monkeypatch):
        # Point autosave to a temp dir that doesn't have the file
        import cyber_qin.core.project_file as pf

        monkeypatch.setattr(pf, "_AUTOSAVE_FILE", Path(tempfile.mkdtemp()) / "nope.cqp")
        result = load_autosave()
        assert result is None

    def test_autosave_roundtrip(self, monkeypatch, tmp_path: Path):
        import cyber_qin.core.project_file as pf

        autosave_path = tmp_path / "autosave.cqp"
        monkeypatch.setattr(pf, "_AUTOSAVE_FILE", autosave_path)

        seq = EditorSequence()
        seq.add_note(60)
        autosave(seq)
        assert autosave_path.exists()

        restored = load_autosave()
        assert restored is not None
        assert restored.note_count == 1
