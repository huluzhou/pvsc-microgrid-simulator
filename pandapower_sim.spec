# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('src/assets', 'assets')],
    hiddenimports=['tomli_w', 'tomli'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtBluetooth', 'PySide6.QtConcurrent', 'PySide6.QtDBus', 'PySide6.QtDesigner', 'PySide6.QtHelp', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtNetwork', 'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets', 'PySide6.QtPositioning', 'PySide6.QtPrintSupport', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickControls2', 'PySide6.QtQuickWidgets', 'PySide6.QtRemoteObjects', 'PySide6.QtScxml', 'PySide6.QtSensors', 'PySide6.QtSerialPort', 'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtWebChannel', 'PySide6.QtWebEngine', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebSockets', 'PySide6.QtXml', 'tkinter', 'Tkinter', 'matplotlib.backends.backend_tkagg', 'matplotlib.backends.backend_webagg', 'matplotlib.backends.backend_qt4agg', 'IPython', 'jupyter', 'notebook', 'pytest', 'test', 'doctest', 'distutils', 'setuptools', 'pkg_resources'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [('O', None, 'OPTION'), ('O', None, 'OPTION')],
    exclude_binaries=True,
    name='pandapower_sim',
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
    name='pandapower_sim',
)
