#!/usr/bin/env python3
"""
RomMate - Your ROM companion
Convert disc images to CHD and create M3U playlists
"""

import tkinter as tk
from gui.main_window import RomMateGUI


if __name__ == "__main__":
    root = tk.Tk()
    app = RomMateGUI(root)
    root.mainloop()
