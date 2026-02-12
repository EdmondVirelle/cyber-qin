# Cyber Qin 賽博琴仙

**用真實鋼琴彈奏，遊戲角色同步演奏。**

[![CI](https://github.com/EdmondVirelle/cyber-qin/actions/workflows/ci.yml/badge.svg)](https://github.com/EdmondVirelle/cyber-qin/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![Version](https://img.shields.io/badge/Version-0.9.0-green)
![Tests](https://img.shields.io/badge/Tests-180%20passed-brightgreen)

[English Version](README.md)

---

## 簡介

**Cyber Qin** 是一款即時 MIDI 轉鍵盤的遊戲彈琴工具。它將 USB MIDI 鍵盤的訊號轉換成 DirectInput 掃描碼（延遲 < 2ms），讓你在各種遊戲中用真實鋼琴演奏。

支援的遊戲包括：
- **燕雲十六聲** (Where Winds Meet) — 36 鍵
- **FF14** (Final Fantasy XIV) — 37 鍵
- **其他遊戲** — 通用 24 / 48 / 88 鍵方案

除了即時演奏，還支援 **MIDI 檔案自動彈奏** 以及內建的 **MIDI 編輯器（編曲器）**。

---

## 功能特色

### 即時演奏 (Live Mode)
| 功能 | 說明 |
|------|------|
| **即時 MIDI 映射** | MIDI 訊號直接在 rtmidi C++ 執行緒上觸發 SendInput，延遲 < 2ms |
| **5 組鍵位方案** | 燕雲 36 鍵 / FF14 37 鍵 / 通用 24 / 48 / 88 鍵，可隨時切換 |
| **智慧前處理** | 自動移調 → 八度摺疊 → 碰撞去重 |
| **自動重連** | MIDI 裝置斷線後每 3 秒自動偵測重連 |
| **防卡鍵看門狗** | 偵測超過 10 秒未釋放的按鍵並自動釋放 |

### MIDI 播放 (Library)
| 功能 | 說明 |
|------|------|
| **匯入 .mid 檔案** | 拖曳或匯入 MIDI 檔案到曲庫 |
| **速度控制** | 0.25x ~ 2.0x 播放速度 |
| **進度條拖曳** | 可拖曳進度條跳轉播放位置 |
| **4 拍倒數** | 播放前自動倒數，方便切換到遊戲視窗 |
| **排序與搜尋** | 依名稱/BPM/音符數/時長排序，支援搜尋 |

### MIDI 編輯器 (Sequencer)
| 功能 | 說明 |
|------|------|
| **鋼琴卷軸編輯** | 直覺式鋼琴卷軸，可繪製/選取/刪除音符 |
| **播放游標** | 平滑播放游標 (30ms 更新) + 動態發光回饋 |
| **多軌匯出** | 支援 Type 1 多軌 MIDI 檔案匯出 |
| **快捷鍵操作** | 完整快捷鍵支援（內建操作指南對話框） |

### 介面 / UI
| 功能 | 說明 |
|------|------|
| **賽博墨韻主題** | 暗色主題：霓虹青 (#00F0FF) + 宣紙白暖色調 |
| **向量圖示** | 所有圖示以 QPainter 繪製，任何解析度完美縮放 |
| **動態鋼琴** | 即時按鍵狀態視覺化 + 霓虹發光動畫 |
| **多語言** | 繁中 / 簡中 / 英文 / 日文 / 韓文 介面切換 |
| **Spotify 風格播放列** | 底部播放控制列 + 迷你鋼琴 + 進度條 + 速度控制 |

---

## 使用方法

### 系統需求
- **作業系統**: Windows 10 / 11
- **Python**: 3.11 以上
- **MIDI 裝置**: 任何 USB MIDI 鍵盤（已測試 Roland FP-30X）
- **權限**: 需以 **系統管理員** 身分執行（SendInput 需要提升權限）

### 安裝

```bash
# 1. 複製專案
git clone https://github.com/EdmondVirelle/cyber-qin.git
cd cyber-qin

# 2. 安裝（含開發依賴）
pip install -e .[dev]
```

### 啟動

```bash
# 以系統管理員身分執行
cyber-qin
```

> **提示**: 若未以系統管理員執行，遊戲內的按鍵注入會靜默失敗。

### 使用流程

1. **連接 MIDI 鍵盤** — 啟動後在「演奏模式」選擇 MIDI 裝置
2. **選擇鍵位方案** — 根據遊戲選擇對應方案（燕雲/FF14/通用）
3. **即時演奏** — 切換到遊戲視窗，開始彈奏
4. **匯入 MIDI** — 點選「曲庫」匯入 .mid 檔案，設定速度後播放
5. **編輯 MIDI** — 點選「編曲器」編輯音符，匯出修改後的 MIDI

### 打包獨立執行檔

```bash
python scripts/build.py
# 輸出: dist/CyberQin/ (~95 MB)
```

---

## 鍵位方案

| 方案 | 鍵數 | MIDI 範圍 | 佈局 | 目標遊戲 |
|------|------|-----------|------|----------|
| **燕雲十六聲 36鍵** | 36 | C3 - B5 | 3×12 (ZXC / ASD / QWE + Shift/Ctrl) | 燕雲十六聲 |
| **FF14 37鍵** | 37 | C3 - C6 | 3×12 Diatonic (數字/QWER/ASDF) | Final Fantasy XIV |
| **通用 24鍵** | 24 | C3 - B4 | 2×12 (ZXC / QWE + Shift/Ctrl) | 通用 |
| **通用 48鍵** | 48 | C2 - B5 | 4×12 (數字行 / ZXC / ASD / QWE) | 通用 |
| **通用 88鍵** | 88 | A0 - C8 | 8×11 (多層 Shift/Ctrl 組合) | 通用 (全鋼琴) |

---

## 系統架構

### 資料流

```
                          即時演奏模式
┌─────────────┐    USB    ┌──────────────┐  callback  ┌───────────┐  lookup  ┌──────────────┐  SendInput  ┌──────┐
│ MIDI Keyboard│─────────→│ python-rtmidi │──────────→│ KeyMapper │────────→│ KeySimulator │───────────→│ Game │
└─────────────┘           └──────────────┘            └───────────┘         └──────────────┘            └──────┘
                            (rtmidi thread)                                  (scan codes)


                          自動播放模式
┌───────────┐  parse  ┌─────────────────┐  preprocess  ┌──────────────────┐  timed events  ┌──────────────┐
│ .mid File │────────→│ MidiFileParser  │────────────→│ MidiPreprocessor │──────────────→│ PlaybackWorker│
└───────────┘         └─────────────────┘              └──────────────────┘               └──────┬───────┘
                                                                                                 │
                                                               lookup + SendInput                 │
                                                       ┌───────────┬──────────────┐←────────────┘
                                                       │ KeyMapper │ KeySimulator │→ Game
                                                       └───────────┴──────────────┘
```

---

## 開發

關於程式碼風格、測試及貢獻流程的詳細規範，請參閱 [CONTRIBUTING.md](CONTRIBUTING.md)。


### 測試

```bash
# 執行所有 180 個測試
pytest

# 詳細輸出
pytest -v
```

### Linting

```bash
ruff check .
ruff check --fix .
```

### 專案統計

| 指標 | 數值 |
|------|------|
| 原始碼行數 | ~5,000 LOC |
| 模組 | 26 |
| 測試 | 180 |
| 支援 Python | 3.11 / 3.12 / 3.13 |

---

## 技術棧

| 層級 | 技術 | 用途 |
|------|------|------|
| **MIDI I/O** | `mido` + `python-rtmidi` | MIDI 裝置通訊、.mid 檔案解析 |
| **輸入模擬** | `ctypes` + Win32 `SendInput` | DirectInput 掃描碼注入 |
| **GUI** | PyQt6 | 桌面介面、事件迴圈、跨執行緒信號 |
| **打包** | PyInstaller | 單資料夾執行檔打包 |
| **CI/CD** | GitHub Actions | 多版本測試 + 自動化 tag 發佈 |
| **品質** | Ruff + pytest | Linting + 180 測試 |

---

## 致謝

- [mido](https://github.com/mido/mido) — Python MIDI library
- [python-rtmidi](https://github.com/SpotlightKid/python-rtmidi) — Low-latency cross-platform MIDI I/O
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — Python Qt 6 bindings
- [PyInstaller](https://pyinstaller.org/) — Python application packaging tool
- [Ruff](https://github.com/astral-sh/ruff) — Extremely fast Python linter
- *Where Winds Meet* — 燕雲十六聲 (Everstone Studio / NetEase)
- *Final Fantasy XIV* — FF14 (Square Enix)

---

## 免責聲明

本工具為開源個人專案，供 MIDI 音樂演奏愛好者交流學習使用。
在遊戲中使用第三方工具可能不符合該遊戲之服務條款，請使用者自行評估風險。
開發者不對因使用本工具導致的帳號處分或任何損失承擔責任。

---

**贊助**: [Ko-fi](https://ko-fi.com/virelleedmond)
