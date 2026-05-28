"""
Wave-0 RED tests for DB-03: SQLite WAL mode + concurrent writes.

These tests must FAIL before Plan 11-04 adds the WAL event listener to
backend/app/db/session.py:
  - test_wal_mode_enabled: fails because the real engine has no WAL event
    listener — PRAGMA journal_mode returns "delete" (not "wal").
  - test_concurrent_writes: uses a standalone WAL-enabled engine; verifies
    that WAL allows 3 concurrent writes. This test passes once the WAL
    pragma fires correctly on a fresh engine — it is the design spec for
    Plan 11-04 and may pass in isolation even before session.py is changed
    (since it builds its own engine). The RED state is primarily enforced
    by test_wal_mode_enabled using the real session.py engine.
"""

import concurrent.futures
import sqlite3
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import event


def test_wal_mode_enabled(tmp_path, monkeypatch):
    """DB-03a: WAL mode is active on SQLite connections from the real engine.

    RED state: session.py has no WAL event listener; PRAGMA returns 'delete'.
    After Plan 11-04 adds the listener, PRAGMA returns 'wal'.
    """
    sqlite_url = f"sqlite:///{tmp_path / 'wal_check.db'}"
    monkeypatch.setenv("DATABASE_URL", sqlite_url)

    # Clear lru_cache so settings picks up the SQLite URL.
    from backend.app.config import get_settings
    get_settings.cache_clear()

    # Import the real engine AFTER setting DATABASE_URL.
    # In RED state, session.py has no WAL event listener attached.
    import importlib
    import backend.app.db.session as session_module
    importlib.reload(session_module)

    real_engine = session_module.engine

    with real_engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA journal_mode")
        journal_mode = result.scalar()

    # RED: returns "delete" (default). Passes after Plan 11-04 adds WAL listener.
    assert journal_mode == "wal", (
        f"Expected journal_mode='wal', got {journal_mode!r}. "
        "WAL event listener not yet added to session.py (RED state)."
    )


def test_concurrent_writes(tmp_path):
    """DB-03b: 3 concurrent writes to SQLite (WAL-enabled) complete without lock error.

    This test creates its own WAL-enabled SQLite engine (the design spec for
    what Plan 11-04 will add to session.py). Tests that the WAL pragma +
    busy_timeout pattern allows concurrent inserts without OperationalError.
    """
    db_path = tmp_path / "concurrent_test.db"
    sqlite_url = f"sqlite:///{db_path}"

    # Create a standalone engine with WAL — this mirrors what session.py will do.
    test_engine = sa.create_engine(sqlite_url)

    @event.listens_for(test_engine, "connect")
    def set_wal(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    # Create a simple test table.
    with test_engine.connect() as conn:
        conn.execute(sa.text(
            "CREATE TABLE IF NOT EXISTS writes_test "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, val TEXT)"
        ))
        conn.commit()

    def insert_one(worker_id: int) -> None:
        """Open a new sqlite3 connection (not shared) and insert one row."""
        conn = sqlite3.connect(str(db_path), timeout=10)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("INSERT INTO writes_test (val) VALUES (?)", (f"worker-{worker_id}",))
            conn.commit()
        finally:
            conn.close()

    errors: list[Exception] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(insert_one, i) for i in range(3)]
        for future in concurrent.futures.as_completed(futures, timeout=10):
            exc = future.exception()
            if exc is not None:
                errors.append(exc)

    assert not errors, (
        f"Concurrent writes raised {len(errors)} error(s): {errors!r}. "
        "SQLite WAL + busy_timeout should allow 3 concurrent inserts."
    )

    # Confirm all 3 rows were inserted.
    with test_engine.connect() as conn:
        count = conn.execute(sa.text("SELECT COUNT(*) FROM writes_test")).scalar()
    assert count == 3, f"Expected 3 rows, got {count}"
