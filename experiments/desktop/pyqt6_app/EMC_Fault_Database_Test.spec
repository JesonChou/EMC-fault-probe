# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['EMC_Fault_Database_Test.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('data_1.json', '.'),
        ('data_2.json', '.'),
        ('BUAA-白底蓝字.png', '.'),
        ('BUAA_logo_2048px.png', '.'),
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
    icon=['BUAA_logo.ico'],
)
