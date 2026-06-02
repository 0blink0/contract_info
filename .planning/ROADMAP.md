# Roadmap: CTRX — 合同要素抽取

**Project root:** `contract_info/`  
**Planning:** `contract_info/.planning/`

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5（shipped 2026-05-26）→ [archive](milestones/1.0-ROADMAP.md)
- ✅ **v1.1 抽取质量与导出扩展** — Phases 6–10（shipped 2026-05-26）→ [archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 桌面化交付** — Phases 11–14（shipped 2026-05-29）→ [archive](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 多文件并行与详情页重构** — Phases 15–19（shipped 2026-05-29）→ [Post-ship UX](v1.3-POST-SHIP-UX.md)
- 🔄 **v1.4 业绩报酬知识库与 RAG 增强** — Phases 20–23（active）

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–5) — SHIPPED 2026-05-26</summary>

- [x] **Phase 1: 文档解析** - docx → Document JSON + PostgreSQL schema + CLI parse
- [x] **Phase 2: 字段抽取** - 规则 + 章节窗 LLM 抽取、字典校验、extract CLI
- [x] **Phase 3: Excel 导出** - 产品要素与运营费率 xlsx 填充、export CLI
- [x] **Phase 4: API 层** - upload / run / poll / download FastAPI 端点
- [x] **Phase 5: 前端界面** - Element Plus 上传、任务列表、步骤条、双下载

</details>

<details>
<summary>✅ v1.1 抽取质量与导出扩展 (Phases 6–10) — SHIPPED 2026-05-26</summary>

- [x] **Phase 6: 黄金回归** - 黄金样例基线、回归脚本、P1+ 字段扩展
- [x] **Phase 7: 申赎费率第五表** - 第五张导入表导出逻辑与模板对齐
- [x] **Phase 8: 路径 B JSON** - 业绩报酬/开放日结构化草稿与 CRM 输出
- [x] **Phase 9: LLM 校验层** - 校验 API、ValidationPanel 前端展示
- [x] **Phase 10: UI 导航与下载** - 左侧菜单路由、五表下载、前端收口

</details>

<details>
<summary>✅ v1.2 桌面化交付 (Phases 11–14) — SHIPPED 2026-05-29</summary>

- [x] **Phase 11: SQLite 迁移与路径修复** - 替换 PostgreSQL 方言类型，修复 _MEIPASS 路径假设，开启 WAL，程序化 Alembic (completed 2026-05-28)
- [x] **Phase 12: PyInstaller 打包** - desktop_main.py 入口，完整 spec，干净 VM 烟雾测试通过 (completed 2026-05-29)
- [x] **Phase 13: Electron 壳与 IPC** - 子进程生命周期、contextBridge IPC、首次启动向导、Settings 页面 (completed 2026-05-29)
- [x] **Phase 14: 构建流水线** - electron-builder NSIS + AppImage + deb，4 步构建脚本 (completed 2026-05-29)

</details>

<details>
<summary>✅ v1.3 多文件并行与详情页重构 (Phases 15–19) — SHIPPED 2026-05-29</summary>

- [x] **Phase 15: 后端并行与分表 API** - ThreadPool 真并行、run 409 守门、分表 preview 与核对端点
- [x] **Phase 16: 详情路由与子菜单骨架** - JobDetailLayout 嵌套路由、左侧六链、Hub 占位与统一轮询
- [x] **Phase 17: 五表独立工作页** - 每表可编辑 preview、摘录核对表、单表下载与 dirty 守卫
- [x] **Phase 18: Hub 摘要与字段 B 专页** - Hub 摘要卡与校验入口、字段 B 摘录与 JSON 导出
- [x] **Phase 19: 多文件上传与并行进度 UI** - ≤3 docx 选择与批量处理、上传页多任务进度轮询

**Post-ship:** [v1.3-POST-SHIP-UX.md](v1.3-POST-SHIP-UX.md)（启动页、摘录右栏、Hub/子页分工、API 回退）

</details>

<details open>
<summary>🔄 v1.4 业绩报酬知识库与 RAG 增强 (Phases 20–23) — ACTIVE</summary>

- [x] **Phase 20: 知识库数据层 + PathB 录入 UI** - LanceDB 向量后端 CRUD + embedding，PathB 页底部可编辑录入表格与存入按钮
- [ ] **Phase 21: 知识库配置页 UI** - 左侧菜单「知识库配置」入口，历史案例列表查看/过滤/删除
- [ ] **Phase 22: RAG 检索与 LLM 注入** - 语义检索 Top-K 相似案例注入业绩报酬提取 prompt，Settings 增加 Top-K 配置
- [ ] **Phase 23: PyInstaller 打包兼容与烟测** - LanceDB + sentence-transformers 模型权重纳入打包，烟测验证全链路

</details>

## Phase Details

### Phase 15: 后端并行与分表 API

**Goal**: 系统可安全并行处理最多 3 个解析任务，并支持按表读写 preview 与核对数据
**Depends on**: Phase 14
**Requirements**: UP-04, API-01, API-02, API-03
**Success Criteria** (what must be TRUE):

  1. 当已有 3 个任务处于 pipeline 执行中时，再触发第 4 个「开始处理」会收到明确可读错误，且该任务不会被启动
  2. 用户（经前端或 API）可单独读取并保存某一张导入表的 preview；保存后其它四张表的 extraction 行数与内容保持不变
  3. 可获取某张导入表的核对数据：字段名、字段值、摘录页码（不可用时允许空值并标注）、原文摘录
  4. 最多 3 个解析任务可同时推进，各任务进度独立可查，不因 SQLite 写锁导致应用整体无响应

**Plans**: 3 plans

Plans:
**Wave 1**

- [ ] 15-01-PLAN.md — JobRunner、全局 409 守门、lifespan、并行测试（API-03, UP-04）

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 15-02-PLAN.md — 分表 preview GET/PUT、全量 PUT Optional 修复、分表测试（API-01）

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 15-03-PLAN.md — verification 端点、LLM Semaphore(2)、核对测试（API-02）

### Phase 16: 详情路由与子菜单骨架

**Goal**: 用户可从左侧菜单在 Hub 与五表、字段 B 子页之间清晰导航，且详情区状态由 Layout 统一维护
**Depends on**: Phase 15
**Requirements**: NAV-01, NAV-02, NAV-03, FE-02
**Success Criteria** (what must be TRUE):

  1. 进入某任务详情后，左侧出现可折叠的「文件详情」子菜单，含五张导入表与字段 B 共六项
  2. 用户可通过 URL 直达 Hub（`/jobs/:id`）、某表页（`/jobs/:id/tables/:tableKey`）、字段 B 页（`/jobs/:id/field-b`），刷新后仍停留在对应页面
  3. 从文件列表进入任务时默认落在 Hub；当前子路由与左侧子菜单高亮一致
  4. 在详情子页间切换时，任务状态由 Layout 层单一轮询更新，子页不会各自重复发起全量 job 轮询

**Plans**: 3 plans

Plans:
**Wave 1**

- [x] 16-01-PLAN.md — jobSections、JobDetailLayout、嵌套路由、provide/inject 单一 poll（NAV-02, FE-02）

**Wave 2**

- [x] 16-02-PLAN.md — AppLayout 子菜单、Hub/表/字段 B 占位页、列表/上传入口 job-hub（NAV-01, NAV-03）

**Wave 3**

- [x] 16-03-PLAN.md — 路由契约测试 + typecheck/build 门禁（D-26, D-27）

**UI hint**: yes

### Phase 17: 五表独立工作页

**Goal**: 运营可在每张导入表独立页面完成编辑、摘录核对与单表下载
**Depends on**: Phase 16
**Requirements**: TBL-01, TBL-02, TBL-03, TBL-04, TBL-05
**Success Criteria** (what must be TRUE):

  1. 用户可在五张导入表各自页面看到与 v1.2 对应 tab 一致的列，并可就地编辑
  2. 用户保存某表编辑后，下载该表 xlsx 反映最新已保存内容
  3. 每表页内展示摘录核对表：字段、字段值、摘录所在页码、原文摘录
  4. 每表页提供该表 xlsx 的单独下载按钮
  5. 存在未保存编辑时离开该表页会收到确认提示，避免静默丢失修改

**Plans**: 3 plans

Plans:
**Wave 1**

- [x] 17-01-PLAN.md — 分表 preview/verification API 客户端 + useSectionPreview（TBL-02）

**Wave 2**

- [x] 17-02-PLAN.md — TablePreviewEditor + VerificationExcerptTable（TBL-01, TBL-03）

**Wave 3**

- [x] 17-03-PLAN.md — JobTableView 编排、dirty 守卫、单表下载、测试（TBL-01~05）

**UI hint**: yes

### Phase 18: Hub 摘要与字段 B 专页

**Goal**: Hub 仅作任务总览与导航入口；字段 B 在专页展示建议摘录供人工判断
**Depends on**: Phase 17
**Requirements**: HUB-01, HUB-02, HUB-03, PB-01, PB-02
**Success Criteria** (what must be TRUE):

  1. Hub 展示任务元信息、处理步骤、五表与字段 B 的摘要卡片及「进入详情」按钮，不出现完整可编辑大表或 v1.2 单体页式的全量面板堆叠
  2. Hub 可查看 warnings 列表，并可一键查看 job 级校验摘要/结果
  3. 字段 B 专页展示业绩报酬与开放日的建议摘录及页码（页码不可用时界面有明确说明），供人工判断是否手录
  4. 用户可在字段 B 页复制或下载 path-b JSON（延续 v1.2 能力）

**Plans**: 3 plans

Plans:
**Wave 1**

- [x] 18-01-PLAN.md — useHubSummary + HubSectionCard + JobHubView 摘要卡（HUB-01）

**Wave 2**

- [x] 18-02-PLAN.md — Hub 挂载 WarningsList + ValidationPanel；Layout 精简（HUB-02, HUB-03）

**Wave 3**

- [x] 18-03-PLAN.md — usePathB + PathBDetail + JobFieldBView + 测试（PB-01, PB-02）

**UI hint**: yes

### Phase 19: 多文件上传与并行进度 UI

**Goal**: 用户可一次上传最多 3 份 docx，并在上传页并行查看与触发处理
**Depends on**: Phase 18
**Requirements**: UP-01, UP-02, UP-03, FE-01
**Success Criteria** (what must be TRUE):

  1. 用户在上传页一次最多选择 3 个 docx；尝试选第 4 个时前端阻止并给出提示
  2. 上传页同时展示最多 3 个任务的解析/导出进度（状态、步骤、错误信息各自独立）
  3. 用户可对多个 pending 任务批量触发「开始处理」，或进入某任务详情单独重试
  4. 上传页上各任务进度通过多 job 轮询保持同步更新，不会出现仅最后一个任务刷新的情况

**Plans**: 3 plans

Plans:
**Wave 1**

- [x] 19-01-PLAN.md — GET /jobs/concurrency + 前端 client/constants（D-13, D-14）

**Wave 2**

- [x] 19-02-PLAN.md — useJobsPoll + UploadJobCard（FE-01, UP-02）

**Wave 3**

- [x] 19-03-PLAN.md — UploadView 多文件上传/批量 run/测试（UP-01~03）

**UI hint**: yes

### Phase 20: 知识库数据层 + PathB 录入 UI

**Goal**: 建立 LanceDB 向量知识库后端（CRUD + embedding），PathB 页底部增加可编辑录入表格和存入按钮
**Depends on**: Phase 19
**Requirements**: KB-BE-01, KB-BE-02, KB-BE-03, KB-BE-04, KB-BE-05, KB-ENTRY-01, KB-ENTRY-02, KB-ENTRY-03, KB-ENTRY-04, KB-ENTRY-05
**Success Criteria** (what must be TRUE):

  1. 应用启动后，`CTRX_DATA_DIR` 下自动创建 LanceDB 向量表（首次启动无需手动操作）；sentence-transformers 模型完成预热，后续 embedding 调用无冷启动延迟
  2. PathB 详情页底部可见 3 列 4 行可编辑表格（字段名/字段值/原文摘录），页面加载时自动预填当前解析结果，字段值与原文摘录单元格可自由修改
  3. 用户勾选行后点击「存入知识库」，选中行批量提交至 `POST /kb/entries`，成功后界面显示入库条数提示（如「已存入 3 条」）
  4. `GET /kb/entries` 返回全部历史案例（含 id/字段名/字段值/原文摘录/来源合同/入库时间）；`DELETE /kb/entries/{id}` 可删除单条并即时从列表消失

**Plans**: 3 plans

Plans:
**Wave 0**

- [x] 20-01-PLAN.md — 后端依赖安装（lancedb, sentence-transformers）+ pytest 测试骨架（KB-BE-01~05）

**Wave 1** *(blocked on Wave 0 completion)*

- [x] 20-02-PLAN.md — 后端核心：kb_service.py + routes/kb.py + main.py lifespan 挂入（KB-BE-01~05）

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 20-03-PLAN.md — 前端：api/kb.ts + useKbEntry.ts + PathBDetail.vue KB 录入区（KB-ENTRY-01~05）

**Cross-cutting constraints:**
- bge-m3 软降级（D-06）：三个波次均需遵守；Wave 0 测试桩需覆盖 503 场景
- kbUnavailable 前端状态（D-07）：Wave 1 返回 503，Wave 2 消费该状态显示 el-alert
**Wave 1**

- [x] 20-01-PLAN.md — Wave 0：依赖安装 + 测试骨架（KB-BE-01~05 测试桩）

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 20-02-PLAN.md — 后端核心：kb_service.py + routes/kb.py + main.py lifespan（KB-BE-01~05）

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 20-03-PLAN.md — 前端：api/kb.ts + useKbEntry.ts + PathBDetail.vue KB 录入区（KB-ENTRY-01~05）

**UI hint**: yes

### Phase 21: 知识库配置页 UI

**Goal**: 左侧菜单新增「知识库配置」入口，知识库列表页支持查看/过滤/删除历史案例
**Depends on**: Phase 20
**Requirements**: KB-UI-01, KB-UI-02, KB-UI-03, KB-UI-04
**Success Criteria** (what must be TRUE):

  1. 左侧导航菜单出现「知识库配置」菜单项；点击后进入知识库列表页，不影响现有菜单项布局与路由
  2. 知识库列表页以表格形式展示所有历史案例（字段名/字段值/原文摘录/来源合同/入库时间），数据量大时支持分页或虚拟滚动保持页面流畅
  3. 用户在搜索框输入字段名关键字后，列表即时过滤只显示匹配条目
  4. 用户点击删除某条案例时出现二次确认弹窗；确认后该条从列表消失，取消后列表不变

**Plans**: 3 plans
 
Plans:
**Wave 1**
 
- [x] 21-01-PLAN.md — 后端 KB 分页/字段名过滤契约与回归测试（KB-UI-02, KB-UI-03）
 
**Wave 2** *(blocked on Wave 1 completion)*
 
- [x] 21-02-PLAN.md — 前端菜单/路由/配置页实现（分页列表+防抖过滤+删除确认刷新）（KB-UI-01~04）
 
**Wave 3** *(blocked on Wave 2 completion)*
 
- [x] 21-03-PLAN.md — 前端导航与交互回归测试门禁（KB-UI-01~04）
**UI hint**: yes

### Phase 22: RAG 检索与 LLM 注入

**Goal**: LLM 提取业绩报酬字段前自动语义检索 Top-K 相似案例注入 prompt；Settings 增加 Top-K 配置
**Depends on**: Phase 21
**Requirements**: KB-RAG-01, KB-RAG-02, KB-RAG-03, KB-RAG-04
**Success Criteria** (what must be TRUE):

  1. 处理一份含业绩报酬条款的合同时，LLM 收到的 prompt 中包含来自知识库的相似历史案例列表（字段名/字段值/原文摘录格式），且案例数量不超过 Settings 中配置的 Top-K 值
  2. 知识库为空（无任何历史案例）时，提取流程正常完成、无报错，LLM prompt 中不出现 few-shot 注入块
  3. 在 Settings 页面可看到「RAG Top-K」整数配置项（默认 3，范围 1–10），修改并保存后重启应用，新值生效且不丢失

**Plans**: 3 plans

Plans:
**Wave 1**

- [x] 22-01-PLAN.md — Electron 侧 RAG Top-K 类型/校验/重启注入链路（KB-RAG-04）

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 22-02-PLAN.md — 后端检索与 few-shot 注入（仅业绩报酬链路）+ 空库降级测试（KB-RAG-01~03）

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 22-03-PLAN.md — Settings 前端 RAG Top-K 配置项接入与表单回归测试（KB-RAG-04）

### Phase 23: PyInstaller 打包兼容与烟测

**Goal**: LanceDB 和 sentence-transformers 模型权重纳入打包，烟测验证全链路
**Depends on**: Phase 22
**Requirements**: KB-PKG-01, KB-PKG-02, KB-PKG-03
**Success Criteria** (what must be TRUE):

  1. 使用 `scripts/build.ps1` 构建的 CTRX 安装包中，LanceDB 及 pyarrow 相关包已通过 hiddenimports 纳入，安装后启动应用无「ModuleNotFoundError: lancedb」类错误
  2. sentence-transformers 模型权重以离线方式打入 `extraResources`，应用启动时通过 `SENTENCE_TRANSFORMERS_HOME` / `TRANSFORMERS_CACHE` 路径变量指向该目录；无网络环境下 embedding 生成正常运行
  3. 打包产物烟测全链路通过：PathB 录入 → embedding 生成 → LanceDB 持久化 → 语义检索 → RAG prompt 注入，全程无异常日志

**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. 文档解析 | v1.0 | — | Complete | 2026-05-26 |
| 2. 字段抽取 | v1.0 | — | Complete | 2026-05-26 |
| 3. Excel 导出 | v1.0 | — | Complete | 2026-05-26 |
| 4. API 层 | v1.0 | — | Complete | 2026-05-26 |
| 5. 前端界面 | v1.0 | — | Complete | 2026-05-26 |
| 6. 黄金回归 | v1.1 | — | Complete | 2026-05-26 |
| 7. 申赎费率第五表 | v1.1 | — | Complete | 2026-05-26 |
| 8. 路径 B JSON | v1.1 | — | Complete | 2026-05-26 |
| 9. LLM 校验层 | v1.1 | — | Complete | 2026-05-26 |
| 10. UI 导航与下载 | v1.1 | — | Complete | 2026-05-26 |
| 11. SQLite 迁移与路径修复 | v1.2 | 4/4 | Complete | 2026-05-28 |
| 12. PyInstaller 打包 | v1.2 | 2/2 | Complete | 2026-05-29 |
| 13. Electron 壳与 IPC | v1.2 | 2/2 | Complete | 2026-05-29 |
| 14. 构建流水线 | v1.2 | 3/3 | Complete | 2026-05-29 |
| 15. 后端并行与分表 API | v1.3 | 3/3 | Complete | 2026-05-29 |
| 16. 详情路由与子菜单骨架 | v1.3 | 3/3 | Complete | 2026-05-29 |
| 17. 五表独立工作页 | v1.3 | 3/3 | Complete | 2026-05-29 |
| 18. Hub 摘要与字段 B 专页 | v1.3 | 3/3 | Complete | 2026-05-29 |
| 19. 多文件上传与并行进度 UI | v1.3 | 3/3 | Complete | 2026-05-29 |
| 20. 知识库数据层 + PathB 录入 UI | v1.4 | 3/3 | Complete | 2026-06-02 |
| 21. 知识库配置页 UI | v1.4 | 3/3 | Complete   | 2026-06-02 |
| 22. RAG 检索与 LLM 注入 | v1.4 | 2/3 | In Progress|  |
| 23. PyInstaller 打包兼容与烟测 | v1.4 | 0/? | Not started | - |

---
*Roadmap updated: 2026-06-02 — v1.4 started (业绩报酬知识库与 RAG 增强, Phases 20–23)*
