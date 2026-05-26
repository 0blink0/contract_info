---
phase: 06-extract-quality
plan: "02"
subsystem: extract
tags: [merge, fee_rules, lock_rules, golden]

requires:
  - phase: 06-01
    provides: golden fixtures and conftest
provides:
  - QUAL-04 merge_field with is_invalid_rule_value
  - Fulu 基金服务费 and lock false-positive fixes
  - Rule-layer golden tests for 石云/福禄

key-files:
  created:
    - backend/tests/test_merge_field.py
    - backend/tests/golden/test_golden_rules_shiyun.py
    - backend/tests/golden/test_golden_rules_fulu.py
  modified:
    - backend/app/extract/merge.py
    - backend/app/extract/pipeline.py
    - backend/app/extract/rules/fee_rules.py
    - backend/app/extract/rules/lock_rules.py
    - backend/tests/golden/README.md

requirements-completed: [QUAL-01, QUAL-02, QUAL-04]

duration: 30min
completed: 2026-05-26
---

# Phase 6 Plan 02 Summary

**Merge mis-extract guardrails and rule-layer fixes so 石云/福禄 Critical fields match contract truth without golden xlsx parties.**

## Accomplishments

- `merge_field(field_name=…)` with `is_invalid_rule_value`, party/long-text/预警止损 priorities (QUAL-04)
- `lock_rules`: empty product lock period → no subscription-chapter false positives (福禄)
- `fee_rules`: 外包服务费 → 基金服务费 via document-text fallback (福禄 0.01%)
- `test_golden_rules_shiyun.py` / `test_golden_rules_fulu.py` — 10+ rule assertions vs `contract_expected.json`

## Self-Check: PASSED

- `pytest backend/tests/test_merge_field.py backend/tests/golden/test_golden_rules_*.py -q -m "not llm"` — 13 passed
