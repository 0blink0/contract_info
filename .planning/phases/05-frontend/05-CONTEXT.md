# Phase 5: 前端上传与下载 - Context

**Gathered:** 2026-05-25  
**Status:** Ready for planning

<domain>
## Phase Boundary

在 `contract_info/frontend/` 交付 **Vue 3 + Vite + TypeScript** 单页应用：运营上传 docx、手动触发处理、轮询状态、查看历史任务、下载两个 xlsx。通过 Phase 4 API 通信；本阶段可 **小幅扩展** 后端（任务列表、warnings 摘要）以支撑 UI。

**本阶段包含：** 上传区、任务历史列表、当前任务详情（步骤条）、warnings 可展开、失败重试、双下载按钮、Vite dev proxy、README 前端启动说明、可选生产构建说明。

**本阶段不包含：** 用户登录/OAuth、批量 ZIP 后端、WebSocket、PDF、字段在线编辑、CRM 对接、移动端专用布局。

</domain>

<decisions>
## Implementation Decisions

### 技术栈与目录
- **D-01:** **`contract_info/frontend/`**，**Vue 3 + Vite + TypeScript**（与 research 一致）。
- **D-02:** UI 文案 **中文**，面向运营非技术人员；布局简洁（上传 + 左侧/上方历史列表 + 主区详情）。

### 交互流程
- **D-03:** **上传后不自动 run**；成功上传后提示并高亮 **「开始处理」**，用户点击后 `POST /api/v1/jobs/{id}/run`。
- **D-04:** 上传成功后在历史列表 **追加/刷新** 该项，并选中为当前任务。
- **D-05:** 处理中 **轮询** `GET /api/v1/jobs/{id}`（建议间隔 **2–3 秒**），离开进行中的任务时停止轮询。
- **D-06:** **`failed` / `extraction_failed` / `export_failed`** 显示 **「重试」**，再次 `POST .../run`（续跑，与 Phase 4 一致）。

### 状态展示（步骤条）
- **D-07:** **三步步骤条：** **解析 → 抽取 → 导出**。
- **D-08:** 与 API 细粒度 status 映射（示例）：
  - `pending`（已上传未 run）— 步骤条均未开始或仅显示「待处理」
  - `parsing` — 第 1 步进行中
  - `parsed` — 第 1 步完成
  - `extracting` — 第 2 步进行中
  - `extracted` — 第 2 步完成
  - `exporting` — 第 3 步进行中
  - `exported` — 三步完成，显示下载区
  - `failed` / `extraction_failed` / `export_failed` — 对应步骤标红 + `error_message`

### Warnings
- **D-09:** 展示 **可展开的 warnings 列表**（字段/消息摘要）；需 Phase 5 **扩展 GET job** 返回 `extraction_warnings` 数组（或 `warnings` 摘要对象列表），**不**返回完整 `parse_json`/`extraction_result`。

### 下载
- **D-10:** **`exported` 后两个按钮：**「下载产品要素」「下载运营费率」，分别打开/下载现有两个 GET 端点；**不做** zip（ROADMAP「或 zip」本阶段不实现）。

### API Key
- **D-11:** **开发：** 后端 `API_KEY` 留空时不校验，前端 **不提供** Key 配置页。
- **D-12:** **生产/固定内网：** 通过 **`VITE_API_KEY`** 构建时注入，所有 `fetch` 统一加 `X-API-Key`（未设置则不带 header）。

### 任务历史列表
- **D-13:** v1 提供 **近期任务列表**（非单任务覆盖式）：新增 **`GET /api/v1/jobs?limit=20`**（按 `created_at` 降序），项含 `job_id`、`filename`、`status`、`created_at`；点击切换当前详情。
- **D-14:** 列表 **不** 做分页 UI（limit 固定 20 即可）；不做搜索/筛选（v2）。

### 开发与部署
- **D-15:** **Vite dev server** `proxy`：`/api` → `http://127.0.0.1:8000`；前端 `fetch('/api/v1/...')` 同源。
- **D-16:** 生产建议：构建 `frontend/dist`，由 Nginx/静态服务托管，`/api` 反代到 Uvicorn（文档说明即可，不必本阶段写 Docker 一体镜像）。

### Claude's Discretion
- 组件库：Element Plus / Naive UI / 无库纯 CSS（与 Vue 3 兼容即可）
- 轮询退避（失败网络时）
- 上传拖拽 vs 仅按钮
- `GET /jobs` 列表响应 Pydantic 模型命名

</decisions>

<specifics>
## Specific Ideas

- 流程：选文件 → 上传 → 列表出现 pending → 点「开始处理」→ 步骤条走动 → 完成后两个下载。
- 历史列表方便运营连续处理多份合同，无需记 job_id。
- Phase 4 已预留 CORS `localhost:5173`；优先 proxy 减少 CORS 配置负担。

</specifics>

<canonical_refs>
## Canonical References

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — UI-01
- `.planning/ROADMAP.md` — Phase 5 成功标准
- `.planning/research/SUMMARY.md` — Vue 3 + Vite

### API（Phase 4 + 本阶段扩展）
- `.planning/phases/04-backend-api/04-CONTEXT.md` — upload / run / poll / download 契约
- `contract_info/README.md` — HTTP API curl 示例
- `contract_info/backend/app/api/routes/jobs.py` — 拟扩展 list + warnings
- `contract_info/backend/app/api/schemas.py` — JobDetailResponse

### Prior phases
- `.planning/phases/03-xlsx-export/03-CONTEXT.md` — 两个 xlsx 产物含义

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 4 全套 `/api/v1` 端点已实现；CORS + `X-API-Key` 依赖已就绪。
- `JobDetailResponse` 已有 `extraction_warnings_count`，需扩展列表字段供 D-09。

### Established Patterns
- 后端 `contract_info/backend/`；前端 greenfield `frontend/`。
- 状态字符串与步骤条映射由前端 constants 维护。

### Integration Points
- 新增 `JobListItem` schema + `GET /jobs` 路由（Phase 5 小改 backend）。
- `frontend/vite.config.ts` proxy `/api`。
- `frontend/src/api/client.ts` 封装 fetch + 可选 `VITE_API_KEY`。

</code_context>

<deferred>
## Deferred Ideas

- **浏览器 JSZip 打包** — 用户选两个按钮；zip 入 backlog
- **后端 ZIP 端点** — Phase 4 已推迟
- **WebSocket 实时进度** — 轮询足够 v1
- **多文件批量上传队列** — v2 DOC-11
- **登录与多用户** — 仅 API Key 环境级

</deferred>

---

*Phase: 05-frontend*  
*Context gathered: 2026-05-25*
