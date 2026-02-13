# 賽博琴仙 (Cyber Qin) - AI Collaboration Guide

**Version**: 0.9.3
**Last Updated**: 2026-02-13

此文件是賽博琴仙專案的 AI 協作憲法。在執行任何任務前，請務必先閱讀此文件。

---

## 目錄

1. [專案概覽](#1-專案概覽)
2. [核心架構](#2-核心架構)
3. [開發環境](#3-開發環境)
4. [開發規範](#4-開發規範)
5. [關鍵技術陷阱](#5-關鍵技術陷阱)
6. [測試策略](#6-測試策略)
7. [打包與部署](#7-打包與部署)
8. [AI 協作協議](#8-ai-協作協議)
9. [Git 工作流](#9-git-工作流)

---

## 1. 專案概覽

### 1.1 專案定位

**賽博琴仙** 是一個專業級的 MIDI-to-Keyboard 實時映射工具，專為遊戲音樂演奏設計。

**核心功能**：
- **即時模式 (Live Mode)**：< 2ms 延遲的 MIDI 轉鍵盤注入
- **樂庫 (Library)**：MIDI 文件管理與自動播放
- **音序器 (Sequencer)**：鋼琴卷簾編輯器，支援多軌導出

**目標遊戲**：
- 燕雲十六聲 (Where Winds Meet) - 36 鍵模式
- 最終幻想 XIV (Final Fantasy XIV) - 37 鍵模式
- 通用模式 - 24 / 48 / 88 鍵方案

### 1.2 技術棧

| 層級 | 技術 | 用途 |
|------|------|------|
| **MIDI I/O** | `mido` + `python-rtmidi` | 設備通訊與 MIDI 解析 |
| **模擬** | `ctypes` + Win32 `SendInput` | DirectInput 掃描碼注入 |
| **GUI** | PyQt6 | 桌面介面、事件循環、跨線程信號 |
| **打包** | PyInstaller | 單資料夾可執行檔打包 |
| **CI/CD** | GitHub Actions | 自動標籤與多平台測試 |
| **品質** | Ruff + pytest | 程式碼檢查與 392 單元/整合測試 |

### 1.3 專案指標

- **程式碼行數**: ~6,500 LOC (含註解)
- **模組數量**: 47 個 Python 模組
- **測試數量**: 392 測試（23 個測試文件）
- **覆蓋率**: > 85%
- **支援版本**: Python 3.11 / 3.12 / 3.13

---

## 2. 核心架構

### 2.1 資料夾結構

```
cyber_qin/
├── core/                    # 核心邏輯層（無 UI 依賴）
│   ├── constants.py         # 全域常數與枚舉
│   ├── key_mapper.py        # MIDI Note → Scan Code 映射引擎
│   ├── key_simulator.py     # Win32 SendInput 注入器
│   ├── midi_listener.py     # 即時 MIDI 監聽器 (rtmidi 回調)
│   ├── midi_file_player.py  # MIDI 文件播放器 (延遲載入 Qt 類)
│   ├── midi_preprocessor.py # MIDI 前處理（轉調、折疊、去重）
│   ├── midi_writer.py       # MIDI Type 1 檔案寫入器
│   ├── midi_recorder.py     # 即時 MIDI 錄製
│   ├── midi_output_player.py# MIDI 輸出播放器
│   ├── musicxml_parser.py   # MusicXML 解析器
│   ├── mapping_schemes.py   # 5 種映射方案定義
│   ├── project_file.py      # .cqp 專案檔序列化
│   ├── config.py            # 設定持久化
│   ├── translator.py        # 多語言翻譯引擎
│   ├── note_sequence.py     # MIDI 音符序列容器
│   ├── beat_sequence.py     # 節拍序列生成器
│   ├── auto_tune.py         # 自動轉調算法
│   └── priority.py          # 按鍵優先級隊列
│
├── gui/                     # GUI 層（PyQt6 依賴）
│   ├── app_shell.py         # 主視窗殼層（分頁管理）
│   ├── theme.py             # Cyber-Ink 主題定義
│   ├── icons.py             # 向量圖標繪製 (QPainter)
│   ├── views/               # 三大視圖
│   │   ├── live_mode_view.py    # 即時模式視圖
│   │   ├── library_view.py      # 樂庫視圖
│   │   └── editor_view.py       # 音序器視圖
│   ├── widgets/             # 可重用組件
│   │   ├── piano_display.py     # 88 鍵鋼琴顯示器
│   │   ├── mini_piano.py        # 迷你鋼琴
│   │   ├── clickable_piano.py   # 可點擊鋼琴
│   │   ├── note_roll.py         # 鋼琴卷簾編輯器
│   │   ├── pitch_ruler.py       # 音高尺標
│   │   ├── editor_track_panel.py# 編輯器軌道面板
│   │   ├── now_playing_bar.py   # 底部播放條
│   │   ├── sidebar.py           # 側邊欄
│   │   ├── track_list.py        # 曲目列表
│   │   ├── speed_control.py     # 速度控制器
│   │   ├── status_bar.py        # 狀態列
│   │   ├── progress_bar.py      # 進度條
│   │   ├── language_selector.py # 語言選擇器
│   │   ├── log_viewer.py        # 日誌查看器
│   │   └── animated_widgets.py  # 動畫組件
│   └── dialogs/             # 對話框
│       └── settings_dialog.py   # 設定對話框
│
├── utils/                   # 工具層
│   ├── admin.py             # UAC 權限檢查
│   └── ime.py               # 輸入法檢測
│
├── __init__.py
├── __main__.py              # python -m cyber_qin 入口點
└── main.py                  # 主程式入口

tests/                       # 測試套件 (392 tests)
├── conftest.py              # pytest 共享 fixtures
├── test_key_mapper.py
├── test_key_simulator.py
├── test_midi_listener.py
├── test_midi_file_player.py
├── test_midi_file_player_qt.py
├── test_midi_preprocessor.py
├── test_midi_writer.py
├── test_midi_recorder.py
├── test_mapping_schemes.py
├── test_ff14_mapping.py
├── test_config.py
├── test_project_file.py
├── test_note_sequence.py
├── test_beat_sequence.py
├── test_beat_sequence_gaps.py
├── test_auto_tune.py
├── test_priority.py
├── test_frontend_components.py
├── test_gui_integration.py
├── test_editor_ux.py
├── test_window_state.py
├── test_coverage_gaps.py
└── test_coverage_gaps.py
```

### 2.2 數據流設計

#### 2.2.1 即時模式 (Live Mode)

```
┌─────────────┐  USB   ┌──────────────┐  callback  ┌───────────┐  lookup  ┌──────────────┐  SendInput  ┌──────┐
│ MIDI Keyboard│───────→│ python-rtmidi│───────────→│ KeyMapper │─────────→│ KeySimulator │────────────→│ Game │
└─────────────┘        └──────────────┘             └───────────┘          └──────────────┘             └──────┘
                       (C++ rtmidi thread)                                  (Scan Code)
```

**關鍵點**：
- `SendInput` **必須**在 rtmidi 回調線程上直接執行（不可通過 Qt 信號槽），否則延遲 > 20ms
- 使用 DirectInput Scan Code（`KEYEVENTF_SCANCODE`），而非虛擬鍵碼（DirectInput 遊戲必需）

#### 2.2.2 播放模式 (Playback Mode)

```
┌───────────┐  parse  ┌─────────────────┐  preprocess  ┌──────────────────┐  timed events  ┌──────────────┐
│ .mid File │────────→│ mido.MidiFile   │─────────────→│ MidiPreprocessor │───────────────→│ PlaybackWorker│
└───────────┘         └─────────────────┘               └──────────────────┘                └──────┬───────┘
                                                                                                   │
                                                                   lookup + SendInput              │
                                                       ┌───────────┬──────────────┐←──────────────┘
                                                       │ KeyMapper │ KeySimulator │→ Game
                                                       └───────────┴──────────────┘
```

**關鍵點**：
- `mido.merge_tracks()` 返回的 `msg.time` 是 **ticks**，不是秒！必須用 `mido.tick2second()` 轉換
- Tempo 變更事件必須實時處理（中途變速）

### 2.3 架構原則

1. **分層隔離**：`core/` 層完全不依賴 PyQt6，便於單元測試
2. **延遲載入**：Qt 相關類定義必須延遲至 `QApplication` 創建後（參考 `midi_file_player.py` 的 lazy class pattern）
3. **線程安全**：
   - rtmidi 回調在 C++ 線程，不可直接操作 Qt 對象
   - 使用 `pyqtSignal` 跨線程通訊
4. **單一真相來源**：所有配置通過 `config.py` 統一管理，避免散落狀態

---

## 3. 開發環境

### 3.1 Python 版本要求

| Python 版本 | 狀態 | 用途 |
|------------|------|------|
| **3.11** | ✅ 推薦 | 日常開發、CI/CD |
| **3.12** | ✅ 支援 | CI 測試 |
| **3.13** | ✅ 支援 | CI 測試 + **打包專用** |
| **3.14 alpha** | ❌ 禁用 | PyQt6 致命崩潰 ("Unable to embed qt.conf") |

**打包規則**：
- 必須使用 Python 3.13 虛擬環境 (`.venv313/`)
- 原因：PyQt6 在 3.14 alpha 導入時會崩潰

### 3.2 虛擬環境設置

```bash
# 開發環境（推薦 3.11）
python3.11 -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]

# 打包環境（必須 3.13）
python3.13 -m venv .venv313
.venv313\Scripts\activate
pip install -e .[dev]
```

### 3.3 依賴管理

**核心依賴** (`pyproject.toml` → `dependencies`):
- `mido>=1.3` - MIDI 文件解析
- `python-rtmidi>=1.5` - 低延遲 MIDI I/O
- `PyQt6>=6.5` - GUI 框架

**開發依賴** (`pyproject.toml` → `optional-dependencies.dev`):
- `pytest>=7.0` + `pytest-cov` + `pytest-qt` - 測試框架
- `ruff>=0.8` - 超快速 linter
- `pyinstaller>=6.0` - 打包工具
- `mypy>=1.6` - 類型檢查（漸進式採用）

### 3.4 IDE 設定建議

**VSCode** (`settings.json`):
```json
{
  "python.defaultInterpreterPath": ".venv/Scripts/python.exe",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": false,
  "python.testing.pytestEnabled": true
}
```

---

## 4. 開發規範

### 4.1 代碼風格

**Linter**: Ruff (配置於 `pyproject.toml`)

```bash
# 檢查
ruff check .

# 自動修復
ruff check --fix .
```

**規則**：
- 目標版本：Python 3.11
- 行寬上限：99 字元
- 啟用規則：`E` (錯誤), `F` (Pyflakes), `W` (警告), `I` (import 排序), `N` (命名), `UP` (升級語法)
- 忽略：`E501` (行寬，由 Ruff formatter 處理)

**例外規則**：
- `cyber_qin/core/key_simulator.py`: 忽略 `N801` (ctypes 內部 union 命名必須大寫)
- `cyber_qin/gui/theme.py`: 忽略 `N806` (Win32 常數命名慣例)

### 4.2 命名規範

| 類型 | 規範 | 範例 |
|------|------|------|
| 模組 | `snake_case` | `key_mapper.py` |
| 類別 | `PascalCase` | `KeyMapper` |
| 函數/方法 | `snake_case` | `map_note_to_key()` |
| 常數 | `UPPER_SNAKE_CASE` | `SCAN_CODE_TABLE` |
| 私有成員 | `_leading_underscore` | `_internal_state` |
| Qt 信號 | `camelCase` (遵循 Qt 慣例) | `notePressed = pyqtSignal(int)` |

### 4.3 類型提示

**策略**：漸進式採用（mypy 配置於 `pyproject.toml`）

```python
# ✅ 推薦：公開 API 必須有類型提示
def map_note(self, note: int, scheme: MappingScheme) -> ScanCode | None:
    ...

# ⚠️ 容忍：內部方法可暫時不標註（未來補齊）
def _internal_helper(self, data):
    ...
```

**忽略缺失型別的第三方庫**：
- `mido.*`, `rtmidi.*`, `PIL.*`, `win32con.*`, `win32api.*`

### 4.4 文件組織

每個模組應包含：

```python
"""模組簡述（單行）。

詳細說明（多段落，可選）。
"""

# 標準庫導入
import sys
from pathlib import Path

# 第三方庫導入
import mido
from PyQt6.QtCore import QObject

# 本地導入
from cyber_qin.core.constants import NOTE_NAMES

# 常數定義
DEFAULT_TIMEOUT = 3.0

# 類別定義
class MyClass:
    ...

# 頂層函數
def my_function():
    ...
```

### 4.5 註解規範

**原則**：代碼應自解釋，註解只用於「為什麼」而非「做什麼」

```python
# ❌ 壞範例：重複代碼語意
count += 1  # Increment count

# ✅ 好範例：解釋設計決策
# Must run on rtmidi callback thread for <2ms latency (Qt signal would add 20ms)
self._send_input(scan_code)
```

**必須註解的場景**：
1. 技術陷阱（如 PyQt6 3.14 崩潰、ctypes 結構體大小問題）
2. 性能優化邏輯
3. 協議/演算法實現（如 MIDI tick 轉換）
4. Workaround（如延遲載入 Qt 類）

---

## 5. 關鍵技術陷阱

### 5.1 PyQt6 + Python 3.14 崩潰

**症狀**：
```python
import PyQt6.QtCore  # Fatal: Unable to embed qt.conf
```

**原因**：PyQt6 與 Python 3.14 alpha 不相容

**解決方案**：
- 開發環境：使用 Python 3.11 / 3.12 / 3.13
- 打包環境：**必須**使用 Python 3.13（在 `.venv313/`）

**檢查點**：
- CI/CD 配置：`strategy.matrix.python-version: ["3.11", "3.12", "3.13"]`（不包含 3.14）

### 5.2 mido.merge_tracks() 時間單位陷阱

**症狀**：播放速度異常（通常過快）

**原因**：
```python
for msg in mido.merge_tracks(mid.tracks):
    print(msg.time)  # ❌ 這是 ticks，不是秒！
```

**正確做法**：
```python
ticks_per_beat = mid.ticks_per_beat
current_tempo = 500000  # 默認 120 BPM

for msg in mido.merge_tracks(mid.tracks):
    delta_seconds = mido.tick2second(msg.time, ticks_per_beat, current_tempo)
    if msg.type == 'set_tempo':
        current_tempo = msg.tempo  # 更新 tempo
```

**參考**：`cyber_qin/core/midi_file_player.py:118`

### 5.3 Qt 類定義時機問題

**症狀**：
```python
# test_foo.py
from cyber_qin.core.my_module import MyQtClass  # ImportError or crash

# my_module.py (模組頂層)
class MyQtClass(QObject):  # ❌ QApplication 尚未創建！
    ...
```

**原因**：Qt 元類要求 `QApplication` 必須先存在

**解決方案**：延遲類定義（Lazy Class Pattern）

```python
# ✅ 正確做法
def get_my_qt_class():
    """Lazy factory to avoid defining QObject subclass before QApplication exists."""
    from PyQt6.QtCore import QObject, pyqtSignal

    class MyQtClass(QObject):
        my_signal = pyqtSignal(int)
        ...

    return MyQtClass

# 使用時
MyQtClass = get_my_qt_class()
instance = MyQtClass()
```

**參考**：`cyber_qin/core/midi_file_player.py:15-50`

### 5.4 ctypes INPUT 結構體大小問題

**症狀**：`SendInput` 返回 0（靜默失敗），鍵盤注入無效

**原因**：ctypes `INPUT` union 未包含 `MOUSEINPUT`（最大成員，32 bytes）

```python
# ❌ 錯誤定義
class INPUT(Structure):
    _fields_ = [
        ("type", DWORD),
        ("ki", KEYBDINPUT),  # 僅 28 bytes
    ]
# sizeof(INPUT) = 32 on 64-bit, but SendInput expects 40!

# ✅ 正確定義
class MOUSEINPUT(Structure):
    _fields_ = [
        ("dx", LONG),
        ("dy", LONG),
        ("mouseData", DWORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", POINTER(ULONG)),
    ]  # 32 bytes

class InputUnion(Union):
    _fields_ = [
        ("mi", MOUSEINPUT),  # ← 必須包含（決定 union 大小）
        ("ki", KEYBDINPUT),
    ]

class INPUT(Structure):
    _fields_ = [
        ("type", DWORD),
        ("union", InputUnion),
    ]
# sizeof(INPUT) = 40 ✓
```

**檢查命令**：
```python
from ctypes import sizeof
from cyber_qin.core.key_simulator import INPUT
assert sizeof(INPUT) == 40, f"Expected 40, got {sizeof(INPUT)}"
```

**參考**：`cyber_qin/core/key_simulator.py:30-70`

### 5.5 DirectInput 遊戲必須用 Scan Code

**症狀**：虛擬鍵碼 (`VK_*`) 在遊戲中無效

**原因**：DirectInput 遊戲繞過 Windows 鍵盤消息佇列，直接讀取硬體掃描碼

**解決方案**：
```python
# ❌ 錯誤（虛擬鍵碼）
kb_input.wVk = 0x5A  # VK_Z
kb_input.dwFlags = 0

# ✅ 正確（掃描碼）
kb_input.wVk = 0
kb_input.wScan = 0x2C  # Z key scan code
kb_input.dwFlags = KEYEVENTF_SCANCODE
```

**參考**：`cyber_qin/core/constants.py:15-85` (SCAN_CODE_TABLE)

### 5.6 SendInput 必須在 rtmidi 線程執行

**症狀**：延遲 > 20ms，遊戲角色反應遲鈍

**原因**：Qt 信號槽跨線程傳遞延遲 ~18-25ms

**解決方案**：
```python
# ❌ 錯誤（通過 Qt 信號）
class MidiListener(QObject):
    note_on = pyqtSignal(int)

    def _callback(self, msg):
        self.note_on.emit(msg.note)  # → 主線程 → 20ms 延遲

# ✅ 正確（直接在回調執行）
class MidiListener:
    def _callback(self, msg):
        if self.key_simulator:
            self.key_simulator.press(msg.note)  # < 2ms
```

**代價**：無法直接操作 Qt 對象（需手動加鎖或使用 signal 通知 UI）

**參考**：`cyber_qin/core/midi_listener.py:45-60`

---

## 6. 測試策略

### 6.1 測試分類

| 類別 | 數量 | 範例文件 | pytest 標記 |
|------|------|----------|-------------|
| **單元測試** | ~250 | `test_key_mapper.py` | (無標記) |
| **整合測試** | ~100 | `test_midi_file_player_qt.py` | `@pytest.mark.integration` |
| **GUI 測試** | ~42 | `test_gui_integration.py` | `@pytest.mark.gui` |

### 6.2 執行測試

```bash
# 全部測試（392 tests）
pytest

# 詳細輸出
pytest -v

# 覆蓋率報告
pytest --cov=cyber_qin --cov-report=html

# 僅單元測試（跳過整合測試）
pytest -m "not integration and not gui"

# 僅 GUI 測試
pytest -m gui

# 單一文件
pytest tests/test_key_mapper.py

# 單一測試函數
pytest tests/test_key_mapper.py::test_note_to_scan_code
```

### 6.3 測試覆蓋率要求

| 模組類型 | 最低覆蓋率 | 目標覆蓋率 |
|---------|-----------|-----------|
| `core/` | 80% | 95% |
| `gui/` | 50% | 70% |
| `utils/` | 90% | 100% |
| **整體** | **75%** | **85%** |

**例外**：
- `__init__.py` 文件：可忽略
- `cyber_qin/main.py`：主程式入口，難以測試（容忍低覆蓋）

### 6.4 測試規範

**命名**：
```python
# 測試文件：test_<module_name>.py
# 測試函數：test_<behavior>_<expected_result>

def test_map_note_returns_correct_scan_code():
    ...

def test_map_note_out_of_range_returns_none():
    ...
```

**結構**：遵循 AAA 模式 (Arrange-Act-Assert)

```python
def test_transpose_shifts_notes_up():
    # Arrange
    processor = MidiPreprocessor(transpose=12)
    input_note = 60  # C4

    # Act
    output_note = processor.process_note(input_note)

    # Assert
    assert output_note == 72  # C5
```

**Fixtures**：共享 fixtures 定義於 `tests/conftest.py`

```python
# conftest.py
@pytest.fixture
def qapp():
    """Provide QApplication instance for Qt tests."""
    app = QApplication.instance() or QApplication([])
    yield app
    app.quit()

# test_foo.py
def test_my_widget(qapp):  # ← pytest 自動注入
    widget = MyWidget()
    assert widget.isVisible()
```

### 6.5 Mock 策略

**原則**：優先使用真實對象，僅在以下情況 mock：

1. **外部依賴**（硬體、網路）
   ```python
   @patch('cyber_qin.core.midi_listener.mido.open_input')
   def test_listen_opens_port(mock_open):
       listener = MidiListener()
       listener.start('Test Port')
       mock_open.assert_called_once_with('Test Port', callback=...)
   ```

2. **非確定性行為**（時間、隨機）
   ```python
   @patch('time.time', return_value=1234567890.0)
   def test_timestamp_recording(mock_time):
       ...
   ```

3. **危險操作**（文件刪除、SendInput）
   ```python
   @patch('cyber_qin.core.key_simulator.windll.user32.SendInput')
   def test_press_key_calls_sendinput(mock_sendinput):
       ...
   ```

**避免過度 mock**：
```python
# ❌ 壞範例：mock 所有依賴，測試變成空殼
@patch('cyber_qin.core.key_mapper.KeyMapper')
@patch('cyber_qin.core.midi_preprocessor.MidiPreprocessor')
def test_player_plays(mock_preprocessor, mock_mapper):
    player = MidiFilePlayer()
    player.play()  # 什麼都沒測試到！

# ✅ 好範例：僅 mock SendInput（危險操作）
@patch('cyber_qin.core.key_simulator.windll.user32.SendInput', return_value=1)
def test_player_sends_correct_keys(mock_sendinput):
    player = MidiFilePlayer()
    player.load('test.mid')
    player.play()
    # 驗證 SendInput 被調用了正確的次數和參數
    assert mock_sendinput.call_count == expected_key_presses
```

---

## 7. 打包與部署

### 7.1 打包流程

**環境準備**（僅首次）：
```bash
python3.13 -m venv .venv313
.venv313\Scripts\activate
pip install -e .[dev]
```

**打包命令**：
```bash
# 激活 Python 3.13 環境
.venv313\Scripts\activate

# 使用 PyInstaller 打包
.venv313\Scripts\pyinstaller cyber_qin.spec --clean -y
```

**輸出**：
```
dist/
└── 賽博琴仙/                  # ~95 MB
    ├── 賽博琴仙.exe           # 主執行檔
    ├── _internal/             # PyQt6、Python 運行時
    └── ...
```

### 7.2 PyInstaller 配置 (`cyber_qin.spec`)

**關鍵配置**：

```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['launcher.py'],  # ← 必須是 launcher.py，不能是 cyber_qin/main.py
    pathex=[],
    binaries=[],
    datas=[
        ('cyber_qin/assets', 'cyber_qin/assets'),  # 資源文件
    ],
    hiddenimports=[
        'mido.backends.rtmidi',  # rtmidi backend 未被自動檢測
    ],
    ...
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='賽博琴仙',
    console=False,          # 無控制台視窗
    uac_admin=True,         # ← 必須！要求管理員權限
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,             # 不使用 UPX 壓縮（避免誤報毒）
    name='賽博琴仙',
)
```

**關鍵點**：
1. **入口點必須是 `launcher.py`**：
   - ❌ 不能用 `cyber_qin/main.py`（相對導入失敗）
   - ✅ `launcher.py` 是薄包裝器，正確設置包路徑

2. **UAC 管理員權限**：
   - `uac_admin=True` 是必須的（SendInput 需要）
   - 否則打包後執行會靜默失敗

3. **隱藏導入**：
   - `mido.backends.rtmidi` 需要手動聲明
   - PyInstaller 無法自動檢測動態導入的模組

### 7.3 launcher.py 設計

```python
"""PyInstaller 打包入口點。

不能直接用 cyber_qin/main.py，因為：
1. 相對導入需要父包上下文
2. PyInstaller 打包後包結構變化
"""
import sys
from pathlib import Path

# 確保包路徑正確
if getattr(sys, 'frozen', False):
    # 打包環境
    bundle_dir = Path(sys._MEIPASS)
else:
    # 開發環境
    bundle_dir = Path(__file__).parent

sys.path.insert(0, str(bundle_dir))

# 導入真正的主程式
from cyber_qin.main import main

if __name__ == '__main__':
    main()
```

### 7.4 版本發布流程

1. **更新版本號**：
   ```bash
   # pyproject.toml
   version = "0.9.3"  # 修改這裡
   ```

2. **打包測試**：
   ```bash
   .venv313\Scripts\pyinstaller cyber_qin.spec --clean -y
   dist\賽博琴仙\賽博琴仙.exe  # 手動測試
   ```

3. **提交標籤**：
   ```bash
   git add pyproject.toml
   git commit -m "chore(release): bump version to v0.9.3"
   git tag v0.9.3
   git push origin main --tags
   ```

4. **GitHub Actions 自動構建**：
   - CI 檢測到 tag 推送
   - 自動在 Windows/macOS/Linux 上運行測試
   - 構建可執行檔並附加到 Release

---

## 8. AI 協作協議

### 8.1 核心原則

**你是什麼**：你是專案協作者，不是自動化腳本執行器。

**目標**：透過連結「機率性的 LLM 決策」與「確定性的程式碼執行」，實現高品質的代碼貢獻。

### 8.2 任務處理流程

#### 階段 1：理解需求

- **必做**：先閱讀相關代碼，再提出建議
- **禁止**：憑空猜測代碼結構或行為
- **工具**：`Read`, `Grep`, `Glob`

#### 階段 2：設計方案

- **必做**：說明「為什麼」這麼做，而非只是「做什麼」
- **建議**：提出多種方案並比較優劣（若有明顯 trade-off）
- **檢查**：是否遵守本文件第 5 節的「技術陷阱」

#### 階段 3：實現代碼

- **必做**：
  1. 先用 `Read` 讀取文件
  2. 再用 `Edit` 修改（不可用 `Write` 覆蓋已存在的文件）
  3. 遵守第 4 節的「開發規範」

- **禁止**：
  1. 不讀文件就直接 `Edit`（會失敗）
  2. 猜測代碼內容（必須先讀取）
  3. 用 `Write` 覆蓋已有文件（除非確定是新文件）

#### 階段 4：驗證

- **必做**：運行相關測試
  ```bash
  pytest tests/test_<module>.py -v
  ```
- **建議**：若改動涉及多模組，運行完整測試套件
  ```bash
  pytest
  ```

#### 階段 5：提交

- **僅在用戶明確要求時才提交**
- 提交格式：
  ```bash
  git add <files>
  git commit -m "<type>: <description>

  <optional body>

  Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
  ```

**Commit 類型**：
- `feat`: 新功能
- `fix`: 修復 bug
- `refactor`: 重構（不改變行為）
- `test`: 新增/修改測試
- `docs`: 文檔更新
- `chore`: 雜項（構建、配置等）

### 8.3 互動模式

**輸出格式**：

```
[分析] 理解需求與現有代碼結構
- 讀取了 X 個文件
- 發現關鍵類別：Y

[方案] 提出實現方案
- 方案 A：... (優點：..., 缺點：...)
- 方案 B：... (推薦，因為...)

[實現] 正在修改代碼...
- 編輯 cyber_qin/core/key_mapper.py:45
- 新增 tests/test_new_feature.py

[驗證] 運行測試...
- pytest tests/test_key_mapper.py ✓ 通過

[完成] 任務完成
- 修改文件：2 個
- 新增測試：5 個
- 測試狀態：全部通過
```

### 8.4 安全防護

**隱私**：
- 絕不輸出 API Tokens 或憑證
- 不讀取 `.env` 文件並在對話中顯示

**破壞性操作**（需用戶確認）：
- 刪除文件（除 `.tmp/` 外）
- 修改資料庫結構
- 強制推送 (`git push --force`)
- 刪除分支

**依賴性檢查**：
- 若腳本需要第三方庫，先檢查是否已安裝
- 若缺失，提示安裝命令

### 8.5 品質檢查清單

每次代碼修改後，自檢以下項目：

- [ ] 是否先讀取了相關文件？
- [ ] 是否遵守命名規範？
- [ ] 是否添加了必要的類型提示？
- [ ] 是否有單元測試覆蓋？
- [ ] 是否通過 `ruff check .`？
- [ ] 是否通過 `pytest`？
- [ ] 是否避免了第 5 節的「技術陷阱」？
- [ ] 是否過度設計（YAGNI 原則）？

---

## 9. Git 工作流

### 9.1 分支策略

- **main**：穩定分支，每次提交都應通過 CI
- **feature/***：功能分支（若有大型開發）
- **hotfix/***：緊急修復分支

**日常開發**：直接在 `main` 上提交（小型專案，單人維護）

### 9.2 提交規範

**格式**：
```
<type>(<scope>): <subject>

<body>

<footer>
```

**範例**：
```
feat(midi): add support for MusicXML import

- Implemented MusicXML parser using xml.etree
- Added tests for basic note parsing
- Updated library view to show .musicxml files

Closes #42

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Type 類型**：
| Type | 說明 | 範例 |
|------|------|------|
| `feat` | 新功能 | `feat(sequencer): add undo/redo` |
| `fix` | 修復 bug | `fix(player): prevent crash on empty MIDI` |
| `refactor` | 重構 | `refactor(mapper): extract scan code table` |
| `test` | 測試 | `test(preprocessor): add edge case tests` |
| `docs` | 文檔 | `docs(readme): update installation steps` |
| `chore` | 雜項 | `chore(ci): update GitHub Actions to v4` |
| `perf` | 性能優化 | `perf(player): reduce latency to <2ms` |

**Scope**（可選）：
- `core` - 核心邏輯
- `gui` - GUI 相關
- `midi` - MIDI 處理
- `build` - 打包相關
- `ci` - CI/CD

### 9.3 Pull Request 規範

**標題**：同 commit message 格式

**描述模板**：
```markdown
## 概述
簡述此 PR 的目的

## 變更內容
- [ ] 新增功能 X
- [ ] 修復 issue #123
- [ ] 重構模組 Y

## 測試
- [ ] 已通過所有現有測試
- [ ] 新增測試覆蓋新功能
- [ ] 手動測試步驟：...

## 截圖（若適用）
...

## Checklist
- [ ] 代碼通過 `ruff check .`
- [ ] 測試通過 `pytest`
- [ ] 更新了相關文檔
```

### 9.4 標籤規範

**版本標籤**：`v<major>.<minor>.<patch>`

```bash
# 發布 v0.9.3
git tag -a v0.9.3 -m "Release v0.9.3: Add MusicXML support"
git push origin v0.9.3
```

**版本號規則**（語義化版本）：
- **Major**：不兼容的 API 變更
- **Minor**：向下兼容的新功能
- **Patch**：向下兼容的 bug 修復

**當前階段**（0.9.x）：
- 尚未達到 1.0（生產就緒）
- Minor 版本可包含破壞性變更（快速迭代期）

---

## 附錄 A：常用命令速查

### 開發環境
```bash
# 激活虛擬環境（開發）
.venv\Scripts\activate

# 激活虛擬環境（打包）
.venv313\Scripts\activate

# 安裝依賴
pip install -e .[dev]

# 運行程式（開發模式）
python -m cyber_qin
```

### 測試與檢查
```bash
# 全部測試
pytest

# 詳細輸出
pytest -v

# 覆蓋率
pytest --cov=cyber_qin --cov-report=html

# Linting
ruff check .
ruff check --fix .
```

### 打包
```bash
# 構建可執行檔
.venv313\Scripts\pyinstaller cyber_qin.spec --clean -y

# 運行打包後的程式
dist\賽博琴仙\賽博琴仙.exe
```

### Git
```bash
# 提交
git add .
git commit -m "feat: ..."

# 推送
git push origin main

# 創建標籤
git tag v0.9.3
git push origin v0.9.3
```

---

## 附錄 B：常見問題

### Q1: 為什麼打包必須用 Python 3.13？
**A**: PyQt6 在 Python 3.14 alpha 上會崩潰（"Unable to embed qt.conf"）。雖然開發可以用 3.11/3.12，但打包環境必須是 3.13 以確保兼容性。

### Q2: SendInput 返回 0，鍵盤注入失敗？
**A**: 檢查三點：
1. 是否以管理員權限運行？
2. `INPUT` 結構體大小是否為 40 bytes？（執行 `assert sizeof(INPUT) == 40`）
3. 是否使用 Scan Code 而非虛擬鍵碼？

### Q3: MIDI 播放速度異常？
**A**: 檢查是否正確轉換 ticks 為秒：
```python
delta_seconds = mido.tick2second(msg.time, ticks_per_beat, current_tempo)
```

### Q4: 測試時 PyQt6 類導入失敗？
**A**: 使用延遲載入模式（參考 `midi_file_player.py`）：
```python
def get_my_qt_class():
    from PyQt6.QtCore import QObject
    class MyQtClass(QObject):
        ...
    return MyQtClass
```

### Q5: 如何添加新的映射方案？
**A**:
1. 在 `cyber_qin/core/mapping_schemes.py` 添加方案定義
2. 在 `cyber_qin/core/constants.py` 更新枚舉
3. 在 `tests/test_mapping_schemes.py` 添加測試
4. 在 GUI 的下拉菜單中添加選項

---

## 附錄 C：參考資源

### 官方文檔
- [mido Documentation](https://mido.readthedocs.io/)
- [python-rtmidi Documentation](https://spotlightkid.github.io/python-rtmidi/)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [PyInstaller Manual](https://pyinstaller.org/en/stable/)

### 技術文章
- [Windows SendInput API](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)
- [DirectInput Scan Codes](https://learn.microsoft.com/en-us/windows/win32/inputdev/about-keyboard-input#scan-codes)
- [MIDI File Format Specification](https://www.cs.cmu.edu/~music/cmsip/readings/Standard-MIDI-file-format-updated.pdf)

### 社群資源
- [GitHub Issues](https://github.com/EdmondVirelle/cyber-qin/issues)
- [GitHub Discussions](https://github.com/EdmondVirelle/cyber-qin/discussions)

---

**文件版本**：v2.0 (2026-02-13)
**維護者**：Edmond Virelle
**AI 協作者**：Claude Sonnet 4.5

---

**結語**

此文件是活文件 (Living Document)，應隨專案演進持續更新。若發現任何過時或錯誤的內容，請提交 PR 或開 Issue 討論。

遵循本文件的規範，可以確保代碼品質、提升協作效率，並避免常見的技術陷阱。

**Remember**:
- 先讀代碼，再寫代碼
- 測試是信心的來源
- 簡單的解決方案往往是最好的解決方案
- AI 為協作，並非自動化工具

Happy Coding! 🎹✨
