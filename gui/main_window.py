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

from tkinter import messagebox
import os
import shutil
import threading

from gui.theme import Theme
from gui.settings_panel import SettingsPanel
from gui.main_panel import MainPanel
from gui.processing_panel import ProcessingPanel
from gui.dialogs import show_info_dialog
from gui.operations import (
    convert_to_chd,
    create_m3u_files,
    convert_and_create_m3u,
    check_rom_health,
    validate_rom_names,
)
from utils.sounds import SoundPlayer
from utils.config import Config
from core.file_utils import normalize_path
from core.chd_converter import CHDConverter
from core.m3u_creator import M3UCreator
from core.rom_health import ROMHealthChecker
from core.name_validator import NameValidator


class RomMateGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RomMate")
        self.root.geometry("670x870")
        self.root.resizable(True, True)

        self.config = Config()

        saved_theme = self.config.get('theme', 'dark')
        import gui.theme as theme_module
        theme_module.set_theme(saved_theme)

        self._init_state()
        self._apply_theme_colors()
        self.root.configure(bg=self.colors['bg_dark'])
        self._build_ui()

        if DND_AVAILABLE:
            self._setup_drag_and_drop()

    # ------------------------------------------------------------------ #
    #  State                                                               #
    # ------------------------------------------------------------------ #

    def _init_state(self):
        if not hasattr(self, 'folder_path'):
            self.folder_path             = tk.StringVar()
            self.operation_mode          = tk.StringVar(value="chd")
            self.delete_after_conversion = tk.BooleanVar(value=False)
            self.sounds_enabled          = tk.BooleanVar(value=True)

        if not hasattr(self, 'sound_player'):
            self.sound_player                = SoundPlayer()
            self.sound_player.volume         = self.config.get('sound_volume', 1.0)
            self.sound_player.sounds_enabled = self.config.get('sound_enabled', True)
            self.sounds_enabled.set(self.sound_player.sounds_enabled)

        if not hasattr(self, 'chd_converter'):
            self.chd_converter  = CHDConverter()
        if not hasattr(self, 'm3u_creator'):
            self.m3u_creator    = M3UCreator()
        if not hasattr(self, 'rom_health'):
            self.rom_health     = ROMHealthChecker()
        if not hasattr(self, 'name_validator'):
            self.name_validator = NameValidator()

        self.is_processing    = False
        self.cancel_requested = False

    def _apply_theme_colors(self):
        from gui.theme import Theme
        self.colors = {
            'bg_dark':       Theme.BG_DARK,
            'bg_frame':      Theme.BG_FRAME,
            'bg_processing': Theme.BG_PROCESSING,
            'bg_info_box':   Theme.BG_INFO_BOX,
            'text_light':    Theme.TEXT_LIGHT,
            'text_gray':     Theme.TEXT_GRAY,
            'text_processing': Theme.TEXT_PROCESSING,
            'text_info':     Theme.TEXT_INFO,
            'text_error':    Theme.TEXT_ERROR,
            'text_success':  Theme.TEXT_SUCCESS,
            'accent_blue':   Theme.ACCENT_BLUE,
            'accent_green':  Theme.ACCENT_GREEN,
            'accent_red':    Theme.ACCENT_RED,
            'accent_orange': Theme.ACCENT_ORANGE,
            'state_success': Theme.STATE_SUCCESS,
            'state_warning': Theme.STATE_WARNING,
            'state_error':   Theme.STATE_ERROR,
            'active_green':  Theme.ACTIVE_GREEN,
            'active_red':    Theme.ACTIVE_RED,
            'active_blue':   Theme.ACTIVE_BLUE,
        }

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # Main panel
        self.main_panel = MainPanel(
            parent         = self.root,
            colors         = self.colors,
            config         = self.config,
            folder_path    = self.folder_path,
            operation_mode = self.operation_mode,
            on_run         = self.run_process,
            on_settings    = self.show_settings_panel,
        )

        # Processing panel
        self.proc_panel = ProcessingPanel(
            parent            = self.root,
            colors            = self.colors,
            sound_player      = self.sound_player,
            get_operation_mode = lambda: self.operation_mode.get(),
            get_is_processing  = lambda: self.is_processing,
            set_cancel         = lambda v: setattr(self, 'cancel_requested', v),
        )
        self.proc_panel.on_reset_and_return = self.reset_and_return

        # Settings panel
        self.settings_panel = SettingsPanel(
            self.root,
            self.config,
            callbacks={
                'get_sounds_enabled':          lambda: self.sounds_enabled.get(),
                'on_sound_toggle':             self._on_sound_toggle,
                'get_delete_after_conversion': lambda: self.delete_after_conversion.get(),
                'on_delete_toggle':            self._on_delete_toggle,
                'on_volume_change':            self._on_volume_change,
                'show_help':                   lambda: show_info_dialog(self.root),
                'on_close':                    self.show_main_panel,
                'reload_theme':                self.reload_theme,
            }
        )

        self.show_main_panel()

    # ------------------------------------------------------------------ #
    #  Theme reload                                                        #
    # ------------------------------------------------------------------ #

    def reload_theme(self, theme_name, return_to_settings=False):
        saved_folder = self.folder_path.get()
        saved_mode   = self.operation_mode.get()

        import gui.theme as theme_module
        theme_module.set_theme(theme_name)

        for widget in self.root.winfo_children():
            widget.destroy()

        self._apply_theme_colors()
        self.root.configure(bg=self.colors['bg_dark'])
        self._build_ui()

        if DND_AVAILABLE:
            self._setup_drag_and_drop()

        self.folder_path.set(saved_folder)
        self.operation_mode.set(saved_mode)
        self.main_panel.update_info_section()

        if return_to_settings:
            self.show_settings_panel()

    # ------------------------------------------------------------------ #
    #  Panel switching                                                     #
    # ------------------------------------------------------------------ #

    def show_main_panel(self):
        self.proc_panel.frame.pack_forget()
        self.settings_panel.panel.pack_forget()
        self.main_panel.show()

    def show_settings_panel(self):
        self.main_panel.hide()
        self.proc_panel.hide()
        self.settings_panel.show()

    def reset_and_return(self):
        self.is_processing = False
        self.proc_panel.reset_bg()
        self.show_main_panel()

    # ------------------------------------------------------------------ #
    #  Drag & drop                                                         #
    # ------------------------------------------------------------------ #

    def _setup_drag_and_drop(self):
        entry = self.main_panel.folder_entry
        entry.drop_target_register(DND_FILES)
        entry.dnd_bind('<<Drop>>', self._on_drop)

    def _on_drop(self, event):
        try:
            dropped = event.data.strip('{}').strip()
            if ' ' in dropped and not os.path.exists(dropped):
                dropped = dropped.split()[0].strip('{}')
            dropped = normalize_path(dropped)
            target = dropped if os.path.isdir(dropped) else os.path.dirname(dropped)
            self.main_panel.update_folder_display(target)
            self.config.set('last_folder', target)
        except Exception as e:
            print(f"Error handling drop: {e}")

    # ------------------------------------------------------------------ #
    #  Callbacks dict for operations                                       #
    # ------------------------------------------------------------------ #

    def _build_callbacks(self):
        return {
            'log':                self.proc_panel.log,
            'progress':           self.proc_panel.update_status,
            'animate':            self.proc_panel.animate_dots,
            'cancel':             lambda: self.cancel_requested,
            'complete':           self.proc_panel.show_completion,
            'return':             self.reset_and_return,
            'set_processing':     lambda v: setattr(self, 'is_processing', v),
            'offer_header_fix':   self.offer_header_fix,
            'show_rename_dialog': self.show_rename_dialog,
        }

    # ------------------------------------------------------------------ #
    #  Run process                                                         #
    # ------------------------------------------------------------------ #

    def run_process(self):
        folder = self.folder_path.get()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return
        if not os.path.exists(folder):
            messagebox.showerror("Error", f"Selected folder does not exist!\n\nPath: {folder}")
            return

        mode      = self.operation_mode.get()
        callbacks = self._build_callbacks()

        self.is_processing = True
        self.main_panel.hide()
        self.proc_panel.show()

        if mode == "chd":
            threading.Thread(
                target=convert_to_chd,
                args=(folder, self.delete_after_conversion.get(), self.chd_converter, callbacks),
                daemon=True
            ).start()

        elif mode == "m3u":
            threading.Thread(
                target=create_m3u_files,
                args=(folder, self.m3u_creator, self.root, callbacks),
                daemon=True
            ).start()

        elif mode == "both":
            threading.Thread(
                target=convert_and_create_m3u,
                args=(folder, self.delete_after_conversion.get(), self.chd_converter, callbacks),
                daemon=True
            ).start()

        elif mode == "health":
            if not self.rom_health.find_chdman():
                if messagebox.askyesno(
                    "chdman Not Found",
                    "chdman is required for CHD verification.\n\n"
                    "Cartridge ROMs can still be checked.\n\n"
                    "Would you like to install chdman now?",
                    icon='warning'
                ):
                    self.chd_converter.prompt_install_chdman()
                    self.is_processing = False
                    self.show_main_panel()
                    return
            self.proc_panel.log(f"ROM Health Check\n\nFolder: {folder}\n{'=' * 60}")
            self.proc_panel.start_spinner()
            check_rom_health(
                folder, self.rom_health, self.chd_converter,
                self.root, callbacks, self.root.after
            )

        elif mode == "validate":
            self.cancel_requested = False
            validate_rom_names(
                folder, self.name_validator, self.root, callbacks, self.root.after
            )

    # ------------------------------------------------------------------ #
    #  Dialogs                                                             #
    # ------------------------------------------------------------------ #

    def show_rename_dialog(self, results):
        c = self.colors
        dialog = tk.Toplevel(self.root)
        dialog.title("ROM Name Validator - Review Changes")
        dialog.configure(bg=c['bg_dark'])
        dialog.transient(self.root)
        dialog.grab_set()
        w, h = 900, 600
        x = (dialog.winfo_screenwidth()  // 2) - (w // 2)
        y = (dialog.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        dialog.minsize(900, 600)

        title_frame = tk.Frame(dialog, bg=c['accent_blue'], height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text=f"Review ROM Names ({len(results)} files need renaming)",
                 font=("Arial", 14, "bold"), bg=c['accent_blue'], fg="white").pack(expand=True)

        content = tk.Frame(dialog, bg=c['bg_dark'], padx=20, pady=20)
        content.pack(fill="both", expand=True)

        list_frame = tk.Frame(content, bg=c['bg_frame'], relief="sunken", bd=1)
        list_frame.pack(fill="both", expand=True, pady=(0, 15))

        canvas    = tk.Canvas(list_frame, bg=c['bg_frame'], highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=c['bg_frame'])
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        rename_vars = []
        for idx, result in enumerate(results):
            item = tk.Frame(scrollable_frame, bg=c['bg_frame'], pady=10, padx=10)
            item.pack(fill="x", padx=5, pady=5)
            if idx > 0:
                tk.Frame(item, bg=c['text_gray'], height=1).pack(fill="x", pady=(0, 10))
            var = tk.BooleanVar(value=True)
            rename_vars.append((var, result))
            tk.Checkbutton(item, text="Rename this file", variable=var,
                           font=("Arial", 10, "bold"), bg=c['bg_frame'], fg=c['text_light'],
                           selectcolor=c['bg_dark'], activebackground=c['bg_frame']).pack(anchor="w")
            tk.Label(item, text=f"Current:  {result['current_name']}",
                     font=("Arial", 9), fg=c['text_error'], bg=c['bg_frame'], anchor="w").pack(fill="x", padx=20, pady=(5, 2))
            tk.Label(item, text=f"Suggested: {result['suggested_name']}",
                     font=("Arial", 9), fg=c['text_success'], bg=c['bg_frame'], anchor="w").pack(fill="x", padx=20, pady=(2, 2))
            tk.Label(item, text=f"Confidence: {result['confidence']} | System: {result['system'].upper()}",
                     font=("Arial", 8), fg=c['text_gray'], bg=c['bg_frame'], anchor="w").pack(fill="x", padx=20, pady=(2, 5))

        btn_frame = tk.Frame(content, bg=c['bg_dark'])
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
                messagebox.showinfo("Rename Complete", f"Successfully renamed {renamed} file(s)!")
            else:
                messagebox.showwarning("Partial Success",
                    f"Renamed: {renamed}  |  Failed: {failed}\n\nSome files could not be renamed.")
            self.reset_and_return()

        for text, cmd in [("Select All",  lambda: [v.set(True)  for v, _ in rename_vars]),
                          ("Select None", lambda: [v.set(False) for v, _ in rename_vars])]:
            tk.Button(btn_frame, text=text, command=cmd, font=("Arial", 10),
                      bg=c['bg_frame'], fg=c['text_light'], cursor="hand2",
                      relief="flat", padx=15, pady=8).pack(side="left", padx=(0, 10))

        tk.Button(btn_frame, text="Cancel",
                  command=lambda: (dialog.destroy(), self.reset_and_return()),
                  font=("Arial", 10), bg=c['bg_frame'], fg=c['text_light'],
                  cursor="hand2", relief="flat", padx=15, pady=8).pack(side="right", padx=(10, 0))

        tk.Button(btn_frame, text="✓ Rename Selected", command=do_rename,
                  font=("Arial", 10, "bold"), bg=c['accent_green'], fg="white",
                  cursor="hand2", relief="flat", padx=20, pady=8).pack(side="right")

    def offer_header_fix(self, results):
        c = self.colors
        roms_with_headers = [r for r in results.get('all_results', []) if r.get('status') == 'has_header']
        if not roms_with_headers:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("External Headers Detected")
        dialog.configure(bg=c['bg_dark'])
        dialog.transient(self.root)
        dialog.grab_set()
        w, h = 650, 600
        x = (dialog.winfo_screenwidth()  // 2) - (w // 2)
        y = (dialog.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        dialog.minsize(650, 600)

        title_frame = tk.Frame(dialog, bg=c['accent_orange'], height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="[!] External Copier Headers Detected",
                 font=("Arial", 14, "bold"), bg=c['accent_orange'], fg="white").pack(expand=True)

        content = tk.Frame(dialog, bg=c['bg_dark'], padx=20, pady=20)
        content.pack(fill="both", expand=True)

        tk.Label(content, text=f"{len(roms_with_headers)} ROM(s) have external copier headers:",
                 font=("Arial", 11, "bold"), bg=c['bg_dark'], fg=c['text_light']).pack(anchor="w", pady=(0, 10))

        list_frame = tk.Frame(content, bg=c['bg_frame'], relief="sunken", bd=1)
        list_frame.pack(fill="both", expand=True, pady=(0, 15))
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        rom_listbox = tk.Listbox(list_frame, bg=c['bg_frame'], fg=c['text_light'],
                                  font=("Arial", 10), selectmode=tk.MULTIPLE,
                                  yscrollcommand=scrollbar.set, relief="flat", highlightthickness=0)
        rom_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        scrollbar.config(command=rom_listbox.yview)
        for rom in roms_with_headers:
            rom_listbox.insert(tk.END, f"• {rom['filename']} ({rom['header_size']} bytes)")
        rom_listbox.select_set(0, tk.END)

        info_frame = tk.Frame(content, bg=c['bg_info_box'], relief="flat", padx=15, pady=12)
        info_frame.pack(fill="x", pady=(0, 15))
        tk.Label(info_frame,
                 text="ℹ️ What are external headers?\n\n"
                      "These are extra bytes added by old ROM copying devices.\n"
                      "They cause checksum mismatches with databases.\n\n"
                      "• Safe to remove (not part of original ROM)\n"
                      "• Improves compatibility with emulators\n"
                      "• Matches No-Intro standards",
                 font=("Arial", 9), bg=c['bg_info_box'], fg=c['text_info'], justify="left").pack()

        backup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(content, text="Create backup before fixing (.backup extension)",
                       variable=backup_var, font=("Arial", 10), bg=c['bg_dark'], fg=c['text_light'],
                       selectcolor=c['bg_frame'], activebackground=c['bg_dark'],
                       bd=0, highlightthickness=0).pack(anchor="w", pady=(0, 15))

        btn_frame = tk.Frame(content, bg=c['bg_dark'])
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

            fixed_roms, failed_roms = [], []
            for idx in selected:
                rom = roms_with_headers[idx]
                if backup_var.get():
                    try:
                        shutil.copy2(rom['path'], os.path.join(backup_folder, os.path.basename(rom['path'])))
                    except Exception as e:
                        failed_roms.append((rom['filename'], f"Backup failed: {str(e)}"))
                        continue
                success, msg = self.rom_health.cartridge_checker.remove_header(
                    rom['path'], rom['header_size'], create_backup=False)
                if success: fixed_roms.append(rom)
                else:       failed_roms.append((rom['filename'], msg))

            if fixed_roms:
                verified, still_bad = [], []
                for rom in fixed_roms:
                    r = self.rom_health.cartridge_checker.verify_rom(rom['path'])
                    if r['status'] == 'verified': verified.append(rom['filename'])
                    else: still_bad.append((rom['filename'], r.get('message', 'Unknown')))

                if still_bad:
                    msg = (f"Some ROMs still don't verify:\n\n"
                           f"Verified: {len(verified)}\nStill bad: {len(still_bad)}\n\nFailed:\n")
                    msg += "".join(f"• {fn}: {st}\n" for fn, st in still_bad)
                    msg += f"\nBackups kept in: {backup_folder}"
                    messagebox.showwarning("Partial Success", msg)
                else:
                    if backup_var.get():
                        if messagebox.askyesno(
                            "Headers Removed Successfully!",
                            f"Removed headers from {len(verified)} ROM(s)!\n"
                            f"All ROMs verified!\n\nBackups in:\n{backup_folder}\n\n"
                            f"Delete backup folder?", icon='question'
                        ):
                            try:
                                shutil.rmtree(backup_folder)
                                messagebox.showinfo("Backups Deleted", "Backup folder deleted!")
                            except Exception as e:
                                messagebox.showerror("Error", f"Could not delete backups:\n{str(e)}")
                        else:
                            messagebox.showinfo("Backups Kept", f"Backups kept in:\n{backup_folder}")
                    else:
                        messagebox.showinfo("Success",
                            f"Removed headers from {len(verified)} ROM(s)! All ROMs verified!")

            if failed_roms:
                messagebox.showerror("Errors",
                    "Some ROMs failed:\n\n" + "".join(f"• {fn}: {err}\n" for fn, err in failed_roms))

        tk.Button(btn_frame, text="Learn More",
                  command=lambda: messagebox.showinfo("External Copier Headers",
                      "External headers are NOT part of the original ROM.\n\n"
                      "Added by devices like:\n• Super Magicom\n• Game Doctor\n• Super Wild Card\n\n"
                      "Removing them:\nMatches No-Intro databases\nFixes checksums\nSafe to remove"),
                  font=("Arial", 10), bg=c['bg_frame'], fg=c['text_light'],
                  cursor="hand2", relief="flat", padx=15, pady=8).pack(side="left", padx=(0, 10))

        tk.Button(btn_frame, text="Skip", command=dialog.destroy,
                  font=("Arial", 10), bg=c['bg_frame'], fg=c['text_light'],
                  cursor="hand2", relief="flat", padx=15, pady=8).pack(side="left", padx=(0, 10))

        tk.Button(btn_frame, text="Remove Headers", command=fix_headers,
                  font=("Arial", 10, "bold"), bg=c['accent_green'], fg="white",
                  cursor="hand2", relief="flat", padx=20, pady=8).pack(side="right")

        dialog.bind('<Escape>', lambda e: dialog.destroy())

    # ------------------------------------------------------------------ #
    #  Settings callbacks                                                  #
    # ------------------------------------------------------------------ #

    def _on_sound_toggle(self, enabled):
        self.sounds_enabled.set(enabled)
        self.config.set('sound_enabled', enabled)
        self.sound_player.sounds_enabled = enabled

    def _on_delete_toggle(self, enabled):
        self.delete_after_conversion.set(enabled)
        self.config.set('delete_after_conversion', enabled)

    def _on_volume_change(self, volume):
        self.sound_player.volume = volume
        self.config.set('sound_volume', volume)
