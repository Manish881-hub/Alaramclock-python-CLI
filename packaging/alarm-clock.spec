# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for alarm-clock standalone executable."""

import platform
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/alarm_clock/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tomli',
        'alarm_clock',
        'alarm_clock.audio',
        'alarm_clock.cli',
        'alarm_clock.config',
        'alarm_clock.logging_conf',
        'alarm_clock.models',
        'alarm_clock.scheduler',
        'alarm_clock.service',
        'alarm_clock.storage',
        'alarm_clock.timezone',
        'alarm_clock.tui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'test',
        'unittest',
        'email',
        'http',
        'xml',
    ],
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
    name='alarm-clock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_travis=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if platform.system() == 'Windows':
    COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='alarm-clock',
    )
