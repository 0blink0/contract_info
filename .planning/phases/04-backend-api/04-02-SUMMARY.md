# 04-02 Summary

**Completed:** 2026-05-25  
**Plan:** pipeline 续跑、run 202、下载、API 测试、README

## Delivered

- `pipeline_service` — resume from pending/parsed/extracted/failed states
- `POST /api/v1/jobs/{id}/run` → 202 + BackgroundTasks
- `GET .../download/product-elements` and `.../fee-rates` (exported only)
- README HTTP API section with curl examples
- pytest: pipeline 409/202, download 409/200

## Verification

`pytest backend/tests -q` → 26 passed, 3 skipped
