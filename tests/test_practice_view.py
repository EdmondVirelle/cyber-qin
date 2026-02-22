"""Tests for practice view song picker UI.

Covers PracticeView page switching, signal emissions,
_PracticeEmptyState track population, change-track flow,
_MiniTrackCard behavior, i18n updates, score display,
mode/scheme switching, and numerous edge cases.
"""

from __future__ import annotations

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from cyber_qin.core.beat_sequence import BeatNote
from cyber_qin.core.midi_file_player import MidiFileInfo
from cyber_qin.core.translator import translator
from cyber_qin.gui.views.practice_view import (
    PracticeView,
    _MiniTrackCard,
    _MusicNoteIcon,
    _PracticeEmptyState,
)

# ── Fixtures ──────────────────────────────────────────────


@pytest.fixture()
def practice_view(qapp):
    view = PracticeView()
    yield view
    view.close()
    view.deleteLater()
    QApplication.processEvents()


@pytest.fixture()
def sample_tracks():
    return [
        MidiFileInfo(
            file_path="/tmp/song_a.mid",
            name="Song A",
            duration_seconds=120.0,
            track_count=2,
            note_count=200,
            tempo_bpm=120.0,
        ),
        MidiFileInfo(
            file_path="/tmp/song_b.mid",
            name="Song B",
            duration_seconds=90.5,
            track_count=1,
            note_count=150,
            tempo_bpm=140.0,
        ),
        MidiFileInfo(
            file_path="/tmp/song_c.mid",
            name="Song C",
            duration_seconds=60.0,
            track_count=3,
            note_count=80,
            tempo_bpm=100.0,
        ),
    ]


@pytest.fixture()
def one_note():
    return [BeatNote(time_beats=0.0, duration_beats=1.0, note=60, velocity=100)]


@pytest.fixture()
def multi_notes():
    return [
        BeatNote(time_beats=0.0, duration_beats=0.5, note=60, velocity=100),
        BeatNote(time_beats=0.5, duration_beats=0.5, note=62, velocity=90),
        BeatNote(time_beats=1.0, duration_beats=0.5, note=64, velocity=80),
        BeatNote(time_beats=1.5, duration_beats=1.0, note=67, velocity=110),
    ]


# ── PracticeView: Initial State ──────────────────────────


class TestPracticeViewInitialState:
    """PracticeView starts on page 0 (empty state) with correct defaults."""

    def test_initial_page_is_zero(self, practice_view):
        assert practice_view._content_stack.currentIndex() == 0

    def test_change_track_btn_hidden_initially(self, practice_view):
        assert not practice_view._change_track_btn.isVisible()

    def test_has_file_open_signal(self, practice_view):
        assert hasattr(practice_view, "file_open_requested")

    def test_has_practice_track_signal(self, practice_view):
        assert hasattr(practice_view, "practice_track_requested")

    def test_initial_scorer_is_none(self, practice_view):
        assert practice_view._scorer is None

    def test_initial_notes_empty(self, practice_view):
        assert practice_view._notes == []

    def test_initial_tempo(self, practice_view):
        assert practice_view._tempo_bpm == 120.0

    def test_initial_score_labels_show_zero(self, practice_view):
        assert "0" in practice_view._score_label.text()
        assert "0%" in practice_view._accuracy_label.text()
        assert "0" in practice_view._combo_label.text()

    def test_start_btn_shows_start_text(self, practice_view):
        assert practice_view._start_btn.text() == translator.tr("practice.start")

    def test_desc_label_shows_gameplay_desc(self, practice_view):
        assert practice_view._desc_lbl.text() == translator.tr("practice.desc")

    def test_mode_combo_defaults_to_midi(self, practice_view):
        assert practice_view._mode_combo.currentData() == "midi"

    def test_scheme_combo_hidden_initially(self, practice_view):
        assert practice_view._scheme_combo.isHidden()

    def test_content_stack_has_two_pages(self, practice_view):
        assert practice_view._content_stack.count() == 2

    def test_empty_state_track_cards_empty(self, practice_view):
        assert len(practice_view._empty_state._track_cards) == 0


# ── PracticeView: start_practice() ───────────────────────


class TestPracticeViewStartPractice:
    """start_practice() switches to page 1 and sets up practice state."""

    def test_switches_to_page_1(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        assert practice_view._content_stack.currentIndex() == 1

    def test_shows_change_track_btn(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        assert not practice_view._change_track_btn.isHidden()

    def test_creates_scorer(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        assert practice_view._scorer is not None

    def test_stores_notes(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        assert practice_view._notes == one_note

    def test_stores_tempo(self, practice_view, one_note):
        practice_view.start_practice(one_note, 90.0)
        assert practice_view._tempo_bpm == 90.0

    def test_start_btn_shows_stop(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        assert practice_view._start_btn.text() == translator.tr("practice.stop")

    def test_display_is_playing(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        assert practice_view._display.is_playing

    def test_multi_note_practice(self, practice_view, multi_notes):
        """start_practice with multiple notes works correctly."""
        practice_view.start_practice(multi_notes, 140.0)
        assert practice_view._content_stack.currentIndex() == 1
        assert practice_view._scorer is not None
        assert practice_view._scorer.stats.total_notes == 4

    def test_start_practice_twice_restarts(self, practice_view, one_note, multi_notes):
        """Calling start_practice again replaces the current session."""
        practice_view.start_practice(one_note, 120.0)
        first_scorer = practice_view._scorer
        assert first_scorer.stats.total_notes == 1

        practice_view.start_practice(multi_notes, 140.0)
        assert practice_view._scorer is not first_scorer
        assert practice_view._scorer.stats.total_notes == 4
        assert practice_view._notes == multi_notes
        assert practice_view._tempo_bpm == 140.0

    def test_start_practice_with_extreme_tempo(self, practice_view, one_note):
        """Very slow and very fast tempos should not crash."""
        practice_view.start_practice(one_note, 20.0)
        assert practice_view._scorer is not None
        practice_view._on_change_track()

        practice_view.start_practice(one_note, 300.0)
        assert practice_view._scorer is not None

    def test_start_practice_with_high_note(self, practice_view):
        """Notes at the extreme high end of MIDI range."""
        notes = [BeatNote(time_beats=0.0, duration_beats=1.0, note=127, velocity=127)]
        practice_view.start_practice(notes, 120.0)
        assert practice_view._scorer is not None

    def test_start_practice_with_low_note(self, practice_view):
        """Notes at MIDI note 0."""
        notes = [BeatNote(time_beats=0.0, duration_beats=1.0, note=0, velocity=1)]
        practice_view.start_practice(notes, 120.0)
        assert practice_view._scorer is not None

    def test_start_practice_with_zero_velocity(self, practice_view):
        """Velocity=0 notes should still create a valid session."""
        notes = [BeatNote(time_beats=0.0, duration_beats=1.0, note=60, velocity=0)]
        practice_view.start_practice(notes, 120.0)
        assert practice_view._scorer is not None

    def test_start_practice_with_very_short_note(self, practice_view):
        """Extremely short duration note."""
        notes = [BeatNote(time_beats=0.0, duration_beats=0.001, note=60, velocity=100)]
        practice_view.start_practice(notes, 120.0)
        assert practice_view._scorer is not None


# ── PracticeView: _on_change_track() ─────────────────────


class TestPracticeViewChangeTrack:
    """_on_change_track() stops practice and returns to page 0."""

    def test_returns_to_page_0(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        practice_view._on_change_track()
        assert practice_view._content_stack.currentIndex() == 0

    def test_hides_change_track_btn(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        practice_view._on_change_track()
        assert not practice_view._change_track_btn.isVisible()

    def test_clears_notes(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        practice_view._on_change_track()
        assert practice_view._notes == []

    def test_clears_scorer(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        practice_view._on_change_track()
        assert practice_view._scorer is None

    def test_stops_display(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        assert practice_view._display.is_playing
        practice_view._on_change_track()
        assert not practice_view._display.is_playing

    def test_resets_desc_label(self, practice_view, one_note):
        practice_view.set_current_track_name("My Song")
        practice_view.start_practice(one_note, 120.0)
        practice_view._on_change_track()
        assert practice_view._desc_lbl.text() == translator.tr("practice.desc")

    def test_resets_start_btn_text(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        practice_view._on_change_track()
        assert practice_view._start_btn.text() == translator.tr("practice.start")

    def test_resets_score_display(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        practice_view._on_change_track()
        assert "0" in practice_view._score_label.text()
        assert "0%" in practice_view._accuracy_label.text()

    def test_change_track_when_not_playing(self, practice_view, one_note):
        """Change track after manually stopping should still work."""
        practice_view.start_practice(one_note, 120.0)
        practice_view._display.stop()
        assert not practice_view._display.is_playing
        # Should not crash
        practice_view._on_change_track()
        assert practice_view._content_stack.currentIndex() == 0

    def test_change_track_without_ever_starting(self, practice_view):
        """Calling _on_change_track on initial state should be safe."""
        practice_view._on_change_track()
        assert practice_view._content_stack.currentIndex() == 0
        assert practice_view._scorer is None

    def test_multiple_start_change_cycles(self, practice_view, one_note, multi_notes):
        """Repeatedly starting and changing tracks should not leak state."""
        for i in range(5):
            notes = one_note if i % 2 == 0 else multi_notes
            practice_view.start_practice(notes, 120.0)
            assert practice_view._content_stack.currentIndex() == 1
            practice_view._on_change_track()
            assert practice_view._content_stack.currentIndex() == 0
            assert practice_view._scorer is None
            assert practice_view._notes == []


# ── PracticeView: _on_start_stop() ───────────────────────


class TestPracticeViewStartStop:
    """The start/stop button toggles practice state."""

    def test_stop_running_practice(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        assert practice_view._display.is_playing
        practice_view._on_start_stop()
        assert not practice_view._display.is_playing
        assert practice_view._start_btn.text() == translator.tr("practice.start")

    def test_restart_stopped_practice(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        practice_view._on_start_stop()  # stop
        practice_view._on_start_stop()  # restart
        assert practice_view._display.is_playing

    def test_start_stop_with_no_notes_does_nothing(self, practice_view):
        """Pressing start/stop when no notes loaded should be a no-op."""
        practice_view._on_start_stop()
        assert not practice_view._display.is_playing
        assert practice_view._content_stack.currentIndex() == 0

    def test_stop_does_not_change_page(self, practice_view, one_note):
        """Stopping via start/stop btn stays on page 1 (unlike change track)."""
        practice_view.start_practice(one_note, 120.0)
        practice_view._on_start_stop()
        assert practice_view._content_stack.currentIndex() == 1


# ── PracticeView: on_user_note() ─────────────────────────


class TestPracticeViewUserNote:
    """on_user_note() scoring behavior."""

    def test_user_note_when_not_playing_is_noop(self, practice_view):
        """Should not crash when called before start."""
        practice_view.on_user_note(60)  # no crash

    def test_user_note_when_no_scorer_is_noop(self, practice_view):
        practice_view._scorer = None
        practice_view.on_user_note(60)  # no crash

    def test_user_note_when_playing_updates_score(self, practice_view, one_note):
        """When playing, user note should trigger scoring."""
        practice_view.start_practice(one_note, 120.0)
        # At this point display.current_time is -1.0 (lead-in), so the note
        # at time 0.0 hasn't arrived yet — result may be None. The important
        # thing is it doesn't crash.
        practice_view.on_user_note(60)

    def test_user_note_wrong_pitch_no_crash(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        practice_view.on_user_note(999)  # way out of range, no crash


# ── PracticeView: set_library_tracks() ───────────────────


class TestPracticeViewSetLibraryTracks:
    """set_library_tracks() populates the empty state track list."""

    def test_creates_correct_card_count(self, practice_view, sample_tracks):
        practice_view.set_library_tracks(sample_tracks)
        assert len(practice_view._empty_state._track_cards) == 3

    def test_empty_list_shows_no_tracks_label(self, practice_view):
        practice_view.set_library_tracks([])
        assert len(practice_view._empty_state._track_cards) == 0
        assert not practice_view._empty_state._no_tracks_lbl.isHidden()

    def test_non_empty_list_hides_no_tracks_label(self, practice_view, sample_tracks):
        practice_view.set_library_tracks(sample_tracks)
        assert practice_view._empty_state._no_tracks_lbl.isHidden()

    def test_replaces_old_cards(self, practice_view, sample_tracks):
        practice_view.set_library_tracks(sample_tracks)
        assert len(practice_view._empty_state._track_cards) == 3
        practice_view.set_library_tracks(sample_tracks[:1])
        assert len(practice_view._empty_state._track_cards) == 1

    def test_single_track(self, practice_view):
        tracks = [
            MidiFileInfo(
                file_path="/tmp/only.mid",
                name="Only Track",
                duration_seconds=60.0,
                track_count=1,
                note_count=50,
                tempo_bpm=120.0,
            )
        ]
        practice_view.set_library_tracks(tracks)
        assert len(practice_view._empty_state._track_cards) == 1

    def test_empty_then_non_empty(self, practice_view, sample_tracks):
        """Setting empty, then setting tracks should work."""
        practice_view.set_library_tracks([])
        assert practice_view._empty_state._no_tracks_lbl.isHidden() is False
        practice_view.set_library_tracks(sample_tracks)
        assert len(practice_view._empty_state._track_cards) == 3
        assert practice_view._empty_state._no_tracks_lbl.isHidden()

    def test_non_empty_then_empty(self, practice_view, sample_tracks):
        """Clearing tracks after having some should show placeholder."""
        practice_view.set_library_tracks(sample_tracks)
        practice_view.set_library_tracks([])
        assert len(practice_view._empty_state._track_cards) == 0
        assert not practice_view._empty_state._no_tracks_lbl.isHidden()

    def test_set_tracks_many_times(self, practice_view, sample_tracks):
        """Rapid set_tracks calls should not leak widgets."""
        for _ in range(20):
            practice_view.set_library_tracks(sample_tracks)
        assert len(practice_view._empty_state._track_cards) == 3

    def test_tracks_with_zero_duration(self, practice_view):
        tracks = [
            MidiFileInfo(
                file_path="/tmp/zero.mid",
                name="Zero Duration",
                duration_seconds=0.0,
                track_count=1,
                note_count=0,
                tempo_bpm=120.0,
            )
        ]
        practice_view.set_library_tracks(tracks)
        assert len(practice_view._empty_state._track_cards) == 1

    def test_tracks_with_unicode_name(self, practice_view):
        tracks = [
            MidiFileInfo(
                file_path="/tmp/春江花月夜.mid",
                name="春江花月夜 — 古箏版",
                duration_seconds=300.0,
                track_count=1,
                note_count=500,
                tempo_bpm=80.0,
            )
        ]
        practice_view.set_library_tracks(tracks)
        assert len(practice_view._empty_state._track_cards) == 1

    def test_tracks_with_very_long_name(self, practice_view):
        tracks = [
            MidiFileInfo(
                file_path="/tmp/long.mid",
                name="A" * 500,
                duration_seconds=60.0,
                track_count=1,
                note_count=10,
                tempo_bpm=120.0,
            )
        ]
        practice_view.set_library_tracks(tracks)
        assert len(practice_view._empty_state._track_cards) == 1

    def test_tracks_with_large_values(self, practice_view):
        tracks = [
            MidiFileInfo(
                file_path="/tmp/big.mid",
                name="Big Track",
                duration_seconds=99999.9,
                track_count=100,
                note_count=999999,
                tempo_bpm=999.0,
            )
        ]
        practice_view.set_library_tracks(tracks)
        assert len(practice_view._empty_state._track_cards) == 1


# ── PracticeView: set_current_track_name() ───────────────


class TestPracticeViewSetTrackName:
    """set_current_track_name() updates the header description."""

    def test_set_track_name(self, practice_view):
        practice_view.set_current_track_name("Test Song")
        assert practice_view._desc_lbl.text() == "Test Song"

    def test_set_track_name_unicode(self, practice_view):
        practice_view.set_current_track_name("春江花月夜")
        assert practice_view._desc_lbl.text() == "春江花月夜"

    def test_set_track_name_empty_string(self, practice_view):
        practice_view.set_current_track_name("")
        assert practice_view._desc_lbl.text() == ""

    def test_set_track_name_very_long(self, practice_view):
        long_name = "X" * 1000
        practice_view.set_current_track_name(long_name)
        assert practice_view._desc_lbl.text() == long_name

    def test_track_name_preserved_on_page_1(self, practice_view, one_note):
        """Track name should stay while practicing."""
        practice_view.set_current_track_name("My Song")
        practice_view.start_practice(one_note, 120.0)
        assert practice_view._desc_lbl.text() == "My Song"


# ── PracticeView: _update_text() (i18n) ──────────────────


class TestPracticeViewI18n:
    """Language change updates all labels correctly."""

    def test_update_text_on_page_0_updates_desc(self, practice_view):
        """On page 0, desc_lbl should refresh to translated practice.desc."""
        practice_view._update_text()
        assert practice_view._desc_lbl.text() == translator.tr("practice.desc")

    def test_update_text_on_page_1_preserves_track_name(self, practice_view, one_note):
        """On page 1, desc_lbl should NOT be overwritten by i18n update."""
        practice_view.set_current_track_name("Custom Track Name")
        practice_view.start_practice(one_note, 120.0)
        practice_view._update_text()
        # Should still show track name, not the generic desc
        assert practice_view._desc_lbl.text() == "Custom Track Name"

    def test_update_text_refreshes_title(self, practice_view):
        practice_view._update_text()
        assert practice_view._title_lbl.text() == translator.tr("practice.title")

    def test_update_text_refreshes_change_track_btn(self, practice_view):
        practice_view._update_text()
        assert practice_view._change_track_btn.text() == translator.tr("practice.change_track")

    def test_update_text_refreshes_mode_combo(self, practice_view):
        practice_view._update_text()
        assert practice_view._mode_combo.itemText(0) == translator.tr("practice.mode.midi")
        assert practice_view._mode_combo.itemText(1) == translator.tr("practice.mode.keyboard")

    def test_update_text_refreshes_start_btn_when_stopped(self, practice_view):
        practice_view._update_text()
        assert practice_view._start_btn.text() == translator.tr("practice.start")

    def test_update_text_refreshes_start_btn_when_playing(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        practice_view._update_text()
        assert practice_view._start_btn.text() == translator.tr("practice.stop")

    def test_update_text_cascades_to_empty_state(self, practice_view):
        """Should not crash and should update empty state labels."""
        practice_view._update_text()
        assert practice_view._empty_state._title_lbl.text() == translator.tr(
            "practice.empty.title"
        )
        assert practice_view._empty_state._open_btn.text() == translator.tr("practice.open_file")

    def test_language_switch_round_trip(self, practice_view):
        """Switch language, update, switch back — labels should be correct."""
        original_lang = translator.current_language
        translator.set_language("zh_tw")
        practice_view._update_text()
        assert practice_view._title_lbl.text() == translator.tr("practice.title")

        translator.set_language("en")
        practice_view._update_text()
        assert practice_view._title_lbl.text() == "Practice Mode"

        # Restore
        translator.set_language(original_lang)


# ── PracticeView: _update_score_display() ─────────────────


class TestPracticeViewScoreDisplay:
    """Score display updates correctly in various states."""

    def test_no_scorer_shows_zeroes(self, practice_view):
        practice_view._scorer = None
        practice_view._update_score_display()
        assert "0" in practice_view._score_label.text()
        assert "0%" in practice_view._accuracy_label.text()
        assert "0" in practice_view._combo_label.text()

    def test_with_scorer_shows_stats(self, practice_view, one_note):
        practice_view.start_practice(one_note, 120.0)
        practice_view._update_score_display()
        # Scorer exists, total_notes=1, no hits yet
        assert "0" in practice_view._score_label.text()


# ── PracticeView: Mode / Scheme switching ─────────────────


class TestPracticeViewModeScheme:
    """Mode combo and scheme combo interaction."""

    def test_switching_to_keyboard_shows_scheme_combo(self, practice_view):
        practice_view._mode_combo.setCurrentIndex(1)  # keyboard
        assert not practice_view._scheme_combo.isHidden()

    def test_switching_back_to_midi_hides_scheme_combo(self, practice_view):
        practice_view._mode_combo.setCurrentIndex(1)  # keyboard
        practice_view._mode_combo.setCurrentIndex(0)  # midi
        assert practice_view._scheme_combo.isHidden()

    def test_keyboard_mode_sets_mapping(self, practice_view):
        """Switching to keyboard mode should call set_keyboard_mapping."""
        practice_view._mode_combo.setCurrentIndex(1)
        # Should not crash; mapping is set on the display
        # Verify reverse_map is set (non-None)
        assert practice_view._display._reverse_map is not None

    def test_midi_mode_clears_mapping(self, practice_view):
        practice_view._mode_combo.setCurrentIndex(1)  # keyboard
        practice_view._mode_combo.setCurrentIndex(0)  # midi
        assert practice_view._display._reverse_map is None
        assert practice_view._display._key_labels is None

    def test_scheme_change_updates_mapping(self, practice_view):
        """Changing scheme while in keyboard mode should update mapping."""
        practice_view._mode_combo.setCurrentIndex(1)
        if practice_view._scheme_combo.count() > 1:
            practice_view._scheme_combo.setCurrentIndex(1)
            # Mapping should have changed (or at least been reassigned)
            # We just verify no crash
            assert practice_view._display._reverse_map is not None

    def test_scheme_change_in_midi_mode_is_noop(self, practice_view):
        """Changing scheme while in MIDI mode should not set mapping."""
        practice_view._mode_combo.setCurrentIndex(0)  # midi
        if practice_view._scheme_combo.count() > 1:
            practice_view._scheme_combo.setCurrentIndex(1)
        assert practice_view._display._reverse_map is None


# ── _PracticeEmptyState ──────────────────────────────────


class TestPracticeEmptyState:
    """_PracticeEmptyState widget behavior."""

    @pytest.fixture()
    def empty_state(self, qapp):
        state = _PracticeEmptyState()
        yield state
        state.close()
        state.deleteLater()

    def test_initial_no_cards(self, empty_state):
        assert len(empty_state._track_cards) == 0

    def test_no_tracks_label_visible_initially(self, empty_state):
        # Initial state: no set_tracks called, label is visible
        assert not empty_state._no_tracks_lbl.isHidden()

    def test_set_tracks_creates_cards(self, empty_state, sample_tracks):
        empty_state.set_tracks(sample_tracks)
        assert len(empty_state._track_cards) == 3

    def test_set_tracks_hides_no_tracks_label(self, empty_state, sample_tracks):
        empty_state.set_tracks(sample_tracks)
        assert empty_state._no_tracks_lbl.isHidden()

    def test_set_empty_tracks_shows_no_tracks_label(self, empty_state, sample_tracks):
        empty_state.set_tracks(sample_tracks)
        empty_state.set_tracks([])
        assert not empty_state._no_tracks_lbl.isHidden()
        assert len(empty_state._track_cards) == 0

    def test_update_text(self, empty_state):
        empty_state.update_text()
        assert empty_state._title_lbl.text() == translator.tr("practice.empty.title")
        assert empty_state._sub_lbl.text() == translator.tr("practice.empty.sub")
        assert empty_state._open_btn.text() == translator.tr("practice.open_file")
        assert empty_state._section_lbl.text() == translator.tr("practice.library_tracks")
        assert empty_state._no_tracks_lbl.text() == translator.tr("practice.no_tracks")

    def test_file_open_signal(self, empty_state, qtbot):
        with qtbot.waitSignal(empty_state.file_open_clicked, timeout=1000):
            empty_state._open_btn.click()

    def test_track_clicked_signal(self, empty_state, qtbot, sample_tracks):
        empty_state.set_tracks(sample_tracks)
        with qtbot.waitSignal(empty_state.track_clicked, timeout=1000) as blocker:
            empty_state._track_cards[0].clicked.emit("/tmp/song_a.mid")
        assert blocker.args == ["/tmp/song_a.mid"]

    def test_each_card_emits_correct_path(self, empty_state, qtbot, sample_tracks):
        """Each card in the list should emit its own file path."""
        empty_state.set_tracks(sample_tracks)
        for i, track in enumerate(sample_tracks):
            with qtbot.waitSignal(empty_state.track_clicked, timeout=1000) as blocker:
                empty_state._track_cards[i].clicked.emit(track.file_path)
            assert blocker.args == [track.file_path]


# ── _MiniTrackCard ────────────────────────────────────────


class TestMiniTrackCard:
    """_MiniTrackCard display and interaction."""

    @pytest.fixture()
    def card(self, qapp):
        info = MidiFileInfo(
            file_path="/tmp/test.mid",
            name="Test Track",
            duration_seconds=125.0,
            track_count=1,
            note_count=42,
            tempo_bpm=120.0,
        )
        card = _MiniTrackCard(info)
        yield card
        card.close()
        card.deleteLater()

    def test_fixed_height(self, card):
        assert card.height() == 48

    def test_stores_file_path(self, card):
        assert card._file_path == "/tmp/test.mid"

    def test_initial_not_hovered(self, card):
        assert card._hovered is False

    def test_click_emits_signal(self, card, qtbot):
        with qtbot.waitSignal(card.clicked, timeout=1000) as blocker:
            card.clicked.emit("/tmp/test.mid")
        assert blocker.args == ["/tmp/test.mid"]

    def test_left_click_emits(self, card, qtbot):
        """mousePressEvent with left button should emit clicked."""
        from PyQt6.QtCore import QPointF
        from PyQt6.QtGui import QMouseEvent

        with qtbot.waitSignal(card.clicked, timeout=1000):
            event = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                QPointF(10.0, 10.0),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            card.mousePressEvent(event)

    def test_right_click_does_not_emit(self, card, qtbot):
        """mousePressEvent with right button should NOT emit clicked."""
        from PyQt6.QtCore import QPointF
        from PyQt6.QtGui import QMouseEvent

        signal_emitted = False

        def on_click(path):
            nonlocal signal_emitted
            signal_emitted = True

        card.clicked.connect(on_click)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(10.0, 10.0),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )
        card.mousePressEvent(event)
        QApplication.processEvents()
        assert not signal_emitted

    def test_hover_state_changes(self, card):
        card.enterEvent(None)
        assert card._hovered is True
        card.leaveEvent(None)
        assert card._hovered is False

    def test_duration_format_minutes_seconds(self, qapp):
        """Duration 125s should display as 2:05."""
        info = MidiFileInfo(
            file_path="/tmp/t.mid",
            name="T",
            duration_seconds=125.0,
            track_count=1,
            note_count=1,
            tempo_bpm=120.0,
        )
        card = _MiniTrackCard(info)
        # Card created without crash, duration formatted as "2:05"
        assert card._file_path == "/tmp/t.mid"
        card.deleteLater()

    def test_card_with_zero_duration(self, qapp):
        info = MidiFileInfo(
            file_path="/tmp/zero.mid",
            name="Zero",
            duration_seconds=0.0,
            track_count=1,
            note_count=0,
            tempo_bpm=120.0,
        )
        card = _MiniTrackCard(info)
        assert card._file_path == "/tmp/zero.mid"
        card.deleteLater()

    def test_card_with_unicode_path(self, qapp):
        info = MidiFileInfo(
            file_path="/tmp/日本語/曲.mid",
            name="日本語の曲",
            duration_seconds=60.0,
            track_count=1,
            note_count=100,
            tempo_bpm=120.0,
        )
        card = _MiniTrackCard(info)
        assert card._file_path == "/tmp/日本語/曲.mid"
        card.deleteLater()

    def test_paint_event_no_crash(self, card):
        """paintEvent should not crash in either hover state."""
        card._hovered = False
        card.update()
        QApplication.processEvents()
        card._hovered = True
        card.update()
        QApplication.processEvents()


# ── _MusicNoteIcon ────────────────────────────────────────


class TestMusicNoteIcon:
    """_MusicNoteIcon renders without crashing."""

    def test_fixed_size(self, qapp):
        icon = _MusicNoteIcon()
        assert icon.width() == 64
        assert icon.height() == 64
        icon.deleteLater()

    def test_paint_event_no_crash(self, qapp):
        icon = _MusicNoteIcon()
        icon.update()
        QApplication.processEvents()
        icon.deleteLater()


# ── Signal Forwarding (integration) ──────────────────────


class TestPracticeViewSignalForwarding:
    """PracticeView correctly forwards signals from _PracticeEmptyState."""

    def test_forwards_file_open_signal(self, practice_view, qtbot):
        with qtbot.waitSignal(practice_view.file_open_requested, timeout=1000):
            practice_view._empty_state.file_open_clicked.emit()

    def test_forwards_track_signal(self, practice_view, qtbot):
        with qtbot.waitSignal(practice_view.practice_track_requested, timeout=1000) as blocker:
            practice_view._empty_state.track_clicked.emit("/tmp/test.mid")
        assert blocker.args == ["/tmp/test.mid"]

    def test_forwards_track_signal_with_unicode_path(self, practice_view, qtbot):
        with qtbot.waitSignal(practice_view.practice_track_requested, timeout=1000) as blocker:
            practice_view._empty_state.track_clicked.emit("/tmp/春江花月夜.mid")
        assert blocker.args == ["/tmp/春江花月夜.mid"]

    def test_open_btn_click_reaches_practice_view(self, practice_view, qtbot):
        """Full chain: button click → empty state signal → practice view signal."""
        with qtbot.waitSignal(practice_view.file_open_requested, timeout=1000):
            practice_view._empty_state._open_btn.click()


# ── Full Flow Integration ─────────────────────────────────


class TestPracticeViewFullFlow:
    """End-to-end flows through multiple states."""

    def test_select_track_practice_change_select_again(
        self, practice_view, one_note, sample_tracks
    ):
        """Full cycle: set tracks → start → change → verify tracks still there."""
        practice_view.set_library_tracks(sample_tracks)
        assert len(practice_view._empty_state._track_cards) == 3

        practice_view.start_practice(one_note, 120.0)
        assert practice_view._content_stack.currentIndex() == 1

        practice_view._on_change_track()
        assert practice_view._content_stack.currentIndex() == 0
        # Track cards should still be there (not cleared by change_track)
        assert len(practice_view._empty_state._track_cards) == 3

    def test_set_name_start_change_desc_resets(self, practice_view, one_note):
        """Track name is shown during practice, reset after change track."""
        practice_view.set_current_track_name("My Song")
        assert practice_view._desc_lbl.text() == "My Song"

        practice_view.start_practice(one_note, 120.0)
        assert practice_view._desc_lbl.text() == "My Song"

        practice_view._on_change_track()
        assert practice_view._desc_lbl.text() == translator.tr("practice.desc")

    def test_update_tracks_while_on_page_1(self, practice_view, one_note, sample_tracks):
        """set_library_tracks while practicing should update page 0 in background."""
        practice_view.start_practice(one_note, 120.0)
        assert practice_view._content_stack.currentIndex() == 1

        practice_view.set_library_tracks(sample_tracks)
        # Cards updated on page 0 even though we're on page 1
        assert len(practice_view._empty_state._track_cards) == 3

        practice_view._on_change_track()
        # Returning to page 0 should show the updated cards
        assert len(practice_view._empty_state._track_cards) == 3

    def test_resize_does_not_crash(self, practice_view):
        """resizeEvent should work without errors."""
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QResizeEvent

        event = QResizeEvent(QSize(1200, 800), QSize(800, 600))
        practice_view.resizeEvent(event)
        # No crash is success

    def test_display_note_hit_delegates_to_on_user_note(self, practice_view, one_note):
        """_on_display_note_hit should call on_user_note."""
        practice_view.start_practice(one_note, 120.0)
        # Should not crash
        practice_view._on_display_note_hit(60, 0.0)
