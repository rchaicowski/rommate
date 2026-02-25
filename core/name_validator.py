"""
RomMate - ROM companion tool
Copyright (C) 2026 Rodrigo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

"""ROM name validation and correction"""

import os
from pathlib import Path
from core.cartridge_checker import CartridgeChecker


class NameValidator:
    """Validate and suggest corrections for ROM filenames"""
    
    def __init__(self):
        """Initialize name validator"""
        self.cartridge_checker = CartridgeChecker()
    
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
                    except:
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
                    except:
                        pass
        
        # Find all ROM files
        rom_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Skip if it's part of a CUE/BIN or GDI set
                if os.path.normpath(full_path) in cue_bin_files:
                    continue
                
                # Skip backup files
                if file.endswith('.backup'):
                    continue
                
                ext = os.path.splitext(file)[1].lower()
                
                # Check if extension is in any system
                for system, extensions in self.cartridge_checker.SYSTEM_EXTENSIONS.items():
                    if ext in extensions:
                        rom_files.append(full_path)
                        break
        
        if not rom_files:
            if log_callback:
                log_callback("❌ No ROM files found in folder")
            return []
        
        if log_callback:
            log_callback(f"\n🔍 Found {len(rom_files)} ROM(s) to validate\n")
        
        # Validate each ROM
        for index, rom_file in enumerate(rom_files, 1):
            if cancel_check and cancel_check():
                break
            
            filename = os.path.basename(rom_file)
            
            if progress_callback:
                progress_callback(index, len(rom_files), filename)
            
            if log_callback:
                log_callback(f"🔎 Checking: {filename}")
            
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
                    log_callback(f"   📝 Needs rename")
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
                    log_callback(f"   ✅ Name is correct")
                return None
        else:
            # ROM unknown or hack
            if log_callback:
                if rom_result['status'] == 'hack':
                    log_callback(f"   🎨 ROM hack - skipping")
                else:
                    log_callback(f"   ❓ Unknown ROM - cannot suggest name")
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
