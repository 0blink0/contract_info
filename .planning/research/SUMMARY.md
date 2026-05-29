# CTRX v1.3 研究摘要

**项目:** 合同要素抽取（CTRX）— 多文件并行与详情页重构  
**领域:** Electron 桌面 · FastAPI + Vue 3 + SQLite（v1.2 基座不变）  
**调研日期:** 2026-05-29  
**整体置信度:** HIGH（栈/功能/架构基于仓库与 `PROJECT.md`）；页码端到端为 MEDIUM

---

## Executive Summary

CTRX v1.3 在 **已交付的 v1.2 桌面栈** 上做增量演进：不引入 Celery、Pinia 或新表格库，核心是用 **stdlib `ThreadPoolExecutor(3)`** 替代「多次 `BackgroundTasks.add_task`」的假并行，用 **vue-router 嵌套 children + Element Plus 子菜单** 拆解 v1.2 的 `JobDetail.vue` 单体页，并保留「每 docx 一 job、五表 xlsx + 路径 B 手录」的业务闭环。

产品形态仍是 **运营半自动录入工具**：一次最多 3 份 docx 并行解析，详情区变为 **Hub 总览 + 六页工作流**（五张导入表 + 字段 B），每页三件套为可编辑 preview、摘录核对表（字段/值/页码/原文）、单表下载。Hub 只做摘要与导航，避免重复 v1.2 长页堆叠。

**主要风险** 集中在三类：(1) **全量 `PUT /preview` 在分表保存时清空其它表**；(2) **单 job 轮询模型无法支撑上传页 3 路进度**；(3) **页码字段尚未在 API/解析层统一**。缓解路径：优先 **分表 PATCH/GET preview API**、**`useJobsPoll` 注册表式轮询**、**python-docx 页分隔符估算页码**（不引入 PDF 引擎）。并行上限 3 既是产品约束，也是 SQLite/LLM/单进程 Python 的资源约束，需后端 409 守门 + 前端 `limit=3`。

---

## Stack additions（v1.3 增补，无新运行时依赖）

| 增补 | 实现 | 用途 |
|------|------|------|
| 并行流水线 | `ThreadPoolExecutor(max_workers=3)` 单例，`pipeline_service` 提交 `run_pipeline` | 真并行 ≤3；勿依赖多个 BackgroundTask |
| 批量上传（可选） | `files: list[UploadFile]` 或 3×`POST /upload` | 上传页多 docx |
| 嵌套路由 | vue-router `children`：`/jobs/:id` + 五表 + `path-b` | Hub + 六页深链接 |
| 详情子导航 | `JobDetailLayout` + `AppLayout` 内 `el-sub-menu` | 左侧可折叠五表 + 字段 B |
| 多 job 轮询 | `useJobsPoll`（扩展 `useJobPoll`） | 上传页 ≤3 进度卡 |
| 核对 UI | `el-table` + `el-input` 可编辑列 | 字段/值/页码/摘录 |
| 页码 | python-docx `w:br[@w:type='page']` 估算 | **不**引入 docx2pdf/LibreOffice |

**明确不引入:** Celery/ARQ、Pinia、AG Grid、aiosqlite、PDF 排版引擎。

**版本/基座:** FastAPI 0.110+、Vue 3.5、Element Plus 2.9、Electron 42、SQLite WAL — 与 v1.2 一致。

---

## Feature priorities

### P0 — 发布门槛（Must ship）

1. **上传页 ≤3 docx**：独立 job、并行进度、完成后进详情  
2. **Hub**（`/jobs/:id`）：五表 + 字段 B 摘要、「进入详情」  
3. **左侧子导航六页**：每页 — 可编辑区 + 摘录核对表 + 单表下载  
4. **字段 B 专页**：业绩报酬/开放日摘录（页码就绪则显示，否则 follow-up）  
5. **回归 v1.2**：设置向导、Electron、删除 job、五表 xlsx 正确性  

### P1 — Should ship

- Hub 上 Validation fail/warn 徽章 + 一键展开校验面板  
- 路由切换 **dirty** 提示（`beforeRouteLeave`）  
- 上传页「批量开始处理」（可选）  

### Defer（post-v1.3 / v2）

- 按表局部 save（若 P0 用分表 API 则部分已覆盖）、PATHB 枚举映射、>3 队列/ZIP、DB 清理 UI、Linux clean-VM  

### Anti-features（v1.3 禁止）

- Hub 塞满 `ExportPreview` + 全量面板（重复 monolith）  
- 六页各触发全量 LLM 校验  
- >3 并行、CRM 自动录入、PDF/OCR、取消摘录列  

---

## Architecture decisions

### 路由与布局

- **父路由** `JobDetailLayout`：`/jobs/:id` + `children`（Hub 默认、`product-elements` … `subscription-fee-rates`、`path-b`）  
- **子菜单挂在 `AppLayout`**（非 Layout 内第二栏），`route.params.id` 动态链接  
- **Hub**：元信息、stepper、摘要卡、`ValidationPanel`（job 级）、`WarningsList` — **无**大表格  
- **表页** `JobTableView`：从 `ExportPreview` 拆单 tab + 核对表 + `downloadBlob(kind)`  
- **字段 B** `JobPathBView`：自 `PathBPanel` 抽出，强化摘录/页码  

### API（推荐新增）

| 端点 | 目的 |
|------|------|
| `GET/PUT /jobs/{id}/preview/{section}` | 分表读写，避免全量覆盖 |
| `GET /jobs/{id}/verification/{table_key}` 或 review-rows | 核对表四列 JSON |
| `count_in_progress` + `POST /run` → **409**（第 4 路） | 并行守门 |
| `POST /upload/batch`（可选） | 简化上传状态机 |

### 并发与数据流

```
选 1–3 docx → POST /upload (×n) → job_ids[]
→ POST /run（未满 3 in-progress）→ useJobsPoll 批量 GET
→ 完成 → /jobs/:id Hub → 子路由编辑 → 分表 PUT → 单表下载
```

- 每线程独立 `SessionLocal()`；SQLite WAL；**in-progress** 状态计入并发槽  
- **Layout 单 poll + provide/inject**，子页不各自 `setInterval`  

### 构建顺序（架构文档 5 步 → 路线图主题）

1. 后端：并行守门 + 分表 preview API  
2. 路由骨架 + `JobDetailLayout` + 子菜单  
3. `JobTableView` 五表 + 分表 GET/PUT + 下载  
4. Hub 摘要 + `JobPathBView`  
5. `UploadView` 多文件 + 并行 run/轮询  

---

## Watch Out For（高发陷阱）

| # | 陷阱 | 预防 |
|---|------|------|
| 1 | 单表保存走全量 `PUT /preview` → **其它表被 `or []` 清空** | **分表 PATCH/PUT** 或父级缓存全量 merge；契约测试未提交表行数不变 |
| 2 | 多个 `BackgroundTasks` / 无池 → **假并行或 SQLite locked** | `ThreadPoolExecutor(3)` + 409 上限；3× pipeline 集成测（可 mock LLM） |
| 3 | `useJobPoll` 单实例 → **上传页仅最后一个 job 更新** | `useJobsPoll` / 注册表，每 jobId 全局一条 poll 链 |
| 4 | 路由切换卸载组件 → **未保存编辑丢失** | `dirtyTables` + `beforeRouteLeave`；Hub 仅摘要不拉全量 preview×5 |
| 5 | 3 路并行 extract → **LLM 429/校验全 skipped** | 全局 `Semaphore(1)` 校验队列，或 Hub 显式「运行校验」 |
| 6 | 子路径 `activeMenu` / 深链接刷新无 job 元数据 | 嵌套 `redirect`；父 Layout 一次 `loadDetail` |
| 7 | 未保存即下载 → **旧 xlsx** | dirty 时禁用下载或强提示 |
| 8 | 页码缺失却 UI 标「精确页码」 | 估算页标注「约第 N 页」或降级段落位置 |

---

## Recommended phase themes（路线图建议）

基于依赖 **底→顶** 与陷阱耦合，建议 **5 个阶段主题**（可与 GSD phase 编号对齐）：

### Theme 1：后端并行与分表契约
**理由:** 阻塞真并行与分表 UI；陷阱 #1 #2 #8 的根因在此。  
**交付:** `ThreadPoolExecutor(3)`、`count_in_progress` + run 409、`GET/PUT preview/{section}`、可选 `verification/{table_key}`、页码估算服务（MVP：estimated_page）。  
**功能:** 并行解析守门、按表保存。  
**规避:** 全量 PUT 清空、BackgroundTasks 假并行。  
**研究标记:** 页码启发式需 **样本验证**（`/gsd-research-phase` 若合同样本复杂）。

### Theme 2：详情路由骨架与导航
**理由:** 前端信息架构前提；无此无法拆页。  
**交付:** `JobDetailLayout`、`JobDetailSubMenu`、`JobHubView` 占位、嵌套 `children`、列表/上传跳转 Hub。  
**功能:** Hub 入口、左侧六链。  
**规避:** 双栏侧栏、Hub 嵌全量 ExportPreview（#4 #6）。  
**研究标记:** 标准 vue-router 模式 — **可跳过深研**。

### Theme 3：五表独立工作页
**理由:** 核心业务 UX；依赖 Theme 1 分表 API。  
**交付:** `JobTableView` ×5、核对表组件、单表下载、接分表 GET/PUT。  
**功能:** 可编辑 + 摘录核对 + 下载（P0）。  
**规避:** 六页各 poll、未保存下载（#3 #7）。  

### Theme 4：Hub 摘要与字段 B 专页
**理由:** 完成「总览仅入口」与路径 B 升级。  
**交付:** Hub 卡片（行数/校验徽章）、`JobPathBView`、Validation 折叠/抽屉；扩展 PathB `page` 字段。  
**功能:** Hub 摘要、字段 B 摘录+页码（页码可 partial 验收）。  
**规避:** Hub N+1 全量 preview（#12）；六页各跑 LLM（#5）。  
**研究标记:** 若 extraction 无 page 元数据 — **规划期 spike**。

### Theme 5：多文件上传与并行进度 UI
**理由:** 用户可见的 v1.3  headline；依赖 Theme 1 守门 + Theme 3 可跳转详情。  
**交付:** `UploadView` `multiple` `limit=3`、`useJobsPoll`、并行 upload/run、进度卡、第四份 UI/API 拒绝。  
**功能:** ≤3 并行上传与解析（P0）。  
**规避:** 单 `activeJobId`、无 batch 契约混乱（#3 #7）。  
**研究标记:** 可选 `POST /upload/batch` — 产品定夺即可。

### Phase ordering rationale

- **先后端契约再前端拆页**，否则分表保存必踩陷阱 #1。  
- **路由骨架早于表页**，便于增量验收导航。  
- **上传多文件放最后**，避免在无分表 API/无子路由时堆 UI 债务。  
- Theme 1 与 Theme 5 共享并行栈研究结论，但 UI 依赖后端 409 与 poll 注册表。

### Research flags

| 主题 | 深研？ | 说明 |
|------|--------|------|
| Theme 1 页码 / verification API | **建议** | docx 无内置页码；`table_key` 映射需对照 `extraction_result` |
| Theme 4 Hub 摘要字段 | **可选** | 扩展 `JobDetailResponse` vs 轻量 summary endpoint |
| Theme 2 嵌套路由 | 跳过 | 项目已有 hash/history 双模式先例 |
| Theme 3 Element 表格 | 跳过 | 与 v1.2 `ExportPreview` 同模式 |

---

## Confidence Assessment

| 领域 | 置信度 | 说明 |
|------|--------|------|
| Stack | **HIGH** | 仓库现状 + FastAPI #13724 BackgroundTasks 串行 |
| Features | **HIGH** | `PROJECT.md` + 组件直接检视 |
| Architecture | **HIGH** | 路由/download kind 已对齐；分表 API 为推荐非强制 MVP |
| Pitfalls | **HIGH** | `preview_edit_service` 全量语义、单 poll 已代码验证 |
| 页码端到端 | **MEDIUM** | 启发式需合同样本；无 page 时字段 B 可降级验收 |

**整体:** HIGH（实施路径清晰），页码与核对 JSON API 为主要不确定性。

### Gaps to address（规划期）

- **页码:** 解析层 `estimated_page` vs UI「约第 N 页」文案；PathB `source_snippets` 元数据扩展  
- **核对 rows API:** 避免前端重复拼装与 `review_workbook` 列不一致  
- **pending 是否占并发槽:** 与产品确认（仅 in-progress 计入为推荐）  
- **按表 PUT vs 父级全量缓存:** Theme 1 必须二选一，勿混用  

---

## Sources

### 项目内（HIGH）
- `contract_info/.planning/PROJECT.md` — v1.3 目标与 Out of Scope  
- `contract_info/.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md`  
- `backend/app/api/routes/jobs.py`, `services/pipeline_service.py`, `preview_edit_service.py`  
- `frontend/src/composables/useJobPoll.ts`, `components/JobDetail.vue`, `ExportPreview.vue`  
- `backend/tests/test_db_wal.py` — WAL 短写，非 pipeline 压测  

### 外部（MEDIUM–HIGH）
- [FastAPI Discussion #13724](https://github.com/fastapi/fastapi/discussions/13724) — BackgroundTasks 顺序执行  
- [vue-router Nested Routes](https://router.vuejs.org/guide/essentials/nested-routes.html)  

---
*研究完成: 2026-05-29*  
*可进入路线图: 是 — 见 Recommended phase themes*
