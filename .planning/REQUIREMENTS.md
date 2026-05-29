# Requirements: CTRX v1.3 多文件并行与详情页重构

**Defined:** 2026-05-29  
**Milestone:** v1.3  
**Core Value:** 上传 docx → 可导入 Excel + 路径 B 手录辅助 + 可解释校验（本地桌面，无服务器依赖）

## v1.3 Requirements

### 多文件上传与并行（UP）

- [ ] **UP-01**: 用户可在上传页一次选择最多 3 个 docx 文件（超出时前端阻止并提示）
- [ ] **UP-02**: 每个 docx 创建独立 job；上传页同时展示最多 3 个任务的解析/导出进度（状态、步骤、错误）
- [ ] **UP-03**: 用户可从上传页对多个 pending job 批量触发「开始处理」，或进入各 job 详情单独重试
- [ ] **UP-04**: 后端限制同时进行 pipeline 的 job 数 ≤3；第 4 路 `POST /run` 返回 409 及可读错误信息

### 后端契约（API）

- [ ] **API-01**: 提供 `GET /jobs/{id}/preview/{section}` 与 `PUT /jobs/{id}/preview/{section}`，`section` 覆盖五表（`product-elements`、`fee-rates`、`lock-periods`、`share-classes`、`subscription-fee-rates`）；PUT 仅合并对应 section，不得清空其它表 extraction 数据
- [ ] **API-02**: 提供按表核对数据端点（如 `GET /jobs/{id}/verification/{table_key}`），返回字段名、字段值、摘录页码、原文摘录四列（页码不可用时允许空值并标注）
- [ ] **API-03**: 流水线并行执行使用有界 worker（如 `ThreadPoolExecutor(max_workers=3)`），每任务独立 DB session；与 SQLite WAL 兼容

### 导航与路由（NAV）

- [ ] **NAV-01**: 左侧菜单在存在当前 job 上下文时展示可折叠「文件详情」子菜单，含五表 + 字段 B 六项
- [ ] **NAV-02**: 使用 `JobDetailLayout` 嵌套路由：`/jobs/:id`（Hub）、`/jobs/:id/tables/:tableKey`（五表）、`/jobs/:id/field-b`（字段 B）
- [ ] **NAV-03**: 从文件列表进入某 job 时默认落在 Hub；子菜单高亮与当前子路由一致

### 详情 Hub（HUB）

- [ ] **HUB-01**: Hub 页仅展示任务元信息、处理步骤、五表 + 字段 B 的摘要卡片（名称、行数/状态、校验 fail/warn 计数可选）及「进入详情」按钮
- [ ] **HUB-02**: Hub 页不包含完整可编辑大表或 PathB/Validation 全量面板（避免重复 v1.2 单体页）
- [ ] **HUB-03**: Hub 保留 warnings 列表与 job 级校验摘要入口（一键查看校验结果）

### 五表工作页（TBL）

- [ ] **TBL-01**: 每张导入表有独立页面，展示该表可编辑数据（列与 v1.2 `ExportPreview` 对应 tab 一致）
- [ ] **TBL-02**: 用户编辑后可通过分表 PUT 保存；保存成功后该表 xlsx 导出反映最新数据
- [ ] **TBL-03**: 每表页内嵌摘录核对表：字段、字段值、摘录所在页码、原文摘录
- [ ] **TBL-04**: 每表页提供该表 xlsx 下载按钮（沿用现有 `DownloadKind`）
- [ ] **TBL-05**: 未保存编辑离开页面时提示确认（`beforeRouteLeave` 或等效 dirty 守卫）

### 字段 B（PB）

- [ ] **PB-01**: 字段 B 专页展示业绩报酬与开放日的建议摘录及页码（来自 path-b / source_snippets），供人工判断，不自动写入 CRM 枚举
- [ ] **PB-02**: 字段 B 页可复制或下载 path-b JSON（延续 v1.2 PathBPanel 能力）

### 前端基础设施（FE）

- [ ] **FE-01**: `useJobsPoll`（或等效）支持注册多个 jobId 并批量轮询状态，供上传页与多任务进度使用
- [ ] **FE-02**: 详情 Layout 层单一 poll + provide/inject，子页不各自重复全量 job 轮询

## Future Requirements（post-v1.3 / v2）

### PATHB 增强

- **PATHB-EX-01**: 业绩报酬提取方式自动映射 CRM 枚举
- **PATHB-EX-02**: 业绩基准类型与门槛净值枚举精度提升

### 批量与平台

- **BATCH-01**: >3 文件队列或 ZIP 批量上传
- **BATCH-02**: 批量任务列表与取消

### 技术债

- **PKG-03**: Linux clean-VM 烟测

## Out of Scope

| Feature | Reason |
|---------|--------|
| >3 并行或后台队列 | v1.3 上限 3；更大批量 → v2 |
| CRM 自动录入 | 仍为手录辅助 |
| PATHB 枚举自动映射 | 明确 deferred post-v1.3 |
| PDF/OCR/新表格库 | 不引入新运行时 |
| Hub 嵌入完整 ExportPreview + 五下载条 | 与六页工作流冲突 |
| 六页各自动触发全量 LLM 校验 | 成本与 429 风险；job 级校验在 Hub |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UP-01 | Phase 19 | Pending |
| UP-02 | Phase 19 | Pending |
| UP-03 | Phase 19 | Pending |
| UP-04 | Phase 15 | Complete |
| API-01 | Phase 15 | Complete |
| API-02 | Phase 15 | Complete |
| API-03 | Phase 15 | Complete |
| NAV-01 | Phase 16 | Pending |
| NAV-02 | Phase 16 | Pending |
| NAV-03 | Phase 16 | Pending |
| HUB-01 | Phase 18 | Pending |
| HUB-02 | Phase 18 | Pending |
| HUB-03 | Phase 18 | Pending |
| TBL-01 | Phase 17 | Pending |
| TBL-02 | Phase 17 | Pending |
| TBL-03 | Phase 17 | Pending |
| TBL-04 | Phase 17 | Pending |
| TBL-05 | Phase 17 | Pending |
| PB-01 | Phase 18 | Pending |
| PB-02 | Phase 18 | Pending |
| FE-01 | Phase 19 | Pending |
| FE-02 | Phase 16 | Pending |

*Coverage: 22/22 v1.3 requirements mapped (Phases 15–19). Updated by roadmapper 2026-05-29.*
