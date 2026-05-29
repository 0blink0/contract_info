---
phase: 11-sqlite-migration
plan: "02"
subsystem: backend

tags: [sqlite, alembic, sqlalchemy, orm, migration, dialect-agnostic, tdd]

requires:
  - phase: 11-sqlite-migration/11-01
    provides: Wave-0 RED test baseline (test_db_migration.py) that this plan makes GREEN

provides:
  - Dialect-agnostic ORM model (contract_file.py) — no postgresql imports
  - 4 fixed migration files (001/002/006/007) using sa.JSON, sa.Uuid, CURRENT_TIMESTAMP
  - alembic upgrade head succeeds against sqlite:/// without psycopg2

affects:
  - 11-03-PLAN (path resolution — independent of this plan)
  - 11-04-PLAN (session WAL + desktop_main — independent of this plan)

tech-stack:
  added: []
  patterns:
    - "sa.JSON() replaces postgresql.JSONB(astext_type=sa.Text()) in all migrations and ORM model"
    - "sa.Uuid(as_uuid=True) replaces postgresql.UUID(as_uuid=True) in migration 001 and ORM model"
    - "sa.text('CURRENT_TIMESTAMP') replaces sa.text('now()') for SQLite-compatible server_default"
    - "Typed sa.table/sa.select needed for JSON deserialization on SQLite (raw sa.text() bypasses type system)"

key-files:
  created:
    - backend/tests/test_db_migration.py (copied + fixed from main repo for worktree execution)
  modified:
    - backend/app/models/contract_file.py
    - alembic/versions/001_contract_files.py
    - alembic/versions/002_extraction_columns.py
    - alembic/versions/006_path_b_json.py
    - alembic/versions/007_validation_result.py

key-decisions:
  - "Remove from sqlalchemy.dialects import postgresql entirely from all 4 migration files — not just the type references, to ensure no accidental psycopg2 dependency trigger"
  - "Use sa.Uuid(as_uuid=True) not sa.String for id column — preserves uuid.UUID roundtrip at ORM level while mapping to CHAR(32) on SQLite"
  - "CURRENT_TIMESTAMP for server_default in DDL — SQLite-native; func.now() remains in ORM for client-side default (both are correct in their respective contexts)"
  - "[Rule 1] Fix test_json_roundtrip: use typed sa.table/sa.select instead of raw sa.text() for SELECT — SQLite returns TEXT for JSON columns when using raw SQL, bypassing the JSON type deserializer"

requirements-completed:
  - DB-01

duration: 5min
completed: 2026-05-28
---

# Phase 11 Plan 02: PostgreSQL-to-SQLite Type Replacement Summary

**Replaced all postgresql dialect types (JSONB, UUID) with dialect-agnostic equivalents (sa.JSON, sa.Uuid) in the ORM model and 4 migration files; alembic upgrade head now succeeds against sqlite:/// without psycopg2**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-28T07:39:21Z
- **Completed:** 2026-05-28T07:44:36Z
- **Tasks:** 2
- **Files modified:** 5 (1 ORM model, 4 migration files) + 1 test file added

## Accomplishments

- Replaced `from sqlalchemy.dialects.postgresql import JSONB, UUID` with `from sqlalchemy import DateTime, JSON, String, Text, Uuid, func` in `contract_file.py`
- Replaced `UUID(as_uuid=True)` with `Uuid(as_uuid=True)` for the `id` column in ORM model and migration 001
- Replaced all 6 `JSONB` mapped_column calls with `JSON` in ORM model
- Removed `from sqlalchemy.dialects import postgresql` from migrations 001, 002, 006, 007
- Replaced `postgresql.JSONB(astext_type=sa.Text())` with `sa.JSON()` in all 4 migration files
- Replaced `sa.text("now()")` with `sa.text("CURRENT_TIMESTAMP")` for `created_at` and `updated_at` server_defaults in migration 001
- `alembic upgrade head` completes against `sqlite:///` with all 7 revisions applied
- Both DB-01 tests now pass GREEN: `test_sqlite_migration_all_revisions` and `test_json_roundtrip`

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace postgresql types in ORM model contract_file.py** - `cb82adf` (feat)
2. **Task 2: Replace postgresql types in migrations 001/002/006/007** - `532119f` (feat)

## Files Created/Modified

- `backend/app/models/contract_file.py` — ORM model: JSON, Uuid instead of JSONB, UUID; no postgresql import
- `alembic/versions/001_contract_files.py` — sa.Uuid for id, sa.JSON for parse_json/outline_preview, CURRENT_TIMESTAMP for server defaults
- `alembic/versions/002_extraction_columns.py` — sa.JSON() for extraction_result and extraction_warnings
- `alembic/versions/006_path_b_json.py` — sa.JSON() for path_b_json
- `alembic/versions/007_validation_result.py` — sa.JSON() for validation_result
- `backend/tests/test_db_migration.py` — added to worktree (copied from main repo) with Rule 1 fix for typed SELECT

## Decisions Made

- `sa.Uuid(as_uuid=True)` preserves Python `uuid.UUID` objects at ORM level; SQLite stores as `CHAR(32)` hex string without hyphens — valid for as_uuid=True with SQLAlchemy
- `CURRENT_TIMESTAMP` as server_default is the SQLite-compatible equivalent of `now()` in PostgreSQL; the ORM model's `func.now()` is evaluated client-side by SQLAlchemy so it remains unchanged
- Migrations 003, 004, 005 have no postgresql type references and were not modified

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree path drift — initial edits went to main repo working tree**
- **Found during:** Task 1 (pre-commit check)
- **Issue:** Initial edits to `contract_file.py` were written to `D:/bid_management/contract_info/backend/app/models/contract_file.py` (main repo) instead of the worktree at `D:/bid_management/contract_info/.claude/worktrees/agent-a3fc91823412dac38/`. Detected before any commit.
- **Fix:** Re-applied all changes to the correct worktree path files. The main repo edit was not committed (no harm).
- **Files modified:** All edits redirected to worktree path
- **Commit:** cb82adf (correct worktree commit)

**2. [Rule 1 - Bug] test_json_roundtrip uses raw sa.text() SELECT which bypasses SQLAlchemy JSON deserialization on SQLite**
- **Found during:** Task 2 verification
- **Issue:** The test uses `conn.execute(sa.text("SELECT extraction_result ..."))` which returns the raw TEXT value from SQLite, not a deserialized dict. SQLAlchemy's `sa.JSON` type only auto-deserializes when using the typed query API (not raw SQL).
- **Fix:** Changed the SELECT to use `sa.table(...)` with `sa.column("extraction_result", sa.JSON)` and `sa.select()` so the JSON type processor applies on read.
- **Files modified:** `backend/tests/test_db_migration.py`
- **Commit:** 532119f

## Known Stubs

None — this plan modifies backend migration files and ORM model only; no UI components or data stubs.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. Type replacement is purely at SQLAlchemy/Alembic level; the schema structure (column names, nullability) is unchanged.

## TDD Gate Compliance

This is a Wave-1 GREEN phase for DB-01 tests established in Plan 11-01.

- RED gate: established in Plan 11-01 (`test_db_migration.py` failed with `CompileError: can't render element of type JSONB`)
- GREEN gate: `test_db_migration.py` — 2 passed after this plan's changes
- REFACTOR gate: not needed (changes are surgical type substitutions)

## Self-Check

Files exist:
- backend/app/models/contract_file.py: FOUND
- alembic/versions/001_contract_files.py: FOUND
- alembic/versions/002_extraction_columns.py: FOUND
- alembic/versions/006_path_b_json.py: FOUND
- alembic/versions/007_validation_result.py: FOUND
- backend/tests/test_db_migration.py: FOUND

Commits exist:
- cb82adf: FOUND (Task 1 — ORM model type replacement)
- 532119f: FOUND (Task 2 — migration files type replacement)

## Self-Check: PASSED

---
*Phase: 11-sqlite-migration*
*Completed: 2026-05-28*
