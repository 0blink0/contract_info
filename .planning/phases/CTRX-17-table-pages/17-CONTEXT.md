# Phase 17: 五表独立工作页 - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning (derived from ROADMAP + Phase 15/16; no discuss questionnaire)

<domain>
## Phase Boundary

本阶段交付**五张导入表**在 `JobTableView` 上的完整工作流（字段 B 属 Phase 18）：

1. **TBL-01** — 每表页展示与 v1.2 `ExportPreview` 对应 tab 一致的列，可就地编辑。
2. **TBL-02** — 分表 `PUT /jobs/{id}/preview/{section}` 保存；保存后 xlsx 反映最新内容（后端 `persist_export` 已由 Phase 15 保证）。
3. **TBL-03** — 每表页展示摘录核对表（`GET /jobs/{id}/verification/{table_key}`）。
4. **TBL-04** — 每表页单表 xlsx 下载（`downloadBlob` + `TABLE_DOWNLOAD_FILES`）。
5. **TBL-05** — 未保存离开表页时 `beforeRouteLeave` 确认。

**不在本阶段：** Hub 摘要卡、Hub 校验入口（Phase 18）；字段 B 专页（Phase 18）；多文件上传 UI（Phase 19）；后端 API 变更（Phase 15 已完成）；`JobDetailLayout` 路由/子菜单改动（Phase 16 已完成）。

**依赖：** Phase 16 的 `JobTableView` 路由、`useJobDetailInject`、禁止子页 `useJobPoll`。

</domain>

<decisions>
## Implementation Decisions

### API 客户端（TBL-02）
- **D-01:** 新增 `getJobPreviewSection(jobId, section)`、`saveJobPreviewSection(jobId, section, body)`，对接 Phase 15 分表端点；**不再**在表页调用全量 `saveJobPreview`。
- **D-02:** 新增 `getTableVerification(jobId, tableKey)` → `TableVerificationResponse`。
- **D-03:** TypeScript 类型与 `JobPreviewSectionResponse` / `VerificationRow` 对齐 `backend/app/api/schemas.py`。

### 组件拆分（TBL-01，自 ExportPreview）
- **D-04:** 新建 `TablePreviewEditor.vue`：`tableKey` prop，内部按 section 渲染产品表（field/value）或列表表（动态列，**可编辑列排除「摘录原文」**）。
- **D-05:** 新建 `VerificationExcerptTable.vue`：只读核对表，列：字段、字段值、摘录页码、原文摘录；`page_no` 为空时显示 `page_no_note` 或「—」。
- **D-06:** `ExportPreview.vue` 保留文件但改为薄封装或标记 `@deprecated`；表页不引用；`JobDetail.vue` 仍不挂路由（无变更要求）。

### 表页编排（JobTableView）
- **D-07:** `useSectionPreview(tableKey)` composable：`loading/saving/dirty/preview`，`load` 在 `extracted|exporting|exported|export_failed` 时拉分表 GET；`save` 调分表 PUT；`markDirty` 供编辑器。
- **D-08:** 页头：表名、保存按钮（disabled 当 !dirty）、单表下载按钮（`exported` 或保存后可下载 — 与 v1.2 一致：`extracted` 起可编辑，下载在 `exported` 显示）。
- **D-09:** 布局顺序：可编辑网格 → 摘录核对表 → 操作提示（与 v1.2 文案一致）。
- **D-10:** 使用 `useJobDetailInject()` 的 `detail.status`，**不**在表页另开 `getJob` 轮询。

### Dirty 守卫（TBL-05）
- **D-11:** `onBeforeRouteLeave`：若 `dirty`，`ElMessageBox.confirm`；取消则 `return false`。
- **D-12:** 同表内保存成功后 `dirty = false`；切换 `tableKey`（路由 param 变）时 reload 并清 dirty。

### Layout 下载条（Claude discretion）
- **D-13:** Phase 17 在表页提供主下载（TBL-04）；`JobDetailLayout` 批量下载按钮**保留**作为快捷入口，避免回归；Phase 18 可再收敛。

### 测试
- **D-14:** 扩展 `job-detail-routes.test.mjs` 或新增 `section-preview-api.test.mjs`：断言 client 含分表路径字符串。
- **D-15:** 可选 composable 纯函数测试；不强制 E2E。

### Claude's Discretion

无 discuss 问卷；按 ROADMAP、REQUIREMENTS TBL-*、ARCHITECTURE 与现有 `ExportPreview.vue` 行为锁定。

</decisions>

<canonical_refs>
## Canonical References

- `contract_info/.planning/REQUIREMENTS.md` — TBL-01~05
- `contract_info/.planning/ROADMAP.md` — Phase 17 Success Criteria
- `contract_info/.planning/phases/CTRX-15-api/15-CONTEXT.md` — 分表 PUT / verification API
- `contract_info/.planning/phases/CTRX-16-detail-nav/16-CONTEXT.md` — 路由与 inject
- `contract_info/FIELD_SPEC.md` — 列名与业务字段
- `contract_info/frontend/src/components/ExportPreview.vue` — v1.2 编辑 UX 基准
- `contract_info/backend/app/api/routes/jobs.py` — preview/{section}, verification/{table_key}
</canonical_refs>
