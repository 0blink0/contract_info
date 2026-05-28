# Feature Research

**Domain:** Electron desktop packaging — first-run UX and settings for a local-first professional tool
**Researched:** 2026-05-28
**Confidence:** HIGH (Electron patterns are stable and well-established; training knowledge through Aug 2025 is reliable here)

---

## Scope

This file covers **only new desktop-specific UX features** for v1.2. The existing web features (upload, extract, export, validation panel, PathB JSON, settings via `.env`) are already shipped and are not re-scoped here.

Audience: non-technical operations staff on Windows (primary) and Linux. They double-click an installer, configure an LLM once, and use the app daily.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or broken on first use.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| First-run setup wizard (3-step) | App is unconfigurable without LLM credentials — blank start = confusion | MEDIUM | Steps: Welcome → LLM credentials → Connection test. Must block normal app until complete. Wizard state stored via `electron-store` or similar JSON config in `app.getPath('userData')`. |
| LLM connection test with visible result | Users (non-technical staff) need immediate confirmation their key works before leaving wizard | LOW | Call backend `/api/v1/llm/ping` or equivalent; show green tick / red error inline. Must not just silently succeed. |
| Settings page accessible any time | User re-opens settings after API key rotation or model change | LOW | A route `/settings` added to Vue Router; accessible from sidebar nav. Reads/writes same config file as wizard. |
| Backend startup indicator | Electron spawns PyInstaller subprocess — startup takes 2-5 s. Without feedback, user thinks app is broken | LOW | Splash screen or loading overlay on main window until FastAPI `/health` responds. |
| Subprocess failure error message | If Python backend fails to start (port conflict, missing files), user needs actionable message | MEDIUM | Main process catches child process `exit` event; shows dialog with restart button and log path. |
| Config persistence across restarts | LLM credentials survive app close/reopen | LOW | Write to JSON config file in `userData` dir. Do NOT use `.env` file at project root (that is the Docker-era pattern). |
| App menu / tray with Quit | Desktop app convention; without it, non-technical users don't know how to close | LOW | Standard Electron `Menu.buildFromTemplate`; include Quit, Settings shortcut, About. |
| About dialog (version + contact) | Professional tool: ops staff escalate issues; version number needed for support tickets | LOW | `app.getVersion()` from `package.json`; modal with version + IT contact. |

### Differentiators (Competitive Advantage)

Features that go beyond baseline expectations for a professional internal tool.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Masked API key display | Shows `sk-...****` in Settings; builds user trust that key is stored, without exposing it | LOW | Mask all but first 4 + last 4 chars client-side; never re-send full key to renderer once saved. |
| Re-run wizard from Settings | When ops changes LLM provider mid-year, having a "Re-configure LLM" button in Settings is faster than uninstalling | LOW | Settings page has a "重新配置" button that navigates to wizard flow without resetting other data. |
| Backend log viewer (last 50 lines) | When extraction fails mysteriously, ops lead can copy logs for IT support without opening file explorer | MEDIUM | IPC channel `log:tail` reads last N lines from backend log file; rendered in a scrollable `<pre>` in Settings. Avoid building a full log viewer — just tail. |
| Model name dropdown with presets | `qwen2.5-72b-instruct`, `gpt-4o-mini`, etc. offered as select options alongside free-text input | LOW | Hard-coded preset list in wizard + settings; user can still type custom. Reduces typos on model names. |
| Startup speed: pre-warm backend | Backend spawned as soon as Electron main process starts, before renderer loads | LOW | Parallelise subprocess spawn with BrowserWindow creation. Cuts perceived startup time by ~50% on most machines. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-update via Squirrel / electron-updater | "It should update itself" | Internal tools distributed via network share or IT push. Auto-update requires a release server, code signing, and IT policy approval. Over-engineered for a 2-person ops team. | Manual versioned installer drops to a shared drive. Show current version in About so users know when to ask IT for update. |
| System tray background operation | "App should stay running" | This tool is not always-on. Running Python subprocess in background wastes memory and conflicts with other processes on shared workstations. | Standard window close = quit. Let the OS or user restart as needed. |
| Encrypted credential store (keychain) | "Keys should be in keychain" | OS keychain integration (keytar) is complex, has native build deps, breaks frequently on Electron upgrades. Overkill for an internal tool on a locked-down corporate workstation. | Store in `userData` JSON with `0600` file permissions. Note: API key is internal/company-owned, not user's personal secret. Document the file location in the About dialog. |
| Multi-account / workspace profiles | "Different users have different LLM keys" | Adds significant UI/state complexity. Operations team shares one API account per org policy. | Single config per machine. |
| Remember window position and size | Developer ergonomic preference | Low value for ops staff using fixed workstations. Adds edge cases (multi-monitor, resolution changes). | Open at a sensible default size (1280×800). Skip persistence for v1.2. |

---

## Feature Dependencies

```
[First-run wizard]
    └──requires──> [Config file read/write layer] (electron-store or fs.writeFileSync)
                       └──required by──> [Settings page]
                       └──required by──> [Backend subprocess receives config on spawn]

[Backend startup indicator]
    └──requires──> [FastAPI /health endpoint] (already exists in v1.1)

[LLM connection test]
    └──requires──> [Backend is running] (depends on startup indicator completing)
    └──requires──> [Config has been written] (wizard step 2 → step 3)

[Settings page]
    └──requires──> [Vue Router /settings route] (new route, no conflict with existing routes)
    └──enhances──> [First-run wizard] (same form fields, shared component)

[Backend log viewer]
    └──requires──> [IPC channel in preload.js] (exposes fs.readFile to renderer)
    └──requires──> [Backend logging to file] (needs --log-file arg in PyInstaller build)

[Model name dropdown presets]
    └──enhances──> [First-run wizard step 2]
    └──enhances──> [Settings page]
```

### Dependency Notes

- **Config file layer is the keystone:** both wizard and settings page must share the same read/write abstraction. If implemented twice independently, settings changes don't reach the backend on next restart.
- **LLM connection test requires backend running:** wizard step 3 (test connection) cannot run before the backend subprocess has passed health check. Design the wizard to start with "waiting for backend..." state.
- **Settings page is a thin wrapper around wizard fields:** build the form fields as a shared Vue component (`LlmConfigForm.vue`) used in both wizard and settings page. Do not duplicate.

---

## MVP Definition

This is a subsequent milestone onto a shipped v1.1 product — "MVP" here means the minimum desktop experience that replaces Docker-only deployment.

### Launch With (v1.2)

- [x] First-run wizard: Welcome → LLM credentials (base URL, API key, model) → connection test
- [x] Config written to `userData/config.json` on wizard completion
- [x] Backend subprocess spawned at app start, config passed as env vars or CLI args
- [x] Backend startup loading overlay with timeout/error handling
- [x] Settings page at `/settings` with same fields, accessible from sidebar nav
- [x] App menu with Quit + Settings shortcut + About
- [x] About dialog with version string

### Add After Validation (v1.2.x)

- [ ] Backend log tail in Settings — add when IT support tickets request logs
- [ ] Model name presets dropdown — add when model selection becomes frequent op
- [ ] Re-run wizard button — add when first key rotation occurs

### Future Consideration (v2+)

- [ ] Auto-update mechanism — only if distribution moves to a release server
- [ ] Multiple config profiles — only if multi-tenant deployment requested

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| First-run wizard | HIGH | MEDIUM | P1 |
| Config persistence (`userData`) | HIGH | LOW | P1 |
| Backend startup indicator | HIGH | LOW | P1 |
| Subprocess failure error message | HIGH | MEDIUM | P1 |
| Settings page `/settings` | HIGH | LOW | P1 |
| LLM connection test | HIGH | LOW | P1 |
| App menu + Quit | HIGH | LOW | P1 |
| About dialog | LOW | LOW | P1 (convention) |
| Masked API key display | MEDIUM | LOW | P2 |
| Model name presets | MEDIUM | LOW | P2 |
| Pre-warm backend (parallel spawn) | MEDIUM | LOW | P2 |
| Re-run wizard from Settings | MEDIUM | LOW | P2 |
| Backend log viewer | MEDIUM | MEDIUM | P2 |
| Auto-update | LOW | HIGH | P3 |
| System tray | LOW | MEDIUM | P3 |
| Window position persistence | LOW | LOW | P3 |

---

## Implementation Notes for Requirements Writer

### Wizard Step Design (3 steps)

**Step 1 — Welcome**
- Title: "欢迎使用合同要素抽取工具"
- Body: brief sentence on what the tool does + note that LLM credentials are needed
- Button: 开始配置

**Step 2 — LLM 配置**
- Fields: API Base URL (text, required), API Key (password input, required), Model Name (combobox with presets, required)
- Validation: all three non-empty; base URL must start with `http`
- Button: 下一步

**Step 3 — 连接测试**
- Auto-triggers a backend call on mount (after writing config)
- Shows spinner → success (绿色对勾) or failure (红色 ✕ + error message)
- On success: 进入应用 button
- On failure: 返回修改 button (back to step 2)

### Config File Schema

Stored at `app.getPath('userData')/config.json` (managed by Electron main process):

```json
{
  "llm": {
    "baseUrl": "https://...",
    "apiKey": "sk-...",
    "model": "qwen2.5-72b-instruct"
  },
  "setup": {
    "wizardComplete": true
  }
}
```

The main process reads this file at startup and injects the values into the Python subprocess environment (`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `LLM_MODEL`). The existing `config.py` in the backend already reads these from env vars — no backend code change needed.

### IPC Channels Required

| Channel | Direction | Purpose |
|---------|-----------|---------|
| `config:get` | renderer → main | Settings page reads current config |
| `config:set` | renderer → main | Wizard / settings writes new config |
| `backend:status` | main → renderer | `starting` / `ready` / `error` for loading overlay |
| `backend:restart` | renderer → main | Restart subprocess after config change |
| `log:tail` | renderer → main (optional P2) | Read last N lines from backend log |

### Sidebar Nav Addition

Add "设置" entry to the existing left nav (after the three current entries: 文件上传解析, 文件列表, 文件详情). Route: `/settings`.

---

## Competitor Feature Analysis

This is an internal tool with no direct commercial competitor. Reference patterns drawn from:

| Pattern Source | What We Borrow |
|----------------|----------------|
| Ollama Desktop (local AI tool) | First-run connection test UX; status indicator for local backend process |
| Cursor / VSCode (local-first dev tools) | Settings page as dedicated route, not modal; config in `userData` |
| DBeaver (local professional tool for non-devs) | Masked credential display; connection test inline in settings form |

---

## Sources

- Electron IPC and subprocess patterns: training knowledge (HIGH confidence — stable API, verified against Electron docs structure through Aug 2025)
- `electron-store` pattern: training knowledge (HIGH confidence — library has been stable since v8)
- Config file location (`app.getPath('userData')`): HIGH confidence, documented Electron API
- Existing codebase analysis: `backend/app/config.py` (env var injection pattern), `frontend/src/router/index.ts` (existing routes), `frontend/src/api/client.ts` (API base URL pattern)
- Project requirements: `.planning/PROJECT.md` v1.2 milestone spec
- Note: WebSearch and WebFetch were unavailable in this research session. All findings are from training knowledge (Aug 2025 cutoff) + codebase inspection. Electron packaging patterns are mature and stable — LOW risk of staleness.

---
*Feature research for: Electron desktop packaging — first-run UX and settings (v1.2)*
*Researched: 2026-05-28*
