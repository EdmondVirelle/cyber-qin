# 賽博琴仙 — 軟體建構技術導覽

> **MIT 6.031 Software Construction 風格課程教材**
>
> 本文件是一份結構化的技術導覽，模仿 MIT 6.031（軟體建構）課程的教學格式。
> 每一篇 Reading 都有明確的**學習目標**、**漸進式講解**、**程式碼範例**、**自我檢測練習**，
> 以及回扣到核心三原則的**總結**。
>
> **適合對象**：想從零理解這個專案的開發者——無論你是完全初學者或有經驗的工程師。

---

## 賽博琴仙的三大核心原則

受 MIT 6.031 "Safe from bugs / Easy to understand / Ready for change" 啟發，
本專案的每一個設計決策都圍繞著三個原則：

| 原則 | 英文 | 含義 |
|------|------|------|
| **低延遲** | Low Latency | 從琴鍵按下到遊戲角色動作 < 2ms。音樂演奏不容許感知得到的延遲。 |
| **音樂正確** | Musically Correct | 音符映射精確、時間量化正確、MIDI 協議語義完整。 |
| **可維護** | Maintainable | 清晰的架構、450 個測試、型別提示、模組化設計。 |

在每篇 Reading 的總結中，我們會用這三個原則來評估所學的技術。

---

## 課程大綱

| # | Reading | 主題 | 前置需求 |
|---|---------|------|---------|
| 1 | [系統總覽與架構](#reading-1-系統總覽與架構) | 這個程式做什麼？技術棧全貌 | 無 |
| 2 | [Python 基礎](#reading-2-python-基礎) | 變數、函式、類別、dataclass、型別提示 | 無 |
| 3 | [MIDI 協議](#reading-3-midi-協議) | MIDI 訊息、音符編號、.mid 檔案、mido | Reading 2 |
| 4 | [Windows 系統程式設計](#reading-4-windows-系統程式設計) | ctypes、SendInput、掃描碼、結構體 | Reading 2 |
| 5 | [PyQt6 GUI 框架](#reading-5-pyqt6-gui-框架) | QApplication、QWidget、QPainter、Signal/Slot | Reading 2 |
| 6 | [翻譯管線：從琴鍵到遊戲按鍵](#reading-6-翻譯管線從琴鍵到遊戲按鍵) | key_mapper、key_simulator、修飾鍵閃按 | Reading 3, 4 |
| 7 | [執行緒與延遲](#reading-7-執行緒與延遲) | 多執行緒、GIL、低延遲設計模式 | Reading 5, 6 |
| 8 | [MIDI 檔案播放](#reading-8-midi-檔案播放) | midi_file_player、tempo map、tick 轉秒 | Reading 3, 7 |
| 9 | [MIDI 預處理管線](#reading-9-midi-預處理管線) | 9 階段管線、八度摺疊、碰撞去重 | Reading 3, 6 |
| 10 | [Beat-Based 資料模型](#reading-10-beat-based-資料模型) | BeatNote、EditorSequence、undo/redo | Reading 3 |
| 11 | [Piano Roll UI](#reading-11-piano-roll-ui) | NoteRoll、QPainter 繪圖、座標系統 | Reading 5, 10 |
| 12 | [編輯器進階：多選、框選、軌道管理](#reading-12-編輯器進階多選框選軌道管理) | marquee、resize、TrackPanel、PitchRuler | Reading 10, 11 |
| 13 | [專案檔案與序列化](#reading-13-專案檔案與序列化) | JSON + gzip、autosave、.cqp 格式 | Reading 10 |
| 14 | [測試與品質保證](#reading-14-測試與品質保證) | pytest、mock、測試設計、CI | Reading 6 |
| 15 | [打包與發佈](#reading-15-打包與發佈) | PyInstaller、GitHub Actions、CI/CD | Reading 14 |

---

## Reading 1: 系統總覽與架構

### 目標

> **賽博琴仙的軟體**
>
> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | 從 MIDI 輸入到 SendInput 輸出的完整路徑在 rtmidi 回呼執行緒上同步完成，不經過 Qt 事件佇列。 | 36 鍵映射表完整覆蓋 C3-B5（MIDI 48-83），包含所有升降號的 Shift/Ctrl 修飾鍵組合。 | 45 個模組、450 個自動化測試、核心與 GUI 完全分離。 |

閱讀本篇後，你將能夠：

- 描述賽博琴仙解決的核心問題
- 畫出從 MIDI 輸入到遊戲按鍵的完整資料流
- 列舉技術棧中的五個核心技術及其角色
- 解釋核心模組（core/）與 GUI 模組（gui/）分離的設計理由

### 目錄

- [1.1 問題定義](#11-問題定義)
- [1.2 系統資料流](#12-系統資料流)
- [1.3 技術棧](#13-技術棧)
- [1.4 專案結構](#14-專案結構)
- [1.5 五大模式](#15-五大模式)
- [1.6 安裝與執行](#16-安裝與執行)
- [總結](#總結)

### 1.1 問題定義

你有一台 MIDI 鍵盤（例如 Roland FP-30X），你想在遊戲《燕雲十六聲》裡面彈琴。
問題是——遊戲只認鍵盤按鍵（Q、W、Shift+Z 這些），不認 MIDI 裝置。

**定義**：**MIDI**（Musical Instrument Digital Interface）是音樂設備之間溝通的數位協議。它不傳送聲音，只傳送指令：「哪個音被按了」「力道多大」「什麼時候放開」。

賽博琴仙是一座橋：

```
你的手指 → 鋼琴琴鍵 → USB → MIDI 訊號 → 賽博琴仙翻譯 → 模擬鍵盤按鍵 → 遊戲角色彈琴
```

### 1.2 系統資料流

```
   ┌────────────────────┐
   │   MIDI 鍵盤         │  note_on, note=60, velocity=80
   └────────┬───────────┘
            │ USB
            ▼
   ┌────────────────────┐
   │   python-rtmidi    │  C++ 層接收原始 MIDI 位元組
   │   (底層驅動)        │  在獨立的 rtmidi 執行緒上運作
   └────────┬───────────┘
            │ callback
            ▼
   ┌────────────────────┐
   │   MidiListener     │  過濾：只留 note_on / note_off
   │   (midi_listener)  │  轉換 velocity=0 的 note_on 為 note_off
   └────────┬───────────┘
            │ callback(event_type, note, velocity)
            ▼
   ┌────────────────────┐
   │   MidiProcessor    │  仍在 rtmidi 執行緒上！
   │   (app_shell)      │  ① 查翻譯表 → note 60 = 按 A 鍵
   │                    │  ② SendInput → 告訴 Windows 按 A
   │                    │  ③ 發 Qt 信號 → 通知 GUI 更新
   └────────┬───────────┘
            │
      ┌─────┴─────┐
      ▼           ▼
  【即時按鍵】  【Qt 信號】→ 主執行緒更新動畫
  SendInput()
      │
      ▼
   ┌────────────────────┐
   │   燕雲十六聲 遊戲   │  收到掃描碼 → 角色彈出音
   └────────────────────┘
```

注意關鍵設計：**按鍵模擬在 rtmidi 回呼執行緒上直接完成**，不經過 Qt 主執行緒。
這是低延遲原則的核心體現——跨執行緒通訊只用於 GUI 更新，不影響音樂性。

#### 練習 1.1：資料流分析

以下哪個操作**不**在 rtmidi 回呼執行緒上執行？

- (A) 查詢 KeyMapper 翻譯表
- (B) 呼叫 SendInput 模擬按鍵
- (C) 更新鋼琴鍵盤動畫
- (D) 過濾非 note_on/note_off 訊息

<details><summary>答案</summary>

**(C)**。GUI 更新透過 Qt Signal 跨執行緒傳遞到主執行緒。(A)(B)(D) 都在 rtmidi 回呼執行緒上同步完成。

</details>

### 1.3 技術棧

#### 核心技術

| 技術 | 角色 | 本專案用途 | 學習資源 |
|------|------|-----------|----------|
| **Python 3.11+** | 程式語言 | 整個應用程式 | [Python Tutorial](https://docs.python.org/3/tutorial/) |
| **PyQt6** | GUI 框架 | 視窗、按鈕、鋼琴鍵盤 | [Qt for Python](https://doc.qt.io/qtforpython-6/) |
| **mido** | MIDI 高階 API | 讀取 MIDI 裝置和 .mid 檔 | [mido docs](https://mido.readthedocs.io/) |
| **python-rtmidi** | MIDI 底層驅動 | USB MIDI 裝置通訊 | [python-rtmidi](https://spotlightkid.github.io/python-rtmidi/) |
| **ctypes** | FFI 標準庫 | 呼叫 Win32 API（SendInput） | [ctypes docs](https://docs.python.org/3/library/ctypes.html) |

#### 開發工具

| 技術 | 角色 | 學習資源 |
|------|------|----------|
| **pytest** | 測試框架（450 個測試） | [pytest docs](https://docs.pytest.org/) |
| **Ruff** | Linter + Formatter | [Ruff docs](https://docs.astral.sh/ruff/) |
| **PyInstaller** | 打包成 .exe | [PyInstaller docs](https://pyinstaller.org/) |
| **GitHub Actions** | CI/CD 自動測試+發佈 | [Actions docs](https://docs.github.com/en/actions) |

#### 練習 1.2：技術選型

為什麼我們選用 `python-rtmidi` 而不是直接用 `mido` 內建的 backend？

<details><summary>答案</summary>

`mido` 的預設 backend 就是 `python-rtmidi`（透過 `rtmidi` 這個 C++ 程式庫）。`mido` 提供高階 API（讀 .mid 檔、列出裝置），`python-rtmidi` 提供底層的即時 callback。兩者是上下層關係，不是替代關係。

</details>

### 1.4 專案結構

```
賽博琴仙/
├── pyproject.toml          ← 專案設定（名稱、版本、依賴）
├── CLAUDE.md               ← AI 助手開發指南
├── README.md               ← GitHub 說明
│
├── cyber_qin/              ← 原始碼（45 個模組，~10,300 行）
│   ├── __init__.py
│   ├── main.py             ← 程式進入點
│   │
│   ├── core/               ← 核心邏輯（無 GUI 依賴）
│   │   ├── constants.py        ← 掃描碼、MIDI 範圍、計時常數
│   │   ├── key_mapper.py       ← MIDI 音符 → 鍵盤按鍵映射
│   │   ├── key_simulator.py    ← ctypes SendInput 封裝
│   │   ├── midi_listener.py    ← MIDI 裝置即時監聽
│   │   ├── midi_file_player.py ← .mid 檔案播放引擎
│   │   ├── midi_preprocessor.py← 9 階段 MIDI 預處理
│   │   ├── midi_recorder.py    ← 即時錄音引擎
│   │   ├── midi_writer.py      ← 錄音匯出 .mid
│   │   ├── auto_tune.py        ← 量化 + 音階校正
│   │   ├── beat_sequence.py    ← Beat-based 多軌編輯模型
│   │   ├── project_file.py     ← 專案存檔（.cqp = JSON + gzip）
│   │   ├── note_sequence.py    ← 秒制編輯模型（舊版）
│   │   ├── mapping_schemes.py  ← 5 種鍵位方案
│   │   └── priority.py         ← 執行緒優先權 + 計時器精度
│   │
│   ├── gui/                ← 圖形介面
│   │   ├── app_shell.py        ← 主視窗框架
│   │   ├── theme.py            ← 賽博墨韻深色主題
│   │   ├── icons.py            ← 向量圖示（QPainter）
│   │   ├── views/              ← 整頁畫面
│   │   │   ├── live_mode_view.py
│   │   │   ├── library_view.py
│   │   │   └── editor_view.py
│   │   └── widgets/            ← 可重用元件
│   │       ├── piano_display.py, clickable_piano.py
│   │       ├── note_roll.py, pitch_ruler.py
│   │       ├── editor_track_panel.py, sidebar.py
│   │       ├── now_playing_bar.py, animated_widgets.py
│   │       └── ...（共 14 個元件）
│   │
│   └── utils/              ← 工具
│       ├── admin.py            ← UAC 管理員權限
│       └── ime.py              ← 輸入法偵測
│
├── tests/                  ← 450 個測試（11 個檔案，~4,100 行）
├── docs/                   ← 文件
└── .github/workflows/      ← CI/CD
```

**設計原則**：`core/` 模組**零 GUI 依賴**——它們可以在沒有 QApplication 的環境下 import 和測試。這是可維護原則的體現：核心邏輯和介面完全解耦。

#### 練習 1.3：模組依賴

下列何者是正確的 import 方向？

- (A) `core/key_mapper.py` imports from `gui/theme.py`
- (B) `gui/app_shell.py` imports from `core/key_mapper.py`
- (C) `core/midi_listener.py` imports from `gui/widgets/piano_display.py`
- (D) `gui/views/editor_view.py` imports from `gui/widgets/note_roll.py`

<details><summary>答案</summary>

**(B)** 和 **(D)**。GUI 層可以 import 核心層，但核心層絕不 import GUI 層。Widget 可以被 View import。(A) 和 (C) 違反了層級依賴規則。

</details>

### 1.5 五大模式

| 模式 | 功能 | 關鍵模組 |
|------|------|---------|
| **即時演奏** | MIDI 鍵盤 → 遊戲同步彈奏（< 2ms） | midi_listener, key_mapper, key_simulator |
| **自動播放** | .mid 檔案自動按鍵演奏 | midi_file_player, midi_preprocessor |
| **即時錄音** | 錄下演奏 → .mid 檔 | midi_recorder, midi_writer, auto_tune |
| **虛擬鍵盤** | 滑鼠點琴鍵輸入音符 | clickable_piano, note_sequence |
| **Piano Roll 編輯器** | 多軌 piano roll、undo/redo、專案存檔 | beat_sequence, project_file, note_roll, editor_view |

### 1.6 安裝與執行

```bash
# 前置：Python 3.11-3.13（不可用 3.14——PyQt6 不相容）
# 安裝時務必勾選 "Add Python to PATH"

# 1. 安裝（editable 模式 + 開發工具）
pip install -e .[dev]

# 2. 執行（需要管理員權限才能注入按鍵到遊戲）
cyber-qin

# 3. 跑測試
pytest          # 全部 450 個
pytest -q       # 簡短輸出
pytest tests/test_beat_sequence.py  # 只跑某個檔案

# 4. 程式碼風格檢查
ruff check .
```

### 總結

本篇介紹了賽博琴仙的全貌。回到核心三原則：

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| 資料流設計確保按鍵模擬在 rtmidi 執行緒上同步完成，不經過 Qt 事件佇列。 | 36 鍵映射表覆蓋 3 個完整八度（C3-B5），包含所有半音的修飾鍵組合。 | core/ 與 gui/ 嚴格分層，核心邏輯可獨立測試。 |

**延伸學習**：閱讀 `cyber_qin/main.py`（65 行）——它是整個程式的進入點，展示了啟動流程。

---

## Reading 2: Python 基礎

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | `frozen dataclass` 建立後不可修改，避免了在高頻回呼中意外 mutation 造成的資料競爭。 | 型別提示讓映射函式的輸入/輸出語義明確：`lookup(midi_note: int) -> KeyMapping | None`。 | `dataclass` 自動生成 `__eq__`、`__repr__`，減少樣板程式碼，降低出錯機率。 |

閱讀本篇後，你將能夠：

- 解釋 Python 的基本資料型別和控制流
- 使用 `class` 和 `@dataclass` 定義自訂型別
- 閱讀型別提示（type hints）並理解其文件作用
- 解釋 `frozen=True` 的語義及其在並行程式中的意義

### 目錄

- [2.1 變數與型別](#21-變數與型別)
- [2.2 函式](#22-函式)
- [2.3 類別](#23-類別)
- [2.4 dataclass：聲明式的類別](#24-dataclass聲明式的類別)
- [2.5 型別提示](#25-型別提示)
- [2.6 字典：O(1) 查詢表](#26-字典o1-查詢表)
- [2.7 套件與匯入](#27-套件與匯入)
- [總結](#總結-1)

### 2.1 變數與型別

Python 是動態型別語言——變數不需要宣告型別，賦值即建立：

```python
name = "賽博琴仙"   # str — 字串
midi_note = 60       # int — 整數
velocity = 0.75      # float — 浮點數
is_active = True     # bool — 布林值
```

**定義**：**變數**是一個名稱，綁定到記憶體中的一個物件。Python 的變數是**參照**（reference），不是盒子——賦值只是讓名稱指向新的物件。

### 2.2 函式

```python
def note_name(midi_note: int) -> str:
    """將 MIDI 音符號碼轉為人類可讀名稱。

    >>> note_name(60)
    'C4'
    >>> note_name(61)
    'C#4'
    """
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = midi_note // 12 - 1
    return f"{names[midi_note % 12]}{octave}"
```

注意三件事：
1. **型別提示** `midi_note: int` 和 `-> str` 是文件——Python 不強制檢查
2. **文件字串**（docstring）用三重引號，`>>>` 標記的是可執行的範例（doctest）
3. **f-string** `f"{names[...]}..."` 是字串內嵌表達式

### 2.3 類別

```python
class KeyMapper:
    """MIDI 音符到鍵盤按鍵的翻譯員。"""

    def __init__(self, transpose: int = 0) -> None:
        self._transpose = transpose        # 前綴底線 = 「私有」慣例
        self._map: dict[int, KeyMapping] = dict(_BASE_MAP)

    def lookup(self, midi_note: int) -> KeyMapping | None:
        """查詢音符對應的按鍵。找不到回傳 None。"""
        adjusted = midi_note + self._transpose
        return self._map.get(adjusted)
```

**定義**：**類別**（class）是一個藍圖，定義了一組資料（屬性）和操作（方法）。**實例**（instance）是根據藍圖建立的具體物件。

- `__init__` 是**建構子**——建立新實例時自動呼叫
- `self` 代表實例自身——所有實例方法的第一個參數
- `_transpose` 前綴底線是**命名慣例**，表示「非公開」

### 2.4 dataclass：聲明式的類別

手動寫類別很囉嗦——你需要 `__init__`、`__eq__`、`__repr__`。`@dataclass` 自動生成這些：

```python
from dataclasses import dataclass
from cyber_qin.core.constants import Modifier

@dataclass(frozen=True)
class KeyMapping:
    scan_code: int       # Windows 掃描碼（如 0x1E = A 鍵）
    modifier: Modifier   # NONE / SHIFT / CTRL
    label: str           # 人類可讀標籤（如 "Shift+Z"）
```

`frozen=True` 使實例**不可變**（immutable）——建立後任何屬性都不能修改。

**為什麼不可變很重要？** 在我們的程式中，`KeyMapping` 物件會在 rtmidi 回呼執行緒和 Qt 主執行緒之間共享。如果它是可變的，一個執行緒修改屬性時另一個執行緒可能正在讀取——這就是**資料競爭**（data race）。`frozen=True` 從根本上消除了這個風險。

本專案大量使用 dataclass：

| dataclass | 用途 | frozen? |
|-----------|------|---------|
| `KeyMapping` | 掃描碼 + 修飾鍵 + 標籤 | Yes |
| `MidiFileEvent` | 播放事件（時間、音符、力道） | Yes |
| `RecordedEvent` | 錄音事件 | Yes |
| `BeatNote` | 拍制音符（位置、長度、音高） | No（需要編輯） |
| `BeatRest` | 拍制休止符 | No |
| `Track` | 軌道（名稱、顏色、mute/solo） | No |

#### 練習 2.1：frozen dataclass

下列程式碼會發生什麼？

```python
mapping = KeyMapping(scan_code=0x1E, modifier=Modifier.NONE, label="A")
mapping.scan_code = 0x2C
```

- (A) `scan_code` 被改成 `0x2C`
- (B) 拋出 `FrozenInstanceError`
- (C) 靜靜地什麼都不做
- (D) 建立一個新的 `KeyMapping` 實例

<details><summary>答案</summary>

**(B)**。`frozen=True` 的 dataclass 會在 `__setattr__` 中拋出 `dataclasses.FrozenInstanceError`。這是在編譯時期就能發現的錯誤——比在執行時期遇到資料競爭好得多。

</details>

### 2.5 型別提示

```python
def lookup(self, midi_note: int) -> KeyMapping | None:
```

- `midi_note: int` — 參數應該是整數
- `-> KeyMapping | None` — 回傳值是 `KeyMapping` 或 `None`
- `|` 是 Python 3.10+ 的聯合型別語法（Union）

Python 不會在執行期檢查型別提示——它們是**文件**，幫助讀者和 IDE 理解程式碼。搭配 `mypy` 或 `pyright` 可以做靜態型別檢查。

**本專案的慣例**：所有公開函式都有型別提示。

### 2.6 字典：O(1) 查詢表

**定義**：**字典**（dict）是鍵值對的集合，支援 O(1) 平均時間的查詢、插入、刪除。

```python
# 本專案的核心：MIDI 音符號碼 → 鍵盤按鍵
_BASE_MAP: dict[int, KeyMapping] = {
    48: KeyMapping(0x2C, Modifier.NONE, "Z"),       # C3  → Z
    49: KeyMapping(0x2C, Modifier.SHIFT, "Shift+Z"), # C#3 → Shift+Z
    50: KeyMapping(0x2D, Modifier.NONE, "X"),       # D3  → X
    # ... 共 36 個條目
}
```

查詢：
```python
result = _BASE_MAP.get(60)     # MIDI 60（中央 C）→ KeyMapping 或 None
result = _BASE_MAP.get(999)    # 不存在 → None（不會拋出 KeyError）
```

`.get(key)` 比 `[key]` 安全——找不到時回傳 `None` 而不是拋出例外。

### 2.7 套件與匯入

```python
# 標準庫
import ctypes
import time

# 第三方套件
import mido

# 本專案模組（相對匯入）
from ..core.constants import Modifier, SCAN
from ..core.key_mapper import KeyMapper
```

- `..` 表示「上兩層」——從 `gui/views/` 回到 `cyber_qin/`，再進入 `core/`
- 相對匯入只在套件內部使用（需要 `__init__.py`）

#### 練習 2.2：匯入路徑

在 `cyber_qin/gui/views/editor_view.py` 中，要匯入 `cyber_qin/core/beat_sequence.py` 裡的 `BeatNote`，正確的語法是？

- (A) `from beat_sequence import BeatNote`
- (B) `from ...core.beat_sequence import BeatNote`
- (C) `from cyber_qin.core.beat_sequence import BeatNote`
- (D) (B) 和 (C) 都可以

<details><summary>答案</summary>

**(D)**。(B) 是相對匯入（`...` = 上三層到 `cyber_qin/`），(C) 是絕對匯入。兩者都正確。本專案慣用相對匯入。

</details>

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| `frozen dataclass` 消除共享資料的 mutation 風險，避免跨執行緒的資料競爭。 | 型別提示讓函式簽名自帶文件：`lookup(int) -> KeyMapping | None`。 | `dataclass` 減少樣板程式碼，`dict.get()` 比 `dict[]` 更安全。 |

**延伸學習**：
- [Python 官方教學 Ch.1-5](https://docs.python.org/3/tutorial/) — 基礎語法
- [Fluent Python 2nd Ed.](https://www.oreilly.com/library/view/fluent-python-2nd/9781492056348/) — 進階

---

## Reading 3: MIDI 協議

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | MIDI callback 在 C++ 層觸發，延遲僅為 USB 輪詢間隔（~1ms）。 | 理解 note_on/note_off 配對語義，避免「幽靈音」（stuck note）。 | mido 提供 Pythonic API，隱藏底層 MIDI 位元組操作的複雜度。 |

閱讀本篇後，你將能夠：

- 解釋 MIDI 協議的 channel voice message 格式
- 將 MIDI 音符號碼轉換為音名（如 60 → C4）
- 區分 tick 和秒，並使用 `mido.tick2second()` 正確轉換
- 說明 `mido` 和 `python-rtmidi` 的分工

### 目錄

- [3.1 什麼是 MIDI？](#31-什麼是-midi)
- [3.2 MIDI 訊息結構](#32-midi-訊息結構)
- [3.3 音符編號系統](#33-音符編號系統)
- [3.4 .mid 檔案與 tick](#34-mid-檔案與-tick)
- [3.5 mido 與 python-rtmidi](#35-mido-與-python-rtmidi)
- [總結](#總結-2)

### 3.1 什麼是 MIDI？

**定義**：**MIDI**（Musical Instrument Digital Interface, 1983）是一套數位通訊協議，定義了音樂設備之間交換演奏資料的格式。MIDI 不傳送音訊——它只傳送**事件**（event）。

類比：MIDI 之於音樂，就像樂譜之於演奏。樂譜告訴你「彈第幾個音、力道多大、持續多久」，但不包含聲音本身。

### 3.2 MIDI 訊息結構

當你按下鋼琴鍵：

```
note_on  channel=0  note=60  velocity=80  time=0
```

| 欄位 | 型別 | 範圍 | 含義 |
|------|------|------|------|
| `type` | str | `note_on` / `note_off` | 按下 / 放開 |
| `channel` | int | 0-15 | MIDI 頻道（不同樂器可用不同頻道） |
| `note` | int | 0-127 | 音高（60 = 中央 C） |
| `velocity` | int | 0-127 | 力道（0 = 最輕，127 = 最重） |

**重要規則**：`velocity=0` 的 `note_on` 等價於 `note_off`。某些 MIDI 裝置只發送 `note_on`，用 velocity 0 表示放開。我們的 `MidiListener` 會自動轉換。

#### 練習 3.1：MIDI 語義

一個 MIDI 裝置依序發送以下訊息：

```
note_on  note=60  velocity=100
note_on  note=64  velocity=90
note_on  note=60  velocity=0
note_off note=64  velocity=0
```

在第三個訊息之後，哪些音符仍在「按住」狀態？

<details><summary>答案</summary>

只有 **note 64**。第三個訊息 `note_on velocity=0` 等價於 `note_off note=60`，所以 60 已放開。64 在第四個訊息才放開。

</details>

### 3.3 音符編號系統

```
MIDI 號碼:   48  49  50  51  52  53  54  55  56  57  58  59
音名:        C3  C#3 D3  D#3 E3  F3  F#3 G3  G#3 A3  A#3 B3

MIDI 號碼:   60  61  62  63  64  65  66  67  68  69  70  71
音名:        C4  C#4 D4  D#4 E4  F4  F#4 G4  G#4 A4  A#4 B4

MIDI 號碼:   72  73  74  75  76  77  78  79  80  81  82  83
音名:        C5  C#5 D5  D#5 E5  F5  F#5 G5  G#5 A5  A#5 B5
```

**公式**：
```python
octave = midi_note // 12 - 1    # 60 // 12 - 1 = 4
semitone = midi_note % 12       # 60 % 12 = 0 → C
```

遊戲的 36 鍵模式涵蓋 **MIDI 48-83**（C3 到 B5 = 3 個完整八度，每個八度 12 個半音）。

### 3.4 .mid 檔案與 tick

**定義**：**Standard MIDI File**（.mid）將 MIDI 事件按時間順序序列化。時間單位是 **tick**，不是秒。

```python
import mido

mid = mido.MidiFile("song.mid")
print(mid.ticks_per_beat)  # 例如 480（每拍 480 ticks）
```

tick 到秒的轉換需要 tempo（微秒/拍）：

```python
# tempo = 500000 表示每拍 500000 微秒 = 0.5 秒 = 120 BPM
seconds = mido.tick2second(ticks, ticks_per_beat, tempo)
```

**陷阱**：`mido.merge_tracks()` 回傳的 `msg.time` 是 **delta tick**（距離上一個事件的 tick 數），不是秒。直接當秒用會讓播放時間全部錯亂。

```python
# ✗ 錯誤：直接把 tick 當秒
for msg in mido.merge_tracks(mid.tracks):
    time.sleep(msg.time)  # msg.time 是 tick，不是秒！

# ✓ 正確：先轉換
for msg in mido.merge_tracks(mid.tracks):
    seconds = mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
    time.sleep(seconds)
```

#### 練習 3.2：tick 轉秒

一個 MIDI 檔案的 `ticks_per_beat = 480`，tempo = 500000（120 BPM）。
一個事件的 delta time 是 240 ticks。它距離上一個事件多少秒？

- (A) 240 秒
- (B) 0.5 秒
- (C) 0.25 秒
- (D) 1.0 秒

<details><summary>答案</summary>

**(C)**。`mido.tick2second(240, 480, 500000)` = 240/480 × 0.5 = 0.25 秒。240 ticks 是半拍，120 BPM 下一拍 = 0.5 秒，半拍 = 0.25 秒。

</details>

### 3.5 mido 與 python-rtmidi

| 層級 | 套件 | 職責 |
|------|------|------|
| 高階 API | `mido` | 列裝置、開連線、讀 .mid、轉時間 |
| 底層驅動 | `python-rtmidi` | C++ RtMidi 的 Python 綁定，提供即時 callback |

```python
# 列出裝置
ports = mido.get_input_names()
# → ['Roland Digital Piano:Roland Digital Piano MIDI 1 ...']

# 開啟裝置，設定 callback
port = mido.open_input(ports[0], callback=on_midi_message)

# callback 在 rtmidi 的 C++ 執行緒上被呼叫——不是主執行緒！
def on_midi_message(message):
    if message.type == "note_on" and message.velocity > 0:
        process_note(message.note, message.velocity)
```

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| rtmidi callback 在 C++ 層觸發，跳過 Python GIL 排程延遲。 | 正確處理 `velocity=0` 的 `note_on` 為 `note_off`，避免 stuck note。 | `mido.tick2second()` 封裝了 tick↔秒的複雜換算。 |

**延伸學習**：
- [mido 官方文件](https://mido.readthedocs.io/) — 重點讀 "Ports" 和 "MIDI Files"
- [MIDI.org Specifications](https://www.midi.org/specifications) — 協議完整規格

---

## Reading 4: Windows 系統程式設計

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | `SendInput` 保證同一批次的按鍵事件不會被其他程式的輸入插隊。 | 使用掃描碼（scan code）而非虛擬鍵碼（VK），確保 DirectInput 遊戲正確接收。 | ctypes 結構體映射必須與 C 記憶體佈局完全一致——一個 byte 都不能差。 |

閱讀本篇後，你將能夠：

- 解釋 ctypes 如何讓 Python 呼叫 C 語言的 DLL 函式
- 定義 ctypes `Structure` 和 `Union`，並解釋記憶體對齊
- 區分掃描碼和虛擬鍵碼，說明為什麼遊戲需要掃描碼
- 描述 `sizeof(INPUT)` 必須為 40 的原因

### 目錄

- [4.1 ctypes 是什麼？](#41-ctypes-是什麼)
- [4.2 呼叫 Windows API](#42-呼叫-windows-api)
- [4.3 結構體與聯合體](#43-結構體與聯合體)
- [4.4 掃描碼 vs 虛擬鍵碼](#44-掃描碼-vs-虛擬鍵碼)
- [4.5 INPUT 結構體的大坑](#45-input-結構體的大坑)
- [總結](#總結-3)

### 4.1 ctypes 是什麼？

**定義**：**ctypes** 是 Python 標準庫的 Foreign Function Interface（FFI），讓 Python 直接呼叫 C 語言編譯的動態連結庫（DLL / .so）函式。

Windows 系統 API 都是 C 語言寫的 DLL。ctypes 讓我們不需要寫任何 C 程式碼就能使用它們：

```python
import ctypes

# 呼叫 Windows API：檢查是否為管理員
is_admin = ctypes.windll.shell32.IsUserAnAdmin()
```

### 4.2 呼叫 Windows API

本專案使用的 Windows API：

| API 函式 | DLL | 用途 |
|----------|-----|------|
| `SendInput()` | user32 | 模擬鍵盤/滑鼠輸入 |
| `IsUserAnAdmin()` | shell32 | 檢查管理員權限 |
| `ShellExecuteW()` | shell32 | 以管理員重新啟動 |
| `DwmSetWindowAttribute()` | dwmapi | 啟用深色標題列 |
| `SetThreadPriority()` | kernel32 | 設定執行緒優先權 |
| `timeBeginPeriod()` | winmm | 請求 1ms 計時器精度 |
| `ImmGetConversionStatus()` | imm32 | 偵測輸入法狀態 |

### 4.3 結構體與聯合體

C 語言的 `struct` 是一組欄位的連續記憶體佈局。在 ctypes 中：

```python
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),        # 虛擬鍵碼（我們設 0）
        ("wScan", ctypes.c_ushort),       # 掃描碼 ← 我們用這個
        ("dwFlags", ctypes.c_ulong),      # 旗標：KEYEVENTF_SCANCODE
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]
```

**定義**：**聯合體**（Union）是多個型別共用同一塊記憶體。Union 的大小 = **最大成員**的大小。

```python
class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),       # 24 bytes
        ("mi", MOUSEINPUT),       # 32 bytes ← 最大！
        ("hi", HARDWAREINPUT),    # 8 bytes
    ]
# sizeof(_INPUT_UNION) = 32（取最大成員）
```

### 4.4 掃描碼 vs 虛擬鍵碼

| 方式 | 範例 | 誰用 |
|------|------|------|
| **虛擬鍵碼**（VK） | `VK_A = 0x41` | 一般應用程式（記事本、瀏覽器） |
| **掃描碼**（Scan Code） | `A = 0x1E` | 遊戲（DirectInput / Raw Input） |

**定義**：**掃描碼**是鍵盤硬體層面的編號——每個實體按鍵有一個固定的掃描碼，與語言設定無關。**DirectInput** 是 Windows 的遊戲輸入 API，大部分遊戲透過它讀取鍵盤，只認掃描碼。

```python
# 掃描碼對照（constants.py）
SCAN = {
    "Z": 0x2C, "X": 0x2D, "C": 0x2E, "V": 0x2F,  # 第一列
    "A": 0x1E, "S": 0x1F, "D": 0x20, "F": 0x21,  # 第二列
    "Q": 0x10, "W": 0x11, "E": 0x12, "R": 0x13,  # 第三列
    "LSHIFT": 0x2A, "LCTRL": 0x1D,                # 修飾鍵
}
```

如果你用虛擬鍵碼送 `SendInput`，遊戲會完全無視——因為它只監聽掃描碼。

#### 練習 4.1：掃描碼

下列哪個 `dwFlags` 組合能讓 DirectInput 遊戲正確接收「按下 A 鍵」？

- (A) `wVk=0x41, wScan=0, dwFlags=0`
- (B) `wVk=0, wScan=0x1E, dwFlags=KEYEVENTF_SCANCODE`
- (C) `wVk=0x41, wScan=0x1E, dwFlags=0`
- (D) `wVk=0, wScan=0x41, dwFlags=KEYEVENTF_SCANCODE`

<details><summary>答案</summary>

**(B)**。`KEYEVENTF_SCANCODE` (0x0008) 告訴 Windows 使用 `wScan` 欄位，而 A 鍵的掃描碼是 `0x1E`。(A) 用 VK，遊戲不認。(C) 沒設 SCANCODE flag。(D) 掃描碼寫錯（`0x41` 是 VK_A，不是掃描碼）。

</details>

### 4.5 INPUT 結構體的大坑

這是本專案踩過最痛的 bug：

```python
class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),     # 4 bytes
        # 4 bytes padding (64-bit alignment)
        ("union", _INPUT_UNION),       # 32 bytes（如果包含 MOUSEINPUT）
    ]
# sizeof(INPUT) = 4 + 4(padding) + 32 = 40 ✓
```

**如果你省略了 `MOUSEINPUT`**（反正我們不用滑鼠）：

```python
class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),       # 24 bytes
        # mi 被省略了！
        ("hi", HARDWAREINPUT),    # 8 bytes
    ]
# sizeof(_INPUT_UNION) = 24
# sizeof(INPUT) = 4 + 4 + 24 = 32 ← 錯！Windows 期望 40！
```

`SendInput` 的第三個參數是 `sizeof(INPUT)`。如果傳 32 而不是 40，**它會靜靜地回傳 0**——不報錯、不拋異常、什麼都不做。

```python
# SendInput 的簽名
# UINT SendInput(UINT nInputs, LPINPUT pInputs, int cbSize);
#                                                ^^^^^^
#                                                必須是 40！
result = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
# result == 0 表示失敗，但 GetLastError 可能也是 0 → 無從 debug
```

**教訓**：ctypes Union 的大小取決於最大成員。即使你不需要 MOUSEINPUT，也必須包含它，否則 `sizeof` 會小於 Windows 期望的值。

#### 練習 4.2：結構體大小

以下 ctypes 定義中，`sizeof(MyUnion)` 是多少？

```python
class A(ctypes.Structure):
    _fields_ = [("x", ctypes.c_uint32)]  # 4 bytes

class B(ctypes.Structure):
    _fields_ = [("x", ctypes.c_uint64), ("y", ctypes.c_uint64)]  # 16 bytes

class C(ctypes.Structure):
    _fields_ = [("x", ctypes.c_uint8)]  # 1 byte

class MyUnion(ctypes.Union):
    _fields_ = [("a", A), ("b", B), ("c", C)]
```

<details><summary>答案</summary>

**16 bytes**。Union 的大小 = 最大成員 B（16 bytes）。即使你只用 A 或 C，Union 仍佔 16 bytes。

</details>

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| `SendInput` 的批次保證——同批次的按鍵不會被插隊。 | 掃描碼是遊戲能正確識別的唯一按鍵表示法。 | `sizeof(INPUT)` 必須是 40——這是 C/Python 互操作的精確性要求。 |

**延伸學習**：
- [ctypes 官方文件](https://docs.python.org/3/library/ctypes.html) — "Structures and unions" 章節
- [SendInput MSDN](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)

---

## Reading 5: PyQt6 GUI 框架

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | Signal/Slot 提供執行緒安全的跨執行緒通訊——GUI 更新不阻塞 MIDI 處理。 | QPainter 自繪琴鍵確保視覺準確度——每個鍵的位置對應精確的 MIDI 音符。 | 元件化設計：每個 Widget 獨立，可單獨測試和替換。 |

閱讀本篇後，你將能夠：

- 解釋 QApplication → QMainWindow → QWidget 的物件層次
- 使用 Signal/Slot 機制進行跨元件和跨執行緒通訊
- 用 QPainter 在 `paintEvent` 中自繪圖形
- 解釋為什麼 Qt 類別不能在 QApplication 之前建立

### 目錄

- [5.1 Qt 物件模型](#51-qt-物件模型)
- [5.2 Signal / Slot](#52-signal--slot)
- [5.3 QPainter：程式碼畫圖](#53-qpainter程式碼畫圖)
- [5.4 Lazy Import 模式](#54-lazy-import-模式)
- [5.5 本專案的 Widget 架構](#55-本專案的-widget-架構)
- [總結](#總結-reading-5)

### 5.1 Qt 物件模型

```
QApplication（整個 App 的根——必須最先建立）
└── QMainWindow (AppShell, 487 行)
    ├── Sidebar（左側導航, 155 行）
    ├── QStackedWidget（頁面堆疊——一次只顯示一頁）
    │   ├── LiveModeView（演奏模式, 476 行）
    │   ├── LibraryView（曲庫, 329 行）
    │   └── EditorView（Piano Roll 編輯器）
│       ├── EditorTrackPanel（軌道面板）
│       ├── PitchRuler（音高尺）
│       └── NoteRoll（piano roll）
    └── NowPlayingBar（底部播放列, 247 行）
```

**定義**：**QWidget** 是所有 UI 元件的基底類別。每個 Widget 有自己的 `paintEvent`（繪圖）、`mousePressEvent`（滑鼠事件）等虛擬方法。

### 5.2 Signal / Slot

**定義**：**Signal** 是一個「事件發生了」的通知；**Slot** 是「收到通知後要做的事」。Signal 可以跨執行緒——Qt 會自動把 Slot 呼叫排入目標執行緒的事件佇列。

```python
class MidiProcessor(QObject):
    # 定義信號：(事件類型, 音符, 力道)
    note_event = pyqtSignal(str, int, int)

    def on_midi_callback(self, event_type, note, velocity):
        """在 rtmidi 執行緒上被呼叫。"""
        # ① 按鍵模擬——直接在這個執行緒做（低延遲！）
        self._simulator.press(note, mapping)

        # ② GUI 更新——透過 Signal 傳到主執行緒
        self.note_event.emit(event_type, note, velocity)

# 在主執行緒連接
processor.note_event.connect(piano_display.note_on)
# → Qt 自動把 piano_display.note_on 排入主執行緒的事件佇列
```

**關鍵洞見**：`emit()` 在 rtmidi 執行緒上呼叫，但 `note_on()` 在主執行緒上執行。Qt 透過 **Queued Connection** 自動跨執行緒。不需要手動加鎖。

#### 練習 5.1：Signal/Slot

下列程式碼中，`on_note` 在哪個執行緒上執行？

```python
# 在主執行緒建立
class Display(QWidget):
    def on_note(self, note: int):
        self.update()  # 觸發重繪

# processor 的 note_signal 從 rtmidi 執行緒 emit
processor.note_signal.connect(display.on_note)
```

- (A) rtmidi 執行緒（因為 emit 在那裡）
- (B) 主執行緒（因為 display 住在主執行緒）
- (C) 新建的第三個執行緒
- (D) 不確定，取決於 Qt 的排程

<details><summary>答案</summary>

**(B)**。Qt 的預設連接方式是 `AutoConnection`——當 Signal 和 Slot 在不同執行緒時，自動使用 `QueuedConnection`，把 Slot 呼叫排入 Slot 所屬物件的執行緒（這裡是主執行緒）。

</details>

### 5.3 QPainter：程式碼畫圖

本專案的鋼琴鍵盤、圖示、piano roll 全部用程式碼繪製——不用任何圖片檔。

```python
def paintEvent(self, event):
    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 畫一個圓角矩形
    path = QPainterPath()
    path.addRoundedRect(QRectF(x, y, width, height), radius, radius)
    painter.fillPath(path, QColor("#00F0FF"))  # 填入賽博青色

    # 畫文字
    painter.setFont(QFont("Microsoft JhengHei", 10))
    painter.setPen(QColor("#E8E0D0"))  # 宣紙白
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "C4")

    painter.end()
```

**好處**：
- 任意縮放不失真（向量圖形）
- 不需要載入外部圖片（零資源依賴）
- 狀態變化可以即時反映（按下 → 青色光暈）

### 5.4 Lazy Import 模式

**陷阱**：如果在 `QApplication()` 建立之前就 import 一個含有 `QObject` 子類別的模組，程式會爆炸。

```python
# ✗ 錯誤：模組頂層定義 QObject 子類別
from PyQt6.QtCore import QObject

class MyWorker(QObject):  # ← 如果此模組在 QApplication 之前被 import，崩潰
    ...

# ✓ 正確：Lazy 定義
_WorkerClass = None

def get_worker_class():
    global _WorkerClass
    if _WorkerClass is None:
        from PyQt6.QtCore import QObject
        class _Worker(QObject):
            ...
        _WorkerClass = _Worker
    return _WorkerClass
```

本專案的 `midi_file_player.py` 使用這個模式——它的核心邏輯（`MidiFileEvent`、`MidiFileInfo`）是純 Python dataclass，但播放控制器需要 Qt 信號，所以用 factory 函式延遲定義。

### 5.5 本專案的 Widget 架構

| Widget | 職責 | 自繪？ |
|--------|------|--------|
| `PianoDisplay` | 鋼琴鍵盤動畫（flash + fade） | Yes |
| `ClickablePiano` | 可點擊的鋼琴（編輯器用） | Yes |
| `NoteRoll` | Beat-based piano roll（多選/框選/resize） | Yes |
| `PitchRuler` | 音高尺（C3..B5 音名標示） | Yes |
| `EditorTrackPanel` | 軌道面板（mute/solo/重命名/排序） | Partial |
| `Sidebar` | 左側導航（Live/Library/Editor） | Partial |
| `NowPlayingBar` | 底部播放列（進度、速度、迷你鋼琴） | Partial |
| `AnimatedWidgets` | TransportButton / IconButton / NavButton | Yes |

**賽博墨韻**色彩系統（`theme.py`, 290 行）：

```
墨黑底 #0A0E14  ██  ← 最深背景
卷軸面 #101820  ██  ← 次深
宣紙暗 #1A2332  ██  ← 卡片背景
賽博青 #00F0FF  ██  ← 主強調色
金墨   #D4A853  ██  ← 次強調色
宣紙白 #E8E0D0  ██  ← 文字
```

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| Signal/Slot 的 `QueuedConnection` 讓 GUI 更新非同步，不阻塞 MIDI 處理路徑。 | QPainter 自繪確保每個琴鍵精確對應一個 MIDI 音符。 | Lazy import 避免模組載入順序的陷阱；Widget 組件化設計支援獨立開發。 |

**延伸學習**：
- [Qt for Python Tutorials](https://doc.qt.io/qtforpython-6/tutorials/) — 從 "Your First Application" 開始
- [QPainter 文件](https://doc.qt.io/qt-6/qpainter.html)

---

## Reading 6: 翻譯管線：從琴鍵到遊戲按鍵

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | 修飾鍵「閃按」技術確保 Shift/Ctrl 不會洩漏到下一個音符。 | 36 鍵完整映射——每個半音都有唯一的掃描碼 + 修飾鍵組合。 | KeyMapper 的 `_map` 字典參照替換是 GIL 原子操作，執行緒安全。 |

閱讀本篇後，你將能夠：

- 追蹤一個 MIDI note_on 事件從進入到最終 SendInput 的完整路徑
- 解釋修飾鍵「閃按」（flash press）技術及其必要性
- 描述 KeySimulator 的 stuck key 看門狗機制
- 說明方案切換時如何保證執行緒安全

### 目錄

- [6.1 翻譯表結構](#61-翻譯表結構)
- [6.2 修飾鍵閃按](#62-修飾鍵閃按)
- [6.3 KeySimulator 生命週期](#63-keysimulator-生命週期)
- [6.4 看門狗：Stuck Key 保護](#64-看門狗stuck-key-保護)
- [6.5 方案切換的執行緒安全](#65-方案切換的執行緒安全)
- [總結](#總結-5)

### 6.1 翻譯表結構

遊戲的 36 鍵模式把鍵盤分成三層（低音/中音/高音），每層 12 個音：

```
高音 C5-B5:  Q  W  E  R  T  Y  U     ← 自然音
            ⇧Q    ^E ⇧R    ⇧T ^U     ← 升降號
中音 C4-B4:  A  S  D  F  G  H  J
            ⇧A    ^D ⇧F    ⇧G ^J
低音 C3-B3:  Z  X  C  V  B  N  M
            ⇧Z    ^C ⇧V    ⇧B ^M
```

（⇧ = Shift, ^ = Ctrl）

`key_mapper.py` 將這個表編碼為 `dict[int, KeyMapping]`：

```python
_BASE_MAP = {
    48: KeyMapping(SCAN["Z"],  Modifier.NONE,  "Z"),        # C3
    49: KeyMapping(SCAN["Z"],  Modifier.SHIFT, "Shift+Z"),  # C#3
    50: KeyMapping(SCAN["X"],  Modifier.NONE,  "X"),        # D3
    51: KeyMapping(SCAN["X"],  Modifier.SHIFT, "Shift+X"),  # D#3（不存在，遊戲用 ^C）
    # ... 共 36 條
}
```

### 6.2 修飾鍵閃按

按 `Shift+Z`（C#3）時，不能像人那樣「按住 Shift 再按 Z」——如果 Shift 按太久，下一個快速音符可能在 Shift 還沒放開時到達，導致錯音。

**解法：閃按（Flash Press）**——修飾鍵只在按鍵的瞬間存在：

```
SendInput 批次: [Shift↓, Z↓, Shift↑]  ← 三個動作一次送出
                         ...
             後來:  [Z↑]                ← 放開 Z 時不管 Shift
```

```python
def press(self, midi_note: int, mapping: KeyMapping) -> None:
    events = []
    if mapping.modifier == Modifier.SHIFT:
        events.append(_make_key_event(SCAN["LSHIFT"], press=True))
    events.append(_make_key_event(mapping.scan_code, press=True))
    if mapping.modifier != Modifier.NONE:
        events.append(_make_key_event(modifier_scan, press=False))  # 立刻放開修飾鍵！

    _send_inputs(events)  # SendInput 保證這批不被插隊
```

**定義**：`SendInput` 的**原子批次保證**——傳入 N 個 INPUT，這 N 個事件會連續注入，不會被其他程式的 `SendInput` 呼叫插隊。

#### 練習 6.1：閃按時序

快速連彈 C#3（Shift+Z）→ D3（X），兩個 note_on 間隔 5ms。如果不用閃按，而是用「按住 Shift 直到 note_off」的策略，會發生什麼？

<details><summary>答案</summary>

D3 的 X 鍵可能在 Shift 還沒放開時被按下，遊戲會收到 `Shift+X`（D#3）而不是 `X`（D3）——錯音！閃按確保 Shift 在 Z 按下後立即放開（同一個 SendInput 批次），所以 5ms 後的 X 一定不會受到 Shift 影響。

</details>

### 6.3 KeySimulator 生命週期

`KeySimulator` 追蹤所有「按住中」的音符：

```python
class KeySimulator:
    def __init__(self):
        self._active: dict[int, tuple[KeyMapping, float]] = {}
        # midi_note → (mapping, press_timestamp)

    def press(self, midi_note, mapping):
        if midi_note in self._active:
            self.release(midi_note)     # 先放開舊的
        self._active[midi_note] = (mapping, time.monotonic())
        _send_inputs([...])             # 送出按鍵

    def release(self, midi_note):
        if midi_note not in self._active:
            return
        mapping, _ = self._active.pop(midi_note)
        _send_inputs([_make_key_event(mapping.scan_code, press=False)])
```

### 6.4 看門狗：Stuck Key 保護

如果 MIDI 裝置斷線或軟體 bug 導致 `note_off` 遺失，按鍵會永遠卡住。看門狗每隔一段時間檢查：

```python
def check_stuck_keys(self) -> int:
    """釋放超過 10 秒的按鍵。回傳釋放數量。"""
    now = time.monotonic()
    stuck = [n for n, (_, t) in self._active.items() if now - t > 10.0]
    for note in stuck:
        self.release(note)
    return len(stuck)
```

### 6.5 方案切換的執行緒安全

切換映射方案時，KeyMapper 直接替換整個字典參照：

```python
def set_scheme(self, scheme_id: str) -> None:
    new_map = _build_map_for_scheme(scheme_id)
    self._map = new_map  # ← 原子操作！
```

**為什麼這是安全的？** CPython 的 GIL（全域直譯器鎖）保證：任一 Python 位元碼指令是原子的。`self._map = new_map` 是一條 `STORE_ATTR` 指令——它要嘛完成、要嘛沒發生，不會出現半完成的狀態。

rtmidi 執行緒的 `lookup()` 要嘛看到舊的字典、要嘛看到新的字典，不會看到中間態。

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| 閃按讓修飾鍵僅存在於 SendInput 批次的瞬間，不干擾後續音符。 | 36 鍵完整映射確保每個半音都有唯一按鍵，不會碰撞。 | GIL 原子性替換字典讓方案切換不需要加鎖。 |

---

## Reading 7: 執行緒與延遲

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | `SetThreadPriority(TIME_CRITICAL)` + `timeBeginPeriod(1)` 確保 MIDI 處理不被搶佔。 | 播放執行緒的計時精度從 15.6ms 降到 1ms，避免可聽的節奏抖動。 | 清晰的執行緒職責分工——每個執行緒只做一件事。 |

閱讀本篇後，你將能夠：

- 描述程式中三個執行緒的職責和通訊方式
- 解釋 GIL 對本專案的實際影響
- 說明 `timeBeginPeriod(1)` 為什麼能改善計時精度
- 分析為什麼 `list.append()` 在 CPython 下不需要加鎖

### 目錄

- [7.1 三個執行緒](#71-三個執行緒)
- [7.2 GIL：Python 的全域鎖](#72-gilpython-的全域鎖)
- [7.3 Windows 計時器精度](#73-windows-計時器精度)
- [7.4 為什麼不用 QThread？](#74-為什麼不用-qthread)
- [總結](#總結-6)

### 7.1 三個執行緒

```
主執行緒（Qt Event Loop）
├── 畫面更新、按鈕點擊、動畫
├── 接收 Signal，執行 Slot
│
rtmidi 執行緒（由 python-rtmidi C++ 層建立）
├── MIDI callback → 查翻譯表 → SendInput（全部同步）
├── 發 Qt Signal（非同步，排入主執行緒佇列）
│
播放執行緒（threading.Thread，播放 .mid 時建立）
├── 按時間播放音符 → SendInput
├── time.sleep() + 校正漂移
```

**設計原則**：按鍵模擬在**產生事件的執行緒**上直接完成——不跨執行緒。

### 7.2 GIL：Python 的全域鎖

**定義**：**GIL**（Global Interpreter Lock）是 CPython 的一個互斥鎖，同一時間只有一個執行緒能執行 Python 位元碼。

GIL 對我們的**有利影響**：
- `list.append()` 是 GIL 原子操作 → 錄音引擎不需要加鎖
- `dict` 參照替換是原子操作 → 方案切換不需要加鎖

GIL **不影響**我們的效能：
- `SendInput` 是 C 函式呼叫 → 呼叫期間會釋放 GIL
- `time.sleep` 會釋放 GIL → 不會阻塞其他執行緒
- rtmidi callback 在 C++ 層觸發 → 不等 GIL

#### 練習 7.1：GIL 與原子性

`MidiRecorder` 的 `record_event` 方法在 rtmidi 執行緒上被呼叫，它只做一件事：`self._events.append(event)`。為什麼不需要 `threading.Lock`？

<details><summary>答案</summary>

`list.append()` 在 CPython 中是單一位元碼指令（`LIST_APPEND`），GIL 保證它是原子的——不會在 append 的中間被中斷。所以即使主執行緒同時讀取 `self._events`，也不會看到損壞的狀態。注意：這是 CPython 的實現細節，不是 Python 語言規範的保證。

</details>

### 7.3 Windows 計時器精度

Windows 預設的排程粒度是 **15.625ms**（64 Hz）。這意味著 `time.sleep(0.001)` 實際上可能休眠 15ms。

```python
# priority.py
ctypes.windll.winmm.timeBeginPeriod(1)  # 請求 1ms 粒度
# 現在 time.sleep(0.001) 真的只休眠 ~1ms
```

播放引擎需要精確的音符間隔。如果一個十六分音符（120 BPM 下 = 125ms）有 ±15ms 的抖動，人耳聽得出來。`timeBeginPeriod(1)` 把抖動降到 ±1ms，低於感知閾值。

### 7.4 為什麼不用 QThread？

早期版本用 `QThread` + `moveToThread()` 做播放，但踩了坑：

```python
# ✗ 錯誤：直接呼叫 worker 的方法
worker.play()  # 這在呼叫者的執行緒上執行！不是 worker 的執行緒！
```

`moveToThread` 只影響透過 Signal/Slot 觸發的方法呼叫。直接呼叫方法仍然在呼叫者的執行緒上執行。播放迴圈的 `while + sleep` 凍結了 GUI。

**解法**：用標準的 `threading.Thread`，透過 `threading.Event` 控制暫停/停止：

```python
class PlaybackThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()

    def run(self):
        for event in self._events:
            if self._stop_event.is_set():
                break
            time.sleep(event.delay)
            send_key(event)

    def stop(self):
        self._stop_event.set()
```

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| TIME_CRITICAL 優先權 + 1ms 計時器確保 MIDI 處理不被搶佔。 | 計時精度從 ±15ms 降到 ±1ms，消除可聽的節奏抖動。 | 每個執行緒職責明確，GIL 原子性消除了大部分鎖的需求。 |

---

## Reading 8: MIDI 檔案播放

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | 播放迴圈用「錨點 + 差值」策略校正累積漂移，避免長曲子越播越不準。 | 多 tempo 的 MIDI 檔（中間變速）透過 tempo map 正確換算每個事件的絕對時間。 | `MidiFileEvent` dataclass 將所有事件統一為 `(time_seconds, type, note, velocity)`。 |

閱讀本篇後，你將能夠：

- 解釋 MIDI 檔案的 multi-track 合併流程
- 建構 tempo map 並將 tick 轉為秒
- 分析播放迴圈的漂移校正策略
- 描述 4 拍倒數的實現

### 8.1 MIDI 檔案解析

`midi_file_player.py`（520 行）分兩步處理 .mid 檔案：

**Step 1：掃描所有軌道的 tempo 變更事件，建構 tempo map**

```python
def _build_tempo_map(mid: mido.MidiFile) -> list[tuple[int, int]]:
    """回傳 [(abs_tick, tempo_microseconds), ...]"""
    tempo_map = [(0, 500000)]  # 預設 120 BPM
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == "set_tempo":
                tempo_map.append((abs_tick, msg.tempo))
    tempo_map.sort()
    return tempo_map
```

**Step 2：用 tempo map 將每個事件的 absolute tick 轉為秒**

```python
def _tick_to_sec(abs_tick: int, tempo_map, tpb: int) -> float:
    seconds = 0.0
    prev_tick = 0
    prev_tempo = 500000
    for map_tick, map_tempo in tempo_map:
        if map_tick >= abs_tick:
            break
        seconds += mido.tick2second(map_tick - prev_tick, tpb, prev_tempo)
        prev_tick = map_tick
        prev_tempo = map_tempo
    seconds += mido.tick2second(abs_tick - prev_tick, tpb, prev_tempo)
    return seconds
```

### 8.2 播放迴圈

播放不是簡單的 `sleep(delta)` 連發——那樣會因為 `sleep` 的不精確性導致累積漂移：

```python
anchor_time = time.perf_counter()
anchor_pos = 0.0

for event in events:
    target_time = anchor_time + (event.time_seconds - anchor_pos)
    now = time.perf_counter()
    if target_time > now:
        time.sleep(target_time - now)
    # 模擬按鍵
    send_key(event)
```

**錨點策略**：記住「開始時間」和「開始位置」，每個事件根據**絕對差值**計算應該睡多久，而不是根據相鄰事件的 delta。這樣 `sleep` 的誤差不會累積。

#### 練習 8.1：漂移校正

假設每次 `time.sleep` 平均多睡 0.5ms。播放一首 300 個音符的曲子，使用 delta sleep vs 錨點策略，各自的總漂移是多少？

<details><summary>答案</summary>

**Delta sleep**：0.5ms × 300 = 150ms 累積漂移（超過一個十六分音符的長度）。**錨點策略**：每個音符的最大漂移 = 0.5ms（不累積）。這就是為什麼長曲子必須用錨點策略。

</details>

### 8.3 倒數機制

播放前有 4 拍倒數（發射 `countdown_tick` 信號），讓演奏者準備：

```python
for i in range(4, 0, -1):
    self.countdown_tick.emit(i)  # 4, 3, 2, 1
    time.sleep(60.0 / self._tempo_bpm)
```

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| 錨點策略消除 sleep 的累積漂移。 | Tempo map 正確處理 MIDI 檔案中的速度變化。 | 統一的 MidiFileEvent dataclass 讓播放和預處理使用相同的資料格式。 |

---

## Reading 9: MIDI 預處理管線

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | 60 FPS 時間量化（Stage 9）確保按鍵時間對齊到遊戲的畫面更新週期。 | 智慧移調（Stage 4）最大化落在可演奏範圍內的音符數，保持調性。 | 9 個階段獨立實作、獨立測試，每個階段回報統計數字。 |

閱讀本篇後，你將能夠：

- 列舉 9 個預處理階段及其順序
- 解釋八度摺疊演算法的設計取捨
- 分析複音限制的策略（保留低音 + 高音）
- 說明每個階段回報的統計數字的意義

### 9 階段管線

```
原始 MIDI 事件
  │
  ├─ Stage 1: 打擊過濾      → 移除 GM channel 10（鼓組）
  ├─ Stage 2: 音軌篩選      → 只保留使用者選擇的軌道
  ├─ Stage 3: 八度去重      → 同時間同 pitch class → 保留最高音
  ├─ Stage 4: 智慧移調      → 找最佳 ±12/±24 shift，最大化 in-range 音符
  ├─ Stage 5: 八度摺疊      → while note > max: note -= 12; while note < min: note += 12
  ├─ Stage 6: 碰撞去重      → 同 (time, note) → 保留最高 velocity
  ├─ Stage 7: 複音限制      → 同時 N 個音 → 保留最低 + 最高 + 前 (N-2) 個
  ├─ Stage 8: 力度正規化    → 所有 velocity → 127
  └─ Stage 9: 時間量化      → 對齊到 60 FPS（~16.67ms）
  │
  ▼
適配到 36 鍵的事件
```

#### 練習 9.1：管線順序

為什麼「智慧移調」（Stage 4）要在「八度摺疊」（Stage 5）之前？

<details><summary>答案</summary>

智慧移調用整體偏移（±12 的倍數）把盡可能多的音符移到 48-83 範圍內。如果先做八度摺疊，所有音符已經被強制壓到範圍內，移調就沒有資訊可以做「選擇最佳偏移」的決策。

</details>

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| 60 FPS 量化確保按鍵與遊戲畫面同步。 | 智慧移調 + 八度摺疊最大化音樂性，保留旋律方向。 | 每個 Stage 是獨立函式，有獨立測試（共 ~80 個）。 |

---

## Reading 10: Beat-Based 資料模型

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | 秒只在播放的那一刻才計算——編輯時零換算開銷。 | 改 BPM 不會破壞音符的拍子位置——四分音符永遠是 1.0 拍。 | 100 步 undo/redo，deep copy snapshot，任何操作都可復原。 |

閱讀本篇後，你將能夠：

- 解釋為什麼用「拍」而不是「秒」作為主要時間單位
- 描述 `BeatNote`、`BeatRest`、`Track` 的資料結構
- 實作拍↔秒的雙向轉換
- 分析 undo/redo snapshot 策略的時間和空間複雜度

### 10.1 為什麼用拍？

假設你在寫一首 120 BPM 的曲子。一個四分音符 = 0.5 秒。

如果你用**秒**存位置，改 BPM 到 60 後，那個四分音符的「位置」還是 0.5 秒——但它應該在 1.0 秒的位置。整首曲子的節奏結構壞了。

用**拍**：四分音符 = 1.0 拍，永遠不變。秒只在播放那一刻算：

```python
time_seconds = time_beats * (60.0 / tempo_bpm)
# 120 BPM: 1.0 拍 × (60/120) = 0.5 秒
# 60 BPM:  1.0 拍 × (60/60)  = 1.0 秒
```

### 10.2 資料結構

```python
@dataclass
class BeatNote:
    time_beats: float       # 在第幾拍開始
    duration_beats: float   # 持續幾拍
    note: int               # MIDI 0-127
    velocity: int = 100     # 力道
    track: int = 0          # 軌道索引

@dataclass
class BeatRest:
    time_beats: float
    duration_beats: float
    track: int = 0

@dataclass
class Track:
    name: str = ""
    color: str = "#00F0FF"
    channel: int = 0
    muted: bool = False
    solo: bool = False
```

**時值預設**（映射到鍵盤快捷鍵 1-5）：

| 按鍵 | 名稱 | 拍數 |
|------|------|------|
| `1` | 全音符 (1/1) | 4.0 |
| `2` | 二分音符 (1/2) | 2.0 |
| `3` | 四分音符 (1/4) | 1.0 |
| `4` | 八分音符 (1/8) | 0.5 |
| `5` | 十六分音符 (1/16) | 0.25 |

### 10.3 拍號

**定義**：**拍號**（time signature）`N/D` 表示每小節 N 個 D 分音符。

```python
beats_per_bar = numerator * (4.0 / denominator)
```

| 拍號 | beats_per_bar | 用途 |
|------|-------------|------|
| 4/4 | 4.0 | 最常見 |
| 3/4 | 3.0 | 華爾滋 |
| 6/8 | 3.0 | 複合拍子 |

#### 練習 10.1：beat-to-second

一首曲子 BPM = 90，拍號 3/4。第二小節第一拍上的音符，其 `time_beats` 是多少？秒數是多少？

<details><summary>答案</summary>

`time_beats = 3.0`（第一小節有 3 拍，第二小節從 3.0 拍開始）。`time_seconds = 3.0 × (60/90) = 2.0 秒`。

</details>

### 10.4 Undo/Redo

每次編輯前，`EditorSequence` 對整個狀態拍一張**深拷貝快照**：

```python
def _push_undo(self):
    snapshot = {
        "notes": [copy.deepcopy(n) for n in self._notes],
        "rests": [copy.deepcopy(r) for r in self._rests],
        "cursor": self._cursor_beats,
        "active_track": self._active_track,
    }
    self._undo_stack.append(snapshot)
    if len(self._undo_stack) > 100:
        self._undo_stack.pop(0)     # 超過 100 步丟掉最舊的
    self._redo_stack.clear()        # 新編輯清空 redo
```

**空間複雜度**：O(N × S)，其中 N = 快照數（最多 100），S = 音符數。對於典型曲子（幾百個音符），這完全可以接受。

### 10.5 快照包含 Tracks（v0.6.0）

早期版本的 `_Snapshot` 只保存 notes、rests、cursor、active_track。但 `remove_track` / `reorder_tracks` 這類軌道操作會修改 `_tracks` 列表——undo 時沒有恢復 tracks，導致軌道被刪除後無法還原。

v0.6.0 修正了這個 bug，`_Snapshot` 現在包含完整的 tracks 資料：

```python
@dataclass
class _Snapshot:
    notes: list[BeatNote]
    rests: list[BeatRest]
    cursor_beats: float
    active_track: int
    tracks: list[Track] | None = None   # ← v0.6.0 新增
```

### 10.6 批次操作（v0.6.0）

v0.6.0 新增多項批次操作，每個都是單一 undo 步驟：

```python
# 批次調整大小：所有選取的音符同時改變持續時間
seq.resize_notes([0, 2, 5], delta_beats=0.5)

# 批次刪除：同時刪除音符和休止符
seq.delete_items(note_indices=[0, 1], rest_indices=[2])

# 複製選取：取得 notes + rests 的 deep copy
copied_notes, copied_rests = seq.copy_items(note_indices=[0], rest_indices=[])

# 軌道重排序：index remapping 確保音符歸屬正確
seq.reorder_tracks([2, 0, 1, 3])  # 把 Track 2 搬到最前面
```

**`reorder_tracks` 的 index remapping**：

重排序不只是搬動 Track 物件——所有音符和休止符的 `track` 欄位都必須跟著更新：

```python
def reorder_tracks(self, new_order: list[int]) -> None:
    old_to_new = {old: new for new, old in enumerate(new_order)}
    self._tracks = [self._tracks[i] for i in new_order]
    for n in self._notes:
        n.track = old_to_new.get(n.track, n.track)
    # rests 和 active_track 也做同樣的映射
```

#### 練習 10.2：index remapping

執行 `reorder_tracks([2, 0, 1])` 前，一個音符的 `track = 1`。執行後它的 `track` 是多少？

<details><summary>答案</summary>

**2**。`old_to_new` = `{2: 0, 0: 1, 1: 2}`，所以原本的 track 1 → 新的 track 2。

</details>

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| 編輯時零秒數換算開銷——全部操作在 beat 空間進行。 | BPM 改變不影響拍子位置。拍號轉換公式 `N × (4/D)` 正確。 | 100 步 undo/redo 用 deep copy snapshot（含 tracks），實作簡單可靠。 |

---

## Reading 11: Piano Roll UI

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | `repaint()` 同步重繪確保新增音符立即可見，不等 Qt 排程。 | Y 軸精確映射 MIDI 音域——每個音高佔一列，間距等分。 | 座標轉換集中在四個 helper 函式中，不散落在繪圖程式碼裡。 |

閱讀本篇後，你將能夠：

- 解釋 NoteRoll 的座標系統（beat → pixel, MIDI → Y）
- 實作以滑鼠位置為中心的 zoom
- 分析拖曳音符的狀態機（idle → drag_detect → dragging）
- 描述 ghost note 和 rest 的視覺表現

### 11.1 座標轉換

四個核心 helper（`note_roll.py`）：

```python
def _beat_to_x(self, beat: float) -> float:
    return beat * self._zoom - self._scroll_x

def _x_to_beat(self, x: float) -> float:
    return (x + self._scroll_x) / self._zoom

def _y_for_note(self, midi_note: int) -> float:
    offset = self._midi_max - midi_note
    return _HEADER_HEIGHT + offset * note_height

def _note_height(self) -> float:
    return max(4.0, (self.height() - _HEADER_HEIGHT) / range_size * 0.85)
```

### 11.2 Zoom

Ctrl+滾輪以滑鼠位置為中心縮放：

```python
def wheelEvent(self, event):
    if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
        mouse_beat = self._x_to_beat(event.position().x())
        factor = 1.15 if event.angleDelta().y() > 0 else 1/1.15
        self._zoom = clamp(self._zoom * factor, 20.0, 400.0)
        # 調整 scroll 使 mouse_beat 保持在滑鼠下方
        self._scroll_x = max(0, mouse_beat * self._zoom - event.position().x())
```

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| `repaint()` 同步繪製，新音符零延遲可見。 | 座標轉換確保每個 MIDI 音高精確對應 Y 位置。 | 四個 helper 函式集中管理所有座標轉換。 |

---

## Reading 12: 編輯器進階：多選、框選、軌道管理

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | 框選演算法用 rect intersection 一次性計算，不逐音符遍歷多次。 | 批次拖曳保持所有選取音符的相對位置不變——不會因為四捨五入而跑拍。 | 選取狀態集中管理在 `_selected_note_indices` / `_selected_rest_indices`，mutation 後自動清除。 |

閱讀本篇後，你將能夠：

- 實作 marquee selection（框選）的矩形相交演算法
- 描述多選狀態的資料結構和清除策略
- 解釋音符 resize（右邊緣拖曳）的偵測邏輯
- 描述 PitchRuler 和 EditorTrackPanel 的設計

### 12.1 多選架構

v0.6.0 的 NoteRoll 用兩個 `set[int]` 追蹤選取：

```python
self._selected_note_indices: set[int] = set()
self._selected_rest_indices: set[int] = set()
```

**選取模式**：

| 操作 | 行為 |
|------|------|
| 左鍵點擊音符 | 清除舊選取，選取該音符 |
| Ctrl+click | 切換（toggle）該音符的選取狀態 |
| Shift+拖曳 | 框選（marquee selection） |
| Ctrl+A | 全選所有活躍軌道的音符和休止符 |

**清除策略**：在 `_update_ui_state()` 中，任何資料 mutation（新增/刪除/移動音符）之後自動清除選取。這避免了選取 index 與資料不同步的問題。

### 12.2 Marquee Selection（框選）

Shift+拖曳時，NoteRoll 繪製一個虛線青色矩形。放開滑鼠時，計算矩形範圍內的所有音符和休止符：

```python
def _apply_marquee_selection(self):
    sel_rect = QRectF(
        QPointF(min(self._marquee_start, self._marquee_end)),
        QPointF(max(self._marquee_start, self._marquee_end)),
    ).normalized()

    for i, note in enumerate(self._visible_notes):
        note_rect = QRectF(
            self._beat_to_x(note.time_beats),
            self._y_for_note(note.note),
            note.duration_beats * self._zoom,
            self._note_height(),
        )
        if sel_rect.intersects(note_rect):
            self._selected_note_indices.add(i)
```

**定義**：**rect intersection** 是 O(1) 的幾何運算——只需比較兩個矩形的左/右/上/下邊界。整個框選是 O(N)，N = 可見音符數。

#### 練習 12.1：框選

框選矩形的像素範圍是 x=100..300, y=50..150。一個音符的像素矩形是 x=250..280, y=120..135。這個音符會被選取嗎？

<details><summary>答案</summary>

**會**。矩形 [100,300]×[50,150] 和 [250,280]×[120,135] 有交集（x 交集 [250,280]，y 交集 [120,135]）。`QRectF.intersects()` 會回傳 `True`。

</details>

### 12.3 音符 Resize

滑鼠移到音符右邊緣 6px 以內時，游標變為 `SizeHorCursor`（↔），開始拖曳即可調整持續時間。

```python
def _is_on_right_edge(self, pos, note) -> bool:
    """右邊緣 6px 以內？"""
    right_x = self._beat_to_x(note.time_beats + note.duration_beats)
    return abs(pos.x() - right_x) < 6

# mouseMoveEvent 中：
if self._is_on_right_edge(pos, hovered_note):
    self.setCursor(Qt.CursorShape.SizeHorCursor)
elif hovered_note:
    self.setCursor(Qt.CursorShape.OpenHandCursor)
else:
    self.setCursor(Qt.CursorShape.ArrowCursor)
```

Resize 時的 snap-to-grid 確保持續時間對齊到拍線：

```python
def _snap_beat(self, beat: float) -> float:
    if not self._snap_enabled:
        return beat
    grid = self._snap_resolution  # 例如 0.25（十六分音符）
    return round(beat / grid) * grid
```

### 12.4 音符標籤

放大後（音符寬度 > 30px），NoteRoll 在音符內部繪製音名文字：

```python
note_w = note.duration_beats * self._zoom
if note_w > 30:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = note.note // 12 - 1
    label = f"{names[note.note % 12]}{octave}"
    painter.drawText(note_rect, Qt.AlignmentFlag.AlignCenter, label)
```

### 12.5 PitchRuler

`PitchRuler` 是 48px 寬的固定寬度 widget，顯示 C3..B5 的音名，與 NoteRoll 的 Y 軸完美對齊。黑鍵音名用暗底色區分：

```python
_BLACK_SEMITONES = {1, 3, 6, 8, 10}  # C#, D#, F#, G#, A#

for i in range(range_size):
    midi_note = self._midi_max - i
    semitone = midi_note % 12
    is_black = semitone in _BLACK_SEMITONES
    # 黑鍵 → 暗底背景 + 灰色文字
    # 白鍵 → 正常背景 + 白色文字
```

**設計關鍵**：PitchRuler 和 NoteRoll 共享 `_HEADER_HEIGHT = 22`，放在同一個 `QHBoxLayout` 中確保高度自動同步。

### 12.6 EditorTrackPanel

`EditorTrackPanel` 是 160px 寬的軌道管理面板，包含：

- **_TrackItem** 行：色點 + 名稱 + M（mute）/ S（solo）指示
- 點擊 → 切換活躍軌道
- 雙擊 → `QInputDialog` 重命名
- 右鍵 → 刪除軌道
- 底部「+ 新增音軌」按鈕

7 個 Qt Signal：`track_activated`、`track_muted`、`track_soloed`、`track_renamed`、`track_removed`、`track_added`、`tracks_reordered`。

```python
class EditorTrackPanel(QWidget):
    track_activated = pyqtSignal(int)
    track_muted = pyqtSignal(int, bool)
    track_soloed = pyqtSignal(int, bool)
    track_renamed = pyqtSignal(int, str)
    track_removed = pyqtSignal(int)
    track_added = pyqtSignal()
    tracks_reordered = pyqtSignal(list)
```

### 12.7 EditorView 佈局

v0.6.0 的 EditorView 佈局使用巢狀的 QHBoxLayout 和 QVBoxLayout：

```
┌──────────────────────────────────────────────┐
│                   Toolbar                     │
├───────────┬─────────┬────────────────────────┤
│           │         │                        │
│ TrackPanel│ Pitch   │     NoteRoll           │
│ (160px)   │ Ruler   │     (flex = 1)         │
│           │ (48px)  │                        │
│           │         │                        │
├───────────┼─────────┼────────────────────────┤
│           │ spacer  │   ClickablePiano       │
│           │ (48px)  │                        │
└───────────┴─────────┴────────────────────────┘
```

**完整鍵盤快捷鍵**（全部透過 `keyPressEvent` 處理）：

| 類別 | 快捷鍵 |
|------|--------|
| 時值 | `1`-`5` 全音符到十六分音符，`0` 休止符 |
| 編輯 | `Ctrl+Z/Y` undo/redo，`Ctrl+A` 全選 |
| 剪貼簿 | `Ctrl+C/X/V` 複製/剪下/貼上，`Ctrl+D` 複製選取 |
| 儲存 | `Ctrl+S` 儲存，`Ctrl+Shift+S` 另存，`Ctrl+E` 匯出 |
| 移動 | `←→` 時間移動，`↑↓` 音高移動 |
| 調整大小 | `Shift+←→` 批次 resize |
| 刪除 | `Delete` 刪除選取 |
| 播放 | `Space` 播放/暫停 |

#### 練習 12.2：Widget 通訊

使用者在 TrackPanel 中按下 mute 按鈕。從按鈕到資料更新，完整的信號鏈是什麼？

<details><summary>答案</summary>

`_TrackItem.mousePressEvent()` → `EditorTrackPanel.track_muted.emit(index, True)` → `EditorView._on_track_muted(index, True)` → `EditorSequence.set_track_muted(index, True)` → `EditorView._update_ui_state()` → `EditorTrackPanel.set_tracks()` + `NoteRoll.update()`。

</details>

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| 框選用 O(N) rect intersection，不做逐像素碰撞。 | Snap-to-grid 確保 resize 結果精確對齊拍線。 | 7 個 Signal 清晰定義 TrackPanel↔EditorView 的通訊介面。 |

---

## Reading 13: 專案檔案與序列化

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | gzip 壓縮讓 autosave 只佔原始 JSON 的 ~30% 大小，寫入時間 < 10ms。 | `to_project_dict()` / `from_project_dict()` 完整序列化所有欄位——不丟失任何音符屬性。 | 分離 `project_file.py`（I/O）和 `EditorSequence`（資料模型），遵循單一職責原則。 |

閱讀本篇後，你將能夠：

- 解釋 .cqp 檔案格式（JSON + gzip）
- 描述 `to_project_dict()` / `from_project_dict()` 的序列化策略
- 實作 autosave 機制（QTimer + 固定路徑）
- 說明為什麼用 gzip 而不是直接寫 JSON

### 13.1 .cqp 格式

賽博琴仙的專案檔案使用 `.cqp` 副檔名（Cyber Qin Project），格式是 **gzipped JSON**：

```python
def save(path: str | Path, seq: EditorSequence) -> None:
    data = seq.to_project_dict()
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with gzip.open(path, "wb") as f:
        f.write(raw)
```

**為什麼 JSON + gzip？**

| 替代方案 | 優點 | 缺點 |
|----------|------|------|
| 純 JSON | 人類可讀 | 檔案大（重複欄位名佔空間） |
| pickle | Python 原生 | 安全風險（反序列化可執行任意程式碼） |
| SQLite | 結構化查詢 | 過度複雜，不需要 |
| **JSON + gzip** | **人類可讀（解壓後）+ 小檔案** | 需要額外的壓縮步驟 |

`separators=(",", ":")` 去除 JSON 中的空白，進一步減小大小。

### 13.2 序列化策略

`EditorSequence.to_project_dict()` 回傳完整的 Python dict：

```python
{
    "tempo_bpm": 120,
    "time_signature": [4, 4],
    "cursor_beats": 8.0,
    "active_track": 0,
    "tracks": [
        {"name": "旋律", "color": "#00F0FF", "channel": 0, "muted": false, "solo": false},
        {"name": "和弦", "color": "#FF6B6B", "channel": 1, "muted": false, "solo": false}
    ],
    "notes": [
        {"time_beats": 0.0, "duration_beats": 1.0, "note": 60, "velocity": 100, "track": 0},
        {"time_beats": 1.0, "duration_beats": 0.5, "note": 64, "velocity": 100, "track": 0}
    ],
    "rests": [
        {"time_beats": 4.0, "duration_beats": 1.0, "track": 0}
    ]
}
```

`from_project_dict(data)` 反序列化——逐欄位重建 `BeatNote`、`BeatRest`、`Track` 物件。

### 13.3 Autosave

EditorView 用 `QTimer` 每 60 秒自動儲存：

```python
self._autosave_timer = QTimer()
self._autosave_timer.setInterval(60_000)  # 60 秒
self._autosave_timer.timeout.connect(self._on_autosave)
self._autosave_timer.start()

def _on_autosave(self):
    project_file.autosave(self._sequence)
```

Autosave 路徑固定為 `~/.cyber_qin/autosave.cqp`。`project_file.autosave()` 內部會自動建立目錄：

```python
_AUTOSAVE_DIR = Path.home() / ".cyber_qin"

def autosave(seq: EditorSequence) -> None:
    save(_AUTOSAVE_FILE, seq)
    # save() 內部：path.parent.mkdir(parents=True, exist_ok=True)
```

#### 練習 13.1：序列化完整性

下列哪些欄位在 `to_project_dict()` → `from_project_dict()` 的 roundtrip 中**會遺失**？

- (A) `BeatNote.velocity`
- (B) `EditorSequence._undo_stack`
- (C) `Track.color`
- (D) `BeatRest.track`

<details><summary>答案</summary>

**(B)**。undo/redo 堆疊是暫態（transient state），不序列化。儲存/載入後 undo 堆疊為空。(A)(C)(D) 都完整保存。

</details>

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| gzip 壓縮 + 無空白 JSON 讓存檔快速且小巧。 | 所有音符屬性完整 roundtrip，不丟資料。 | `project_file.py` 只做 I/O，不碰資料模型邏輯。 |

**延伸學習**：
- [json 模組文件](https://docs.python.org/3/library/json.html)
- [gzip 模組文件](https://docs.python.org/3/library/gzip.html)

---

## Reading 14: 測試與品質保證

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | Mock 掉 `SendInput`，在沒有硬體的環境下驗證按鍵邏輯。 | 參數化測試覆蓋所有 36 個音符的映射正確性。 | 450 個測試提供回歸保護——改任何程式碼後立刻知道有沒有壞。 |

閱讀本篇後，你將能夠：

- 使用 `pytest` 編寫和執行測試
- 使用 `unittest.mock.patch` 替換硬體依賴
- 解釋測試金字塔和本專案的測試分佈
- 分析為什麼每個預處理 Stage 需要獨立測試

### 14.1 基本 pytest

```python
def test_lookup_middle_c():
    mapper = KeyMapper()
    result = mapper.lookup(60)          # 中央 C
    assert result is not None
    assert result.scan_code == 0x1E     # A 鍵
    assert result.modifier == Modifier.NONE
    assert result.label == "A"
```

### 14.2 Mock

```python
from unittest.mock import patch, MagicMock

def test_press_sends_input():
    with patch("cyber_qin.core.key_simulator._send") as mock_send:
        sim = KeySimulator()
        mapping = KeyMapping(0x1E, Modifier.NONE, "A")
        sim.press(60, mapping)
        assert mock_send.call_count == 1
```

`mock` 攔截真正的 `SendInput` 呼叫，讓測試可以在沒有 Windows GUI 的 CI 環境中執行。

### 14.3 測試分佈

| 檔案 | 主題 | 約幾個 |
|------|------|--------|
| `test_key_mapper.py` | 36 鍵映射 | ~30 |
| `test_key_simulator.py` | SendInput 模擬 | ~25 |
| `test_midi_file_player.py` | .mid 播放 | ~30 |
| `test_midi_preprocessor.py` | 9 階段預處理 | ~80 |
| `test_mapping_schemes.py` | 5 種方案 | ~25 |
| `test_auto_tune.py` | 量化 + 校正 | ~25 |
| `test_midi_recorder.py` | 錄音 + 匯出 | ~20 |
| `test_note_sequence.py` | 秒制序列 | ~20 |
| `test_beat_sequence.py` | Beat 模型 | ~103 |
| `test_project_file.py` | 專案檔案 | ~7 |

CI 矩陣：`windows-latest` × Python {3.11, 3.12, 3.13}，加上 `ubuntu-latest` 的 lint。

#### 練習 14.1：Mock 設計

為什麼我們 mock `_send`（底層函式）而不是 mock `ctypes.windll.user32.SendInput`？

<details><summary>答案</summary>

`_send` 是我們自己定義的 wrapper，mock 它更穩定——不依賴 ctypes 的內部路徑。而且 `_send` 的參數已經是我們的 `INPUT` 列表，更容易斷言。

</details>

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| Mock 讓延遲相關的程式碼可以在 CI 中驗證，不需要真實硬體。 | 參數化測試覆蓋所有 36 鍵 + 所有邊界值。 | 450 個測試 = 強大的回歸保護。~0.3 秒跑完 = 零摩擦。 |

---

## Reading 15: 打包與發佈

### 目標

> | 低延遲 | 音樂正確 | 可維護 |
> |--------|---------|--------|
> | `uac_admin=True` 確保打包後的 .exe 自動請求管理員權限，SendInput 才能注入到遊戲。 | 所有依賴（mido、rtmidi、PyQt6）打包進同一個資料夾，不依賴使用者環境。 | Git tag push → CI 自動建置 + 發佈，零手動操作。 |

閱讀本篇後，你將能夠：

- 解釋 PyInstaller 的 onedir vs onefile 模式
- 說明為什麼需要 `launcher.py` 作為入口點
- 描述 CI/CD 流程從 git tag 到 GitHub Release

### 15.1 PyInstaller

PyInstaller 把 Python 程式碼 + 依賴 + 直譯器打包成可獨立執行的資料夾：

```bash
.venv313/Scripts/pyinstaller cyber_qin.spec --clean -y
# 輸出: dist/賽博琴仙/ (~95 MB)
```

**注意**：必須用 Python 3.13 的 venv——PyQt6 在 3.14 alpha 上會爆 "Unable to embed qt.conf"。

### 15.2 CI/CD 流程

```
開發者                    GitHub Actions
  │                          │
  ├─ git tag v0.7.1         │
  ├─ git push origin v0.7.1 │
  │                          ├─ 觸發 ci.yml
  │                          ├─ pip install + pytest（3 個 Python 版本）
  │                          ├─ ruff check
  │                          ├─ PyInstaller 建置
  │                          ├─ 壓縮成 .zip
  │                          └─ 建立 GitHub Release + 上傳 .zip
```

### 總結

| 低延遲 | 音樂正確 | 可維護 |
|--------|---------|--------|
| 管理員權限確保 SendInput 不被遊戲的 UIPI 屏障攔截。 | 打包所有依賴確保使用者環境的一致性。 | 自動化 CI/CD 消除人工發佈的錯誤風險。 |

---

## 附錄 A：常見陷阱速查表

| # | 陷阱 | 原因 | 修復 |
|---|------|------|------|
| 1 | `SendInput` 靜靜回傳 0 | `sizeof(INPUT)` 不是 40 | Union 必須包含 `MOUSEINPUT` |
| 2 | MIDI 播放時間全亂 | `msg.time` 是 tick 不是秒 | 用 `mido.tick2second()` 轉換 |
| 3 | Import PyQt6 崩潰 | QApplication 還沒建立 | 用 lazy import 模式 |
| 4 | GUI 凍結 | 播放迴圈在主執行緒 | 用 `threading.Thread` |
| 5 | PyInstaller 3.14 爆炸 | PyQt6 不支援 3.14 alpha | 用 Python 3.13 的 venv |
| 6 | 改 BPM 後音符位移 | 用秒儲存位置 | 用拍（beat）作為主要時間單位 |
| 7 | 遊戲不認按鍵 | 用了虛擬鍵碼 | 用掃描碼 + `KEYEVENTF_SCANCODE` |
| 8 | 修飾鍵洩漏到下一音 | Shift/Ctrl 按太久 | 閃按：同批次 down-key-up |
| 9 | `remove_track` 後 undo 不還原軌道 | `_Snapshot` 沒存 tracks | Snapshot 必須包含 tracks 列表 |
| 10 | 選取 index 與資料不同步 | 資料 mutation 後沒清選取 | 每次 mutation 後清除 `_selected_*` |

## 附錄 B：技術學習路線圖

```
階段 1（1-2 週）：Python 基礎
├── Python Tutorial Ch.1-5
├── 能看懂 key_mapper.py
└── 驗證：解釋 _BASE_MAP 字典

階段 2（1 週）：核心原理
├── 讀 constants.py → key_mapper.py → key_simulator.py
├── 理解掃描碼 vs 虛擬鍵碼
└── 驗證：解釋閃按技術

階段 3（1 週）：MIDI
├── mido 文件：Ports + MIDI Files
├── 讀 midi_listener.py → midi_file_player.py
└── 驗證：能跟蹤預處理管線

階段 4（1-2 週）：GUI
├── Qt for Python: "Your First Application"
├── 讀 theme.py → piano_display.py → app_shell.py
└── 驗證：能讀懂 NoteRoll.paintEvent

階段 5（1 週）：編輯器進階
├── 讀 beat_sequence.py → project_file.py
├── 讀 note_roll.py → pitch_ruler.py → editor_track_panel.py
├── 理解多選/框選/resize 的狀態機
└── 驗證：能追蹤 Ctrl+C → Ctrl+V 的完整信號鏈

階段 6（持續）：進階
├── 多執行緒（threading / GIL）
├── 測試（pytest + mock）
├── 序列化設計（JSON + gzip）
└── CI/CD（GitHub Actions）
```

## 附錄 C：推薦資源

| 主題 | 資源 | 難度 |
|------|------|------|
| Python 入門 | [Python Tutorial](https://docs.python.org/3/tutorial/) | 初 |
| Python 進階 | [Fluent Python 2/e](https://www.oreilly.com/library/view/fluent-python-2nd/9781492056348/) | 中 |
| PyQt6 | [Qt for Python](https://doc.qt.io/qtforpython-6/tutorials/) | 初-中 |
| MIDI 理論 | [MIDI.org](https://www.midi.org/specifications) | 初 |
| mido | [mido docs](https://mido.readthedocs.io/) | 初 |
| ctypes | [ctypes docs](https://docs.python.org/3/library/ctypes.html) | 中 |
| pytest | [pytest Getting Started](https://docs.pytest.org/en/stable/getting-started.html) | 初 |
| Git | [Pro Git 中文](https://git-scm.com/book/zh-tw/v2) | 初 |
| GitHub Actions | [Actions docs](https://docs.github.com/en/actions) | 中 |
| MIT 6.031 | [Software Construction](https://web.mit.edu/6.031/) | 中-高 |

## 附錄 D：詞彙表

| 術語 | 定義 |
|------|------|
| **MIDI** | Musical Instrument Digital Interface — 音樂設備間的數位通訊協議 |
| **掃描碼** (scan code) | 鍵盤硬體層的按鍵編號，DirectInput 遊戲用這個識別按鍵 |
| **DirectInput** | Windows 的遊戲輸入 API，只認掃描碼 |
| **callback** | 回呼函式——先登記，事件發生時自動被呼叫 |
| **執行緒** (thread) | 程式中的獨立執行流，可以並行 |
| **Signal/Slot** | Qt 的跨元件/跨執行緒事件通訊機制 |
| **GIL** | Global Interpreter Lock — CPython 的全域鎖，同時只有一個執行緒跑 Python |
| **mock** | 測試用的假物件，模擬真實元件的行為 |
| **QSS** | Qt Style Sheet — 類似 CSS，用來定義 Qt 元件外觀 |
| **UAC** | User Account Control — Windows 的權限提升確認機制 |
| **dataclass** | Python 裝飾器，自動生成 `__init__`、`__eq__`、`__repr__` |
| **frozen** | dataclass 的不可變模式——建立後不能修改屬性 |
| **transpose** | 移調——把所有音符整體往上/下移 N 個半音 |
| **quantize** | 量化——把不精準的時間點對齊到格線 |
| **beat** | 拍——音樂的基本時間單位，1 拍 = 1 個四分音符 |
| **BPM** | Beats Per Minute — 每分鐘幾拍，決定速度 |
| **拍號** (time signature) | 如 4/4：每小節 4 個四分音符 |
| **tick** | MIDI 檔案的時間單位，需搭配 ticks_per_beat 和 tempo 轉換為秒 |
| **tempo** | MIDI 的速度表示，單位是微秒/拍（500000 = 120 BPM） |
| **ghost note** | 非活躍軌道的音符，以半透明顯示提供上下文 |
| **piano roll** | 水平時間軸上的音符視覺化，源自自動演奏鋼琴的紙卷 |
| **CI/CD** | 持續整合/持續部署——提交程式碼後自動測試和發佈 |
| **daemon thread** | 背景執行緒——主程式結束時自動終止 |
| **EMA** | Exponential Moving Average — 指數移動平均，用於平滑追蹤值 |
| **anchor** | 錨點——播放迴圈中記住的起始時間，用來校正累積漂移 |
| **marquee selection** | 框選——按住 Shift 拖曳畫矩形，選取矩形內的所有物件 |
| **resize** | 調整大小——拖曳音符右邊緣改變持續時間 |
| **snap-to-grid** | 吸附格線——移動或調整時自動對齊到最近的拍子分割點 |
| **autosave** | 自動儲存——定時將編輯狀態寫入固定路徑，防止意外丟失 |
| **snapshot** | 快照——undo 系統中對完整狀態的 deep copy，用於還原 |
| **.cqp** | Cyber Qin Project 檔案格式——gzipped JSON |
| **index remapping** | 索引重映射——軌道重排序時更新所有音符的 track 欄位 |
| **PitchRuler** | 音高尺——左側顯示 MIDI 音名的固定寬度 Widget |
| **EditorTrackPanel** | 軌道面板——管理多軌 mute/solo/重命名/排序的側邊 Widget |

---

> **本文件參考了 MIT 6.031 Software Construction 的教學格式**（Reading 結構、三大原則、
> 內嵌練習、漸進式講解），但內容完全針對賽博琴仙專案撰寫。
> 共 15 篇 Reading，涵蓋從 Python 基礎到完整 Piano Roll 編輯器的全部技術。
>
> 授權：本文件隨專案以 MIT License 發佈。
