# 賽博琴仙 — 從零開始的技術導覽

> 這份文件是寫給**完全初學者**的。即使你從來沒寫過程式，跟著看也能懂。
> 我們會從「Python 是什麼」一路講到「這個程式怎麼讓鋼琴控制遊戲角色彈琴」。
>
> **適合對象**：想理解這個專案用了什麼技術、每個技術該從哪裡學起、以及整個專案從無到有是怎麼蓋出來的人。

---

## 目錄

1. [這個程式在做什麼？](#1-這個程式在做什麼)
2. [技術棧總覽：我們用了什麼](#2-技術棧總覽我們用了什麼)
3. [Python 基礎：給零基礎的你](#3-python-基礎給零基礎的你)
4. [MIDI 入門：音樂設備的語言](#4-midi-入門音樂設備的語言)
5. [PyQt6 入門：蓋一個桌面程式](#5-pyqt6-入門蓋一個桌面程式)
6. [ctypes 入門：直接跟 Windows 說話](#6-ctypes-入門直接跟-windows-說話)
7. [專案資料夾結構](#7-專案資料夾結構)
8. [核心原理：從琴鍵到遊戲按鍵](#8-核心原理從琴鍵到遊戲按鍵)
9. [每個檔案在做什麼？（完整版）](#9-每個檔案在做什麼完整版)
10. [重要觀念：執行緒與延遲](#10-重要觀念執行緒與延遲)
11. [Beat-based 編輯器：新一代資料模型](#11-beat-based-編輯器新一代資料模型)
12. [測試哲學：為什麼寫 366 個測試](#12-測試哲學為什麼寫-366-個測試)
13. [打包發佈：從原始碼到可執行檔](#13-打包發佈從原始碼到可執行檔)
14. [如何安裝與執行](#14-如何安裝與執行)
15. [技術學習路線圖](#15-技術學習路線圖)
16. [常見陷阱與學到的教訓](#16-常見陷阱與學到的教訓)
17. [詞彙表](#17-詞彙表)

---

## 1. 這個程式在做什麼？

想像一下：你有一台**真的鋼琴**（MIDI 鍵盤），你想在遊戲《燕雲十六聲》裡面彈琴。

問題是——遊戲只認鍵盤按鍵（Q、W、E、Shift+Z 這些），不認鋼琴。

**賽博琴仙**就是那座橋：

```
你的手指 → 鋼琴琴鍵 → USB線 → 電腦收到 MIDI 訊號 → 賽博琴仙翻譯 → 假裝按鍵盤 → 遊戲角色彈琴
```

就像一個**即時翻譯員**：鋼琴說「我按了中央 C」，翻譯員立刻告訴遊戲「使用者按了 A 鍵」。

### 五大模式

| 模式 | 做什麼 |
|------|--------|
| **即時演奏** | 你按鋼琴，遊戲角色同步彈奏，延遲 < 2ms |
| **自動播放** | 載入 .mid 檔案，程式自動按鍵替你演奏 |
| **即時錄音** | 錄下你的演奏，存成 .mid 檔案 |
| **虛擬鍵盤編輯** | 沒有鋼琴？用滑鼠點琴鍵來輸入音符 |
| **拍號制編輯器** | 進階 piano roll 介面，多軌編輯、拖曳音符、undo/redo |

---

## 2. 技術棧總覽：我們用了什麼

先看全貌，後面每個都會詳細解釋。

### 核心技術

| 技術 | 是什麼 | 在這裡做什麼 | 學習資源 |
|------|--------|-------------|----------|
| **Python 3.11+** | 程式語言 | 整個程式都用它寫 | [python.org/tutorial](https://docs.python.org/3/tutorial/) |
| **PyQt6** | GUI 框架 | 視窗、按鈕、鋼琴鍵盤畫面 | [Qt for Python](https://doc.qt.io/qtforpython-6/) |
| **mido** | MIDI 程式庫 | 讀取 MIDI 裝置和 .mid 檔案 | [mido docs](https://mido.readthedocs.io/) |
| **python-rtmidi** | MIDI 底層驅動 | 真正跟 USB MIDI 裝置溝通 | [python-rtmidi docs](https://spotlightkid.github.io/python-rtmidi/) |
| **ctypes** | Python 標準庫 | 呼叫 Windows C API（SendInput） | [ctypes docs](https://docs.python.org/3/library/ctypes.html) |

### 開發工具

| 技術 | 是什麼 | 在這裡做什麼 | 學習資源 |
|------|--------|-------------|----------|
| **pytest** | 測試框架 | 跑 366 個自動化測試 | [pytest docs](https://docs.pytest.org/) |
| **Ruff** | Linter | 程式碼風格檢查 | [Ruff docs](https://docs.astral.sh/ruff/) |
| **PyInstaller** | 打包工具 | 把 Python 程式變成 .exe | [PyInstaller docs](https://pyinstaller.org/) |
| **GitHub Actions** | CI/CD | 自動測試 + 自動發佈 | [GitHub Actions docs](https://docs.github.com/en/actions) |
| **Git** | 版本控制 | 追蹤程式碼變更 | [Pro Git book](https://git-scm.com/book/zh-tw/v2) |

### 核心概念

| 概念 | 為什麼重要 |
|------|-----------|
| **多執行緒** | 同時做好幾件事：接 MIDI、模擬按鍵、更新畫面 |
| **DirectInput 掃描碼** | 遊戲只認這個，虛擬鍵碼沒用 |
| **Signal/Slot** | Qt 的跨執行緒事件通訊機制 |
| **dataclass** | Python 的自動類別產生器 |
| **beat-based 時間模型** | 以「拍」為單位表示音符位置，BPM 變更不會壞 |

---

## 3. Python 基礎：給零基礎的你

### 3.1 Python 是什麼？

Python 是一種**程式語言**——你用文字告訴電腦要做什麼事。

```python
# 這是一行「註解」，電腦會跳過它，是寫給人看的筆記
print("哈囉，世界！")   # 在螢幕上印出文字
```

> **從哪裡學**：[Python 官方教學](https://docs.python.org/3/tutorial/)，或搜尋「Python 入門 中文」。建議先跟著做到「第 5 章」就夠理解這個專案的基礎了。

### 3.2 變數：給東西取名字

```python
name = "賽博琴仙"   # 文字（字串）
age = 1              # 數字（整數）
speed = 1.5          # 小數（浮點數）
is_cool = True       # 是/否（布林值）
```

就像貼標籤：把「賽博琴仙」這張紙貼上「name」這個標籤。

### 3.3 函式：可以重複使用的動作

```python
def say_hello(who):
    """跟某人打招呼。"""    # ← 這叫「文件字串」，解釋這函式做什麼
    print(f"哈囉，{who}！")

say_hello("小明")   # 印出：哈囉，小明！
say_hello("小花")   # 印出：哈囉，小花！
```

`def` 是「定義」的意思。定義一次，到處使用。

### 3.4 類別（class）：藍圖

如果函式是「一個動作」，那類別就是「一整套東西」。

```python
class Dog:
    """一隻狗的藍圖。"""

    def __init__(self, name):
        """造一隻新狗時會自動執行。"""
        self.name = name       # self = 「我自己」

    def bark(self):
        print(f"{self.name} 說：汪！")

my_dog = Dog("小黑")    # 用藍圖造一隻叫小黑的狗
my_dog.bark()           # 印出：小黑 說：汪！
```

在我們的專案裡，`KeyMapper` 就是一個類別——它是「翻譯員的藍圖」。

### 3.5 字典（dict）：查詢表

```python
phone_book = {
    "小明": "0912-345-678",
    "小花": "0987-654-321",
}

print(phone_book["小明"])   # 印出：0912-345-678
```

我們的程式用字典把 **MIDI 音符號碼** 對應到 **鍵盤按鍵**：

```python
mapping = {
    60: "A鍵",    # 中央C → 按 A
    62: "S鍵",    # D4   → 按 S
    64: "D鍵",    # E4   → 按 D
}
```

### 3.6 套件（Package）：別人寫好的工具箱

你不需要自己發明輪子。別人已經寫好了很多工具，你只要「匯入」就能用：

```python
import mido   # 匯入 mido 套件（處理 MIDI 的工具箱）

ports = mido.get_input_names()   # 用它來找電腦上有哪些 MIDI 裝置
```

### 3.7 型別提示（Type Hints）

你會在程式裡看到這種寫法：

```python
def lookup(self, midi_note: int) -> KeyMapping | None:
```

這不是魔法，只是「備註」：
- `midi_note: int` → 「midi_note 應該是整數」
- `-> KeyMapping | None` → 「這個函式回傳 KeyMapping 或什麼都沒有」

Python 不會強制檢查，但它幫助**讀程式的人**理解。

### 3.8 dataclass：懶人版的類別

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class KeyMapping:
    scan_code: int
    modifier: Modifier
    label: str
```

`@dataclass` 會自動幫你產生 `__init__`、`__eq__` 等方法。`frozen=True` 表示建立之後不能修改（像是用水泥固定住）。

> **這專案大量使用 dataclass**：`KeyMapping`、`MidiFileEvent`、`RecordedEvent`、`BeatNote`、`BeatRest`、`Track`、`AutoTuneStats` 全都是。

---

## 4. MIDI 入門：音樂設備的語言

### 4.1 什麼是 MIDI？

**MIDI**（Musical Instrument Digital Interface）是音樂設備之間溝通的「語言」。
它不傳送聲音，只傳送**指令**：「哪個音被按了」「力道多大」「什麼時候放開」。

### 4.2 MIDI 訊息長什麼樣？

當你在鋼琴上按一個鍵，鋼琴會透過 USB 傳送這樣的訊息：

```
note_on  channel=0  note=60  velocity=80  time=0
```

意思是：「第 60 號音（中央 C）被按下了，力道 80」。

| 欄位 | 意思 |
|------|------|
| `note_on` | 「按下了」 |
| `note_off` | 「放開了」 |
| `channel` | 頻道（0-15），不同樂器可以用不同頻道 |
| `note` | 音高（0-127），60 = 中央 C |
| `velocity` | 力道（0-127），127 = 最大力 |

### 4.3 MIDI 音符編號

```
C3 = 48    C4 = 60（中央C）  C5 = 72
D3 = 50    D4 = 62            D5 = 74
E3 = 52    E4 = 64            E5 = 76
...
```

每個八度有 12 個半音。遊戲的 36 鍵模式涵蓋 MIDI 48-83（C3 到 B5 = 3 個完整八度）。

### 4.4 .mid 檔案

`.mid` 檔案把 MIDI 訊息按時間順序存下來。時間單位是 **tick**（不是秒！），需要用 BPM 來換算：

```python
seconds = mido.tick2second(ticks, ticks_per_beat, tempo)
```

> **陷阱**：`mido.merge_tracks()` 回傳的 `msg.time` 是 tick，不是秒。這是我們踩過的一個大坑。

### 4.5 我們用的 MIDI 套件

| 套件 | 角色 | 比喻 |
|------|------|------|
| `mido` | 高階介面 | 餐廳的服務生（你跟他點菜） |
| `python-rtmidi` | 底層驅動 | 廚房的廚師（真正做菜的人） |

**mido** 幫我們：
- 列出電腦上有哪些 MIDI 裝置（`mido.get_input_names()`）
- 打開裝置接收訊息（`mido.open_input()`）
- 讀取 .mid 檔案（`mido.MidiFile()`）
- 轉換時間單位（`mido.tick2second()`）

> **從哪裡學**：[mido 官方文件](https://mido.readthedocs.io/)，先讀 "Ports" 和 "MIDI Files" 這兩章。

---

## 5. PyQt6 入門：蓋一個桌面程式

### 5.1 什麼是 Qt？

**Qt**（發音：cute）是一個超大的圖形介面框架，可以蓋跨平台的桌面程式。
**PyQt6** 是它的 Python 綁定。

### 5.2 基本概念

| 概念 | 解釋 | 比喻 |
|------|------|------|
| **QApplication** | 整個 App 的根物件 | 一棟大樓的地基 |
| **QMainWindow** | 主視窗 | 大樓的外殼 |
| **QWidget** | 所有 UI 元件的父類別 | 房間裡的傢俱 |
| **Layout** | 排列元件的方式 | 傢俱的擺放規則 |
| **Signal / Slot** | 事件通知機制 | 「門鈴響了 → 去開門」 |
| **QPainter** | 自訂繪圖 | 畫筆和畫布 |

### 5.3 我們蓋了什麼？

```
QApplication（整個 App）
└── QMainWindow (AppShell)
    ├── Sidebar（左側導航欄）
    ├── QStackedWidget（可以切換的頁面）
    │   ├── LiveModeView（演奏模式頁）
    │   ├── LibraryView（曲庫頁）
    │   └── EditorView（編輯器頁）
    └── NowPlayingBar（底部播放列）
```

### 5.4 QPainter：用程式碼畫畫

我們的鋼琴鍵盤不是用圖片做的，而是用 `QPainter` 一筆一筆畫出來的：

```python
def paintEvent(self, event):
    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # 反鋸齒

    # 畫一個圓角矩形
    path = QPainterPath()
    path.addRoundedRect(QRectF(x, y, width, height), radius, radius)
    painter.fillPath(path, QColor("#00F0FF"))  # 填色

    painter.end()
```

好處：任意縮放不失真，不需要載入外部圖片。

### 5.5 Signal / Slot：跨執行緒的安全溝通

```python
class MidiProcessor(QObject):
    note_event = pyqtSignal(str, int, int)   # ← 定義一個「信號」

    def on_midi_event(self, event_type, note, velocity):
        # 在 rtmidi 執行緒上執行
        self.note_event.emit(event_type, note, velocity)  # 發信號

# 在主執行緒上連接
processor.note_event.connect(live_view.on_note_event)
# Qt 會自動把 on_note_event 排進主執行緒的隊列
```

> **從哪裡學**：[Qt for Python 教學](https://doc.qt.io/qtforpython-6/tutorials/)，先做 "Your First Application" 範例。

---

## 6. ctypes 入門：直接跟 Windows 說話

### 6.1 為什麼需要它？

Windows 有很多內建功能（叫做 **API**），但它們是用 C 語言寫的。
`ctypes` 讓 Python 能直接呼叫這些 C 函式，不需要寫任何 C 程式碼。

### 6.2 我們用 ctypes 做什麼？

| 功能 | Windows API | 用途 |
|------|------------|------|
| 模擬按鍵 | `SendInput()` | 假裝使用者按了鍵盤 |
| 檢查管理員 | `IsUserAnAdmin()` | 確認有權限注入按鍵 |
| 深色標題列 | `DwmSetWindowAttribute()` | 讓標題列變黑 |
| 執行緒優先權 | `SetThreadPriority()` | 讓 MIDI 處理不被搶走 CPU |
| 計時器精度 | `timeBeginPeriod()` | 從 15.6ms 降到 1ms |

### 6.3 結構體（Structure）

C 語言的資料結構在 Python 中要這樣模擬：

```python
import ctypes

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),        # 虛擬鍵碼
        ("wScan", ctypes.c_ushort),       # 掃描碼 ← 我們用這個！
        ("dwFlags", ctypes.c_ulong),      # 旗標
        ("time", ctypes.c_ulong),         # 時間戳
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]
```

### 6.4 最大的坑：結構體大小

`INPUT` 結構體有一個 union（聯合體），裡面有三種輸入類型。union 的大小 = **最大成員的大小**。

```
MOUSEINPUT  = 32 bytes ← 最大！
KEYBDINPUT  = 24 bytes
HARDWAREINPUT = 8 bytes
```

如果你省略了 `MOUSEINPUT`（反正我們不用滑鼠嘛），union 只有 24 bytes → `sizeof(INPUT)` 變成 32 而不是 40 → `SendInput` **靜靜地回傳 0**，什麼都不做，也不報錯。

這是我們踩過最痛的一個坑。debug 了好幾個小時才發現。

> **從哪裡學**：[ctypes 官方文件](https://docs.python.org/3/library/ctypes.html)，重點看 "Structures and unions" 章節。

---

## 7. 專案資料夾結構

```
賽博琴仙/
├── pyproject.toml          ← 專案設定檔（名稱、版本、需要哪些套件）
├── CLAUDE.md               ← 給 AI 助手看的開發指南
├── README.md               ← 專案說明（給 GitHub 上的人看的）
│
├── cyber_qin/              ← 所有程式碼都在這裡（40 個模組，~8,500 行）
│   ├── __init__.py         ← 告訴 Python「這是一個套件」
│   ├── main.py             ← 程式的「大門」——從這裡開始執行
│   │
│   ├── core/               ← 核心邏輯（跟畫面無關的部分）
│   │   ├── constants.py        ← 常數定義（掃描碼、MIDI 範圍…）
│   │   ├── key_mapper.py       ← MIDI 音符 → 按鍵 的翻譯表
│   │   ├── key_simulator.py    ← 模擬鍵盤按鍵（ctypes SendInput）
│   │   ├── midi_listener.py    ← 接收 MIDI 裝置的即時訊號
│   │   ├── midi_file_player.py ← 讀取 .mid 檔並按時間播放
│   │   ├── midi_preprocessor.py← 9 階段 MIDI 預處理管線
│   │   ├── midi_recorder.py    ← 即時 MIDI 錄音引擎
│   │   ├── midi_writer.py      ← 錄音結果 → .mid 檔案
│   │   ├── auto_tune.py        ← 錄音後處理（量化 + 音階校正）
│   │   ├── beat_sequence.py    ← ★ Beat-based 多軌音符序列（新！）
│   │   ├── note_sequence.py    ← 秒制音符序列（舊版編輯器）
│   │   ├── mapping_schemes.py  ← 5 種鍵位方案的註冊表
│   │   └── priority.py         ← Windows 執行緒優先權工具
│   │
│   ├── gui/                ← 圖形介面（所有你看得到的東西）
│   │   ├── app_shell.py        ← 主視窗框架（組裝所有元件）
│   │   ├── theme.py            ← 「賽博墨韻」深色主題
│   │   ├── icons.py            ← 用程式碼畫的向量圖示
│   │   ├── views/              ← 整頁的畫面
│   │   │   ├── live_mode_view.py   ← 演奏模式（連裝置、看琴鍵）
│   │   │   ├── library_view.py     ← 曲庫（匯入、管理 MIDI 檔）
│   │   │   └── editor_view.py      ← ★ 拍號制編輯器（新！）
│   │   └── widgets/            ← 可重複使用的小元件
│   │       ├── piano_display.py    ← 大鋼琴顯示（3×12 琴鍵動畫）
│   │       ├── mini_piano.py       ← 迷你鋼琴（底部播放列用的）
│   │       ├── clickable_piano.py  ← 可互動鋼琴（點選輸入音符）
│   │       ├── note_roll.py        ← ★ Beat-based piano roll（新！）
│   │       ├── sidebar.py          ← 左側導航欄
│   │       ├── now_playing_bar.py  ← 底部播放控制列
│   │       ├── track_list.py       ← 曲目清單元件
│   │       ├── progress_bar.py     ← 可拖曳進度條
│   │       ├── speed_control.py    ← 播放速度控制器
│   │       ├── log_viewer.py       ← 事件日誌視窗
│   │       ├── status_bar.py       ← 狀態列
│   │       └── animated_widgets.py ← 動畫基礎元件（IconButton）
│   │
│   └── utils/              ← 工具函式
│       ├── admin.py            ← 管理員權限檢查 / UAC 提升
│       └── ime.py              ← 輸入法狀態偵測
│
├── tests/                  ← 自動化測試（9 個檔案，~2,900 行，366 個測試）
│   ├── test_key_mapper.py
│   ├── test_key_simulator.py
│   ├── test_midi_file_player.py
│   ├── test_midi_preprocessor.py
│   ├── test_mapping_schemes.py
│   ├── test_auto_tune.py
│   ├── test_midi_recorder.py
│   ├── test_note_sequence.py
│   └── test_beat_sequence.py   ← ★ 77 個新測試
│
├── docs/
│   ├── ONBOARDING.md           ← 你正在看的這份文件
│   └── EDITOR_SDD.md           ← 編輯器軟體設計文件
│
└── .github/workflows/
    └── ci.yml                  ← GitHub Actions CI/CD 設定
```

---

## 8. 核心原理：從琴鍵到遊戲按鍵

### 8.1 完整流程圖

```
   【你的手指按下鋼琴的中央 C】
              │
              ▼
   ┌────────────────────┐
   │   Roland FP-30X    │  ← 鋼琴透過 USB 送出 MIDI 訊號
   │   (MIDI 鍵盤)      │     note_on, note=60, velocity=80
   └────────┬───────────┘
            │ USB
            ▼
   ┌────────────────────┐
   │   python-rtmidi    │  ← C++ 層接收原始 MIDI 位元組
   │   (底層驅動)        │     在獨立的 rtmidi 執行緒上運作
   └────────┬───────────┘
            │ callback
            ▼
   ┌────────────────────┐
   │   MidiListener     │  ← 過濾：只留 note_on / note_off
   │   (midi_listener)  │     轉換 velocity=0 的 note_on 為 note_off
   └────────┬───────────┘
            │ callback(event_type, note, velocity)
            ▼
   ┌────────────────────┐
   │   MidiProcessor    │  ← 「大腦」——仍在 rtmidi 執行緒上
   │   (app_shell)      │     ① 查翻譯表 → note 60 = 按 A 鍵
   │                    │     ② 模擬按鍵 → 告訴 Windows 按 A
   │                    │     ③ 發 Qt 信號 → 通知畫面更新
   └────────┬───────────┘
            │
      ┌─────┴─────┐
      ▼           ▼
  【即時按鍵】  【Qt 信號】
  KeySimulator   ↓（跨執行緒，自動排隊）
  SendInput()    ↓
      │     ┌─────────────────┐
      │     │  Qt 主執行緒     │
      │     │  更新琴鍵動畫    │
      │     │  更新事件日誌    │
      │     │  更新延遲顯示    │
      │     └─────────────────┘
      ▼
   ┌────────────────────┐
   │   Windows 作業系統  │  ← 收到 SendInput，把按鍵送給前景視窗
   └────────┬───────────┘
            ▼
   ┌────────────────────┐
   │   燕雲十六聲 遊戲   │  ← 收到 A 鍵 → 角色彈出中央 C 的音
   └────────────────────┘
```

### 8.2 為什麼用「掃描碼」而不是「虛擬鍵碼」？

鍵盤按鍵有兩種表示法：

| 方式 | 範例 | 用途 |
|------|------|------|
| 虛擬鍵碼（VK） | `VK_A = 0x41` | 一般應用程式（記事本、瀏覽器） |
| 掃描碼（Scan Code） | `A = 0x1E` | 遊戲（DirectInput） |

大部分遊戲用 **DirectInput** 讀取鍵盤，它只認掃描碼。如果你送虛擬鍵碼，遊戲會完全無視。

掃描碼是鍵盤硬體層面的編號，每個實體按鍵有一個固定的掃描碼：

```python
SCAN = {
    "Z": 0x2C,    # Z 鍵的掃描碼是 0x2C（十六進位）= 44（十進位）
    "A": 0x1E,    # A 鍵 = 0x1E = 30
    "Q": 0x10,    # Q 鍵 = 0x10 = 16
    "LSHIFT": 0x2A,  # 左 Shift = 0x2A = 42
    "LCTRL": 0x1D,   # 左 Ctrl  = 0x1D = 29
}
```

### 8.3 翻譯表怎麼運作？

遊戲的 36 鍵模式把鍵盤分成三層：

```
高音 (C5-B5)：  Q  W  E  R  T  Y  U  ← 自然音
               ⇧Q    ^E ⇧R    ⇧T ^U  ← 升降號（Shift / Ctrl 組合）

中音 (C4-B4)：  A  S  D  F  G  H  J
               ⇧A    ^D ⇧F    ⇧G ^J

低音 (C3-B3)：  Z  X  C  V  B  N  M
               ⇧Z    ^C ⇧V    ⇧B ^M
```

（⇧ = Shift, ^ = Ctrl）

### 8.4 修飾鍵的處理

按 `Shift+Z`（C#3）的時候，不能像人那樣「按住 Shift 再按 Z」——因為如果 Shift 按太久，會影響下一個音。

我們的策略是**「閃按」修飾鍵**：

```
Shift↓ → Z↓ → Shift↑   （三個動作一次送出，作為一個 batch）
         ...
         Z↑              （放開 Z 時不需要再管 Shift）
```

`SendInput` 保證同一批次中的事件不會被其他程式的輸入事件插隊。

---

## 9. 每個檔案在做什麼？（完整版）

### 核心模組 (`core/`)

#### `main.py` — 程式大門

```
啟動 → 設定 log → 建立 QApplication → 檢查管理員權限
     → 開啟 1ms 計時器 → 套用深色主題 → 建立主視窗 → 進入事件迴圈
```

#### `constants.py` — 常數倉庫

所有「不會變的數字」都放在這裡：掃描碼對照表、MIDI 音域範圍（48-83）、移調限制、播放速度範圍。

#### `key_mapper.py` — 翻譯員

核心功能只有一個：給一個 MIDI 音符，查出對應的鍵盤按鍵。支援移調和切換方案。

```python
mapper = KeyMapper(transpose=0)
result = mapper.lookup(60)   # MIDI 60（中央C）→ KeyMapping(scan_code=0x1E, ...)
```

#### `key_simulator.py` — 假鍵盤

用 ctypes 呼叫 Windows 的 `SendInput` API。追蹤哪些音正在按（`_active` 字典），確保配對放開。還有**看門狗**：超過 10 秒沒放開的鍵自動釋放。

#### `midi_listener.py` — 耳朵

打開 MIDI 裝置，設定 callback。過濾掉踏板/表情控制等，只留 `note_on` 和 `note_off`。每 3 秒檢查裝置是否斷線，斷了就嘗試重連。

#### `midi_file_player.py` — 自動演奏機

讀取 `.mid` 檔案，按照時間軸逐個音符播放。播放迴圈在獨立的 `threading.Thread` 上運作。支援暫停、停止、拖動、調速。播放前有 4 拍倒數。

#### `midi_preprocessor.py` — 9 階段整理師

把任意 MIDI 檔案適配到遊戲的有限音域。9 個階段：打擊過濾 → 音軌篩選 → 八度去重 → 智慧移調 → 八度摺疊 → 碰撞去重 → 複音限制 → 力度正規化 → 時間量化。每個階段回報統計數字。

#### `midi_recorder.py` — 錄音引擎

純 Python，無 Qt 依賴。用 `time.perf_counter()` 做高精度時間戳。`list.append()` 在 CPython 下是 GIL 原子操作，所以不需要額外的鎖。

```python
recorder = MidiRecorder()
recorder.start()
# ... rtmidi callback 呼叫 recorder.record_event("note_on", 60, 100)
events = recorder.stop()  # 回傳 list[RecordedEvent]
```

#### `midi_writer.py` — 匯出 .mid

把 `RecordedEvent` 列表轉成標準 MIDI Type 0 檔案。處理 timestamp → delta tick 的轉換。

#### `auto_tune.py` — 錄音後處理

兩個功能：
1. **節拍量化**（`quantize_to_beat_grid`）：把不精準的時間點對齊到節拍格線，strength 0.0-1.0 控制「拉多緊」
2. **音階校正**（`snap_to_scale`）：把超出範圍的音符摺回可演奏區間

#### `beat_sequence.py` — ★ Beat-based 多軌模型

v0.5.0 新增的核心。所有時間用**拍**（float）而不是秒：

```python
@dataclass
class BeatNote:
    time_beats: float      # 位置（拍）
    duration_beats: float  # 長度（拍）
    note: int              # MIDI 0-127
    velocity: int = 100
    track: int = 0

# 好處：改 BPM 不會壞掉音符位置
# 拍轉秒：time_seconds = time_beats * (60.0 / tempo_bpm)
```

`EditorSequence` 提供完整的 CRUD：
- `add_note()` / `add_rest()` — 在游標位置新增
- `delete_note()` / `move_note()` / `resize_note()` — 編輯
- `undo()` / `redo()` — 100 步歷史
- `copy_notes()` / `paste_at_cursor()` — 剪貼簿
- `to_midi_file_events()` / `from_midi_file_events()` — MIDI 轉換
- `to_project_dict()` / `from_project_dict()` — JSON 序列化

支援 12 軌、5 種拍號、mute/solo、12 色色盤。

#### `note_sequence.py` — 舊版秒制模型

v0.4.0 的編輯器模型，時間用秒。仍保留作為向後相容。

#### `mapping_schemes.py` — 方案倉庫

5 種鍵位方案的對照表：36 鍵、32 鍵、24 鍵、48 鍵、88 鍵。

#### `priority.py` — 加速器

`SetThreadPriority(TIME_CRITICAL)` + `timeBeginPeriod(1)` — 讓關鍵路徑有最高的排程優先權和 1ms 計時器精度。

### GUI 模組 (`gui/`)

#### `app_shell.py` — 總指揮

主視窗的骨架。組裝所有 UI 元件、串接信號。內含 `MidiProcessor`——rtmidi 執行緒和 Qt 主執行緒之間的橋樑。

#### `theme.py` — 化妝師

「賽博墨韻」深色主題：

```
墨黑底 #0A0E14  ██  ← 最深的背景
卷軸面 #101820  ██  ← 次深
宣紙暗 #1A2332  ██  ← 卡片背景
賽博青 #00F0FF  ██  ← 主要強調色（霓虹青）
金墨   #D4A853  ██  ← 次要強調色（古風金）
宣紙白 #E8E0D0  ██  ← 文字顏色
```

用 Qt Style Sheet（QSS，類似網頁的 CSS）統一風格。

#### `icons.py` — 向量圖示

所有圖示用 `QPainter` 程式碼畫。每個圖示是一個 `draw_xxx(painter, rect, color)` 函式。好處：任意大小不失真、不需要圖片檔。

#### `views/editor_view.py` — ★ 拍號制編輯器

整合 `EditorSequence` + `NoteRoll` + `ClickablePiano`。

鍵盤快捷鍵：
- `1`-`5`: 切換時值（全音符到十六分音符）
- `0`: 插入休止符
- `Ctrl+Z` / `Ctrl+Y`: undo / redo
- `Space`: 播放/停止
- `Delete`: 刪除選取的音符

#### `widgets/note_roll.py` — ★ Beat-based Piano Roll

Beat-based 水平時間軸。特色：
- 拍格線（粗 bar line + 細 beat line + 超細 sub-beat）
- 音符 = 圓角矩形，顏色 = 軌道色
- 休止符 = 紅色半透明長條
- Ghost notes = 非活躍軌道音符，20% 透明度
- 游標 = 青色垂直線
- 滑鼠：左鍵選取/拖曳，右鍵刪除
- Ctrl+滾輪：以滑鼠位置為中心縮放

#### `widgets/clickable_piano.py` — 可互動鋼琴

跟 `PianoDisplay` 同樣視覺風格，但可以點選。發射 `note_clicked(int)` 信號。

#### `widgets/piano_display.py` — 琴鍵動畫

用 QPainter 畫出鋼琴鍵盤。每個琴鍵有三種狀態：靜止、按下（青色 + 光暈）、剛放開（淡出動畫）。

#### 其他 widgets

| 檔案 | 功能 |
|------|------|
| `sidebar.py` | 左側導航（演奏 / 曲庫 / 編輯器 切頁） |
| `now_playing_bar.py` | Spotify 風格底部列（迷你鋼琴、進度條、速度） |
| `animated_widgets.py` | `IconButton`（動畫圖示按鈕）+ disabled 狀態灰色 |
| `progress_bar.py` | 可拖曳的進度條 |
| `speed_control.py` | 0.25x - 2.0x 播放速度 |
| `log_viewer.py` | 即時事件日誌（最近 N 行 MIDI 事件） |
| `status_bar.py` | 連線狀態、延遲顯示 |
| `mini_piano.py` | 迷你版鋼琴（NowPlayingBar 裡用的） |
| `track_list.py` | 曲目清單（LibraryView 裡用的） |

### 工具模組 (`utils/`)

#### `admin.py` — 權限門衛

遊戲通常以較高權限運行。如果我們的程式權限不夠，`SendInput` 會被擋。啟動時檢查並提示提權。

#### `ime.py` — 輸入法偵探

如果注音/倉頡輸入法是開的，按鍵會被攔截。這個模組偵測輸入法狀態並提醒關閉。

---

## 10. 重要觀念：執行緒與延遲

### 10.1 什麼是執行緒？

想像一家餐廳：
- **單執行緒** = 只有一個服務生，點菜、送菜、收錢都是他
- **多執行緒** = 有好幾個服務生，可以同時做不同的事

我們的程式有這些執行緒：

```
主執行緒（Qt Event Loop）
├── 畫面更新、按鈕點擊、動畫…
│
rtmidi 執行緒（由 python-rtmidi 建立）
├── 接收 MIDI 訊號
├── 查翻譯表
├── 模擬按鍵 ← 直接在這裡做，不傳給主執行緒！
│
播放執行緒（threading.Thread，播放 .mid 檔時建立）
├── 按時間播放音符
├── 模擬按鍵
```

### 10.2 為什麼不把所有事情都丟給主執行緒？

**延遲！**

如果模擬按鍵要先排隊等主執行緒處理，會多出幾毫秒的延遲。
對音樂來說，10 毫秒的延遲就能被感覺到。

所以我們的設計是：
- **按鍵模擬** → 直接在 rtmidi 執行緒上做（最快）
- **畫面更新** → 透過 Qt 信號傳到主執行緒（慢一點沒關係，人眼感受不到）

### 10.3 GIL：Python 的大鎖

Python 有一個全域鎖（GIL），同一時間只有一個執行緒能執行 Python 程式碼。

但這不影響我們，因為：
- `SendInput` 是 C 函式呼叫，不受 GIL 限制
- `time.sleep` 會釋放 GIL
- `list.append()` 在 GIL 保護下是原子操作（錄音用到這點）
- 切換映射方案時只是換一個字典參照（原子操作）

---

## 11. Beat-based 編輯器：新一代資料模型

### 11.1 為什麼用「拍」而不是「秒」？

想像你在寫一首 120 BPM 的曲子。一個四分音符 = 0.5 秒。

如果你之後把 BPM 改成 60，那個四分音符「應該」變成 1.0 秒——但如果你用秒來存位置，它還是 0.5 秒，整首曲子的節奏結構就壞了。

**用拍來存**：四分音符永遠是 1.0 拍，不管 BPM 怎麼變。秒只在播放的那一刻才計算：

```
time_seconds = time_beats × (60 / tempo_bpm)
```

### 11.2 資料結構

```python
@dataclass
class BeatNote:
    time_beats: float      # 在第幾拍開始
    duration_beats: float  # 持續幾拍
    note: int              # MIDI 音符（0-127）
    velocity: int = 100    # 力道
    track: int = 0         # 屬於第幾軌

@dataclass
class BeatRest:
    time_beats: float      # 在第幾拍開始
    duration_beats: float  # 持續幾拍
    track: int = 0

@dataclass
class Track:
    name: str = ""
    color: str = "#00F0FF"
    channel: int = 0
    muted: bool = False
    solo: bool = False
```

### 11.3 時值預設

| 鍵盤快捷鍵 | 名稱 | 拍數 |
|-----------|------|------|
| `1` | 全音符 (1/1) | 4.0 拍 |
| `2` | 二分音符 (1/2) | 2.0 拍 |
| `3` | 四分音符 (1/4) | 1.0 拍 |
| `4` | 八分音符 (1/8) | 0.5 拍 |
| `5` | 十六分音符 (1/16) | 0.25 拍 |

### 11.4 拍號

| 拍號 | beats_per_bar | 解釋 |
|------|-------------|------|
| 4/4 | 4.0 | 每小節 4 拍（最常見） |
| 3/4 | 3.0 | 每小節 3 拍（華爾滋） |
| 2/4 | 2.0 | 每小節 2 拍（進行曲） |
| 6/8 | 3.0 | 6 個八分音符 = 3 拍 |
| 4/8 | 2.0 | 4 個八分音符 = 2 拍 |

公式：`beats_per_bar = numerator × (4 / denominator)`

### 11.5 Undo/Redo

每次編輯前拍一張「快照」（所有音符 + 游標位置 + 活躍軌道），推入 undo stack。最多 100 步。

```
[初始] → add_note → [快照1] → move_note → [快照2] → delete → [快照3]
                                                                  ↑ 你在這裡
                                                        按 Ctrl+Z → 回到 [快照2]
                                                        再按 Ctrl+Z → 回到 [快照1]
                                                        按 Ctrl+Y → 前進到 [快照2]
```

---

## 12. 測試哲學：為什麼寫 366 個測試

### 12.1 測試是什麼？

測試是「用程式檢查程式」：

```python
def test_lookup_middle_c():
    mapper = KeyMapper()
    result = mapper.lookup(60)          # 中央 C
    assert result is not None           # 一定有結果
    assert result.scan_code == 0x1E     # 對應 A 鍵
```

如果 `assert` 失敗，pytest 會報錯告訴你哪裡壞了。

### 12.2 為什麼這麼多？

| 原因 | 解釋 |
|------|------|
| **信心** | 改了一個檔案，跑一次 pytest，如果全過就知道沒弄壞其他東西 |
| **文件** | 測試就是最好的使用範例——看測試就知道函式怎麼用 |
| **回歸** | 修了一個 bug，寫一個測試確保它不會再回來 |
| **邊界** | 測試極端情況：空列表、最大值、最小值、無效輸入 |

### 12.3 Mock：假裝有硬體

我們不需要真的 MIDI 鍵盤和 Windows 來跑測試：

```python
from unittest.mock import patch

with patch("cyber_qin.core.key_simulator._send") as mock_send:
    simulator = KeySimulator()
    simulator.press(60, mapping)
    assert mock_send.call_count == 1   # 確認「假裝送了一次按鍵」
```

`mock` 會攔截真正的函式呼叫，讓你可以檢查它被呼叫了幾次、用什麼參數。

### 12.4 測試分佈

| 測試檔案 | 測試什麼 | 約幾個 |
|---------|---------|--------|
| `test_key_mapper.py` | 音符 → 按鍵映射 | ~30 |
| `test_key_simulator.py` | SendInput 模擬 | ~25 |
| `test_midi_file_player.py` | .mid 播放 | ~30 |
| `test_midi_preprocessor.py` | 9 階段預處理 | ~80 |
| `test_mapping_schemes.py` | 5 種方案 | ~25 |
| `test_auto_tune.py` | 量化 + 校正 | ~25 |
| `test_midi_recorder.py` | 錄音 + 匯出 | ~20 |
| `test_note_sequence.py` | 舊版序列模型 | ~20 |
| `test_beat_sequence.py` | ★ 新版 beat 模型 | ~77 |

> **從哪裡學**：[pytest 官方文件](https://docs.pytest.org/)，先做 "Getting Started" 就好。

---

## 13. 打包發佈：從原始碼到可執行檔

### 13.1 為什麼需要打包？

使用者不想裝 Python、不想 `pip install`、不想開終端機。
他們只想**雙擊一個 .exe 就能跑**。

### 13.2 PyInstaller

PyInstaller 把你的 Python 程式碼 + 所有依賴 + Python 直譯器本身，打包成一個資料夾或一個 .exe。

```bash
# 用我們的 spec 檔案建置
.venv313/Scripts/pyinstaller cyber_qin.spec --clean -y
# 輸出: dist/賽博琴仙/ (~95 MB)
```

### 13.3 注意事項

| 問題 | 解法 |
|------|------|
| PyQt6 在 Python 3.14 爆炸 | 用 Python 3.13 的 venv |
| 相對 import 失敗 | 用 `launcher.py` 薄包裝 |
| 防毒軟體誤報 | 建置時設 `uac_admin=True` |

### 13.4 CI/CD 自動發佈

推送 `v*` tag → GitHub Actions 自動：
1. 安裝依賴
2. PyInstaller 建置
3. 壓縮成 .zip
4. 建立 GitHub Release

```bash
git tag v0.5.0
git push origin v0.5.0
# → 自動觸發，幾分鐘後 Release 頁面就有下載連結
```

---

## 14. 如何安裝與執行

### 14.1 安裝 Python

到 [python.org](https://www.python.org/downloads/) 下載 **Python 3.11 或 3.12 或 3.13**。

> 注意：Python 3.14 和 PyQt6 不相容，不要用！

安裝時**一定要勾選「Add Python to PATH」**。

### 14.2 安裝專案

打開命令提示字元（按 Win+R，輸入 `cmd`），然後：

```bash
# 1. 切到專案目錄
cd C:\專案\賽博琴仙

# 2. 安裝（editable 模式 + 開發工具）
pip install -e .[dev]
```

`-e` 是「editable」的意思——你改了程式碼不需要重新安裝，馬上生效。

### 14.3 執行

```bash
# 方法一：用 entry point
cyber-qin

# 方法二：直接用 Python
python -m cyber_qin.main
```

第一次執行會問你要不要用管理員身份重新啟動。建議選「是」。

### 14.4 跑測試

```bash
# 跑所有 366 個測試
pytest

# 簡短結果
pytest -q

# 只跑某個檔案
pytest tests/test_beat_sequence.py

# 程式碼風格
ruff check .
```

測試不需要真的 MIDI 裝置——全部用 mock 模擬。

---

## 15. 技術學習路線圖

如果你是零基礎，建議按以下順序學習：

### 階段 1：Python 基礎（1-2 週）

```
Python 官方教學 → 第 1-5 章
├── 變數、函式、if/else/for
├── 字典和列表
├── 類別（class）
└── 匯入模組（import）
```

能看懂 `key_mapper.py` 就算過關。

### 階段 2：理解核心原理（1 週）

```
讀 constants.py → key_mapper.py → key_simulator.py
├── 掃描碼是什麼
├── ctypes 怎麼呼叫 C API
└── SendInput 怎麼模擬按鍵
```

能解釋「為什麼用掃描碼不用虛擬鍵碼」就算過關。

### 階段 3：MIDI 基礎（1 週）

```
讀 mido 文件 → midi_listener.py → midi_file_player.py
├── MIDI 訊息結構
├── tick vs 秒
└── 播放迴圈怎麼運作
```

能看懂 `midi_preprocessor.py` 的 9 個階段就算過關。

### 階段 4：GUI 基礎（1-2 週）

```
Qt for Python 教學 → theme.py → piano_display.py → app_shell.py
├── QApplication / QMainWindow / QWidget
├── Layout 排版
├── QPainter 自訂繪圖
└── Signal / Slot 事件機制
```

能看懂 `NoteRoll.paintEvent` 就算過關。

### 階段 5：進階概念（持續學習）

```
├── 多執行緒（threading）
├── 測試（pytest + mock）
├── 打包（PyInstaller）
├── CI/CD（GitHub Actions）
└── 資料模型設計（beat_sequence.py）
```

### 推薦資源彙整

| 主題 | 資源 | 難度 |
|------|------|------|
| Python 入門 | [Python 官方教學](https://docs.python.org/3/tutorial/) | 初 |
| Python 進階 | [Fluent Python](https://www.oreilly.com/library/view/fluent-python-2nd/9781492056348/) | 中 |
| PyQt6 | [Qt for Python 教學](https://doc.qt.io/qtforpython-6/tutorials/) | 初-中 |
| MIDI 理論 | [MIDI.org 基礎](https://www.midi.org/specifications) | 初 |
| mido | [mido 文件](https://mido.readthedocs.io/) | 初 |
| ctypes | [Python ctypes 文件](https://docs.python.org/3/library/ctypes.html) | 中 |
| pytest | [pytest 入門](https://docs.pytest.org/en/stable/getting-started.html) | 初 |
| Git | [Pro Git 中文版](https://git-scm.com/book/zh-tw/v2) | 初 |
| GitHub Actions | [官方文件](https://docs.github.com/en/actions) | 中 |

---

## 16. 常見陷阱與學到的教訓

### 陷阱 1：SendInput 結構體大小錯誤

**問題**：`sizeof(INPUT)` 必須是 40（64 位元），但如果 union 裡面少了 `MOUSEINPUT`（最大的成員），大小會變成 32，`SendInput` 就會靜靜地回傳 0。

**教訓**：ctypes Union 的大小取決於最大成員。即使你不用滑鼠功能，也必須包含 `MOUSEINPUT`。

### 陷阱 2：MIDI tick 不是秒

**問題**：`mido.merge_tracks()` 回傳的 `msg.time` 是 **tick**（節拍單位），不是秒。

**教訓**：永遠用 `mido.tick2second(msg.time, ticks_per_beat, tempo)` 來轉換。

### 陷阱 3：Qt 類別不能在 QApplication 之前建立

**問題**：如果你在模組頂層定義繼承 `QObject` 的類別，但這個模組在 `QApplication()` 建立之前被 import，整個程式會爆炸。

**教訓**：用 lazy import 模式——把 Qt 類別的定義放在函式裡面，第一次使用時才建立。

### 陷阱 4：播放迴圈阻塞主執行緒

**問題**：雖然用了 `QThread` 和 `moveToThread()`，但直接呼叫 worker 的方法（而非透過信號）仍然會在呼叫者的執行緒上執行。播放迴圈的 `while + sleep` 凍結了整個 GUI。

**教訓**：用 `threading.Thread` 來跑阻塞迴圈，透過 `threading.Event` 來控制暫停/停止。

### 陷阱 5：PyQt6 與 Python 3.14

**問題**：Python 3.14 alpha 會在 import PyQt6 時爆出 "Unable to embed qt.conf" 錯誤。

**教訓**：用穩定版的 Python（3.11-3.13）。打包時用專門的 3.13 venv。

### 陷阱 6：beat-based vs seconds-based 時間模型

**問題**：舊版 `NoteSequence` 用秒儲存音符位置。改 BPM 後音符的拍子位置就不對了。

**教訓**：用拍（beat）作為主要時間單位。秒只在需要播放/匯出的那一刻才計算。

---

## 17. 詞彙表

| 術語 | 白話解釋 |
|------|---------|
| **MIDI** | 音樂設備之間的溝通語言（像是音樂界的 USB） |
| **掃描碼** | 每個實體按鍵的硬體編號（遊戲用這個認鍵） |
| **DirectInput** | Windows 的遊戲輸入介面，大部分遊戲用它讀鍵盤 |
| **callback** | 「等事情發生時打給我」——你先登記一個函式，事件發生時它會被自動呼叫 |
| **執行緒** | 程式裡面的「分身」，可以同時做不同的事 |
| **Signal/Slot** | Qt 的事件通知機制——「某件事發生了」→「做某個反應」 |
| **GIL** | Python 的全域鎖，同時只讓一個執行緒跑 Python 程式碼 |
| **mock** | 測試用的假物件，模擬真實元件的行為 |
| **QSS** | Qt Style Sheet，類似網頁的 CSS，用來美化 Qt 元件 |
| **UAC** | 使用者帳戶控制——Windows 問你「允許此程式做變更嗎？」的那個彈窗 |
| **dataclass** | Python 的自動類別產生器，幫你少寫重複的程式碼 |
| **transpose** | 移調——把所有音符整體往上或往下移 |
| **quantize** | 量化——把不精準的時間點對齊到整齊的格線上 |
| **daemon thread** | 背景執行緒——主程式結束時它會自動結束，不會卡住 |
| **beat** | 拍——音樂的基本時間單位，通常 1 拍 = 1 個四分音符 |
| **BPM** | Beats Per Minute——每分鐘幾拍，決定曲子快慢 |
| **拍號** | 如 4/4、3/4——分子 = 每小節幾拍，分母 = 以什麼音符為一拍 |
| **ghost note** | 非活躍軌道的音符，以半透明顯示，提供上下文參考 |
| **undo/redo** | 復原/重做——回到上一步或前進到下一步 |
| **piano roll** | 水平時間軸上的音符視覺化，像是自動演奏鋼琴的紙卷 |
| **CI/CD** | 持續整合/持續部署——每次提交程式碼自動跑測試和發佈 |
| **PyInstaller** | 把 Python 程式打包成獨立可執行檔的工具 |
| **Entry Point** | 程式的入口——`pip install` 後可以直接打 `cyber-qin` 執行 |

---

> **最後的話**：這個專案從一個簡單的「鋼琴按鍵 → 遊戲按鍵」翻譯器，成長為一個有 40 個模組、366 個測試、5 種模式的完整桌面應用。每一層技術都可以獨立學習。不需要一次搞懂所有東西——從你最感興趣的部分開始，一步一步來就好。
