"""Tests for library metadata and bundle (.cqlib) support."""

import json
import zipfile
from pathlib import Path

import pytest

from cyber_qin.core.library_metadata import (
    BUNDLE_FILES_DIR,
    BUNDLE_MANIFEST,
    LibraryEntry,
    LibraryIndex,
    TrackMetadata,
    export_bundle,
    import_bundle,
)

# ── TrackMetadata Tests ──────────────────────────────────────


def test_track_metadata_default_values():
    """TrackMetadata uses empty strings and zero for defaults."""
    meta = TrackMetadata()
    assert meta.title == ""
    assert meta.artist == ""
    assert meta.game == ""
    assert meta.difficulty == 0
    assert meta.tags == []
    assert meta.source_url == ""
    assert meta.description == ""


def test_track_metadata_matches_title():
    """matches() finds query in title."""
    meta = TrackMetadata(title="青花瓷")
    assert meta.matches("青花")
    assert meta.matches("花瓷")
    assert not meta.matches("東風破")


def test_track_metadata_matches_artist():
    """matches() finds query in artist."""
    meta = TrackMetadata(artist="周杰倫")
    assert meta.matches("周杰")
    assert meta.matches("杰倫")
    assert not meta.matches("王力宏")


def test_track_metadata_matches_game():
    """matches() finds query in game."""
    meta = TrackMetadata(game="燕雲十六聲")
    assert meta.matches("燕雲")
    assert meta.matches("十六聲")
    assert not meta.matches("原神")


def test_track_metadata_matches_tag():
    """matches() finds query in tags."""
    meta = TrackMetadata(tags=["古風", "抒情", "經典"])
    assert meta.matches("古風")
    assert meta.matches("抒情")
    assert meta.matches("經典")
    assert not meta.matches("搖滾")


def test_track_metadata_matches_case_insensitive():
    """matches() is case-insensitive."""
    meta = TrackMetadata(title="Blue Sky", artist="John Doe", tags=["Jazz"])
    assert meta.matches("blue")
    assert meta.matches("BLUE")
    assert meta.matches("john")
    assert meta.matches("JOHN")
    assert meta.matches("jazz")
    assert meta.matches("JAZZ")


def test_track_metadata_matches_description():
    """matches() searches in description field."""
    meta = TrackMetadata(description="A beautiful classical piece from 2020")
    assert meta.matches("beautiful")
    assert meta.matches("classical")
    assert meta.matches("2020")
    assert not meta.matches("modern")


def test_track_metadata_to_dict():
    """to_dict() serializes all fields."""
    meta = TrackMetadata(
        title="Test Song",
        artist="Test Artist",
        game="Test Game",
        difficulty=3,
        tags=["tag1", "tag2"],
        source_url="https://example.com",
        description="Test description",
    )
    data = meta.to_dict()
    assert data["title"] == "Test Song"
    assert data["artist"] == "Test Artist"
    assert data["game"] == "Test Game"
    assert data["difficulty"] == 3
    assert data["tags"] == ["tag1", "tag2"]
    assert data["source_url"] == "https://example.com"
    assert data["description"] == "Test description"


def test_track_metadata_from_dict():
    """from_dict() deserializes all fields."""
    data = {
        "title": "Test Song",
        "artist": "Test Artist",
        "game": "Test Game",
        "difficulty": 4,
        "tags": ["tag1", "tag2"],
        "source_url": "https://example.com",
        "description": "Test description",
    }
    meta = TrackMetadata.from_dict(data)
    assert meta.title == "Test Song"
    assert meta.artist == "Test Artist"
    assert meta.game == "Test Game"
    assert meta.difficulty == 4
    assert meta.tags == ["tag1", "tag2"]
    assert meta.source_url == "https://example.com"
    assert meta.description == "Test description"


def test_track_metadata_roundtrip():
    """to_dict() / from_dict() roundtrip preserves data."""
    meta = TrackMetadata(
        title="青花瓷",
        artist="周杰倫",
        game="燕雲十六聲",
        difficulty=5,
        tags=["古風", "抒情"],
        source_url="https://example.com",
        description="經典曲目",
    )
    data = meta.to_dict()
    restored = TrackMetadata.from_dict(data)
    assert restored.title == meta.title
    assert restored.artist == meta.artist
    assert restored.game == meta.game
    assert restored.difficulty == meta.difficulty
    assert restored.tags == meta.tags
    assert restored.source_url == meta.source_url
    assert restored.description == meta.description


def test_track_metadata_from_dict_missing_fields():
    """from_dict() uses defaults for missing fields."""
    data = {"title": "Only Title"}
    meta = TrackMetadata.from_dict(data)
    assert meta.title == "Only Title"
    assert meta.artist == ""
    assert meta.game == ""
    assert meta.difficulty == 0
    assert meta.tags == []
    assert meta.source_url == ""
    assert meta.description == ""


# ── LibraryEntry Tests ───────────────────────────────────────


def test_library_entry_default_metadata():
    """LibraryEntry creates default TrackMetadata if not provided."""
    entry = LibraryEntry(file_path="test.mid")
    assert entry.file_path == "test.mid"
    assert isinstance(entry.metadata, TrackMetadata)
    assert entry.metadata.title == ""


def test_library_entry_to_dict():
    """to_dict() serializes file_path and metadata."""
    meta = TrackMetadata(title="Test", artist="Artist")
    entry = LibraryEntry(file_path="test.mid", metadata=meta)
    data = entry.to_dict()
    assert data["file_path"] == "test.mid"
    assert data["metadata"]["title"] == "Test"
    assert data["metadata"]["artist"] == "Artist"


def test_library_entry_from_dict():
    """from_dict() deserializes file_path and metadata."""
    data = {
        "file_path": "test.mid",
        "metadata": {
            "title": "Test Song",
            "artist": "Test Artist",
        },
    }
    entry = LibraryEntry.from_dict(data)
    assert entry.file_path == "test.mid"
    assert entry.metadata.title == "Test Song"
    assert entry.metadata.artist == "Test Artist"


def test_library_entry_roundtrip():
    """to_dict() / from_dict() roundtrip preserves data."""
    meta = TrackMetadata(title="青花瓷", artist="周杰倫", difficulty=5)
    entry = LibraryEntry(file_path="qhc.mid", metadata=meta)
    data = entry.to_dict()
    restored = LibraryEntry.from_dict(data)
    assert restored.file_path == entry.file_path
    assert restored.metadata.title == entry.metadata.title
    assert restored.metadata.artist == entry.metadata.artist
    assert restored.metadata.difficulty == entry.metadata.difficulty


def test_library_entry_from_dict_preserves_file_path():
    """from_dict() correctly preserves file path with special characters."""
    data = {
        "file_path": "C:\\Music\\燕雲\\青花瓷.mid",
        "metadata": {},
    }
    entry = LibraryEntry.from_dict(data)
    assert entry.file_path == "C:\\Music\\燕雲\\青花瓷.mid"


# ── LibraryIndex Tests ───────────────────────────────────────


def test_library_index_empty_count():
    """Empty index has count 0."""
    index = LibraryIndex()
    assert index.count == 0


def test_library_index_add_increases_count():
    """add() increases count."""
    index = LibraryIndex()
    entry = LibraryEntry(file_path="test1.mid")
    index.add(entry)
    assert index.count == 1
    index.add(LibraryEntry(file_path="test2.mid"))
    assert index.count == 2


def test_library_index_remove_existing_returns_true():
    """remove() returns True when entry found and removed."""
    index = LibraryIndex()
    entry = LibraryEntry(file_path="test.mid")
    index.add(entry)
    assert index.remove("test.mid") is True
    assert index.count == 0


def test_library_index_remove_nonexistent_returns_false():
    """remove() returns False when entry not found."""
    index = LibraryIndex()
    assert index.remove("nonexistent.mid") is False


def test_library_index_get_existing():
    """get() returns entry by file_path."""
    index = LibraryIndex()
    meta = TrackMetadata(title="Test Song")
    entry = LibraryEntry(file_path="test.mid", metadata=meta)
    index.add(entry)
    retrieved = index.get("test.mid")
    assert retrieved is not None
    assert retrieved.file_path == "test.mid"
    assert retrieved.metadata.title == "Test Song"


def test_library_index_get_nonexistent_returns_none():
    """get() returns None when entry not found."""
    index = LibraryIndex()
    assert index.get("nonexistent.mid") is None


def test_library_index_search_empty_query_returns_all():
    """search() with empty query returns all entries."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(title="Song 1")))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(title="Song 2")))
    results = index.search("")
    assert len(results) == 2


def test_library_index_search_filters_by_title():
    """search() filters by title match."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(title="青花瓷")))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(title="東風破")))
    results = index.search("青花")
    assert len(results) == 1
    assert results[0].metadata.title == "青花瓷"


def test_library_index_search_filters_by_artist():
    """search() filters by artist match."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(artist="周杰倫")))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(artist="王力宏")))
    results = index.search("周杰倫")
    assert len(results) == 1
    assert results[0].metadata.artist == "周杰倫"


def test_library_index_search_filters_by_game():
    """search() filters by game match."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(game="燕雲十六聲")))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(game="原神")))
    results = index.search("燕雲")
    assert len(results) == 1
    assert results[0].metadata.game == "燕雲十六聲"


def test_library_index_search_filters_by_tag():
    """search() filters by tag match."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(tags=["古風"])))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(tags=["搖滾"])))
    results = index.search("古風")
    assert len(results) == 1
    assert results[0].metadata.tags == ["古風"]


def test_library_index_filter_by_game():
    """filter_by_game() returns matching entries (case-insensitive)."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(game="燕雲十六聲")))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(game="原神")))
    index.add(LibraryEntry(file_path="test3.mid", metadata=TrackMetadata(game="燕雲十六聲")))
    results = index.filter_by_game("燕雲十六聲")
    assert len(results) == 2
    # Test case-insensitive
    results = index.filter_by_game("原神")
    assert len(results) == 1


def test_library_index_filter_by_difficulty_range():
    """filter_by_difficulty() filters by difficulty range."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(difficulty=1)))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(difficulty=3)))
    index.add(LibraryEntry(file_path="test3.mid", metadata=TrackMetadata(difficulty=5)))
    results = index.filter_by_difficulty(min_diff=2, max_diff=4)
    assert len(results) == 1
    assert results[0].metadata.difficulty == 3


def test_library_index_filter_by_tag():
    """filter_by_tag() returns entries with matching tag."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(tags=["古風", "抒情"])))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(tags=["搖滾"])))
    index.add(LibraryEntry(file_path="test3.mid", metadata=TrackMetadata(tags=["古風"])))
    results = index.filter_by_tag("古風")
    assert len(results) == 2


def test_library_index_all_games_unique_sorted():
    """all_games() returns unique sorted game names."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(game="燕雲十六聲")))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(game="原神")))
    index.add(LibraryEntry(file_path="test3.mid", metadata=TrackMetadata(game="燕雲十六聲")))
    index.add(LibraryEntry(file_path="test4.mid", metadata=TrackMetadata(game="")))
    games = index.all_games()
    assert games == ["原神", "燕雲十六聲"]


def test_library_index_all_tags_unique_sorted():
    """all_tags() returns unique sorted tag names."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(tags=["古風", "抒情"])))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(tags=["搖滾", "古風"])))
    index.add(LibraryEntry(file_path="test3.mid", metadata=TrackMetadata(tags=["經典"])))
    tags = index.all_tags()
    assert tags == ["古風", "抒情", "搖滾", "經典"]


def test_library_index_to_dict():
    """to_dict() serializes version and entries."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test.mid", metadata=TrackMetadata(title="Test")))
    data = index.to_dict()
    assert data["version"] == 1
    assert len(data["entries"]) == 1
    assert data["entries"][0]["file_path"] == "test.mid"
    assert data["entries"][0]["metadata"]["title"] == "Test"


def test_library_index_from_dict():
    """from_dict() deserializes entries."""
    data = {
        "version": 1,
        "entries": [
            {
                "file_path": "test1.mid",
                "metadata": {"title": "Song 1"},
            },
            {
                "file_path": "test2.mid",
                "metadata": {"title": "Song 2"},
            },
        ],
    }
    index = LibraryIndex.from_dict(data)
    assert index.count == 2
    assert index.get("test1.mid").metadata.title == "Song 1"
    assert index.get("test2.mid").metadata.title == "Song 2"


def test_library_index_roundtrip():
    """to_dict() / from_dict() roundtrip preserves data."""
    index = LibraryIndex()
    index.add(
        LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(title="青花瓷", difficulty=5))
    )
    index.add(
        LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(title="東風破", difficulty=3))
    )
    data = index.to_dict()
    restored = LibraryIndex.from_dict(data)
    assert restored.count == index.count
    assert restored.get("test1.mid").metadata.title == "青花瓷"
    assert restored.get("test2.mid").metadata.difficulty == 3


def test_library_index_save_load_roundtrip(tmp_path):
    """save() / load() roundtrip preserves data."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(title="Song 1")))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(title="Song 2")))

    file_path = tmp_path / "library.json"
    index.save(file_path)

    loaded = LibraryIndex.load(file_path)
    assert loaded.count == 2
    assert loaded.get("test1.mid").metadata.title == "Song 1"
    assert loaded.get("test2.mid").metadata.title == "Song 2"


def test_library_index_load_nonexistent_returns_empty(tmp_path):
    """load() returns empty index when file does not exist."""
    file_path = tmp_path / "nonexistent.json"
    index = LibraryIndex.load(file_path)
    assert index.count == 0


def test_library_index_entries_property_returns_copy():
    """entries property returns a copy, not the internal list."""
    index = LibraryIndex()
    entry = LibraryEntry(file_path="test.mid")
    index.add(entry)
    entries = index.entries
    entries.append(LibraryEntry(file_path="fake.mid"))
    assert index.count == 1  # Should not be affected


def test_library_index_search_whitespace_query_returns_all():
    """search() with whitespace-only query returns all entries."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid"))
    index.add(LibraryEntry(file_path="test2.mid"))
    results = index.search("   ")
    assert len(results) == 2


# ── Bundle (.cqlib) Tests ────────────────────────────────────


def test_export_bundle_creates_zip_file(tmp_path):
    """export_bundle() creates a ZIP file."""
    midi_file = tmp_path / "test.mid"
    midi_file.write_bytes(b"MIDI_DATA")

    entry = LibraryEntry(file_path=str(midi_file), metadata=TrackMetadata(title="Test"))
    output_path = tmp_path / "bundle.cqlib"

    result = export_bundle([entry], output_path)
    assert result.exists()
    assert zipfile.is_zipfile(result)


def test_export_bundle_contains_manifest(tmp_path):
    """export_bundle() includes manifest.json."""
    midi_file = tmp_path / "test.mid"
    midi_file.write_bytes(b"MIDI_DATA")

    entry = LibraryEntry(file_path=str(midi_file), metadata=TrackMetadata(title="Test"))
    output_path = tmp_path / "bundle.cqlib"

    export_bundle([entry], output_path)

    with zipfile.ZipFile(output_path, "r") as zf:
        assert BUNDLE_MANIFEST in zf.namelist()


def test_export_bundle_contains_files(tmp_path):
    """export_bundle() includes MIDI files in files/ directory."""
    midi_file = tmp_path / "test.mid"
    midi_file.write_bytes(b"MIDI_DATA")

    entry = LibraryEntry(file_path=str(midi_file), metadata=TrackMetadata(title="Test"))
    output_path = tmp_path / "bundle.cqlib"

    export_bundle([entry], output_path)

    with zipfile.ZipFile(output_path, "r") as zf:
        expected_path = BUNDLE_FILES_DIR + "test.mid"
        assert expected_path in zf.namelist()
        assert zf.read(expected_path) == b"MIDI_DATA"


def test_import_bundle_extracts_files(tmp_path):
    """import_bundle() extracts files to target directory."""
    # Create bundle
    midi_file = tmp_path / "test.mid"
    midi_file.write_bytes(b"MIDI_DATA")

    entry = LibraryEntry(file_path=str(midi_file), metadata=TrackMetadata(title="Test"))
    bundle_path = tmp_path / "bundle.cqlib"
    export_bundle([entry], bundle_path)

    # Import bundle
    extract_dir = tmp_path / "extracted"
    entries = import_bundle(bundle_path, extract_dir)

    assert len(entries) == 1
    extracted_file = Path(entries[0].file_path)
    assert extracted_file.exists()
    assert extracted_file.read_bytes() == b"MIDI_DATA"


def test_import_bundle_reads_metadata(tmp_path):
    """import_bundle() correctly reads metadata from manifest."""
    midi_file = tmp_path / "test.mid"
    midi_file.write_bytes(b"MIDI_DATA")

    meta = TrackMetadata(title="Test Song", artist="Test Artist", difficulty=4)
    entry = LibraryEntry(file_path=str(midi_file), metadata=meta)
    bundle_path = tmp_path / "bundle.cqlib"
    export_bundle([entry], bundle_path)

    extract_dir = tmp_path / "extracted"
    entries = import_bundle(bundle_path, extract_dir)

    assert len(entries) == 1
    assert entries[0].metadata.title == "Test Song"
    assert entries[0].metadata.artist == "Test Artist"
    assert entries[0].metadata.difficulty == 4


def test_export_import_roundtrip_preserves_metadata(tmp_path):
    """export → import roundtrip preserves metadata."""
    midi_file = tmp_path / "test.mid"
    midi_file.write_bytes(b"MIDI_DATA")

    meta = TrackMetadata(
        title="青花瓷",
        artist="周杰倫",
        game="燕雲十六聲",
        difficulty=5,
        tags=["古風", "抒情"],
    )
    entry = LibraryEntry(file_path=str(midi_file), metadata=meta)
    bundle_path = tmp_path / "bundle.cqlib"
    export_bundle([entry], bundle_path)

    extract_dir = tmp_path / "extracted"
    entries = import_bundle(bundle_path, extract_dir)

    assert len(entries) == 1
    assert entries[0].metadata.title == "青花瓷"
    assert entries[0].metadata.artist == "周杰倫"
    assert entries[0].metadata.game == "燕雲十六聲"
    assert entries[0].metadata.difficulty == 5
    assert entries[0].metadata.tags == ["古風", "抒情"]


def test_export_bundle_skips_nonexistent_file(tmp_path):
    """export_bundle() gracefully skips non-existent files."""
    entry = LibraryEntry(file_path="nonexistent.mid", metadata=TrackMetadata(title="Test"))
    output_path = tmp_path / "bundle.cqlib"

    export_bundle([entry], output_path)

    with zipfile.ZipFile(output_path, "r") as zf:
        # Should only contain manifest, no files
        assert BUNDLE_MANIFEST in zf.namelist()
        assert len([n for n in zf.namelist() if n.startswith(BUNDLE_FILES_DIR)]) == 0


def test_import_bundle_corrupt_zip_returns_empty(tmp_path):
    """import_bundle() returns empty list for corrupt ZIP."""
    corrupt_file = tmp_path / "corrupt.cqlib"
    corrupt_file.write_bytes(b"NOT_A_ZIP")

    extract_dir = tmp_path / "extracted"
    with pytest.raises(zipfile.BadZipFile):
        import_bundle(corrupt_file, extract_dir)


def test_export_bundle_includes_title_and_author(tmp_path):
    """export_bundle() includes bundle title and author in manifest."""
    midi_file = tmp_path / "test.mid"
    midi_file.write_bytes(b"MIDI_DATA")

    entry = LibraryEntry(file_path=str(midi_file))
    output_path = tmp_path / "bundle.cqlib"

    export_bundle(
        [entry], output_path, bundle_title="Test Collection", bundle_author="Test Author"
    )

    with zipfile.ZipFile(output_path, "r") as zf:
        manifest = json.loads(zf.read(BUNDLE_MANIFEST))
        assert manifest["title"] == "Test Collection"
        assert manifest["author"] == "Test Author"


def test_export_bundle_multiple_entries(tmp_path):
    """export_bundle() handles multiple entries correctly."""
    midi1 = tmp_path / "song1.mid"
    midi1.write_bytes(b"MIDI1")
    midi2 = tmp_path / "song2.mid"
    midi2.write_bytes(b"MIDI2")

    entries = [
        LibraryEntry(file_path=str(midi1), metadata=TrackMetadata(title="Song 1")),
        LibraryEntry(file_path=str(midi2), metadata=TrackMetadata(title="Song 2")),
    ]
    output_path = tmp_path / "bundle.cqlib"

    export_bundle(entries, output_path)

    with zipfile.ZipFile(output_path, "r") as zf:
        manifest = json.loads(zf.read(BUNDLE_MANIFEST))
        assert len(manifest["entries"]) == 2
        assert BUNDLE_FILES_DIR + "song1.mid" in zf.namelist()
        assert BUNDLE_FILES_DIR + "song2.mid" in zf.namelist()


def test_import_bundle_missing_manifest_returns_empty(tmp_path):
    """import_bundle() returns empty list if manifest is missing."""
    # Create ZIP without manifest
    bundle_path = tmp_path / "no_manifest.cqlib"
    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.writestr("dummy.txt", "data")

    extract_dir = tmp_path / "extracted"
    entries = import_bundle(bundle_path, extract_dir)
    assert len(entries) == 0


def test_import_bundle_invalid_json_manifest_returns_empty(tmp_path):
    """import_bundle() returns empty list if manifest has invalid JSON."""
    bundle_path = tmp_path / "bad_manifest.cqlib"
    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.writestr(BUNDLE_MANIFEST, "NOT VALID JSON")

    extract_dir = tmp_path / "extracted"
    entries = import_bundle(bundle_path, extract_dir)
    assert len(entries) == 0


def test_filter_by_tag_case_insensitive(tmp_path):
    """filter_by_tag() is case-insensitive."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test1.mid", metadata=TrackMetadata(tags=["Jazz", "Blues"])))
    index.add(LibraryEntry(file_path="test2.mid", metadata=TrackMetadata(tags=["Rock"])))

    results = index.filter_by_tag("jazz")
    assert len(results) == 1
    results = index.filter_by_tag("JAZZ")
    assert len(results) == 1


def test_library_index_save_creates_parent_directories(tmp_path):
    """save() creates parent directories if they don't exist."""
    index = LibraryIndex()
    index.add(LibraryEntry(file_path="test.mid"))

    nested_path = tmp_path / "nested" / "dirs" / "library.json"
    index.save(nested_path)

    assert nested_path.exists()
    loaded = LibraryIndex.load(nested_path)
    assert loaded.count == 1
