# Phase 22 Validation

**Phase:** 22 - RAG 检索与 LLM 注入  
**Updated:** 2026-06-02  
**Status:** READY

## Validation Architecture Baseline

本文件基于 `22-RESEARCH.md` 的 **Validation Architecture** 建立，作为 Phase 22 的 Nyquist 门禁输入。

- Frontend test runner: Node built-in test runner
- Backend test runner: pytest
- Quick command: `pytest backend/tests/test_rag_prompt_injection.py -q`
- Full gate command: `node --test electron/tests/settings-rag-topk.test.mjs && pytest backend/tests/test_rag_prompt_injection.py -q && npm run test:frontend --prefix frontend -- llm-config-form.test.mjs`

## Nyquist 8a-8d Checks

### 8a — Requirement-to-Test Mapping

| Requirement | Validation Target | Command | Expected Result |
|-------------|-------------------|---------|-----------------|
| KB-RAG-01 | fees 分支 Top-K 检索触发与传递 | `pytest backend/tests/test_rag_prompt_injection.py -q` | 仅 performance_fee 链路触发检索，Top-K 上限生效 |
| KB-RAG-02 | few-shot 注入结构（字段名/字段值/原文摘录） | `pytest backend/tests/test_rag_prompt_injection.py -q` | prompt 注入块结构固定且有序 |
| KB-RAG-03 | 空库/不可用降级无报错 | `pytest backend/tests/test_rag_prompt_injection.py -q` | 空案例时流程继续，不注入占位文本 |
| KB-RAG-04 | Settings Top-K 默认值/范围/持久化与重启生效 | `node --test electron/tests/settings-rag-topk.test.mjs && npm run test:frontend --prefix frontend -- llm-config-form.test.mjs` | 默认值 3、范围 1-10、保存后重启链路带新值 |

### 8b — Automated Coverage Gate

- 必须存在并纳入执行的测试文件：
  - `backend/tests/test_rag_prompt_injection.py`
  - `electron/tests/settings-rag-topk.test.mjs`
  - `frontend/tests/frontend/llm-config-form.test.mjs`
- 命令必须覆盖三层链路：Electron 配置、Backend 检索注入、Frontend 表单约束。

### 8c — Wave Sampling Strategy

- Per task commit:
  - `pytest backend/tests/test_rag_prompt_injection.py -q`
  - `node --test electron/tests/settings-rag-topk.test.mjs`
- Per wave merge:
  - `pytest backend/tests/test_rag_prompt_injection.py -q && npm run test:frontend --prefix frontend -- llm-config-form.test.mjs`
- Phase gate:
  - `node --test electron/tests/settings-rag-topk.test.mjs && pytest backend/tests/test_rag_prompt_injection.py -q && npm run test:frontend --prefix frontend -- llm-config-form.test.mjs`

### 8d — Exit Criteria

Phase 22 通过验证需同时满足：

1. 8a 中 KB-RAG-01~04 均有自动化命令覆盖并可重复通过。  
2. 8b 列出的测试文件全部存在并被执行。  
3. 8c 的 phase gate 命令全绿，无 blocker。  
4. D-01~D-08 对应行为全部可由自动化断言映射验证（尤其 D-01/D-05/D-07/D-08）。

## Notes

- 本文件用于修复“`22-VALIDATION.md` 缺失导致 Nyquist gate 阻断”的 checker blocker。
- 若后续测试命令或文件名调整，需同步更新本文件以保持 gate 可执行性。
