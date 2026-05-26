---
phase: 06-extract-quality
status: passed
verified: 2026-05-26
score: 8/8
---

# Phase 6 Verification

## Must-haves

| ID | Criterion | Result |
|----|-----------|--------|
| 1 | 石云/福禄管理人/托管人无散文误抽 | PASS — `is_invalid_rule_value` + party helpers; golden rules green |
| 2 | 锁定期 180天、开放日含排期（石云）；福禄无假锁定期行 | PASS — lock_rules + export lock sheet asserts |
| 3 | 黄金 diff pytest CI (`not llm`) | PASS — `backend/tests/golden/` 15 tests |
| 4 | `tests/golden/` 脚手架齐备 | PASS |
| 5 | merge QUAL-04 有测试与 README | PASS — `test_merge_field.py` |
| 6 | 合同真值非黄金 xlsx 当事人 | PASS — `contract_expected.json` only |
| 7 | 四类产品 xlsx 生成 | PASS — export E2E |
| 8 | LLM 可选 e2e | PASS — `test_golden_llm.py` skips without key |

## Automated

```
pytest backend/tests/golden/ -q -m "not llm"  → 15 passed
pytest backend/tests/ -q -m "not llm"         → 55 passed
```

## Human verification

None required for phase close.
