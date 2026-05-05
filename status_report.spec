# StatusReport PyInstaller build spec -- D-08 (checked into repo).
# Build: run build.bat from repo root (activates venv, runs pyinstaller).
# Output: dist/status_report/ -- IT copies this folder to USB flash drive.
#
# Constraints:
#   --onedir only (EXE exclude_binaries=True + COLLECT) -- CLAUDE.md, D-07
#   NEVER --onefile: quarantined by CrowdStrike Falcon on enrolled machines
#   upx=False: UPX packer signature increases AV false positive rate (RESEARCH.md)
#   console=True: D-04 requires verbose progress output via print()

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# win32com uses COM dispatch -- PyInstaller cannot trace these imports statically.
# collect_submodules ensures all win32com submodules are included (RESEARCH.md Pitfall 1).
win32com_hidden = collect_submodules('win32com')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Bundle Jinja2 template so importlib.resources finds it inside _internal/.
        # renderer/_load_template_source() uses ir.files('renderer').joinpath(...)
        # In --onedir mode this lands at _internal/renderer/templates/ on disk.
        # RESEARCH.md Pitfall 3: templates MUST be declared here -- not auto-collected.
        ('renderer/templates', 'renderer/templates'),
    ],
    hiddenimports=[
        'wmi',
        'win32api',
        'win32con',
        'win32com',
        'win32com.client',
        'win32com.server',
        'pywintypes',
        'pythoncom',
        'win32transaction',
        'win32security',
    ] + win32com_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Safe excludes -- none of these are needed by wmi, psutil, jinja2, or winreg.
        # Remove any entry here if you see ModuleNotFoundError at runtime (RESEARCH.md Pitfall 8).
        'tkinter',
        'unittest',
        'email',
        'xml',
        'xmlrpc',
        'http',
        'urllib',
        'multiprocessing',
        'concurrent',
        'asyncio',
        'sqlite3',
        'ssl',
        '_ssl',
        'test',
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
    [],
    exclude_binaries=True,   # --onedir: binaries go to COLLECT, not embedded in exe
    name='status_report',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # NEVER True -- UPX packer increases AV suspicion (RESEARCH.md)
    console=True,            # D-04: show console window; NEVER --noconsole
    disable_windowed_traceback=False,
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
    upx=False,
    upx_exclude=[],
    name='status_report',    # dist/status_report/ is the distributable folder
)
