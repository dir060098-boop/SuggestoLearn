# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets',  'assets'),
        ('data/words_example.csv', 'data'),
    ],
    hiddenimports=[
        'edge_tts',
        'pygame',
        'pydub',
        'sqlite3',
        'pandas',
    ] + collect_submodules('PyQt6'),
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
    [],
    exclude_binaries=True,
    name='SuggestoLearn',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SuggestoLearn',
)

app = BUNDLE(
    coll,
    name='SuggestoLearn.app',
    icon=None,
    bundle_identifier='com.suggestolearn.app',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleName': 'SuggestoLearn',
        'NSMicrophoneUsageDescription': 'Not required',
    },
)
