# 賽博琴仙 v1.0.0 安裝指南

## 📋 系統需求

- **作業系統**: Windows 10 / 11 (64-bit)
- **Python**: 3.11 / 3.12 / 3.13
- **MIDI 裝置**: 任何 USB MIDI 鍵盤
- **權限**: 必須以系統管理員身分執行

---

## 🚀 快速安裝（推薦）

### 步驟 1: 下載

從 [GitHub Releases](https://github.com/EdmondVirelle/cyber-qin/releases/tag/v1.0.0) 下載源碼壓縮包：
- **Source code (zip)** - 點擊下載

### 步驟 2: 解壓縮

解壓到任意位置，例如：
```
C:\賽博琴仙\
```

### 步驟 3: 安裝 Python（如果尚未安裝）

前往 https://www.python.org/downloads/ 下載並安裝 Python 3.11 或更高版本。

⚠️ **重要**：安裝時勾選「Add Python to PATH」

### 步驟 4: 執行安裝腳本

**以系統管理員身分**開啟 PowerShell：
1. 在專案資料夾按住 `Shift` + 右鍵
2. 選擇「在這裡開啟 PowerShell 視窗」
3. 執行安裝腳本：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install.ps1
```

腳本會自動：
- ✅ 檢查 Python 環境
- ✅ 安裝所有依賴套件
- ✅ 創建桌面捷徑（可選）

### 步驟 5: 啟動

點擊桌面捷徑，或在專案目錄執行：
```powershell
cyber-qin
```

⚠️ **首次運行必須以系統管理員身分執行**（SendInput 需要提升權限）

---

## 🛠️ 手動安裝（進階）

如果自動安裝腳本無法運行：

```powershell
# 1. 進入專案目錄
cd C:\賽博琴仙

# 2. 安裝依賴
pip install -e .[dev]

# 3. 啟動（以管理員身分）
cyber-qin
```

---

## ❓ 常見問題

### Q: 為什麼需要以管理員身分執行？
A: Windows 的 `SendInput` API 需要提升權限才能在遊戲中注入按鍵。

### Q: 執行時出現「找不到 Python」錯誤
A: 確認 Python 已正確安裝並加入 PATH。重新安裝 Python 並勾選「Add Python to PATH」。

### Q: 連接 MIDI 裝置後沒有反應
A:
1. 確認 MIDI 裝置已正確連接
2. 在「演奏模式」重新整理裝置列表
3. 檢查裝置是否被其他軟體佔用

### Q: 遊戲中按鍵沒有反應
A:
1. 確認以系統管理員身分執行
2. 檢查是否選擇了正確的鍵位方案（燕雲 36 鍵 / FF14 37 鍵）
3. 確認遊戲視窗為焦點視窗

### Q: Windows Defender 攔截
A: 將專案目錄加入排除項目：
- 設定 → 病毒與威脅防護 → 管理設定 → 排除項目
- 加入專案資料夾

---

## 🎮 使用說明

### 即時演奏

1. 連接 MIDI 鍵盤
2. 開啟賽博琴仙
3. 在「演奏模式」選擇 MIDI 裝置
4. 選擇對應的鍵位方案（燕雲/FF14/通用）
5. 切換到遊戲視窗開始演奏

### MIDI 播放

1. 點選「曲庫」
2. 匯入 .mid 檔案
3. 調整播放速度（0.25x ~ 2.0x）
4. 開啟循環模式（可選）
5. 點擊播放

### MIDI 編輯

1. 點選「編曲器」
2. 在鋼琴卷軸上繪製音符
3. 使用快捷鍵編輯（按 `?` 查看快捷鍵）
4. 匯出修改後的 MIDI 檔案

---

## 📚 更多資源

- [完整功能說明](README_TW.md)
- [鍵位映射表](README_TW.md#鍵位方案)
- [問題回報](https://github.com/EdmondVirelle/cyber-qin/issues)

---

**🎹 享受你的遊戲鋼琴演奏！**
