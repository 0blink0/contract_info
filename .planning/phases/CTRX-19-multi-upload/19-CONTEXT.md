# Phase 19: 多文件上传与并行进度 UI - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段交付**上传页**多文件（≤3 docx）与并行进度体验，闭合 v1.3 里程碑：

1. **UP-01** — 一次最多选 3 个 docx；第 4 个前端阻止并提示。
2. **UP-02** — 每文件独立 job；上传页同时展示最多 3 张进度卡（状态、步骤条、错误各自独立）。
3. **UP-03** — 批量「开始处理」全部 pending；单卡重试/进入详情。
4. **FE-01** — `useJobsPoll` 注册多 jobId，单定时器批量 `getJob`，避免仅最后一卡刷新。

**不在本阶段：** 批量 `POST /upload/batch`（沿用 n×`POST /upload`）；>3 队列（v2 BATCH）；Hub/表页改动。

**依赖：** Phase 15 全局 3 槽 `POST /run` 409；Phase 16–18 详情路由（`job-hub` 跳转）。

</domain>

<decisions>
## Implementation Decisions

### 上传交互（UP-01）
- **D-01:** `el-upload` 设置 `multiple` + `:limit="3"`；`on-exceed` → `ElMessage.warning('最多同时上传 3 个文件')`。
- **D-02:** `accept=".docx"`；非 docx 单文件拒绝（沿用现有校验）。
- **D-03:** 选文件后 **并行** `POST /upload`（最多 3），每成功一项追加到 `sessionJobs` 列表（本页会话，刷新页面可清空 — 不持久化 localStorage）。

### 进度卡（UP-02）
- **D-04:** 新建 `UploadJobCard.vue`：文件名、状态 tag、`ProcessStepper`、error alert、单 job「开始/重试」「查看结果」。
- **D-05:** `UploadView` 用 `v-for` 渲染最多 3 卡；无「当前单文件」模式。
- **D-06:** 卡数据 `UploadSessionJob { jobId, filename, status, detail, runError? }` 由 `useJobsPoll` 更新 `detail`。

### 批量运行（UP-03）
- **D-07:** 工具栏按钮「全部开始处理」：对 `sessionJobs` 中 `status===pending` 依次 `runJob`；单 job 失败不阻断其余。
- **D-08:** 遇全局 409（3 槽满）解析 `detail` 对象或字符串，提示「已有 3 个任务正在处理」；未启动的 pending 保持 pending。
- **D-09:** 单卡「查看结果」→ `router.push({ name: 'job-hub', params: { id } })`。

### 多 job 轮询（FE-01）
- **D-10:** 新建 `useJobsPoll.ts`：维护 `Map<jobId, { status, onUpdate }>`；**一个** `setInterval(2000)` 对需轮询的 id 并行 `getJob`；逻辑复用 `useJobPoll` 的 TERMINAL/PIPELINE_POLL/activate。
- **D-11:** `register(jobId, initialStatus, onUpdate)` / `unregister(jobId)`；组件卸载 unregister。
- **D-12:** `UploadView` onMounted 不 poll 历史 list — 仅 poll 本页 `sessionJobs`。

### 并发可见性（Claude discretion，按调研）
- **D-13:** 新增 `GET /jobs/concurrency` → `{ active: number, max: 3 }`（包装 `count_in_progress`）；前端 `getJobConcurrency()` 用于上传页展示「系统处理中 X/3」及批量 run 前提示。
- **D-14:** 若 `active >= 3`，批量开始按钮 disabled 并 tooltip 说明（pending 仍可上传占槽位前的 pending 状态）。

### 测试
- **D-15:** `useJobsPoll` 行为用静态/轻量测试或 `upload-multi.test.mjs` 断言 UploadView 含 `useJobsPoll`、`limit`、`:multiple`。
- **D-16:** 后端 `test_api_concurrency.py` 或扩展现有 parallel 测试覆盖 GET concurrency。

</decisions>

<canonical_refs>
- `contract_info/.planning/REQUIREMENTS.md` — UP-01~03, FE-01
- `contract_info/.planning/research/ARCHITECTURE.md` — 多文件数据流
- `contract_info/backend/app/services/pipeline_service.py` — count_in_progress
- `contract_info/frontend/src/views/UploadView.vue` — v1.2 单文件基准
- `contract_info/frontend/src/composables/useJobPoll.ts` — 单 job 轮询参考
</canonical_refs>
