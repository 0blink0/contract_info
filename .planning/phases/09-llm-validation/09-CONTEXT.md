# Phase 9：LLM 校验层 — 上下文

**收集日期：** 2026-05-26  
**状态：** 可供规划

<domain>
## 阶段边界

在 **extract 完成之后、export 之前（或与之同次 pipeline）**，使用 LLM 对已有抽取结果做 **摘录一致性审查**：比对字段 `value` 与合同原文证据（`snippet` / `block_id` 段落），输出 **pass / warn / fail**；**不使用** 黄金 xlsx 对照（VAL-02）。

**本阶段包含：**

- `backend/app/validate/llm_validator.py`（或等价）及批校验 prompt
- 证据链：`FieldValue.snippet` 优先，`parse_json` 按 `block_id` 补全文
- 校验范围：**product_elements** + 有摘录的 **fee_rates / subscription_fees / path_b** 关键字段
- DB：**`validation_result`**（JSONB）；与现有 **`extraction_warnings`**（规则/导出）**分离**
- **extract 成功后自动校验**（LLM 不可用时跳过并记 warning，不阻断任务）
- **`GET /api/v1/jobs/{id}/validation`**（或等价）；`JobDetail` 带 `validation_summary`（pass/warn/fail 计数）
- **TEST-02**：构造「值与摘录矛盾」单测（mock LLM 或 fixture 响应）必须 **fail**

**本阶段不包含：**

- 前端 pass/warn/fail **高亮 UI**（VAL-04 完整体验 → **Phase 10** / UI-01）
- 用黄金 xlsx 做运行时批改
- 自动修正抽取值（仅报告，不改写 `extraction_result`）
- 批量队列、PDF

</domain>

<decisions>
## 实现决策

### 触发与流水线（D-T）

- **D-T01:** **`persist_extract` 成功之后**、**`persist_export` 之前** 自动调用校验（`run_pipeline` 路径同理）；不在 parse 阶段运行。
- **D-T02:** **`LlmClient.available == false`** 时 **跳过** 校验：不写 `validation_result`（或写 `skipped: true` 摘要）；追加 `extraction_warnings` 一条 `code=validation_skipped`；任务仍可继续 export。
- **D-T03:** 支持 **CLI / 可选 API** 对已有 `extracted` 任务 **重跑校验**（Claude 酌情，非阻塞 Phase 9 验收）。

### 存储（D-P）

- **D-P01:** 新列 **`validation_result`**（JSONB），**不** 与 `extraction_warnings` 混存 pass 项。
- **D-P02:** **`extraction_warnings`** 继续承载：enum、export 必填、path_b 不完整、**validation_skipped** 等；**fail/warn** 的 LLM 校验明细在 **`validation_result.items[]`**。
- **D-P03:** `validation_result` 建议结构：`validated_at`、`model`、`items[]`（`field`, `status`, `reason`, `suggestion?`）、`summary`（`pass`/`warn`/`fail` 计数）。

### 校验范围（D-S）

- **D-S01:** **必校：** `product_elements` 中有 **非空 value 且具备 snippet 或 block_id** 的字段。
- **D-S02:** **扩展：** `fee_rates`、`subscription_fees` 行级字段；`path_b_json` 中带 `source_snippets` 的路径；无摘录的字段 **不送 LLM**（避免幻觉评判）。
- **D-S03:** **不校：** 纯规则占位、空值字段、无证据的列；**不对照** 字典枚举表（已由 `validate_enums` 覆盖）。

### 证据来源（D-E）

- **D-E01:** 优先使用 **`FieldValue.snippet`**；`path_b` 使用 **`source_snippets`** 对应路径文本。
- **D-E02:** snippet 缺失或过短（如 &lt;20 字）时，从 **`parse_json.blocks`** 按 **`block_id`** 取段落作为 `evidence_text`。
- **D-E03:** **不** 默认发送整章 `section_windows`（控制 token）；批处理按字段/小批（planner 定 batch size）。

### 严重级与 export（D-V）

- **D-V01:** **顾问式（advisory）**：`fail` **不阻止** `export`；`status=exported` 仍可达。
- **D-V02:** `status` 枚举：**`pass`**（一致）、**`warn`**（可疑/证据不足/格式边缘）、**`fail`**（值与摘录明显矛盾或捏造）。
- **D-V03:** 矛盾样例（TEST-02）必须得到 **`fail`**；一致样例为 **`pass`**。

### API（D-A）

- **D-A01:** Phase 9 **仅后端**；前端展示留给 Phase 10。
- **D-A02:** **`GET /jobs/{id}/validation`** 返回完整 `validation_result`；门禁：`status` ∈ `PREVIEW_STATUSES`（与 path-b 一致）。
- **D-A03:** **`JobDetailResponse`** 增加摘要：`validation_available`、`validation_fail_count`、`validation_warn_count`（或等价），**不**嵌入全量 items。

### 测试（D-CI）

- **D-CI01:** CI 默认 **不依赖** 真实 LLM；TEST-02 用 **mock** `LlmClient` 或录制响应。
- **D-CI02:** 可选 `@pytest.mark.llm` 端到端抽检 1 份合同。

### Claude 酌情

- 批大小、prompt 模板、`validate/llm_validator.py` vs `extract/llm/validate_extract.py` 路径
- Alembic `007_validation_result.py`
- fail 是否包含「当事人误抽」类 party_helpers 已过滤字段的二次校验

</decisions>

<canonical_refs>
## 规范引用（规划/实现前必读）

### 需求与路线图
- `contract_info/.planning/REQUIREMENTS.md` — VAL-01–04、TEST-02
- `contract_info/.planning/ROADMAP.md` — Phase 9 成功标准
- `contract_info/.planning/PROJECT.md` — 校验只看摘录、不用黄金表

### 上游阶段
- `contract_info/.planning/phases/06-extract-quality/06-CONTEXT.md` — merge_field、误抽标记、CI 无 LLM
- `contract_info/.planning/phases/08-path-b-json/08-CONTEXT.md` — source_snippets、path_b_json
- `contract_info/.planning/phases/04-backend-api/04-CONTEXT.md` — API 模式、PREVIEW_STATUSES

### 实现锚点
- `contract_info/backend/app/extract/schemas.py` — `FieldValue`、`ExtractionWarning`
- `contract_info/backend/app/extract/validate.py` — `validate_enums`（勿混淆）
- `contract_info/backend/app/extract/llm/chapter_extract.py` — `chat_json` 模式
- `contract_info/backend/app/llm/client.py` — `LlmClient`
- `contract_info/backend/app/services/extract_service.py`、`pipeline_service.py` — 挂钩点
- `contract_info/backend/app/export/validate_export.py` — 导出必填 warnings（保持独立）
- `contract_info/frontend/src/components/WarningsList.vue` — Phase 10 扩展参考

</canonical_refs>

<code_context>
## 现有代码洞察

### 可复用
- **`LlmClient.chat_json`** + Pydantic response model（同 chapter_extract）
- **`ExtractionWarning`** 列表已在前端展示（无 status 分级）
- **`persist_extract` → `persist_export`** 流水线

### 缺口
- 无 `validate/` 包；无 `validation_result` 列
- `validate_enums` 仅为字典枚举，非摘录一致性

### 集成点
1. `extract_service.persist_extract` 末尾调用 `run_llm_validation`
2. `pipeline_service.run_pipeline` 在 export 前确保已校验（或由 extract 保证）
3. `jobs.py` 新端点；`ContractFile.validation_result`

</code_context>

<specifics>
## 具体想法

- 当事人字段（管理人/托管人等）是误抽高发区，校验 prompt 应明确要求：公司全称须出现在摘录中。
- path_b 的 `source_snippets` 已满足 PATHB-03，可直接作为 path_b 字段证据。

</specifics>

<deferred>
## 延后项

| 想法 | 归属 |
|------|------|
| 前端 fail/warn 高亮、导出前确认弹窗 | Phase 10 / VAL-04、UI-01 |
| API-02 合并 path-b + validation 单一 preview | Phase 10 |
| 校验后自动改写 extraction_result | 不做（非本里程碑） |
| 黄金 xlsx 对照 | 明确不做（VAL-02） |

</deferred>

---

*Phase: 09-llm-validation*  
*Context gathered: 2026-05-26*
