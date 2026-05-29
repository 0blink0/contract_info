# Phase 19 — Research

**Created:** 2026-05-29

## Backend

- Phase 15: `count_in_progress()` + run 409 with `{ detail, active_count }` — **done**.
- Gap: no `GET /jobs/concurrency` for upload UI — add in 19-01.

## Frontend

- `UploadView`: single file, single `useJobPoll` — replace entirely.
- Element Plus `el-upload` supports `limit` + `multiple` + `on-exceed`.

## Plan waves

1. Concurrency endpoint + client + constant `MAX_PARALLEL_JOBS = 3`
2. `useJobsPoll` + `UploadJobCard`
3. `UploadView` rewrite + tests
