---
phase: "02"
phase_slug: extract
created: "2026-05-25"
---

# Phase 2 Validation Strategy

## Dimension Coverage

| Dimension | Phase 2 approach |
|-----------|------------------|
| 1 Correctness | pytest 断言正仁合同关键字段非空；费率≥2 行 |
| 2 Regression | `backend/tests/test_extract_*.py` 纳入 CI |
| 3 Integration | `extract --persist` + DB 列 roundtrip |
| 4 Security | API Key 仅 `.env`；日志不打印 key |
| 5 Performance | 单合同 extract < 120s（含 LLM，本地） |
| 6 Observability | CLI 打印 warnings 条数；`_meta.chapters_called` |
| 7 DevEx | `.env.example` LLM 变量；README extract 小节 |
| 8 Nyquist | 每 task 含 verify + acceptance_criteria |

## Test Matrix

| Case | Command / test | Without LLM |
|------|----------------|-------------|
| Dict export | `python scripts/export_dicts.py` | ✓ |
| Rule extract | `pytest backend/tests/test_extract_rules.py` | ✓ |
| Full pipeline | `pytest backend/tests/test_extract_pipeline.py` | ✓（mock/skip llm） |
| CLI | `python -m backend.cli extract example/*.docx` | ✓ rules only |
| DB persist | `test_extract_persist.py` | ✓ needs Docker |

## LLM Optional Path

- Env `OPENAI_API_KEY` unset → skip `@pytest.mark.llm`
- Document in README
