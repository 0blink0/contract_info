# Phase 15: 后端并行与分表 API - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段仅交付**后端**能力，支撑 v1.3 后续前端阶段：

1. 全局最多 **3** 个 job 同时处于 pipeline 执行中；第 4 路 `POST /run` 返回 **409** 与可读中文/英文 detail。
2. **分表** `GET/PUT /jobs/{id}/preview/{section}`，PUT 不得因缺省字段清空其它表的 `extraction_result`。
3. **按表核对** `GET /jobs/{id}/verification/{table_key}`，返回字段名、字段值、摘录页码、原文摘录（页码可空并带说明）。
4. 有界 **ThreadPoolExecutor(max_workers=3)** 执行 `run_pipeline`，每任务独立 `SessionLocal()`。

不在本阶段：上传页 UI、Vue 路由/子菜单、Hub/表页组件、字段 B 专页 UI、批量 upload 端点（可 Phase 19 再议）。

</domain>

<decisions>
## Implementation Decisions

### 并行槽位与 409 语义（UP-04）
- **D-01:** 仅 `IN_PROGRESS = {parsing, extracting, exporting}` 计入并发槽；`pending` **不占槽**（已上传未点开始不阻塞他人）。
- **D-02:** `POST /run` 在入队前查询 DB：`COUNT(*) WHERE status IN IN_PROGRESS`；若 ≥3 则 **409**，detail 示例：`"已有 3 个任务正在处理，请稍后再试"`（可同时返回 `active_count: 3` 供前端展示）。
- **D-03:** 单 job 若自身已在 `IN_PROGRESS`，仍走现有 `PipelineBusyError`（409）；与全局槽位错误区分 status code 相同但 detail 文案不同。

### 并行执行器（API-03）
- **D-04:** 引入模块级 **`JobRunner`**（`ThreadPoolExecutor(max_workers=3)` + 提交队列）；`run_job` 不再对每个请求直接 `background_tasks.add_task(run_pipeline)`，改为 `runner.submit(file_id)`。
- **D-05:** `run_pipeline` 保持同步实现；worker 线程内 **新建 `SessionLocal()`**，禁止跨线程共享 session。
- **D-06:** 应用关闭/测试 teardown 时 `executor.shutdown(wait=False)`（或 wait=True 在 pytest fixture）避免挂死。

### 分表 preview 契约（API-01）
- **D-07:** 新增 **`GET/PUT /jobs/{job_id}/preview/{section}`**，`section` 枚举：
  - `product-elements` → `product_rows` / `product_elements`
  - `fee-rates` → `fee_*` / `fee_rates`
  - `lock-periods` → `lock_*` / `lock_periods`
  - `share-classes` → `share_*` / `share_classes`
  - `subscription-fee-rates` → `subscription_*` / `subscription_fees`
- **D-08:** 分表 PUT body 仅含该 section 字段（专用 Pydantic model）；服务端 **只 merge 对应 extraction 子树**，绝不将未提交表写成 `[]`。
- **D-09:** **保留** `GET/PUT /jobs/{id}/preview` 全量端点供 v1.2 前端过渡；**同阶段修复**全量 PUT：`JobPreviewUpdateRequest` 改为字段 **Optional**（未传 = 不修改），禁止 `payload.get("fee_rows") or []` 语义。OpenAPI/description 标注「新客户端请用分表 PUT」。
- **D-10:** 分表 GET 返回结构与全量 preview 中对应片段一致（便于 Phase 17 直接绑定 `JobTableView`）。

### 分表保存后的 export（Claude discretion，按调研推荐）
- **D-11:** 任一分表 PUT 成功后仍调用现有 **`persist_export(file_id)` 重生成全部五表 xlsx**（与 v1.2 一致，避免单表文件与 extraction 不一致）。不在 Phase 15 做单表增量 export。

### 按表核对端点（API-02）
- **D-12:** 新增 `GET /jobs/{job_id}/verification/{table_key}`，`table_key` 与 `section` 同名五表枚举。
- **D-13:** 行数据 **主数据源为 `extraction_result`**（产品要素 dict、各 list 表的 snippet 字段）；列：`field_label`（中文）、`field`（内部键）、`value`、`page_no`、`excerpt`。
- **D-14:** 若存在 `validation_result.items`，按 `field` 路径匹配合并行，**附加** `validation_status` / `validation_reason`（可选字段），但不作为唯一数据源（避免无 validation 时表为空）。
- **D-15:** 响应 schema：`TableVerificationResponse { job_id, table_key, rows: VerificationRow[], page_no_available: bool }`。

### 页码列（Phase 15 深度 — 按调研「轻量估算」）
- **D-16:** **本阶段实现**轻量页码：在 `build_verification_rows` 时，若 `document_json` / outline blocks 含 `page` 或可从 parse 阶段写入的 `page_index` 读取则填入；否则 `page_no: null`，`page_no_note: "页码暂未解析"`（或英文 key `page_no_status: "unavailable"`）。
- **D-17:** 不在 Phase 15 引入 PDF/LibreOffice；若 parse 层尚无页信息，允许 **全部 null** 但 API 契约与 schema 必须稳定，Phase 17 UI 可展示「—」。
- **D-18:** 字段 B（path-b）**不在**本 verification 端点；留给 Phase 18（`GET /path-b` 已有摘录）。

### 并行 LLM 校验（Claude discretion，按调研推荐）
- **D-19:** 在 `persist_extract` 触发 LLM validation 的路径上加 **进程内全局 `threading.Semaphore(2)`**（最多 2 路同时打 LLM API），第 3 路 pipeline 在 validation 步骤阻塞等待。
- **D-20:** 不跳过 validation；不改为「仅 Hub 手动触发」——保持 v1.2 行为，仅削峰。
- **D-21:** 若 validation skipped（无 API key），行为与 v1.2 相同，不受 semaphore 影响。

### 测试与契约
- **D-22:** 必测：单表 PUT 后其它四表 `extraction_result` 行数不变；3 路并行 smoke；第 4 路 run 409；分表 GET 与全量 GET 片段一致。
- **D-23:** 扩展 `test_preview_edit.py` 覆盖分表 PUT；新增 `test_parallel_run.py`（可 mock `persist_extract` 加速）。

### Claude's Discretion（用户：「按推荐走」）

用户授权按 v1.3 调研（SUMMARY / ARCHITECTURE / PITFALLS）默认选项执行，未逐项问答。上述 D-01–D-23 即锁定实现偏好。

### Folded Todos

（无）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 里程碑与需求
- `contract_info/.planning/PROJECT.md` — v1.3 目标与 Out of Scope
- `contract_info/.planning/REQUIREMENTS.md` — UP-04, API-01~03 验收条文
- `contract_info/.planning/ROADMAP.md` — Phase 15 目标与 Success Criteria

### v1.3 调研（实现顺序与陷阱）
- `contract_info/.planning/research/SUMMARY.md` — 构建顺序、P0 风险
- `contract_info/.planning/research/ARCHITECTURE.md` — JobRunner、分表 API、路由（前端 Phase 16+）
- `contract_info/.planning/research/PITFALLS.md` — 全量 PUT 清空、假并行、LLM 风暴

### 字段与业务规格
- `contract_info/FIELD_SPEC.md` — 五表字段中文名、extraction 键映射

### 现有后端（修改锚点）
- `contract_info/backend/app/services/pipeline_service.py` — `run_pipeline`, `IN_PROGRESS`
- `contract_info/backend/app/api/routes/jobs.py` — `run_job`, preview, validation
- `contract_info/backend/app/services/preview_edit_service.py` — `apply_preview_edits`（须拆分为分表 merge + 修复全量 PUT）
- `contract_info/backend/app/services/preview_service.py` — `build_job_preview`, `get_job_preview`
- `contract_info/backend/app/api/schemas.py` — `JobPreviewUpdateRequest`, 新增分表/verification schema
- `contract_info/backend/tests/test_preview_edit.py` — 回归基线
- `contract_info/backend/tests/test_api_pipeline.py` — run 行为

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline_service.IN_PROGRESS` / `assert_can_run` — 扩展为全局槽位查询 + 单 job 状态检查。
- `preview_edit_service._apply_product_edits` / `_apply_list_table_edits` — 拆成按 section 调用，避免重复逻辑。
- `GET /jobs/{id}/validation` + `ValidationItemResponse` — 核对行可复用 `field_label`、`evidence_text` 映射为 `excerpt`。
- `persist_export` — 分表保存后仍统一调用。

### Established Patterns
- 路由均在 `backend/app/api/routes/jobs.py`，Pydantic schema 在 `schemas.py`。
- 服务层短事务：`SessionLocal()` + try/finally close。
- 错误映射：`LookupError`→404，`ValueError`→409，`PipelineBusyError`→409。

### Integration Points
- `POST /jobs/{id}/run` — 接入 JobRunner + 全局槽位检查。
- 新路由注册在 `jobs.router`，需在 Phase 16 前保持 v1.2 前端仍可用全量 preview（修复后）。
- Electron 单进程后端：并行上限 3 为硬约束，与 SQLite WAL 一致。

</code_context>

<specifics>
## Specific Ideas

- 用户确认里程碑范围后，Phase 15 讨论选择 **「按推荐走」**，与调研结论一致。
- 409 文案需运营可读（中文），便于上传页展示「请等待其它任务完成」。

</specifics>

<deferred>
## Deferred Ideas

- `POST /upload/batch` 单次 multipart 多文件 — 属 Phase 19；Phase 15 不强制，维持 3× `POST /upload` + 并行 run。
- 单表 `persist_export` 仅重导一张 xlsx — 性能优化，post-v1.3。
- PATHB 页码与 verification 合并 — Phase 18。
- Pinia 缓存全量 preview 作为全量 PUT 替代方案 — 已用分表 API + 修复全量 PUT 取代。

</deferred>

---

*Phase: 15-后端并行与分表 API*
*Context gathered: 2026-05-29*
