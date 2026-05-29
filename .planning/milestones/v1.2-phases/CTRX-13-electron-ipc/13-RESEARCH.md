# Phase 13: Electron 壳与 IPC - Research

**Researched:** 2026-05-28  
**Domain:** Electron main/preload IPC contract + Python subprocess orchestration  
**Confidence:** HIGH

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 启动采用严格阻塞模型：显示加载页，30 秒内健康检查通过后才进入主界面；超时直接错误弹窗并展示日志路径。
- **D-02:** 崩溃重试采用指数退避：第 1 次立即重启，第 2 次 2 秒，第 3 次 5 秒；3 次后停止并提示失败。
- **D-03:** 应用退出时执行先 `SIGTERM` 再等待 5 秒，超时后 `SIGKILL`，确保子进程不会残留。
- **D-04:** 三次失败后的错误弹窗默认展示“日志路径 + 最近错误摘要 + 一键重试”。
- **D-05:** `save-settings` / `load-settings` / `get-port` 统一返回 `Result` 结构：`{ ok, data, error }`。
- **D-06:** `save-settings` 使用严格字段校验：`llmBaseUrl` 必须合法 URL，`llmApiKey` 与 `llmModel` 必填。
- **D-07:** API Key 在界面默认掩码展示，可短暂显式查看；禁止在日志中打印明文 Key。
- **D-08:** 配置落盘固定为 `userData/config.json` 单文件（同时可由 electron-store v10 管理读写）。
- **D-09:** 当 `llmBaseUrl` 或 `llmApiKey` 任一为空时，强制进入 3 步向导，禁止直接进入主界面。
- **D-10:** 向导“连接测试”失败时不可完成，必须修正后才能进入主界面。
- **D-11:** 用户关闭向导时仍停留在向导流程，不提供绕过路径。
- **D-12:** 向导中断后下次启动应恢复到上次未完成步骤。
- **D-13:** Settings 保存后立即重启 Python 子进程，重启期间阻塞关键操作。
- **D-14:** 重启期间展示全局遮罩与“正在重连后端”状态提示。
- **D-15:** 若重启失败，回滚到旧配置并提示失败原因与日志路径。
- **D-16:** 修改 API Key 时保存前弹一次确认框，避免误改。

### Claude's Discretion
- 日志摘要字段长度与截断策略（建议 200-400 chars）。
- 重试与重连中的文案微调与国际化键名。
- Settings 重连遮罩的交互细节（是否允许最小化）。

### Deferred Ideas (OUT OF SCOPE)
- Linux clean 启动验证补跑（已在 Phase 12 标记 deferred，不阻塞 Phase 13 规划）。
- auto-update / 系统托盘 / keychain 仍保持 out-of-scope。

## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| ELEC-01 | 主进程生命周期：spawn -> `/health` 轮询（300ms, 30s）-> 健康后展示主窗口 -> 崩溃最多重试 3 次 -> 退出 TERM/KILL | 生命周期状态机、`app` 退出钩子、子进程清理与重试模式 |
| ELEC-02 | `contextBridge` + `ipcMain.handle` 暴露 `save/load/get-port`，使用 electron-store v10，配置字段固定 | IPC 合约设计、字段校验、持久化位置、CJS/ESM 兼容建议 |
| ELEC-03 | 首启或缺失凭证强制 3 步向导且禁止绕过 | 路由门禁策略、向导恢复策略、主界面封闭条件 |
| ELEC-04 | Settings 可改配置并触发后端重启，失败回滚旧配置；向导与 Settings 共用表单组件 | 共用 `LlmConfigForm` 模式、保存-重启-回滚事务流、UI 阻塞建议 |

## Summary

Phase 13 的关键不是“把 Electron 跑起来”，而是把**后端生命周期、IPC 合约、首启门禁、配置回滚**统一为可验证的状态机。现有代码已具备 Python 后端入口 `desktop_main.py`（环境注入 + 迁移 + uvicorn），但仓库尚无 Electron main/preload 与路由守卫实现，适合本阶段一次性落地。 [VERIFIED: codebase]

Electron 官方推荐的请求/响应 IPC 方案是 `ipcRenderer.invoke` + `ipcMain.handle`，并明确要求 preload 只暴露窄 API，不要把整个 `ipcRenderer` 直接暴露给 renderer。该模式与 D-05 的 `Result` 返回结构天然匹配。 [CITED: https://www.electronjs.org/docs/latest/tutorial/ipc] [CITED: https://www.electronjs.org/docs/latest/api/context-bridge]

配置持久化采用 `userData/config.json` 与 electron-store 可直接契合：electron-store 默认就是 `app.getPath('userData')/config.json` 且写入是原子写，适合“先持久化、再重启后端、失败可回滚”的事务流程。 [CITED: https://www.npmjs.com/package/electron-store]

**Primary recommendation:** 采用“主进程状态机 + preload 窄桥 + 路由门禁 + 保存重启回滚事务”的单一实现路径，不并行引入替代存储或替代 IPC 框架。 [VERIFIED: requirements/context]

## Project Constraints (from .cursor/rules/)

- 默认自动提交并推送 `master`（除非用户明确禁止）。 [VERIFIED: `contract_info/.cursor/rules/auto-commit-push.mdc`]
- 仅提交任务相关文件，不纳入 `.env`、密钥、本地产物。 [VERIFIED: `contract_info/.cursor/rules/auto-commit-push.mdc`]
- 涉及 export/extract 改动时运行相关 `pytest`。 [VERIFIED: `contract_info/.cursor/rules/auto-commit-push.mdc`]
- `.planning/` 文档状态应同步更新。 [VERIFIED: `contract_info/.cursor/rules/auto-commit-push.mdc`]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Python 子进程 spawn/health/retry/cleanup | Electron Main Process | Python Backend | 进程控制与退出钩子属于主进程职责 |
| `save-settings`/`load-settings`/`get-port` IPC | Preload + Main IPC Layer | Renderer | 安全边界在 preload，业务动作在 main |
| 首启向导门禁与路由阻断 | Frontend Router Layer | Main IPC Layer | 是否放行取决于配置状态，门禁执行在前端路由 |
| Settings 保存后后端重启 | Main Process | Frontend | 重启动作需主进程执行，前端仅触发与反馈 |
| 配置持久化与回滚 | Main Process Storage Layer | Frontend Form Layer | 文件落盘和回滚一致性只能由主进程保证 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---|---:|---|---|
| Electron | 42.3.0 | 桌面壳、主进程、preload、窗口生命周期 | 官方 API 覆盖生命周期与 IPC 需求 [VERIFIED: npm registry] [CITED: https://www.electronjs.org/docs/latest/tutorial/ipc] |
| electron-store | 10.1.0 (phase pin) | `userData/config.json` 持久化 | 与 D-08 一致，避免 v11 ESM-only 与 CJS 入口冲突 [VERIFIED: npm registry] [CITED: https://www.npmjs.com/package/electron-store] |
| Vue Router | 4.6.4 | 向导门禁与主界面路由控制 | 当前前端已使用，扩展成本最低 [VERIFIED: codebase] |

### Supporting

| Library | Version | Purpose | When to Use |
|---|---:|---|---|
| Node `child_process` | Node 22 built-in | spawn/kill Python 子进程 | 主进程管理后端生命周期 |
| Element Plus | 2.9.0 | 向导和设置表单 UI | 与现有前端视觉体系保持一致 [VERIFIED: codebase] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| electron-store v10 | electron-store v11+ | v11 是 ESM-only；若 main 仍为 CJS 将触发兼容成本 [CITED: https://www.npmjs.com/package/electron-store] |
| 手工 JSON 读写 | electron-store | 手工方案需自管 schema/原子写/跨进程变更监听，重复造轮子 |

**Installation:**
```bash
npm install electron@42.3.0 electron-store@10.1.0
```

**Version verification:**  
- `npm view electron version time --json` -> `42.3.0`, modified `2026-05-27` [VERIFIED: npm registry]  
- `npm view electron-store version time --json` -> latest `11.0.2` (published `2025-10-05`) [VERIFIED: npm registry]  
- `npm view electron-store@10 version time --json` -> `10.1.0` (published `2025-06-14`) [VERIFIED: npm registry]

## Architecture Patterns

### System Architecture Diagram

```text
App launch
  -> Electron main boots
     -> read persisted config (userData/config.json via electron-store)
     -> decide route gate target (wizard or app)
     -> spawn Python child (desktop_main)
     -> poll http://127.0.0.1:<port>/api/v1/health every 300ms (timeout 30s)
        -> healthy: create/show BrowserWindow + load renderer route
        -> timeout/crash: retry policy (0s, 2s, 5s; max 3)
           -> 3 failures: error dialog with log path + retry action

Renderer (Vue)
  -> preload exposes window.api.{saveSettings, loadSettings, getPort}
  -> router guard checks config completeness
     -> incomplete: force /onboarding/*
     -> complete: allow main routes

Settings save
  -> renderer calls saveSettings
  -> main validates + persists new config
  -> main restarts Python child and re-healthchecks
     -> success: commit new config + clear reconnect mask
     -> failure: rollback old config + report error/log path

App quit
  -> main handles before-quit/will-quit
  -> TERM child, wait 5s, KILL if still alive
```

### Recommended Project Structure

```text
electron/
├── main.ts                # child lifecycle + health poll + retry + restart/rollback
├── preload.ts             # contextBridge narrow API wrapper
├── store.ts               # schema + save/load helpers + transactional rollback
└── ipc.ts                 # ipcMain.handle channel registration

frontend/src/
├── components/LlmConfigForm.vue     # onboarding + settings shared form
├── views/OnboardingWizardView.vue   # 3-step wizard shell
├── views/SettingsView.vue           # settings page
├── router/index.ts                  # route guard (wizard gate)
└── stores/appBootstrap.ts           # preload bridge state (port/settings readiness)
```

### Pattern 1: 主进程子进程状态机
**What:** 将 `spawn -> health -> ready -> crash-retry -> fatal` 明确为状态机，而不是散落回调。  
**When to use:** 需要可重试、可观测、可回滚的本地后端托管。  
**Example:**
```typescript
type BackendState = 'idle' | 'starting' | 'healthy' | 'restarting' | 'failed' | 'stopped'

interface RetryPolicy {
  maxAttempts: 3
  backoffMs: [0, 2000, 5000]
}
```
Source: [VERIFIED: requirements/context]

### Pattern 2: preload 窄桥 + invoke/handle 合约
**What:** preload 暴露白名单 API，renderer 只能调用三条通道。  
**When to use:** contextIsolation 开启且需要请求-响应 IPC。  
**Example:**
```typescript
// preload
contextBridge.exposeInMainWorld('api', {
  saveSettings: (payload) => ipcRenderer.invoke('save-settings', payload),
  loadSettings: () => ipcRenderer.invoke('load-settings'),
  getPort: () => ipcRenderer.invoke('get-port'),
})
```
Source: [CITED: https://www.electronjs.org/docs/latest/tutorial/ipc] [CITED: https://www.electronjs.org/docs/latest/api/context-bridge]

### Pattern 3: 门禁路由与共用表单
**What:** 用单一 `LlmConfigForm` 承载字段校验和提交协议；向导与 Settings 只负责流程容器。  
**When to use:** 同字段在首次配置和日常设置中重复出现且语义一致。  
**Example:**
```typescript
// router guard pseudo
if (!settings.llmBaseUrl || !settings.llmApiKey) return next('/onboarding/welcome')
next()
```
Source: [VERIFIED: requirements + codebase router baseline]

### Anti-Patterns to Avoid
- **直接在 renderer 暴露 `ipcRenderer`：** 扩大攻击面，违背 Electron 官方安全建议。 [CITED: https://www.electronjs.org/docs/latest/api/context-bridge]
- **保存配置后不做后端重启：** 与 ELEC-04“立即生效”冲突。 [VERIFIED: requirements]
- **在主进程日志输出明文 API Key：** 违背 D-07。 [VERIFIED: context]
- **重试策略无退避：** 容易形成崩溃风暴并导致误判不可恢复。 [VERIFIED: context]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| 配置原子写 | 手写 `fs.writeFile` 临时文件协议 | electron-store | 已提供原子写与 schema，减少损坏风险 [CITED: https://www.npmjs.com/package/electron-store] |
| 双向 IPC 应答模型 | `send/on` 自己拼 request-id | `ipcRenderer.invoke` + `ipcMain.handle` | 官方推荐，Promise 语义清晰 [CITED: https://www.electronjs.org/docs/latest/tutorial/ipc] |
| 路由门禁状态复制 | 向导和 Settings 各自维护表单规则 | 共享 `LlmConfigForm` + 单源校验 | 减少规则漂移，便于测试 |

**Key insight:** 本阶段复杂度主要在“状态一致性”，不是 API 数量；重复造轮子会直接增加一致性缺陷面。

## Common Pitfalls

### Pitfall 1: 退出时残留 Python 进程
**What goes wrong:** 窗口关闭后后端仍驻留，占用端口导致下次启动失败。  
**Why it happens:** 只监听窗口关闭，未在 `before-quit/will-quit` 做进程清理。  
**How to avoid:** 在 `app.quit()` 路径统一执行 TERM->5s->KILL。  
**Warning signs:** 下一次启动立即端口占用、`/health` 长时间拒绝连接。  
Source: [CITED: https://www.electronjs.org/docs/latest/api/app] [VERIFIED: requirements]

### Pitfall 2: IPC 合约漂移（前后端字段不一致）
**What goes wrong:** renderer 发送字段与 main 校验 schema 不一致，保存失败或静默丢失。  
**Why it happens:** 类型定义未集中、通道返回格式不统一。  
**How to avoid:** 三通道统一 `Result`，抽取共享 `SettingsPayload` 类型。  
**Warning signs:** 某些字段仅在向导可保存、Settings 保存后丢值。

### Pitfall 3: 设置保存成功但后端未真正生效
**What goes wrong:** UI 显示成功，实际请求仍使用旧 API Key/BaseURL。  
**Why it happens:** 缺少“保存后重启并重新健康确认”的事务步骤。  
**How to avoid:** 成功条件定义为“重启成功 + health 200 + 端口可达”，否则回滚。  
**Warning signs:** 保存后首次 LLM 请求认证失败但设置页显示已更新。  
Source: [VERIFIED: requirements/context]

## Code Examples

### IPC Result envelope
```typescript
type IpcResult<T> = { ok: true; data: T } | { ok: false; error: string }
```
Source: [VERIFIED: context D-05]

### 退出清理逻辑（主进程）
```typescript
app.on('before-quit', async (event) => {
  event.preventDefault()
  await stopBackendGracefully() // TERM -> wait 5s -> KILL
  app.exit(0)
})
```
Source: [CITED: https://www.electronjs.org/docs/latest/api/app] [VERIFIED: requirements]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| renderer 直接调用高权限 Electron API | preload `contextBridge` 暴露最小 API | Electron 安全基线长期实践 | 降低 XSS 扩权风险 [CITED: https://www.electronjs.org/docs/latest/api/context-bridge] |
| 手工 JSON 配置文件写入 | `electron-store` 原子写 + schema | 社区主流近几年稳定方案 | 降低配置损坏与校验缺失风险 [CITED: https://www.npmjs.com/package/electron-store] |

**Deprecated/outdated:**
- `electron-store` 最新版直接 `require()` 于 CJS main：不再可行（ESM-only）。 [CITED: https://www.npmjs.com/package/electron-store]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Phase 13 仍会采用 CJS 风格 Electron main 入口，因此继续 pin v10 最稳妥 | Standard Stack | 若 main 已迁移 ESM，可直接升级 v11，需调整建议 |
| A2 | 向导步骤状态建议持久化在同一配置文件中（例如 `onboardingStep`） | Architecture Patterns | 若团队不希望持久化进度，需改为每次从第 1 步开始 |

## Open Questions (RESOLVED)

1. **`save-settings` 回滚后 UI 值策略（RESOLVED）**
   - **Decision:** 主存储立即回滚旧配置；UI 默认回显旧值，并提供“使用失败值重试”快捷操作。
   - **Why:** 满足 D-15 的一致性要求，避免“界面值与生效值不一致”。

2. **Settings 重启期间阻塞边界（RESOLVED）**
   - **Decision:** 采用全局遮罩阻塞关键写操作（上传、运行任务、保存设置），允许只读浏览（列表与详情查看）。
   - **Why:** 满足 D-13/D-14 的安全重连要求，同时减少纯阅读场景的等待成本。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Node.js | Electron main/preload build/runtime | ✓ | v22.22.0 | — |
| npm | Electron dependency install | ✓ | 11.12.1 | — |
| Electron runtime | 本地开发运行 `electron .` | ✓ (via npx) | v42.3.0 | 项目本地安装 `electron` 依赖 |
| Python backend binary | main spawn target | ✓ | `electron/resources` manifest points `ctrx-backend-win-x64-v1.2.0` | 若缺失需先完成 Phase 12 产物落位 |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- electron 未本地安装为项目依赖时，可先用 `npx electron`，后续在 `package.json` 固化版本。 [VERIFIED: shell]

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest (backend) + Node test runner or Vitest (new for Electron layer) |
| Config file | `pytest.ini` (exists), Electron test config (none yet - Wave 0) |
| Quick run command | `pytest backend/tests/test_desktop_main.py -q -x` |
| Full suite command | `pytest backend/tests -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| ELEC-01 | spawn + health poll + retry + quit cleanup | integration (Electron main) | `npm run test:electron -- lifecycle` | ❌ Wave 0 |
| ELEC-02 | `save/load/get-port` IPC contract + payload validation | unit/integration | `npm run test:electron -- ipc` | ❌ Wave 0 |
| ELEC-03 | 首启向导门禁、未完成不可进主界面 | router unit + e2e smoke | `npm run test:router -- wizard-gate` | ❌ Wave 0 |
| ELEC-04 | Settings 保存后重启生效 + 失败回滚 | integration | `npm run test:electron -- settings-restart` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Electron quick subset + `pytest backend/tests/test_desktop_main.py -q -x`
- **Per wave merge:** Full Electron suite + `pytest backend/tests -q`
- **Phase gate:** `electron .` 冷启动烟测（加载页 -> 主界面） + Settings 改 Key 后成功请求一次 LLM 端点

### Wave 0 Gaps
- [ ] `electron/tests/lifecycle.spec.ts` - 覆盖 ELEC-01 状态机
- [ ] `electron/tests/ipc.spec.ts` - 覆盖 ELEC-02 合约与校验
- [ ] `frontend/src/router/__tests__/wizard-guard.spec.ts` - 覆盖 ELEC-03 门禁
- [ ] `electron/tests/settings-restart.spec.ts` - 覆盖 ELEC-04 回滚链路
- [ ] `frontend/package.json` scripts: `test:electron`, `test:router`

## Security Domain

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | 本阶段不新增用户身份认证 |
| V3 Session Management | no | 无会话系统 |
| V4 Access Control | yes | renderer 仅能访问 preload 白名单 API |
| V5 Input Validation | yes | `save-settings` main 侧严格 schema 校验 |
| V6 Cryptography | no | 不引入自定义加密；禁止手写“伪加密” |

### Known Threat Patterns for Electron + local backend

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| 过度暴露 IPC 导致权限提升 | Elevation of Privilege | preload 窄桥，不暴露完整 `ipcRenderer` |
| 明文日志泄露 API Key | Information Disclosure | 日志脱敏 + 禁止打印 key 原文 |
| 崩溃循环导致可用性下降 | Denial of Service | 指数退避 + 最大重试 3 次 + 明确失败态 |
| 配置写坏导致无法启动 | Tampering | 原子写 + schema 校验 + 回滚旧配置 |

## Risks and Rollback

### Top Risks
1. **R1: 子进程重启风暴**（端口冲突或配置错误导致连续崩溃）  
   Mitigation: 固定退避 + 最大 3 次 + 显示日志路径与手动重试。  
2. **R2: IPC 合约漂移**（renderer/main 类型不一致）  
   Mitigation: 单一 `types/ipc.ts` + 统一 `Result` 包装。  
3. **R3: 保存后“假成功”**（配置已写入但后端未生效）  
   Mitigation: 保存成功判定包含“重启后健康通过”，否则回滚。

### Rollback Plan
- 触发条件：Settings 保存后后端重启超时/崩溃达到上限。
- 回滚动作：
  1. 恢复旧配置快照到 `config.json`；
  2. 重新 spawn 后端并完成健康轮询；
  3. 弹窗提示失败原因与日志路径；
  4. 保持当前页面，允许用户修正后重试。

## Sources

### Primary (HIGH confidence)
- [Electron IPC tutorial](https://www.electronjs.org/docs/latest/tutorial/ipc) - `invoke/handle` 模式与 preload 窄桥建议。
- [Electron contextBridge API](https://www.electronjs.org/docs/latest/api/context-bridge) - contextIsolation 与桥接边界、安全限制。
- [Electron app API](https://www.electronjs.org/docs/latest/api/app) - `before-quit`/`will-quit`/`app.quit`/`app.exit` 生命周期语义。
- [electron-store npm docs](https://www.npmjs.com/package/electron-store) - `config.json` 位置、原子写、ESM/CJS注意事项。
- Project anchors: `desktop_main.py`, `frontend/src/main.ts`, `frontend/src/router/index.ts`, `frontend/src/layouts/AppLayout.vue`, `electron/resources/.backend-manifest.json`.

### Secondary (MEDIUM confidence)
- [Electron ESM tutorial](https://www.electronjs.org/docs/latest/tutorial/esm) - main/preload ESM 约束，支持 CJS/ESM决策。

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - npm registry + 官方文档 + 现有仓库约束一致。
- Architecture: HIGH - 上下游 phase context 与 requirements 已锁定关键决策。
- Pitfalls: MEDIUM - 部分来自工程经验归纳，但已映射到可执行验证项。

**Research date:** 2026-05-28  
**Valid until:** 2026-06-27
