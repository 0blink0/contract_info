# 合同要素抽取与 Excel 导入生成（CTRX）

## What This Is

面向私募综合业务管理系统的**半自动录入工具**：运营上传基金合同（**docx**），系统解析、抽取字段，生成可导入 Excel（产品要素、运营费率、申赎费率、锁定期、分级份额），并输出**业绩报酬/开放日** JSON 供 CRM 手录；可选 **LLM 校验层** 核对摘录与填值是否一致。

独立子项目，根目录 `contract_info/`。

## Core Value

**上传一份 docx → 得到接近人工填写质量的 Excel + 可手录的结构化草稿 + 可解释的校验报告。**

## Current State

- **Shipped:** v1.1（2026-05-26）
- **Delivery scope:** 抽取质量黄金回归、申赎费率第 5 张导入表、路径 B JSON（业绩报酬/开放日）、LLM 校验结果 API/UI 展示
- **Runtime:** FastAPI + Vue + PostgreSQL + Docker；LLM 通过 OpenAI-compatible 接口可切换模型（如 qwen）
- **Recent closure:** 里程碑审计 gap 已清理（ValidationPanel 可用性 gate、需求追溯补齐、Nyquist frontmatter 补齐）

## Current Milestone: v1.2 桌面化交付

**Goal:** 将 CTRX 从 Docker-only 部署转型为 Electron 桌面应用，双击安装包即用，内嵌 Python + SQLite，首次启动完成 LLM 配置。

**Target features:**
- Electron 桌面壳（Windows + Linux）
- PyInstaller 打包 Python/FastAPI 后端为可执行文件
- SQLite 替换 PostgreSQL（SQLAlchemy 迁移适配）
- Electron 管理 Python 子进程生命周期
- 首次启动设置向导（LLM API Base + Key + Model）
- 应用内 Settings 页面（可随时修改）
- 构建流水线：Windows .exe 安装包 + Linux AppImage/deb

## Requirements

### Validated (v1.0)

- ✓ docx 解析、P1+ 扩展抽取、4 xlsx、API/UI、PostgreSQL、Docker — v1.0

### Active (v1.2)

- Electron 桌面壳与子进程管理
- PyInstaller Python 运行时打包
- SQLite 替换 PostgreSQL
- 首次启动 LLM 设置向导
- 应用内 Settings 页面
- Windows/Linux 构建流水线

### Out of Scope（当前）

- 黄金 xlsx 作为线上自动批改器
- CRM 自动录入、PDF、批量队列（见 v2）
- 路径 B 枚举映射增强（→ v1.3）
- 批量多文件上传/ZIP（→ v2 预研）

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

**Milestone v1.1（2026-05-26）：** 从「能导出」转向「接近人工填写 + 可校验」，并完成五表、路径 B、校验闭环。

## Constraints

- 输入：docx；LLM 抽取与校验依赖 `.env` API Key
- 样例合同与 xlsx 在 `example/`，不提交敏感生产数据

<details>
<summary>Archived Milestone Notes (v1.1 planning snapshot)</summary>

- 以 `example/` 双合同 + 黄金样例为主验证基线
- 完成 Phase 6–10 全链路（规则、导出、API、前端、文档）
- 子表导出修复与前端导航优化在同一里程碑收口

</details>

---

*Last updated: 2026-05-28 — v1.2 milestone started*
