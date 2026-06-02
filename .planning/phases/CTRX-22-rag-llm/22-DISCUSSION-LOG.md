# Phase 22: RAG 检索与 LLM 注入 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 22-RAG 检索与 LLM 注入
**Areas discussed:** 检索触发范围、Prompt 注入结构、空库降级、Top-K 生效方式

---

## 检索触发与范围

| Option | Description | Selected |
|--------|-------------|----------|
| perf-fee-only | 仅业绩报酬链路触发 | ✓ |
| pathb-all | PathB 全链路触发 | |
| hybrid-flagged | 默认业绩报酬，保留扩展开关 | |

**User's choice:** perf-fee-only  
**Notes:** 先控制范围，降低对其它字段提取稳定性的影响。

---

## Prompt 注入形态

| Option | Description | Selected |
|--------|-------------|----------|
| ranked-compact | 按相似度排序、紧凑案例列表、不显式分数 | ✓ |
| ranked-with-score | 显式带分数注入 | |
| group-by-field | 按字段分组后注入 | |

**User's choice:** ranked-compact  
**Notes:** 优先保证提示词长度与稳定性。

---

## 空库与弱命中降级

| Option | Description | Selected |
|--------|-------------|----------|
| no-inject | 无案例则完全不注入 few-shot | ✓ |
| inject-empty-note | 注入空案例占位提示 | |
| threshold-no-inject | 设阈值后低分不注入 | |

**User's choice:** no-inject  
**Notes:** 采用最干净降级路径，避免引入额外提示噪声。

---

## Top-K 配置生效方式

| Option | Description | Selected |
|--------|-------------|----------|
| restart-apply | 保存后重启后端生效 | ✓ |
| hot-apply | 保存后热更新立即生效 | |
| hybrid-preview | 前端即时更新，后端重启生效 | |

**User's choice:** restart-apply  
**Notes:** 与现有 Settings 机制保持一致，降低实现复杂度。

---

## Claude's Discretion

- 具体检索函数放置于 service 层或 extract 层由后续计划决定。
- 注入模板在 `performance_fee.py` 与 `chapter_prompts.py` 的具体拼接位置由实现阶段细化。

## Deferred Ideas

- PathB 全字段 RAG 化
- 相似度阈值策略与重排
- 相似度分数对模型/UI 的可见化
