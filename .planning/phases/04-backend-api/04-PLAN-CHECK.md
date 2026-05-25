# Phase 4 Plan Check

**Checked:** 2026-05-25  
**Verdict:** PASS

## ROADMAP success criteria

| Criterion | Plan coverage |
|-----------|----------------|
| curl 上传 docx 返回 job_id | 04-01 upload + 04-02 README curl |
| 轮询 status 直至 completed/failed | 04-02 GET job + granular status（`exported` / `*_failed`） |
| 下载正确 Content-Type 与文件名 | 04-02 FileResponse + test_api_download |

## Requirements

| ID | Plans |
|----|-------|
| API-01 | 04-01 upload；04-02 run 202 + BackgroundTasks |
| API-02 | 04-01 GET job；04-02 扩展字段 |
| API-03 | 04-02 两个 download 端点 |
| DOC-01 | 04-01 upload docx |
| DOC-03 | 04-01 persist_upload → contract_files |
| XLS-03 | 04-02 download after export |
| DEV-01 | 04-02 README API 节 |

## CONTEXT alignment (D-01–D-18)

| Decision | Plans |
|----------|-------|
| job_id = file id | 04-01 UploadResponse.job_id |
| Granular status in GET | 04-01/02 JobDetailResponse |
| Upload only pending | 04-01 persist_upload |
| run resume + 202 async | 04-02 pipeline + BackgroundTasks |
| /api/v1 prefix | 04-01 main routers |
| X-API-Key | 04-01 deps |
| CORS localhost:5173 | 04-01 config |
| .docx only, no size cap | 04-01 upload validation |
| exported-only download | 04-02 download 409 |
| Keep CLI | 04-01 parse_service 兼容 |
| TestClient tests | 04-01/02 pytest |

## Waves

- **Wave 1 (04-01):** 依赖、upload/parse 拆分、FastAPI 骨架、upload+auth 测试  
- **Wave 2 (04-02):** pipeline、run、download、E2E 测试、README  

**Dependency:** 04-02 depends on 04-01 — valid.

## Notes for executor

- DB 失败状态名：`failed`（非 parse_failed）、`extraction_failed`、`export_failed`
- RESEARCH 允许 `failed` 状态重试 run
- GET job 禁止返回完整 `parse_json` / `extraction_result`
