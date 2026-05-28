"""
Wave-0 RED tests for DB-02: CTRX_DATA_DIR path resolution.

These tests must FAIL before Plan 11-03 adds data_dir() / uploads_dir() /
_bundle_base() to backend/app/config.py:
  - test_uploads_dir_uses_env:   ImportError — uploads_dir not in config
  - test_uploads_dir_fallback:   ImportError — uploads_dir not in config
  - test_bundle_base_frozen:     AttributeError — _bundle_base not in config
"""

import importlib
import sys

import pytest
from pathlib import Path


def test_uploads_dir_uses_env(tmp_path, monkeypatch):
    """DB-02a: CTRX_DATA_DIR env var -> uploads_dir() returns data_dir / 'uploads'."""
    monkeypatch.setenv("CTRX_DATA_DIR", str(tmp_path))

    # Import AFTER env is set so data_dir() picks up the override.
    # ImportError (RED) because uploads_dir does not yet exist in config.py.
    from backend.app.config import get_settings, uploads_dir

    get_settings.cache_clear()
    result = uploads_dir()
    assert result == tmp_path / "uploads", (
        f"Expected {tmp_path / 'uploads'}, got {result!r}"
    )


def test_uploads_dir_fallback(monkeypatch):
    """DB-02b: unset CTRX_DATA_DIR -> uploads_dir() falls back to PROJECT_ROOT / 'uploads'."""
    monkeypatch.delenv("CTRX_DATA_DIR", raising=False)

    # ImportError (RED) because uploads_dir / PROJECT_ROOT not exported from config.py
    # in the expected form yet.
    from backend.app.config import PROJECT_ROOT, get_settings, uploads_dir

    get_settings.cache_clear()
    assert uploads_dir() == PROJECT_ROOT / "uploads", (
        f"Expected {PROJECT_ROOT / 'uploads'}, got {uploads_dir()!r}"
    )


def test_bundle_base_frozen(monkeypatch, tmp_path):
    """DB-02c: sys.frozen=True + sys._MEIPASS -> _bundle_base() returns sys._MEIPASS."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    # Force reimport so config.py picks up the mocked sys attributes.
    # AttributeError (RED) because _bundle_base() does not yet exist in config.py.
    import backend.app.config as cfg_module

    importlib.reload(cfg_module)
    result = cfg_module._bundle_base()
    assert result == tmp_path, (
        f"Expected {tmp_path}, got {result!r}"
    )
