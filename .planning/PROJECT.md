# 合同要素抽取与 Excel 导入生成（CTRX）

## What This Is

面向私募综合业务管理系统的**半自动录入工具**：运营上传基金合同（首期仅 **docx** 测试），系统解析文档、按 `FIELD_SPEC.md` 抽取字段，填入官方导入模板（产品要素、运营费率等），生成**可下载、可修改**的 Excel，供系统在「模板导入」路径批量入库。每个上传文件在 **PostgreSQL** 中独立留档（解析结果、抽取 JSON、任务状态）。

与 `ai_bid_management`（招投标评标）为**独立子项目**；规划与代码均以 `contract_info/` 为根。

## Core Value

**上传一份 docx 合同 → 得到结构正确、可导入的 Excel，显著减少手抄模板时间。**

## Requirements

### Validated

（尚无 — 待首期交付验证）

### Active

- [ ] docx 解析为结构化 Document（章节、段落、表格）
- [ ] 按 FIELD_SPEC P1 字段抽取（规则 + LLM 归一化）
- [ ] 生成 `产品要素` / `运营费率` 导入用 xlsx
- [ ] Web 上传、任务状态、Excel 下载
- [ ] PostgreSQL 按文件保存解析与抽取结果
- [ ] 虚拟环境与可运行的抽取/填表测验代码

### Out of Scope

- **PDF / MinerU 解析** — 首期仅 docx；后续里程碑
- **系统页面手录**（业绩报酬、开放日等无 Excel 模板）— 路径 B，另立项
- **自动登录 CRM 写库** — 仅生成 Excel，人工导入
- **复用 bid_tool_agents 运行时** — 可参考模式，不耦合部署

## Context

- 业务材料：`contract_info/example/`（合同 docx、要素/费率 xlsx 模板）
- 字段规格：`contract_info/FIELD_SPEC.md`（77 列要素 + 费率 + 子表；P1 MVP 约 18+6 字段）
- 仓库内已有 `ai_bid_management/.planning/` 用于评标项目；**本项目规划在 `contract_info/.planning/`**
- 批量场景：管理人一次提供几十～上百份合同；首期可先单文件闭环

## Constraints

- **输入格式**：v1 仅 docx（`python-docx`）
- **输出格式**：与 `example/产品要素-2.xlsx`、`产品运营费率导入模板-1.xlsx` 列一致
- **数据存储**：PostgreSQL，粒度 = 一个上传文件一条主记录 + 关联 artifact
- **抽取策略**：规则优先，LLM 负责枚举映射与难字段（见 FIELD_SPEC）
- **依赖管理**：`contract_info` 下独立 venv，不污染仓库其他 Python 环境

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 规划目录 `contract_info/.planning/` | 与业务代码、模板同根；避免与 bid_management 根目录混淆 | — Pending |
| 首期路径 A（Excel 导入）only | 业务明确需求；页面手录无批量接口 | — Pending |
| docx-only 测试 | 降低首期复杂度；PDF 后置 | — Pending |
| 独立后端 + 简单前端 | 上传/下载/状态；对齐用户描述 | — Pending |

## Evolution

阶段切换或里程碑结束时更新：Validated / Active / Out of Scope、Key Decisions、「What This Is」是否仍准确。

---
*Last updated: 2026-05-25 after project initialization*
