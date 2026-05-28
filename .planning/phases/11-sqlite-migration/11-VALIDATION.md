---
phase: "11"
phase_slug: sqlite-migration
date: 2026-05-28
---

# Phase 11 Validation Strategy

## Coverage

| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| DB-01a | `alembic upgrade head` succeeds against SQLite URL (all 7 migrations) | integration | `pytest backend/tests/test_db_migration.py -x` |
| DB-01b | `extraction_result` column stores dict, reads back as dict (not str) | unit | `pytest backend/tests/test_db_migration.py::test_json_roundtrip -x` |
| DB-01c | No `postgresql` dialect import in any migration or model | static | `grep -r "from sqlalchemy.dialects.postgresql" alembic/ backend/app/models/` |
| DB-02a | `CTRX_DATA_DIR=/tmp/test` → uploads written to `/tmp/test/uploads/` | unit | `pytest backend/tests/test_path_resolution.py::test_uploads_dir_uses_env -x` |
| DB-02b | Unset `CTRX_DATA_DIR` → falls back to `PROJECT_ROOT` (dev unchanged) | unit | `pytest backend/tests/test_path_resolution.py::test_uploads_dir_fallback -x` |
| DB-02c | `_bundle_base()` returns `sys._MEIPASS` when `sys.frozen=True` | unit | `pytest backend/tests/test_path_resolution.py::test_bundle_base_frozen -x` |
| DB-03a | WAL mode is active on SQLite connections | integration | `pytest backend/tests/test_db_wal.py::test_wal_mode_enabled -x` |
| DB-03b | 3 concurrent uploads complete without lock timeout | integration | `pytest backend/tests/test_db_wal.py::test_concurrent_writes -x` |
| DB-04a | `desktop_main.run_migrations()` creates schema on fresh DB | integration | `pytest backend/tests/test_desktop_main.py::test_migrations_fresh_db -x` |
| DB-04b | `desktop_main.run_migrations()` is idempotent on already-migrated DB | integration | `pytest backend/tests/test_desktop_main.py::test_migrations_idempotent -x` |

## Commands

```bash
cd contract_info
# Per-task smoke
pytest backend/tests/test_db_migration.py backend/tests/test_path_resolution.py backend/tests/test_desktop_main.py -x -q

# Per-wave
pytest backend/tests/ -q --ignore=backend/tests/golden

# Phase gate (before /gsd:verify-work)
pytest backend/tests/ -q --ignore=backend/tests/golden -m "not llm"
```

## Wave 0 Test Files (must be created)

- [ ] `backend/tests/test_db_migration.py` — DB-01a, DB-01b
- [ ] `backend/tests/test_path_resolution.py` — DB-02a, DB-02b, DB-02c
- [ ] `backend/tests/test_db_wal.py` — DB-03a, DB-03b
- [ ] `backend/tests/test_desktop_main.py` — DB-04a, DB-04b
