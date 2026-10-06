# -*- mode: python ; coding: utf-8 -*-
"""koutu PyInstaller 打包 spec（--onedir --windowed）。

用法（仓库根执行；或直接用 packaging\\打包.ps1）：
  .venv\\Scripts\\python.exe -m PyInstaller --noconfirm --clean packaging\\koutu.spec

产物：dist\\koutu\\ = koutu.exe + _internal\\；
随包资源（排版demo.png / 使用说明.txt）由 打包.ps1 拷贝到 exe 同级。
"""
import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()  # packaging\ 目录（PyInstaller 注入的 SPECPATH）
ROOT = SPEC_DIR.parent               # 仓库根
sys.path.insert(0, str(ROOT))

a = Analysis(
    [str(SPEC_DIR / 'launcher.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
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
    [],
    exclude_binaries=True,
    name='koutu',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='koutu',
)
