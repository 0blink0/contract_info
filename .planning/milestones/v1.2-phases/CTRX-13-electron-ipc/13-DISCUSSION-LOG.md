# Phase 13: Electron 壳与 IPC - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the options considered.

**Date:** 2026-05-28
**Phase:** 13-electron-ipc
**Mode:** discuss (default)
**Areas discussed:** 子进程生命周期, IPC与配置持久化, 首次启动向导门禁, Settings重启体验

---

## 子进程生命周期

| Question | Selected |
|---|---|
| 启动体验 | 严格阻塞（30s 内健康通过才进主界面） |
| 崩溃重试 | 指数退避（0s / 2s / 5s） |
| 退出清理 | SIGTERM 后 5s 超时再 SIGKILL |
| 连续失败弹窗 | 日志路径 + 错误摘要 + 一键重试 |

---

## IPC 与配置持久化

| Question | Selected |
|---|---|
| IPC 返回结构 | 统一 `{ ok, data, error }` |
| 保存校验策略 | 严格校验（URL + 必填） |
| API Key 展示 | 默认掩码，短暂可见 |
| 配置文件位置 | `userData/config.json` 单文件 |

---

## 首次启动向导门禁

| Question | Selected |
|---|---|
| 触发条件 | `llmBaseUrl` 或 `llmApiKey` 为空即强制向导 |
| 连接测试失败 | 不允许完成 |
| 关闭向导行为 | 仍停留向导，不可进入主界面 |
| 中断恢复 | 恢复到上次未完成步骤 |

---

## Settings 保存后重启体验

| Question | Selected |
|---|---|
| 生效时机 | 保存后立即重启后端 |
| 重启中反馈 | 全局遮罩“正在重连后端” |
| 重启失败 | 回滚旧配置并提示日志路径 |
| API Key 修改 | 保存前一次确认 |

---

## Deferred Ideas

- Linux clean 启动验证补跑（后续环境窗口执行，不阻塞本阶段）。
- 自动更新、托盘、keychain 继续保持后续阶段再评估。
