# Phase 21: 知识库配置页 UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 21-知识库配置页 UI
**Areas discussed:** 导航入口位置与高亮、列表加载策略、筛选交互、删除流程

---

## 导航入口位置与高亮

| Option | Description | Selected |
|--------|-------------|----------|
| below-jobs-above-settings | 放在“文件列表”下方、“系统设置”上方 | ✓ |
| below-settings | 放在“系统设置”下方 | |
| top-level-near-upload | 放在“文件上传解析”附近 | |

**User's choice:** below-jobs-above-settings  
**Notes:** 强调业务入口优先级，不放在系统设置区域。

---

## 列表加载策略

| Option | Description | Selected |
|--------|-------------|----------|
| server-pagination | 服务端分页，翻页请求 | |
| all-at-once | 全量拉取，本地筛选分页 | |
| hybrid-firstpage | 首屏分页 + 筛选服务端查询（推荐） | ✓ |

**User's choice:** 按推荐来  
**Notes:** 采用推荐的折中方案，兼顾实现复杂度与规模适配。

---

## 筛选交互

| Option | Description | Selected |
|--------|-------------|----------|
| debounced-fieldname-only | 防抖即时查询，仅字段名过滤 | |
| debounced-multi-field | 防抖即时查询，字段名/字段值/来源合同 | ✓（初选） |
| enter-to-search | 回车触发查询 | |

**User's choice:** debounced-multi-field（初选）  
**Notes:** 经范围确认后，最终锁定 Phase 21 为字段名过滤，多字段搜索记为后续能力。

---

## 删除流程

| Option | Description | Selected |
|--------|-------------|----------|
| stay-and-refresh | 保留筛选并刷新当前结果 | ✓ |
| reset-filter-after-delete | 删除后重置筛选 | |
| optimistic-remove | 乐观更新，失败回滚 | |

**User's choice:** stay-and-refresh  
**Notes:** 删除不打断当前工作上下文。

---

## 删除确认与失败提示

| Option | Description | Selected |
|--------|-------------|----------|
| strict-clear | 明确不可恢复 + 后端错误细节 | ✓ |
| simple-friendly | 简短文案 + 通用错误 | |
| with-source-info | 增加来源与请求追踪信息 | |

**User's choice:** strict-clear  
**Notes:** 偏稳妥文案，强调不可恢复与可诊断性。

---

## Claude's Discretion

- 防抖时长与请求取消策略由后续 planner/researcher 按现有客户端模式确定。
- 分页与虚拟滚动的具体实现技术由后续计划阶段落地。

## Deferred Ideas

- 多字段搜索（字段名 + 字段值 + 来源合同）延期到后续 phase。
