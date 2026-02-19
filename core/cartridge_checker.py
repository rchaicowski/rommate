"""Cartridge ROM validation and health checking"""

import os
import hashlib
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path


class CartridgeChecker:
    """Check cartridge ROM integrity and validate against databases"""
    
    # System detection by file extension
    SYSTEM_EXTENSIONS = {
        # Cartridges
        'nes': ['.nes', '.unf', '.unif'],
        'snes': ['.sfc', '.smc'],
        'n64': ['.n64', '.z64', '.v64'],
        'gb': ['.gb'],
        'gbc': ['.gbc'],
        'gba': ['.gba'],
        'nds': ['.nds'],
        '3ds': ['.3ds', '.cci', '.cia'],
        'genesis': ['.gen', '.md', '.smd'],
        'sms': ['.sms'],
        'gamegear': ['.gg'],
        'sega32x': ['.32x'],
        'a2600': ['.a26'],
        'a7800': ['.a78'],
        'pce': ['.pce'],
        'ngp': ['.ngp', '.ngc'],
        'ws': ['.ws', '.wsc'],
        
        # Disc-based (Redump)
        'gamecube': ['.iso', '.gcm', '.gcz'],
        'wii': ['.iso', '.wbfs'],
        'ps3': ['.iso'],
        'xbox': ['.iso'],
        'xbox360': ['.iso'],
    }
    
    # Which systems use Redump vs No-Intro
    REDUMP_SYSTEMS = ['gamecube', 'wii', 'ps3', 'xbox', 'xbox360']
    
    # Systems that commonly have external headers
    HEADER_SYSTEMS = {
        'snes': 512,  # SMC header
        'nes': 16,    # iNES header (sometimes needed, sometimes not)
        'n64': 0,     # No common headers
        'gb': 0,
        'gbc': 0,
        'gba': 0,
    }
    
    def __init__(self):
        """Initialize cartridge checker"""
        self.databases = {}
        self.no_intro_dir = os.path.join(
            os.path.dirname(__file__), '..', 'databases', 'no-intro'
        )
        self.redump_dir = os.path.join(
            os.path.dirname(__file__), '..', 'databases', 'redump'
        )
    
    def detect_system(self, rom_file):
        """Detect system from file extension
        
        Args:
            rom_file (str): Path to ROM file
            
        Returns:
            str: System name or None
        """
        ext = os.path.splitext(rom_file)[1].lower()
        
        for system, extensions in self.SYSTEM_EXTENSIONS.items():
            if ext in extensions:
                return system
        
        return None
    
    def calculate_checksums(self, rom_file, skip_bytes=0):
        """Calculate CRC32, MD5, and SHA1 checksums
        
        Args:
            rom_file (str): Path to ROM file
            skip_bytes (int): Number of bytes to skip (for header removal)
            
        Returns:
            tuple: (crc32_hex, md5_hex, sha1_hex)
        """
        crc32 = 0
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        
        try:
            with open(rom_file, 'rb') as f:
                # Skip header if needed
                if skip_bytes > 0:
                    f.seek(skip_bytes)
                
                # Read in chunks for large files
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    crc32 = zlib.crc32(chunk, crc32)
                    md5.update(chunk)
                    sha1.update(chunk)
            
            # Format as hex strings
            crc32_hex = format(crc32 & 0xFFFFFFFF, '08x').upper()
            md5_hex = md5.hexdigest().upper()
            sha1_hex = sha1.hexdigest().upper()
            
            return crc32_hex, md5_hex, sha1_hex
            
        except Exception as e:
            return None, None, None
    
    def load_database(self, system):
        """Load database for a system
        
        Args:
            system (str): System name
            
        Returns:
            dict: Database dictionary {crc32: game_info}
        """
        # Check if already loaded
        if system in self.databases:
            return self.databases[system]
        
        # Determine which database directory to use
        if system in self.REDUMP_SYSTEMS:
            db_file = os.path.join(self.redump_dir, f"{system}.dat")
        else:
            db_file = os.path.join(self.no_intro_dir, f"{system}.dat")
        
        if not os.path.exists(db_file):
            # Database not found - return empty
            return {}
        
        # Parse database
        database = {}
        try:
            tree = ET.parse(db_file)
            root = tree.getroot()
            
            for game in root.findall('game'):
                game_name = game.get('name', 'Unknown')
                
                for rom in game.findall('rom'):
                    crc = rom.get('crc', '').upper()
                    if crc:
                        database[crc] = {
                            'name': game_name,
                            'size': rom.get('size', '0'),
                            'md5': rom.get('md5', '').upper(),
                            'sha1': rom.get('sha1', '').upper(),
                        }
            
            # Cache the database
            self.databases[system] = database
            
        except Exception as e:
            print(f"Error loading database for {system}: {e}")
            return {}
        
        return database
    
    def has_external_header(self, rom_file, system):
        """Check if ROM likely has an external copier header
        
        Args:
            rom_file (str): Path to ROM file
            system (str): System name
            
        Returns:
            bool: True if likely has header
        """
        if system not in self.HEADER_SYSTEMS:
            return False
        
        header_size = self.HEADER_SYSTEMS[system]
        if header_size == 0:
            return False
        
        file_size = os.path.getsize(rom_file)
        
        if system == 'snes':
            # SNES ROMs should be multiples of 1024
            # If size % 1024 == 512, likely has SMC header
            return (file_size % 1024) == 512
        
        elif system == 'nes':
            # Check for iNES header signature
            try:
                with open(rom_file, 'rb') as f:
                    signature = f.read(4)
                    return signature == b'NES\x1a'
            except:
                return False
        
        return False
    
    def verify_rom(self, rom_file):
        """Verify a single ROM file
        
        Args:
            rom_file (str): Path to ROM file
            
        Returns:
            dict: Verification result with status, message, details
        """
        filename = os.path.basename(rom_file)
        
        # Detect system
        system = self.detect_system(rom_file)
        if not system:
            return {
                'status': 'unknown',
                'message': 'Unknown file type',
                'filename': filename,
                'system': None
            }
        
        # Load database
        database = self.load_database(system)
        if not database:
            return {
                'status': 'no_database',
                'message': f'No database available for {system.upper()}',
                'filename': filename,
                'system': system
            }
        
        # Calculate checksums
        crc32, md5, sha1 = self.calculate_checksums(rom_file)
        
        if not crc32:
            return {
                'status': 'error',
                'message': 'Could not read ROM file',
                'filename': filename,
                'system': system
            }
        
        # Check database
        if crc32 in database:
            match = database[crc32]
            return {
                'status': 'verified',
                'message': 'Verified Good Dump',
                'filename': filename,
                'system': system,
                'game_name': match['name'],
                'crc32': crc32
            }
        
        # Check if has external header
        if self.has_external_header(rom_file, system):
            header_size = self.HEADER_SYSTEMS[system]
            crc32_clean, md5_clean, sha1_clean = self.calculate_checksums(rom_file, header_size)
            
            if crc32_clean in database:
                match = database[crc32_clean]
                return {
                    'status': 'has_header',
                    'message': 'Has External Header (fixable)',
                    'filename': filename,
                    'system': system,
                    'game_name': match['name'],
                    'crc32': crc32_clean,
                    'header_size': header_size
                }
        
        # Check if might be a ROM hack (look for similar games)
        # For now, just mark as unknown
        # TODO: Add fuzzy matching for ROM hacks
        
        return {
            'status': 'unknown',
            'message': 'Unknown ROM (not in database)',
            'filename': filename,
            'system': system,
            'crc32': crc32
        }
    
    def check_folder(self, folder, log_callback=None, progress_callback=None, cancel_check=None):
        """Check all cartridge ROMs in a folder
        
        Args:
            folder (str): Folder path to scan
            log_callback (function): Callback for logging messages
            progress_callback (function): Callback for progress updates
            cancel_check (function): Function that returns True if cancelled
            
        Returns:
            tuple: (verified, has_header, unknown, failed, results)
        """
        verified = 0
        has_header = 0
        unknown = 0
        failed = 0
        results = []
        
        # Find all cartridge ROM files
        rom_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                # Check if extension is in any system
                for system, extensions in self.SYSTEM_EXTENSIONS.items():
                    if ext in extensions:
                        rom_files.append(os.path.join(root, file))
                        break
        
        if not rom_files:
            if log_callback:
                log_callback("❌ No cartridge ROM files found in folder")
            return 0, 0, 0, 0, []
        
        if log_callback:
            log_callback(f"\n🎮 Found {len(rom_files)} cartridge ROM(s) to verify\n")
        
        # Verify each ROM
        for index, rom_file in enumerate(rom_files, 1):
            # Check for cancellation
            if cancel_check and cancel_check():
                if log_callback:
                    log_callback("\n⚠️ Health check cancelled by user")
                break
            
            filename = os.path.basename(rom_file)
            
            if progress_callback:
                progress_callback(index, len(rom_files), filename)
            
            if log_callback:
                log_callback(f"🔎 Verifying: {filename}")
            
            # Verify the ROM
            result = self.verify_rom(rom_file)
            results.append(result)
            
            # Log result
            if result['status'] == 'verified':
                verified += 1
                if log_callback:
                    log_callback(f"   ✅ {result['message']}")
                    log_callback(f"      Game: {result['game_name']}")
                    
            elif result['status'] == 'has_header':
                has_header += 1
                if log_callback:
                    log_callback(f"   ⚠️ {result['message']}")
                    log_callback(f"      Game: {result['game_name']}")
                    log_callback(f"      Header Size: {result['header_size']} bytes")
                    
            elif result['status'] == 'unknown':
                unknown += 1
                if log_callback:
                    log_callback(f"   ❓ {result['message']}")
                    
            elif result['status'] == 'no_database':
                unknown += 1
                if log_callback:
                    log_callback(f"   ⚠️ {result['message']}")
                    
            else:
                failed += 1
                if log_callback:
                    log_callback(f"   ❌ {result['message']}")
        
        return verified, has_header, unknown, failed, results
