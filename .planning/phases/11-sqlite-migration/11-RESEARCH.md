# Phase 11: SQLite 迁移与路径修复 - Research

**Researched:** 2026-05-28
**Domain:** SQLAlchemy dialect migration (PostgreSQL → SQLite), PyInstaller path resolution, Alembic programmatic usage
**Confidence:** HIGH

---

## Summary

Phase 11 replaces all PostgreSQL-specific SQLAlchemy types with dialect-agnostic equivalents across 7 Alembic migrations and 1 ORM model, fixes path resolution so data directories come from a `CTRX_DATA_DIR` environment variable instead of `__file__`-relative `PROJECT_ROOT`, enables SQLite WAL mode + busy timeout on the engine, and wires up programmatic `alembic upgrade head` in a new `desktop_main.py`.

The codebase is small and well-scoped: one model (`ContractFile`), one session module, one config module, seven migrations, and roughly 8 service/route files that all import `PROJECT_ROOT`, `uploads_dir`, `exports_dir`, or `templates_dir`. The migration is surgical — no new architecture, no new data model, just type swaps and path resolution changes.

The biggest risk is the `storage_path` column: it currently stores `uploads/<uuid>/filename.docx` relative to `PROJECT_ROOT`. After the migration it must still resolve against `CTRX_DATA_DIR`, not `PROJECT_ROOT`. Every service that currently does `PROJECT_ROOT / record.storage_path` must switch to `data_dir() / record.storage_path`. That propagation touches 6 files.

**Primary recommendation:** Replace `postgresql.JSONB` → `sa.JSON`, `postgresql.UUID(as_uuid=True)` → `sa.Uuid(as_uuid=True)` in all 7 migrations and the ORM model; add a `data_dir()` helper to `config.py` driven by `CTRX_DATA_DIR`; update the 6 path-consuming files to call `data_dir()`; add WAL + busy_timeout event listener in `session.py`; implement `desktop_main.py` with programmatic Alembic.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DB-01 | Replace `postgresql.JSONB` → `JSON`, `postgresql.UUID` → `Uuid` in all 7 migrations and ORM model; JSON columns serialize/deserialize correctly | Dialect-agnostic types section; JSON serialization section |
| DB-02 | Data directories resolve from `CTRX_DATA_DIR` env var; works in PyInstaller `_MEIPASS` and dev mode | Path resolution section; config.py changes |
| DB-03 | SQLite session with WAL mode; Uvicorn thread pool concurrent reads/writes without lock timeouts | WAL mode section; session.py changes |
| DB-04 | `desktop_main.py` runs `alembic upgrade head` programmatically before uvicorn starts; idempotent | Programmatic Alembic section |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dialect type replacement (JSONB→JSON, UUID→Uuid) | Backend (ORM + migrations) | — | SQLAlchemy model and migration files own type definitions |
| Data directory resolution | Backend (config.py) | All services that consume it | Single source of truth; propagated via function |
| SQLite engine setup (WAL, pool) | Backend (db/session.py) | — | Engine is created once here |
| Programmatic Alembic upgrade | Backend (desktop_main.py) | alembic/env.py | Caller sets URL + script_location; env.py uses it |
| PyInstaller path branching | Backend (desktop_main.py + config.py) | — | `sys.frozen` check governs base path selection |

---

## Standard Stack

### Core (already in requirements.txt)

| Library | Version in repo | Purpose | Notes |
|---------|----------------|---------|-------|
| sqlalchemy | >=2.0 | ORM + type system | `sa.Uuid` and `sa.JSON` are in `sqlalchemy.types` since 2.0 [VERIFIED: SQLAlchemy GitHub issue #7212] |
| alembic | >=1.13 | Migrations | `command.upgrade`, `Config()` programmatic API [VERIFIED: alembic.sqlalchemy.org] |
| pydantic-settings | >=2.0 | Settings with env var loading | `CTRX_DATA_DIR` added as field [ASSUMED] |
| uvicorn[standard] | >=0.27 | ASGI server | Called from `desktop_main.py` programmatically [ASSUMED] |

### No New Packages Required

This phase makes zero new package installations. All needed types (`sa.JSON`, `sa.Uuid`) are in SQLAlchemy 2.0 which is already pinned. `psycopg2-binary` stays in `requirements.txt` for Docker/dev path — it is only removed from the PyInstaller spec in Phase 12.

**Rationale:** Requirements say to clear PostgreSQL **dialect dependencies** from the application code. The `psycopg2` package being present in `requirements.txt` is not a problem as long as the running `DATABASE_URL` is a `sqlite://` URL at runtime. Removal from the packaged binary is a Phase 12 concern.

---

## Package Legitimacy Audit

No new packages are installed in this phase. Existing packages (`sqlalchemy`, `alembic`) are established OSS with multi-year track records.

| Package | Disposition |
|---------|-------------|
| sqlalchemy | Already installed — not reviewed here |
| alembic | Already installed — not reviewed here |

---

## Architecture Patterns

### System Architecture Diagram

```
desktop_main.py startup sequence
        │
        ├─ resolve CTRX_DATA_DIR ──► set data_dir()
        ├─ set DATABASE_URL (sqlite:///CTRX_DATA_DIR/ctrx.db)
        ├─ clear get_settings() lru_cache
        ├─ run alembic upgrade head ──► alembic/env.py ──► 7 migrations
        │                                                   (dialect-agnostic types)
        └─ uvicorn.run(app) ──► FastAPI handlers
                                    │
                                    ├─ upload → data_dir()/uploads/<uuid>/
                                    ├─ parse  → data_dir()/uploads/<uuid>/file.docx
                                    ├─ export → data_dir()/exports/<uuid>/
                                    └─ download ← data_dir()/exports/<uuid>/file.xlsx

SQLAlchemy engine (session.py)
        │
        └─ create_engine(sqlite:///...)
               └─ event.listens_for("connect")
                       ├─ PRAGMA journal_mode=WAL
                       └─ PRAGMA busy_timeout=5000
```

### Recommended Project Structure (changes only)

```
contract_info/
├── backend/
│   └── app/
│       ├── config.py          # add data_dir(), uploads_dir(), update templates_dir()
│       ├── db/
│       │   └── session.py     # add WAL + busy_timeout event listener
│       └── models/
│           └── contract_file.py  # postgresql.JSONB → sa.JSON, postgresql.UUID → sa.Uuid
├── alembic/
│   ├── env.py                 # add config.attributes.get('connection') branch
│   └── versions/
│       ├── 001_contract_files.py   # postgresql.UUID → sa.Uuid, postgresql.JSONB → sa.JSON
│       ├── 002_extraction_columns.py  # postgresql.JSONB → sa.JSON
│       ├── 006_path_b_json.py      # postgresql.JSONB → sa.JSON
│       └── 007_validation_result.py   # postgresql.JSONB → sa.JSON
└── desktop_main.py            # new file: path init + alembic + uvicorn
```

### Anti-Patterns to Avoid

- **Keeping `from sqlalchemy.dialects import postgresql` in any migration:** Once replaced, remove the import entirely — leaving it causes an import error if psycopg2 is absent.
- **Using `PROJECT_ROOT / "uploads"` in any path after this phase:** All upload/export paths must go through `data_dir()`.
- **Storing `storage_path` as relative to `PROJECT_ROOT`:** The stored value `uploads/<uuid>/file.docx` remains relative — but it is now resolved against `data_dir()`, not `PROJECT_ROOT`.
- **Calling `alembic upgrade head` with a CLI subprocess in `desktop_main.py`:** Use the Python API (`alembic.command.upgrade`), not `subprocess.run(["alembic", "upgrade", "head"])`. The latter may not find `alembic` in a frozen environment.
- **Setting `check_same_thread=True`:** SQLAlchemy already sets it to False for file-based SQLite. Do not override it to True.

---

## DB-01: Dialect-Agnostic Type Replacement

### What Changes

**Migrations with PostgreSQL types (complete list from codebase inspection):**

| File | Type to replace |
|------|----------------|
| `001_contract_files.py` | `postgresql.UUID(as_uuid=True)` on `id` column, `postgresql.JSONB` on `parse_json`, `outline_preview` |
| `002_extraction_columns.py` | `postgresql.JSONB` on `extraction_result`, `extraction_warnings` |
| `003_export_paths.py` | No PostgreSQL types (uses `sa.Text`) — no change needed |
| `004_subtable_export_paths.py` | No PostgreSQL types — no change needed |
| `005_subscription_xlsx_path.py` | No PostgreSQL types — no change needed |
| `006_path_b_json.py` | `postgresql.JSONB` on `path_b_json` |
| `007_validation_result.py` | `postgresql.JSONB` on `validation_result` |

**ORM model (`contract_file.py`):**
- `from sqlalchemy.dialects.postgresql import JSONB, UUID` → remove
- `UUID(as_uuid=True)` → `sa.Uuid(as_uuid=True)` (from `sqlalchemy`)
- All 7 `JSONB` columns → `sa.JSON`

### Replacement Types

**`sqlalchemy.types.Uuid` (dialect-agnostic UUID):** [VERIFIED: SQLAlchemy GitHub issue #7212, discussion #9290]
- Added in SQLAlchemy 2.0
- On PostgreSQL: uses native `UUID` type
- On SQLite: uses `CHAR(32)`, stores UUID as 32-char hex string (no hyphens)
- `as_uuid=True` parameter: Python side uses `uuid.UUID` objects (same as before)
- Import: `from sqlalchemy import Uuid` or `sa.Uuid`

```python
# Before
from sqlalchemy.dialects.postgresql import UUID
id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

# After
from sqlalchemy import Uuid
id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

**`sqlalchemy.types.JSON` (dialect-agnostic JSON):** [VERIFIED: SQLAlchemy docs, blog.stigok.com confirmed behavior]
- On PostgreSQL: maps to native `JSONB` (with psycopg2) — NOTE: plain JSON, not JSONB. If JSONB-specific operators (GIN indexes, `@>` containment) are needed, this would matter; this codebase does not use them.
- On SQLite: stores as TEXT containing JSON; SQLAlchemy auto-serializes Python dict→JSON string on write, auto-deserializes JSON string→Python dict on read [VERIFIED: confirmed via blog.stigok.com test]
- Returns `dict` on read, not `str` — no extra processing needed
- Import: `from sqlalchemy import JSON` or `sa.JSON`

```python
# Before
from sqlalchemy.dialects.postgresql import JSONB
extraction_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

# After
from sqlalchemy import JSON
extraction_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

**Migration column definition pattern:**
```python
# Before (in upgrade())
sa.Column("extraction_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True)

# After
sa.Column("extraction_result", sa.JSON(), nullable=True)
```

### JSONB vs JSON Functional Impact

The codebase stores dicts/lists and reads them back. It never uses:
- JSONB containment operators (`@>`, `<@`)
- GIN indexes on JSONB columns
- PostgreSQL-specific JSONB aggregation functions

Switching from JSONB to JSON causes no functional regression. [ASSUMED — based on codebase inspection showing no JSONB operators used in queries]

---

## DB-02: Path Resolution via CTRX_DATA_DIR

### Current Problem

`config.py` line 6:
```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
```

In a PyInstaller `--onedir` bundle, `__file__` for `config.py` will be something like `C:\Users\user\AppData\Local\Programs\CTRX\_internal\backend\app\config.py`. The user's data (uploads, exports) must NOT go there — it must go to a user-controlled, writable directory. [VERIFIED: PyInstaller runtime docs — `__file__` resolves inside `_MEIPASS` / `_internal` in bundled apps]

### Solution: `CTRX_DATA_DIR` Environment Variable

`desktop_main.py` sets `CTRX_DATA_DIR` before importing the app. Config reads it:

```python
# config.py additions

import os
import sys

def _bundle_base() -> Path:
    """Resolve the base directory for bundled read-only assets (templates, dicts, alembic)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]

def data_dir() -> Path:
    """Resolve user-writable data directory (uploads, exports, DB file).
    
    In desktop mode: set by desktop_main.py via CTRX_DATA_DIR env var.
    In dev mode: defaults to PROJECT_ROOT (existing behaviour).
    """
    raw = os.environ.get("CTRX_DATA_DIR", "").strip()
    if raw:
        p = Path(raw)
        p.mkdir(parents=True, exist_ok=True)
        return p
    return PROJECT_ROOT  # dev/Docker fallback

def uploads_dir() -> Path:
    return data_dir() / "uploads"

def exports_dir() -> Path:
    return data_dir() / "exports"

def templates_dir() -> Path:
    return _bundle_base() / "templates"   # read-only — from bundle

DICTS_DIR_PATH = _bundle_base() / "dicts"  # for extract/validate.py
```

### Files That Need `data_dir()` Updates

Every file currently using `PROJECT_ROOT / "uploads"` or `PROJECT_ROOT / "exports"` must be updated:

| File | Current pattern | New pattern |
|------|----------------|-------------|
| `services/upload_service.py` | `PROJECT_ROOT / "uploads" / str(file_id)` | `uploads_dir() / str(file_id)` |
| `services/upload_service.py` | `str(dest_file.relative_to(PROJECT_ROOT))` | `str(dest_file.relative_to(data_dir()))` |
| `services/parse_service.py` | `PROJECT_ROOT / record.storage_path` | `data_dir() / record.storage_path` |
| `services/delete_service.py` | `PROJECT_ROOT / "uploads" / str(file_id)` | `uploads_dir() / str(file_id)` |
| `services/delete_service.py` | `PROJECT_ROOT / "exports" / str(file_id)` | `exports_dir() / str(file_id)` |
| `services/preview_service.py` | `PROJECT_ROOT / record.product_xlsx_path` (×5) | `data_dir() / record.*_path` |
| `api/routes/jobs.py` | `PROJECT_ROOT / rel_path` | `data_dir() / rel_path` |
| `extract/validate.py` | `PROJECT_ROOT / "dicts"` | `_bundle_base() / "dicts"` or new `dicts_dir()` |

**Critical invariant:** `storage_path` stored in the DB continues to be a relative path like `uploads/<uuid>/file.docx`. The resolution base changes from `PROJECT_ROOT` to `data_dir()`. No data migration needed for existing dev data; behaviour is identical when `CTRX_DATA_DIR` is unset.

### PyInstaller `sys._MEIPASS` vs Dev Mode

```python
# Pattern for resolving bundled read-only assets (templates, dicts, alembic/)
import sys
from pathlib import Path

def _bundle_base() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)          # --onedir: points to _internal/
    return Path(__file__).resolve().parents[2]   # dev: project root
```

[VERIFIED: PyInstaller runtime docs — pyinstaller.org/en/stable/runtime-information.html]

For `--onedir` (the chosen mode per STATE.md decision):
- `sys._MEIPASS` → `<install_dir>/_internal/`
- Bundled files (alembic/, dicts/, templates/) are in `_internal/`
- User data (DB, uploads, exports) must be in `CTRX_DATA_DIR` (set by Electron main process)

---

## DB-03: SQLite WAL Mode + Busy Timeout

### Engine Configuration

```python
# backend/app/db/session.py

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from backend.app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    # connect_args not needed for file-based SQLite —
    # SQLAlchemy sets check_same_thread=False automatically
)

@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Enable WAL mode and busy timeout on every new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")   # 5 seconds in milliseconds
    cursor.execute("PRAGMA synchronous=NORMAL")  # safe with WAL, faster than FULL
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
```

[CITED: docs.sqlalchemy.org/en/20/dialects/sqlite.html — event listener pattern for PRAGMA foreign_keys, adapted for WAL]
[CITED: sqlite.org/wal.html — WAL mode semantics]

### Why WAL Solves the Concurrency Problem

Uvicorn with `--workers 1` (single process) uses a thread pool for sync route handlers. Without WAL, SQLite uses rollback journal mode where **any write blocks all reads**. With WAL:
- Unlimited concurrent readers, one writer at a time
- Readers and the one active writer can coexist
- `busy_timeout=5000` makes concurrent writers retry for up to 5 seconds instead of immediately raising `OperationalError: database is locked`

[VERIFIED: sqlite.org/wal.html — "WAL allows readers and a writer to coexist"]

### WAL Pragma Persistence

`PRAGMA journal_mode=WAL` is **persistent across connections** once set on a database file. However, `PRAGMA busy_timeout` is **per-connection** and resets to 0. Setting both in the `connect` event listener ensures every new connection gets the timeout. [VERIFIED: github.com/openclaw/openclaw/issues/39176 — busy_timeout is per-connection]

### `check_same_thread` 

For file-based SQLite, SQLAlchemy 2.0 automatically passes `check_same_thread=False` to the Python sqlite3 driver. No explicit `connect_args` needed. [CITED: docs.sqlalchemy.org/en/20/dialects/sqlite.html]

### Database URL Pattern

The SQLite URL must be set in `desktop_main.py` before any import of `session.py`:

```python
# In desktop_main.py, before importing the app:
os.environ["DATABASE_URL"] = f"sqlite:///{data_path}/ctrx.db"
os.environ["CTRX_DATA_DIR"] = str(data_path)
get_settings.cache_clear()   # flush the lru_cache
```

SQLAlchemy URL format: `sqlite:///absolute/path/to/ctrx.db` (triple slash + absolute path) [VERIFIED: SQLAlchemy docs]

---

## DB-04: Programmatic Alembic in desktop_main.py

### Complete Pattern

```python
# desktop_main.py (skeleton)

import os
import sys
from pathlib import Path

def _get_bundle_base() -> Path:
    """Read-only assets: alembic/, dicts/, templates/."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

def run_migrations(db_url: str, alembic_dir: Path) -> None:
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    # Suppress fileConfig() call: env.py will skip logging config
    # when config.config_file_name is None
    command.upgrade(alembic_cfg, "head")

def main() -> None:
    bundle_base = _get_bundle_base()

    # 1. Determine data directory
    data_path = Path(os.environ.get("CTRX_DATA_DIR") or Path.home() / ".ctrx")
    data_path.mkdir(parents=True, exist_ok=True)

    # 2. Set environment variables before any app import
    db_url = f"sqlite:///{data_path / 'ctrx.db'}"
    os.environ["DATABASE_URL"] = db_url
    os.environ["CTRX_DATA_DIR"] = str(data_path)
    os.environ.setdefault("CTRX_PORT", "8765")

    # 3. Clear lru_cache so get_settings() re-reads the new env vars
    from backend.app.config import get_settings
    get_settings.cache_clear()

    # 4. Run Alembic migrations (idempotent — skips already-applied revisions)
    alembic_dir = bundle_base / "alembic"
    run_migrations(db_url, alembic_dir)

    # 5. Start Uvicorn
    import uvicorn
    port = int(os.environ.get("CTRX_PORT", "8765"))
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port)

if __name__ == "__main__":
    main()
```

[VERIFIED: alembic.sqlalchemy.org/en/latest/api/commands.html — `command.upgrade(cfg, "head")`]
[VERIFIED: alembic.sqlalchemy.org/en/latest/cookbook.html — programmatic Config without file]

### env.py Modification

`alembic/env.py` currently reads the URL from `get_settings()`. When called from `desktop_main.py`, `sqlalchemy.url` is already set in the `Config` object. The env.py must not override it. Modify `run_migrations_online()` to check `config.attributes.get('connection')` as a first option, then fall back to the URL approach — this is the standard Alembic cookbook pattern:

```python
# alembic/env.py — run_migrations_online() modification

def run_migrations_online() -> None:
    connectable = config.attributes.get("connection", None)
    
    if connectable is None:
        # Standard path: build engine from config URL
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    else:
        # Programmatic path: use provided connection
        context.configure(connection=connectable, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

The `fileConfig()` call at the top of `env.py` is guarded by `if config.config_file_name is not None:` — this is already in the codebase and correctly skips logging config when no `.ini` file is provided. [VERIFIED: alembic/env.py line 11 in codebase]

### Idempotency

`alembic upgrade head` is **idempotent**: Alembic tracks applied revisions in the `alembic_version` table. Re-running when already at head does nothing. First run creates all tables. [VERIFIED: alembic docs, sqlalchemy-alembic.narkive.com]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dialect-agnostic JSON | Custom TypeDecorator with json.loads/json.dumps | `sa.JSON` | Built into SQLAlchemy; handles both PG and SQLite correctly |
| Dialect-agnostic UUID | Custom GUID type (CHAR(32) branching) | `sa.Uuid(as_uuid=True)` | Added to SQLAlchemy 2.0; native UUID on PG, CHAR(32) on SQLite |
| WAL mode | Manual PRAGMA in app code at various points | `event.listens_for(engine, "connect")` | Runs on every new connection; correct for pool reuse |
| Migration on startup | `subprocess.run(["alembic", ...])` | `alembic.command.upgrade(cfg, "head")` | No subprocess needed; works in frozen bundle |
| DB lock retries | Custom retry loop around session | `PRAGMA busy_timeout=5000` | SQLite's built-in retry mechanism |

---

## Common Pitfalls

### Pitfall 1: Leftover `postgresql` Import After Type Replacement

**What goes wrong:** After replacing `postgresql.JSONB` with `sa.JSON` in a migration, forgetting to remove `from sqlalchemy.dialects import postgresql` causes `ImportError: No module named 'psycopg2'` when running under SQLite if psycopg2 is absent.

**Why it happens:** The import of `sqlalchemy.dialects.postgresql` triggers psycopg2 import under some SQLAlchemy versions.

**How to avoid:** After type replacement, grep for `from sqlalchemy.dialects import postgresql` and `from sqlalchemy.dialects.postgresql import` and remove all occurrences from migrations that no longer use PostgreSQL types.

**Warning signs:** `ImportError` or `ModuleNotFoundError: psycopg2` when running `alembic upgrade head` with a `sqlite://` URL.

### Pitfall 2: storage_path Resolution After data_dir() Change

**What goes wrong:** `storage_path` stored as `uploads/<uuid>/file.docx` is resolved with the OLD `PROJECT_ROOT`. Parse fails with `FileNotFoundError` because the file is in `$CTRX_DATA_DIR/uploads/...` not `$PROJECT_ROOT/uploads/...`.

**Why it happens:** `parse_service.py` does `PROJECT_ROOT / record.storage_path`. After the change, `data_dir()` must be the base.

**How to avoid:** Update all 6 files listed in the "Files That Need data_dir() Updates" table. Grep for `PROJECT_ROOT / record.storage_path` and `PROJECT_ROOT / "uploads"` as a checklist.

**Warning signs:** `FileNotFoundError` on parse step when `CTRX_DATA_DIR` is set to a non-default path.

### Pitfall 3: lru_cache Not Cleared Before App Import

**What goes wrong:** `desktop_main.py` sets `DATABASE_URL` env var, then imports the app. But if any module already imported `get_settings()` (e.g., at import time of a dependency), the cached `Settings()` still has the old PostgreSQL URL.

**Why it happens:** `@lru_cache` on `get_settings()` — first call wins.

**How to avoid:** Call `get_settings.cache_clear()` **after** setting env vars, **before** importing any backend module that calls `get_settings()`. In `desktop_main.py`, set env vars first (lines 1-N), then clear cache, then import uvicorn/app.

**Warning signs:** App attempts to connect to `postgresql+psycopg2://...` despite env var being set.

### Pitfall 4: WAL Pragma Not Applied to Alembic Connections

**What goes wrong:** Alembic's migration engine is created with `NullPool` in `env.py`, bypassing the event listener attached to the app engine. Migrations run without WAL, causing potential lock issues if another process has the DB open.

**Why it happens:** `engine_from_config` in `env.py` creates a fresh engine — it does not inherit the app engine's event listeners.

**How to avoid:** In `desktop_main.py`, run Alembic migrations **before** starting Uvicorn. During startup, there are no concurrent connections. The lock risk is minimal. For defense in depth, add the event listener to the Alembic engine too (or use the `attributes['connection']` pattern to reuse the app engine's connection).

**Warning signs:** `OperationalError: database is locked` during migration in testing with concurrent DB access.

### Pitfall 5: `sa.JSON` Returns `None` Not `{}` for Unset Columns

**What goes wrong:** Code that does `record.extraction_result.get(...)` raises `AttributeError: 'NoneType' object has no attribute 'get'` for rows where the column is NULL.

**Why it happens:** `nullable=True` JSON columns return Python `None` when the DB value is NULL (not an empty dict). This is identical to JSONB behaviour — no regression, but worth noting.

**How to avoid:** Existing patterns like `getattr(record, "extraction_result", None) or {}` already handle this correctly and should be preserved.

### Pitfall 6: alembic/ Directory Not Found in Bundle

**What goes wrong:** `desktop_main.py` sets `script_location` to `bundle_base / "alembic"` but the PyInstaller spec did not include the alembic directory, so the path does not exist at runtime.

**Why it happens:** Phase 11 lays the groundwork; Phase 12 adds the spec. But the `run_migrations()` call in `desktop_main.py` must use a path that will exist in the bundle.

**How to avoid:** In `desktop_main.py`, add a guard:
```python
if not alembic_dir.is_dir():
    raise RuntimeError(f"Alembic directory not found: {alembic_dir}")
```
This surfaces the error immediately with a clear message rather than a cryptic Alembic error.

---

## Runtime State Inventory

This is not a rename/refactor phase, but the DB transition has a runtime state aspect.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | SQLite DB does not yet exist (PostgreSQL was the backend) — first run creates it via migrations | None — Alembic creates fresh SQLite DB |
| Live service config | Docker Compose uses PostgreSQL container — not affected by this phase (Docker path preserved unchanged per STATE.md decision) | None |
| OS-registered state | None | None — verified by codebase inspection |
| Secrets/env vars | `DATABASE_URL` in `.env` currently points to PostgreSQL; dev workflow needs a `sqlite:///` URL for local SQLite testing | Add `DATABASE_URL=sqlite:///./ctrx_dev.db` to `.env.sqlite` or override in shell |
| Build artifacts | `psycopg2-binary` remains in requirements.txt and is available in dev — not a problem until Phase 12 | None in this phase |

---

## Validation Architecture

`nyquist_validation: true` in `.planning/config.json` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pytest.ini` (project root) |
| Quick run command | `pytest backend/tests/ -x -q --ignore=backend/tests/golden` |
| Full suite command | `pytest backend/tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01a | `alembic upgrade head` succeeds against SQLite URL (all 7 migrations) | integration | `pytest backend/tests/test_db_migration.py -x` | No — Wave 0 |
| DB-01b | `extraction_result` column stores dict, reads back as dict (not str) | unit | `pytest backend/tests/test_db_migration.py::test_json_roundtrip -x` | No — Wave 0 |
| DB-01c | No `postgresql` import in any migration or model | static check | `grep -r "from sqlalchemy.dialects.postgresql" alembic/ backend/app/models/` | N/A (grep) |
| DB-02a | `CTRX_DATA_DIR=/tmp/test` → uploads written to `/tmp/test/uploads/` | unit | `pytest backend/tests/test_path_resolution.py::test_uploads_dir_uses_env -x` | No — Wave 0 |
| DB-02b | Unset `CTRX_DATA_DIR` → falls back to `PROJECT_ROOT` (dev behaviour unchanged) | unit | `pytest backend/tests/test_path_resolution.py::test_uploads_dir_fallback -x` | No — Wave 0 |
| DB-02c | `_bundle_base()` returns `sys._MEIPASS` when `sys.frozen=True` | unit | `pytest backend/tests/test_path_resolution.py::test_bundle_base_frozen -x` | No — Wave 0 |
| DB-03a | WAL mode is active on SQLite connections | integration | `pytest backend/tests/test_db_wal.py::test_wal_mode_enabled -x` | No — Wave 0 |
| DB-03b | 3 concurrent uploads complete without lock timeout | integration | `pytest backend/tests/test_db_wal.py::test_concurrent_writes -x` | No — Wave 0 |
| DB-04a | `desktop_main.run_migrations()` creates schema on fresh DB | integration | `pytest backend/tests/test_desktop_main.py::test_migrations_fresh_db -x` | No — Wave 0 |
| DB-04b | `desktop_main.run_migrations()` is idempotent on already-migrated DB | integration | `pytest backend/tests/test_desktop_main.py::test_migrations_idempotent -x` | No — Wave 0 |

### Observable Behaviors (non-automated verification)

These are the Phase 11 Success Criteria from ROADMAP.md expressed as observable checks:

1. `DATABASE_URL=sqlite:///./test.db alembic upgrade head` completes with "Running upgrade" for each of the 7 revisions, no errors
2. `CTRX_DATA_DIR=/tmp/ctrx_test pytest backend/tests/test_api_upload.py -x` — upload writes to `/tmp/ctrx_test/uploads/`
3. `pytest backend/tests/test_db_wal.py::test_concurrent_writes` — 3 concurrent uploads complete without `OperationalError`
4. Start app with SQLite URL, upload a contract, run extraction: `extraction_result` in DB is a dict when read back, not a JSON string

### Sampling Rate

- **Per task commit:** `pytest backend/tests/test_db_migration.py backend/tests/test_path_resolution.py backend/tests/test_desktop_main.py -x -q`
- **Per wave merge:** `pytest backend/tests/ -q --ignore=backend/tests/golden`
- **Phase gate:** Full suite green (excluding `@pytest.mark.llm` tests) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_db_migration.py` — covers DB-01a, DB-01b: SQLite migration roundtrip
- [ ] `backend/tests/test_path_resolution.py` — covers DB-02a, DB-02b, DB-02c: `data_dir()` with/without env var, `_bundle_base()` frozen mock
- [ ] `backend/tests/test_db_wal.py` — covers DB-03a, DB-03b: WAL mode enabled, concurrent write test
- [ ] `backend/tests/test_desktop_main.py` — covers DB-04a, DB-04b: programmatic Alembic fresh + idempotent

---

## Code Examples

### Example 1: Full ORM Model After Type Replacement

```python
# backend/app/models/contract_file.py — after Phase 11
import uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ContractFile(Base):
    __tablename__ = "contract_files"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    outline_preview: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extraction_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    product_xlsx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    fee_xlsx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    lock_xlsx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    share_xlsx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    subscription_xlsx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    path_b_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

### Example 2: Migration 001 After Type Replacement

```python
# alembic/versions/001_contract_files.py — after Phase 11
import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision = None

def upgrade() -> None:
    op.create_table(
        "contract_files",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("parse_json", sa.JSON(), nullable=True),
        sa.Column("outline_preview", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_contract_files_status", "contract_files", ["status"])
    op.create_index("ix_contract_files_created_at", "contract_files", ["created_at"])
```

**Note on `server_default=sa.text("now()")`:** SQLite does not have a `now()` function; it uses `CURRENT_TIMESTAMP`. However, for migrations that already ran on PostgreSQL (dev/Docker), this only matters for SQLite first-time setup. The fix is to use `sa.text("CURRENT_TIMESTAMP")` instead of `sa.text("now()")` in migrations that create columns with server defaults, **or** to use SQLAlchemy's `func.now()` as the ORM default (client-side) and remove `server_default` from the migration. The ORM model already uses `server_default=func.now()` which the ORM handles at Python level. The migration `server_default` is only used by Alembic DDL generation. [ASSUMED — SQLite behavior with `now()` in DDL; should be verified with a test]

### Example 3: WAL-Enabled Session

```python
# backend/app/db/session.py — after Phase 11
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)

@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Apply WAL mode and busy timeout for SQLite connections.
    For non-SQLite databases (PostgreSQL in Docker mode) these pragmas are no-ops
    only if the connection is not SQLite — guard with a dialect check.
    """
    # Only apply to SQLite connections
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

@contextmanager
def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**Important:** The event listener must guard on `database_url.startswith("sqlite")` so it does not attempt to execute SQLite PRAGMAs against a PostgreSQL connection in Docker mode. [ASSUMED — PRAGMA execution against non-SQLite DBAPI; should verify whether it raises or silently passes]

### Example 4: data_dir() Test Pattern

```python
# backend/tests/test_path_resolution.py

import os
from pathlib import Path
import pytest

def test_uploads_dir_uses_env(tmp_path, monkeypatch):
    monkeypatch.setenv("CTRX_DATA_DIR", str(tmp_path))
    # Import after env is set — or force config reload
    from backend.app.config import get_settings, uploads_dir
    get_settings.cache_clear()
    result = uploads_dir()
    assert result == tmp_path / "uploads"

def test_uploads_dir_fallback(monkeypatch):
    monkeypatch.delenv("CTRX_DATA_DIR", raising=False)
    from backend.app.config import PROJECT_ROOT, uploads_dir, get_settings
    get_settings.cache_clear()
    assert uploads_dir() == PROJECT_ROOT / "uploads"

def test_bundle_base_frozen(monkeypatch, tmp_path):
    import sys
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    # Force reimport of config to pick up mocked sys attributes
    import importlib
    import backend.app.config as cfg
    importlib.reload(cfg)
    assert cfg._bundle_base() == tmp_path
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `postgresql.UUID` for UUID columns | `sa.Uuid(as_uuid=True)` (dialect-agnostic) | SQLAlchemy 2.0 (2023) | Works on SQLite, PostgreSQL, MariaDB without custom types |
| `postgresql.JSONB` | `sa.JSON` | SQLAlchemy 1.1+ (JSON), project migrates in Phase 11 | No JSONB GIN-index advantage but no PostgreSQL dependency |
| Custom GUID TypeDecorator | `sa.Uuid` | SQLAlchemy 2.0 | Removes boilerplate |
| `subprocess.run(["alembic", ...])` in startup scripts | `alembic.command.upgrade(Config(), "head")` | Established Alembic pattern | Works in frozen bundles, no PATH dependency |
| `__file__`-relative `PROJECT_ROOT` | `CTRX_DATA_DIR` env var + `sys._MEIPASS` for bundle assets | Phase 11 | Required for PyInstaller where `__file__` is inside read-only bundle |

**Deprecated:**
- `from sqlalchemy.dialects.postgresql import JSONB, UUID`: Works only with psycopg2; breaks in SQLite environments. Replace entirely.
- `PROJECT_ROOT = Path(__file__).resolve().parents[2]` as data root: Correct in dev/Docker but wrong in PyInstaller where `__file__` is inside `_internal/`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Codebase does not use JSONB GIN indexes, containment operators (`@>`, `<@`), or any JSONB-specific query syntax | DB-01 | If JSONB operators exist in unreached code, they will fail at runtime with SQLite; fix: audit all SQLAlchemy query statements |
| A2 | `PRAGMA journal_mode=WAL` against a non-SQLite dbapi connection is a no-op or raises; guarding on `database_url.startswith("sqlite")` is correct | DB-03 | If guard is missing and PostgreSQL connection receives PRAGMA, psycopg2 may raise ProgrammingError; mitigation: use `isinstance(dbapi_connection, sqlite3.Connection)` check instead |
| A3 | `sa.text("now()")` in migration `server_default` will fail on SQLite (no `now()` function); `CURRENT_TIMESTAMP` is the correct SQLite equivalent | DB-01, Example 2 | If left as `now()`, `alembic upgrade head` against SQLite raises `OperationalError: no such function: now`; fix: replace with `CURRENT_TIMESTAMP` in DDL server defaults |
| A4 | `uvicorn.run()` accepts string app path `"backend.app.main:app"` from `desktop_main.py` | DB-04 | If `uvicorn.run()` does not find the module, the app will not start; mitigation: import app directly and pass the object: `uvicorn.run(app, ...)` |
| A5 | Setting `CTRX_DATA_DIR` as env var before importing backend modules is sufficient to override `data_dir()` (no module-level evaluation of `data_dir()` at import time) | DB-02 | If any module evaluates `data_dir()` or `exports_dir()` at import time (not inside a function), the env var override will not take effect; mitigation: ensure all path functions in config.py are regular functions, not module-level constants |

---

## Open Questions

1. **`server_default=sa.text("now()")` in migration 001 and 007**
   - What we know: SQLite does not have a `now()` function; migrations 001 creates `created_at`/`updated_at` with `server_default=sa.text("now()")`
   - What's unclear: Does Alembic's SQLite DDL emit this directly? If so, `CREATE TABLE` will fail
   - Recommendation: Replace with `sa.text("CURRENT_TIMESTAMP")` in the migration server_default, or remove server_default entirely (the ORM model uses `func.now()` which is client-evaluated)

2. **Docker/PostgreSQL path after Phase 11**
   - What we know: STATE.md says "Docker path preserved unchanged"
   - What's unclear: After replacing `postgresql.JSONB` with `sa.JSON`, do existing PostgreSQL migrations still apply cleanly? (sa.JSON renders as `JSON` not `JSONB` in PostgreSQL DDL)
   - Recommendation: Verify with `DATABASE_URL=postgresql://... alembic upgrade head` after the change; JSON vs JSONB is a storage difference (JSONB has binary storage, GIN indexes) but functionally equivalent for this app's usage

3. **Concurrent write test design**
   - What we know: DB-03 requires no lock timeouts under concurrent uploads
   - What's unclear: How to simulate concurrent Uvicorn thread pool writes in a pytest test without a running server
   - Recommendation: Use `concurrent.futures.ThreadPoolExecutor` to call `persist_upload()` from 3 threads simultaneously against a SQLite test DB

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | Confirmed (project runs) | Unknown in this env | — |
| SQLAlchemy >=2.0 | DB-01, DB-03 | In requirements.txt | >=2.0 | — |
| Alembic >=1.13 | DB-01, DB-04 | In requirements.txt | >=1.13 | — |
| SQLite (sqlite3) | DB-01 through DB-04 | Built into Python stdlib | 3.x | — |
| psycopg2-binary | Docker mode (unchanged) | In requirements.txt | >=2.9 | Not needed for SQLite path |

---

## Security Domain

This phase has no new authentication, session management, or external input surface changes. The only security-adjacent consideration:

| ASVS Category | Applies | Control |
|---------------|---------|---------|
| V5 Input Validation | Partial — path traversal | `_resolve_export_path()` in `jobs.py` already validates that resolved paths are within `exports_dir()`. After the change, `exports_dir()` returns `data_dir() / "exports"`, so the traversal check remains correct as long as `data_dir()` is set to a user-controlled root, not an attacker-controlled value. `CTRX_DATA_DIR` is set by the Electron main process, not from HTTP input — low risk. |
| V6 Cryptography | No | Not applicable |

---

## Sources

### Primary (HIGH confidence)
- [alembic.sqlalchemy.org/en/latest/api/commands.html](https://alembic.sqlalchemy.org/en/latest/api/commands.html) — `command.upgrade()` signature and programmatic Config
- [alembic.sqlalchemy.org/en/latest/cookbook.html](https://alembic.sqlalchemy.org/en/latest/cookbook.html) — "Sharing a Connection" pattern for env.py
- [docs.sqlalchemy.org/en/20/dialects/sqlite.html](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) — check_same_thread, event listener pattern, JSON1
- [pyinstaller.org/en/stable/runtime-information.html](https://pyinstaller.org/en/stable/runtime-information.html) — sys.frozen, sys._MEIPASS, `__file__` in bundles
- [github.com/sqlalchemy/sqlalchemy/issues/7212](https://github.com/sqlalchemy/sqlalchemy/issues/7212) — `sa.Uuid` dialect-agnostic type added in SQLAlchemy 2.0
- [sqlite.org/wal.html](https://sqlite.org/wal.html) — WAL mode semantics

### Secondary (MEDIUM confidence)
- [blog.stigok.com/2020/09/06/sqlalchemy-sqlite-json-column-field.html](https://blog.stigok.com/2020/09/06/sqlalchemy-sqlite-json-column-field.html) — confirmed JSON type returns dict on read from SQLite
- [lukaszherok.com/post/view/3/...](https://lukaszherok.com/post/view/3/The%20database%20migrations%20for%20the%20desktop%20application%20with%20Alembic) — desktop app Alembic pattern (set_main_option script_location)
- [github.com/openclaw/openclaw/issues/39176](https://github.com/openclaw/openclaw/issues/39176) — busy_timeout is per-connection

### Tertiary (LOW confidence)
- Multiple WebSearch results on SQLite + WAL + FastAPI patterns (community blogs, corroborated by official SQLite docs)

---

## Metadata

**Confidence breakdown:**
- DB-01 type replacement: HIGH — SQLAlchemy 2.0 official feature, codebase fully audited
- DB-02 path resolution: HIGH — PyInstaller official docs, pattern is established
- DB-03 WAL mode: HIGH — SQLite official docs + SQLAlchemy event listener confirmed pattern
- DB-04 programmatic Alembic: HIGH — official Alembic cookbook pattern
- Assumption A3 (`now()` in DDL): LOW — needs test to confirm

**Research date:** 2026-05-28
**Valid until:** 2026-08-28 (stable libraries; SQLAlchemy and Alembic rarely break these patterns between minor versions)
