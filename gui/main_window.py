"""
RomMate - ROM companion tool
Copyright (C) 2026 Rodrigo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    import tkinter as tk
    DND_AVAILABLE = True
except ImportError:
    import tkinter as tk
    DND_AVAILABLE = False
    print("Warning: tkinterdnd2 not available. Drag & drop disabled.")
from tkinter import filedialog, scrolledtext, messagebox, ttk
import os
import re
from pathlib import Path
import threading
import subprocess
import platform
import shutil
from gui.theme import Theme
from gui.settings_panel import SettingsPanel
from utils.sounds import SoundPlayer
from core.file_utils import normalize_path, detect_available_formats, find_multidisc_games, create_m3u_file
from gui.dialogs import show_format_choice_dialog, show_info_dialog
from core.chd_converter import CHDConverter
from core.m3u_creator import M3UCreator
from core.rom_health import ROMHealthChecker
from utils.config import Config

class RomMateGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RomMate")
        self.root.geometry("700x1000")
        self.root.resizable(True, True)

        # Load config
        self.config = Config()

        # Apply saved theme before reading Theme colors
        saved_theme = self.config.get('theme', 'dark')
        import gui.theme as theme_module
        theme_module.set_theme(saved_theme)

        # Initialize app state (variables that survive UI rebuilds)
        self._init_state()

        # Build UI
        self._apply_theme_colors()
        self.root.configure(bg=self.bg_dark)
        self.create_widgets()
        self._create_settings_panel()

        if DND_AVAILABLE:
            self.setup_drag_and_drop()

    # ------------------------------------------------------------------ #
    #  State & theme helpers                                               #
    # ------------------------------------------------------------------ #

    def _init_state(self):
        """Initialize non-UI state. Called once; survives UI rebuilds."""
        # Only create these once so we don't reset in-progress state
        if not hasattr(self, 'folder_path'):
            self.folder_path      = tk.StringVar()
            self.operation_mode   = tk.StringVar(value="chd")
            self.m3u_file_type    = tk.StringVar(value="all")
            self.delete_after_conversion = tk.BooleanVar(value=False)
            self.sounds_enabled   = tk.BooleanVar(value=True)

        if not hasattr(self, 'sound_player'):
            self.sound_player = SoundPlayer()
            self.sound_player.volume        = self.config.get('sound_volume', 1.0)
            self.sound_player.sounds_enabled = self.config.get('sound_enabled', True)
            self.sounds_enabled.set(self.sound_player.sounds_enabled)

        if not hasattr(self, 'chd_converter'):
            self.chd_converter = CHDConverter()
        if not hasattr(self, 'm3u_creator'):
            self.m3u_creator = M3UCreator()
        if not hasattr(self, 'rom_health'):
            self.rom_health = ROMHealthChecker()

        # Processing state
        self.is_processing    = False
        self.cancel_requested = False
        self.spinner_running  = False
        self.spinner_chars    = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        self.spinner_index    = 0

    def _apply_theme_colors(self):
        """Read current Theme class values into instance attributes."""
        from gui.theme import Theme
        self.bg_dark       = Theme.BG_DARK
        self.bg_frame      = Theme.BG_FRAME
        self.bg_processing = Theme.BG_PROCESSING
        self.bg_info_box   = Theme.BG_INFO_BOX

        self.text_light      = Theme.TEXT_LIGHT
        self.text_gray       = Theme.TEXT_GRAY
        self.text_processing = Theme.TEXT_PROCESSING
        self.text_info       = Theme.TEXT_INFO
        self.text_error      = Theme.TEXT_ERROR
        self.text_success    = Theme.TEXT_SUCCESS

        self.accent_blue   = Theme.ACCENT_BLUE
        self.accent_green  = Theme.ACCENT_GREEN
        self.accent_red    = Theme.ACCENT_RED
        self.accent_orange = Theme.ACCENT_ORANGE

        self.state_success = Theme.STATE_SUCCESS
        self.state_warning = Theme.STATE_WARNING
        self.state_error   = Theme.STATE_ERROR

        self.active_green = Theme.ACTIVE_GREEN
        self.active_red   = Theme.ACTIVE_RED
        self.active_blue  = Theme.ACTIVE_BLUE

    def _create_settings_panel(self):
        """(Re-)create the SettingsPanel after the main UI exists."""
        self.settings_panel = SettingsPanel(
            self.root,
            self.config,
            callbacks={
                'get_sounds_enabled':          lambda: self.sounds_enabled.get(),
                'on_sound_toggle':             self.on_sound_toggle,
                'get_delete_after_conversion': lambda: self.delete_after_conversion.get(),
                'on_delete_toggle':            self.on_delete_toggle,
                'on_volume_change':            self.on_volume_change,
                'show_help':                   self.show_info,
                'on_close':                    self.hide_settings_panel,
                'reload_theme':                self.reload_theme,
            }
        )

    # ------------------------------------------------------------------ #
    #  Theme reload — the safe way                                         #
    # ------------------------------------------------------------------ #

    def reload_theme(self, theme_name):
        """Switch theme by destroying only widgets and rebuilding the UI."""
        # Preserve user state across rebuild
        saved_folder = self.folder_path.get()
        saved_mode   = self.operation_mode.get()

        # Apply new theme to the module-level Theme class
        import gui.theme as theme_module
        theme_module.set_theme(theme_name)

        # Destroy every widget (but NOT the Tk root itself)
        for widget in self.root.winfo_children():
            widget.destroy()

        # Refresh color attributes from the updated Theme class
        self._apply_theme_colors()
        self.root.configure(bg=self.bg_dark)

        # Rebuild UI (state variables are untouched)
        self.create_widgets()
        self._create_settings_panel()

        if DND_AVAILABLE:
            self.setup_drag_and_drop()

        # Restore user state
        self.folder_path.set(saved_folder)
        self.operation_mode.set(saved_mode)
        self.update_info_section()

    # ------------------------------------------------------------------ #
    #  Spinner                                                             #
    # ------------------------------------------------------------------ #

    def start_spinner(self):
        self.spinner_running = True
        self.update_spinner()

    def stop_spinner(self):
        self.spinner_running = False

    def update_spinner(self):
        if not self.spinner_running:
            return
        spinner = self.spinner_chars[self.spinner_index]
        current_text = self.status_title.cget("text")
        if any(ch in current_text for ch in self.spinner_chars):
            current_text = current_text.split()[0] + " " + " ".join(current_text.split()[1:-1])
        self.status_title.config(text=f"{current_text} {spinner}")
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
        self.root.after(100, self.update_spinner)

    # ------------------------------------------------------------------ #
    #  Panel switching                                                     #
    # ------------------------------------------------------------------ #

    def show_main_panel(self):
        self.main_container.pack(fill="both", expand=True, padx=30, pady=20)
        self.processing_panel.pack_forget()

    def show_processing_panel(self):
        self.main_container.pack_forget()
        self.processing_panel.pack(fill="both", expand=True, padx=30, pady=20)

        self.cancel_requested = False
        self.status_title.config(text="Starting", fg=self.text_light)
        self.status_subtitle.config(text="Initializing")
        self.file_counter_label.config(text="0 / 0 files")
        self.current_file_label.config(text="")

        self.processing_log.config(state="normal")
        self.processing_log.delete(1.0, tk.END)
        self.processing_log.config(state="disabled")

        self.cancel_frame.pack(pady=10)
        self.completion_frame.pack_forget()
        self.start_spinner()

    def update_processing_status(self, title, subtitle, progress=None, total=None, current_file=""):
        was_spinning = self.spinner_running
        if was_spinning:
            self.stop_spinner()
        self.status_title.config(text=title)
        self.status_subtitle.config(text=subtitle)
        if progress is not None and total is not None and total > 0:
            self.file_counter_label.config(text=f"{progress} / {total} files")
        if current_file:
            self.current_file_label.config(text=f"📄 {current_file}")
        if was_spinning:
            self.start_spinner()
        self.root.update_idletasks()

    def log_to_processing(self, message):
        self.processing_log.config(state="normal")
        self.processing_log.insert(tk.END, message + "\n")
        self.processing_log.see(tk.END)
        self.processing_log.config(state="disabled")
        self.root.update_idletasks()

    def animate_processing_dots(self, text):
        try:
            self.processing_log.config(state='normal')
            current_text = self.processing_log.get("end-2c linestart", "end-1c")
            if current_text.strip().startswith("Processing"):
                log_position = self.processing_log.index("end-2c linestart")
                self.processing_log.delete(log_position, "end-1c")
                self.processing_log.insert(log_position, text + "\n")
            else:
                self.processing_log.insert("end", text + "\n")
            self.processing_log.config(state='disabled')
            self.processing_log.see("end")
            self.root.update_idletasks()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Drag & drop                                                         #
    # ------------------------------------------------------------------ #

    def setup_drag_and_drop(self):
        self.folder_entry.drop_target_register(DND_FILES)
        self.folder_entry.dnd_bind('<<Drop>>', self.on_drop)

    def on_drop(self, event):
        try:
            dropped_path = event.data.strip('{}').strip()
            if ' ' in dropped_path and not os.path.exists(dropped_path):
                dropped_path = dropped_path.split()[0].strip('{}')
            dropped_path = normalize_path(dropped_path)
            if os.path.isdir(dropped_path):
                self.update_folder_display(dropped_path)
                self.config.set('last_folder', dropped_path)
            else:
                parent_dir = os.path.dirname(dropped_path)
                self.update_folder_display(parent_dir)
                self.config.set('last_folder', parent_dir)
        except Exception as e:
            print(f"Error handling drop: {e}")

    # ------------------------------------------------------------------ #
    #  Folder entry helpers                                                #
    # ------------------------------------------------------------------ #

    def add_placeholder_to_entry(self):
        placeholder = "⬇️  Drop folder here"
        self.folder_entry.config(justify='center')
        if not self.folder_path.get():
            self.folder_entry.insert(0, placeholder)
            self.folder_entry.config(fg=self.text_gray)

        def on_focus_in(event):
            if self.folder_entry.get() == placeholder:
                self.folder_entry.delete(0, tk.END)
                self.folder_entry.config(fg=self.text_light, justify='left')

        def on_focus_out(event):
            if not self.folder_entry.get():
                self.folder_entry.insert(0, placeholder)
                self.folder_entry.config(fg=self.text_gray, justify='center')

        self.folder_entry.bind('<FocusIn>',  on_focus_in)
        self.folder_entry.bind('<FocusOut>', on_focus_out)

    def update_folder_display(self, folder):
        self.folder_path.set(folder)
        self.folder_entry.config(fg=self.text_light, justify='left')

    # ------------------------------------------------------------------ #
    #  Completion / cancel                                                 #
    # ------------------------------------------------------------------ #

    def show_completion(self, success=True, converted=0, skipped=0, failed=0):
        self.stop_spinner()
        self.cancel_frame.pack_forget()
        self.sound_player.play("success" if success else "fail", self.sound_player.volume)

        mode = self.operation_mode.get()
        if mode == "health":
            if success and failed == 0:
                self.status_title.config(text="✅ All ROMs Verified Successfully!", fg=self.accent_green)
                self.status_subtitle.config(text="All CHD files passed verification")
                self.processing_panel.config(bg=self.state_success)
            elif converted > 0:
                self.status_title.config(text="⚠️ Health Check Complete with Issues", fg=self.accent_orange)
                self.status_subtitle.config(text="Some files failed verification - check details above")
                self.processing_panel.config(bg=self.state_warning)
            else:
                self.status_title.config(text="❌ Health Check Failed", fg=self.accent_red)
                self.status_subtitle.config(text="No files verified successfully")
                self.processing_panel.config(bg=self.state_error)
        else:
            if success:
                self.status_title.config(text="✅ Completed Successfully!", fg=self.accent_green)
                self.status_subtitle.config(text="All operations finished")
                self.processing_panel.config(bg=self.state_success)
            else:
                self.status_title.config(text="⚠️ Completed with Errors", fg=self.accent_red)
                self.status_subtitle.config(text="Some operations failed - check details below")
                self.processing_panel.config(bg=self.state_error)

        self.completion_frame.pack(pady=20)
        self.root.update_idletasks()

    def reset_and_return(self):
        self.is_processing = False
        self.processing_panel.config(bg=self.bg_frame)
        self.show_main_panel()

    def cancel_processing(self):
        if not self.is_processing:
            return
        if messagebox.askyesno(
            "Cancel Processing",
            "Are you sure you want to cancel?\n\nAny incomplete CHD files will be deleted.",
            icon='warning'
        ):
            self.cancel_requested = True
            self.log_to_processing("\n⚠️ Cancellation requested...")
            self.log_to_processing("Cleaning up and returning to main screen...")

    # ------------------------------------------------------------------ #
    #  Widget construction                                                 #
    # ------------------------------------------------------------------ #

    def create_widgets(self):
        # Main container
        self.main_container = tk.Frame(self.root, bg=self.bg_dark)

        # Title section
        title_outer = tk.Frame(self.main_container, bg=self.bg_dark)
        title_outer.pack(fill="x", pady=(10, 5))

        tk.Button(
            title_outer, text="⚙️", command=self.show_settings_panel,
            font=("Arial", 20), bg=self.bg_dark, fg=self.text_light,
            cursor="hand2", relief="flat", activebackground=self.bg_frame,
            bd=0, highlightthickness=0, highlightbackground=self.bg_frame,
            highlightcolor=self.bg_frame, padx=10
        ).place(relx=1.0, x=-10, y=0, anchor="ne")

        tk.Label(
            title_outer, text="RomMate", font=("Arial", 24, "bold"),
            bg=self.bg_dark, fg=self.text_light
        ).pack()

        tk.Label(
            self.main_container,
            text="Your ROM companion - Convert, compress, and organize disc images",
            font=("Arial", 11), bg=self.bg_dark, fg=self.text_gray
        ).pack(pady=(0, 30))

        # Folder selection
        folder_frame = tk.Frame(self.main_container, bg=self.bg_dark)
        folder_frame.pack(pady=10, fill="x")

        tk.Label(
            folder_frame, text="Game Folder:", font=("Arial", 11, "bold"),
            bg=self.bg_dark, fg=self.text_light
        ).pack(side="left", padx=(0, 15))

        self.folder_entry = tk.Entry(
            folder_frame, textvariable=self.folder_path, width=50,
            font=("Arial", 11), bg=self.bg_frame, fg=self.text_light,
            insertbackground=self.text_light, relief="solid", bd=1,
            highlightthickness=2, highlightbackground=self.bg_dark,
            highlightcolor=self.accent_blue
        )
        self.folder_entry.pack(side="left", padx=10, fill="x", expand=True, ipady=6)
        self.add_placeholder_to_entry()

        tk.Button(
            folder_frame, text="Browse", command=self.browse_folder,
            font=("Arial", 10, "bold"), bg=self.accent_green, fg="white",
            cursor="hand2", padx=20, pady=8, relief="flat",
            activebackground=self.active_green, activeforeground="white", bd=0
        ).pack(side="left")

        # Disc-Based ROMs section
        disc_frame = tk.Frame(self.main_container, bg=self.bg_frame, relief="groove", bd=2)
        disc_frame.pack(pady=20, fill="x")

        tk.Label(
            disc_frame, text="📀 Disc-Based ROMs", font=("Arial", 12, "bold"),
            bg=self.bg_frame, fg=self.text_light
        ).pack(anchor="w", padx=25, pady=(15, 10))

        for text, value in [
            ("💾 Convert to CHD (compress disc images)", "chd"),
            ("📁 Create M3U Playlists (for multi-disc games)", "m3u"),
            ("🔄 Convert to CHD + Create M3U Playlists", "both"),
        ]:
            tk.Radiobutton(
                disc_frame, text=text, variable=self.operation_mode, value=value,
                font=("Arial", 11), command=self.update_info_section,
                bg=self.bg_frame, fg=self.text_light, selectcolor=self.bg_dark,
                activebackground=self.bg_frame, bd=0, highlightthickness=0
            ).pack(anchor="w", padx=25, pady=8)

        tk.Frame(disc_frame, height=1, bg=self.text_gray).pack(fill="x", padx=25, pady=15)

        tk.Button(
            disc_frame, text="ℹ️  Help - When to use each?", command=self.show_info,
            font=("Arial", 10), bg=self.accent_blue, fg="white",
            cursor="hand2", relief="flat", padx=15, pady=6
        ).pack(anchor="w", padx=25, pady=(0, 15))

        # ROM Tools section
        rom_tools_frame = tk.Frame(self.main_container, bg=self.bg_frame, relief="groove", bd=2)
        rom_tools_frame.pack(pady=20, fill="x")

        tk.Label(
            rom_tools_frame, text="🎮 ROM Tools (All ROM Types)",
            font=("Arial", 12, "bold"), bg=self.bg_frame, fg=self.text_light
        ).pack(anchor="w", padx=25, pady=(15, 10))

        for text, value in [
            ("🔍 Check ROM Health", "health"),
            ("✏️  Validate & Fix ROM Names", "validate"),
        ]:
            tk.Radiobutton(
                rom_tools_frame, text=text, variable=self.operation_mode, value=value,
                font=("Arial", 11), command=self.update_info_section,
                bg=self.bg_frame, fg=self.text_light, selectcolor=self.bg_dark,
                activebackground=self.bg_frame, bd=0, highlightthickness=0
            ).pack(anchor="w", padx=25, pady=8)

        # Info section
        self.info_frame = tk.Frame(self.main_container, bg=self.bg_frame, relief="groove", bd=2, height=185)
        self.info_frame.pack(pady=20, fill="x")
        self.info_frame.pack_propagate(False)

        self.info_title = tk.Label(
            self.info_frame, text="ℹ️  Info", font=("Arial", 12, "bold"),
            bg=self.bg_frame, fg=self.text_light
        )
        self.info_title.pack(anchor="w", padx=25, pady=(15, 10))

        self.info_content = tk.Frame(self.info_frame, bg=self.bg_frame)
        self.info_content.pack(fill="x", padx=25, pady=(0, 15))

        # Process button — created BEFORE create_info_sections so
        # update_info_section() can safely reference it
        self.process_btn = tk.Button(
            self.main_container, text="▶ Start Operation",
            command=self.run_process, font=("Arial", 14, "bold"),
            bg=self.accent_blue, fg="white", cursor="hand2",
            height=2, padx=50, relief="flat", width=15
        )
        self.process_btn.pack(pady=30)

        # Build info sub-frames (calls update_info_section internally,
        # which is now safe because process_btn already exists)
        self.create_info_sections()

        # Processing panel
        self.processing_panel = tk.Frame(self.root, bg=self.bg_frame, relief="groove", bd=2)

        status_header = tk.Frame(self.processing_panel, bg=self.bg_frame)
        status_header.pack(fill="x", pady=20, padx=30)

        self.status_title = tk.Label(
            status_header, text="Processing...", font=("Arial", 20, "bold"),
            bg=self.bg_frame, fg=self.text_light
        )
        self.status_title.pack()

        self.status_subtitle = tk.Label(
            status_header, text="Starting operation", font=("Arial", 12),
            bg=self.bg_frame, fg=self.text_gray
        )
        self.status_subtitle.pack(pady=(5, 0))

        self.current_file_label = tk.Label(
            self.processing_panel, text="", font=("Consolas", 11),
            bg=self.bg_frame, fg=self.accent_blue, wraplength=700
        )
        self.current_file_label.pack(pady=(10, 20))

        self.file_counter_label = tk.Label(
            self.processing_panel, text="0 / 0 files", font=("Arial", 13, "bold"),
            bg=self.bg_frame, fg=self.text_light
        )
        self.file_counter_label.pack(pady=(0, 20))

        tk.Frame(self.processing_panel, height=2, bg=self.text_gray).pack(fill="x", padx=30, pady=10)

        tk.Label(
            self.processing_panel, text="Details:", font=("Arial", 11, "bold"),
            bg=self.bg_frame, fg=self.text_light
        ).pack(anchor="w", padx=30, pady=(10, 5))

        log_border = tk.Frame(self.processing_panel, bg=self.text_gray, relief="solid", bd=1)
        log_border.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        self.processing_log = scrolledtext.ScrolledText(
            log_border, width=80, height=12, font=("Consolas", 9),
            bg=self.bg_processing, fg=self.text_processing,
            wrap=tk.WORD, state="disabled", relief="flat", bd=0, padx=10, pady=8
        )
        self.processing_log.pack(fill="both", expand=True, padx=1, pady=1)

        self.cancel_frame = tk.Frame(self.processing_panel, bg=self.bg_frame)
        self.cancel_frame.pack(pady=10)

        self.cancel_btn = tk.Button(
            self.cancel_frame, text="✖ Cancel", command=self.cancel_processing,
            font=("Arial", 11, "bold"), bg=self.accent_red, fg="white",
            cursor="hand2", padx=25, pady=10, relief="flat",
            activebackground=self.active_red
        )
        self.cancel_btn.pack()

        self.completion_frame = tk.Frame(self.processing_panel, bg=self.bg_frame)
        btn_frame = tk.Frame(self.completion_frame, bg=self.bg_frame)
        btn_frame.pack()

        tk.Button(
            btn_frame, text="✓ Done - Return to Main", command=self.reset_and_return,
            font=("Arial", 12, "bold"), bg=self.accent_green, fg="white",
            cursor="hand2", padx=30, pady=12, relief="flat",
            activebackground=self.active_green, bd=0
        ).pack(side="left", padx=10)

        tk.Button(
            btn_frame, text="🔄 Process Another Folder", command=self.reset_and_return,
            font=("Arial", 11), bg=self.accent_blue, fg="white",
            cursor="hand2", padx=20, pady=12, relief="flat",
            activebackground=self.active_blue, bd=0
        ).pack(side="left", padx=10)

        self.show_main_panel()

    # ------------------------------------------------------------------ #
    #  Info sections                                                       #
    # ------------------------------------------------------------------ #

    def show_info(self):
        show_info_dialog(self.root)

    def create_info_sections(self):
        """Create all info section contents."""
        # CHD Info
        self.chd_info = tk.Frame(self.info_content, bg=self.bg_frame)
        for text, font, fg in [
            ("Converts: CUE, GDI, CDI, ISO → CHD format", ("Arial", 10), self.text_gray),
            ("Supported: PS1, PS2, Dreamcast, Saturn, PSP", ("Arial", 9), self.text_gray),
            ("Not supported: GameCube (use GCZ), Wii (use RVZ/WBFS)", ("Arial", 9, "italic"), self.accent_orange),
            ("• CHD files are compressed and save 40-60% space", ("Arial", 9), self.text_gray),
            ("• Supported by RetroArch and most modern emulators", ("Arial", 9), self.text_gray),
        ]:
            tk.Label(self.chd_info, text=text, font=font, fg=fg, bg=self.bg_frame).pack(anchor="w", pady=(0, 5))

        # M3U Info
        self.m3u_info = tk.Frame(self.info_content, bg=self.bg_frame)
        tk.Label(
            self.m3u_info, text="Scans for: CUE, GDI, CDI, ISO, CHD files",
            font=("Arial", 10), fg=self.text_gray, bg=self.bg_frame
        ).pack(anchor="w", pady=(0, 10))
        info_box = tk.Frame(self.m3u_info, bg=self.bg_info_box, relief="flat")
        info_box.pack(fill="x", pady=(0, 5))
        tk.Label(
            info_box,
            text="ℹ️ Note: All disc files must be in the same folder.\n"
                 "    Works with PSX, PS2, Dreamcast, Saturn, Sega CD, and more!\n"
                 "    If both CUE and CHD files exist, you'll be asked which to use.",
            font=("Arial", 9), bg=self.bg_info_box, fg=self.text_info, justify="left"
        ).pack(padx=15, pady=12, anchor="w")

        # Both Info
        self.both_info = tk.Frame(self.info_content, bg=self.bg_frame)
        for text, font in [
            ("Step 1: Convert all disc images to CHD", ("Arial", 10, "bold")),
            ("  Converts: CUE, GDI, CDI, ISO → CHD",  ("Arial", 9)),
            ("Step 2: Create M3U playlists for multi-disc games", ("Arial", 10, "bold")),
            ("  Groups CHD files into playlists", ("Arial", 9)),
        ]:
            tk.Label(self.both_info, text=text, font=font,
                     fg=self.text_light if "bold" in font else self.text_gray,
                     bg=self.bg_frame).pack(anchor="w", pady=(0, 5))

        # Health Info
        self.health_info = tk.Frame(self.info_content, bg=self.bg_frame)
        tk.Label(self.health_info, text="Check ROM files and identify games:",
                 font=("Arial", 10), fg=self.text_gray, bg=self.bg_frame).pack(anchor="w", pady=(0, 5))
        for text in [
            "• CHD Files: Full integrity verification ✓",
            "• Cartridge ROMs: Checksum verification ✓",
            "• ISO/CDI/GDI: Identification by name & size (Cannot verify disc image checksums)",
            "• Compare against No-Intro & Redump databases",
        ]:
            tk.Label(self.health_info, text=text, font=("Arial", 9),
                     fg=self.text_gray, bg=self.bg_frame).pack(anchor="w", pady=(0, 3))

        # Validate Info
        self.validate_info = tk.Frame(self.info_content, bg=self.bg_frame)
        tk.Label(self.validate_info, text="Checks and fixes ROM filenames:",
                 font=("Arial", 10), fg=self.text_gray, bg=self.bg_frame).pack(anchor="w", pady=(0, 5))
        for text in [
            "• Compares against No-Intro/Redump databases",
            "• Suggests correct naming conventions",
            "• Detects region and version information",
        ]:
            tk.Label(self.validate_info, text=text, font=("Arial", 9),
                     fg=self.text_gray, bg=self.bg_frame).pack(anchor="w", pady=(0, 3))

        # Show the correct section for the current mode
        self.update_info_section()

    def update_info_section(self):
        """Update the info section based on selected operation."""
        for frame in [self.chd_info, self.m3u_info, self.both_info,
                      self.health_info, self.validate_info]:
            frame.pack_forget()

        btn_labels = {
            "health":   ("▶ Check ROM Health",    self.health_info),
            "validate": ("▶ Validate ROM Names",  self.validate_info),
            "chd":      ("▶ Convert to CHD",       self.chd_info),
            "m3u":      ("▶ Create M3U Files",     self.m3u_info),
            "both":     ("▶ Convert & Create M3U", self.both_info),
        }
        label, frame = btn_labels.get(self.operation_mode.get(), ("▶ Start Operation", self.chd_info))
        frame.pack(fill="x", expand=True)
        # process_btn is always created before this method is called
        self.process_btn.config(text=label)

    # ------------------------------------------------------------------ #
    #  Browse / run process                                                #
    # ------------------------------------------------------------------ #

    def browse_folder(self):
        folder_mode = self.config.get('folder_mode', 'remember_last')
        initial_dir = (
            self.config.get('default_folder', str(Path.home()))
            if folder_mode == 'use_default'
            else self.config.get('last_folder', str(Path.home()))
        )
        folder = filedialog.askdirectory(title="Select Game Folder", initialdir=initial_dir)
        if folder:
            folder = normalize_path(folder)
            self.update_folder_display(folder)
            self.config.set('last_folder', folder)

    def run_process(self):
        folder = self.folder_path.get()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return
        if not os.path.exists(folder):
            messagebox.showerror("Error", f"Selected folder does not exist!\n\nPath: {folder}")
            return

        mode = self.operation_mode.get()
        if mode == "health":
            self.check_rom_health()
            return
        elif mode == "validate":
            self.validate_rom_names()
            return

        self.is_processing = True
        self.show_processing_panel()

        targets = {
            "m3u":  self.create_m3u_files,
            "chd":  self.convert_to_chd,
            "both": self.convert_and_create_m3u,
        }
        thread = threading.Thread(target=targets[mode], args=(folder,))
        thread.start()

    # ------------------------------------------------------------------ #
    #  Operations (unchanged logic, kept intact)                           #
    # ------------------------------------------------------------------ #

    def convert_to_chd(self, folder):
        try:
            self.update_processing_status("CHD Conversion", "Checking for chdman tool...", 0, 1)
            self.chd_converter.chdman_path = self.chd_converter.find_chdman()
            if not self.chd_converter.chdman_path:
                self.log_to_processing("❌ ERROR: chdman not found!")
                if platform.system() == 'Linux':
                    self.log_to_processing("\nOffering automatic installation...")
                    if self.chd_converter.prompt_install_chdman():
                        self.log_to_processing("\n⏳ Installation in progress.")
                        self.log_to_processing("Please complete installation in the terminal, then try again.")
                    else:
                        self.log_to_processing("\n❌ Installation cancelled.")
                else:
                    self.log_to_processing("\nchdman is required for CHD conversion.")
                    self.log_to_processing("It should be in the tools/ folder.")
                    messagebox.showerror("chdman Not Found", "chdman is required for CHD conversion.\n\nIt should be bundled in the tools/ folder.")
                self.show_completion(success=False)
                return

            try:
                test_result = subprocess.run([self.chd_converter.chdman_path, '--help'], capture_output=True, text=True, timeout=5)
                if test_result.returncode != 0 and platform.system() == 'Linux':
                    if 'error while loading shared libraries' in test_result.stderr:
                        self.log_to_processing("❌ ERROR: chdman has missing dependencies!")
                        self.log_to_processing(f"Error: {test_result.stderr[:150]}")
                        if self.chd_converter.prompt_install_chdman():
                            self.log_to_processing("\n⏳ Installation in progress.")
                            self.log_to_processing("Please complete installation in the terminal, then try again.")
                        else:
                            self.log_to_processing("\n❌ Installation cancelled.")
                        self.show_completion(success=False)
                        return
            except Exception as e:
                self.log_to_processing(f"⚠️ Warning: Could not test chdman: {e}")

            self.log_to_processing(f"✓ Found chdman: {self.chd_converter.chdman_path}")
            self.update_processing_status("CHD Conversion", "Scanning for disc images...")

            converted, skipped, failed = self.chd_converter.convert_folder(
                folder,
                delete_after=self.delete_after_conversion.get(),
                log_callback=self.log_to_processing,
                progress_callback=lambda current, total, filename: self.update_processing_status(
                    "Converting to CHD", f"Processing file {current} of {total}", current, total, filename),
                animation_callback=self.animate_processing_dots,
                cancel_check=lambda: self.cancel_requested
            )

            if self.cancel_requested:
                self.reset_and_return()
                return

            if converted == 0 and skipped == 0 and failed == 0:
                self.log_to_processing("\n❌ No convertible files found.")
                self.log_to_processing("Supported formats: CUE, GDI, CDI, ISO")
                messagebox.showinfo("No Files", "No convertible disc images found.")
                self.show_completion(success=False)
                return

            self.log_to_processing("\n" + "=" * 60)
            self.log_to_processing(f"✅ Converted: {converted} | ⏭️ Skipped: {skipped} | ❌ Failed: {failed}")
            self.log_to_processing("=" * 60)

            if self.cancel_requested:
                self.reset_and_return()
                return

            self.show_completion(success=failed == 0, converted=converted, skipped=skipped, failed=failed)
            messagebox.showinfo("Conversion Complete", f"CHD conversion finished!\n\nConverted: {converted}\nSkipped: {skipped}\nFailed: {failed}")

        except Exception as e:
            self.log_to_processing(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_completion(success=False)

    def create_m3u_files(self, folder):
        try:
            self.update_processing_status("M3U Creator", "Detecting available disc formats...")
            created, skipped, cancelled = self.m3u_creator.auto_detect_and_create(
                folder,
                log_callback=self.log_to_processing,
                progress_callback=lambda current, total, filename: self.update_processing_status(
                    "Creating M3U Playlists", f"Processing game {current} of {total}", current, total, filename),
                format_choice_callback=lambda: show_format_choice_dialog(self.root)
            )
            if cancelled:
                self.reset_and_return()
                return
            if created == 0 and skipped == 0:
                self.log_to_processing("❌ No multi-disc games found.")
                self.log_to_processing("\nMake sure files follow naming conventions like:")
                self.log_to_processing("  • Game Name (Disc 1).cue")
                self.log_to_processing("  • Game Name (Disc 2).chd")
                messagebox.showinfo("No Games Found", "No multi-disc games were found.")
                self.show_completion(success=False)
            else:
                self.log_to_processing(f"\n{'=' * 60}")
                self.log_to_processing(f"✅ Created: {created} | ⚠️ Skipped: {skipped}")
                self.log_to_processing(f"{'=' * 60}\n✅ ALL OPERATIONS COMPLETE!\n{'=' * 60}")
                self.show_completion(success=True, converted=created, skipped=skipped)
                messagebox.showinfo("M3U Creation Complete", f"M3U playlist creation finished!\n\nCreated: {created}\nSkipped: {skipped}")
        except Exception as e:
            self.log_to_processing(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_completion(success=False)

    def convert_and_create_m3u(self, folder):
        try:
            self.update_processing_status("CHD + M3U", "Step 1: Checking for chdman...")
            self.chd_converter.chdman_path = self.chd_converter.find_chdman()
            if not self.chd_converter.chdman_path:
                self.log_to_processing("❌ ERROR: chdman not found!")
                if platform.system() == "Linux":
                    if self.chd_converter.prompt_install_chdman():
                        self.log_to_processing("⏳ Installation in progress.")
                    else:
                        self.log_to_processing("❌ Installation cancelled.")
                else:
                    messagebox.showerror("chdman Not Found", "chdman is required.")
                self.show_completion(success=False)
                return

            try:
                test_result = subprocess.run([self.chd_converter.chdman_path, "--help"], capture_output=True, text=True, timeout=5)
                if test_result.returncode != 0 and platform.system() == "Linux":
                    if "error while loading shared libraries" in test_result.stderr:
                        self.log_to_processing("❌ ERROR: chdman has missing dependencies!")
                        if self.chd_converter.prompt_install_chdman():
                            self.log_to_processing("⏳ Installation in progress.")
                        else:
                            self.log_to_processing("❌ Installation cancelled.")
                        self.show_completion(success=False)
                        return
            except Exception as e:
                self.log_to_processing(f"⚠️ Warning: Could not test chdman: {e}")

            self.log_to_processing(f"✓ Found chdman: {self.chd_converter.chdman_path}")
            self.log_to_processing("\n=== STEP 1: CHD Conversion ===")

            converted, skipped, failed = self.chd_converter.convert_folder(
                folder,
                delete_after=self.delete_after_conversion.get(),
                log_callback=self.log_to_processing,
                progress_callback=lambda current, total, filename: self.update_processing_status(
                    "Step 1: Converting to CHD", f"Processing file {current} of {total}", current, total, filename),
                animation_callback=self.animate_processing_dots,
                cancel_check=lambda: self.cancel_requested
            )

            self.log_to_processing(f"\nStep 1 complete: Converted {converted} file(s)" if converted > 0 or skipped > 0 else "No files found to convert")
            self.log_to_processing("\n=== STEP 2: M3U Creation ===\n")
            self.update_processing_status("Step 2: Creating M3U", "Scanning for multi-disc games...")

            multidisc_games = find_multidisc_games(folder, extensions=["*.chd"], log_callback=self.log_to_processing)
            created = 0

            if multidisc_games:
                total_games = len(multidisc_games)
                self.log_to_processing(f"Found {total_games} multi-disc game(s)\n")
                for index, (game_name, disc_files) in enumerate(multidisc_games.items(), 1):
                    self.update_processing_status("Step 2: Creating M3U", f"Processing game {index} of {total_games}", index, total_games, f"{game_name}.m3u")
                    if create_m3u_file(game_name, disc_files, folder, self.log_to_processing):
                        created += 1
                self.log_to_processing(f"\nStep 2 complete: Created {created} M3U file(s)")
            else:
                self.log_to_processing("No multi-disc games found")

            self.log_to_processing("\n" + "=" * 60 + "\n✅ ALL OPERATIONS COMPLETE!\n" + "=" * 60)

            if self.cancel_requested:
                self.reset_and_return()
                return

            self.show_completion(success=True, converted=created, skipped=0, failed=0)

        except Exception as e:
            self.log_to_processing(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_completion(success=False)

    def check_rom_health(self):
        folder = self.folder_path.get()
        if not self.rom_health.find_chdman():
            if messagebox.askyesno(
                "chdman Not Found",
                "chdman is required for CHD verification.\n\nCartridge ROMs can still be checked.\n\nWould you like to install chdman now?",
                icon='warning'
            ):
                self.chd_converter.prompt_install_chdman()
                return

        self.show_processing_panel()
        self.is_processing = True
        self.processing_log.delete(1.0, tk.END)
        self.log_to_processing(f"🔍 ROM Health Check\n\nFolder: {folder}\n{'=' * 60}")
        self.start_spinner()

        def run_check():
            try:
                results = self.rom_health.check_folder(
                    folder,
                    log_callback=self.log_to_processing,
                    progress_callback=lambda current, total, filename: self.update_processing_status(
                        "Checking ROM Health", f"Verifying file {current} of {total}", current, total, filename),
                    cancel_check=lambda: self.cancel_requested
                )

                if self.cancel_requested:
                    self.reset_and_return()
                    return

                total_verified = results['chd_verified'] + results['cue_verified'] + results['cart_verified']
                total_issues   = results['chd_failed'] + results['cue_failed'] + results['cart_has_header'] + results['cart_unknown'] + results['cart_failed']

                self.log_to_processing("\n" + "=" * 60 + "\n📊 Summary:\n" + "=" * 60)
                if results['chd_verified'] + results['chd_failed'] > 0:
                    self.log_to_processing(f"CHD Files: ✅ {results['chd_verified']} verified | ❌ {results['chd_failed']} failed")
                if results['cue_verified'] + results['cue_failed'] > 0:
                    self.log_to_processing(f"CUE/BIN: ✅ {results['cue_verified']} verified | ❌ {results['cue_failed']} failed")
                if (results['cart_verified'] + results['cart_has_header'] + results.get('cart_hacks', 0) + results['cart_unknown'] + results['cart_failed']) > 0:
                    self.log_to_processing(
                        f"Game Files: ✅ {results['cart_verified']} verified | "
                        f"⚠️ {results['cart_has_header']} have headers | "
                        f"🎨 {results.get('cart_hacks', 0)} ROM hacks | "
                        f"❓ {results['cart_unknown']} unknown | "
                        f"❌ {results['cart_failed']} failed"
                    )
                self.log_to_processing("=" * 60)

                if self.cancel_requested:
                    self.reset_and_return()
                    return

                if results.get('cart_has_header', 0) > 0:
                    self.root.after(100, lambda: self.offer_header_fix(results))

                if total_issues == 0 and total_verified > 0:
                    self.show_completion(success=True, converted=total_verified, skipped=0, failed=0)
                elif total_verified > 0:
                    self.show_completion(success=False, converted=total_verified, skipped=0, failed=total_issues)
                else:
                    self.show_completion(success=False, converted=0, skipped=0, failed=total_issues)

            except Exception as e:
                self.log_to_processing(f"\n❌ Error: {str(e)}")
                import traceback
                self.log_to_processing(traceback.format_exc())
                self.show_completion(success=False)
            finally:
                self.is_processing = False

        threading.Thread(target=run_check, daemon=True).start()

    def validate_rom_names(self):
        from core.name_validator import NameValidator
        if not hasattr(self, 'name_validator'):
            self.name_validator = NameValidator()
        self.is_processing    = True
        self.cancel_requested = False
        self.show_processing_panel()
        threading.Thread(target=self.run_validation, args=(self.folder_path.get(),), daemon=True).start()

    def run_validation(self, folder):
        try:
            self.log_to_processing(f"🔍 ROM Name Validator\nFolder: {folder}\n{'=' * 60}")
            results = self.name_validator.validate_folder(
                folder,
                log_callback=self.log_to_processing,
                progress_callback=lambda current, total, filename:
                    self.log_to_processing(f"Processing file {current} of {total}: {filename}"),
                cancel_check=lambda: self.cancel_requested
            )
            if self.cancel_requested:
                self.reset_and_return()
                return
            self.log_to_processing("\n" + "=" * 60 + "\n📊 Summary:\n" + "=" * 60)
            if not results:
                self.log_to_processing("✅ All ROM names are correct!")
                self.show_completion(success=True, converted=0, skipped=0, failed=0)
            else:
                self.log_to_processing(f"📝 Found {len(results)} ROM(s) that need renaming")
                self.root.after(100, lambda: self.show_rename_dialog(results))
        except Exception as e:
            self.log_to_processing(f"\n❌ Error: {str(e)}")
            import traceback
            self.log_to_processing(traceback.format_exc())
            self.show_completion(success=False, converted=0, skipped=0, failed=1)

    # ------------------------------------------------------------------ #
    #  Dialogs (unchanged logic)                                           #
    # ------------------------------------------------------------------ #

    def show_rename_dialog(self, results):
        dialog = tk.Toplevel(self.root)
        dialog.title("ROM Name Validator - Review Changes")
        dialog.configure(bg=self.bg_dark)
        dialog.transient(self.root)
        dialog.grab_set()
        w, h = 900, 600
        x = (dialog.winfo_screenwidth()  // 2) - (w // 2)
        y = (dialog.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        dialog.minsize(900, 600)

        title_frame = tk.Frame(dialog, bg=self.accent_blue, height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text=f"📝 Review ROM Names ({len(results)} files need renaming)",
                 font=("Arial", 14, "bold"), bg=self.accent_blue, fg="white").pack(expand=True)

        content = tk.Frame(dialog, bg=self.bg_dark, padx=20, pady=20)
        content.pack(fill="both", expand=True)

        list_frame = tk.Frame(content, bg=self.bg_frame, relief="sunken", bd=1)
        list_frame.pack(fill="both", expand=True, pady=(0, 15))

        canvas    = tk.Canvas(list_frame, bg=self.bg_frame, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.bg_frame)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        rename_vars = []
        for idx, result in enumerate(results):
            item_frame = tk.Frame(scrollable_frame, bg=self.bg_frame, pady=10, padx=10)
            item_frame.pack(fill="x", padx=5, pady=5)
            if idx > 0:
                tk.Frame(item_frame, bg=self.text_gray, height=1).pack(fill="x", pady=(0, 10))
            var = tk.BooleanVar(value=True)
            rename_vars.append((var, result))
            tk.Checkbutton(item_frame, text="Rename this file", variable=var,
                           font=("Arial", 10, "bold"), bg=self.bg_frame, fg=self.text_light,
                           selectcolor=self.bg_dark, activebackground=self.bg_frame).pack(anchor="w")
            tk.Label(item_frame, text=f"Current:  {result['current_name']}",
                     font=("Arial", 9), fg=self.text_error, bg=self.bg_frame, anchor="w").pack(fill="x", padx=20, pady=(5, 2))
            tk.Label(item_frame, text=f"Suggested: {result['suggested_name']}",
                     font=("Arial", 9), fg=self.text_success, bg=self.bg_frame, anchor="w").pack(fill="x", padx=20, pady=(2, 2))
            tk.Label(item_frame, text=f"Confidence: {result['confidence']} | System: {result['system'].upper()}",
                     font=("Arial", 8), fg=self.text_gray, bg=self.bg_frame, anchor="w").pack(fill="x", padx=20, pady=(2, 5))

        btn_frame = tk.Frame(content, bg=self.bg_dark)
        btn_frame.pack(fill="x")

        def do_rename():
            renamed = failed = 0
            for var, result in rename_vars:
                if var.get():
                    success, _, _ = self.name_validator.rename_rom(result['path'], result['suggested_name'])
                    if success: renamed += 1
                    else:       failed  += 1
            dialog.destroy()
            if failed == 0:
                messagebox.showinfo("Rename Complete", f"✅ Successfully renamed {renamed} file(s)!")
            else:
                messagebox.showwarning("Partial Success", f"✅ Renamed: {renamed}\n❌ Failed: {failed}\n\nSome files could not be renamed.")
            self.reset_and_return()

        for text, cmd in [("Select All",  lambda: [v.set(True)  for v, _ in rename_vars]),
                          ("Select None", lambda: [v.set(False) for v, _ in rename_vars])]:
            tk.Button(btn_frame, text=text, command=cmd, font=("Arial", 10),
                      bg=self.bg_frame, fg=self.text_light, cursor="hand2",
                      relief="flat", padx=15, pady=8).pack(side="left", padx=(0, 10))

        tk.Button(btn_frame, text="Cancel",
                  command=lambda: (dialog.destroy(), self.reset_and_return()),
                  font=("Arial", 10), bg=self.bg_frame, fg=self.text_light,
                  cursor="hand2", relief="flat", padx=15, pady=8).pack(side="right", padx=(10, 0))

        tk.Button(btn_frame, text="✓ Rename Selected", command=do_rename,
                  font=("Arial", 10, "bold"), bg=self.accent_green, fg="white",
                  cursor="hand2", relief="flat", padx=20, pady=8).pack(side="right")

    def offer_header_fix(self, results):
        roms_with_headers = [r for r in results.get('all_results', []) if r.get('status') == 'has_header']
        if not roms_with_headers:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("External Headers Detected")
        dialog.configure(bg=self.bg_dark)
        dialog.transient(self.root)
        dialog.grab_set()
        w, h = 650, 600
        x = (dialog.winfo_screenwidth()  // 2) - (w // 2)
        y = (dialog.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        dialog.minsize(650, 600)

        title_frame = tk.Frame(dialog, bg=self.accent_orange, height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="⚠️ External Copier Headers Detected",
                 font=("Arial", 14, "bold"), bg=self.accent_orange, fg="white").pack(expand=True)

        content = tk.Frame(dialog, bg=self.bg_dark, padx=20, pady=20)
        content.pack(fill="both", expand=True)

        tk.Label(content, text=f"{len(roms_with_headers)} ROM(s) have external copier headers:",
                 font=("Arial", 11, "bold"), bg=self.bg_dark, fg=self.text_light).pack(anchor="w", pady=(0, 10))

        list_frame = tk.Frame(content, bg=self.bg_frame, relief="sunken", bd=1)
        list_frame.pack(fill="both", expand=True, pady=(0, 15))
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        rom_listbox = tk.Listbox(list_frame, bg=self.bg_frame, fg=self.text_light,
                                  font=("Arial", 10), selectmode=tk.MULTIPLE,
                                  yscrollcommand=scrollbar.set, relief="flat", highlightthickness=0)
        rom_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        scrollbar.config(command=rom_listbox.yview)
        for rom in roms_with_headers:
            rom_listbox.insert(tk.END, f"• {rom['filename']} ({rom['header_size']} bytes)")
        rom_listbox.select_set(0, tk.END)

        info_frame = tk.Frame(content, bg=self.bg_info_box, relief="flat", padx=15, pady=12)
        info_frame.pack(fill="x", pady=(0, 15))
        tk.Label(info_frame,
                 text="ℹ️ What are external headers?\n\n"
                      "These are extra bytes added by old ROM copying devices.\n"
                      "They cause checksum mismatches with databases.\n\n"
                      "• Safe to remove (not part of original ROM)\n"
                      "• Improves compatibility with emulators\n"
                      "• Matches No-Intro standards",
                 font=("Arial", 9), bg=self.bg_info_box, fg=self.text_info, justify="left").pack()

        backup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(content, text="☑ Create backup before fixing (.backup extension)",
                       variable=backup_var, font=("Arial", 10), bg=self.bg_dark, fg=self.text_light,
                       selectcolor=self.bg_frame, activebackground=self.bg_dark,
                       bd=0, highlightthickness=0).pack(anchor="w", pady=(0, 15))

        btn_frame = tk.Frame(content, bg=self.bg_dark)
        btn_frame.pack(fill="x")

        def fix_headers():
            selected = rom_listbox.curselection()
            if not selected:
                messagebox.showwarning("No Selection", "Please select ROMs to fix.")
                return
            dialog.destroy()
            folder        = self.folder_path.get()
            backup_folder = os.path.join(folder, "RomMate_Backups")
            if backup_var.get():
                os.makedirs(backup_folder, exist_ok=True)

            fixed_roms = []
            failed_roms = []
            for idx in selected:
                rom = roms_with_headers[idx]
                if backup_var.get():
                    backup_path = os.path.join(backup_folder, os.path.basename(rom['path']))
                    try:
                        shutil.copy2(rom['path'], backup_path)
                    except Exception as e:
                        failed_roms.append((rom['filename'], f"Backup failed: {str(e)}"))
                        continue
                success, msg = self.rom_health.cartridge_checker.remove_header(rom['path'], rom['header_size'], create_backup=False)
                if success: fixed_roms.append(rom)
                else:       failed_roms.append((rom['filename'], msg))

            if fixed_roms:
                verified_roms = []
                still_bad     = []
                for rom in fixed_roms:
                    result = self.rom_health.cartridge_checker.verify_rom(rom['path'])
                    if result['status'] == 'verified': verified_roms.append(rom['filename'])
                    else:                              still_bad.append((rom['filename'], result.get('message', 'Unknown status')))

                if still_bad:
                    msg = f"⚠️ Header removal completed but some ROMs still don't verify:\n\n✅ Successfully verified: {len(verified_roms)}\n❌ Still not verified: {len(still_bad)}\n\nFailed ROMs:\n"
                    msg += "".join(f"• {fn}: {st}\n" for fn, st in still_bad)
                    msg += f"\n💾 Backups kept in: {backup_folder}"
                    messagebox.showwarning("Partial Success", msg)
                else:
                    if backup_var.get():
                        if messagebox.askyesno(
                            "Headers Removed Successfully!",
                            f"✅ Successfully removed headers from {len(verified_roms)} ROM(s)!\n✅ All ROMs verified as good dumps!\n\nBackups are stored in:\n{backup_folder}\n\nWould you like to delete the backup folder?",
                            icon='question'
                        ):
                            try:
                                shutil.rmtree(backup_folder)
                                messagebox.showinfo("Backups Deleted", "✅ Backup folder deleted successfully!")
                            except Exception as e:
                                messagebox.showerror("Error", f"Could not delete backup folder:\n{str(e)}")
                        else:
                            messagebox.showinfo("Backups Kept", f"💾 Backups kept in:\n{backup_folder}")
                    else:
                        messagebox.showinfo("Headers Removed Successfully!", f"✅ Successfully removed headers from {len(verified_roms)} ROM(s)!\n✅ All ROMs verified as good dumps!")

            if failed_roms:
                messagebox.showerror("Errors Occurred", "❌ Some ROMs failed to process:\n\n" + "".join(f"• {fn}: {err}\n" for fn, err in failed_roms))

        tk.Button(btn_frame, text="Learn More",
                  command=lambda: messagebox.showinfo(
                      "External Copier Headers",
                      "External headers are NOT part of the original ROM.\n\nThey were added by devices like:\n• Super Magicom\n• Game Doctor\n• Super Wild Card\n\n"
                      "Removing them:\n✅ Makes ROMs match No-Intro databases\n✅ Fixes checksum verification\n✅ Safe - your ROM data is unchanged\n\nThe actual cartridge ROM data starts after the header!"
                  ),
                  font=("Arial", 10), bg=self.bg_frame, fg=self.text_light,
                  cursor="hand2", relief="flat", padx=15, pady=8).pack(side="left", padx=(0, 10))

        tk.Button(btn_frame, text="Skip", command=dialog.destroy,
                  font=("Arial", 10), bg=self.bg_frame, fg=self.text_light,
                  cursor="hand2", relief="flat", padx=15, pady=8).pack(side="left", padx=(0, 10))

        tk.Button(btn_frame, text="✂️ Remove Headers", command=fix_headers,
                  font=("Arial", 10, "bold"), bg=self.accent_green, fg="white",
                  cursor="hand2", relief="flat", padx=20, pady=8).pack(side="right")

        dialog.bind('<Escape>', lambda e: dialog.destroy())

    # ------------------------------------------------------------------ #
    #  Settings callbacks                                                  #
    # ------------------------------------------------------------------ #

    def on_sound_toggle(self, enabled):
        self.sounds_enabled.set(enabled)
        self.config.set('sound_enabled', enabled)
        self.sound_player.sounds_enabled = enabled

    def on_delete_toggle(self, enabled):
        self.delete_after_conversion.set(enabled)
        self.config.set('delete_after_conversion', enabled)

    def on_volume_change(self, volume):
        self.sound_player.volume = volume
        self.config.set('sound_volume', volume)

    def show_settings_panel(self):
        self.main_container.pack_forget()
        self.settings_panel.show()

    def hide_settings_panel(self):
        self.show_main_panel()
