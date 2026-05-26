# Phase 8：路径 B JSON — 调研

**调研日期：** 2026-05-26  
**领域：** 业绩报酬 + 开放日结构化 JSON、DB 持久化、GET API  
**置信度：** HIGH（Phase 7 规则/持久化模式可复用）/ MEDIUM（业绩报酬 tiers 结构化边界）

<user_constraints>
## 用户约束（08-CONTEXT.md）

- D-S01：顶层 `performance_fee` + `open_day`
- D-S02：`performance_fee.tiers[]`；无法结构化时 `summary` fallback
- D-S03：开放日扩展产品要素摘要，不要求逐字一致
- D-E01/E02：CI 仅规则层；可选 `@pytest.mark.llm`
- D-E03：`fees` + `subscription` 窗口，不足补扫全文
- D-P01/P02：`path_b_json` JSONB 列，extract 阶段写入
- D-A01/A02：仅后端 `GET /path-b`；门禁 ≥ `extracted`
- D-SN01–03：扁平 `source_snippets`；内部 FieldValue；无值无 snippet + warnings
</user_constraints>

<phase_requirements>
| ID | 描述 | 调研结论 |
|----|------|----------|
| PATHB-01 | 业绩报酬结构化草稿 | `path_b_rules` 解析 fees 窗 + 份额表「业绩报酬」行 → `tiers[]` 或 `summary` |
| PATHB-02 | 开放日管理草稿 | `subscription` 窗 + 复用/扩展 `product_rules` 开放日规则；补扫「临时开放」 |
| PATHB-03 | source_snippets | `path_b_assemble.py` 从 FieldValue 汇总点分路径 dict |
| PATHB-04 | API 返回 JSON | `GET /jobs/{id}/path-b`；`JobDetailResponse.path_b_available` |
</phase_requirements>

## 摘要

Phase 8 **不新增 xlsx**，在 `extract_document` 流水线旁路生成 `path_b_json`，与 `extraction_result` 同次 `persist_extract` 写入 PostgreSQL JSONB 列。规则层为主；LLM 仅可选 refine `tiers`。测试沿用 Phase 6/7：`contract_expected.path_b` 合同真值 + snippet 键存在性。

## 合同样本观察（石云/福禄）

| 来源 | 业绩报酬 | 开放日 |
|------|----------|--------|
| 份额分类表 | 行「业绩报酬（计算方式详见…）」含超额计提描述 | — |
| fees 窗 | 虚拟净值估值、费用计提散文 | — |
| subscription 窗 | 认申购承诺中的业绩报酬引用 | 开放日申购赎回流程 |
| 全文补扫 | — | 「临时开放日」披露段落 |

**结论：** tiers 优先从 **份额表业绩报酬行** 按 A/B/C/D 解析；散文章节进 `summary`；开放日 `fixed_schedule` 可对齐 `product_elements.开放日规则`。

## 推荐 Schema（规划定稿）

```python
class PerformanceFeeTier(BaseModel):
    share_class: str | None = None      # A/B/C/D
    benchmark: str | None = None        # 业务基准描述
    threshold: str | None = None        # 门槛
    ratio_pct: str | None = None        # 计提比例 %
    description: str | None = None      # 原文级描述 fallback

class PerformanceFeeModule(BaseModel):
    extraction_method: str | None = None
    benchmark_type: str | None = None
    hurdle_nav: str | None = None
    extraction_timing: str | None = None
    summary: str | None = None
    tiers: list[PerformanceFeeTier] = Field(default_factory=list)

class OpenDayModule(BaseModel):
    fixed_schedule: str | None = None
    open_business: str | None = None
    temporary_open: str | None = None
    ad_hoc_rules: str | None = None

class PathBDocument(BaseModel):
    performance_fee: PerformanceFeeModule = Field(default_factory=PerformanceFeeModule)
    open_day: OpenDayModule = Field(default_factory=OpenDayModule)
    source_snippets: dict[str, str] = Field(default_factory=dict)
```

## 架构变更面

| 文件 | 变更 |
|------|------|
| `extract/path_b_assemble.py` | FieldValue 映射 → PathBDocument + snippets |
| `extract/rules/path_b_rules.py` | `extract_path_b_rules` |
| `extract/pipeline.py` | 返回三元组 `(result, warnings, path_b_dict)` |
| `extract_service.py` | 写 `path_b_json` |
| `models/contract_file.py` | `path_b_json` JSONB |
| `alembic/006_path_b_json.py` | 迁移 |
| `api/routes/jobs.py` | `GET /path-b` |
| `api/schemas.py` | `PathBResponse`、detail 摘要 |
| `tests/test_path_b_rules.py` | 规则 + expected |
| `tests/test_api_path_b.py` | API |

**不修改：** `export/`、`frontend/`（Phase 10）

## 流水线返回类型（破坏性）

`extract_document` / `extract_document_sync` 由二元组改为 **三元组** `(ExtractionResult, warnings, path_b_dict)`。同 PR 更新：`extract_service`、CLI、`tests`、golden runner（若调用 sync）。

## 测试策略

- CI：`pytest backend/tests/test_path_b_rules.py -m "not llm"`
- `contract_expected.json` 增加 `path_b` 段（关键字符串子集 + `tiers_min_count`）
- API：`status=extracted` 可 GET；`parsed` → 409
- 不对照 CRM 字段码或黄金 xlsx

## 风险

1. **三元组返回** — 须一次改全调用点（计划 08-01 任务 3 列出 grep 清单）
2. **业绩报酬散文** — tiers 可能仅 1 条 summary；测试用「非空 + snippet」而非 CRM 结构 1:1
3. **JSONB vs SQLite 测试** — 集成测用 PostgreSQL 或 mock 列；单测不依赖 DB

---
*Phase 8 research — ready for planning*
