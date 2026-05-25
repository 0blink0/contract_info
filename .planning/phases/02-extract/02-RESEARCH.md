# Phase 2 Research: 字段抽取引擎

**Researched:** 2026-05-25  
**Phase:** 02 — 规则 + LLM 抽取 → JSON 入库

## Summary

在 Phase 1 `Document JSON` 之上实现 **`extract(document) → { product_elements, fee_rates, _meta }`**，规则层覆盖封面/当事人/费用表格，**按章节窗口**调用 OpenAI 兼容 API 补枚举与混合字段，结果写入 **`extraction_result` / `extraction_warnings`**，CLI `extract` 与 pytest 验证（无 Key 时跳过 LLM）。

## Stack（本阶段采用）

| 组件 | 选型 | 理由 |
|------|------|------|
| 配置 | pydantic-settings 扩展 `LLM_*` | CONTEXT D-08；与 bid 解耦 |
| HTTP LLM | `httpx` + chat/completions JSON | 轻量，无 LangChain |
| 校验 | Pydantic v2 models + `model_validate_json` | D-11 strict schema |
| 字典 | `openpyxl` 一次性导出 → `dicts/*.json` | D-15；CI 不读 xlsx |
| DB | Alembic `002` 增列 | D-17/D-18 |
| 测试 | pytest + `@pytest.mark.llm` skipif | D-10 |

**不采用：** LangChain、RAG、子表 `lock_periods`/`share_classes`、FastAPI。

## 章节窗口（D-05/D-06）

按 `outline[].title` 与 `contract_keywords.txt` 将 blocks 归入：

| 窗口 key | 匹配线索 | 主要字段 |
|----------|----------|----------|
| `cover_parties` | 封面、私募基金管理人、托管人 | 基金全称/简称、管理人、托管人、投顾 |
| `basic` | 第四章/基本情况 | 基金类型、管理类型、份额结构、结构类型、存续期 |
| `establish` | 成立与备案 | 备案编码、成立/备案日期 |
| `subscription` | 申购赎回 | 申购起点、交易确认、金额赎回、是否封闭、锁定期摘要 |
| `investment` | 投资/风控 | 预警线、止损线 |
| `fees` | 费用与税收 | 费率表格 → fee_rates[] |

实现：`section_windows.py` 根据 `section_id` 过滤 blocks，每窗文本上限 ~12k 字符（截断保留表头行）。

## 规则层要点

1. **封面/当事人**：正则 `私募基金管理人[：:]\s*(.+)`、`私募基金托管人[：:]`；基金名从 `metadata` 或首段标题行。
2. **费用表**：`fees` 窗内 `type=table` blocks，列含「管理费」「托管费」「投资顾问」→ 行对象；费率列解析 `%` 与「年」。
3. **申赎数字**：「万元」→ 数值；「T+N」→ 交易确认规则原文。
4. 规则命中字段：`confidence=high`，`source=rule`。

## LLM 层要点

- 每窗一次调用，system 要求 **仅输出 JSON**，字段子集为该窗负责的 P1 LLM/混合列。
- `temperature=0.1`，`max_tokens=4096`，失败 **重试 1 次**（D-07）。
- 响应模型：`ChapterExtractResponse`（pydantic），合并时 LLM 覆盖空字段或 `confidence=low` 的规则候选。
- 无 `OPENAI_API_KEY`：`LlmClient` 为 None，管道仅返回规则结果。

## `extraction_result` 形状（建议）

```json
{
  "product_elements": {
    "基金全称": { "value": "...", "confidence": "high", "source": "rule", "block_id": "b12", "section_id": "s3", "snippet": "..." }
  },
  "fee_rates": [
    { "基金名称": "...", "运营费类型": "管理费", "计费频率": "...", "费率（%/年）": "1.5", ... }
  ],
  "_meta": { "model": "...", "chapters_called": ["basic", "fees"], "extracted_at": "ISO" }
}
```

`extraction_warnings`: `[{ "field": "销售机构信息", "code": "enum_unknown", "message": "...", "suggestion": "..." }]`

## P1 字段范围（实现清单）

**MVP 18 + 扩展 P1 列**（`FIELD_SPEC` 阶段=P1，不含 P2/P3）：

基金全称、基金简称、管理人、托管人、投资顾问、基金类型、管理类型、份额结构、结构类型、首次申购起点、追加起点、交易确认规则、是否支持金额赎回、预警线、止损线、锁定期、备案编码、成立日期、备案日期、到期日期、产品类型（协会）、是否封闭、产品存续期。

费率行：基金名称、运营费类型、计费频率、计费基准（若有）、费率（%/年）；类型至少管理费+托管费，有投顾条款则顾问费。

## 风险与规避

| 风险 | 规避 |
|------|------|
| LLM 幻觉枚举 | dict JSON 校验 + warnings，不阻断 |
| 费用表结构不一 | 规则 + LLM fees 窗兜底 |
| token 超限 | 按窗截断；表格优先保留 |
| 测试依赖外网 | `@pytest.mark.llm` + env skip |

## Validation Architecture

| 维度 | 策略 |
|------|------|
| 规则单元 | pytest：样例 docx parse 后 rules 抽出管理人非空 |
| 管道集成 | CLI `extract example/正仁...docx` 输出 JSON；多数 P1 键存在 |
| DB | `extract --persist` + file_id 路径；status=extracted |
| LLM | 可选 mark；CI 默认 skip |
| 字典 | `dicts/*.json` 存在且非空；export 脚本可重复运行 |

## References

- `02-CONTEXT.md` — 全部 D-xx 决策
- `FIELD_SPEC.md` §一、§四、§六
- `metadata_llm.py` / `prompts_evidence.py` — 合并与 JSON 提示模式（参考）
