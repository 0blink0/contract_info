# Requirements: CTRX（合同要素抽取）

**Defined:** 2026-05-26  
**Milestone:** v1.1 — 抽取质量与导出扩展  
**Core Value:** 上传 docx → 结构正确、可导入/可手录的产出，且机器可校验合理性

**黄金样例（仅开发/UAT，非运行时校验）：**

- `example/产品要素 - 副本(1).xlsx` — 石云两基金产品要素/锁定期/分级（人工填好）
- `example/产品运营费率导入模板.xlsx` — 运营费率（按份额类多行）
- `example/产品申赎费率导入模板.xlsx` — **申赎费率**（按份额类多行）
- `example/石云中证1000…(1).docx`、`example/石云福禄1000…(1).docx` — 对应合同

## v1.1 Requirements

### 抽取质量（QUAL）

- [ ] **QUAL-01**: 当事人字段（管理人、托管人、投资顾问、外包机构）不得命中风险揭示/承诺类散文；输出为公司/机构全称
- [ ] **QUAL-02**: 锁定期、开放日规则、预警/止损线等与石云合同样本一致的规则层行为有 pytest 黄金回归（对比 `example/` 人工表，容差说明在测试中文档化）
- [ ] **QUAL-03**: LLM 可用时，产品要素主表关键长文本字段（投资目标/范围/策略/限制、风险等级等）非空率显著高于仅规则层（以两份额合同测）
- [ ] **QUAL-04**: `merge_field` 策略文档化：规则高置信误抽（如「保证…登记为管理人」）应可被 LLM 覆盖或校验层标红

### 导出扩展（XLS）

- [ ] **XLS-01**: 新增第 **5** 个导出文件：**产品申赎费率** xlsx，母版对齐 `example/产品申赎费率导入模板.xlsx`（按份额类：认购/申购/赎回等行）
- [ ] **XLS-02**: 运营费率、申赎费率导出与黄金样例在**列结构、份额类行数**上一致（允许基金代码等系统字段由运营后补）
- [ ] **XLS-03**: 产品要素/锁定期/分级导出与 `example/产品要素 - 副本(1).xlsx` 对应 sheet 列对齐；两基金各一条主表记录可回归
- [ ] **XLS-04**: 导出路径写入 DB（`subscription_xlsx_path` 或等价）+ 下载 API + 前端下载/预览 Tab

### 路径 B — 手录辅助（PATHB）

- [ ] **PATHB-01**: 从合同抽取 **业绩报酬** 结构化草稿（提取方式、基准、比例/门槛、计提时点等），输出 **JSON**（不进 CRM、不写导入母版）
- [ ] **PATHB-02**: 从合同抽取 **开放日管理** 结构化草稿（固定开放日规则、开放业务、临时开放等），输出 JSON
- [ ] **PATHB-03**: JSON 含 `source_snippets`（字段 → 合同摘录），供运营对照手录
- [ ] **PATHB-04**: API 返回路径 B JSON；前端单独区域展示（可复制/下载 JSON），明确「需 CRM 手录」

### LLM 校验层（VAL）

- [ ] **VAL-01**: 抽取完成后增加 **校验 pass**（可用 LLM）：对每个已填字段比对 `value` 与 `snippet`/合同原文，判断是否合理
- [ ] **VAL-02**: 校验 **不使用** 黄金 xlsx 作对照；仅「摘录 + 语义一致性 + 格式/枚举」
- [ ] **VAL-03**: 输出 `validation_result`：`field`、`status`（pass/warn/fail）、`reason`、建议；写入 DB 或挂在 `extraction_warnings` 扩展结构
- [ ] **VAL-04**: 前端展示校验结果（失败/警告高亮），导出前可见

### API 与前端（API / UI）

- [ ] **API-01**: `GET /jobs/{id}/download/subscription-fees`（或统一命名）下载申赎费率 xlsx
- [ ] **API-02**: `GET /jobs/{id}/path-b` 或 preview 扩展返回路径 B + 校验结果
- [ ] **UI-01**: 任务详情：5 个 Excel 下载 + 路径 B JSON + 校验摘要
- [ ] **UI-02**: 配置说明：生产环境必须配置 `OPENAI_API_KEY` 方可启用 LLM 抽取与校验

### 测试与验收（TEST）

- [ ] **TEST-01**: `pytest` 黄金回归：`example/` 两合同 end-to-end（parse → extract → export），与 xlsx 样例字段级 diff（忽略空码、日期格式归一）
- [ ] **TEST-02**: 校验层单测：构造「值与摘录矛盾」用例必须 `fail`
- [ ] **TEST-03**: 文档更新 `FIELD_SPEC.md`、`README`：5 表 + 路径 B + 校验层

## v2 Requirements（本里程碑不做）

- **BATCH-01**: 批量多文件上传与队列
- **DOC-10**: PDF 解析
- **NER-01**: 专用 NER 模型

## Out of Scope

| 功能 | 原因 |
|------|------|
| 用黄金 xlsx 自动批改线上任务 | 样例仅开发/UAT；校验层只对合同摘录 |
| CRM 自动写库 | 路径 B 仍手录 |
| 认申赎/业绩报酬写入路径 A 母版之外的新 CRM 页面 | 仅 JSON 辅助 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| QUAL-01–04 | Phase 6 | Pending |
| XLS-01–04 | Phase 7 | Pending |
| PATHB-01–04 | Phase 8 | Pending |
| VAL-01–04 | Phase 9 | Pending |
| API-01–02, UI-01–02 | Phase 10 | Pending |
| TEST-01–03 | Phase 6–10 | Pending |

**Coverage:** v1.1 requirements 20 total · Mapped 20 · Unmapped 0

---
*Requirements defined: 2026-05-26 — milestone v1.1*
