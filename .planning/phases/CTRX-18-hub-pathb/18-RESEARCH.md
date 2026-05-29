# Phase 18 — Research

**Created:** 2026-05-29

## Ready to reuse

- `getJobPreviewSection` ×5 for hub row counts (Phase 17 client).
- `getPathB`, `getValidation` — already in `client.ts`.
- `PathBPanel.vue` — full CRM/raw/json UX; needs composable extract + full-page variant.
- `ValidationPanel.vue` — collapse + lazy load; drop into Hub as-is with inject props.
- `WarningsList.vue` — move from Layout to Hub.

## Gaps

- Hub placeholder text still says Phase 18 pending.
- `PathBResponse` has no dedicated page_no; PB-01 satisfied via UI note + 「页码暂未解析」.

## Wave split

1. Hub summary composable + cards + JobHubView upgrade  
2. Warnings/Validation on Hub; strip from Layout  
3. PathB composable + PathBDetail + JobFieldBView + tests
