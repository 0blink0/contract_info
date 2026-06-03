---
phase: CTRX-23-pyinstaller
plan: "03"
subsystem: infra
tags: [electron, backendChildEnv, extraResources, env-injection, packaging, kb-pkg-02, d-08, d-09, d-12]

requires:
  - phase: CTRX-23-pyinstaller
    plan: "01"
    provides: bge-m3 model at electron/resources/models/bge-m3/
  - phase: CTRX-23-pyinstaller
    plan: "02"
    provides: hiddenimports extended for lancedb/sentence-transformers pipeline

provides:
  - backendChildEnv() injects CTRX_MODELS_DIR + SENTENCE_TRANSFORMERS_HOME + TRANSFORMERS_CACHE (all -> resourcesDir/models)
  - bootstrap() D-08 fast-fail guard for missing bge-m3 directory
  - package.json extraResources filter includes models/** for electron-builder bundling

affects:
  - electron/main.ts
  - electron/store.ts
  - package.json

tech-stack:
  added: []
  patterns:
    - three-candidate resourcesDir resolution (dev / app-path / packed) duplicated inside backendChildEnv()
    - ...process.env spread-first pattern for env override (D-12)
    - D-08 fast-fail guard with Chinese error message in bootstrap()

key-files:
  created: []
  modified:
    - electron/main.ts
    - electron/store.ts
    - package.json

decisions:
  - backendChildEnv() duplicates three-candidate resourcesDir resolution independently from backendEntrypoint() — avoids coupling exe-path logic with env-path logic
  - ...process.env spread is first in return object so explicit keys (CTRX_MODELS_DIR etc.) always override system env (D-12)
  - D-08 guard uses bootstrapResourcesCandidates (same three-candidate logic) to derive bgem3Path — no hardcoded paths (D-11)
  - Option A (append to existing filter array) chosen for package.json — minimal delta, no new extraResources entry

metrics:
  duration: "~10 minutes"
  completed: "2026-06-03"
  tasks_completed: 2
  files_modified: 3
---

# Phase 23 Plan 03: Electron 模型 env 注入与 extraResources 扩展 Summary

**One-liner:** backendChildEnv() 注入三个模型路径 env var、bootstrap() 增加 bge-m3 目录存在性快速失败守卫、package.json extraResources filter 追加 models/**

## What Was Built

### Task 1: backendChildEnv() env 注入 + D-08 守卫 (electron/main.ts)

`electron/main.ts` 做了两处修改：

**修改 1 — backendChildEnv() 扩展 (D-09, D-10, D-11, D-12)**

在 `backendChildEnv()` 内部复制三候选 `resourcesDir` 解析逻辑（与 `backendEntrypoint()` 相同的模式），导出 `modelsDir = path.join(resourcesDir, 'models')`，并在 return 对象中追加三个 env var：

```typescript
CTRX_MODELS_DIR: modelsDir,
SENTENCE_TRANSFORMERS_HOME: modelsDir,
TRANSFORMERS_CACHE: modelsDir,
```

`...process.env` spread 保持在 return 对象的第一位，确保显式键覆盖系统环境变量（D-12）。

由于 `backendChildEnv()` 被 `spawnBackend()` 调用，`spawnBackend()` 又被 `bootstrap()` 和 `scheduleRestart()` 调用，每次后端启动和重启都能收到这三个变量（D-10 满足）。

**修改 2 — D-08 快速失败守卫 (bootstrap())**

在 `bootstrap()` 中 `spawnBackend(port)` 调用之前，插入 bge-m3 目录存在性检查：

```typescript
const bgem3Path = path.join(bootstrapResourcesDir, 'models', 'bge-m3')
if (!fs.existsSync(bgem3Path)) {
  lastError = {
    summary: `模型目录缺失: ${bgem3Path} — 请重新安装应用以恢复模型权重`,
    logPath: backendLogPath(),
  }
  setBackendState('failed')
  await showFatalDialog()
  return
}
```

### Task 2: package.json extraResources filter 扩展

将 `"models/**"` 追加到现有 `extraResources[0].filter` 数组：

```json
"filter": [
  "ctrx-backend-*/**",
  "ctrx-backend-*",
  ".backend-manifest.json",
  "models/**"
]
```

`from`/`to` 均为 `"electron/resources"`，`models/**` glob 匹配 `electron/resources/models/bge-m3/` 及其全部内容，electron-builder 打包时将其注入至安装包的 `resources/electron/resources/models/bge-m3/` 路径（D-05 满足）。

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | `12a5907` | feat(23-03): extend backendChildEnv() with model env vars and add D-08 guard |
| Task 2 | `c518477` | feat(23-03): add models/** to extraResources filter for electron-builder bundling |

## Verification Results

- `npx tsc --noEmit -p tsconfig.electron.json` — EXIT 0 (no type errors)
- `grep -n "CTRX_MODELS_DIR" electron/main.ts` — 1 line in backendChildEnv return, 0 in bgem3Path derivation (derivation uses `models/bge-m3` path directly)
- `grep -n "SENTENCE_TRANSFORMERS_HOME"` — 1 line (return object)
- `grep -n "TRANSFORMERS_CACHE"` — 1 line (return object)
- `grep -n "模型目录缺失"` — 1 line (D-08 guard)
- `...process.env` at line 127, `CTRX_MODELS_DIR` at line 135 — spread-first order confirmed
- `package.json` filter array length: 4 entries, `models/**` present, `extraResources` array length: 1

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 修复 electron/store.ts 既有 TypeScript 严格模式错误**

- **发现于：** Task 1 TypeScript 类型检查阶段
- **问题：** `AppSettings.ragTopK` 为可选字段（`ragTopK?: number`），TypeScript 6.x 严格模式在 `validateSettings()` 第 40-41 行对其算术比较时报 TS18048（`'input.ragTopK' is possibly 'undefined'`）。此错误在本计划之前已存在，但阻断了 `tsc --noEmit` 验收标准
- **修复：** 在 `if (!Number.isInteger(input.ragTopK))` 条件中前置 `input.ragTopK === undefined ||` 判断，使 undefined 值明确返回验证错误而非落入算术比较
- **修改文件：** `electron/store.ts` 第 40 行
- **提交：** 与 Task 1 同一提交（`12a5907`）

## Known Stubs

无 — 所有 env 变量均指向真实路径推导，无硬编码占位符。

## Threat Flags

T-23-05（CTRX_MODELS_DIR 系统环境变量覆盖）— 已通过 `...process.env` spread-first 模式缓解（D-12）。
T-23-06（D-08 守卫绕过）— 接受，本地桌面应用无需额外缓解。

## Self-Check: PASSED

- `electron/main.ts` 存在且包含 CTRX_MODELS_DIR / SENTENCE_TRANSFORMERS_HOME / TRANSFORMERS_CACHE / 模型目录缺失
- `electron/store.ts` 存在且第 40 行包含 undefined 检查
- `package.json` 存在且 extraResources[0].filter 包含 "models/**"
- 提交 `12a5907` 存在（Task 1）
- 提交 `c518477` 存在（Task 2）
