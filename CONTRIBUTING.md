# Contributing To Cyber Qin / 貢獻指南

This document provides rigorous guidelines for contributing to Cyber Qin. Adhering to these standards is mandatory for maintaining the project's high performance and reliability.

本文提供了貢獻此專案的嚴格準則。為了維護專案的高效能與可靠性，請務必遵守以下規範。

---

## 1. Technical Standards / 技術規範

### Code Style / 程式碼風格
- **Python Version**: Target Python **3.11+**.
- **Type Hinting**: 
  - Must use `from __future__ import annotations`.
  - All function arguments and return types must be typed.
  - **強制型別提示**：必須使用 `from __future__ import annotations`，且所有參數與回傳值皆需標註型別。
- **Docstrings**: 
  - Use **Google-style** docstrings for all public classes and methods.
  - **文件字串**：所有公開類別與方法必須使用 **Google-style** 格式。
- **Linting**: 
  - Code must pass `ruff check .` with no errors.
  - Line length limit: **99 characters**.
  - **靜態檢查**：代碼必須通過 `ruff` 檢查且無錯誤，行長限制 99 字元。

### Architecture Guidelines / 架構指南

#### I18N (Internationalization) / 國際化
- **No Hardcoded Strings**: All UI text must use `translator.tr("key")`.
- **Key Management**: Add new keys to `cyber_qin/core/translator.py`.
- **Dynamic Update**: UI components must connect to `translator.language_changed` signal to refresh text dynamically.
- **嚴禁硬編碼**：所有 UI 文字必須使用 `translator.tr()`。新增 Key 請至 `translator.py`，並確保組件監聽 `language_changed` 信號。

#### Threading Model / 執行緒模型
- **Main Thread (GUI)**: All PyQt widget operations MUST run on the main thread.
- **Audio Thread (rtmidi)**: MIDI callbacks run on a high-priority C++ thread.
  - 🛑 **NO** blocking operations (I/O, heavy computation).
  - 🛑 **NO** direct GUI updates.
  - ✅ **USE** `pyqtSignal` to communicate with the main thread.
- **即時音訊執行緒**：MIDI 回調運行於高優先級 C++ 執行緒。嚴禁阻塞操作或直接更新 GUI，必須透過 `pyqtSignal` 通訊。

---

## 2. Development Workflow / 開發流程

### Environment Setup / 環境建置
1. **Clone & Install**:
   ```bash
   git clone https://github.com/EdmondVirelle/cyber-qin.git
   pip install -e .[dev]
   ```
2. **Dependencies**: Manage dependencies in `pyproject.toml`, NOT requirements.txt.
   - **依賴管理**：請在 `pyproject.toml` 中管理依賴。

### Git Workflow / Git 工作流
- **Branch Naming**:
  - `feat/`: New features (e.g., `feat/midi-export`)
  - `fix/`: Bug fixes (e.g., `fix/latency-spike`)
  - `refactor/`: Code restructuring
  - `docs/`: Documentation updates
- **Commit Messages**: Follow **Conventional Commits** strictly.
  - `feat: allow type 1 midi export`
  - `fix: resolve race condition in audio thread`

---

## 3. Pull Request (PR) Checklist / PR 檢查清單

Before submitting your PR, ensure the following:
提交 PR 前，請確保完成以下事項：

- [ ] **Linting**: Run `ruff check .` and fix all violations.
- [ ] **Tests**: Run `pytest` and ensure all tests pass (especially `test_concurrency`).
- [ ] **I18N**: Verified all new UI strings are translatable and added to `translator.py`.
- [ ] **Thread Safety**: Verified no GUI calls are made from background threads.
- [ ] **Type Hints**: Checked that strict type hinting is applied.

---

## 4. Issue Reporting / 問題回報

Provide strict technical details (OS, Python ver, MIDI hardware) and a minimal reproduction script if possible.
請提供嚴格的技術細節（作業系統、Python 版本、MIDI 硬體），若可能請附上最小重現腳本。
