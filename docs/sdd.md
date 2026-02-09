# 燕雲十六聲 MIDI 演奏映射系統設計文件 (SDD)

> **專案代號**：賽博琴仙
> **輸入設備**：Roland FP-30X 數位鋼琴
> **目標遊戲**：燕雲十六聲 (Where Winds Meet)
> **平台**：Windows

---

## 1. 系統概述 (System Overview)

本系統旨在建立一個**低延遲的中間層（Middleware）**，將標準 MIDI 協議（MIDI Protocol）訊號映射至《燕雲十六聲》演奏系統所使用的 **36 鍵**鍵盤指令。

系統須處理複雜的修飾鍵（`Shift` / `Ctrl`）組合邏輯，以實現完整的半音階演奏。

---

## 2. 硬體與環境規範 (Hardware & Environment)

| 項目       | 規格                                               |
| ---------- | -------------------------------------------------- |
| **輸入設備** | Roland FP-30X 數位鋼琴（USB-MIDI 模式）             |
| **輸出目標** | Windows DirectInput 環境下之遊戲程序（Where Winds Meet） |
| **核心需求** | 支援 36 鍵模式（`F1` 切換），包含升記號（♯）與降記號（♭） |

---

## 3. 核心映射邏輯 (Core Mapping Logic)

### 3.1 映射規則定義

根據遊戲界面與演奏邏輯，按鍵行為分為三類：

| 類型                | 行為說明                    | 修飾鍵          |
| ------------------- | --------------------------- | ---------------- |
| **原音 (Natural)**  | 直接對應基礎按鍵             | 無               |
| **升音 (Sharp ♯)**  | 觸發 `Shift` + 基礎按鍵     | `Shift`          |
| **降音 (Flat ♭)**   | 觸發 `Ctrl` + 基礎按鍵      | `Ctrl`           |

### 3.2 36 鍵映射表 (Detailed Mapping Table)

#### 低音層 (Low Octave) — MIDI 48 ~ 59

| 音名 | MIDI | 類型    | 輸出按鍵         |
| ---- | ---- | ------- | ---------------- |
| C3   | 48   | Natural | `Z`              |
| C#3  | 49   | Sharp   | `Shift` + `Z`   |
| D3   | 50   | Natural | `X`              |
| Eb3  | 51   | Flat    | `Ctrl` + `C`    |
| E3   | 52   | Natural | `C`              |
| F3   | 53   | Natural | `V`              |
| F#3  | 54   | Sharp   | `Shift` + `V`   |
| G3   | 55   | Natural | `B`              |
| G#3  | 56   | Sharp   | `Shift` + `B`   |
| A3   | 57   | Natural | `N`              |
| Bb3  | 58   | Flat    | `Ctrl` + `M`    |
| B3   | 59   | Natural | `M`              |

#### 中音層 (Mid Octave) — MIDI 60 ~ 71

| 音名 | MIDI | 類型    | 輸出按鍵         |
| ---- | ---- | ------- | ---------------- |
| C4   | 60   | Natural | `A`              |
| C#4  | 61   | Sharp   | `Shift` + `A`   |
| D4   | 62   | Natural | `S`              |
| Eb4  | 63   | Flat    | `Ctrl` + `D`    |
| E4   | 64   | Natural | `D`              |
| F4   | 65   | Natural | `F`              |
| F#4  | 66   | Sharp   | `Shift` + `F`   |
| G4   | 67   | Natural | `G`              |
| G#4  | 68   | Sharp   | `Shift` + `G`   |
| A4   | 69   | Natural | `H`              |
| Bb4  | 70   | Flat    | `Ctrl` + `J`    |
| B4   | 71   | Natural | `J`              |

#### 高音層 (High Octave) — MIDI 72 ~ 83

| 音名 | MIDI | 類型    | 輸出按鍵         |
| ---- | ---- | ------- | ---------------- |
| C5   | 72   | Natural | `Q`              |
| C#5  | 73   | Sharp   | `Shift` + `Q`   |
| D5   | 74   | Natural | `W`              |
| Eb5  | 75   | Flat    | `Ctrl` + `E`    |
| E5   | 76   | Natural | `E`              |
| F5   | 77   | Natural | `R`              |
| F#5  | 78   | Sharp   | `Shift` + `R`   |
| G5   | 79   | Natural | `T`              |
| G#5  | 80   | Sharp   | `Shift` + `T`   |
| A5   | 81   | Natural | `Y`              |
| Bb5  | 82   | Flat    | `Ctrl` + `U`    |
| B5   | 83   | Natural | `U`              |

---

## 4. 系統架構與工作流 (Architecture & Workflow)

### 4.1 數據流向 (Data Pipeline)

```
Roland FP-30X ──USB-MIDI──▶ [捕獲層] ──▶ [預處理層] ──▶ [轉換層] ──▶ [執行層] ──▶ 遊戲視窗
```

| 階段                         | 說明                                                                |
| ---------------------------- | ------------------------------------------------------------------- |
| **捕獲層 (Capture)**         | 監聽實體 MIDI 設備之 `Note_On` 與 `Note_Off` 事件                     |
| **預處理層 (Pre-processing)** | 計算 Note Number 對應之音程與八度；套用移調量（Transpose Offset），確保鋼琴中央 C 對應遊戲中音區 |
| **轉換層 (Transformation)**   | 根據映射表檢索目標按鍵；判斷是否需要附加 `Shift` 或 `Ctrl` 狀態            |
| **執行層 (Execution)**        | 調用內核級模擬驅動（如 DirectInput 模擬）                               |

### 4.2 組合鍵時序控制

模擬組合鍵時，須嚴格遵循以下序列：

```
KeyDown(Modifier) → KeyDown(Key) → KeyUp(Key) → KeyUp(Modifier)
```

> **注意**：修飾鍵的按下與釋放必須包裹目標鍵，否則遊戲可能無法正確識別組合鍵。

---

## 5. 功能需求 (Functional Requirements)

### 5.1 演奏模式支援

- **單音模式**：快速響應單個按鍵
- **組合鍵處理**：處理同一個實體鍵在不同情境下的修飾鍵輸出（例如：`Eb` 觸發 `Ctrl+C` 而非單純的 `C`）

### 5.2 系統參數調整

- **動態移調**：允許調整 MIDI 音符與遊戲鍵位的 Offset（以 12 半音為單位）
- **輸入過濾**：過濾 MIDI 指令中的 Aftertouch 與 SysEx 訊息，減少處理負擔

---

## 6. 非功能需求 (Non-functional Requirements)

### 6.1 延遲控制 (Latency)

端到端延遲（MIDI 輸入至模擬按鍵發出）須低於 **10ms**，以確保演奏同步感。

### 6.2 穩定性與相容性

- **權限級別**：執行程序須具備管理員權限，以繞過遊戲視窗的輸入攔截
- **輸入法兼容**：系統須在演奏期間強制或提醒切換至「英文輸入模式」，防止按鍵轉為文字輸入

### 6.3 安全性 (Anti-Cheat Considerations)

> 不讀寫遊戲記憶體，僅進行**硬體層級模擬**，降低被反外掛系統判定為惡意軟體的風險。

---

## 7. 異常處理 (Exception Handling)

| 異常情境       | 處理策略                                                              |
| -------------- | --------------------------------------------------------------------- |
| **音符丟失**   | 當快速彈奏時，確保每一組 `Note_On` 都有對應的 `KeyUp` 釋放               |
| **範圍溢出**   | 若彈奏 Roland 88 鍵中超出遊戲 36 鍵範圍的音符，系統應進行忽略或自動取八度（Closest Octave）處理 |
