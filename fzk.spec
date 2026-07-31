# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置:FZK 桌面应用。

构建(在 Windows + Python 3.12 环境下):
    pyinstaller fzk.spec --noconfirm

产物:dist/FZK.exe(onefile,约 80-120MB)。
首次启动稍慢(解包到临时目录),之后正常。
数据目录在 exe 旁的 data/ 文件夹(SQLite 库 + 上传图纸 + 日志)。
"""

import os
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

block_cipher = None
spec_root = Path(SPECPATH)  # noqa: F821  由 PyInstaller 注入,本文件所在目录
backend_dir = spec_root / "backend"
frontend_dist = spec_root / "frontend" / "dist"

# 前端构建产物作为数据文件打入,运行时解包到 _MEIPASS/frontend_dist
datas = []
if frontend_dist.is_dir():
    datas.append((str(frontend_dist), "frontend_dist"))

# backend/app 是纯 Python,PyInstaller 经 import 图(pathex 含 backend 目录)
# 自动收集进 PYZ,无需作为 datas;避免误打入 __pycache__。

# pywebview(Windows 走 EdgeChromium/WebView2)+ pythonnet(CLR 桥)的运行时资源,
# PyInstaller 静态分析难以全部捕获,这里显式收集。
for pkg in ("webview", "clr_loader", "pythonnet"):
    datas += collect_data_files(pkg)
    datas += collect_dynamic_libs(pkg)
hiddenimports = list(set(
    collect_submodules("webview")
    + collect_submodules("clr_loader")
    + [
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "bcrypt",
        "httpx",
        "httpx._transports",
        "httpx._transports.default",
        # SQLAlchemy 方言(桌面用 sqlite,但 import 链可能引用 pg)
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.sqlite.pysqlite",
        # pywebview Windows 后端
        "webview.platforms.edgechromium",
        "clr_loader",
        "pythonnet",
        # FastAPI / pydantic 内部
        "pydantic",
        "pydantic.deprecated",
        "pydantic_settings",
        "email_validator",
        # 解析相关
        "pdfplumber",
        "fitz",
        "openpyxl",
        "docx",
        "PIL",
    ]
))

a = Analysis(
    ["desktop_launcher.py"],
    pathex=[str(spec_root), str(backend_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 桌面模式用不到,剔除以减小体积
        "psycopg",
        "psycopg2",
        "minio",
        "boto3",
        "botocore",
        "s3transfer",
        "alembic",
        "passlib",
        "pytest",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="FZK",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 模式,无控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=str(spec_root / "build" / "fzk.ico"),  # 如有图标可启用
)
