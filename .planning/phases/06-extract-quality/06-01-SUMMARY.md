---
phase: 06-extract-quality
plan: "01"
subsystem: testing
tags: [pytest, golden, regression]

requires: []
provides:
  - tests/golden/ scaffold with contract_expected.json
  - normalize, pipeline_runner, xlsx_diff helpers
  - golden conftest with D-G01 docx paths

key-files:
  created:
    - backend/tests/golden/README.md
    - backend/tests/golden/conftest.py
    - backend/tests/golden/fixtures/contract_expected.json
    - backend/tests/golden/helpers/normalize.py
    - backend/tests/golden/helpers/pipeline_runner.py
    - backend/tests/golden/helpers/xlsx_diff.py
  modified:
    - backend/tests/test_shiyun_contract_rules.py

requirements-completed: [QUAL-01, QUAL-02, TEST-01]

duration: 25min
completed: 2026-05-26
---

# Phase 6 Plan 01 Summary

**Golden test infrastructure: contract truth fixtures, normalization helpers, and LlmOff pipeline runner for Wave 2 E2E.**

## Accomplishments

- `tests/golden/` package with README documenting Critical fields, four-class emptiness, and CI/`llm` markers
- `contract_expected.json` for both 石云 docx keys with `fee_rates_by_type` and lock period hints
- Helpers for cell normalization, parse→extract→export without LLM, and xlsx Critical diff
- `conftest.py` fixtures aligned to `example/*.(1).docx` paths; fixed `test_shiyun_contract_rules.py` docx path

## Self-Check: PASSED

- `pytest backend/tests/golden/ --collect-only` — OK
- Helper import smoke — OK
