# RomMate - ROM companion tool
# Copyright (C) 2026 Rodrigo
# GNU General Public License v3.0 - see LICENSE file for details

"""ROM name validation and correction"""

import os
import re
import difflib
from pathlib import Path
from core.cartridge_checker import CartridgeChecker

# Words ignored when comparing titles, so "The Legend of Zelda" matches
# "Legend of Zelda, The".
_IGNORED_WORDS = {'the', 'a', 'an'}

# Roman numerals are compared as numbers, so "Dragon Quest III" is not confused
# with "Dragon Quest I & II". A bare "X" is left alone (e.g. "Mega Man X").
_ROMAN_NUMERALS = {
    'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6',
    'vii': '7', 'viii': '8', 'ix': '9', 'xi': '11', 'xii': '12', 'xiii': '13',
}


def _title_tokens(name):
    """Reduce a ROM or database name to comparable words.

    Lowercase, without (tags) and [tags] (regions, revisions, translation
    info), without punctuation, without "the/a/an", roman numerals as digits.
    """
    text = name.lower()
    text = re.sub(r'\[.*?\]|\(.*?\)', ' ', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return [_ROMAN_NUMERALS.get(w, w) for w in text.split() if w not in _IGNORED_WORDS]


_DB_DISC_RE = re.compile(r'\(disc (\d+)\)', re.IGNORECASE)
_FILE_DISC_RE = re.compile(r'\b(?:disc|disk|cd)[\s._-]*(\d+)\b', re.IGNORECASE)


def _db_disc_number(name):
    """Disc number of a database name like 'Game (USA) (Disc 2)', or None."""
    match = _DB_DISC_RE.search(name)
    return int(match.group(1)) if match else None


def _split_file_disc(stem):
    """Pull a disc number out of a filename ('Game Disc 2', 'Game CD2').

    Returns (stem without the disc part, disc number or None).
    """
    match = _FILE_DISC_RE.search(stem)
    if not match:
        return stem, None
    return (stem[:match.start()] + ' ' + stem[match.end():]), int(match.group(1))


def _region_rank(name):
    """Sort order for regions in the suggestion list: USA, Europe, Japan, World, other."""
    lowered = name.lower()
    for rank, marker in enumerate(('(usa', '(europe', '(japan', '(world')):
        if marker in lowered:
            return rank
    return 4


class NameValidator:
    """Validate and suggest corrections for ROM filenames"""
    
    # Tuning for the "similar names" suggestions
    SUGGESTION_CUTOFF = 0.6        # minimum similarity (0-1) to be suggested
    SUGGESTION_LIMIT = 8           # max names suggested per ROM
    SUGGESTIONS_PER_TITLE = 3      # max variants (regions/revisions) of one game

    def __init__(self):
        """Initialize name validator"""
        self.cartridge_checker = CartridgeChecker()
        self._title_index = {}     # system -> {normalized title: {...}}
        self._known_names = {}     # system -> {lowercase database names}

    def _get_title_index(self, system):
        """Build (once per system) an index of database names grouped by title.

        All regions/revisions of the same game share one normalized title, so
        "Super Mario World (USA)", "(Europe)" and "(Japan)" are scored together.
        """
        if system in self._title_index:
            return self._title_index[system]

        database = self.cartridge_checker.load_database(system)
        index = {}
        db_names = {entry['name'] for entry in database.values()}
        self._known_names[system] = {n.lower() for n in db_names}
        for name in db_names:
            tokens = _title_tokens(name)
            if not tokens:
                continue
            slot = index.setdefault(' '.join(tokens), {
                'tokens': set(tokens),
                'numbers': {t for t in tokens if t.isdigit()},
                'names': [],
            })
            slot['names'].append(name)

        self._title_index[system] = index
        return index

    def _is_database_name(self, system, stem):
        """True if a filename (without extension) is exactly a database name."""
        self._get_title_index(system)
        return stem.lower() in self._known_names.get(system, ())

    def find_similar_names(self, filename, system, limit=None, cutoff=None):
        """Find database names that look like a ROM filename.

        Compares titles only (ignoring region/revision tags), so every region
        of a similar game is offered. Different numbers (sequels, roman
        numerals) lower the score.

        Args:
            filename (str): ROM filename (with or without extension)
            system (str): System name used to pick the database
            limit (int): Max names to return
            cutoff (float): Minimum similarity, 0 to 1

        Returns:
            list: [{'name': database name, 'score': percent}], best first
        """
        limit = limit or self.SUGGESTION_LIMIT
        cutoff = cutoff if cutoff is not None else self.SUGGESTION_CUTOFF

        index = self._get_title_index(system)
        stem, query_disc = _split_file_disc(os.path.splitext(filename)[0])
        query = _title_tokens(stem)
        if not index or not query:
            return []

        query_str = ' '.join(query)
        query_set = set(query)
        query_numbers = {t for t in query if t.isdigit()}

        matcher = difflib.SequenceMatcher(None, autojunk=False)
        matcher.set_seq2(query_str)

        scored = []
        for title, info in index.items():
            overlap = len(query_set & info['tokens']) / min(len(query_set), len(info['tokens']))
            matcher.set_seq1(title)
            if overlap < 0.5 and matcher.quick_ratio() < 0.5:
                continue

            score = 0.6 * matcher.ratio() + 0.4 * overlap

            if query_numbers:
                if info['numbers'] and not (query_numbers & info['numbers']):
                    score *= 0.6      # different number = different game
                elif not info['numbers']:
                    score *= 0.7      # file has a number, this title has none

            if score >= cutoff:
                scored.append((score, info['names']))

        scored.sort(key=lambda item: -item[0])

        # Multi-disc games: show the disc the file asks for (Disc 1 if it
        # doesn't say), so the list is regions of that disc, not Disc 1/2/3.
        wanted_disc = query_disc or 1

        suggestions = []
        for score, names in scored:
            if any(_db_disc_number(n) is not None for n in names):
                same_disc = [n for n in names if _db_disc_number(n) in (None, wanted_disc)]
                names = same_disc or names
            # Plainest entries first (fewer tags), then USA, Europe, Japan...
            names = sorted(names, key=lambda n: (len(re.findall(r'\(.*?\)', n)),
                                                 _region_rank(n), n))
            for name in names[:self.SUGGESTIONS_PER_TITLE]:
                suggestions.append({'name': name, 'score': int(round(score * 100))})
                if len(suggestions) >= limit:
                    return suggestions
        return suggestions

    def _log_suggestions(self, suggestions, log_callback, header):
        """Write the suggestion list to the log."""
        if not log_callback:
            return
        if suggestions:
            log_callback(header)
            for suggestion in suggestions:
                log_callback(f"      {suggestion['score']:>3}%  {suggestion['name']}")
        else:
            log_callback("   [?] No similar names found in the database")
    
    def validate_folder(self, folder, log_callback=None, progress_callback=None, cancel_check=None):
        """Validate ROM names in a folder
        
        Args:
            folder (str): Folder path to scan
            log_callback (function): Callback for logging messages
            progress_callback (function): Callback for progress updates
            cancel_check (function): Function that returns True if cancelled
            
        Returns:
            list: List of validation results for each ROM
        """
        results = []
        
        # First, find all CUE and GDI files to exclude their BINs
        cue_bin_files = set()
        for root, dirs, files in os.walk(folder):
            for file in files:
                # Handle CUE files
                if file.lower().endswith('.cue'):
                    cue_path = os.path.join(root, file)
                    cue_dir = os.path.dirname(cue_path)
                    try:
                        with open(cue_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                if 'FILE' in line.upper():
                                    parts = line.split('"')
                                    if len(parts) >= 2:
                                        bin_file = parts[1]
                                        bin_path = os.path.join(cue_dir, bin_file)
                                        cue_bin_files.add(os.path.normpath(bin_path))
                    except Exception:
                        pass
                
                # Handle GDI files
                elif file.lower().endswith('.gdi'):
                    gdi_path = os.path.join(root, file)
                    gdi_dir = os.path.dirname(gdi_path)
                    try:
                        with open(gdi_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                parts = line.strip().split()
                                if len(parts) >= 5:
                                    bin_file = parts[4]
                                    bin_path = os.path.join(gdi_dir, bin_file)
                                    cue_bin_files.add(os.path.normpath(bin_path))
                    except Exception:
                        pass
        
        # Find all ROM files
        rom_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Skip backup files
                if file.endswith('.backup'):
                    continue
                
                ext = os.path.splitext(file)[1].lower()
                
                # Include CUE and GDI files for validation
                if ext in ['.cue', '.gdi']:
                    rom_files.append(full_path)
                    continue
                
                # Skip if it's a BIN/track from a CUE/GDI set
                if os.path.normpath(full_path) in cue_bin_files:
                    continue
                
                # Check if extension is in any system
                for system, extensions in self.cartridge_checker.SYSTEM_EXTENSIONS.items():
                    if ext in extensions:
                        rom_files.append(full_path)
                        break
        
        if not rom_files:
            if log_callback:
                log_callback("[x] No ROM files found in folder")
            return []
        
        if log_callback:
            log_callback(f"\nFound {len(rom_files)} ROM(s) to validate\n")
        
        # Validate each ROM
        for index, rom_file in enumerate(rom_files, 1):
            if cancel_check and cancel_check():
                break
            
            filename = os.path.basename(rom_file)
            
            if progress_callback:
                progress_callback(index, len(rom_files), filename)
            
            if log_callback:
                log_callback(f">> {filename}")
            
            result = self.validate_rom(rom_file, log_callback)
            if result:
                results.append(result)
        
        return results
    
    def validate_rom(self, rom_file, log_callback=None):
        """Validate a single ROM filename
        
        Args:
            rom_file (str): Path to ROM file
            log_callback (function): Optional logging callback
            
        Returns:
            dict: Validation result with suggestions, or None if name is OK
        """
        # Use cartridge_checker to identify the ROM
        rom_result = self.cartridge_checker.verify_rom(rom_file)
        
        current_name = os.path.basename(rom_file)
        
        # If ROM was identified, suggest the database name
        if rom_result['status'] in ['verified', 'identified', 'probable', 'likely', 'has_header', 'possible']:
            suggested_name = rom_result['game_name']
            extension = os.path.splitext(current_name)[1]
            suggested_name_full = suggested_name + extension
            
            # Check if names are different (case-insensitive comparison)
            if current_name.lower() != suggested_name_full.lower():
                if log_callback:
                    log_callback(f"   [!] Needs rename")
                    log_callback(f"      Current: {current_name}")
                    log_callback(f"      Suggested: {suggested_name_full}")
                    log_callback(f"      Confidence: {rom_result.get('confidence', 'N/A')}")
                
                return {
                    'path': rom_file,
                    'current_name': current_name,
                    'suggested_name': suggested_name_full,
                    'confidence': rom_result.get('confidence', 'N/A'),
                    'status': 'needs_rename',
                    'system': rom_result.get('system'),
                    'all_matches': rom_result.get('all_regions', None),  # For multi-region
                    'match_status': rom_result['status']
                }
            else:
                if log_callback:
                    log_callback(f"   [✓] Name is correct")
                return None
        else:
            status = rom_result['status']
            system = rom_result.get('system')
            is_translation = (status == 'hack' and rom_result.get('hack_type') == 'translation')

            # Other hacks/modified ROMs are skipped
            if status == 'hack' and not is_translation:
                if log_callback:
                    log_callback(f"   [!] ROM hack - skipping")
                return None

            # No exact match (or a translation): offer similar names instead
            # of a dead end, e.g. a fan translation can be renamed to the
            # original (Japanese) name.
            if system and (status in ('unknown', 'name_match') or is_translation):
                # Already named exactly like a database entry (common for CUE
                # files, which can't be checksum-verified): nothing to fix.
                if self._is_database_name(system, os.path.splitext(current_name)[0]):
                    if log_callback:
                        log_callback(f"   [✓] Name is correct")
                    return None

                suggestions = self.find_similar_names(current_name, system)
                header = ("   [!] Translation - possible original names:" if is_translation
                          else "   [?] No exact match - possible names:")
                self._log_suggestions(suggestions, log_callback, header)

                if not suggestions:
                    return None

                # Let the user pick one of the names (or keep the current one)
                extension = os.path.splitext(current_name)[1]
                return {
                    'path': rom_file,
                    'current_name': current_name,
                    'status': 'needs_choice',
                    'system': system,
                    'is_translation': is_translation,
                    'suggestions': [
                        {'name': item['name'] + extension, 'score': item['score']}
                        for item in suggestions
                    ],
                }

            if log_callback:
                log_callback(f"   [?] Unknown ROM - cannot suggest name")
            return None
    
    def rename_rom(self, rom_path, new_name):
        """Rename a ROM file
        
        Args:
            rom_path (str): Current path to ROM
            new_name (str): New filename (not full path)
            
        Returns:
            tuple: (success: bool, message: str, new_path: str or None)
        """
        try:
            directory = os.path.dirname(rom_path)
            new_path = os.path.join(directory, new_name)
            
            # Check if target already exists
            if os.path.exists(new_path):
                return False, "Target file already exists", None
            
            # Rename the file
            os.rename(rom_path, new_path)
            
            return True, "Renamed successfully", new_path
            
        except Exception as e:
            return False, f"Error: {str(e)}", None
