import os
import re
from pathlib import Path

# === SETTINGS ===
GAME_FOLDER = "D:/FF/"  # Change this to your game folder
# =================

def extract_game_info(filename):
    """
    Extract game name and disc number from filename.
    Handles formats like:
    - Game Name (Disc 1).cue
    - Game Name (Disk 2).bin
    - Game Name - Disc 3.cue
    - Game Name [Disc 1].cue
    """
    # Remove file extension
    name_without_ext = os.path.splitext(filename)[0]

    # Patterns to match disc numbers
    patterns = [
        r'(.*?)[\s\-_]*\(Dis[ck]\s*(\d+)\)',  # (Disc 1) or (Disk 1)
        r'(.*?)[\s\-_]*\[Dis[ck]\s*(\d+)\]',  # [Disc 1] or [Disk 1]
        r'(.*?)[\s\-_]*Dis[ck]\s*(\d+)',      # Disc 1 or Disk 1 (no brackets)
    ]

    for pattern in patterns:
        match = re.match(pattern, name_without_ext, re.IGNORECASE)
        if match:
            game_name = match.group(1).strip()
            disc_num = int(match.group(2))
            return game_name, disc_num

    return None, None


def find_multidisc_games(folder):
    """
    Scan folder for multi-disc games and group them.
    Returns a dictionary: {game_name: [list of disc files]}
    """
    games = {}

    # Look for .cue files (primary format for disc games)
    cue_files = list(Path(folder).glob("*.cue"))

    for cue_file in cue_files:
        filename = cue_file.name
        game_name, disc_num = extract_game_info(filename)

        if game_name and disc_num:
            if game_name not in games:
                games[game_name] = []
            games[game_name].append((disc_num, filename))

    # Filter only games with multiple discs
    multidisc_games = {name: files for name, files in games.items() if len(files) > 1}

    # Sort disc files by disc number
    for game_name in multidisc_games:
        multidisc_games[game_name].sort(key=lambda x: x[0])

    return multidisc_games


def create_m3u_file(game_name, disc_files, folder):
    """
    Create an .m3u file for a multi-disc game.
    """
    m3u_filename = os.path.join(folder, f"{game_name}.m3u")

    # Check if m3u already exists
    if os.path.exists(m3u_filename):
        print(f"  ⚠ M3U already exists: {game_name}.m3u")
        return False

    # Create the m3u file
    with open(m3u_filename, 'w', encoding='utf-8') as f:
        for disc_num, disc_file in disc_files:
            f.write(f"{disc_file}\n")

    print(f"  ✓ Created: {game_name}.m3u")
    print(f"    Discs: {len(disc_files)}")
    for disc_num, disc_file in disc_files:
        print(f"      - {disc_file}")

    return True


def main():
    print("=" * 60)
    print("Multi-disc M3U Creator")
    print("=" * 60)

    if not os.path.exists(GAME_FOLDER):
        print(f"\n✗ ERROR: Folder not found: {GAME_FOLDER}")
        return

    print(f"\nScanning folder: {GAME_FOLDER}\n")

    # Find all multi-disc games
    multidisc_games = find_multidisc_games(GAME_FOLDER)

    if not multidisc_games:
        print("No multi-disc games found.")
        print("\nMake sure your disc files follow naming conventions like:")
        print("  - Game Name (Disc 1).cue")
        print("  - Game Name (Disc 2).cue")
        return

    print(f"Found {len(multidisc_games)} multi-disc game(s):\n")

    created_count = 0
    skipped_count = 0

    for game_name, disc_files in multidisc_games.items():
        if create_m3u_file(game_name, disc_files, GAME_FOLDER):
            created_count += 1
        else:
            skipped_count += 1
        print()

    print("=" * 60)
    print(f"✓ Complete!")
    print(f"  Created: {created_count} M3U file(s)")
    print(f"  Skipped: {skipped_count} (already exist)")
    print("=" * 60)


if __name__ == "__main__":
    main()