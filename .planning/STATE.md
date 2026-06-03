---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: 业绩报酬知识库与 RAG 增强
status: complete
last_updated: "2026-06-03T10:00:00.000Z"
last_activity: "2026-06-03 -- v1.4 shipped: Phase 23 全部完成，字段级 RAG + KB LLM 提取 + 模型状态 UI"
progress:
  total_phases: 9
  completed_phases: 9
  total_plans: 28
  completed_plans: 28
  percent: 100
---

# State: CTRX

## Project Reference

See: `contract_info/.planning/PROJECT.md`

**Core value:** 上传 docx → 可导入 Excel + 路径 B 手录辅助 + 可解释校验（本地桌面，无服务器依赖）
**Current focus:** v1.4 shipped — 下一版本待规划
**Project root:** `contract_info/`

## Current Position

Phase: Phase 23 — 完成
Status: **v1.4 SHIPPED 2026-06-03**
Last activity: Phase 23-04 烟测验收 + RAG 架构升级（字段级并行召回 + KB LLM 字段提取 + 模型等待逻辑 + 全局状态 UI）

Progress: [██████████] 100%

## Performance Metrics

| Metric | Value |
|--------|-------|
| v1.4 phases | 4 (20–23) |
| Plans complete (v1.4) | 12/12 |

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
- Phase 23-03: backendChildEnv() 独立复制三候选 resourcesDir 解析，避免与 backendEntrypoint() exe 路径逻辑耦合
- Phase 23-04: 字段级并行 RAG 召回（5 字段各一次向量查询）取代文档级单次查询
- Phase 23-04: KB few-shot LLM 字段提取优先于 regex 规则；相似段落本身作为 snippet 展示
- Phase 23-04: 模型加载时提取不跳过，等待最多 300s（计入提取时间）
- Phase 23-04: `useKbStatus` 单例 composable，侧边栏常驻状态点

### Todos

- [x] `/gsd-plan-phase 20` — 知识库 UI（菜单 + PathB 录入表格）✓ 2026-06-02
- [x] `/gsd-execute-phase 21` — 执行 3 个计划（Wave 1/2/3）✓ 2026-06-02
- [x] `/gsd-execute-phase 22` — 执行 RAG 检索与 LLM 注入计划 ✓ 2026-06-02
- [x] `/gsd-execute-phase 23` — PyInstaller 打包兼容与烟测 ✓ 2026-06-03
- [ ] `/gsd-complete-milestone` — 归档 v1.4 ROADMAP/REQUIREMENTS（待执行）

### Blockers

_None_

## Session Continuity

_Last update: 2026-06-03 — v1.4 shipped，所有 Phase 23 计划执行完毕_

## Archived Context

Decisions are logged in PROJECT.md Key Decisions table.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v1.5+ | PATHB-EX-01/02 路径B枚举映射增强 | Deferred | v1.2 start |
| v1.5+ | docx 真实页码（解析层） | Deferred | v1.3 ship |
| v1.2 | PKG-03 Linux clean-VM verify | Deferred | v1.2 close |
| v1.5+ | RAG 召回质量评估（相似度阈值调优） | Deferred | v1.4 ship |
