# Phase 21 Validation

**Phase:** 21 - 知识库配置页 UI  
**Updated:** 2026-06-02  
**Status:** READY

## Validation Architecture Baseline

本文件基于 `21-RESEARCH.md` 的 **Validation Architecture** 建立，作为 Phase 21 的 Nyquist 门禁输入。

- Frontend test runner: Node built-in test runner
- Backend test runner: pytest
- Quick command: `npm run test:router --prefix frontend`
- Full gate command: `npm run test:router --prefix frontend && npm run test:frontend --prefix frontend && pytest backend/tests/test_api_kb.py -q`

## Nyquist 8a-8d Checks

### 8a — Requirement-to-Test Mapping

| Requirement | Validation Target | Command | Expected Result |
|-------------|-------------------|---------|-----------------|
| KB-UI-01 | 导航入口与路由可达 | `npm run test:router --prefix frontend` | `/kb-config` 路由与菜单位置断言通过 |
| KB-UI-02 | 列表展示与分页控件 | `npm run test:frontend --prefix frontend` | 表格列与分页控件断言通过 |
| KB-UI-03 | 字段名即时过滤 | `npm run test:frontend --prefix frontend` | `field_name` 防抖过滤断言通过 |
| KB-UI-04 | 删除确认与刷新 | `npm run test:frontend --prefix frontend && pytest backend/tests/test_api_kb.py -q` | 删除确认文案、刷新上下文与 API 契约断言通过 |

### 8b — Automated Coverage Gate

- 必须存在并纳入执行的测试文件：
  - `frontend/tests/router/kb-config-nav.test.mjs`
  - `frontend/tests/frontend/kb-config-view.test.mjs`
  - `frontend/tests/frontend/kb-config-filter.test.mjs`
  - `frontend/tests/frontend/kb-config-delete.test.mjs`
- 后端回归继续使用：`backend/tests/test_api_kb.py`

### 8c — Wave Sampling Strategy

- Per task commit:
  - `npm run test:router --prefix frontend`
- Per wave merge:
  - `npm run test:frontend --prefix frontend && pytest backend/tests/test_api_kb.py -q`
- Phase gate:
  - `npm run test:router --prefix frontend && npm run test:frontend --prefix frontend && pytest backend/tests/test_api_kb.py -q`

### 8d — Exit Criteria

Phase 21 通过验证需同时满足：

1. 上述 8a 映射中的四个需求均有自动化命令覆盖并可重复通过。
2. 8b 列出的前端测试文件全部存在且纳入测试脚本。
3. 8c 的 phase gate 命令全绿，无新增 blocker。
4. 删除失败场景可保留后端错误详情并附中文提示（与 D-06 对齐）。

## Notes

- 本文件用于修复“`21-VALIDATION.md` 缺失导致 Nyquist 门禁前置失败”的阻断问题。
- 若后续变更测试命令或测试文件名，需同步更新本文件以保持 gate 可执行性。
