# Phase 20: 知识库数据层 + PathB 录入 UI - Research

**Researched:** 2026-06-02
**Domain:** LanceDB 向量存储 / sentence-transformers / FastAPI lifespan / Vue 3 inline-edit 表格
**Confidence:** HIGH（核心 API 从包源码直接验证）

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 使用 bge-m3（`BAAI/bge-m3`），不使用 `paraphrase-multilingual-MiniLM-L12-v2`
- **D-02:** 模型从本地路径加载：`SentenceTransformer(str(models_dir / "bge-m3"))`，`CTRX_MODELS_DIR` 环境变量指向缓存目录
- **D-03:** LanceDB 向量列维度固定为 **1024**，建表时硬编码
- **D-04:** embedding 输入截断至约 **512 字符**（`text[:512]`）
- **D-05:** embedding 输入格式：`"字段名：{field_name}\n字段值：{field_value}\n原文摘录：{snippet}"`，截断后传入
- **D-06:** 软降级——bge-m3 加载失败时应用正常启动，KB 功能进入"不可用"状态
- **D-07:** KB 不可用时：`POST /kb/entries` 返回 503；前端显示橙色 `el-alert`；「存入知识库」按钮 disabled；表格仍渲染但禁用输入
- **D-08:** PathB 数据不可用（`available === false`）时，完全隐藏 KB 录入区
- **D-09:** PathB 数据可用时，KB 录入区始终可见（即使模型未加载）
- **D-10:** 允许 `原文摘录` 为空，无客户端强验证

### Claude's Discretion

- LanceDB 表结构（字段名、列类型）由 researcher/planner 确定
- `POST /kb/entries` 批量入库的并发模式由 planner 确定，保持与现有 lifespan/FastAPI 模式一致
- PathB → KB 4 行预填映射由 researcher 从代码中查明

### Deferred Ideas (OUT OF SCOPE)

- Phase 21: 左侧菜单「知识库配置」入口与历史案例列表页
- Phase 22: RAG 检索 Top-K 注入 performance_fee/chapter_prompts prompt
- Phase 23: PyInstaller 打包兼容
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| KB-BE-01 | 后端初始化 LanceDB 本地向量表（`CTRX_DATA_DIR` 下），应用启动时自动创建 | LanceDB `connect()` + `create_table(exist_ok=True)` 模式；lifespan hook 挂入点已确认 |
| KB-BE-02 | 加载 sentence-transformers bge-m3 模型，启动时预热 | `SentenceTransformer(local_path, local_files_only=True)` + `model.encode(["预热"])` 模式已验证 |
| KB-BE-03 | `POST /kb/entries`：批量入库 + embedding，返回 ID 列表 | `asyncio.to_thread` + `table.add(list_of_dict)` 模式；schema 设计已完成 |
| KB-BE-04 | `GET /kb/entries`：全量列表 + `field_name` 过滤 | `table.to_pandas()` / `table.to_arrow()` + filter 模式 |
| KB-BE-05 | `DELETE /kb/entries/{id}`：删除单条 | `table.delete(f"id = '{id}'")`（字符串 where 子句） |
| KB-ENTRY-01 | PathBDetail 底部 3 列 4 行可编辑录入表格 | `el-table` + `el-table-column type="selection"` + `el-input` inline-edit 模式（参考 TablePreviewEditor） |
| KB-ENTRY-02 | 页面加载时自动预填当前解析结果 | 从 `crmRows` computed 中取 4 个固定 `crm_field` 的 `suggested_value` + `snippet` |
| KB-ENTRY-03 | 字段值和原文摘录单元格可自由编辑 | `el-input v-model="row.field_value"` 模式已有参考 |
| KB-ENTRY-04 | 每行左侧复选框 | `el-table-column type="selection"` + `@selection-change` |
| KB-ENTRY-05 | 「存入知识库」按钮批量提交，成功后提示 | `ElMessage.success(\`已存入 ${n} 条\`)` 模式 |
</phase_requirements>

---

## Summary

Phase 20 交付两个并行能力：（1）LanceDB 本地向量知识库后端，包括 5 个 CRUD 端点和 bge-m3 embedding 生成；（2）PathB 页底部可编辑录入表格。从 LanceDB 0.33.0 轮档源码直接验证了核心 API（`connect`、`create_table`、`open_table`、`table.add`、`table.delete`、`table.to_arrow`），从 sentence-transformers 5.5.1 轮档源码验证了 `SentenceTransformer.__init__` 参数（`model_name_or_path`、`local_files_only=True`）和 `encode()` 签名。

两个新包（`lancedb==0.33.0`、`sentence-transformers==5.5.1`）均需添加至 `requirements.txt`；`pyarrow>=16` 已被 lancedb 作为依赖自动引入。从现有代码读取后：后端集成点在 `main.py` 的 `lifespan()` 中（目前仅在 `yield` 后执行 `shutdown_runner`，前置空间完整可用）；前端集成点在 `PathBDetail.vue` 底部追加，参考 `TablePreviewEditor.vue` 的 `el-input v-model` inline-edit 模式。

**Primary recommendation:** 后端新建 `kb_service.py`（模块单例 `_kb: KbService | None`）+ `routes/kb.py`；前端新建 `api/kb.ts` + `composables/useKbEntry.ts` + 在 `PathBDetail.vue` 底部追加录入区块。

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LanceDB 初始化 + 表创建 | Backend（Python 服务层） | — | 文件系统操作，必须在服务端完成 |
| bge-m3 embedding 生成 | Backend（Python 服务层） | — | CPU 密集型，不适合浏览器；依赖本地模型权重 |
| KB CRUD 端点 | API（FastAPI router） | — | REST 接口层，与其他 /kb/ 端点一致 |
| KB 录入表格渲染 | Frontend（Vue 组件） | — | 纯展示层，数据来自 pathB crmRows |
| 预填数据映射 | Frontend（composable） | — | 从已有 `crmRows` computed 派生，无需额外 API 调用 |
| KB 入库成功通知 | Frontend（composable） | — | `ElMessage.success` 是全项目统一模式 |
| 503 软降级状态 | API（FastAPI route） → Frontend（el-alert） | — | 后端返回 503，前端检测并展示橙色警告 |

---

## Standard Stack

### Core（新增）

| 库 | 版本 | 用途 | Why Standard |
|----|------|------|--------------|
| `lancedb` | `0.33.0` | 本地向量数据库 CRUD | 项目已决策（STATE.md）；纯本地文件，无服务端，PyInstaller 兼容路径 |
| `sentence-transformers` | `5.5.1` | 加载 bge-m3，生成 1024 维 embedding | 项目已决策；官方库，支持本地路径加载 |
| `pyarrow` | `>=16`（lancedb 依赖自动引入，当前最新 `24.0.0`） | LanceDB 底层列式存储 Schema 定义 | lancedb 强依赖，项目之前未直接使用 |

### Supporting（现有，本阶段复用）

| 库 | 版本 | 用途 | When to Use |
|----|------|------|-------------|
| `fastapi` | `>=0.110` | KB 路由层 | 已存在，新建 `routes/kb.py` |
| `pydantic` | `>=2.0` | KB 请求/响应 schema | 已存在，新建 Pydantic model |
| `element-plus` | `^2.9.0` | 前端 el-table + el-input | 已存在，复用 inline-edit 模式 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `lancedb` local file | ChromaDB | ChromaDB 需要服务端进程；lancedb 纯文件更适合 PyInstaller |
| `sentence-transformers` | 直接用 transformers + torch | sentence-transformers 封装更简洁；本项目 `encode()` 调用量少 |
| `table.to_arrow().to_pydict()` 做全量查询 | pandas | pandas 是 lancedb 推荐方式，但本项目未安装；to_arrow() 更轻量 |

**Installation（新增两行到 requirements.txt）：**
```bash
lancedb>=0.33.0
sentence-transformers>=5.5.1
```
（pyarrow 作为 lancedb 的依赖自动安装，无需显式声明）

---

## Package Legitimacy Audit

> 本阶段安装 Python（PyPI）包。slopcheck 错误地将 Python 包名与 npm 注册表比对，结果对 pyarrow 和 sentence-transformers 报 SLOP——这是已知的跨生态假阳性（slopcheck 仅懂 npm，不懂 PyPI）。以下 Disposition 基于 PyPI 注册表直接验证。

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `lancedb` | PyPI | ~3 yrs | 高（主流向量库） | github.com/lancedb/lancedb | N/A（跨生态假阳性，PyPI 确认存在） | Approved |
| `sentence-transformers` | PyPI | ~6 yrs | 极高（数百万/月） | github.com/UKPLab/sentence-transformers | N/A（跨生态假阳性，PyPI 确认存在） | Approved |
| `pyarrow` | PyPI | ~8 yrs（Apache Arrow 官方） | 极高 | github.com/apache/arrow | N/A（跨生态假阳性，PyPI 确认存在） | Approved（作为 lancedb 依赖自动引入） |

**slopcheck 跨生态说明：** slopcheck 在 npm 上搜索 Python 包名，必然找不到，误报 SLOP。PyPI 注册表通过 `pip index versions` 直接验证三个包均存在且活跃。

**Packages removed due to slopcheck [SLOP] verdict:** none（全部为假阳性）
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
PathBDetail.vue（前端）
    │
    ├── [加载时] crmRows(computed) ──→ kbRows(ref) 预填 4 条目
    │
    ├── [用户勾选 + 点击「存入知识库」]
    │        │
    │        ▼
    │   useKbEntry.submit(selectedRows)
    │        │
    │        ▼
    │   POST /api/v1/kb/entries   ────────────────────────────────┐
    │                                                              │
    ▼                                                              ▼
  el-alert (橙色，D-07)                                  FastAPI: routes/kb.py
  el-button disabled                                          │
                                                             ▼
                                               KbService.add_entries(items)
                                                             │
                                              ┌──────────────┴──────────────┐
                                              ▼                              ▼
                                    asyncio.to_thread(                 lancedb Table
                                      model.encode(texts)            table.add(rows)
                                    )                                        │
                                              │                              │
                                              └──────────────┬──────────────┘
                                                             ▼
                                                   返回 { ids: [...] }

GET /api/v1/kb/entries  ──→  KbService.list_entries(field_name?)
                                        │
                                        ▼
                                table.to_arrow().to_pydict()
                                        │
                                        ▼ (filter if field_name)
                                   返回 entry list

DELETE /api/v1/kb/entries/{id}  ──→  KbService.delete_entry(id)
                                              │
                                              ▼
                                  table.delete(f"id = '{id}'")
```

### Recommended Project Structure

```
backend/app/
├── services/
│   └── kb_service.py          # 新建：KbService 单例 + _kb 模块级变量
├── api/routes/
│   └── kb.py                  # 新建：/kb 路由
└── main.py                    # 修改：lifespan() 挂入 KB 初始化

frontend/src/
├── api/
│   └── kb.ts                  # 新建：postKbEntries / getKbEntries / deleteKbEntry
├── composables/
│   └── useKbEntry.ts          # 新建：kbRows ref / selected / submit / kbStatus
└── components/pathb/
    └── PathBDetail.vue        # 修改：底部追加 KB 录入区块
```

### Pattern 1: LanceDB 初始化（lifespan 挂入）

**What:** lifespan() yield 前初始化 LanceDB 连接与表，创建 KbService 单例存入模块变量

**When to use:** 应用启动时一次性初始化，后续路由直接调用 `get_kb_service()`

```python
# Source: LanceDB 0.33.0 wheel source (lancedb/db.py + lancedb/__init__.py)
# backend/app/services/kb_service.py

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa

from backend.app.config import data_dir

logger = logging.getLogger(__name__)

KB_TABLE_NAME = "kb_entries"
VECTOR_DIM = 1024  # bge-m3 native output (D-03)

_KB_SCHEMA = pa.schema([
    pa.field("id", pa.string()),                         # UUID string
    pa.field("field_name", pa.string()),                 # 字段名
    pa.field("field_value", pa.string()),                # 字段值
    pa.field("snippet", pa.string()),                    # 原文摘录（允许空字符串 D-10）
    pa.field("source_job_id", pa.string()),              # 来源合同 job_id
    pa.field("source_filename", pa.string()),            # 来源合同文件名
    pa.field("created_at", pa.string()),                 # ISO 时间戳字符串
    pa.field("vector", pa.list_(pa.float32(), VECTOR_DIM)),  # 1024-dim
])


class KbService:
    def __init__(self, table):
        self._table = table
        self._model = None  # 由外部注入或 None

    def set_model(self, model) -> None:
        self._model = model

    @property
    def model_available(self) -> bool:
        return self._model is not None

    def _build_embedding_text(self, field_name: str, field_value: str, snippet: str) -> str:
        text = f"字段名：{field_name}\n字段值：{field_value}\n原文摘录：{snippet}"
        return text[:512]  # D-04

    async def add_entries(self, items: list[dict]) -> list[str]:
        """items 每项含 field_name/field_value/snippet/source_job_id/source_filename"""
        if not self.model_available:
            raise RuntimeError("model_unavailable")

        texts = [
            self._build_embedding_text(
                item["field_name"], item["field_value"], item.get("snippet") or ""
            )
            for item in items
        ]
        # encode() 是 CPU 阻塞调用，用 asyncio.to_thread 避免阻塞事件循环
        vectors = await asyncio.to_thread(
            self._model.encode,
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        rows = []
        ids = []
        now = datetime.now(timezone.utc).isoformat()
        for item, vec in zip(items, vectors):
            entry_id = str(uuid.uuid4())
            ids.append(entry_id)
            rows.append({
                "id": entry_id,
                "field_name": item["field_name"],
                "field_value": item.get("field_value") or "",
                "snippet": item.get("snippet") or "",
                "source_job_id": item.get("source_job_id") or "",
                "source_filename": item.get("source_filename") or "",
                "created_at": now,
                "vector": vec.tolist(),
            })

        await asyncio.to_thread(self._table.add, rows)
        return ids

    def list_entries(self, field_name: str | None = None) -> list[dict]:
        tbl = self._table.to_arrow()
        d = tbl.to_pydict()
        n = len(d["id"])
        entries = []
        for i in range(n):
            if field_name and d["field_name"][i] != field_name:
                continue
            entries.append({
                "id": d["id"][i],
                "field_name": d["field_name"][i],
                "field_value": d["field_value"][i],
                "snippet": d["snippet"][i],
                "source_job_id": d["source_job_id"][i],
                "source_filename": d["source_filename"][i],
                "created_at": d["created_at"][i],
            })
        return entries

    def delete_entry(self, entry_id: str) -> None:
        # LanceDB delete() 接受 SQL where 字符串
        self._table.delete(f"id = '{entry_id}'")


_kb: KbService | None = None


def get_kb_service() -> KbService | None:
    return _kb


def init_kb_service() -> None:
    """在 lifespan() yield 前调用，初始化 LanceDB + 加载 bge-m3 模型。"""
    global _kb
    import os
    import lancedb

    kb_dir = str(data_dir() / "kb")
    db = lancedb.connect(kb_dir)  # 本地文件，自动创建目录

    # 表不存在则创建，已存在则打开（exist_ok=True）
    try:
        table = db.open_table(KB_TABLE_NAME)
    except Exception:
        table = db.create_table(KB_TABLE_NAME, schema=_KB_SCHEMA)

    svc = KbService(table)

    # 加载 bge-m3 模型（D-06 软降级）
    models_dir_raw = os.environ.get("CTRX_MODELS_DIR", "").strip()
    if models_dir_raw:
        model_path = Path(models_dir_raw) / "bge-m3"
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(str(model_path), local_files_only=True)
            # 预热（D-02）
            model.encode(["预热"], show_progress_bar=False)
            svc.set_model(model)
            logger.info("bge-m3 loaded from %s", model_path)
        except Exception as e:
            logger.warning("bge-m3 failed to load, KB unavailable: %s", e)
    else:
        logger.warning("CTRX_MODELS_DIR not set, KB model unavailable")

    _kb = svc
```

### Pattern 2: FastAPI 路由（kb.py）

**What:** `POST /kb/entries`（批量入库）、`GET /kb/entries`（列表）、`DELETE /kb/entries/{id}`

**When to use:** 遵循现有 jobs.py 路由结构

```python
# Source: 基于现有 backend/app/api/routes/jobs.py 模式
# backend/app/api/routes/kb.py

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.app.api.deps import verify_api_key
from backend.app.services.kb_service import get_kb_service

router = APIRouter(prefix="/kb", tags=["kb"], dependencies=[Depends(verify_api_key)])


class KbEntryInput(BaseModel):
    field_name: str
    field_value: str
    snippet: str = ""  # D-10 允许空
    source_job_id: str = ""
    source_filename: str = ""


class KbEntriesRequest(BaseModel):
    entries: list[KbEntryInput]


class KbEntriesResponse(BaseModel):
    ids: list[str]
    count: int


class KbEntryItem(BaseModel):
    id: str
    field_name: str
    field_value: str
    snippet: str
    source_job_id: str
    source_filename: str
    created_at: str


class KbListResponse(BaseModel):
    items: list[KbEntryItem]
    total: int


@router.post("/entries", response_model=KbEntriesResponse)
async def post_kb_entries(body: KbEntriesRequest) -> KbEntriesResponse:
    svc = get_kb_service()
    if svc is None or not svc.model_available:
        raise HTTPException(
            status_code=503,
            detail="知识库功能不可用（bge-m3 模型未加载）",
        )
    try:
        ids = await svc.add_entries([e.model_dump() for e in body.entries])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return KbEntriesResponse(ids=ids, count=len(ids))


@router.get("/entries", response_model=KbListResponse)
def get_kb_entries(field_name: str | None = Query(None)) -> KbListResponse:
    svc = get_kb_service()
    if svc is None:
        return KbListResponse(items=[], total=0)
    items = svc.list_entries(field_name=field_name)
    return KbListResponse(items=[KbEntryItem(**i) for i in items], total=len(items))


@router.delete("/entries/{entry_id}", status_code=204)
def delete_kb_entry(entry_id: str) -> None:
    svc = get_kb_service()
    if svc is None:
        raise HTTPException(status_code=503, detail="知识库不可用")
    try:
        svc.delete_entry(entry_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

### Pattern 3: lifespan() 挂入（main.py 修改）

**What:** 在 `yield` 前调用 `init_kb_service()`

```python
# Source: 现有 backend/app/main.py lifespan 结构
# 修改 lifespan() 函数：

@asynccontextmanager
async def lifespan(app: FastAPI):
    # yield 前：启动初始化（LanceDB + bge-m3 预热可能耗时数秒）
    await asyncio.to_thread(init_kb_service)   # 阻塞操作放入线程
    yield
    # yield 后：关闭清理
    shutdown_runner(wait=False)
```

**注意：** `init_kb_service()` 内部加载 bge-m3 模型，是 CPU 密集型同步操作。在 lifespan 中用 `asyncio.to_thread` 包裹，避免阻塞 FastAPI 事件循环启动。

### Pattern 4: router 注册（main.py 新增一行）

```python
# backend/app/main.py 新增：
from backend.app.api.routes import health, jobs, kb, upload

v1 = APIRouter(prefix="/api/v1")
v1.include_router(health.router)
v1.include_router(upload.router)
v1.include_router(jobs.router)
v1.include_router(kb.router)      # 新增
app.include_router(v1)
```

路由实际前缀为 `/api/v1/kb`（v1 prefix + kb router prefix）。

### Pattern 5: 前端 useKbEntry.ts composable

**What:** 管理 kbRows 数据、勾选状态、提交逻辑（参考 usePathB.ts 结构）

```typescript
// Source: 现有 frontend/src/composables/usePathB.ts 结构模式
// frontend/src/composables/useKbEntry.ts

import { ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { CrmHandoffItem } from '@/api/types'

export interface KbRow {
  field_name: string       // 不可编辑（来自 crmRows）
  field_value: string      // 可编辑
  snippet: string          // 可编辑（允许空 D-10）
  selected: boolean        // 复选框状态
}

const KB_FIELDS = ['业绩报酬提取方式', '业绩基准类型', '门槛净值类型', '提取时点'] as const

export function useKbEntry(
  jobId: Ref<string | null>,
  jobFilename: Ref<string | null>,
  crmRows: Ref<CrmHandoffItem[]>,
) {
  const kbRows = ref<KbRow[]>([])
  const submitting = ref(false)
  const kbUnavailable = ref(false)   // 503 状态

  function buildRows() {
    kbRows.value = KB_FIELDS.map((fieldName) => {
      const row = crmRows.value.find((r) => r.crm_field === fieldName)
      return {
        field_name: fieldName,
        field_value: row?.suggested_value ?? '',
        snippet: row?.snippet ?? '',
        selected: false,
      }
    })
  }

  async function submit() {
    const selected = kbRows.value.filter((r) => r.selected)
    if (!selected.length || !jobId.value) return

    submitting.value = true
    try {
      const res = await postKbEntries({
        entries: selected.map((r) => ({
          field_name: r.field_name,
          field_value: r.field_value,
          snippet: r.snippet,
          source_job_id: jobId.value!,
          source_filename: jobFilename.value ?? '',
        })),
      })
      ElMessage.success(`已存入 ${res.count} 条`)
    } catch (e) {
      // 检测 503
      if (e instanceof Error && e.message.includes('503')) {
        kbUnavailable.value = true
      }
      ElMessage.error(e instanceof Error ? e.message : '存入失败')
    } finally {
      submitting.value = false
    }
  }

  return { kbRows, submitting, kbUnavailable, buildRows, submit }
}
```

### Pattern 6: PathBDetail.vue 底部追加 KB 录入区块

**What:** 在 `</template>` 关闭之前（`v-else-if="data"` 块内）追加

```vue
<!-- Source: 现有 PathBDetail.vue 模板 + TablePreviewEditor.vue inline-edit 模式 -->
<div v-if="available" class="kb-entry-section">
  <div class="sub-title">存入知识库</div>

  <!-- D-07: KB 不可用时橙色警告 -->
  <el-alert
    v-if="kbUnavailable"
    type="warning"
    :closable="false"
    title="知识库功能不可用（模型未加载）"
    class="kb-alert"
  />

  <el-table
    :data="kbRows"
    size="small"
    stripe
    border
    class="section-table"
    @selection-change="(rows) => kbRows.forEach(r => r.selected = rows.includes(r))"
  >
    <!-- D-04: 复选框列 -->
    <el-table-column type="selection" width="46" />

    <!-- 字段名：不可编辑 -->
    <el-table-column prop="field_name" label="字段名" width="150" />

    <!-- 字段值：可编辑 -->
    <el-table-column label="字段值" min-width="160">
      <template #default="{ row }">
        <el-input
          v-model="row.field_value"
          size="small"
          :disabled="kbUnavailable"
          placeholder="（可修改）"
        />
      </template>
    </el-table-column>

    <!-- 原文摘录：可编辑，允许空（D-10）-->
    <el-table-column label="原文摘录" min-width="240">
      <template #default="{ row }">
        <el-input
          v-model="row.snippet"
          size="small"
          :disabled="kbUnavailable"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 3 }"
          placeholder="（可选）"
        />
      </template>
    </el-table-column>
  </el-table>

  <el-button
    type="primary"
    size="small"
    :loading="submitting"
    :disabled="kbUnavailable || !kbRows.some(r => r.selected)"
    @click="submit"
  >
    存入知识库
  </el-button>
</div>
```

### Anti-Patterns to Avoid

- **直接在 FastAPI async route 中调用 `model.encode()`：** encode() 是 CPU 阻塞操作；必须用 `asyncio.to_thread()` 包裹，否则阻塞整个事件循环
- **在 lifespan yield 前直接 await 阻塞调用：** 应用 lifespan 期间调用阻塞 I/O（模型加载）必须用 `asyncio.to_thread`
- **用 `table.create_table(mode="create")` 不带 `exist_ok`：** 重启后会因表已存在而报错。应使用 `open_table` + 捕获异常后 `create_table`，或 `create_table(exist_ok=True)`
- **pandas 依赖：** `table.to_pandas()` 需要 pandas；本项目未安装。改用 `table.to_arrow().to_pydict()` 读取全量数据
- **el-table selection 模式的 `selection-change` 误用：** Element Plus `@selection-change` 回调参数是当前选中行的数组；需要对 kbRows 遍历设置 `selected` flag，不能直接赋值
- **`table.delete()` 用整数 ID：** 本项目 KB 表 id 列是 string（UUID）；where 子句必须用引号：`f"id = '{entry_id}'"` 而不是 `f"id = {entry_id}"`

---

## PathB → KB 4 行预填映射（已从 path_b_crm.py 源码确认）

[VERIFIED: codebase grep of backend/app/extract/path_b_crm.py]

`build_crm_handoff()` 返回的 `items` 列表中，`crm_field` 值与 `suggested_value`/`snippet` 对应关系如下：

| KB 表行 | crm_field 精确字符串 | 数据来源 |
|---------|---------------------|---------|
| 第 1 行 | `"业绩报酬提取方式"` | `perf.extraction_method` 经模式匹配；snippet 来自 `snippets["performance_fee.extraction_method"]` |
| 第 2 行 | `"业绩基准类型"` | `_suggest_benchmark()` 判断超额收益/净值型；snippet 来自 benchmark 字段 |
| 第 3 行 | `"门槛净值类型"` | `perf.hurdle_nav` 或 `_suggest_hurdle()`；snippet 来自对应摘录 |
| 第 4 行 | `"提取时点"` | `perf.extraction_timing` 或 `_suggest_timing(fees_ctx)`；snippet 来自对应摘录 |

**注意：** `crm_handoff` 列表中 index 0 是「是否计提业绩报酬」，index 5 可能是「提取比例」，index 6（条件存在）是「固定时点提取频率」。KB 录入表格固定取 4 个字段：通过 `crm_field` 字符串匹配，不依赖数组下标。

前端 `useKbEntry.buildRows()` 实现：
```typescript
const KB_FIELDS = ['业绩报酬提取方式', '业绩基准类型', '门槛净值类型', '提取时点']
// 从 crmRows.value (PathBResponse.crm_handoff) 中 find() 对应行
const row = crmRows.value.find((r) => r.crm_field === fieldName)
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 向量存储 / 持久化 | 自己写 sqlite + numpy array | `lancedb` | LanceDB 处理 Lance 格式、文件一致性、列压缩 |
| Embedding 生成 | 自己调用 transformers tokenizer+model | `sentence_transformers.SentenceTransformer.encode()` | encode() 封装了 batching、padding、pooling、normalize；手写易错维度 |
| pyarrow schema 向量类型 | `pa.list_(pa.float32())` 不固定维度 | `pa.list_(pa.float32(), 1024)` 或 `lancedb.vector(1024)` | 不固定维度时 LanceDB 无法建 ANN 索引；Phase 22 向量检索需要固定维度 |
| LanceDB 表是否存在检查 | 手写 `try/except` + 路径 glob | `db.open_table()` + catch → `db.create_table(schema=...)` | LanceDB 内置该语义；`exist_ok=True` 也可用 |
| asyncio thread safety | 每个请求新建 SentenceTransformer | 单例 `_model` + `asyncio.to_thread` | SentenceTransformer 线程安全（`@torch.inference_mode()` 修饰，无状态推理） |
| el-table 行内编辑 | 自定义 input + v-if 切换显示/编辑模式 | `el-input v-model="row.field"` 直接嵌入 `el-table-column #default` | 项目已有 TablePreviewEditor.vue 的参考模式 |

**Key insight:** LanceDB 的 `table.delete(where: str)` 使用 SQL-like 字符串过滤，不接受 Python lambda 或 dict 参数。

---

## Common Pitfalls

### Pitfall 1: pandas 未安装导致 to_pandas() 报错

**What goes wrong:** `table.to_pandas()` 内部调用 `self.to_arrow().to_pandas()`，需要 pandas 已安装。本项目 requirements.txt 中无 pandas。
**Why it happens:** 习惯从 LanceDB 示例代码直接 copy，未注意 pandas 依赖。
**How to avoid:** 全部使用 `table.to_arrow().to_pydict()`（返回 `dict[str, list]`）读取数据；不调用 `to_pandas()`。
**Warning signs:** `ModuleNotFoundError: No module named 'pandas'` 在测试或运行时出现。

### Pitfall 2: LanceDB open_table() 在表不存在时抛出 FileNotFoundError

**What goes wrong:** 第一次启动时 `kb_entries` 表不存在，`db.open_table("kb_entries")` 会抛异常。
**Why it happens:** LanceDB 没有"如不存在则创建"的 `open_or_create` API（与 SQLite 不同）。
**How to avoid:** 先 `try: table = db.open_table(...)` except → `table = db.create_table(..., schema=_KB_SCHEMA)`。或者直接 `db.create_table(exist_ok=True)`。
**Warning signs:** 首次启动 KB 功能时 lifespan 报错，但后续重启正常。

### Pitfall 3: bge-m3 encode 阻塞事件循环

**What goes wrong:** 在 `async def` 路由中直接 `await svc.add_entries(...)` 但内部同步调用 `model.encode()`，导致 FastAPI 事件循环被阻塞；所有其他请求暂停直到 encoding 完成（bge-m3 单条约 100-500ms）。
**Why it happens:** `SentenceTransformer.encode()` 是同步方法，不是协程。
**How to avoid:** 用 `await asyncio.to_thread(self._model.encode, texts, ...)` 包裹 encode 调用，放入线程池执行。
**Warning signs:** 入库请求期间其他 API（如 GET /jobs）出现明显延迟。

### Pitfall 4: CTRX_MODELS_DIR 不包含 bge-m3 子目录

**What goes wrong:** `CTRX_MODELS_DIR=/path/to/models`，实际 bge-m3 权重在 `/path/to/models/bge-m3/`，但用户将 `CTRX_MODELS_DIR` 直接指向 bge-m3 目录。
**Why it happens:** 决策 D-02 明确：`SentenceTransformer(str(models_dir / "bge-m3"))`，即 `CTRX_MODELS_DIR` 是父目录，`bge-m3` 是子目录。
**How to avoid:** 文档和错误信息中明确：`CTRX_MODELS_DIR` 应指向包含 `bge-m3/` 子目录的父目录（如 `D:\models`，其中 `D:\models\bge-m3\` 包含模型权重）。
**Warning signs:** `OSError: bge-m3 does not appear to have a file named config.json`。

### Pitfall 5: el-table selection-change 与 reactive kbRows

**What goes wrong:** 用 `kbRows.value = selectionRows` 替换整个数组导致 Vue 追踪丢失；或 `@selection-change` 回调中直接设置 `row.selected = true` 但 `row` 是 Element Plus 内部引用，不等于 `kbRows.value` 中的对象。
**Why it happens:** Element Plus el-table 的 `selection-change` 参数是当前选中行的对象数组，这些对象是 `:data` 绑定数组中的原始对象引用（reactive 数据）。
**How to avoid:** `@selection-change="(sel) => kbRows.value.forEach(r => r.selected = sel.includes(r))"` — 注意 `sel.includes(r)` 基于对象引用比较，正确。或者维护一个独立的 `selectedRows: Set` ref。
**Warning signs:** 勾选/取消勾选后「存入知识库」按钮的 disabled 状态不更新。

### Pitfall 6: sentence-transformers 5.x 参数名变化

**What goes wrong:** sentence-transformers 5.x 将 `sentences` 参数重命名为 `inputs`；调用 `model.encode(sentences=[...])` 可能触发 deprecation warning，但仍可用（`@deprecated_kwargs(sentences="inputs")` 装饰器处理了向后兼容）。
**Why it happens:** 版本 5.x 重构了 API，但保留了 `sentences` 关键字参数的向后兼容。
**How to avoid:** 使用位置参数：`model.encode(texts, convert_to_numpy=True)` 而不是 `model.encode(sentences=texts, ...)`。
**Warning signs:** 启动时出现 `FutureWarning: sentences is deprecated`。

---

## KB API Response Schemas（Claude's Discretion 设计）

### POST /api/v1/kb/entries

**Request:**
```json
{
  "entries": [
    {
      "field_name": "业绩报酬提取方式",
      "field_value": "基金整体资产高水位法",
      "snippet": "原文摘录…",
      "source_job_id": "uuid-string",
      "source_filename": "xxx基金合同.docx"
    }
  ]
}
```

**Response 201（成功）：**
```json
{ "ids": ["uuid1", "uuid2"], "count": 2 }
```

**Response 503（模型未加载，D-07）：**
```json
{ "detail": "知识库功能不可用（bge-m3 模型未加载）" }
```

### GET /api/v1/kb/entries?field_name=业绩报酬提取方式

**Response:**
```json
{
  "items": [
    {
      "id": "uuid-string",
      "field_name": "业绩报酬提取方式",
      "field_value": "基金整体资产高水位法",
      "snippet": "合同摘录文本",
      "source_job_id": "uuid-string",
      "source_filename": "xxx基金合同.docx",
      "created_at": "2026-06-02T10:00:00+00:00"
    }
  ],
  "total": 1
}
```

### DELETE /api/v1/kb/entries/{id}

**Response 204（成功，无 body）**

---

## LanceDB 表 Schema 设计（Claude's Discretion）

```python
# [VERIFIED: lancedb 0.33.0 wheel source lancedb/schema.py]
# lancedb.vector(dim) = pa.list_(pa.float32(), dim)

_KB_SCHEMA = pa.schema([
    pa.field("id", pa.string()),             # UUID，主键（软）
    pa.field("field_name", pa.string()),     # 字段名
    pa.field("field_value", pa.string()),    # 字段值
    pa.field("snippet", pa.string()),        # 原文摘录（空字符串允许）
    pa.field("source_job_id", pa.string()), # 来源 job UUID 字符串
    pa.field("source_filename", pa.string()),# 来源合同文件名
    pa.field("created_at", pa.string()),     # ISO 8601 时间戳字符串
    pa.field("vector", pa.list_(pa.float32(), 1024)),  # bge-m3 1024-dim
])
```

**设计决策：**
- `id` 用 string UUID：方便 `table.delete(f"id = '{id}'")`；LanceDB 无原生主键约束，string 比 int 更安全（无自增冲突）
- `created_at` 用 ISO string 而非 `pa.timestamp()`：避免时区序列化问题；`to_pydict()` 后直接返回字符串给前端
- `vector` 用 `pa.list_(pa.float32(), 1024)` 固定维度：Phase 22 ANN 向量检索要求固定维度

---

## 配置扩展（models_dir）

`config.py` 新增：
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

遵循现有 `data_dir()` 模式：读环境变量，不创建目录（模型目录由用户预置）。

---

## Runtime State Inventory

> Phase 20 是 greenfield 新功能，非 rename/refactor。但涉及持久化存储，记录如下：

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | 无现有 KB 数据（Phase 20 首次创建） | 无迁移，首次 `init_kb_service()` 自动创建表 |
| Live service config | 无（`CTRX_MODELS_DIR` 为新增环境变量，用户手动设置） | 文档说明用户需设置此变量 |
| OS-registered state | 无 | — |
| Secrets/env vars | `CTRX_MODELS_DIR`：新增，指向本地模型目录 | 无 secret，仅本地路径 |
| Build artifacts | 无 | — |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | 后端运行时 | ✓ | 3.11.9 | — |
| `lancedb` | KB-BE-01~05 | ✗（未安装） | — | 需 `pip install lancedb>=0.33.0` |
| `sentence-transformers` | KB-BE-02 | ✗（未安装） | — | 需 `pip install sentence-transformers>=5.5.1` |
| `pyarrow` | lancedb 依赖 | ✗（未安装） | — | 随 lancedb 自动安装，无需单独声明 |
| bge-m3 权重 | KB-BE-02 | 未检查（用户预置） | — | D-06 软降级：模型不存在时 KB 不可用，应用正常启动 |
| `CTRX_MODELS_DIR` 环境变量 | KB-BE-02 模型加载 | 未检查（用户设置） | — | 未设置时 KB 不可用（软降级） |
| Element Plus `el-table` | KB-ENTRY-01~05 | ✓ | ^2.9.0 | — |

**Missing dependencies with no fallback:**
- `lancedb`、`sentence-transformers`：Wave 0 必须 `pip install` 并添加至 `requirements.txt`

**Missing dependencies with fallback:**
- `bge-m3` 模型权重：D-06 软降级，应用可无模型运行，KB 功能 503

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x（现有） |
| Config file | `backend/tests/conftest.py` |
| Quick run command | `pytest backend/tests/test_api_kb.py -x` |
| Full suite command | `pytest backend/tests/ -x -q` |
| Frontend typecheck | `cd frontend && npx vue-tsc --noEmit -p tsconfig.app.json` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KB-BE-01 | `init_kb_service()` 创建 LanceDB 表 | unit | `pytest backend/tests/test_kb_service.py::test_init_creates_table -x` | ❌ Wave 0 |
| KB-BE-02 | bge-m3 加载失败时软降级 | unit | `pytest backend/tests/test_kb_service.py::test_model_unavailable_soft_degrade -x` | ❌ Wave 0 |
| KB-BE-03 | `POST /kb/entries` 入库成功 | integration（TestClient） | `pytest backend/tests/test_api_kb.py::test_post_entries_success -x` | ❌ Wave 0 |
| KB-BE-03 | `POST /kb/entries` 模型不可用返回 503 | integration | `pytest backend/tests/test_api_kb.py::test_post_entries_503_when_no_model -x` | ❌ Wave 0 |
| KB-BE-04 | `GET /kb/entries` 返回列表 | integration | `pytest backend/tests/test_api_kb.py::test_get_entries -x` | ❌ Wave 0 |
| KB-BE-04 | `GET /kb/entries?field_name=X` 过滤 | integration | `pytest backend/tests/test_api_kb.py::test_get_entries_filter -x` | ❌ Wave 0 |
| KB-BE-05 | `DELETE /kb/entries/{id}` 删除成功 | integration | `pytest backend/tests/test_api_kb.py::test_delete_entry -x` | ❌ Wave 0 |
| KB-ENTRY-01~05 | 前端 KB 录入区渲染 | 手动（无 vitest/playwright） | — | N/A（手动验证） |

**测试策略：**
- 后端测试用 `tmp_path` fixture 提供临时 LanceDB 目录，不污染生产数据
- 用 `unittest.mock.patch` mock `KbService._model`（避免真实加载 bge-m3）
- mock encode 返回 `np.zeros((n, 1024), dtype=np.float32)`
- 复用现有 `api_client` + `api_headers` fixture

### Sampling Rate

- **Per task commit:** `pytest backend/tests/test_kb_service.py backend/tests/test_api_kb.py -x -q`
- **Per wave merge:** `pytest backend/tests/ -x -q`
- **Phase gate:** Full suite green + `cd frontend && npx vue-tsc --noEmit -p tsconfig.app.json`

### Wave 0 Gaps

- [ ] `backend/tests/test_kb_service.py` — covers KB-BE-01, KB-BE-02（unit，mock model）
- [ ] `backend/tests/test_api_kb.py` — covers KB-BE-03~05（TestClient integration）
- [ ] `lancedb>=0.33.0` + `sentence-transformers>=5.5.1` 添加至 `requirements.txt`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `lancedb.connect()` + 直接 `create_table()` 每次 | `open_table()` + catch → `create_table(schema=)` | lancedb 0.3+ | 生产安全：首次建表，后续复用 |
| `model.encode(sentences=...)` | `model.encode(inputs=...)` 或位置参数 | sentence-transformers 5.0 | 旧关键字参数触发 DeprecationWarning |
| `table.to_pandas()` | `table.to_arrow().to_pydict()` | — | 避免引入 pandas 依赖 |
| `pa.list_(pa.float32())` 不固定维度 | `pa.list_(pa.float32(), 1024)` 固定维度 | lancedb ANN 索引要求 | Phase 22 向量检索前提 |

**Deprecated/outdated:**
- `db.table_names()`：已标注 deprecated，改用 `db.list_tables()`（lancedb 0.33.0）

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `SentenceTransformer` 实例在多线程并发 `asyncio.to_thread` 调用下线程安全（`@torch.inference_mode()` 修饰，无状态推理） | Pattern 1 / Pitfall 3 | 若非线程安全，需在 `add_entries` 加锁（asyncio.Lock） |
| A2 | bge-m3 本地路径格式为 `CTRX_MODELS_DIR / "bge-m3"`（HuggingFace 标准目录结构，含 config.json + pytorch_model.bin / safetensors） | Pattern 1 | 若目录结构不同（如 ModelScope 特有格式），需调整加载路径或使用 modelscope SDK |
| A3 | `table.to_arrow().to_pydict()` 在 Windows + Python 3.11 上正常工作，无需 pandas | Pattern 1 / Pitfall 1 | pyarrow to_pydict 是原生 pyarrow 方法，不需要 pandas，风险极低 |

---

## Open Questions (RESOLVED)

1. **bge-m3 在 Windows CPU 上的首次加载时间**
   - What we know：bge-m3 是 580M 参数模型，CPU 推理单条约 200-500ms
   - What's unclear：首次 lifespan 预热时加载权重到内存需要多久（可能 10-30 秒）
   - Recommendation：lifespan 中 `init_kb_service()` 用 `asyncio.to_thread` 包裹，加载期间 FastAPI 仍可接受健康检查请求；Electron IPC 在 Python ready 信号前已有超时处理
   - RESOLVED：使用 `asyncio.to_thread(init_kb_service)` 包裹，加载期间不阻塞事件循环；本阶段不新增超时处理（Electron 已有）

2. **`table.to_arrow().to_pydict()` 性能在大量记录时**
   - What we know：本阶段 Phase 20 仅录入少量条目（预计 < 1000 条）；`GET /kb/entries` 为全量返回
   - What's unclear：Phase 21 列表页大量数据时是否需要分页
   - Recommendation：本阶段实现全量返回；Phase 21 需分页时在 `list_entries()` 添加 `offset/limit` 参数（LanceDB 支持 `.scan(limit=N)` 模式）
   - RESOLVED：本阶段实现全量返回，Phase 21 再决定是否分页

3. **kbUnavailable 状态如何初始化**
   - What we know：前端无法在页面加载时知道 KB 是否可用（没有独立的 `/kb/status` 端点）
   - What's unclear：首次渲染 KB 区域时 `kbUnavailable` 应为 `false` 还是通过轮询检测
   - Recommendation：初始 `kbUnavailable = false`；第一次点击「存入知识库」时若返回 503 才设为 `true`；或在 Phase 20 新增 `GET /kb/status` 端点（轻量，返回 `{available: bool}`），前端页面加载时调用一次
   - RESOLVED：初始 `kbUnavailable = false`；不新增 `/kb/status` 端点（Phase 21 决定）；首次 503 响应后设为 `true`

---

## Security Domain

> `security_enforcement` 未在 config.json 中设置为 false，视为启用。本阶段无认证/会话/敏感数据新增，主要注意以下两点：

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | 否（沿用现有 X-API-Key 机制） | `Depends(verify_api_key)`（router 级） |
| V5 Input Validation | 是 | Pydantic `KbEntriesRequest` 自动校验 |
| V6 Cryptography | 否 | 无新增敏感字段 |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LanceDB delete 注入（where 子句拼接） | Tampering | entry_id 是 UUID 字符串格式，调用前用 `uuid.UUID(entry_id)` 验证格式，防止注入 `;DROP TABLE` 类攻击 |
| 超大 entries 请求（DoS） | DoS | 在 `KbEntriesRequest` 添加 `max_items=20`（Field 约束）；单批次限制条目数 |

---

## Sources

### Primary (HIGH confidence)
- `lancedb-0.33.0-cp39-abi3-win_amd64.whl` — 直接从包源码验证：`connect()`, `create_table()`, `open_table()`, `table.add()`, `table.delete()`, `table.to_arrow()`, `lancedb.vector(dim)` API [VERIFIED: PyPI lancedb 0.33.0 wheel]
- `sentence_transformers-5.5.1-py3-none-any.whl` — 直接验证 `SentenceTransformer.__init__` 参数（`model_name_or_path`, `local_files_only`）和 `encode()` 签名 [VERIFIED: PyPI sentence-transformers 5.5.1 wheel]
- `backend/app/main.py` — lifespan 结构 [VERIFIED: codebase]
- `backend/app/config.py` — `data_dir()` 模式 [VERIFIED: codebase]
- `backend/app/extract/path_b_crm.py` — `build_crm_handoff()` crm_field 字符串精确值 [VERIFIED: codebase]
- `frontend/src/components/table/TablePreviewEditor.vue` — el-input inline-edit 模式 [VERIFIED: codebase]
- `frontend/src/composables/usePathB.ts` — composable 结构模式 [VERIFIED: codebase]
- `frontend/src/api/client.ts` — `apiFetch` 模式 [VERIFIED: codebase]
- `pip index versions lancedb / sentence-transformers / pyarrow` — 最新版本确认 [VERIFIED: PyPI registry]

### Secondary (MEDIUM confidence)
- LanceDB 线程安全：`asyncio.to_thread` 用于 CPU 阻塞操作是 FastAPI 标准做法，LanceDB 操作可并发（本地文件写有锁）

### Tertiary (LOW confidence)
- 无

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — 版本通过 pip index versions + wheel 源码直接验证
- Architecture: HIGH — 现有代码模式直接读取，新代码是现有模式的直接扩展
- Pitfalls: HIGH（pandas/open_table/thread）+ MEDIUM（sentence-transformers 5.x API）
- PathB 映射: HIGH — 从 path_b_crm.py 源码直接读取

**Research date:** 2026-06-02
**Valid until:** 2026-07-02（lancedb 快速迭代，建议锁定版本）
