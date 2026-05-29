# Milestones

## v1.0 MVP (Shipped: 2026-05-26)

**Phases completed:** 5 phases, 10 plans

**Delivered:** docx 解析 → 规则/LLM 抽取 → Excel 导出 → FastAPI + Vue 运营界面 → Docker 一键部署

**Key accomplishments:**

1. **Phase 1** — docx 解析为 Document JSON（outline/blocks），PostgreSQL `contract_files`，CLI `parse`
2. **Phase 2** — P1 字段抽取管道（规则 + 章节窗 LLM）、字典校验、`extract` CLI
3. **Phase 3** — 按官方母版填充产品要素与运营费率 xlsx，`export` CLI
4. **Phase 4** — `POST /upload`、`POST /jobs/{id}/run`（202 异步）、状态轮询、Excel 下载 API
5. **Phase 5** — Element Plus 前端：上传、任务列表、步骤条、warnings、双下载

**Post-roadmap enhancements (same repo, not separate GSD phases):**

- 导出内容预览、任务删除、全表字段尝试抽取、锁定期/分级份额子表与 **4 个 Excel** 下载
- Docker / alembic 部署修复（国内镜像、健康检查）

**Known gaps (tech debt for v1.1+):**

- 无里程碑审计（`v1.0-MILESTONE-AUDIT.md` 未跑）；建议下一里程碑前 `/gsd:audit-milestone`
- Phase 1 DB 集成验证（Docker + `alembic upgrade head`）未在 STATE 勾完
- 批量多文件上传 / ZIP、路径 B（业绩报酬/开放日）手录模块未做
- `REQUIREMENTS.md` 追溯表曾标 API/UI 为 Pending，代码已交付（归档时已更正）

**Archives:**

- [milestones/1.0-ROADMAP.md](milestones/1.0-ROADMAP.md)
- [milestones/1.0-REQUIREMENTS.md](milestones/1.0-REQUIREMENTS.md)

**Tag:** `v1.0`

---

## v1.1 抽取质量与导出扩展 (Shipped: 2026-05-26)

**Phases completed:** 5 phases (6–10), 15 plans

**Delivered:** 黄金回归、申赎第五表、path B JSON、LLM 校验、五表 UI/预览/下载

**Post-ship 子表修复（同一里程碑，见 `v1.1-TABLE-EXPORT-FIXES.md`）：**

- 申赎/分级导出清空母版样例行（修复多基金 20 行假象）
- 分级份额按份额分类 + A–D 抽取；福禄/石云命名；防 LLM 稀疏覆盖
- 锁定期字段归一 + 规则/LLM merge；每文件单业务 sheet

**Post-ship 前端（同一里程碑，见 `v1.1-FRONTEND-NAV.md`）：**

- 左侧菜单：**文件上传解析** / **文件列表** / **文件详情**（Vue Router）
- 上传页展示进度，完成后「查看结果」进入详情
- 切换任务时校验/PathB 面板随 `jobId` 刷新

**Tag:** `v1.1`（规划内交付，含子表修复与前端导航）

**Audit:** ✅ passed (`.planning/v1.1-MILESTONE-AUDIT.md`, 2026-05-28)  
**Archive:** [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md), [milestones/v1.1-REQUIREMENTS.md](milestones/v1.1-REQUIREMENTS.md)

---

## v1.2 桌面化交付 (Shipped: 2026-05-29)

**Phases completed:** 4 phases (11–14), 11 plans

**Delivered:** SQLite 迁移 + PyInstaller 打包 + Electron 生命周期壳 + Windows/Linux 一键安装包 → CTRX 从 Docker-only 转型为桌面应用

**Key accomplishments:**

1. **Phase 11** — SQLite 完整迁移：PostgreSQL 方言类型全替换（JSONB→JSON, UUID→Uuid），WAL 模式开启，CTRX_DATA_DIR 路径隔离，programmatic Alembic on startup
2. **Phase 12** — PyInstaller 单 spec 打包：hiddenimports 审计基线 + CI 门禁（check_hiddenimports_diff.py）+ Windows 主链路烟测通过（health→upload→extract→download）
3. **Phase 13** — Electron 主进程状态机：子进程生命周期管理、健康轮询（300ms/30s）、崩溃自动重试（最多 3 次）、SIGTERM→SIGKILL 优雅退出；3 通道 contextBridge IPC + electron-store
4. **Phase 13** — 首启向导（Welcome→凭证→连接测试）+ Settings 页面（保存后重启事务 + 失败回滚配置）；向导未完成封闭主界面
5. **Phase 14** — 构建流水线：electron-builder 26.x NSIS + AppImage + deb 一键构建，产出 CTRX-Setup-1.2.0.exe（133MB）
6. **Phase 14** — 修复 TypeScript 6 NodeNext 双标志（allowImportingTsExtensions+rewriteRelativeImportExtensions）、electron-builder 26.x 版本注入语法、signAndEditExecutable=false

**Stats:** 4 phases · 11 plans · 57 files changed · 10,908 insertions · 2 days (2026-05-28 → 2026-05-29)

**Known deferred items at close:** 1 (PKG-03 Linux clean-VM verify, user-approved — see STATE.md Deferred Items)

**Archives:**

- [milestones/v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)
- [milestones/v1.2-REQUIREMENTS.md](milestones/v1.2-REQUIREMENTS.md)

**Tag:** `v1.2`

---
