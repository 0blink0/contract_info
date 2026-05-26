# Phase 7：申赎费率导出 — 上下文

**收集日期：** 2026-05-26  
**状态：** 可供规划

<domain>
## 阶段边界

在现有 **parse → extract → export（4 类 xlsx）** 流水线之上，新增第 **5** 个导出文件：**产品申赎费率导入模板**（按份额类 A/B/C/D 多行），写入 DB、并入同一次 `export_xlsx` 持久化；提供 **下载 API**。本阶段 **不包含** 前端预览/五表 UI（留给 Phase 10）。

**本阶段包含：**

- `subscription_fee`（申赎费率）规则层抽取 + schema（`subscription_fees[]` 或等价结构）
- `export/subscription_workbook.py`（或对称命名）+ 母版 `templates/`
- Alembic：`subscription_xlsx_path`（或等价列名）
- `export_xlsx` / pipeline 一次生成 **5** 个 xlsx
- `GET /jobs/{id}/download/subscription-fee-rates`
- 扩展 `tests/golden/`：E2E 为 **5** 个 xlsx（结构 + 合同真值费率；基金代码等允许与黄金差异）

**本阶段不包含：**

- 任务详情前端 Tab、五表下载 UI 集成（Phase 10 / UI-01）
- 路径 B JSON（Phase 8）
- LLM 校验层（Phase 9）
- 用黄金 xlsx 做线上任务自动批改
- 默认 CI 依赖 `OPENAI_API_KEY` 的申赎 LLM 抽取

</domain>

<decisions>
## 实现决策

### 抽取与行展开（D-S01–S04）

- **D-S01:** **优先份额分类表**（基本情况/募集中的 A/B/C/D 表）确定份额类与表内费率线索；**申赎章节**补充申购/赎回规则、短期赎回分段等。
- **D-S02:** 每个份额类至少导出 **认购费 + 申购费** 两行；**赎回费** 仅当合同有明确费率或分段条款时再出（不强制三行齐全）。
- **D-S03:** 若合同存在 **赎回分段/短期赎回**（如持有天数区间 + 不同费率），导出 **多行**：`计费基准` 用区间类，`区间开始`/`区间结束`/`费率` 按模板列填写。
- **D-S04:** 申赎费率抽取 **默认仅规则层**；与 Phase 6 一致，CI 不依赖 API Key；LLM 可留 `@pytest.mark.llm` 扩展，非本阶段验收必需。

### 与黄金样例 / 合同真值（D-G01–G04）

- **D-G01:** **基金代码**：份额分类表或合同有则填，否则留空（不强制对齐黄金 BPL38A 等）。
- **D-G02:** **基金名称** 列：`基金全称` + 份额后缀（`…证券投资基金A` 或 `…一号A类`），与 `example/产品申赎费率导入模板.xlsx` 命名风格尽量一致。
- **D-G03:** 费率 **Critical 真值以合同/份额表为准**（延续 Phase 6 `contract_expected` 思路）；黄金 xlsx 用于 **列结构、行形态、份额类集合**；数值与黄金不一致且合同有依据时不判失败。
- **D-G04:** 合同未写明某份额某类申赎费率时，**费率列写 `0`**（与黄金「0」一致），并视情况追加 **warning**（与 D-T03「最小填列」并存：未抽取到的其他必填项仍空 + warning）。

### 母版与填表（D-T01–T04）

- **D-T01:** 从 `example/产品申赎费率导入模板.xlsx` **复制到 `templates/`** 并提交 git（同 Phase 3 D-01）。
- **D-T02:** 复制到 `templates/` 时 **修正 sheet 名** 为 `产品申赎费率导入模板`（原文件 sheet 误标为「产品运营费率导入模板」）；确保与业务导入系统一致后再定稿。
- **D-T03:** **最小填列**：仅写入抽取到的列；模板标注必填但合同/规则未提供的列 **留空并 warning**（不默认价外法/不分段等黄金常值）。
- **D-T04:** 磁盘输出路径：`exports/{file_id}/subscription_fee_rates.xlsx`；DB 列：**`subscription_xlsx_path`**（相对 `contract_info/` 根）。

### API、流水线与测试（D-A01–A04）

- **D-A01:** Phase 7 **仅后端**：抽取 + 导出 + DB + 下载 API；**不做** 前端预览 Tab（Phase 10）。
- **D-A02:** 下载端点：`GET /jobs/{id}/download/subscription-fee-rates`；仅 `status=exported` 且路径存在时返回（同 Phase 4 既有下载）。
- **D-A03:** **并入** 现有 `export_xlsx` / 任务 pipeline，与 4 类 xlsx **同次** 生成并持久化（不单独要求运营二次点击）。
- **D-A04:** **扩展** `tests/golden/` E2E 为 **5** 个 xlsx（在现有 `run_golden_pipeline` / export 断言上增加申赎文件）；可增 `contract_expected` 中 `subscription_fees_by_share` 段；**不** 用黄金 xlsx 当事人/基金代码做 hard fail。

### Claude 酌情

- `SubscriptionFeeRow` schema 字段名与 `column_map` 表头映射表
- 份额后缀正则（`A类` vs `证券投资基金A`）的具体归一规则
- 赎回分段解析与多行展开的 regex/表格行策略
- `templates/` 下申赎母版文件名（建议 `产品申赎费率导入模板.xlsx`）

</decisions>

<canonical_refs>
## 规范引用（规划/实现前必读）

### 需求与路线图
- `contract_info/.planning/REQUIREMENTS.md` — XLS-01–04、API-01
- `contract_info/.planning/ROADMAP.md` — Phase 7 成功标准
- `contract_info/.planning/PROJECT.md` — 第 5 表、黄金样例说明

### 上游阶段决策
- `contract_info/.planning/phases/03-xlsx-export/03-CONTEXT.md` — 母版复制、openpyxl 填表、warnings、路径约定
- `contract_info/.planning/phases/04-backend-api/04-CONTEXT.md` — 下载 API、`exported` 门禁
- `contract_info/.planning/phases/06-extract-quality/06-CONTEXT.md` — 黄金测试、合同真值 vs 黄金表、申赎本阶段纳入
- `contract_info/.planning/phases/06-extract-quality/06-FIELD-MATRIX.md` — 第 9 项认申赎费、§6 Critical

### 字段与模板
- `contract_info/FIELD_SPEC.md` — 申赎章节、份额类、费率相关列
- `contract_info/field_instructions.txt` — 日期/枚举/计费方式说明
- `contract_info/example/产品申赎费率导入模板.xlsx` — 黄金结构（复制源）
- `contract_info/example/石云中证1000…(1).docx`、`example/石云福禄1000…(1).docx` — 合同样本

### 代码锚点
- `contract_info/backend/app/export/fee_workbook.py` — 费率多行填表模式
- `contract_info/backend/app/export/pipeline.py` — `export_xlsx` 扩展点
- `contract_info/backend/app/export/column_map.py` — 表头归一
- `contract_info/backend/app/extract/rules/share_rules.py` — 份额分类表
- `contract_info/backend/app/extract/section_windows.py` — `subscription` 窗
- `contract_info/backend/app/api/routes/jobs.py` — 现有 download 路由
- `contract_info/backend/tests/golden/` — 扩展为 5 表 E2E

</canonical_refs>

<code_context>
## 现有代码要点

### 可复用资产
- `fill_fee_workbook` + `build_header_index` / `write_cell_values` — 申赎表同为「多行 + 表头映射」
- `export_xlsx` 四路径返回元组 — 扩展为五路径 + warnings 合并
- `ContractFile` 已有 `product/fee/lock/share_xlsx_path` — 新增 `subscription_xlsx_path`
- `tests/golden/helpers/pipeline_runner.py` — `run_golden_pipeline` 扩展第五文件断言

### 已建立模式
- 母版在 `templates/`，输出在 `exports/{uuid}/`
- 下载路由一对一路径；前端 Phase 5 已消费 4 类下载 URL

### 集成点
- `extract_document_sync` → `extraction_result` 增加申赎费率数组
- `export_service` / `pipeline_service` 在 export 步写 DB 第五列
- Golden：`contract_expected.json` 增加申赎费率段（按份额类 + 费类型）

</code_context>

<specifics>
## 具体想法

- 黄金申赎表：两基金 × 4 份额类 × 认购/申购为主；赎回费行数较少；费率多为百分比列 `0` / `0.5`。
- 用户明确：Phase 7 **不做前端**；预览与五表 UI 统一 Phase 10。
- 申赎 sheet 名需在入库母版时修正，避免与运营费率 sheet 混淆。

</specifics>

<deferred>
## 延后事项

- 前端「申赎费率」预览 Tab、五表下载区 — **Phase 10**（UI-01）
- 路径 B、LLM 校验层 — Phase 8/9
- 申赎费率 LLM 抽取质量基线（可选 mark.llm）— 非 Phase 7 验收必需
- 基金代码与 CRM 系统码自动对齐 — 运营后补，非合同真值

</deferred>

---

*阶段：7-申赎费率导出*  
*上下文收集：2026-05-26*
