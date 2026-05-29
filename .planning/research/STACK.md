# 技术栈研究 — CTRX v1.3 新能力

**项目:** 合同要素抽取（CTRX）v1.3 — 多文件并行与详情页重构  
**领域:** Electron 桌面端 · FastAPI + Vue 3 + SQLite（既有栈不变）  
**调研日期:** 2026-05-29  
**置信度:** HIGH（栈增补基于仓库现状 + FastAPI 官方讨论/社区共识；页码能力为 MEDIUM，需实现期验证）

---

## 既有栈（不重复调研）

| 层 | 技术 | v1.3 角色 |
|----|------|-----------|
| 后端 | FastAPI 0.110+、Uvicorn、SQLAlchemy 2.0、Alembic、openpyxl、python-docx、python-multipart | 扩展 API/服务，不替换 |
| 前端 | Vue 3.5、vue-router 4.6、Element Plus 2.9、Vite 6、TypeScript 5.7 | 嵌套路由 + 多任务 UI |
| 数据 | SQLite（WAL，`CTRX_DATA_DIR`） | 每文件一行 `contract_files`，并行写需沿用 WAL |
| 桌面 | Electron 42、electron-builder 26、PyInstaller 6 | 无变更；≤3 并行在单机线程池内完成 |

---

## v1.3 推荐栈增补与变更

### 核心变更（无新运行时依赖）

| 变更点 | 实现方式 | 用途 | 推荐理由 |
|--------|----------|------|----------|
| 并行流水线调度 | **stdlib** `concurrent.futures.ThreadPoolExecutor(max_workers=3)`，模块级单例，在 `pipeline_service` 提交 `run_pipeline` | 最多 3 份 docx 同时解析/抽取/导出 | 现有每 job 一次 `BackgroundTasks.add_task(run_pipeline)`；FastAPI **按注册顺序串行**执行多个 BackgroundTask（[Discussion #13724](https://github.com/fastapi/fastapi/discussions/13724)）。桌面场景 ≤3 路、CPU/IO 混合，线程池足够，无需 Celery/ARQ |
| 批量上传 API | FastAPI `files: list[UploadFile] = File(...)` + 现有 `persist_upload` 循环 | 一次请求上传 ≤3 个 docx，返回 `job_id[]` | `python-multipart` 已在 `requirements.txt`；与单文件校验逻辑复用 |
| 批量启动解析 | `POST /jobs/batch-run` 或复用多次 `POST /jobs/{id}/run` + 线程池提交 | 上传后一键并行 run | 前端 `Promise.all` 调 3 次 run 亦可；后端集中提交便于统一并发上限 |
| 详情嵌套路由 | **vue-router** `children`：`/jobs/:id` → hub + `/jobs/:id/tables/:tableKey` + `/jobs/:id/field-b` | 六页工作流 + Hub 总览 | 已在 v1.1 用 hash/history 双模式；子路由共享 `jobId`，无需新路由库 |
| 详情侧栏子导航 | **Element Plus** `el-sub-menu` / `el-menu-item`（`router` 模式）嵌在 `JobDetailLayout` | 五表 + 字段 B 可折叠子菜单 | 与 `AppLayout` 全局 `el-menu` 一致；`el-menu-item-group` 可作「导入表 / 路径 B」分组 |
| 多 job 进度轮询 | 前端 composable **`useJobsPoll`**（扩展 `useJobPoll`：`Map<jobId, interval>` 或单 interval + `Promise.all(getJob)`） | 上传页同时显示 ≤3 条进度 | 不引入 Pinia；上传页状态局部即可 |
| 人工核对表 UI | **Element Plus** `el-table` + `el-input`（可编辑列）+ 现有 `ExportPreview` 拆分 | 字段 / 值 / 页码 / 摘录 | `ValidationPanel`、`PathBPanel` 已用同模式；v1.3 按表拆组件即可 |

### 后端 API / 数据形状（库不变，契约扩展）

| 能力 | 建议端点 / 模型 | 依赖 |
|------|-----------------|------|
| 单表核对行 | `GET /jobs/{id}/verification/{table_key}` → `VerificationRow[]`（field, value, source_page, excerpt, source） | 从已有 `extraction_result` JSON + `preview_service` 列映射聚合；**Pydantic v2** 新 schema，无新 pip 包 |
| 单表 preview 局部读写 | `GET/PATCH /jobs/{id}/preview/{table_key}`（或 query `?table=fee`） | 减轻六页各自拉全量 preview；仍用 openpyxl 重导出 |
| 字段 B 摘录 + 页码 | 扩展 `PathBSnippetRow`：`page: int \| null`、`anchor_id: str \| null` | 见下文「页码」 |
| 并发上限 | 应用层常量 `MAX_PARALLEL_JOBS = 3` + 上传/ run 时计数 `IN_PROGRESS` | SQLite WAL 已在 `test_db_wal.py` 用 3 worker 验证 |

### 页码与摘录（栈层面的唯一「能力缺口」）

当前 `parse` 层无物理页码，仅有 `anchor_id` / 段落索引；`PathBSnippetRow` 亦无 `page` 字段。

| 方案 | 新增依赖 | 推荐 |
|------|----------|------|
| **A. python-docx 页分隔符计数** | 无 | **推荐 v1.3**：遍历 `document.element.body` 中 `w:br[@w:type='page']` + 段落映射，为 snippet 填 `estimated_page`；UI 标注「约第 N 页」 |
| B. 段落序号代替页码 | 无 | 降级：列名为「段落位置」，避免虚假精确页码 |
| C. docx→PDF + 页映射 | `docx2pdf` / LibreOffice 子进程 | **不推荐 v1.3**：Electron 已捆绑 Python，再加 Office/PDF 链路过重，与「内部工具」约束冲突 |

**结论：** v1.3 **不新增** PDF/排版引擎；在 **python-docx** 上扩展页码估算服务即可。

### 明确不引入（Anti-stack）

| 避免 | 原因 | 替代 |
|------|------|------|
| Celery / ARQ / Dramatiq | 桌面单机、≤3 任务、无 Redis | `ThreadPoolExecutor(3)` |
| 多个 `background_tasks.add_task(run_pipeline)` 指望并行 | Starlette 顺序执行 | 一次提交到线程池 |
| Pinia / Vuex | 仅 job 详情子树共享 `jobId` + detail | `provide/inject` 或父 layout `props` + `useJobPoll` |
| `@vueuse/core` | 非必需；poll/防抖可 30 行 composable | 手写 `useJobsPoll` |
| 新表格组件（AG Grid、handsontable） | 运营表列数有限，Element Plus 够用 | `el-table` + 列级 `el-input` |
| 新 Excel 库 | 已用 openpyxl 读写模板 | 保持 |
| aiosqlite / 全 async ORM | 流水线为 sync + 线程；v1.2 已选 sync SQLite | 保持 sync `SessionLocal` per thread |

---

## 前端结构建议（实现约束，非新包）

```
/jobs/:id                    → JobDetailHubView（摘要 + 进入各表）
/jobs/:id/tables/:tableKey   → TableDetailView（product|fee|lock|share|subscription）
/jobs/:id/field-b            → FieldBDetailView
```

- **`JobDetailLayout.vue`**：左侧 `el-menu` 子导航 + `<router-view>`；`activeMenu` 用 `route.path`。
- **上传页**：`el-upload` 增加 `multiple`、`:limit="3"`、`:on-exceed`；`file-list` 展示 3 个待处理项。
- **Composable 契约**：`useJobsPoll(jobIds: Ref<string[]>)` 在任一 job 进入 `PIPELINE_POLL` 时轮询，全部 `TERMINAL` 后停止（复用 `useJobPoll.ts` 常量）。

---

## 后端并发与 SQLite（沿用 v1.2）

| Concern | v1.3 做法 |
|---------|-----------|
| 并行 parse | 每线程独立 `SessionLocal()`（`run_pipeline` 已如此） |
| 写冲突 | 保持 WAL；避免跨 job 单事务写多行 |
| LLM 限流 | 线程池 3 + 现有 `asyncio` 校验批处理；若 API 限流，可在 `pipeline_service` 加 `threading.Semaphore(2)` 仅限制 extract 阶段（**可选**，仍 stdlib） |

---

## 与现有组件的映射

| v1.3 页面 | 复用 / 拆分 |
|-----------|-------------|
| 可编辑 preview | `ExportPreview.vue` → 按 `tableKey` 拆为 `TablePreviewEditor.vue` |
| LLM 校验 | `ValidationPanel.vue` 可保留在 Hub 或并入各表核对区 |
| 字段 B | `PathBPanel.vue` → `FieldBDetailView` + 扩展页码列 |
| 单表下载 | 现有 `downloadBlob(kind)` 路由已分表，子页直接调用 |
| 核对 Excel | 现有 `review-report` 下载；页内表为 **live API**，非新库 |

---

## 安装 / 依赖变更摘要

```bash
# v1.3 预期：requirements.txt 与 frontend/package.json 无 mandatory 新包

# 若采用批量上传单端点，仅需确认已有：
#   python-multipart>=0.0.9
#   fastapi File/UploadFile list 模式

# PyInstaller hiddenimports：无新增第三方模块时不必改 spec
```

**可选（仅当产品坚持「印刷页码」且启发式不足时，post-v1.3 再评估）：**  
`docx2pdf` + Windows 上依赖 Word — 与 Electron 打包目标冲突，**不列入 v1.3**。

---

## 备选方案

| 推荐 | 备选 | 不选原因 |
|------|------|----------|
| ThreadPoolExecutor(3) | 每 job 独立 `multiprocessing.Process` | 内存 ×3、PyInstaller 子进程复杂 |
| vue-router children | 单页 `?tab=` query | 深链接、侧栏高亮、六页状态不清晰 |
| 扩展 extraction JSON + API | 每表独立 SQLite 表 | 过度建模；JSON 已存 `extraction_result` |
| el-sub-menu 详情导航 | 右侧 `el-tabs` | 需求明确要求左侧子菜单 |

---

## 置信度说明

| 领域 | 级别 | 说明 |
|------|------|------|
| 并行调度 | HIGH | FastAPI BackgroundTasks 串行行为有官方讨论；仓库已用单 task |
| 前端路由/EP 组件 | HIGH | 与 v1.1/v1.2 栈一致，代码已存在 `useJobPoll`、`el-menu` |
| 核对 API 形状 | MEDIUM | 需从 `extraction_result` 设计 `table_key` 映射，无新库 |
| 物理页码 | MEDIUM | docx 无内置页码；启发式需合同样本验证 |

---

## 来源

- 仓库：`contract_info/backend/app/api/routes/jobs.py`（`BackgroundTasks` + `run_pipeline`）
- 仓库：`contract_info/frontend/src/composables/useJobPoll.ts`、`router/index.ts`、`UploadView.vue`
- 仓库：`contract_info/backend/tests/test_db_wal.py`（3 并发写）
- FastAPI GitHub Discussions [#13724](https://github.com/fastapi/fastapi/discussions/13724)、[#10682](https://github.com/fastapi/fastapi/discussions/10682) — BackgroundTasks 并发限制
- Element Plus Upload 多文件：`limit` / `multiple`（项目已依赖 EP 2.9）
- vue-router 4 嵌套路由：[官方 guide - Nested Routes](https://router.vuejs.org/guide/essentials/nested-routes.html)

---

*v1.3 STACK 增补调研 — 仅覆盖多文件并行、详情子路由、增强核对 UI；不重研 Electron/SQLite/PyInstaller 基座。*
