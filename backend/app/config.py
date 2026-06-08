import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _bundle_base() -> Path:
    """Resolve base directory for bundled read-only assets (templates, dicts, alembic).

    In frozen (PyInstaller) mode: returns sys._MEIPASS.
    In dev/Docker mode: returns the project root (parents[2] of this file).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Resolve user-writable data directory (uploads, exports, DB file).

    Desktop mode: CTRX_DATA_DIR env var (set by Electron main before spawning Python).
    Dev/Docker mode: PROJECT_ROOT (unchanged behaviour).
    """
    raw = os.environ.get("CTRX_DATA_DIR", "").strip()
    if raw:
        p = Path(raw)
        p.mkdir(parents=True, exist_ok=True)
        return p
    return PROJECT_ROOT


def uploads_dir() -> Path:
    return data_dir() / "uploads"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg2://postgres:contract_info_dev@localhost:5433/contract_info"
    )

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout: int = 120
    llm_max_retries: int = 1
    llm_max_tokens: int = 16384
    rag_top_k: int = 3

    api_key: str = ""
    cors_origins: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def cors_origin_list() -> list[str]:
    raw = get_settings().cors_origins.strip()
    origins: list[str] = []
    if raw:
        origins = [o.strip() for o in raw.split(",") if o.strip()]
    # Electron loads frontend via file://; browser sends Origin: null on cross-origin fetch.
    if os.environ.get("CTRX_DATA_DIR"):
        for extra in ("null", "file://"):
            if extra not in origins:
                origins.append(extra)
    return origins


def templates_dir() -> Path:
    return _bundle_base() / "templates"


def exports_dir() -> Path:
    return data_dir() / "exports"


def models_dir() -> Path | None:
    """Resolve local model directory configured by CTRX_MODELS_DIR."""
    raw = os.environ.get("CTRX_MODELS_DIR", "").strip()
    if raw:
        return Path(raw)
    return None
