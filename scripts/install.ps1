# 賽博琴仙 v1.0.0 安裝腳本
# 使用方式：在 PowerShell 中以管理員身分執行此腳本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  賽博琴仙 v1.0.0 安裝程式" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 檢查 Python
Write-Host "檢查 Python 環境..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Host "❌ 未找到 Python！" -ForegroundColor Red
    Write-Host "請先安裝 Python 3.11 或更高版本：" -ForegroundColor Red
    Write-Host "https://www.python.org/downloads/" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✓ 找到 Python: $($pythonCmd.Source)" -ForegroundColor Green

# 檢查版本
$pythonVersion = & $pythonCmd.Source --version 2>&1
Write-Host "✓ Python 版本: $pythonVersion" -ForegroundColor Green

# 安裝依賴
Write-Host ""
Write-Host "正在安裝依賴套件..." -ForegroundColor Yellow
& $pythonCmd.Source -m pip install -e . --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 依賴套件安裝完成" -ForegroundColor Green
} else {
    Write-Host "❌ 安裝失敗" -ForegroundColor Red
    pause
    exit 1
}

# 創建桌面快捷方式（可選）
Write-Host ""
$createShortcut = Read-Host "是否創建桌面捷徑？(Y/N)"
if ($createShortcut -eq "Y" -or $createShortcut -eq "y") {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\賽博琴仙.lnk")
    $Shortcut.TargetPath = "$($pythonCmd.Source)"
    $Shortcut.Arguments = "-m cyber_qin.main"
    $Shortcut.WorkingDirectory = $PSScriptRoot
    $Shortcut.IconLocation = "$PSScriptRoot\assets\icon.ico"
    $Shortcut.Description = "賽博琴仙 v1.0.0 - MIDI 遊戲演奏工具"
    $Shortcut.Save()
    Write-Host "✓ 桌面捷徑已創建" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  安裝完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "啟動方式：" -ForegroundColor Yellow
Write-Host "1. 點擊桌面捷徑（如果已創建）" -ForegroundColor White
Write-Host "2. 或在此目錄執行：cyber-qin" -ForegroundColor White
Write-Host ""
Write-Host "⚠️ 注意：首次運行需要以系統管理員身分執行" -ForegroundColor Yellow
Write-Host ""
pause
