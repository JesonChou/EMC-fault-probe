# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


APP_DIR = Path.cwd()
PROJECT_ROOT = APP_DIR.parents[2]
DATA_DIR = PROJECT_ROOT / 'data' / 'published' / 'v1'
ICON_DIR = APP_DIR / 'resources' / 'icons'

a = Analysis(
    [str(APP_DIR / 'EMC_Fault_Database_Test.py')],
    pathex=[str(APP_DIR)],
    binaries=[],
    datas=[
        (str(DATA_DIR / 'data_1.json'), 'data/published/v1'),
        (str(DATA_DIR / 'data_2.json'), 'data/published/v1'),
        (str(ICON_DIR / 'BUAA-白底蓝字.png'), 'resources/icons'),
        (str(ICON_DIR / 'BUAA_logo_2048px.png'), 'resources/icons'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EMC_Fault_Database_Test',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ICON_DIR / 'BUAA_logo.ico')],
)
