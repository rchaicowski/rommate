# RomMate

**Your ROM companion** - Convert, compress, verify, and organize disc images and cartridge ROMs.

---

## Features

### Disc-Based Systems
- **CHD Conversion** - Convert CUE, GDI, CDI, ISO to compressed CHD format (40-60% space savings)
- **CHD Extraction** - Extract CHD files back to their original format (CUE/BIN, ISO)
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

## Installation

### Windows
1. Download `RomMate.exe` from the [Releases](https://github.com/rchaicowski/rommate/releases) page
2. Double-click and run — no installation needed

> **Note:** Windows may show a "Windows protected your PC" SmartScreen warning, since RomMate isn't code-signed. This is expected for open-source apps without a paid certificate. Click **"More info" → "Run anyway"** to proceed. You can verify your download against the SHA256 checksum listed on the release page.

### Linux
1. Download `RomMate-x86_64.AppImage` from the [Releases](https://github.com/rchaicowski/rommate/releases) page
2. Double-click and run — no installation needed

> **Note:** Some newer distros (Arch, CachyOS, Fedora, etc.) don't ship `libfuse2` by default, which AppImages need to run. If you see a `libfuse.so.2` error, install it first:
> - Arch/CachyOS: `sudo pacman -S fuse2`
> - Fedora: `sudo dnf install fuse-libs`
> - Debian/Ubuntu: `sudo apt install libfuse2`
>
> Alternatively, run without FUSE by extracting the AppImage: `./RomMate-x86_64.AppImage --appimage-extract && ./squashfs-root/AppRun`

### Run from source (developers)
```bash
# Prerequisites
sudo apt install python3 python3-tk  # Linux only
pip install tkinterdnd2 customtkinter

git clone https://github.com/rchaicowski/rommate.git
cd rommate
python3 rommate.py
```

---

## Usage

### Quick Start

1. **Launch RomMate**
2. **Select a folder** containing your ROMs or disc images
3. **Choose an operation:**
   - Convert to CHD
   - Extract CHD to original format
   - Create M3U playlists
   - Check ROM health
   - Validate & fix ROM names
4. **Click Start** and let RomMate do the work!

### Settings

Access settings via the ⚙️ gear icon:
- Sound preferences
- Folder behavior (remember last / default)
- Conversion options
- Language (9 languages supported)

---

## Project Structure
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
│   ├── i18n.py                 # Internationalization
│   ├── sounds.py               # Sound playback
│   ├── theme.py                # UI theming
│   └── file_utils.py           # File operations
├── databases/
│   ├── no-intro/               # Cartridge ROM databases
│   └── redump/                 # Disc ROM databases
├── locales/                    # Translations (EN, PT, ES, FR, DE, IT, JA, ZH)
├── icon.png                        # App icon (Linux)
├── icon.ico                        # App icon (Windows)
└── sounds/                         # Sound effects
```

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the **GNU General Public License v3.0** (GPLv3).

See [LICENSE](LICENSE) file for full text.

### What this means:
- ✅ You can use, modify, and distribute this software
- ✅ You must keep the source code open
- ✅ You must license derivative works under GPLv3
- ✅ You must credit the original authors

---

## Credits & Attribution

### Tools & Libraries
- **[MAME chdman](https://www.mamedev.org/)** - CHD compression and verification
- **Python tkinter** - GUI framework
- **tkinterdnd2** - Drag and drop support
- **customtkinter** - Modern UI widgets (toggle switch)
- **pycaw** - Windows audio control

### Databases
- **[No-Intro](https://no-intro.org)** - Cartridge ROM databases
- **[Redump](http://redump.org)** - Optical disc databases

### Special Thanks
- The ROM preservation community
- MAME development team
- No-Intro and Redump projects

---

## Bug Reports & Feature Requests

Found a bug or have a feature idea?

- Open an issue on GitHub
- Include your OS, app version, and steps to reproduce

---

## Documentation

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

## Support

- **Issues:** [GitHub Issues](https://github.com/rchaicowski/rommate/issues)
- **Discussions:** [GitHub Discussions](https://github.com/rchaicowski/rommate/discussions)
- **Ko-fi:** [Support the project](https://ko-fi.com/rchaicowski)

---

**Made with ❤️ for the ROM preservation community**
