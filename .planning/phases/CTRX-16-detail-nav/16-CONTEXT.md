# Phase 16: 详情路由与子菜单骨架 - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段仅交付**前端导航与状态骨架**，为 Phase 17–18 的表页/Hub/字段 B 内容铺路：

1. **`JobDetailLayout`** 作为 `/jobs/:id` 的父路由，嵌套 Hub、五表子页、字段 B 子页。
2. **`AppLayout`** 在存在 `route.params.id` 时展示可折叠「文件详情」子菜单（五表 + 字段 B，共六项）。
3. URL 与刷新保位：`/jobs/:id`（Hub）、`/jobs/:id/tables/:tableKey`、`/jobs/:id/field-b`。
4. 从列表/上传页进入任务默认 **Hub**；子菜单高亮与当前子路由一致。
5. **Layout 层单一 `useJobPoll`** + `provide/inject`；子路由组件不得各自全量轮询 `getJob`。

**不在本阶段：** 五表可编辑 preview、摘录核对表、单表下载、dirty 离开守卫（Phase 17）；Hub 摘要卡、warnings/校验入口、字段 B 摘录与 JSON 导出（Phase 18）；多文件上传 UI（Phase 19）；后端 API 变更（Phase 15 已完成）。

**过渡期说明：** v1.2 单体 `JobDetail.vue`（五表 + ValidationPanel + PathB 堆叠）从默认路由移除；Phase 16 子页为**占位**，完整业务能力在 17–18 按路由回填。接受短期「可导航但表页为占位」的中间态。

</domain>

<decisions>
## Implementation Decisions

### 路由形态（NAV-02，以 ROADMAP 为准）
- **D-01:** 父路由 `path: '/jobs/:id'`，`component: JobDetailLayout.vue`，`props: true`。
- **D-02:** 子路由：
  - `path: ''`，`name: 'job-hub'` → `JobHubView.vue`
  - `path: 'tables/:tableKey'`，`name: 'job-table'` → `JobTableView.vue`（`tableKey` 为路由 param）
  - `path: 'field-b'`，`name: 'job-field-b'` → `JobFieldBView.vue`
- **D-03:** `tableKey` 合法值与后端分表 `section` **完全一致**（五枚举）：
  `product-elements` | `fee-rates` | `lock-periods` | `share-classes` | `subscription-fee-rates`
- **D-04:** 未知 `tableKey` → 子路由 `beforeEnter` 或视图内重定向至 `job-hub`（404 式回 Hub，不白屏）。
- **D-05:** 删除旧扁平路由 `name: 'job-detail'` → `JobDetailView.vue` 单体；路由表不再挂载 `JobDetail.vue` 为默认页。

### 常量与菜单标签（NAV-01）
- **D-06:** 新增 `frontend/src/constants/jobSections.ts`：
  - `JOB_TABLE_SECTIONS`：五表 `{ key, label, previewSection }`（`key` = 路由 `tableKey` = API section）
  - `JOB_FIELD_B`：`{ pathSuffix: 'field-b', label: '字段 B' }`
- **D-07:** 子菜单六项文案与 v1.2 tab/下载语义一致：产品要素、运营费率、份额锁定期、分级份额、申赎费率、字段 B。
- **D-08:** 子菜单链接形态：
  - Hub → `/jobs/${id}`
  - 表 → `/jobs/${id}/tables/${key}`
  - 字段 B → `/jobs/${id}/field-b`

### 子菜单 UX（AppLayout）
- **D-09:** 子菜单挂在 **`AppLayout.vue` 全局侧栏**（与调研一致），**不**在 `JobDetailLayout` 内再建第二侧栏。
- **D-10:** 仅当 `typeof route.params.id === 'string'` 时渲染 `el-sub-menu` 标题「文件详情」。
- **D-11:** 进入 job 上下文时子菜单 **默认展开**（`default-openeds` 含该 sub-menu index）。
- **D-12:** 全局父项「文件列表」：凡 `route.path.startsWith('/jobs/')` 且含 id 段时，`activeMenu` 仍为 **`/jobs`**（与 v1.2 一致）。
- **D-13:** 子菜单项 `default-active` 使用 **完整 `route.path`**（含 hash 模式下完整 path），保证表页与字段 B 高亮正确。

### 入口与命名（NAV-03）
- **D-14:** `FileListView.openDetail`、`UploadView` 跳转详情处，统一改为 `router.push({ name: 'job-hub', params: { id } })`。
- **D-15:** 旧书签 `/jobs/:id` 仍有效（默认 child = Hub，无需额外 redirect 记录）。

### Layout 壳与子页占位
- **D-16:** `JobDetailLayout` 承载从 `JobDetail.vue` **抽出**的共享 chrome（本阶段最小集）：
  - 返回列表、文件名/状态、处理步骤条（或等价 status 展示）
  - 「开始处理」等等待 pipeline 的控件可保留在 Layout（复用现有逻辑），避免子页重复
  - 底部/主区 `<router-view />` 渲染子页
- **D-17:** `JobHubView`：**占位** — 标题「任务总览」+ 简短说明 + 六张 **导航卡片/按钮** 链到五表与字段 B（**非** Phase 18 的摘要数据卡与校验入口）。
- **D-18:** `JobTableView`：**占位** — 根据 `tableKey` 显示表中文名 +「本页编辑与核对功能将在下一阶段开放」；**不**调用分表 preview/verification API。
- **D-19:** `JobFieldBView`：**占位** — 标题「字段 B」+ 同上说明；**不**挂载 `PathBPanel` 完整能力。

### 单一轮询与 inject 契约（FE-02）
- **D-20:** 仅在 `JobDetailLayout` 调用 `useJobPoll`；子页通过 inject 读取状态。
- **D-21:** 新增 `frontend/src/composables/useJobDetailContext.ts`（或同级）定义 `InjectionKey<JobDetailContext>`：
  ```ts
  interface JobDetailContext {
    jobId: ComputedRef<string | null>
    detail: Ref<JobDetail | null>
    loading: Ref<boolean>
    status: Ref<string>
    refresh: () => Promise<void>
    activate: () => void  // POST /run 后强制轮询
  }
  ```
- **D-22:** Layout `onMounted` 首次 `getJob`；`useJobPoll` 的 `onUpdate` 写回 `detail`/`status`；子组件 **禁止** import `useJobPoll`（Phase 16 代码审查点）。
- **D-23:** 删除任务、404 处理留在 Layout（与现 `JobDetail.vue` 行为对齐），通过 inject 可选暴露 `reload`/`onDeleted` 或由 Layout 直接处理路由回列表。

### 遗留组件
- **D-24:** **`JobDetail.vue` 本阶段不删除文件**，仅从路由卸载；Phase 17–18 按路由拆分为 `ExportPreview`/`ValidationPanel`/`PathBPanel` 等的目标宿主。
- **D-25:** `JobDetailView.vue` 可删除或改为 re-export Layout（推荐 **删除**，由 router 直接指向 `JobDetailLayout`）。

### 测试与质量（Claude discretion）
- **D-26:** 建议新增轻量 **路由单元测试**（vitest + `createMemoryHistory`）：默认 child=Hub、`tables/:tableKey` 解析、非法 key 回 Hub、列表 push 的 name 为 `job-hub`。
- **D-27:** 不强制 E2E；手工验收对照 ROADMAP Success Criteria 四条。

### Claude's Discretion

用户跳过讨论问卷；按 `ROADMAP.md`、`REQUIREMENTS.md`（NAV-01~03、FE-02）与 `research/ARCHITECTURE.md` 默认项锁定。路由路径以 ROADMAP 的 `/tables/:tableKey` 为准（**覆盖**调研文档中扁平 `product-elements` 路径草稿）。

### Folded Todos

（无）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 里程碑与需求
- `contract_info/.planning/PROJECT.md` — v1.3 目标
- `contract_info/.planning/REQUIREMENTS.md` — NAV-01~03、FE-02
- `contract_info/.planning/ROADMAP.md` — Phase 16 Success Criteria（含 `/tables/:tableKey`）

### v1.3 调研
- `contract_info/.planning/research/ARCHITECTURE.md` — JobDetailLayout、AppLayout 子菜单、provide 模式（路径以 ROADMAP 为准）
- `contract_info/.planning/research/SUMMARY.md` — 前端构建顺序 Phase 16→17→18

### Phase 15 后端契约（Phase 17 消费，Phase 16 仅对齐命名）
- `contract_info/backend/app/api/routes/jobs.py` — `preview/{section}`、`verification/{table_key}` 枚举
- `contract_info/.planning/phases/CTRX-15-api/15-CONTEXT.md` — section 与 extraction 键映射

### 现有前端锚点
- `contract_info/frontend/src/router/index.ts` — 当前单体 `/jobs/:id`
- `contract_info/frontend/src/layouts/AppLayout.vue` — 全局菜单
- `contract_info/frontend/src/components/JobDetail.vue` — v1.2 单体详情（待拆分）
- `contract_info/frontend/src/composables/useJobPoll.ts` — 轮询终止条件
- `contract_info/frontend/src/views/FileListView.vue` — `openDetail` 入口
- `contract_info/frontend/src/views/UploadView.vue` — 上传后跳转详情

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useJobPoll` — 直接迁入 `JobDetailLayout`，逻辑不变。
- `JobDetail.vue` — 头部、步骤条、run/delete、loading 错误态可剪切至 Layout。
- `statusLabelZh` / `isInProgress` — Layout 与子页占位共用。
- `getJob`（`api/client.ts`）— Layout 首次加载与 poll tick。

### Established Patterns
- `AppLayout` + `el-menu` `router` 模式；`activeMenu` 已对 `/jobs/*` 特判。
- 页面壳 `page-shell` / `surface-card` CSS 类。
- Electron：`createWebHashHistory` 与嵌套路由兼容。

### Integration Points
- 列表/上传 → `job-hub` 路由名。
- Phase 17：`JobTableView` 注入 `detail` + 调用 `GET/PUT preview/{section}`、`GET verification/{table_key}`。
- Phase 18：`JobHubView` / `JobFieldBView` 替换占位内容。

</code_context>

<specifics>
## Specific Ideas

- 子菜单与 ROADMAP 六项一一对应；Hub 占位用「导航卡片」预演 Phase 18 信息架构，但不抢 Phase 18 的摘要/校验职责。
- 保持「文件列表」父菜单高亮，避免用户误以为离开列表域。

</specifics>

<deferred>
## Deferred Ideas

- 调研稿中的**扁平**表路径（`/jobs/:id/fee-rates`）— 不采用，以免与 NAV-02 及后端 section 路径心智分裂。
- Hub warnings / 校验摘要按钮 — Phase 18（HUB-02）。
- 表页 dirty 守卫 — Phase 17（TBL-05）。
- 多文件上传与并行进度条 — Phase 19。

</deferred>
