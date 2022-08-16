# -*- mode: python ; coding: utf-8 -*-

import os
import pathlib
import pypylon

_binaries = list()
_pathex = list()
for module in [pypylon,]:
    _dir = pathlib.Path(module.__file__).parent
    _dlls = [(str(dll), '.') for dll in _dir.glob('*.dll')]
    _pyds = [(str(dll), '.') for dll in _dir.glob('*.pyd')]
    _binaries.extend(_dlls)
    _binaries.extend(_pyds)
    _pathex.append(str(_dir))

_hiddenimports = list()
_hiddenimports.extend(['pypylon', 'pypylon.pylon', 'pypylon.genicam', 'pypylon._pylon', 'pypylon._genicam', 'pyvisa_py'])

_datas = list()
_datas.extend([ ('config_default.yml', '.') ])
for path, dirnames, filenames in os.walk('sequential'):
    foldername = str(path)
    #if foldername == 'sequential': foldername = '.'
    #else: foldername = foldername[11:]
    if foldername.endswith('__pycache__'): continue
    for f in filenames:
        if f.endswith('.py'): continue
        filepath = os.path.join(path,f)
        _datas.append((str(filepath),str(foldername)))


block_cipher = None


a = Analysis(
    ['start_sequential.py'],
    pathex=_pathex,
    binaries=_binaries,
    datas=_datas,
    hiddenimports=_hiddenimports,
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
    name='start_sequential',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='start_sequential',
)
