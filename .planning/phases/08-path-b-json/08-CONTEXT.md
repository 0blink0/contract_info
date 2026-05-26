# Phase 8：路径 B JSON — 上下文

**收集日期：** 2026-05-26  
**状态：** 可供规划

<domain>
## 阶段边界

从基金合同抽取 **路径 B** 结构化 JSON，供运营在 CRM **手录**「业绩报酬提取设置」「开放日管理」——**不**生成 Excel 母版、**不**自动写 CRM、**不**用黄金 xlsx 做运行时校验。

**本阶段包含：**

- `path_b` Pydantic schema（`performance_fee` + `open_day` 两模块）
- 规则层抽取（`path_b_rules` 或等价）；可选 LLM refine（`@pytest.mark.llm`，非 CI 必需）
- `source_snippets`：字段路径 → 合同摘录（扁平 dict）
- 抽取阶段写入 DB：**`path_b_json`**（JSONB 列）
- **`GET /api/v1/jobs/{id}/path-b`**（`status` ≥ `extracted`）；`JobDetail` 可带 path_b 是否存在/条数摘要
- 单元/黄金测试：合同真值 + snippet 存在性（不对照 CRM 系统字段码）

**本阶段不包含：**

- 任务详情 **前端** JSON 面板、复制按钮、五表下载 UI（Phase 10 / UI-01、API-02）
- LLM **校验层**（值 vs 摘录 pass/fail，Phase 9）
- 申赎/运营费率等路径 A 导出变更
- CRM 自动写库、路径 B 导入模板

</domain>

<decisions>
## 实现决策

### JSON 结构（D-S）

- **D-S01:** 顶层 **`performance_fee`**（业绩报酬提取设置）与 **`open_day`**（开放日管理）两个对象；不用扁平前缀字段。
- **D-S02:** 业绩报酬分段/比例用 **`performance_fee.tiers[]`** 数组（每项含门槛、基准、比例等 planner 定稿列）；合同无法结构化时允许 `tiers` 为空并保留 `summary` 类 fallback 字段（Claude 酌情命名）。
- **D-S03:** **开放日管理** 为 CRM 细字段；**固定开放日规则** 可与产品要素 **`开放日规则`** 摘要一致，并额外抽取 **开放业务**、**不定期/临时开放** 等；两处以各自 `source_snippets` 记录，不要求字符串完全一致。

### 抽取策略（D-E）

- **D-E01:** **默认流水线 / CI：仅规则层**，不依赖 `OPENAI_API_KEY`（与 Phase 6/7 一致）。
- **D-E02:** 提供 **可选 LLM 增强**（`@pytest.mark.llm`），主要用于业绩报酬长条款与 `tiers` refine；无 Key 时 skip。
- **D-E03:** 规则层优先 **`fees`** 窗口（业绩报酬）+ **`subscription`** 窗口（开放日、临时开放）；窗口不足时对全文段落 **补扫**（与 Phase 7 短期赎回补扫同模式）。

### 持久化（D-P）

- **D-P01:** 独立 DB 列 **`path_b_json`**（JSONB），与 `extraction_result` 并列；**不**采用仅嵌套 `extraction_result.path_b` 方案。
- **D-P02:** 在 **`extract` 阶段** 与 `extraction_result` **同次** 写入（`pipeline_service` / `extract_service` 一步完成）。

### API（D-A）

- **D-A01:** Phase 8 **仅后端**；前端 JSON 展示留给 Phase 10。
- **D-A02:** 专用端点 **`GET /jobs/{id}/path-b`** 返回完整 JSON；门禁：`extracted` / `exporting` / `exported`（与 preview 一致，**非**仅 `exported`）。
- **D-A03:** `JobDetailResponse` 可增加 `path_b_available: bool` 或 `path_b_field_count` 类摘要（Claude 酌情，非必须全量嵌入 detail）。

### source_snippets（D-SN）

- **D-SN01:** 独立键 **`source_snippets`**：`{ "字段路径": "合同摘录原文" }`（点分路径，如 `performance_fee.tiers[0].ratio`）。
- **D-SN02:** 内部抽取仍用 **`FieldValue`**（value + snippet + block_id）；组装 `path_b_json` 时汇总到 `source_snippets`。
- **D-SN03:** 无有效值则 **省略字段且不写 snippet**；通过 **`extraction_warnings`** 说明缺失（PATHB-03 可审计）。

### Claude 酌情

- `tiers[]` 单条字段集、regex/表格解析策略
- Alembic `006_path_b_json.py` 列名与迁移
- `path_b` 与 `extraction_warnings` 错误码命名
- LLM prompt 章节与 `path_b_rules` 模块拆分文件布局

</decisions>

<canonical_refs>
## 规范引用（规划/实现前必读）

### 需求与路线图
- `contract_info/.planning/REQUIREMENTS.md` — PATHB-01–04、API-02（API 实现延至 Phase 10 的 UI 部分）
- `contract_info/.planning/ROADMAP.md` — Phase 8 目标与成功标准
- `contract_info/.planning/PROJECT.md` — 路径 B JSON 手录、不用黄金表校验

### 字段规格
- `contract_info/FIELD_SPEC.md` — §五「路径 B — 页面手录」模块与字段列表

### 上游阶段决策
- `contract_info/.planning/phases/06-extract-quality/06-CONTEXT.md` — CI 无 LLM、合同真值、章节窗口
- `contract_info/.planning/phases/06-extract-quality/06-FIELD-MATRIX.md` — 可抽/可空字段调研
- `contract_info/.planning/phases/07-subscription-fees/07-CONTEXT.md` — 后端-only API、extract 阶段持久化模式
- `contract_info/.planning/phases/04-backend-api/04-CONTEXT.md` — 下载/详情 API 模式

### 实现锚点（现有代码）
- `contract_info/backend/app/extract/schemas.py` — `FieldValue`、`ExtractionResult`
- `contract_info/backend/app/extract/pipeline.py` — `extract_document` 集成点
- `contract_info/backend/app/extract/section_windows.py` — `fees` / `subscription` 窗口
- `contract_info/backend/app/extract/rules/product_rules.py` — 已有 `开放日规则` 摘要
- `contract_info/backend/app/models/contract_file.py` — 新增 `path_b_json` 列
- `contract_info/backend/app/api/routes/jobs.py` — 新端点模式（对照 subscription 下载）

</canonical_refs>

<code_context>
## 现有代码洞察

### 可复用资产
- **`FieldValue`** + `merge_field`：路径 B 字段级摘录与置信度
- **`build_section_windows`**：`fees`、`subscription` 已配置关键词
- **`product_rules` 开放日规则**：路径 B `open_day.fixed_schedule` 可对齐或交叉引用
- **`extract_document` / `persist_extract`**：与 `extraction_result` 同批持久化入口

### 已建立模式
- Phase 7：**extract 阶段写 JSON/列**、**专用 GET 下载/资源**、**Phase N 不做前端**
- Phase 6：**规则层 CI** + **`@pytest.mark.llm` 可选** + **合同真值 `contract_expected`**

### 集成点
- `extract/pipeline.py` → 调用 `extract_path_b_rules` → 合并进 `path_b_json`
- `extract_service` / `pipeline_service` → commit `path_b_json`
- `jobs.py` → `GET .../path-b`；schema → `JobDetailResponse` 摘要字段

</code_context>

<specifics>
## 具体想法

- 石云/福禄合同样本均含 **业绩报酬**、**开放日**、**临时开放** 段落，适合作为规则层 + 黄金测试锚点。
- 业绩报酬在份额分类表中为行级描述（如「超额计提…」），`tiers[]` 需兼容表格式与散文式两种来源。

</specifics>

<deferred>
## 延后项

| 想法 | 归属 |
|------|------|
| 前端 JSON 面板、复制/下载 JSON 文件按钮 | Phase 10 / UI-01 |
| LLM 校验 pass/warn/fail | Phase 9 |
| `GET /path-b` 返回 `validation_result` | Phase 9 + API-02 |
| 路径 B 与黄金 CRM 截屏 1:1 字段码对齐 | 不做；仅合同真值 + 结构稳定 |

</deferred>

---

*Phase: 08-path-b-json*  
*Context gathered: 2026-05-26*
