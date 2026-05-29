# Phase 16 Discussion Log

**Phase:** 16 — 详情路由与子菜单骨架  
**Date:** 2026-05-29  
**Mode:** 默认锁定（用户跳过问卷；延续 Phase 15「按推荐走」偏好）

## Inputs

- ROADMAP Phase 16 Success Criteria（4 条）
- REQUIREMENTS: NAV-01, NAV-02, NAV-03, FE-02
- research/ARCHITECTURE.md（Layout + AppLayout 子菜单 + provide）
- 现有 v1.2：`JobDetailView` + 单体 `JobDetail.vue`

## Key Resolutions

| Topic | Decision |
|-------|----------|
| 路由路径 | `/jobs/:id`、`/jobs/:id/tables/:tableKey`、`/jobs/:id/field-b`（ROADMAP 优先于调研扁平路径） |
| 子菜单位置 | AppLayout 动态 `el-sub-menu`，非 Layout 内第二栏 |
| 列表入口 | `job-hub`，默认 Hub |
| 轮询 | 仅 JobDetailLayout + inject；子页禁止 useJobPoll |
| v1.2 单体页 | 从路由卸载，文件保留供 17–18 拆分 |
| Phase 16 子页 | Hub/表/字段 B 均为占位 + 导航，不调分表 API |

## Output

- `16-CONTEXT.md` — D-01～D-27，Ready for planning

## Next Step

`/gsd-plan-phase 16`
