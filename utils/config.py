"""Configuration management for RomMate"""

import os
import json
from pathlib import Path


class Config:
    """Manages user preferences and settings"""
    
    def __init__(self):
        """Initialize config with default values"""
        # Config file location in user's home directory
        self.config_dir = os.path.join(Path.home(), '.rommate')
        self.config_file = os.path.join(self.config_dir, 'config.json')
        
        # Default settings
        self.defaults = {
            'last_folder': str(Path.home()),
            'sound_enabled': True,
            'sound_volume': 1.0,
            'delete_after_conversion': False
        }
        
        self.settings = self.load()
    
    def load(self):
        """Load settings from config file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults (in case new settings were added)
                    return {**self.defaults, **loaded}
        except Exception as e:
            print(f"Could not load config: {e}")
        
        return self.defaults.copy()
    
    def save(self):
        """Save settings to config file"""
        try:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_dir, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Could not save config: {e}")
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Set a setting value and save"""
        self.settings[key] = value
        self.save()
