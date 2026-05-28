---
phase: 07
slug: subscription-fees
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-26
updated: 2026-05-28
---

# Phase 7 验证策略

**阶段：** 申赎费率导出  
**日期：** 2026-05-26

## 自动化（Nyquist）

| 需求 | 验证类型 | 测试位置 |
|------|----------|----------|
| XLS-01 | 单元 + 集成 | `test_export_subscription.py`, `test_export_pipeline.py` |
| XLS-02 | E2E golden | `test_golden_export.py` + `xlsx_diff.assert_subscription_*` |
| XLS-04 | DB + 集成 | `test_export_persist.py` |
| API-01 | API | `test_api_download.py` |
| 抽取 | 规则 | `test_subscription_rules.py` |

## 命令

```bash
cd contract_info
python -m pytest backend/tests/test_subscription_rules.py -q -m "not llm"
python -m pytest backend/tests/test_export_subscription.py -q
python -m pytest backend/tests/golden/ -q -m "not llm"
python -m pytest backend/tests/test_api_download.py -q -k subscription
python -m pytest backend/tests/ -q -m "not llm"
```

## 人工 UAT（可选）

1. 上传石云 docx → 跑 pipeline → 下载 `subscription_fee_rates.xlsx`
2. 打开 xlsx：4 份额 × 认购+申购行存在；列与 CRM 导入模板一致
3. 本阶段 **不验收** 前端按钮（Phase 10）

## 不在范围

- `@pytest.mark.llm` 申赎 LLM 抽取
- 前端预览 Tab
- 申赎费率与黄金 xlsx 数值 1:1（仅结构+合同真值）
