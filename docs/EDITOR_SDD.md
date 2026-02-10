# 賽博琴仙 編曲器 軟體設計文件 (SDD)

> **版本**：v1.0 Draft
> **日期**：2026-02-11
> **作者**：Developer + Claude
> **狀態**：RFC (Request for Comments)

---

## 目錄

1. [概覽與願景 (Overview & Vision)](#1-概覽與願景)
2. [競品分析 (Competitive Analysis)](#2-競品分析)
3. [設計原則 (Design Principles)](#3-設計原則)
4. [功能規格 (Feature Specification)](#4-功能規格)
5. [UI/UX 設計 (UI/UX Design)](#5-uiux-設計)
6. [資料模型與架構 (Data Model & Architecture)](#6-資料模型與架構)
7. [實作路線圖 (Implementation Roadmap)](#7-實作路線圖)

---

## 1. 概覽與願景

### 1.1 產品定位

賽博琴仙編曲器是一個內建於賽博琴仙 MIDI 映射器的**精簡型 MIDI 編曲器**。
目標是在不安裝 DAW 的情況下，讓使用者能快速編寫、編輯、匯出旋律，
用於《燕雲十六聲》遊戲內的 36 鍵演奏系統。

### 1.2 願景宣言

> **以 MuseScore 的鍵盤效率 + FL Studio 的 Piano Roll 直覺操作，
> 做一個零學習成本、開箱即用的 36 鍵編曲器。**

我們不追求取代專業 DAW，而是要在以下三個維度做到極致：

| 維度 | 目標 | 對標產品 |
|------|------|----------|
| **輸入速度** | 鍵盤快捷鍵 + 點擊雙模式，10 秒內完成一個樂句 | MuseScore Step Input |
| **視覺直覺** | 一眼看懂節拍、休止符、小節結構 | FL Studio Piano Roll |
| **操作流暢** | 拖曳、框選、複製，不需要切換工具 | FL Studio 單工具模式 |

### 1.3 範圍限制 (Scope Boundaries)

| 做 | 不做 |
|----|------|
| Piano Roll 時間軸編輯 | VST/AU 插件宿主 |
| 多軌 MIDI 編輯 (4~12 軌) | 音訊錄音 / 混音 |
| 拍號 / 小節線 / 節拍格線 | 五線譜完整排版引擎 |
| 休止符作為一等公民 | 連音線 / 圓滑線標記 |
| 自動校正 (量化 + 音高) | AI 作曲建議 |
| MIDI 匯出 + 專案檔 | MusicXML / LilyPond 匯出 |
| 即時聲音回饋 | MIDI 軟體合成器 |

---

## 2. 競品分析

### 2.1 Piano Roll 標竿：六大產品比較

| 特性 | FL Studio | Ableton Live 12 | MuseScore 4 | LMMS | Logic Pro | Reaper |
|------|-----------|------------------|-------------|------|-----------|--------|
| **Ghost Notes** (跨軌半透明音符) | 內建 | 有限 | N/A | 無 | 無 | 腳本 |
| **Scale Highlighting** | 內建 | 每 Clip | 記譜原生 | 無 | 無 | 腳本 |
| **Chord Stamps** | 內建 | 無 | N/A | 無 | 無 | 腳本 |
| **Paint / Brush 模式** | 內建 | 無 | N/A | 無 | 無 | 無 |
| **Step Input (鍵盤驅動)** | 無 | 無 | 最強 | 無 | 有 | 無 |
| **休止符處理** | 隱式 (空白) | 隱式 | 一等公民 | 隱式 | 隱式 | 隱式 |
| **拍號切換** | 基本 | 基本 | 完整 | 基本 | 完整 | 完整 |
| **多軌編輯** | Ghost Notes | 有限 | 多譜表 | 無 | 有限 | 腳本 |
| **價格** | $99~$499 | $99~$599 | 免費 | 免費 | $199 | $60~$225 |

### 2.2 各家優勢精華

#### FL Studio — Piano Roll 之王

- **單工具模式**：左鍵放置、右鍵刪除、拖曳移動、拖邊緣調整長度。
  幾乎不需要切換工具，感覺像「用 PowerPoint 操作音符」。
- **Ghost Notes**：半透明顯示其他軌的音符，提供和聲上下文。
- **Scale Highlighting**：標示合法音階，減少樂理錯誤。
- **Velocity 視覺化**：音符顏色深淺直接反映力度。

#### MuseScore — Step Input 之王

- **Duration-First 工作流**：先選時值（數字鍵 1~7），再輸入音高。
  經訓練後速度遠超滑鼠點擊。
- **休止符一等公民**：自動填充小節、完整顯示休止符時值。
- **鍵盤快捷鍵覆蓋率極高**：幾乎所有操作都有快捷鍵。

#### Ableton Live 12 — 生成式 MIDI 工具

- **5 種 Generator**：Rhythm、Seed、Shape、Stacks、Euclidean。
- **Per-note Probability**：每個音符 0~100% 觸發機率。
- **Scale-aware Transformations**：所有 MIDI 工具尊重 Scale 設定。

### 2.3 使用者十大痛點 (跨產品論壇統計)

| # | 痛點 | 我們的對策 |
|---|------|-----------|
| 1 | 頻繁切換工具 | 單工具模式 (FL Studio 風格) |
| 2 | 量化太死板 | Snap + Ctrl 暫時關閉 |
| 3 | Velocity 編輯困難 | 本專案統一力度，不需要 |
| 4 | 缺少跨軌上下文 | Ghost Notes (半透明跨軌音符) |
| 5 | 缺少音階提示 | Scale Highlighting (36 鍵範圍) |
| 6 | 音符輸入太慢 | 鍵盤 Step Input + 滑鼠雙模式 |
| 7 | Undo 粒度太粗 | 每個操作獨立 Undo |
| 8 | 缺少 inline 自動化 | 超出範圍 — 不做 |
| 9 | Zoom / Scroll 體驗差 | 游標中心縮放、平滑捲動 |
| 10 | 缺少和弦工具 | Phase 3 再評估 |

### 2.4 我們的差異化

大多數 DAW 的休止符是「空白」——使用者看不見它。
**賽博琴仙是第一個把休止符用紅色顯示在 Piano Roll 上的編曲器**，
讓節奏結構一目了然。

結合 MuseScore 的 Step Input 效率 + FL Studio 的拖曳直覺 + 紅色休止符視覺化，
這是其他產品都沒有的組合。

---

## 3. 設計原則

### 3.1 五大原則

#### P1: 拍為核心 (Beat-Native)

內部時間模型以「拍」(beat) 為單位，不是秒數。
所有音符位置、時值、格線都以拍表示。
秒數只在 MIDI 匯出和播放時計算。

**理由**：以秒為單位的系統在改變 BPM 時會破壞節奏對齊。
以拍為單位，改 BPM 只影響播放速度，不影響音符位置。

#### P2: 休止符即音符 (Rests Are Notes)

休止符不是「空白」，而是和音符一樣的一等資料物件。
有時間位置、有時值、有視覺表示（紅色半透明方塊）。

**理由**：明確的休止符讓使用者在 Piano Roll 上直接「看到」節奏結構。

#### P3: 單工具操作 (Single-Tool Interaction)

不需要工具列切換。左鍵的行為取決於滑鼠位置：
- 空白格 → 放置音符
- 音符上 → 選取 / 開始拖曳
- 音符右邊緣 → 調整長度
- 右鍵 → 刪除
- 框選 → Shift + 拖曳

**理由**：FL Studio 使用者一致認為這是 Piano Roll 「手感好」的第一要素。

#### P4: 鍵盤與滑鼠平等 (Dual Input Parity)

所有操作都可以用滑鼠完成，也可以用鍵盤完成。
快捷鍵可全域開關，預設開啟。

**理由**：新手用滑鼠、熟手用鍵盤。不強迫任何一種。

#### P5: 即時回饋 (Instant Feedback)

每次輸入音符立即發出聲音。
每次操作立即更新畫面 (repaint, 非 update)。
Flash 動畫 (350ms) 標記剛輸入的位置。

**理由**：操作與結果之間的延遲超過 50ms 就會破壞「演奏感」。

---

## 4. 功能規格

### 4.1 時間系統

#### 4.1.1 拍號 (Time Signature)

| 屬性 | 規格 |
|------|------|
| 預設拍號 | 4/4 |
| 支援拍號 | 4/4, 3/4, 2/4, 6/8, 4/8 |
| 切換方式 | 工具列下拉選單 |
| 小節線 | 每拍號週期自動繪製 (例：4/4 每 4 拍一條) |
| 拍號變更 | Phase 2 — 初版只支援單一拍號 |

#### 4.1.2 格線 (Grid)

| 屬性 | 規格 |
|------|------|
| 最小格線 | 1/16 音符 (十六分音符) |
| 格線層次 | 小節線 (粗) > 拍線 (中) > 細分線 (細) |
| Snap 行為 | 預設吸附格線；按住 Ctrl 暫時自由放置 |
| 格線密度 | 隨縮放等級自動調整顯示密度 |

#### 4.1.3 可選時值

使用者在輸入前選擇時值，決定下一個音符的長度：

| 鍵盤快捷鍵 | 時值 | 佔拍數 (4/4) | 格數 (1/16 base) |
|------------|------|-------------|-----------------|
| `1` | 全音符 | 4 拍 | 16 格 |
| `2` | 二分音符 | 2 拍 | 8 格 |
| `3` | 四分音符 | 1 拍 | 4 格 |
| `4` | 八分音符 | 1/2 拍 | 2 格 |
| `5` | 十六分音符 | 1/4 拍 | 1 格 |
| `0` | (同時值) 休止符 | 同上 | 同上 |

> 按 `0` 插入對應時值的休止符。例：當前時值是四分音符 → `0` 插入四分休止符。

### 4.2 音符與休止符

#### 4.2.1 音符 (Note)

| 屬性 | 類型 | 說明 |
|------|------|------|
| `time_beats` | float | 在拍時間軸上的位置 |
| `duration_beats` | float | 時值（以拍為單位）|
| `note` | int | MIDI 音高 (48~83) |
| `velocity` | int | 固定 100 (v1 不支援可變力度) |
| `track` | int | 所屬軌道 (0~11) |

#### 4.2.2 休止符 (Rest)

| 屬性 | 類型 | 說明 |
|------|------|------|
| `time_beats` | float | 在拍時間軸上的位置 |
| `duration_beats` | float | 時值（以拍為單位）|
| `track` | int | 所屬軌道 |

休止符**不佔用 MIDI 音高**，但在 Piano Roll 上以**紅色半透明橫條**顯示，
橫跨該軌道的全音域高度，明確標記「這裡是空的」。

### 4.3 多軌系統

| 屬性 | 規格 |
|------|------|
| 預設軌道數 | 4 |
| 最大軌道數 | 12 |
| 軌道操作 | 新增、刪除、靜音、獨奏、重新命名 |
| 軌道顏色 | 預設 12 色色板，可自訂 |
| 活動軌道 | 點擊軌道列表切換；輸入的音符進入活動軌道 |
| Ghost Notes | 非活動軌道的音符以 20% 透明度顯示 |
| MIDI Channel | 每軌獨立 MIDI Channel (匯出時保留) |

#### 軌道預設色板

```
Track 0: #00F0FF (賽博青 — 主旋律)
Track 1: #FF6B6B (珊瑚紅)
Track 2: #4ECDC4 (薄荷綠)
Track 3: #D4A853 (金墨)
Track 4: #A06BFF (紫霧)
Track 5: #FF9F43 (琥珀)
Track 6: #54A0FF (天藍)
Track 7: #5F27CD (深紫)
Track 8: #01A3A4 (深青)
Track 9: #F368E0 (粉紫)
Track 10: #10AC84 (翡翠)
Track 11: #EE5A24 (朱砂)
```

### 4.4 編輯操作

#### 4.4.1 單音符操作

| 操作 | 滑鼠 | 鍵盤 |
|------|------|------|
| 放置音符 | 左鍵點擊空白格 | 方向鍵選位 + Enter |
| 刪除音符 | 右鍵點擊音符 | 選取 + Delete |
| 選取音符 | 左鍵點擊音符 | 方向鍵移動選取框 |
| 移動音符 (時間) | 拖曳水平方向 | 選取 + ← → |
| 移動音符 (音高) | 拖曳垂直方向 | 選取 + ↑ ↓ |
| 調整長度 | 拖曳音符右邊緣 | 選取 + Shift + ← → |

#### 4.4.2 多音符操作 (框選)

| 操作 | 觸發方式 |
|------|----------|
| 框選 | Shift + 左鍵拖曳 (矩形框選) |
| 追加選取 | Ctrl + 左鍵點擊 |
| 全選 | Ctrl + A |
| 刪除選取 | Delete |
| 移動選取 | 拖曳選取區域 |
| 複製選取 | Ctrl + C → Ctrl + V (在游標位置貼上) |
| 剪下選取 | Ctrl + X |

#### 4.4.3 Undo / Redo

| 屬性 | 規格 |
|------|------|
| 粒度 | 每個獨立操作 (放置、刪除、移動、框選操作) |
| 堆疊深度 | 100 步 |
| 快捷鍵 | Ctrl + Z / Ctrl + Y |
| 跨軌 | Undo 影響所有軌道 (全域堆疊) |

### 4.5 自動校正 (Auto-Tune)

| 功能 | 規格 |
|------|------|
| 量化 (Quantize) | 將音符對齊到最近的格線位置 |
| 量化強度 | 0% ~ 100% (預設 75%) |
| 量化格線 | 1/4, 1/8, 1/16, 三連音 |
| 音高校正 | 將超出 48~83 範圍的音符摺疊到合法八度 |
| 觸發方式 | 工具列核取方塊 (即時) 或手動按鈕 (選取後套用) |

### 4.6 播放與聲音

| 屬性 | 規格 |
|------|------|
| 輸入回饋 | 點擊琴鍵 / 鍵盤輸入時即時發聲 |
| 播放引擎 | 使用現有 MidiFilePlayer (轉換 beats → seconds) |
| 播放速度 | 0.25x ~ 2.0x |
| 播放游標 | 青色垂直線跟隨播放位置移動 |
| 循環播放 | 選取範圍循環 (Phase 2) |

### 4.7 檔案格式

#### 4.7.1 MIDI 匯出

- 格式：Standard MIDI File Type 1 (多軌)
- 解析度：480 TPB
- 每軌獨立 MIDI Track + Channel
- 拍號事件寫入 Track 0 (conductor track)

#### 4.7.2 專案檔 (.cqp)

| 屬性 | 規格 |
|------|------|
| 格式 | JSON (gzip 壓縮，副檔名 `.cqp`) |
| 版本欄位 | `"version": 1` |
| 內容 | 拍號、BPM、軌道設定、所有音符 + 休止符、Undo 歷史 |
| 自動儲存 | 每 60 秒寫入 `~/.cyber_qin/autosave.cqp` |

專案檔 JSON 結構範例：

```json
{
  "version": 1,
  "tempo_bpm": 120,
  "time_signature": [4, 4],
  "tracks": [
    {
      "name": "主旋律",
      "color": "#00F0FF",
      "channel": 0,
      "muted": false,
      "notes": [
        {"time": 0.0, "duration": 1.0, "note": 60, "velocity": 100},
        {"time": 1.0, "duration": 0.5, "note": 64, "velocity": 100}
      ],
      "rests": [
        {"time": 1.5, "duration": 0.5}
      ]
    }
  ]
}
```

### 4.8 鍵盤快捷鍵總表

| 快捷鍵 | 功能 | 分類 |
|--------|------|------|
| `1` | 全音符 | 時值 |
| `2` | 二分音符 | 時值 |
| `3` | 四分音符 | 時值 |
| `4` | 八分音符 | 時值 |
| `5` | 十六分音符 | 時值 |
| `0` | 休止符 (同當前時值) | 時值 |
| `Space` | 播放 / 暫停 | 播放 |
| `Ctrl+Z` | 復原 | 編輯 |
| `Ctrl+Y` | 重做 | 編輯 |
| `Ctrl+A` | 全選 | 選取 |
| `Ctrl+C` | 複製 | 選取 |
| `Ctrl+V` | 貼上 | 選取 |
| `Ctrl+X` | 剪下 | 選取 |
| `Delete` | 刪除選取 | 編輯 |
| `←` `→` | 移動選取 (時間) | 編輯 |
| `↑` `↓` | 移動選取 (音高) | 編輯 |
| `Shift+←→` | 調整長度 | 編輯 |
| `Ctrl+滾輪` | 縮放 | 瀏覽 |
| `滾輪` | 水平捲動 | 瀏覽 |
| `Ctrl+S` | 儲存專案 | 檔案 |
| `Ctrl+Shift+S` | 另存新檔 | 檔案 |
| `Ctrl+E` | 匯出 MIDI | 檔案 |

> 所有快捷鍵可在設定中全域關閉。關閉後僅保留 Ctrl 組合鍵。

---

## 5. UI/UX 設計

### 5.1 整體佈局

```
┌─────────────────────────────────────────────────────────┐
│ 漸層標題: "編曲器" (紫霧色)                                │
├───────────┬─────────────────────────────────────────────┤
│           │ Toolbar Row 1:                              │
│           │ [●錄音][▶播放][■停止] | [↩↪✕] | [匯入][匯出]  │
│  Track    │ Toolbar Row 2:                              │
│  List     │ 時值[♩▾] 拍號[4/4▾] BPM[120] □Snap  N音符   │
│           ├─────────────────────────────────────────────┤
│  [T1] ●s  │                                             │
│  [T2]  s  │            Note Roll                        │
│  [T3]  s  │         (Piano Roll Grid)                   │
│  [T4]  s  │                                             │
│           │  小節線 │ 拍線 │ 細分線                        │
│  [+ 新增]  │  ──── 青色音符 / 紅色休止符 ────              │
│           │                                             │
│           ├─────────────────────────────────────────────┤
│           │         Clickable Piano (36 keys)           │
└───────────┴─────────────────────────────────────────────┘
```

### 5.2 軌道列表 (Track List Panel)

左側窄面板 (寬度 ~160px)：

```
┌──────────────┐
│ 主旋律   ● S │  ← 活動軌 (高亮)
│ 低音     ○ S │
│ 和弦     ○ S │
│ 裝飾     ○ S │
├──────────────┤
│   [+ 新增軌]  │
└──────────────┘
```

- 點擊軌道名稱 → 切換活動軌道
- `●` 靜音切換 (Mute)
- `S` 獨奏切換 (Solo)
- 雙擊名稱 → 重新命名
- 右鍵 → 刪除軌道、變更顏色
- 活動軌道左側顯示金墨色指示條 (3px)

### 5.3 Note Roll 視覺設計

#### 5.3.1 格線層次

| 層次 | 顏色 | 粗細 | 觸發條件 |
|------|------|------|----------|
| 小節線 | `#3A4050` | 1.5px | 每拍號週期 |
| 拍線 | `#2A3040` | 1.0px | 每拍 |
| 細分線 | `#1E2530` | 0.5px | 1/8 或 1/16 (依縮放等級) |

小節線上方 Header (20px) 顯示小節號碼。

#### 5.3.2 音符視覺

| 狀態 | 填色 | 邊框 | 說明 |
|------|------|------|------|
| 一般 | 軌道色 80% | 無 | 標準狀態 |
| 選取 | `#40FFFF` | 軌道色 1.5px | 單選或框選 |
| 拖曳中 | 軌道色 55% alpha | `#00F0FF` 1.5px | 半透明預覽 |
| Flash | `ACCENT_GLOW` | 白色 2.0px | 350ms 新增回饋 |
| Ghost | 軌道色 20% alpha | 無 | 非活動軌道的音符 |

#### 5.3.3 休止符視覺

| 狀態 | 填色 | 說明 |
|------|------|------|
| 一般 | `#FF4444` 25% alpha | 紅色半透明橫條，跨全音域高度 |
| 選取 | `#FF6666` 50% alpha | 加亮 |

休止符不顯示為特定音高的方塊，而是整個格位高度的紅色條帶，
視覺上表達「這裡故意留空」。

#### 5.3.4 游標

| 屬性 | 規格 |
|------|------|
| 外觀 | 青色垂直線 (`#00F0FF`), 2px 寬 |
| 行為 | 輸入音符後自動前進一個時值 |
| 播放時 | 跟隨播放位置移動 |
| 點擊 | 點擊空白區域移動游標 |

### 5.4 工具列設計

#### Row 1: 傳輸 + 編輯 + 檔案

```
[● 錄音] [▶ 播放] [■ 停止]  │  [↩][↪][✕]  │  ──stretch──  │  [匯入] [匯出] [存檔]
```

- 錄音按鈕：暗紅背景 → 按下後亮紅 + 文字變「■ 停止」
- 播放按鈕：accent 色 (青色)
- 編輯群組：IconButton with tooltip

#### Row 2: 設定

```
時值 [♩ 四分 ▾]  拍號 [4/4 ▾]  BPM [120 ▲▼]  [□ Snap]  ──stretch──  42 音符 · 8 小節
```

- 時值選擇器：下拉 + 數字鍵快捷
- 拍號選擇器：下拉選單
- BPM：SpinBox (40~300)
- Snap 核取方塊：控制格線吸附
- 統計資訊：右側灰字

### 5.5 互動行為細節

#### 5.5.1 滑鼠行為 (單工具模式)

```
Left Click:
  ├─ on empty cell     → Place note (current duration, at grid snap)
  ├─ on note body      → Select note (prepare for drag)
  ├─ on note right edge → Start resize drag
  └─ on header area    → Move cursor to clicked time

Left Drag (after 4px threshold):
  ├─ from empty cell   → (with Shift) Marquee selection
  ├─ from note body    → Move note (time + pitch)
  └─ from note edge    → Resize note duration

Right Click:
  ├─ on note           → Delete note
  └─ on empty          → Context menu (paste, select all)

Wheel:
  ├─ plain             → Horizontal scroll
  └─ + Ctrl            → Zoom (centered on cursor)
```

#### 5.5.2 拖曳預覽

拖曳時顯示半透明「影子」在預期放置位置，
鬆開滑鼠才真正移動音符。4px 門檻防止誤觸。

#### 5.5.3 框選行為

Shift + 左鍵拖曳繪製矩形選取框。
框內所有音符 (含休止符) 進入選取狀態。
選取後可整體拖曳移動、Delete 刪除、Ctrl+C 複製。

---

## 6. 資料模型與架構

### 6.1 核心資料類別

#### 6.1.1 新增：BeatNote (取代 EditableNote)

```python
@dataclass
class BeatNote:
    """音符 — 以拍為時間單位。"""
    time_beats: float          # 在拍時間軸上的位置
    duration_beats: float      # 時值 (拍)
    note: int                  # MIDI 音高 (48~83)
    velocity: int = 100        # 力度 (v1 固定)
    track: int = 0             # 軌道索引
```

#### 6.1.2 新增：BeatRest

```python
@dataclass
class BeatRest:
    """休止符 — 以拍為時間單位。"""
    time_beats: float          # 位置
    duration_beats: float      # 時值
    track: int = 0             # 軌道索引
```

#### 6.1.3 新增：Track

```python
@dataclass
class Track:
    """單一軌道的狀態。"""
    name: str = ""
    color: str = "#00F0FF"
    channel: int = 0           # MIDI channel (0~15)
    muted: bool = False
    solo: bool = False
```

#### 6.1.4 重構：EditorSequence (取代 NoteSequence)

```python
class EditorSequence:
    """多軌、拍為基礎的音符序列。"""

    # 狀態
    tracks: list[Track]
    notes: list[BeatNote]       # 所有軌道的音符
    rests: list[BeatRest]       # 所有軌道的休止符
    cursor_beats: float         # 游標位置 (拍)
    active_track: int           # 活動軌道索引

    # 設定
    tempo_bpm: float            # BPM
    time_signature: tuple[int, int]  # (numerator, denominator)
    step_duration_beats: float  # 當前步進時值

    # Undo/Redo
    _undo_stack: list[Snapshot]  # 深拷貝快照
    _redo_stack: list[Snapshot]
    _MAX_UNDO = 100

    # CRUD
    def add_note(self, midi_note: int) -> None
    def add_rest(self) -> None
    def delete_items(self, indices: list[int]) -> None
    def move_items(self, indices: list[int], dt: float, dp: int) -> None
    def copy_items(self, indices: list[int]) -> list[BeatNote | BeatRest]
    def paste_items(self, items: list, at_beat: float) -> None
    def resize_item(self, index: int, new_duration: float) -> None

    # Track management
    def add_track(self, name: str = "") -> int
    def remove_track(self, index: int) -> None
    def set_active_track(self, index: int) -> None

    # Conversion
    def to_midi_file_events(self) -> list[MidiFileEvent]
    def to_project_dict(self) -> dict
    @classmethod
    def from_project_dict(cls, data: dict) -> EditorSequence
    @classmethod
    def from_midi_file_events(cls, events: list[MidiFileEvent], tempo_bpm: float) -> EditorSequence

    # Queries
    @property
    def bar_count(self) -> int
    @property
    def beats_per_bar(self) -> int
    def notes_in_track(self, track: int) -> list[BeatNote]
    def items_in_rect(self, t0: float, t1: float, n0: int, n1: int) -> list[int]
```

### 6.2 與現有架構的關係

```
                    現有 (不動)                    新增
                ┌──────────────┐          ┌──────────────────┐
                │ MidiFileEvent│          │   BeatNote       │
                │ MidiFileInfo │   ←→     │   BeatRest       │
                │ MidiFileParser│  轉換   │   EditorSequence │
                └──────┬───────┘          └────────┬─────────┘
                       │                           │
                ┌──────▼───────┐          ┌────────▼─────────┐
                │ MidiFilePlayer│         │   EditorView     │
                │ (播放引擎)     │  ←─────  │   (GUI)          │
                └──────────────┘  events  └──────────────────┘
                                                   │
                                          ┌────────▼─────────┐
                                          │   NoteRoll v2    │
                                          │   TrackListPanel  │
                                          │   ClickablePiano  │
                                          └──────────────────┘
```

#### 轉換路徑

- **EditorSequence → MidiFileEvent**: 播放 / 匯出時，
  `time_seconds = time_beats * (60.0 / tempo_bpm)`
- **MidiFileEvent → EditorSequence**: 匯入時，
  `time_beats = time_seconds / (60.0 / tempo_bpm)`
- **EditorSequence → Project JSON**: 存檔
- **Project JSON → EditorSequence**: 開檔

### 6.3 模組結構 (新增檔案)

```
cyber_qin/
├── core/
│   ├── beat_sequence.py      # NEW: BeatNote, BeatRest, Track, EditorSequence
│   └── project_file.py       # NEW: .cqp 讀寫 (JSON + gzip)
├── gui/
│   ├── views/
│   │   └── editor_view.py    # MODIFIED: 使用 EditorSequence, 多軌 UI
│   └── widgets/
│       ├── note_roll.py      # MODIFIED: 拍為基礎格線, 休止符渲染, Ghost Notes
│       ├── track_list.py     # NEW: 軌道列表面板
│       └── clickable_piano.py # MINOR: 聲音回饋
```

### 6.4 Signal Flow (重構後)

```
ClickablePiano.note_clicked(midi_note)
  │
  ▼
EditorView._on_note_clicked(midi_note)
  ├── sequence.add_note(midi_note)  ← 加入活動軌道, 游標前進
  ├── _update_ui_state()
  │     ├── note_roll.set_data(sequence.notes, sequence.rests)
  │     ├── note_roll.set_cursor(sequence.cursor_beats)
  │     ├── note_roll.set_ghost_notes(non_active_track_notes)
  │     ├── track_list.update_stats()
  │     └── toolbar.update_counts()
  └── note_roll.flash_at_beat(cursor_before)

NoteRoll.item_moved(indices, dt_beats, dp)
  │
  ▼
EditorView._on_items_moved(indices, dt, dp)
  ├── sequence.move_items(indices, dt, dp)
  └── _update_ui_state()

TrackList.track_activated(index)
  │
  ▼
EditorView._on_track_activated(index)
  ├── sequence.set_active_track(index)
  └── _update_ui_state()  ← Ghost Notes 切換
```

---

## 7. 實作路線圖

### Phase 1: 核心重構 (Foundation)

**目標**：拍為基礎的資料模型 + 單軌增強版 Piano Roll

| # | 任務 | 檔案 | 估計工時 |
|---|------|------|----------|
| 1.1 | `BeatNote`, `BeatRest`, `Track` dataclass | `beat_sequence.py` (新) | S |
| 1.2 | `EditorSequence` 核心 CRUD + Undo | `beat_sequence.py` | M |
| 1.3 | 拍號 → 小節線計算邏輯 | `beat_sequence.py` | S |
| 1.4 | `to_midi_file_events()` / `from_midi_file_events()` 轉換 | `beat_sequence.py` | M |
| 1.5 | 單元測試 (BeatNote, EditorSequence) | `test_beat_sequence.py` (新) | M |
| 1.6 | NoteRoll 改為拍基礎格線 + 小節線 + 休止符渲染 | `note_roll.py` | L |
| 1.7 | EditorView 切換到 EditorSequence | `editor_view.py` | M |
| 1.8 | 時值選擇器 UI (ComboBox + 數字鍵快捷) | `editor_view.py` | S |
| 1.9 | 拍號選擇器 UI | `editor_view.py` | S |
| 1.10 | 休止符輸入 (`0` 鍵) | `editor_view.py` | S |

**驗收標準**：
- 可以用數字鍵切換時值 + 點擊琴鍵輸入音符
- 小節線正確對應拍號
- 休止符以紅色橫條顯示
- 匯出的 MIDI 節奏正確

### Phase 2: 多軌 + 進階編輯

**目標**：多軌系統 + 框選 + 複製貼上

| # | 任務 | 檔案 |
|---|------|------|
| 2.1 | TrackListPanel widget | `track_list.py` (新) |
| 2.2 | 多軌 EditorSequence 邏輯 | `beat_sequence.py` |
| 2.3 | Ghost Notes 渲染 | `note_roll.py` |
| 2.4 | 框選 (Marquee Selection) | `note_roll.py` |
| 2.5 | 複製 / 貼上 / 剪下 | `editor_view.py` |
| 2.6 | 音符 Resize (拖曳右邊緣) | `note_roll.py` |
| 2.7 | 右鍵刪除 | `note_roll.py` |
| 2.8 | MIDI Type 1 多軌匯出 | `midi_writer.py` (修改) |
| 2.9 | 多軌單元測試 | `test_beat_sequence.py` |

**驗收標準**：
- 4 軌預設，可新增至 12 軌
- Ghost Notes 正確顯示
- 框選 → 移動 / 刪除 / 複製正常運作
- 多軌 MIDI 匯出包含正確 Channel

### Phase 3: 專案檔 + 體驗打磨

**目標**：持久化 + 聲音 + 體驗優化

| # | 任務 | 檔案 |
|---|------|------|
| 3.1 | `.cqp` 專案檔讀寫 | `project_file.py` (新) |
| 3.2 | 自動儲存 (60s interval) | `editor_view.py` |
| 3.3 | 即時聲音回饋 (輸入 + 播放) | `clickable_piano.py` + `app_shell.py` |
| 3.4 | 播放游標跟隨 | `note_roll.py` |
| 3.5 | 完整鍵盤快捷鍵系統 | `editor_view.py` |
| 3.6 | 快捷鍵開關設定 | `app_shell.py` |
| 3.7 | Snap 開關 + Ctrl 臨時取消 | `note_roll.py` |
| 3.8 | 單元測試 (專案檔, 快捷鍵) | `test_project_file.py` (新) |

**驗收標準**：
- 專案存讀正常、自動儲存運作
- 輸入音符時發聲
- 所有快捷鍵可開關
- Snap 行為符合設計

### 里程碑

| 版本 | 內容 | Phase |
|------|------|-------|
| v0.5.0 | 拍基礎編輯 + 休止符 + 拍號 | Phase 1 |
| v0.6.0 | 多軌 + 框選 + Ghost Notes | Phase 2 |
| v0.7.0 | 專案檔 + 聲音 + 快捷鍵 | Phase 3 |

---

## 附錄 A: 設計決策記錄

### A.1 為什麼用「拍」而不是「秒」？

| | 拍基礎 | 秒基礎 (現狀) |
|--|--------|-------------|
| 改 BPM | 音符位置不變，只改播放速度 | 需要重算所有位置 |
| 拍號小節線 | 整數倍，精確對齊 | 浮點累積誤差 |
| 量化 | 直接 round 到格線 | 需要 BPM 轉換再 round |
| MIDI 匯出 | 乘法轉換 (beats × TPB) | 需要 BPM 參照 |

### A.2 為什麼休止符是獨立資料物件？

替代方案：推算空白區間。
問題：使用者意圖無法區分「故意的休止」和「還沒寫到」。
獨立物件可以：
- 被選取、移動、刪除
- 有明確時值 (四分休止 vs 八分休止)
- 紅色視覺化

### A.3 為什麼不用 Staff Notation？

五線譜排版是一個獨立的巨大工程 (MuseScore 核心引擎 ~50 萬行)。
Piano Roll 已經是最直覺的時間 × 音高視圖，
加上紅色休止符和明確的小節線，節奏結構已經一目了然。

---

## 附錄 B: 名詞對照表

| 中文 | English | 說明 |
|------|---------|------|
| 拍 | Beat | 時間單位，4/4 拍中一個四分音符 = 1 拍 |
| 小節 | Bar / Measure | 拍號週期，4/4 中 = 4 拍 |
| 時值 | Duration | 音符長度 |
| 休止符 | Rest | 明確標記的靜音段 |
| 格線 | Grid | Piano Roll 上的時間分割線 |
| 框選 | Marquee Selection | 拖曳矩形選取多個物件 |
| 量化 | Quantize | 對齊到格線 |
| Ghost Notes | Ghost Notes | 半透明顯示非活動軌道音符 |
| 活動軌道 | Active Track | 當前接收輸入的軌道 |
