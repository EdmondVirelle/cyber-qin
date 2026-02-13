# Release Notes — v1.0.0

**Release Date**: 2024-02-13
**Milestone**: First Stable Release

---

## 🎉 Highlights

**Cyber Qin** v1.0.0 marks the first stable release of the real-time MIDI-to-keyboard mapping tool for games. This release brings a complete feature set for live performance, MIDI playback, and editing, along with comprehensive UI improvements and user-requested enhancements.

---

## ✨ New Features

### Settings Dialog
- **Centralized Configuration** (`Ctrl+,`): Manage all application settings in one place
- **MIDI Device Selection**: Set preferred MIDI device with automatic prioritization on startup
- **Persistent Preferences**: Settings saved automatically and restored across sessions

### Key Mapping Viewer
- **Read-only Mapping Table**: View complete MIDI-to-keyboard mapping for current scheme
- **4-Column Display**: MIDI Note, Note Name, Keyboard Key, Modifier
- **Accessible from Live Mode**: "View Mapping" button for quick reference

### Enhanced MIDI Hot-plug Support
- **Automatic Device Detection**: Scans for new/removed devices every 5 seconds when disconnected
- **Change Logging**: Logs device connection/disconnection events in real-time
- **Seamless Reconnection**: Automatically connects to preferred device when detected

### Loop Playback Mode
- **Library Loop Toggle**: Enable loop mode for continuous playback in Library view
- **Editor Loop Toggle**: Press `L` in Sequencer to toggle loop during editing
- **Gold Accent Indicator**: Active loop button shows gold (#D4AF37) background

### Metronome Count-in
- **Optional 4-Beat Countdown**: Toggle metronome on/off before playback
- **Visual Countdown Indicator**: Large gold numbers (4→3→2→1) displayed on screen
- **Editor Shortcut**: Press `M` in Sequencer to toggle metronome
- **Enabled by Default**: Ensures smooth transition to game window

---

## 🔧 Improvements

### Code Quality
- **598 Tests**: Comprehensive test coverage (3.3x increase from v0.9.0)
- **30 Modules**: Modular architecture with clear separation of concerns
- **~6,500 LOC**: Well-organized codebase with consistent coding standards
- **Type Hints**: Full static type checking with mypy compliance

### Documentation
- **Updated README**: Complete v1.0.0 feature documentation in English and Traditional Chinese
- **Keyboard Shortcuts**: Comprehensive shortcut documentation for all views
- **Workflow Guide**: Step-by-step usage instructions for new users
- **Architecture Diagrams**: Clear data flow visualization for developers

### UI/UX
- **賽博墨韻 Theme**: Consistent dark theme with Neon Cyan (#00F0FF) accents
- **Gold Active States**: New gold (#D4AF37) color for active buttons (loop, metronome)
- **Improved Contrast**: Better text contrast in light mode for accessibility
- **Checkable Buttons**: Visual feedback for toggle states (loop/metronome)

---

## 🐛 Bug Fixes

- **Fixed MIDI Device Selection**: Preferred device now correctly prioritized on startup
- **Fixed Loop Restart**: Loop mode now correctly resets playback position to beginning
- **Fixed Metronome Timing**: Countdown tick events synchronized with playback thread
- **Fixed Settings Persistence**: All settings now properly saved and restored

---

## 📦 Technical Details

### Dependencies
- Python 3.11 / 3.12 / 3.13
- PyQt6 6.8.1
- mido 1.3.4
- python-rtmidi 1.5.9
- pytest 8.3.5

### Platform Support
- Windows 10 / 11 (x64)
- Requires Administrator privileges for SendInput

### Build
- PyInstaller bundled executable: `dist/賽博琴仙/` (~95 MB)
- Single-folder distribution with all dependencies included

---

## 🚀 Upgrade Guide

### From v0.9.x to v1.0.0

1. **Backup Your Data**: Export any custom MIDI projects from Library
2. **Uninstall Previous Version**: Remove old executable or Python installation
3. **Install v1.0.0**: Download and extract new version
4. **Configure Settings**: Press `Ctrl+,` to set preferred MIDI device
5. **Verify Mapping**: Click "View Mapping" to confirm correct key layout

### Breaking Changes
- **None**: v1.0.0 is fully backward compatible with v0.9.x project files

---

## 🙏 Acknowledgments

Special thanks to:
- All users who provided feedback during the v0.9.x beta period
- Contributors who reported issues and suggested enhancements
- The open-source MIDI and PyQt communities

---

## 📝 Known Issues

- **Windows Defender**: May flag executable as unrecognized app (click "More info" → "Run anyway")
- **Input Method Editors**: Some IME software may interfere with key injection (see FAQ)
- **High DPI Displays**: UI scaling may not be perfect on 4K monitors (workaround: set Windows scaling to 150%)

For full issue tracker, see: https://github.com/EdmondVirelle/cyber-qin/issues

---

## 🔮 What's Next

Planned for v1.1.0:
- Cloud save/sync for MIDI library
- MIDI input monitoring graph
- Custom key mapping editor
- Multi-language localization improvements

---

**Full Changelog**: https://github.com/EdmondVirelle/cyber-qin/compare/v0.9.2...v1.0.0
**Download**: https://github.com/EdmondVirelle/cyber-qin/releases/tag/v1.0.0

