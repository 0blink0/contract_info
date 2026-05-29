# 16-01 Summary — Layout, router, inject

**Status:** Complete  
**Commit:** (see phase-16 commit)

## Delivered

- `frontend/src/constants/jobSections.ts`
- `frontend/src/composables/useJobDetailContext.ts`
- `frontend/src/layouts/JobDetailLayout.vue` — chrome + single `useJobPoll` + `provide`
- Nested routes in `router/index.ts`; removed `JobDetailView.vue`
- Stub/full child views: `JobHubView`, `JobTableView`, `JobFieldBView`

## Verification

- `npm run typecheck` — pass
