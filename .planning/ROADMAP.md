# Roadmap: CTRX — 合同要素抽取

**Project root:** `contract_info/`  
**Planning:** `contract_info/.planning/`

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5（shipped 2026-05-26）→ [archive](milestones/1.0-ROADMAP.md)
- ✅ **v1.1 抽取质量与导出扩展** — Phases 6–10（shipped 2026-05-26）→ [archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 桌面化交付** — Phases 11–14（shipped 2026-05-29）→ [archive](milestones/v1.2-ROADMAP.md)

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

---
*Roadmap updated: 2026-05-29 — v1.2 桌面化交付 shipped, milestone archived*
