# Phase 8 计划审查

**审查日期：** 2026-05-26  
**结论：** PASS

## 目标回溯

| ROADMAP 成功标准 | 计划覆盖 |
|------------------|----------|
| ① JSON schema 稳定 | 08-01 schema + assemble |
| ② 含摘录 source_snippets | 08-01 assemble + 测试 |
| ③ API/前端可查看 | 08-03 API（前端 Phase 10） |

## 需求映射

| 需求 | 计划 |
|------|------|
| PATHB-01 | 08-01 path_b_rules tiers/summary |
| PATHB-02 | 08-01 open_day 字段 |
| PATHB-03 | 08-01 assemble；08-02 持久化 |
| PATHB-04 | 08-03 GET /path-b |

## 依赖与波次

| Wave | 计划 | 依赖 | 评估 |
|------|------|------|------|
| 0 | 08-01 | — | 抽取 + 三元组 ✓ |
| 1 | 08-02 | 08-01 | DB 写 path_b_json ✓ |
| 2 | 08-03 | 08-01, 08-02 | API 最后 ✓ |

## 上下文一致性

- D-A01 无前端：08-03 明确 ✓
- D-P01 独立列：08-02 不写 extraction_result ✓
- D-E01 CI 无 LLM：08-01 测试 -m "not llm"；08-03 LLM 可选 ✓
- D-A02 门禁 extracted+：08-03 PREVIEW_STATUSES ✓

## 风险（已记录）

1. `extract_document_sync` 三元组破坏性变更 — 08-01-03 要求同 PR 改全调用点
2. 业绩报酬 tiers 可能仅为 summary — 测试用 min_tiers 或 summary_contains 柔性断言
3. 08-03-03 LLM 为 optional，不阻塞验收

## 建议

- 执行顺序：08-01 → 08-02 → 08-03；08-01 完成后再填 `contract_expected.path_b` 真值

---
*gsd-plan-checker — Phase 8*
