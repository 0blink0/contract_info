---
phase: 19
slug: multi-upload
status: draft
created: 2026-05-29
---

# Phase 19 — Validation

| Gate | Command |
|------|---------|
| Backend | `pytest backend/tests/test_parallel_run.py backend/tests/test_api_concurrency.py -q` |
| Frontend | `cd frontend && npm run test:router && npm run typecheck && npm run build` |

## Manual UAT

1. 选 4 个 docx → 第 4 个被阻止并提示。
2. 上传 2–3 个 → 各卡独立步骤与状态更新。
3. 「全部开始处理」→ 多 pending 同时推进；第 4 路 run（若槽满）显示 409 提示。
4. Network：多 job 周期 GET /jobs/{id}，非仅一个 id。
