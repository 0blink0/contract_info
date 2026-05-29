# Feature Landscape — CTRX v1.3

**Domain:** 私募基金合同 docx → 五张 CRM 导入 Excel + 路径 B 手录草稿 + 可审计摘录核对（Electron 桌面半自动录入工具）  
**Researched:** 2026-05-29  
**Scope:** v1.3 里程碑（多文件并行 + 文件详情六页工作流）；对照 v1.2 已交付能力与代码现状  
**Overall confidence:** **HIGH**（`PROJECT.md` + 前端/后端实现直接检视）；页码列端到端能力为 **MEDIUM**（规划已写，代码尚未暴露 `page_no`）

---

## 基线（v1.2 已交付，v1.3 须保持）

| 能力 | 实现锚点 | v1.3 关系 |
|------|----------|-----------|
| 单份 docx 上传 → 独立 job | `UploadView.vue` → `upload()` | 扩展为 ≤3 并行，不破坏单 job 模型 |
| 解析流水线（pending → exported） | `ProcessStepper` + `useJobPoll` | 每 job 仍独立轮询 |
| 五表 xlsx 下载 | `JobDetail.vue` 五个绿色按钮 | 下沉到各子页「单表下载」 |
| 可编辑导出预览（五表 tabs） | `ExportPreview.vue` + `saveJobPreview` | 拆成五张独立详情页，逻辑复用 |
| LLM 摘录一致性校验 | `ValidationPanel.vue`（折叠面板） | 可保留为全局折叠或并入各表核对区 |
| 路径 B（业绩报酬/开放日） | `PathBPanel.vue` + `getPathB` | 升级为独立「字段 B」路由页 |
| 核对报告 xlsx | `download/review-report` + `review_workbook.py` | 升级为各页**内联**核对表（字段/值/页码/摘录） |
| 文件详情单路由 monolith | `JobDetail.vue` 堆叠全部面板 | **反模式来源**，v1.3 专门拆解 |

---

## Table Stakes（缺了就不像 CTRX）

运营人员默认「上传合同 → 等进度 → 改数 → 对摘录 → 下 Excel → 手录 CRM」。v1.3 在保持上述闭环前提下，解决「一次多份合同」与「详情页太长难找」。

| Feature | 为何是标配 | 复杂度 | 备注 |
|---------|------------|--------|------|
| **docx 上传 + 任务状态机** | 无上传则无产品；`pending`/`extracted`/`exported` 等状态驱动 UI | 低（已有） | v1.3：上传页展示多 job 卡片，每份独立「开始/重试」 |
| **≤3 份并行解析** | 运营常同时处理 2–3 只产品合同；单线程上传是 v1.2 瓶颈 | **中** | 每文件独立 `job_id` + 后台 worker；**硬上限 3**（`PROJECT.md` Out of Scope：>3 → v2 队列） |
| **五张导入表 Excel 生成与下载** | 核心业务交付物（产品要素、运营费率、申赎费率、锁定期、分级份额） | 低（已有） | 每详情子页保留一个主下载 CTA，避免 Hub 堆五个按钮 |
| **可编辑导出数据 + 保存回写** | 抽取必错，运营需改值后再导入 CRM | 低（`ExportPreview` 已有） | 保存触发 `saveJobPreview` 并重生成 xlsx；**按表 dirty**，避免六页共用一个 giant form |
| **摘录核对表（字段 / 值 / 原文摘录）** | 「可解释、可审计」是项目核心决策；无摘录则不敢导入 | **中** | 后端已有 `snippet` 列（`preview_service._append_snippet_column`）与 `review_workbook`；v1.3 需在 UI **每表一页**展示，对齐核对报告列语义 |
| **页码（定位合同原文）** | 运营翻纸质/ PDF 合同时靠页码；仅摘录无页码则核对成本高 | **中–高** | 规划明确要求；当前 `review_workbook` / PathB API **未统一暴露 page_no** — 需解析层或抽取 JSON 补字段，属 v1.3 后端缺口 |
| **路径 B 业绩报酬 / 开放日摘录** | 不进 Excel 母版，但必须手录 CRM（`FIELD_SPEC` 路径 B） | 低（`PathBPanel` 已有摘录块） | v1.3 独立「字段 B」页：建议值 + 章节原文 + **页码** + JSON 复制/下载 |
| **任务列表与删除** | 历史合同可追溯；误传需删 | 低（`FileListView` / `deleteJob`） | 处理中不可删（已有 `canDelete`） |
| **处理进度可见** | 解析 30s–数分钟；无步骤条用户以为卡死 | 低（`ProcessStepper`） | 上传页多 job 时每个卡片自带 stepper |
| **LLM 校验（可选）** | 配置 Key 后自动 fail/warn；未配置则跳过 | 低（`ValidationPanel`） | 建议：Hub 显示 fail/warn **计数**，详情页展开完整表；避免六页各拉一遍 LLM |
| **桌面设置 / 首次向导** | v1.2 Electron 交付必备 | 低（已交付） | 不在 v1.3 重构范围，仅回归 |

---

## Differentiators（v1.3 相对 v1.2 的增值）

| Feature | 价值 | 复杂度 | 备注 |
|---------|------|--------|------|
| **文件详情 Hub 总览** | 进入 `/jobs/:id` 先看五表 + 字段 B **摘要**（行数、warn 数、覆盖度），再点「进入详情」 | 中 | Hub **不做**全量编辑，降低认知负荷；对齐 `PROJECT.md`「总览页仅作入口」 |
| **左侧可折叠子菜单（五表 + 字段 B）** | 替代 `ExportPreview` 内 tabs + 长页折叠；符合 v1.1 后运营反馈的导航痛点 | 中 | 嵌套路由建议：`/jobs/:id`（hub）、`/jobs/:id/product` … `/jobs/:id/field-b`；`AppLayout` 全局菜单不变 |
| **每表独立工作页三件套** | 同一屏：**可编辑表** + **核对表** + **单表下载**；无需滚过 PathB/Validation | 中 | 从 `JobDetail` monolith **拆分组件**，共享 `jobId` + `useJobPoll` |
| **并行上传工作区** | 上传页同时挂起最多 3 个进度卡片，完成即跳转对应详情 | 中 | `el-upload` `multiple` + 前端队列；或批量 `POST`（若后端新增） |
| **字段 B 专页（人工判断模式）** | 强调「建议摘录 + 页码」而非 CRM 枚举自动映射（刻意 defer PATHB-EX） | 中 | 复用 `PathBPanel` 数据模型；弱化 JSON 墙，突出原文块 |
| **Hub 级校验摘要徽章** | 一眼看到能否发 CRM：`fail 3 / warn 1` | 低 | `detail.validation_*_count` 已有 |
| **按表保存（局部回写）** | 只改运营费率时不重写五表 preview | 中（可选 P2） | v1.3 可先做「整包 saveJobPreview」；后续 API 按 `table_kind` 拆分 |

---

## Anti-Features（明确不做或警惕）

| Anti-Feature | 为何避免 | 替代方案 |
|--------------|----------|----------|
| **>3 份 / ZIP / 批量队列** | 桌面 SQLite + 单用户；LLM 成本与内存不可控 | v1.3 硬限 3；v2 再做队列与 CRM 批量 |
| **Hub 页塞满 ExportPreview + PathB + Validation 全量** | 重复 v1.2 `JobDetail` monolith，违背重构目标 | Hub 仅摘要 + 导航；深度操作在子路由 |
| **六页各触发一次全量 LLM 校验** | 成本 ×6、等待 ×6 | Hub/详情顶栏一次校验；子页只读缓存结果 |
| **CRM 自动录入 / PATHB 枚举自动映射** | 无母版、枚举易错；已 defer PATHB-EX-01/02 | 继续 JSON + 摘录手录 |
| **PDF / 扫描件 OCR** | 输入契约是 docx | 维持 `.docx` only |
| **黄金 xlsx 线上自动批改** | 运营手工表非生产真值 | dev/UAT 回归脚本 |
| **取消摘录只显示最终值** | 违反「校验层只看摘录」决策 | 核对表必含 `evidence_text` / snippet 列 |
| **全局单页保存无 dirty 提示** | 易丢改 | 每子页 `dirty` + 路由离开 `beforeRouteLeave` 确认 |
| **子菜单不可折叠占宽** | 小屏笔记本侧栏挤压表格 | `el-sub-menu` 可折叠；默认展开当前表 |
| **自动更新 / 托盘常驻** | v1.2 已判定过度工程 | 版本号 About + 手工安装包 |

---

## Feature Dependencies

```
[多文件上传 ≤3]
    └──requires──> [每文件独立 job 记录]（已有 ContractFile 模型）
    └──requires──> [并行 runJob / 后台任务不互斥]（需确认 SQLite 写锁策略）
    └──enhances──> [上传页多卡片 UI]

[详情 Hub 总览]
    └──requires──> [job 级 preview/path_b/validation 摘要 API]（多数已有于 JobDetail）
    └──routes──> [六张子页]

[左侧子菜单 + 六路由]
    └──requires──> [Vue Router 嵌套路由 + JobDetailLayout]
    └──splits──> [ExportPreview] → 5 × TableDetailPage
    └──splits──> [PathBPanel] → FieldBDetailPage
    └──splits──> [ValidationPanel] → 全局或 per-table 片段

[每页：可编辑 + 核对表 + 下载]
    └──requires──> [getJobPreview 按表切片]（可先前端 filter，后端的 table 参数更佳）
    └──requires──> [摘录核对 rows：field, value, page_no, excerpt]（page_no 可能需新 API）
    └──reuses──> [downloadBlob(kind)] 单表 kind 已有
    └──parallels──> [review_workbook 列定义]（避免 UI 与 xlsx 列不一致）

[字段 B 页码]
    └──requires──> [docx 解析保留块级页码或锚点]（研究缺口，见 Gaps）
    └──blocks──> [FIELD B 页完整体验] 若仅有摘录无页码则降级为 MEDIUM 验收
```

---

## MVP Recommendation（v1.3 发布门槛）

**Must ship（P0）：**

1. 上传页：一次选 1–3 个 docx，分别创建 job，并行显示进度，完成后可进详情  
2. `/jobs/:id` Hub：五表行数/状态 + 字段 B 覆盖度 + 六枚「进入详情」  
3. 左侧子导航六页 + 每页：编辑区 + 摘录核对表 + 单表下载  
4. 字段 B 专页：CRM 建议表 + 业绩报酬/开放日原文块（页码若后端就绪则显示，否则标为 follow-up）  
5. 保持 v1.2：设置向导、Electron 启动、删除 job、全表 xlsx 逻辑正确  

**Should ship（P1）：**

- Hub 上 Validation fail/warn 徽章 + 一键展开校验面板  
- 路由切换 dirty 提示  
- 上传页「批量开始处理」按钮（可选，非必须）  

**Defer（post-v1.3 / v2）：**

- 按表局部 save API、PATHB 枚举映射、>3 队列、DB 清理 UI、Linux clean-VM  

---

## 与现有组件的映射（实施提示）

| v1.3 页面 | 主要复用 | 新建/改动 |
|-----------|----------|-----------|
| 上传（多文件） | `UploadView`, `upload`, `runJob`, `useJobPoll` | 多文件队列 UI、3 上限校验 |
| Hub | `JobDetail` 头部（文件名、状态、stepper） | 摘要卡片 + `router-link` |
| 产品要素 … 分级份额 | `ExportPreview` 各 tab 表格 | `TableDetailPage` + 核对表组件 |
| 字段 B | `PathBPanel` 内容展平为整页 | 页码列、弱化折叠 |
| 校验 | `ValidationPanel` | 提到 layout 层或 Hub 抽屉 |
| 布局 | — | `JobDetailLayout.vue`（侧栏 + `<router-view>`） |

---

## Gaps / 需阶段内 Spike

| 缺口 | 影响 | 建议 |
|------|------|------|
| **页码未在 API/schema 统一** | 核对表「四列」缺一列 | 解析 pipeline 输出 `page_no`；Path B `source_snippets` 扩展元数据 |
| **核对表仅 xlsx 下载、无 JSON API** | 前端需重复拼装 rows | 新增 `GET /jobs/{id}/review-rows?table=product` 或复用 preview + extraction 原始 JSON |
| **SQLite 并行 runJob** | 第三份并行可能锁库 | 序列化写阶段或 WAL + 短事务（见 `PITFALLS.md`） |
| **Validation 与 per-table 边界** | 产品要素 fail 在费率页重复展示？ | 校验项带 `table`/`field` 标签过滤 |

---

## Sources

| 来源 | 置信度 |
|------|--------|
| `contract_info/.planning/PROJECT.md`（v1.3 目标与 Out of Scope） | HIGH |
| `frontend/src/components/JobDetail.vue`, `ExportPreview.vue`, `ValidationPanel.vue`, `PathBPanel.vue` | HIGH |
| `frontend/src/views/UploadView.vue`, `router/index.ts`, `layouts/AppLayout.vue` | HIGH |
| `backend/app/export/review_workbook.py`, `services/preview_service.py` | HIGH |
| `FIELD_SPEC.md`（路径 A/B 边界） | HIGH |
| 页码字段：全库 `grep page_no` 无实现 | HIGH（负向验证） |

---

*Feature research for: CTRX v1.3 — 多文件并行与详情页重构*  
*Supersedes v1.2-only desktop UX section in prior FEATURES.md (Electron wizard/settings); that content remains valid in milestone v1.2 docs.*
