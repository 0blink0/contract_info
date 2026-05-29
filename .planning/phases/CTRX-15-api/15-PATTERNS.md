# Phase 15: 后端并行与分表 API - Pattern Map

**Mapped:** 2026-05-29  
**Files analyzed:** 16 new/modified targets  
**Analogs found:** 14 / 16

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/services/job_runner_service.py` | service | batch (thread pool) | `pipeline_service.py` + `test_db_wal.py` ThreadPoolExecutor | role-match |
| `backend/app/services/pipeline_service.py` (`count_in_progress`) | utility | CRUD (COUNT query) | `delete_service.py` (`IN_PROGRESS` check) | exact |
| `backend/app/services/verification_service.py` | service | transform | `preview_service.py` + `validate/evidence.py` | exact |
| `backend/app/services/preview_service.py` (`slice_preview`) | utility | transform | `build_job_preview` return dict | exact |
| `backend/app/services/preview_edit_service.py` (section + Optional full) | service | CRUD merge | existing `_apply_*_edits` in same file | exact |
| `backend/app/services/validation_service.py` (Semaphore) | service | request-response (LLM) | `persist_validation` + `extract_service.persist_extract` | exact |
| `backend/app/api/routes/jobs.py` (section preview + verification + run) | route | request-response | existing `preview_job` / `get_validation` / `download_*` | exact |
| `backend/app/api/schemas.py` | config (Pydantic) | request-response | `JobPreviewUpdateRequest`, `ValidationItemResponse` | exact |
| `backend/app/main.py` (lifespan) | config | event-driven (shutdown) | — | **no analog** |
| `backend/tests/test_parallel_run.py` | test | batch | `test_api_pipeline.py` + `test_db_wal.py` | role-match |
| `backend/tests/test_preview_edit.py` | test | CRUD merge | existing `test_apply_preview_edits_*` | exact |
| `backend/tests/test_preview_section_api.py` | test | request-response | `test_api_validation.py` | exact |
| `backend/tests/test_verification_service.py` | test | transform | `test_validation_evidence.py` (if exists) / `test_preview_edit.py` | role-match |
| `backend/tests/test_api_verification.py` | test | request-response | `test_api_validation.py` | exact |
| `backend/tests/test_api_pipeline.py` | test | request-response | self (update patch target) | exact |
| `backend/tests/conftest.py` (optional runner teardown) | test fixture | event-driven | session-scoped fixtures in `conftest.py` | partial |

---

## Pattern Assignments

### `backend/app/services/job_runner_service.py` (service, batch)

**Analog:** `backend/app/services/pipeline_service.py` (worker target) + `backend/tests/test_db_wal.py` (executor sizing)

**Module / executor pattern** (`test_db_wal.py` lines 98-99 — max_workers=3 与 Phase 15 一致):

```98:99:contract_info/backend/tests/test_db_wal.py
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(insert_one, i) for i in range(3)]
```

**Worker 只调 pipeline，不在 worker 内开请求 session** (`pipeline_service.py` lines 48-71):

```48:71:contract_info/backend/app/services/pipeline_service.py
def run_pipeline(file_id: uuid.UUID) -> None:
    from backend.app.db.session import SessionLocal
    from backend.app.models.contract_file import ContractFile

    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise ValueError(f"contract_file not found: {file_id}")
        status = record.status
    finally:
        session.close()

    assert_can_run(status)

    if status in ("pending", "failed"):
        parse_file_id(file_id)
        persist_extract(file_id)
        persist_export(file_id)
    elif status in ("parsed", "extraction_failed"):
        persist_extract(file_id)
        persist_export(file_id)
    elif status in ("extracted", "export_failed"):
        persist_export(file_id)
```

**子服务各自 SessionLocal**（`parse_service.py` lines 12-46）— JobRunner 不得传入路由线程的 session：

```12:27:contract_info/backend/app/services/parse_service.py
def parse_file_id(file_id: uuid.UUID) -> uuid.UUID:
    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        ...
        record.status = "parsing"
        session.commit()
```

**建议骨架：** 模块级 `_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="ctrx-pipeline")`；`submit(file_id)` → `executor.submit(_run_in_worker, file_id)`；`_run_in_worker` 内 `try/except` + `run_pipeline(file_id)`；`shutdown_runner(wait=False)` 供 lifespan/pytest。

---

### `backend/app/services/pipeline_service.py` — `count_in_progress()` (utility, CRUD)

**Analog:** `backend/app/services/delete_service.py` (`IN_PROGRESS` 成员检查)

**IN_PROGRESS 常量** (`pipeline_service.py` lines 9-9):

```9:9:contract_info/backend/app/services/pipeline_service.py
IN_PROGRESS = frozenset({"parsing", "extracting", "exporting"})
```

**状态守门异常** (`pipeline_service.py` lines 39-41):

```39:41:contract_info/backend/app/services/pipeline_service.py
def assert_can_run(status: str) -> None:
    if status in IN_PROGRESS:
        raise PipelineBusyError(f"Job is in progress: {status}")
```

**delete 侧复用 IN_PROGRESS** (`delete_service.py` lines 10-24):

```10:24:contract_info/backend/app/services/delete_service.py
from backend.app.services.pipeline_service import IN_PROGRESS
...
        if record.status in IN_PROGRESS:
            raise JobDeleteBusyError(f"Job is in progress: {record.status}")
```

**COUNT 模式（RESEARCH 推荐，仓库尚无 `func.count` 先例）：** 在 `count_in_progress(session=None)` 中用 `select(func.count()).select_from(ContractFile).where(ContractFile.status.in_(IN_PROGRESS))`；`pending` 不在 `IN_PROGRESS` 内，无需额外过滤。

---

### `backend/app/api/routes/jobs.py` — `POST /run` 全局 409 + JobRunner (route, request-response)

**Analog:** 现有 `run_job` + `delete_job` 409 映射

**当前 run（待替换 BackgroundTasks）** (`jobs.py` lines 192-208):

```192:208:contract_info/backend/app/api/routes/jobs.py
@router.post("/{job_id}/run", response_model=RunResponse, status_code=202)
def run_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
) -> RunResponse:
    record = _get_record(job_id)
    try:
        assert_can_run(record.status)
    except PipelineBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    ...
    background_tasks.add_task(run_pipeline, job_id)
    return RunResponse(job_id=job_id, status=record.status)
```

**插入顺序（D-01–D-03）：** `_get_record` → `assert_can_run`（单 job `PipelineBusyError`，409，detail 字符串）→ `if count_in_progress() >= 3:` → `HTTPException(409, detail={...})`（结构化 dict 含 `active_count`）→ `get_runner().submit(job_id)`；移除 `BackgroundTasks` 参数与 import。

**409 映射惯例**（同文件 `delete_job` lines 187-188）:

```187:188:contract_info/backend/app/api/routes/jobs.py
    except JobDeleteBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
```

**短事务读 record** (`jobs.py` lines 50-59):

```50:59:contract_info/backend/app/api/routes/jobs.py
def _get_record(job_id: uuid.UUID) -> ContractFile:
    session = SessionLocal()
    try:
        record = session.get(ContractFile, job_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Job not found")
        session.expunge(record)
        return record
    finally:
        session.close()
```

---

### `backend/app/api/routes/jobs.py` — 分表 `GET/PUT /preview/{section}` (route, CRUD)

**Analog:** 全量 `preview_job` / `update_job_preview` + 下载路由 section 命名

**Preview GET/PUT 错误映射** (`jobs.py` lines 140-178):

```140:178:contract_info/backend/app/api/routes/jobs.py
@router.get("/{job_id}/preview", response_model=JobPreviewResponse)
def preview_job(job_id: uuid.UUID) -> JobPreviewResponse:
    try:
        data = get_job_preview(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _preview_response_from_data(data)

@router.put("/{job_id}/preview", response_model=JobPreviewResponse)
def update_job_preview(
    job_id: uuid.UUID,
    body: JobPreviewUpdateRequest,
) -> JobPreviewResponse:
    try:
        data = apply_preview_edits(job_id, body.model_dump())
```

**全量 PUT 修复：** 改为 `body.model_dump(exclude_unset=True)` 传入服务层（Pydantic v2；仓库尚无先例，与 RESEARCH D-09 一致）。

**Section 路径命名** — 与现有 download 路由一致 (`jobs.py` lines 224-275):

```224:225:contract_info/backend/app/api/routes/jobs.py
@router.get("/{job_id}/download/fee-rates")
def download_fee_rates(job_id: uuid.UUID) -> FileResponse:
```

**分表 GET：** `get_job_preview` → `slice_preview(full, section)` → 专用 response model（含 `section` 字段）。  
**分表 PUT：** `apply_section_preview_edits(job_id, section, body.model_dump())` → `persist_export` → 再 `get_job_preview` + slice 返回。

**响应组装** (`jobs.py` lines 151-164):

```151:164:contract_info/backend/app/api/routes/jobs.py
def _preview_response_from_data(data: dict) -> JobPreviewResponse:
    return JobPreviewResponse(
        job_id=data["job_id"],
        source=data["source"],
        product_rows=[ProductPreviewItem.model_validate(r) for r in data["product_rows"]],
        fee_columns=data["fee_columns"],
        ...
    )
```

分表路由可抽 `_section_response_from_data(data, section)`，仅填充该 section 的 keys。

---

### `backend/app/api/routes/jobs.py` — `GET /verification/{table_key}` (route, transform)

**Analog:** `get_validation` (`jobs.py` lines 322-354)

**PREVIEW_STATUSES 守门** (`jobs.py` lines 324-329):

```324:329:contract_info/backend/app/api/routes/jobs.py
    if record.status not in PREVIEW_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Job not extracted yet",
        )
```

**field_label 叠加** (`jobs.py` lines 333-346):

```333:346:contract_info/backend/app/api/routes/jobs.py
    from backend.app.validate.field_labels import label_for_validation_field
    ...
        if not payload.get("field_label"):
            payload["field_label"] = label_for_validation_field(
                str(payload.get("field") or ""),
                getattr(record, "extraction_result", None),
            )
        items.append(ValidationItemResponse.model_validate(payload))
```

**Verification 路由：** `_get_record` → `PREVIEW_STATUSES` 检查 → `build_verification_rows(record, table_key)` → `TableVerificationResponse`；404 仅 job 不存在；无 validation 时仍 200（行来自 extraction）。

---

### `backend/app/services/preview_edit_service.py` (service, CRUD merge)

**Analog:** 同文件 `_apply_product_edits` / `_apply_list_table_edits` + `apply_preview_edits`

**列表表 merge（勿用 `or []`）** (`preview_edit_service.py` lines 36-61):

```36:61:contract_info/backend/app/services/preview_edit_service.py
def _apply_list_table_edits(
    extraction: dict[str, Any],
    *,
    list_key: str,
    preview_rows: list[dict[str, Any]],
    label_to_key: Callable[[str], str],
) -> None:
    existing = extraction.get(list_key) or []
    ...
    extraction[list_key] = updated
```

**全量入口（待修 Optional）** (`preview_edit_service.py` lines 82-112):

```82:112:contract_info/backend/app/services/preview_edit_service.py
        extraction = deepcopy(record.extraction_result)
        _apply_product_edits(extraction, payload.get("product_rows") or [])
        _apply_list_table_edits(
            extraction,
            list_key="fee_rates",
            preview_rows=payload.get("fee_rows") or [],
            label_to_key=extraction_key_for_fee_header,
        )
        ...
        record.extraction_result = extraction
        session.commit()

        persist_export(file_id)
```

**修复模式：** `if payload.get("product_rows") is not None:` 再调用 `_apply_product_edits`；各 list 表同理。

**分表 `apply_section_preview_edits`：** 复制 `apply_preview_edits` 的 session/状态/deepcopy/commit/`persist_export`/`build_job_preview` 外壳，内部按 `section` 仅调用一个 `_apply_*`（映射见 CONTEXT D-07）。

**事务模式** (`preview_edit_service.py` lines 72-79):

```72:79:contract_info/backend/app/services/preview_edit_service.py
    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise LookupError(f"contract_file not found: {file_id}")
        if record.status not in PREVIEW_STATUSES:
            raise ValueError(f"Cannot edit preview for status: {record.status}")
```

---

### `backend/app/services/preview_service.py` — `slice_preview` (utility, transform)

**Analog:** `build_job_preview` 返回结构 (`preview_service.py` lines 502-514)

```502:514:contract_info/backend/app/services/preview_service.py
    return {
        "job_id": record.id,
        "source": source,
        "product_rows": product_rows,
        "fee_columns": fee_columns,
        "fee_rows": fee_rows,
        "lock_columns": lock_columns,
        "lock_rows": lock_rows,
        "share_columns": share_columns,
        "share_rows": share_rows,
        "subscription_columns": subscription_columns,
        "subscription_rows": subscription_rows,
    }
```

**`get_job_preview` session 模式** (`preview_service.py` lines 520-542):

```520:542:contract_info/backend/app/services/preview_service.py
def get_job_preview(file_id: uuid.UUID) -> dict[str, Any]:
    from backend.app.db.session import SessionLocal
    from backend.app.models.contract_file import ContractFile

    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise LookupError(f"contract_file not found: {file_id}")
        return build_job_preview(record)
    finally:
        session.close()
```

`slice_preview(full, section)` 从上述 dict 按 section 取子集（`product-elements` → 仅 `product_rows`；`fee-rates` → `fee_columns` + `fee_rows`；等）。

---

### `backend/app/services/verification_service.py` (service, transform)

**Analog:** `preview_service._product_from_extraction` / `_fee_from_extraction` + `validate/evidence.resolve_evidence_text`

**产品要素行** (`preview_service.py` lines 167-189):

```167:189:contract_info/backend/app/services/preview_service.py
def _product_from_extraction(extraction: dict[str, Any]) -> list[dict[str, str | None]]:
    elements = extraction.get("product_elements") or {}
    rows: list[dict[str, str | None]] = []
    for field, raw in elements.items():
        if isinstance(raw, dict):
            val = raw.get("value")
        else:
            val = raw
        text = _cell_str(val)
        if text:
            rows.append({"field": field, "value": text})
    return rows
```

**摘录解析** (`evidence.py` lines 44-57):

```44:57:contract_info/backend/app/validate/evidence.py
def resolve_evidence_text(
    snippet: str | None,
    block_id: str | None,
    parse_json: dict,
) -> str | None:
    snip = (snippet or "").strip()
    if len(snip) >= MIN_SNIPPET_LEN:
        return snip
    from_block = _block_text(block_id, parse_json)
    ...
```

**field_label** (`field_labels.py` lines 57-85):

```57:85:contract_info/backend/app/validate/field_labels.py
def label_for_validation_field(
    field: str,
    extraction_result: dict | None = None,
) -> str:
    ...
    if text.startswith("fee_rates["):
        m = re.match(r"^fee_rates\[(\d+)\]\.(.+)$", text)
        if m:
            return f"费率表·第{int(m.group(1)) + 1}行·{m.group(2)}"
```

**页码占位（D-16–D-17）：** `_page_for_block` 恒 `None`；`page_no_note="页码暂未解析"`；`page_no_available = any(r.page_no is not None for r in rows)`。

**Validation overlay：** 读 `record.validation_result["items"]`，按 `field` 路径 dict 附加 `validation_status` / `validation_reason`（映射 `status` / `reason`），不替代 extraction 行。

---

### `backend/app/api/schemas.py` (config, request-response)

**Analog:** `JobPreviewUpdateRequest` + `ValidationItemResponse`

**当前全量 PUT schema（待改 Optional）** (`schemas.py` lines 63-72):

```63:72:contract_info/backend/app/api/schemas.py
class JobPreviewUpdateRequest(BaseModel):
    product_rows: list[ProductPreviewItem] = Field(default_factory=list)
    fee_columns: list[str] = Field(default_factory=list)
    fee_rows: list[dict[str, str | None]] = Field(default_factory=list)
    lock_columns: list[str] = Field(default_factory=list)
    lock_rows: list[dict[str, str | None]] = Field(default_factory=list)
    share_columns: list[str] = Field(default_factory=list)
    share_rows: list[dict[str, str | None]] = Field(default_factory=list)
    subscription_columns: list[str] = Field(default_factory=list)
    subscription_rows: list[dict[str, str | None]] = Field(default_factory=list)
```

**修复：** 各字段 `| None = None`（列表字段不用 `default_factory=list`）。

**Validation 行字段先例** (`schemas.py` lines 99-106):

```99:106:contract_info/backend/app/api/schemas.py
class ValidationItemResponse(BaseModel):
    field: str
    field_label: str | None = None
    status: str
    value: str | None = None
    evidence_text: str | None = None
    reason: str
    suggestion: str | None = None
```

**新增：** `PreviewSection = Literal[...]`；`ProductSectionUpdate` / `FeeSectionUpdate` / …；`JobPreviewSectionResponse`；`VerificationRow` / `TableVerificationResponse`（见 RESEARCH API Schemas）。

---

### `backend/app/services/validation_service.py` — Semaphore (service, request-response)

**Analog:** `persist_validation` 现有结构 (`validation_service.py` lines 74-114)

```74:114:contract_info/backend/app/services/validation_service.py
def persist_validation(
    file_id: uuid.UUID,
    session: Session | None = None,
) -> dict | None:
    own_session = session is None
    if own_session:
        session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        ...
        try:
            result = run_llm_validation_sync(
                record.extraction_result,
                record.path_b_json,
                record.parse_json or {},
            )
```

**调用链** (`extract_service.py` lines 38-44):

```38:44:contract_info/backend/app/services/extract_service.py
            result_dict, warnings, path_b = _run_extract_on_document(record.parse_json)
            record.extraction_result = result_dict
            record.path_b_json = path_b
            record.extraction_warnings = warnings
            persist_validation(file_id, session=session)
            record.status = "extracted"
```

**Semaphore 插入点：** 模块级 `_llm_validation_semaphore = threading.Semaphore(2)`；在 `run_llm_validation_sync(...)` 外包 `with _llm_validation_semaphore:`。`result.skipped` 快速路径仍在 semaphore 内（D-21）。

---

### `backend/app/main.py` — lifespan shutdown (config, event-driven)

**Analog:** 无现有 lifespan；按 RESEARCH 在 `FastAPI(..., lifespan=lifespan)` 注册。

**现有 app 组装** (`main.py` lines 9-31):

```9:31:contract_info/backend/app/main.py
app = FastAPI(
    title="CTRX Contract Extraction API",
    description="上传 docx → 解析 → 抽取 → 导出 Excel",
    version="0.1.0",
)
...
v1.include_router(jobs.router)
app.include_router(v1)
```

**模式：** `@asynccontextmanager` → `yield` → `shutdown_runner(wait=False)`；pytest 用 `shutdown_runner(wait=True)`。

---

### Tests

#### `backend/tests/test_preview_edit.py` (extend)

**Analog:** `test_apply_preview_edits_updates_product_and_reexports` (`test_preview_edit.py` lines 8-56)

```45:56:contract_info/backend/tests/test_preview_edit.py
    with (
        patch("backend.app.db.session.SessionLocal", return_value=FakeSession()),
        patch("backend.app.services.preview_edit_service.persist_export") as mock_export,
        patch(
            "backend.app.services.preview_service.build_job_preview",
            return_value={"job_id": job_id, "source": "xlsx", "product_rows": payload["product_rows"]},
        ),
    ):
        apply_preview_edits(job_id, payload)
```

新增：`test_section_put_fee_does_not_clear_lock`；`test_full_put_omitted_fields_unchanged`（仅传 `product_rows`，断言 `fee_rates` 长度不变）。

#### `backend/tests/test_parallel_run.py` (new)

**Analog:** `test_api_pipeline.py` + `test_db_wal.py`

```16:27:contract_info/backend/tests/test_api_pipeline.py
def test_run_returns_202(api_client, api_headers):
    ...
    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        with patch("backend.app.api.routes.jobs.run_pipeline"):
            response = api_client.post(
                f"/api/v1/jobs/{job_id}/run",
```

**更新 patch 目标：** `job_runner.submit` 或 `get_runner().submit`，不再 patch `run_pipeline` 于路由层。

**全局 409：** patch `count_in_progress` 返回 3，断言 409 与 detail 含「3」。

#### `backend/tests/test_preview_section_api.py` / `test_api_verification.py` (new)

**Analog:** `test_api_validation.py` (`test_validation_requires_extracted` / `test_validation_success`)

```7:20:contract_info/backend/tests/test_api_validation.py
def test_validation_requires_extracted(api_client, api_headers):
    ...
    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/validation",
            headers=api_headers,
        )
    assert response.status_code == 409
```

分表 API：patch `_get_record` + `get_job_preview` / `apply_section_preview_edits`；比对 GET section 与 GET full 的 `fee_rows` deep equal。

#### `backend/tests/test_verification_service.py` (new)

**Analog:** `test_validation_persist.py` mock 模式 + extraction fixture

```45:49:contract_info/backend/tests/test_validation_persist.py
    with patch(
        "backend.app.services.validation_service.run_llm_validation_sync",
        return_value=mock_result,
    ):
```

对 `build_verification_rows(SimpleNamespace(...))` 断言 `page_no is None`、`page_no_available is False`、`field_label` 中文。

#### `backend/tests/conftest.py` (optional)

**Analog:** `api_client` fixture (`conftest.py` lines 58-64) — 可加 module/autouse fixture 在 teardown 调用 `shutdown_runner(wait=True)`。

---

## Shared Patterns

### API 路由与鉴权
**Source:** `backend/app/api/routes/jobs.py` line 45  
**Apply to:** 所有新路由（分表 preview、verification）— 挂在现有 `router`，自动继承 `Depends(verify_api_key)`。

```45:45:contract_info/backend/app/api/routes/jobs.py
router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(verify_api_key)])
```

### 异常 → HTTP 状态
**Source:** `jobs.py` preview/run/delete  
**Apply to:** 所有新路由 handler

| 服务层异常 | HTTP |
|-----------|------|
| `LookupError` | 404 |
| `ValueError`（状态/空 extraction） | 409 |
| `PipelineBusyError` / `JobDeleteBusyError` | 409 |

### 短事务 SessionLocal
**Source:** `preview_edit_service.apply_preview_edits`, `parse_service.parse_file_id`, `export_service.persist_export`  
**Apply to:** `preview_edit_service` 分表路径、`count_in_progress`（可选传入 session）、**不**用于 JobRunner worker（worker 只用 `run_pipeline` 内建 session）。

### PREVIEW_STATUSES 守门
**Source:** `preview_service.py` line 75  
**Apply to:** preview 编辑、verification GET

```75:75:contract_info/backend/app/services/preview_service.py
PREVIEW_STATUSES = frozenset({"extracted", "exporting", "exported", "export_failed"})
```

### 保存后全量 export
**Source:** `preview_edit_service.py` line 112  
**Apply to:** 全量 PUT 与分表 PUT（D-11）

```112:112:contract_info/backend/app/services/preview_edit_service.py
        persist_export(file_id)
```

### IN_PROGRESS 语义
**Source:** `pipeline_service.IN_PROGRESS`  
**Apply to:** `count_in_progress`, `assert_can_run`, `delete_service` — 单一常量源，禁止重复定义。

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `backend/app/main.py` (lifespan) | config | event-driven | v1.2 `main.py` 无 lifespan；按 FastAPI `@asynccontextmanager` + RESEARCH 实现 |
| `HTTPException(detail=dict)` 含 `active_count` | route | request-response | 仓库现有 409 均为 `detail=str`；RESEARCH A1 推荐结构化 dict |

Planner：lifespan 参考 [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) 与 `15-RESEARCH.md` D-04–D-06 代码片段。

---

## Metadata

**Analog search scope:** `contract_info/backend/app/services/`, `api/routes/`, `api/schemas.py`, `validate/`, `tests/`  
**Files scanned:** ~25  
**Pattern extraction date:** 2026-05-29
