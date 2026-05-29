---
phase: 17
slug: table-pages
status: draft
nyquist_compliant: true
created: 2026-05-29
---

# Phase 17 — Validation Strategy

| Gate | Command |
|------|---------|
| Typecheck | `cd frontend && npm run typecheck` |
| Router/client | `cd frontend && npm run test:router` |
| Build | `cd frontend && npm run build` |

## Manual UAT

1. 打开已 `exported` 任务 → 任一张表 → 列与 v1.2 tab 一致，可编辑。
2. 改单元格 → 保存 → 下载该表 xlsx → 内容已更新。
3. 核对表显示字段/值/页码/摘录；页码不可用时见说明或「—」。
4. 未保存切换侧栏另一表 → 确认框。
5. Network：表页仅 `GET preview/{section}`、`PUT preview/{section}`、`GET verification/{key}`，无重复 `GET /jobs/{id}` 轮询（除 Layout poll）。
