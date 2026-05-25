# Phase 2: 字段抽取引擎 - Context

**Gathered:** 2026-05-25  
**Status:** Ready for planning

<domain>
## Phase Boundary

从 Phase 1 的 **Document JSON**（`parse_json`）抽取 **P1 产品要素 + 运营费率**，输出结构化 JSON 并写入 PostgreSQL（`extraction_result` / `extraction_warnings`），通过 **CLI + pytest** 验证。

**本阶段包含：** 规则抽取、按章节窗口的 LLM 补全、JSON Schema 校验、字段溯源与枚举 warnings、字典 JSON、DB 迁移与 `extract` 子命令。

**本阶段不包含：** Excel 填充（Phase 3）、HTTP API/上传（Phase 4）、前端（Phase 5）、份额锁定期子表行、分级份额子表行、路径 B 页面录入、RAG、PDF。

</domain>

<decisions>
## Implementation Decisions

### P1 范围与输出形态
- **D-01:** 产品要素主表抽取 **18 个 MVP 字段 + FIELD_SPEC 中其它标为 P1 的列**（如产品类型、备案编码、成立日期等），P2/P3 列本阶段不抽。
- **D-02:** **锁定期**仅在主表输出摘要字段；**不**输出 `lock_periods[]` 子表（留给后续阶段）。
- **D-03:** **不**输出 `share_classes[]` 分级子表；仅主表 **份额结构** 等枚举字段。
- **D-04:** 运营费率至少 **管理费 + 托管费** 各一行；合同有投资顾问条款时增加 **投资顾问费** 行。每行含 P1 必填：基金名称、运营费类型、计费频率、计费基准（若有）、费率（%/年）。

### 规则与 LLM 分工
- **D-05:** **规则优先**；对规则未覆盖或枚举/混合字段，按 **章节窗口** 调用 LLM（基本情况、费用、申赎等），每窗一次结构化 JSON（`hybrid_batch`，非逐字段刷屏）。
- **D-06:** 规则层主要依据 **`outline` 章节锚点 + `contract_keywords.txt` + 表格 blocks**；Phase 2 允许在 keywords 上增补正则/表格模式。
- **D-07:** LLM **失败或 JSON 不合 schema**：**重试 1 次**；仍失败则保留已抽字段，失败字段为空并记入 `extraction_warnings`，不整单 `failed`（除非 DB/IO 级错误）。

### LLM 接入
- **D-08:** **`contract_info/.env` 独立配置**：`OPENAI_API_KEY`、`OPENAI_BASE_URL`（或等价）、`LLM_MODEL`；**不**依赖 bid_tool 部署耦合（可参考其调用模式）。
- **D-09:** 具体模型型号写在 **`.env.example`**，由运营/开发自选（Claude 规划时不锁死单一型号）。
- **D-10:** 无 API Key 时：**pytest 跳过 LLM 用例**；CLI 仍可跑纯规则层。
- **D-11:** LLM 输出须经 **Pydantic JSON Schema 严格校验**；不合 schema 视为该次调用失败，进入 D-07 重试/警告流程。

### 溯源与校验（EXT-03 / EXT-04）
- **D-12:** 每字段（至少全部 P1 必填与费率行）记录 **`block_id` + `section_id` + `snippet`**。
- **D-13:** 置信度 **三级**：`high` / `medium` / `low`（规则命中倾向 high，LLM 倾向 medium，兜底 low）。
- **D-14:** 枚举不合规：**写入 `warnings`，保留 LLM 原文到 `suggestions`**，不阻断、不清空字段。
- **D-15:** 字典从 **`example/产品要素-2.xlsx` 预导出为 `contract_info/dicts/*.json`**，校验时读 JSON（便于 diff 与版本管理）。

### CLI 与数据库
- **D-16:** **`parse` 与 `extract` 分离**；`extract` 可接受 docx 路径，或对已 `--persist` 的 `file_id` 读 `parse_json`。
- **D-17:** DB 新增 **`extraction_result` (jsonb)** 与 **`extraction_warnings` (jsonb)**（分列，warnings 不塞进 result 顶层以免膨胀）。
- **D-18:** `status` 扩展：**`parsed` → `extracting` → `extracted` | `extraction_failed`**（解析失败仍用 Phase 1 的 `failed`/`parsed` 语义）。
- **D-19:** 示例合同（正仁）测验：**18+ 扩展 P1 字段大部分有值** + 管理费/托管费（+投顾若有）非空；允许合理 `warnings`。

### Claude's Discretion
- 各章节窗口的段落选取上限与 token 预算
- `extraction_result` 内部 JSON 分区命名（`product_elements` / `fee_rates` / `_meta`）
- Alembic 迁移编号与是否同步更新 `outline_preview` 查询辅助
- 规则层具体正则与表格列映射实现细节

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目与范围
- `contract_info/.planning/PROJECT.md` — 路径 A、规则+LLM、无 RAG
- `contract_info/.planning/REQUIREMENTS.md` — EXT-01–04
- `contract_info/.planning/ROADMAP.md` — Phase 2 成功标准
- `contract_info/.planning/phases/01-docx/01-CONTEXT.md` — Document JSON、CLI-only、DB 表基线

### 字段与规则
- `contract_info/FIELD_SPEC.md` — P1 字段、费率表、字典依赖、抽取方法列
- `contract_info/contract_keywords.txt` — 章节/术语锚点
- `contract_info/field_instructions.txt` — 运营填写说明摘要
- `contract_info/product_fields.txt` — 要素列清单
- `contract_info/template_analysis.txt` — xlsx sheet 结构

### 样例与字典源
- `contract_info/example/正仁1号私募证券投资基金私募基金合同.docx` — 主测验合同
- `contract_info/example/产品要素-2.xlsx` — 要素母版 + 字典 sheet 来源
- `contract_info/example/产品运营费率导入模板-1.xlsx` — 费率母版列定义

### 已实现代码（Phase 1）
- `contract_info/backend/app/parse/schemas.py` — Document / Block / Outline
- `contract_info/backend/app/parse/outline.py` — 中文章节正则
- `contract_info/backend/app/models/contract_file.py` — 待扩展 extraction 列
- `contract_info/backend/cli.py` — 扩展 `extract` 子命令

### 可参考（不 import）
- `ai_bid_management/bid_tool_agents/backend/app/services/document_pipeline/metadata_llm.py` — 规则+LLM 合并、分块
- `ai_bid_management/bid_tool_agents/backend/app/agents/evaluation/prompts_evidence.py` — 结构化 JSON 提示模式

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`parse_json` / `outline_preview`**：`contract_files` 已存 Phase 1 解析结果，extract 可直接消费。
- **`contract_keywords.txt`**：封面/当事人/费用等锚点，规则层第一数据源。
- **`document_to_dict` / Block `section_id`**：溯源可挂到现有 block id。

### Established Patterns
- **CLI + pytest only**（Phase 1 D-01）；无 FastAPI。
- **独立 venv + compose Postgres**（5433）；Alembic 迁移。
- **中文章节正则 outline**，非 Heading 样式。

### Integration Points
- Phase 3 `export_xlsx` 读取 `extraction_result` + 字典校验结果。
- Phase 4 在上传链中于 `parsed` 后触发 extract，更新 status。

</code_context>

<specifics>
## Specific Ideas

- 用户希望 **比严格 18 字段更宽一点**，把 FIELD_SPEC 里其它 P1 列一并带上，仍控制总量。
- 锁定期、分级 **子表行** 明确推迟，降低 Phase 2 复杂度。
- 字典 **预导出 JSON** 便于审计与 CI，不必每次解析 xlsx。
- LLM 配置 **与 bid 解耦**，但开发机可用同类 OpenAI 兼容网关。

</specifics>

<deferred>
## Deferred Ideas

- **`lock_periods[]` 子表** — 多行锁定期规则（FIELD_SPEC 第二节）
- **`share_classes[]` 分级子表** — 份额结构=分级时的明细行
- **路径 B 辅助 JSON**（业绩报酬、开放日）— PROJECT Out of Scope
- **golden extraction JSON 快照 diff** — 用户未选；可用 pytest 宽松断言替代
- **内部计算参数第二套 Excel** — 待业务确认；当前按费率模板 + FIELD_SPEC 第四节

### Reviewed Todos (not folded)
（无）

</deferred>

---
*Phase: 02-extract*  
*Context gathered: 2026-05-25*
