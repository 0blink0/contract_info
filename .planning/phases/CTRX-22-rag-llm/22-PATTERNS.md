# Phase 22: RAG 检索与 LLM 注入 - Pattern Map

**Mapped:** 2026-06-02  
**Files analyzed:** 13  
**Analogs found:** 13 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/services/kb_service.py` | service | CRUD + transform | `backend/app/services/kb_service.py` | exact |
| `backend/app/extract/pipeline.py` | service | request-response + batch | `backend/app/extract/pipeline.py` | exact |
| `backend/app/extract/llm/performance_fee.py` | service | request-response | `backend/app/extract/llm/subscription_billing.py` | role-match |
| `backend/app/extract/llm/chapter_prompts.py` | utility | transform | `backend/app/extract/llm/chapter_prompts.py` | exact |
| `backend/app/config.py` | config | transform | `backend/app/config.py` | exact |
| `frontend/src/components/LlmConfigForm.vue` | component | request-response | `frontend/src/components/LlmConfigForm.vue` | exact |
| `frontend/src/views/SettingsView.vue` | component | request-response | `frontend/src/views/SettingsView.vue` | exact |
| `frontend/src/stores/appBootstrap.ts` | store | request-response | `frontend/src/stores/appBootstrap.ts` | exact |
| `electron/types/ipc.ts` | model | transform | `electron/types/ipc.ts` | exact |
| `electron/store.ts` | service | CRUD + validation | `electron/store.ts` | exact |
| `electron/main.ts` | service | event-driven + request-response | `electron/main.ts` | exact |
| `backend/tests/test_rag_prompt_injection.py` | test | request-response | `backend/tests/test_extract_pipeline.py` | role-match |
| `electron/tests/settings-rag-topk.test.mjs` | test | validation | `electron/tests/settings-restart.test.mjs` | role-match |

## Pattern Assignments

### `backend/app/services/kb_service.py` (service, CRUD + transform)

**Analog:** `backend/app/services/kb_service.py`

**Imports + service structure** (lines 1-13, 32-45):
```python
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

class KbService:
    def __init__(self, table: Any) -> None:
        self._table = table
        self._model: Any = None

    def _build_embedding_text(self, field_name: str, field_value: str, snippet: str) -> str:
        return f"字段名：{field_name}\n字段值：{field_value}\n原文摘录：{snippet}"[:512]
```

**Async encode + persistence pattern** (lines 47-85):
```python
texts = [self._build_embedding_text(...) for item in items]
vectors = await asyncio.to_thread(
    self._model.encode,
    texts,
    convert_to_numpy=True,
    show_progress_bar=False,
)
await asyncio.to_thread(self._table.add, rows)
```

**Soft degrade pattern** (lines 48-49, 151-152):
```python
if not self.model_available:
    raise RuntimeError("model_unavailable")

def get_kb_service() -> KbService | None:
    return _kb
```

> Phase 22 可在此文件新增 `search_similar(query, top_k)`，保持同样的 `asyncio.to_thread(...)` + 结构化返回模式。

---

### `backend/app/extract/pipeline.py` (service, request-response + batch)

**Analog:** `backend/app/extract/pipeline.py`

**并发调用 + 条件任务拼装** (lines 324-346):
```python
tasks = []
if fees_win:
    tasks.append(extract_performance_fee_section_llm(client, windows["fees"]))
if sub_win:
    tasks.append(extract_open_day_section_llm(client, windows["subscription"]))
if tasks:
    results_raw = await asyncio.gather(*tasks)
```

**注入到下游规则层参数** (lines 347-355):
```python
path_b_dict, path_b_warnings = extract_path_b_rules(
    document,
    windows,
    fund_name=fund_name,
    product_elements=merged_product,
    llm_perf_raw_section=llm_perf_raw,
    llm_perf_flag=llm_perf_flag,
)
```

**错误容忍/不中断主流程** (lines 356-359):
```python
warnings.extend(path_b_warnings)
result = enrich_extraction_result(result, document)
return result, warnings, path_b_dict
```

> Phase 22 在 performance_fee 分支前增加 RAG 检索时，沿用“可选任务 + warnings 收敛 + 主流程继续”模式。

---

### `backend/app/extract/llm/performance_fee.py` (service, request-response)

**Analog:** `backend/app/extract/llm/subscription_billing.py`

**消息构造模式** (`subscription_billing.py` lines 57-74):
```python
system = ("你是...助手。...只输出 JSON，禁止 markdown。")
user = (
    "【合同片段】\n"
    f"{text_for_llm_prompt(text)}\n\n"
    '请输出 JSON：{"认购费计费方式":"","申购费计费方式":"","赎回费计费方式":""}'
)
messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
```

**重试 + 失败告警模式** (`subscription_billing.py` lines 74-91):
```python
settings = get_settings()
for attempt in range(settings.llm_max_retries + 1):
    try:
        parsed = await client.chat_json(messages, SubscriptionBillingResponse)
        return billing_map_from_response(parsed), []
    except Exception as exc:
        last_err = str(exc)
return {}, [ExtractionWarning(...)]
```

**当前文件已具备同构实现** (`performance_fee.py` lines 57-76)，可直接在 `user` 内容中拼接 few-shot 块，不改返回协议：
```python
parsed = await client.chat_json(messages, PerformanceFeeRawResponse)
return raw, flag, []
```

---

### `backend/app/extract/llm/chapter_prompts.py` (utility, transform)

**Analog:** `backend/app/extract/llm/chapter_prompts.py`

**模板分段拼装模式** (lines 53-75):
```python
system = ("你是私募基金合同要素抽取助手。...")
user = (
    f"【章节窗口】{window_key}\n"
    f"【需抽取字段】{field_list}\n"
    f"【枚举参考】\n{hint_block}\n\n"
    f"【合同片段】\n{text_for_llm_prompt(text)}\n\n"
    "请仅输出 JSON 对象。"
)
```

> 若 Phase 22 选择在 prompt 工具层新增“历史案例参考”片段，优先复用该“标签段落 + 文本限长函数”拼接风格。

---

### `backend/app/config.py` (config, transform)

**Analog:** `backend/app/config.py`

**Pydantic Settings 扩展模式** (lines 40-56):
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(...)
    llm_model: str = "gpt-4o-mini"
    llm_timeout: int = 120
    llm_max_retries: int = 1
```

**读取环境变量并归一化模式** (lines 28-33, 87-92):
```python
raw = os.environ.get("CTRX_DATA_DIR", "").strip()
if raw:
    p = Path(raw)
    p.mkdir(parents=True, exist_ok=True)
    return p
```

> Phase 22 新增 `rag_top_k` 时，遵循 `BaseSettings` 字段默认值 + 读取时 strip/边界处理风格。

---

### `frontend/src/components/LlmConfigForm.vue` (component, request-response)

**Analog:** `frontend/src/components/LlmConfigForm.vue`

**双向绑定 + typed emits** (lines 5-18):
```ts
const props = defineProps<{ modelValue: AppSettings; disabled?: boolean }>()
const emit = defineEmits<{
  (event: 'update:modelValue', value: AppSettings): void
  (event: 'valid-change', value: boolean): void
}>()
```

**计算属性校验 + watch 回传** (lines 20-35):
```ts
const valid = computed(() => { ... })
watch(valid, (value) => emit('valid-change', value), { immediate: true })
```

**UI 约束组件模式** (lines 53-55):
```vue
<el-input-number v-model="form.temperature" :disabled="disabled" :min="0" :max="2" :step="0.1" />
```

> `ragTopK` 输入应复用 `el-input-number` 的 `:min="1"` `:max="10"` 约束。

---

### `frontend/src/views/SettingsView.vue` (component, request-response)

**Analog:** `frontend/src/views/SettingsView.vue`

**加载/保存闭环** (lines 37-51, 57-104):
```ts
const result = await window.api.loadSettings()
formData.value = { ...result.data }

const payload: AppSettings = { ... }
result = await withTimeout(window.api.saveSettings(payload), SAVE_TIMEOUT_MS, '保存超时...')
if (!result.ok) { ElMessage.error(...) }
```

**重启状态联动模式** (lines 11-14, 117-121):
```ts
const reconnecting = computed(() => backendState.value === 'restarting' || saving.value)
<div v-if="reconnecting" class="blocking-mask">...</div>
```

---

### `frontend/src/stores/appBootstrap.ts` (store, request-response)

**Analog:** `frontend/src/stores/appBootstrap.ts`

**默认配置常量模式** (lines 20-25):
```ts
const EMPTY_SETTINGS: AppSettings = {
  llmBaseUrl: '',
  llmApiKey: '',
  llmModel: '',
  temperature: 0.2,
}
```

**loadSettings 合并模式** (lines 72-89):
```ts
const [portRes, configRes] = await Promise.all([window.api.getPort(), window.api.loadSettings()])
state.onboardingDraft = {
  ...state.onboardingDraft,
  ...configRes.data,
}
```

> `ragTopK` 新增后应同时补到 `EMPTY_SETTINGS`、读取 merge、localStorage 草稿同步。

---

### `electron/types/ipc.ts` (model, transform)

**Analog:** `electron/types/ipc.ts`

**配置类型集中定义模式** (lines 12-20):
```ts
export interface LlmSettings {
  llmBaseUrl: string
  llmApiKey: string
  llmModel: string
}

export interface AppSettings extends LlmSettings {
  temperature?: number
}
```

> `ragTopK?: number` 应添加在 `AppSettings`，确保前端/Electron IPC 类型一致。

---

### `electron/store.ts` (service, CRUD + validation)

**Analog:** `electron/store.ts`

**默认值 + 持久化模式** (lines 9-23, 42-48):
```ts
const DEFAULT_SETTINGS: AppSettings = { ... }
const store = new Store<StoreShape>({ defaults: { settings: DEFAULT_SETTINGS } })
```

**输入校验集中函数模式** (lines 30-40):
```ts
export function validateSettings(input: AppSettings): string | null {
  try { new URL(input.llmBaseUrl) } catch { return 'llmBaseUrl must be a valid URL' }
  if (!input.llmApiKey?.trim()) return 'llmApiKey is required'
  if (!input.llmModel?.trim()) return 'llmModel is required'
  return null
}
```

**失败回滚模式** (lines 54-67):
```ts
const current = loadSettings()
try {
  store.set('settings', next)
  return { ok: true }
} catch (error) {
  store.set('settings', current)
  return { ok: false, reason: ... }
}
```

> `ragTopK` 范围校验（1-10）应在 `validateSettings` 实现，沿用同一失败返回协议。

---

### `electron/main.ts` (service, event-driven + request-response)

**Analog:** `electron/main.ts`

**配置注入到后端 env 模式** (lines 111-120):
```ts
function backendChildEnv(port: number): NodeJS.ProcessEnv {
  const settings = loadSettings()
  return {
    ...process.env,
    CTRX_PORT: String(port),
    OPENAI_API_KEY: settings.llmApiKey.trim(),
    OPENAI_BASE_URL: settings.llmBaseUrl.trim(),
    LLM_MODEL: settings.llmModel.trim(),
  }
}
```

**重启+回滚容错模式** (lines 183-223):
```ts
async function restartBackendWithRollback(previous: AppSettings): Promise<...> {
  try {
    await stopBackend()
    await spawnBackend(port)
    return { restarted: true, rollbackApplied: false, ... }
  } catch (restartError) {
    restoreSettings(previous)
    ...
  }
}
```

> Phase 22 新增 `RAG_TOP_K` 时，直接扩展 `backendChildEnv` 注入，保持重启生效机制不变。

---

### `backend/tests/test_rag_prompt_injection.py` (test, request-response)

**Analog:** `backend/tests/test_extract_pipeline.py`

**同步入口 + llm 开关桩模式** (lines 16-24):
```python
class _LlmOff:
    available = False
    model_name = ""

result, warnings, path_b = extract_document_sync(sample_document, llm_client=_LlmOff())
```

**API/服务 mock 模式补充参考:** `backend/tests/test_api_kb.py` lines 16-33
```python
mock_svc = Mock()
mock_svc.model_available = True
mock_svc.add_entries = AsyncMock(return_value=["test-uuid-1"])
```

---

### `electron/tests/settings-rag-topk.test.mjs` (test, validation)

**Analog:** `electron/tests/settings-restart.test.mjs`

**源码断言风格模式** (lines 12-22):
```js
test('save-settings handler triggers restart workflow', () => {
  assert.match(ipcCode, /restartBackendWithRollback/)
  assert.match(ipcCode, /RESTART_ERROR/)
  assert.match(ipcCode, /rollbackApplied/)
})
```

**生命周期断言补充参考:** `electron/tests/lifecycle.test.mjs` lines 16-20
```js
assert.match(mainCode, /HEALTH_TIMEOUT_MS\s*=\s*30_000/)
assert.match(mainCode, /RETRY_BACKOFF_MS\s*=\s*\[0,\s*2000,\s*5000\]/)
```

## Shared Patterns

### 1) LLM 调用与降级
**Source:** `backend/app/extract/llm/performance_fee.py`, `backend/app/extract/llm/subscription_billing.py`  
**Apply to:** `performance_fee.py` RAG 注入逻辑
```python
if not client or not client.available or not text.strip():
    return {}, []

for attempt in range(settings.llm_max_retries + 1):
    try:
        ...
    except Exception as exc:
        last_err = str(exc)
```

### 2) Pipeline 非阻塞集成
**Source:** `backend/app/extract/pipeline.py`  
**Apply to:** 检索失败或空库时继续提取主流程
```python
tasks = []
if fees_win:
    tasks.append(...)
if tasks:
    results_raw = await asyncio.gather(*tasks)
warnings.extend(path_b_warnings)
```

### 3) 表单与配置双层校验
**Source:** `frontend/src/components/LlmConfigForm.vue`, `electron/store.ts`  
**Apply to:** `ragTopK` 1-10 约束
```ts
<el-input-number v-model="..." :min="1" :max="10" />
export function validateSettings(input: AppSettings): string | null { ... }
```

### 4) 保存后重启生效
**Source:** `frontend/src/views/SettingsView.vue`, `electron/ipc.ts`, `electron/main.ts`  
**Apply to:** D-07 “重启后生效”
```ts
result = await window.api.saveSettings(payload)
const restartResult = await options.restartBackendWithRollback(previous)
env: backendChildEnv(port)
```

## No Analog Found

无。Phase 22 目标文件均能在当前代码库找到强匹配实现（exact 或 role-match）。

## Metadata

**Analog search scope:**  
- `backend/app/services`  
- `backend/app/extract`  
- `backend/app/api/routes`  
- `backend/tests`  
- `frontend/src/components`  
- `frontend/src/views`  
- `frontend/src/stores`  
- `frontend/tests/frontend`  
- `electron/`  
- `electron/tests`

**Files scanned:** 16  
**Pattern extraction date:** 2026-06-02
