---
phase: 06-extract-quality
plan: "03"
subsystem: testing
tags: [e2e, export, llm, pytest]

requires:
  - phase: 06-01
    provides: pipeline_runner and xlsx_diff
  - phase: 06-02
    provides: rule fixes for export inputs
provides:
  - TEST-01 export E2E golden tests
  - QUAL-03 optional LLM fill-rate comparison

key-files:
  created:
    - backend/tests/golden/test_golden_export.py
    - backend/tests/golden/test_golden_llm.py
  modified:
    - pytest.ini

requirements-completed: [TEST-01, QUAL-03]

duration: 20min
completed: 2026-05-26
---

# Phase 6 Plan 03 Summary

**Export E2E golden diff for both contracts (no LLM) and optional LLM baseline tests gated by `@pytest.mark.llm`.**

## Accomplishments

- `test_golden_export.py`: parse→extract→export for 石云/福禄; Critical product + fee types + lock row counts
- `test_golden_llm.py`: LlmOff vs LlmClient fill rate ≥80% on long-text Critical fields when API key present
- `pytest.ini` marker description updated for Chinese CI docs

## Self-Check: PASSED

- `pytest backend/tests/golden/ -q -m "not llm"` — 15 passed
- `pytest backend/tests/ -q -m "not llm"` — 55 passed
