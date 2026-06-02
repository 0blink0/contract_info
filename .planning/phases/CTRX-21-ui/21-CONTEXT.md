# Phase 21: 知识库配置页 UI - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段仅交付知识库配置页的前端信息架构与交互闭环：

1. 左侧菜单新增「知识库配置」入口并可正确高亮导航。
2. 知识库列表页展示历史案例（字段名/字段值/原文摘录/来源合同/入库时间）。
3. 支持按字段名过滤查询。
4. 支持单条删除，含二次确认与删除后列表即时刷新。

不在本阶段：
- RAG 注入与检索策略（Phase 22）
- 打包兼容与离线模型分发（Phase 23）
- 多字段联合搜索（字段值/来源合同）扩展能力

</domain>

<decisions>
## Implementation Decisions

### 导航入口与路由
- **D-01:** 「知识库配置」菜单项放在左侧「文件列表」下方、「系统设置」上方，作为业务操作入口而非系统级配置入口。
- **D-02:** 菜单高亮遵循现有 `AppLayout.vue` 的 `default-active + router` 机制，不改变现有「文件详情」子菜单展开行为。

### 列表加载与查询
- **D-03:** 采用推荐中间方案：首屏服务端分页加载，筛选时继续走服务端查询，不做一次性全量拉取。
- **D-04:** 本阶段搜索范围锁定为“字段名过滤”（严格对齐 KB-UI-03）；输入采用防抖即时查询，不要求用户按回车触发。

### 删除交互与反馈
- **D-05:** 删除后保持当前筛选条件与当前页面上下文，刷新当前查询结果，不重置筛选器。
- **D-06:** 删除确认文案采用“稳妥明确”风格，明确提示“删除后不可恢复”；失败提示保留后端错误详情并补充简短中文提示。

### Claude's Discretion
- 列表采用分页还是虚拟滚动的具体技术选型，由 planner/researcher 结合数据量与现有组件栈决定。
- 防抖时长、请求取消策略（如 abort controller）由实现阶段按现有 API 客户端模式决定。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求与范围
- `contract_info/.planning/ROADMAP.md` — Phase 21 目标与 4 条 Success Criteria
- `contract_info/.planning/REQUIREMENTS.md` — KB-UI-01~04 的需求约束
- `contract_info/.planning/phases/CTRX-20-pathb-ui/20-CONTEXT.md` — 延续 Phase 20 的知识库接口与状态约定

### 前端导航与路由
- `contract_info/frontend/src/layouts/AppLayout.vue` — 左侧菜单结构与 active 逻辑
- `contract_info/frontend/src/router/index.ts` — 路由注册与页面入口模式

### 现有列表交互模式
- `contract_info/frontend/src/views/FileListView.vue` — 列表页的加载/刷新/删除交互基线
- `contract_info/frontend/src/api/kb.ts` — 知识库列表与删除 API 能力（`getKbEntries`, `deleteKbEntry`）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AppLayout.vue`: 可直接按现有 `el-menu-item` 模式新增「知识库配置」入口。
- `FileListView.vue`: 可复用“页头 + 刷新 + el-table + 删除动作”的页面骨架与消息反馈。
- `api/kb.ts`: 已具备列表查询和删除接口，Phase 21 重点是页面装配与交互细节。

### Established Patterns
- 统一使用 Element Plus 表格与按钮交互（`el-table`, `el-button`, `el-message`）。
- 页面刷新走显式 `refresh()` 方法，错误统一中文提示。
- 路由守卫与标题元信息由 `router/index.ts` 统一管理。

### Integration Points
- 新增视图页（知识库配置页）并在 `router/index.ts` 注册新路由。
- 在 `AppLayout.vue` 注入菜单入口并连接到新路由。
- 列表页调用 `getKbEntries`，删除动作调用 `deleteKbEntry` 后触发当前查询重拉。

</code_context>

<specifics>
## Specific Ideas

- 搜索交互采用“输入即筛选（防抖）”而非回车触发，减少操作步骤。
- 删除后不打断用户上下文：保持筛选条件，继续停留当前结果视图。

</specifics>

<deferred>
## Deferred Ideas

- 多字段搜索（字段名 + 字段值 + 来源合同）作为后续能力单独规划，不并入 Phase 21。

</deferred>

---

*Phase: 21-知识库配置页 UI*
*Context gathered: 2026-06-02*
