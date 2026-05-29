# Phase 16 — Research

**Created:** 2026-05-29  
**Status:** Complete (planning-only; CONTEXT locked)

## Question

How to introduce v1.3 nested job detail routes without breaking Electron hash routing, existing onboarding gate, or v1.2 poll semantics?

## Findings

### Router

- `frontend/src/router/index.ts` uses `createWebHashHistory` when `VITE_ELECTRON=1`; nested `children` under `/jobs/:id` work with hash URLs (`#/jobs/uuid/tables/fee-rates`).
- Replace flat `job-detail` route with parent `JobDetailLayout` + default child `job-hub` (empty path).
- Invalid `tableKey`: use `beforeEnter` on table child calling `isValidTableKey` → redirect `{ name: 'job-hub', params: { id } }`.

### Poll (FE-02)

- `useJobPoll` already keyed on `jobId` + `status` ref; move to `JobDetailLayout` only.
- `provide(JOB_DETAIL_KEY, { jobId, detail, loading, status, refresh: poll.refresh, activate: poll.activate })`.
- Child views use `inject` + optional `assertJobDetailContext()` helper; **grep** `useJobPoll` in `views/` after phase — must be zero outside layout.

### AppLayout submenu (NAV-01)

- Second `el-menu` block OR nested items under aside: use `el-sub-menu` with `index="job-detail-nav"` when `route.params.id` is string.
- `default-openeds` includes `job-detail-nav` while in job context.
- Job submenu uses `router` mode with `:index` = full path strings built from `route.params.id` + `jobSections` constants.

### Chrome extraction from JobDetail.vue

- **Move to Layout:** loadDetail, poll, start/retry, delete, title row, ProcessStepper, error alert, WarningsList (pipeline feedback).
- **Remove from routed tree:** ExportPreview, ValidationPanel, PathBPanel (Phase 17–18).
- **Optional bridge:** keep exported-state bulk download buttons in Layout until Phase 17 per-table downloads (reduces regression during stub period).

### Tests

- Project uses `node --test` + static router source assertions (`tests/router/wizard-gate.test.mjs`), not vitest — align D-26 with `test:router` script.

## Recommendation

Three-wave plans: (1) constants + layout + router + context, (2) AppLayout submenu + stub views + entry links, (3) router tests + typecheck gate.
