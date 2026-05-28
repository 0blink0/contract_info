# Project Research Summary

**Project:** CTRX v1.2 -- Electron Desktop Packaging Milestone
**Domain:** Electron desktop shell wrapping an existing FastAPI + Vue 3 SPA with PostgreSQL to SQLite migration
**Researched:** 2026-05-28
**Confidence:** HIGH

## Executive Summary

CTRX v1.2 is a well-scoped migration milestone: an already-shipped web app (upload, extract, validate, export contract data via LLM) gains a native Windows and Linux desktop installer. The core pattern -- Electron main process spawning a PyInstaller-bundled FastAPI subprocess, with the Vue SPA loaded as static files -- is a mature, well-documented approach with clear precedents (Ollama Desktop, local AI tools). The technology choices have high confidence: Electron 42 + electron-builder 26 for the shell, PyInstaller 6.20 for the Python binary, SQLite replacing PostgreSQL, and electron-store for LLM credential persistence.

The single largest risk is not the Electron integration itself but the PostgreSQL-to-SQLite migration hiding in the codebase. All seven existing Alembic migrations and the ContractFile model use PostgreSQL-specific dialect types (postgresql.JSONB, postgresql.UUID) that must be replaced with SQLAlchemy generic types (sa.JSON, sa.String(36)) before any packaging work begins. A second structural problem is that PROJECT_ROOT and storage_path are computed relative to __file__ -- paths that point into a read-only or ephemeral PyInstaller _MEIPASS temp directory when packaged. These two issues will cause silent data corruption and invisible file loss if not corrected in the first phase.

The recommended approach is three sequential phases: (1) SQLite migration and path correctness, (2) PyInstaller binary build and smoke-test on a clean VM, (3) Electron shell, first-run wizard, and packaging. This ordering is load-bearing: the SQLite code must work correctly in pure Python before it is bundled, and the binary must be verified on a clean machine before Electron IPC is layered on top. Skipping ahead produces compound failures that are difficult to diagnose. Docker deployment is explicitly preserved -- no changes are required to the server path.
---

## Key Findings

### Recommended Stack

The desktop build adds a thin layer of new dependencies on top of the existing stack. Electron 42 wraps the Vue SPA and manages the Python subprocess lifecycle. electron-builder 26 produces the NSIS .exe installer (Windows) and AppImage (Linux) from a single electron-builder.yml. PyInstaller 6.20 compiles the FastAPI + Uvicorn + SQLAlchemy stack into a --onedir binary bundle (never --onefile -- AV false-positive risk is too high). SQLite replaces PostgreSQL; SQLAlchemy 2.x ORM requires only a dialect swap and type substitutions, not a query rewrite. electron-store 11 persists LLM configuration in %APPDATA%/CTRX/settings.json on Windows.

**Core technologies:**
- **Electron 42** -- desktop shell, subprocess management, IPC; industry standard; ships Chromium + Node; well-tested on Windows and Linux
- **electron-builder 26** -- NSIS and AppImage packaging; better extraResources control than Forge; required for Python binary bundling
- **PyInstaller 6.20 (--onedir)** -- Python binary; only mature option for FastAPI + pydantic + lxml; pyinstaller-hooks-contrib covers all major deps automatically
- **SQLite (stdlib sqlite3 + optional aiosqlite 0.22)** -- replaces PostgreSQL; no server required; SQLAlchemy 2.x handles dialect transparently
- **electron-store 11** -- LLM config persistence; stores JSON in OS userData; ESM-only (requires type:module or pin to v10 for CJS main process)
- **vite-plugin-electron 0.29** -- dev-mode integration; enables npm run dev to start Vite + Electron together
- **wait-on ~8** -- startup gate; Electron waits for Python HTTP port before loading the renderer URL

**Critical version note:** electron-store v11 is ESM-only. If the Electron main process uses CommonJS require(), pin to ^10.0.0.

### Expected Features

The v1.2 milestone adds desktop-specific UX on top of the shipped v1.1 feature set. The target user is non-technical operations staff on Windows who double-click an installer and configure once.

**Must have (table stakes -- v1.2 launch):**
- First-run setup wizard (3 steps: Welcome -> LLM credentials -> connection test) -- app is unconfigurable without it
- Config written to userData/config.json (electron-store) -- must survive restarts; NOT a .env file at project root
- Backend subprocess spawned at app start, config injected as env vars (OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL)
- Backend startup loading overlay until /api/v1/health returns 200 -- cold start takes 8-20 seconds; user must not see blank screen
- Subprocess failure dialog with restart button and log path -- actionable, not generic network error
- Settings page at /settings route -- re-entry after API key rotation
- App menu with Quit + Settings shortcut + About
- About dialog showing app.getVersion() -- needed for support ticket escalation

**Should have (v1.2.x after validation):**
- Backend log tail (last 50 lines) in Settings -- add when IT support tickets arrive
- Model name presets dropdown -- add when model selection becomes frequent operation
- Re-run wizard button in Settings -- add when first key rotation occurs
- Masked API key display (sk-...****) -- trust indicator

**Defer (v2+):**
- Auto-update via electron-updater -- requires release server; over-engineered for a 2-person ops team
- System tray background operation -- not an always-on tool; wastes memory on shared workstations
- Multi-account / workspace profiles -- ops team shares one API account per org policy

**Keystone dependency:** the config read/write layer (electron-store + IPC channels) must be a single abstraction shared by both wizard and settings page. If implemented independently, settings changes do not reach the backend on next restart.
### Architecture Approach

The architecture is a three-layer stack: Electron main process (Node.js) manages app lifecycle, spawns the Python subprocess, and owns IPC; the Renderer (Chromium, Vue 3 SPA from static dist/) makes HTTP calls to localhost as before; the PyInstaller binary runs FastAPI on port 18765. All mutable data -- SQLite file, uploads, exports, settings.json -- lives in app.getPath(userData) (%APPDATA%/CTRX on Windows, ~/.config/CTRX on Linux), completely separate from the read-only app bundle. The Vue SPA requires a one-line modification to api/client.ts to resolve an absolute http://127.0.0.1:{port}/api/v1 base URL via IPC, with a guard that leaves the existing relative URL intact for Docker/browser deployments.

**Major components (new or modified):**

1. **electron/main.ts** -- app entry, window creation, IPC hub (NEW)
2. **electron/subprocess.ts** -- Python process spawn, health-poll loop (30s timeout, 300ms interval), crash recovery with 3-retry limit (NEW)
3. **electron/ipc.ts** -- get-port, get-settings, save-settings, backend:restart, log:tail handlers (NEW)
4. **electron/preload.ts** -- contextBridge.exposeInMainWorld -- the only surface the renderer can touch (NEW)
5. **electron/settings-store.ts** -- electron-store read/write abstraction (NEW)
6. **backend/desktop_main.py** -- PyInstaller entry point; reads CTRX_DATA_DIR, runs Alembic programmatically, starts uvicorn (NEW)
7. **backend/app/config.py** -- adds get_user_data_dir() (checks sys.frozen), _bundle_root() (checks sys._MEIPASS), SQLite URL default (MODIFY)
8. **backend/app/models/contract_file.py** -- postgresql.JSONB -> sa.JSON, postgresql.UUID -> sa.String(36) (MODIFY)
9. **alembic/versions/001_init_sqlite.py** -- single fresh-schema migration replacing all 7 PostgreSQL migrations (NEW; old migrations archived)
10. **frontend/src/views/SettingsView.vue** -- LLM settings page at /settings route (NEW)
11. **ctrx.spec** -- PyInstaller spec with explicit hiddenimports list (NEW)
12. **electron-builder.yml** -- NSIS + AppImage targets, extraResources, asarUnpack for Python binary (NEW)

**Key patterns:**
- Health-poll gate: never show main window until /api/v1/health returns 200
- userData isolation: all mutable data in OS userData dir; bundle is read-only after install
- Programmatic Alembic: alembic.command.upgrade(cfg, head) inside desktop_main.py, not a subprocess call
- Dynamic API base: renderer calls window.electron.getPort() once at mount; falls back to relative URL when window.electron is undefined (Docker compat)

### Critical Pitfalls

1. **postgresql.JSONB/UUID dialect types in model and all 7 migrations** -- Replace with sa.JSON and sa.String(36) universally; write a single 001_init_sqlite.py. Symptom to catch: extraction_result returns Python str instead of dict.

2. **PROJECT_ROOT and storage_path point into read-only _MEIPASS bundle** -- Add get_user_data_dir() that reads CTRX_DATA_DIR env var (set by Electron before spawning); store storage_path relative to CTRX_DATA_DIR, not PROJECT_ROOT. Silent symptom: uploads return 200 but no files written to disk.

3. **PyInstaller missing hidden imports for FastAPI/uvicorn/pydantic dynamic loading** -- Maintain explicit hiddenimports in ctrx.spec covering at minimum: uvicorn.lifespan.on, uvicorn.protocols.http.auto, anyio._backends._asyncio, pydantic_core, pydantic_settings, sqlalchemy.dialects.sqlite.pysqlite, lxml.etree, lxml._elementpath, openpyxl.cell._writer, h11. Test on a clean VM with no Python installed.

4. **PyInstaller --onefile triggers Windows Defender quarantine** -- Use --onedir exclusively; electron-builder wraps the directory so users never see it. Never use --onefile for this project.

5. **asar packaging swallows the Python binary directory** -- Add asarUnpack: [resources/ctrx-backend/**/*] to electron-builder.yml. Assert fs.existsSync(backendExePath) before calling spawn().

6. **lru_cache on get_settings() caches the PostgreSQL URL before SQLite URL is injected** -- Call get_settings.cache_clear() in desktop_main.py after env vars are set, before Alembic runs. Symptom: psycopg2.OperationalError in a packaged app that has no PostgreSQL.

7. **Cold-start (8-20 seconds) perceived as crash** -- Show persistent loading splash from first frame; 30-second health-poll timeout; pipe Python stdout/stderr to log file; expose log path in error dialog.
---

## Implications for Roadmap

### Phase 1: SQLite Migration and Path Correctness

**Rationale:** This is the blocker for everything else. The existing codebase contains PostgreSQL-specific type imports and a hard-coded PROJECT_ROOT path assumption that will silently corrupt data or fail to write files in any packaging scenario. These must be fixed and verified in pure Python before PyInstaller is introduced.

**Delivers:** A working FastAPI + SQLite backend that runs with sqlite:/// URL, passes all existing API tests, reads/writes files to a configurable data directory, and has clean Alembic migrations with no PostgreSQL dialect dependencies.

**Addresses (FEATURES.md):** Config persistence layer (the keystone dependency shared by wizard and settings page); backend startup precondition.

**Avoids (PITFALLS.md):** Pitfall 1 (JSONB/UUID types), Pitfall 2 (PROJECT_ROOT writable path), Pitfall 4 (SQLite batch_alter_table), Pitfall 8 (Alembic wrong URL), Pitfall 9 (updated_at staleness), Pitfall 11 (storage_path wrong base).

**Research flag:** Standard patterns. SQLAlchemy 2.x SQLite migration is well-documented; ARCHITECTURE.md provides exact code patterns. No additional research needed for planning.

---

### Phase 2: PyInstaller Binary Build and Smoke Testing

**Rationale:** PyInstaller must be verified in isolation on a clean machine before Electron IPC is layered on top. Compound failures (missing imports + wrong data paths + Electron spawn issues all at once) are extremely hard to diagnose. A passing smoke test on a clean Windows VM is the gate condition for Phase 3.

**Delivers:** A ctrx-backend.exe (Windows) and ctrx-backend (Linux) that pass a full upload -> extract -> export smoke test on a machine with no Python or PostgreSQL installed, writing files to a CTRX_DATA_DIR test directory.

**Uses (STACK.md):** PyInstaller 6.20, ctrx.spec with explicit hiddenimports, --onedir mode.

**Implements (ARCHITECTURE.md):** backend/desktop_main.py, ctrx.spec, _bundle_root() / get_user_data_dir() in config.py.

**Avoids (PITFALLS.md):** Pitfall 2 (PROJECT_ROOT in packaged build), Pitfall 3 (hidden imports), Pitfall 6 (AV false positive from --onefile).

**Research flag:** May need one rebuild iteration after first clean-VM test to catch LLM client transitive imports (openai SDK, httpx internals) not covered by the initial hiddenimports list.

---

### Phase 3: Electron Shell, IPC, and First-Run Wizard

**Rationale:** With a verified Python binary in hand, the Electron integration is straightforward plumbing. The main risks (subprocess lifecycle, port detection, asar packaging) are well-understood and addressable with known patterns. The first-run wizard and settings page are pure frontend work with no backend changes needed.

**Delivers:** A launchable Electron app that spawns the Python binary, shows a loading splash until health check passes, displays the first-run wizard on first launch, and reaches the existing CTRX feature set. Settings page at /settings with LLM config.

**Uses (STACK.md):** Electron 42, vite-plugin-electron 0.29, electron-store 11, wait-on ~8.

**Implements (ARCHITECTURE.md):** electron/main.ts, subprocess.ts, ipc.ts, preload.ts, settings-store.ts, Vue SettingsView.vue, dynamic API_BASE in client.ts.

**Addresses (FEATURES.md):** First-run wizard (P1), backend startup indicator (P1), subprocess failure error message (P1), settings page (P1), app menu + Quit (P1), About dialog (P1), masked API key display (P2).

**Avoids (PITFALLS.md):** Pitfall 5 (port collision), Pitfall 7 (asar swallowing binary), Pitfall 10 (cold-start perceived crash), nodeIntegration security mistake.

**Research flag:** Standard patterns. Electron subprocess management and IPC are thoroughly documented. No additional research needed.

---

### Phase 4: Packaging, Installer Build, and Distribution

**Rationale:** Once the app runs correctly in electron . dev mode, electron-builder packaging is mostly configuration. The primary new risk is the asar/extraResources setup and Windows Defender behavior on the NSIS installer -- both testable with a clean VM.

**Delivers:** CTRX-Setup-1.2.0.exe (Windows NSIS installer) and CTRX-1.2.0.AppImage (Linux). Verified on clean Windows 11 VM with default Defender settings. Build pipeline documented.

**Uses (STACK.md):** electron-builder 26, NSIS target (Windows), AppImage + deb (Linux), GitHub Actions (two jobs: build-win on windows-latest, build-linux on ubuntu-latest).

**Implements (ARCHITECTURE.md):** electron-builder.yml, asarUnpack directive, 4-step build pipeline (PyInstaller -> Vite build -> tsc -> electron-builder).

**Avoids (PITFALLS.md):** Pitfall 6 (AV quarantine via --onedir + code signing consideration), Pitfall 7 (asar unpack), Linux glibc version mismatch.

**Research flag:** Standard patterns. Code signing setup may need additional research only if an EV certificate is obtained.

---

### Phase Ordering Rationale

- SQLite before PyInstaller: PostgreSQL-specific types cause runtime errors inside the bundle masked during Python dev mode. Fix at source and verify with unit tests before packaging.
- PyInstaller before Electron: Isolates the two hardest failure modes (hidden imports, path resolution) to a phase with one variable. Once the binary is proven on a clean VM, Electron integration is additive plumbing.
- Electron shell before packaging: electron . dev mode and packaged build differ only in asar. Building shell in dev mode confirms all IPC and subprocess logic; packaging phase adds only asar/installer wrapping.
- No phase requires backtracking: each phase leaves a runnable, testable artifact the next phase builds on.

### Research Flags

**Phases with standard implementation (no additional research required):**
- Phase 1 (SQLite migration): ARCHITECTURE.md provides exact code patterns for all type replacements and path functions
- Phase 3 (Electron shell): IPC, contextBridge, subprocess lifecycle are mature, stable Electron APIs
- Phase 4 (Packaging): electron-builder NSIS/AppImage targets are thoroughly documented

**Phases where one iteration may be needed after first test:**
- Phase 2 (PyInstaller): hiddenimports list covers known deps; LLM client transitive imports should be verified against actual installed requirements on first clean-VM test
---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against npm registry and PyPI; compatibility matrix confirmed via Context7 (Electron, electron-builder, SQLAlchemy, electron-store) |
| Features | HIGH | Patterns from stable Electron app UX conventions (Ollama, Cursor, DBeaver); IPC APIs stable since Electron 12 |
| Architecture | HIGH | Health-poll gate, userData isolation, programmatic Alembic, dynamic API base are well-established; code snippets verified against existing codebase |
| Pitfalls | HIGH | 9 of 11 pitfalls identified via direct codebase inspection of actual CTRX files; 2 (AV quarantine, hidden imports) from documented PyInstaller ecosystem issues |

**Overall confidence:** HIGH

### Gaps to Address

- **electron-store v11 ESM caveat:** Determine module format of electron/main.ts at start of Phase 3. If CommonJS, pin electron-store to v10.
- **LLM transitive hidden imports:** Run packaged binary against a real LLM call during Phase 2 smoke testing; the hiddenimports list may need one iteration for openai SDK or httpx internals.
- **Linux glibc compatibility:** Build on ubuntu:22.04 Docker container for the Linux CI job to ensure glibc 2.35 compatibility; verify against target Debian/Ubuntu versions.
- **Code signing for Windows:** Acceptable to skip for internal distribution to known machines. If SmartScreen blocks end users, an EV code signing certificate is the only complete fix.

---

## Sources

### Primary (HIGH confidence)

- Context7 /electron/electron -- app.getPath, isPackaged, IPC (ipcMain.handle, contextBridge), BrowserWindow.loadFile, child process spawn
- Context7 /electron-userland/electron-builder -- NSIS target, AppImage target, extraResources, asarUnpack
- Context7 /sindresorhus/electron-store -- store.get, store.set, schema, ESM-only note
- Context7 /websites/sqlalchemy_en_20 -- sa.JSON SQLite behavior, GUID TypeDecorator pattern, sqlite+aiosqlite dialect
- PyPI pip index versions pyinstaller -- confirmed 6.20.0 latest stable
- npm show electron version -- confirmed 42.3.0 latest stable
- npm show electron-builder version -- confirmed 26.8.1 latest stable
- Direct codebase inspection: backend/app/models/contract_file.py, alembic/versions/001-007, backend/app/config.py, backend/app/services/upload_service.py, frontend/src/api/client.ts

### Secondary (MEDIUM confidence)

- PyInstaller hidden imports list -- compiled from FastAPI/pydantic/uvicorn packaging issues (PyInstaller GitHub issues #4629, #6912 and community reports); needs clean-VM validation pass
- SQLite ALTER TABLE DROP COLUMN compatibility -- SQLite release notes (3.35.0, 2021-03-12); batch_alter_table workaround from Alembic docs

### Tertiary (LOW confidence -- validate during implementation)

- Linux AppImage glibc compatibility -- based on general Linux packaging knowledge; verify with actual CI runner and target OS versions
- electron-store ESM vs CJS decision -- depends on final electron/main.ts module format; resolve at Phase 3 start

---
*Research completed: 2026-05-28*
*Ready for roadmap: yes*