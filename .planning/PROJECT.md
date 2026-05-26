# 合同要素抽取与 Excel 导入生成（CTRX）

## What This Is

面向私募综合业务管理系统的**半自动录入工具**：运营上传基金合同（**docx**），系统解析、按 `FIELD_SPEC.md` 抽取字段，生成可导入的 Excel（产品要素、运营费率、份额锁定期、分级份额），通过 Web 上传与下载。每份合同在 PostgreSQL 独立留档。

独立子项目，根目录 `contract_info/`（与 `ai_bid_management` 评标系统分离）。

## Core Value

**上传一份 docx 合同 → 得到结构正确、可导入的 Excel，显著减少手抄模板时间。**

## Current State (v1.0 shipped 2026-05-26)

- **解析：** python-docx → Document JSON（章节 + 段落/表格 blocks）
- **抽取：** 规则 + 分章节 LLM；产品要素主表广泛尝试；子表（锁定期、分级份额）
- **导出：** 4 个 xlsx（产品要素、运营费率、锁定期、分级份额）
- **服务：** FastAPI（upload / run / jobs / preview / download / delete）+ Vue 3 前端
- **部署：** Docker Compose（postgres + api + web），见 `README.md`
- **测试：** pytest 覆盖解析、抽取、导出、API；生产 E2E 需配置 LLM 与 Docker

## Requirements

### Validated (v1.0)

- ✓ docx 解析为结构化 Document — v1.0
- ✓ P1 字段抽取（规则 + LLM）与字典校验 — v1.0（v1.1 扩展为更广字段尝试）
- ✓ 生成产品要素 / 运营费率 xlsx — v1.0（v1.1 增至 4 个模板文件）
- ✓ Web 上传、任务状态、Excel 下载 — v1.0
- ✓ PostgreSQL 按文件保存解析与抽取结果 — v1.0
- ✓ venv、CLI、pytest 测验链路 — v1.0

### Active (next milestone — draft)

- [ ] 批量多文件上传与并行/队列处理
- [ ] 路径 B 辅助 JSON（业绩报酬提取设置、开放日规则）供运营对照手录
- [ ] PDF 合同解析（MinerU 或等价）
- [ ] 里程碑级 UAT 与 `/gsd:audit-milestone` 闭环
- [ ] NER 或领域词典增强（管理人/托管人/金额）

### Out of Scope

- **CRM 页面自动写库** — 仅生成 Excel，人工导入；业绩报酬/开放日仍在业务系统手录
- **与 bid_tool_agents 共用部署** — 独立栈
- **首期 PDF** — 已移至 v1.1 候选（v1.0 仅 docx）

## Context

- 模板：`templates/`、`example/`
- 字段规格：`FIELD_SPEC.md`
- 规划：`contract_info/.planning/`；v1 归档见 `milestones/1.0-*`
- 已部署示例：`http://` + 服务器 8080（见会话记录）

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 规划目录 `contract_info/.planning/` | 与代码同根 | ✓ Good |
| 路径 A（Excel 导入）only | 业务批量导入模板 | ✓ Good；路径 B 仍手录 |
| docx-only v1 | 降复杂度 | ✓ Good；PDF 后置 |
| 上传与 run 分离 | 运营可控、可重试 | ✓ Good |
| 规则优先 + LLM 分窗 | 成本与准确率平衡 | ✓ Good |
| Docker 独立 compose | 一键交付 | ✓ Good |

## Next Milestone Goals

1. **批量与吞吐** — 多 docx、队列、并发上限
2. **质量与验收** — audit-milestone、verify-work、生产合同样本集
3. **路径 B 辅助** — 从合同抽「业绩报酬/开放日」结构化草稿（不进 Excel 母版）
4. **可选 NER** — 机构名、金额、日期 span 层

## Constraints

- 输入：v1.0 docx only；输出对齐官方导入母版列
- PostgreSQL 存 parse/extract/路径；大文件落盘 `uploads/`、`exports/`
- 独立 Python venv；LLM 通过 `.env` 配置

---

*Last updated: 2026-05-26 after v1.0 milestone*
