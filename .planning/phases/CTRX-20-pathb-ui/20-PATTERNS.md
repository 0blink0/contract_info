# Phase 20: 知识库数据层 + PathB 录入 UI - Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 10（6 后端 + 4 前端，含新建与修改）
**Analogs found:** 10 / 10

---

## File Classification

| 新建 / 修改文件 | Role | Data Flow | 最近类比文件 | 匹配质量 |
|----------------|------|-----------|------------|---------|
| `backend/app/services/kb_service.py` | service | CRUD + batch | `backend/app/services/job_runner_service.py` | role-match（同为模块单例服务） |
| `backend/app/api/routes/kb.py` | route | request-response | `backend/app/api/routes/jobs.py` | exact（同为 APIRouter + Pydantic schema + HTTPException 模式） |
| `backend/app/main.py`（修改） | config | request-response | 自身（现有 `lifespan()` 结构） | exact（在 `yield` 前插入 init 调用） |
| `backend/app/config.py`（修改） | config | — | 自身（现有 `data_dir()` 函数） | exact（`models_dir()` 遵循完全相同的模式） |
| `requirements.txt`（修改） | config | — | 自身（现有文件格式） | exact |
| `frontend/src/api/kb.ts` | api-client | request-response | `frontend/src/api/client.ts` | exact（`apiFetch` + 类型导出模式） |
| `frontend/src/composables/useKbEntry.ts` | composable | request-response | `frontend/src/composables/usePathB.ts` | exact（`ref`/`computed`/`async`/`ElMessage` 模式） |
| `frontend/src/components/pathb/PathBDetail.vue`（修改） | component | request-response | 自身 + `TablePreviewEditor.vue` | exact（`el-table` + `el-input` inline-edit 模式） |
| `backend/tests/test_kb_service.py` | test（unit） | — | `backend/tests/test_api_path_b.py` | role-match（`unittest.mock.patch` + `SimpleNamespace` 模式） |
| `backend/tests/test_api_kb.py` | test（integration） | — | `backend/tests/test_api_path_b.py` | exact（`api_client` + `api_headers` fixture + `patch` 模式） |

---

## Pattern Assignments

### `backend/app/services/kb_service.py`（service，CRUD + batch）

**类比：** `backend/app/services/job_runner_service.py`（模块级单例 + getter 函数模式）

**模块单例模式**（`job_runner_service.py` 第 13、28、32 行）：
```python
# 模块级私有单例变量
_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="ctrx-pipeline")
_runner = JobRunner()

def get_runner() -> JobRunner:
    return _runner
```
KB service 照此模式，用 `_kb: KbService | None = None` + `get_kb_service() -> KbService | None`。

**`asyncio.to_thread` 阻塞调用模式**（`job_runner_service.py` 第 21-25 行）：
```python
def _run_in_worker(file_id: uuid.UUID) -> None:
    try:
        run_pipeline(file_id)
    except Exception:
        logger.exception("pipeline failed for job %s", file_id)
```
KB service 在 `add_entries()` 内用 `await asyncio.to_thread(self._model.encode, texts, ...)` 将 CPU 密集型 encode 放入线程池，与此处 ThreadPoolExecutor submit 同理。

**软降级 + logger.warning 模式**（`job_runner_service.py` 第 24-25 行）：
```python
    except Exception:
        logger.exception("pipeline failed for job %s", file_id)
```
`init_kb_service()` 模型加载失败时用 `logger.warning("bge-m3 failed to load, KB unavailable: %s", e)`，不重新抛出，保持软降级（D-06）。

**imports 模式**（`job_runner_service.py` 第 1-9 行）：
```python
from __future__ import annotations
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from backend.app.services.pipeline_service import run_pipeline

logger = logging.getLogger(__name__)
```
`kb_service.py` 遵循相同结构：`from __future__ import annotations`、`logging.getLogger(__name__)`、`from backend.app.config import data_dir`。

**`data_dir()` 子路径模式**（`config.py` 第 36-37 行）：
```python
def uploads_dir() -> Path:
    return data_dir() / "uploads"
```
LanceDB 存储路径使用 `data_dir() / "kb"`，完全相同模式。

---

### `backend/app/api/routes/kb.py`（route，request-response）

**类比：** `backend/app/api/routes/jobs.py`（最完整的路由文件）

**router 声明 + auth 模式**（`jobs.py` 第 69 行）：
```python
router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(verify_api_key)])
```
`kb.py` 照此：
```python
router = APIRouter(prefix="/kb", tags=["kb"], dependencies=[Depends(verify_api_key)])
```
`verify_api_key` 定义在 `backend/app/api/deps.py` 第 6 行，是唯一的认证依赖，所有路由文件（jobs、upload）均在 router 级别 `dependencies=` 中统一注入。

**HTTPException 错误处理模式**（`jobs.py` 第 79-82、277-279 行）：
```python
if record is None:
    raise HTTPException(status_code=404, detail="Job not found")

except LookupError as exc:
    raise HTTPException(status_code=404, detail=str(exc)) from exc
except ValueError as exc:
    raise HTTPException(status_code=409, detail=str(exc)) from exc
```
`kb.py` 对 503（模型不可用）和 500（内部错误）使用相同的 `raise HTTPException(status_code=..., detail=...) from exc` 模式。

**Pydantic request/response schema 模式**（`jobs.py` 第 14-37 行）：
```python
from backend.app.api.schemas import (
    DeleteJobResponse,
    JobDetailResponse,
    JobListResponse,
    ...
)
```
`kb.py` 因体量较小，将 Pydantic model 直接定义在路由文件内（`KbEntryInput`、`KbEntriesRequest`、`KbEntriesResponse`、`KbEntryItem`、`KbListResponse`），而非单独 schemas 文件，与 `health.py`（简单路由不拆 schema）的判断原则一致。

**GET + Query 参数模式**（`jobs.py` 第 139-140 行）：
```python
@router.get("", response_model=JobListResponse)
def list_jobs(limit: int = Query(50, ge=1, le=200)) -> JobListResponse:
```
`GET /kb/entries` 使用 `field_name: str | None = Query(None)` 做可选过滤，模式相同。

**DELETE 路由模式**（`jobs.py` 第 272-280 行）：
```python
@router.delete("/{job_id}", response_model=DeleteJobResponse)
def delete_job(job_id: uuid.UUID) -> DeleteJobResponse:
    try:
        delete_job_record(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JobDeleteBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DeleteJobResponse(job_id=job_id)
```
`DELETE /kb/entries/{entry_id}` 返回 204（无 body），用 `status_code=204` + `-> None`。

**async route 模式**（`jobs.py`中所有路由均为 `async def` 或 `def`）：
- 无 I/O 阻塞的读取路由（`GET /kb/entries`、`DELETE`）使用同步 `def`
- `POST /kb/entries` 内部调用 `await svc.add_entries(...)` 须用 `async def`

---

### `backend/app/main.py`（修改：lifespan + router 注册）

**类比：** 自身现有文件（`backend/app/main.py`）

**lifespan 现有结构**（`main.py` 第 12-15 行）：
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    shutdown_runner(wait=False)
```
修改后在 `yield` 前插入一行（`asyncio.to_thread` 包裹同步初始化）：
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(init_kb_service)   # 新增：KB 初始化（含模型加载）
    yield
    shutdown_runner(wait=False)
```

**router 注册现有结构**（`main.py` 第 37-41 行）：
```python
from backend.app.api.routes import health, jobs, upload
v1 = APIRouter(prefix="/api/v1")
v1.include_router(health.router)
v1.include_router(upload.router)
v1.include_router(jobs.router)
app.include_router(v1)
```
新增一行：
```python
from backend.app.api.routes import health, jobs, kb, upload
...
v1.include_router(kb.router)   # 新增
```
最终前缀为 `/api/v1/kb`（v1 prefix + kb router prefix `/kb`）。

---

### `backend/app/config.py`（修改：新增 models_dir()）

**类比：** 自身现有 `data_dir()` 函数（`config.py` 第 22-33 行）

**`data_dir()` 完整模式**（`config.py` 第 22-33 行）：
```python
def data_dir() -> Path:
    """Resolve user-writable data directory (uploads, exports, DB file).

    Desktop mode: CTRX_DATA_DIR env var (set by Electron main before spawning Python).
    Dev/Docker mode: PROJECT_ROOT (unchanged behaviour).
    """
    raw = os.environ.get("CTRX_DATA_DIR", "").strip()
    if raw:
        p = Path(raw)
        p.mkdir(parents=True, exist_ok=True)
        return p
    return PROJECT_ROOT
```
`models_dir()` 遵循相同模式，但有两处差异：
1. 返回 `Path | None`（未设置时返回 None，而非 PROJECT_ROOT）
2. **不调用 `p.mkdir()`**（模型目录由用户预置，不由应用创建）

新增函数：
```python
def models_dir() -> Path | None:
    """Resolve local model directory (CTRX_MODELS_DIR).
    Returns None if not set.
    """
    raw = os.environ.get("CTRX_MODELS_DIR", "").strip()
    if raw:
        return Path(raw)
    return None
```

---

### `requirements.txt`（修改：新增两行）

**类比：** 自身现有文件（根目录 `requirements.txt`）

**现有格式**（`requirements.txt` 第 1-14 行）：
```
python-docx>=1.1.0
sqlalchemy>=2.0
fastapi>=0.110
uvicorn[standard]>=0.27
...
```
新增格式保持一致（`>=` 约束，无空格）：
```
lancedb>=0.33.0
sentence-transformers>=5.5.1
```
pyarrow 作为 lancedb 依赖自动安装，无需单独添加。

---

### `frontend/src/api/kb.ts`（新建，API client）

**类比：** `frontend/src/api/client.ts`（完整参考）

**`apiFetch` + 错误处理模式**（`client.ts` 第 31-50 行）：
```typescript
async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers)
  for (const [k, v] of Object.entries(apiHeaders())) {
    headers.set(k, v as string)
  }
  const response = await fetch(`${getApiBase()}${path}`, { ...options, headers })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      if (body.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch { /* ignore */ }
    throw new Error(detail || `HTTP ${response.status}`)
  }
  return response
}
```
`kb.ts` **不重新定义 `apiFetch`**，而是从 `@/api/client.ts` 中导出后在内部使用（参考 `getPathB` 等函数的做法），或通过 `import { apiFetch } from '@/api/client'`（若需要导出的话需在 `client.ts` 导出该函数）。

**GET 函数模式**（`client.ts` 第 97-100 行）：
```typescript
export async function getPathB(jobId: string): Promise<PathBResponse> {
  const res = await apiFetch(`/jobs/${jobId}/path-b`)
  return res.json()
}
```
`kb.ts` 的三个导出函数遵循相同形态：
```typescript
export async function postKbEntries(body: KbEntriesRequest): Promise<KbEntriesResponse>
export async function getKbEntries(fieldName?: string): Promise<KbListResponse>
export async function deleteKbEntry(entryId: string): Promise<void>
```

**POST + JSON body 模式**（`client.ts` 第 109-119 行）：
```typescript
export async function saveJobPreview(
  jobId: string,
  payload: JobPreviewUpdatePayload,
): Promise<JobPreview> {
  const res = await apiFetch(`/jobs/${jobId}/preview`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return res.json()
}
```
`postKbEntries` 使用 `method: 'POST'` + `headers: { 'Content-Type': 'application/json' }` + `body: JSON.stringify(body)`，完全相同。

**类型定义位置：** `kb.ts` 内直接声明接口（`KbEntryInput`、`KbEntriesRequest`、`KbEntriesResponse`、`KbEntryItem`、`KbListResponse`），不写入 `types.ts`，与 `client.ts` 对 `JobPreviewUpdatePayload` 的做法一致（在 `client.ts` 内定义）。

**503 错误检测方式**（`client.ts` 第 39-47 行）：
```typescript
if (!response.ok) {
  let detail = response.statusText
  try {
    const body = await response.json()
    if (body.detail) {
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    }
  } catch { /* ignore */ }
  throw new Error(detail || `HTTP ${response.status}`)
}
```
`apiFetch` 在 503 时抛出 `Error`，其 `message` 包含后端 `detail` 字符串。`useKbEntry.ts` 在 catch 中检测 503：`e.message.includes('503')` 或检测 message 内容（`'知识库功能不可用'`）。

---

### `frontend/src/composables/useKbEntry.ts`（新建，composable）

**类比：** `frontend/src/composables/usePathB.ts`（完整参考）

**composable 签名模式**（`usePathB.ts` 第 11 行）：
```typescript
export function usePathB(jobId: Ref<string | null>) {
```
`useKbEntry` 接收多个 Ref 参数：
```typescript
export function useKbEntry(
  jobId: Ref<string | null>,
  jobFilename: Ref<string | null>,
  crmRows: Ref<CrmHandoffItem[]>,
)
```

**ref 声明模式**（`usePathB.ts` 第 12-15 行）：
```typescript
const loaded = ref(false)
const loading = ref(false)
const data = ref<PathBResponse | null>(null)
const showJson = ref(false)
```
`useKbEntry` 声明：
```typescript
const kbRows = ref<KbRow[]>([])
const submitting = ref(false)
const kbUnavailable = ref(false)
```

**async load + try/catch/finally + ElMessage 模式**（`usePathB.ts` 第 58-69 行）：
```typescript
async function load(force = false) {
  if (!jobId.value || (loaded.value && !force)) return
  loading.value = true
  try {
    data.value = await getPathB(jobId.value)
    loaded.value = true
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '开放日与业绩报酬加载失败')
  } finally {
    loading.value = false
  }
}
```
`useKbEntry.submit()` 遵循完全相同的 `submitting.value = true` → `try` → `ElMessage.success/error` → `finally { submitting.value = false }` 结构。

**imports 模式**（`usePathB.ts` 第 1-4 行）：
```typescript
import { computed, ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getPathB } from '@/api/client'
import type { PathBResponse } from '@/api/types'
```
`useKbEntry.ts` 的 imports：
```typescript
import { ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { postKbEntries } from '@/api/kb'
import type { CrmHandoffItem } from '@/api/types'
```

**return 对象模式**（`usePathB.ts` 第 106-124 行）：
```typescript
return {
  data, loading, loaded, showJson, crmRows, ...
  load, refresh, copyJson, downloadJson, reset,
}
```
`useKbEntry` 返回：`{ kbRows, submitting, kbUnavailable, buildRows, submit }`。

---

### `frontend/src/components/pathb/PathBDetail.vue`（修改：底部追加 KB 录入区块）

**类比（模板结构）：** 自身现有文件 `PathBDetail.vue`
**类比（inline-edit 模式）：** `frontend/src/components/table/TablePreviewEditor.vue`

**`v-else-if="data"` 块内插入位置**（`PathBDetail.vue` 第 64 行）：
```vue
<template v-else-if="data">
  <!-- 现有内容：tierRows 表格、crmRows 表格、snippetRows 表格、rawSections、json-block -->
  ...
  <!-- 新增 KB 录入区块：追加在 </template> 关闭标签前 -->
</template>
```

**`.sub-title` + `.section-table` CSS 类模式**（`PathBDetail.vue` 第 127-128、158-160 行）：
```vue
<div class="sub-title">合同原文（业绩报酬 / 开放日章节）</div>
...
<style scoped>
.section-table { margin-bottom: 12px; }
.sub-title { font-size: 13px; font-weight: 600; margin-bottom: 6px; }
</style>
```
KB 录入区使用相同类名 `.section-table` 和 `.sub-title`，无需新增样式。

**`el-table` 基础属性模式**（`PathBDetail.vue` 第 74-81 行）：
```vue
<el-table
  :data="crmRows"
  size="small"
  stripe
  border
  class="section-table"
  empty-text="..."
>
```
KB 录入表格使用相同四个 prop：`size="small" stripe border class="section-table"`。

**`el-input` inline-edit 模式**（`TablePreviewEditor.vue` 第 70-79 行）：
```vue
<el-table-column label="值" min-width="240">
  <template #default="{ row }">
    <el-input
      v-if="canEdit"
      v-model="row.value"
      size="small"
      @input="onInput"
    />
    <span v-else>{{ row.value }}</span>
  </template>
</el-table-column>
```
KB 录入表格的「字段值」和「原文摘录」列均使用 `<template #default="{ row }">` + `<el-input v-model="row.field_value" size="small" :disabled="kbUnavailable" />`，与此完全一致（用 `:disabled` 替代 `v-if="canEdit"` 以实现 D-07 禁用状态）。

**`el-alert` 模式**（`PathBDetail.vue` 第 43-49 行）：
```vue
<el-alert
  type="info"
  :closable="false"
  show-icon
  title="..."
  description="..."
  class="top-alert"
/>
```
KB 不可用警告使用 `type="warning"` + `:closable="false"` + `title="知识库功能不可用（模型未加载）"`，无 `description`，遵循相同结构。

**`v-if="available"` 守卫模式**（决策 D-08）：
PathB 整体 `v-if` 已在 `PathBDetail.vue` 第 51 行：`<el-empty v-if="!available" ...>`，以及 `<template v-else>` 包裹所有内容。KB 录入区追加在 `<template v-else-if="data">` 内，天然继承 `available` 守卫，无需额外条件。

**`el-table-column type="selection"` 模式**（Element Plus 标准用法，项目中无现有示例）：
```vue
<el-table-column type="selection" width="46" />
```
配合 `@selection-change="(sel) => kbRows.value.forEach(r => r.selected = sel.includes(r))"`。注意：`sel.includes(r)` 基于对象引用比较，`kbRows.value` 的元素就是 `:data` 绑定的原始对象，因此引用比较正确。

---

### `backend/tests/test_kb_service.py`（新建，unit test）

**类比：** `backend/tests/test_api_path_b.py`（`patch` + `SimpleNamespace` 模式）

**`unittest.mock.patch` + SimpleNamespace 模式**（`test_api_path_b.py` 第 1-18 行）：
```python
import uuid
from types import SimpleNamespace
from unittest.mock import patch

def test_path_b_requires_extracted(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(id=job_id, status="parsed", path_b_json=None, filename="a.docx")
    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(f"/api/v1/jobs/{job_id}/path-b", headers=api_headers)
    assert response.status_code == 409
```
`test_kb_service.py` 使用 `unittest.mock.MagicMock` mock lancedb table（`mock_table = MagicMock()`）和 `patch` mock `SentenceTransformer`，无需真实数据库或模型。

**`tmp_path` fixture 模式**（pytest 内置）：
```python
def test_init_creates_table(tmp_path, monkeypatch):
    monkeypatch.setenv("CTRX_DATA_DIR", str(tmp_path))
    from backend.app.services.kb_service import init_kb_service, get_kb_service
    init_kb_service()
    svc = get_kb_service()
    assert svc is not None
```
`tmp_path` 提供临时目录，`monkeypatch.setenv` 设置 `CTRX_DATA_DIR`，不污染生产 LanceDB 文件。

**assert 风格**（`test_api_path_b.py` 第 46-48 行）：
```python
assert response.status_code == 200
body = response.json()
assert body["performance_fee"]["tiers"]
```
`test_kb_service.py` 使用相同的直接 `assert` 断言风格，不使用 `unittest.TestCase`。

---

### `backend/tests/test_api_kb.py`（新建，integration test）

**类比：** `backend/tests/test_api_path_b.py`（最精确的类比：TestClient + `api_client`/`api_headers` fixture + `patch` service 层）

**`api_client` + `api_headers` fixture 模式**（`conftest.py` 第 58-69 行）：
```python
@pytest.fixture
def api_client(api_settings):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    return TestClient(app)

@pytest.fixture
def api_headers():
    return {"X-API-Key": "test-key"}
```
`test_api_kb.py` 所有测试函数签名：`def test_xxx(api_client, api_headers):`，直接复用这两个 fixture，无需额外配置。

**patch service 层模式**（`test_api_path_b.py` 第 38-43 行）：
```python
with patch("backend.app.api.routes.jobs._get_record", return_value=record):
    response = api_client.get(
        f"/api/v1/jobs/{job_id}/path-b",
        headers=api_headers,
    )
```
`test_api_kb.py` patch `backend.app.services.kb_service._kb`（模块单例）或 patch `backend.app.api.routes.kb.get_kb_service` 返回 mock service 对象：
```python
mock_svc = MagicMock()
mock_svc.model_available = True
mock_svc.add_entries = AsyncMock(return_value=["uuid1"])
with patch("backend.app.api.routes.kb.get_kb_service", return_value=mock_svc):
    response = api_client.post("/api/v1/kb/entries", json=body, headers=api_headers)
assert response.status_code == 200
```

**`api_settings` 依赖**（`conftest.py` 第 48-55 行）：
```python
@pytest.fixture
def api_settings(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    from backend.app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```
`api_client` fixture 依赖 `api_settings`，测试时 API key 为 `"test-key"`，对应 `api_headers` 中的 `{"X-API-Key": "test-key"}`。无需在 `test_api_kb.py` 中重复设置。

---

## Shared Patterns（跨文件复用）

### 认证：verify_api_key
**来源：** `backend/app/api/deps.py` 第 6-11 行
**应用于：** `backend/app/api/routes/kb.py`（router 级别 `dependencies=[Depends(verify_api_key)]`）
```python
from backend.app.api.deps import verify_api_key
router = APIRouter(prefix="/kb", tags=["kb"], dependencies=[Depends(verify_api_key)])
```
所有现有 router（jobs、upload）均使用此模式，`kb.py` 必须同样注入。

### 错误处理：HTTPException + from exc
**来源：** `backend/app/api/routes/jobs.py` 第 277-280 行
**应用于：** `backend/app/api/routes/kb.py` 所有三个 endpoint
```python
except SomeError as exc:
    raise HTTPException(status_code=5xx, detail=str(exc)) from exc
```
`from exc` 保留原始 traceback，是项目统一写法。

### 软降级：logger.warning + 不重抛
**来源：** `backend/app/services/job_runner_service.py` 第 24-25 行（`logger.exception`）
**应用于：** `backend/app/services/kb_service.py` `init_kb_service()` 中的模型加载 except 块
```python
except Exception as e:
    logger.warning("bge-m3 failed to load, KB unavailable: %s", e)
    # 不 re-raise，_kb 仍被赋值（model 为 None）
```

### 前端 ElMessage 反馈
**来源：** `frontend/src/composables/usePathB.ts` 第 65 行
**应用于：** `frontend/src/composables/useKbEntry.ts` `submit()` 函数
```typescript
ElMessage.success(`已存入 ${n} 条`)
ElMessage.error(e instanceof Error ? e.message : '存入失败')
```

### 前端 apiFetch + JSON POST
**来源：** `frontend/src/api/client.ts` 第 31-50、109-119 行
**应用于：** `frontend/src/api/kb.ts` 的 `postKbEntries` 函数（`method: 'POST'`、`'Content-Type': 'application/json'`、`JSON.stringify(body)`）

---

## No Analog Found

无——所有文件均找到质量充分的类比。

---

## Metadata

**类比搜索范围：**
- `backend/app/api/routes/`（4 个文件全量读取）
- `backend/app/services/`（14 个文件，读取 `job_runner_service.py`）
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/api/deps.py`
- `backend/tests/conftest.py`
- `backend/tests/test_api_path_b.py`
- `backend/tests/test_api_upload.py`
- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`
- `frontend/src/composables/usePathB.ts`
- `frontend/src/components/pathb/PathBDetail.vue`
- `frontend/src/components/table/TablePreviewEditor.vue`
- `requirements.txt`

**文件扫描数：** 18 个
**Pattern 提取日期：** 2026-06-02
