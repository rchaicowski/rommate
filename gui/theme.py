"""Theme and color constants for RomMate GUI"""


class DarkTheme:
    """Dark theme colors for RomMate"""
    
    # Background colors
    BG_DARK = "#2b2b2b"
    BG_FRAME = "#3c3c3c"
    BG_PROCESSING = "#1e1e1e"
    BG_INFO_BOX = "#1a237e"
    
    # Text colors
    TEXT_LIGHT = "#e0e0e0"
    TEXT_GRAY = "#9e9e9e"
    TEXT_PROCESSING = "#d4d4d4"
    TEXT_INFO = "#90caf9"
    TEXT_ERROR = "#ff6b6b"
    TEXT_SUCCESS = "#51cf66"
    
    # Accent colors
    ACCENT_BLUE = "#42a5f5"
    ACCENT_GREEN = "#66bb6a"
    ACCENT_RED = "#ef5350"
    ACCENT_ORANGE = "#ff9800"
    
    # State colors (background states)
    STATE_SUCCESS = "#1b5e20"
    STATE_WARNING = "#f57f17"
    STATE_ERROR = "#b71c1c"
    
    # Active/hover colors
    ACTIVE_GREEN = "#4caf50"
    ACTIVE_RED = "#d32f2f"
    ACTIVE_BLUE = "#1e88e5"


class LightTheme:
    """Light theme (Famicom inspired) colors for RomMate"""
    
    # Background colors (Famicom beige/cream)
    BG_DARK = "#f5f3e8"
    BG_FRAME = "#ffffff"
    BG_PROCESSING = "#fafafa"
    BG_INFO_BOX = "#fff8e1"
    
    # Text colors
    TEXT_LIGHT = "#2d2d2d"
    TEXT_GRAY = "#616161"
    TEXT_PROCESSING = "#424242"
    TEXT_INFO = "#8b2635"
    TEXT_ERROR = "#c62828"
    TEXT_SUCCESS = "#2e7d32"
    
    # Accent colors (Famicom burgundy/gold)
    ACCENT_BLUE = "#1976d2"
    ACCENT_GREEN = "#43a047"
    ACCENT_RED = "#8b2635"
    ACCENT_ORANGE = "#d4a574"
    
    # State colors (background states)
    STATE_SUCCESS = "#c8e6c9"
    STATE_WARNING = "#fff3e0"
    STATE_ERROR = "#ffcdd2"
    
    # Active/hover colors
    ACTIVE_GREEN = "#66bb6a"
    ACTIVE_RED = "#e53935"
    ACTIVE_BLUE = "#42a5f5"


# Default theme (will be switchable in settings later)
Theme = DarkTheme
