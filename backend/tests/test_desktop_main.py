"""Regression tests for desktop entrypoint behavior in desktop_main.py."""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def test_migrations_fresh_db(tmp_path):
    """DB-04a: run_migrations() creates full schema on a fresh SQLite DB.

    RED state: ImportError because desktop_main.py does not yet exist.
    After Plan 11-04 creates it, the function call applies all 7 migrations.
    """
    # Import at function scope to get ImportError (not collection error) when absent.
    from desktop_main import run_migrations  # noqa: PLC0415

    db_url = f"sqlite:///{tmp_path / 'fresh.db'}"
    alembic_dir = Path(__file__).resolve().parents[2] / "alembic"

    # Should not raise; creates all tables via alembic upgrade head.
    run_migrations(db_url, alembic_dir)

    import sqlite3
    conn = sqlite3.connect(str(tmp_path / "fresh.db"))
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

    assert "contract_files" in table_names, (
        f"Expected 'contract_files' table after migration, got: {table_names!r}"
    )


def test_migrations_idempotent(tmp_path):
    """DB-04b: run_migrations() is idempotent — second call does not raise.

    RED state: same ImportError as above.
    After Plan 11-04, both calls complete silently (Alembic skips applied revisions).
    """
    from desktop_main import run_migrations  # noqa: PLC0415

    db_url = f"sqlite:///{tmp_path / 'idempotent.db'}"
    alembic_dir = Path(__file__).resolve().parents[2] / "alembic"

    # First call: apply all migrations.
    run_migrations(db_url, alembic_dir)

    # Second call: must NOT raise (Alembic already at head, nothing to do).
    run_migrations(db_url, alembic_dir)

    # If we reach here, idempotency is confirmed.
    assert True


def test_main_fails_fast_when_required_resources_missing(tmp_path, monkeypatch):
    """Startup must fail-fast when a required bundle resource directory is absent."""
    from desktop_main import main  # noqa: PLC0415

    bundle = tmp_path / "bundle"
    (bundle / "alembic").mkdir(parents=True)
    (bundle / "dicts").mkdir(parents=True)
    # templates intentionally missing

    monkeypatch.setattr("desktop_main._get_bundle_base", lambda: bundle)
    monkeypatch.setenv("CTRX_DATA_DIR", str(tmp_path / "data"))

    with pytest.raises(RuntimeError, match="Missing required resource directory"):
        main()


def test_main_uses_sqlite_then_clears_cache_then_migrates_then_runs_uvicorn(
    tmp_path, monkeypatch
):
    """Startup chain order is deterministic and settings cache is cleared."""
    from desktop_main import main  # noqa: PLC0415

    bundle = tmp_path / "bundle"
    (bundle / "alembic").mkdir(parents=True)
    (bundle / "dicts").mkdir(parents=True)
    (bundle / "templates").mkdir(parents=True)

    events = []
    cache_clear = MagicMock(side_effect=lambda: events.append("cache_clear"))
    get_settings_stub = MagicMock()
    get_settings_stub.cache_clear = cache_clear

    def _run_migrations(db_url, alembic_dir):
        events.append(("migrate", db_url, str(alembic_dir)))

    def _run_uvicorn(*args, **kwargs):
        events.append(("uvicorn", args, kwargs))

    monkeypatch.setattr("desktop_main._get_bundle_base", lambda: bundle)
    monkeypatch.setattr("desktop_main.run_migrations", _run_migrations)
    monkeypatch.setenv("CTRX_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CTRX_PORT", "8766")
    monkeypatch.setattr("backend.app.config.get_settings", get_settings_stub)
    monkeypatch.setattr("uvicorn.run", _run_uvicorn)

    main()

    expected_db = f"sqlite:///{tmp_path / 'data' / 'ctrx.db'}"
    assert os.environ["DATABASE_URL"] == expected_db
    assert events[0] == "cache_clear"
    assert events[1] == ("migrate", expected_db, str(bundle / "alembic"))
    assert events[2][0] == "uvicorn"
    assert events[2][1] == ("backend.app.main:app",)
    assert events[2][2]["host"] == "127.0.0.1"
    assert events[2][2]["port"] == 8766


def test_main_never_falls_back_to_postgres_url(tmp_path, monkeypatch):
    """Desktop startup must enforce sqlite URL and reject postgres fallback."""
    from desktop_main import main  # noqa: PLC0415

    bundle = tmp_path / "bundle"
    (bundle / "alembic").mkdir(parents=True)
    (bundle / "dicts").mkdir(parents=True)
    (bundle / "templates").mkdir(parents=True)

    monkeypatch.setattr("desktop_main._get_bundle_base", lambda: bundle)
    monkeypatch.setenv("CTRX_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:bad@localhost:5432/contract_info",
    )

    captured = {}

    def _run_migrations(db_url, _):
        captured["db_url"] = db_url
        assert db_url.startswith("sqlite:///")
        assert "postgresql" not in db_url

    monkeypatch.setattr("desktop_main.run_migrations", _run_migrations)
    monkeypatch.setattr("backend.app.config.get_settings", MagicMock(cache_clear=MagicMock()))
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: None)

    main()
    assert captured["db_url"].startswith("sqlite:///")
