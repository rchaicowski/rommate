# RomMate - ROM companion tool
# Copyright (C) 2026 Rodrigo
# GNU General Public License v3.0 - see LICENSE file for details

"""Internationalization support for RomMate"""

import gettext
import os
from pathlib import Path

_translator = None
_current_language = 'en'

SUPPORTED_LANGUAGES = {
    'en': 'English',
    'pt_BR': 'Português (Brasil)',
    'pt_PT': 'Português (Portugal)',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'it': 'Italiano',
    'ja': '日本語',
    'zh_CN': '中文（简体）',
}

CJK_LANGUAGES = {'ja', 'zh_CN'}

def get_cjk_font(size=11, style=''):
    """Return a CJK-compatible font tuple for the current OS."""
    import platform
    system = platform.system()
    if system == 'Windows':
        family = 'MS Gothic' if _current_language == 'ja' else 'Microsoft YaHei'
    elif system == 'Darwin':
        family = 'Hiragino Sans' if _current_language == 'ja' else 'PingFang SC'
    else:
        family = 'Noto Sans CJK JP' if _current_language == 'ja' else 'Noto Sans CJK SC'
    return (family, size, style) if style else (family, size)

def needs_cjk_font():
    """Return True if the current language needs a CJK font."""
    return _current_language in CJK_LANGUAGES

def setup_i18n(language='en'):
    """Initialize the translation system.
    
    Args:
        language (str): Language code (e.g. 'en', 'pt_BR', 'es')
    """
    global _translator, _current_language

    _current_language = language

    import sys
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    locales_dir = os.path.join(base_dir, 'locales')

    try:
        _translator = gettext.translation(
            'rommate',
            localedir=locales_dir,
            languages=[language]
        )
        _translator.install()
    except FileNotFoundError:
        _translator = gettext.NullTranslations()
        _translator.install()


def get_language():
    """Return the current language code."""
    return _current_language


def _(text):
    """Translate a string.
    
    Args:
        text (str): String to translate
        
    Returns:
        str: Translated string, or original if no translation found
    """
    if _translator is None:
        return text
    return _translator.gettext(text)
