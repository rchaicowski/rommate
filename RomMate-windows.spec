# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for RomMate - Windows

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files
datas = [
    ('locales',   'locales'),
    ('databases', 'databases'),
    ('sounds',    'sounds'),
    ('tools',     'tools'),
    ('icon.ico',  '.'),
    ('icon.png',  '.'),
]

# Collect customtkinter data files
datas += collect_data_files('customtkinter')

a = Analysis(
    ['rommate.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinterdnd2',
        'customtkinter',
        'pycaw',
        'comtypes',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RomMate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
