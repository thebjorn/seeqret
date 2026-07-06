# PyInstaller spec for the one-file seeqret GUI executable.
#
# Build from the repo root:
#
#   pyinstaller packaging/seeqret-gui.spec --noconfirm
#
# Produces dist/seeqret-gui.exe (windowed, no console). The exe is
# self-contained: it unpacks to a temp dir on launch and needs only
# the SEEQRET env var, like the CLI.
import os

repo_root = os.path.abspath(os.path.join(SPECPATH, '..'))  # noqa: F821

a = Analysis(  # noqa: F821
    [os.path.join(SPECPATH, 'launch_gui.py')],  # noqa: F821
    pathex=[repo_root],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # only QtCore/QtGui/QtWidgets are used -- keep the fat out
        'PySide6.QtNetwork',
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.QtWebEngineCore',
        'PySide6.QtPdf',
        'PySide6.QtOpenGL',
        # stdlib/test baggage
        'tkinter',
        'pytest',
        'unittest',
    ],
    noarchive=False,
)

# Trim bundled Qt payloads the widget set never touches: the software
# OpenGL fallback rasterizer (~20 MB) and the Qt translation catalogs.
_drop_binaries = ('opengl32sw.dll', 'qt6network', 'qt6qml', 'qt6quick',
                  'qt6pdf', 'qt6virtualkeyboard')
a.binaries = [b for b in a.binaries
              if not any(k in b[0].lower() for k in _drop_binaries)]
a.datas = [d for d in a.datas
           if not d[0].replace('\\', '/').startswith(
               'PySide6/translations')]

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='seeqret-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
