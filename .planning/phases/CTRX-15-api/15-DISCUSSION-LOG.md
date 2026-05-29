# Phase 15: 后端并行与分表 API - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 15-后端并行与分表 API
**Areas discussed:** 并行槽位、执行器、分表 preview、核对数据源、页码、export 范围、LLM 限流（用户委托「按推荐走」）

---

## 用户委托

| Option | Description | Selected |
|--------|-------------|----------|
| 逐项讨论六个灰区 | 每区 4 轮问答 | |
| **按推荐走** | 采用 v1.3 调研默认项，写入 CONTEXT D-01~D-23 | ✓ |

**User's choice:** 「按推荐走就行」
**Notes:** 未单独讨论 UI；Phase 15 纯后端。

---

## 并行槽位规则

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 IN_PROGRESS 占槽 | pending 不占；与 ARCHITECTURE 一致 | ✓ |
| pending 也占槽 | 上传即占坑 | |

**User's choice:** 调研推荐（Claude 锁定 D-01~D-03）

---

## 分表 preview 契约

| Option | Description | Selected |
|--------|-------------|----------|
| 新 `/preview/{section}` + 修复全量 PUT Optional | PITFALLS #1 预防 | ✓ |
| 仅新端点，不修复旧 PUT | 风险高 | |
| 废弃全量 PUT | 破坏 v1.2 至 Phase 17 | |

**User's choice:** 调研推荐（D-07~D-10）

---

## 核对表数据来源

| Option | Description | Selected |
|--------|-------------|----------|
| extraction 为主 + validation 附加 | API-02 四列完整 | ✓ |
| 仅过滤 validation items | 无 validation 时空表 | |

**User's choice:** 调研推荐（D-12~D-15）

---

## 页码列深度

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 15 契约 + 尽力填 page；无则 null+说明 | MEDIUM 置信度可接受 | ✓ |
| 完全 defer 到 post-v1.3 | 前端 Phase 17 无列 | |

**User's choice:** 调研推荐（D-16~D-18）

---

## 分表保存后 export

| Option | Description | Selected |
|--------|-------------|----------|
| 仍 `persist_export` 全五表 | 与 v1.2 一致、实现简单 | ✓ |
| 仅重导当前表 | 优化，defer | |

**User's choice:** 调研推荐（D-11）

---

## 并行 LLM 校验

| Option | Description | Selected |
|--------|-------------|----------|
| 全局 Semaphore(2) 削峰 | PITFALLS #5 预防 | ✓ |
| 三路与解析完全并行无限制 | 易 429 | |
| 校验改手动触发 | 改变 v1.2 行为 | |

**User's choice:** 调研推荐（D-19~D-21）

---

## Claude's Discretion

全部六个灰区由用户一次性委托，决策见 `15-CONTEXT.md` §Implementation Decisions。

## Deferred Ideas

见 CONTEXT.md `<deferred>`：batch upload、单表 export、PathB verification 合并。
