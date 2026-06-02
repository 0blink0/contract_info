# Phase 20: 知识库数据层 + PathB 录入 UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 20-知识库数据层-PathB录入UI
**Areas discussed:** Embedding text, Startup failure mode, KB section visibility

---

## Embedding Text

| Option | Description | Selected |
|--------|-------------|----------|
| 原文摘录 only | Embed only the 原文摘录 field (matches KB-RAG-01 literal phrasing) | |
| 字段名 + 字段値 + 原文摘录 | Concatenate all three fields for richer semantic context | ✓ |
| 字段名 + 原文摘录 | Middle ground: field category + excerpt, no value label | |

**User's choice:** 字段名 + 字段値 + 原文摘录

---

| Option | Description | Selected |
|--------|-------------|----------|
| Truncate to ~512 chars | Cap concatenated input before embedding for stability | ✓ |
| No truncation | Pass full text as-is | |

**User's choice:** Truncate to ~512 chars

---

| Option | Description | Selected |
|--------|-------------|----------|
| Local path via sentence-transformers | Pre-downloaded from ModelScope, loaded from CTRX_MODELS_DIR | ✓ |
| FlagEmbedding library | BGE native SDK, new dependency | |
| Auto-download on first startup | Download from ModelScope at runtime if not found locally | |

**User's choice:** Local path via sentence-transformers

**Notes:** User specified switching model from `paraphrase-multilingual-MiniLM-L12-v2` to **bge-m3** (BAAI/bge-m3), downloaded from ModelScope (国内源). User also noted bge-m3 vector dimension is 1024 — this locks LanceDB schema to `FLOAT[1024]`.

---

## Startup Failure Mode

| Option | Description | Selected |
|--------|-------------|----------|
| Soft degradation | App starts; KB features disabled with warning if model fails | ✓ |
| Hard fail | App refuses to start if model can't load | |

**User's choice:** Soft degradation

---

| Option | Description | Selected |
|--------|-------------|----------|
| el-alert warning above entry table | Orange el-alert shown; button disabled; table rendered read-only | ✓ |
| Hide KB section entirely | If model failed, hide entire KB section | |

**User's choice:** el-alert warning above the entry table

**Notes:** "存入知识库" button disabled; table still shown so user can reference pre-filled values.

---

## KB Section Visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Hide KB section entirely | v-if="available" guard — consistent with existing PathBDetail pattern | ✓ |
| Show greyed-out table with placeholder rows | Show structure but disable all inputs | |

**User's choice:** Hide KB section entirely (when PathB unavailable)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Allow empty 原文摘录 | No client-side validation required | ✓ |
| Require non-empty 原文摘录 | Checkbox only checkable when excerpt present | |

**User's choice:** Allow empty 原文摘录

---

## Claude's Discretion

- LanceDB table schema column names and types (beyond the locked 1024-dim vector)
- POST /kb/entries async concurrency model (asyncio.to_thread vs run_in_executor)
- PathB → 4 KB row pre-fill mapping (researcher reads crm_handoff structure from code)
- Exact CTRX_MODELS_DIR env var name and config.py integration pattern

## Deferred Ideas

- Phase 21: 左侧菜单「知识库配置」入口，历史案例列表查看/过滤/删除
- Phase 22: RAG 检索 Top-K 注入 performance_fee/chapter_prompts prompt
- Phase 23: PyInstaller 打包 bge-m3 模型权重至 extraResources
