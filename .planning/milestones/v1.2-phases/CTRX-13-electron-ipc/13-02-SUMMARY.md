# Phase CTRX-13 Plan 02 Summary

## 完成状态

- Task 1（ELEC-03）已完成：实现首启三步向导、路由强门禁、向导中断进度恢复、连接测试通过前禁止完成。
- Task 2（ELEC-04）已完成：实现 Settings 复用共享表单、API Key 变更二次确认、保存后触发重启、失败回滚旧配置并返回结构化结果。
- 按要求执行为本地改动，未进行任何 git commit。

## 关键实现

### Task 1: 向导门禁与恢复

- 新增 `frontend/src/views/OnboardingWizardView.vue`：Welcome -> 凭证 -> 连接测试三步流程。
- 新增 `frontend/src/components/LlmConfigForm.vue`：向导与 Settings 共享配置表单和基础校验。
- 更新 `frontend/src/router/index.ts`：在 `beforeEach` 里执行 bootstrap，并基于配置完整性 + onboarding 完成状态强制跳转。
- 更新 `frontend/src/stores/appBootstrap.ts`：增加 onboarding 草稿、步骤、完成标记持久化；支持恢复与完成状态管理。

### Task 2: Settings 重启与回滚

- 新增 `frontend/src/views/SettingsView.vue`：复用共享表单，API Key 变化时确认，保存时显示阻塞遮罩“正在重连后端”。
- 更新 `electron/ipc.ts`：`save-settings` 增加重启事务调用与结构化返回（`restarted`/`rollbackApplied`/`logPath`）。
- 更新 `electron/main.ts`：新增重启事务（停旧进程 -> 启新进程 -> 失败时恢复旧配置并重拉）。
- 更新 `electron/store.ts`：新增配置快照与恢复函数。
- 更新 `electron/preload.ts` 与 `frontend/src/types/window-api.d.ts`：补充 `onBackendStatus` 监听与 `SaveSettingsData` 类型。
- 更新 `frontend/src/layouts/AppLayout.vue`：补充 Settings 导航入口。

## Verify 摘要

### 计划内命令执行结果（复跑后）

1. `npm run test:router -- wizard-gate --runInBand`  
   - 结果：通过（`tests 1, pass 1`）
2. `npm run test:frontend -- llm-config-form --runInBand`  
   - 结果：通过（`tests 2, pass 2`）
3. `npm run test:electron -- settings-restart --runInBand`  
   - 结果：通过（`tests 7, pass 7`）
4. `npm run test:frontend -- settings-view --runInBand`  
   - 结果：通过（`tests 2, pass 2`）

### 额外验证

- `npm run typecheck`：通过。
- `npm run build`：通过（仅有 rollup chunk 体积 warning，无构建失败）。
- `ReadLints` 检查本次改动文件：无新增 linter 报错。

## 改动文件（本次任务相关）

- `frontend/src/router/index.ts`
- `frontend/src/stores/appBootstrap.ts`
- `frontend/src/components/LlmConfigForm.vue`
- `frontend/src/views/OnboardingWizardView.vue`
- `frontend/src/views/SettingsView.vue`
- `frontend/src/layouts/AppLayout.vue`
- `frontend/src/types/window-api.d.ts`
- `electron/main.ts`
- `electron/ipc.ts`
- `electron/store.ts`
- `electron/preload.ts`
- `electron/types/ipc.ts`
