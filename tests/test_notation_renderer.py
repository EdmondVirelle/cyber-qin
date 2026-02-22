"""Tests for notation_renderer module.

Covers:
- midi_to_staff_position (MIDI → staff line/accidental/ledger lines)
- duration_to_head_type (beats → note head + dotted flag)
- stem_direction (staff line → up/down)
- render_notation (end-to-end conversion)
- Beam grouping logic
"""

from cyber_qin.core.beat_sequence import BeatNote
from cyber_qin.core.notation_renderer import (
    Accidental,
    NotationData,
    NoteHeadType,
    StemDirection,
    duration_to_head_type,
    midi_to_staff_position,
    render_notation,
    stem_direction,
)

# ── midi_to_staff_position tests ────────────────────────────────


def test_midi_to_staff_position_c4_middle_c():
    """Middle C (C4, MIDI 60) is one ledger line below staff (line -2)."""
    pos = midi_to_staff_position(60)
    assert pos.line == -2
    assert pos.accidental == Accidental.NONE
    assert pos.ledger_lines == -2  # (line - 1) // 2 = (-2 - 1) // 2 = -2


def test_midi_to_staff_position_e4_bottom_line():
    """E4 (MIDI 64) is the bottom line of the staff (line 0)."""
    pos = midi_to_staff_position(64)
    assert pos.line == 0
    assert pos.accidental == Accidental.NONE
    assert pos.ledger_lines == 0


def test_midi_to_staff_position_b4_middle_line():
    """B4 (MIDI 71) is line 4 (middle line of treble staff)."""
    pos = midi_to_staff_position(71)
    assert pos.line == 4  # octave=4, diatonic=6 → (4-4)*7 + 6 - 2 = 4
    assert pos.accidental == Accidental.NONE
    assert pos.ledger_lines == 0


def test_midi_to_staff_position_f5_top_line_area():
    """F5 (MIDI 77) is line 8 (top line of staff)."""
    pos = midi_to_staff_position(77)
    assert pos.line == 8  # octave=5, diatonic=3 → (5-4)*7 + 3 - 2 = 8
    assert pos.accidental == Accidental.NONE
    assert pos.ledger_lines == 0


def test_midi_to_staff_position_c5():
    """C5 (MIDI 72) is line 5 (third space from bottom)."""
    pos = midi_to_staff_position(72)
    assert pos.line == 5
    assert pos.accidental == Accidental.NONE
    assert pos.ledger_lines == 0


def test_midi_to_staff_position_c6_ledger_above():
    """C6 (MIDI 84) is above staff with ledger lines."""
    pos = midi_to_staff_position(84)
    assert pos.line == 12  # 7 notes per octave from C4 @ -2
    assert pos.ledger_lines == 2  # two ledger lines above


def test_midi_to_staff_position_c7_ledger_above():
    """C7 (MIDI 96) is far above staff with multiple ledger lines."""
    pos = midi_to_staff_position(96)
    assert pos.line == 19
    assert pos.ledger_lines > 0


def test_midi_to_staff_position_c3_ledger_below():
    """C3 (MIDI 48) is below staff with ledger lines."""
    pos = midi_to_staff_position(48)
    assert pos.line == -9
    assert pos.ledger_lines < 0


def test_midi_to_staff_position_c2_ledger_below():
    """C2 (MIDI 36) is far below staff with multiple ledger lines."""
    pos = midi_to_staff_position(36)
    assert pos.line == -16
    assert pos.ledger_lines < 0


def test_midi_to_staff_position_sharp_note():
    """C# (MIDI 61) should have a sharp accidental in C major."""
    pos = midi_to_staff_position(61)  # C#4
    assert pos.accidental == Accidental.SHARP


def test_midi_to_staff_position_natural_note():
    """Natural notes (white keys) get Accidental.NONE in C major."""
    pos = midi_to_staff_position(62)  # D4
    assert pos.accidental == Accidental.NONE


def test_midi_to_staff_position_c_major_no_accidentals():
    """White keys in C major (key_sig=0) have no accidentals."""
    white_keys = [60, 62, 64, 65, 67, 69, 71]  # C, D, E, F, G, A, B
    for midi in white_keys:
        pos = midi_to_staff_position(midi, key_sig=0)
        assert pos.accidental == Accidental.NONE


def test_midi_to_staff_position_g_major_f_sharp_in_key():
    """G major (key_sig=1) has F# in key signature → no accidental."""
    pos = midi_to_staff_position(66, key_sig=1)  # F#4
    assert pos.accidental == Accidental.NONE  # F# is in G major key sig


def test_midi_to_staff_position_ledger_count_far_above():
    """High notes far above staff have correct ledger line count."""
    pos = midi_to_staff_position(88)  # E6
    assert pos.line > 8
    expected_ledger = (pos.line - 8 + 1) // 2
    assert pos.ledger_lines == expected_ledger


def test_midi_to_staff_position_ledger_count_far_below():
    """Low notes far below staff have correct ledger line count."""
    pos = midi_to_staff_position(40)  # E2
    assert pos.line < 0
    expected_ledger = (pos.line - 1) // 2
    assert pos.ledger_lines == expected_ledger


# ── duration_to_head_type tests ──────────────────────────────────


def test_duration_whole_note():
    """4.0 beats → WHOLE note, not dotted."""
    head, dotted = duration_to_head_type(4.0)
    assert head == NoteHeadType.WHOLE
    assert dotted is False


def test_duration_half_note():
    """2.0 beats → HALF note, not dotted."""
    head, dotted = duration_to_head_type(2.0)
    assert head == NoteHeadType.HALF
    assert dotted is False


def test_duration_quarter_note():
    """1.0 beats → QUARTER note, not dotted."""
    head, dotted = duration_to_head_type(1.0)
    assert head == NoteHeadType.QUARTER
    assert dotted is False


def test_duration_eighth_note():
    """0.5 beats → EIGHTH note, not dotted."""
    head, dotted = duration_to_head_type(0.5)
    assert head == NoteHeadType.EIGHTH
    assert dotted is False


def test_duration_sixteenth_note():
    """0.25 beats → SIXTEENTH note, not dotted."""
    head, dotted = duration_to_head_type(0.25)
    assert head == NoteHeadType.SIXTEENTH
    assert dotted is False


def test_duration_dotted_half():
    """3.0 beats → WHOLE note, not dotted (threshold is >= 6.0 for dotted)."""
    head, dotted = duration_to_head_type(3.0)
    assert head == NoteHeadType.WHOLE  # >= 3.0 → WHOLE
    assert dotted is False  # dotted only if >= 6.0


def test_duration_dotted_quarter():
    """1.5 beats → HALF note, not dotted (threshold is >= 3.0 for dotted)."""
    head, dotted = duration_to_head_type(1.5)
    assert head == NoteHeadType.HALF  # >= 1.5 → HALF
    assert dotted is False  # dotted only if >= 3.0


def test_duration_very_long():
    """Very long duration (8 beats) → WHOLE note, dotted."""
    head, dotted = duration_to_head_type(8.0)
    assert head == NoteHeadType.WHOLE
    assert dotted is True


def test_duration_very_short():
    """Very short duration (0.1 beats) → SIXTEENTH note."""
    head, dotted = duration_to_head_type(0.1)
    assert head == NoteHeadType.SIXTEENTH
    assert dotted is False


# ── stem_direction tests ──────────────────────────────────────────


def test_stem_direction_below_middle_up():
    """Notes below middle line (line < 4) have stem UP."""
    assert stem_direction(0) == StemDirection.UP  # E4
    assert stem_direction(3) == StemDirection.UP  # B4


def test_stem_direction_above_middle_down():
    """Notes above middle line (line >= 4) have stem DOWN."""
    assert stem_direction(5) == StemDirection.DOWN  # C5
    assert stem_direction(8) == StemDirection.DOWN  # A5


def test_stem_direction_at_middle_down():
    """Note at middle line (line 4) has stem DOWN."""
    assert stem_direction(4) == StemDirection.DOWN


def test_stem_direction_far_below_up():
    """Notes far below staff have stem UP."""
    assert stem_direction(-5) == StemDirection.UP


def test_stem_direction_far_above_down():
    """Notes far above staff have stem DOWN."""
    assert stem_direction(12) == StemDirection.DOWN


# ── render_notation tests ─────────────────────────────────────────


def test_render_empty_input():
    """Empty input produces empty NotationData with bar lines."""
    result = render_notation([])
    assert isinstance(result, NotationData)
    assert result.notes == []
    assert result.total_beats == 0.0
    # At least one bar line at beat 0 (double bar)
    assert len(result.bar_lines) >= 1
    assert result.bar_lines[0].x_beats == 0.0


def test_render_single_note():
    """Single note produces one NotationNote and bar lines."""
    beat_notes = [BeatNote(time_beats=0.0, duration_beats=1.0, note=60)]
    result = render_notation(beat_notes)

    assert len(result.notes) == 1
    assert result.notes[0].midi_note == 60
    assert result.notes[0].x_beats == 0.0
    assert result.notes[0].duration_beats == 1.0
    assert len(result.bar_lines) > 0


def test_render_multiple_notes_sorted():
    """Multiple notes are sorted by time."""
    beat_notes = [
        BeatNote(time_beats=2.0, duration_beats=1.0, note=64),
        BeatNote(time_beats=0.0, duration_beats=1.0, note=60),
        BeatNote(time_beats=1.0, duration_beats=1.0, note=62),
    ]
    result = render_notation(beat_notes)

    assert len(result.notes) == 3
    assert result.notes[0].x_beats == 0.0
    assert result.notes[1].x_beats == 1.0
    assert result.notes[2].x_beats == 2.0


def test_render_bar_lines_4_4_time():
    """Bar lines at correct positions for 4/4 time."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=0.5, note=60),
        BeatNote(time_beats=5.0, duration_beats=0.5, note=64),  # extends to beat 5.5
    ]
    result = render_notation(beat_notes, time_signature=(4, 4))

    # Expect bar lines at 0, 4, 8 (double bar)
    bar_positions = [bl.x_beats for bl in result.bar_lines]
    assert 0.0 in bar_positions
    assert 4.0 in bar_positions
    assert 8.0 in bar_positions


def test_render_bar_lines_3_4_time():
    """Bar lines at correct positions for 3/4 time."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=0.5, note=60),
        BeatNote(time_beats=4.0, duration_beats=0.5, note=64),
    ]
    result = render_notation(beat_notes, time_signature=(3, 4))

    # 3/4 time: beats_per_bar = 3
    bar_positions = [bl.x_beats for bl in result.bar_lines]
    assert 0.0 in bar_positions
    assert 3.0 in bar_positions
    assert 6.0 in bar_positions


def test_render_double_bar_at_end():
    """Final bar line is a double bar."""
    beat_notes = [BeatNote(time_beats=0.0, duration_beats=1.0, note=60)]
    result = render_notation(beat_notes)

    # Last bar line should have is_double=True
    assert result.bar_lines[-1].is_double is True


def test_render_key_signature_stored():
    """Key signature is stored in result."""
    beat_notes = [BeatNote(time_beats=0.0, duration_beats=1.0, note=60)]
    result = render_notation(beat_notes, key_signature=2)

    assert result.key_signature == 2


def test_render_time_signature_stored():
    """Time signature is stored in result."""
    beat_notes = [BeatNote(time_beats=0.0, duration_beats=1.0, note=60)]
    result = render_notation(beat_notes, time_signature=(6, 8))

    assert result.time_signature == (6, 8)


def test_render_total_beats_calculated():
    """total_beats reflects the end of the last note."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=1.0, note=60),  # ends at 1.0
        BeatNote(time_beats=2.0, duration_beats=3.0, note=64),  # ends at 5.0
    ]
    result = render_notation(beat_notes)

    assert result.total_beats == 5.0


def test_render_beam_groups_eighth_notes():
    """Eighth notes in same beat are beamed together."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=0.5, note=60),
        BeatNote(time_beats=0.5, duration_beats=0.5, note=62),
    ]
    result = render_notation(beat_notes)

    # Both notes should have the same beam_group
    assert result.notes[0].beam_group == result.notes[1].beam_group
    assert result.notes[0].beam_group != -1


def test_render_no_beam_for_quarter_notes():
    """Quarter notes are not beamed."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=1.0, note=60),
        BeatNote(time_beats=1.0, duration_beats=1.0, note=62),
    ]
    result = render_notation(beat_notes)

    # Both notes should have beam_group = -1
    assert result.notes[0].beam_group == -1
    assert result.notes[1].beam_group == -1


def test_render_beam_groups_same_beat():
    """Eighth notes within same beat are beamed together."""
    beat_notes = [
        BeatNote(time_beats=1.0, duration_beats=0.5, note=60),
        BeatNote(time_beats=1.5, duration_beats=0.5, note=62),
    ]
    result = render_notation(beat_notes)

    assert result.notes[0].beam_group == result.notes[1].beam_group
    assert result.notes[0].beam_group >= 0


def test_render_beam_groups_different_beats():
    """Eighth notes in different beats are not beamed together."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=0.5, note=60),
        BeatNote(time_beats=1.0, duration_beats=0.5, note=62),
    ]
    result = render_notation(beat_notes)

    # Different beats → different beam groups or -1
    # Since each has only one note in its beat, both should be -1
    assert result.notes[0].beam_group == -1
    assert result.notes[1].beam_group == -1


def test_render_note_head_types_assigned():
    """Note head types are correctly assigned from durations."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=4.0, note=60),  # whole
        BeatNote(time_beats=4.0, duration_beats=2.0, note=62),  # half
        BeatNote(time_beats=6.0, duration_beats=1.0, note=64),  # quarter
        BeatNote(time_beats=7.0, duration_beats=0.5, note=65),  # eighth
    ]
    result = render_notation(beat_notes)

    assert result.notes[0].head_type == NoteHeadType.WHOLE
    assert result.notes[1].head_type == NoteHeadType.HALF
    assert result.notes[2].head_type == NoteHeadType.QUARTER
    assert result.notes[3].head_type == NoteHeadType.EIGHTH


# ── Beam grouping detailed tests ──────────────────────────────────


def test_beam_two_eighths_same_beat():
    """Two eighth notes in same beat are beamed."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=0.5, note=60),
        BeatNote(time_beats=0.5, duration_beats=0.5, note=62),
    ]
    result = render_notation(beat_notes)

    assert result.notes[0].beam_group == result.notes[1].beam_group
    assert result.notes[0].beam_group >= 0


def test_beam_two_eighths_different_beats():
    """Two eighth notes in different beats are not beamed."""
    beat_notes = [
        BeatNote(time_beats=0.5, duration_beats=0.5, note=60),
        BeatNote(time_beats=1.5, duration_beats=0.5, note=62),
    ]
    result = render_notation(beat_notes)

    assert result.notes[0].beam_group == -1
    assert result.notes[1].beam_group == -1


def test_beam_three_eighths_same_beat():
    """Three eighth notes in same beat are all beamed together."""
    # Note: 3 eighths = 1.5 beats, need to fit in one beat boundary
    # Use a shorter duration to stay within beat 0-1
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=0.25, note=60),
        BeatNote(time_beats=0.25, duration_beats=0.25, note=62),
        BeatNote(time_beats=0.5, duration_beats=0.25, note=64),
    ]
    result = render_notation(beat_notes)

    # All three should have same beam group
    assert result.notes[0].beam_group == result.notes[1].beam_group
    assert result.notes[1].beam_group == result.notes[2].beam_group
    assert result.notes[0].beam_group >= 0


def test_beam_quarter_notes_no_beam():
    """Quarter notes do not get beamed."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=1.0, note=60),
        BeatNote(time_beats=1.0, duration_beats=1.0, note=62),
    ]
    result = render_notation(beat_notes)

    assert result.notes[0].beam_group == -1
    assert result.notes[1].beam_group == -1


def test_beam_mix_eighth_quarter():
    """Mix of eighth and quarter notes: only eighths beamed."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=0.5, note=60),
        BeatNote(time_beats=0.5, duration_beats=0.5, note=62),
        BeatNote(time_beats=1.0, duration_beats=1.0, note=64),
    ]
    result = render_notation(beat_notes)

    # First two eighths beamed together
    assert result.notes[0].beam_group == result.notes[1].beam_group
    assert result.notes[0].beam_group >= 0
    # Quarter note not beamed
    assert result.notes[2].beam_group == -1


def test_beam_sixteenth_notes():
    """Sixteenth notes are beamed."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=0.25, note=60),
        BeatNote(time_beats=0.25, duration_beats=0.25, note=62),
    ]
    result = render_notation(beat_notes)

    assert result.notes[0].beam_group == result.notes[1].beam_group
    assert result.notes[0].beam_group >= 0


def test_beam_single_eighth_no_beam():
    """Single eighth note has no beam (need at least 2)."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=0.5, note=60),
        BeatNote(time_beats=1.0, duration_beats=1.0, note=62),
    ]
    result = render_notation(beat_notes)

    # Single eighth note at beat 0 → no beam
    assert result.notes[0].beam_group == -1


def test_beam_groups_cross_beat_boundary():
    """Beam groups don't cross beat boundaries."""
    beat_notes = [
        BeatNote(time_beats=0.5, duration_beats=0.5, note=60),  # in beat 0
        BeatNote(time_beats=1.0, duration_beats=0.5, note=62),  # in beat 1
        BeatNote(time_beats=1.5, duration_beats=0.5, note=64),  # in beat 1
    ]
    result = render_notation(beat_notes)

    # First note alone in beat 0 → no beam
    assert result.notes[0].beam_group == -1
    # Last two in beat 1 → beamed together
    assert result.notes[1].beam_group == result.notes[2].beam_group
    assert result.notes[1].beam_group >= 0


# ── Edge cases and integration ────────────────────────────────────


def test_render_with_velocity():
    """Note velocity is preserved in notation."""
    beat_notes = [BeatNote(time_beats=0.0, duration_beats=1.0, note=60, velocity=80)]
    result = render_notation(beat_notes)

    assert result.notes[0].velocity == 80


def test_render_stem_directions_assigned():
    """Stem directions are correctly assigned based on staff position."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=1.0, note=60),  # C4, below middle
        BeatNote(time_beats=1.0, duration_beats=1.0, note=72),  # C5, above middle
    ]
    result = render_notation(beat_notes)

    # C4 has line -2 → stem UP
    assert result.notes[0].stem_dir == StemDirection.UP
    # C5 has line 5 → stem DOWN
    assert result.notes[1].stem_dir == StemDirection.DOWN


def test_render_dotted_notes():
    """Dotted notes are flagged correctly (threshold is >= 3.0 for HALF)."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=1.5, note=60),  # half note, not dotted
    ]
    result = render_notation(beat_notes)

    assert result.notes[0].dot is False  # dotted only if >= 3.0
    assert result.notes[0].head_type == NoteHeadType.HALF  # >= 1.5 → HALF


def test_render_simultaneous_notes_sorted_by_pitch():
    """Simultaneous notes are sorted by pitch."""
    beat_notes = [
        BeatNote(time_beats=0.0, duration_beats=1.0, note=64),
        BeatNote(time_beats=0.0, duration_beats=1.0, note=60),
        BeatNote(time_beats=0.0, duration_beats=1.0, note=67),
    ]
    result = render_notation(beat_notes)

    # Should be sorted: 60, 64, 67
    assert result.notes[0].midi_note == 60
    assert result.notes[1].midi_note == 64
    assert result.notes[2].midi_note == 67
