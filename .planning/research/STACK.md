# Stack Research

**Domain:** Electron desktop packaging — FastAPI+Vue app with embedded Python backend
**Researched:** 2026-05-28
**Confidence:** HIGH (Electron/electron-builder verified via Context7; PyInstaller version via PyPI; SQLAlchemy SQLite dialect verified via Context7)

---

## Context: What Already Exists (Do Not Re-research)

- **FastAPI 0.136+** — Python 3.11, Uvicorn, pydantic-settings
- **Vue 3.5 + Element Plus + Vite 6** — frontend, TypeScript, vue-router 4
- **SQLAlchemy 2.0.50 + Alembic 1.18** — ORM + migrations
- **psycopg2-binary 2.9** — PostgreSQL driver (to be REPLACED)
- **Docker + docker-compose** — server deployment (to be SUPPLEMENTED, not removed)

---

## New Stack Additions for v1.2 Desktop

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Electron | 42.x (latest stable) | Desktop shell — wraps Vue frontend, manages Python subprocess | Industry standard for desktop-from-web-app; ships Chromium+Node in one binary; well-supported on Windows+Linux |
| electron-builder | 26.x (latest stable) | Builds .exe (NSIS) installer for Windows, AppImage/deb for Linux | De-facto standard packager; native NSIS and AppImage targets built-in; handles code signing, extraResources bundling |
| PyInstaller | 6.20 (latest stable) | Packages Python 3.11 + FastAPI backend into single-dir bundle | Only mature solution for packaging Python with native extensions (lxml, psycopg2 removed, etc.); Python 3.11 fully supported |
| aiosqlite | 0.22.1 | SQLite async driver for SQLAlchemy | Required for `sqlite+aiosqlite://` URL if async sessions are used; synchronous `sqlite:///` works with existing sync session setup |
| electron-store | 11.x (latest stable) | Persist LLM config (API key, base URL, model) in Electron userData | Purpose-built for Electron config persistence; stores JSON in OS-appropriate location (%APPDATA% on Windows); schema validation built-in |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| vite-plugin-electron | 0.29.x | Integrates Electron main/preload scripts into Vite dev build | Use during development so `npm run dev` starts both Vite dev server and Electron together |
| wait-on | ~8.x | Electron main process waits for Python backend HTTP port before loading URL | Essential — Python subprocess takes 1-3s to start; without this, `loadURL` hits a blank error page |
| cross-env | ~7.x | Cross-platform env var injection in npm scripts | Needed for Windows-compatible `NODE_ENV=production` in build scripts |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| electron-builder (CLI) | `npx electron-builder --win --linux` | Run on Windows to produce both targets; Linux AppImage can be cross-compiled from Windows via wine or CI |
| PyInstaller spec file | `backend.spec` — controls what gets bundled | Required to include `dicts/`, `templates/`, `contract_keywords.txt`; use `--add-data` directives |
| Alembic (existing) | SQLite schema migrations at first run | Re-use existing migration chain; replace `postgresql.UUID` and `postgresql.JSONB` types in migration files |

---

## Installation

```bash
# Electron shell (add to frontend/ or new electron/ package)
npm install electron electron-builder vite-plugin-electron electron-store

# Dev utilities
npm install -D cross-env wait-on

# Python additions (add to requirements.txt)
# Remove: psycopg2-binary
# Add:
pip install aiosqlite
# PyInstaller is a build-time tool, not a runtime dep:
pip install pyinstaller==6.20.0
```

---

## Critical Migration: PostgreSQL-Specific Types → SQLite-Compatible

The existing model uses PostgreSQL-only types that **must** be replaced:

| Current (PostgreSQL-only) | Replace With | Notes |
|---------------------------|-------------|-------|
| `sqlalchemy.dialects.postgresql.JSONB` | `sqlalchemy.types.JSON` | SQLite stores as TEXT; SQLAlchemy 2.x `JSON` type handles serialize/deserialize transparently |
| `sqlalchemy.dialects.postgresql.UUID(as_uuid=True)` | `sqlalchemy.types.Uuid` (SA 2.0) or `CHAR(36)` TypeDecorator | SQLAlchemy 2.0 ships `sqlalchemy.types.Uuid` — dialect-agnostic UUID; stores as `CHAR(36)` on SQLite, native UUID on PostgreSQL |
| `server_default=sa.text("now()")` in Alembic migrations | `server_default=sa.text("(datetime('now'))")` | SQLite uses `datetime('now')` not `now()` — or use Python-side `default=datetime.utcnow` to avoid dialect split |

**Alembic migration files** (001–007) all import from `sqlalchemy.dialects.postgresql` — these need a SQLite-compat variant. The recommended approach: write a new `008_sqlite_compat.py` migration that is a no-op when schema already matches, and update the model file to use dialect-agnostic types.

**`pool_pre_ping=True`** in `session.py` is safe with SQLite — no change needed. SQLite connection URL: `sqlite:///path/to/ctrx.db`.

---

## Config Architecture: LLM Settings Storage

Use **electron-store** (Node.js side, main process) to store:
```json
{
  "llm": {
    "apiBase": "https://api.openai.com/v1",
    "apiKey": "sk-...",
    "model": "gpt-4o-mini"
  },
  "setupComplete": true
}
```

On app start, main process reads store and passes LLM config to Python subprocess via environment variables (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_MODEL`). Renderer reads/writes settings via IPC (`ipcRenderer.invoke` → `ipcMain.handle`). **Do not** store the API key inside the Python `.env` file on disk — pass at process spawn time only.

---

## Electron Process Architecture

```
Electron Main Process (Node.js)
  ├── Spawns: python_backend/ (PyInstaller exe) as child_process
  │     └── Passes env: OPENAI_API_KEY, DB_PATH, UPLOADS_DIR
  ├── Manages: app lifecycle (ready, window-all-closed, will-quit)
  ├── IPC handlers: get/set LLM config, get backend port/status
  ├── Preload script: contextBridge.exposeInMainWorld('electronAPI', {...})
  └── BrowserWindow: loadFile(dist/index.html) after backend ready

Renderer Process (Vue 3 app, Vite-built static files)
  └── Calls http://127.0.0.1:8000/api/v1/* (same as before — no change needed)
```

**Key constraint:** Use `contextIsolation: true` (Electron default since v12) + preload script. Never set `nodeIntegration: true`.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| electron-builder | Electron Forge | Forge is opinionated scaffolding; builder is more flexible for adding pre-built Python binary as extraResource; better NSIS/AppImage control |
| electron-builder | Tauri | Tauri requires Rust; backend must be Rust or sidecar; Python-as-sidecar support is experimental and adds complexity |
| PyInstaller | cx_Freeze | PyInstaller has better hook ecosystem (`pyinstaller-hooks-contrib`) covering FastAPI, SQLAlchemy, lxml, pydantic automatically |
| PyInstaller | Nuitka | Nuitka compiles to C; faster startup but requires C compiler on build host and has edge cases with dynamic imports heavy in FastAPI |
| electron-store | node-keytar | keytar is for OS credential vault (better for secrets); electron-store is simpler and sufficient for LLM base URL + model; consider keytar only if compliance requires it |
| SQLite (aiosqlite) | Keep PostgreSQL | PostgreSQL requires a running server — incompatible with desktop single-install requirement; SQLAlchemy 2.x makes SQLite migration straightforward |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `nodeIntegration: true` in BrowserWindow | Exposes full Node.js to renderer — XSS = RCE; Electron security docs mark this insecure | `contextIsolation: true` + preload script with `contextBridge` |
| `psycopg2-binary` in desktop build | Requires PostgreSQL server; binary is platform-specific and large; PyInstaller hooks are fragile for it | Remove from requirements; SQLite with built-in Python `sqlite3` module |
| `postgresql.JSONB` / `postgresql.UUID` in models | These are PostgreSQL dialect-specific; will raise `CompileError` against SQLite | `sqlalchemy.types.JSON` and `sqlalchemy.types.Uuid` (SA 2.0+) |
| Alembic `autogenerate` against SQLite for migration 001-007 | Alembic migrations import `postgresql` dialect directly — will fail | Write adapter migration 008 or rewrite model imports to be dialect-agnostic |
| Bundling Vue dev server in production | `vite dev` is not for production; adds ~200MB Node.js overhead | `vite build` → static `dist/` → `win.loadFile('dist/index.html')` |
| `server_default=sa.text("now()")` in new SQLite migrations | PostgreSQL SQL function; SQLite uses `(datetime('now'))` | Python-side `default=datetime.utcnow` in SQLAlchemy model, no server_default needed |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| electron@42.x | Node.js 22.x (bundled) | Electron ships its own Node — host Node version irrelevant for runtime |
| electron-builder@26.x | electron@42.x | Builder 26.x explicitly supports Electron 42; check `electronVersion` config field |
| PyInstaller@6.20 | Python 3.11, 3.12 | 3.11 fully supported; `pyinstaller-hooks-contrib` auto-installed as dependency, covers SQLAlchemy, FastAPI, pydantic |
| SQLAlchemy@2.0.50 | SQLite (stdlib sqlite3), aiosqlite@0.22 | Sync `sqlite:///` works without aiosqlite; only needed if adding async sessions |
| vite@6.x + vite-plugin-electron@0.29 | Vue 3.5, TypeScript 5.7 | Plugin wraps Vite config; no additional Vite version constraint |
| electron-store@11.x | ESM only | Requires `"type": "module"` in electron package.json, or use dynamic `import()` from CommonJS main process |

**electron-store v11 ESM caveat:** If the Electron main process uses CommonJS (`require()`), pin electron-store to `^10.0.0` which supports both CJS and ESM. electron-store v11+ is ESM-only.

---

## Stack Patterns by Variant

**If building on Windows only (CI = Windows runner):**
- NSIS `.exe` installer builds natively
- Linux AppImage requires either a Linux runner in CI or Docker-based cross-compile via electron-builder's `--linux` with wine
- Recommended: GitHub Actions with two jobs — `build-win` (windows-latest) and `build-linux` (ubuntu-latest)

**If PyInstaller bundle is too large (>300 MB):**
- Use `--exclude-module` to drop unused stdlib modules (`tkinter`, `test`, `unittest`)
- Use `UPX` compression (PyInstaller `--upx-dir` flag) for ~30% size reduction on Windows
- Do NOT exclude `_ssl` — httpx (used for LLM calls) requires TLS

**If SQLite concurrency becomes a problem (multiple windows):**
- SQLite with WAL mode (`PRAGMA journal_mode=WAL`) handles concurrent readers + one writer
- Add `engine = create_engine("sqlite:///...", connect_args={"check_same_thread": False})` since Uvicorn's thread pool may access from non-creator threads

---

## Sources

- Context7 `/electron/electron` — `app.getPath`, `isPackaged`, IPC (`ipcMain.handle`, `contextBridge`), `BrowserWindow.loadFile`, subprocess spawn
- Context7 `/electron-userland/electron-builder` — Windows NSIS target, Linux AppImage target, `extraResources`, auto-update targets
- Context7 `/sindresorhus/electron-store` — `store.get`, `store.set`, schema, ESM note
- Context7 `/websites/sqlalchemy_en_20` — `sqlalchemy.types.JSON` SQLite support, `GUID` TypeDecorator pattern, `sqlite+aiosqlite` dialect
- PyPI `pip index versions pyinstaller` — confirmed 6.20.0 is latest
- `npm show electron version` — confirmed 42.3.0 is latest stable
- `npm show electron-builder version` — confirmed 26.8.1 is latest stable
- `npm show electron-store version` — confirmed 11.0.2 is latest (ESM-only)
- `npm show vite-plugin-electron version` — confirmed 0.29.1

---
*Stack research for: Electron desktop packaging of FastAPI+Vue app (CTRX v1.2)*
*Researched: 2026-05-28*
