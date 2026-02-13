# 賽博琴仙 v2.0.0 — 專業級編曲工具升級

**發布日期**: 2026-02-13
**里程碑**: 11 大功能全面升級，從 MIDI 映射器進化為專業級數位編曲工作站

---

## 概述

v2.0.0 是賽博琴仙自 v1.0.0 以來最大規模的更新。新增 11 項核心功能，涵蓋智慧編排、MIDI 效果器、AI 作曲、練習模式、標準樂譜顯示、多格式匯入匯出等，將賽博琴仙從單純的 MIDI-鍵盤映射工具升級為完整的數位編曲工作站。

**數據一覽**:

| 指標 | v1.0.1 | v2.0.0 | 增幅 |
|------|--------|--------|------|
| 測試數量 | 598 | 1,123 | +88% |
| Python 模組 | 30 | 58 | +93% |
| 程式碼行數 | ~6,500 | ~12,750 | +96% |
| 新增檔案 | — | 28 | — |
| 支援匯入格式 | MIDI, MusicXML | + ABC, LilyPond | +2 |
| 支援匯出格式 | MIDI | + ABC, LilyPond, WAV | +3 |
| 主要視圖 | 3 | 4 (新增練習模式) | +1 |

---

## 新功能一覽

### Phase A: 核心邏輯引擎

#### A1. 智慧編排 (Smart Arrangement)
- **自動移調**: 分析音符分佈，計算最佳移調量
- **智慧折疊**: 將超出遊戲可彈奏範圍的音符摺疊至有效八度
- **三種策略**: `global_transpose`（全局移調）、`flowing_fold`（流動折疊）、`hybrid`（混合策略）
- **自動選擇**: 根據音符分佈自動選擇最佳策略（>80% 在範圍內 → 全局移調，跨度 > 36 半音 → 混合）
- 新增檔案: `cyber_qin/core/smart_arrangement.py`

#### A2. MIDI 效果器 (MIDI FX)
四種即時效果處理器，均操作 `list[BeatNote]`，可自由組合：

| 效果器 | 功能 | 核心參數 |
|--------|------|----------|
| **琶音器** (Arpeggiator) | 將和弦展開為時間序列 | pattern (up/down/up_down/random), rate, octave_range |
| **人性化** (Humanize) | 加入隨機微擾模擬真人演奏 | timing_jitter_ms, velocity_jitter, seed |
| **量化** (Quantize) | 將音符對齊到指定節拍網格 | grid (beats), strength (0-1) |
| **和弦生成** (Chord Gen) | 為單音生成和弦 | chord_type (10種), voicing (close/spread/drop2) |

- 新增檔案: `cyber_qin/core/midi_fx.py`, `cyber_qin/gui/dialogs/fx_dialog.py`
- 編輯器工具列新增 **FX** 按鈕，開啟四分頁效果器對話框

#### A3. AI 作曲 (Melody Generator)
基於一階馬可夫鏈的規則式旋律生成器：

- **旋律生成**: 音階感知（大調/小調/五聲/藍調/多利安等 8 種音階）、逐步運動偏好、樂句解析（主音/五度收束）、輪廓塑形
- **低音線生成**: 根據和弦進行（I-IV-V-I、I-V-vi-IV 等 4 種）自動產生低音
- **確定性測試**: `seed` 參數確保可重現結果
- 新增檔案: `cyber_qin/core/melody_generator.py`, `cyber_qin/gui/dialogs/melody_dialog.py`
- 編輯器工具列新增 **Generate** 按鈕

---

### Phase B: 編輯器增強

#### B1. 復原/重做系統升級 (Undo/Redo Polish)
- 每次操作記錄描述文字（如「移動音符」、「刪除音符」、「量化」等 18 種操作描述）
- 新增 `undo_descriptions` / `redo_descriptions` 屬性，支援未來歷史選單
- 修改檔案: `cyber_qin/core/beat_sequence.py`

#### B2. 幽靈音符增強 (Ghost Notes Enhancement)
- **編排幽靈層**: 執行智慧編排後，原始位置以珊瑚紅半透明顯示
- **透明度控制**: 可調整幽靈音符透明度 (10%-80%)
- 編輯器 Row 2 新增 **Ghost** 切換按鈕 + 透明度滑桿
- 修改檔案: `cyber_qin/gui/widgets/note_roll.py`

#### B3. 自動化曲線 (Automation Lane)
- **視覺化編輯**: 可拖曳控制點，線性內插顯示
- **操作方式**: 點擊新增、雙擊刪除、拖曳移動控制點
- **同步捲動**: 與鋼琴卷簾的水平捲動和縮放同步
- **支援參數**: velocity（力度）、tempo（速度）
- 新增檔案: `cyber_qin/core/automation.py`, `cyber_qin/gui/widgets/automation_lane_widget.py`
- 編輯器 Row 2 新增 **Auto** 切換按鈕

---

### Phase C: 新視圖

#### C1. 練習模式 (Practice Mode)
全新的第四個主要視圖，節奏遊戲風格的練習系統：

```
┌──────────────────────────────────────────┐
│ 綠色漸層標頭: "練習模式"                    │
├──────────────────────────────────────────┤
│ [分數: 0]  [準確率: 0%]  [連擊: 0]         │
├──────────────────────────────────────────┤
│   落下的音符 (60fps QPainter 渲染)         │
│   ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓           │
│ ═══════════════════════════════ 判定線     │
│   [PERFECT! / GREAT! / GOOD / MISS]      │
└──────────────────────────────────────────┘
```

- **判定時間窗口**: PERFECT (30ms), GREAT (80ms), GOOD (150ms)
- **即時計分**: 分數、準確率、連擊數即時更新
- **視覺回饋**: 判定等級浮動動畫（漸變色彩 + 上飄消失）
- **MIDI 即時輸入**: 從曲庫右鍵選擇「練習」即可開始
- 新增檔案: `cyber_qin/core/practice_engine.py`, `cyber_qin/gui/views/practice_view.py`, `cyber_qin/gui/widgets/practice_display.py`
- 側邊欄新增第四個導航按鈕「練習」

#### C2. 即時視覺化器 (Live Visualizer)
即時模式新增粒子特效視覺化：

- **粒子爆發**: 按下音符時產生金色粒子群，隨重力飄落
- **波紋效果**: 音高映射到垂直位置，產生擴散波紋
- **八度色譜**: C-B 映射 12 色光譜
- **力度條圖**: 底部顯示各音符力度，含衰減動畫
- **60fps 渲染**: QPainter 高效能動畫
- 新增檔案: `cyber_qin/gui/widgets/live_visualizer.py`
- 即時模式新增視覺化器切換按鈕

#### C3. 樂譜顯示 (Score View)
標準五線譜記譜法渲染：

- **五線譜**: 正確的 5 線譜表繪製
- **高音譜號**: Unicode 高音譜號符號
- **音符渲染**: 全音符/二分/四分/八分/十六分音符頭 + 符桿 + 符尾
- **附加線**: 超出五線譜的上下附加線自動繪製
- **小節線**: 根據拍號自動標示小節線，結尾雙線
- **升降號**: 根據調號自動標示臨時升降記號
- 新增檔案: `cyber_qin/core/notation_renderer.py`, `cyber_qin/gui/widgets/score_view_widget.py`
- 編輯器 Row 2 新增 **Score** 切換按鈕

---

### Phase D: 匯入匯出與社群功能

#### D1. 多格式匯入/匯出 (Multi-Format I/O)

| 格式 | 匯入 | 匯出 | 說明 |
|------|:----:|:----:|------|
| MIDI (.mid) | ✅ | ✅ | 原有支援 |
| MusicXML (.xml) | ✅ | — | 原有支援 |
| ABC Notation (.abc) | ✅ | ✅ | 正則表達式分詞器 |
| LilyPond (.ly) | ✅ | ✅ | 子集語法支援 |
| WAV Audio (.wav) | — | ✅ | 16-bit PCM 正弦波合成，純 Python（無外部依賴） |
| CQP Project (.cqp) | ✅ | ✅ | 原有支援 |

- 新增檔案: `cyber_qin/core/abc_parser.py`, `cyber_qin/core/lilypond_parser.py`, `cyber_qin/core/audio_exporter.py`
- 編輯器匯入/匯出對話框已擴展支援所有格式

#### D2. 社群樂庫 (Community Library)
曲目元資料管理與 `.cqlib` 合集分享：

- **元資料編輯**: 標題、演奏者、遊戲、難度、標籤、來源、說明
- **搜尋與篩選**: 根據元資料欄位搜尋曲目
- **合集打包**: `.cqlib` 格式（ZIP + manifest.json）
- **右鍵選單**: 播放、編輯、練習、編輯資訊、移除
- 新增檔案: `cyber_qin/core/library_metadata.py`, `cyber_qin/gui/dialogs/metadata_dialog.py`

---

## GUI 整合變更

### 編輯器 (editor_view.py)
- **Row 1**: 新增 Arrange / FX / Generate 按鈕
- **Row 2**: 新增 Ghost (+ 透明度滑桿) / Auto / Score 切換按鈕
- **匯入對話框**: 支援 MIDI / MusicXML / ABC / LilyPond / CQP
- **匯出對話框**: 支援 MIDI / ABC / LilyPond / WAV
- **NoteRoll 下方**: 新增隱藏式 Automation Lane 和 Score View

### 側邊欄 (sidebar.py)
- 新增第四個導航按鈕「練習」

### 即時模式 (live_mode_view.py)
- 新增視覺化器切換按鈕與 LiveVisualizer widget

### 曲庫 (library_view.py / track_list.py)
- TrackCard 新增右鍵選單（播放 / 編輯 / 練習 / 編輯資訊 / 移除）
- 新增 `practice_requested` / `metadata_requested` 信號

### 主視窗 (app_shell.py)
- QStackedWidget 新增 View 3 (PracticeView)
- 連接曲庫 → 練習模式信號
- 連接 MIDI 事件 → 練習模式計分器

---

## 多語言翻譯

所有新功能的 UI 文字已翻譯為五種語言：

| 語言 | 代碼 | 新增翻譯鍵 |
|------|------|-----------|
| English | `en` | ~40 keys |
| 繁體中文 | `zh_tw` | ~40 keys |
| 簡體中文 | `zh_cn` | ~40 keys |
| 日本語 | `ja` | ~40 keys |
| 한국어 | `ko` | ~40 keys |

---

## 測試

### 新增測試檔案 (8 個)

| 測試檔案 | 測試數 | 覆蓋模組 |
|----------|--------|----------|
| `test_smart_arrangement.py` | 50 | smart_arrangement.py |
| `test_midi_fx.py` | 83 | midi_fx.py |
| `test_melody_generator.py` | 60 | melody_generator.py |
| `test_automation.py` | 53 | automation.py |
| `test_practice_engine.py` | 68 | practice_engine.py |
| `test_notation_renderer.py` | 55 | notation_renderer.py |
| `test_format_parsers.py` | 105 | abc_parser, lilypond_parser, audio_exporter |
| `test_library_metadata.py` | 53 | library_metadata.py |
| **合計** | **527** | |

### 測試結果
```
1,123 passed in 17.99s
ruff check: All checks passed!
```

---

## 新增檔案清單

### 核心模組 (10 個)
```
cyber_qin/core/smart_arrangement.py     — 智慧編排引擎
cyber_qin/core/midi_fx.py              — 4 種 MIDI 效果處理器
cyber_qin/core/melody_generator.py     — 馬可夫鏈旋律/低音生成
cyber_qin/core/automation.py           — 自動化曲線 (點、軌道、管理器)
cyber_qin/core/practice_engine.py      — 練習模式計分引擎
cyber_qin/core/notation_renderer.py    — MIDI → 五線譜渲染
cyber_qin/core/abc_parser.py           — ABC 記譜法解析/匯出
cyber_qin/core/lilypond_parser.py      — LilyPond 解析/匯出
cyber_qin/core/audio_exporter.py       — WAV 音訊匯出 (正弦波合成)
cyber_qin/core/library_metadata.py     — 曲目元資料 + .cqlib 合集
```

### GUI 組件 (8 個)
```
cyber_qin/gui/dialogs/fx_dialog.py           — MIDI FX 四分頁對話框
cyber_qin/gui/dialogs/melody_dialog.py       — 旋律/低音生成對話框
cyber_qin/gui/dialogs/metadata_dialog.py     — 元資料編輯對話框
cyber_qin/gui/views/practice_view.py         — 練習模式主視圖
cyber_qin/gui/widgets/practice_display.py    — 落下音符 60fps 顯示
cyber_qin/gui/widgets/live_visualizer.py     — 粒子特效視覺化器
cyber_qin/gui/widgets/automation_lane_widget.py — 自動化曲線編輯器
cyber_qin/gui/widgets/score_view_widget.py   — 五線譜渲染 widget
```

### 測試檔案 (8 個)
```
tests/test_smart_arrangement.py
tests/test_midi_fx.py
tests/test_melody_generator.py
tests/test_automation.py
tests/test_practice_engine.py
tests/test_notation_renderer.py
tests/test_format_parsers.py
tests/test_library_metadata.py
```

### 修改檔案 (10 個)
```
cyber_qin/core/beat_sequence.py        — Undo 描述、ghost 儲存
cyber_qin/core/translator.py           — ~200 新翻譯鍵 (5 語言)
cyber_qin/gui/app_shell.py             — Practice View 註冊、信號連接
cyber_qin/gui/views/editor_view.py     — 工具列按鈕、匯入匯出擴展
cyber_qin/gui/views/library_view.py    — 練習/元資料信號
cyber_qin/gui/views/live_mode_view.py  — 視覺化器整合
cyber_qin/gui/widgets/note_roll.py     — 幽靈音符渲染層
cyber_qin/gui/widgets/sidebar.py       — 第四導航按鈕
cyber_qin/gui/widgets/track_list.py    — 右鍵選單、新信號
cyber_qin/gui/dialogs/settings_dialog.py — SpinBox 寬度修正
```

---

## 技術規格

### 依賴
- Python 3.11 / 3.12 / 3.13
- PyQt6 >= 6.5
- mido >= 1.3
- python-rtmidi >= 1.5
- **無新增外部依賴** — 所有新功能均使用純 Python 實現

### 相容性
- 完全向下相容 v1.0.x 專案檔案 (.cqp)
- 新格式 (.abc, .ly, .wav, .cqlib) 為新增支援，不影響現有功能

### 已知限制
- WAV 匯出使用正弦波合成，音色較為簡單（適合預覽用途）
- LilyPond 解析僅支援旋律子集（不支援和聲記號、歌詞等）
- 練習模式判定僅支援音高匹配，不支援力度判定

---

## 從 v1.0.x 升級

1. 備份現有 `.cqp` 專案檔案
2. 更新程式碼（`git pull` 或下載新版本）
3. 重新安裝依賴: `pip install -e .[dev]`
4. 驗證: `pytest` 確認所有測試通過

**無破壞性變更** — v1.0.x 的所有功能與設定完全保留。

---

## 致謝

- AI 協作: Claude Opus 4.6
- MIDI 硬體測試: Roland FP-30X
- 開源社群: mido, python-rtmidi, PyQt6

---

**完整變更記錄**: [v1.0.1...v2.0.0](https://github.com/EdmondVirelle/cyber-qin/compare/v1.0.1...v2.0.0)
