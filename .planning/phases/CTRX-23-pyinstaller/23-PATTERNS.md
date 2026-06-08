# Phase 23: PyInstaller 打包兼容与烟测 - Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 8
**Analogs found:** 7 / 8 (1 no analog — new smoke-test doc format, uses Phase 12 template)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `ctrx_backend.spec` | config/build | batch | `ctrx_backend.spec` (Phase 12 baseline, same file) | exact |
| `electron/main.ts` | config/runtime | request-response | `electron/main.ts` `backendChildEnv()` (same file, extension) | exact |
| `package.json` | config/build | batch | `package.json` `build.extraResources` (same file, extension) | exact |
| `docs/packaging/hiddenimports-changelog.md` | config/docs | batch | `docs/packaging/hiddenimports-changelog.md` (same file, append entry) | exact |
| `docs/smoke-test-23.md` | docs | — | `docs/packaging/smoke-checklist-template.md` (Phase 12 template) | role-match |
| `.gitignore` | config | — | `.gitignore` (same file, append entry) | exact |
| `requirements.txt` | config/build | batch | `requirements.txt` (same file — lancedb/sentence-transformers already declared) | exact |
| `electron/resources/models/bge-m3/` | runtime asset | file-I/O | `electron/resources/ctrx-backend-win-x64-v1.2.0/` (same extraResources convention) | role-match |

---

## Pattern Assignments

### `ctrx_backend.spec` — hiddenimports 增量扩充

**Analog:** `ctrx_backend.spec` (lines 34–36 and 46–48 for the two extension hooks)

**Existing `windows_hidden` list** (lines 34–36):
```python
windows_hidden = [
    "colorama",
]
```
Extend by appending lancedb/pyarrow/sentence-transformers entries to this list, following D-01 (Windows-only) and D-02 (append to `windows_hidden`, not `common_hidden`).

**Existing optional-dep pattern** (lines 46–48):
```python
# Optional dependency chain: include only when installed.
if find_spec("openai") is not None:
    hiddenimports.extend(["openai", "openai._client"])
```
If the planner wants lancedb/sentence-transformers guarded by install-check, copy this `find_spec` guard. If they are required (not optional), append unconditionally to `windows_hidden`.

**Target extension** (D-01 minimal-increment strategy):
```python
windows_hidden = [
    "colorama",
    # --- Phase 23: lancedb / pyarrow / sentence-transformers ---
    "lancedb",
    "lancedb.remote",
    "lancedb.embeddings",
    "pyarrow",
    "pyarrow.vendored",
    "pyarrow.vendored.version",
    "sentence_transformers",
    "sentence_transformers.models",
    "sentence_transformers.util",
    "torch",
    "torch.utils",
    "torch.utils.data",
    "tokenizers",
    "transformers",
    "transformers.models",
    "transformers.models.bert",
    "transformers.models.xlm_roberta",
    "huggingface_hub",
    "huggingface_hub.file_download",
]
```
NOTE: Actual minimum set must be confirmed by `pyinstaller --debug=imports` after Wave 0 install (see RESEARCH.md Open Questions #3). The list above is the research-provided starting point; trim or extend based on actual import errors.

**Constraint from D-03 gate:** `windows_hidden` change in spec MUST be in the same commit as a changelog entry in `docs/packaging/hiddenimports-changelog.md` or `check_hiddenimports_diff.py` returns exit code 1 and blocks CI.

---

### `electron/main.ts` — `backendChildEnv()` env injection

**Analog:** `electron/main.ts` (same file)

**Exact current `backendChildEnv()` function** (lines 111–123):
```typescript
function backendChildEnv(port: number): NodeJS.ProcessEnv {
  const settings = loadSettings()
  const ragTopK = Number.isInteger(settings.ragTopK) ? settings.ragTopK : 3
  return {
    ...process.env,
    CTRX_PORT: String(port),
    CTRX_DATA_DIR: app.getPath('userData'),
    OPENAI_API_KEY: settings.llmApiKey.trim(),
    OPENAI_BASE_URL: settings.llmBaseUrl.trim(),
    LLM_MODEL: settings.llmModel.trim(),
    RAG_TOP_K: String(ragTopK),
  }
}
```

**`backendEntrypoint()` resourcesDir derivation pattern** (lines 47–54) — reuse to derive `modelsDir`:
```typescript
const resourcesCandidates = [
  path.join(__dirname, 'resources'),
  path.join(app.getAppPath(), 'electron', 'resources'),
  path.join(process.resourcesPath, 'electron', 'resources'),
]
const resourcesDir =
  resourcesCandidates.find((candidate) => fs.existsSync(path.join(candidate, '.backend-manifest.json'))) ??
  resourcesCandidates[0]
```
This three-candidate resolution (dev / app-path / packed) is the established pattern — DO NOT hardcode absolute paths (D-11).

**Phase 23 extension — inject three model env vars** (D-09, D-10, D-11, D-12):
```typescript
function backendChildEnv(port: number): NodeJS.ProcessEnv {
  const settings = loadSettings()
  const ragTopK = Number.isInteger(settings.ragTopK) ? settings.ragTopK : 3

  // Derive resourcesDir using same three-candidate logic as backendEntrypoint()
  const resourcesCandidates = [
    path.join(__dirname, 'resources'),
    path.join(app.getAppPath(), 'electron', 'resources'),
    path.join(process.resourcesPath, 'electron', 'resources'),
  ]
  const resourcesDir =
    resourcesCandidates.find((candidate) => fs.existsSync(path.join(candidate, '.backend-manifest.json'))) ??
    resourcesCandidates[0]
  const modelsDir = path.join(resourcesDir, 'models')

  return {
    ...process.env,           // spread FIRST — explicit keys below override system env (D-12)
    CTRX_PORT: String(port),
    CTRX_DATA_DIR: app.getPath('userData'),
    OPENAI_API_KEY: settings.llmApiKey.trim(),
    OPENAI_BASE_URL: settings.llmBaseUrl.trim(),
    LLM_MODEL: settings.llmModel.trim(),
    RAG_TOP_K: String(ragTopK),
    // Phase 23 additions (D-09)
    CTRX_MODELS_DIR: modelsDir,
    SENTENCE_TRANSFORMERS_HOME: modelsDir,
    TRANSFORMERS_CACHE: modelsDir,
  }
}
```

**D-08 model-directory existence check** — add a fast-fail guard before `spawnBackend()` call in `bootstrap()` (lines 307–327). Pattern:
```typescript
// In bootstrap(), before spawnBackend():
const modelsPath = path.join(resolvedResourcesDir, 'models', 'bge-m3')
if (!fs.existsSync(modelsPath)) {
  // fast-fail: show error and prevent backend spawn
  lastError = { summary: `模型目录缺失: ${modelsPath}`, logPath: backendLogPath() }
  setBackendState('failed')
  await showFatalDialog()
  return
}
```

**Caller chain confirmed** (lines 125–135, 307–327): `backendChildEnv()` is called only inside `spawnBackend()`, which is called from both `bootstrap()` and `scheduleRestart()` — satisfying D-10 (every spawn/restart gets the vars).

---

### `package.json` — `build.extraResources` models entry

**Analog:** `package.json` (same file)

**Exact current `extraResources` block** (lines 40–50):
```json
"extraResources": [
  {
    "from": "electron/resources",
    "to": "electron/resources",
    "filter": [
      "ctrx-backend-*/**",
      "ctrx-backend-*",
      ".backend-manifest.json"
    ]
  }
]
```

**Extension Option A — append `models/**` to existing filter** (RESEARCH.md Pattern 3, preferred for minimal delta):
```json
"extraResources": [
  {
    "from": "electron/resources",
    "to": "electron/resources",
    "filter": [
      "ctrx-backend-*/**",
      "ctrx-backend-*",
      ".backend-manifest.json",
      "models/**"
    ]
  }
]
```

**Extension Option B — separate entry** (if planner prefers explicit isolation):
```json
"extraResources": [
  {
    "from": "electron/resources",
    "to": "electron/resources",
    "filter": [
      "ctrx-backend-*/**",
      "ctrx-backend-*",
      ".backend-manifest.json"
    ]
  },
  {
    "from": "electron/resources/models",
    "to": "electron/resources/models",
    "filter": ["**/*"]
  }
]
```
Both are functionally equivalent; the planner chooses. Option A is one-line and follows minimal-increment D-01 spirit.

---

### `docs/packaging/hiddenimports-changelog.md` — Phase 23 entry

**Analog:** `docs/packaging/hiddenimports-changelog.md` (same file)

**Exact current content** (lines 1–7 — entire file):
```markdown
# hiddenimports changelog

## 2026-05-28

- Added initial `ctrx_backend.spec` hiddenimports baseline.
- Split hiddenimports by `common/windows/linux`.
- Locked excludes with explicit `psycopg2` removal.
```

**Phase 23 append pattern** — copy the `## YYYY-MM-DD` heading + bullet list format:
```markdown
## 2026-06-02

- Phase 23: Appended lancedb/pyarrow/sentence-transformers/torch/tokenizers/transformers/huggingface_hub
  entries to `windows_hidden` for KB embedding pipeline packaging (KB-PKG-01).
- Rationale: lancedb uses Rust extension (`lancedb._lib`) and pyarrow uses C extensions;
  static analysis cannot resolve all dynamic imports.
- Platform scope: Windows only (D-02); Linux deferred to next milestone.
```

**Gate requirement:** This append must be in the **same git commit** as the `windows_hidden` changes in `ctrx_backend.spec`. The `check_hiddenimports_diff.py` gate (see Shared Patterns below) compares both files against `origin/master` in a single diff run.

---

### `docs/smoke-test-23.md` — Phase 23 full-chain smoke checklist (NEW FILE)

**Analog:** `docs/packaging/smoke-checklist-template.md` (Phase 12 template)

**Phase 12 template structure to copy** (lines 1–52, full file):
- `## Execution Metadata` — executor, date, machine, OS, build version, backend binary path, `CTRX_DATA_DIR`
- `## Preconditions` — clean machine, binary present, input file prepared, data dir writable
- `## Smoke Chain` — ordered checklist steps
- `## Data Isolation` — verify writes go only to `CTRX_DATA_DIR`
- `## Evidence Collected` — commands, log paths, screenshots, verdict: PASS / FAIL

**Phase 23 additions to the template structure** (D-14 four-part pass criteria):
The Smoke Chain section must expand to cover the KB full chain. The four pass criteria from D-14:

1. `[ ] 后端启动日志无 ModuleNotFoundError（embedding 模型加载行可见）`
   — Log file location: `app.getPath('userData')/logs/backend.log` (verified: `backendLogPath()` in `electron/main.ts` line 43)
2. `[ ] PathB 页录入并提交后出现「已存入 N 条」ElMessage.success 提示`
3. `[ ] 知识库配置页刷新后可见该新录入条目`
4. `[ ] 重新处理一份含业绩报酬条款的合同后，后端日志包含 RAG context 或 few-shot 关键字`

**Precondition additions** (Phase 23 specific):
```
- [ ] 已安装打包产物（CTRX-Setup-1.4.0.exe）到无 Python 环境机器
- [ ] electron/resources/models/bge-m3/ 已就位（安装时由 extraResources 注入）
- [ ] 备有含业绩报酬条款的合同文件（用于第 4 项验证）
```

**Metadata additions**:
```
- CTRX_MODELS_DIR (injected):
- bge-m3 模型目录是否存在:
```

---

### `.gitignore` — exclude model weights directory

**Analog:** `.gitignore` (same file)

**Exact current content** (lines 1–17):
```gitignore
.venv/
__pycache__/
*.py[cod]
.env
uploads/*
!uploads/.gitkeep
exports/*
!exports/.gitkeep
.pytest_cache/
out.json
frontend/node_modules/
frontend/dist/
node_modules/
dist/
```

**Phase 23 append** — follow the same `dir/` trailing-slash pattern:
```gitignore
electron/resources/models/
```
This prevents the ~2.5GB bge-m3 weights from being accidentally committed. Place after the existing `dist/` line.

---

### `requirements.txt` — verify lancedb/sentence-transformers declared

**Analog:** `requirements.txt` (same file)

**Current relevant lines** (lines 14–15 — already present):
```
lancedb>=0.33.0
sentence-transformers>=5.5.1
```
`pyarrow` and `torch` are transitive dependencies installed automatically by the above; no explicit entries needed unless a version pin becomes necessary after Wave 0 testing. The file requires NO change unless version pins are added post Wave-0 audit.

---

### `electron/resources/models/bge-m3/` — model weights directory (Wave 0 asset)

**Analog:** `electron/resources/ctrx-backend-win-x64-v1.2.0/` (same extraResources tree)

This is a file-system directory, not a code file. The analog establishes the naming and placement convention. No code pattern to extract. Key facts:

- Created by Wave 0 script: `model.save('electron/resources/models/bge-m3')` (or equivalent `snapshot_download` + flatten)
- Must contain: `config.json`, `tokenizer.json`, `pytorch_model.bin` / `model.safetensors` (standard SentenceTransformer local-path format — NOT HuggingFace hub cache format)
- Referenced by `kb_service.py` line pattern: `model_path = Path(CTRX_MODELS_DIR) / "bge-m3"` → `SentenceTransformer(str(model_path), local_files_only=True)`
- Excluded from git via `.gitignore` entry above
- Wave 0 download script pattern from `backend/app/config.py` `models_dir()` (lines 88–93) — consumes `CTRX_MODELS_DIR` env var

---

## Shared Patterns

### Environment variable injection override (D-12)

**Source:** `electron/main.ts` `backendChildEnv()` lines 114–115
**Apply to:** `electron/main.ts` Phase 23 extension
```typescript
return {
  ...process.env,  // spread FIRST
  CTRX_PORT: ...,  // explicit keys AFTER spread — these WIN over system env
  ...
}
```
JavaScript object spread semantics: later keys override earlier ones. `{ ...process.env, KEY: value }` guarantees the explicit `KEY` wins even if `process.env.KEY` already exists. This satisfies D-12 for `TRANSFORMERS_CACHE` / `SENTENCE_TRANSFORMERS_HOME`.

---

### hiddenimports CI gate

**Source:** `.github/workflows/backend-packaging-gate.yml` (full file, 37 lines) + `scripts/check_hiddenimports_diff.py`
**Apply to:** Any commit that modifies `ctrx_backend.spec` hiddenimports

Gate command (verified from workflow lines 33–36):
```bash
python scripts/check_hiddenimports_diff.py \
  --base origin/master \
  --spec ctrx_backend.spec \
  --changelog docs/packaging/hiddenimports-changelog.md
```

Gate logic (from `check_hiddenimports_diff.py` lines 78–86):
```python
if hidden_changed and not changelog_changed:
    print("hiddenimports changed in spec but changelog was not updated: ...")
    return 1
```
Watched tokens that trigger `hidden_changed` (line 57–63): `common_hidden`, `windows_hidden`, `linux_hidden`, `hiddenimports`.

**Rule:** Spec change + changelog change must be in the **same commit** relative to `origin/master`.

---

### `data_dir()` / `models_dir()` env-var consumption pattern (backend)

**Source:** `backend/app/config.py` lines 22–33 (`data_dir`) and 88–93 (`models_dir`)
**Apply to:** Wave 0 model download script (should call `models_dir()` to derive target path in dev mode)

```python
def data_dir() -> Path:
    raw = os.environ.get("CTRX_DATA_DIR", "").strip()
    if raw:
        p = Path(raw)
        p.mkdir(parents=True, exist_ok=True)
        return p
    return PROJECT_ROOT

def models_dir() -> Path | None:
    raw = os.environ.get("CTRX_MODELS_DIR", "").strip()
    if raw:
        return Path(raw)
    return None
```
Pattern: `os.environ.get("VAR", "").strip()` then `Path(raw)` — no default path for models (returns `None` if unset). The `data_dir()` pattern adds `mkdir(parents=True, exist_ok=True)` — models_dir does NOT mkdir (model dir is pre-populated at build time, not created at runtime).

---

### Manifest-based resourcesDir resolution (Electron)

**Source:** `electron/main.ts` `backendEntrypoint()` lines 47–54
**Apply to:** `backendChildEnv()` Phase 23 extension for `modelsDir` derivation

```typescript
const resourcesCandidates = [
  path.join(__dirname, 'resources'),                         // dev: next to main.ts
  path.join(app.getAppPath(), 'electron', 'resources'),      // packaged fallback
  path.join(process.resourcesPath, 'electron', 'resources'), // electron-builder packed
]
const resourcesDir =
  resourcesCandidates.find((candidate) =>
    fs.existsSync(path.join(candidate, '.backend-manifest.json'))
  ) ?? resourcesCandidates[0]
```
The manifest sentinel (`.backend-manifest.json`) is what `package_backend.ps1` writes (lines 34–43 of that script). The same sentinel can anchor `modelsDir = path.join(resourcesDir, 'models')`.

---

### `package_backend.ps1` copy pattern (build pipeline)

**Source:** `scripts/package_backend.ps1` lines 11–16 and 28–32
**Apply to:** Wave 0 model copy step (planner may add a step to `package_backend.ps1` or a sibling script)

```powershell
$ResourcesDir = Join-Path $Root "electron/resources"
$TargetDir = Join-Path $ResourcesDir $TargetName

New-Item -ItemType Directory -Path $ResourcesDir -Force | Out-Null
if (Test-Path $TargetDir) {
  Remove-Item -Path $TargetDir -Recurse -Force
}
Copy-Item -Path $DistDir -Destination $TargetDir -Recurse -Force
```
Follow the same `New-Item -Force` + `Copy-Item -Recurse` pattern to place bge-m3 weights into `electron/resources/models/bge-m3/`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `docs/smoke-test-23.md` (KB chain section) | docs | — | Phase 12 template covers basic API chain; KB embedding + LanceDB + RAG path is new; planner must write new checklist steps from D-14 criteria |

---

## Metadata

**Analog search scope:** `electron/main.ts`, `ctrx_backend.spec`, `package.json`, `requirements.txt`, `docs/packaging/`, `scripts/`, `backend/app/config.py`, `backend/app/services/kb_service.py`, `.gitignore`, `.github/workflows/backend-packaging-gate.yml`
**Files scanned:** 13
**Pattern extraction date:** 2026-06-02
