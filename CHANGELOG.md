# Cyber Qin 版本技術變更紀錄 (v0.1.0 → v2.4.0)

---

## v2.4.0 - 練習模式音樂遊戲體驗強化
**參考音樂播放**：練習模式現在透過 `MidiOutputPlayer` 播放參考音樂，與落下音符同步，速度可即時調整。
**按鍵回饋音效**：使用者按鍵時透過 `preview_note()` 發出即時音效回饋，確認是否命中。
**速度控制器**：新增 `SpeedControl` 元件 (0.25x–2.0x)，降速練習困難段落，顯示時間與音訊同步縮放。
**成績結果頁**：練習結束後顯示總分、準確率、PERFECT/GREAT/GOOD/MISS 分級統計、最大連擊數，支援「重試」與「換曲」。
**視覺強化**：命中時判定線產生圓形光暈閃爍效果；連擊數 > 5 時顯示 COMBO 疊加文字。
**生命週期信號**：新增 `practice_started` / `practice_stopped` / `practice_finished` / `speed_changed` 信號，供 AppShell 同步音訊播放器。
**翻譯補全**：補齊日文 (JA) 與韓文 (KO) 的練習模式翻譯鍵；新增 `practice.retry`、`practice.total_notes` 五語系翻譯。
**測試擴充**：新增 29 項測試涵蓋速度控制、連擊顯示、閃光效果、成績頁、生命週期信號。全套件 1,270 項測試通過。

## v2.3.2 - 使用者手冊重寫
**文件重構**：全面重寫 `README.md` 與 `README_TW.md`，從開發者文件轉型為面向終端使用者的完整操作手冊。

## v2.3.1 - 練習模式序列修正
**類方法回傳值修正**：修復 `EditorSequence.from_midi_file_events` 類方法之回傳值未被正確接收的問題，導致練習模式無法載入 MIDI 事件序列。

## v2.3.0 - 練習模式內建選曲器
**內建曲目選擇器**：練習模式新增內建歌曲選擇器 (Song Picker)，使用者可直接在練習視圖中瀏覽並載入曲庫曲目。
**邊界強化**：多處邊界條件加固與錯誤處理改善，提升整體穩定性。

## v2.2.1 - 建構配置同步
**PyInstaller Spec 更新**：同步 `cyber_qin.spec` 以涵蓋 v2.0.0 新增之模組與移動後的 `RELEASE.txt` 路徑。

## v2.2.0 - 編輯器 UX 強化與練習模式修正
**編輯器國際化**：工具列 Tooltips 全面實裝多語系支援；新增暫停/繼續 (Pause/Resume) 操作。
**練習模式修正**：修復標頭 UI 佈局問題；新增鍵盤輸入模式 (Keyboard Input Mode) 供無 MIDI 裝置使用者使用。
**樂譜對齊**：修正 `ScoreViewWidget` 屬性名稱與 `NotationNote` 資料模型之不一致。

## v2.1.0 - CI 修復與邊界強化
**Lint/Type-check 修復**：解決 CI 管線中 Ruff lint 與 mypy 型別檢查失敗。
**邊界強化**：強化多處邊界情境之錯誤處理邏輯。

## v2.0.0 - 專業級數位編曲工作站
賽博琴仙最大規模更新。新增 11 項核心功能，從 MIDI 映射器進化為完整數位編曲工作站。模組數 30→58，測試數 598→1,123，程式碼行數 ~6,500→~12,750。

**Phase A — 核心邏輯引擎**：
- **智慧編排 (Smart Arrangement)**：自動移調與八度折疊引擎，三種策略 (`global_transpose` / `flowing_fold` / `hybrid`) 依音符分佈自動選擇。
- **MIDI 效果器 (MIDI FX)**：琶音器、人性化、量化、和弦生成四種即時效果處理器，操作 `list[BeatNote]` 可自由組合。
- **AI 作曲 (Melody Generator)**：一階馬可夫鏈規則式旋律生成器，支援 8 種音階與 4 種和弦進行之低音線生成。

**Phase B — 編輯器增強**：
- **復原/重做升級**：18 種操作描述之命名快照追蹤。
- **幽靈音符 (Ghost Notes)**：智慧編排後原始位置以珊瑚紅半透明顯示，透明度 10%-80% 可調。
- **自動化曲線 (Automation Lane)**：力度/速度曲線之可拖曳控制點，線性內插，與鋼琴卷簾同步捲動。

**Phase C — 新視圖**：
- **練習模式 (Practice Mode)**：落下音符節奏遊戲，PERFECT(30ms)/GREAT(80ms)/GOOD(150ms) 判定窗口，60fps QPainter 渲染。
- **即時視覺化器 (Live Visualizer)**：粒子爆發+波紋效果+八度色譜+力度條圖，60fps 動畫。
- **樂譜顯示 (Score View)**：五線譜記譜法渲染，支援全/二分/四分/八分/十六分音符、符桿符尾、臨時升降號。

**Phase D — 匯入匯出與社群**：
- **多格式 I/O**：新增 ABC Notation / LilyPond 匯入匯出，WAV 正弦波合成匯出（純 Python，無外部依賴）。
- **社群樂庫 (Community Library)**：元資料編輯器 + `.cqlib` 合集打包分享。

## v1.0.1 - 版本穩定化
**版本修正**：穩定化修復，確保 v1.0.0 所有功能之發布完整性。

## v1.0.0 - 專業 DAW 級音序器
從「遊戲工具」升級為「專業 DAW 級」MIDI 編輯器。598 項測試全數通過。

**DAW 級音序器 (Phase 1)**：
- **視窗尺寸提升**：預設 1600×1000、最小 1400×900，為 88 鍵鋼琴卷簾騰出垂直空間。
- **力度軌道 (Velocity Lane)**：鋼琴卷簾下方 80px 專用力度軌道，拖曳調整力度值。
- **力度色彩編碼**：音符亮度反映 MIDI 力度值 (alpha 64-255)。
- **水平縮放滑桿**：工具列 120px 滑桿 (20-400 px/beat)，與 Ctrl+Wheel 雙向同步。
- **播放跟隨模式**：OFF / PAGE / CONTINUOUS / SMART 四種跟隨策略。

**DAW 級音序器 (Phase 2-5)**：
- **雙軸縮放系統**：水平 Ctrl+Wheel + 垂直 Ctrl+Shift+Wheel，滑鼠中心縮放。
- **網格精度擴展**：從 1/32 延伸至 1/128 音符精度，使用者可自選。
- **可收合側邊欄**：隱藏 TrackPanel+PitchRuler 可回收 208px 水平空間。
- **效能優化**：力度軌道採用二分搜尋視口裁剪 (Binary Search Viewport Culling)，O(log n) 複雜度。
- **鍵盤導航**：Ctrl+Left/Right 水平捲動，所有縮放快捷鍵可由鍵盤觸發。

**Minimap 與批次編輯**：全域縮圖導覽 + 力度批次編輯功能。
**設定對話框 (Settings Dialog)**：完整 ConfigManager 整合，支援 MIDI 裝置選擇。
**MIDI 熱插拔**：增強 MIDI 裝置自動探索與熱插拔支援。
**鍵位檢視器 (Key Mapping Viewer)**：新增對話框顯示目前映射方案之完整鍵位對照。
**節拍器先導 (Metronome Count-in)**：播放前可設定節拍器先導拍。
**循環播放 (Loop Playback)**：編輯器內建選區循環播放功能。

## v0.9.4 - MusicXML 匯入與 Cyber Ink 主題
**MusicXML 匯入**：實裝 MusicXML (.xml) 檔案解析器，可將標準樂譜匯入編輯器。
**網格精度**：鋼琴卷簾網格最小精度提升至 1/32 音符。
**Cyber Ink 主題強化**：進一步精煉賽博墨韻視覺主題。

## v0.9.3 - 跨平台 CI/CD 與設定系統
**跨平台防護**：新增 Windows 專用程式碼之平台防護 (Platform Guards)，Unix 系統自動跳過 ctypes/SendInput 相關測試。
**CI/CD 強化**：GitHub Actions 多作業系統矩陣 (Windows/macOS/Linux) + 覆蓋率報告整合。
**設定對話框測試**：新增 pytest-qt 整合測試覆蓋 Settings Dialog。
**NoteRoll 效能**：實裝二分搜尋優化 (Binary Search Optimization) 於鋼琴卷簾渲染，大型專案效能顯著提升。
**JSON 設定系統**：新增 `ConfigManager`，遷移 `app_shell` 視窗狀態與 `live_mode_view` 設定至統一 JSON 持久化。
**88 鍵編輯器**：MIDI 編輯器擴展至完整 88 鍵範圍，以遊戲區域高亮 (Game Zone Highlighting) 區分可彈奏範圍。
**測試覆蓋率躍升**：`midi_file_player` Qt 相關測試覆蓋率由 33% → 94%。

## v0.9.2 - 穩定性修復
**全域異常處理**：新增全域例外處理程式與錯誤對話框，攔截未預期的異常，避免直接閃退。
**曲庫載入容錯**：增強曲庫載入機制之錯誤容忍度與日誌記錄，自動略過損壞或遺失的檔案。

## v0.9.1 - 型別嚴格化與專案清理
**MyPy 嚴格模式**：解決 73 項 MyPy strict mode 型別錯誤，涵蓋 `core/` 與 `gui/` 全部模組。
**CI 強化**：CI 管線新增嚴格 I18N 與型別檢查執行。
**專案清理**：移除 git 倉庫中的測試產物與覆蓋率報告，更新 `.gitignore`。
**文件國際化**：README 拆分為英文版與繁體中文版；新增雙語 `CONTRIBUTING.md`。

## v0.9.0 - 歸屬系統與語系強化
**動態映射機制**：實裝 Credit 標籤的多語系動態映射 (Multi-language Dynamic Mapping)，確保不同語系下的貢獻資訊能準確呈現。

## v0.8.9 - Credit 系統與定位轉型
**Credit 標註更新**：側邊欄更新 Credit 為「Edmond Virelle」，新增 FF14 與 VTuber 角色標註，全面支援多語系切換。
**README 定位轉型**：從燕雲專屬工具轉向通用「遊戲彈琴工具」定位。

## v0.8.8 - 播放系統國際化 (I18N)
**播放列全區域 I18N**：實裝未載入曲目、播放速度標籤及所有 Transport Tooltips 的多語系支持。
**狀態同步優化**：確保執行緒狀態切換時，Tooltips 內容能即時更新，消除顯示延遲。

## v0.8.7 - 中繼資料與組件 I18N
**映射方案 I18N**：映射名稱與描述欄位改為自 `translator` 模組動態獲取翻譯，新增 `translated_name()` / `translated_desc()` 方法。
**曲庫組件優化**：實裝排序選單 (Sort Menu) 與搜尋列 (Search Input) 佔位符的翻譯機制。
**移調控制**：實裝移調旋鈕之語系適配後綴。

## v0.8.6 - UI 佈局修正與精簡
**側邊欄佈局優化**：啟用 Credit 標籤的 Word-wrap 屬性，實裝字體自動縮小與 12px 水平邊距，防止文字裁切。
**字串長度優化**：針對英、日、韓語系精簡 Credit 字串長度，提升視覺一致性。

## v0.8.5 - 組件補丁
**AnimatedNavButton 修正**：補足缺失之 `set_text` 方法。
**初始化邏輯優化**：移除側邊欄初始化中重複的按鈕附加 (Append) 邏輯，減少資源浪費。

## v0.8.4 - 主題系統修復
**AttributeError 修正**：移除對字串型主題常數之 `.name()` 異常呼叫，提升穩定性。

## v0.8.3 - 路徑引用修正
**ModuleNotFoundError 修正**：更正 `language_selector` 中對於 `theme` 模組的導入路徑。

## v0.8.2 - 核心編輯器進化與性能優化
**編輯器 UX 進化**：實裝核心 33Hz 播放游標；`PianoDisplay` 與 `NoteRoll` 導入動態發光渲染效果。
**映射方案新增**：新增針對 FF14 37-Key (C3-C6) 的自然音階映射方案。
**資料匯出**：實裝 SMF Type 1 多軌 MIDI 匯出功能。
**效能躍升**：將音符索引效能由 O(N²) 大幅優化至 O(N)。

## v0.8.1 - 檔案管理修正
**版本衝突解決**：修復 Release Asset 與快取衝突導致的版本號識別問題。

## v0.8.0 - 多語系框架元年
**框架實裝**：正式導入支援五國語系 (繁中/簡中/日/韓/英) 的翻譯核心與側邊欄語言切換元件。
**FF14 方案**：新增 FF14 37-Key 映射方案。
**文件同步**：提供多語系版本的 README 與發布說明。

## v0.7.5 - 編輯器說明與贊助連結
**Help 對話框**：新增編輯器 Help 按鈕（書本+? 圖示）→ 可捲動操作指南對話框，涵蓋所有快捷鍵與編輯操作。
**Release 模板**：修正 Release workflow 範本（7-Zip 提示 + 免責聲明）。
**Ko-fi 贊助**：新增 Ko-fi 贊助連結至側邊欄與 README。

## v0.7.4 - 編輯器說明與開發者體驗
**Help 對話框**：編輯器 Help 對話框初版實裝。
**Ko-fi 連結**：側邊欄與 README 新增贊助入口。
**MIDI 忽略規則**：`.gitignore` 新增 `.mid/.midi` 檔案排除規則。

## v0.7.3 - 運行時修復
**VC Runtime 捆綁**：將 Visual C++ Runtime DLLs 捆綁至打包輸出，解決部分使用者因缺少 VC Redistributable 而啟動失敗的問題。
**視窗圖示**：新增開發模式之視窗圖示。

## v0.7.2 - 文件更新
**README 重寫**：全面重寫 `README.md`。
**ONBOARDING 更新**：同步更新 `ONBOARDING.md` 統計資料。

## v0.7.1 - 品牌識別
**自訂應用圖示**：新增專屬應用程式圖示。
**Credit 標籤**：側邊欄新增開發者 Credit 標籤。

## v0.7.0 - 編輯器架構重構
**Beat Model**：全面重構為 Beat-based 多軌資料模型 (`EditorSequence` / `EditorTrack`)，取代舊有事件序列。
**鋼琴卷簾互動**：NoteRoll 實裝點擊放置 (Click-to-place)、拖曳調整 (Drag Resize)、框選 (Selection) 操作。
**專案檔案系統**：`.cqp` 專案檔序列化 (JSON + gzip) 實裝，支援儲存/載入完整編輯狀態。
**MIDI 輸出播放**：新增 `MidiOutputPlayer` 供編輯器內預覽播放。
**PyInstaller 修復**：補齊 17 個缺失之 `hiddenimports`。
**測試提升**：測試數量增至 450（新增 `beat_sequence` / `editor_ux` / `project_file` 測試）。

## v0.5.0 - 節拍資料模型
**Beat-based Editor Model**：設計並實作節拍式編輯器資料模型 (`BeatSequence`)，為 v0.7.0 編輯器重構奠定基礎 (Phase 1)。
**軟體設計文件**：撰寫 SDD (Software Design Document)。

## v0.4.0 - 錄音與編輯器
**流水摺疊 (Flowing Fold)**：以 Voice-leading 感知之八度摺疊取代舊版 Modulo Fold，per-channel 追蹤 voice state，打分選擇最佳八度位置。
**9 階段預處理管線**：完整實作打擊樂過濾、八度去重、複音限制等 9 階段 MIDI 前處理管線。
**即時 MIDI 錄音**：錄音引擎 + `.mid` 匯出。
**Auto-Tune 後處理**：節拍量化 + 音階校正。
**虛擬鍵盤編輯器**：可互動鋼琴 + Piano Roll + Undo/Redo。
**音符序列模型**：`NoteSequence` 容器支援 `MidiFileEvent` 互轉。
**測試增長**：289 項測試（+109），8 個測試檔案。

## v0.3.0 - 播放強化與前處理
**循環播放模式**：實裝三種循環模式 (關閉/全部循環/單曲循環) 與上下一首按鈕。
**9 階段前處理**：打擊樂過濾 (Percussion Filter)、八度去重 (Octave Dedup)、複音限制器 (Polyphony Limiter) 等。
**防毒誤報優化**：改善 PyInstaller 打包設定以減少防毒軟體誤報。

## v0.2.0 - 智慧前處理與 CI
**賽博墨韻主題 (Cyber Ink)**：UI 從 Spotify 綠色調全面重設計為青金暖紙深色主題。
**多方案映射引擎**：可切換映射方案 (燕雲 36 鍵 / FF14 32 鍵 / 通用 24/48 鍵) 與動態鋼琴佈局。
**MIDI 前處理器**：八度正規化、力度正規化、時序量化。
**優先級模組**：`timeBeginPeriod` 1ms 計時器精度 + `SetThreadPriority` 即時播放線程。
**MIDI 容錯**：以 `clip=True` 容忍格式不正確的 MIDI 檔案。
**PyInstaller 打包**：`cyber_qin.spec` + `launcher.py` 薄包裝器，Python 3.13 + UAC Admin + Windowed。
**播放快捷鍵**：新增播放控制鍵盤快捷鍵與平滑進度條。
**和弦防汙**：修復修飾鍵閃爍 (Flash Modifier Keys) 防止和弦汙染。
**Release CI**：GitHub Actions 自動構建。

## v0.1.0 - 創世紀
**專案誕生**：MIDI-to-Keyboard 即時映射器，專為燕雲十六聲 36 鍵模式設計。
**技術棧**：Python 3.11+ / PyQt6 / mido + python-rtmidi / ctypes `SendInput`。
**核心管線**：USB MIDI 輸入 → rtmidi 回調 → KeyMapper → SendInput (Scan Code) → DirectInput 遊戲。
**延遲目標**：< 2ms（回調線程直接執行 `SendInput`，不經 Qt 事件佇列）。
