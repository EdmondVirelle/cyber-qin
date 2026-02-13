# 🎉 Cyber Qin v1.0.0 — First Stable Release

**Play a real piano, and your game character plays in sync.**

This is the first stable release of Cyber Qin (賽博琴仙), a real-time MIDI-to-keyboard mapping tool for games like Where Winds Meet (燕雲十六聲) and Final Fantasy XIV. With < 2ms latency, comprehensive MIDI editing capabilities, and a polished user interface, v1.0.0 delivers a complete solution for piano players who want to perform in games.

[繁體中文](#繁體中文) | [简体中文](#简体中文)

---

## ✨ What's New in v1.0.0

### 🎛️ Settings & Configuration
- **Settings Dialog** (`Ctrl+,`): Centralized interface for MIDI device selection and preferences
- **Key Mapping Viewer**: View complete MIDI-to-keyboard mapping table for your selected scheme
- **Enhanced Hot-plug Support**: Automatic device detection every 5 seconds with connection logging

### 🔁 Playback Enhancements
- **Loop Playback Mode**: Toggle loop in both Library and Sequencer (press `L` in Editor)
- **Metronome Count-in**: Optional 4-beat countdown with visual indicator (press `M` in Editor)
- **Gold Active States**: New gold accent color for active buttons

### 🔧 Improvements
- **598 Tests**: 3.3x increase in test coverage from v0.9.0
- **30 Modules**: Well-organized codebase with ~6,500 LOC
- **Multi-language Docs**: Release notes in English, Traditional Chinese, and Simplified Chinese

---

## 📥 Installation

### Option 1: From Source (Recommended)
```bash
git clone https://github.com/EdmondVirelle/cyber-qin.git
cd cyber-qin
pip install -e .[dev]
cyber-qin  # Run as Administrator
```

### Option 2: Download Source Code
Download the source code from the Assets section below, extract, and follow the installation instructions in [README.md](https://github.com/EdmondVirelle/cyber-qin/blob/main/README.md).

---

## 🎮 Supported Games

- **Where Winds Meet** (燕雲十六聲) — 36 keys
- **Final Fantasy XIV** — 37 keys
- **Generic Games** — 24 / 48 / 88 key schemes

---

## 🚀 Quick Start

1. **Connect Your MIDI Keyboard** (tested with Roland FP-30X, works with any USB MIDI device)
2. **Open Settings** (`Ctrl+,`) and select your preferred MIDI device
3. **View Key Mapping** to see the complete key layout
4. **Choose Your Scheme** (WWM / FF14 / Generic)
5. **Switch to Game** and start playing!

For MIDI playback and editing, go to **Library** or **Sequencer** tabs.

---

## 📖 Documentation

- [English README](https://github.com/EdmondVirelle/cyber-qin/blob/main/README.md)
- [繁體中文 README](https://github.com/EdmondVirelle/cyber-qin/blob/main/README_TW.md)
- [Changelog](https://github.com/EdmondVirelle/cyber-qin/blob/main/CHANGELOG.md)

---

## 📝 System Requirements

- **OS**: Windows 10 / 11 (x64)
- **Python**: 3.11 / 3.12 / 3.13
- **MIDI Device**: Any USB MIDI keyboard
- **Privileges**: Must run as **Administrator** for SendInput to work in games

---

## 🐛 Known Issues

- **Windows Defender**: May flag as unrecognized app (click "More info" → "Run anyway")
- **Input Method Editors**: Some IME software may interfere with key injection
- **High DPI Displays**: UI scaling may not be perfect on 4K monitors (workaround: set Windows scaling to 150%)

See [Issues](https://github.com/EdmondVirelle/cyber-qin/issues) for full tracker.

---

**Full Changelog**: [v0.9.2...v1.0.0](https://github.com/EdmondVirelle/cyber-qin/compare/v0.9.2...v1.0.0)

---
---

<a name="繁體中文"></a>
# 🎉 賽博琴仙 v1.0.0 — 首個穩定版本

**用真實鋼琴彈奏，遊戲角色同步演奏。**

這是賽博琴仙 (Cyber Qin) 的首個穩定版本，一款專為燕雲十六聲與 Final Fantasy XIV 等遊戲設計的即時 MIDI-鍵盤映射工具。擁有 < 2ms 延遲、完整的 MIDI 編輯功能與精緻的使用者介面，v1.0.0 為想在遊戲中演奏鋼琴的玩家提供完整解決方案。

[English](#-cyber-qin-v100--first-stable-release) | [简体中文](#简体中文)

---

## ✨ v1.0.0 新功能

### 🎛️ 設定與配置
- **設定對話框** (`Ctrl+,`)：集中管理 MIDI 裝置選擇與偏好設定
- **鍵位映射查看器**：檢視當前方案的完整 MIDI-鍵盤映射表
- **增強熱插拔支援**：每 5 秒自動偵測裝置，記錄連線變更

### 🔁 播放增強
- **循環播放模式**：在曲庫與編曲器中切換循環（編輯器按 `L`）
- **節拍器倒數**：可選 4 拍倒數，附視覺化指示器（編輯器按 `M`）
- **金色啟用狀態**：啟用按鈕採用新的金色強調色

### 🔧 改進
- **598 個測試**：較 v0.9.0 測試覆蓋率增加 3.3 倍
- **30 個模組**：組織良好的程式碼庫，約 6,500 行程式碼
- **多語言文件**：英文、繁體中文、簡體中文發布說明

---

## 📥 安裝方式

### 方式一：從原始碼安裝（推薦）
```bash
git clone https://github.com/EdmondVirelle/cyber-qin.git
cd cyber-qin
pip install -e .[dev]
cyber-qin  # 以系統管理員身分執行
```

### 方式二：下載原始碼
從下方 Assets 區域下載原始碼，解壓縮後依照 [README_TW.md](https://github.com/EdmondVirelle/cyber-qin/blob/main/README_TW.md) 的安裝說明進行。

---

## 🎮 支援遊戲

- **燕雲十六聲** (Where Winds Meet) — 36 鍵
- **Final Fantasy XIV** — 37 鍵
- **通用遊戲** — 24 / 48 / 88 鍵方案

---

## 🚀 快速開始

1. **連接 MIDI 鍵盤**（已測試 Roland FP-30X，支援任何 USB MIDI 裝置）
2. **開啟設定** (`Ctrl+,`) 並選擇偏好的 MIDI 裝置
3. **查看鍵位映射**，檢視完整按鍵配置
4. **選擇鍵位方案**（燕雲/FF14/通用）
5. **切換到遊戲**，開始彈奏！

MIDI 播放與編輯功能請前往**曲庫**或**編曲器**分頁。

---

## 📖 文件

- [English README](https://github.com/EdmondVirelle/cyber-qin/blob/main/README.md)
- [繁體中文 README](https://github.com/EdmondVirelle/cyber-qin/blob/main/README_TW.md)
- [變更記錄](https://github.com/EdmondVirelle/cyber-qin/blob/main/CHANGELOG.md)

---

## 📝 系統需求

- **作業系統**: Windows 10 / 11 (x64)
- **Python**: 3.11 / 3.12 / 3.13
- **MIDI 裝置**: 任何 USB MIDI 鍵盤
- **權限**: 必須以**系統管理員**身分執行才能在遊戲中使用 SendInput

---

## 🐛 已知問題

- **Windows Defender**：可能將應用程式標記為未識別（點選「更多資訊」→「仍要執行」）
- **輸入法編輯器**：某些輸入法軟體可能干擾按鍵注入
- **高 DPI 顯示器**：UI 縮放在 4K 螢幕上可能不完美（解決方法：將 Windows 縮放設為 150%）

完整問題追蹤請見 [Issues](https://github.com/EdmondVirelle/cyber-qin/issues)。

---

**完整變更記錄**: [v0.9.2...v1.0.0](https://github.com/EdmondVirelle/cyber-qin/compare/v0.9.2...v1.0.0)

---
---

<a name="简体中文"></a>
# 🎉 赛博琴仙 v1.0.0 — 首个稳定版本

**用真实钢琴弹奏，游戏角色同步演奏。**

这是赛博琴仙 (Cyber Qin) 的首个稳定版本，一款专为燕云十六声与 Final Fantasy XIV 等游戏设计的实时 MIDI-键盘映射工具。拥有 < 2ms 延迟、完整的 MIDI 编辑功能与精致的用户界面，v1.0.0 为想在游戏中演奏钢琴的玩家提供完整解决方案。

[English](#-cyber-qin-v100--first-stable-release) | [繁體中文](#繁體中文)

---

## ✨ v1.0.0 新功能

### 🎛️ 设置与配置
- **设置对话框** (`Ctrl+,`)：集中管理 MIDI 设备选择与偏好设置
- **键位映射查看器**：查看当前方案的完整 MIDI-键盘映射表
- **增强热插拔支持**：每 5 秒自动检测设备，记录连接变更

### 🔁 播放增强
- **循环播放模式**：在曲库与编曲器中切换循环（编辑器按 `L`）
- **节拍器倒数**：可选 4 拍倒数，附可视化指示器（编辑器按 `M`）
- **金色启用状态**：启用按钮采用新的金色强调色

### 🔧 改进
- **598 个测试**：较 v0.9.0 测试覆盖率增加 3.3 倍
- **30 个模块**：组织良好的代码库，约 6,500 行代码
- **多语言文档**：英文、繁体中文、简体中文发布说明

---

## 📥 安装方式

### 方式一：从源码安装（推荐）
```bash
git clone https://github.com/EdmondVirelle/cyber-qin.git
cd cyber-qin
pip install -e .[dev]
cyber-qin  # 以系统管理员身份运行
```

### 方式二：下载源码
从下方 Assets 区域下载源码，解压缩后依照 [README.md](https://github.com/EdmondVirelle/cyber-qin/blob/main/README.md) 的安装说明进行。

---

## 🎮 支持游戏

- **燕云十六声** (Where Winds Meet) — 36 键
- **Final Fantasy XIV** — 37 键
- **通用游戏** — 24 / 48 / 88 键方案

---

## 🚀 快速开始

1. **连接 MIDI 键盘**（已测试 Roland FP-30X，支持任何 USB MIDI 设备）
2. **打开设置** (`Ctrl+,`) 并选择偏好的 MIDI 设备
3. **查看键位映射**，查看完整按键配置
4. **选择键位方案**（燕云/FF14/通用）
5. **切换到游戏**，开始弹奏！

MIDI 播放与编辑功能请前往**曲库**或**编曲器**标签页。

---

## 📖 文档

- [English README](https://github.com/EdmondVirelle/cyber-qin/blob/main/README.md)
- [繁体中文 README](https://github.com/EdmondVirelle/cyber-qin/blob/main/README_TW.md)
- [变更记录](https://github.com/EdmondVirelle/cyber-qin/blob/main/CHANGELOG.md)

---

## 📝 系统要求

- **操作系统**: Windows 10 / 11 (x64)
- **Python**: 3.11 / 3.12 / 3.13
- **MIDI 设备**: 任何 USB MIDI 键盘
- **权限**: 必须以**系统管理员**身份运行才能在游戏中使用 SendInput

---

## 🐛 已知问题

- **Windows Defender**：可能将应用程序标记为未识别（点击「更多信息」→「仍要运行」）
- **输入法编辑器**：某些输入法软件可能干扰按键注入
- **高 DPI 显示器**：UI 缩放在 4K 屏幕上可能不完美（解决方法：将 Windows 缩放设为 150%）

完整问题追踪请见 [Issues](https://github.com/EdmondVirelle/cyber-qin/issues)。

---

**完整变更记录**: [v0.9.2...v1.0.0](https://github.com/EdmondVirelle/cyber-qin/compare/v0.9.2...v1.0.0)

