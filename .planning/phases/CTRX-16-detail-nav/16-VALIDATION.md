---
phase: 16
slug: detail-nav
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-29
---

# Phase 16 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `node --test` (frontend router); `vue-tsc` (types) |
| **Quick run** | `cd frontend && npm run test:router` |
| **Typecheck** | `cd frontend && npm run typecheck` |
| **Build smoke** | `cd frontend && npm run build` |

## Per-Plan Gate

| Plan | After complete |
|------|----------------|
| 16-01 | `npm run typecheck` |
| 16-02 | Manual: open job → submenu visible → click each child route |
| 16-03 | `npm run test:router` + `npm run typecheck` |

## Phase Gate

```bash
cd contract_info/frontend && npm run test:router && npm run typecheck
```

## Manual UAT (ROADMAP Success Criteria)

1. 进入任务后左侧「文件详情」子菜单含 5 表 + 字段 B，可折叠，默认展开。
2. 刷新 `/jobs/:id`、`/jobs/:id/tables/product-elements`、`/jobs/:id/field-b` 停留当前页。
3. 文件列表进入默认 Hub；子菜单高亮与 URL 一致。
4. 子页切换时 Network 仅 Layout 周期 `GET /jobs/{id}`（无子页重复全量 poll）。
