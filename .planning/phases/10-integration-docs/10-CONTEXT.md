# Phase 10：集成与文档 — 上下文

**收集日期：** 2026-05-26  
**状态：** 可供规划

<domain>
## 阶段边界

交付 **v1.1 运营可用完整面**：前端补齐 **5 个 Excel 下载**、**路径 B JSON** 手录辅助、**LLM 摘录校验** 可视化，并更新 **README / FIELD_SPEC / .env.example**（含 LLM 与迁移说明）。

**本阶段包含：**

- `JobDetail`：第 5 下载按钮（申赎费率）、`validation_*` 摘要展示
- 新组件：`PathBPanel`（折叠 + JSON + 复制 + 下载 `.json`）、`ValidationPanel`（fail/warn 着色表）
- `client.ts` / `types.ts`：`getPathB`、`getValidation`、`subscription` 下载 kind
- `ExportPreview`：增加 **申赎费率** Tab（需扩展 preview API 或等价数据）
- 文档：README、FIELD_SPEC、`.env.example`（`OPENAI_*`、`alembic upgrade head`、Docker 内 LLM）

**本阶段不包含：**

- 用户登录/OAuth、批量队列、PDF
- 校验 fail **阻止导出** 或强制确认弹窗（Phase 9 已锁定 advisory）
- ZIP 打包下载、路径 B 写回 CRM
- 合并 `GET /preview` 为单一 mega 端点（保持 `/path-b` + `/validation` 分端点）
- 独立 `DEPLOY.md`（内容并入 README 章节即可）

</domain>

<decisions>
## 实现决策

### 五表下载（D-DL）

- **D-DL01:** **`exported` 后显示 5 个并列绿色按钮**（与 Phase 5 一致），新增「下载申赎费率」→ `GET /jobs/{id}/download/subscription-fee-rates`，文件名 `subscription_fee_rates.xlsx`。
- **D-DL02:** 按钮文案中文、与运营模板语义一致；`flex-wrap` 换行，不采用下拉菜单。

### 路径 B（D-PB）

- **D-PB01:** 独立 **`el-collapse` 面板**「路径 B（需 CRM 手录）」；副标题说明不进 Excel 导入母版。
- **D-PB02:** 内容：`performance_fee` / `open_day` 结构化展示 + `source_snippets` 键值表；底部 **格式化 JSON**（`JSON.stringify` 缩进）。
- **D-PB03:** 操作：**复制 JSON**、**下载 `path_b_{job_id}.json`**（前端 Blob，无需新后端端点）。
- **D-PB04:** **可见时机：** `status` ∈ `{extracted, exporting, exported}`（与后端 `PREVIEW_STATUSES` 一致）；`path_b_available=false` 时面板禁用或提示「暂无」。
- **D-PB05:** **懒加载：** 首次展开时 `GET /api/v1/jobs/{id}/path-b`。

### LLM 校验（D-VAL）

- **D-VAL01:** **独立 `ValidationPanel`**，**不** 与 `WarningsList`（规则/导出/validation_skipped）合并。
- **D-VAL02:** 标题区展示 JobDetail 摘要：`validation_fail_count` / `validation_warn_count` 徽章；`validation_available=false` 且非 skipped 时提示未校验。
- **D-VAL03:** 明细表列：字段、状态、值、原因、建议；行按 **status 着色**（fail 红、warn 橙、pass 绿灰）。
- **D-VAL04:** **默认筛选 fail + warn**；提供「显示 pass」切换。
- **D-VAL05:** **懒加载：** 首次展开时 `GET /api/v1/jobs/{id}/validation`。
- **D-VAL06:** **顾问式：** 不增加「校验未通过禁止下载」弹窗；可在 fail>0 时显示 **非阻塞** `el-alert` 提醒运营复核。

### 详情页信息架构（D-UX）

- **D-UX01:** 自上而下建议顺序：文件名/状态 → 步骤条 → 操作按钮（开始/重试/下载）→ `WarningsList` → `ValidationPanel` → `PathBPanel` → `ExportPreview`。
- **D-UX02:** 下载区仍在 **`exported`** 后显示；Path B / 校验在 **`extracted+`** 可展开（与下载区分）。
- **D-UX03:** 轮询 `getJob` 时更新摘要计数；展开面板后若任务仍在 `exporting`，可选手动刷新按钮（planner 酌情）。

### 导出预览（D-PR）

- **D-PR01:** **`ExportPreview` 增加「申赎费率」Tab**，列与 xlsx 模板对齐（与 fee/lock/share 同模式）。
- **D-PR02:** 若当前 `GET /preview` 无申赎数据，**本阶段扩展后端 preview** 返回 `subscription_columns` + `subscription_rows`（优先于前端读 xlsx 文件）。
- **D-PR03:** 预览门禁与现有一致（`exported` 优先读 xlsx；`extracted` 可读 extraction 兜底——保持 Phase 5 行为）。

### API 与类型（D-API）

- **D-API01:** 扩展 `JobDetail` TS 类型：`subscription_xlsx_path`、`path_b_available`、`validation_available`、`validation_fail_count`、`validation_warn_count`。
- **D-API02:** 新增 `getPathB(jobId)`、`getValidation(jobId)`；`DownloadKind` 增加 `'subscription-fee-rates'`。
- **D-API03:** **不** 新增合并 preview 端点；API-02 由前端组合消费满足。

### 文档（D-DOC）

- **D-DOC01:** **README**：v1.1 能力列表（5 表 + path B + 校验）、本地/Docker 启动、`alembic upgrade head`（至 007）、**生产必须配置 `OPENAI_API_KEY`** 方可 LLM 抽取与校验。
- **D-DOC02:** **FIELD_SPEC.md**：五表字段说明、路径 B JSON 字段、`validation_result` 结构、与 `extraction_warnings` 区别。
- **D-DOC03:** **`.env.example`**（根目录与 `frontend/.env.example`）：补全 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`LLM_MODEL` 等占位与注释。
- **D-DOC04:** **TEST-03** 验收：文档与实现一致；不要求独立 DEPLOY.md。

### Claude 酌情

- ValidationPanel / PathBPanel 是否拆为独立 `.vue` 文件
- 申赎 preview 列名与 `SubscriptionFeeRow` 别名映射
- fail>0 时 alert 文案与是否显示 pass 默认开关持久化（localStorage）
- 前端 Vitest/组件测试（非阻塞，有则更好）

</decisions>

<canonical_refs>
## 规范引用（规划/实现前必读）

### 需求与路线图
- `contract_info/.planning/REQUIREMENTS.md` — UI-01–02、API-02、TEST-03、VAL-04
- `contract_info/.planning/ROADMAP.md` — Phase 10 成功标准
- `contract_info/.planning/PROJECT.md` — 路径 B 手录、校验只看摘录

### 上游阶段
- `contract_info/.planning/phases/05-frontend/05-CONTEXT.md` — 步骤条、warnings、双下载模式
- `contract_info/.planning/phases/07-subscription-fees/07-CONTEXT.md` — 申赎模板与下载端点
- `contract_info/.planning/phases/08-path-b-json/08-CONTEXT.md` — path_b schema、PATHB-04
- `contract_info/.planning/phases/09-llm-validation/09-CONTEXT.md` — advisory、GET /validation

### 实现锚点
- `contract_info/frontend/src/components/JobDetail.vue`
- `contract_info/frontend/src/components/WarningsList.vue`
- `contract_info/frontend/src/components/ExportPreview.vue`
- `contract_info/frontend/src/api/client.ts`、`types.ts`
- `contract_info/backend/app/api/routes/jobs.py` — download/path-b/validation
- `contract_info/backend/app/services/preview_service.py`
- `contract_info/FIELD_SPEC.md`、`README.md`、`.env.example`

</canonical_refs>

<code_context>
## 现有代码洞察

### 缺口（Phase 10 主要工作）
- `JobDetail.vue` 仅 4 个下载按钮；`types.ts` 无 subscription / validation / path_b 字段
- `client.ts` 无 `getPathB` / `getValidation`；`DownloadKind` 缺申赎
- `ExportPreview` 四 Tab，无申赎
- 后端 `JobDetailResponse` 已有 `validation_*`、`path_b_available`（Phase 8–9）

### 可复用
- Element Plus：`el-collapse`、`el-table`、`el-tag`、`el-alert`
- `downloadBlob` + `downloadUrl` 模式
- `useJobPoll` 刷新 JobDetail 摘要

### 集成点
1. 扩展 `getJob` 消费新 JobDetail 字段
2. 懒加载面板调用 `/path-b`、`/validation`
3. `preview_service` 扩展申赎行（若缺失）

</code_context>

<specifics>
## 讨论结论摘要

- 五按钮并列；Path B 折叠 + 复制/下载 JSON
- 校验独立面板，默认 fail+warn，懒加载，不阻止导出
- extracted+ 可见 path B / 校验；预览增加申赎 Tab
- 文档：README + FIELD_SPEC + .env.example

</specifics>

<deferred>
## 延后项

| 想法 | 归属 |
|------|------|
| ZIP 五表打包下载 | backlog |
| 校验 fail 阻止导出 / 强制确认弹窗 | 不做（非本里程碑） |
| 合并 path-b + validation 单一 API | 不做；前端组合即可 |
| 独立 DEPLOY.md | 合并进 README |
| 批量上传、登录鉴权 | v2 |

</deferred>

---

*Phase: 10-integration-docs*  
*Context gathered: 2026-05-26*
