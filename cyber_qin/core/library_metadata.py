"""Community library metadata and bundle (.cqlib) support.

Provides metadata tagging, search/filter, and ZIP-based bundle
import/export for sharing MIDI collections.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TrackMetadata:
    """Metadata for a single track in the library."""

    title: str = ""
    artist: str = ""
    game: str = ""
    difficulty: int = 0  # 0-5 stars
    tags: list[str] = field(default_factory=list)
    source_url: str = ""
    description: str = ""

    def matches(self, query: str) -> bool:
        """Check if this metadata matches a search query (case-insensitive)."""
        q = query.lower()
        return (
            q in self.title.lower()
            or q in self.artist.lower()
            or q in self.game.lower()
            or q in self.description.lower()
            or any(q in tag.lower() for tag in self.tags)
        )

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "artist": self.artist,
            "game": self.game,
            "difficulty": self.difficulty,
            "tags": list(self.tags),
            "source_url": self.source_url,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TrackMetadata:
        return cls(
            title=data.get("title", ""),
            artist=data.get("artist", ""),
            game=data.get("game", ""),
            difficulty=data.get("difficulty", 0),
            tags=data.get("tags", []),
            source_url=data.get("source_url", ""),
            description=data.get("description", ""),
        )


@dataclass
class LibraryEntry:
    """A single entry in the library index."""

    file_path: str  # relative or absolute path to the MIDI file
    metadata: TrackMetadata = field(default_factory=TrackMetadata)

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> LibraryEntry:
        return cls(
            file_path=data.get("file_path", ""),
            metadata=TrackMetadata.from_dict(data.get("metadata", {})),
        )


class LibraryIndex:
    """In-memory index of library entries with search and filter."""

    def __init__(self) -> None:
        self._entries: list[LibraryEntry] = []

    @property
    def entries(self) -> list[LibraryEntry]:
        return list(self._entries)

    @property
    def count(self) -> int:
        return len(self._entries)

    def add(self, entry: LibraryEntry) -> None:
        self._entries.append(entry)

    def remove(self, file_path: str) -> bool:
        """Remove entry by file path. Returns True if found and removed."""
        for i, e in enumerate(self._entries):
            if e.file_path == file_path:
                self._entries.pop(i)
                return True
        return False

    def get(self, file_path: str) -> LibraryEntry | None:
        """Get entry by file path."""
        for e in self._entries:
            if e.file_path == file_path:
                return e
        return None

    def search(self, query: str) -> list[LibraryEntry]:
        """Search entries by metadata text match."""
        if not query.strip():
            return list(self._entries)
        return [e for e in self._entries if e.metadata.matches(query)]

    def filter_by_game(self, game: str) -> list[LibraryEntry]:
        """Filter entries by game name."""
        return [e for e in self._entries if e.metadata.game.lower() == game.lower()]

    def filter_by_difficulty(self, min_diff: int = 0, max_diff: int = 5) -> list[LibraryEntry]:
        """Filter entries by difficulty range."""
        return [e for e in self._entries if min_diff <= e.metadata.difficulty <= max_diff]

    def filter_by_tag(self, tag: str) -> list[LibraryEntry]:
        """Filter entries by tag."""
        tag_lower = tag.lower()
        return [e for e in self._entries if any(t.lower() == tag_lower for t in e.metadata.tags)]

    def all_games(self) -> list[str]:
        """Return sorted list of unique game names."""
        games = {e.metadata.game for e in self._entries if e.metadata.game}
        return sorted(games)

    def all_tags(self) -> list[str]:
        """Return sorted list of unique tags."""
        tags: set[str] = set()
        for e in self._entries:
            tags.update(e.metadata.tags)
        return sorted(tags)

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "entries": [e.to_dict() for e in self._entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> LibraryIndex:
        index = cls()
        for ed in data.get("entries", []):
            index.add(LibraryEntry.from_dict(ed))
        return index

    def save(self, path: str | Path) -> None:
        """Save index to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> LibraryIndex:
        """Load index from JSON file."""
        path = Path(path)
        if not path.exists():
            return cls()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


# ── Bundle (.cqlib) format ────────────────────────────────


BUNDLE_MANIFEST = "manifest.json"
BUNDLE_FILES_DIR = "files/"


def export_bundle(
    entries: list[LibraryEntry],
    output_path: str | Path,
    *,
    bundle_title: str = "",
    bundle_author: str = "",
) -> Path:
    """Export library entries as a .cqlib bundle (ZIP with manifest).

    Parameters
    ----------
    entries : list[LibraryEntry]
        Entries to include.
    output_path : str | Path
        Output .cqlib file path.
    bundle_title : str
        Title for the bundle.
    bundle_author : str
        Author of the bundle.

    Returns
    -------
    Path
        The output file path.
    """
    output_path = Path(output_path)

    manifest = {
        "version": 1,
        "title": bundle_title,
        "author": bundle_author,
        "entries": [],
    }

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in entries:
            src = Path(entry.file_path)
            if not src.exists():
                continue

            # Store file in files/ directory
            arc_name = BUNDLE_FILES_DIR + src.name
            zf.write(src, arc_name)

            manifest["entries"].append({
                "filename": src.name,
                "metadata": entry.metadata.to_dict(),
            })

        # Write manifest
        zf.writestr(BUNDLE_MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))

    return output_path


def import_bundle(
    bundle_path: str | Path,
    extract_dir: str | Path,
) -> list[LibraryEntry]:
    """Import a .cqlib bundle, extracting files and returning entries.

    Parameters
    ----------
    bundle_path : str | Path
        Path to the .cqlib file.
    extract_dir : str | Path
        Directory to extract MIDI files into.

    Returns
    -------
    list[LibraryEntry]
        Imported entries with updated file paths.
    """
    bundle_path = Path(bundle_path)
    extract_dir = Path(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    entries: list[LibraryEntry] = []

    with zipfile.ZipFile(bundle_path, "r") as zf:
        # Read manifest
        try:
            manifest_data = json.loads(zf.read(BUNDLE_MANIFEST))
        except (KeyError, json.JSONDecodeError):
            return entries

        for entry_data in manifest_data.get("entries", []):
            filename = entry_data.get("filename", "")
            arc_name = BUNDLE_FILES_DIR + filename
            metadata = TrackMetadata.from_dict(entry_data.get("metadata", {}))

            # Extract file
            if arc_name in zf.namelist():
                target = extract_dir / filename
                with zf.open(arc_name) as src, open(target, "wb") as dst:
                    dst.write(src.read())

                entries.append(LibraryEntry(
                    file_path=str(target),
                    metadata=metadata,
                ))

    return entries
