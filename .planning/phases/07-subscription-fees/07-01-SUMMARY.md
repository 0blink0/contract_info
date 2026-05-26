# 07-01 执行摘要

**状态：** 完成  
**日期：** 2026-05-26

## 交付

- `SubscriptionFeeRow` + `ExtractionResult.subscription_fees`
- `subscription_rules.py`：份额分类表认购/申购 + 福禄短期赎回分段
- `extract/pipeline.py` 集成；`merge_extraction` 扩展
- `test_subscription_rules.py`；`contract_expected.json` 增加 `subscription_fees_by_share`

## 验证

`pytest backend/tests/test_subscription_rules.py -m "not llm"` — 8 passed
