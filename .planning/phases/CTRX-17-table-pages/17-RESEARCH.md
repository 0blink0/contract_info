# Phase 17 — Research

**Created:** 2026-05-29

## Backend (ready)

- `GET/PUT /jobs/{id}/preview/{section}` — `JobPreviewSectionResponse` with section-scoped fields only.
- `GET /jobs/{id}/verification/{table_key}` — `VerificationRow` with `page_no`, `page_no_note`, `excerpt`.
- List preview rows may include display column `摘录原文` from extraction snippets; verification API is the canonical excerpt table for TBL-03.

## Frontend gap

- `client.ts` only has full `getJobPreview` / `saveJobPreview`.
- `JobTableView` is placeholder.
- `ExportPreview` is 5-tab monolith; only referenced from unrouted `JobDetail.vue`.

## Recommended plan waves

1. API types + client + `useSectionPreview`
2. `TablePreviewEditor` + `VerificationExcerptTable`
3. `JobTableView` integration + dirty guard + tests
