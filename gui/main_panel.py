"""
RomMate - Main Panel
Builds the main UI: folder selector, operation radio buttons, info section.
"""

import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from core.file_utils import normalize_path
from gui.dialogs import show_info_dialog


class MainPanel:
    """Builds and manages the main configuration panel."""

    def __init__(self, parent, colors, config, folder_path, operation_mode, on_run, on_settings, on_dnd_drop=None):
        """
        Args:
            parent:         Root Tk window
            colors:         Dict of theme color values
            config:         Config instance
            folder_path:    tk.StringVar for folder path
            operation_mode: tk.StringVar for selected operation
            on_run:         Callable — called when Start button is pressed
            on_settings:    Callable — called when settings gear is pressed
            on_dnd_drop:    Optional callable for drag-and-drop events
        """
        self.parent         = parent
        self.c              = colors
        self.config         = config
        self.folder_path    = folder_path
        self.operation_mode = operation_mode
        self.on_run         = on_run
        self.on_settings    = on_settings
        self.on_dnd_drop    = on_dnd_drop

        self._build()

    def _build(self):
        c = self.c
        self.frame = tk.Frame(self.parent, bg=c['bg_dark'])

        # Title row
        title_outer = tk.Frame(self.frame, bg=c['bg_dark'])
        title_outer.pack(fill="x", pady=(10, 5))

        tk.Button(
            title_outer, text="⚙️", command=self.on_settings,
            font=("Arial", 20), bg=c['bg_dark'], fg=c['text_light'],
            cursor="hand2", relief="flat", activebackground=c['bg_frame'],
            bd=0, highlightthickness=0, highlightbackground=c['bg_frame'],
            highlightcolor=c['bg_frame'], padx=10
        ).place(relx=1.0, x=-10, y=0, anchor="ne")

        tk.Label(
            title_outer, text="RomMate", font=("Arial", 24, "bold"),
            bg=c['bg_dark'], fg=c['text_light']
        ).pack()

        tk.Label(
            self.frame,
            text="Your ROM companion - Convert, compress, and organize disc images",
            font=("Arial", 11), bg=c['bg_dark'], fg=c['text_gray']
        ).pack(pady=(0, 30))

        # Folder selection
        folder_frame = tk.Frame(self.frame, bg=c['bg_dark'])
        folder_frame.pack(pady=10, fill="x")

        tk.Label(
            folder_frame, text="Game Folder:", font=("Arial", 11, "bold"),
            bg=c['bg_dark'], fg=c['text_light']
        ).pack(side="left", padx=(0, 15))

        self.folder_entry = tk.Entry(
            folder_frame, textvariable=self.folder_path, width=50,
            font=("Arial", 11), bg=c['bg_frame'], fg=c['text_light'],
            insertbackground=c['text_light'], relief="solid", bd=1,
            highlightthickness=2, highlightbackground=c['bg_dark'],
            highlightcolor=c['accent_blue']
        )
        self.folder_entry.pack(side="left", padx=10, fill="x", expand=True, ipady=6)
        self._add_placeholder()

        tk.Button(
            folder_frame, text="Browse", command=self.browse_folder,
            font=("Arial", 10, "bold"), bg=c['accent_green'], fg="white",
            cursor="hand2", padx=20, pady=8, relief="flat",
            activebackground=c['active_green'], activeforeground="white", bd=0
        ).pack(side="left")

        # Disc-Based ROMs section
        disc_frame = tk.Frame(self.frame, bg=c['bg_frame'], relief="groove", bd=2)
        disc_frame.pack(pady=20, fill="x")

        tk.Label(
            disc_frame, text="📀 Disc-Based ROMs", font=("Arial", 12, "bold"),
            bg=c['bg_frame'], fg=c['text_light']
        ).pack(anchor="w", padx=25, pady=(15, 10))

        for text, value in [
            ("💾 Convert to CHD (compress disc images)", "chd"),
            ("📁 Create M3U Playlists (for multi-disc games)", "m3u"),
            ("🔄 Convert to CHD + Create M3U Playlists", "both"),
        ]:
            tk.Radiobutton(
                disc_frame, text=text, variable=self.operation_mode, value=value,
                font=("Arial", 11), command=self.update_info_section,
                bg=c['bg_frame'], fg=c['text_light'], selectcolor=c['bg_dark'],
                activebackground=c['bg_frame'], bd=0, highlightthickness=0
            ).pack(anchor="w", padx=25, pady=8)

        tk.Frame(disc_frame, height=1, bg=c['text_gray']).pack(fill="x", padx=25, pady=15)

        tk.Button(
            disc_frame, text="ℹ️  Help - When to use each?",
            command=lambda: show_info_dialog(self.parent),
            font=("Arial", 10), bg=c['accent_blue'], fg="white",
            cursor="hand2", relief="flat", padx=15, pady=6
        ).pack(anchor="w", padx=25, pady=(0, 15))

        # ROM Tools section
        tools_frame = tk.Frame(self.frame, bg=c['bg_frame'], relief="groove", bd=2)
        tools_frame.pack(pady=20, fill="x")

        tk.Label(
            tools_frame, text="🎮 ROM Tools (All ROM Types)",
            font=("Arial", 12, "bold"), bg=c['bg_frame'], fg=c['text_light']
        ).pack(anchor="w", padx=25, pady=(15, 10))

        for text, value in [
            ("🔍 Check ROM Health", "health"),
            ("✏️  Validate & Fix ROM Names", "validate"),
        ]:
            tk.Radiobutton(
                tools_frame, text=text, variable=self.operation_mode, value=value,
                font=("Arial", 11), command=self.update_info_section,
                bg=c['bg_frame'], fg=c['text_light'], selectcolor=c['bg_dark'],
                activebackground=c['bg_frame'], bd=0, highlightthickness=0
            ).pack(anchor="w", padx=25, pady=8)

        # Info section
        info_frame = tk.Frame(self.frame, bg=c['bg_frame'], relief="groove", bd=2, height=185)
        info_frame.pack(pady=20, fill="x")
        info_frame.pack_propagate(False)

        tk.Label(
            info_frame, text="ℹ️  Info", font=("Arial", 12, "bold"),
            bg=c['bg_frame'], fg=c['text_light']
        ).pack(anchor="w", padx=25, pady=(15, 10))

        self.info_content = tk.Frame(info_frame, bg=c['bg_frame'])
        self.info_content.pack(fill="x", padx=25, pady=(0, 15))

        # Start button — must exist before _build_info_sections()
        self.process_btn = tk.Button(
            self.frame, text="▶ Start Operation", command=self.on_run,
            font=("Arial", 14, "bold"), bg=c['accent_blue'], fg="white",
            cursor="hand2", height=2, padx=50, relief="flat", width=15
        )
        self.process_btn.pack(pady=30)

        self._build_info_sections()

    # ------------------------------------------------------------------ #
    #  Show / hide                                                         #
    # ------------------------------------------------------------------ #

    def show(self):
        self.frame.pack(fill="both", expand=True, padx=30, pady=20)

    def hide(self):
        self.frame.pack_forget()

    # ------------------------------------------------------------------ #
    #  Folder helpers                                                      #
    # ------------------------------------------------------------------ #

    def _add_placeholder(self):
        placeholder = "⬇️  Drop folder here"
        self.folder_entry.config(justify='center')
        if not self.folder_path.get():
            self.folder_entry.insert(0, placeholder)
            self.folder_entry.config(fg=self.c['text_gray'])

        def on_focus_in(event):
            if self.folder_entry.get() == placeholder:
                self.folder_entry.delete(0, tk.END)
                self.folder_entry.config(fg=self.c['text_light'], justify='left')

        def on_focus_out(event):
            if not self.folder_entry.get():
                self.folder_entry.insert(0, placeholder)
                self.folder_entry.config(fg=self.c['text_gray'], justify='center')

        self.folder_entry.bind('<FocusIn>',  on_focus_in)
        self.folder_entry.bind('<FocusOut>', on_focus_out)

    def update_folder_display(self, folder):
        self.folder_path.set(folder)
        self.folder_entry.config(fg=self.c['text_light'], justify='left')

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

    # ------------------------------------------------------------------ #
    #  Info sections                                                       #
    # ------------------------------------------------------------------ #

    def _build_info_sections(self):
        c = self.c

        self.chd_info = tk.Frame(self.info_content, bg=c['bg_frame'])
        for text, font, fg in [
            ("Converts: CUE, GDI, CDI, ISO → CHD format", ("Arial", 10), c['text_gray']),
            ("Supported: PS1, PS2, Dreamcast, Saturn, PSP", ("Arial", 9), c['text_gray']),
            ("Not supported: GameCube (use GCZ), Wii (use RVZ/WBFS)", ("Arial", 9, "italic"), c['accent_orange']),
            ("• CHD files are compressed and save 40-60% space", ("Arial", 9), c['text_gray']),
            ("• Supported by RetroArch and most modern emulators", ("Arial", 9), c['text_gray']),
        ]:
            tk.Label(self.chd_info, text=text, font=font, fg=fg, bg=c['bg_frame']).pack(anchor="w", pady=(0, 5))

        self.m3u_info = tk.Frame(self.info_content, bg=c['bg_frame'])
        tk.Label(self.m3u_info, text="Scans for: CUE, GDI, CDI, ISO, CHD files",
                 font=("Arial", 10), fg=c['text_gray'], bg=c['bg_frame']).pack(anchor="w", pady=(0, 10))
        info_box = tk.Frame(self.m3u_info, bg=c['bg_info_box'], relief="flat")
        info_box.pack(fill="x", pady=(0, 5))
        tk.Label(info_box,
                 text="ℹ️ Note: All disc files must be in the same folder.\n"
                      "    Works with PSX, PS2, Dreamcast, Saturn, Sega CD, and more!\n"
                      "    If both CUE and CHD files exist, you'll be asked which to use.",
                 font=("Arial", 9), bg=c['bg_info_box'], fg=c['text_info'], justify="left"
                 ).pack(padx=15, pady=12, anchor="w")

        self.both_info = tk.Frame(self.info_content, bg=c['bg_frame'])
        for text, font in [
            ("Step 1: Convert all disc images to CHD", ("Arial", 10, "bold")),
            ("  Converts: CUE, GDI, CDI, ISO → CHD",  ("Arial", 9)),
            ("Step 2: Create M3U playlists for multi-disc games", ("Arial", 10, "bold")),
            ("  Groups CHD files into playlists", ("Arial", 9)),
        ]:
            tk.Label(self.both_info, text=text, font=font,
                     fg=c['text_light'] if "bold" in font else c['text_gray'],
                     bg=c['bg_frame']).pack(anchor="w", pady=(0, 5))

        self.health_info = tk.Frame(self.info_content, bg=c['bg_frame'])
        tk.Label(self.health_info, text="Check ROM files and identify games:",
                 font=("Arial", 10), fg=c['text_gray'], bg=c['bg_frame']).pack(anchor="w", pady=(0, 5))
        for text in [
            "• CHD Files: Full integrity verification ✓",
            "• Cartridge ROMs: Checksum verification ✓",
            "• ISO/CDI/GDI: Identification by name & size (Cannot verify disc image checksums)",
            "• Compare against No-Intro & Redump databases",
        ]:
            tk.Label(self.health_info, text=text, font=("Arial", 9),
                     fg=c['text_gray'], bg=c['bg_frame']).pack(anchor="w", pady=(0, 3))

        self.validate_info = tk.Frame(self.info_content, bg=c['bg_frame'])
        tk.Label(self.validate_info, text="Checks and fixes ROM filenames:",
                 font=("Arial", 10), fg=c['text_gray'], bg=c['bg_frame']).pack(anchor="w", pady=(0, 5))
        for text in [
            "• Compares against No-Intro/Redump databases",
            "• Suggests correct naming conventions",
            "• Detects region and version information",
        ]:
            tk.Label(self.validate_info, text=text, font=("Arial", 9),
                     fg=c['text_gray'], bg=c['bg_frame']).pack(anchor="w", pady=(0, 3))

        self.update_info_section()

    def update_info_section(self):
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
        self.process_btn.config(text=label)
