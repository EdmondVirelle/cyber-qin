# 🎉 Cyber Qin v1.0.0 — First Stable Release

**Play a real piano, and your game character plays in sync.**

This is the first stable release of Cyber Qin (賽博琴仙), a real-time MIDI-to-keyboard mapping tool for games like Where Winds Meet (燕雲十六聲) and Final Fantasy XIV. With < 2ms latency, comprehensive MIDI editing capabilities, and a polished user interface, v1.0.0 delivers a complete solution for piano players who want to perform in games.

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

### Option 1: Standalone Executable (Recommended)
1. Download `CyberQin-v1.0.0-Windows-x64.zip` from Assets below
2. Extract to your preferred location
3. Run `賽博琴仙.exe` **as Administrator**

### Option 2: Python Source
```bash
git clone https://github.com/EdmondVirelle/cyber-qin.git
cd cyber-qin
pip install -e .[dev]
cyber-qin  # Run as Administrator
```

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

## 📖 Full Documentation

- [English README](README.md)
- [繁體中文 README](README_TW.md)
- [Release Notes — EN](RELEASE_NOTES_v1.0.0.md)
- [Release Notes — 繁中](RELEASE_NOTES_v1.0.0_TW.md)
- [Release Notes — 简中](RELEASE_NOTES_v1.0.0_CN.md)
- [Changelog](CHANGELOG.md)

---

## 🐛 Known Issues

- **Windows Defender**: May flag executable as unrecognized app (click "More info" → "Run anyway")
- **Input Method Editors**: Some IME software may interfere with key injection
- **High DPI Displays**: UI scaling may not be perfect on 4K monitors (workaround: set Windows scaling to 150%)

See [Issues](https://github.com/EdmondVirelle/cyber-qin/issues) for full tracker.

---

## 🙏 Acknowledgments

Special thanks to all users who provided feedback during the v0.9.x beta period, and to the open-source MIDI and PyQt communities.

---

## 📝 System Requirements

- **OS**: Windows 10 / 11 (x64)
- **MIDI Device**: Any USB MIDI keyboard
- **Privileges**: Must run as **Administrator** for SendInput to work in games

---

## 🔮 What's Next

Planned for v1.1.0:
- Cloud save/sync for MIDI library
- MIDI input monitoring graph
- Custom key mapping editor
- Enhanced multi-language localization

---

**Full Changelog**: [v0.9.2...v1.0.0](https://github.com/EdmondVirelle/cyber-qin/compare/v0.9.2...v1.0.0)

