# Cyber Qin (賽博琴仙)

**Play a real piano, and your game character plays in sync.**

[![CI](https://github.com/EdmondVirelle/cyber-qin/actions/workflows/ci.yml/badge.svg)](https://github.com/EdmondVirelle/cyber-qin/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![Version](https://img.shields.io/badge/Version-2.3.1-green)
![Tests](https://img.shields.io/badge/Tests-1241%20passed-brightgreen)

[中文版 (Traditional Chinese)](README_TW.md)

---

## Table of Contents

- [Introduction](#introduction)
- [Quick Start](#quick-start)
- [Download & Installation](#download--installation)
- [Feature Guide](#feature-guide)
  - [Live Mode](#1-live-mode-即時演奏)
  - [Library](#2-library-曲庫)
  - [Sequencer](#3-sequencer-編曲器)
  - [Practice Mode](#4-practice-mode-練習模式)
- [Mapping Schemes](#mapping-schemes)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Settings & Configuration](#settings--configuration)
- [Smart Preprocessing Pipeline](#smart-preprocessing-pipeline)
- [MIDI Effects (FX)](#midi-effects-fx)
- [AI Melody Generator](#ai-melody-generator)
- [Multi-Format I/O](#multi-format-io)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Tech Stack](#tech-stack)
- [Acknowledgments](#acknowledgments)
- [Disclaimer](#disclaimer)

---

## Introduction

**Cyber Qin** is a professional-grade, real-time MIDI-to-Keyboard mapping tool designed for in-game music performance. It converts USB MIDI keyboard signals into DirectInput scan codes with **< 2ms latency**, enabling your game character to perform in perfect sync with your real-world playing.

What started as a simple key mapper has evolved into a full **digital music workstation** — featuring a multi-track MIDI editor, intelligent arrangement algorithms, MIDI effects processing, AI-assisted composition, rhythm-game-style practice mode, and multi-format import/export.

### Supported Games

| Game | Keys | Scheme |
|------|------|--------|
| **Where Winds Meet** (燕雲十六聲) | 36 | `wwm_36` |
| **Final Fantasy XIV** | 37 | `ff14_37` |
| **Other Games** | 24 / 48 / 88 | `generic_24` / `generic_48` / `generic_88` |

### Languages

The entire UI supports 5 languages, switchable at any time via the bottom-left language selector:

- English
- 繁體中文 (Traditional Chinese)
- 简体中文 (Simplified Chinese)
- 日本語 (Japanese)
- 한국어 (Korean)

---

## Quick Start

1. **Download** the latest release ZIP from [GitHub Releases](https://github.com/EdmondVirelle/cyber-qin/releases)
2. **Extract** using [7-Zip](https://www.7-zip.org/) (Windows built-in extractor may fail on Unicode paths)
3. **Run** `賽博琴仙.exe` — it will automatically request Administrator privileges
4. **Connect** your USB MIDI keyboard
5. **Select** your MIDI device in the Live Mode dropdown
6. **Choose** the mapping scheme for your game (e.g., "燕雲十六聲 36鍵")
7. **Switch** to your game window and play

> **Important**: The application **must** run as Administrator. Without elevated privileges, `SendInput` (the Windows API used for key injection) silently fails — your MIDI keyboard will appear to work in the app, but no keys will be sent to the game. The packaged `.exe` automatically requests UAC elevation.

---

## Download & Installation

### Option A: Pre-built Executable (Recommended)

1. Go to [GitHub Releases](https://github.com/EdmondVirelle/cyber-qin/releases)
2. Download the latest `賽博琴仙-v*.zip`
3. **Extract with 7-Zip** — the Windows built-in extractor often fails because the folder name `賽博琴仙` contains CJK characters. 7-Zip handles Unicode paths correctly.
4. Run `賽博琴仙.exe`

> **Windows Defender may flag the executable** because it lacks a commercial code certificate. This is a false positive. You can add the folder to Windows Defender exclusions, or build from source.

### Option B: From Source

#### System Requirements

- **OS**: Windows 10 / 11 (64-bit)
- **Python**: 3.11, 3.12, or 3.13
- **MIDI Device**: Any USB MIDI keyboard (tested with Roland FP-30X)
- **Privileges**: Administrator (for `SendInput`)

> **Do NOT use Python 3.14 alpha** — PyQt6 fatally crashes on import with "Unable to embed qt.conf". This is a known PyQt6 incompatibility.

#### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/EdmondVirelle/cyber-qin.git
cd cyber-qin

# 2. Create virtual environment (Python 3.11 recommended)
python -m venv .venv
.venv\Scripts\activate

# 3. Install with development dependencies
pip install -e .[dev]

# 4. Run (must be in an Administrator terminal)
cyber-qin
# or: python -m cyber_qin
```

### Option C: Build Executable from Source

```bash
# One-click build script (auto-detects Python 3.13, creates venv, packages)
python scripts/build.py

# Output: dist/賽博琴仙/賽博琴仙.exe (~95 MB)
```

The build script will:
1. Find Python 3.13 on your system
2. Create a `.venv313/` virtual environment
3. Install all dependencies
4. Generate the application icon
5. Run PyInstaller
6. Optionally sign the executable with a self-signed certificate

> **Packaging requires Python 3.13 specifically** — not 3.11 or 3.12. This is because the PyInstaller spec is configured for 3.13 compatibility.

---

## Feature Guide

### 1. Live Mode (即時演奏)

Live Mode is the core feature — real-time MIDI-to-keyboard conversion with sub-2ms latency.

#### How It Works

```
MIDI Keyboard → USB → python-rtmidi (C++ thread) → KeyMapper → SendInput (scan codes) → Game
```

The key injection happens **directly on the rtmidi callback thread** (not through Qt's event queue), which is critical for achieving < 2ms latency. Routing through Qt signals would add ~20ms.

#### Controls

| Control | Description |
|---------|-------------|
| **MIDI Device** dropdown | Select your connected MIDI keyboard. Refreshes automatically every 5 seconds. |
| **Mapping Scheme** dropdown | Choose the key layout for your game (see [Mapping Schemes](#mapping-schemes)). |
| **Transpose** spinner | Shift all notes up/down by semitones. Useful when a song is in a key that extends beyond the game's range. |
| **View Mapping** button | Opens a read-only dialog showing the complete MIDI note → keyboard key mapping table. |
| **Auto-Tune** toggle | Enable post-recording quantization and pitch correction. |

#### Where You Might Get Stuck

- **"I connected my MIDI keyboard but nothing happens in the game"**
  - Check if you're running as Administrator. Without it, `SendInput` silently fails.
  - Check the scheme — if your game uses 36 keys but you selected 88-key, out-of-range notes won't map.
  - Make sure the game window is focused when you play. `SendInput` sends to the foreground window.

- **"Some notes don't trigger in the game"**
  - Those notes are outside the mapping scheme's MIDI range. Use **Transpose** to shift them into range, or enable Smart Preprocessing (which auto-transposes).
  - Check if your keyboard's IME (Input Method Editor) is active — Chinese/Japanese IME can intercept key events. The app detects this and shows a warning.

- **"There's noticeable delay"**
  - Close any DAW software that might be holding the MIDI port.
  - Ensure you're using a **USB** connection, not Bluetooth MIDI (which adds ~10-20ms latency).

#### Automatic Features

| Feature | Behavior |
|---------|----------|
| **Hot-plug detection** | Scans for new/removed MIDI devices every 5 seconds and logs changes. |
| **Auto-reconnect** | If your MIDI device disconnects, the app tries to reconnect every 3 seconds. |
| **Stuck-key watchdog** | If a key is held for more than 10 seconds (likely a stuck note), it's automatically released. |
| **Preferred device** | Set in Settings (`Ctrl+,`). The app connects to this device first on startup. |

#### 88-Key Piano Display

The bottom of Live Mode shows a real-time 88-key piano visualization. Active notes glow with the scheme's color. This helps you verify that MIDI input is being received correctly even before switching to the game.

---

### 2. Library (曲庫)

The Library manages your MIDI file collection and provides automatic playback.

#### Importing MIDI Files

- Click the **Import** button, or **drag and drop** `.mid` / `.midi` files into the library
- Files are parsed immediately — metadata (BPM, duration, note count, tracks) is extracted and displayed
- The library remembers your last import directory

#### Track List

Each track shows:
- **Name** (from filename or MIDI metadata)
- **BPM** (detected from MIDI tempo events)
- **Note count**
- **Duration**

**Sorting**: Click column headers to sort by Name / BPM / Notes / Duration. Toggle ascending/descending.

**Search**: Type in the search bar to filter tracks by name.

#### Playback Controls

| Control | Description |
|---------|-------------|
| **Play / Pause / Stop** | Standard transport controls. |
| **Speed** slider | 0.25x to 2.0x playback speed. The slider is in the bottom Now Playing Bar. |
| **Loop** toggle | Repeat the current track indefinitely. |
| **Metronome Count-in** | Optional 4-beat countdown before playback starts. Gives you time to switch to the game window. |
| **Seek bar** | Drag to jump to any position in the track. |

#### Right-Click Context Menu

Right-clicking a track in the library offers:
- **Play** — Start playback
- **Edit in Sequencer** — Open in the MIDI editor
- **Practice** — Load into Practice Mode
- **Metadata** — View detailed MIDI file information
- **Remove** — Remove from library (does not delete the file)

#### Where You Might Get Stuck

- **"Playback is too fast/slow"**
  - Check the speed slider in the Now Playing Bar (bottom of the window). It may be set to something other than 1.0x.

- **"Some notes are missing during playback"**
  - The Smart Preprocessing pipeline automatically transposes and folds notes into the scheme's range. Notes that absolutely cannot be mapped are silently dropped. Check the preprocessing stats in the log viewer.

- **"I hear audio from my speakers but the game doesn't respond"**
  - Audio preview (via Windows GS Wavetable Synth) is separate from key injection. Make sure the game window is focused during playback.

---

### 3. Sequencer (編曲器)

A full piano-roll MIDI editor for creating and editing musical arrangements.

#### Editor Layout

```
┌──────────────────────────────────────────────────────────┐
│ Toolbar: [New] [Open] [Save] [Undo] [Redo] [FX] [Gen]   │
│          [Play] [Stop] [Loop] [Metro] [Speed]            │
├────────┬─────────────────────────────────────────────────┤
│ Pitch  │            Piano Roll                           │
│ Ruler  │  ┌──────────────────────────────────────────┐   │
│ (C0-C8)│  │  ████  ██  ████████████  ██ ██          │   │
│        │  │      ██████      ████        ██████      │   │
│        │  │  ██  ██    ████  ██  ████    ██          │   │
│        │  └──────────────────────────────────────────┘   │
├────────┴─────────────────────────────────────────────────┤
│ Track Panel: [Track 1 ♪] [Track 2 ♪] [Track 3 ♪] [+]   │
└──────────────────────────────────────────────────────────┘
```

#### Editing Operations

| Action | How |
|--------|-----|
| **Draw note** | Click on the piano roll at the desired position and pitch |
| **Select notes** | Click a note, or drag to select multiple |
| **Move notes** | Drag selected notes to a new position |
| **Resize notes** | Drag the right edge of a note to change duration |
| **Delete notes** | Select and press `Delete`, or right-click → Delete |
| **Undo / Redo** | `Ctrl+Z` / `Ctrl+Y` (up to 100 levels) |

#### Multi-Track Support

- Create up to 12 tracks, each with its own color and MIDI channel
- **Mute** / **Solo** individual tracks
- Track colors are from a predefined Cyber-Ink palette (12 colors)
- Export as Type 1 (multi-track) MIDI file

#### Ghost Notes

After running Smart Arrangement, the original note positions are shown as semi-transparent "ghost notes" in coral red. This helps you see what the arrangement algorithm changed. Toggle with the **Ghost** button, and adjust transparency with the slider.

#### Automation Lanes

Draw automation curves for **velocity** and **tempo**:
- Click to add control points
- Drag points to adjust values
- Double-click to delete a point
- Linear interpolation between points
- Syncs horizontally with the piano roll

#### Where You Might Get Stuck

- **"I can't hear anything when I press Play"**
  - The editor plays through the system MIDI synthesizer (Windows GS Wavetable Synth). Make sure your system audio is not muted. If no MIDI output port is available, playback is silent but the cursor still moves.

- **"Undo doesn't seem to work"**
  - Undo has a maximum of 100 levels. Each operation is recorded with a description (visible in the status bar). If you've performed more than 100 operations, the earliest ones are discarded.

- **"Exported MIDI file sounds different in my DAW"**
  - The editor exports standard Type 1 MIDI. However, the Smart Arrangement pipeline may have transposed or folded notes. Export the raw (unarranged) version if you need the original pitches.

---

### 4. Practice Mode (練習模式)

A rhythm-game-style practice system where notes fall from above, and you press the correct key when they reach the judgment line.

#### How to Enter Practice Mode

**Option A**: Click "Practice" (練習) in the sidebar → use the built-in song picker:
- Click **"Open MIDI File..."** to load any `.mid` file
- Or select from your **Library tracks** (displayed below the open button)

**Option B**: Right-click a track in the Library → select **"Practice"**

#### Gameplay

```
     ↓ ↓ ↓ ↓ ↓     (Notes falling)
     ↓ ↓ ↓ ↓ ↓
═══════════════════  (Gold judgment line)
     PERFECT!        (Hit feedback)
```

Notes fall from the top of the screen at a speed proportional to the track's tempo. When a note reaches the gold line, press the corresponding key on your MIDI keyboard (or use keyboard input mode).

#### Scoring

| Grade | Timing Window | Points | Visual |
|-------|--------------|--------|--------|
| **PERFECT** | ±30 ms | 300 | Gold flash |
| **GREAT** | ±80 ms | 200 | Green flash |
| **GOOD** | ±150 ms | 100 | Blue flash |
| **MISS** | > ±150 ms | 0 | Red flash |

**Stats displayed**: Score, Accuracy %, Combo count, Max Combo

#### Input Modes

| Mode | Description |
|------|-------------|
| **MIDI** | Use your connected MIDI keyboard. Pitch must match exactly. |
| **Keyboard** | Use your computer keyboard. Keys map according to the selected scheme. |

#### Song Picker (Empty State)

When you first open Practice Mode, you see the **Song Picker** page:
- A music note icon and title "Select a Track"
- **"Open MIDI File..."** button — opens a file dialog
- **"Library Tracks"** section — shows all tracks from your Library as clickable cards
- Each card displays the track name, duration, and note count
- Click any card to immediately start practicing that track

After starting a practice session, click **"Change Track"** in the header to return to the song picker.

#### Where You Might Get Stuck

- **"I clicked a track card but nothing happened"**
  - This was a bug in v2.3.0 (fixed in v2.3.1). Update to the latest version.

- **"The notes fall too fast / too slow"**
  - Fall speed is tied to the track's BPM. There is currently no manual speed override in Practice Mode — use the Library's speed control to play at a different speed, then switch to Practice.

- **"Library tracks section shows 'Library is empty'"**
  - Import MIDI files in the Library tab first. The practice mode song picker mirrors the Library's track list.

---

## Mapping Schemes

Five built-in schemes cover different games and key counts:

### WWM 36-Key (燕雲十六聲)

| Row | Modifier | Keys | MIDI Range |
|-----|----------|------|------------|
| Bottom | None | Z X C V B N M , . / ; ' | C3 – B3 |
| Middle | None | A S D F G H J K L | C4 – B4 |
| Top | None | Q W E R T Y U I O P [ ] | C5 – B5 |

Accidentals (sharps/flats) use **Shift** and **Ctrl** modifiers combined with the same keys.

### FF14 37-Key

Diatonic layout optimized for Final Fantasy XIV's bard performance system. Uses number row, QWER row, and ASDF row. Ctrl modifier for accidentals.

### Generic 24 / 48 / 88-Key

Scalable layouts for other games or general use. The 88-key scheme covers the full piano range (A0–C8) using 8 layers of Shift/Ctrl modifier combinations.

#### Switching Schemes

Select the scheme from the dropdown in Live Mode or the Sequencer toolbar. The scheme affects:
- Which MIDI notes map to which keyboard keys
- The highlighted range on the piano display
- The preprocessing pipeline's target range

---

## Keyboard Shortcuts

### Global

| Shortcut | Action |
|----------|--------|
| `Ctrl+,` | Open Settings dialog |
| `Ctrl+Q` | Quit application |

### Sequencer

| Shortcut | Action |
|----------|--------|
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+S` | Save project |
| `Ctrl+O` | Open project |
| `Ctrl+N` | New project |
| `Space` | Play / Pause |
| `Escape` | Stop |
| `L` | Toggle loop |
| `M` | Toggle metronome count-in |
| `Delete` | Delete selected notes |
| `Ctrl+A` | Select all notes |
| `Ctrl+E` | Export MIDI |

### Library

| Shortcut | Action |
|----------|--------|
| `Space` | Play / Pause selected track |
| `Escape` | Stop playback |

---

## Settings & Configuration

Open Settings with `Ctrl+,` or via the sidebar gear icon.

### MIDI Tab

| Setting | Description | Gotcha |
|---------|-------------|--------|
| **Preferred Device** | Auto-connect to this device on startup | Must match the exact device name as shown in the dropdown |
| **Auto-Connect** | Automatically connect when preferred device is found | Disable if you have multiple MIDI devices and want manual control |

### Playback Tab

| Setting | Description |
|---------|-------------|
| **Default Scheme** | Which mapping scheme to use by default |
| **Default Transpose** | Semitone offset applied to all playback |

### Editor Tab

| Setting | Description |
|---------|-------------|
| **Snap to Grid** | Enable/disable note snapping in the piano roll |
| **Grid Subdivision** | 1/4, 1/8, 1/16 note grid |
| **Auto-save** | Automatically save editor state periodically |
| **Auto-save Interval** | How often to auto-save (default: 60 seconds) |

### UI Tab

| Setting | Description |
|---------|-------------|
| **Language** | UI language (auto-detect or manual selection) |
| **Theme** | Currently only "Cyber Ink" (dark theme) |

### Configuration File

Settings are stored as JSON at `%USERPROFILE%\.cyber_qin\config.json`. This file is human-readable and can be edited manually if needed.

Auto-save data is stored at `%USERPROFILE%\.cyber_qin\autosave.cqp` (gzip-compressed JSON).

---

## Smart Preprocessing Pipeline

When a MIDI file is loaded for playback, it passes through a 9-stage preprocessing pipeline:

| Stage | What It Does | Why |
|-------|-------------|-----|
| 1. **Percussion Filter** | Removes GM channel 10 (drums) | Games don't have drum keys |
| 2. **Track Filter** | Keeps only selected tracks | Focus on melody, skip accompaniment |
| 3. **Octave Deduplication** | Same pitch class at same time → keep highest | Reduces redundant keypresses |
| 4. **Smart Global Transpose** | Auto ±12 semitone shifts | Maximizes notes within the scheme's range |
| 5. **Flowing Fold** (流水摺疊) | Voice-leading-aware octave transposition | Avoids jarring octave jumps; uses exponential moving average as "gravity center" |
| 6. **Collision Dedup** | Velocity-priority duplicate removal | Prevents double-triggering same key |
| 7. **Polyphony Limiter** | Cap simultaneous notes | Some games limit polyphony |
| 8. **Velocity Normalization** | All velocities → 127 | Games don't respond to velocity |
| 9. **Time Quantization** | Snap to 60 FPS grid (~16.67ms) | Align with game's input polling rate |

After preprocessing, a `PreprocessStats` summary is available showing how many notes were shifted, removed, or folded.

---

## MIDI Effects (FX)

The Sequencer includes four real-time MIDI effects, accessible via the **FX** button in the toolbar:

### Arpeggiator

Breaks chords into sequential note patterns.

| Parameter | Options |
|-----------|---------|
| **Pattern** | Up, Down, Up-Down, Random |
| **Rate** | Note subdivision (1/4, 1/8, 1/16) |
| **Octave Range** | How many octaves to span |

### Humanize

Adds subtle random variation to simulate human performance.

| Parameter | Range |
|-----------|-------|
| **Timing Jitter** | 0–50 ms random offset |
| **Velocity Jitter** | 0–30 random velocity variation |
| **Seed** | Deterministic randomness for reproducible results |

### Quantize

Snaps notes to the nearest beat grid position.

| Parameter | Options |
|-----------|---------|
| **Grid** | Quarter, Eighth, Sixteenth, Triplet 8th |
| **Strength** | 0.0 (no change) – 1.0 (full snap) |

### Chord Generator

Generates chords from single notes.

| Parameter | Options |
|-----------|---------|
| **Chord Type** | Major, Minor, 7th, Maj7, Min7, Dim, Aug, Sus2, Sus4, Power |
| **Voicing** | Close, Spread, Drop-2 |

---

## AI Melody Generator

The **Generate** button in the Sequencer opens the Melody Generator dialog.

### Melody Generation

A rule-based generator using first-order Markov chains:

| Parameter | Options |
|-----------|---------|
| **Scale** | Major, Minor, Pentatonic, Blues, Dorian, Mixolydian, Phrygian, Lydian |
| **Key** | C through B |
| **Length** | Number of notes to generate |
| **Seed** | For reproducible output |

The generator produces melodies with:
- Stepwise motion preference (avoiding large jumps)
- Phrase structure with tonic/dominant resolution
- Contour shaping for musical coherence

### Bass Line Generation

Automatic bass lines based on chord progressions:

| Progression | Chords |
|-------------|--------|
| I-IV-V-I | Classic |
| I-V-vi-IV | Pop |
| I-vi-IV-V | 50s |
| ii-V-I | Jazz |

---

## Multi-Format I/O

### Import Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| **MIDI** | `.mid`, `.midi` | Standard MIDI file (Type 0 and Type 1) |
| **MusicXML** | `.musicxml`, `.xml` | Sheet music interchange format |
| **ABC Notation** | `.abc` | Text-based folk music notation |
| **LilyPond** | `.ly` | Typesetting music notation |

### Export Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| **MIDI** | `.mid` | Type 0 (single track) or Type 1 (multi-track) |
| **ABC Notation** | `.abc` | Text-based notation |
| **LilyPond** | `.ly` | For engraving with LilyPond |
| **WAV** | `.wav` | Audio render via system MIDI synthesizer |

---

## Architecture

### Data Flow — Live Mode

```
┌─────────────┐  USB   ┌──────────────┐  callback  ┌───────────┐  lookup  ┌──────────────┐  SendInput  ┌──────┐
│ MIDI Keyboard│───────→│ python-rtmidi│───────────→│ KeyMapper │─────────→│ KeySimulator │────────────→│ Game │
└─────────────┘        └──────────────┘             └───────────┘          └──────────────┘             └──────┘
                       (C++ rtmidi thread)                                  (scan codes)
```

### Data Flow — Playback

```
┌───────────┐  parse  ┌──────────────┐  preprocess  ┌──────────────────┐  timed events  ┌──────────────┐
│ .mid File │────────→│ MidiFileParser│────────────→│ MidiPreprocessor │──────────────→│ PlaybackWorker│
└───────────┘         └──────────────┘              └──────────────────┘               └──────┬───────┘
                                                                                              │
                                                          lookup + SendInput                   │
                                                  ┌───────────┬──────────────┐←──────────────┘
                                                  │ KeyMapper │ KeySimulator │→ Game
                                                  └───────────┴──────────────┘
```

### Module Structure

```
cyber_qin/
├── core/           # Pure logic (no Qt dependency) — testable without QApplication
│   ├── constants.py         # Scan codes, MIDI ranges, enums
│   ├── key_mapper.py        # MIDI note → keyboard key mapping
│   ├── key_simulator.py     # Win32 SendInput wrapper
│   ├── midi_listener.py     # Real-time MIDI device capture
│   ├── midi_file_player.py  # MIDI file parsing + playback
│   ├── midi_preprocessor.py # 9-stage event pipeline
│   ├── midi_fx.py           # 4 MIDI effects processors
│   ├── melody_generator.py  # AI melody + bass generation
│   ├── smart_arrangement.py # Auto-transpose + fold algorithms
│   ├── practice_engine.py   # Scoring system (Perfect/Great/Good/Miss)
│   ├── beat_sequence.py     # Beat-based timeline + EditorSequence
│   ├── translator.py        # 5-language i18n engine
│   ├── config.py            # JSON config persistence
│   └── ...                  # (18 core modules total)
├── gui/            # PyQt6 UI layer
│   ├── app_shell.py         # Main window + tab management
│   ├── theme.py             # Cyber-Ink dark theme (30+ colors)
│   ├── icons.py             # 21 vector icons (QPainter, no image files)
│   ├── views/               # Live Mode, Library, Editor, Practice
│   ├── widgets/             # Piano, sidebar, note roll, etc.
│   └── dialogs/             # Settings, FX, Melody Generator, etc.
└── utils/          # System utilities
    ├── admin.py             # UAC privilege check + elevation
    └── ime.py               # Input method detection (CJK warning)
```

### Design Principles

1. **Core/GUI Separation**: Everything in `core/` is pure Python with zero PyQt6 dependency, enabling unit testing without QApplication
2. **Lazy Qt Classes**: Modules that need both pure-Python and Qt classes use a factory pattern to defer Qt class definition until after QApplication exists (see `midi_file_player.py`)
3. **Thread Safety**: MIDI callbacks run on a C++ thread. Never touch Qt widgets from this thread — use `pyqtSignal` for cross-thread communication
4. **Scan Codes**: Uses DirectInput scan codes (`KEYEVENTF_SCANCODE`), not virtual key codes — required for games that bypass the Windows message queue

---

## Troubleshooting

### Installation Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| `import PyQt6.QtCore` crashes with "Unable to embed qt.conf" | Python 3.14 alpha | Use Python 3.11, 3.12, or 3.13 |
| `pip install` fails for `python-rtmidi` | Missing C++ build tools | Install [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| Extraction fails with garbled folder name | Windows Explorer can't handle Unicode ZIP paths | Use [7-Zip](https://www.7-zip.org/) to extract |

### Runtime Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Keys don't work in game | Not running as Administrator | Right-click → "Run as administrator", or check UAC elevation dialog |
| Keys don't work in game (with admin) | Game uses anti-cheat that blocks SendInput | This is a limitation; some anti-cheat systems block all external input |
| MIDI device not listed | Device in use by another app | Close your DAW or other MIDI software |
| MIDI device not listed | Driver issue | Reconnect USB, check Device Manager |
| High latency (> 10ms) | Using Bluetooth MIDI adapter | Switch to USB connection |
| High latency (> 10ms) | Running through a VM | Run natively on Windows |
| Some notes trigger wrong keys | Wrong mapping scheme selected | Match the scheme to your game |
| Chinese/Japanese IME warning | Active IME intercepting key events | Switch IME to English mode while playing |
| `SendInput` returns 0 | ctypes INPUT struct size mismatch | This is a build bug — please report it. The INPUT struct must be exactly 40 bytes. |

### Editor Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| No sound during editor playback | No MIDI output port | Windows GS Wavetable Synth should be available by default. Check audio settings. |
| Notes sound but cursor doesn't move | Playback thread timing issue | Stop and restart playback |
| Auto-save not working | Config issue | Check `~/.cyber_qin/config.json`, ensure `editor.auto_save` is `true` |

### Practice Mode Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Track card click does nothing | v2.3.0 bug (fixed in v2.3.1) | Update to latest version |
| "Library is empty" in song picker | No tracks imported | Import MIDI files in the Library tab first |
| Wrong pitch grading | MIDI keyboard octave offset | Adjust your keyboard's octave setting to match |

---

## Development

### Running Tests

```bash
# All 1241 tests
pytest

# Verbose output
pytest -v

# With coverage
pytest --cov=cyber_qin --cov-report=html

# Unit tests only (skip integration + GUI)
pytest -m "not integration and not gui"

# Single test file
pytest tests/test_practice_view.py -v
```

### Linting

```bash
ruff check .
ruff check --fix .
ruff format --check .
```

### Type Checking

```bash
mypy cyber_qin --install-types --non-interactive
```

### Project Statistics

| Metric | Value |
|--------|-------|
| Version | 2.3.1 |
| Lines of Code | ~12,750+ LOC |
| Python Modules | 58 |
| Tests | 1,241 |
| Test Files | 25 |
| Coverage | > 85% |
| Python Support | 3.11 / 3.12 / 3.13 |
| Languages | 5 (en, zh_TW, zh_CN, ja, ko) |
| i18n Keys | 300+ |

### CI/CD

- **CI** (`.github/workflows/ci.yml`): Runs on every push/PR to `main`
  - Test matrix: 3 OS (Ubuntu, Windows, macOS) x 3 Python versions (3.11, 3.12, 3.13)
  - Lint + format check (Ruff)
  - i18n completeness check
  - Type check (mypy)
  - Build artifact (Windows only, on main branch)

- **Release** (`.github/workflows/release.yml`): Triggered by tag push (`v*`)
  - Builds Windows executable with PyInstaller
  - Creates GitHub Release with ZIP download

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for detailed code style, testing, and contribution workflow guidelines.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **MIDI I/O** | `mido` + `python-rtmidi` | USB device communication, MIDI file parsing |
| **Key Injection** | `ctypes` + Win32 `SendInput` | DirectInput scan code injection (< 2ms) |
| **GUI** | PyQt6 | Desktop interface, event loop, cross-thread signals |
| **Theme** | Custom QSS + QPainter | "Cyber Ink" dark theme, 21 vector icons, 30+ colors |
| **Bundling** | PyInstaller | Single-folder executable (~95 MB) |
| **CI/CD** | GitHub Actions | 9-job test matrix + automated release |
| **Linting** | Ruff | Ultra-fast Python linter (99-char line width) |
| **Testing** | pytest + pytest-qt | 1,241 unit / integration / GUI tests |
| **Type Check** | mypy | Gradual type adoption |

---

## Acknowledgments

- [mido](https://github.com/mido/mido) — Python MIDI library
- [python-rtmidi](https://github.com/SpotlightKid/python-rtmidi) — Low-latency cross-platform MIDI I/O
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — Python Qt 6 bindings
- [PyInstaller](https://pyinstaller.org/) — Python application packaging tool
- [Ruff](https://github.com/astral-sh/ruff) — Extremely fast Python linter
- *Where Winds Meet* — 燕雲十六聲 (Everstone Studio / NetEase)
- *Final Fantasy XIV* — FF14 (Square Enix)

---

## Disclaimer

This tool is an open-source personal project for MIDI music performance enthusiasts.
Using third-party tools in games may violate the game's Terms of Service. Please use at your own risk.
The developer is not responsible for any account penalties or losses resulting from the use of this tool.

---

**Sponsor**: [Ko-fi](https://ko-fi.com/virelleedmond)
