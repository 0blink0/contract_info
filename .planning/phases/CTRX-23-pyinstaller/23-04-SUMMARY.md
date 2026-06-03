# Phase 23-04 Summary — RAG 烟测与字段级增强

**Completed:** 2026-06-03  
**Plan:** 23-04-PLAN.md（烟测清单与验收）  
**Requirements satisfied:** KB-PKG-03

---

## What Was Done

### 烟测验收（KB-PKG-03）

人工烟测全链路通过：

- PathB 录入 → embedding 生成 → LanceDB 持久化 ✓
- 语义检索 → RAG prompt 注入 → LLM 提取 ✓
- 前端 RAG 召回状态 alert 展示 ✓
- `rag_warnings` 字段经 JSON 查看确认正确 ✓

### 超出原计划的增强（本 session 新增）

在烟测过程中发现 RAG 对字段判断影响有限，进行了以下架构升级：

#### 1. 字段级并行 RAG 召回（`pipeline.py`、`kb_service.py`）

- 从单次文档级查询改为对 5 个 CRM 字段各发一次向量查询（并行）
- `search_similar_entries` 增加 `field_name` 参数，做向量空间和 SQL 双重过滤
- 每字段 top-k 结果各自精准，`kb_index` 按 `field_name` 分组后传下游

#### 2. KB Few-Shot LLM 字段提取（`kb_field_extract.py`，新文件）

- 新增 `extract_crm_fields_with_kb()`：为每个有 KB 案例的字段：
  1. 用 KB 摘录 bigram 在当前合同里定位最相似段落
  2. 以相似段落 + KB few-shot 案例调用 LLM → 输出字段值
  3. 相似段落同时作为该字段的 `snippet`（摘录）展示
- 与 `extract_performance_fee_section_llm` 并行执行
- 结果存入 `kb_field_extractions` 透传至 `build_crm_handoff`

#### 3. `build_crm_handoff` 优先级重构（`path_b_crm.py`）

- 各 CRM 字段提取顺序：**KB LLM → 原 regex 规则兜底**
- `_kb_matches` 改为子集判断（"赎回、基金清算" vs "分红、赎回、基金清算" → 正确标记缺失）
- `_rag_note` 增加 `· 知识库含「分红」，建议核查` 精确缺失提示

#### 4. 模型加载等待（`pipeline.py`）

- 触发提取时模型仍在加载 → 后端每 5s 轮询，最多等 300s（算入提取时间）
- 超时才降级报警，不再静默跳过

#### 5. 全局 RAG 状态指示（前端）

- 新增 `/kb/status` 端点（`model_loaded`, `entry_count`）
- `useKbStatus.ts` 模块级单例，应用启动即轮询（10s 间隔，就绪后停止）
- `AppLayout` 侧边栏「知识库配置」旁常驻状态点：黄色闪烁=加载中，绿色=就绪
- `KbConfigView` 顶部 banner 共享同一份轮询

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/kb_service.py` | `search_similar_entries` 加 `field_name` 参数与 SQL 过滤 |
| `backend/app/extract/pipeline.py` | 字段级并行召回、模型加载等待、`extract_crm_fields_with_kb` 并行 |
| `backend/app/extract/llm/kb_field_extract.py` | **新建**：KB few-shot LLM 字段提取 |
| `backend/app/extract/path_b_crm.py` | `_find_similar_passage`、`_kb_llm`、字段优先级重构、`_kb_matches` 子集判断 |
| `backend/app/extract/path_b_assemble.py` | 存 `kb_field_extractions` |
| `backend/app/extract/rules/path_b_rules.py` | 透传 `kb_field_extractions` |
| `backend/app/api/routes/kb.py` | 新增 `GET /kb/status` |
| `frontend/src/api/kb.ts` | `getKbStatus()` + `KbStatusResponse` |
| `frontend/src/composables/useKbStatus.ts` | **新建**：单例轮询 composable |
| `frontend/src/layouts/AppLayout.vue` | 侧边栏状态点 |
| `frontend/src/views/KbConfigView.vue` | banner 改用 `useKbStatus` 共享 |

---

## Phase 23 Complete ✓

所有 4 个计划执行完毕，KB-PKG-01/02/03 全部满足。
