"""Translation manager for multi-language support (I18N)."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

# ISO 639-1 / 3166 codes
LANGUAGES = {
    "en": "English",
    "zh_tw": "繁體中文",
    "zh_cn": "简体中文",
    "ja": "日本語",
    "ko": "한국어",
}

class Translator(QObject):
    """Global translation manager singleton."""

    language_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._current_lang = "en"  # Default

        # Define translations
        self._data = {
            "en": {
                "app.title": "Cyber Qin",
                "app.subtitle": "Cyber Qin Xian",
                "nav.live": "Live Mode",
                "nav.library": "Library",
                "nav.editor": "Sequencer",
                "sidebar.credit": "by Ye Weiyu (Where Winds Meet)",
                "sidebar.support": "Support on Ko-fi",
                "sidebar.version": "v{version}",

                # Live Mode
                "live.title": "Live Mode",
                "live.desc": "Connect MIDI device and play in real-time.",
                "live.midi_device": "MIDI Device",
                "live.refresh": "Refresh",
                "live.connect": "Connect",
                "live.disconnect": "Disconnect",
                "live.mapping": "Mapping Scheme",
                "live.transpose": "Transpose",
                "live.auto_tune": "Auto-Tune",
                "live.record": "Record",
                "live.stop_record": "Stop Rec",
                "live.recording": "Recording...",
                "live.log": "Event Log",
                "live.status.connected": "Connected: {port}",
                "live.status.disconnected": "Disconnected",

                # Library
                "lib.title": "Library",
                "lib.desc": "Import MIDI files, double-click or press play to listen.",
                "lib.search": "Search tracks...",
                "lib.import": "+ Import MIDI",
                "lib.col.num": "#",
                "lib.col.title": "Title",
                "lib.col.duration": "Duration",
                "lib.empty.title": "No MIDI files imported",
                "lib.empty.sub": "Click '+ Import MIDI' to start",

                # Editor
                "editor.title": "Sequencer",
                "editor.desc": "Compose via piano keys or drag on timeline.",
                "editor.record": "● Record",
                "editor.play": "▶ Play",
                "editor.stop": "■ Stop",
                "editor.save": "Save",
                "editor.import": "Import",
                "editor.export": "Export",
                "editor.undo": "Undo (Ctrl+Z)",
                "editor.redo": "Redo (Ctrl+Y)",
                "editor.clear": "Clear All",
                "editor.pencil": "✎ Pencil",
                "editor.help": "Help",
                "editor.duration": "Duration",
                "editor.time_sig": "Time Sig",
                "editor.bpm": "BPM",
                "editor.snap": "Snap",
                "editor.velocity": "Velocity",
                "editor.shortcuts": "⌨ Shortcuts",
                "editor.note_count": "{notes} Notes · {bars} Bars",

                 # Now Playing
                "player.repeat.off": "Repeat Off",
                "player.repeat.one": "Repeat One",
                "player.repeat.all": "Repeat All",
            },
            "zh_tw": {
                "app.title": "賽博琴仙",
                "app.subtitle": "Cyber Qin Xian",
                "nav.live": "演奏模式",
                "nav.library": "曲庫",
                "nav.editor": "編曲器",
                "sidebar.credit": "燕雲十六聲 · 葉微雨 製作",
                "sidebar.support": "Support on Ko-fi",
                "sidebar.version": "v{version}",

                "live.title": "演奏模式",
                "live.desc": "連接 MIDI 裝置，即時演奏映射到遊戲按鍵。",
                "live.midi_device": "MIDI 裝置",
                "live.refresh": "重新整理",
                "live.connect": "連線",
                "live.disconnect": "斷線",
                "live.mapping": "映射方案",
                "live.transpose": "移調",
                "live.auto_tune": "自動校正",
                "live.record": "錄音",
                "live.stop_record": "停止錄音",
                "live.recording": "錄音中...",
                "live.log": "事件紀錄",
                "live.status.connected": "已連線: {port}",
                "live.status.disconnected": "未連線",

                "lib.title": "曲庫",
                "lib.desc": "匯入 MIDI 檔案，雙擊或按播放鍵自動演奏。",
                "lib.search": "搜尋曲目...",
                "lib.import": "+ 匯入 MIDI",
                "lib.col.num": "#",
                "lib.col.title": "標題",
                "lib.col.duration": "時長",
                "lib.empty.title": "尚未匯入任何 MIDI 檔案",
                "lib.empty.sub": "點擊「+ 匯入 MIDI」開始",

                "editor.title": "編曲器",
                "editor.desc": "點擊琴鍵輸入音符，拖曳時間軸編輯旋律。",
                "editor.record": "● 錄音",
                "editor.play": "▶ 播放",
                "editor.stop": "■ 停止",
                "editor.save": "存檔",
                "editor.import": "匯入",
                "editor.export": "匯出",
                "editor.undo": "復原 (Ctrl+Z)",
                "editor.redo": "重做 (Ctrl+Y)",
                "editor.clear": "清除全部",
                "editor.pencil": "✎ 鉛筆",
                "editor.help": "說明",
                "editor.duration": "時值",
                "editor.time_sig": "拍號",
                "editor.bpm": "BPM",
                "editor.snap": "Snap",
                "editor.velocity": "力度",
                "editor.shortcuts": "⌨ 快捷鍵",
                "editor.note_count": "{notes} 音符 · {bars} 小節",

                "player.repeat.off": "關閉",
                "player.repeat.one": "單曲重複",
                "player.repeat.all": "全部循環",
            },
            "zh_cn": {
                "app.title": "赛博琴仙",
                "app.subtitle": "Cyber Qin Xian",
                "nav.live": "演奏模式",
                "nav.library": "曲库",
                "nav.editor": "编曲器",
                "sidebar.credit": "燕云十六声 · 叶微雨 制作",
                "sidebar.support": "Support on Ko-fi",
                "sidebar.version": "v{version}",

                "live.title": "演奏模式",
                "live.desc": "连接 MIDI 设备，即时演奏映射到游戏按键。",
                "live.midi_device": "MIDI 设备",
                "live.refresh": "刷新",
                "live.connect": "连接",
                "live.disconnect": "断开",
                "live.mapping": "映射方案",
                "live.transpose": "移调",
                "live.auto_tune": "自动校正",
                "live.record": "录音",
                "live.stop_record": "停止录音",
                "live.recording": "录音中...",
                "live.log": "事件记录",
                "live.status.connected": "已连接: {port}",
                "live.status.disconnected": "未连接",

                "lib.title": "曲库",
                "lib.desc": "导入 MIDI 文件，双击或按播放键自动演奏。",
                "lib.search": "搜索曲目...",
                "lib.import": "+ 导入 MIDI",
                "lib.col.num": "#",
                "lib.col.title": "标题",
                "lib.col.duration": "时长",
                "lib.empty.title": "尚未导入任何 MIDI 文件",
                "lib.empty.sub": "点击“+ 导入 MIDI”开始",

                "editor.title": "编曲器",
                "editor.desc": "点击琴键输入音符，拖拽时间轴编辑旋律。",
                "editor.record": "● 录音",
                "editor.play": "▶ 播放",
                "editor.stop": "■ 停止",
                "editor.save": "保存",
                "editor.import": "导入",
                "editor.export": "导出",
                "editor.undo": "撤销 (Ctrl+Z)",
                "editor.redo": "重做 (Ctrl+Y)",
                "editor.clear": "清除全部",
                "editor.pencil": "✎ 铅笔",
                "editor.help": "说明",
                "editor.duration": "时值",
                "editor.time_sig": "拍号",
                "editor.bpm": "BPM",
                "editor.snap": "Snap",
                "editor.velocity": "力度",
                "editor.shortcuts": "⌨ 快捷键",
                "editor.note_count": "{notes} 音符 · {bars} 小节",

                "player.repeat.off": "关闭",
                "player.repeat.one": "单曲重复",
                "player.repeat.all": "全部循环",
            },
             "ja": {
                "app.title": "サイバー琴仙",
                "app.subtitle": "Cyber Qin Xian",
                "nav.live": "演奏モード",
                "nav.library": "ライブラリ",
                "nav.editor": "シーケンサー",
                "sidebar.credit": "by Ye Weiyu (Where Winds Meet)",
                "sidebar.support": "Ko-fiでサポート",
                "sidebar.version": "v{version}",

                "live.title": "演奏モード",
                "live.desc": "MIDIデバイスを接続して、リアルタイムで演奏します。",
                "live.midi_device": "MIDIデバイス",
                "live.refresh": "更新",
                "live.connect": "接続",
                "live.disconnect": "切断",
                "live.mapping": "キー配置",
                "live.transpose": "移調",
                "live.auto_tune": "自動補正",
                "live.record": "録音",
                "live.stop_record": "録音停止",
                "live.recording": "録音中...",
                "live.log": "イベントログ",
                "live.status.connected": "接続済み: {port}",
                "live.status.disconnected": "未接続",

                "lib.title": "ライブラリ",
                "lib.desc": "MIDIファイルをインポートし、ダブルクリックまたは再生ボタンで演奏します。",
                "lib.search": "検索...",
                "lib.import": "+ MIDIインポート",
                "lib.col.num": "#",
                "lib.col.title": "タイトル",
                "lib.col.duration": "時間",
                "lib.empty.title": "MIDIファイルがありません",
                "lib.empty.sub": "「+ MIDIインポート」をクリックして開始",

                "editor.title": "シーケンサー",
                "editor.desc": "鍵盤をクリックして音符を入力、タイムラインで編集。",
                "editor.record": "● 録音",
                "editor.play": "▶ 再生",
                "editor.stop": "■ 停止",
                "editor.save": "保存",
                "editor.import": "インポート",
                "editor.export": "エクスポート",
                "editor.undo": "元に戻す (Ctrl+Z)",
                "editor.redo": "やり直し (Ctrl+Y)",
                "editor.clear": "全消去",
                "editor.pencil": "✎ 鉛筆",
                "editor.help": "ヘルプ",
                "editor.duration": "音価",
                "editor.time_sig": "拍子",
                "editor.bpm": "BPM",
                "editor.snap": "スナップ",
                "editor.velocity": "ベロシティ",
                "editor.shortcuts": "⌨ ショートカット",
                "editor.note_count": "{notes} 音符 · {bars} 小節",

                "player.repeat.off": "リピートオフ",
                "player.repeat.one": "1曲リピート",
                "player.repeat.all": "全曲リピート",
            },
            "ko": {
                "app.title": "사이버 琴仙",
                "app.subtitle": "Cyber Qin Xian",
                "nav.live": "연주 모드",
                "nav.library": "라이브러리",
                "nav.editor": "시퀀서",
                "sidebar.credit": "by Ye Weiyu (Where Winds Meet)",
                "sidebar.support": "Ko-fi 후원하기",
                "sidebar.version": "v{version}",

                "live.title": "연주 모드",
                "live.desc": "MIDI 장치를 연결하고 실시간으로 연주하세요.",
                "live.midi_device": "MIDI 장치",
                "live.refresh": "새로고침",
                "live.connect": "연결",
                "live.disconnect": "연결 끊기",
                "live.mapping": "키 매핑",
                "live.transpose": "조옮김",
                "live.auto_tune": "자동 보정",
                "live.record": "녹음",
                "live.stop_record": "녹음 중지",
                "live.recording": "녹음 중...",
                "live.log": "이벤트 로그",
                "live.status.connected": "연결됨: {port}",
                "live.status.disconnected": "연결 안 됨",

                "lib.title": "라이브러리",
                "lib.desc": "MIDI 파일을 가져오고 더블 클릭하거나 재생 버튼을 누르세요.",
                "lib.search": "검색...",
                "lib.import": "+ MIDI 가져오기",
                "lib.col.num": "#",
                "lib.col.title": "제목",
                "lib.col.duration": "시간",
                "lib.empty.title": "가져온 MIDI 파일 없음",
                "lib.empty.sub": "시작하려면 '+ MIDI 가져오기'를 클릭하세요",

                "editor.title": "시퀀서",
                "editor.desc": "피아노 건반을 클릭하여 음표 입력, 타임라인에서 편집.",
                "editor.record": "● 녹음",
                "editor.play": "▶ 재생",
                "editor.stop": "■ 정지",
                "editor.save": "저장",
                "editor.import": "가져오기",
                "editor.export": "내보내기",
                "editor.undo": "실행 취소 (Ctrl+Z)",
                "editor.redo": "다시 실행 (Ctrl+Y)",
                "editor.clear": "모두 지우기",
                "editor.pencil": "✎ 연필",
                "editor.help": "도움말",
                "editor.duration": "음표 길이",
                "editor.time_sig": "박자",
                "editor.bpm": "BPM",
                "editor.snap": "스냅",
                "editor.velocity": "벨로시티",
                "editor.shortcuts": "⌨ 단축키",
                "editor.note_count": "{notes} 음표 · {bars} 마디",

                "player.repeat.off": "반복 끔",
                "player.repeat.one": "한 곡 반복",
                "player.repeat.all": "전체 반복",
            }
        }

    @property
    def current_language(self) -> str:
        return self._current_lang

    def set_language(self, lang_code: str) -> None:
        """Change current language and emit signal."""
        if lang_code in LANGUAGES and lang_code != self._current_lang:
            self._current_lang = lang_code
            self.language_changed.emit()

    def tr(self, key: str, **kwargs) -> str:
        """Translate key to current language. Returns key if not found."""
        lang_data = self._data.get(self._current_lang, {})
        text = lang_data.get(key)

        if text is None:
            # Fallback to English
            text = self._data.get("en", {}).get(key, key)

        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text

# Global singleton instance
translator = Translator()
