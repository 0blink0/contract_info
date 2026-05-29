# Phase 16 — Patterns

**Maps new work to closest existing frontend patterns.**

| New artifact | Closest analog | Notes |
|--------------|----------------|-------|
| `JobDetailLayout.vue` | `JobDetail.vue` + `AppLayout.vue` | Extract chrome from JobDetail; parent `<router-view />` like AppLayout |
| `useJobDetailContext.ts` | `useJobPoll.ts` | InjectionKey + typed inject; poll stays in layout only |
| `jobSections.ts` | `constants/status.ts` | Frozen const arrays + type guards |
| Nested `/jobs/:id` routes | Global routes in `router/index.ts` | Same lazy `import()` style |
| `JobHubView` nav cards | `FileListView` row-click → router | `router-link` or `RouterLink` to named routes |
| Router tests | `tests/router/wizard-gate.test.mjs` | Read `index.ts` as text; assert route names/paths |

**Anti-patterns to avoid**

- Calling `useJobPoll` inside `JobTableView` / `JobHubView`.
- Mounting `JobDetail.vue` on any route (keeps duplicate poll + v1.2 stack).
- Flat table paths (`/jobs/:id/fee-rates`) — conflicts with NAV-02.
