# SDD: Practice Mode Song Picker

**Software Design Document**
**Feature**: Practice Mode Built-in Song Picker
**Version**: 1.0
**Date**: 2026-02-23
**Author**: Claude Opus 4.6 + Edmond Virelle

---

## 1. Overview

### 1.1 Problem Statement

練習模式（Practice Mode）目前只能透過曲庫（Library）右鍵選單 → 「練習」進入。使用者直接點選側邊欄「練習」時，只會看到空白的下落音符畫面，沒有任何選曲機制，體驗斷裂。

### 1.2 Solution Summary

在 `PracticeView` 內部新增 `QStackedWidget`，提供雙頁切換：

- **Page 0 — 選曲空狀態**：內建歌曲選擇器（開檔按鈕 + 曲庫曲目列表）
- **Page 1 — 練習內容**：原有的 score bar + PracticeDisplay

使練習模式**自給自足**：無論從側邊欄直接進入或從曲庫右鍵進入，都能流暢使用。

### 1.3 Scope

| In Scope | Out of Scope |
|----------|-------------|
| 練習模式內建選曲 UI | 新的練習玩法模式 |
| 開啟 MIDI 檔案對話框 | MIDI 檔案預覽播放 |
| 曲庫曲目同步顯示 | 搜尋 / 排序 / 篩選 |
| 換曲流程（停止 → 返回選曲） | 練習成績歷史記錄 |
| 5 語言 i18n 支援 | 新增語言 |

---

## 2. Architecture

### 2.1 Component Hierarchy

```
PracticeView (QWidget)
  │
  ├── header (100px, _PracticeGradientHeader + overlay)
  │   ├── row1: [title_lbl] [stretch] [change_track_btn] [mode_combo] [scheme_combo]
  │   └── row2: [desc_lbl]  ← 練習中顯示曲名，選曲時顯示玩法說明
  │
  └── _content_stack (QStackedWidget)
      │
      ├── page 0: _PracticeEmptyState (QWidget)
      │   └── QScrollArea
      │       ├── _MusicNoteIcon (64×64, QPainter)
      │       ├── title_lbl: "選擇練習曲目"
      │       ├── sub_lbl: "開啟 MIDI 檔案，或從曲庫選擇"
      │       ├── [Open MIDI File] button (gold accent, ACCENT_GOLD)
      │       ├── section_lbl: "曲庫曲目"
      │       ├── _tracks_container (QVBoxLayout)
      │       │   └── _MiniTrackCard × N  ← 動態生成
      │       └── no_tracks_lbl (placeholder when empty)
      │
      └── page 1: practice_content (QWidget)
          ├── score_bar (40px)
          │   ├── score_label (ACCENT_GOLD)
          │   ├── accuracy_label (TEXT_PRIMARY)
          │   ├── combo_label (ACCENT)
          │   └── start_btn
          └── PracticeDisplay (flex, 1)
```

### 2.2 New Widget Classes

| Class | Parent | Responsibility |
|-------|--------|---------------|
| `_PracticeEmptyState` | `QWidget` | 選曲空狀態頁面，含開檔按鈕與曲庫曲目列表 |
| `_MiniTrackCard` | `QWidget` | 48px 高的可點擊曲目卡片，顯示曲名 / 時長 / 音符數 |
| `_MusicNoteIcon` | `QWidget` | 64×64 QPainter 繪製音符圖標裝飾 |

### 2.3 Signal Flow

```
User clicks "Open MIDI File" button
  │
  └─→ _PracticeEmptyState.file_open_clicked
      └─→ PracticeView.file_open_requested
          └─→ AppShell._on_practice_open_file()
              └─→ QFileDialog.getOpenFileName()
                  └─→ AppShell._on_practice_file(path)
                      ├─→ PracticeView.set_current_track_name(name)
                      ├─→ PracticeView.start_practice(notes, bpm)
                      │   └─→ _content_stack → page 1
                      └─→ Sidebar._set_active(3)

User clicks a _MiniTrackCard
  │
  └─→ _MiniTrackCard.clicked(file_path)
      └─→ _PracticeEmptyState.track_clicked(file_path)
          └─→ PracticeView.practice_track_requested(file_path)
              └─→ AppShell._on_practice_file(path)
                  └─→ (same flow as above)

User clicks "Change Track" button
  │
  └─→ PracticeView._on_change_track()
      ├─→ display.stop()
      ├─→ _content_stack → page 0
      ├─→ change_track_btn.hide()
      └─→ desc_lbl → practice.desc (reset)

Sidebar switches to Practice tab (index 3)
  │
  └─→ AppShell._on_view_changed(3)
      └─→ PracticeView.set_library_tracks(library_view._tracks)
          └─→ _PracticeEmptyState.set_tracks(tracks)
              └─→ Rebuild _MiniTrackCard list
```

### 2.4 Data Flow

```
LibraryView._tracks : list[MidiFileInfo]
        │
        │  (reference passed on view switch)
        ▼
_PracticeEmptyState.set_tracks()
        │
        │  (creates _MiniTrackCard per item)
        ▼
_MiniTrackCard.clicked → file_path : str
        │
        ▼
AppShell._on_practice_file(file_path)
        │
        ├─→ MidiFileParser.parse(file_path) → events, info
        ├─→ EditorSequence.from_midi_file_events(events) → notes : list[BeatNote]
        ├─→ PracticeView.set_current_track_name(info.name)
        └─→ PracticeView.start_practice(notes, info.tempo_bpm)
                │
                ├─→ notes_to_practice(notes, bpm) → practice_notes
                ├─→ PracticeScorer(practice_notes)
                └─→ PracticeDisplay.set_notes() + .start()
```

---

## 3. UI Design

### 3.1 Page 0 — Empty State (Song Picker)

```
┌─────────────────────────────────────────────────────────────────┐
│  ██ Practice Mode ██                    [MIDI Keyboard ▼]       │ ← Header (100px gradient)
│  Notes fall from above — press...                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                          ♪                                      │ ← _MusicNoteIcon
│                                                                 │
│                   選擇練習曲目                                    │ ← 20pt Bold
│            開啟 MIDI 檔案，或從曲庫選擇                             │ ← 12pt Secondary
│                                                                 │
│              ┌──────────────────────┐                            │
│              │  開啟 MIDI 檔案...    │  ← Gold accent button      │
│              └──────────────────────┘                            │
│                                                                 │
│  曲庫曲目 ─────────────────────────                               │ ← Section header
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Song A                              2:00    200 notes  │    │ ← _MiniTrackCard
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Song B                              1:30    150 notes  │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Song C                              1:00     80 notes  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Page 1 — Practice Session

```
┌─────────────────────────────────────────────────────────────────┐
│  ██ Practice Mode ██      [換曲]  [MIDI Keyboard ▼]            │ ← change_track_btn visible
│  春江花月夜                                                      │ ← Track name in desc_lbl
├─────────────────────────────────────────────────────────────────┤
│  Score: 1200    Accuracy: 85%    Combo: 12          [Stop]     │ ← Score bar (40px)
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──┐  ┌──┐     ┌──┐        ┌──┐                              │ ← Falling notes
│  │  │  │  │     │  │        │  │                              │
│  └──┘  └──┘     └──┘        └──┘                              │
│                                                                 │
│ ════════════════ GOLD LINE ════════════════                     │ ← Hit zone
│                                                                 │
│  ┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐                        │ ← Piano keys
│  └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘                        │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Visual Styling

| Element | Color | Font |
|---------|-------|------|
| Open File button | `ACCENT_GOLD` (#D4AF37) bg | JhengHei 12pt Bold |
| Change Track button | `ACCENT_GOLD` border, transparent bg | 12px |
| Track card (normal) | `BG_SCROLL` (#15191F) | JhengHei 11pt |
| Track card (hover) | `BG_PAPER` (#1A1F2E) | — |
| Track card border | `BORDER_DIM` (#404759), 6px radius | — |
| Music note icon | `ACCENT_GOLD` stroke + fill | — |
| Section header | `TEXT_SECONDARY` (#A0A8B8) | JhengHei 13pt Bold |
| No-tracks placeholder | `TEXT_DISABLED` (#5A6270) | JhengHei 11pt |

---

## 4. State Machine

```
                    ┌─────────────────┐
                    │   SONG_PICKER   │ ← Initial state (page 0)
                    │  (Empty State)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         [Open File]   [Click Card]   [Library右鍵]
              │              │              │
              ▼              ▼              ▼
        QFileDialog    emit signal    emit signal
              │              │              │
              └──────────────┼──────────────┘
                             │
                    _on_practice_file()
                             │
                             ▼
                    ┌─────────────────┐
                    │   PRACTICING    │ ← page 1
                    │ (Score + Notes) │
                    └────────┬────────┘
                             │
                      [Change Track]
                             │
                             ▼
                    ┌─────────────────┐
                    │   SONG_PICKER   │ ← Back to page 0
                    └─────────────────┘
```

**State transitions**:

| From | Trigger | To | Side Effects |
|------|---------|-----|-------------|
| SONG_PICKER | Open file → select .mid | PRACTICING | Parse MIDI, set track name, start display |
| SONG_PICKER | Click library card | PRACTICING | Same as above |
| SONG_PICKER | Library右鍵 → Practice | PRACTICING | Same (via `practice_requested` signal) |
| PRACTICING | Click "Change Track" | SONG_PICKER | Stop display, clear scorer/notes, reset desc |
| PRACTICING | Click "Start/Stop" btn | PRACTICING | Toggle play/pause within same track |

---

## 5. I18N Keys

6 new keys added across 5 languages:

| Key | en | zh_tw | zh_cn | ja | ko |
|-----|-----|-------|-------|-----|-----|
| `practice.empty.title` | Select a Track | 選擇練習曲目 | 选择练习曲目 | 練習曲を選択 | 연습곡 선택 |
| `practice.empty.sub` | Open a MIDI file or pick from library | 開啟 MIDI 檔案，或從曲庫選擇 | 打开 MIDI 文件，或从曲库选择 | MIDIファイルを開くか、ライブラリから選択 | MIDI 파일을 열거나 라이브러리에서 선택 |
| `practice.open_file` | Open MIDI File... | 開啟 MIDI 檔案... | 打开 MIDI 文件... | MIDIファイルを開く... | MIDI 파일 열기... |
| `practice.library_tracks` | Library Tracks | 曲庫曲目 | 曲库曲目 | ライブラリ曲目 | 라이브러리 곡목 |
| `practice.no_tracks` | Library is empty... | 曲庫為空... | 曲库为空... | ライブラリが空です... | 라이브러리가 비어 있습니다... |
| `practice.change_track` | Change Track | 換曲 | 换曲 | 曲を変更 | 곡 변경 |

Additionally, `practice.desc` was updated to remove navigation instructions (now purely gameplay description).

---

## 6. Design Decisions

### 6.1 Why QStackedWidget inside PracticeView (not a separate view)?

**Chosen**: `QStackedWidget` 內嵌於 PracticeView，page 0 = 選曲，page 1 = 練習。

**Alternatives considered**:
- **Separate EmptyPracticeView**: 需要在 AppShell 的主 stack 新增第 5 個 view，修改 sidebar 導航邏輯。過度設計。
- **Modal dialog**: 彈窗會打斷 flow，且需要額外處理「返回選曲」的 UX。

**Rationale**: 內嵌 stack 最簡單，不影響 AppShell 的 view index (0-3)，sidebar 不需改動。

### 6.2 Why pass library tracks by reference on view switch?

**Chosen**: `_on_view_changed(index==3)` 時從 `library_view._tracks` 取資料。

**Alternatives considered**:
- **Signal 同步**: LibraryView 每次 tracks 變動就 emit signal → Practice view 更新。增加耦合，且大部分時間使用者不在 Practice tab。
- **Shared model**: 抽取 `TrackStore` 共享模型。對此單一功能過度抽象。

**Rationale**: 惰性同步（切換時才拿）最簡單、最低耦合。使用者切到 Practice 時看到的曲目永遠是最新的。

### 6.3 Why _MiniTrackCard instead of reusing TrackList?

**Chosen**: 新建 `_MiniTrackCard` (48px, 精簡版)。

**Rationale**: Library 的 `TrackList` 帶有右鍵選單、排序、多欄表格等複雜功能。Practice 只需要點擊即開始練習的單欄列表。重用 TrackList 會引入不必要的依賴和 UX 噪音。

---

## 7. Files Modified

| File | Lines Changed | Description |
|------|-------------|-------------|
| `cyber_qin/core/translator.py` | +42 | 6 new i18n keys × 5 languages + practice.desc update |
| `cyber_qin/gui/views/practice_view.py` | Rewritten (~548 LOC) | +3 new classes, QStackedWidget, signals, change track |
| `cyber_qin/gui/app_shell.py` | +15 | Wire new signals, QFileDialog, library track passing |
| `tests/test_practice_view.py` | +926 (new file) | 114 tests covering all behavior + edge cases + regression |

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Library tracks stale when staying on Practice tab | Low | Low | Tracks refresh on every view switch |
| Large library (500+ tracks) causes scroll lag | Low | Medium | `_MiniTrackCard` is lightweight (48px fixed height, no complex rendering) |
| Signal chain too deep (5 hops for file open) | — | Low | Standard Qt pattern; each hop is single-line connect |
| `_on_practice_file` fails on corrupt MIDI | Low | Low | Existing try/except with error logging preserved |

---

## 9. Post-Release Bug Fix (v2.3.0 → v2.3.1)

### 9.1 Bug: Track Card Click Did Nothing

**Symptom**: Clicking a `_MiniTrackCard` in the song picker had no visible effect — no page switch, no practice start.

**Root Cause**: `EditorSequence.from_midi_file_events()` is a `@classmethod` that returns a **new** `EditorSequence`. In `AppShell._on_practice_file()`, the return value was discarded:

```python
# BUG:
seq = EditorSequence(tempo_bpm=info.tempo_bpm)
seq.from_midi_file_events(events)   # ← classmethod return value ignored
notes = seq.notes                    # ← always [] (empty instance)

# FIX:
seq = EditorSequence.from_midi_file_events(events, tempo_bpm=info.tempo_bpm)
notes = seq.notes                    # ← correctly populated
```

**Why it passed tests**: The 112 practice view tests validated the signal chain and UI behavior, but `_on_practice_file()` lives in `AppShell` (integration layer, not unit-tested). The signal chain was correct — the bug was in the handler at the end of the chain.

**Regression test added**: `TestEditorSequenceClassmethod` (2 tests) in `tests/test_practice_view.py`.
