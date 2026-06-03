# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from importlib.util import find_spec
import sys


# PyInstaller executes spec without defining __file__; SPECPATH is provided.
ROOT = Path(globals().get("SPECPATH", Path.cwd())).resolve()
IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")

common_hidden = [
    "backend.app.main",
    "backend.app.models",
    "backend.app.models.contract_file",
    "sqlalchemy.dialects.sqlite",
    "pydantic_settings",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "httpx",
    "httpcore",
    "anyio",
]

windows_hidden = [
    "colorama",
    # --- Phase 23: lancedb / pyarrow / sentence-transformers (KB-PKG-01) ---
    "lancedb",
    "lancedb.remote",
    "lancedb.embeddings",
    "pyarrow",
    "pyarrow.vendored",
    "pyarrow.vendored.version",
    "sentence_transformers",
    "sentence_transformers.models",
    "sentence_transformers.util",
    "torch",
    "torch.utils",
    "torch.utils.data",
    "tokenizers",
    "transformers",
    "transformers.models",
    "transformers.models.bert",
    "transformers.models.xlm_roberta",
    "huggingface_hub",
    "huggingface_hub.file_download",
]

linux_hidden = []

hiddenimports = list(common_hidden)
if IS_WINDOWS:
    hiddenimports.extend(windows_hidden)
if IS_LINUX:
    hiddenimports.extend(linux_hidden)

# Optional dependency chain: include only when installed.
if find_spec("openai") is not None:
    hiddenimports.extend(["openai", "openai._client"])

datas = [
    (str(ROOT / "alembic"), "alembic"),
    (str(ROOT / "dicts"), "dicts"),
    (str(ROOT / "templates"), "templates"),
]

excludes = [
    "psycopg2",
]

a = Analysis(
    ["desktop_main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ctrx-backend",
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ctrx-backend",
)
