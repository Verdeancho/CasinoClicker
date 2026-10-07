# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# los juegos se importan bajo demanda (importlib): hay que incluirlos a mano. Se listan desde las carpetas (sin
# importar nada), porque collect_submodules no ve el proyecto según desde dónde se lance PyInstaller
HIDDEN = []
for root, dirs, files in os.walk(os.path.join(SPECPATH, 'casino')):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    pkg = os.path.relpath(root, SPECPATH).replace(os.sep, '.')
    HIDDEN += [pkg if f == '__init__.py' else f'{pkg}.{f[:-3]}' for f in files if f.endswith('.py')]
if 'casino.games.pickaxe' not in HIDDEN:
    raise SystemExit('No se encuentran los juegos para incluirlos en la build')
MAC = sys.platform == 'darwin'


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('casino/assets', 'casino/assets')],
    hiddenimports=HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

if not MAC:
    # Windows: un solo .exe
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='CasinoClicker',
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
        icon=['casino_clicker.ico'],
    )
else:
    # macOS: CasinoClicker.app (carpeta dentro del bundle; Pillow convierte el icono a .icns)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='CasinoClicker',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=['casino_clicker.ico'],
    )
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='CasinoClicker')
    app = BUNDLE(
        coll,
        name='CasinoClicker.app',
        icon='casino_clicker.ico',
        bundle_identifier='com.verdeancho.casinoclicker',
        info_plist={
            'CFBundleName': 'Casino Clicker',
            'CFBundleDisplayName': 'Casino Clicker',
            'CFBundleShortVersionString': '4.4',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '11.0',
        },
    )
