"""
Wave-0 RED tests for DB-04: desktop_main.run_migrations() programmatic Alembic.

These tests must FAIL before Plan 11-02/11-04 creates desktop_main.py:
  - test_migrations_fresh_db:   ImportError — desktop_main.py does not exist
  - test_migrations_idempotent: ImportError — desktop_main.py does not exist

Imports are done at function scope so collection succeeds even with the file absent.
"""

from pathlib import Path


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
