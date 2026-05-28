---
phase: 11-sqlite-migration
plan: "03"
subsystem: backend/config
tags: [path-resolution, config, desktop-packaging, data-dir]
dependency_graph:
  requires: ["11-01"]
  provides: ["data_dir()", "uploads_dir()", "_bundle_base()", "exports_dir(updated)", "templates_dir(updated)"]
  affects: ["backend/app/config.py", "backend/app/services/*", "backend/app/api/routes/jobs.py", "backend/app/extract/validate.py"]
tech_stack:
  added: []
  patterns: ["CTRX_DATA_DIR env var for desktop data isolation", "_bundle_base() for frozen/dev bundle asset resolution"]
key_files:
  created: []
  modified:
    - backend/app/config.py
    - backend/app/services/upload_service.py
    - backend/app/services/parse_service.py
    - backend/app/services/delete_service.py
    - backend/app/services/preview_service.py
    - backend/app/api/routes/jobs.py
    - backend/app/extract/validate.py
decisions:
  - "DICTS_DIR in extract/validate.py is a module-level constant using _bundle_base() — acceptable because bundle base (sys._MEIPASS or project root) does not change after process start"
  - "data_dir() uses runtime env-var evaluation (not module-level constant) to support test monkeypatching of CTRX_DATA_DIR"
  - "PROJECT_ROOT retained in config.py as fallback in data_dir() and for Settings.env_file resolution"
metrics:
  duration: "3m"
  completed_date: "2026-05-28T07:42:32Z"
  tasks_completed: 2
  files_modified: 7
---

# Phase 11 Plan 03: Path Resolution Helpers (data_dir / _bundle_base) Summary

## One-liner

Added `_bundle_base()`, `data_dir()`, `uploads_dir()` to config.py and propagated them to 6 consumer files so CTRX_DATA_DIR env var fully controls all data paths in desktop mode.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add data_dir() / _bundle_base() helpers to config.py | fd943a3 | backend/app/config.py |
| 2 | Propagate data_dir() to 6 consumer files | ed7f3dc | upload_service, parse_service, delete_service, preview_service, jobs.py, validate.py |

## What Was Built

### Task 1 — config.py new helpers

Added to `backend/app/config.py`:

- `_bundle_base() -> Path`: Returns `sys._MEIPASS` when frozen (PyInstaller desktop bundle), or `Path(__file__).resolve().parents[2]` in dev/Docker mode.
- `data_dir() -> Path`: Returns `Path(CTRX_DATA_DIR)` when env var is set (desktop mode), or `PROJECT_ROOT` as fallback (dev/Docker unchanged).
- `uploads_dir() -> Path`: Returns `data_dir() / "uploads"`.
- Updated `exports_dir()`: Now returns `data_dir() / "exports"` (was `PROJECT_ROOT / "exports"`).
- Updated `templates_dir()`: Now returns `_bundle_base() / "templates"` (was `PROJECT_ROOT / "templates"`).

All 3 RED tests in `backend/tests/test_path_resolution.py` now GREEN.

### Task 2 — 6 consumer files updated

| File | Change |
|------|--------|
| `upload_service.py` | `uploads_dir() / str(file_id)` for dest_dir; `data_dir()` for `relative_to` base |
| `parse_service.py` | `data_dir() / record.storage_path` (was PROJECT_ROOT) |
| `delete_service.py` | `uploads_dir()` and `exports_dir()` for removal paths |
| `preview_service.py` | `data_dir()` for all 5 xlsx path resolutions (product, fee, lock, share, sub) |
| `jobs.py` | `data_dir() / rel_path` in `_resolve_export_path`; path traversal guard (`full.relative_to(root)`) preserved |
| `extract/validate.py` | `DICTS_DIR = _bundle_base() / "dicts"` at module level |

Zero `PROJECT_ROOT /` data-path references remain in any of the 6 consumer files.

## Verification Results

1. `grep -r "PROJECT_ROOT / " backend/app/services/ ...` — **zero matches** (PASS)
2. `pytest backend/tests/test_path_resolution.py -x` — **3 passed** (PASS)
3. CTRX_DATA_DIR env var test: `uploads_dir()` returns `$CTRX_DATA_DIR/uploads` (PASS)
4. All consumer module imports succeed (PASS)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all code paths are fully wired.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. The `_resolve_export_path` path traversal guard in `jobs.py` was preserved when changing the base from `PROJECT_ROOT` to `data_dir()`. This satisfies threat T-11-07 mitigation.

## Self-Check: PASSED

- `backend/app/config.py` — exists and contains `_bundle_base`, `data_dir`, `uploads_dir`
- `fd943a3` — commit exists (Task 1)
- `ed7f3dc` — commit exists (Task 2)
- test_path_resolution.py — 3 tests GREEN
- Zero PROJECT_ROOT data-path references in consumer files
