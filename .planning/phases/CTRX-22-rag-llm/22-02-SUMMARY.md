---
phase: 22-rag-llm
plan: "02"
subsystem: api
tags: [rag, lancedb, llm, extraction, prompt]
requires:
  - phase: 22-rag-llm
    provides: 22-01 的 RAG Top-K 配置与环境变量注入
provides:
  - 业绩报酬链路 Top-K 语义检索接入
  - few-shot 历史案例注入模板与空库静默降级
  - RAG 注入自动化回归测试
affects: [phase-22, performance-fee, kb-service, pipeline]
tech-stack:
  added: []
  patterns: [Pipeline 非阻塞降级, Prompt 模板化注入, Top-K 边界约束]
key-files:
  created: [backend/tests/test_rag_prompt_injection.py]
  modified:
    - backend/app/config.py
    - backend/app/services/kb_service.py
    - backend/app/extract/pipeline.py
    - backend/app/extract/llm/chapter_prompts.py
    - backend/app/extract/llm/performance_fee.py
key-decisions:
  - "仅在 fees 分支触发 KB 检索，未扩散到其它 PathB 字段链路"
  - "RAG query 只使用业绩报酬上下文，并在运行时将 Top-K 夹逼到 1-10"
  - "few-shot 注入块固定为字段名/字段值/原文摘录，不暴露相似度分数"
patterns-established:
  - "Pattern: 失败检索记录 warning 并降级为空案例，主提取流程不中断"
  - "Pattern: prompt 注入使用可复用的历史案例构造函数，空案例不拼接占位文本"
requirements-completed: [KB-RAG-01, KB-RAG-02, KB-RAG-03]
duration: 6min
completed: 2026-06-02
---

# Phase 22 Plan 02: 后端检索与 few-shot 注入 Summary

**业绩报酬提取前已接入 LanceDB Top-K 语义检索，并将结构化历史案例稳定注入 prompt，空库与检索异常场景均可静默降级继续抽取。**

## Performance

- **Duration:** 6 min
- **Started:** 2026-06-02T10:10:00Z
- **Completed:** 2026-06-02T10:15:46Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- 新增 TDD 回归测试，先失败后通过，覆盖 fees-only 检索触发、Top-K 注入与空库降级。
- 在 `KbService` 增加 `search_similar_entries`，复用 embedding 语义模板并返回结构化案例。
- 在 pipeline 仅对 performance_fee 分支执行检索并将 `rag_cases` 传入下游，失败时仅追加 warning。
- 在 prompt 层加入“历史案例参考”模板，固定字段三元组并显式避免 score/相似度文本泄漏。

## Task Commits

Each task was committed atomically:

1. **Task 1: 补齐 RAG 注入行为测试（先测后改）** - `1f8abd7` (test)
2. **Task 2: 实现 kb_service 检索与 pipeline 注入编排** - `4cbe6db` (feat)
3. **Task 3: 实现 few-shot prompt 注入模板** - `f64685d` (feat)

## Files Created/Modified

- `backend/tests/test_rag_prompt_injection.py` - 新增 RAG 注入与空库降级测试
- `backend/app/config.py` - 增加 `rag_top_k` 配置默认值
- `backend/app/services/kb_service.py` - 增加 `search_similar_entries` 检索接口
- `backend/app/extract/pipeline.py` - fees 分支接入检索与降级 warning
- `backend/app/extract/llm/chapter_prompts.py` - 增加历史案例 prompt 片段生成函数
- `backend/app/extract/llm/performance_fee.py` - 注入可选 `rag_cases` 并拼接 few-shot 块

## Decisions Made

- 保持 D-01：只在业绩报酬提取链路触发检索，订阅相关链路不触发。
- 保持 D-02：query 仅来自 fees window，不引入跨字段拼接。
- 保持 D-03/D-04：注入块仅三元组文本，不输出分数。
- 保持 D-05/D-06：空案例时不拼接任何占位文案。

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Task 2 首轮实现未截断服务返回列表，测试暴露 Top-K 透传问题；已在 pipeline 端追加 `[:rag_top_k]` 限制并复测通过。

## Known Stubs

None.

## Self-Check: PASSED

- Summary 文件存在且路径正确。
- Task 提交哈希 `1f8abd7`、`4cbe6db`、`f64685d` 均可在 git 历史中检索到。
