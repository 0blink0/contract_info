# Phase 13: Electron 壳与 IPC - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

交付 Electron 桌面壳与 IPC：主进程负责 Python 子进程生命周期、健康轮询与崩溃重试；通过 contextBridge 暴露配置读写与端口查询；在配置缺失时强制首启向导，在 Settings 保存后重启后端并立即生效。

本阶段不扩展新业务功能（如 auto-update、托盘、批量处理、鉴权）。

</domain>

<decisions>
## Implementation Decisions

### 子进程生命周期与故障恢复
- **D-01:** 启动采用严格阻塞模型：显示加载页，30 秒内健康检查通过后才进入主界面；超时直接错误弹窗并展示日志路径。
- **D-02:** 崩溃重试采用指数退避：第 1 次立即重启，第 2 次 2 秒，第 3 次 5 秒；3 次后停止并提示失败。
- **D-03:** 应用退出时执行先 `SIGTERM` 再等待 5 秒，超时后 `SIGKILL`，确保子进程不会残留。
- **D-04:** 三次失败后的错误弹窗默认展示“日志路径 + 最近错误摘要 + 一键重试”。

### IPC 与配置持久化
- **D-05:** `save-settings` / `load-settings` / `get-port` 统一返回 `Result` 结构：`{ ok, data, error }`。
- **D-06:** `save-settings` 使用严格字段校验：`llmBaseUrl` 必须合法 URL，`llmApiKey` 与 `llmModel` 必填。
- **D-07:** API Key 在界面默认掩码展示，可短暂显式查看；禁止在日志中打印明文 Key。
- **D-08:** 配置落盘固定为 `userData/config.json` 单文件（同时可由 electron-store v10 管理读写）。

### 首次启动向导门禁
- **D-09:** 当 `llmBaseUrl` 或 `llmApiKey` 任一为空时，强制进入 3 步向导，禁止直接进入主界面。
- **D-10:** 向导“连接测试”失败时不可完成，必须修正后才能进入主界面。
- **D-11:** 用户关闭向导时仍停留在向导流程，不提供绕过路径。
- **D-12:** 向导中断后下次启动应恢复到上次未完成步骤。

### Settings 保存后的重启体验
- **D-13:** Settings 保存后立即重启 Python 子进程，重启期间阻塞关键操作。
- **D-14:** 重启期间展示全局遮罩与“正在重连后端”状态提示。
- **D-15:** 若重启失败，回滚到旧配置并提示失败原因与日志路径。
- **D-16:** 修改 API Key 时保存前弹一次确认框，避免误改。

### Claude's Discretion
- 日志摘要字段长度与截断策略（建议 200-400 chars）。
- 重试与重连中的文案微调与国际化键名。
- Settings 重连遮罩的交互细节（是否允许最小化）。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 路线与需求
- `contract_info/.planning/ROADMAP.md` — Phase 13 目标、依赖与成功标准。
- `contract_info/.planning/REQUIREMENTS.md` — ELEC-01..04 的硬性约束。
- `contract_info/.planning/PROJECT.md` — v1.2 桌面化目标与 out-of-scope 边界。
- `contract_info/.planning/STATE.md` — 当前执行状态与阶段衔接。

### 上游阶段（直接依赖）
- `contract_info/.planning/phases/CTRX-12-pyinstaller/12-CONTEXT.md` — 后端打包入口、资源布局、启动边界。
- `contract_info/.planning/phases/CTRX-12-pyinstaller/12-01-SUMMARY.md` — PyInstaller/spec/packaging 实际落地情况。
- `contract_info/.planning/phases/CTRX-12-pyinstaller/12-02-SUMMARY.md` — Windows 烟测通过与 Linux 验证延期说明。

### 代码锚点
- `contract_info/desktop_main.py` — Python 后端入口与启动链。
- `contract_info/frontend/src/main.ts` — Vue 应用挂载入口（后续与 preload 注入联动）。
- `contract_info/frontend/src/router/index.ts` — 现有路由结构（向导与主界面路由门禁接入点）。
- `contract_info/electron/resources/.backend-manifest.json` — 打包后端资源目录索引（主进程定位 backend 二进制）。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `desktop_main.py` 已具备环境注入、迁移、服务启动链，可直接由 Electron spawn。
- `frontend/src/router/index.ts` 已有上传/列表/详情三路由，可扩展向导路由与门禁逻辑。
- `frontend/src/components` 现有 Element Plus 组件体系可复用在向导与 Settings 表单。

### Established Patterns
- Phase 12 已锁定 `--onedir` 与 `electron/resources` 目录约定，主进程应遵循 manifest 定位后端。
- 启动失败采用 fail-fast 风格并输出可诊断日志路径，适合沿用到 Electron 错误弹窗。
- 配置变更后即时生效是里程碑关键路径，需由主进程主导“保存->重启->健康恢复”。

### Integration Points
- 新增 Electron `main` / `preload` 与前端 `window.api` 调用桥接。
- `save-settings` 成功后触发子进程重启与健康轮询，成功再解除 UI 阻塞。
- 首次启动门禁接入前端 router：配置缺失时强制进入向导流程。

</code_context>

<specifics>
## Specific Ideas

- 错误弹窗必须包含日志路径与“重试”入口，避免用户无助失败。
- 向导失败不可放行，保持“可用优先”而非“先进入再报错”。
- Settings 重启反馈采用全局遮罩，避免并发操作造成状态错乱。

</specifics>

<deferred>
## Deferred Ideas

- Linux clean 启动验证补跑（已在 Phase 12 标记 deferred，不阻塞 Phase 13 规划）。
- auto-update / 系统托盘 / keychain 仍保持 out-of-scope。

</deferred>

---

*Phase: 13-electron-ipc*
*Context gathered: 2026-05-28*
