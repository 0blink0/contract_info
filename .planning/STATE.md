---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: 业绩报酬知识库与 RAG 增强
status: executing
last_updated: "2026-06-03T02:02:36.409Z"
last_activity: "2026-06-03 -- 23-03 complete: backendChildEnv() model env injection + D-08 guard + extraResources models/**"
progress:
  total_phases: 9
  completed_phases: 8
  total_plans: 28
  completed_plans: 27
  percent: 89
---

# State: CTRX

## Project Reference

See: `contract_info/.planning/PROJECT.md`

**Core value:** 上传 docx → 可导入 Excel + 路径 B 手录辅助 + 可解释校验（本地桌面，无服务器依赖）
**Current focus:** v1.4 业绩报酬知识库与 RAG 增强（Phases 20–23）
**Project root:** `contract_info/`

## Current Position

Phase: Phase 23 — PyInstaller 打包兼容与烟测
Plan: 23-04-PLAN.md (next, Wave 2)
Status: Executing (3/4 plans complete)
Last activity: 2026-06-03 -- 23-03 complete: backendChildEnv() model env injection + D-08 guard + extraResources models/**

Progress: [██████████] 96%

## Performance Metrics

| Metric | Value |
|--------|-------|
| v1.3 phases | 5 (15–19) |
| v1.3 requirements | 22 + 5 post-ship UX |
| Plans complete (v1.3) | 15/15 |

## Accumulated Context

### Decisions

- 向量知识库选用 LanceDB（本地文件，无服务器，PyInstaller 兼容）
- Embedding 使用 sentence-transformers 本地模型（多语言，支持中文）
- KB 固定 4 个字段：业绩报酬提取方式 / 业绩基准类型 / 门槛净值类型 / 提取时点
- RAG 注入点：`performance_fee.py` / `chapter_prompts.py` 的 prompt 构建处
- Phase 22-01: `ragTopK` 默认值固定为 3，且在 store 层强制 1-10 整数校验
- Phase 22-01: Electron 后端子进程环境注入 `RAG_TOP_K`，沿用保存后重启生效机制
- Phase 22-02: 仅 fees 链路触发 KB Top-K 检索并注入 performance fee prompt
- Phase 22-02: 注入块固定三元组（字段名/字段值/原文摘录），不包含 score
- Phase 23-01: bge-m3 以 flat local-path 格式（model.save()）存入 electron/resources/models/bge-m3/，通过 local_files_only=True 离线加载
- Phase 23-01: torch 安装 CPU-only variant（--index-url whl/cpu），避免 CUDA wheel 额外体积
- Phase 23-02: windows_hidden 仅扩展（不修改 common_hidden/linux_hidden）；sentence_transformers.models namespace package WARNING 属已知限制，不阻断发布
- Phase 23-03: backendChildEnv() 独立复制三候选 resourcesDir 解析，避免与 backendEntrypoint() exe 路径逻辑耦合；package.json 使用 Option A（追加到现有 filter 数组，最小化差异）

### Todos

- [x] `/gsd-plan-phase 20` — 知识库 UI（菜单 + PathB 录入表格）✓ 2026-06-02
- [x] `/gsd-execute-phase 21` — 执行 3 个计划（Wave 1/2/3）✓ 2026-06-02
- [ ] `/gsd-execute-phase 22` — 执行 RAG 检索与 LLM 注入计划
- [ ] `/gsd-complete-milestone` — 归档 v1.3 ROADMAP/REQUIREMENTS（仍待执行）

### Blockers

_None_

## Session Continuity

_Last update: 2026-06-03 — 23-03 complete (backendChildEnv() 模型 env 注入 + D-08 guard + package.json extraResources models/**); next: 23-04 烟测清单文档_

## Archived Context

Decisions are logged in PROJECT.md Key Decisions table.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v1.3+ | PATHB-EX-01/02 路径B枚举映射增强 | Deferred | v1.2 start |
| v1.3+ | docx 真实页码（解析层） | Deferred | v1.3 ship |
| v1.2 | PKG-03 Linux clean-VM verify | Deferred | v1.2 close |
