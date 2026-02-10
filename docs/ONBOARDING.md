# 賽博琴仙 v0.4.0 — 從零開始的系統架構導覽

> **適用對象**：零經驗到中階工程師。從 Python 基礎一路講到即時系統設計、Windows 核心 API、
> 智慧前處理演算法（含流水摺疊）、錄音與編輯系統、CI/CD 自動化。每個設計決策都附上「為什麼這樣做」的推理過程。

---

## 目錄

1. [這個程式在做什麼？](#1-這個程式在做什麼)
2. [Python 基礎：給零基礎的你](#2-python-基礎給零基礎的你)
3. [技術棧與套件選型](#3-技術棧與套件選型)
4. [專案資料夾結構](#4-專案資料夾結構)
5. [核心原理：從琴鍵到遊戲按鍵](#5-核心原理從琴鍵到遊戲按鍵)
6. [每個檔案在做什麼？](#6-每個檔案在做什麼)
7. [智慧前處理管線：五階段演算法設計](#7-智慧前處理管線五階段演算法設計)
8. [搜尋與排序的 UI 架構](#8-搜尋與排序的-ui-架構)
9. [即時系統設計：執行緒、延遲與優先權](#9-即時系統設計執行緒延遲與優先權)
10. [測試策略與 Mock 架構](#10-測試策略與-mock-架構)
11. [CI/CD 管線：自動測試與發佈](#11-cicd-管線自動測試與發佈)
12. [建置與打包系統](#12-建置與打包系統)
13. [如何安裝與執行](#13-如何安裝與執行)
14. [常見陷阱與學到的教訓](#14-常見陷阱與學到的教訓)
15. [詞彙表](#15-詞彙表)

---

## 1. 這個程式在做什麼？

想像你有一台**真的 MIDI 鍵盤**（例如 Roland FP-30X），你想在遊戲《燕雲十六聲》裡面彈琴。

問題在於——遊戲只認鍵盤按鍵（Q、W、E、Shift+Z 這些），完全不認 MIDI 裝置。

**賽博琴仙**就是這座橋：

```
你的手指 → 鋼琴琴鍵 → USB → MIDI 訊號 → 賽博琴仙翻譯 → 模擬鍵盤掃描碼 → 遊戲角色彈琴
```

同時，它也能讀取 `.mid` 檔案，經過**智慧前處理**（自動移調、八度摺疊、碰撞去重、力度正規化、時間量化）後，按照時間軸自動演奏——讓遊戲角色演出完美的鋼琴表演。

### 1.1 核心特性一覽

| 功能 | 說明 |
|------|------|
| 即時演奏 | MIDI 鍵盤 → 遊戲按鍵，端到端延遲 < 2ms |
| MIDI 檔案播放 | 9 階段智慧前處理（含流水摺疊）+ 精準計時播放 |
| 即時錄音 | 錄製 MIDI 演奏，Auto-Tune 後儲存為 `.mid` 檔案 |
| 虛擬鍵盤編輯 | 滑鼠點選輸入音符 + piano roll 時間軸 + undo/redo |
| 多方案支援 | 5 種鍵位方案（36/32/24/48/88 鍵） |
| 曲庫管理 | 搜尋、多維排序、持久化儲存 |
| 賽博墨韻介面 | 深色主題 + 即時琴鍵動畫 |

---

## 2. Python 基礎：給零基礎的你

> 已經會 Python 的讀者可以跳到[第 3 節](#3-技術棧與套件選型)。

**核心概念速覽**：

| 概念 | 說明 | 本專案範例 |
|------|------|-----------|
| 變數 | 給資料取名字 | `name = "賽博琴仙"` |
| 函式 `def` | 可重複使用的動作 | `def lookup(midi_note)` |
| 類別 `class` | 一整套東西的藍圖 | `class KeyMapper` |
| 字典 `dict` | 鍵值對查詢表，O(1) 查找 | `{60: KeyMapping(...)}` |
| 型別提示 | 給人看的參數備註 | `def lookup(self, midi_note: int) -> KeyMapping \| None` |

**dataclass** 是本專案中大量使用的模式——自動產生 `__init__`、`__eq__` 等方法：

```python
@dataclass(frozen=True, slots=True)
class KeyMapping:
    scan_code: int
    modifier: Modifier
    label: str
```

`frozen=True` 表示不可變（天然執行緒安全），`slots=True` 減少記憶體用量並加速屬性存取。

---

## 3. 技術棧與套件選型

### 3.1 核心依賴

打開 `pyproject.toml`，你會看到：

```toml
[project]
name = "cyber-qin"
version = "0.4.0"

dependencies = [
    "mido>=1.3",
    "python-rtmidi>=1.5",
    "PyQt6>=6.5",
]
```

版本號透過 `importlib.metadata` 在執行期動態讀取，確保唯一來源（Single Source of Truth）。

### 3.2 mido — MIDI 訊息的翻譯官

**MIDI**（Musical Instrument Digital Interface）是音樂設備之間溝通的「語言」。
當你在鋼琴上按一個鍵，鋼琴會透過 USB 傳送這樣的訊息：

```
note_on  channel=0  note=60  velocity=80  time=0
```

意思是：「第 60 號音（中央 C）被按下了，力道 80」。

**mido** 幫我們：
- 列出電腦上有哪些 MIDI 裝置（`mido.get_input_names()`）
- 打開裝置接收訊息（`mido.open_input()`）
- 讀取 .mid 檔案（`mido.MidiFile()`）
- 轉換時間單位（`mido.tick2second()`）——這一點極其重要，因為 MIDI 的 tick 和秒是不同的時間系統

### 3.3 python-rtmidi — 真正跟硬體說話的人

`mido` 是高階介面（好用但自己不會跟硬體溝通），`python-rtmidi` 是底層驅動（真正透過 USB 跟鋼琴對話的 C++ 程式庫）。

關鍵特性：它在**獨立的 C++ 執行緒**上執行 callback。這代表 MIDI 事件的接收不會被 Python GIL 或 Qt 事件迴圈阻塞——這正是我們能做到 < 2ms 延遲的基石。

### 3.4 PyQt6 — 圖形介面框架

**Qt**（發音：cute）是跨平台的圖形介面框架。**PyQt6** 是它的 Python 綁定。

我們用它來蓋：
- 視窗骨架（`QMainWindow`）
- 堆疊頁面切換（`QStackedWidget`）
- 自訂琴鍵動畫（`QPainter` 向量繪製）
- 搜尋框（`QLineEdit`）+ 排序下拉選單（`QComboBox`）
- 跨執行緒通訊（`pyqtSignal` / slot 機制）

```
PyQt6 的 Widget 階層：
QApplication（整個 App）
└── QMainWindow（主視窗 = AppShell）
    ├── Sidebar（側邊欄導航）
    ├── QStackedWidget（可切換的頁面）
    │   ├── LiveModeView（演奏模式頁）
    │   └── LibraryView（曲庫頁）
    │       └── TrackList（搜尋 + 排序 + 卡片列表）
    └── NowPlayingBar（底部播放控制列）
```

### 3.5 ctypes — 直接跟 Windows 核心 API 對話

Windows 有很多內建功能（叫做 **Win32 API**），但它們是用 C 語言寫的。
`ctypes` 讓 Python 能直接呼叫這些 C 函式，不需要額外的 C 擴充模組。

我們用它來：
- **模擬按鍵**：呼叫 `user32.SendInput()` 假裝使用者按了鍵盤
- **檢查管理員權限**：呼叫 `shell32.IsUserAnAdmin()`
- **設定深色標題列**：呼叫 `dwmapi.DwmSetWindowAttribute()`
- **提升執行緒優先權**：呼叫 `kernel32.SetThreadPriority()`
- **設定計時器精度**：呼叫 `winmm.timeBeginPeriod()`

### 3.6 開發工具

| 套件 | 用途 |
|------|------|
| `pytest` | 自動跑 289 個測試，確認程式沒壞 |
| `ruff` | 程式碼風格檢查（比 flake8 快 100 倍以上的 Rust 實作） |
| `pyinstaller` | 打包成免安裝的 .exe |
| `pillow` | 圖示生成（配合 QPainter 輸出多解析度 .ico） |

---

## 4. 專案資料夾結構

```
賽博琴仙/
├── pyproject.toml              ← 專案設定（名稱、版本 0.4.0、依賴、ruff 規則）
├── cyber_qin.spec              ← PyInstaller 打包規格（onedir + UAC admin）
├── CLAUDE.md                   ← 給 AI 助手看的開發指南
│
├── cyber_qin/                  ← 所有程式碼都在這裡（~7,500 LOC / 39 模組）
│   ├── __init__.py             ← 版本號動態讀取（importlib.metadata → pyproject.toml fallback）
│   ├── main.py                 ← 程式入口：權限檢查 → 計時器 → 主題 → 主視窗
│   │
│   ├── core/                   ← 核心邏輯（與 GUI 完全解耦）
│   │   ├── constants.py            ← 掃描碼表、MIDI 範圍、SendInput 常數
│   │   ├── key_mapper.py           ← MIDI 音符 → KeyMapping 翻譯 + 方案切換
│   │   ├── key_simulator.py        ← ctypes SendInput 封裝（含修飾鍵閃按）
│   │   ├── midi_listener.py        ← python-rtmidi callback 封裝
│   │   ├── midi_file_player.py     ← MIDI 檔案解析 + 計時播放引擎
│   │   ├── midi_preprocessor.py    ← 9 階段預處理管線（含流水摺疊）
│   │   ├── midi_recorder.py        ← 即時 MIDI 錄音引擎 [v0.4.0 新增]
│   │   ├── midi_writer.py          ← 錄音匯出 .mid 檔案 [v0.4.0 新增]
│   │   ├── auto_tune.py            ← 錄音後處理：節拍量化 + 音階校正 [v0.4.0 新增]
│   │   ├── note_sequence.py        ← 可變音符序列模型（編輯器用）[v0.4.0 新增]
│   │   ├── mapping_schemes.py      ← 5 種鍵位方案註冊表
│   │   └── priority.py             ← 執行緒優先權 + 計時器精度工具
│   │
│   ├── gui/                    ← 圖形介面
│   │   ├── app_shell.py            ← 主視窗骨架 + MidiProcessor 橋接器
│   │   ├── theme.py                ← 賽博墨韻深色主題（QSS + DWM）
│   │   ├── icons.py                ← QPainter 向量圖示繪製
│   │   ├── views/
│   │   │   ├── live_mode_view.py   ← 演奏模式（裝置連線、琴鍵顯示、錄音控制）
│   │   │   ├── library_view.py     ← 曲庫（匯入、管理、失敗提示）
│   │   │   └── editor_view.py      ← 虛擬鍵盤編輯器 [v0.4.0 新增]
│   │   └── widgets/
│   │       ├── piano_display.py    ← 大鋼琴顯示（動態行列 + 光暈動畫）
│   │       ├── mini_piano.py       ← 迷你鋼琴（底部播放列用的）
│   │       ├── clickable_piano.py  ← 可互動鋼琴（點選輸入音符）[v0.4.0 新增]
│   │       ├── note_roll.py        ← 水平音符時間軸 [v0.4.0 新增]
│   │       ├── sidebar.py          ← 左側導航欄
│   │       ├── now_playing_bar.py  ← 底部播放控制列
│   │       ├── track_list.py       ← 曲目列表（搜尋 + 排序）
│   │       ├── log_viewer.py       ← 事件日誌視窗
│   │       ├── status_bar.py       ← 狀態列（連線、延遲顯示）
│   │       └── animated_widgets.py ← 動畫按鈕等共用元件
│   │
│   └── utils/
│       ├── admin.py                ← 管理員權限檢查 / UAC 提升
│       └── ime.py                  ← 輸入法狀態偵測
│
├── tests/                      ← 289 個自動化測試，8 個檔案
│   ├── test_key_mapper.py
│   ├── test_key_simulator.py
│   ├── test_midi_file_player.py
│   ├── test_midi_preprocessor.py
│   ├── test_mapping_schemes.py
│   ├── test_auto_tune.py           [v0.4.0 新增]
│   ├── test_midi_recorder.py       [v0.4.0 新增]
│   └── test_note_sequence.py       [v0.4.0 新增]
│
├── scripts/                    ← 開發工具腳本
│   ├── build.py                    ← 一鍵建置（自動找 Python 3.13 → venv → 打包）
│   └── generate_icon.py            ← 圖示生成（QPainter + Pillow 多解析度 .ico）
│
├── .github/workflows/          ← CI/CD 管線
│   ├── ci.yml                      ← 持續整合（3 版 Python × Windows + lint）
│   └── release.yml                 ← 自動發佈（v* tag → build → GitHub Release）
│
├── launcher.py                 ← PyInstaller 入口包裝（避免相對匯入問題）
└── docs/
    └── ONBOARDING.md           ← 你正在讀的這份文件
```

---

## 5. 核心原理：從琴鍵到遊戲按鍵

### 5.1 完整流程圖

```
   【你的手指按下鋼琴的中央 C】
              │
              ▼
   ┌────────────────────────┐
   │   Roland FP-30X        │  ← 鋼琴透過 USB 送出 MIDI 位元組
   │   (MIDI 鍵盤)          │     note_on, note=60, velocity=80
   └────────┬───────────────┘
            │ USB (< 1ms)
            ▼
   ┌────────────────────────┐
   │   python-rtmidi         │  ← C++ 層接收原始 MIDI 位元組
   │   (底層驅動)            │     在獨立的 rtmidi 執行緒上運作
   └────────┬───────────────┘
            │ callback (仍在 rtmidi 執行緒)
            ▼
   ┌────────────────────────┐
   │   MidiListener          │  ← 過濾：只留 note_on / note_off
   │   (midi_listener.py)    │     velocity=0 的 note_on → note_off
   └────────┬───────────────┘
            │ callback(event_type, note, velocity)
            ▼
   ┌────────────────────────┐
   │   MidiProcessor         │  ← 「大腦」——仍在 rtmidi 執行緒上
   │   (app_shell.py)        │     ① 首次觸發時提升執行緒優先權
   │                         │     ② 查翻譯表 → note 60 = 按 A 鍵
   │                         │     ③ 模擬按鍵 → 告訴 Windows 按 A
   │                         │     ④ perf_counter 量測延遲
   │                         │     ⑤ 發 Qt 信號 → 通知畫面更新
   └────────┬───────────────┘
            │
      ┌─────┴─────────┐
      ▼               ▼
  【即時按鍵】     【Qt 信號】
  KeySimulator      ↓（自動跨執行緒排隊）
  SendInput()       ↓
      │     ┌───────────────────┐
      │     │  Qt 主執行緒       │
      │     │  更新琴鍵動畫      │
      │     │  更新事件日誌      │
      │     │  更新延遲顯示      │
      │     └───────────────────┘
      ▼
   ┌────────────────────────┐
   │   Windows 作業系統      │  ← 收到 SendInput，以掃描碼送給前景視窗
   └────────┬───────────────┘
            ▼
   ┌────────────────────────┐
   │   燕雲十六聲 遊戲       │  ← 收到 A 鍵掃描碼 → 角色彈出中央 C
   └────────────────────────┘
```

**設計哲學**：按鍵模擬在收到 MIDI 事件的同一個執行緒上立即完成，完全不經過 Qt 事件佇列。這是達到亞毫秒延遲的關鍵。GUI 更新走 Signal/Slot 跨執行緒排隊，慢幾毫秒人眼完全無感。

### 5.2 為什麼用「掃描碼」而不是「虛擬鍵碼」？

鍵盤按鍵有兩種表示法：

| 方式 | 範例 | 用途 |
|------|------|------|
| 虛擬鍵碼（VK） | `VK_A = 0x41` | 一般應用程式（記事本、瀏覽器） |
| 掃描碼（Scan Code） | `A = 0x1E` | 遊戲（DirectInput / Raw Input） |

**為什麼遊戲用掃描碼？** 大部分遊戲用 **DirectInput** 讀取鍵盤輸入。DirectInput 直接跟鍵盤硬體溝通，略過 Windows 的輸入處理管線。它只認掃描碼——那是鍵盤控制器送出的原始硬體編號。

如果你用 `SendInput` 送虛擬鍵碼（不帶 `KEYEVENTF_SCANCODE` 旗標），Windows 會把它插入高階輸入佇列，但 DirectInput 的低階介面完全看不到。結果就是：你的程式瘋狂送按鍵，遊戲紋風不動。

我們在 `constants.py` 裡定義了完整的掃描碼對照表：

```python
SCAN = {
    "Z": 0x2C,  "X": 0x2D,  "C": 0x2E,  "V": 0x2F,  # 低音行
    "A": 0x1E,  "S": 0x1F,  "D": 0x20,  "F": 0x21,  # 中音行
    "Q": 0x10,  "W": 0x11,  "E": 0x12,  "R": 0x13,  # 高音行
    "LSHIFT": 0x2A,  "LCTRL": 0x1D,                   # 修飾鍵
    # ... 共 30+ 個鍵
}
```

### 5.3 翻譯表怎麼運作？

遊戲的 36 鍵模式把鍵盤分成三層（3 行 x 12 鍵 = 36 鍵）：

```
高音 (C5-B5)：  Q  W  E  R  T  Y  U  ← 自然音
               ⇧Q    ^E ⇧R    ⇧T ^U  ← 升降號（Shift / Ctrl 組合）

中音 (C4-B4)：  A  S  D  F  G  H  J
               ⇧A    ^D ⇧F    ⇧G ^J

低音 (C3-B3)：  Z  X  C  V  B  N  M
               ⇧Z    ^C ⇧V    ⇧B ^M
```

（⇧ = Shift, ^ = Ctrl）

在程式碼裡，這就是一個 `dict[int, KeyMapping]`：

```python
_BASE_MAP: dict[int, KeyMapping] = {
    48: KeyMapping(scan_code=0x2C, modifier=NONE,  label="Z"),       # C3
    49: KeyMapping(scan_code=0x2C, modifier=SHIFT, label="Shift+Z"), # C#3
    50: KeyMapping(scan_code=0x2D, modifier=NONE,  label="X"),       # D3
    # ... 一直到 ...
    83: KeyMapping(scan_code=0x16, modifier=NONE,  label="U"),       # B5
}
```

**查詢的時間複雜度**：O(1) 字典查找。在即時路徑上，每一微秒都是寶貴的。

### 5.4 模擬按鍵的魔法：SendInput 與 INPUT 結構體

Windows 的 `SendInput` API 可以「注入」鍵盤事件到作業系統的輸入管線。

```python
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),       # 虛擬鍵碼（我們設為 0）
        ("wScan", ctypes.wintypes.WORD),      # 掃描碼（我們的主角）
        ("dwFlags", ctypes.wintypes.DWORD),   # KEYEVENTF_SCANCODE 旗標
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]
```

**致命陷阱：INPUT 聯合體的大小**

`SendInput` 的第三個參數是 `sizeof(INPUT)`。在 64 位元 Windows 上，它必須等於 **40 位元組**。

`INPUT` 結構體內部是一個 Union（C 語言的聯合體），包含三種輸入型別：
- `MOUSEINPUT`（32 位元組 — 最大的成員）
- `KEYBDINPUT`（24 位元組）
- `HARDWAREINPUT`（8 位元組）

Union 的大小取決於**最大的成員**。如果你省略了 `MOUSEINPUT`（反正我們不用滑鼠），Union 的大小就只有 24 位元組，`sizeof(INPUT)` 變成 32 而不是 40。

結果：`SendInput` **靜靜地回傳 0**（不報錯，不丟例外，什麼都不做）。這是我們踩過最痛的一個坑——你會以為程式完全正常，但遊戲就是不反應。

```python
class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [
            ("mi", MOUSEINPUT),     # 必須包含！即使不用滑鼠
            ("ki", KEYBDINPUT),
            ("hi", HARDWAREINPUT),
        ]
    _anonymous_ = ("_union",)
    _fields_ = [("type", ctypes.wintypes.DWORD), ("_union", _INPUT_UNION)]
```

### 5.5 修飾鍵的閃按（Flash Press）策略

按 `Shift+Z`（C#3）的時候，如果像人那樣「按住 Shift 再按 Z」，會有一個嚴重問題：如果 Shift 按住的時間稍長，下一個快速跟上的音符也會被 Shift 影響。

我們的策略是**閃按修飾鍵**——把三個動作打包成一個 `SendInput` 批次：

```
SendInput 一次送出三個 INPUT：
  ① Shift↓  → ② Z↓  → ③ Shift↑

（Windows 會在同一個 input dispatch cycle 中依序處理）
```

放開 Z 時只需要送 `Z↑`——Shift 早已放開了。

```python
def press(self, midi_note: int, mapping: KeyMapping) -> None:
    mod_scan = _modifier_scan(mapping.modifier)
    if mod_scan is not None:
        _send(
            _make_input(mod_scan, key_up=False),    # Shift↓
            _make_input(mapping.scan_code, key_up=False),  # Z↓
            _make_input(mod_scan, key_up=True),     # Shift↑
        )
    else:
        _send(_make_input(mapping.scan_code, key_up=False))
    self._active[midi_note] = (mapping, time.monotonic())
```

---

## 6. 每個檔案在做什麼？

### 6.1 `main.py` — 程式入口

```
啟動 → 設定 logging → 建立 QApplication → 檢查管理員權限（UAC 彈窗）
     → 要求 1ms 計時器精度 → 套用賽博墨韻主題 → 建立 AppShell → 進入事件迴圈
     → 結束時歸還計時器精度
```

權限檢查是**非阻塞式**的：如果使用者選擇不提升權限，程式照樣能跑，只是遊戲可能收不到按鍵。

### 6.2 `core/constants.py` — 常數倉庫

所有「不會變的數字」都放在這裡，形成整個系統的參數配置中心：

| 常數群組 | 內容 |
|----------|------|
| `SCAN` | 30+ 個鍵的掃描碼字典 |
| `MIDI_NOTE_MIN/MAX` | 預設可演奏範圍 48-83 |
| `TRANSPOSE_STEP/MIN/MAX` | 移調控制範圍 |
| `STUCK_KEY_TIMEOUT` | 看門狗逾時（10 秒） |
| `KEYEVENTF_SCANCODE` | SendInput 旗標 |
| `PLAYBACK_SPEED_PRESETS` | 播放速度預設值 |

### 6.3 `core/key_mapper.py` — 翻譯員

核心功能只有一個：把 MIDI 音符號碼翻譯成遊戲按鍵。

```python
mapper = KeyMapper(transpose=0)
result = mapper.lookup(60)   # MIDI 60（中央C）
# result = KeyMapping(scan_code=0x1E, modifier=NONE, label="A")
```

支援**移調**：如果 `transpose=12`，那 MIDI 48 會被當成 60 來查。

支援**原子方案切換**：`set_scheme()` 方法替換字典參照。在 CPython 中，reference assignment 在 GIL 保護下是原子操作——rtmidi 執行緒讀到的要麼是舊字典，要麼是新字典，不會看到「半新半舊」的撕裂狀態。

```python
def set_scheme(self, scheme: MappingScheme) -> None:
    """CPython GIL guarantees atomic dict reference swap."""
    self._scheme = scheme
    self._mapping = scheme.mapping  # 原子性參照替換
```

### 6.4 `core/key_simulator.py` — 按鍵模擬器

用 ctypes 封裝 Windows `SendInput` API。除了按鍵模擬，還負責兩件事：

1. **追蹤活躍音符**：`_active` 字典記錄目前哪些 MIDI 音正在按住、按了多久
2. **看門狗（Watchdog）**：每 10 秒檢查一次，如果某個鍵按超過 `STUCK_KEY_TIMEOUT` 秒沒放開，自動強制放開（防止鍵盤卡住）

### 6.5 `core/midi_listener.py` — MIDI 耳朵

打開 MIDI 裝置，設定一個 callback（回呼函式）。
每當鋼琴送來一個 MIDI 訊息，callback 會在 **rtmidi 的 C++ 執行緒**上被觸發。

它會過濾掉不需要的訊息（踏板、表情控制、SysEx 等），只留 `note_on` 和 `note_off`。還會處理一個 MIDI 的常見陷阱：某些裝置用 `note_on velocity=0` 表示放開，而不是送 `note_off`。

### 6.6 `core/midi_file_player.py` — 自動演奏引擎

這是整個專案中最複雜的檔案，它同時示範了三個進階 Python 技巧：

**技巧一：Qt Lazy Import 模式**

```python
_PlaybackWorkerClass = None

def _ensure_qt_classes():
    global _PlaybackWorkerClass
    if _PlaybackWorkerClass is not None:
        return
    from PyQt6.QtCore import QObject, pyqtSignal

    class PlaybackWorker(QObject):
        ...

    _PlaybackWorkerClass = PlaybackWorker
```

為什麼？因為這個模組可能在 `QApplication` 建立之前被 import（例如測試環境）。如果在模組頂層定義 `class PlaybackWorker(QObject)`，Python 會立刻嘗試載入 Qt，然後爆炸。

**技巧二：精準計時播放迴圈**

播放迴圈用 `threading.Thread`（不是 `QThread`），因為它需要阻塞等待（`time.sleep` + 忙等），如果放在 Qt 執行緒上會凍結整個 GUI。

```python
# 精準計時：sleep 到接近目標時間，然後忙等消除最後的不精確
if wait > 0.002:
    time.sleep(wait - 0.001)      # sleep 到距離目標 1ms 處
while time.perf_counter() < target_wall:  # 忙等最後 1ms
    if self._stop_flag.is_set():
        return
```

**技巧三：4 拍倒數計時**

播放前有 4 秒倒數（節拍器嗶嗶聲），讓使用者有時間 Alt+Tab 切回遊戲視窗。倒數過程中支援暫停和取消。

### 6.7 `core/midi_preprocessor.py` — 9 階段智慧前處理管線

從 v0.2.0 的 5 階段演進到 v0.4.0 的 9 階段。核心改進是 Stage 5 的**流水摺疊**（Flowing Fold）——不再每個音獨立做 modulo fold，而是根據上下文打分，為每個音選出最能保持旋律走向的八度位置。每個 MIDI channel 獨立追蹤 voice state，低音線和旋律線不互相干擾。詳見[第 7 節](#7-智慧前處理管線九階段演算法設計)。

### 6.7b `core/midi_recorder.py` — 即時 MIDI 錄音引擎

v0.4.0 新增。用 `time.perf_counter()` 記錄每個 note_on / note_off 事件的精確時間戳。開始錄音時記下基準時間，後續每個事件的時間都是相對差值。

### 6.7c `core/midi_writer.py` — 錄音匯出

把 `RecordedEvent` 列表轉成 mido 的 `MidiFile` 物件再寫入 `.mid` 檔案。delta time 用 `mido.second2tick()` 轉換——跟播放端的 `tick2second()` 剛好是反操作。

### 6.7d `core/auto_tune.py` — 錄音後處理

錄完之後可選擇做兩道後處理：
1. **節拍量化**（Beat Grid Quantize）：把音符起始時間吸附到最近的節拍格線，支援 1/4、1/8、1/16 音符。有 strength 參數控制量化強度（0.0 = 不動，1.0 = 完全對齊）。
2. **音階校正**（Pitch Snap）：把超出遊戲音域的音符用八度摺疊拉回範圍內。這裡用的是簡單的 modulo fold，不是流水摺疊——因為錄音後的音符大致已在合理位置，不需要 context-aware 的複雜邏輯。

### 6.7e `core/note_sequence.py` — 可變音符序列模型

虛擬鍵盤編輯器的資料模型。用 list 儲存音符，支援 add / delete / move，內建 undo/redo stack。可以跟 `MidiFileEvent` 和 `RecordedEvent` 互轉，所以編輯完的東西可以直接丟進播放引擎或存檔。

### 6.8 `core/mapping_schemes.py` — 方案註冊表

定義了 5 種鍵位方案，用 **Registry 模式**管理：

| 方案 ID | 名稱 | 鍵數 | MIDI 範圍 | 佈局 |
|---------|------|------|----------|------|
| `wwm_36` | 燕雲十六聲 36鍵 | 36 | 48-83 | 3 x 12 |
| `ff14_32` | FF14 32鍵 | 32 | 48-79 | 4 x 8 |
| `generic_24` | 通用 24鍵 | 24 | 48-71 | 2 x 12 |
| `generic_48` | 通用 48鍵 | 48 | 36-83 | 4 x 12 |
| `generic_88` | 通用 88鍵 | 88 | 21-108 | 8 x 11 |

每個方案都是一個不可變的 `MappingScheme` dataclass，包含完整的 `dict[int, KeyMapping]` 映射表。

Registry 用 lazy initialization：第一次呼叫 `get_scheme()` 或 `list_schemes()` 時才建構所有方案。這避免了模組載入時的開銷，也避免了循環匯入。

```python
_SCHEMES: dict[str, MappingScheme] = {}

def _init_registry() -> None:
    if _SCHEMES:
        return
    for builder in [_build_wwm_36, _build_ff14_32, ...]:
        scheme = builder()
        _SCHEMES[scheme.id] = scheme
```

### 6.9 `core/priority.py` — 執行緒優先權管理

三個功能：

1. **TIME_CRITICAL 執行緒優先權**：呼叫 `SetThreadPriority(handle, 15)` 讓排程器優先分配 CPU 給音樂執行緒。
2. **Warn-Once 模式**：用模組層級旗標 `_priority_warning_shown` 確保失敗警告只印一次，避免日誌被淹沒。
3. **高解析度計時器**：`timeBeginPeriod(1)` 把 Windows 計時器精度從 15.6ms 提升到 1ms。程式結束時必須呼叫 `timeEndPeriod(1)` 歸還，否則影響全系統電源管理。

```python
_priority_warning_shown = False

def set_thread_priority_realtime() -> bool:
    global _priority_warning_shown
    try:
        result = ctypes.windll.kernel32.SetThreadPriority(handle, 15)
        if not result and not _priority_warning_shown:
            log.warning("SetThreadPriority failed")
            _priority_warning_shown = True
        return bool(result)
    except Exception:
        if not _priority_warning_shown:
            log.warning("Failed to set thread priority", exc_info=True)
            _priority_warning_shown = True
        return False
```

### 6.10 `gui/app_shell.py` — 總指揮

主視窗骨架，內含關鍵的 `MidiProcessor` 類別——**即時 MIDI 路徑的核心**。它在 rtmidi 執行緒上直接做按鍵模擬，同時用 `perf_counter` 量測延遲，並把前處理統計（智慧移調、碰撞去重）寫入日誌視窗。詳見[第 9 節](#9-即時系統設計執行緒延遲與優先權)的執行緒模型。

### 6.11 `gui/theme.py` — 賽博墨韻主題

色彩系統：墨黑底 `#0A0E14` → 卷軸面 `#101820` → 宣紙暗 `#1A2332`。強調色為賽博青 `#00F0FF` + 金墨 `#D4A853`。同時用 `DwmSetWindowAttribute` 讓 Windows 標題列也變深色。

### 6.12 `gui/widgets/piano_display.py` — 琴鍵動畫

用 `QPainter` 向量繪製，佈局根據映射方案動態調整行列數。三種狀態：靜止（暗色）、按下（賽博青 + glow）、放開（fade 動畫）。標籤自動縮寫：`Shift+Q` → `⇧Q`、`Ctrl+E` → `^E`。

### 6.13 `utils/` — 工具模組

- **admin.py**：檢查 `IsUserAnAdmin()`，權限不足時顯示 `QMessageBox` 建議 UAC 提升。遊戲的 UIPI 會擋下低權限程式的 `SendInput`。
- **ime.py**：偵測輸入法狀態。注音/倉頡開啟時按鍵會被攔截，需要提醒使用者關閉。

---

## 7. 智慧前處理管線：九階段演算法設計

v0.4.0 將管線從 5 階段擴展為 9 階段，每一階段處理一種特定問題。核心改進是第 5 階段的流水摺疊。

### 7.1 管線總覽

```
原始 MIDI 事件
      │
      ├── 1. 打擊過濾 (Percussion Filter)     GM channel 10 鼓組 → 移除
      ├── 2. 音軌篩選 (Track Filter)           只保留使用者選的音軌
      ├── 3. 八度去重 (Octave Dedup)           同時間同 pitch class → 保留最高
      ├── 4. 智慧全域移調 (Global Transpose)   嘗試 ±48（步進 12），選最佳位移
      ├── 5. 流水摺疊 (Flowing Fold) ★         voice-leading aware 八度摺疊
      ├── 6. 碰撞去重 (Collision Dedup)        velocity 優先去重
      ├── 7. 複音限制 (Polyphony Limiter)      超過 N 聲部 → 保留最高+最低
      ├── 8. 力度正規化 (Velocity Normalize)   所有 note_on → 127
      └── 9. 時間量化 (Time Quantize)          對齊 60fps 格線
      │
      ▼
  排序（時間 → note_off 優先） + PreprocessStats
```

### 7.2 Stage 1-3：打擊過濾、音軌篩選、八度去重

前三階段都是「清理」步驟，在進入摺疊前先把不需要的東西拿掉：

- **打擊過濾**：MIDI 的 channel 10（0-indexed = 9）是 GM 規範的鼓組通道。遊戲沒有打擊樂鍵位，直接移除。
- **音軌篩選**：多音軌 MIDI 裡使用者可能只想聽主旋律。這個階段根據使用者選擇，只保留指定的 track index。
- **八度去重**：同一時間有 C4 和 C5（同一個 pitch class 的八度重疊）時，摺疊後它們會撞在一起。不如先在摺疊前就幹掉低的那個，減少後面的碰撞壓力。

### 7.3 Stage 4：智慧全域移調

**問題**：許多鋼琴曲的音域遠超遊戲的 36 鍵（MIDI 48-83）。如果一首曲子集中在 MIDI 84-107（高音區），暴力八度摺疊會讓所有音都擠進一個八度，完全失去旋律結構。

**演算法**：暴力搜尋最佳的全域偏移量。

```python
def compute_optimal_transpose(events, *, note_min=48, note_max=83) -> int:
    notes = [e.note for e in events if e.event_type == "note_on"]
    best_shift, best_in_range = 0, sum(1 for n in notes if note_min <= n <= note_max)

    for shift in range(-48, 49, 12):     # 嘗試 -4 到 +4 個八度
        if shift == 0: continue
        in_range = sum(1 for n in notes if note_min <= n + shift <= note_max)
        if in_range > best_in_range or (
            in_range == best_in_range and abs(shift) < abs(best_shift)
        ):
            best_in_range = in_range
            best_shift = shift

    return best_shift  # 是 12 的倍數，保持音階關係
```

**關鍵設計決策**：
- 只嘗試 12 的倍數（整八度），保持音符之間的音程關係不變
- 同分時選擇**絕對值最小**的偏移量，最大程度保留原曲音高
- 搜尋空間只有 9 個候選值（-48, -36, -24, -12, 0, 12, 24, 36, 48），O(9n) 複雜度

### 7.4 Stage 5：流水摺疊（Flowing Fold）★

這是 v0.4.0 的核心演算法改進。

**舊做法的問題**：v0.3.0 以前用 `while note > max: note -= 12` 逐個搬入。這個 modulo fold 每個音獨立處理、不看前後文。當原曲跨越 3 個八度以上，旋律方向會被破壞——本來上行的樂句，摺疊後可能變成亂跳。

**流水摺疊的思路**：每個音的 pitch class 在目標範圍 [48, 83] 裡通常有 2-3 個八度位置可選（比如 C 可以放在 48、60 或 72）。不盲選，而是根據上下文打分：

```python
對每個 note_on：
  1. 列出所有合法八度位置（candidates）
  2. 只有 1 個候選 → 直接用
  3. 第一個音（沒有前文）→ 已在範圍內就保留原位，否則選最近中心的
  4. 有前文 → 對每個 candidate 打分：
     a. 聲導距離: -2.0 × |candidate - prev_note|    越近越好
     b. 方向延續: 與前一步同方向 → +4.0；平滑反轉 → +1.5
     c. 重力中心: -0.5 × |candidate - center|        留在最近活動區域
     d. 範圍偏好: -0.1 × |candidate - mid|            微弱偏好中間位置
  5. 選最高分的 candidate
  6. 更新 prev_note, center (EMA α=0.15)
```

**Per-channel 獨立追蹤**：低音線走到哪、旋律線走到哪，各自記錄。channel 0 的 voice state 不會污染 channel 1 的決策。

**note_off 配對**：用 `dict[(channel, original_note)] → list[folded_note]` 的 stack 記錄每個 note_on 摺疊到哪，note_off 從對應 stack pop，確保一對一配對。

### 7.5 Stage 6：碰撞去重（velocity 優先）

流水摺疊後仍可能有碰撞（不同原始音折到同一個 pitch）。v0.4.0 改成 velocity 優先——同一時間同一音高，保留力度最大的那個。舊版是 first-seen-wins，可能留下力度弱的。

### 7.6 Stage 7：複音限制

可以設定同時最多幾個聲部。超出時，保留最高音 + 最低音（bass anchor），剩餘從高到低填滿。被丟棄的 note_on 連同對應的 note_off 一起移除。

### 7.7 Stage 8-9：力度正規化 + 時間量化

- **力度**：全部 `note_on` 設為 127（遊戲不分輕重）
- **時間**：對齊到 60fps 格線（`round(t / 16.67ms) * 16.67ms`），消除微小偏差。只在有差異時才建立新的 immutable dataclass 物件。

### 7.8 統計回報（PreprocessStats）

整個管線結束後，回報一個凍結的統計物件：

```python
@dataclass(frozen=True, slots=True)
class PreprocessStats:
    total_notes: int                    # 原始音符總數
    notes_shifted: int                  # 被八度摺疊的音符數
    original_range: tuple[int, int]     # 原始音域 (最低, 最高)
    global_transpose: int = 0           # 全域移調量（12 的倍數）
    duplicates_removed: int = 0         # 碰撞去重移除數
    percussion_removed: int = 0         # 打擊通道移除數
    tracks_removed: int = 0             # 音軌篩選移除數
    octave_deduped: int = 0             # 八度去重移除數
    polyphony_limited: int = 0          # 複音限制移除數
```

這些統計資訊會顯示在 GUI 的日誌視窗中，讓使用者清楚知道每個階段做了什麼。

### 7.9 前後對比範例

假設一首帶鼓組的高音區鋼琴曲，音域 MIDI 72-107（C5-B7）：

```
原始：      [72 ═══════════════════════════════════ 107] + 鼓組 channel 10

Stage 1-2（打擊 + 音軌篩選）：
            鼓組移除，只留鋼琴音軌

Stage 3（八度去重）：
            同時出現的 C5 和 C6 → 只留 C6

Stage 4（智慧移調 -24）：
            [48 ═══════════════════════════════════ 83]
            大部分音落入範圍，少數仍超出

Stage 5（流水摺疊）：
            剩餘超出音符根據旋律走向選擇八度位置
            上行樂句 → 折完仍然上行，不會亂跳

Stage 6（碰撞去重）：
            折完碰撞的 → 保留力度最大的

Stage 7-9（複音限制 + 力度 127 + 60fps 量化）

統計：percussion_removed=16, global_transpose=-24,
      notes_shifted=5, duplicates_removed=3
```

如果沒有 Stage 4 的智慧移調，直接做流水摺疊，所有 72-107 的音都要做大幅度的八度跳轉，即使有打分機制也很難保持旋律的自然感。先「整體搬家」再「微調個別音」，效果好得多。

---

## 8. 搜尋與排序的 UI 架構

### 8.1 雙列表模式：_all_cards vs _visible_cards

`TrackList` widget 管理兩個獨立的列表：

```python
class TrackList(QWidget):
    def __init__(self):
        self._all_cards: list[TrackCard] = []      # 全部卡片（真實資料來源）
        self._visible_cards: list[TrackCard] = []   # 目前顯示的卡片（篩選後）
        self._playing_index: int = -1
        self._current_sort: str = "default"
```

**為什麼要分兩個列表？**

- `_all_cards` 是**資料的 Single Source of Truth**。新增、刪除、索引都以它為準。
- `_visible_cards` 是**視圖層的投影**。它是 `_all_cards` 經過篩選 + 排序後的子集。

這種分離讓我們能在不影響資料完整性的情況下，任意切換過濾和排序條件。播放索引、刪除操作都對應到 `_all_cards` 的索引，不會因為使用者正在搜尋而混亂。

### 8.2 即時搜尋

搜尋框用 `QLineEdit`，每次文字變化都觸發 `_apply_filter()`：

```python
self._search_input = QLineEdit()
self._search_input.setPlaceholderText("搜尋曲名...")
self._search_input.setClearButtonEnabled(True)
self._search_input.textChanged.connect(self._apply_filter)
```

### 8.3 多維排序

排序下拉選單支援 5 種排序方式：

```python
_SORT_OPTIONS = [
    ("預設順序", "default"),    # 匯入順序
    ("名稱",    "name"),       # 字母序
    ("BPM",     "bpm"),        # 速度（降序）
    ("音符數",  "notes"),      # 複雜度（降序）
    ("時長",    "duration"),   # 長度（降序）
]
```

### 8.4 篩選 + 排序的統一流程

每次搜尋文字或排序選項改變，都呼叫 `_apply_filter()`：篩選 → 排序 → 重建佈局（移除舊 widget、插入新 widget）。O(n) 重建對曲庫規模（< 100 首）完全可接受。

### 8.5 MIDI 匯入失敗處理

v0.2.0 新增**批次失敗報告**——多選匯入時，解析失敗的檔案會收集到 `failed: list[str]`，最後用 `QMessageBox.warning` 列出所有失敗的檔案名稱。成功的檔案不受影響，繼續匯入。

---

## 9. 即時系統設計：執行緒、延遲與優先權

### 9.1 執行緒模型

我們的程式有三類執行緒：

```
主執行緒（Qt Event Loop）
├── 畫面更新、按鈕點擊、動畫繪製
├── 搜尋框即時過濾
├── Signal/Slot 接收端
│
rtmidi 執行緒（由 python-rtmidi 的 C++ 層建立）
├── 接收 MIDI 硬體事件
├── 查翻譯表（O(1) dict lookup）
├── 模擬按鍵（SendInput — C 函式，不受 GIL 限制）
├── 量測延遲（perf_counter）
├── 首次觸發時 SetThreadPriority(TIME_CRITICAL)
│
播放執行緒（threading.Thread，播放 .mid 檔時建立）
├── 按時間軸播放音符
├── 精準計時（sleep + 忙等混合策略）
├── SetThreadPriority(TIME_CRITICAL)
├── 支援暫停 / 停止 / 拖動（threading.Event 控制）
```

### 9.2 為什麼不把按鍵模擬丟給主執行緒？

**延遲！**

如果模擬按鍵要先透過 Qt Signal 排隊等主執行緒處理，會多出**不確定的延遲**——取決於主執行緒正在做什麼（可能正在重繪 3x12 的琴鍵動畫、可能正在處理視窗 resize）。

```
路徑 A（我們的做法）：
  rtmidi 收到事件 → 直接 SendInput → 完成 (< 1ms)

路徑 B（如果透過 Qt 排隊）：
  rtmidi 收到事件 → emit signal → Qt 排入佇列 → 等主執行緒空閒
  → 從佇列取出 → 執行 SendInput → 完成 (3-15ms，不確定)
```

對音樂來說，10ms 的延遲就能被專業演奏者感覺到。不確定的延遲更糟——它讓音符之間的時間間隔抖動（jitter），破壞節奏感。

### 9.3 Qt Signal / Slot 跨執行緒通訊

當 `emit` 在非 GUI 執行緒上被呼叫時，Qt 自動使用 **Qt::QueuedConnection**——把 slot 呼叫包裝成事件，放入主執行緒佇列。不需要手動加鎖。

### 9.4 GIL 為什麼不影響延遲？

1. `SendInput` 透過 ctypes 呼叫 C 函式，進入 C 層時釋放 GIL
2. `time.sleep` 也會釋放 GIL
3. 方案切換只是字典參照替換，CPython 中是原子操作
4. rtmidi C++ callback 本身不持有 GIL

### 9.5 計時器精度

`timeBeginPeriod(1)` 把全系統計時器精度從 15.6ms 提升到 1ms（影響 `time.sleep` 精度）。程式結束時必須 `timeEndPeriod(1)` 歸還，否則影響電源管理。

---

## 10. 測試策略與 Mock 架構

### 10.1 測試概覽

| 測試檔案 | 測試數 | 涵蓋模組 |
|----------|--------|----------|
| `test_key_mapper.py` | 翻譯表正確性、移調、方案切換 | `key_mapper.py` |
| `test_key_simulator.py` | SendInput 呼叫、修飾鍵序列、看門狗 | `key_simulator.py` |
| `test_midi_file_player.py` | MIDI 解析、時間轉換、播放狀態機 | `midi_file_player.py` |
| `test_midi_preprocessor.py` | 9 階段管線、流水摺疊、velocity 去重、邊界條件 | `midi_preprocessor.py` |
| `test_mapping_schemes.py` | 方案完整性、範圍正確性、註冊表 | `mapping_schemes.py` |
| `test_auto_tune.py` | 節拍量化、音階校正、strength 參數 | `auto_tune.py` |
| `test_midi_recorder.py` | 錄音狀態機、事件時間戳、.mid 匯出 | `midi_recorder.py`, `midi_writer.py` |
| `test_note_sequence.py` | 音符增刪改、undo/redo、格式互轉 | `note_sequence.py` |

**共 289 個測試**，全部在 Windows CI 上跑，不需要真的 MIDI 裝置。

### 10.2 Mock 硬體

測試的核心挑戰：`SendInput` 需要 Windows、`rtmidi` 需要 MIDI 硬體。我們用 `unittest.mock.patch` 替換這些依賴：

```python
# 範例：驗證 SendInput 收到正確的掃描碼
with patch("cyber_qin.core.key_simulator._send") as mock_send:
    simulator = KeySimulator()
    mapping = KeyMapping(scan_code=0x1E, modifier=Modifier.NONE, label="A")
    simulator.press(60, mapping)
    assert mock_send.call_count == 1

    # 驗證送出的 INPUT 結構體
    args = mock_send.call_args[0]
    assert args[0].ki.wScan == 0x1E  # 掃描碼正確
```

### 10.3 前處理管線的測試策略

前處理器有 118 個測試（佔全部的 40%），特別注重**邊界條件**和**不變量驗證**：

- 空事件列表 → 回傳空列表 + 零統計
- 全部音符都在範圍內 → `global_transpose=0`, `notes_shifted=0`
- 全部音符都超出範圍 → 驗證所有音符都被搬入範圍
- 碰撞去重 → 驗證 `duplicates_removed` 計數正確
- 管線不變量：輸出的每個 note_on 音符都在 `[note_min, note_max]` 範圍內
- 流水摺疊：上行旋律折完仍上行、下行仍下行
- 流水摺疊：note_off 與 note_on 配對正確
- 流水摺疊：不同 channel 獨立追蹤
- velocity 去重：碰撞時保留力度最高的
- 極端 MIDI 值（0 和 127）不 crash

```bash
# 跑所有 289 個測試
pytest

# 跑測試，簡短輸出
pytest -q

# 只跑前處理器測試（含流水摺疊）
pytest tests/test_midi_preprocessor.py -v
```

---

## 11. CI/CD 管線：自動測試與發佈

### 11.1 持續整合（ci.yml）

每次 push 到 `main` 或開 PR 時自動觸發兩個 job：

- **test**：`windows-latest` x Python `[3.11, 3.12, 3.13]` 矩陣 → `pytest -q`（必須用 Windows，因為 `ctypes.windll`）
- **lint**：`ubuntu-latest` → `ruff check .`（純文字分析，不需 Windows，啟動更快）

### 11.2 自動發佈（release.yml）

推送 `v*` 格式的 Git tag 時自動觸發：

```
git tag v0.4.0 && git push --tags
  → checkout → pip install → generate icon → pyinstaller
  → Compress-Archive (pwsh) → upload artifact → create GitHub Release
  → 產出：賽博琴仙-v0.4.0.zip + 自動 release notes
```

workflow 需要 `contents: write` 權限，在 `windows-latest` + Python 3.13 上執行。用 `softprops/action-gh-release@v2` 建立 Release 並附加 zip 檔案。

---

## 12. 建置與打包系統

### 12.1 一鍵建置腳本（scripts/build.py）

解決了手動建置的痛苦——五個步驟全部自動化：

```
python scripts/build.py  →  找 Python 3.13 → 建 .venv313/ → pip install
                         →  生成 icon.ico → PyInstaller → dist/賽博琴仙/ (~95 MB)
```

腳本會依序嘗試 `python3.13` / `python3` / `python` / `py -3.13` 來尋找正確版本。限定 3.13 是因為 PyQt6 在 3.14 alpha 上會 fatal crash。

### 12.2 圖示生成（scripts/generate_icon.py）

完全用程式碼繪製——不依賴外部圖片。用 QPainter 在 6 個解析度（16-256px）上畫圓形墨黑底 + 金墨圓環 + 宣紙白音符，然後透過 Pillow 匯出多解析度 .ico。

注意：Qt 的 `QImage` 是 BGRA 記憶體排列，轉 Pillow 時必須指定 `Image.frombytes("RGBA", ..., "raw", "BGRA")`。

### 12.3 PyInstaller 規格檔

`cyber_qin.spec` 配置了：

| 項目 | 設定 |
|------|------|
| 入口 | `launcher.py`（非 `cyber_qin/main.py`） |
| 模式 | `onedir`（目錄模式，比 onefile 快啟動） |
| 視窗 | `windowed=True`（不顯示命令列視窗） |
| 權限 | `uac_admin=True`（要求管理員權限） |
| 圖示 | `assets/icon.ico` |

**為什麼入口是 launcher.py 而不是 main.py？** 因為 `main.py` 位於 `cyber_qin/` 套件內部，它裡面用了相對匯入（`from .utils.admin import ...`）。PyInstaller 直接執行 `main.py` 時，沒有 parent package context，相對匯入會失敗。`launcher.py` 是一個薄包裝，用 `from cyber_qin.main import main; main()` 來正確啟動。

---

## 13. 如何安裝與執行

```bash
# 安裝 Python 3.11-3.13（勿用 3.14），勾選「Add Python to PATH」

# 安裝專案（editable 模式 + 開發工具）
cd C:\專案\賽博琴仙
pip install -e .[dev]       # .[dev] = pytest + ruff + pyinstaller + pillow

# 執行（建議以管理員身份，否則遊戲可能收不到按鍵）
cyber-qin                   # 或 python -m cyber_qin.main

# 建置可執行檔
python scripts/build.py     # 一鍵建置

# 跑測試（289 個，不需要 MIDI 硬體）
pytest -q

# 程式碼風格
ruff check .                # 檢查
ruff check --fix .          # 自動修正
```

---

## 14. 常見陷阱與學到的教訓

| # | 問題 | 教訓 |
|---|------|------|
| 1 | `sizeof(INPUT)` 必須 40 位元組（64-bit），省略 `MOUSEINPUT` 會變 32，`SendInput` 靜靜回傳 0 | 永遠在 Union 中包含所有成員，加 assert 驗證大小 |
| 2 | `mido.merge_tracks()` 的 `msg.time` 是 tick 不是秒，且 tempo 可能中途改變 | 永遠用 `mido.tick2second()`，追蹤 `set_tempo` 事件 |
| 3 | 模組頂層定義 `class Foo(QObject)` 會在 import 時炸，如果 `QApplication` 尚未建立 | 用 lazy class definition（見 `_ensure_qt_classes()`） |
| 4 | `QThread.moveToThread()` 不會讓直接呼叫的方法在新執行緒上跑，播放迴圈凍結 GUI | 用 `threading.Thread` + `threading.Event` 控制暫停/停止 |
| 5 | Python 3.14 alpha + PyQt6 → `Unable to embed qt.conf` fatal crash | 用穩定版 3.11-3.13，CI 明確指定版本矩陣 |
| 6 | 八度摺疊讓不同音高碰撞到同一個鍵（v0.2.0 新發現） | 先智慧移調減少摺疊量，再去重處理殘留碰撞 |
| 7 | PyInstaller 打包 `cyber_qin/main.py` 時相對匯入失敗 | 用 `launcher.py` 薄包裝做絕對匯入 |
| 8 | 純 modulo fold 破壞旋律方向（v0.4.0 改進） | 改用流水摺疊：對所有合法八度位置打分，根據前後文選最佳。per-channel 獨立追蹤 |
| 9 | 碰撞去重 first-seen-wins 可能留下弱音（v0.4.0 改進） | 改成 velocity 優先，pre-scan 找最大力度再過濾 |

---

## 15. 詞彙表

| 術語 | 白話解釋 |
|------|---------|
| **MIDI** | 音樂設備之間的溝通語言——鋼琴告訴電腦「我按了哪個鍵、多大力」 |
| **掃描碼（Scan Code）** | 每個實體按鍵的硬體編號，DirectInput 遊戲用它來認鍵 |
| **虛擬鍵碼（VK Code）** | Windows 高階輸入系統的按鍵編號，一般程式用但遊戲不認 |
| **DirectInput** | Windows 的低階遊戲輸入介面，直接跟硬體溝通 |
| **callback** | 「等事情發生時打電話給我」——你先登記一個函式，事件發生時它會被自動呼叫 |
| **執行緒（Thread）** | 程式裡面的「分身」，可以同時做不同的事 |
| **Signal / Slot** | Qt 的跨執行緒事件通知機制——發信號 → 觸發對應的處理函式 |
| **GIL** | Python 的全域解譯器鎖，同時只讓一個執行緒執行 Python 位元組碼 |
| **mock** | 測試用的假物件，模擬真實硬體或 API 的行為 |
| **QSS** | Qt Style Sheet——類似網頁的 CSS，用來美化 Qt 元件的外觀 |
| **UAC** | 使用者帳戶控制——Windows 問你「允許此程式做變更嗎？」的那個彈窗 |
| **UIPI** | 使用者介面權限隔離——低權限程式無法送訊息給高權限程式 |
| **dataclass** | Python 的自動類別產生器，減少重複的 `__init__`、`__eq__` 程式碼 |
| **transpose** | 移調——把所有音符整體往上或往下移若干半音 |
| **全域移調（Global Transpose）** | v0.2.0 新增：以整八度為單位的智慧移調，在八度摺疊之前執行 |
| **八度摺疊（Octave Fold）** | 把超出範圍的音符移入最近的合法八度 |
| **流水摺疊（Flowing Fold）** | v0.4.0 的 voice-leading aware 八度摺疊。不盲選八度位置，而是根據前後音符的走向打分選最佳位置 |
| **碰撞去重（Collision Dedup）** | 移除八度摺疊後產生的重複音符——同一時間、同一音高只保留力度最高的 |
| **Auto-Tune** | 錄音後處理——節拍量化（吸附到格線）+ 音階校正（折入可演奏範圍）|
| **quantize** | 量化——把不精準的時間點對齊到整齊的格線上 |
| **daemon thread** | 背景執行緒——主程式結束時它會自動終止，不會卡住 |
| **Registry 模式** | 用一個中央字典管理所有註冊的物件（本專案用於映射方案） |
| **Single Source of Truth** | 單一真實來源——同一份資料只在一個地方定義，避免不一致 |
| **CI/CD** | 持續整合/持續部署——每次程式碼變更自動跑測試、自動建置發佈 |
| **perf_counter** | Python 的高精度計時器，精度可達奈秒級 |
| **TIME_CRITICAL** | Windows 最高的執行緒優先權等級，讓排程器優先分配 CPU 時間 |
| **timeBeginPeriod** | Windows API，請求提升系統計時器精度（預設 15.6ms → 1ms） |

---

> 如果你讀完還有不懂的地方，歡迎提問。
> 最好的學習方式是：邊讀文件、邊開程式碼、邊用 `print()` 到處印東西看看結果。
> 用 `pytest -v` 跑測試，觀察每個測試在驗證什麼——那是理解系統行為最快的方式。
