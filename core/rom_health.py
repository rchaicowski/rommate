"""ROM health check utilities for RomMate"""

import os
import subprocess
import shutil
from pathlib import Path


class ROMHealthChecker:
    """Check ROM file integrity and health"""
    
    def __init__(self):
        """Initialize ROM health checker"""
        self.chdman_path = None
    
    def find_chdman(self):
        """Find chdman executable"""
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
    
    def verify_chd(self, chd_file):
        """Verify a single CHD file
        
        Args:
            chd_file (str): Path to CHD file
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.chdman_path:
            if not self.find_chdman():
                return False, "chdman not found"
        
        try:
            # Run chdman verify
            result = subprocess.run(
                [self.chdman_path, 'verify', '-i', chd_file],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Check output for success
            output = result.stdout + result.stderr
            
            if 'verification successful' in output.lower():
                return True, "Verified OK"
            elif 'verification failed' in output.lower():
                return False, "Verification failed - file may be corrupted"
            elif result.returncode != 0:
                return False, f"Error: {output.strip()}"
            else:
                # Fallback - if no error and returncode is 0, assume success
                return True, "Verified OK"
                
        except subprocess.TimeoutExpired:
            return False, "Verification timeout (file too large or corrupted)"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def check_folder(self, folder, log_callback=None, progress_callback=None, cancel_check=None):
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
                log_callback("❌ No CHD files found in folder")
            return 0, 0, []
        
        if log_callback:
            log_callback(f"\n🔍 Found {len(chd_files)} CHD file(s) to verify\n")
        
        # Verify each CHD
        for index, chd_file in enumerate(chd_files, 1):
            # Check for cancellation
            if cancel_check and cancel_check():
                if log_callback:
                    log_callback("\n⚠️ Health check cancelled by user")
                break
            
            filename = os.path.basename(chd_file)
            
            if progress_callback:
                progress_callback(index, len(chd_files), filename)
            
            if log_callback:
                log_callback(f"🔎 Verifying: {filename}")
            
            # Verify the CHD
            success, message = self.verify_chd(chd_file)
            
            if success:
                verified += 1
                if log_callback:
                    log_callback(f"   ✅ {message}")
                results.append({
                    'file': filename,
                    'path': chd_file,
                    'status': 'verified',
                    'message': message
                })
            else:
                failed += 1
                if log_callback:
                    log_callback(f"   ❌ {message}")
                results.append({
                    'file': filename,
                    'path': chd_file,
                    'status': 'failed',
                    'message': message
                })
        
        return verified, failed, results
