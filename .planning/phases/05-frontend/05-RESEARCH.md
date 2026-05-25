# Phase 5 Research: 前端上传与下载

**Researched:** 2026-05-25  
**Phase:** 5 — 前端  
**Focus:** Vue 3 SPA、API 扩展、步骤条与轮询

## Summary

Greenfield `frontend/` 消费既有 Phase 4 API，并增加 **列表 + warnings 详情** 两个后端字段。推荐 **Vite proxy** 联调（端口 **5173**，与 CORS 默认一致）。UI 用 **Element Plus** 可快速实现步骤条、上传、列表（CONTEXT 裁量）。

## Backend extensions

| 端点/字段 | 用途 |
|-----------|------|
| `GET /api/v1/jobs?limit=20` | 历史列表，按 `created_at` DESC |
| `JobDetailResponse.extraction_warnings` | `list[{field, code, message, suggestion?}]`，来自 DB JSONB |

列表路由须注册在 `GET /{job_id}` **之前**（FastAPI 路径顺序）。

## Frontend structure

```
frontend/
  package.json
  vite.config.ts      # proxy /api → 127.0.0.1:8000, port 5173
  src/
    main.ts
    App.vue
    api/client.ts     # fetch + VITE_API_KEY
    api/types.ts
    composables/useJobPoll.ts
    constants/status.ts   # status → stepper state
    components/
      UploadPanel.vue
      JobList.vue
      JobDetail.vue
      ProcessStepper.vue
      WarningsList.vue
```

## Status → stepper

| status | 解析 | 抽取 | 导出 |
|--------|------|------|------|
| pending | wait | wait | wait |
| parsing | process | wait | wait |
| parsed | finish | wait | wait |
| extracting | finish | process | wait |
| extracted | finish | finish | wait |
| exporting | finish | finish | process |
| exported | finish | finish | finish |
| failed | error | wait | wait |
| extraction_failed | finish | error | wait |
| export_failed | finish | finish | error |

`IN_PROGRESS` 集合：`parsing`, `extracting`, `exporting` — 启用轮询。

## Polling

- 间隔 **2500ms**（2–3s 中值）
- 选中任务且 status 属于 in-progress 时启动；切换任务或终态时 `clearInterval`
- 网络错误：可选单次退避，不阻塞 UI

## API client

```typescript
const headers: HeadersInit = {}
if (import.meta.env.VITE_API_KEY) {
  headers['X-API-Key'] = import.meta.env.VITE_API_KEY
}
```

下载：`<a href="/api/v1/jobs/{id}/download/product-elements">` 或 `fetch` + blob；带 Key 时用 fetch+blob 更稳。

## Reference

- `ai_bid_management/bid_tool_agents/frontend/vite.config.ts` — proxy 模式
- `backend/app/extract/schemas.py` — `ExtractionWarning` 字段

## RESEARCH COMPLETE
