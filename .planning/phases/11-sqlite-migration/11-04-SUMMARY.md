---
plan: 11-04
phase: 11-sqlite-migration
status: complete
wave: 2
completed: 2026-05-28
requirements:
  - DB-03
  - DB-04
self_check: PASSED
---

# Plan 11-04 Summary: WAL Mode + desktop_main.py

## What Was Built

### Task 1 — SQLite WAL Event Listener (DB-03)

Added `@event.listens_for(engine, "connect")` handler to `backend/app/db/session.py`.

On every new SQLite connection the handler executes three PRAGMAs:
- `PRAGMA journal_mode=WAL` — enables Write-Ahead Logging for concurrent read/write
- `PRAGMA busy_timeout=5000` — waits up to 5 seconds before raising `OperationalError: database is locked`
- `PRAGMA synchronous=NORMAL` — balances durability and performance (fsync only at checkpoint)

Guard: the handler only fires when `settings.database_url.startswith("sqlite")` — PostgreSQL connections in Docker mode are not affected.

### Task 2 — desktop_main.py + alembic/env.py (DB-04)

Created `desktop_main.py` at project root with:
- `_get_bundle_base()` — resolves `sys._MEIPASS` (frozen) or `Path(__file__).parent` (dev)
- `run_migrations(db_url, alembic_dir)` — programmatic Alembic Config, no `alembic.ini` required; guards on `alembic_dir.is_dir()`
- `main()` — sets `DATABASE_URL` and `CTRX_DATA_DIR` env vars **before** any backend import; calls `get_settings.cache_clear()`; runs migrations; starts uvicorn on `127.0.0.1:CTRX_PORT` (default 8765)
- `if __name__ == "__main__": main()`

Updated `alembic/env.py` `run_migrations_online()` to support `config.attributes.get("connection", None)` programmatic path — when `desktop_main.py` calls `command.upgrade()`, the connection branch is used directly instead of `engine_from_config`.

## Test Results

| Test | Status | Notes |
|------|--------|-------|
| test_wal_mode_enabled | ✓ PASS | `PRAGMA journal_mode` returns `"wal"` on real engine |
| test_concurrent_writes | ✓ PASS | 3 threads, each with separate connection, all complete without lock error |
| test_migrations_fresh_db | ✓ PASS | `contract_files` table exists after `run_migrations()` on fresh SQLite DB |
| test_migrations_idempotent | ✓ PASS | Second `run_migrations()` call raises no exception |

## Key Files Created/Modified

| File | Change |
|------|--------|
| `backend/app/db/session.py` | Added WAL event listener with SQLite guard |
| `desktop_main.py` | **New file** — PyInstaller entry point with programmatic Alembic + uvicorn |
| `alembic/env.py` | `run_migrations_online()` supports programmatic `config.attributes["connection"]` path |

## Self-Check

- [x] All 4 tests GREEN (`test_db_wal.py` + `test_desktop_main.py`)
- [x] WAL pragma guard does not break PostgreSQL connections
- [x] `desktop_main.py` has no module-level backend imports
- [x] `get_settings.cache_clear()` called before any backend import in `main()`
- [x] `alembic_dir.is_dir()` guard raises `RuntimeError` if path missing
- [x] SUMMARY.md committed before returning
