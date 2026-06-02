# Phase 22: RAG 检索与 LLM 注入 - Research

**Researched:** 2026-06-02
**Domain:** 本地 LanceDB 语义检索 + LLM Prompt few-shot 注入（业绩报酬链路）
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### 检索触发范围
- **D-01:** RAG 仅在“业绩报酬提取链路”触发，不扩展到 PathB 全链路其它字段。
- **D-02:** 检索输入优先使用业绩报酬相关原文上下文，不在本阶段引入额外多字段拼接策略。

### Prompt 注入结构
- **D-03:** 采用“按相似度排序的紧凑案例列表”注入 prompt，案例结构固定为：字段名 / 字段值 / 原文摘录。
- **D-04:** 不向模型显式注入相似度分数，仅保留排序结果，减少提示噪声。

### 空库降级
- **D-05:** 知识库为空（或无可用案例）时不注入 few-shot 块，直接走原始提取流程并保证无报错。
- **D-06:** 不注入“空案例占位提示”文本，避免对模型产生无效引导。

### Top-K 配置生效
- **D-07:** Settings 中 `RAG Top-K` 保存后按现有设置机制“重启后端生效”，不做热更新。
- **D-08:** 保持输入约束：整数、范围 1–10；非法值在设置层阻断并给出明确反馈。

### Claude's Discretion
- 检索 API 的内部函数拆分（service 层 vs extract 层）由 planner/researcher 结合现有代码组织决定。
- 注入模板在 `performance_fee.py` 与 `chapter_prompts.py` 的具体拼接位置由实现阶段确定，但须满足 D-03/D-04。

### Deferred Ideas (OUT OF SCOPE)
- PathB 其它字段的 RAG 全面接入（本阶段仅业绩报酬链路）。
- 基于相似度阈值的动态过滤与重排策略。
- 将相似度分数暴露给模型或 UI 的能力。
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| KB-RAG-01 | 提取前按原文摘录做 Top-K 语义检索 | `KbService` 新增 query 接口 + 在 `extract_document` 的 performance_fee 分支前调用检索 [VERIFIED: codebase] |
| KB-RAG-02 | 将检索结果 few-shot 注入 prompt | 在 `performance_fee.py` 构造 user prompt 时拼接“历史案例参考列表”模板 [VERIFIED: codebase] |
| KB-RAG-03 | 空库时不报错并降级无注入 | 空结果/服务不可用返回空列表，prompt 不拼接案例块 [VERIFIED: codebase] |
| KB-RAG-04 | Settings 增加 RAG Top-K，默认 3，范围 1–10，持久化 | 扩展 `AppSettings` + `electron-store` 校验 + `backendChildEnv` 注入环境变量 [VERIFIED: codebase] |
</phase_requirements>

## Summary

当前代码已具备 RAG 的主要地基：LanceDB 表与向量字段存在、入库链路与 API 完整、业绩报酬 LLM 提取点稳定、Settings 具备“保存并重启后端”闭环。[VERIFIED: codebase] 这使得 Phase 22 可以作为“能力拼接”实施，而不是新建子系统。

技术上最稳妥路径是：在 `KbService` 增加“按 query 文本检索 Top-K 记录”方法，`extract_document` 在 `extract_performance_fee_section_llm` 调用前完成检索并把结果传入 `performance_fee.py`，再由 prompt 构造层按 D-03/D-04 生成紧凑 few-shot 块。LanceDB 官方 Python 用法确认 `table.search(...).limit(k).to_list()` 适配该路径。[CITED: https://github.com/lancedb/lancedb/blob/main/python/README.md]

配置侧建议只做最小增量：新增 `ragTopK`（默认 3）并在 Electron 层做范围校验（1–10），通过重启注入到后端进程环境，严格遵循 D-07。FastAPI/Query 的 `ge/le` 数值约束已在现有 KB API 使用，模式可复用。[VERIFIED: codebase][CITED: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/path-params-numeric-validations.md]

**Primary recommendation:** 采用“后端检索服务 + performance_fee prompt 注入 + Electron 持久化重启生效”的最小改动方案，一次性交付 KB-RAG-01~04。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 业绩报酬语义检索（Top-K） | API / Backend | Database / Storage | 检索依赖 LanceDB 表与业务降级逻辑，应在后端统一控制 [VERIFIED: codebase] |
| few-shot prompt 注入 | API / Backend | — | Prompt 构造与 LLM 调用均在 `extract/llm`，不应前端参与 [VERIFIED: codebase] |
| 空库降级 | API / Backend | Database / Storage | 需要在“检索结果为空/不可用”时保证提取主流程继续 [VERIFIED: codebase] |
| RAG Top-K 配置录入与持久化 | Frontend Server (Electron Main) | Browser / Client | Vue 表单采集，electron-store 持久化，主进程重启后端 [VERIFIED: codebase] |
| Top-K 生效到运行时 | Frontend Server (Electron Main) | API / Backend | Electron 通过子进程 env 注入，后端读取配置 [VERIFIED: codebase] |

## Project Constraints (from .cursor/rules/)

- `contract_info/.cursor/rules/auto-commit-push.mdc` 要求默认自动提交并推送；但本阶段规划仍需遵守上游 orchestrator 的提交策略（仅在明确触发提交步骤时执行）。[VERIFIED: codebase]
- 改动涉及 extract/export 时应运行相关 `pytest`。[VERIFIED: codebase]
- 提交信息风格倾向 `fix|feat(scope): why`。[VERIFIED: codebase]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lancedb | 0.33.0 | 本地向量检索与 Top-K 返回 | 当前项目已在用，且官方 search/limit/to_list API 直接满足 Phase 22 [VERIFIED: PyPI `pip index versions lancedb`][CITED: https://github.com/lancedb/lancedb/blob/main/python/README.md] |
| sentence-transformers | 5.5.1 | query 文本向量化（与入库同 embedding 空间） | 现有 KB 入库已使用该模型，复用可避免向量空间不一致 [VERIFIED: PyPI `pip index versions sentence-transformers`][CITED: https://github.com/huggingface/sentence-transformers/blob/main/docs/_static/html/models_en_sentence_embeddings.html] |
| fastapi | 0.136.3 (latest), 0.136.0 (installed) | 配置/参数校验模式参考（ge/le） | 当前 API 框架；已有 Query 边界约束模式可直接沿用 [VERIFIED: PyPI `pip index versions fastapi`][CITED: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/path-params-numeric-validations.md] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| electron-store | 10.1.0 | Settings 持久化 `ragTopK` | 继续沿用现有设置保存体系 [VERIFIED: codebase] |
| pydantic (backend) | 2.x | 请求/响应模型与配置模型边界约束 | 新增 RAG 参数的后端配置解析时使用 [VERIFIED: codebase] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 在后端做检索并注入 | 在前端先检索再传 prompt | 会泄漏提示构造细节到前端，且破坏既有后端抽取边界 [VERIFIED: codebase] |
| 固定 Top-K=3 | 动态阈值+重排 | 超出 D-08 与 Deferred 范围，复杂度高 [VERIFIED: context] |

**Installation:**
```bash
pip install lancedb sentence-transformers fastapi
npm install electron-store
```

**Version verification:** 已用 `pip index versions` 现场核验 lancedb / sentence-transformers / fastapi 当前版本。[VERIFIED: local CLI]

## Architecture Patterns

### System Architecture Diagram
```text
合同 fees 窗口文本
   |
   v
extract_document (pipeline 编排)
   |----> 生成 RAG query 文本 (D-02)
   |----> KbService.search_similar(query, top_k)
   |           |
   |           v
   |      LanceDB 向量检索 -> Top-K 案例
   |                         |
   |                         v
   |----> build few-shot block (字段名/字段值/原文摘录, 仅排序不含分数 D-04)
   |                         |
   v                         v
extract_performance_fee_section_llm(messages with/without rag block)
   |
   v
PathB performance_fee 结果
```

### Recommended Project Structure
```text
backend/app/
├── services/kb_service.py          # 新增检索方法（query -> top-k entries）
├── extract/pipeline.py             # 在 performance_fee 调用前注入检索流程
├── extract/llm/performance_fee.py  # 组装 few-shot prompt 块
└── config.py                       # 读取 RAG Top-K（环境变量）
frontend/src/
├── components/LlmConfigForm.vue    # 新增 RAG Top-K 输入与校验
└── views/SettingsView.vue          # 保存 payload 带 ragTopK
electron/
├── types/ipc.ts                    # AppSettings 扩展 ragTopK
├── store.ts                        # 默认值与范围校验
└── main.ts                         # 注入 RAG_TOP_K 到 backend env
```

### Pattern 1: 检索与 prompt 构造解耦
**What:** 在 service 层只返回结构化案例，在 LLM 模块做文本模板拼接。  
**When to use:** 需要后续替换模板或扩展注入字段时。  
**Example:**
```python
# Source: https://github.com/lancedb/lancedb/blob/main/python/README.md
results = table.search([0.1, 0.3]).limit(20).to_list()
```

### Pattern 2: 参数边界在输入层硬校验
**What:** 对 Top-K 做整数与范围约束（1–10）。  
**When to use:** 任意可导致 prompt 膨胀或性能劣化的用户输入。  
**Example:**
```python
# Source: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/path-params-numeric-validations.md
page_size: int = Query(default=20, ge=1, le=100)
```

### Anti-Patterns to Avoid
- **在 `performance_fee.py` 直接访问 LanceDB:** 破坏职责分层，难测且难复用。
- **把相似度分数注入 prompt:** 与 D-04 冲突，会增加提示噪声。
- **空库时注入“无案例”占位文本:** 与 D-06 冲突，可能干扰模型判断。
- **在前端热更新 Top-K:** 与 D-07 冲突，应走保存后重启。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 向量检索排序与 Top-K | 自写余弦相似度扫描+存储层 | LanceDB `search().limit().to_list()` | 检索/存储一致性与性能边界已由官方实现覆盖 [CITED: https://github.com/lancedb/lancedb/blob/main/python/README.md] |
| 文本 embedding 管线 | 自写 tokenizer+encoder 推理 | sentence-transformers `model.encode(...)` | 模型加载、批量编码、兼容性成熟 [CITED: https://github.com/huggingface/sentence-transformers/blob/main/docs/_static/html/models_en_sentence_embeddings.html] |
| 配置持久化 | 手写 JSON 文件并发读写 | electron-store | 现有工程已稳定使用并带校验入口 [VERIFIED: codebase] |

**Key insight:** 本阶段是“拼装现有能力”，不是“新造基础设施”；手写替代方案只会引入额外维护成本。

## Common Pitfalls

### Pitfall 1: query 与入库向量语义空间不一致
**What goes wrong:** 检索返回看似合法但语义不相关。  
**Why it happens:** 查询侧未复用与入库相同的模型/文本拼接规则。  
**How to avoid:** 查询调用复用 `KbService._build_embedding_text` 语义结构，或至少保持“字段名/字段值/原文摘录”一致模板。  
**Warning signs:** Top-K 命中跨字段、与费用章节毫不相关。

### Pitfall 2: Top-K 未做硬边界
**What goes wrong:** Prompt 过长、响应变慢或超时。  
**Why it happens:** 仅 UI 限制，后端未二次校验。  
**How to avoid:** Electron 保存时 + 后端读取时双重夹逼到 1–10。  
**Warning signs:** 同一合同不同端触发参数漂移。

### Pitfall 3: 空库异常直接中断抽取
**What goes wrong:** KB-RAG-03 失败，用户看到报错。  
**Why it happens:** 把“检索失败”当作“抽取失败”。  
**How to avoid:** 检索层吞吐异常并返回空案例，抽取主流程继续。  
**Warning signs:** 日志出现 KB 异常后 pipeline 中断。

## Code Examples

### LanceDB Top-K 检索（官方）
```python
# Source: https://github.com/lancedb/lancedb/blob/main/python/README.md
import lancedb
db = lancedb.connect('<PATH_TO_LANCEDB_DATASET>')
table = db.open_table('my_table')
results = table.search([0.1, 0.3]).limit(20).to_list()
```

### SentenceTransformer 编码（官方）
```python
# Source: https://github.com/huggingface/sentence-transformers/blob/main/docs/_static/html/models_en_sentence_embeddings.html
sentences = ['This is an example sentence', 'Each sentence is converted']
embeddings = model.encode(sentences)
```

### 现有代码中 Query 边界校验模式
```python
# Source: backend/app/api/routes/kb.py
page_size: int = Query(default=20, ge=1, le=100)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 纯规则 + 通用 LLM 提取 | 检索增强 few-shot（RAG）后再抽取 | 本阶段（Phase 22） | 提升条款模式对齐能力与稳定性 [VERIFIED: roadmap/context] |
| 固定 prompt 无历史案例 | Top-K 历史案例注入（可配置） | 本阶段（Phase 22） | 允许按经验案例约束模型输出 [VERIFIED: requirements] |

**Deprecated/outdated:**
- “在前端拼 prompt 再传后端”不符合当前架构分层，不建议采用。[VERIFIED: codebase]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `table.search(...).to_list()` 返回结构可直接映射 `field_name/field_value/snippet` | Architecture Patterns | 若返回字段命名差异，需要额外映射层 |

## Open Questions (RESOLVED)

1. **RAG query 文本的最终构造粒度 — RESOLVED**
   - Resolution: 统一采用 `fees` window 作为 query 来源，不拼接 `llm_perf_raw` 候选，严格执行 D-02。
   - Planning impact: 已在 `22-02-PLAN.md` 任务 1/2 中固化“仅 fees 路径触发检索 + query 来源为业绩报酬上下文”。

2. **Top-K 配置传递命名 — RESOLVED**
   - Resolution: 采用 `RAG_TOP_K` 作为唯一环境变量键名，并在 `backend/app/config.py` 统一收敛读取。
   - Planning impact: 已在 `22-01-PLAN.md` 任务 2 与 `22-02-PLAN.md` 任务 2 中固化该命名与边界约束（1-10）。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 后端检索与抽取 | ✓ | 3.11.9 | — |
| Node.js | Electron/前端配置链路 | ✓ | v22.22.0 | — |
| npm | 前端依赖与脚本 | ✓ | 11.12.1 | — |
| pytest | Phase 22 回归验证 | ✓ | 9.0.3 | — |
| gsd-sdk CLI | 规划流程辅助 | ✓ | 可执行（路径已解析） | — |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + Node built-in test runner [VERIFIED: local CLI, package.json] |
| Config file | `pytest.ini` |
| Quick run command | `pytest backend/tests/test_kb_service.py backend/tests/test_api_kb.py -q` |
| Full suite command | `pytest -q && npm run test:frontend --prefix frontend && npm run test:router --prefix frontend` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KB-RAG-01 | 提取前触发 Top-K 检索 | unit/integration | `pytest backend/tests/test_extract_pipeline.py -k performance_fee -q` | ❌ Wave 0（需新增 RAG 注入专测） |
| KB-RAG-02 | few-shot 注入格式正确 | unit | `pytest backend/tests/test_extract_pipeline.py -k rag -q` | ❌ Wave 0 |
| KB-RAG-03 | 空库降级不报错 | unit | `pytest backend/tests/test_kb_service.py backend/tests/test_extract_pipeline.py -k \"empty or unavailable\" -q` | ⚠️ 部分存在（`test_kb_service.py` 仅覆盖模型不可用） |
| KB-RAG-04 | Top-K 设置项持久化并重启生效 | frontend/electron | `npm run test:frontend --prefix frontend && npm run test:electron --prefix frontend` | ⚠️ 部分存在（settings 基础测试已存在，缺 ragTopK 断言） |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/test_kb_service.py backend/tests/test_api_kb.py -q`
- **Per wave merge:** `pytest -q` + 前端 `test:frontend`/`test:router`
- **Phase gate:** 全量测试绿灯后再进入 `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_rag_prompt_injection.py` — 覆盖 KB-RAG-01/02/03
- [ ] `frontend/tests/frontend/llm-config-form.test.mjs` 扩展 `ragTopK` 字段断言 — 覆盖 KB-RAG-04
- [ ] `electron/tests/settings-rag-topk.test.mjs` — 覆盖 store 校验与默认值

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | 复用现有 API Key 保护 `/api/v1/*` 路由 [VERIFIED: codebase] |
| V3 Session Management | no | 桌面本地应用，无服务端 session |
| V4 Access Control | yes | 路由层依赖 `verify_api_key` [VERIFIED: codebase] |
| V5 Input Validation | yes | Pydantic/FastAPI 参数约束 + Electron 表单校验 [VERIFIED: codebase] |
| V6 Cryptography | no | 本阶段不新增加密需求 |

### Known Threat Patterns for FastAPI + LanceDB + Electron

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt 注入污染（恶意 snippet 入库） | Tampering | 注入模板仅用结构化字段，长度限制与字符清洗 |
| 配置越界（Top-K 超范围） | Denial of Service | 1–10 双层校验（store + backend） |
| 未授权 KB API 调用 | Elevation of Privilege | 保持 `verify_api_key` 依赖不移除 |

## Sources

### Primary (HIGH confidence)
- Codebase inspection (`backend/app/services/kb_service.py`, `backend/app/extract/pipeline.py`, `backend/app/extract/llm/performance_fee.py`, `electron/store.ts`, `frontend/src/views/SettingsView.vue`)
- PyPI CLI verification (`python -m pip index versions lancedb/sentence-transformers/fastapi`)
- Context7 docs:
  - https://github.com/lancedb/lancedb/blob/main/python/README.md
  - https://github.com/huggingface/sentence-transformers/blob/main/docs/_static/html/models_en_sentence_embeddings.html
  - https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/path-params-numeric-validations.md

### Secondary (MEDIUM confidence)
- None.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - 本地版本与官方文档均已核验
- Architecture: HIGH - 注入点与配置链路在代码中明确存在
- Pitfalls: MEDIUM - 主要基于现有实现推断，尚需执行阶段测试验证

**Research date:** 2026-06-02  
**Valid until:** 2026-07-02
