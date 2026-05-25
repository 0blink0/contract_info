# Phase 2: 字段抽取引擎 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-05-25  
**Phase:** 2-字段抽取引擎  
**Areas discussed:** P1 范围与输出形态, 规则 vs LLM 分工, LLM 接入, 溯源与校验, CLI 与入库

---

## P1 范围与输出形态

| Option | Description | Selected |
|--------|-------------|----------|
| 严格 18 字段 | 仅 MVP 18 列 | |
| 18 + 其它 P1 列 | 扩展 FIELD_SPEC 中其它 P1 | ✓ |
| 锁定期子表 | Phase 2 输出 lock_periods[] | |
| 仅主表摘要 | 锁定期摘要，无子表 | ✓ |
| 分级子表 | share_classes[] | |
| 仅份额结构枚举 | 无分级子表 | ✓ |
| 费率最少 | 管理费+托管费 | |
| 含投顾费 | +投资顾问费（若有） | ✓ |

## 规则 vs LLM 分工

| Option | Selected |
|--------|----------|
| 规则优先 + 章节窗口 LLM 补批 | ✓ |
| LLM 按章节窗口 | ✓ |
| 规则源：outline + keywords + 表格 | ✓ |
| 失败：重试 1 次 → partial + warnings | ✓ |

## LLM 接入

| Option | Selected |
|--------|----------|
| contract_info/.env 独立配置 | ✓ |
| 模型型号 .env.example，不锁死 | ✓ |
| 无 Key：pytest 跳过 LLM | ✓ |
| Pydantic schema 严格校验 | ✓ |

## 溯源与校验

| Option | Selected |
|--------|----------|
| block_id + section_id + snippet | ✓ |
| 置信度 high/medium/low | ✓ |
| 枚举不合规：warnings + suggestions | ✓ |
| 字典预导出 dicts/*.json | ✓ |

## CLI 与入库

| Option | Selected |
|--------|----------|
| parse / extract 分离 | ✓ |
| extraction_result + extraction_warnings 分列 | ✓ |
| status: parsed→extracting→extracted/failed | ✓ |
| 测验：18+ P1 大部分有值 | ✓ |

## Claude's Discretion

- 章节窗口 token 上限、result JSON 分区命名、迁移细节

## Deferred Ideas

- lock_periods[]、share_classes[]、路径 B JSON、golden diff、第二套内部参数 Excel
