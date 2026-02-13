# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2024-02-13

### Added
- **Settings Dialog**: Centralized settings interface (`Ctrl+,`) for MIDI device selection and preferences
- **Key Mapping Viewer**: Read-only dialog showing complete MIDI-to-keyboard mapping table (accessible from Live Mode)
- **Enhanced MIDI Hot-plug**: Automatic device detection every 5 seconds with connection/disconnection logging
- **Loop Playback Mode**: Toggle loop in Library view and Sequencer (press `L` in Editor)
- **Metronome Count-in**: Optional 4-beat countdown before playback with visual indicator (press `M` in Editor to toggle)
- **Gold Accent Color**: New gold (#D4AF37) active state for loop/metronome buttons
- **Comprehensive Test Coverage**: 598 tests (3.3x increase from v0.9.0)
- **Multi-language Release Notes**: English, Traditional Chinese, and Simplified Chinese

### Changed
- **MIDI Device Priority**: Preferred device setting now correctly prioritized on startup
- **UI Contrast**: Improved text contrast in light mode for better accessibility
- **Module Count**: Expanded to 30 modules with clear separation of concerns
- **Codebase Size**: Grown to ~6,500 LOC with consistent coding standards

### Fixed
- **Loop Restart**: Loop mode now correctly resets playback position to beginning
- **Metronome Timing**: Countdown tick events synchronized with playback thread
- **Settings Persistence**: All settings now properly saved and restored across sessions
- **Device Selection**: Preferred MIDI device now correctly prioritized on startup

### Documentation
- Updated README.md with complete v1.0.0 feature documentation
- Updated README_TW.md (Traditional Chinese) with all new features
- Added comprehensive keyboard shortcut documentation
- Added detailed workflow guide for new users
- Updated architecture diagrams with current data flow

---

## [0.9.2] - 2024-01-15

### Added
- **Global Exception Handler**: Unhandled exceptions now show error dialog with full traceback
- **Robust Logging**: Comprehensive logging system for debugging and error tracking

### Fixed
- **Library Crash**: Fixed crash when loading certain MIDI files with malformed metadata
- **Test Artifacts**: Removed test artifacts and coverage reports from version control

---

## [0.9.1] - 2024-01-10

### Fixed
- **Import Sorting**: Corrected import order and mypy ignore placement for strict compliance
- **Type Checking**: Fixed mypy issues across multiple modules

---

## [0.9.0] - 2024-01-05

### Added
- **MIDI Editor (Sequencer)**: Fully functional piano roll editor with note drawing, selection, and deletion
- **Multi-track Export**: Support for Type 1 multi-track MIDI file export
- **Playback Cursor**: Smooth 30ms refresh cursor with dynamic glow feedback
- **Keyboard Shortcuts**: Full hotkey support with built-in help dialog
- **Library Management**: Sort by Name/BPM/Notes/Duration with search functionality
- **Spotify-style Now Playing Bar**: Bottom transport bar with mini-piano, progress seek, and speed control
- **Dynamic Piano Visualization**: Real-time key state visualization with neon glow animations
- **Multi-language Support**: Traditional Chinese / Simplified Chinese / English / Japanese / Korean
- **賽博墨韻 Theme**: Custom dark theme with Neon Cyan (#00F0FF) accents

### Changed
- **Window Size**: Increased minimum size to 1400x900 for better 88-key editor visibility
- **Test Coverage**: 180 comprehensive unit and integration tests

---

## [0.8.0] - 2023-12-20

### Added
- **MIDI Playback**: Automatic MIDI file playback with speed control (0.25x - 2.0x)
- **4-Beat Countdown**: Pre-playback countdown to allow switching to game window
- **Progress Seek Bar**: Jump to any position in the track
- **Drag & Drop Import**: Easy MIDI file import into library

### Changed
- **Performance**: Optimized playback engine for smoother performance

---

## [0.7.0] - 2023-12-10

### Added
- **Live Mode Recorder**: Record live performances directly in Live Mode
- **Watchdog System**: Automatically releases keys stuck for more than 10 seconds
- **Auto Reconnect**: Detects and reconnects MIDI devices every 3 seconds if disconnected
- **Log Viewer**: Real-time logging panel in Live Mode

---

## [0.6.0] - 2023-12-01

### Added
- **5 Mapping Schemes**:
  - WWM 36-Key (Where Winds Meet)
  - FF14 37-Key (Final Fantasy XIV)
  - Generic 24-Key
  - Generic 48-Key
  - Generic 88-Key
- **Smart Preprocessing**: Auto Transpose → Octave Folding → Collision Deduplication
- **Scheme Switching**: On-the-fly scheme changes without restart

---

## [0.5.0] - 2023-11-20

### Added
- **Real-time MIDI Mapping**: Direct MIDI-to-SendInput injection on rtmidi C++ thread
- **< 2ms Latency**: Optimized for real-time game performance
- **DirectInput Scan Codes**: Proper keyboard simulation using scan codes instead of virtual key codes
- **Thread Priority**: Automatic real-time thread priority for callback thread

---

## [0.1.0] - 2023-11-01

### Added
- Initial release
- Basic MIDI input listening
- Simple keyboard simulation for WWM 36-key layout
- Windows SendInput integration

---

[1.0.0]: https://github.com/EdmondVirelle/cyber-qin/compare/v0.9.2...v1.0.0
[0.9.2]: https://github.com/EdmondVirelle/cyber-qin/compare/v0.9.1...v0.9.2
[0.9.1]: https://github.com/EdmondVirelle/cyber-qin/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/EdmondVirelle/cyber-qin/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/EdmondVirelle/cyber-qin/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/EdmondVirelle/cyber-qin/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/EdmondVirelle/cyber-qin/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/EdmondVirelle/cyber-qin/compare/v0.1.0...v0.5.0
[0.1.0]: https://github.com/EdmondVirelle/cyber-qin/releases/tag/v0.1.0

