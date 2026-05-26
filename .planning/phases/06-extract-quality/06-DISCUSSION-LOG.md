# Phase 6 Discussion Log

**Date:** 2026-05-26  
**Mode:** interactive (area multi-select)

## Areas Selected

User selected all four gray areas:

1. 黄金回归怎么比  
2. 规则与 LLM 谁优先  
3. CI 是否跑 LLM  
4. 本阶段是否测导出  

## Captured Decisions

### 黄金回归

- 固定 2 docx + 2 xlsx（产品要素、运营费率）为黄金集；申赎 xlsx 仅参考。  
- Critical vs Extended 两层断言 + 归一化规则。  
- 按基金维度绑定 expected 行。

### 规则 vs LLM

- 当事人：校验通过的规则优先；误抽片段不算规则值。  
- merge 增强 QUAL-04；未设预警止损规则优先。

### CI / LLM

- 默认 pytest 无 Key；`@pytest.mark.llm` 可选 e2e。  
- DeepSeek `.env` 文档化。

### 导出范围

- Phase 6 含 4 类现有 export 与黄金 diff；申赎表 Phase 7。

## Deferred

- 申赎费率、路径 B、校验层、批量 — 见 CONTEXT.md deferred.
