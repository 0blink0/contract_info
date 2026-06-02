# Phase 20: 知识库数据层 + PathB 录入 UI - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段交付两个并行部分：

1. **后端知识库数据层（KB-BE-01~05）**
   - 应用启动时自动初始化 LanceDB 本地向量表（`data_dir() / "kb"`）
   - 加载 bge-m3 模型（从 CTRX_MODELS_DIR 路径读取本地缓存），启动时预热
   - 5 个 CRUD 端点：`POST /kb/entries`（批量入库 + embedding）、`GET /kb/entries`（列表 + 过滤）、`DELETE /kb/entries/{id}`

2. **前端 PathB 录入 UI（KB-ENTRY-01~05）**
   - 在 `PathBDetail.vue` 底部追加 3 列 4 行可编辑录入表格（字段名 / 字段值 / 原文摘录）
   - 页面加载时自动预填当前解析结果；字段名列不可编辑；字段值与原文摘录可自由编辑
   - 每行左侧复选框；「存入知识库」按钮批量提交勾选行至 `POST /kb/entries`

**不在本阶段：**
- 知识库配置页 UI（Phase 21）
- RAG 检索注入（Phase 22）
- PyInstaller 打包兼容（Phase 23）
- 左侧菜单「知识库配置」导航入口（Phase 21）

</domain>

<decisions>
## Implementation Decisions

### Embedding 模型与向量

- **D-01:** 使用 **bge-m3**（`BAAI/bge-m3`），不使用原计划的 `paraphrase-multilingual-MiniLM-L12-v2`。bge-m3 对中文语义表示更强。
- **D-02:** 模型从 **ModelScope**（国内源）下载，离线缓存到本地路径。运行时通过 **`CTRX_MODELS_DIR`** 环境变量指向缓存目录，使用 `sentence-transformers` 库从本地路径加载（`SentenceTransformer(str(models_dir / "bge-m3"))`）。
- **D-03:** LanceDB 向量列维度固定为 **1024**（bge-m3 原生输出维度），建表时硬编码此值。
- **D-04:** 入库前对 embedding 输入文本**截断至约 512 字符**（避免超出 bge-m3 有效窗口导致静默截断）。
- **D-05:** Embedding 输入文本格式：拼接三个字段：
  ```
  字段名：{field_name}
  字段值：{field_value}
  原文摘录：{snippet}
  ```
  截断后传入模型。

### 启动失败模式

- **D-06:** **软降级**策略——若 bge-m3 模型加载失败（路径不存在、权重损坏等），应用正常启动，其余功能（抽取、导出、校验）不受影响；KB 功能进入"不可用"状态。
- **D-07:** KB 不可用时：
  - 后端 `POST /kb/entries` 返回 **503**（服务不可用），附带说明文案。
  - 前端 PathBDetail 中 KB 录入区顶部显示橙色 **`el-alert`** 警告：「知识库功能不可用（模型未加载）。」；「存入知识库」按钮 disabled。
  - KB 录入表格仍渲染，但所有输入禁用（仅供参考预填数据）。

### KB 录入区可见性

- **D-08:** PathB 数据不可用时（`available === false` 或 job 尚未处理），**完全隐藏** KB 录入区（与现有 `v-if="available"` 守卫一致，不增加空状态设计）。
- **D-09:** PathB 数据可用后，KB 录入区始终可见（即使模型未加载，见 D-07）。
- **D-10:** 「存入知识库」提交时**允许 `原文摘录` 为空**——无客户端强验证；后端接受空字符串（embedding 仍基于字段名+字段值生成）。

### Claude's Discretion

- LanceDB 表结构（字段名、列类型）由 researcher/planner 根据 KB-BE 要求和 bge-m3 1024 维度确定。
- `POST /kb/entries` 批量入库的并发模式（asyncio vs 线程池）由 planner 确定，保持与现有 lifespan/FastAPI 模式一致。
- PathB → KB 4 行预填映射（具体取 `crm_handoff` 中哪几条 `crm_field` 的 `suggested_value` 和 `snippet`）由 researcher 从代码中查明，对应 4 个固定字段：业绩报酬提取方式 / 业绩基准类型 / 门槛净值类型 / 提取时点。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求规格

- `contract_info/.planning/REQUIREMENTS.md` — KB-BE-01~05（后端数据层）、KB-ENTRY-01~05（PathB 录入 UI）的完整需求描述与验收标准
- `contract_info/.planning/ROADMAP.md` — Phase 20 目标与 Success Criteria（4 条）

### 后端集成点

- `contract_info/backend/app/config.py` — `data_dir()` 模式（CTRX_DATA_DIR）；新增 `CTRX_MODELS_DIR` 遵循相同模式
- `contract_info/backend/app/main.py` — `lifespan()` 上下文管理器；LanceDB 初始化与 bge-m3 预热 hook 挂入此处
- `contract_info/backend/app/api/routes/` — 现有路由文件模式（health.py, jobs.py, upload.py）；新建 `kb.py` 遵循相同结构并在 main.py 注册

### 前端集成点

- `contract_info/frontend/src/components/pathb/PathBDetail.vue` — KB 录入表格追加在此组件底部；`available` prop 控制整体显示
- `contract_info/frontend/src/composables/usePathB.ts` — `useKbEntry.ts` composable 的参考模式（ref/computed/async load 结构）
- `contract_info/frontend/src/composables/useJobDetailContext.ts` — job 状态 provide/inject 模式（KB 入库成功通知可复用）

### 现有抽取参考（RAG 注入点，Phase 22 用，此阶段仅阅读了解）

- `contract_info/backend/app/extract/llm/performance_fee.py` — KB-RAG-01 注入点（Phase 22 修改，此阶段不改动）
- `contract_info/backend/app/extract/llm/chapter_prompts.py` — 同上

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`PathBDetail.vue`** — KB 录入表格直接追加在 `<div class="path-b-detail">` 最底部；沿用 `.section-table` 类名和 `el-table size="small" stripe border` 模式
- **`usePathB.ts`** — `useKbEntry(jobId: Ref<string | null>)` composable 参考此形态：`loading ref`、`async submit()`、`ElMessage.success/error` 反馈
- **`el-table` + `el-table-column`** — 全项目统一表格组件，KB 录入表格用 `el-input` 嵌入单元格（参考 `TablePreviewEditor.vue` 的 inline edit 模式）

### Established Patterns

- **`data_dir() / "subdir"`** — 所有可写路径（uploads/exports/db）均通过此函数解析；LanceDB 存储路径用 `data_dir() / "kb"`
- **`lifespan()` 启动钩子** — `backend/app/main.py` 中的 `@asynccontextmanager async def lifespan(app)`；初始化代码在 `yield` 前执行
- **`async FastAPI routes`** — 所有路由函数 `async def`；I/O 密集型操作（embedding 生成）用 `asyncio.to_thread` 或 `run_in_executor` 避免阻塞
- **`ElMessage.success/error`** — 操作反馈统一方式；「已存入 {N} 条」用 `ElMessage.success`

### Integration Points

- 新建 `backend/app/api/routes/kb.py` → 在 `main.py` 注册 router：`app.include_router(kb.router, prefix="/kb")`
- 新建 `backend/app/services/kb_service.py`（或 `kb/`目录）：封装 LanceDB 初始化、embedding 生成、CRUD 操作
- 前端新建 `frontend/src/api/kb.ts`（API client）+ `frontend/src/composables/useKbEntry.ts`

</code_context>

<specifics>
## Specific Ideas

- **bge-m3 from ModelScope**: 用 modelscope SDK (`from modelscope import snapshot_download`) 下载，或直接从 ModelScope 镜像拉取到本地目录，用 `CTRX_MODELS_DIR` 指向。
- **向量维度 1024**: LanceDB 建表时 `pa.list_(pa.float32(), 1024)` 硬编码，不从模型动态获取。
- **截断 512 字符**: 在 embedding 调用前 `text[:512]`，简单粗暴，无需 tokenizer 感知截断。
- **模型预热**: `lifespan` 中用 `model.encode(["预热"])` 发一次空推理，确保模型权重全加载到内存。

</specifics>

<deferred>
## Deferred Ideas

- Phase 21: 左侧菜单「知识库配置」入口与历史案例列表页
- Phase 22: RAG 检索 Top-K 注入 performance_fee/chapter_prompts prompt
- Phase 23: PyInstaller 打包 bge-m3 模型权重至 extraResources；SENTENCE_TRANSFORMERS_HOME / CTRX_MODELS_DIR 路径绑定

</deferred>

---

*Phase: 20-知识库数据层-PathB录入UI*
*Context gathered: 2026-06-02*
