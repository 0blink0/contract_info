"""
Wave-0 RED tests for DB-01: dialect-agnostic migration (SQLite).

These tests must FAIL before Plan 11-02 touches the migrations:
  - test_sqlite_migration_all_revisions: fails because migration 001/002 use
    postgresql.JSONB which SQLite cannot compile
    (CompileError: can't render element of type JSONB), OR because
    server_default=sa.text("now()") fails on SQLite (no now() function).
  - test_json_roundtrip: same migration failure; unreachable until 11-02.
"""

import json
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _make_alembic_cfg(db_path: Path, monkeypatch=None) -> Config:
    """Build an Alembic Config object pointing at a SQLite file.

    We also set DATABASE_URL env var so that alembic/env.py's call to
    get_settings() returns the SQLite URL instead of the default PostgreSQL URL.
    """
    alembic_dir = Path(__file__).resolve().parents[2] / "alembic"
    sqlite_url = f"sqlite:///{db_path}"

    if monkeypatch is not None:
        monkeypatch.setenv("DATABASE_URL", sqlite_url)
        # Clear lru_cache so get_settings() re-reads DATABASE_URL.
        from backend.app.config import get_settings
        get_settings.cache_clear()

    cfg = Config()
    cfg.set_main_option("script_location", str(alembic_dir))
    cfg.set_main_option("sqlalchemy.url", sqlite_url)
    return cfg


def test_sqlite_migration_all_revisions(tmp_path, monkeypatch):
    """DB-01a: alembic upgrade head succeeds against SQLite; all 7 revisions applied.

    RED state: fails because migrations 001/002/006/007 use postgresql.JSONB /
    postgresql.UUID, which SQLite dialect cannot compile.
    """
    db_file = tmp_path / "test.db"
    cfg = _make_alembic_cfg(db_file, monkeypatch)

    # FAILS in RED state: CompileError on postgresql.JSONB or now() OperationalError.
    # Passes after Plan 11-02 replaces postgresql types with sa.JSON / sa.Uuid.
    command.upgrade(cfg, "head")

    engine = sa.create_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        result = conn.execute(sa.text("SELECT version_num FROM alembic_version"))
        rows = [row[0] for row in result]

    # After all 7 migrations apply, the version table should contain "007".
    assert "007" in rows, f"Expected '007' in alembic_version, got {rows!r}"


def test_json_roundtrip(tmp_path, monkeypatch):
    """DB-01b: extraction_result stores dict and reads back as dict (not JSON string).

    RED state: same migration failure prevents reaching the assertion.
    """
    db_file = tmp_path / "roundtrip.db"
    cfg = _make_alembic_cfg(db_file, monkeypatch)

    # Fails in RED state (migration cannot apply to SQLite due to postgresql types).
    command.upgrade(cfg, "head")

    engine = sa.create_engine(f"sqlite:///{db_file}")
    file_id = uuid.uuid4()
    payload = {"key": "val", "nested": {"x": 1}}

    with engine.connect() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO contract_files "
                "(id, filename, status, extraction_result) "
                "VALUES (:id, :fn, :st, :er)"
            ),
            {
                "id": str(file_id),
                "fn": "test.docx",
                "st": "done",
                "er": json.dumps(payload),
            },
        )
        conn.commit()

        # Use type_coerce so SQLAlchemy's JSON type processes the TEXT value
        # from SQLite (raw sa.text() returns str; typed select returns dict).
        t = sa.table("contract_files", sa.column("id"), sa.column("extraction_result", sa.JSON))
        row = conn.execute(
            sa.select(t.c.extraction_result).where(t.c.id == str(file_id))
        ).fetchone()

    # sa.JSON auto-deserializes on read; result must be dict, not str.
    assert isinstance(row[0], dict), (
        f"Expected dict, got {type(row[0])!r}: {row[0]!r}"
    )
    assert row[0]["key"] == "val"
