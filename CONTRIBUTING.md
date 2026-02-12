# Contributing To Cyber Qin / 貢獻指南

This document provides guidelines for contributing to Cyber Qin. Following these rules helps ensure a smooth development process and consistent code quality.

本文提供了貢獻此專案的準則。遵循這些規範有助於確保開發流程與程式碼品質的穩定性。

---

## 1. Contribution Guidelines and Code Style / 貢獻準則與程式碼規範

### Code Style / 程式碼風格
- **Indentation**: Use 4 spaces for indentation.
- **變數縮進**: 統一使用 4 個空格（Spaces）進行縮進。
- **Naming Conventions**: Follow PEP 8 (snake_case for functions/variables, PascalCase for classes).
- **命名規則**: 遵循 PEP 8 規範（函數與變數使用小寫蛇形 snake_case，類別使用大駝峰 PascalCase）。
- **Line Length**: Maximum line length is 99 characters.
- **行長度**: 每行最長 99 個字元。
- **Linting**: The project uses **Ruff** for linting. Ensure your code passes all checks before submitting.
- **代碼檢查**: 專案使用 **Ruff** 進行代碼檢查。提交前請確保程式碼通過所有檢查。

### Development Environment Setup / 開發環境設置
1. **Python Version**: Ensure you are using Python 3.11 or higher.
2. **安裝 Python 版本**: 請確保使用 Python 3.11 或以上版本。
3. **Environment Setup**: Clone the repository and install dependencies in editable mode.
4. **環境建置**: 複製倉庫並以可編輯模式安裝依賴。
   ```bash
   pip install -e .[dev]
   ```
5. **MIDI Environment**: For testing MIDI features, use `python-rtmidi`. Ensure you have a virtual MIDI port or a physical MIDI device connected.
6. **MIDI 環境**: 測試 MIDI 功能時請使用 `python-rtmidi`。確保已連接虛擬 MIDI 端口或實體 MIDI 設備。

---

## 2. Issue Reporting / 如何回報問題

If you encounter a bug or have a feature request, please open an Issue. Providing the following information helps us resolve it faster:

如果您發現 Bug 或有新功能建議，請提交 Issue。提供以下資訊能加快處理速度：

- **Steps to Reproduce**: Detailed steps on how to trigger the bug.
- **重現步驟**: 詳細說明如何觸發 Bug。
- **Environment Details**: OS version, Python version, hardware model (e.g., Roland FP-30X).
- **環境資訊**: 作業系統版本、Python 版本、硬體型號。
- **Log/Screenshots**: Error messages or relevant screenshots.
- **日誌與截圖**: 錯誤訊息或相關截圖。

---

## 3. Git Workflow / 分支與提交規範

### Branch Naming / 分支命名
- Feature development: `feature/description`
- Bug fixes: `fix/description`
- Refactoring: `refactor/description`
- Documentation: `docs/description`

### Commit Message Format / 提交格式
We follow the **Conventional Commits** specification:
我們遵循 **Conventional Commits** 規範：
- `feat`: A new feature / 新功能
- `fix`: A bug fix / Bug 修復
- `docs`: Documentation only changes / 僅文件更新
- `style`: Changes that do not affect the meaning of the code / 不影響邏輯的格式調整
- `refactor`: A code change that neither fixes a bug nor adds a feature / 代碼重構
- `test`: Adding missing tests or correcting existing tests / 測試相關
- `chore`: Changes to the build process or auxiliary tools / 構建流程或工具調整

Example: `feat: add FF14 mapping support`

---

## 4. Pull Request (PR) Process / 拉取請求流程

1. **Base Branch**: Submit PRs to the `main` branch unless instructed otherwise.
2. **目標分支**: 除非另有說明，否則請將 PR 發送到 `main` 分支。
3. **Pre-submission Checks**:
4. **提交前檢查**:
   - Run linter: `ruff check .`
   - Run tests: `pytest`
5. **Review**: All PRs require a review. Address any feedback before merge.
6. **審查**: 所有 PR 都需要經過審查，請在合併前處理反饋建議。
