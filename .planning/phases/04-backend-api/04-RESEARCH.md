# Phase 4 Research: 后端 API

**Researched:** 2026-05-25  
**Phase:** 4 — 后端 API  
**Focus:** FastAPI 集成、上传/续跑编排、鉴权与测试策略

## Summary

Phase 4 在现有 CLI 服务层之上增加 HTTP 入口。核心难点不是新算法，而是 **拆分「仅上传」与「按状态续跑」**，并让 **BackgroundTasks** 与 SQLAlchemy session 生命周期安全配合。参考同仓 `bid_tool_agents` 的 FastAPI 路由与 `Depends` 鉴权模式，但保持 CTRX 更小的 API 面（5 个业务端点 + health）。

## Technical Findings

### 1. 依赖

| 包 | 用途 |
|----|------|
| `fastapi>=0.110` | 路由、TestClient、BackgroundTasks |
| `uvicorn[standard]>=0.27` | ASGI 服务 |
| `python-multipart` | `UploadFile` |

`httpx` 已在 requirements（LLM）；TestClient 内置，无需额外包。

### 2. 服务层拆分（相对 `persist_parse`）

当前 `persist_parse(path)` **一步完成**：复制文件 → insert → parse → `parsed`。

API 需要：

| 函数 | 行为 |
|------|------|
| `persist_upload(file_bytes, filename)` | 生成 `file_id`，写入 `uploads/{id}/`，`status=pending`，**不** parse |
| `parse_file_id(file_id)` | 从 `storage_path` 读 docx，`parsing` → `parsed` / `failed` |
| `persist_extract` / `persist_export` | 已有，直接复用 |

`pipeline_service.run_pipeline(file_id)` 根据 `status` 分支调用上表（CONTEXT D-05）。

### 3. 状态机（实现须与代码一致）

| status | 含义 | run 行为 |
|--------|------|----------|
| `pending` | 已上传未解析 | parse → extract → export |
| `parsing` / `extracting` / `exporting` | 进行中 | **409**，禁止并发 run |
| `parsed` | 可抽取 | extract → export |
| `extracted` | 可导出 | export only |
| `exported` | 完成 | **409** 或 no-op |
| `failed` | 解析失败（parse_service 现用） | 允许 **重试 run**（重新 parse 链） |
| `extraction_failed` | 抽取失败 | run → extract → export |
| `export_failed` | 导出失败 | run → export only |

CONTEXT 中的 `parse_failed` 与 DB 实际 **`failed`** 对齐；API 文档与响应使用 DB 原值。

### 4. FastAPI 结构建议

```
backend/app/
  main.py              # app factory, CORS, include_router
  api/
    deps.py            # verify_api_key, get_db optional
    schemas.py         # JobResponse, UploadResponse
    routes/
      health.py
      jobs.py          # upload, get, run, download
  services/
    upload_service.py
    pipeline_service.py
```

- **鉴权：** `APIRouter(dependencies=[Depends(verify_api_key)])`；`/api/v1/health` 单独 router 无依赖。
- **API Key：** `Settings.api_key`；空字符串时 **跳过校验**（本地 dev），非空则必须 `X-API-Key` 匹配。
- **CORS：** `Settings.cors_origins` 逗号分隔，默认 `http://localhost:5173`。

### 5. BackgroundTasks 与测试

- `POST .../run` 返回 **202** 后立即 `background_tasks.add_task(pipeline_service.run_pipeline, file_id)`。
- pytest：对 integration 可用 **同步包装** `run_pipeline` 的 test dependency override，或 `TestClient` + 短轮询；无 Docker 时 mock `SessionLocal` / 仅测 upload + 401 + schema。
- 下载：`FileResponse(path, media_type=..., filename=...)`，`status != exported` → **409**。

### 6. 启动命令

```bash
cd contract_info
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI：`http://localhost:8000/docs`

## Risks & Mitigations

| 风险 | 缓解 |
|------|------|
| 后台任务异常未写 DB | pipeline 顶层 try/except 写 `error_message` + `*_failed` |
| 大 JSON 拖慢 GET job | 响应 **不含** `parse_json` / `extraction_result` 全文；仅 `outline_preview` 条数或省略 |
| LLM 慢导致 run 超时 | HTTP 已 202；无客户端超时问题 |
| 路径遍历下载 | 仅通过 DB 存的路径拼接 `PROJECT_ROOT`，校验 resolved path 在 exports/ 下 |

## References

- `04-CONTEXT.md` — 用户锁定决策
- `backend/app/services/*.py` — 现有 persist 逻辑
- `ai_bid_management/bid_tool_agents/backend/app/api/v1/files.py` — 上传/后台任务模式参考

## RESEARCH COMPLETE
