---
phase: 15
slug: api
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-29
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`contract_info/pytest.ini`) |
| **Config file** | `contract_info/pytest.ini` |
| **Quick run command** | `pytest backend/tests/test_preview_edit.py backend/tests/test_parallel_run.py -q` |
| **Full suite command** | `pytest backend/tests -q --ignore=backend/tests/golden -m "not llm"` |
| **Estimated runtime** | ~60–120 seconds (non-LLM) |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | API-03 | unit | `pytest backend/tests/test_parallel_run.py -x` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | UP-04 | api | `pytest backend/tests/test_parallel_run.py -x` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 2 | API-01 | unit | `pytest backend/tests/test_preview_edit.py -x` | ⚠️ extend | ⬜ pending |
| 15-02-02 | 02 | 2 | API-01 | api | `pytest backend/tests/test_preview_section_api.py -x` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 3 | API-02 | unit | `pytest backend/tests/test_verification_service.py -x` | ❌ W0 | ⬜ pending |
| 15-03-02 | 03 | 3 | API-02 | api | `pytest backend/tests/test_api_verification.py -x` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `backend/app/services/job_runner_service.py`
- [ ] `backend/tests/test_parallel_run.py`
- [ ] `backend/tests/test_preview_section_api.py`
- [ ] `backend/tests/test_verification_service.py`
- [ ] `backend/tests/test_api_verification.py`
- [ ] `backend/app/main.py` lifespan shutdown hook
- [ ] Optional fields on `JobPreviewUpdateRequest`

---

## Phase Gate

```bash
pytest backend/tests -q -m "not llm" --ignore=backend/tests/golden
```
