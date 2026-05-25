# Phase 4: 后端 API - Context

**Gathered:** 2026-05-25  
**Status:** Ready for planning

<domain>
## Phase Boundary

在 `contract_info/backend/` 交付 **FastAPI + Uvicorn** HTTP 层：上传 docx、查询任务状态、触发处理流水线、下载两个 xlsx。复用 Phase 1–3 的 `parse_service` / `extract_service` / `export_service` 与 `contract_files` 表。

**本阶段包含：** `/api/v1` 路由、API Key 鉴权、上传校验（`.docx`）、分步上传 + `run` 续跑、异步后台处理、job 状态 JSON、两个下载端点、pytest/API 测试、README 运行说明（可部分满足 DEV-01）。

**本阶段不包含：** Vue/前端页面（Phase 5）、ZIP 打包下载、批量上传、WebSocket 推送、OAuth/多用户、PDF、独立 `jobs` 表。

</domain>

<decisions>
## Implementation Decisions

### 任务模型（job = file）
- **D-01:** **`contract_files.id` 即 API 的 `job_id`**；不新建 `jobs` 表。
- **D-02:** **GET job 返回 DB 细粒度 `status`**（`pending`、`parsing`、`parsed`、`extracting`、`extracted`、`exporting`、`exported` 及各 `*_failed`），不映射为单一的 `completed`；可同时返回 `filename`、`error_message`、`product_xlsx_path`、`fee_xlsx_path`（相对路径或仅在有文件时暴露）、`extraction_warnings` 摘要等，供 Phase 5 UI 直接展示。
- **D-03:** 上传成功后记录 **`status=pending`**，`storage_path` 指向 `uploads/{file_id}/` 下文件；**不在 upload 内执行 parse**。

### 处理模式（上传 + run 续跑）
- **D-04:** **两步 API：** `POST /api/v1/upload` 仅接收文件并入库；`POST /api/v1/jobs/{id}/run` 触发处理。
- **D-05:** **`run` 从当前状态续跑**（与 CLI 三步等价，但可一次调用多步）：
  - `pending` → parse → extract → export
  - `parsed`（或 `parse_failed` 修复后）→ extract → export
  - `extracted`（或 `extract_failed`）→ export only
  - `exported` → **409** 或明确 no-op（已完成的不再跑）
  - 正在 `parsing`/`extracting`/`exporting` 时再次 `run` → **409 Conflict**
- **D-06:** **`run` 异步：** 立即 **`202 Accepted`**，响应体含 `job_id` 与当前/即将进入的 `status`；后台任务（FastAPI `BackgroundTasks` 或等价）执行续跑逻辑；客户端 **轮询 GET job** 直至 `exported` 或 `*_failed`。
- **D-07:** 后台任务内复用现有 **`persist_parse` / `persist_extract` / `export_service`** 逻辑（可抽 `orchestrator` 服务封装续跑分支，避免 HTTP 层重复业务代码）。

### API 设计与路由
- **D-08:** 所有业务路由加前缀 **`/api/v1`**：
  - `POST /api/v1/upload` — multipart `file`，返回 `{ "job_id": "<uuid>", "status": "pending", "filename": "..." }`
  - `POST /api/v1/jobs/{job_id}/run` — 202，触发续跑
  - `GET /api/v1/jobs/{job_id}` — 任务详情与状态
  - `GET /api/v1/jobs/{job_id}/download/product-elements` — 产品要素 xlsx
  - `GET /api/v1/jobs/{job_id}/download/fee-rates` — 运营费率 xlsx
- **D-09:** 可选 **`GET /api/v1/health`**（或 `/health` 在根）用于探活；鉴权策略见下（health 可免 Key）。
- **D-10:** 错误约定：**400** 非 docx / 无文件；**401** API Key 缺失或错误；**404** job 不存在；**409** 状态不允许 run 或重复 run；**404/409** 下载时未 `exported` 或文件缺失（实现时二选一并在测试中固定）。

### 鉴权、CORS 与上传约束
- **D-11:** 首期 **API Key**：请求头 **`X-API-Key`**，与 **`.env` 中 `API_KEY`** 比对；未配置 `API_KEY` 时开发模式可文档化「跳过校验」或启动失败（由实现择一并在 README 写明）。
- **D-12:** **CORS** 为 Phase 5 预留：允许本地前端源（如 `http://localhost:5173`），具体列表可配置；生产域名后续再加。
- **D-13:** 上传 **仅校验扩展名为 `.docx`**（大小写不敏感）；**不设文件大小上限**（内网/受信环境）。

### 下载
- **D-14:** **两个独立下载端点**（对齐 API-03 / XLS-03）；**仅当 `status=exported`** 且磁盘路径存在时返回文件。
- **D-15:** **`Content-Type`:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`；**`Content-Disposition: attachment`**，文件名建议 `product_elements.xlsx` / `fee_rates.xlsx`（或带原始合同 stem 前缀，实现可酌）。
- **D-16:** **ZIP 打包** 留给 Phase 5（用户确认 Phase 4 仍双端点）。

### CLI 与测试
- **D-17:** **保留现有 CLI**（parse/extract/export）；API 为并行入口，不删除 CLI。
- **D-18:** pytest：**TestClient** 测 upload → run → poll（可 mock 后台或用小 fixture docx）；鉴权用测试用 `API_KEY`；DB 集成测与 Phase 1–3 相同（Docker 可选 skip）。

### Claude's Discretion
- `run` 对 `*_failed` 是否允许重试及如何重置 `error_message`
- 后台任务异常与 session 生命周期（每步独立 session vs 单 session）
- `GET /jobs/{id}` 是否包含 `outline_preview` 长度或仅计数（避免巨大 JSON）
- Uvicorn 启动命令、`backend.app.main:app` 模块位置
- OpenAPI 标签与中文 description

</decisions>

<specifics>
## Specific Ideas

- 流程类似「先上传拿单号，再点处理」——运营可先传多个文件再逐个触发 `run`。
- Postman/curl 验证 ROADMAP 成功标准：upload → run → 轮询 → 两个 download。
- 与 `ai_bid_management` 一致采用 FastAPI，但路由用 `/api/v1` 前缀便于版本化。

</specifics>

<canonical_refs>
## Canonical References

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — API-01–03、XLS-03（下载经 API）
- `.planning/ROADMAP.md` — Phase 4 目标与成功标准
- `.planning/research/SUMMARY.md` — FastAPI + Uvicorn 栈

### Prior phase decisions
- `.planning/phases/01-docx/01-CONTEXT.md` — `contract_files`、uploads 路径、Phase 4 才上 FastAPI
- `.planning/phases/02-extract/02-CONTEXT.md` — 抽取 JSON、status 链
- `.planning/phases/03-xlsx-export/03-CONTEXT.md` — `exports/{file_id}/`、`product_xlsx_path` / `fee_xlsx_path`、`exported`

### Field & export behavior
- `FIELD_SPEC.md` — 字段语义（API 响应可选摘要）
- `backend/app/services/parse_service.py` — 解析落库
- `backend/app/services/extract_service.py` — 抽取落库
- `backend/app/services/export_service.py` — xlsx 生成

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/parse_service.py` — `persist_parse`（含 uploads 复制）；upload 端点可只做到「存文件 + insert pending」，run 时再调解析逻辑或拆 `parse_file_id`。
- `backend/app/services/extract_service.py` — `persist_extract(file_id)`，需已 `parsed`。
- `backend/app/services/export_service.py` — `persist_export(file_id)`，需已 `extracted`。
- `backend/app/models/contract_file.py` — 全字段已具备 API 响应所需列。

### Established Patterns
- `status` 字符串状态机贯穿 CLI 与 DB；API **原样暴露** granular status。
- 路径均相对 `PROJECT_ROOT`（`uploads/`、`exports/`）。
- 配置集中在 `backend/app/config.py` + `.env`。

### Integration Points
- 新建 `backend/app/main.py`（或 `api/` 包）挂载路由与中间件（CORS、API Key dependency）。
- 新建 `backend/app/services/pipeline_service.py`（建议名）封装 **D-05** 续跑分支，供 `run` 后台任务调用。

</code_context>

<deferred>
## Deferred Ideas

- **ZIP 下载** — Phase 5 与 UI 一键下载一并考虑。
- **WebSocket / SSE** 推送进度 — 轮询足够 v1；可入 backlog。
- **同步 upload 一条龙** — 用户选择分步；不实现单请求阻塞全流程。
- **上传大小限制 / 病毒扫描** — 内网 v1 不设上限；若上公网再加强。
- **Bearer Token / OAuth** — 仅用 X-API-Key v1。

</deferred>

---

*Phase: 04-backend-api*  
*Context gathered: 2026-05-25*
