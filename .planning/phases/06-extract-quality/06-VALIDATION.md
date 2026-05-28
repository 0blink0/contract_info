---
phase: 06
slug: extract-quality
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-26
updated: 2026-05-28
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `contract_info/pytest.ini` |
| **Quick run command** | `python -m pytest backend/tests/golden/ -q -m "not llm"` |
| **Full suite command** | `python -m pytest backend/tests/ -q -m "not llm"` |
| **LLM optional** | `python -m pytest backend/tests/golden/ -m llm` |
| **Estimated runtime** | ~30–90 seconds (no LLM) |

---

## Sampling Rate

- **After every task commit:** Run quick golden suite (`-m "not llm"`)
- **After every plan wave:** Run full `backend/tests/` without llm marker
- **Before `/gsd:verify-work`:** Full non-llm suite green; optional llm locally

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 06-01-01~03 | 01 | 0 | TEST-01, QUAL-01–02 | infra | `pytest backend/tests/golden/ -q -m "not llm" --collect-only` | pending |
| 06-02-01 | 02 | 1 | QUAL-04 | unit | `pytest backend/tests/test_merge_field.py -x` | pending |
| 06-02-02~03 | 02 | 1 | QUAL-01–02 | integration | `pytest backend/tests/golden/test_golden_rules_*.py -x -m "not llm"` | pending |
| 06-03-01 | 03 | 2 | TEST-01 | integration | `pytest backend/tests/golden/test_golden_export.py -x -m "not llm"` | pending |
| 06-03-02 | 03 | 2 | QUAL-03 | e2e | `pytest backend/tests/golden/test_golden_llm.py -m llm` | pending |

---

## Wave 0 Gaps

- [ ] `backend/tests/golden/` + README + fixtures
- [ ] `contract_expected.json` from `example/_contract_keys.json`
- [ ] `test_merge_field.py`, golden export/rules tests
- [ ] Fix `test_shiyun_contract_rules.py` docx `(1)` paths

---

*Phase: 06-extract-quality · 2026-05-26*
