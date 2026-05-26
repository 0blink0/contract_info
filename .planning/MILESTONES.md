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
