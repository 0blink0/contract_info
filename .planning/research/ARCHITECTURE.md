# Architecture Research

**Domain:** Electron desktop shell wrapping FastAPI + Vue SPA (v1.2 desktop migration)
**Researched:** 2026-05-28
**Confidence:** HIGH (training-based; all libraries at well-documented stable versions)

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Electron Main Process (Node.js)                                     │
│                                                                      │
│  ┌──────────────────┐   ┌──────────────────┐  ┌──────────────────┐  │
│  │  subprocess.ts   │   │  ipcMain handlers│  │  app lifecycle   │  │
│  │  (spawn/monitor) │   │  (port, settings)│  │  (ready/quit)    │  │
│  └────────┬─────────┘   └────────┬─────────┘  └────────┬─────────┘  │
│           │                      │                     │            │
│           │ child_process.spawn  │ ipcMain.handle      │            │
│           ▼                      ▼                     ▼            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  PyInstaller binary  (ctrx-backend.exe / ctrx-backend)      │    │
│  │  FastAPI + Uvicorn, port 18765, SQLite, uploads/ exports/   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                            ▲  stdout/stderr                         │
│                            │  HTTP health poll                      │
├────────────────────────────┼────────────────────────────────────────┤
│  Electron Renderer (Chromium)                                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Vue 3 SPA  (loadFile dist/index.html or loadURL dev server) │   │
│  │  API calls → http://127.0.0.1:18765/api/v1/...               │   │
│  │  ipcRenderer.invoke('get-port') on startup                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

                  ┌──────────────────────────────────────┐
                  │  User Data Directory (OS-managed)     │
                  │  Windows: %APPDATA%\CTRX              │
                  │  Linux:   ~/.config/CTRX              │
                  │                                       │
                  │  ctrx.sqlite       ← database         │
                  │  uploads/          ← docx files       │
                  │  exports/          ← xlsx outputs     │
                  │  settings.json     ← LLM config       │
                  └──────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | New vs Existing |
|-----------|----------------|-----------------|
| `electron/main.ts` | App entry, spawn backend, window creation, IPC | **NEW** |
| `electron/subprocess.ts` | Python process lifecycle: spawn, health-poll, kill | **NEW** |
| `electron/ipc.ts` | IPC handlers: port forwarding, settings read/write | **NEW** |
| `electron/preload.ts` | Context bridge exposing safe APIs to renderer | **NEW** |
| `backend/app/main.py` | FastAPI application — unchanged | EXISTING |
| `backend/app/config.py` | Settings — needs SQLite URL + user-data path support | **MODIFY** |
| `backend/app/db/session.py` | SQLAlchemy engine — dialect swap only | **MODIFY** |
| `backend/app/models/contract_file.py` | ORM model — JSONB→JSON, UUID type swap | **MODIFY** |
| `alembic/versions/` | All migrations — dialect-specific types to be replaced | **MODIFY** |
| `alembic/env.py` | DB URL injection — unchanged (already from Settings) | EXISTING |
| `frontend/src/api/client.ts` | API_BASE constant — switch to dynamic port | **MODIFY** |
| `frontend/src/main.ts` | Boot — wait for port IPC before first API call | **MODIFY** |
| `ctrx.spec` | PyInstaller spec file | **NEW** |
| `electron-builder.yml` | electron-builder packaging config | **NEW** |
| `package.json` (root) | Electron + build tooling | **NEW** |

---

## Data Flow: App Start to API Ready

```
[User double-clicks installer / app icon]
         │
         ▼
[Electron main process starts]  (Node.js)
         │
         ├─ app.getPath('userData')  →  resolve DATA_DIR
         ├─ resolve BINARY_PATH:
         │    dev:  python -m uvicorn ...
         │    prod: path.join(process.resourcesPath, 'ctrx-backend[.exe]')
         │
         ▼
[subprocess.spawn(binary, ['--port','18765','--data-dir', DATA_DIR])]
         │
         ├─ stdout piped → scan for "Application startup complete"
         │    OR
         ├─ poll  GET http://127.0.0.1:18765/api/v1/health  every 300 ms
         │         with 30 s timeout / 100 retries
         │
         ▼  (health returns 200)
[ipcMain emits 'backend-ready', stores port]
         │
         ▼
[BrowserWindow created]
         │  loadFile('frontend/dist/index.html')   ← prod
         │  loadURL('http://localhost:5173')        ← dev
         │
         ▼
[Renderer Vue SPA boots]
         │
         ├─ preload.contextBridge.exposeInMainWorld('electron', {
         │      getPort: () => ipcRenderer.invoke('get-port'),
         │      getSettings: () => ipcRenderer.invoke('get-settings'),
         │      saveSettings: (s) => ipcRenderer.invoke('save-settings', s)
         │  })
         │
         ├─ App.vue onMounted → window.electron.getPort()
         │      → sets import.meta.env.VITE_API_BASE or reactive apiBase
         │
         ▼
[Vue SPA makes API calls to http://127.0.0.1:18765/api/v1/...]
```

### Backend Startup Sequence (Python side)

```
[ctrx-backend binary invoked by Electron]
         │
         ├─ parse CLI args: --port 18765  --data-dir <path>
         │
         ├─ configure Settings:
         │    database_url = sqlite:///<data_dir>/ctrx.sqlite
         │    uploads_dir  = <data_dir>/uploads/
         │    exports_dir  = <data_dir>/exports/
         │    reads settings.json for LLM keys (if exists)
         │
         ├─ alembic upgrade head  (run programmatically at startup)
         │
         ├─ uvicorn.run(app, host='127.0.0.1', port=18765)
         │
         └─ writes "Application startup complete" to stdout
                ↑ Electron subprocess.ts scans for this string
```

---

## Subprocess Lifecycle: Start / Stop / Crash

### Normal lifecycle

```
Electron main:ready
  → spawn()
  → health poll loop (max 30s)
  → BrowserWindow.show()

app.on('before-quit')
  → pythonProcess.kill('SIGTERM')   // Windows: taskkill /PID
  → wait up to 5s for exit
  → if still alive: .kill('SIGKILL')
  → app.quit()
```

### Crash recovery

```
pythonProcess.on('exit', (code, signal) => {
  if (appIsQuitting) return           // intentional shutdown, ignore
  if (restartAttempts < 3) {
    restartAttempts++
    respawnBackend()                  // re-run spawn + health poll
  } else {
    dialog.showErrorBox(
      'Backend crashed',
      'ctrx-backend exited unexpectedly 3 times. Check logs.'
    )
    app.quit()
  }
})
```

### Key signals

| Event | Electron action | Python action |
|-------|-----------------|---------------|
| Window X button (macOS) | `win.on('close')` — keep running | n/a |
| app.quit() | kill python → quit | receives SIGTERM → uvicorn shutdown |
| Python crash (code ≠ 0) | dialog + optional restart | process exit |
| Health poll timeout | dialog + quit | kill stale process |

---

## PostgreSQL → SQLite Migration

### What changes

| Item | PostgreSQL | SQLite replacement |
|------|------------|-------------------|
| `database_url` | `postgresql+psycopg2://...` | `sqlite:///path/to/ctrx.sqlite` |
| driver | `psycopg2-binary` | built-in `sqlite3` (no extra dep) |
| `JSONB` columns (model) | `sqlalchemy.dialects.postgresql.JSONB` | `sqlalchemy.types.JSON` |
| `UUID` column type (model) | `sqlalchemy.dialects.postgresql.UUID` | `sqlalchemy.types.String(36)` + `str(uuid4())` |
| `func.now()` server_default | works natively | works in SQLAlchemy (uses `CURRENT_TIMESTAMP`) |
| pool settings | `pool_pre_ping=True` | remove / no-op (SQLite is in-process) |
| alembic migrations | use `postgresql.JSONB`, `postgresql.UUID` | rewrite to use `sa.JSON`, `sa.String(36)` |

### Model change pattern

```python
# BEFORE (contract_file.py)
from sqlalchemy.dialects.postgresql import JSONB, UUID

class ContractFile(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ...)
    parse_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

# AFTER (contract_file.py)
import uuid as _uuid
from sqlalchemy import JSON, String

class ContractFile(Base):
    # Store UUID as 36-char string; Python layer still uses uuid.UUID
    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                    default=lambda: str(_uuid.uuid4()))
    parse_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

### Session change

```python
# AFTER (db/session.py)
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # required for SQLite + threading
)
```

### Alembic migration rewrite

All 7 existing migration files import `from sqlalchemy.dialects import postgresql`. These must be rewritten to use `sa.JSON` and `sa.String(36)`. The cleanest approach for desktop:

**Option A (recommended):** Replace all migrations with a single `001_init_sqlite.py` that creates the final schema directly. Alembic is still used for future upgrades. The old PostgreSQL migrations are archived but not deleted.

**Option B:** Keep incremental history, rewrite each file to remove PostgreSQL dialect types. More work, same result.

Option A is recommended because the SQLite desktop database starts fresh on first install — there is no production PostgreSQL data to migrate in place.

### Alembic env.py

No changes needed — it already reads `database_url` from `Settings`, which will be the SQLite URL in desktop mode.

---

## Config: Settings Resolution for Desktop vs Docker

```python
# backend/app/config.py additions

import os
from pathlib import Path

def _resolve_data_dir() -> Path:
    """
    CLI arg takes precedence; fallback to env; fallback to project root (dev).
    PyInstaller binary receives --data-dir from Electron subprocess.ts.
    """
    cli_val = os.environ.get("CTRX_DATA_DIR")
    if cli_val:
        return Path(cli_val)
    # dev / Docker default
    return Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    # NEW: SQLite default for desktop; Docker override via DATABASE_URL env
    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{_resolve_data_dir() / 'ctrx.sqlite'}"
    )
    data_dir: str = Field(default_factory=lambda: str(_resolve_data_dir()))
    ...
```

Electron passes `CTRX_DATA_DIR` as an environment variable to the child process (easier than CLI arg parsing in PyInstaller entry point):

```typescript
// electron/subprocess.ts
const proc = spawn(binaryPath, [], {
  env: {
    ...process.env,
    CTRX_DATA_DIR: app.getPath('userData'),
    CTRX_PORT: String(PORT),
  }
})
```

---

## Vue SPA: Dynamic API Base URL

Current `API_BASE = '/api/v1'` is a relative path, relying on nginx reverse proxy. In the Electron renderer there is no nginx, so calls must be absolute to localhost.

```typescript
// frontend/src/api/client.ts  — MODIFY
let API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

// Called once at Vue app mount from App.vue
export async function initApiBase(): Promise<void> {
  if (window.electron) {
    const port = await window.electron.getPort()
    API_BASE = `http://127.0.0.1:${port}/api/v1`
  }
}
```

`window.electron` is undefined in the Docker/browser environment, so existing Docker deployment continues working without changes.

---

## PyInstaller Spec File Structure

```python
# ctrx.spec  (schematic)
block_cipher = None

a = Analysis(
    ['backend/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('templates/', 'templates/'),   # xlsx templates
        # alembic migrations needed at runtime
        ('alembic/', 'alembic/'),
        ('alembic.ini', '.'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'sqlalchemy.dialects.sqlite',
        'pydantic_settings',
        'httpx',
        # LLM dependency (if bundled local model, add here)
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['psycopg2', 'psycopg2-binary', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ctrx-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # keep True: Electron reads stdout for startup signal
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ctrx-backend',
)
```

### Resource path in packaged binary

FastAPI config must resolve template paths relative to `sys._MEIPASS` (PyInstaller temp dir) when bundled:

```python
# backend/app/config.py
import sys

def _bundle_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)   # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]

def templates_dir() -> Path:
    return _bundle_root() / "templates"
```

`uploads/` and `exports/` are user data, NOT inside the bundle — they go to `_resolve_data_dir()`.

---

## Recommended Project Structure (new layout)

```
contract_info/
├── backend/                        # existing — Python FastAPI
│   ├── app/
│   │   ├── config.py               # MODIFY: SQLite URL, data-dir, bundle path
│   │   ├── db/session.py           # MODIFY: check_same_thread, no pool_pre_ping
│   │   ├── models/contract_file.py # MODIFY: JSON, String(36) instead of JSONB/UUID
│   │   └── ...                     # unchanged
│   └── desktop_main.py             # NEW: uvicorn entry point with CLI arg parsing
│
├── alembic/
│   ├── env.py                      # unchanged
│   └── versions/
│       ├── 001–007_*.py            # archive (PostgreSQL)
│       └── 001_init_sqlite.py      # NEW: single-file SQLite init migration
│
├── frontend/                       # existing Vue 3 SPA
│   └── src/
│       ├── api/client.ts           # MODIFY: dynamic API_BASE
│       ├── main.ts                 # MODIFY: call initApiBase() before mount
│       └── views/SettingsView.vue  # NEW: LLM settings page
│
├── electron/                       # NEW directory
│   ├── main.ts                     # Electron main entry
│   ├── subprocess.ts               # Python binary spawn + health poll
│   ├── ipc.ts                      # ipcMain handlers
│   ├── preload.ts                  # contextBridge for renderer
│   └── settings-store.ts           # read/write settings.json in userData
│
├── ctrx.spec                       # NEW: PyInstaller spec
├── electron-builder.yml            # NEW: packaging config
├── package.json                    # NEW: Electron + build scripts
├── tsconfig.electron.json          # NEW: TS config for electron/ (target: node18)
│
├── docker-compose.yml              # unchanged (Docker path still works)
├── requirements.txt                # MODIFY: remove psycopg2-binary; add nothing (sqlite3 built-in)
└── requirements-prod.txt           # same
```

---

## Architectural Patterns

### Pattern 1: Health-Poll Gate (Backend Ready Check)

**What:** Main process polls `GET /api/v1/health` on a timer before showing the window. The window is created but hidden until the API responds 200.

**When to use:** Always for Python subprocess — startup time is 2–8 s depending on bundle size.

**Trade-offs:** Simple and reliable. No stdout-parsing fragility. A 30 s timeout covers cold starts on slow machines. Show a loading screen in a splash window while polling.

```typescript
// electron/subprocess.ts
export async function waitForBackend(port: number, timeoutMs = 30_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/api/v1/health`)
      if (res.ok) return
    } catch { /* not ready yet */ }
    await new Promise(r => setTimeout(r, 300))
  }
  throw new Error(`Backend did not start within ${timeoutMs / 1000}s`)
}
```

### Pattern 2: Fixed Port with Conflict Guard

**What:** Use a fixed port (18765) but check availability before spawning. If occupied, increment by 1 and retry (up to 3 times).

**When to use:** Single-user desktop app. Avoids random port IPC complexity. Random port is only necessary for multi-instance apps.

**Trade-offs:** Fixed port is simpler for debugging. Rare conflict on ephemeral port range is unlikely; guard handles it.

### Pattern 3: userData Isolation

**What:** All mutable data (SQLite file, uploads, exports, settings.json) goes to `app.getPath('userData')` — an OS-managed per-user directory (`%APPDATA%\CTRX` / `~/.config/CTRX`). The app bundle is read-only after install.

**When to use:** Always for desktop apps. Separates install-time files from runtime data.

**Trade-offs:** Makes uninstall clean. Survives app upgrades. Requires alembic to run at startup for schema migrations.

### Pattern 4: Alembic Programmatic Startup Migration

**What:** Instead of running `alembic upgrade head` as a subprocess, call it programmatically inside `desktop_main.py` before uvicorn starts.

```python
# backend/desktop_main.py
from alembic.config import Config
from alembic import command

def run_migrations(db_url: str) -> None:
    cfg = Config()
    cfg.set_main_option("script_location", str(_bundle_root() / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")
```

**When to use:** Always for bundled desktop app — avoids subprocess-in-subprocess complexity.

---

## Integration Points

### New vs Existing Component Interface

| Boundary | Communication | Contract |
|----------|---------------|---------|
| Electron main ↔ Python backend | HTTP (localhost) + stdout scan | `/api/v1/health` returns `{"status": "ok"}` |
| Electron main ↔ Renderer | Electron IPC (`ipcMain` / `ipcRenderer`) | `get-port` → number; `get-settings` → object; `save-settings` → void |
| Renderer Vue ↔ Python backend | HTTP fetch to `http://127.0.0.1:{PORT}/api/v1/` | No change to existing REST contracts |
| Python ↔ SQLite | SQLAlchemy engine (same ORM) | URL changes; no model query changes |
| Python ↔ LLM API | httpx to external HTTPS | No change; configured via settings.json read at startup |
| PyInstaller bundle ↔ filesystem | `sys._MEIPASS` for read-only assets | `templates/` bundled; `uploads/` `exports/` in userData |

### External Services

| Service | Integration | Notes |
|---------|-------------|-------|
| LLM API (OpenAI-compat) | httpx outbound HTTPS | Key stored in settings.json (userData), not bundled |
| Windows NSIS installer | electron-builder | Code-signing optional for internal use |
| Linux AppImage | electron-builder | No installer needed; self-contained |

---

## Build Pipeline

```
[Source]
    │
    ├─ Step 1: Build Python binary
    │    cd contract_info/
    │    pip install pyinstaller
    │    pyinstaller ctrx.spec --distpath electron/resources/
    │    → electron/resources/ctrx-backend/ctrx-backend[.exe]
    │
    ├─ Step 2: Build Vue SPA
    │    cd frontend/
    │    npm run build
    │    → frontend/dist/   (static files)
    │
    ├─ Step 3: Compile Electron TypeScript
    │    cd contract_info/
    │    tsc -p tsconfig.electron.json
    │    → electron/dist/   (compiled .js)
    │
    └─ Step 4: Package with electron-builder
         npm run dist
         → release/
              Windows:  CTRX-Setup-1.2.0.exe   (NSIS)
              Linux:    CTRX-1.2.0.AppImage
                        CTRX-1.2.0.deb
```

### electron-builder.yml (schematic)

```yaml
appId: com.ctrx.contract-extraction
productName: CTRX
directories:
  output: release/

files:
  - electron/dist/**
  - frontend/dist/**
  - "!node_modules/**"

extraResources:
  - from: electron/resources/ctrx-backend/
    to: ctrx-backend/
    filter: ["**/*"]

win:
  target: nsis
  icon: assets/icon.ico

linux:
  target:
    - AppImage
    - deb
  icon: assets/icon.png

nsis:
  oneClick: false
  perMachine: false
  allowToChangeInstallationDirectory: true
```

---

## Anti-Patterns

### Anti-Pattern 1: Keeping PostgreSQL JSONB/UUID Types in SQLite Migration

**What people do:** Copy-paste existing alembic migrations, only change the URL. The `postgresql.JSONB` and `postgresql.UUID` types are no-ops or raise errors under SQLite.

**Why it's wrong:** `postgresql.JSONB` compiles to unsupported DDL under SQLite. `postgresql.UUID(as_uuid=True)` stores as bytes, breaking string comparisons. Silent data corruption in UUID primary keys.

**Do this instead:** Write a single `001_init_sqlite.py` using only `sa.JSON`, `sa.String(36)`, `sa.Text`, `sa.DateTime`. Keep old PostgreSQL migrations in a `versions/postgres_archive/` subdirectory.

### Anti-Pattern 2: Storing Uploads/Exports Inside PyInstaller Bundle

**What people do:** Bundle `uploads/` and `exports/` inside the `datas` list of the spec file.

**Why it's wrong:** The MEIPASS temp dir is read-only and recreated on every run. Files written to it are lost on exit.

**Do this instead:** Resolve mutable data dirs from `CTRX_DATA_DIR` env var (app.getPath('userData') in Electron). Read-only assets (templates/) go in datas; mutable directories go in userData.

### Anti-Pattern 3: Blocking Main Process on Backend Startup

**What people do:** Use synchronous `spawnSync` or `execSync` to wait for the Python process to be ready before creating the BrowserWindow.

**Why it's wrong:** Blocks the Electron main process event loop. The app appears frozen. macOS/Windows will prompt "app not responding".

**Do this instead:** Show a splash window immediately, spawn asynchronously, poll health in a `setInterval`, then `splashWindow.close(); mainWindow.show()` when ready.

### Anti-Pattern 4: Hardcoding `process.resourcesPath` in renderer code

**What people do:** Access `process.resourcesPath` directly from renderer Vue components.

**Why it's wrong:** `process` is not available in renderer when `nodeIntegration: false` (which is the secure default). Also breaks in browser/Docker mode.

**Do this instead:** Expose only the port number and settings via `contextBridge`. The renderer never needs to know it's in Electron — it only needs the API base URL.

### Anti-Pattern 5: Leaving `pool_pre_ping=True` for SQLite

**What people do:** Copy `create_engine(url, pool_pre_ping=True)` verbatim.

**Why it's wrong:** SQLite does not support connection pool health checks. Causes `NotImplementedError` or silent failures under some SQLAlchemy versions.

**Do this instead:** Use `connect_args={"check_same_thread": False}` for SQLite. Remove `pool_pre_ping`.

---

## Scaling Considerations

This is a single-user desktop application. Traditional scaling does not apply.

| Concern | Desktop Reality |
|---------|----------------|
| Concurrency | One user, one SQLite file. `check_same_thread=False` + SQLAlchemy session-per-request is sufficient. |
| DB file growth | Each job stores full docx bytes + JSON blobs. 1000 contracts ≈ 500 MB. Add periodic cleanup UI in v1.3. |
| LLM latency | 30–120s per validation call (already handled by async background tasks). No change. |
| Memory | PyInstaller bundle + ML deps can be 200–500 MB resident. Test on 8 GB RAM machines. |

---

## Sources

- Electron documentation (contextBridge, ipcMain, child_process, app.getPath) — HIGH confidence, well-established patterns since Electron 12+
- PyInstaller documentation (spec file, sys._MEIPASS, hiddenimports) — HIGH confidence, stable API
- SQLAlchemy documentation (SQLite dialect, check_same_thread, JSON type) — HIGH confidence, documented behavior
- Alembic documentation (programmatic usage via `command.upgrade`) — HIGH confidence
- electron-builder documentation (extraResources, nsis, AppImage) — HIGH confidence
- Existing codebase analysis: `backend/app/config.py`, `backend/app/db/session.py`, `backend/app/models/contract_file.py`, `alembic/versions/001–007_*.py`, `frontend/src/api/client.ts` — direct inspection

---
*Architecture research for: CTRX v1.2 Electron desktop migration*
*Researched: 2026-05-28*
