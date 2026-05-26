# Phase 7 验证报告

**阶段：** 申赎费率导出  
**日期：** 2026-05-26  
**结论：** 通过

## 成功标准

| 标准 | 结果 |
|------|------|
| 申赎模板列可写入 | 通过 — `SUBSCRIPTION_SHEET` + `fill_subscription_workbook` |
| 每份额类≥认购+申购 | 通过 — 石云/福禄各 8 行 + 福禄赎回分段 |
| 下载端点可用 | 通过 — `download/subscription-fee-rates` |

## 自动化测试

```
pytest backend/tests/ -q -m "not llm"  → 67 passed, 2 skipped
```

含：`test_subscription_rules`、`test_export_subscription`、`golden` 五表 E2E、`test_api_download`

## 已知差异（按 CONTEXT 预期）

- 导出仅填抽取列，不默认「价外法」等 — 与 `example/产品申赎费率导入模板.xlsx` 黄金行不完全一致
- 基金代码：合同无则留空，不对齐黄金 BPL38A/FLZB38

## 部署注意

- 运行 `alembic upgrade head` 应用 `005_subscription_xlsx_path`
- 母版：`templates/产品申赎费率导入模板.xlsx`（可用 `python scripts/prepare_subscription_template.py` 重建）
