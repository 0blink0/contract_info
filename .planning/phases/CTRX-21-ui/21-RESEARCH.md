# Phase 21: 知识库配置页 UI - Research

**Researched:** 2026-06-02  
**Domain:** Vue 3 + Element Plus 知识库配置页（导航/列表/过滤/删除）  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 「知识库配置」菜单项放在左侧「文件列表」下方、「系统设置」上方，作为业务操作入口而非系统级配置入口。
- **D-02:** 菜单高亮遵循现有 `AppLayout.vue` 的 `default-active + router` 机制，不改变现有「文件详情」子菜单展开行为。
- **D-03:** 采用推荐中间方案：首屏服务端分页加载，筛选时继续走服务端查询，不做一次性全量拉取。
- **D-04:** 本阶段搜索范围锁定为“字段名过滤”（严格对齐 KB-UI-03）；输入采用防抖即时查询，不要求用户按回车触发。
- **D-05:** 删除后保持当前筛选条件与当前页面上下文，刷新当前查询结果，不重置筛选器。
- **D-06:** 删除确认文案采用“稳妥明确”风格，明确提示“删除后不可恢复”；失败提示保留后端错误详情并补充简短中文提示。

### Claude's Discretion
- 列表采用分页还是虚拟滚动的具体技术选型，由 planner/researcher 结合数据量与现有组件栈决定。
- 防抖时长、请求取消策略（如 abort controller）由实现阶段按现有 API 客户端模式决定。

### Deferred Ideas (OUT OF SCOPE)
- 多字段搜索（字段名 + 字段值 + 来源合同）作为后续能力单独规划，不并入 Phase 21。
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| KB-UI-01 | 左侧菜单新增「知识库配置」菜单项并进入列表页 | 明确 `AppLayout.vue` 的菜单插入位和 `router/index.ts` 的路由注册模式 |
| KB-UI-02 | 列表展示历史案例并支持分页或虚拟滚动 | 推荐 `el-table + el-pagination` 主路径，`el-table-v2` 作为大数据备选 |
| KB-UI-03 | 按字段名过滤/搜索 | 复用 `GET /kb/entries?field_name=` 契约并补防抖与请求清理 |
| KB-UI-04 | 删除单条案例并二次确认，删除后即时刷新 | 复用项目“确认后删除 + refresh”范式，保持筛选和页码上下文 |
</phase_requirements>

## Summary

Phase 21 的核心不是新技术引入，而是把已有能力正确编排：导航、路由、表格、过滤、删除流程都已在仓库中存在成熟模式。[VERIFIED: `frontend/src/layouts/AppLayout.vue`, `frontend/src/router/index.ts`, `frontend/src/views/FileListView.vue`, `frontend/src/api/kb.ts`]

规划上的关键事实：当前后端 `GET /kb/entries` 只支持 `field_name`，无分页参数；`KbService.list_entries` 也仅做全量遍历+过滤。若执行 D-03（服务端分页），Phase 21 计划必须包含 KB API 分页契约扩展，而不仅是前端页面拼装。[VERIFIED: `backend/app/api/routes/kb.py`, `backend/app/services/kb_service.py`]

在 UI 选型上，Element Plus 已覆盖表格、分页、确认交互；结合本项目现有 `node --test` 前端测试基线，推荐优先落地 `el-table + el-pagination`，将虚拟滚动保留为后续性能优化选项。[CITED: https://element-plus.org/en-US/component/table] [CITED: https://element-plus.org/en-US/component/pagination] [CITED: https://element-plus.org/en-US/component/menu]

**Primary recommendation:** 以“服务端分页 + 字段名防抖筛选 + 删除后保持上下文刷新”为主线，拆成 API 契约、页面实现、测试补齐三条并行可验证任务链。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 左侧菜单新增「知识库配置」入口 | Frontend (Layout + Router) | — | 菜单项与高亮由 `el-menu` + vue-router 驱动 |
| 历史案例列表展示 | Frontend View | API / Backend | 前端负责渲染，后端负责提供分页后的数据切片 |
| 字段名过滤 | API / Backend | Frontend | 过滤条件由前端输入，过滤执行应在服务端以满足 D-03 |
| 删除二次确认 | Frontend | API / Backend | 确认交互在前端，删除动作在后端 |
| 删除后上下文保持刷新 | Frontend | API / Backend | 前端保留 query/page 状态后重拉，后端返回最新列表 |

## Project Constraints (from .cursor/rules/)

- 未发现 `.cursor/rules/` 目录下的规则文件，本阶段无额外项目规则注入项。[VERIFIED: glob `.cursor/rules/**/*.md` returned 0 files]
- 未发现项目级 `.claude/skills/` 或 `.agents/skills/`，无需附加技能约束适配。[VERIFIED: glob `.claude/skills/**/SKILL.md` and `.agents/skills/**/SKILL.md` returned 0 files]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vue | project: `^3.5.13`; latest: `3.5.35` (2026-05-27) | 页面状态与交互 | 现有前端主框架，且已支持 watcher cleanup 模式 |
| vue-router | project: `^4.6.4`; latest: `5.1.0` (2026-05-28) | 路由和菜单联动 | 仓库现有路由全部基于 v4 API，Phase 21 不建议升级主版本 |
| element-plus | project: `^2.9.0`; latest: `2.14.1` (2026-05-29) | 表格/分页/菜单/确认交互 | 当前 UI 基础库，功能完全覆盖 KB-UI-01~04 |
| @element-plus/icons-vue | project: `^2.3.1`; latest: `2.3.2` (2025-08-05) | 菜单图标 | 与 Element Plus 图标生态一致 |

[VERIFIED: npm registry + `frontend/package.json`]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Node.js | `v22.22.0` | 前端测试运行环境 | 执行 `npm run test:router` / `test:frontend` |
| npm | `11.12.1` | 依赖与脚本管理 | 执行前端测试与构建 |
| Python | `3.11.9` | 后端测试运行环境 | 运行 KB API pytest |
| pytest | `9.0.3` | 后端 API 回归测试 | 覆盖 `GET/DELETE /kb/entries` |

[VERIFIED: local environment probes]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `el-table + el-pagination` | `el-table-v2` | 虚拟滚动性能更强，但对现有页面模式侵入更大 |
| `ElMessageBox.confirm` | `ElPopconfirm` | `Popconfirm` 更轻量，但复杂删除状态处理通常不如 MessageBox 清晰 |

**Installation:**
```bash
# 本阶段建议零新增依赖，复用现有前端栈
npm install
```

## Architecture Patterns

### System Architecture Diagram

```text
[左侧菜单点击“知识库配置”]
            |
            v
[router /kb-config 路由进入页面]
            |
            v
[输入字段名关键词]
            |
            v
[debounce + cancel stale request]
            |
            v
[GET /kb/entries?field_name=&page=&page_size=]
            |
            v
[kb route 参数校验 + service 过滤分页]
            |
            v
[返回 items + total]
            |
            v
[el-table 渲染 + el-pagination 控制页码]
            |
            +------> [删除按钮]
                         |
                         v
              [MessageBox 二次确认]
                         |
                         v
               [DELETE /kb/entries/{id}]
                         |
                         v
       [按当前过滤条件和页码重新请求列表]
```

### Recommended Project Structure
```text
frontend/src/
├── views/KbConfigView.vue          # 知识库配置主页面
├── composables/useKbConfigList.ts  # 过滤/分页/删除的状态管理
├── api/kb.ts                       # 扩展分页参数的 API 客户端
├── layouts/AppLayout.vue           # 菜单新增“知识库配置”
└── router/index.ts                 # 注册 kb-config 路由

backend/app/
├── api/routes/kb.py                # 增加 page/page_size 参数
└── services/kb_service.py          # 过滤+分页查询实现
```

### Pattern 1: 菜单路由高亮一致性
**What:** 使用 `el-menu` 的 `router` + `default-active` 让 URL 与菜单高亮自动同步。  
**When to use:** 新增一级业务菜单。  
**Example:**
```typescript
// Source: https://element-plus.org/en-US/component/menu
<el-menu :default-active="menuActive" router>
  <el-menu-item index="/kb-config">知识库配置</el-menu-item>
</el-menu>
```

### Pattern 2: 防抖过滤 + 过期请求清理
**What:** `watch` 输入变化，防抖后请求，并清理过期副作用。  
**When to use:** 输入即查询场景（KB-UI-03）。  
**Example:**
```typescript
// Source: https://vuejs.org/guide/essentials/watchers
watch(keyword, (val, _, onCleanup) => {
  const timer = setTimeout(() => fetchList(val), 300)
  onCleanup(() => clearTimeout(timer))
})
```

### Anti-Patterns to Avoid
- **前端全量拉取再筛选：** 与 D-03 冲突，且随数据增长明显退化。[VERIFIED: D-03 in `21-CONTEXT.md`]
- **删除后本地直接 splice：** 易与后端真实状态偏离，且破坏“保持筛选上下文刷新”。[ASSUMED]
- **将详情子菜单逻辑绑到新页面：** 会干扰现有 `jobId` 条件展开逻辑。[VERIFIED: `AppLayout.vue`]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 分页 UI | 手写页码组件 | `el-pagination` | 已有双向绑定、总数、页大小等能力 |
| 删除确认对话框 | `window.confirm` | `ElMessageBox.confirm` | 交互一致、可定制文案和按钮语义 |
| 大数据渲染优化 | 自写虚拟列表 | `el-table-v2`（需要时） | 官方维护，减少边界 bug |

**Key insight:** 本阶段重点是“契约一致性”和“状态一致性”，不是组件研发。

## Common Pitfalls

### Pitfall 1: 过滤后页码不回退
**What goes wrong:** 输入过滤词后还停在旧页码，导致空列表。  
**Why it happens:** `keyword` 与 `currentPage` 状态更新时序未统一。  
**How to avoid:** 过滤词变化时强制 `currentPage = 1` 再请求。  
**Warning signs:** `total > 0` 但当前页 `items` 为空。  

### Pitfall 2: 请求竞态覆盖新结果
**What goes wrong:** 快速输入时旧请求晚到，覆盖新筛选结果。  
**Why it happens:** 没有清理 watcher 副作用或请求序列保护。  
**How to avoid:** `onCleanup` 清理定时器，或使用请求版本号/AbortController。  
**Warning signs:** 输入停止后列表短暂正确又回退。  

### Pitfall 3: 删除后丢失筛选上下文
**What goes wrong:** 删除成功后页面回到默认查询。  
**Why it happens:** `refresh()` 未携带当前 `keyword/page`。  
**How to avoid:** 删除成功调用 `loadList({ keyword, page, pageSize })`。  
**Warning signs:** 删除后筛选框内容和列表结果不一致。  

## Code Examples

### Element Plus 分页
```vue
<!-- Source: https://element-plus.org/en-US/component/pagination -->
<el-pagination
  v-model:current-page="currentPage"
  v-model:page-size="pageSize"
  :total="total"
  layout="total, prev, pager, next"
/>
```

### 删除确认
```typescript
// Source: https://element-plus.org/en-US/component/message-box
await ElMessageBox.confirm('删除后不可恢复，是否继续？', '删除确认', {
  type: 'warning',
  confirmButtonText: '删除',
  cancelButtonText: '取消',
})
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 前端全量列表筛选 | 服务端过滤 + 服务端分页 | 持续演进实践 | 降低首屏和内存压力 |
| 无请求清理的即时搜索 | watcher cleanup / 请求取消 | Vue 3.5+ 明确推荐 | 降低竞态导致的 UI 错乱 |

**Deprecated/outdated:**
- 高频筛选不做清理控制会引发结果抖动，官方 watcher 文档已给出清理模式。[CITED: https://vuejs.org/guide/essentials/watchers]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 删除后必须“整页重拉”而不是局部 splice | Anti-Patterns | 若后端稳定且数据规模小，局部更新也可满足需求，但一致性风险更高 |

## Open Questions

1. **分页参数命名**
   - What we know: 当前只有 `field_name` 参数。[VERIFIED: `backend/app/api/routes/kb.py`]
   - What's unclear: 使用 `page/page_size` 还是 `offset/limit`。
   - Recommendation: 与 planner 在 Wave 0 锁定并同步前后端。

2. **字段名匹配方式**
   - What we know: 当前 `list_entries` 是“完全相等”匹配。[VERIFIED: `backend/app/services/kb_service.py`]
   - What's unclear: “关键字过滤”是否要求子串匹配。
   - Recommendation: 默认按“包含匹配”实现，更贴近需求文案；若有歧义先在计划中加确认点。[ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | 前端测试与构建 | ✓ | v22.22.0 | — |
| npm | 前端脚本执行 | ✓ | 11.12.1 | — |
| Python | 后端 pytest | ✓ | 3.11.9 | — |
| pytest | KB API 测试 | ✓ | 9.0.3 | — |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Node built-in test runner + pytest |
| Config file | `frontend/package.json` scripts, `pytest.ini` |
| Quick run command | `npm run test:router --prefix frontend` |
| Full suite command | `npm run test:router --prefix frontend && npm run test:frontend --prefix frontend && pytest backend/tests/test_api_kb.py -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KB-UI-01 | 菜单新增与路由可达 | unit (router contract) | `npm run test:router --prefix frontend` | ❌ Wave 0 (`frontend/tests/router/kb-config-nav.test.mjs`) |
| KB-UI-02 | 列表展示 + 分页路径 | unit (view/composable) | `npm run test:frontend --prefix frontend` | ❌ Wave 0 (`frontend/tests/frontend/kb-config-view.test.mjs`) |
| KB-UI-03 | 字段名即时过滤 | unit (view/composable) | `npm run test:frontend --prefix frontend` | ❌ Wave 0 (`frontend/tests/frontend/kb-config-filter.test.mjs`) |
| KB-UI-04 | 删除确认后刷新 | unit + API | `npm run test:frontend --prefix frontend && pytest backend/tests/test_api_kb.py -q` | ⚠️ 仅部分存在（需补前端删除交互测试） |

### Sampling Rate
- **Per task commit:** `npm run test:router --prefix frontend`
- **Per wave merge:** `npm run test:frontend --prefix frontend && pytest backend/tests/test_api_kb.py -q`
- **Phase gate:** 以上命令全绿后进入 `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `frontend/tests/router/kb-config-nav.test.mjs` — 覆盖 KB-UI-01
- [ ] `frontend/tests/frontend/kb-config-view.test.mjs` — 覆盖 KB-UI-02
- [ ] `frontend/tests/frontend/kb-config-filter.test.mjs` — 覆盖 KB-UI-03
- [ ] `frontend/tests/frontend/kb-config-delete.test.mjs` — 覆盖 KB-UI-04
- [ ] 扩展 `backend/tests/test_api_kb.py` 的分页参数用例（若后端新增分页）

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 本阶段不新增登录认证流程 |
| V3 Session Management | no | 本地桌面工具，无新会话机制 |
| V4 Access Control | yes | `/kb` 路由继续由 `verify_api_key` 依赖保护 |
| V5 Input Validation | yes | `field_name`、`entry_id` 由 FastAPI/Pydantic/UUID 校验 |
| V6 Cryptography | no | 本阶段无新增加密需求 |

### Known Threat Patterns for Vue + FastAPI KB UI
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 删除误操作 | Tampering | 二次确认 + 明确不可恢复文案 |
| 参数污染导致异常查询 | Tampering | query 参数约束 + 后端白名单字段处理 |
| 过度暴露错误细节 | Information Disclosure | 前端保留可读提示，避免回显敏感堆栈 |

## Sources

### Primary (HIGH confidence)
- `frontend/src/layouts/AppLayout.vue` — 菜单结构、`default-active`、`router` 使用 [VERIFIED: codebase]
- `frontend/src/router/index.ts` — 路由注册与页面入口模式 [VERIFIED: codebase]
- `frontend/src/views/FileListView.vue` — 列表刷新/删除交互基线 [VERIFIED: codebase]
- `frontend/src/api/kb.ts` — KB 列表与删除 API 客户端现状 [VERIFIED: codebase]
- `backend/app/api/routes/kb.py` — `GET/DELETE /kb/entries` 契约 [VERIFIED: codebase]
- `backend/app/services/kb_service.py` — 当前过滤匹配实现 [VERIFIED: codebase]
- `frontend/package.json`, `pytest.ini` — 测试命令与测试基线 [VERIFIED: codebase]
- [Element Plus Menu](https://element-plus.org/en-US/component/menu) [CITED: https://element-plus.org/en-US/component/menu]
- [Element Plus Table](https://element-plus.org/en-US/component/table) [CITED: https://element-plus.org/en-US/component/table]
- [Element Plus Pagination](https://element-plus.org/en-US/component/pagination) [CITED: https://element-plus.org/en-US/component/pagination]
- [Vue Watchers](https://vuejs.org/guide/essentials/watchers) [CITED: https://vuejs.org/guide/essentials/watchers]
- npm registry `npm view`：`vue@3.5.35`、`vue-router@5.1.0`、`element-plus@2.14.1`、`@element-plus/icons-vue@2.3.2` [VERIFIED: npm registry]

### Secondary (MEDIUM confidence)
- None.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - 版本、发布时间、项目当前版本均已核验。
- Architecture: HIGH - 关键结论都来自 CONTEXT + 代码实证。
- Pitfalls: MEDIUM - 部分防错策略为工程经验归纳。

**Research date:** 2026-06-02  
**Valid until:** 2026-07-02
