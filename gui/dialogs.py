"""Custom dialog windows for RomMate"""

import tkinter as tk
from gui.theme import Theme
from utils.i18n import _


def show_format_choice_dialog(parent):
    """Show dialog asking user to choose between CHD and original files
    
    Args:
        parent: Parent tkinter window
        
    Returns:
        str: "chd", "original", or None if cancelled
    """
    choice_dialog = tk.Toplevel(parent)
    choice_dialog.title(_("Choose Format"))
    choice_dialog.geometry("500x250")
    choice_dialog.configure(bg=Theme.BG_DARK)
    choice_dialog.transient(parent)
    choice_dialog.grab_set()
    
    # Center the dialog on parent window
    choice_dialog.update_idletasks()
    parent.update_idletasks()

    # Get parent window position and size
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()

    # Calculate center position
    dialog_width = 500
    dialog_height = 280
    x = parent_x + (parent_width // 2) - (dialog_width // 2)
    y = parent_y + (parent_height // 2) - (dialog_height // 2)

    choice_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    selected_format = None
    
    def select_chd():
        nonlocal selected_format
        selected_format = "chd"
        choice_dialog.destroy()
    
    def select_original():
        nonlocal selected_format
        selected_format = "original"
        choice_dialog.destroy()
    
    def cancel():
        nonlocal selected_format
        selected_format = None
        choice_dialog.destroy()
    
    # Title
    tk.Label(
        choice_dialog,
        text=_("[!] Multiple Disc Formats Found"),
        font=("Arial", 16, "bold"),
        bg=Theme.BG_DARK,
        fg=Theme.ACCENT_ORANGE
    ).pack(pady=(20, 10))
    
    # Message
    tk.Label(
        choice_dialog,
        text=_("Both original disc files and CHD files were found.\nWhich format do you want to use for M3U playlists?"),
        font=("Arial", 11),
        bg=Theme.BG_DARK,
        fg=Theme.TEXT_LIGHT,
        justify="center"
    ).pack(pady=(0, 30))
    
    # Buttons frame
    btn_frame = tk.Frame(choice_dialog, bg=Theme.BG_DARK)
    btn_frame.pack(pady=10)
    
    tk.Button(
        btn_frame,
        text=_("Use CHD Files\n(compressed)"),
        command=select_chd,
        font=("Arial", 11, "bold"),
        bg=Theme.ACCENT_BLUE,
        fg="white",
        cursor="hand2",
        padx=20,
        pady=15,
        relief="flat",
        width=15
    ).pack(side="left", padx=10)
    
    tk.Button(
        btn_frame,
        text=_("Use Original Files\n(CUE/BIN/etc)"),
        command=select_original,
        font=("Arial", 11, "bold"),
        bg=Theme.ACCENT_GREEN,
        fg="white",
        cursor="hand2",
        padx=20,
        pady=15,
        relief="flat",
        width=15
    ).pack(side="left", padx=10)
    
    # Cancel button
    tk.Button(
        choice_dialog,
        text=_("Cancel"),
        command=cancel,
        font=("Arial", 10),
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_LIGHT,
        cursor="hand2",
        padx=15,
        pady=8,
        relief="flat"
    ).pack(pady=(10, 0))
    
    # Wait for dialog to close
    parent.wait_window(choice_dialog)
    
    return selected_format


def show_info_dialog(parent):
    """Show information dialog about when to use each option
    
    Args:
        parent: Parent tkinter window
    """
    from tkinter import scrolledtext
    
    info_text = _("""
 CONVERT TO CHD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Compresses your disc images to save space.

What it does:
  • Converts CUE/BIN, GDI, CDI and ISO files to CHD format
  • Reduces file size by 40-60%
  • Preserves all game data perfectly

Best for:
  • Saving storage space
  • RetroArch and most modern emulators

Example:
  Game.cue + Game.bin (700 MB)  →  Game.chd (~350 MB)

[!] Always keep backups before converting!

[~] Most games run perfectly in CHD format, but a small
    number of titles may have compatibility issues.
    If you experience problems, try the original format.


 CREATE M3U PLAYLISTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use this for multi-disc games (Disc 1, Disc 2, etc.)

What it does:
  • Creates .m3u playlist files grouping all discs per game
  • Lets you switch discs inside your emulator during gameplay
  • Works with CUE, GDI, CDI, ISO and CHD files

Best for:
  • PS1, PS2, Dreamcast, Saturn and Sega CD multi-disc games

Example:
  Final Fantasy VII (Disc 1).chd
  Final Fantasy VII (Disc 2).chd
  Final Fantasy VII (Disc 3).chd
  
  →  Final Fantasy VII.m3u
    """)
    
    info_window = tk.Toplevel(parent)
    info_window.title(_("Help - When to use each option"))
    info_window.geometry("600x650")
    info_window.configure(bg=Theme.BG_DARK)
    
    text_widget = scrolledtext.ScrolledText(
        info_window,
        width=70,
        height=35,
        font=("Arial", 10),
        wrap=tk.WORD,
        padx=15,
        pady=15,
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_LIGHT
    )
    text_widget.pack(fill="both", expand=True, padx=10, pady=10)
    text_widget.insert(1.0, info_text)
    text_widget.config(state="disabled")
    
    close_btn = tk.Button(
        info_window,
        text=_("Close"),
        command=info_window.destroy,
        font=("Arial", 10),
        bg=Theme.ACCENT_GREEN,
        fg="white",
        cursor="hand2",
        padx=20,
        relief="flat"
    )
    close_btn.pack(pady=10)
