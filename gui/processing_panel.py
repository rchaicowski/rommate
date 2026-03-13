"""
RomMate - Processing Panel
Handles the processing UI: spinner, log, status updates, cancel and completion.
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
from utils.i18n import _


class ProcessingPanel:
    """Manages the processing panel UI and all its state."""

    def __init__(self, parent, colors, sound_player, get_operation_mode, get_is_processing, set_cancel):
        """
        Args:
            parent:             The root Tk window
            colors:             Dict of theme color values
            sound_player:       SoundPlayer instance
            get_operation_mode: Callable returning current operation mode string
            get_is_processing:  Callable returning bool
            set_cancel:         Callable(bool) to set cancel_requested
        """
        self.parent            = parent
        self.c                 = colors
        self.sound_player      = sound_player
        self.get_mode          = get_operation_mode
        self.get_is_processing = get_is_processing
        self.set_cancel        = set_cancel

        # Spinner state
        self.spinner_running = False
        self.spinner_chars   = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        self.spinner_index   = 0

        # Callbacks set externally after construction
        self.on_reset_and_return = None

        self._build()

    def _build(self):
        """Build the processing panel widget tree."""
        c = self.c
        self.frame = tk.Frame(self.parent, bg=c['bg_frame'], relief="groove", bd=2)

        # Status header
        header = tk.Frame(self.frame, bg=c['bg_frame'])
        header.pack(fill="x", pady=20, padx=30)

        self.status_title = tk.Label(
            header, text=_("Processing..."), font=("Arial", 20, "bold"),
            bg=c['bg_frame'], fg=c['text_light']
        )
        self.status_title.pack()

        self.status_subtitle = tk.Label(
            header, text=_("Starting operation"), font=("Arial", 12),
            bg=c['bg_frame'], fg=c['text_gray']
        )
        self.status_subtitle.pack(pady=(5, 0))

        self.current_file_label = tk.Label(
            self.frame, text="", font=("Consolas", 11),
            bg=c['bg_frame'], fg=c['accent_blue'], wraplength=700
        )
        self.current_file_label.pack(pady=(10, 20))

        self.file_counter_label = tk.Label(
            self.frame, text=_("0 / 0 files"), font=("Arial", 13, "bold"),
            bg=c['bg_frame'], fg=c['text_light']
        )
        self.file_counter_label.pack(pady=(0, 20))

        tk.Frame(self.frame, height=2, bg=c['text_gray']).pack(fill="x", padx=30, pady=10)

        tk.Label(
            self.frame, text=_("Details:"), font=("Arial", 11, "bold"),
            bg=c['bg_frame'], fg=c['text_light']
        ).pack(anchor="w", padx=30, pady=(10, 5))

        log_border = tk.Frame(self.frame, bg=c['text_gray'], relief="solid", bd=1)
        log_border.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        self.processing_log = scrolledtext.ScrolledText(
            log_border, width=80, height=12, font=("Consolas", 9),
            bg=c['bg_processing'], fg=c['text_processing'],
            wrap=tk.WORD, state="disabled", relief="flat", bd=0, padx=10, pady=8
        )
        self.processing_log.pack(fill="both", expand=True, padx=1, pady=1)

        # Cancel button frame
        self.cancel_frame = tk.Frame(self.frame, bg=c['bg_frame'])
        self.cancel_frame.pack(pady=10)

        tk.Button(
            self.cancel_frame, text=_("✖ Cancel"), command=self.cancel_processing,
            font=("Arial", 11, "bold"), bg=c['accent_red'], fg="white",
            cursor="hand2", padx=25, pady=10, relief="flat",
            activebackground=c['active_red']
        ).pack()

        # Completion buttons frame (hidden until done)
        self.completion_frame = tk.Frame(self.frame, bg=c['bg_frame'])
        btn_frame = tk.Frame(self.completion_frame, bg=c['bg_frame'])
        btn_frame.pack()

        tk.Button(
            btn_frame, text=_("✓ Done - Return to Main"),
            command=self._on_return,
            font=("Arial", 12, "bold"), bg=c['accent_green'], fg="white",
            cursor="hand2", padx=30, pady=12, relief="flat",
            activebackground=c['active_green'], bd=0
        ).pack(side="left", padx=10)

        tk.Button(
            btn_frame, text=_("↺ Process Another Folder"),
            command=self._on_return,
            font=("Arial", 11), bg=c['accent_blue'], fg="white",
            cursor="hand2", padx=20, pady=12, relief="flat",
            activebackground=c['active_blue'], bd=0
        ).pack(side="left", padx=10)

    def _on_return(self):
        if self.on_reset_and_return:
            self.on_reset_and_return()

    # ------------------------------------------------------------------ #
    #  Show / hide                                                         #
    # ------------------------------------------------------------------ #

    def show(self):
        """Show the processing panel and reset its state."""
        self.frame.pack(fill="both", expand=True, padx=30, pady=20)
        self.set_cancel(False)

        # Reset background for all widgets back to normal
        self._set_bg_recursive(self.frame, self.c['bg_frame'])

        self.status_title.config(text=_("Starting"), fg=self.c['text_light'])
        self.status_subtitle.config(text=_("Initializing"))
        self.file_counter_label.config(text=_("0 / 0 files"))
        self.current_file_label.config(text="")

        self.processing_log.config(state="normal")
        self.processing_log.delete(1.0, tk.END)
        self.processing_log.config(state="disabled")

        self.cancel_frame.pack(pady=10)
        self.completion_frame.pack_forget()
        self.start_spinner()

    def hide(self):
        self.frame.pack_forget()

    def reset_bg(self):
        self._set_bg_recursive(self.frame, self.c['bg_frame'])

    # ------------------------------------------------------------------ #
    #  Background helper                                                   #
    # ------------------------------------------------------------------ #

    def _set_bg_recursive(self, widget, color):
        """Recursively set bg color on all widgets, skipping those that don't support it
        (e.g. ScrolledText internals) and intentionally-colored widgets like the log."""
        # Keep the log box always dark and buttons always their original color
        if widget is self.processing_log:
            return
        if isinstance(widget, tk.Button):
            return
        try:
            widget.config(bg=color)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._set_bg_recursive(child, color)

    # ------------------------------------------------------------------ #
    #  Spinner                                                             #
    # ------------------------------------------------------------------ #

    def start_spinner(self):
        self.spinner_running = True
        self._tick_spinner()

    def stop_spinner(self):
        self.spinner_running = False

    def _tick_spinner(self):
        if not self.spinner_running:
            return
        spinner = self.spinner_chars[self.spinner_index]
        current = self.status_title.cget("text")
        if any(ch in current for ch in self.spinner_chars):
            current = current.split()[0] + " " + " ".join(current.split()[1:-1])
        self.status_title.config(text=f"{current} {spinner}")
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
        self.parent.after(100, self._tick_spinner)

    # ------------------------------------------------------------------ #
    #  Status / log updates                                                #
    # ------------------------------------------------------------------ #

    def update_status(self, title, subtitle, progress=None, total=None, current_file=""):
        was_spinning = self.spinner_running
        if was_spinning:
            self.stop_spinner()
        self.status_title.config(text=title)
        self.status_subtitle.config(text=subtitle)
        if progress is not None and total is not None and total > 0:
            self.file_counter_label.config(text=f"{progress} / {total} files")
        if current_file:
            self.current_file_label.config(text=f">> {current_file}")
        if was_spinning:
            self.start_spinner()
        self.parent.update_idletasks()

    def log(self, message):
        self.processing_log.config(state="normal")
        self.processing_log.insert(tk.END, message + "\n")
        self.processing_log.see(tk.END)
        self.processing_log.config(state="disabled")
        self.parent.update_idletasks()

    def animate_dots(self, text):
        try:
            self.processing_log.config(state='normal')
            current_text = self.processing_log.get("end-2c linestart", "end-1c")
            if current_text.strip().startswith("Processing"):
                pos = self.processing_log.index("end-2c linestart")
                self.processing_log.delete(pos, "end-1c")
                self.processing_log.insert(pos, text + "\n")
            else:
                self.processing_log.insert("end", text + "\n")
            self.processing_log.config(state='disabled')
            self.processing_log.see("end")
            self.parent.update_idletasks()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Cancel                                                              #
    # ------------------------------------------------------------------ #

    def cancel_processing(self):
        if not self.get_is_processing():
            return
        if messagebox.askyesno(
            _("Cancel Processing"),
            _("Are you sure you want to cancel?\n\nAny incomplete CHD files will be deleted."),
            icon='warning'
        ):
            self.set_cancel(True)
            self.log("\n[!] Cancellation requested...")
            self.log("Cleaning up and returning to main screen...")

    # ------------------------------------------------------------------ #
    #  Completion                                                          #
    # ------------------------------------------------------------------ #

    def show_completion(self, success=True, converted=0, skipped=0, failed=0):
        self.stop_spinner()
        self.cancel_frame.pack_forget()
        self.sound_player.play("success" if success else "fail", self.sound_player.volume)

        c    = self.c
        mode = self.get_mode()

        if mode == "health":
            if success and failed == 0:
                self.status_title.config(text=_("[✓] All ROMs Verified Successfully!"), fg=c['accent_green'])
                self.status_subtitle.config(text=_("All CHD files passed verification"))
                self._set_bg_recursive(self.frame, c['state_success'])
            elif converted > 0:
                self.status_title.config(text=_("[!] Health Check Complete with Issues"), fg=c['accent_orange'])
                self.status_subtitle.config(text=_("Some files failed verification - check details above"))
                self._set_bg_recursive(self.frame, c['state_warning'])
            else:
                self.status_title.config(text=_("[x] Health Check Failed"), fg=c['accent_red'])
                self.status_subtitle.config(text=_("No files verified successfully"))
                self._set_bg_recursive(self.frame, c['state_error'])
        else:
            if success:
                self.status_title.config(text=_("[✓] Completed Successfully!"), fg=c['accent_green'])
                self.status_subtitle.config(text=_("All operations finished"))
                self._set_bg_recursive(self.frame, c['state_success'])
            else:
                self.status_title.config(text=_("[!] Completed with Errors"), fg=c['accent_red'])
                self.status_subtitle.config(text=_("Some operations failed - check details below"))
                self._set_bg_recursive(self.frame, c['state_error'])

        self.completion_frame.pack(pady=20)
        self.parent.update_idletasks()
