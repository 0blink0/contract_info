"""Desktop entry point for CTRX PyInstaller bundle.

Responsibilities:
1. Resolve data directory (CTRX_DATA_DIR or ~/.ctrx).
2. Set DATABASE_URL env var to sqlite:///CTRX_DATA_DIR/ctrx.db BEFORE any
   backend module is imported (to avoid stale Settings from lru_cache).
3. Run alembic upgrade head programmatically (no alembic.ini required).
4. Start uvicorn on 127.0.0.1:CTRX_PORT (default 8765).

This file must be importable as ``import desktop_main`` from the project root.
No backend modules are imported at module level — all backend imports are
deferred to function scope so that DATABASE_URL is already in os.environ when
SQLAlchemy loads Settings.
"""

import os
import sys
from pathlib import Path


def _get_bundle_base() -> Path:
    """Resolve project/bundle root for read-only assets (alembic dir, templates).

    Frozen (PyInstaller) mode: sys._MEIPASS (extracted bundle contents).
    Dev/Docker mode: the directory containing this file (project root).

    Note: desktop_main.py lives at project root, so parent is the project root.
    (Not parents[2] like backend/app/config.py which is two levels deeper.)
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def run_migrations(db_url: str, alembic_dir: Path) -> None:
    """Run alembic upgrade head against db_url using a programmatic Config.

    No alembic.ini file is required.  The alembic_dir must contain the
    script package (versions/ sub-directory and env.py).

    Args:
        db_url:     SQLAlchemy database URL, e.g. "sqlite:///path/to/ctrx.db".
        alembic_dir: Path to the alembic/ directory (containing env.py).

    Raises:
        RuntimeError: If alembic_dir does not exist.
    """
    from alembic.config import Config
    from alembic import command

    if not alembic_dir.is_dir(): raise RuntimeError(f"Alembic directory not found: {alembic_dir}")

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")


def _assert_required_resources(bundle_base: Path) -> None:
    """Fail-fast if required bundled resource directories are missing."""
    required_dirs = ("alembic", "dicts", "templates")
    for directory in required_dirs:
        path = bundle_base / directory
        if not path.is_dir():
            raise RuntimeError(f"Missing required resource directory: {path}")


def main() -> None:
    """Application entry point: configure environment, migrate DB, start server."""
    bundle_base = _get_bundle_base()
    _assert_required_resources(bundle_base)

    # Resolve data directory — writable location for DB, uploads, exports.
    data_path = Path(os.environ.get("CTRX_DATA_DIR") or Path.home() / ".ctrx")
    data_path.mkdir(parents=True, exist_ok=True)

    # Set env vars BEFORE importing any backend module so Settings picks them up.
    db_url = f"sqlite:///{data_path / 'ctrx.db'}"
    os.environ["DATABASE_URL"] = db_url
    os.environ["CTRX_DATA_DIR"] = str(data_path)
    os.environ.setdefault("CTRX_PORT", "8765")

    # Clear lru_cache so get_settings() re-reads the newly set DATABASE_URL.
    from backend.app.config import get_settings

    get_settings.cache_clear()

    # Apply all pending migrations before uvicorn starts accepting requests.
    alembic_dir = bundle_base / "alembic"
    run_migrations(db_url, alembic_dir)

    # Start the ASGI server.
    import uvicorn
    port = int(os.environ.get("CTRX_PORT", "8765"))
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
