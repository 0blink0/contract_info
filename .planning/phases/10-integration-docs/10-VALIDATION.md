# Phase 10 验证策略

**阶段：** 集成与文档  
**日期：** 2026-05-26

## 计划级验证

| 计划 | 命令 |
|------|------|
| 10-01 | `pytest backend/tests/test_api_preview.py -q` |
| 10-02 | `cd frontend && npm run build` |
| 10-03 | 上述 + README/FIELD_SPEC 人工对照 |

## 阶段 UAT

1. 上传 `example/*.docx`，开始处理至 `exported`
2. 确认 5 个下载按钮均可下载 xlsx
3. `extracted` 后展开「摘录校验」「路径 B」，数据加载正常
4. 导出预览 5 个 Tab（含申赎）
5. 无 `OPENAI_API_KEY` 时见 `validation_skipped` warning

## 自动化

```bash
cd contract_info
pytest backend/tests -q -m "not llm"
cd frontend && npm run build
```
