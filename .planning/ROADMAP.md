# Roadmap: CTRX — 合同要素抽取

**Project root:** `contract_info/`  
**Planning:** `contract_info/.planning/`

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5（shipped 2026-05-26）→ [archive](milestones/1.0-ROADMAP.md)
- ✅ **v1.1 抽取质量与导出扩展** — Phases 6–10（shipped 2026-05-26）→ [archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 桌面化交付** — Phases 11–14（shipped 2026-05-29）→ [archive](milestones/v1.2-ROADMAP.md)
- 🚧 **v1.3 多文件并行与详情页重构** — Phases 15–19（in progress）

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

### v1.3 多文件并行与详情页重构 (Phases 15–19)

- [x] **Phase 15: 后端并行与分表 API** - ThreadPool 真并行、run 409 守门、分表 preview 与核对端点
- [x] **Phase 16: 详情路由与子菜单骨架** - JobDetailLayout 嵌套路由、左侧六链、Hub 占位与统一轮询
- [ ] **Phase 17: 五表独立工作页** - 每表可编辑 preview、摘录核对表、单表下载与 dirty 守卫
- [ ] **Phase 18: Hub 摘要与字段 B 专页** - Hub 摘要卡与校验入口、字段 B 摘录与 JSON 导出
- [ ] **Phase 19: 多文件上传与并行进度 UI** - ≤3 docx 选择与批量处理、上传页多任务进度轮询

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

- [ ] 17-01-PLAN.md — 分表 preview/verification API 客户端 + useSectionPreview（TBL-02）

**Wave 2**

- [ ] 17-02-PLAN.md — TablePreviewEditor + VerificationExcerptTable（TBL-01, TBL-03）

**Wave 3**

- [ ] 17-03-PLAN.md — JobTableView 编排、dirty 守卫、单表下载、测试（TBL-01~05）

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

**Plans**: TBD
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

**Plans**: TBD
**UI hint**: yes

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
| 16. 详情路由与子菜单骨架 | v1.3 | 0/? | Not started | — |
| 17. 五表独立工作页 | v1.3 | 0/? | Not started | — |
| 18. Hub 摘要与字段 B 专页 | v1.3 | 0/? | Not started | — |
| 19. 多文件上传与并行进度 UI | v1.3 | 0/? | Not started | — |

---
*Roadmap updated: 2026-05-29 — v1.3 多文件并行与详情页重构：Phases 15–19 已规划*
