# Phase 1: 项目骨架与 docx 解析 - Context

**Gathered:** 2026-05-25  
**Status:** Ready for planning

<domain>
## Phase Boundary

在 `contract_info/` 下交付可运行的**开发骨架**：独立 venv、`backend/` 包、docx→结构化 Document JSON、PostgreSQL **按文件一条记录**落库，以及针对 `example/*.docx` 的 CLI/pytest 验证。

**本阶段不包含：** 字段抽取（Phase 2）、Excel 生成（Phase 3）、上传 API 与前端（Phase 4–5）、PDF/MinerU。

</domain>

<decisions>
## Implementation Decisions

### 目录与交付形态
- **D-01:** Phase 1 对外入口为 **CLI + pytest only**（例如 `python -m backend.cli parse <path>`）；完整 FastAPI 上传链路到 Phase 4。
- **D-02:** 代码布局采用 **`contract_info/backend/`**（`backend/app/` 下 parse、db、models）；`frontend/` 留给 Phase 5；运行时 xlsx 母版放 **`contract_info/templates/`**（从 `example/` 复制，Phase 3 使用）。

### PostgreSQL 与开发环境
- **D-03:** 本地库使用 **`contract_info` 独立 `docker-compose.yml`** 启动 PostgreSQL，与 `ai_bid_management/bid_tool_agents` **不共用**库/卷。
- **D-04:** 主表（建议名 `contract_files`）Phase 1 字段至少包含：
  - 元数据：`id` (uuid)、`filename`、`status` (pending|parsing|parsed|failed)、`created_at`、`updated_at`、`error_message`
  - **`parse_json` (jsonb)**：完整 Document 结构（blocks、tables 等）
  - **`outline_preview` (jsonb)**：章节列表摘要（title、anchor_id、可选 level），便于查询/调试不必解析整份 jsonb
  - **`storage_path` (text)**：原 docx 相对路径（见存储策略）
- **D-05:** 连接配置通过 **`contract_info/.env`**（`DATABASE_URL`），README 说明 compose 启停与迁移。

### docx 解析
- **D-06:** 解析库为 **`python-docx`**（写入 `requirements.txt`）；不在 Phase 1 引入 MinerU/PDF。
- **D-07:** **章节 outline** 使用 **中文序号正则**（如 `第[一二三四五六七八九十百]+章`、`[一二三四五六七八九十]+、`、`^\d+、` 等），匹配基金合同常见体例；**不**依赖 Word Heading 样式作为主路径。
- **D-08:** Document JSON 契约（Phase 1 锁定最小 schema）：
  - 顶层：`source_file`, `format: "docx"`, `metadata`, `outline[]`, `blocks[]`
  - `blocks[]` 项：`id`, `type` (`paragraph`|`table`), `section_id`, `text` 或 `rows`, 可选 `page`
  - 段落块关联最近匹配的 `section_id`；表格单独 block，保留二维 `rows`

### 文件存储
- **D-09:** 原始 docx 落盘 **`contract_info/uploads/{file_id}/original.docx`**（或同名保留扩展名）；DB **`storage_path`** 存相对 `contract_info/` 的路径。
- **D-10:** 大对象 **不进** PostgreSQL（仅 jsonb 存解析结果）；`example/` 下样例在 pytest/CLI 中可直接读，不必先 copy 到 uploads。

### Claude's Discretion
- 精确正则集合与章节层级推断（在 D-07 框架内调优）
- Alembic 迁移 vs 首版 `create_all`（倾向 Alembic 若 compose 已就绪）
- pytest 目录：`backend/tests/` vs `tests/` 顶层
- `outline_preview` 由 parse 管道自动从 `outline` 投影生成

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目与范围
- `contract_info/.planning/PROJECT.md` — 产品目标、Out of Scope
- `contract_info/.planning/REQUIREMENTS.md` — DOC-01–03, DEV-01–02
- `contract_info/.planning/ROADMAP.md` — Phase 1 成功标准与建议目录
- `contract_info/.planning/research/SUMMARY.md` — 推荐栈（FastAPI/Postgres 等，Phase 1 仅用其中 PG+python-docx 部分）

### 业务与样例（解析测验用）
- `contract_info/example/` — 样例 docx 与 xlsx 母版（Phase 1 读 docx）
- `contract_info/FIELD_SPEC.md` — 字段规格（Phase 2 用；Phase 1 仅需理解 outline/章节与后续 block 溯源）
- `contract_info/template_analysis.txt` — 模板 sheet 结构备忘

### 可参考（不耦合）
- `ai_bid_management/bid_tool_agents/docs/troubleshooting-postgres-docker-password.md` — Docker PG 口令与卷初始化注意点

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **无** `contract_info/backend/` 代码（greenfield）；`ai_bid_management/bid_tool_agents/backend/app/tools/document/parser.py` 仅作**模式参考**（Document 结构、解析分层），不 import、不共用部署。

### Established Patterns
- 子项目规划在 **`contract_info/.planning/`**，执行 GSD 命令时 cwd 应为 **`contract_info`**。
- 与评标项目分离：独立 venv、独立 compose、独立 DB。

### Integration Points
- Phase 2 将读取 DB 中 `parse_json` + `outline_preview` 做抽取。
- Phase 4 API 将写入 `uploads/{file_id}/` 并更新 `contract_files.status`。

</code_context>

<specifics>
## Specific Ideas

- 用户为后端开发；首期 **docx 测试**即可，批量 PDF 后置。
- 数据库 **以每个上传文件为单位** 保存（一条 `contract_files` 记录）。
- 测验代码在 **虚拟环境** 中安装依赖并运行。

</specifics>

<deferred>
## Deferred Ideas

- **最小 FastAPI /health** — 用户选 CLI-only，留 Phase 4
- **复用 bid_tool Postgres** — 已拒绝
- **Heading 样式识别 outline** — 已拒绝，仅用中文正则
- **Phase 1 字段抽取 / Excel** — Phase 2–3

### Reviewed Todos (not folded)
（无待办匹配）

</deferred>

---
*Phase: 01-docx*  
*Context gathered: 2026-05-25*
