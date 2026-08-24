# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置
# 用法: pyinstaller Nexus-AI.spec

import sys
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("cryptography")
try:
    # mcp 仅在 mcp_client 中延迟导入（轻量 SDK，pydantic/httpx）
    hiddenimports += collect_submodules("mcp")
except Exception:
    pass

# 重型且未被应用使用的库：排除，避免把 torch/cv2/pandas/scipy 等卷进 exe
# （这些多由 fastmcp 的隐藏导入牵连，应用本身不依赖它们）
_EXCLUDE = [
    "tkinter", "unittest", "pydoc",
    "torch", "torchvision", "torchaudio",
    "cv2", "numpy.testing",
    "pandas", "scipy", "sympy",
    "matplotlib", "PIL", "sklearn",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_EXCLUDE,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Nexus-AI-0.3.0",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # 可替换为 .ico 路径
)