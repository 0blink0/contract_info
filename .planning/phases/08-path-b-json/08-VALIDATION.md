# Phase 8 验证策略

**阶段：** 路径 B JSON  
**日期：** 2026-05-26

## 计划级验证

| 计划 | 自动化命令 |
|------|------------|
| 08-01 | `pytest backend/tests/test_path_b_rules.py -q -m "not llm"` |
| 08-02 | `pytest backend/tests/test_extract_persist.py -q -m integration` |
| 08-03 | `pytest backend/tests/test_api_path_b.py -q` |

## 阶段验收（08-VERIFICATION 执行时）

```bash
cd contract_info
alembic upgrade head   # 006
pytest backend/tests/test_path_b_rules.py backend/tests/test_api_path_b.py -q -m "not llm"
```

## 人工抽检

1. 对石云合同跑 CLI extract，`curl GET /api/v1/jobs/{id}/path-b` 查看 JSON
2. 确认 `source_snippets` 中 `open_day.fixed_schedule` 与合同开放日段落一致
3. 确认 **无** 新 xlsx 文件生成

## 非目标

- 不对照 CRM 页面字段码
- 不要求 LLM 测试在 CI 通过
