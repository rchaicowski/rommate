# RomMate - ROM companion tool
# Copyright (C) 2026 Rodrigo
# GNU General Public License v3.0 - see LICENSE file for details

"""CHD conversion functionality for RomMate"""

import os
import re
import subprocess
import platform
import shutil
from pathlib import Path
from tkinter import messagebox
from utils.i18n import _


class CHDConverter:
    """Handles conversion of disc images to CHD format"""
    
    def __init__(self):
        """Initialize CHD converter"""
        self.chdman_path = None

    @staticmethod
    def _subprocess_kwargs():
        """Extra kwargs for subprocess.Popen calls that run chdman directly.

        On Windows, chdman.exe is a console app, so spawning it normally pops
        up a visible console window behind/above the app for the duration of
        the conversion. This suppresses that window. No-op on Linux/macOS.
        """
        kwargs = {}
        if platform.system() == 'Windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs['startupinfo'] = startupinfo
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        return kwargs

    _PERCENT_RE = re.compile(r'(\d+\.?\d*)%\s*complete[.\s]*(\(ratio=[\d.]+%\))?', re.IGNORECASE)

    def _run_chdman_progress(self, cmd, animation_callback=None, base_label="Processing"):
        """Run a chdman command, streaming its own output so we can show its
        real percentage in the UI instead of a generic dot animation.

        chdman prints progress like "Compressing, 29.7% complete... (ratio=72.9%)"
        using carriage returns to update the same line, the same way a normal
        progress bar would in a terminal. Python's subprocess text-mode pipes
        translate \\r the same as \\n, so iterating over stdout still yields
        each update as its own "line".

        Continuously reading stdout as it comes in (rather than waiting for
        the process to finish first) also avoids the classic subprocess
        deadlock where a child blocks trying to write to a pipe nobody is
        draining — so this is safe to use for large files too.

        Note: some C programs fully buffer their output instead of flushing
        per line when stdout isn't an interactive terminal, which can make
        updates arrive in bursts rather than smoothly. If that turns out to
        be the case for chdman on a given platform, updates will just be
        chunkier rather than missing entirely.

        Returns:
            tuple: (returncode, last_output_line)
        """
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            **self._subprocess_kwargs()
        )

        last_line = ""
        try:
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                last_line = line
                if animation_callback:
                    match = self._PERCENT_RE.search(line)
                    if match:
                        percent = match.group(1)
                        ratio_part = f" {match.group(2)}" if match.group(2) else ""
                        animation_callback(f"   {base_label}: {percent}% complete{ratio_part}")
                    else:
                        animation_callback(f"   {base_label}...")
        finally:
            process.wait()

        return process.returncode, last_line
    
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
                return "sudo pacman -S mame"
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
                    ['kitty', '-e'],
                    ['alacritty', '-e'],
                    ['xterm', '-e'],
                ]
                
                install_script = f'{install_cmd}; echo "\n✅ Installation complete! Press Enter to close."; read'
                
                # PyInstaller onefile sets LD_LIBRARY_PATH to its own bundled libs
                # dir (e.g. /tmp/_MEIxxxxxx). Spawning an external GUI terminal
                # (Konsole, GNOME Terminal, etc.) with that inherited makes it try
                # to load its system libraries but pick up our older bundled
                # libssl/libcrypto instead, causing a version mismatch and instant
                # crash before any window appears. Restore the original library
                # path (which PyInstaller saves off) for the child process only.
                clean_env = os.environ.copy()
                if 'LD_LIBRARY_PATH_ORIG' in clean_env:
                    clean_env['LD_LIBRARY_PATH'] = clean_env['LD_LIBRARY_PATH_ORIG']
                else:
                    clean_env.pop('LD_LIBRARY_PATH', None)
                
                terminal_opened = False
                for terminal in terminals:
                    try:
                        subprocess.Popen(terminal + ['bash', '-c', install_script], env=clean_env)
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
        
        # chdman does not support DiscJuggler .cdi images. Modern versions
        # (0.139+) will accept the file and report "success" but produce a
        # broken/unbootable CHD (0 tracks, 0 length) instead of failing
        # loudly, so we refuse it here rather than let it silently corrupt.
        if source_ext == '.cdi':
            if log_callback:
                log_callback(_("   [x] Skipped: .cdi (DiscJuggler) format is not supported by chdman — convert to GDI first"))
            return False, None
        
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
                if log_callback and is_dvd:
                    log_callback(f"   [!] Note: PS2/DVD conversion may take longer than other formats")
                    log_callback(f"   Please wait... (app may appear frozen)")
                
                label = "Processing (Large DVD - please wait)" if is_dvd else "Processing"
                returncode, last_output = self._run_chdman_progress(
                    cmd, animation_callback=animation_callback, base_label=label
                )
                
                if returncode == 0:
                    if delete_after:
                        self._safe_delete_originals(
                            source_path, source_ext, chd_path, log_callback)
                    return True, chd_path
                else:
                    if log_callback:
                        log_callback(f"   [x] Conversion failed (return code: {returncode})")
                    return False, None
            
            else:
                returncode, last_output = self._run_chdman_progress(
                    cmd, animation_callback=animation_callback, base_label="Processing"
                )
                
                if returncode == 0:
                    if delete_after:
                        self._safe_delete_originals(
                            source_path, source_ext, chd_path, log_callback)
                    return True, chd_path
                else:
                    if log_callback:
                        log_callback(f"   [x] Failed: {last_output[:100]}")
                    return False, None
        
        except Exception as e:
            if log_callback:
                log_callback(f"   [x] Error: {str(e)}")
            return False, None
    
    def extract_folder(self, folder, log_callback=None, progress_callback=None,
                       animation_callback=None, cancel_check=None):
        """Extract all CHD files in a folder back to their original format.

        Returns:
            tuple: (extracted, skipped, failed)
        """
        if not self.chdman_path:
            self.chdman_path = self.find_chdman()
            if not self.chdman_path:
                return 0, 0, 0

        from pathlib import Path
        chd_files = list(Path(folder).glob("*.chd"))

        if not chd_files:
            if log_callback:
                log_callback("[x] No CHD files found in folder")
            return 0, 0, 0

        total = len(chd_files)
        if log_callback:
            log_callback(f"Found {total} CHD file(s) to extract\n")

        extracted = skipped = failed = 0

        for index, chd_file in enumerate(chd_files, 1):
            if cancel_check and cancel_check():
                if log_callback:
                    log_callback("[!] Extraction cancelled by user")
                break

            filename = chd_file.name
            if progress_callback:
                progress_callback(index, total, filename)

            if log_callback:
                log_callback(f">> {filename}")

            success, out_path = self.extract_file(
                chd_file,
                log_callback=log_callback,
                animation_callback=animation_callback
            )

            if cancel_check and cancel_check():
                if out_path and os.path.exists(out_path):
                    try:
                        os.remove(out_path)
                    except Exception:
                        pass
                if log_callback:
                    log_callback("[!] Extraction cancelled by user")
                break

            if success:
                if log_callback:
                    log_callback(f"   [✓] Extracted successfully")
                extracted += 1
            else:
                failed += 1

        return extracted, skipped, failed

    def extract_file(self, chd_file, log_callback=None, animation_callback=None):
        """Extract a single CHD file to its original format.

        Returns:
            tuple: (success, output_path)
        """
        chd_path = str(chd_file)
        out_dir = str(chd_file.parent)
        stem = chd_file.stem

        # Try extractcd first (for CD-based games: PS1, Dreamcast, Saturn, etc.)
        # Output will be a .cue + .bin set
        cue_out = os.path.join(out_dir, stem + ".cue")
        bin_out = os.path.join(out_dir, stem + ".bin")

        # Skip if output already exists
        if os.path.exists(cue_out):
            if log_callback:
                log_callback(f"   Skipped: {stem}.cue already exists")
            return True, cue_out

        cmd = [self.chdman_path, 'extractcd', '-i', chd_path, '-o', cue_out, '-ob', bin_out]

        try:
            returncode, last_output = self._run_chdman_progress(
                cmd, animation_callback=animation_callback, base_label="Processing (extracting)"
            )

            if returncode == 0:
                return True, cue_out

            # extractcd failed — try extractdvd (for DVD ISOs: PS2, Xbox, etc.)
            iso_out = os.path.join(out_dir, stem + ".iso")
            if os.path.exists(cue_out):
                try:
                    os.remove(cue_out)
                except Exception:
                    pass

            cmd_dvd = [self.chdman_path, 'extractdvd', '-i', chd_path, '-o', iso_out]
            returncode2, last_output2 = self._run_chdman_progress(
                cmd_dvd, animation_callback=animation_callback, base_label="Processing DVD (extracting)"
            )

            if returncode2 == 0:
                return True, iso_out

            if log_callback:
                log_callback(f"   [x] Extraction failed: {last_output2[:100]}")
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
