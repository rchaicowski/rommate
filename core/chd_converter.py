# RomMate - ROM companion tool
# Copyright (C) 2026 Rodrigo
# GNU General Public License v3.0 - see LICENSE file for details

"""CHD conversion functionality for RomMate"""

import os
import subprocess
import platform
import shutil
import time
from pathlib import Path
from tkinter import messagebox


class CHDConverter:
    """Handles conversion of disc images to CHD format"""
    
    def __init__(self):
        """Initialize CHD converter"""
        self.chdman_path = None
    
    def find_chdman(self):
        """Try to find chdman executable
        
        Returns:
            str: Path to chdman or None if not found
        """
        # Check if bundled with app
        import sys
        base_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.join(os.path.dirname(__file__), '..')
        bundled_path = os.path.join(base_dir, 'tools',
                                    'chdman.exe' if platform.system() == 'Windows' else 'chdman')
        if os.path.exists(bundled_path):
            return bundled_path
        
        # Check if in system PATH
        chdman_name = 'chdman.exe' if platform.system() == 'Windows' else 'chdman'
        chdman_path = shutil.which(chdman_name)
        if chdman_path:
            return chdman_path
        
        return None
    
    def get_install_command(self):
        """Get the correct package manager command for this Linux distro
        
        Returns:
            str: Installation command or None if not Linux
        """
        if platform.system() != 'Linux':
            return None
        
        try:
            with open('/etc/os-release', 'r') as f:
                os_info = f.read().lower()
            
            if 'ubuntu' in os_info or 'debian' in os_info or 'mint' in os_info:
                return "sudo apt install mame-tools"
            elif 'fedora' in os_info or 'rhel' in os_info or 'centos' in os_info:
                return "sudo dnf install mame"
            elif 'arch' in os_info or 'manjaro' in os_info:
                return "sudo pacman -S mame-tools"
            elif 'opensuse' in os_info:
                return "sudo zypper install mame-tools"
            else:
                return "sudo apt install mame-tools"  # Default to apt
        except Exception:
            return "sudo apt install mame-tools"
    
    def prompt_install_chdman(self):
        """Prompt user to install chdman automatically (Linux only)
        
        Returns:
            bool: True if installation was attempted, False otherwise
        """
        install_cmd = self.get_install_command()
        
        if not install_cmd:
            return False
        
        response = messagebox.askyesno(
            "First-Time Setup Required",
            f"CHD conversion requires chdman.\n\n"
            f"Would you like to install it now?\n"
            f"(This will open a terminal and require your password)\n\n"
            f"Command: {install_cmd}\n\n"
            f"This is a one-time setup.",
            icon='question'
        )
        
        if response:
            try:
                # Try different terminal emulators (Linux has many)
                terminals = [
                    ['gnome-terminal', '--'],
                    ['konsole', '-e'],
                    ['xfce4-terminal', '-e'],
                    ['xterm', '-e'],
                ]
                
                install_script = f'{install_cmd}; echo "\n✅ Installation complete! Press Enter to close."; read'
                
                terminal_opened = False
                for terminal in terminals:
                    try:
                        subprocess.Popen(terminal + ['bash', '-c', install_script])
                        terminal_opened = True
                        break
                    except FileNotFoundError:
                        continue
                
                if terminal_opened:
                    messagebox.showinfo(
                        "Installing...",
                        "Please complete the installation in the terminal window.\n\n"
                        "After installation, try CHD conversion again."
                    )
                    return True
                else:
                    messagebox.showwarning(
                        "Manual Installation Required",
                        f"Could not open terminal automatically.\n\n"
                        f"Please run this command manually:\n{install_cmd}\n\n"
                        f"Then try CHD conversion again."
                    )
                    return False
            except Exception as e:
                messagebox.showerror(
                    "Installation Error",
                    f"Could not start installation.\n\n"
                    f"Please run manually:\n{install_cmd}"
                )
                return False
        
        return False
    

    def _get_bin_files_from_cue(self, cue_path):
        """Parse a CUE file and return list of referenced BIN file paths."""
        bin_files = []
        cue_dir = os.path.dirname(cue_path)
        try:
            with open(cue_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.upper().startswith('FILE'):
                        parts = line.split('"')
                        if len(parts) >= 2:
                            bin_path = os.path.join(cue_dir, parts[1])
                            if os.path.exists(bin_path):
                                bin_files.append(bin_path)
        except Exception:
            pass
        return bin_files

    def _safe_delete_originals(self, source_path, source_ext, chd_path, log_callback=None):
        """Safely delete original files only after verifying CHD is valid."""
        # 1. CHD must exist
        if not os.path.exists(chd_path):
            if log_callback:
                log_callback("   [!] CHD not found, keeping originals")
            return

        # 2. CHD must not be empty
        chd_size = os.path.getsize(chd_path)
        if chd_size == 0:
            if log_callback:
                log_callback("   [!] CHD is empty, keeping originals")
            return

        # 3. CHD must be at least 5% of source size (catches truncated output)
        try:
            source_size = os.path.getsize(source_path)
            if source_size > 0 and chd_size < source_size * 0.30:
                if log_callback:
                    log_callback("   [!] CHD seems too small, keeping originals")
                return
        except Exception:
            pass

        # Safe to delete — collect files to remove before deleting anything
        files_to_delete = [source_path]
        if source_ext == '.cue':
            files_to_delete.extend(self._get_bin_files_from_cue(source_path))

        for f in files_to_delete:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                if log_callback:
                    log_callback(f"   [!] Could not delete {os.path.basename(f)}: {e}")
                return

        if log_callback:
            log_callback("   Deleted original files")

    def convert_file(self, source_file, delete_after=False, 
                log_callback=None, animation_callback=None):
        """Convert a single file to CHD
        
        Args:
            source_file (Path): Source file to convert
            delete_after (bool): Delete original after successful conversion
            log_callback (callable): Function to call with log messages
            animation_callback (callable): Function to call for animation updates
                                         Should accept (position, text) args
        
        Returns:
            tuple: (success, chd_path) - success is bool, chd_path is str or None
        """
        source_path = str(source_file)
        source_ext = source_file.suffix.lower()
        chd_path = str(source_file.with_suffix('.chd'))
        
        # Skip if CHD already exists
        if os.path.exists(chd_path):
            return True, chd_path
        
        try:
            # Determine if CD or DVD format
            is_dvd = False
            file_size = os.path.getsize(source_path)
            
            # Check file size for ISOs - DVDs are larger than 800 MB
            if source_ext == '.iso' and file_size > 800 * 1024 * 1024:
                is_dvd = True
            
            # Use appropriate chdman command
            if is_dvd:
                cmd = [self.chdman_path, 'createdvd', '-i', source_path, '-o', chd_path]
            else:
                cmd = [self.chdman_path, 'createcd', '-i', source_path, '-o', chd_path]
            
            # For large files (> 100 MB), don't capture output to avoid buffering issues
            if file_size > 100 * 1024 * 1024:
                # Large file - run without capturing output
                if log_callback and is_dvd:
                    log_callback(f"   [!] Note: PS2/DVD conversion may take longer than other formats")
                    log_callback(f"   Please wait... (app may appear frozen)")
                
                process = subprocess.Popen(cmd)
                
                # Animate dots while waiting
                if animation_callback:
                    dots = 0
                    while process.poll() is None:
                        dots = (dots + 1) % 4
                        dot_str = "." * dots
                        if is_dvd:
                            animation_callback(f"   Processing (Large DVD - please wait){dot_str}")
                        else:
                            animation_callback(f"   Processing{dot_str}")
                        time.sleep(0.5)
                else:
                    # Just wait without animation
                    process.wait()
                
                # Check if successful
                if process.returncode == 0:
                    # Success - delete originals if requested
                    if delete_after:
                        self._safe_delete_originals(
                            source_path, source_ext, chd_path, log_callback)
                    
                    return True, chd_path
                else:
                    if log_callback:
                        log_callback(f"   [x] Conversion failed (return code: {process.returncode})")
                    return False, None
            
            else:
                # Small file - can safely capture output for error messages
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Animate dots while waiting
                if animation_callback:
                    dots = 0
                    while process.poll() is None:
                        dots = (dots + 1) % 4
                        dot_str = "." * dots
                        animation_callback(f"   Processing{dot_str}")
                        time.sleep(0.3)
                else:
                    # Just wait without animation
                    process.wait()
                
                # Get final result
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    # Success - delete originals if requested
                    if delete_after:
                        self._safe_delete_originals(
                            source_path, source_ext, chd_path, log_callback)
                    
                    return True, chd_path
                else:
                    if log_callback:
                        log_callback(f"   [x] Failed: {stderr[:100]}")
                    return False, None
        
        except Exception as e:
            if log_callback:
                log_callback(f"   [x] Error: {str(e)}")
            return False, None
    
    def convert_folder(self, folder, delete_after=False, 
                      log_callback=None, progress_callback=None, animation_callback=None, cancel_check=None):
        """Convert all disc images in a folder to CHD
        
        Args:
            folder (str): Folder containing disc images
            delete_after (bool): Delete originals after successful conversion
            log_callback (callable): Function to call with log messages
            progress_callback (callable): Function to call with progress updates
                                        Should accept (current, total, filename) args
            cancel_check (callable): Function to call to check if cancellation was requested
        
        Returns:
            tuple: (converted, skipped, failed) - counts of each outcome
        """
        # Make sure chdman_path is set
        if not self.chdman_path:
            self.chdman_path = self.find_chdman()
            if not self.chdman_path:
                return 0, 0, 0
        
        # Find all convertible files
        source_files = []
        for pattern in ["*.cue", "*.gdi", "*.cdi", "*.iso"]:
            found = list(Path(folder).glob(pattern))
            if found:
                if log_callback:
                    log_callback(f"Found {len(found)} {pattern} file(s)")
                source_files.extend(found)
        
        if not source_files:
            return 0, 0, 0
        
        total_files = len(source_files)
        if log_callback:
            log_callback(f"\nTotal files to convert: {total_files}\n")
        
        converted = 0
        skipped = 0
        failed = 0
        
        for index, source_file in enumerate(source_files, 1):
            # Check if cancellation was requested
            if cancel_check and cancel_check():
                if log_callback:
                    log_callback("[!] Conversion cancelled by user")
                return converted, skipped, failed
            
            if progress_callback:
                progress_callback(index, total_files, source_file.name)
            
            # Check if already exists
            chd_path = str(source_file.with_suffix('.chd'))
            if os.path.exists(chd_path):
                if log_callback:
                    log_callback(f"   Skipped: {source_file.name} (CHD already exists)")
                skipped += 1
                continue
            
            if log_callback:
                log_callback(f">> {source_file.name}")
            
            success, chd_path = self.convert_file(
                source_file, 
                delete_after=delete_after,
                log_callback=log_callback,
                animation_callback=animation_callback
            )
            
            # If conversion was cancelled mid-file, delete the partial CHD
            if cancel_check and cancel_check():
                if chd_path and os.path.exists(chd_path):
                    try:
                        os.remove(chd_path)
                        if log_callback:
                            log_callback(f"   Deleted incomplete: {os.path.basename(chd_path)}")
                    except Exception:
                        pass
                if log_callback:
                    log_callback("[!] Conversion cancelled by user")
                return converted, skipped, failed
            
            if success:
                if log_callback:
                    log_callback(f"   [✓] Converted to CHD")
                converted += 1
            else:
                # Error already logged in convert_file
                failed += 1
        
        return converted, skipped, failed
