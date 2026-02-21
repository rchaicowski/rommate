# 🎮 RomMate

**Your ROM companion** - Convert, compress, verify, and organize disc images and cartridge ROMs.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## 🌟 Features

### Disc-Based Systems
- **CHD Conversion** - Convert CUE, GDI, CDI, ISO to compressed CHD format (40-60% space savings)
- **M3U Playlist Creation** - Automatically organize multi-disc games
- **CHD Verification** - Verify CHD file integrity with chdman
- **CUE/BIN Validation** - Check file structure and references

### Cartridge ROMs
- **ROM Health Check** - Verify ROMs against No-Intro/Redump databases
- **Multi-level Verification** - 5 confidence levels (100% to 80%)
- **ROM Hack Detection** - Identify translations and modifications
- **Header Detection** - Find external copier headers (SNES, NES)
- **Fuzzy Matching** - Smart filename and checksum comparison

### Supported Systems (26+)

**Cartridges:**
- Nintendo: NES, SNES, N64, GB, GBC, GBA, NDS, 3DS
- Sega: Genesis, Master System, Game Gear, 32X
- Atari: 2600, 5200

**Discs:**
- Sony: PS1, PS2, PS3, PSP
- Nintendo: GameCube, Wii
- Sega: Saturn, Dreamcast, Sega CD
- Microsoft: Xbox, Xbox 360
- SNK: Neo Geo CD

---

## 📸 Screenshots

*(Screenshots here when ready)*

---

## 🚀 Installation

### Prerequisites

**Linux:**
```bash
sudo apt install python3 python3-tk chdman
```

**Windows:**
```bash
# Install Python 3.8+ from python.org
# Download chdman from MAME website
```

### Install RomMate
```bash
git clone https://github.com/yourusername/rommate.git
cd rommate
python3 rommate.py
```

---

## 🎯 Usage

### Quick Start

1. **Launch RomMate**
```bash
   python3 rommate.py
```

2. **Select a folder** containing your ROMs/disc images

3. **Choose operation:**
   - Convert to CHD
   - Create M3U playlists
   - Check ROM health
   - Validate ROM names *(coming soon)*

4. **Click Start** and let RomMate do the work!

### Settings

Access settings via the ⚙️ gear icon:
- Sound preferences
- Folder behavior (remember last / default)
- Conversion options
- Language *(coming soon)*

---

## 🗂️ Project Structure
```
rommate/
├── core/
│   ├── chd_converter.py       # CHD conversion logic
│   ├── m3u_creator.py          # M3U playlist creation
│   ├── rom_health.py           # ROM verification
│   └── cartridge_checker.py    # Cartridge ROM validation
├── gui/
│   ├── main_window.py          # Main interface
│   ├── processing_panel.py     # Progress display
│   ├── completion_panel.py     # Results screen
│   └── settings_panel.py       # Settings interface
├── utils/
│   ├── config.py               # Configuration management
│   ├── sounds.py               # Sound playback
│   ├── theme.py                # UI theming
│   └── file_utils.py           # File operations
├── databases/
│   ├── no-intro/               # Cartridge ROM databases
│   └── redump/                 # Disc ROM databases
└── sounds/                     # Sound effects
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the **GNU General Public License v3.0** (GPLv3).

See [LICENSE](LICENSE) file for full text.

### What this means:
- ✅ You can use, modify, and distribute this software
- ✅ You must keep the source code open
- ✅ You must license derivative works under GPLv3
- ✅ You must credit the original authors

---

## 🙏 Credits & Attribution

### Tools & Libraries
- **[MAME chdman](https://www.mamedev.org/)** - CHD compression and verification
- **Python tkinter** - GUI framework
- **tkinterdnd2** - Drag and drop support
- **pycaw** - Windows audio control

### Databases
- **[No-Intro](https://no-intro.org)** - Cartridge ROM databases
- **[Redump](http://redump.org)** - Optical disc databases

### Special Thanks
- The ROM preservation community
- MAME development team
- No-Intro and Redump projects

---

## 🐛 Bug Reports & Feature Requests

Found a bug or have a feature idea?

- Open an issue on GitHub
- Include your OS, Python version, and steps to reproduce
- Screenshots are helpful!

---

## 📚 Documentation

### ROM Verification Confidence Levels

| Level | Confidence | Description |
|-------|-----------|-------------|
| ✅ Verified Good Dump | 100% | Exact checksum match with database |
| ✅ Probable Good Dump | 99% | 2/3 checksums match |
| 📝 Likely Match | 95% | Filename + size match |
| 🔍 Name Match | 80% | Filename similar, checksum differs |
| ❓ Unknown | N/A | Not in database |
| 🎨 ROM Hack | 90% | Modification/translation detected |
| ⚠️ Has Header | 100% | External header detected (fixable) |

---

## 🗺️ Roadmap

### Current Features
- [x] CHD conversion
- [x] M3U playlist creation
- [x] ROM health checking
- [x] Multi-level verification
- [x] ROM hack detection
- [x] Cross-platform support

### Planned Features
- [ ] ROM name validator/fixer
- [ ] Header removal tool
- [ ] Batch renaming
- [ ] Multi-language support
- [ ] Advanced filters
- [ ] Export reports (CSV, HTML)

---

## ⚡ Performance

- **CHD Conversion:** ~2-5 minutes per disc (PS1)
- **ROM Verification:** ~100 ROMs/second
- **Database Loading:** < 1 second (all 26 systems)

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/rommate/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/rommate/discussions)

---

## 📄 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Made with ❤️ for the ROM preservation community**
