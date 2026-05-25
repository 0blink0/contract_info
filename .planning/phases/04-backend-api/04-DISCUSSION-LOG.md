# Phase 4 Discussion Log

**Date:** 2026-05-25  
**Participants:** User + GSD discuss-phase

Decisions are canonical in `04-CONTEXT.md`. This log records alternatives considered.

## Gray areas discussed

1. 任务模型  
2. 处理模式  
3. 路由与响应  
4. 上传约束 / 鉴权 / CORS  
5. 下载行为  

## Choices

| Topic | Chosen | Alternatives not chosen |
|-------|--------|-------------------------|
| Job ID | `contract_files.id` | Separate `jobs` table |
| Status in API | Granular DB `status` | Coarse pending/processing/completed; hybrid `phase` field |
| Pipeline trigger | Upload then `POST .../run` | Sync on upload; BackgroundTasks on upload only |
| Run behavior | Resume from current state | Full pipeline always; single-step only |
| Run response | 202 + background | Sync blocking `run` |
| Route prefix | `/api/v1/...` | Flat `/upload` per REQUIREMENTS text only |
| Auth | `X-API-Key` vs `API_KEY` in `.env` | No auth; CORS `*` only |
| Upload limit | `.docx` extension only | 20MB / 50MB caps |
| Download | Two endpoints; `exported` only | Partial download when extracted; ZIP in Phase 4 |

## Notes

- User wants operational flow: upload multiple contracts, then trigger processing per job.
- REQUIREMENTS still name `/upload` and `/jobs/{id}` — implement under `/api/v1` prefix (document in OpenAPI).
