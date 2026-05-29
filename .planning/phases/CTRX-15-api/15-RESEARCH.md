# Phase 15: 后端并行与分表 API - Research

**Researched:** 2026-05-29  
**Domain:** FastAPI job pipeline · SQLite · sectional preview/verification APIs  
**Confidence:** HIGH（栈与锁定决策来自 CONTEXT + 代码检视）；页码端到端 MEDIUM（解析层无 `page` 字段）

## Summary

Phase 15 在 v1.2 后端上增加四类能力：**全局 3 槽 pipeline 守门**、**有界 `ThreadPoolExecutor` 真并行**、**五表分片 preview GET/PUT（并修复全量 PUT 清空陷阱）**、**按表 verification 行 JSON**。用户决策 D-01–D-23 已与仓库现状对齐：`IN_PROGRESS` 已存在于 `pipeline_service`；`run_job` 仍用 `BackgroundTasks.add_task`（假并行）；`apply_preview_edits` 仍用 `payload.get("fee_rows") or []`（会清空未提交表）。

**Primary recommendation:** 新增 `job_runner_service.py` 单例池 + `pipeline_service.count_in_progress()`；路由层 `POST /run` 先全局 409 再 `runner.submit`；`preview_edit_service` 按 section 拆分 merge；新建 `verification_service.build_verification_rows`；`validation_service` 包一层 `threading.Semaphore(2)`；解析层本阶段**不**改 docx parser，页码 API 稳定返回 `null` + `page_no_available: false`。

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01–D-03:** 仅 `parsing|extracting|exporting` 占槽；`pending` 不占；全局 ≥3 → 409（中文 detail + 可选 `active_count`）；单 job `IN_PROGRESS` 仍 `PipelineBusyError`（409，文案区分）。
- **D-04–D-06:** 模块级 `JobRunner`（`ThreadPoolExecutor(3)`）；`run_pipeline` 同步，worker 内新建 `SessionLocal()`；shutdown `wait=False`（pytest fixture 可 `wait=True`）。
- **D-07–D-11:** `GET/PUT /jobs/{id}/preview/{section}` 五枚举；分表 PUT 仅 merge 子树；保留全量 preview 并修复 Optional 全量 PUT；分表 PUT 后仍 `persist_export` 全五表。
- **D-12–D-18:** `GET /jobs/{id}/verification/{table_key}`；主数据 `extraction_result`；validation 叠加可选字段；`page_no` 轻量估算或 null；不含 path-b。
- **D-19–D-21:** `threading.Semaphore(2)` 限制并发 LLM validation；不跳过 validation；无 API key 时 skipped 不受影响。
- **D-22–D-23:** 契约测试清单（分表不清空、3 路 smoke、第 4 路 409、分表 GET 与全量片段一致）。

### Claude's Discretion

用户授权按 v1.3 调研（SUMMARY / ARCHITECTURE / PITFALLS）默认执行；D-11/D-19 已按调研锁定。

### Deferred Ideas (OUT OF SCOPE)

- `POST /upload/batch`、单表 `persist_export`、PATHB 并入 verification、Pinia 全量缓存替代分表 API。

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UP-04 | 后端 pipeline 并发 ≤3，第 4 路 `POST /run` → 409 | `count_in_progress()` + `JobRunner(max_workers=3)`；路由在 `assert_can_run` 之后、submit 之前查全局槽 |
| API-01 | 分表 `GET/PUT /preview/{section}`，PUT 不清空其它表 | `PreviewSection` 枚举 + `apply_section_preview_edits` + `slice_preview`；全量 PUT 改 Optional |
| API-02 | `GET /verification/{table_key}` 四列 + 页码可空 | `verification_service` + schema `TableVerificationResponse`；页码现阶段恒 unavailable |
| API-03 | 有界 worker + 每任务独立 DB session | `ThreadPoolExecutor`；`run_pipeline` 已在入口/各 persist 内自建 session（保持） |

</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 全局并发槽位计数 | API / Backend | Database | `COUNT` 查询 `ContractFile.status`；路由返回 409 |
| Pipeline 执行调度 | API / Backend | — | `JobRunner` 提交 `run_pipeline`，非 BackgroundTasks |
| 分表 preview 读写 | API / Backend | — | Pydantic 校验 + `preview_edit_service` merge |
| 全量 preview 兼容修复 | API / Backend | — | 同服务层，Optional 字段语义 |
| Verification 行构建 | API / Backend | — | 读 `extraction_result` + 可选 overlay `validation_result` |
| LLM 校验削峰 | API / Backend | — | `validation_service` 进程内 Semaphore |
| 页码解析 | — (deferred) | Parse | 当前 `parse_json.blocks` 无 `page`；Phase 15 仅 API 契约 |

---

## Current Codebase Anchors

| Area | Location | Notes |
|------|----------|-------|
| `IN_PROGRESS` / `run_pipeline` | `backend/app/services/pipeline_service.py:7-72` | `IN_PROGRESS = frozenset({"parsing","extracting","exporting"})`；`run_pipeline` 先开 session 读 status 后关，再调 `parse_file_id` / `persist_extract` / `persist_export`（各自独立 session） |
| `POST /run` | `backend/app/api/routes/jobs.py:192-208` | `background_tasks.add_task(run_pipeline, job_id)` — **待替换** |
| 全量 PUT 清空风险 | `backend/app/services/preview_edit_service.py:83-107` | `payload.get("fee_rows") or []` 等 |
| 全量请求 schema | `backend/app/api/schemas.py:63-72` | 所有列表字段 `default_factory=list` — **待改 Optional** |
| Preview 构建 | `backend/app/services/preview_service.py:346-514` | `build_job_preview` 五表；`SNIPPET_DISPLAY = "摘录原文"` |
| Validation 证据 | `backend/app/validate/evidence.py:20-175` | `block_id` + `snippet` → `resolve_evidence_text`；**无页码** |
| Parse 块结构 | `backend/app/parse/schemas.py:10-16` | `Block`: `id`, `type`, `section_id`, `text`/`rows` — **无 `page`** |
| docx 解析 | `backend/app/parse/docx_parser.py:27-90` | 不扫描 `w:br` 分页符 |
| LLM 校验入口 | `backend/app/services/extract_service.py:43` | `persist_validation` 在 extract 事务内同步调用 |
| `persist_validation` | `backend/app/services/validation_service.py:74-114` | `run_llm_validation_sync` 无全局限流 |
| 字段中文标签 | `backend/app/validate/field_labels.py:57-80` | `label_for_validation_field` 可复用于 verification |
| 测试基线 | `backend/tests/test_preview_edit.py` | 仅全量 product 编辑 |
| Pipeline API 测试 | `backend/tests/test_api_pipeline.py` | mock `run_pipeline`；无全局 409 |
| App 生命周期 | `backend/app/main.py:9-31` | **无** lifespan — JobRunner shutdown 需新增 |

---

## Recommended Implementation Approach (D-01 … D-23)

### D-01 – D-03：全局槽位与 409

**新增** `pipeline_service.count_in_progress(session=None) -> int`：

```python
# Pattern: [VERIFIED: codebase] pipeline_service.IN_PROGRESS
from sqlalchemy import func, select
stmt = select(func.count()).select_from(ContractFile).where(
    ContractFile.status.in_(IN_PROGRESS)
)
```

在 `run_job`（`jobs.py`）中顺序：

1. `_get_record` + `assert_can_run`（单 job `PipelineBusyError` → 409，detail 来自 exception）。
2. `if count_in_progress() >= 3:` → `HTTPException(409, detail="已有 3 个任务正在处理，请稍后再试", headers 或 body 内 `active_count: 3`)。
3. `job_runner.submit(job_id)`。

**Race 注意（MEDIUM）：** 检查与 submit 之间可能有第 4 个线程入队；缓解：submit 前再查一次，或 accept 极罕见越界（executor `max_workers=3` 硬上限）。Planner 可加「双检」任务。

`pending` 不计入 — 与 D-01 一致，无需改 `can_run`。

### D-04 – D-06：JobRunner

**新文件** `backend/app/services/job_runner_service.py`：

| 成员 | 行为 |
|------|------|
| `_executor` | `ThreadPoolExecutor(max_workers=3, thread_name_prefix="ctrx-pipeline")` |
| `submit(file_id: UUID)` | `executor.submit(_run_in_worker, file_id)` |
| `_run_in_worker` | try/except 记录日志；内部只调 `run_pipeline(file_id)` |
| `shutdown(wait: bool = False)` | 模块级函数，供 lifespan / pytest 调用 |

**不要**在 worker 内复用请求线程的 session — `run_pipeline` 与子服务已各自 `SessionLocal()` [VERIFIED: `parse_service.py:13-46`, `extract_service.py:27-57`]。

**FastAPI lifespan**（`main.py`）：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from backend.app.services.job_runner_service import shutdown_runner
    shutdown_runner(wait=False)
```

**pytest**（`conftest.py` 或 `test_parallel_run.py`）：`autouse` fixture `yield` 后 `shutdown_runner(wait=True)` 避免 worker 泄漏。

移除 `run_job` 的 `BackgroundTasks` 参数。

### D-07 – D-10：分表 preview

**枚举** `PreviewSection`（`schemas.py` 或 `preview_service.py`）：

```python
PreviewSection = Literal[
    "product-elements",
    "fee-rates",
    "lock-periods",
    "share-classes",
    "subscription-fee-rates",
]
```

**映射表** [VERIFIED: 15-CONTEXT.md D-07, ARCHITECTURE.md]：

| section | GET 响应字段 | PUT body model | extraction 键 |
|---------|-------------|----------------|-----------------|
| `product-elements` | `product_rows` | `ProductSectionUpdate` | `product_elements` |
| `fee-rates` | `fee_columns`, `fee_rows` | `FeeSectionUpdate` | `fee_rates` |
| `lock-periods` | `lock_columns`, `lock_rows` | `LockSectionUpdate` | `lock_periods` |
| `share-classes` | `share_columns`, `share_rows` | `ShareSectionUpdate` | `share_classes` |
| `subscription-fee-rates` | `subscription_columns`, `subscription_rows` | `SubscriptionSectionUpdate` | `subscription_fees` |

**`preview_service.slice_preview(full: dict, section: PreviewSection) -> dict`** — 从 `build_job_preview` 返回值切片。

**`preview_edit_service.apply_section_preview_edits(file_id, section, payload)`** — 仅调用既有 `_apply_product_edits` / `_apply_list_table_edits` 之一；**不** touch 其它 list keys。

**全量 PUT 修复** — `JobPreviewUpdateRequest` 所有字段改为 `| None = None`；`apply_preview_edits` 改为：

```python
if payload.get("product_rows") is not None:
    _apply_product_edits(extraction, payload["product_rows"])
# 同理 fee_rows — 仅当 is not None
```

`body.model_dump(exclude_unset=True)` 在路由层传入服务层（Pydantic v2 默认行为）。

OpenAPI：`PUT /preview` description 注明「新客户端请用分表 PUT」。

### D-11：分表保存后 export

分表与全量路径末尾保持 `persist_export(file_id)` [VERIFIED: `preview_edit_service.py:112`]。

### D-12 – D-18：Verification

**新文件** `backend/app/services/verification_service.py`：

- `build_verification_rows(record, table_key) -> list[VerificationRow]`
- `table_key` 同 `PreviewSection` 五值（path-b 排除）

**行构建规则：**

| table_key | 行来源 | field / field_label | value | excerpt |
|-----------|--------|---------------------|-------|---------|
| `product-elements` | `product_elements` 每项 dict | `field`=中文键；`field_label` 同键或 FIELD_SPEC | `value` | `snippet` 或 `resolve_evidence_text(snippet, block_id, parse_json)` |
| 四 list 表 | `fee_rates` 等每行每列 | 列名为中文 header（与 preview 一致，费率表用 `template_header_for_fee_key`） | 单元格值 | 行级 `snippet` / `摘录原文` |

**Validation overlay（D-14）：** 建 `dict[field_path, ValidationItem]` 自 `validation_result.items`；匹配键与 `label_for_validation_field` / 现有 validation `field` 路径（如 `fee_rates[0].运营费类型`）一致时附加 `validation_status`, `validation_reason`。

**页码（D-16–D-17）：** 见下文「Page number strategy」；默认 `page_no=None`, `page_no_note="页码暂未解析"`, `page_no_available=False`。

**路由** `GET /jobs/{job_id}/verification/{table_key}` → `TableVerificationResponse`。

### D-19 – D-21：LLM Semaphore

在 `validation_service.py` 模块级：

```python
_llm_validation_semaphore = threading.Semaphore(2)

def persist_validation(...):
    ...
    with _llm_validation_semaphore:
        result = run_llm_validation_sync(...)
```

`ValidationResult.skipped` 为 True 时仍在 semaphore 内但几乎无 IO — 可接受。若 API key 缺失导致快速 skipped，行为与 v1.2 一致 [VERIFIED: `validation_service.py:42-48`]。

### D-22 – D-23：测试

见「Test plan」节。

---

## API Schemas

### Section / table_key enum

URL 路径段：`product-elements` | `fee-rates` | `lock-periods` | `share-classes` | `subscription-fee-rates`  
非法值 → FastAPI 422。

###分表 GET 响应（示例：`fee-rates`）

```json
{
  "job_id": "uuid",
  "section": "fee-rates",
  "source": "extraction",
  "fee_columns": ["基金名称", "运营费类型", "费率（%/年）", "摘录原文"],
  "fee_rows": [{ "基金名称": "X", "运营费类型": "管理费", "摘录原文": "..." }]
}
```

`product-elements` 仅 `product_rows: [{ "field", "value" }]`。

### 分表 PUT 请求

仅含该 section 字段（专用 model，无其它表键）。

### 全量 PUT（修复后）

```json
{
  "product_rows": [{ "field": "基金全称", "value": "新" }]
}
```

未出现的键 → 不修改对应 extraction 子树。

### 全局 409（第 4 路 run）

```json
{
  "detail": "已有 3 个任务正在处理，请稍后再试",
  "active_count": 3
}
```

实现可用 `HTTPException` + 自定义 `detail` dict（FastAPI 支持）。

### `TableVerificationResponse`

```python
class VerificationRow(BaseModel):
    field: str
    field_label: str
    value: str | None = None
    page_no: int | None = None
    page_no_note: str | None = None  # e.g. "页码暂未解析"
    excerpt: str | None = None
    validation_status: str | None = None
    validation_reason: str | None = None

class TableVerificationResponse(BaseModel):
    job_id: uuid.UUID
    table_key: PreviewSection  # 同 section 枚举
    rows: list[VerificationRow]
    page_no_available: bool = False
```

---

## JobRunner Design

```
POST /run
  → assert_can_run (per-job)
  → count_in_progress() >= 3 ? 409 global
  → JobRunner.submit(job_id)
       ThreadPoolExecutor worker
         → run_pipeline(job_id)
              → parse_file_id (status parsing→parsed)
              → persist_extract (extracting→extracted, + validation)
              → persist_export (exporting→exported)
```

|  Concern | Design choice |
|---------|----------------|
| Singleton | 模块级 `_runner = JobRunner()`；`get_runner().submit()` |
| 与池大小关系 | `max_workers=3` 对齐业务槽；全局 COUNT 防止第 4 个 **入队** |
| 错误传播 | worker 内 exception 应由 `parse_service`/`extract_service` 写 `failed`/`extraction_failed`；runner 可 `logger.exception` |
| 测试 | mock `run_pipeline` sleep；或 mock `persist_extract` 加速（D-23） |
| Electron 单进程 | 不引入 Celery [VERIFIED: SUMMARY.md, STACK.md] |

---

## Verification Row Builder

**主路径：** `extraction_result` → 展平为 UI 行（与 TBL-03 四列对齐）。

**复用：**

- `preview_service._product_from_extraction` / `_fee_from_extraction` / `_table_from_extraction_list` 逻辑可抽共用，或 verification 直接遍历 extraction 原始 dict（避免 xlsx 源覆盖摘录）。
- `validate.evidence.resolve_evidence_text` 填 `excerpt` [VERIFIED: `evidence.py:44-57`]。
- `label_for_validation_field(field, extraction_result)` 填 `field_label` [VERIFIED: `field_labels.py:57+`]。

**产品要素表：** 每个 `product_elements` 键一行；`field` 建议用中文名（与 preview `product_rows[].field` 一致）。

**列表表：** 每个非 `snippet` 列一行；`field` 建议 `fee_rates[{i}].{col}` 或仅 `{col}` + 行索引在内部——与 validation items 对齐时用 bracket 路径（与 `evidence._collect_table_rows` 一致）[VERIFIED: `evidence.py:168`]。

**Validation overlay：** 仅附加字段，不替代 extraction 行（D-14）；无 validation 时仍返回 extraction 行。

**Path B：** 不在此端点（D-18）；继续 `GET /path-b`。

---

## Page Number Strategy

| 来源 | 现状 | Phase 15 动作 |
|------|------|----------------|
| `parse_json.blocks[]` | 仅有 `id`, `section_id`, `text`/`rows` [VERIFIED: `parse/schemas.py:10-16`, `docx_parser.py:56-78`] | **不修改 parser**（D-17） |
| `outline_preview` | `anchor_id`, `title`, `level` — 无页码 | 不用于 page |
| `extraction` 行/字段 | 可有 `block_id`, `snippet` [VERIFIED: `extract/schemas.py:16-18`] | 可解析摘录文本，**不能**映射页码 |
| SUMMARY 建议 | python-docx `w:br` 估算 | **Deferred** post–Phase 15（D-17 允许全 null） |

**`build_verification_rows` 实现建议：**

1. 定义 `_page_for_block(block_id, parse_json) -> int | None`：当前恒 `None`。
2. 若未来 block 含 `page` 或 `page_index`，在此读取（D-16 预留）。
3. 响应 `page_no_available = any(row.page_no is not None for row in rows)`；现阶段为 `False`。

**置信度：** HIGH（无页码字段已代码确认）；轻量估算留 Phase 17+ spike。

---

## Test Plan

| 文件 | 用例 | 断言 |
|------|------|------|
| `test_preview_edit.py` | `test_section_put_fee_does_not_clear_lock` | mock session；仅 PUT fee_rows；`len(extraction["lock_periods"])` 不变 |
| `test_preview_edit.py` | `test_full_put_omitted_fields_unchanged` | `model_dump(exclude_unset=True)` 仅 product；fee_rates 行数不变 |
| `test_preview_section_api.py`（新建） | GET/PUT `/preview/fee-rates` | 200；body 无其它表键 |
| `test_preview_section_api.py` | GET section vs GET full | `fee_rows` 与全量 preview 片段 deep equal |
| `test_parallel_run.py`（新建） | 3× submit + 4th run | mock `count_in_progress` 返回 3 → 409 + detail 含「3」 |
| `test_parallel_run.py` | JobRunner invokes pipeline | mock `run_pipeline`；`submit` ×3 被调用 |
| `test_verification_service.py`（新建） | product + fee rows | `field_label` 中文；`excerpt` 来自 snippet；`page_no is None`；`page_no_available is False` |
| `test_api_verification.py`（新建） | GET verification | 404 job；409 未 extract；200 行数 >0 |
| `test_api_pipeline.py` | 更新 run 路径 | patch `job_runner.submit` 而非 `run_pipeline` 直接 |
| `test_validation_persist.py`（可选） | semaphore 串行 | mock `run_llm_validation_sync` sleep；并发 3 路调用 max 同时 2（脆弱，可仅集成 smoke） |

**运行命令** [VERIFIED: `pytest.ini`]：

```bash
cd contract_info
pytest backend/tests/test_preview_edit.py backend/tests/test_parallel_run.py -q
pytest backend/tests -q --ignore=backend/tests/golden -m "not llm"
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest（项目 `pytest.ini`，无 pin 版本于 repo根） |
| Config file | `contract_info/pytest.ini` |
| Quick run command | `pytest backend/tests/test_preview_edit.py backend/tests/test_parallel_run.py -q` |
| Full suite command | `pytest backend/tests -q --ignore=backend/tests/golden -m "not llm"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UP-04 | 第 4 路 run → 409 | unit/api | `pytest backend/tests/test_parallel_run.py -x` | ❌ Wave 0 |
| UP-04 | 3 worker 提交 | unit | 同上 | ❌ Wave 0 |
| API-01 | 分表 PUT 不清空它表 | unit | `pytest backend/tests/test_preview_edit.py -x` | ⚠️ 需扩展 |
| API-01 | 分表 GET ≡ 全量片段 | api | `pytest backend/tests/test_preview_section_api.py -x` | ❌ Wave 0 |
| API-02 | verification 四列 + page null | unit/api | `pytest backend/tests/test_verification_service.py -x` | ❌ Wave 0 |
| API-03 | ThreadPoolExecutor + 独立 session | unit | `test_parallel_run.py` + 现有 pipeline 测试 | ⚠️ 部分 |

### Sampling Rate

- **Per task commit:** `pytest backend/tests/test_preview_edit.py backend/tests/test_parallel_run.py -q`
- **Per wave merge:** `pytest backend/tests -q -m "not llm" --ignore=backend/tests/golden`
- **Phase gate:** 全量非 LLM 测试绿 + `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `backend/app/services/job_runner_service.py`
- [ ] `backend/tests/test_parallel_run.py`
- [ ] `backend/tests/test_preview_section_api.py`
- [ ] `backend/tests/test_verification_service.py`
- [ ] `backend/tests/test_api_verification.py`
- [ ] `main.py` lifespan shutdown hook
- [ ] Optional fields on `JobPreviewUpdateRequest`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | 现有 `verify_api_key` on `jobs.router` [VERIFIED: `jobs.py:45`] |
| V4 Access Control | yes | job_id UUID；404 不泄露它 job |
| V5 Input Validation | yes | Pydantic section enum + section-scoped PUT models |
| V6 Cryptography | no change | — |

### Known Threat Patterns

| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| 超大 PUT body | DoS | 沿用现有 preview 行数上限（`max_data_rows=100` 模式） |
| 并发耗尽 | DoS | 3 槽 + 409 |
| 路径遍历 export | Tampering | 现有 `_resolve_export_path` [VERIFIED: `jobs.py:96-107`] |

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| COUNT 与 submit 竞态，短暂 4 路 in-progress | MEDIUM | 双检 COUNT；executor max_workers=3 |
| SQLite `database is locked` 三写并发 | MEDIUM | 已有 WAL [VERIFIED: `test_db_wal.py`]；保持短事务；监控日志 |
| 全量 PUT 修复破坏 v1.2 客户端（总传全表） | LOW | 仍接受全表 body；行为不变；仅「部分字段」客户端受益 |
| verification 行爆炸（产品要素 77 字段） | MEDIUM | 与 preview 一致：有 value 或 excerpt 才出行；Hub 可分页（前端 Phase 17） |
| LLM semaphore 导致 extract 步骤阻塞变长 | LOW | 可接受（D-19）；仅 validation 段持锁 |
| 测试未覆盖 BackgroundTasks 移除回归 | MEDIUM | 更新 `test_api_pipeline.py` patch 点 |
| 页码 UI 期望与 API 不一致 | LOW | `page_no_available: false` 契约稳定；Phase 17 显示「—」 |

---

## Project Constraints (from .cursor/rules/)

- `contract_info/.cursor/rules/auto-commit-push.mdc`：完成可交付改动后默认 commit+push（规划文档可含 `.planning/`）；**本阶段研究文档由 orchestrator 决定是否提交**。
- 改动涉及 export/extract 时跑 pytest。
- 不提交 `.env`、密钥。

---

## Don't Hand-Roll

| Problem | Use Instead | Why |
|---------|-------------|-----|
| 分布式任务队列 | `ThreadPoolExecutor(3)` | 桌面单进程 ≤3 [VERIFIED: STACK.md] |
| 自定义 merge JSON | 复用 `_apply_*_edits` | 列映射已在 `column_map` |
| 全文检索 excerpts | `resolve_evidence_text` | block_id 已贯通 |
| asyncio 并行 pipeline | 同步 `run_pipeline` + 线程池 | GIL/现有服务全同步 |

---

## Common Pitfalls

### Pitfall 1: 全量 PUT `or []`（陷阱 #1）

**避免：** Optional + `is not None`；分表 API 为默认保存路径。

### Pitfall 2: BackgroundTasks 假并行（陷阱 #2）

**避免：** JobRunner；集成测 3 submit。

### Pitfall 5: LLM 风暴（陷阱 #5）

**避免：** Semaphore(2)；非 Semaphore(1)（CONTEXT D-19 明确为 2）。

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | FastAPI `HTTPException(detail=dict)` 前端能展示 `active_count` | 409 schema | 需改为结构化 body model |
| A2 | `model_dump(exclude_unset=True)` 足以修复全量 PUT | D-09 | v1.2 若传显式 `null` 需 `exclude_none` |
| A3 | verification 列表表每列一行（非每物理行一行） | API-02 | UI 列数与运营预期不符 → 对齐 FIELD_SPEC |

---

## Open Questions (RESOLVED)

1. **409 响应体格式** — **RESOLVED:** 使用结构化 `detail` dict：`{"detail": "已有 3 个任务正在处理，请稍后再试", "active_count": 3}`（见 15-01-PLAN Task 2）。
2. **verification 列表表 field 路径** — **RESOLVED:** 与 validation `field` 路径一致（如 `fee_rates[0].管理费率`），overlay 用相同键；列表表 `field_label` 用列头中文（见 15-03-PLAN Task 1）。

---

## Environment Availability

**Step 2.6:** SKIPPED — Phase 15 为代码/契约变更；依赖现有 Python 3.11+、pytest、FastAPI（与 v1.2 相同）。无新外部服务。

---

## Sources

### Primary (HIGH confidence)

- `contract_info/.planning/phases/CTRX-15-api/15-CONTEXT.md` — D-01–D-23
- `contract_info/backend/app/services/pipeline_service.py`, `preview_edit_service.py`, `jobs.py`
- `contract_info/backend/app/parse/schemas.py`, `docx_parser.py`
- `contract_info/backend/app/validate/evidence.py`, `extract/schemas.py`
- `contract_info/pytest.ini`

### Secondary (MEDIUM confidence)

- `contract_info/.planning/research/SUMMARY.md`, `ARCHITECTURE.md`, `PITFALLS.md`
- [FastAPI Discussion #13724](https://github.com/fastapi/fastapi/discussions/13724) — BackgroundTasks 顺序执行（STACK.md 引用）

---

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — stdlib ThreadPoolExecutor + 现有 FastAPI/SQLAlchemy
- Architecture: **HIGH** — 锚点文件已逐行确认
- Pitfalls: **HIGH** — `preview_edit_service` 与 PITFALLS.md 一致
- Page numbers: **MEDIUM** — 解析层无 page 已验证；估算留后续

**Research date:** 2026-05-29  
**Valid until:** ~2026-06-28（栈稳定）
