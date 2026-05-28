---
phase: 09
slug: llm-validation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-26
updated: 2026-05-28
---

# Phase 9 验证策略

**阶段：** LLM 校验层  
**日期：** 2026-05-26

## 计划级验证

| 计划 | 命令 |
|------|------|
| 09-01 | `pytest backend/tests/test_validation_evidence.py backend/tests/test_llm_validator.py -q` |
| 09-02 | `pytest backend/tests/test_validation_persist.py -q` |
| 09-03 | `pytest backend/tests/test_api_validation.py -q` |

## 阶段验收

```bash
cd contract_info
alembic upgrade head   # 007
pytest backend/tests/test_validation_*.py backend/tests/test_api_validation.py -q -m "not llm"
```

## 人工抽检

1. 配置 `.env` LLM Key，跑一份合同 pipeline
2. `GET /api/v1/jobs/{id}/validation` 查看 fail/warn 项
3. 确认有 fail 时仍可 download xlsx（advisory）
