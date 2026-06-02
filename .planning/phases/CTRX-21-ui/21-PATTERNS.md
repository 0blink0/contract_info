# Phase 21: 知识库配置页 UI - Pattern Map

**Mapped:** 2026-06-02  
**Files analyzed:** 10  
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/layouts/AppLayout.vue` | component | request-response | `frontend/src/layouts/AppLayout.vue` | exact |
| `frontend/src/router/index.ts` | route | request-response | `frontend/src/router/index.ts` | exact |
| `frontend/src/views/KbConfigView.vue` | component | CRUD | `frontend/src/views/FileListView.vue` | role+flow |
| `frontend/src/composables/useKbConfigList.ts` | hook | CRUD | `frontend/src/composables/usePathB.ts` | role-match |
| `frontend/src/api/kb.ts` | service | request-response | `frontend/src/api/kb.ts` | exact |
| `backend/app/api/routes/kb.py` | route | request-response | `backend/app/api/routes/kb.py` | exact |
| `backend/app/services/kb_service.py` | service | CRUD | `backend/app/services/kb_service.py` | exact |
| `frontend/tests/router/kb-config-nav.test.mjs` | test | request-response | `frontend/tests/router/wizard-gate.test.mjs` | role+flow |
| `frontend/tests/frontend/kb-config-*.test.mjs` | test | CRUD | `frontend/tests/frontend/settings-view.test.mjs` | role-match |
| `backend/tests/test_api_kb.py` | test | request-response | `backend/tests/test_api_kb.py` | exact |

## Pattern Assignments

### `frontend/src/layouts/AppLayout.vue` (component, request-response)

**Analog:** `frontend/src/layouts/AppLayout.vue`

**Imports pattern** (lines 1-6):
```ts
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { List, Setting, Upload } from '@element-plus/icons-vue'
```

**Menu active/router pattern** (lines 34-43):
```vue
<el-menu
  :default-active="menuActive"
  :default-openeds="defaultOpeneds"
  router
>
```

**Menu item insertion pattern** (lines 43-70):
```vue
<el-menu-item index="/upload">...</el-menu-item>
<el-menu-item index="/jobs" :class="{ 'jobs-parent-active': !!jobId }">...</el-menu-item>
<!-- 在这里插入 /kb-config -->
<el-menu-item index="/settings">...</el-menu-item>
```

---

### `frontend/src/router/index.ts` (route, request-response)

**Analog:** `frontend/src/router/index.ts`

**Lazy route registration pattern** (lines 21-32, 70-75):
```ts
{
  path: '/jobs',
  name: 'jobs',
  component: () => import('@/views/FileListView.vue'),
  meta: { title: '文件列表' },
},
{
  path: '/settings',
  name: 'settings',
  component: () => import('@/views/SettingsView.vue'),
  meta: { title: '系统设置' },
},
```

**Global guard pattern** (lines 79-86):
```ts
router.beforeEach(async (to) => {
  if (!bootstrapPromise) bootstrapPromise = bootstrapDesktopApp()
  await bootstrapPromise
  const needsOnboarding = shouldRequireOnboarding()
  if (needsOnboarding && to.name !== 'onboarding') return { name: 'onboarding' }
  if (!needsOnboarding && to.name === 'onboarding') return { name: 'upload' }
  return true
})
```

---

### `frontend/src/views/KbConfigView.vue` (component, CRUD)

**Analog:** `frontend/src/views/FileListView.vue`

**Page shell + refresh header** (lines 61-68):
```vue
<div class="page-shell">
  <div class="list-header">
    <div>
      <h1 class="page-title">文件列表</h1>
      <p class="page-desc">...</p>
    </div>
    <el-button :loading="loading" @click="refresh">刷新</el-button>
  </div>
```

**Table CRUD interaction pattern** (lines 71-107):
```vue
<el-table v-loading="loading" :data="items" stripe>
  <el-table-column prop="filename" label="文件名" />
  <el-table-column label="操作" width="160" fixed="right">
    <template #default="{ row }">
      <el-button type="danger" link @click.stop="onDelete(row)">删除</el-button>
    </template>
  </el-table-column>
</el-table>
```

**Error feedback pattern** (lines 14-24):
```ts
try {
  const res = await listJobs(100)
  items.value = res.items ?? []
} catch (e) {
  items.value = []
  ElMessage.error(e instanceof Error ? e.message : '加载文件列表失败')
}
```

---

### `frontend/src/composables/useKbConfigList.ts` (hook, CRUD)

**Analog:** `frontend/src/composables/usePathB.ts`

**Composable state and computed pattern** (lines 11-44):
```ts
export function usePathB(jobId: Ref<string | null>) {
  const loaded = ref(false)
  const loading = ref(false)
  const data = ref<PathBResponse | null>(null)
  const snippetRows = computed(() => data.value?.source_snippet_rows ?? [])
```

**Refresh/reset pattern** (lines 71-74, 97-104):
```ts
async function refresh() {
  loaded.value = false
  await load(true)
}

function reset() {
  loaded.value = false
  loading.value = false
  data.value = null
}
watch(jobId, () => reset())
```

**Async error feedback pattern** (lines 58-68):
```ts
try {
  data.value = await getPathB(jobId.value)
  loaded.value = true
} catch (e) {
  ElMessage.error(e instanceof Error ? e.message : '开放日与业绩报酬加载失败')
} finally {
  loading.value = false
}
```

---

### `frontend/src/api/kb.ts` (service, request-response)

**Analog:** `frontend/src/api/kb.ts`

**Typed request/response DTO pattern** (lines 3-33):
```ts
export interface KbEntryItem {
  id: string
  field_name: string
  field_value: string
  snippet: string
  source_job_id: string
  source_filename: string
  created_at: string
}
```

**Query composition pattern** (lines 44-49):
```ts
export async function getKbEntries(field_name?: string): Promise<KbListResponse> {
  const path = field_name
    ? `/kb/entries?field_name=${encodeURIComponent(field_name)}`
    : '/kb/entries'
  const res = await apiFetch(path)
  return res.json()
}
```

**Delete endpoint wrapper pattern** (lines 52-54):
```ts
export async function deleteKbEntry(id: string): Promise<void> {
  await apiFetch(`/kb/entries/${id}`, { method: 'DELETE' })
}
```

---

### `backend/app/api/routes/kb.py` (route, request-response)

**Analog:** `backend/app/api/routes/kb.py`

**APIRouter + auth dependency pattern** (lines 3-10):
```py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.app.api.deps import verify_api_key

router = APIRouter(prefix="/kb", tags=["kb"], dependencies=[Depends(verify_api_key)])
```

**GET query + response model pattern** (lines 53-60):
```py
@router.get("/entries", response_model=KbListResponse)
def get_kb_entries(field_name: str | None = Query(default=None)) -> KbListResponse:
    svc = get_kb_service()
    if svc is None:
        return KbListResponse(items=[], total=0)
    items = svc.list_entries(field_name=field_name)
    return KbListResponse(items=[KbEntryItem(**item) for item in items], total=len(items))
```

**Delete validation + HTTPException pattern** (lines 62-73):
```py
@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kb_entry(entry_id: str) -> None:
    try:
        uuid.UUID(entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="entry_id 格式无效") from exc
```

---

### `backend/app/services/kb_service.py` (service, CRUD)

**Analog:** `backend/app/services/kb_service.py`

**Service class + model availability pattern** (lines 32-43):
```py
class KbService:
    def __init__(self, table: Any) -> None:
        self._table = table
        self._model: Any = None

    @property
    def model_available(self) -> bool:
        return self._model is not None
```

**List + filter baseline pattern** (lines 87-105):
```py
def list_entries(self, field_name: str | None = None) -> list[dict[str, str]]:
    table = self._table.to_arrow()
    data = table.to_pydict()
    # ... assemble row ...
    if field_name and row["field_name"] != field_name:
        continue
    items.append(row)
    return items
```

**Delete storage operation pattern** (lines 107-108):
```py
def delete_entry(self, entry_id: str) -> None:
    self._table.delete(f"id = '{entry_id}'")
```

---

### `frontend/tests/router/kb-config-nav.test.mjs` (test, request-response)

**Analog:** `frontend/tests/router/wizard-gate.test.mjs`

**Router source-file assertion pattern** (lines 6-14):
```js
const root = path.resolve(import.meta.dirname, '..', '..', '..')
const routerPath = path.join(root, 'frontend', 'src', 'router', 'index.ts')
const routerCode = fs.readFileSync(routerPath, 'utf-8')

test('router has onboarding route and gate', () => {
  assert.match(routerCode, /path:\s*['"]\/onboarding['"]/)
})
```

---

### `frontend/tests/frontend/kb-config-*.test.mjs` (test, CRUD)

**Analog:** `frontend/tests/frontend/settings-view.test.mjs`

**View source-file smoke assertion pattern** (lines 6-14):
```js
const root = path.resolve(import.meta.dirname, '..', '..', '..')
const viewPath = path.join(root, 'frontend', 'src', 'views', 'SettingsView.vue')
const viewCode = fs.readFileSync(viewPath, 'utf-8')

test('settings view uses save-settings and restart feedback', () => {
  assert.match(viewCode, /saveSettings/)
})
```

---

### `backend/tests/test_api_kb.py` (test, request-response)

**Analog:** `backend/tests/test_api_kb.py`

**Service patch + endpoint call pattern** (lines 16-24):
```py
mock_svc = Mock()
mock_svc.model_available = True
mock_svc.add_entries = AsyncMock(return_value=["test-uuid-1"])
with patch("backend.app.api.routes.kb.get_kb_service", return_value=mock_svc):
    resp = api_client.post("/api/v1/kb/entries", json=KB_ENTRY_PAYLOAD, headers=api_headers)
assert resp.status_code == 200
```

**Query assertion pattern** (lines 60-70):
```py
resp = api_client.get("/api/v1/kb/entries?field_name=业绩报酬提取方式", headers=api_headers)
assert resp.status_code == 200
mock_svc.list_entries.assert_called_once_with(field_name="业绩报酬提取方式")
```

## Shared Patterns

### Authentication
**Source:** `backend/app/api/routes/kb.py` (line 9)  
**Apply to:** 后端 KB 路由保持 API key 保护
```py
router = APIRouter(prefix="/kb", tags=["kb"], dependencies=[Depends(verify_api_key)])
```

### Error Handling
**Source:** `frontend/src/views/FileListView.vue` (lines 19-24), `frontend/src/composables/useConfirmDeleteJob.ts` (lines 17-24)  
**Apply to:** 前端列表加载/删除动作统一 `ElMessage` 错误反馈
```ts
} catch (e) {
  ElMessage.error(e instanceof Error ? e.message : '删除失败')
  return false
}
```

### Confirmation UX
**Source:** `frontend/src/composables/useConfirmDeleteJob.ts` (lines 9-13), `frontend/src/layouts/JobDetailLayout.vue` (lines 121-125)  
**Apply to:** KB 删除必须二次确认且文案含“不可恢复”
```ts
await ElMessageBox.confirm(
  `确定删除「${filename}」？...且不可恢复。`,
  '删除确认',
  { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
)
```

### Route + Menu Active Sync
**Source:** `frontend/src/layouts/AppLayout.vue` (lines 9-21, 34-37), `frontend/src/router/index.ts` (route meta block)  
**Apply to:** 新增 `/kb-config` 后保持菜单高亮与路由一致
```ts
const menuActive = computed(() => (jobId.value ? route.path : activeMenu.value))
```

## No Analog Found

无。Phase 21 涉及文件均存在直接或高相似度对照实现。

## Metadata

**Analog search scope:** `frontend/src/layouts`, `frontend/src/router`, `frontend/src/views`, `frontend/src/composables`, `frontend/src/api`, `frontend/tests`, `backend/app/api/routes`, `backend/app/services`, `backend/tests`  
**Files scanned:** 12  
**Pattern extraction date:** 2026-06-02
