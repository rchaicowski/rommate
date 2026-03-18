# RomMate - ROM companion tool
# Copyright (C) 2026 Rodrigo
# GNU General Public License v3.0 - see LICENSE file for details

"""ROM health check utilities for RomMate"""

import os
import subprocess
import shutil
import platform
from pathlib import Path
from core.cartridge_checker import CartridgeChecker


class ROMHealthChecker:
    """Check ROM file integrity and health"""
    
    def __init__(self):
        """Initialize ROM health checker"""
        self.chdman_path = None
        self.cartridge_checker = CartridgeChecker()
        self._current_process = None  # Track running subprocess for cancellation
    
    def find_chdman(self):
        """Find chdman executable"""
        # Check for bundled chdman in tools/ directory FIRST
        bundled_path = os.path.join(
            os.path.dirname(__file__), '..', 'tools',
            'chdman.exe' if platform.system() == 'Windows' else 'chdman')
    
        if os.path.exists(bundled_path):
            self.chdman_path = bundled_path
            return True

        # Check if chdman is in PATH
        chdman_path = shutil.which('chdman')
        if chdman_path:
            self.chdman_path = chdman_path
            return True
        
        # Check common locations
        common_paths = [
            '/usr/bin/chdman',
            '/usr/local/bin/chdman',
            'C:\\Program Files\\chdman\\chdman.exe',
            'C:\\chdman\\chdman.exe',
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                self.chdman_path = path
                return True
        
        return False
    
    def verify_chd(self, chd_file, cancel_check=None):
        """Verify a single CHD file
        
        Args:
            chd_file (str): Path to CHD file
            cancel_check (function): Optional cancel check — kills process immediately if True
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.chdman_path:
            if not self.find_chdman():
                return False, "chdman not found"
        
        try:
            self._current_process = subprocess.Popen(
                [self.chdman_path, 'verify', '-i', chd_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Poll every 100ms so cancel is near-instant
            import time
            while self._current_process.poll() is None:
                if cancel_check and cancel_check():
                    self._current_process.kill()
                    self._current_process.wait()
                    self._current_process = None
                    return False, "Cancelled"
                time.sleep(0.1)

            stdout, stderr = self._current_process.stdout.read(), self._current_process.stderr.read()
            returncode = self._current_process.returncode
            self._current_process = None

            output = stdout + stderr

            if 'verification successful' in output.lower():
                return True, "Verified (Integrity Check Passed)"
            elif 'verification failed' in output.lower():
                return False, "Verification failed - file may be corrupted"
            elif returncode != 0:
                return False, f"Error: {output.strip()}"
            else:
                return True, "Verified (Integrity Check Passed)"

        except Exception as e:
            self._current_process = None
            return False, f"Error: {str(e)}"
    
    def parse_cue_file(self, cue_file):
        """Parse a CUE file and extract BIN file references
        
        Args:
            cue_file (str): Path to CUE file
            
        Returns:
            list: List of referenced BIN files
        """
        bin_files = []
        
        try:
            with open(cue_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    # Look for FILE "filename.bin" BINARY
                    if line.upper().startswith('FILE'):
                        # Extract filename between quotes
                        parts = line.split('"')
                        if len(parts) >= 2:
                            filename = parts[1]
                            bin_files.append(filename)
        except Exception:
            return []
        
        return bin_files
    
    def verify_cue_bin(self, cue_file):
        """Verify a CUE/BIN set
        
        Args:
            cue_file (str): Path to CUE file
            
        Returns:
            tuple: (success: bool, message: str, details: list)
        """
        cue_dir = os.path.dirname(cue_file)
        
        # Parse CUE file
        bin_files = self.parse_cue_file(cue_file)
        
        if not bin_files:
            return False, "Could not parse CUE file or no BIN files referenced", []
        
        # Check each BIN file
        missing = []
        found = []
        details = []
        
        for bin_file in bin_files:
            # Try exact path first
            bin_path = os.path.join(cue_dir, bin_file)
            
            # Try case-insensitive match (for cross-platform compatibility)
            if not os.path.exists(bin_path):
                # Look for case-insensitive match
                found_match = False
                for file in os.listdir(cue_dir):
                    if file.lower() == bin_file.lower():
                        bin_path = os.path.join(cue_dir, file)
                        found_match = True
                        break
                
                if not found_match:
                    missing.append(bin_file)
                    details.append(f"   [x] Missing: {bin_file}")
                    continue
            
            # Check if file is readable and has size
            try:
                size = os.path.getsize(bin_path)
                if size == 0:
                    details.append(f"   [!] Empty file: {bin_file}")
                else:
                    found.append(bin_file)
                    size_mb = size / (1024 * 1024)
                    details.append(f"   [✓] Found: {bin_file} ({size_mb:.1f} MB)")
            except Exception as e:
                details.append(f"   [x] Error reading: {bin_file} - {str(e)}")
                missing.append(bin_file)
        
        # Determine overall result
        if missing:
            return False, f"{len(missing)} BIN file(s) missing or unreadable", details
        elif found:
            return True, f"All {len(found)} BIN file(s) found and readable", details
        else:
            return False, "No BIN files could be verified", details
    
    def check_folder_chd(self, folder, log_callback=None, progress_callback=None, cancel_check=None):
        """Check all CHD files in a folder
        
        Args:
            folder (str): Folder path to scan
            log_callback (function): Callback for logging messages
            progress_callback (function): Callback for progress updates
            cancel_check (function): Function that returns True if cancelled
            
        Returns:
            tuple: (verified_count, failed_count, results_list)
        """
        verified = 0
        failed = 0
        results = []
        
        # Find all CHD files
        chd_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.chd'):
                    chd_files.append(os.path.join(root, file))
        
        if not chd_files:
            if log_callback:
                log_callback("[x] No CHD files found in folder")
            return 0, 0, []
        
        if log_callback:
            log_callback(f"\nFound {len(chd_files)} CHD file(s) to verify\n")
        
        # Verify each CHD
        for index, chd_file in enumerate(chd_files, 1):
            # Check for cancellation
            if cancel_check and cancel_check():
                if log_callback:
                    log_callback("\n[!] Health check cancelled by user")
                break
            
            filename = os.path.basename(chd_file)
            
            if progress_callback:
                progress_callback(index, len(chd_files), filename)
            
            if log_callback:
                log_callback(f">> {filename}")
            
            # Check cancel before starting verify (kill any running process)
            if cancel_check and cancel_check():
                if self._current_process:
                    self._current_process.kill()
                    self._current_process.wait()
                    self._current_process = None
                break

            # Verify the CHD
            success, message = self.verify_chd(chd_file, cancel_check)
            
            if success:
                verified += 1
                if log_callback:
                    log_callback(f"   [✓] {message}")
                results.append({
                    'file': filename,
                    'path': chd_file,
                    'status': 'verified',
                    'message': message
                })
            else:
                failed += 1
                if log_callback:
                    log_callback(f"   [x] {message}")
                results.append({
                    'file': filename,
                    'path': chd_file,
                    'status': 'failed',
                    'message': message
                })
        
        return verified, failed, results
    
    def check_folder_cue_bin(self, folder, log_callback=None, progress_callback=None, cancel_check=None):
        """Check all CUE/BIN sets in a folder
        
        Args:
            folder (str): Folder path to scan
            log_callback (function): Callback for logging messages
            progress_callback (function): Callback for progress updates
            cancel_check (function): Function that returns True if cancelled
            
        Returns:
            tuple: (verified_count, failed_count, results_list)
        """
        verified = 0
        failed = 0
        results = []
        
        # Find all CUE files
        cue_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.cue'):
                    cue_files.append(os.path.join(root, file))
        
        if not cue_files:
            if log_callback:
                log_callback("[x] No CUE files found in folder")
            return 0, 0, []
        
        if log_callback:
            log_callback(f"\nFound {len(cue_files)} CUE file(s) to verify\n")
        
        # Verify each CUE/BIN set
        for index, cue_file in enumerate(cue_files, 1):
            # Check for cancellation
            if cancel_check and cancel_check():
                if log_callback:
                    log_callback("\n[!] Health check cancelled by user")
                break
            
            filename = os.path.basename(cue_file)
            
            if progress_callback:
                progress_callback(index, len(cue_files), filename)
            
            if log_callback:
                log_callback(f">> {filename}")
            
            # Verify the CUE/BIN set
            success, message, details = self.verify_cue_bin(cue_file)
            
            if success:
                verified += 1
                if log_callback:
                    log_callback(f"   [✓] {message}")
                    for detail in details:
                        log_callback(f"      {detail}")
                results.append({
                    'file': filename,
                    'path': cue_file,
                    'status': 'verified',
                    'message': message,
                    'details': details
                })
            else:
                failed += 1
                if log_callback:
                    log_callback(f"   [x] {message}")
                    for detail in details:
                        log_callback(f"      {detail}")
                results.append({
                    'file': filename,
                    'path': cue_file,
                    'status': 'failed',
                    'message': message,
                    'details': details
                })
        
        return verified, failed, results
    
    def check_folder(self, folder, log_callback=None, progress_callback=None, cancel_check=None):
        """Check all ROM files in a folder (disc and cartridge)
        
        Args:
            folder (str): Folder path to scan
            log_callback (function): Callback for logging messages
            progress_callback (function): Callback for progress updates
            cancel_check (function): Function that returns True if cancelled
            
        Returns:
            dict: Results with counts for each category
        """
        results = {
            'chd_verified': 0,
            'chd_failed': 0,
            'cue_verified': 0,
            'cue_failed': 0,
            'cart_verified': 0,
            'cart_has_header': 0,
            'cart_unknown': 0,
            'cart_failed': 0,
            'all_results': []
        }
        
        # Check CHD files
        if log_callback:
            log_callback("\n-- CHD files --")
        
        chd_verified, chd_failed, chd_results = self.check_folder_chd(folder, log_callback, progress_callback, cancel_check)
        results['chd_verified'] = chd_verified
        results['chd_failed'] = chd_failed
        results['all_results'].extend(chd_results)
        
        # Check if cancelled
        if cancel_check and cancel_check():
            return results
        
        # Check CUE/BIN files
        if log_callback:
            log_callback("\n\n-- CUE/BIN files --")
        
        cue_verified, cue_failed, cue_results = self.check_folder_cue_bin(folder, log_callback, progress_callback, cancel_check)
        results['cue_verified'] = cue_verified
        results['cue_failed'] = cue_failed
        results['all_results'].extend(cue_results)
        
        # Check if cancelled
        if cancel_check and cancel_check():
            return results
        
        # Check Cartridge ROMs
        if log_callback:
            log_callback("\n\n-- Game files --")
        
        cart_verified, cart_header, cart_hacks, cart_unknown, cart_failed, cart_results = self.cartridge_checker.check_folder(
            folder, log_callback, progress_callback, cancel_check
        )
        results['cart_verified'] = cart_verified
        results['cart_has_header'] = cart_header
        results['cart_hacks'] = cart_hacks
        results['cart_unknown'] = cart_unknown
        results['cart_failed'] = cart_failed
        results['all_results'].extend(cart_results)
        
        return results
