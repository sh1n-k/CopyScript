# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import platform


project_root = Path(SPECPATH).parents[1]
is_macos = platform.system() == "Darwin"
is_windows = platform.system() == "Windows"
is_linux = platform.system() == "Linux"
hiddenimports = ["youtube_transcript_api"]
datas = []
icon_path = None

if is_macos:
    hiddenimports.append("AppKit")

if is_windows or is_linux:
    hiddenimports.extend(["pystray", "PIL"])
    icon_path = project_root / "assets" / "CopyScript.ico"
    datas.append((str(icon_path), "assets"))

if is_windows:
    hiddenimports.append("win11toast")

if is_linux:
    hiddenimports.append("optparse")

a = Analysis(
    [str(project_root / "copyscript" / "main.py")],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="CopyScript",
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
    icon=str(icon_path) if icon_path else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CopyScript",
)

if is_macos:
    app = BUNDLE(
        coll,
        name="CopyScript.app",
        icon=None,
        bundle_identifier=None,
    )
