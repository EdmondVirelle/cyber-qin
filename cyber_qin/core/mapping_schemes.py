"""Mapping scheme definitions and registry for multi-game key layout support."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import SCAN, Modifier
from .key_mapper import KeyMapping, _km


@dataclass(frozen=True)
class MappingScheme:
    """A complete key mapping scheme for a specific game/layout."""

    id: str                         # "wwm_36", "ff14_32", ...
    name: str                       # "燕雲十六聲 36鍵"
    game: str                       # "燕雲十六聲" or "通用"
    key_count: int                  # 24, 32, 36, 48, 88
    midi_range: tuple[int, int]     # (min_note, max_note) inclusive
    mapping: dict[int, KeyMapping]  # MIDI note → KeyMapping
    description: str
    rows: int                       # display rows
    keys_per_row: int               # keys per row


# ── Scheme builders ──────────────────────────────────────────


def _build_wwm_36() -> MappingScheme:
    """燕雲十六聲 36鍵 — the original scheme."""
    from .key_mapper import _BASE_MAP

    return MappingScheme(
        id="wwm_36",
        name="燕雲十六聲 36鍵",
        game="燕雲十六聲",
        key_count=36,
        midi_range=(48, 83),
        mapping=dict(_BASE_MAP),
        description="3×12 佈局：ZXC / ASD / QWE 行，Shift/Ctrl 修飾升降號",
        rows=3,
        keys_per_row=12,
    )


def _build_ff14_32() -> MappingScheme:
    """FF14 32鍵 — 4 rows of 8 keys."""
    m: dict[int, KeyMapping] = {}
    # Row 1 (low): A S D F G H J K — MIDI 48-55
    row1_keys = ["A", "S", "D", "F", "G", "H", "J", "K"]
    for i, key in enumerate(row1_keys):
        m[48 + i] = _km(key)

    # Row 2: Q W E R T Y U I — MIDI 56-63
    row2_keys = ["Q", "W", "E", "R", "T", "Y", "U", "I"]
    for i, key in enumerate(row2_keys):
        m[56 + i] = _km(key)

    # Row 3: 1 2 3 4 5 6 7 8 — MIDI 64-71
    row3_keys = ["1", "2", "3", "4", "5", "6", "7", "8"]
    for i, key in enumerate(row3_keys):
        m[64 + i] = _km(key)

    # Row 4: Ctrl+1 through Ctrl+8 — MIDI 72-79
    for i in range(8):
        key = str(i + 1)
        m[72 + i] = _km(key, Modifier.CTRL)

    return MappingScheme(
        id="ff14_32",
        name="FF14 32鍵",
        game="FF14",
        key_count=32,
        midi_range=(48, 79),
        mapping=m,
        description="4×8 佈局：ASDFGHJK / QWERTYUI / 12345678 / Ctrl+1~8",
        rows=4,
        keys_per_row=8,
    )


def _build_generic_24() -> MappingScheme:
    """通用 24鍵 — 2 rows of 12 keys."""
    m: dict[int, KeyMapping] = {}
    # Row 1 (low octave, MIDI 48-59): Z X C V B N M + Shift/Ctrl variants
    # Same pattern as WWM low octave
    low_map = [
        ("Z", Modifier.NONE),     # C
        ("Z", Modifier.SHIFT),    # C#
        ("X", Modifier.NONE),     # D
        ("C", Modifier.CTRL),     # Eb
        ("C", Modifier.NONE),     # E
        ("V", Modifier.NONE),     # F
        ("V", Modifier.SHIFT),    # F#
        ("B", Modifier.NONE),     # G
        ("B", Modifier.SHIFT),    # G#
        ("N", Modifier.NONE),     # A
        ("M", Modifier.CTRL),     # Bb
        ("M", Modifier.NONE),     # B
    ]
    for i, (key, mod) in enumerate(low_map):
        m[48 + i] = _km(key, mod)

    # Row 2 (high octave, MIDI 60-71): Q W E R T Y U + Shift/Ctrl variants
    high_map = [
        ("Q", Modifier.NONE),     # C
        ("Q", Modifier.SHIFT),    # C#
        ("W", Modifier.NONE),     # D
        ("E", Modifier.CTRL),     # Eb
        ("E", Modifier.NONE),     # E
        ("R", Modifier.NONE),     # F
        ("R", Modifier.SHIFT),    # F#
        ("T", Modifier.NONE),     # G
        ("T", Modifier.SHIFT),    # G#
        ("Y", Modifier.NONE),     # A
        ("U", Modifier.CTRL),     # Bb
        ("U", Modifier.NONE),     # B
    ]
    for i, (key, mod) in enumerate(high_map):
        m[60 + i] = _km(key, mod)

    return MappingScheme(
        id="generic_24",
        name="通用 24鍵",
        game="通用",
        key_count=24,
        midi_range=(48, 71),
        mapping=m,
        description="2×12 佈局：ZXC 行 + QWE 行，Shift/Ctrl 修飾升降號",
        rows=2,
        keys_per_row=12,
    )


def _build_generic_48() -> MappingScheme:
    """通用 48鍵 — 4 rows of 12 keys."""
    m: dict[int, KeyMapping] = {}

    # Row 1 (MIDI 36-47): 1 2 3 4 5 6 7 8 9 0 - = (number row)
    num_keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "MINUS", "EQUALS"]
    num_labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="]
    for i, key in enumerate(num_keys):
        sc = SCAN[key]
        m[36 + i] = KeyMapping(scan_code=sc, modifier=Modifier.NONE, label=num_labels[i])

    # Row 2 (MIDI 48-59): Z X C V B N M + Shift/Ctrl (same as wwm_36 low octave)
    low_map = [
        ("Z", Modifier.NONE), ("Z", Modifier.SHIFT), ("X", Modifier.NONE),
        ("C", Modifier.CTRL), ("C", Modifier.NONE), ("V", Modifier.NONE),
        ("V", Modifier.SHIFT), ("B", Modifier.NONE), ("B", Modifier.SHIFT),
        ("N", Modifier.NONE), ("M", Modifier.CTRL), ("M", Modifier.NONE),
    ]
    for i, (key, mod) in enumerate(low_map):
        m[48 + i] = _km(key, mod)

    # Row 3 (MIDI 60-71): A S D F G H J + Shift/Ctrl (same as wwm_36 mid octave)
    mid_map = [
        ("A", Modifier.NONE), ("A", Modifier.SHIFT), ("S", Modifier.NONE),
        ("D", Modifier.CTRL), ("D", Modifier.NONE), ("F", Modifier.NONE),
        ("F", Modifier.SHIFT), ("G", Modifier.NONE), ("G", Modifier.SHIFT),
        ("H", Modifier.NONE), ("J", Modifier.CTRL), ("J", Modifier.NONE),
    ]
    for i, (key, mod) in enumerate(mid_map):
        m[60 + i] = _km(key, mod)

    # Row 4 (MIDI 72-83): Q W E R T Y U + Shift/Ctrl (same as wwm_36 high octave)
    high_map = [
        ("Q", Modifier.NONE), ("Q", Modifier.SHIFT), ("W", Modifier.NONE),
        ("E", Modifier.CTRL), ("E", Modifier.NONE), ("R", Modifier.NONE),
        ("R", Modifier.SHIFT), ("T", Modifier.NONE), ("T", Modifier.SHIFT),
        ("Y", Modifier.NONE), ("U", Modifier.CTRL), ("U", Modifier.NONE),
    ]
    for i, (key, mod) in enumerate(high_map):
        m[72 + i] = _km(key, mod)

    return MappingScheme(
        id="generic_48",
        name="通用 48鍵",
        game="通用",
        key_count=48,
        midi_range=(36, 83),
        mapping=m,
        description="4×12 佈局：數字行 / ZXC / ASD / QWE，4 個八度",
        rows=4,
        keys_per_row=12,
    )


def _build_generic_88() -> MappingScheme:
    """通用 88鍵 — 8 rows of 11 keys (covering full piano range)."""
    m: dict[int, KeyMapping] = {}

    # 88 keys: MIDI 21 (A0) to 108 (C8)
    # We use layered modifier combinations across keyboard rows.
    # 8 rows × 11 keys = 88

    layers = [
        Modifier.NONE,     # Row 1: plain
        Modifier.SHIFT,    # Row 2: Shift
        Modifier.CTRL,     # Row 3: Ctrl
    ]

    row_key_sets = [
        # Rows 1-3: ZXC row keys
        ["Z", "X", "C", "V", "B", "N", "M", "A", "S", "D", "F"],
        # Rows 4-6: QWE/ASD row keys
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "K"],
        # Rows 7-8: number row keys
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "MINUS"],
    ]

    midi = 21  # A0
    for group_idx, keys in enumerate(row_key_sets):
        for mod in layers:
            if midi > 108:
                break
            for key in keys:
                if midi > 108:
                    break
                m[midi] = _km(key, mod)
                midi += 1

    # Fill remaining with EQUALS key variants if needed
    remaining_keys = ["EQUALS"]
    remaining_mods = [Modifier.NONE, Modifier.SHIFT]
    for mod in remaining_mods:
        for key in remaining_keys:
            if midi > 108:
                break
            m[midi] = _km(key, mod)
            midi += 1

    return MappingScheme(
        id="generic_88",
        name="通用 88鍵",
        game="通用",
        key_count=88,
        midi_range=(21, 108),
        mapping=m,
        description="8×11 佈局：多層 Shift/Ctrl 組合，完整鋼琴範圍",
        rows=8,
        keys_per_row=11,
    )


# ── Registry ─────────────────────────────────────────────────

_SCHEMES: dict[str, MappingScheme] = {}

_DEFAULT_SCHEME_ID = "wwm_36"


def _init_registry() -> None:
    """Populate the scheme registry (called once on first access)."""
    if _SCHEMES:
        return
    for builder in [
        _build_wwm_36,
        _build_ff14_32,
        _build_generic_24,
        _build_generic_48,
        _build_generic_88,
    ]:
        scheme = builder()
        _SCHEMES[scheme.id] = scheme


def get_scheme(scheme_id: str) -> MappingScheme:
    """Return a scheme by ID. Raises KeyError if not found."""
    _init_registry()
    return _SCHEMES[scheme_id]


def list_schemes() -> list[MappingScheme]:
    """Return all registered schemes in display order."""
    _init_registry()
    return list(_SCHEMES.values())


def default_scheme_id() -> str:
    """Return the default scheme ID."""
    return _DEFAULT_SCHEME_ID
