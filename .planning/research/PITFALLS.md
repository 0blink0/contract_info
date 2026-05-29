# 领域陷阱：CTRX v1.3

**领域：** 桌面合同抽取（FastAPI + Vue + SQLite + Electron）— 多文件并行（≤3）+ 详情六页路由重构  
**调研日期：** 2026-05-29  
**置信度：** HIGH（基于 `PROJECT.md`、`parse_service.py`、`useJobPoll.ts`、`pipeline_service.py`、`preview_edit_service.py`、现有前端路由与 v1.2 已交付基线）

> v1.2 桌面化/SQLite/PyInstaller 类陷阱已在里程碑 11–14 收口。本文档仅针对 **v1.3 多文件并行与 JobDetail 六页拆分**。

---

## 严重陷阱（可能导致数据丢失、假并行或大面积返工）

### 陷阱 1：单表保存误用 `PUT /preview` 全量契约，清空其它四张表

**会出现什么问题：**  
`apply_preview_edits` 对缺失字段使用 `payload.get("fee_rows") or []` 等默认值。若六页拆分后某页只提交 `product_rows`，其余表键缺省 → 后端收到空列表 → `_apply_list_table_edits` 将 `extraction["fee_rates"]` 等写成 `[]`，并 `persist_export` 重生成 Excel。**其它表数据被静默抹除。**

**根因：**  
v1.1 的 `ExportPreview.vue` 在单组件内持有完整 `JobPreview`，保存时始终提交五表全量字段（见 `onSave`）。六页后每页天然只编辑局部，但 API 仍是全量语义。

**后果：** 运营在「申赎费率」页点保存后，产品要素/运营费率 xlsx 变空或缺行；难以从 UI 察觉，直到 CRM 导入失败。

**预防：**
- **方案 A（推荐）：** 按表拆分 `PATCH /jobs/{id}/preview/{table}`，服务端只 merge 对应 `list_key` / `product_elements` 子集。
- **方案 B：** 保留全量 PUT，但前端用 **Pinia/父 layout 缓存完整 preview**，子页保存前 merge 再提交；路由离开前 `onBeforeRouteLeave` 拦截 `dirty`。
- 契约测试：单表 payload 不得改变未提交表的 `extraction_result` 行数。

**预警信号：**
- 单表保存后 `GET /preview` 其它 `*_rows` 长度变 0
- 保存成功但某张 xlsx 体积骤降
- 集成测试只测单表编辑路径

**关联代码：** `preview_edit_service.py` 第 83–107 行；`ExportPreview.vue` 第 76–86 行。

---

### 陷阱 2：误以为 `BackgroundTasks` 或多次 `POST /run` 即「三文件真并行」

**会出现什么问题：**  
当前 `run_job` 仅 `background_tasks.add_task(run_pipeline, job_id)`（`jobs.py`）。`run_pipeline` 为 **同步 CPU 密集**（`parse_file_id` → `persist_extract` → `persist_export`）。在 **单 worker Uvicorn** 下：
- 同一请求内多个 `add_task` 在 Starlette 中 **顺序执行**；
- 多请求并发时虽可能进入线程池，但默认池大小、GIL、单进程 SQLite 写入仍易形成 **实际串行或长时间 `database is locked`**。

**根因：**  
`parse_service.parse_file_id` 在独立 `SessionLocal` 中短事务提交后做 `parse_docx`（CPU），但 extract/export/validation 仍长时间占线程并频繁写库；未设计 **显式并发上限（3）与队列**。

**后果：** 上传页显示 3 个「处理中」，实际逐个完成；或间歇 500/`OperationalError: database is locked`；Electron 单 Python 子进程 CPU 打满导致 UI 卡顿。

**预防：**
- 引入 **`asyncio.Semaphore(3)` 或 `ThreadPoolExecutor(max_workers=3)`** 的 `job_runner`，`POST /run` 只入队；拒绝第 4 个活跃 pipeline（409 + 明确文案）。
- 保持 **每 job 独立 `file_id` 目录**（已满足），避免共享写路径。
- 压测：`test_db_wal.py` 仅覆盖短 INSERT；需加 **3× 完整 pipeline** 集成测试（可 mock LLM）。
- 文档写明：v1.3 并行上限是 **业务约束 + 资源约束**，不是「无限扩展」。

**预警信号：**
- 3 份合同总耗时 ≈ 单份 × 3
- 日志交替出现 `busy_timeout` / `database is locked`
- 任务状态长期停在 `parsing` 仅一份在前进

**关联代码：** `jobs.py` `run_job`；`pipeline_service.run_pipeline`；`session.py` WAL pragma。

---

### 陷阱 3：`useJobPoll` 单实例模型无法支撑上传页 3 job 进度

**会出现什么问题：**  
`useJobPoll(jobId, status, onUpdate)` 每个实例 **一个 `setInterval`（2s）**。`UploadView` 仅维护 `activeJobId` + 单一 `status`（`UploadView.vue`）。v1.3 需同时展示 ≤3 份进度时：
- 若只 poll 最后一个 jobId → 前两份状态冻结在 `parsing`；
- 若复制 3 份 composable → 6s 内 6 次 `GET /jobs/{id}`，且 `status` ref 与列表项易错位；
- 子路由再挂载 poll → **重复轮询同一 job**。

**根因：**  
轮询与终端状态判断（`TERMINAL`、`PIPELINE_POLL`）绑定在 composable 内，无 **jobId → 订阅者** 注册表；`onUpdate` 写单个 `detail` ref。

**后果：** 用户以为某份已完成仍显示「处理中」；或完成后未刷新列表；离开上传页后后台 job 无人 poll（若未在列表页补 poll）。

**预防：**
- 实现 **`useJobPollRegistry`**（Map<jobId, Set<listener>>，单定时器 tick 批量 `getJob`）或在上传页用 **一个** `setInterval` + `Promise.all` 拉取活跃 id 列表。
- 规则：**每个 jobId 全局最多一条 poll 链**；Hub/子页通过 store 读缓存，不各自 `setInterval`。
- `activate()` 在批量 `POST /run` 后对 **每个** id 调用一次。

**预警信号：**
- Network 面板同一 `job_id` 每 2s 出现 2+ 条 GET
- 多文件卡片状态与进入详情页后不一致
- `forcePoll` 仅作用于最后一个 id

**关联代码：** `useJobPoll.ts`；`UploadView.vue`；`JobDetail.vue` watch + poll。

---

### 陷阱 4：六页路由拆分后「未保存编辑」在 Hub ↔ 子页导航间丢失

**会出现什么问题：**  
`ExportPreview` 用组件内 `dirty` + `watch(jobId, status)` 重新 `loadPreview()`（会 **丢弃本地编辑**）。拆成 6 个 route 后，每次 `router.push` 卸载组件 → 未点「保存」的表格行丢失。Hub 总览若每表嵌预览，还会 **重复请求** `GET /preview`（payload 大）。

**根因：**  
状态在叶子组件，不在 **job 级 store**；无 `beforeRouteLeave` / `onBeforeUnmount` 守卫；v1.3 需求要求每页可编辑 + 摘录核对，编辑会话长于单页停留时间。

**后果：** 运营在多表间核对时反复丢改；对「保存并重新生成 Excel」信任下降。

**预防：**
- `stores/jobPreview.ts`：`previewByJobId[jobId]` + `dirtyTables: Set<TableKind>`。
- 子页只读写自己表切片；保存仍走全量或 PATCH（见陷阱 1）。
- Hub 仅展示 **摘要**（行数、校验 fail 数、`JobDetail` 已有字段），点击进入子页再加载全量。
- 统一「离开未保存」对话框（与 Electron 关闭窗口无关，但 hash 路由内同样必要）。

**预警信号：**
- 切换侧栏菜单后表格恢复为服务端旧值
- Hub 打开即触发 5 次相同 preview 请求
- E2E 无「编辑→切换路由→再回来」用例

**关联代码：** `ExportPreview.vue` `dirty`/`loadPreview`；`JobDetail.vue` 单页聚合 `ValidationPanel`/`PathBPanel`。

---

### 陷阱 5：三 pipeline 并行触发 LLM 校验风暴（配额、耗时、失败语义）

**会出现什么问题：**  
`persist_extract` 内同步调用 `persist_validation`（`extract_service.py`）。三份合同同时 extract → **3 路 `run_llm_validation_sync`**。桌面端共用 Settings 中单一 API Key；易触发 **429/超时**，且某一 job `validation_result` 为 skipped/failed 而其它成功，UI 若只在总览显示 aggregate 易误判。

**根因：**  
校验与抽取绑在同一事务路径，无 **全局限流**；v1.2 单 job 场景未暴露问题。

**后果：** 并行名义上成功但校验全跳过；运营以为「已校验」实则 `validation_available: false`。

**预防：**
- 全局 **`LLMValidationSemaphore(1)`** 或串行队列（并行只针对 parse/extract/export，校验排队）。
- 或 v1.3 将校验改为 **显式按钮**（Hub 上「运行校验」），与 pipeline 解耦。
- Job 卡片展示 **校验状态**（skipped/fail/ok），不只显示 `exported`。

**预警信号：**
- 三 job 同时 exported 但 `validation_available` 均为 false
- 后端日志集中 burst 后长时间无 LLM 日志
- 单 job 重试校验成功、并行时失败

---

## 中等陷阱

### 陷阱 6：子路由与 Electron `createWebHashHistory` 的菜单高亮、深链接

**会出现什么问题：**  
当前仅 `/jobs/:id` 单路由（`router/index.ts`）。拆为 `/jobs/:id`、`/jobs/:id/product`、…、`/jobs/:id/path-b` 后，侧栏 `router-link` 的 `active-class` 对子路径匹配不当；刷新深链接时 **Hub 未加载** `jobId` 元数据。

**预防：**  
嵌套路由 + `meta: { jobSection: 'product' }`；父 `JobLayout.vue` 负责 `loadDetail` **一次** + 提供 `jobId`；`redirect: '' → hub`。

---

### 陷阱 7：并行上传接口仍按「单文件 `UploadFile`」设计

**会出现什么问题：**  
`upload.py` 仅 `file: UploadFile = File(...)`。前端若用 `el-upload` `multiple` 却循环 3 次 POST，需 **客户端限制 ≤3**、去重、失败部分回滚；否则第 4 个文件应 400。缺少 **batch 响应**（`job_ids[]`）时上传页状态机复杂。

**预防：**  
`POST /upload/batch`（最多 3 files）返回 `{ jobs: [{ job_id, filename, status }] }`；或保留单文件 API 但文档化 **串行 upload + 并行 run** 的契约。

---

### 陷阱 8：`parse_service` 失败回滚与并行交叉

**会出现什么问题：**  
`parse_file_id` 在 `except` 中 `rollback` 后重新 `get` 行写 `failed`（`parse_service.py` 37–44）。高并发下若同一 `file_id` 被重复 `POST /run`（双击），可能出现 **状态竞态**（一个线程写 `parsed` 另一个写 `failed`）。

**预防：**  
`run_pipeline` 入口用 **乐观锁**：`UPDATE ... WHERE status IN (...)` 行数=1；或 `assert_can_run` 后立即将状态置为 `parsing` 并 commit（占坑）。

---

### 陷阱 9：单表下载与「保存后 regenerate」顺序

**会出现什么问题：**  
六页各带「单表下载」，若用户 **未保存** 编辑即下载，拿到旧 xlsx。v1.1 在 tab 内尚有上下文；分页后更易误解。

**预防：**  
下载前检查 `dirtyTables`；或下载 API 支持 `?from=preview` 从内存生成（复杂）；至少 UI 禁用 dirty 时下载并提示先保存。

---

## 轻微陷阱

### 陷阱 10：删除进行中 job 的 409 与并行列表

`JobDeleteBusyError` 在 pipeline 中途删除返回 409。并行列表需 **禁用删除按钮** 与 `isInProgress` 同步，避免一份失败阻塞 UI。

### 陷阱 11：SQLite 文件体积与三份大 docx

`parse_json` + `extraction_result` 三份同时膨胀，`CTRX_DATA_DIR/ctrx.sqlite` 快速增长；无清理 UI（ARCHITECTURE 已提示 v1.3 可考虑）。

### 陷阱 12：Hub「六页摘要」与 `GET /jobs/{id}` 字段不足

`JobDetailResponse` 无 per-table 行数/校验摘要；Hub 要么 N+1 调 preview，要么扩展 schema（注意 JSON 体积）。

---

## 分阶段预警

| 阶段主题 | 高发陷阱 | 缓解措施 |
|----------|----------|----------|
| 多文件上传 + 并行 run | #2 #7 #8 | 显式 worker 池 + batch API + 占坑状态 |
| 上传页 3 路进度 UI | #3 #5 | Poll 注册表 + LLM 限流 |
| 六页路由 + 侧栏 | #4 #6 #9 | Job layout store + 嵌套路由 |
| 每页编辑/摘录/下载 | #1 #9 | PATCH 或全量 merge + dirty 守卫 |
| Hub 总览 | #4 #12 | 扩展 detail 或轻量 summary endpoint |

---

## 来源

| 来源 | 用途 | 置信度 |
|------|------|--------|
| `contract_info/.planning/PROJECT.md` v1.3 范围 | 需求边界（≤3、六页、Hub） | HIGH |
| `backend/app/services/parse_service.py` | 解析事务与失败写回 | HIGH |
| `backend/app/services/preview_edit_service.py` | 全量 PUT 清空风险 | HIGH |
| `backend/app/services/pipeline_service.py` / `jobs.py` | BackgroundTasks 并行语义 | HIGH |
| `frontend/src/composables/useJobPoll.ts` | 单 job 轮询模型 | HIGH |
| `frontend/src/views/UploadView.vue` | 单 activeJobId | HIGH |
| `backend/tests/test_db_wal.py` | WAL 仅验证短写，非 pipeline | HIGH |
| Starlette BackgroundTasks 行为 | 同请求任务顺序执行 | MEDIUM（需实现时再验证线程池路径） |

---

## v1.2 历史陷阱（已交付，勿在 v1.3 重复踩坑）

PostgreSQL 方言、PyInstaller 路径、`CTRX_DATA_DIR`、端口 18765、Electron 子进程重试等见 `.planning/milestones/v1.2-*` 与旧版 `PITFALLS.md` 归档。v1.3 默认在 **SQLite + 已打包桌面** 基线上演进。
