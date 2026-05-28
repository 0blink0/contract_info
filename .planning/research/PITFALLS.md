# Pitfalls Research

**Domain:** Electron desktop packaging of an existing FastAPI + Vue + PostgreSQL app (CTRX v1.2)
**Researched:** 2026-05-28
**Confidence:** HIGH (based on direct codebase inspection + well-documented ecosystem issues)

---

## Critical Pitfalls

### Pitfall 1: `postgresql.JSONB` and `postgresql.UUID` imports survive SQLite migration in model and all seven Alembic migrations

**What goes wrong:**
Every column in `ContractFile` uses `postgresql.JSONB` and the primary key uses `postgresql.UUID`. All seven Alembic migrations import `from sqlalchemy.dialects import postgresql` and pass `postgresql.JSONB(...)` and `postgresql.UUID(as_uuid=True)` directly to `op.add_column` and `op.create_table`. SQLite does not have these dialect types. The engine will throw `CompileError: PostgreSQL dialect required` or silently create a TEXT column with no type coercion — meaning JSON columns read back as raw strings instead of dicts, and UUID columns read back as strings that break `.get(ContractFile, file_id)` comparisons.

**Why it happens:**
The original code was correct for PostgreSQL-only deployment. The dialect-specific type classes were not abstracted behind a compatibility layer because there was no need. When switching engines the imports still resolve (psycopg2 may not even be installed), but the dialect-specific compile path is invoked at DDL time.

**How to avoid:**
Replace ALL occurrences across the model AND migrations:
- `postgresql.UUID(as_uuid=True)` → `sa.String(36)` with explicit `str(uuid)` serialization, OR use SQLAlchemy's `Uuid` type (2.0+ generic, works on SQLite)
- `postgresql.JSONB(...)` → `sa.JSON()` (SQLAlchemy's generic JSON type, which uses TEXT on SQLite with automatic serialize/deserialize)
Remove `psycopg2-binary` from the packaged requirements; add `aiosqlite` or use sync `sqlite3` (built-in).
Write a single `compat_types.py` that exports `JSON_TYPE` and `UUID_TYPE` set conditionally on the database URL dialect, then import from there in both the model and migrations.

**Warning signs:**
- `ImportError: No module named 'psycopg2'` during PyInstaller boot (psycopg2 binary is not included)
- `extraction_result` comes back as a Python string `'{"fields": ...}'` instead of a dict — symptom of JSON not being deserialized
- `record.extraction_result["fields"]` raises `TypeError: string indices must be integers`

**Phase to address:**
SQLite migration phase (before any PyInstaller work; SQLite must be working in pure Python before packaging begins)

---

### Pitfall 2: `PROJECT_ROOT` resolves to the `.app` bundle or temp `_MEIPASS` dir, not a writable location

**What goes wrong:**
`config.py` computes `PROJECT_ROOT = Path(__file__).resolve().parents[2]`. In development this is the repo root. Under PyInstaller one-dir mode, `__file__` resolves inside the unpacked `_MEIPASS` temp directory. Writes to `PROJECT_ROOT / "uploads"` and `PROJECT_ROOT / "exports"` go into the read-only bundle directory. On Windows this fails silently (UAC-protected paths inside `%LOCALAPPDATA%\Temp`) or raises `PermissionError`. The app appears to accept uploads but produces no output files and logs nothing because the error is swallowed in `persist_upload`.

**Why it happens:**
`Path(__file__).parents[N]` is the standard development idiom. It is never tested against a packaged layout where the source tree does not exist. PyInstaller sets `sys._MEIPASS` for the temp extraction dir but does not set anything for "where should I write user data."

**How to avoid:**
Add a `get_user_data_dir()` function to `config.py` that checks `sys.frozen` (set by PyInstaller):
```python
def get_user_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        # Electron sets CTRX_DATA_DIR before spawning the Python subprocess
        data_dir = os.environ.get("CTRX_DATA_DIR")
        if data_dir:
            return Path(data_dir)
        # Fallback: platform user data dir
        if sys.platform == "win32":
            return Path(os.environ["APPDATA"]) / "CTRX"
        return Path.home() / ".ctrx"
    return PROJECT_ROOT
```
Electron's main process must set `CTRX_DATA_DIR` to `app.getPath('userData')` before spawning the Python subprocess. `uploads/` and `exports/` are then created inside that dir at startup.

**Warning signs:**
- Upload returns 200 but no file appears in `uploads/`
- Export says "exported" but download returns 404
- Works in `python -m uvicorn` dev mode, breaks in packaged form

**Phase to address:**
PyInstaller packaging phase; verify with a smoke test that writes and reads a file through the full upload → export pipeline in the packaged binary before touching Electron IPC

---

### Pitfall 3: PyInstaller misses hidden imports for FastAPI/uvicorn/pydantic dynamic loading

**What goes wrong:**
PyInstaller's static analysis cannot follow dynamic imports. FastAPI uses `anyio` as its async backend (uvicorn[standard] pulls in `uvloop` on Linux and `asyncio` on Windows). Pydantic v2 has a Rust core (`pydantic_core`) and dynamic validator factories. `pydantic_settings` uses importlib entry points. `python-docx` loads `lxml` via optional import. Any of these missing produces `ModuleNotFoundError` that only appears at runtime inside the packaged binary, not during the build.

**Why it happens:**
`pyinstaller --onedir backend/app/main.py` only traces static `import` statements. Dynamic imports via `importlib`, `__import__`, or plugin systems are invisible to the analysis phase.

**How to avoid:**
Maintain an explicit `hiddenimports` list in `ctrx.spec`:
```python
hiddenimports = [
    # uvicorn / anyio
    "uvicorn.lifespan.on",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "anyio._backends._asyncio",
    # pydantic
    "pydantic.deprecated.class_validators",
    "pydantic_core",
    "pydantic_settings",
    # SQLAlchemy dialects
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.pysqlite",
    # docx / lxml
    "lxml.etree",
    "lxml._elementpath",
    "docx",
    # openpyxl
    "openpyxl.cell._writer",
    # httpx
    "httpx._transports.default",
    "h11",
    # encoding
    "encodings.utf_8",
    "encodings.idna",
]
```
After every dependency upgrade, run the packaged binary against all five export paths and the LLM path, not just the health endpoint.

**Warning signs:**
- `ModuleNotFoundError: No module named 'anyio._backends._asyncio'` on first launch
- Health check passes but `/api/v1/upload` hangs with no error (async backend not loaded)
- Works on dev machine (Python env present), fails on clean test VM

**Phase to address:**
PyInstaller packaging phase; add a CI job that runs packaged binary on a clean Windows VM (no Python installed)

---

### Pitfall 4: SQLite `ALTER TABLE ADD COLUMN` works but `ALTER TABLE DROP COLUMN` and type changes do not

**What goes wrong:**
Alembic's `downgrade()` functions call `op.drop_column(...)`. SQLite does not support `ALTER TABLE DROP COLUMN` in versions before 3.35 (released 2021). Windows ships SQLite 3.31 in many system installs. PyInstaller bundles its own Python, which ships a specific SQLite version. The `pysqlite` dialect silently ignores unsupported ALTER statements in some SQLAlchemy versions, causing the schema to diverge from what Alembic's version table says. The next upgrade migration then fails with a "table already has column X" error.

**Why it happens:**
The seven existing Alembic migrations were written for PostgreSQL, which supports full ALTER TABLE. The `downgrade()` paths have never been exercised against SQLite.

**How to avoid:**
For the SQLite version of migrations, use the `batch_alter_table` context manager for ALL column modifications, including drops:
```python
with op.batch_alter_table("contract_files") as batch_op:
    batch_op.drop_column("old_column")
```
`batch_alter_table` works by creating a new table, copying data, dropping old, renaming — compatible with all SQLite versions. Set `render_as_batch=True` in `alembic/env.py` when the dialect is SQLite.

**Warning signs:**
- `OperationalError: near "DROP": syntax error` during Alembic downgrade
- Schema version table says "007" but `validation_result` column is missing
- Alembic `upgrade head` fails on second install with "duplicate column name"

**Phase to address:**
SQLite migration phase; specifically add a test that runs `alembic upgrade head` on a fresh SQLite file AND on a file already at revision 005

---

### Pitfall 5: Port 18765 (or any fixed port) collision causes silent Python process death

**What goes wrong:**
Electron spawns the Python subprocess with `uvicorn --port 18765`. If that port is in use (previous crashed instance, another app, Windows reserved port range), uvicorn raises `OSError: [Errno 98] Address already in use` and exits with code 1. Electron's main process typically checks `process.exitCode` only in the `close` event handler, which fires asynchronously. The renderer has already loaded `index.html` and started polling `/api/v1/health`. It gets `ERR_CONNECTION_REFUSED` for 30 seconds before showing an error. The user sees a white screen with network errors, not a helpful message.

**Why it happens:**
Fixed port + fire-and-forget subprocess spawning + async event handling. The standard pattern for spawning subprocesses in Electron does not include synchronous "wait for port to be open" logic.

**How to avoid:**
Use port discovery: before spawning, find a free port with a short Node.js snippet (`net.createServer().listen(0)`), pass it to the Python subprocess as `--port`, and store it in a module-level variable for use in all renderer `fetch()` calls. Implement a startup health-check loop in main.js that polls `http://127.0.0.1:{port}/api/v1/health` every 300ms for up to 15 seconds before showing the main window (`mainWindow.show()` deferred until health check passes). If health check times out, show an error dialog, not a blank screen.

**Warning signs:**
- App opens to white/blank screen on second launch after crash
- `EADDRINUSE` in Electron stderr but no user-visible error
- Works in dev (Vite dev server avoids the port), breaks in packaged form

**Phase to address:**
Electron process management phase; test specifically with a mock process holding port 18765

---

### Pitfall 6: Windows Defender / antivirus flags PyInstaller one-file binaries

**What goes wrong:**
PyInstaller `--onefile` mode creates a self-extracting archive that drops files to `%TEMP%\_MEIxxxxxx` and executes them. This is identical behavior to many malware packers. Windows Defender and third-party AV products quarantine or block execution. The `.exe` silently disappears from the user's Downloads folder or the installer fails with "access denied" during extraction. This is a known, documented PyInstaller issue with no complete fix — only mitigations.

**Why it happens:**
`--onefile` uses the same executable-packing technique as common malware. The heuristic is triggered by the self-extraction to temp dir + execution pattern, not by the actual code.

**How to avoid:**
Use `--onedir` mode (not `--onefile`). `--onedir` produces a directory of files, not a self-extracting single binary. Electron Builder then wraps the entire directory, so the user never sees it. This eliminates the temp-dir extraction entirely. Additionally: obtain a code-signing certificate (EV cert for strongest SmartScreen signal) before distributing. Add an NSIS or Squirrel installer wrapper (Electron Builder handles this) so the installer is signed, not just the executable. Do NOT use `--onefile` for this project.

**Warning signs:**
- Test on a fresh Windows machine, not the dev machine (Defender exclusions may be in place)
- `This app can't run on your PC` dialog
- Installer completes but `.exe` is absent from install directory

**Phase to address:**
Windows build pipeline phase; test on a clean Windows VM with default Defender settings before declaring the build ready

---

### Pitfall 7: `asar` packaging swallows the Vue `dist/` or the Python binary directory

**What goes wrong:**
Electron Builder by default packs all files under `resources/` into an `app.asar` archive. Files inside `asar` are read-only and cannot be executed as child processes. If `electron-builder.yml` places the PyInstaller output directory inside the default asar scope, the `child_process.spawn()` call in main.js fails with `ENOENT` or `EACCES` because the path resolves into the asar virtual filesystem, not a real disk path.

**Why it happens:**
`electron-builder` uses `asar: true` by default. The developer adds the PyInstaller dist directory to `extraResources` or `files` without realizing it falls inside the asar scope. The error message references a real-looking path that happens to be inside `app.asar`.

**How to avoid:**
In `electron-builder.yml`, explicitly mark the Python binary directory as `asarUnpack`:
```yaml
asarUnpack:
  - "resources/python-backend/**/*"
```
Or place the PyInstaller output outside the asar entirely using `extraResources` with a `filter`. The spawned process path must resolve to a real filesystem path — test with `fs.existsSync(backendExePath)` before calling `spawn()`.

**Warning signs:**
- `spawn ENOENT` error in Electron main process for the Python executable path
- Path looks correct when logged but `fs.existsSync` returns false
- Works in `electron .` dev mode (no asar), breaks in packaged build

**Phase to address:**
Electron Builder / packaging phase; add a startup assertion that checks the backend binary exists on disk before spawning

---

### Pitfall 8: Alembic runs at startup against a read-only or wrong SQLite path

**What goes wrong:**
The app calls `alembic upgrade head` (or equivalent) on startup to ensure the schema is current. If called before `CTRX_DATA_DIR` is set, Alembic uses the fallback `database_url` from `Settings` which points to `postgresql+psycopg2://...`. On a user machine with no PostgreSQL, this raises `OperationalError` or hangs indefinitely trying to connect. Alternatively, if the SQLite path is constructed from `PROJECT_ROOT` (which is inside the bundle), the DB file is created in a read-only location and every write raises `sqlite3.OperationalError: attempt to write a readonly database`.

**Why it happens:**
Migration logic was written assuming the database URL comes from `.env` which is not present in packaged builds. The Settings class uses `lru_cache`, so the wrong URL is cached for the entire process lifetime.

**How to avoid:**
At packaged startup:
1. Electron sets `CTRX_DATA_DIR` env var BEFORE spawning Python
2. Python startup script (not `main.py` directly) reads `CTRX_DATA_DIR`, constructs `sqlite:////<data_dir>/ctrx.db`, and sets `DATABASE_URL` env var
3. Call `Settings.model_validate(...)` freshly (or clear `lru_cache`) so the new URL is picked up
4. Run `alembic upgrade head` programmatically using the correct engine
5. Only then start uvicorn

**Warning signs:**
- `psycopg2.OperationalError: could not connect to server` in packaged app logs (should never see postgres errors)
- DB file created inside `_MEIPASS` temp dir
- App works on first launch, breaks after reboot (temp dir cleaned, DB gone)

**Phase to address:**
SQLite migration phase (correct URL construction) + Electron process management phase (env var handoff ordering)

---

### Pitfall 9: `updated_at` auto-update via `onupdate=func.now()` silently does nothing in SQLite

**What goes wrong:**
`ContractFile.updated_at` uses `onupdate=func.now()`. In PostgreSQL, `func.now()` is a server-side function. In SQLite, SQLAlchemy translates `func.now()` to the CURRENT_TIMESTAMP SQL function for the `server_default`, but `onupdate` is a Python-side ORM event — it sets the column value when SQLAlchemy issues an UPDATE. However, if the column is not explicitly included in the UPDATE statement (e.g., bulk updates via `session.execute(update(ContractFile)...)`), `onupdate` is silently skipped. Status transitions in `pipeline_service.py` that set `record.status = "exporting"` and then `session.commit()` may leave `updated_at` stale.

**Why it happens:**
`onupdate` in SQLAlchemy ORM works only for ORM-style updates (object attribute mutation + commit), not for Core-style `UPDATE` statements. The inconsistency is documented but easy to miss.

**How to avoid:**
Replace `onupdate=func.now()` with a SQLAlchemy `@event.listens_for(ContractFile, "before_update")` hook, or use a `__init_subclass__` pattern that sets `updated_at = datetime.utcnow()` before each commit. Alternatively, accept that `updated_at` is best-effort and add a SQL trigger in the SQLite migration:
```sql
CREATE TRIGGER update_contract_files_updated_at
AFTER UPDATE ON contract_files
BEGIN
    UPDATE contract_files SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

**Warning signs:**
- `updated_at` always equals `created_at` in SQLite
- Pipeline status transitions visible in `status` column but `updated_at` frozen

**Phase to address:**
SQLite migration phase; add a unit test that verifies `updated_at` changes on status transition

---

### Pitfall 10: First-run startup latency perceived as crash

**What goes wrong:**
The PyInstaller `--onedir` binary must load Python's stdlib, all site packages, FastAPI, SQLAlchemy, pydantic, lxml, openpyxl, and run Alembic migrations before uvicorn begins accepting connections. On a cold HDD this takes 8–20 seconds. Electron shows the main window immediately (or after a 2-second splash), the renderer starts polling `/api/v1/health`, gets 15 consecutive `ERR_CONNECTION_REFUSED` errors, and React/Vue error handlers display a red error state. The user clicks the icon again, spawning a second Python process. Port conflict (Pitfall 5) then kills the first. The user files a bug: "app crashes on startup."

**Why it happens:**
Web apps (FastAPI) start in milliseconds in development because Python is already loaded. The PyInstaller cold-start cost is invisible during development. Electron developers often assume the backend is "instant."

**How to avoid:**
Show a persistent loading state ("正在启动…") from the moment Electron opens until the health check succeeds. Do NOT show the main UI until health check passes. Set a generous timeout (20 seconds for first launch, 10 seconds for subsequent). Show a progress indicator, not a spinner-with-timeout. If startup exceeds 25 seconds, show a diagnostic dialog with the Python process stdout/stderr (pipe it through IPC). Add a `--preload` flag to the PyInstaller entry point that imports all heavy modules at startup time (rather than lazily), so the first request does not trigger an additional cold import.

**Warning signs:**
- Testers report "app crashes immediately" on a machine they've never used it on before
- Works fine after being left open for 30 seconds (Python process eventually ready)
- Electron `webContents.openDevTools()` shows 15+ failed fetch calls on startup

**Phase to address:**
Electron process management phase; specifically test on a cold Windows system with a spinning HDD, not an SSD dev machine

---

### Pitfall 11: `storage_path` stored as relative path breaks when data dir changes between launches

**What goes wrong:**
`upload_service.py` stores `storage_path = str(dest_file.relative_to(PROJECT_ROOT)).replace("\\", "/")` — a path like `"uploads/abc-123/contract.docx"`. This is relative to `PROJECT_ROOT`. In the packaged app, `PROJECT_ROOT` changes between PyInstaller versions (temp dir hash changes). If the user upgrades the app and the bundle extracts to a new `_MEIPASS` path, all existing DB records have invalid `storage_path` values. `parse_service.py` reconstructs the path as `PROJECT_ROOT / record.storage_path` which now points nowhere.

**Why it happens:**
Relative paths assume a stable base. `_MEIPASS` is intentionally ephemeral. The user data directory (`CTRX_DATA_DIR`) is stable across upgrades; the bundle directory is not.

**How to avoid:**
Store `storage_path` as relative to `CTRX_DATA_DIR`, not `PROJECT_ROOT`. When reading back: `get_user_data_dir() / record.storage_path`. On migration day, run a one-time DB migration that rewrites all existing paths (from relative-to-PROJECT_ROOT to relative-to-data-dir). Alternatively store absolute paths, but relative-to-data-dir is portable across installs.

**Warning signs:**
- After upgrading the app, all previously uploaded files return 404 on download
- `FileNotFoundError` in logs references a path under `_MEIPASS` or old bundle dir

**Phase to address:**
SQLite migration phase (data dir path design) + PyInstaller packaging phase (smoke test upgrade scenario)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep `postgresql.JSONB` in model, cast manually at read/write | Avoids model rewrite | JSON columns silently return strings; every caller needs `.json.loads()` defensively | Never — replace with `sa.JSON()` |
| Use `--onefile` PyInstaller to ship single `.exe` | Simpler distribution | Antivirus quarantine; slow startup; no asar path clarity | Never for this project |
| Skip Alembic for SQLite; call `Base.metadata.create_all()` instead | No migration complexity | Cannot upgrade existing installations without data loss | Only acceptable if this is a fresh-install-only product with no upgrade path (it is not) |
| Hard-code port 18765 without fallback | Simpler IPC | Port conflicts cause silent failures; crashes on second launch | Acceptable only if port detection is added as a follow-up in the same phase |
| Skip code signing for Windows | Saves $300-$500/year on EV cert | SmartScreen blocks all users; enterprise deployments fail | Acceptable for internal-only distribution to known machines; never for general release |
| Store LLM API key in `app.json` in app data dir unencrypted | Simple config | Key exposed to any process running as same user | Acceptable for v1.2 (single-user desktop app); revisit if app runs as a service |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Electron → Python subprocess | Spawning with `exec()` instead of `spawn()` | Use `spawn()` with `stdio: ['pipe', 'pipe', 'pipe']` to capture stdout/stderr for diagnostics; `exec()` buffers all output and gives no signal until exit |
| Electron → Python subprocess | Not handling `process.on('exit')` | Always attach exit handler; restart or show error dialog; without it the app silently loses its backend |
| Electron renderer → FastAPI | Using `nodeIntegration: true` to call `fetch()` | Keep `contextIsolation: true`, `nodeIntegration: false`; use `fetch()` directly in renderer (it is available in Chromium) or expose specific IPC via `contextBridge` |
| Electron → Python env vars | Setting env vars after `spawn()` call | Env vars must be passed as `{ env: { ...process.env, CTRX_DATA_DIR: ... } }` in the `spawn()` options object; cannot be set after process starts |
| SQLAlchemy → SQLite | `pool_pre_ping=True` on SQLite | Remove `pool_pre_ping` or set to False for SQLite; it issues a `SELECT 1` which works but adds latency; SQLite connections don't need keepalive |
| Alembic → SQLite | Missing `render_as_batch=True` in `env.py` | Set `context.configure(..., render_as_batch=True)` when dialect is SQLite; required for all column alterations |
| openpyxl → PyInstaller | Template `.xlsx` files not found | Template files must be in `datas` in the `.spec` file: `datas=[("templates/*.xlsx", "templates")]`; they are NOT auto-included |
| python-docx → PyInstaller | `docx` package data (default styles XML) not bundled | Add `datas=[("path/to/docx/templates", "docx/templates")]` to spec; missing causes `PackageNotFoundError` on first parse |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Running Alembic `upgrade head` on every startup | 200–500ms added to every launch | Run migration only when DB file is new or version mismatch detected; check `alembic_version` table first | Immediately noticeable on every cold start; worsens as migrations grow |
| Loading all `openpyxl` template files at import time | 3–8 second startup penalty | Lazy-load templates at first export call, not at module import | Any time openpyxl is imported at top level in a module imported by `main.py` |
| SQLite WAL mode not enabled | Write contention if Electron ever opens a second window or future multi-tab scenario | `PRAGMA journal_mode=WAL` on first connection | Under concurrent read+write; for single-user desktop this is low risk but worth setting |
| `lru_cache` on `get_settings()` after env var injection | Stale settings read (postgres URL cached before SQLite URL set) | Clear cache before startup: `get_settings.cache_clear()` after env vars are set | Always, on first launch; cached wrong value persists for process lifetime |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `nodeIntegration: true` in BrowserWindow | Any XSS in renderer can call `require('child_process')` and execute arbitrary code | Keep default: `nodeIntegration: false`, `contextIsolation: true`; use `contextBridge.exposeInMainWorld()` for approved IPC only |
| Accepting arbitrary file paths from renderer via IPC | Path traversal: renderer sends `../../.ssh/id_rsa` as upload target | Validate all paths in main process; never pass user-provided paths directly to `fs` operations |
| LLM API key in plain `app.json` | Key visible to any process reading user's AppData | Acceptable for v1.2 (single-user, no remote access); for v2 use OS keychain (`keytar` package) |
| CORS `allow_origins: "*"` in packaged app | Any web page can call the local FastAPI server | Set `cors_origins` to `app://` (Electron's custom protocol) or `null` for file:// loaded pages; never wildcard for a local server |
| Electron `webSecurity: false` | Disables same-origin policy; enables CORS bypass | Never disable; load Vue from `http://127.0.0.1:{port}` (served by FastAPI static) or use Electron's custom protocol |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No visible feedback during 8–20 second cold start | User assumes crash; double-clicks icon again; two processes conflict | Show OS-level splash (Electron `BrowserWindow` with splash HTML) immediately, defer main window until health check passes |
| "Server error" shown when LLM key is not configured | First-run user has no context for what "server error" means | First-run wizard gates LLM configuration before any extraction is possible; extraction UI grays out if LLM not configured |
| Download links pointing to `exports/` using absolute paths from packaged binary | Works on dev machine, 404 on user machine | All download endpoints must return paths relative to `CTRX_DATA_DIR`; Electron's `shell.openPath()` or IPC-mediated download is more reliable than HTTP file serving |
| No way to see Python process logs | Crashes are invisible; users can't diagnose | Pipe Python stdout/stderr to a log file in `CTRX_DATA_DIR/logs/`; expose a "View Logs" button in the Settings page |
| Settings page saves but requires restart to take effect | LLM key updated, extraction still fails with old key | `lru_cache` on `get_settings()` means new env values are ignored; either restart Python subprocess on settings save, or clear cache and reinitialize `LlmClient` via an endpoint |

---

## "Looks Done But Isn't" Checklist

- [ ] **SQLite migration:** Verify `extraction_result` column reads back as `dict`, not `str` — run `type(record.extraction_result)` assertion in a test
- [ ] **PyInstaller binary:** Run packaged binary on a clean Windows VM with no Python installed; do not test only on the dev machine
- [ ] **File writes:** After upload → extract → export cycle in packaged mode, confirm files exist on disk in `CTRX_DATA_DIR`, not inside `_MEIPASS`
- [ ] **Port fallback:** Hold port 18765 with a test server, launch the app, verify it uses a different port and starts successfully
- [ ] **Alembic on upgrade:** Install v1.2, create a job, upgrade to v1.3 schema, confirm the job row survives migration
- [ ] **Settings persistence:** Save new LLM API key via Settings page, kill and relaunch app, confirm new key is used
- [ ] **Linux AppImage:** Test on Ubuntu 22.04 and Debian 11 (glibc version matters); the PyInstaller binary links against the build machine's glibc
- [ ] **asar unpack:** Confirm `fs.existsSync(backendExePath)` returns true in packaged build before spawn
- [ ] **Antivirus:** Run packaged installer on a fresh Windows 11 VM with default Defender settings; confirm no quarantine dialog
- [ ] **Offline launch:** Disconnect network, launch app, confirm it starts (should work; LLM features degrade gracefully, not crash)

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| `postgresql.JSONB` in SQLite migration breaks | HIGH — schema corrupt, data may be unreadable | Drop and recreate DB (acceptable for desktop app with single user); write a data repair script that reads TEXT columns and re-inserts as proper JSON |
| Wrong `storage_path` base after upgrade | MEDIUM | Write a one-time migration that re-anchors paths: find all rows where `storage_path` starts with old bundle prefix, rewrite to relative path |
| PyInstaller hidden import missing | LOW — rebuild required | Add to `hiddenimports` in `.spec`, rebuild, redistribute; no data impact |
| Port collision on startup | LOW | Kill lingering Python process (show PID in error dialog); app restarts cleanly |
| Antivirus quarantine | MEDIUM | Sign binary (requires cert); rebuild with `--onedir`; submit to AV vendor for whitelisting |
| `lru_cache` caching wrong settings | LOW | `get_settings.cache_clear()` + subprocess restart; document as known issue with workaround |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| `postgresql.JSONB`/UUID dialect types | SQLite migration | Unit test: `type(record.extraction_result) == dict` after round-trip |
| `PROJECT_ROOT` writable path assumption | SQLite migration + PyInstaller packaging | Integration test: full upload→export on packaged binary writing to temp data dir |
| PyInstaller hidden imports | PyInstaller packaging | Clean VM smoke test: all 5 export paths exercised |
| SQLite `batch_alter_table` for schema changes | SQLite migration | Test: `alembic upgrade head` on fresh file AND on file at revision 005 |
| Port collision | Electron process management | Test: hold port, launch app, verify graceful fallback |
| AV false positive on PyInstaller binary | Windows build pipeline | Clean Windows 11 VM with default Defender, no exclusions |
| `asar` swallowing Python binary | Electron Builder / packaging | `fs.existsSync(backendExePath)` assertion before spawn |
| Alembic running against wrong DB URL | SQLite migration + Electron process mgmt | Verify first line of Python startup log shows `sqlite://` not `postgresql://` |
| `updated_at` silent staleness | SQLite migration | Unit test: status transition changes `updated_at` timestamp |
| Cold-start perceived crash | Electron process management | Test on cold HDD machine; measure time from launch to health-check pass |
| `storage_path` relative to wrong base | SQLite migration | After upgrade test: previously uploaded files still downloadable |

---

## Sources

- Direct codebase inspection: `backend/app/models/contract_file.py` (seven JSONB columns, postgresql.UUID PK), `alembic/versions/001–007` (all use `postgresql.JSONB` directly), `backend/app/config.py` (`PROJECT_ROOT = Path(__file__).resolve().parents[2]`), `backend/app/services/upload_service.py` (relative path storage)
- SQLAlchemy 2.x documentation: `sa.JSON` generic type behavior on SQLite (TEXT + serialize/deserialize), `batch_alter_table` for SQLite ALTER TABLE compatibility, `render_as_batch` in Alembic env
- PyInstaller documentation: `hiddenimports`, `datas`, `--onedir` vs `--onefile`, `sys.frozen`, `sys._MEIPASS`
- Electron Security documentation: `contextIsolation`, `nodeIntegration`, `contextBridge`, BrowserWindow `webSecurity`
- Electron Builder documentation: `asarUnpack`, `extraResources`, AppImage vs deb packaging
- Known PyInstaller issue: AV false positives on self-extracting binaries (GitHub issues #4629, #6912 and numerous community reports)
- pydantic-settings known PyInstaller behavior: entry-point based settings sources require explicit `hiddenimports`
- SQLite version compatibility: `ALTER TABLE DROP COLUMN` added in SQLite 3.35.0 (2021-03-12); Python 3.11 ships SQLite 3.39+ but end-user Windows may have older system SQLite loaded by non-bundled builds

---
*Pitfalls research for: Electron + PyInstaller + SQLite desktop packaging of CTRX FastAPI app*
*Researched: 2026-05-28*
