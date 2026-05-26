# Phase 7 模式映射

**阶段：** 07-subscription-fees  
**日期：** 2026-05-26

## 最近似实现

| 新组件 | 参照 | 说明 |
|--------|------|------|
| `SubscriptionFeeRow` | `FeeRateRow` | `schemas.py` 同文件追加 |
| `subscription_rules.py` | `fee_rules.py` + `share_rules.py` | 多行费率 + 份额表 |
| `subscription_workbook.py` | `fee_workbook.py` | `fill_*_workbook` 同结构 |
| `check_subscription_fees` | `check_fees` | `validate_export.py` |
| download 路由 | `download/fee-rates` | `jobs.py` 复制 |
| alembic 005 | `003_export_paths.py` | 单列 text |
| golden 第五文件 | `test_golden_export.py` | 扩展 `GoldenRunResult` |

## 集成点

```
extract_document_sync
  └─ extract_subscription_fees_rules(...)  → subscription_fees[]
export_xlsx(extraction)
  └─ fill_subscription_workbook(...)
export_service.run_export
  └─ record.subscription_xlsx_path = rel_path
GET /jobs/{id}/download/subscription-fee-rates
run_golden_pipeline → 5 paths
```

## 命名约定

- 磁盘：`subscription_fee_rates.xlsx`
- DB：`subscription_xlsx_path`
- 抽取键：`subscription_fees`（JSONB 内数组）
- 测试 fixture：`subscription_fees_by_share` in `contract_expected.json`
