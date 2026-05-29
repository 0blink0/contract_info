---
phase: 13
slug: CTRX-13-electron-ipc
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-28
updated: 2026-05-28
---

# Phase 13 验证策略

**阶段：** Electron 壳与 IPC  
**日期：** 2026-05-28

## 需求到验证映射

| 需求 | 关键行为 | 自动化命令 | 类型 | 对应计划任务 |
|------|----------|------------|------|--------------|
| ELEC-01 | spawn + health poll + 30s 超时 + 3 次退避重试 + TERM/KILL 退出清理 | `npm run test:electron -- lifecycle --runInBand` | integration | 13-01 Task 1 |
| ELEC-02 | preload 窄桥三通道 + Result 结构 + 严格字段校验 + userData/config.json 落盘 | `npm run test:electron -- ipc --runInBand` | unit/integration | 13-01 Task 2 |
| ELEC-03 | 配置缺失强制向导 + 连接测试失败不可放行 + 向导恢复 | `npm run test:router -- wizard-gate --runInBand` | router/e2e-lite | 13-01 Task 3 |
| ELEC-04 | Settings 保存后立即重启生效 + 全局重连态 + 失败回滚 | `npm run test:electron -- settings-restart --runInBand` | integration | 13-01 Task 4 |

## Wave 0 缺口

- [ ] `electron/tests/lifecycle.spec.ts`
- [ ] `electron/tests/ipc.spec.ts`
- [ ] `frontend/src/router/__tests__/wizard-guard.spec.ts`
- [ ] `electron/tests/settings-restart.spec.ts`
- [ ] 前端脚本补齐：`test:electron`、`test:router`

## 采样与门禁

- **每任务完成后：** 跑对应单项验证命令
- **每 wave 收口：** 运行所有 Electron 相关测试 + 前端 typecheck
- **阶段门禁：**
  1. `npm run test:electron -- lifecycle --runInBand`
  2. `npm run test:electron -- ipc --runInBand`
  3. `npm run test:router -- wizard-gate --runInBand`
  4. `npm run test:electron -- settings-restart --runInBand`

## 人工验收补充

1. 冷启动看到加载页，健康通过后再进入主界面。
2. 人为制造后端崩溃，确认最多 3 次重试后出现含日志路径弹窗。
3. 清空 `llmBaseUrl` 或 `llmApiKey`，确认强制进入向导且无法绕过。
4. Settings 修改 Key 保存后，确认后端重启且新配置立即生效；失败时回滚旧配置。
