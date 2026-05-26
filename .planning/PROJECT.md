# 合同要素抽取与 Excel 导入生成（CTRX）

## What This Is

面向私募综合业务管理系统的**半自动录入工具**：运营上传基金合同（**docx**），系统解析、抽取字段，生成可导入 Excel（产品要素、运营费率、申赎费率、锁定期、分级份额），并输出**业绩报酬/开放日** JSON 供 CRM 手录；可选 **LLM 校验层** 核对摘录与填值是否一致。

独立子项目，根目录 `contract_info/`。

## Core Value

**上传一份 docx → 得到接近人工填写质量的 Excel + 可手录的结构化草稿 + 可解释的校验报告。**

## Current Milestone: v1.1 抽取质量与导出扩展

**Goal:** 以 `example/` 中两份石云合同及人工填好的模板为黄金标准，提升抽取准确率，补齐申赎费率导出与路径 B、LLM 校验。

**Target features:**

- 抽取质量加固（当事人、锁定期、开放日等；黄金 pytest 回归）
- 第 **5** 个 Excel：**产品申赎费率**（`example/产品申赎费率导入模板.xlsx`）
- 路径 B JSON：**业绩报酬**、**开放日**（不进 CRM 自动写库）
- LLM **校验层**：值 vs 合同摘录，**不用** 黄金表做运行时校验
- API/前端：5 表下载 + JSON + 校验展示

## Current State (v1.0 shipped)

- 4 个 xlsx 导出、规则+LLM 抽取、Web + Docker
- 仓库内已有部分规则修复（石云合同样本），**生产环境需 pull + 重建 + LLM Key** 才与本地一致

## Requirements

### Validated (v1.0)

- ✓ docx 解析、P1+ 扩展抽取、4 xlsx、API/UI、PostgreSQL、Docker — v1.0

### Active (v1.1)

见 [REQUIREMENTS.md](REQUIREMENTS.md)（QUAL / XLS / PATHB / VAL / API / UI / TEST，共 20 条）

### Out of Scope (v1.1)

- 黄金 xlsx 作为线上自动批改器
- CRM 自动录入、PDF、批量队列（见 v2）

## Context

- 开发黄金样例：`example/产品要素 - 副本(1).xlsx`、`example/产品运营费率导入模板.xlsx`、`example/产品申赎费率导入模板.xlsx`
- 字段规格：`FIELD_SPEC.md`（本里程碑需更新）
- v1 归档：`.planning/milestones/1.0-*`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 黄金样例仅 dev/UAT | 避免把运营手工表当生产真值 | v1.1 采用 |
| 校验层只看摘录 | 可解释、可审计 | v1.1 采用 |
| 路径 B 仍 JSON 手录 | 无 CRM 母版 Excel | v1.1 采用 |
| 申赎费率独立第 5 表 | 业务新增导入模板 | v1.1 采用 |

## Evolution

**Milestone v1.1（2026-05-26）：** 从「能导出」转向「接近人工填写 + 可校验」；新增申赎费率与路径 B。

## Constraints

- 输入：docx；LLM 抽取与校验依赖 `.env` API Key
- 样例合同与 xlsx 在 `example/`，不提交敏感生产数据

---

*Last updated: 2026-05-26 — milestone v1.1 started*
