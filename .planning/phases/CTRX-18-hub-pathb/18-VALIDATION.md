---
phase: 18
slug: hub-pathb
status: draft
created: 2026-05-29
---

# Phase 18 — Validation

| Gate | Command |
|------|---------|
| Typecheck | `cd frontend && npm run typecheck` |
| Tests | `cd frontend && npm run test:router` |
| Build | `cd frontend && npm run build` |

## Manual UAT

1. Hub：exported 任务见五表行数 + 字段 B 摘要；无 ExportPreview 大表。
2. Hub：warnings 列表可见；展开校验面板可看 fail/warn。
3. 字段 B 页：CRM 表、原文块、复制/下载 JSON；页码列显示「页码暂未解析」或等价提示。
4. 表页无 ValidationPanel/WarningsList 堆叠。
