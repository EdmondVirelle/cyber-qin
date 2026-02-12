# 賽博琴仙 Cyber Qin Xian

**用真實鋼琴演奏遊戲中的古琴 — Play a real piano, and the game character plays in sync.**

[![CI](https://github.com/EdmondVirelle/cyber-qin/actions/workflows/ci.yml/badge.svg)](https://github.com/EdmondVirelle/cyber-qin/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![Version](https://img.shields.io/badge/Version-0.8.0-green)
![Tests](https://img.shields.io/badge/Tests-180%20passed-brightgreen)

---

## 簡介

**賽博琴仙** 是一款即時 MIDI-to-Keyboard 映射工具，專為《燕雲十六聲》(*Where Winds Meet*) 等遊戲設計。將 USB MIDI 鍵盤（如 Roland FP-30X）的琴鍵訊號，以 **< 2ms 延遲** 轉換為 DirectInput 掃描碼按鍵，讓遊戲角色與你的演奏完全同步。

支援即時演奏與 MIDI 檔案自動播放兩種模式，內建智慧移調、八度摺疊、碰撞去重等預處理管線，並提供 5 種可切換的鍵位配置方案。

---

## 展示

> ![Demo Screenshot](docs/screenshot-placeholder.png)
>
> *即時演奏模式 — 鋼琴鍵盤視覺化 + 低延遲監控*

---

## 功能特色

### 核心能力

| 功能 | 說明 |
|------|------|
| **即時 MIDI 映射** | MIDI callback 直接在 rtmidi 執行緒上觸發 `SendInput`，不經過 Qt 事件佇列，延遲 < 2ms |
| **5 種鍵位方案** | 燕雲十六聲 36 鍵、FF14 32 鍵、通用 24/48/88 鍵，執行時即時切換 |
| **智慧 MIDI 預處理** | 3 階段管線：全曲智慧移調 → 八度摺疊 → 碰撞去重（詳見[技術深潛](#智慧-midi-預處理管線)） |
| **MIDI 檔案自動播放** | 匯入 `.mid` 檔案，0.25x - 2.0x 變速控制，可拖曳進度條，4 拍節拍器倒數 |
| **修飾鍵閃擊技術** | `Shift↓ → Key↓ → Shift↑` 以單一批次送出，防止修飾鍵污染後續和弦 |
| **自動重連** | MIDI 裝置斷線時每 3 秒輪詢，插回自動恢復 |
| **卡鍵看門狗** | 偵測按住超過 10 秒的按鍵並自動釋放，防止遊戲內角色卡死 |

### 使用者介面

| 功能 | 說明 |
|------|------|
| **賽博墨韻主題** | 武俠賽博龐克暗色主題，霓虹青 (`#00F0FF`) + 宣紙白暖色調 |
| **向量圖示** | 全部以 QPainter 繪製，無外部圖片依賴，任意縮放不失真 |
| **動態鋼琴鍵盤** | 即時顯示按鍵狀態，帶霓虹光暈動畫效果 |
| **曲庫管理** | 匯入、搜尋、依名稱 / BPM / 音符數 / 時長排序 |
| **底部播放列** | Spotify 風格，含迷你鋼琴、進度條、速度控制 |

---

## 系統架構

### 資料流

```
                          即時演奏模式
┌─────────────┐    USB    ┌──────────────┐  callback  ┌───────────┐  lookup  ┌──────────────┐  SendInput  ┌──────┐
│ Roland FP-30X│─────────→│ python-rtmidi │──────────→│ KeyMapper │────────→│ KeySimulator │───────────→│ Game │
└─────────────┘           └──────────────┘            └───────────┘         └──────────────┘            └──────┘
                            (rtmidi thread)                                  (scan codes)
                                  │
                           Qt signals (async)
                                  │
                         Qt Main Thread → GUI 更新


                          自動播放模式
┌───────────┐  parse  ┌─────────────────┐  preprocess  ┌──────────────────┐  timed events  ┌──────────────┐
│ .mid 檔案 │────────→│ MidiFileParser  │────────────→│ MidiPreprocessor │──────────────→│ PlaybackWorker│
└───────────┘         └─────────────────┘              └──────────────────┘               └──────┬───────┘
                                                                                                 │
                                                              lookup + SendInput                 │
                                                       ┌───────────┬──────────────┐←────────────┘
                                                       │ KeyMapper │ KeySimulator │→ Game
                                                       └───────────┴──────────────┘
```

### 延遲最佳化路徑

```
MIDI Note On 訊號
    │
    ├── [rtmidi C++ thread] ← SetThreadPriority(TIME_CRITICAL)
    │       │
    │       ├── KeyMapper.lookup()        ~0.01ms  (dict 查表)
    │       ├── KeySimulator.press()      ~0.05ms  (SendInput syscall)
    │       └── Qt signal emit            ~0.00ms  (跨執行緒佇列，非同步)
    │
    └── 總延遲: < 2ms (MIDI USB polling + callback + SendInput)

    ※ GUI 更新走 Qt 訊號佇列，不佔用關鍵路徑
```

---

## 技術棧

| 層級 | 技術 | 用途 |
|------|------|------|
| **MIDI I/O** | `mido` + `python-rtmidi` | MIDI 裝置通訊、`.mid` 檔案解析 |
| **鍵盤模擬** | `ctypes` + Win32 `SendInput` | DirectInput 掃描碼按鍵注入 |
| **GUI** | PyQt6 | 桌面介面、事件迴圈、跨執行緒訊號 |
| **建置** | PyInstaller | 單資料夾可執行檔封裝 |
| **CI/CD** | GitHub Actions | 多版本測試 + tag 自動發佈 |
| **程式碼品質** | Ruff + pytest | Linting + 180 項測試 |

---

## 快速開始

### 系統需求

- **作業系統**: Windows 10 / 11（DirectInput 掃描碼僅 Windows 支援）
- **Python**: 3.11 或以上
- **MIDI 裝置**: 任何 USB MIDI 鍵盤（已測試 Roland FP-30X）
- **權限**: 需要以 **系統管理員** 身分執行（`SendInput` 對 DirectInput 遊戲需要提權）

### 安裝

```bash
# 1. 複製專案
git clone https://github.com/EdmondVirelle/cyber-qin.git
cd cyber-qin

# 2. 安裝（含開發依賴）
pip install -e .[dev]
```

### 執行

```bash
# 以管理員身分執行
cyber-qin
```

> **提示**: 若未以管理員身分執行，`SendInput` 對全螢幕 DirectInput 遊戲的按鍵注入會靜默失敗。

### 建置獨立執行檔

```bash
python scripts/build.py
# 輸出: dist/賽博琴仙/ (~95 MB)
```

---

## 開發

### 測試

```bash
# 執行全部 180 項測試（5 個測試檔案）
pytest

# 詳細輸出
pytest -v
```

測試完全模擬 `ctypes.windll` 和 `rtmidi`，不需要實體硬體即可執行。

### Lint

```bash
# 檢查
ruff check .

# 自動修復
ruff check --fix .
```

### 專案統計

| 指標 | 數值 |
|------|------|
| 原始碼行數 | ~5,000 LOC |
| 模組數量 | 26 |
| 測試數量 | 180 |
| 測試檔案 | 5 |
| 測試涵蓋平台 | Python 3.11 / 3.12 / 3.13 |

---

## 專案結構

```
cyber_qin/
├── core/                        # 平台無關核心邏輯
│   ├── constants.py             # Win32 掃描碼、MIDI 範圍、計時常數
│   ├── key_mapper.py            # MIDI 音符 → 按鍵映射查表
│   ├── key_simulator.py         # ctypes SendInput 封裝（DirectInput 掃描碼）
│   ├── midi_listener.py         # python-rtmidi 即時輸入 + 自動重連
│   ├── midi_file_player.py      # MIDI 檔案播放引擎（精準計時 + 4 拍倒數）
│   ├── midi_preprocessor.py     # 智慧移調 + 八度摺疊 + 碰撞去重管線
│   ├── mapping_schemes.py       # 5 種可切換鍵位方案註冊表
│   └── priority.py              # 執行緒優先權 + 高解析度計時器
├── gui/                         # PyQt6 使用者介面
│   ├── app_shell.py             # QMainWindow 主框架（Spotify 風格佈局）
│   ├── icons.py                 # QPainter 向量圖示提供器
│   ├── theme.py                 # 「賽博墨韻」暗色主題系統
│   ├── views/
│   │   ├── live_mode_view.py    # 即時演奏頁面
│   │   └── library_view.py      # 曲庫管理頁面
│   └── widgets/
│       ├── piano_display.py     # 動態鋼琴鍵盤（霓虹光暈效果）
│       ├── mini_piano.py        # 底部迷你鋼琴視覺化
│       ├── sidebar.py           # 側邊欄導航
│       ├── now_playing_bar.py   # 底部播放控制列
│       ├── track_list.py        # 曲目清單元件
│       ├── progress_bar.py      # 可拖曳進度條
│       ├── speed_control.py     # 播放速度控制器
│       ├── log_viewer.py        # 即時事件日誌
│       ├── status_bar.py        # 狀態列
│       └── animated_widgets.py  # 動畫基礎元件
└── utils/
    ├── admin.py                 # UAC 提權檢查
    └── ime.py                   # 輸入法偵測
```

---

## 技術深潛

### 1. 延遲最佳化：為何不走 Qt 事件佇列

遊戲演奏的核心需求是 **低延遲** — 從按下琴鍵到遊戲角色出聲，玩家可感知的上限約 10ms。

典型架構會將 MIDI 事件透過 Qt 訊號傳遞到主執行緒再處理，但 Qt 的事件佇列在 GUI 繁忙時（如重繪動畫）可能引入 5-15ms 的額外延遲。

本專案的做法是 **直接在 rtmidi 的 C++ callback 執行緒上** 執行鍵盤模擬：

```python
# app_shell.py — MidiProcessor.on_midi_event()
# 此函式在 rtmidi callback thread 上執行

def on_midi_event(self, event_type, note, velocity):
    # 1. 首次呼叫時提升執行緒優先權
    if not self._priority_set:
        set_thread_priority_realtime()  # TIME_CRITICAL
        self._priority_set = True

    # 2. 關鍵路徑：查表 + SendInput（< 0.1ms）
    if event_type == "note_on":
        mapping = self._mapper.lookup(note)      # dict lookup
        if mapping is not None:
            self._simulator.press(note, mapping)  # SendInput syscall

    # 3. GUI 更新走非同步訊號（不阻塞關鍵路徑）
    self.note_event.emit(event_type, note, velocity)
```

配合 `timeBeginPeriod(1)` 將系統計時器解析度降至 1ms，以及 `SetThreadPriority(TIME_CRITICAL)` 提升執行緒排程優先權，實現端到端 < 2ms 延遲。

### 2. 修飾鍵閃擊技術（Modifier Flash）

遊戲的 36 鍵模式使用 Shift / Ctrl 修飾鍵表示升降號。若在和弦中先按下 Shift 再按 Key，Shift 可能「洩漏」到同時按下的其他音符，導致遊戲誤判按鍵。

解決方案：將修飾鍵的按下與釋放 **包裹在同一次 `SendInput` 批次呼叫** 中：

```python
# key_simulator.py — KeySimulator.press()

def press(self, midi_note, mapping):
    mod_scan = _modifier_scan(mapping.modifier)
    if mod_scan is not None:
        # 三個事件作為一個原子批次送出
        _send(
            _make_input(mod_scan, key_up=False),           # Shift ↓
            _make_input(mapping.scan_code, key_up=False),  # Key ↓
            _make_input(mod_scan, key_up=True),            # Shift ↑
        )
    else:
        _send(_make_input(mapping.scan_code, key_up=False))
```

`SendInput` 的設計保證同一批次中的事件不會被其他行程的輸入事件插隊，確保修飾鍵的作用範圍精確限定在單一按鍵上。

### 3. 智慧 MIDI 預處理管線

將任意 MIDI 檔案適配到遊戲有限的音域範圍（如 36 鍵 = C3-B5），需要一套自動化的音符轉換管線：

```
原始 MIDI 事件
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Stage 1: 智慧全曲移調                                  │
│ 嘗試 -48 ~ +48 半音（12 的倍數），選擇使最多音符        │
│ 落入可演奏範圍的位移量。同分時取絕對值最小者。           │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Stage 2: 八度摺疊                                      │
│ 剩餘超出範圍的音符逐一 ±12 半音摺疊至範圍內。           │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Stage 3: 碰撞去重                                      │
│ 摺疊後可能產生同一時間點、同一音高的重複音符。            │
│ 移除重複，保留最後一個 note_off（最長延音）。            │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Stage 4: 力度正規化                                    │
│ 所有 note_on 力度統一為 127（遊戲不區分力度）。          │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Stage 5: 60fps 時間量化                                │
│ 將事件時間對齊至 ~16.67ms 格線，消除微延遲。            │
└──────────────────────────────────────────────────────┘
    │
    ▼
處理後事件（按時間排序，note_off 優先於 note_on）
```

### 4. ctypes INPUT 結構體陷阱

Windows `SendInput` API 要求 `INPUT` 結構體的大小精確為 40 bytes（64-bit）。結構體內部使用 union 包含 `MOUSEINPUT`、`KEYBDINPUT`、`HARDWAREINPUT` 三種類型。

若 union 中 **省略了最大的成員 `MOUSEINPUT`**（32 bytes），`sizeof(INPUT)` 會變成 32 而非 40，導致 `SendInput` **靜默返回 0** 且不送出任何按鍵 — 不報錯、不丟例外，只是完全無效。

```python
# 必須包含 MOUSEINPUT 作為 union 成員
class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [
            ("mi", MOUSEINPUT),      # ← 最大成員，決定 union 大小
            ("ki", KEYBDINPUT),
            ("hi", HARDWAREINPUT),
        ]
    _anonymous_ = ("_union",)
    _fields_ = [("type", ctypes.wintypes.DWORD), ("_union", _INPUT_UNION)]
```

---

## CI/CD

### 持續整合

每次推送至 `main` 或開啟 Pull Request 時自動執行：

| 工作 | 環境 | 內容 |
|------|------|------|
| **測試** | `windows-latest` x Python 3.11 / 3.12 / 3.13 | `pip install -e .[dev]` → `pytest -q` |
| **Lint** | `ubuntu-latest` x Python 3.13 | `ruff check .` |

### 自動發佈

推送 `v*` 標籤時觸發：

1. 安裝依賴 + 生成圖示
2. PyInstaller 建置（`onedir` + `windowed` + `uac_admin`）
3. 壓縮為 `.zip`
4. 建立 GitHub Release 並上傳附件

```bash
# 觸發一次發佈
git tag v0.2.0
git push origin v0.2.0
```

---

## 鍵位方案一覽

| 方案 | 鍵數 | MIDI 範圍 | 佈局 | 適用遊戲 |
|------|------|-----------|------|----------|
| **燕雲十六聲 36 鍵** | 36 | C3 - B5 | 3 x 12 (ZXC / ASD / QWE + Shift/Ctrl) | 燕雲十六聲 |
| **FF14 32 鍵** | 32 | C3 - G5 | 4 x 8 (ASDF / QWER / 1234 / Ctrl+1~8) | Final Fantasy XIV |
| **通用 24 鍵** | 24 | C3 - B4 | 2 x 12 (ZXC / QWE + Shift/Ctrl) | 通用 |
| **通用 48 鍵** | 48 | C2 - B5 | 4 x 12 (數字行 / ZXC / ASD / QWE) | 通用 |
| **通用 88 鍵** | 88 | A0 - C8 | 8 x 11 (多層 Shift/Ctrl 組合) | 通用（全鋼琴） |

---

## 致謝

- [mido](https://github.com/mido/mido) — Python MIDI 程式庫
- [python-rtmidi](https://github.com/SpotlightKid/python-rtmidi) — 低延遲跨平台 MIDI I/O
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — Python Qt 6 綁定
- [PyInstaller](https://pyinstaller.org/) — Python 應用程式封裝工具
- [Ruff](https://github.com/astral-sh/ruff) — 極速 Python linter
- 《燕雲十六聲》(*Where Winds Meet*) — 網易旗下 Everstone Studio 開發的武俠開放世界遊戲
