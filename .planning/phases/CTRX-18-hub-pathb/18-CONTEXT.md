# Phase 18: Hub 摘要与字段 B 专页 - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段交付 **Hub 摘要/校验入口** 与 **字段 B 专页**（五表工作页已在 Phase 17 完成）：

1. **HUB-01** — Hub 六张摘要卡：表名、行数（或状态提示）、可选 job 级校验 fail/warn 角标；「进入详情」链到子路由。
2. **HUB-02** — Hub **不**堆叠可编辑大表、`ExportPreview`、`PathBPanel` 全量；校验以 Hub 折叠区/入口呈现。
3. **HUB-03** — `WarningsList` 与 `ValidationPanel` 置于 **Hub**（从 Layout 迁出，避免表页重复 v1.2 单体堆叠）。
4. **PB-01** — 字段 B 专页展示业绩报酬/开放日建议摘录；无页码数据时明确文案说明。
5. **PB-02** — 字段 B 页保留复制/下载 path-b JSON（v1.2 `PathBPanel` 行为）。

**不在本阶段：** 表页编辑/核对（Phase 17）；多文件上传（Phase 19）；后端 API 变更。

**Layout 保持：** 文件名、步骤条、开始/重试/删除、批量下载仍在 `JobDetailLayout`（Phase 16/17 约定）。

</domain>

<decisions>
## Implementation Decisions

### Hub 摘要数据（HUB-01）
- **D-01:** 新建 `useHubSummary`：当 `status ∈ {extracted, exporting, exported, export_failed}` 时，对五表 **并行** `getJobPreviewSection` 仅取行数（不渲染全表）。
- **D-02:** 摘要卡组件 `HubSectionCard`：`label`、`rowCount`、`statusHint`、`router-link`；无数据时显示「—」或「尚未抽取」。
- **D-03:** 字段 B 摘要卡：若 `detail.path_b_available`，Hub mount 时 **单次** `getPathB` 取一句摘要（如 CRM 已建议 x/6 项或固定开放日）；否则「暂无路径 B」。
- **D-04:** 校验角标（可选）：卡片上显示 job 级 `validation_fail_count` / `validation_warn_count`（来自 inject `detail`，**不**每表打 verification API）。

### Hub 校验与警告（HUB-02, HUB-03）
- **D-05:** 从 `JobDetailLayout` **移除** `WarningsList`；仅在 `JobHubView` 渲染（`detail.extraction_warnings`）。
- **D-06:** `ValidationPanel` 仅挂载于 `JobHubView`（`visible` = PREVIEW_PLUS）；表页/字段 B 页不挂载。
- **D-07:** 替换 Hub 占位文案；保留导航卡片布局，升级为摘要卡。

### 字段 B 专页（PB-01, PB-02）
- **D-08:** 抽取 `usePathB(jobId)` composable（load/refresh/copyJson/downloadJson/data）自 `PathBPanel.vue`。
- **D-09:** 新建 `PathBDetail.vue`（无 collapse，onMounted 自动 load）；`JobFieldBView` 全宽承载。
- **D-10:** `PathBPanel.vue` 改为 collapse 薄包装 + 内部 `PathBDetail`（保留供 `JobDetail.vue` 参考，路由仍不用）。
- **D-11:** 摘录展示：`crm_handoff.snippet`、`raw_sections`、`source_snippet_rows`；**页码列**：若 API 无 page 字段，表头仍保留「页码」列并统一显示「页码暂未解析」（PB-01）。
- **D-12:** 顶部 `el-alert` 说明字段 B 需 CRM 手录、不进 Excel 导入母版。

### 测试与质量
- **D-13:** 扩展 router/静态测试：Hub 引用 `useHubSummary`/`ValidationPanel`；`JobFieldBView` 引用 `PathBDetail`/`usePathB`；Layout 不再含 `WarningsList`。
- **D-14:** `npm run typecheck` + `test:router` + `build` 阶段门禁。

### Claude's Discretion

按 ROADMAP + ARCHITECTURE + 现有 `PathBPanel`/`ValidationPanel` 锁定；Hub 不调用全量 `getJobPreview`。

</decisions>

<canonical_refs>
- `contract_info/.planning/REQUIREMENTS.md` — HUB-01~03, PB-01~02
- `contract_info/.planning/research/ARCHITECTURE.md` — Hub vs 表页职责
- `contract_info/frontend/src/views/JobHubView.vue` — 当前占位
- `contract_info/frontend/src/views/JobFieldBView.vue` — 当前占位
- `contract_info/frontend/src/components/PathBPanel.vue` — v1.2 字段 B UX
- `contract_info/frontend/src/components/ValidationPanel.vue`
- `contract_info/frontend/src/layouts/JobDetailLayout.vue`
</canonical_refs>
