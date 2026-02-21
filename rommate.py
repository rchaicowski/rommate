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

#!/usr/bin/env python3
"""
RomMate - Your ROM companion
Convert disc images to CHD and create M3U playlists
"""

import tkinter as tk
from gui.main_window import RomMateGUI


if __name__ == "__main__":
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()
    
    app = RomMateGUI(root)
    root.mainloop()
