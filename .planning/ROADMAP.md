# Roadmap: CTRX — 合同要素抽取

**Project root:** `contract_info/`  
**Planning:** `contract_info/.planning/`

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5（shipped 2026-05-26）→ [archive](milestones/1.0-ROADMAP.md)
- 🚧 **v1.1 抽取质量与导出扩展** — Phases 6–10（规划中）

## Phases（v1.1）

| # | Phase | Goal | Requirements | Success criteria |
|---|-------|------|--------------|----------------|
| 6 | 抽取质量与黄金回归 | 修复当事人/锁定期等误抽；两合同 pytest 对齐 example | QUAL-01–04, TEST-01 | ① 石云两合同管理人/托管人无风险散文 ② 锁定期=180天、开放日含排期 ③ 黄金 diff 测试 CI 通过 |
| 7 | 申赎费率导出 | 第 5 个 xlsx + DB/API | XLS-01–04, API-01 | ① 申赎模板列正确 ② 每份额类≥认购/申购/赎回行 ③ 下载端点可用 |
| 8 | 路径 B JSON | 业绩报酬 + 开放日手录草稿 | PATHB-01–04 | ① JSON schema 稳定 ② 含摘录 ③ API/前端可查看 |
| 9 | LLM 校验层 | 值 vs 摘录合理性审查 | VAL-01–04, TEST-02 | ① 矛盾样例 fail ② 结果持久化 ③ 前端高亮 |
| 10 | 集成与文档 | 五表 UI、部署说明、FIELD_SPEC | API-02, UI-01–02, TEST-03 | ① 单任务 5 xlsx + JSON + 校验 ② README 更新 ③ Docker 环境 LLM 说明 |

<details>
<summary>✅ v1.0 MVP (Phases 1–5) — SHIPPED 2026-05-26</summary>

| # | Phase | Plans | Status |
|---|-------|-------|--------|
| 1 | 项目骨架与 docx 解析 | 2/2 | Complete |
| 2 | 字段抽取引擎 | 2/2 | Complete |
| 3 | Excel 模板填充 | 2/2 | Complete |
| 4 | 后端 API | 2/2 | Complete |
| 5 | 前端上传与下载 | 2/2 | Complete |

详见 [milestones/1.0-ROADMAP.md](milestones/1.0-ROADMAP.md)。

</details>

### Phase 6: 抽取质量与黄金回归

**Goal:** 输出接近 `example/` 人工填写结果；消除图中类错误（管理人/投顾/外包/锁定期）。

**调研入档:** `phases/06-extract-quality/06-FIELD-MATRIX.md`（12 项可抽取性、四分类可空性、合同真值 vs 黄金表）。

**Plans（待 `/gsd:plan-phase 6` 细化）:**

1. 合并规则修复入库（party_helpers、费用表、投资章节全文规则）+ `merge_field` 误抽策略
2. `tests/golden/`：两 docx + 三 xlsx diff 框架（归一化日期/空码）
3. LLM 开关与章节窗截断排查（石云/福禄）

**Requirements:** QUAL-01–04, TEST-01

---

### Phase 7: 申赎费率导出

**Goal:** 新增 `产品申赎费率导入模板` 导出（按 A/B/C/D 份额类多行）。

**Plans:**

1. `subscription_fee` 抽取（份额分类表 + 申赎章节）+ schema
2. `export/subscription_workbook.py` + alembic `subscription_xlsx_path`
3. 下载 API + 预览 tab

**Requirements:** XLS-01–04, API-01

---

### Phase 8: 路径 B JSON

**Goal:** 业绩报酬、开放日结构化草稿供 CRM 手录，不进 Excel 母版。

**Plans:**

1. `path_b/schemas.py` + 规则/LLM 抽取
2. 持久化 `path_b_json` 列或 `extraction_result.path_b`
3. API + 前端 JSON 面板

**Requirements:** PATHB-01–04

---

### Phase 9: LLM 校验层

**Goal:** 抽取后自动审查「值是否与摘录一致、是否合理」。

**Plans:**

1. `validate/llm_validator.py`：字段批校验 prompt
2. 与 `FieldValue.snippet` / block 原文联动
3. warnings UI 分级（fail/warn/pass）

**Requirements:** VAL-01–04, TEST-02

---

### Phase 10: 集成与文档

**Goal:** 运营可用的完整交付面。

**Plans:**

1. 前端 5 下载 + 路径 B + 校验摘要
2. `FIELD_SPEC.md` / README / `.env.example`
3. 可选：服务器部署 checklist（LLM key、alembic）

**Requirements:** API-02, UI-01–02, TEST-03

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 6 | v1.1 | 0/3 | Not started | — |
| 7 | v1.1 | 0/3 | Not started | — |
| 8 | v1.1 | 0/3 | Not started | — |
| 9 | v1.1 | 0/3 | Not started | — |
| 10 | v1.1 | 0/3 | Not started | — |

---
*Roadmap updated: 2026-05-26 — milestone v1.1 started*
