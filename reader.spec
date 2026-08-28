# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


ROOT = Path(SPECPATH)
pyside6_datas = collect_data_files('PySide6',
    includes=[
        'Qt/resources/*',
        'Qt/translations/*',
        'QtWebEngineProcess.exe',
        'Qt/libexec/*',
        'Qt/bin/QtWebEngineProcess.exe',
    ],
)
pyside6_hidden = (
    collect_submodules('PySide6.QtWebEngineCore')
    + collect_submodules('PySide6.QtWebEngineWidgets')
    + collect_submodules('PySide6.QtWebChannel')
)

a = Analysis(
    [str(ROOT / 'src/reader/__main__.py')],
    pathex=[str(ROOT / 'src')],
    binaries=[],
    datas=pyside6_datas
    + [
        (str(ROOT / 'assets/icons/reader.ico'), 'assets/icons'),
        (str(ROOT / 'assets/icons/reader-r.svg'), 'assets/icons'),
        (str(ROOT / 'assets/pptx-viewer'), 'assets/pptx-viewer'),
        (str(ROOT / 'assets/md-viewer'), 'assets/md-viewer'),
    ],
    hiddenimports=pyside6_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Reader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / 'assets/icons/reader.ico'),
    version=str(ROOT / 'version_info.txt'),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Reader',
)
