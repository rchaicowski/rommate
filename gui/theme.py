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
    ACCENT_GREEN = "#42a5f5"
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
    
    # Background colors (Famicom beige/cream with gold accents)
    BG_DARK = "#d4a574"           # Gold/tan (main background)
    BG_FRAME = "#f5f3e8"          # Cream/beige (sections)
    BG_PROCESSING = "#fafafa"     # Light processing panel
    BG_INFO_BOX = "#fff8e1"       # Light yellow info box
    
    # Text colors
    TEXT_LIGHT = "#2d2d2d"        # Dark text
    TEXT_GRAY = "#5d4037"         # Brown-grey text 
    TEXT_PROCESSING = "#424242"   # Processing text
    TEXT_INFO = "#8b2635"         # Burgundy info text
    TEXT_ERROR = "#c62828"        # Red error
    TEXT_SUCCESS = "#2e7d32"      # Green success
    
    # Accent colors (Famicom burgundy/gold)
    ACCENT_BLUE = "#8b2635"       # Burgundy instead of blue!
    ACCENT_GREEN = "#8b2635"      # Green accent
    ACCENT_RED = "#8b2635"        # Burgundy (Famicom red)
    ACCENT_ORANGE = "#d4a574"     # Gold accent
    
    # State colors
    STATE_SUCCESS = "#c8e6c9"     # Light green background
    STATE_WARNING = "#fff3e0"     # Light orange background
    STATE_ERROR = "#ffcdd2"       # Light red background
    
    # Active/hover colors
    ACTIVE_GREEN = "#66bb6a"
    ACTIVE_RED = "#a52a2a"        # Darker burgundy 
    ACTIVE_BLUE = "#8b2635"       # Burgundy 


# Default theme - will be set by config
_current_theme = 'dark'

def set_theme(theme_name):
    """Set the active theme"""
    global Theme, _current_theme
    _current_theme = theme_name
    if theme_name == 'light':
        Theme = LightTheme
    else:
        Theme = DarkTheme
    return Theme

# Initialize with dark theme
Theme = DarkTheme
