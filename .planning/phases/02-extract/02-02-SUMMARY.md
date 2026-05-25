# Phase 2 Plan 02 Summary

**Plan:** 02-02 — 抽取管道  
**Status:** Complete

## Delivered

- `section_windows` — 六窗文本（cover/basic/establish/subscription/investment/fees）
- `rules/product_rules`, `rules/fee_rules` — 规则层 + 溯源
- `llm/chapter_*` — 按窗 LLM（可选）
- `merge`, `validate`, `pipeline` — 合并与枚举 warnings
- `extract_service` + CLI `extract`（docx / `--file-id` / `--persist`）
- pytest: `test_extract_rules`, `test_extract_pipeline`, `test_extract_persist`（integration skip 无 DB）

## Verify

- `pytest backend/tests -q` → **9 passed, 2 skipped**
- `python -m backend.cli extract example/*.docx` → fields≥7, fee_rows≥2（规则层）

## Notes

- 配置 `.env` 中 API Key 时 CLI 会调 LLM（较慢）；无 Key 时仅规则层。
- 费率「%/年」在部分合同样例中需 LLM 或增强表格解析（后续可调）。
