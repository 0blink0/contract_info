---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: 抽取质量与导出扩展
status: ready_to_plan
last_updated: "2026-05-26T07:51:26.322Z"
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 20
---

# State: CTRX

## Project Reference

See: `contract_info/.planning/PROJECT.md` (updated 2026-05-26)

**Core value:** 上传 docx → 可导入 Excel + 路径 B 手录辅助 + 可解释校验  
**Current focus:** Phase 7 — 申赎费率导出
**Project root:** `contract_info/`

## Current Position

Phase: 7
Plan: Not started
| Field | Value |
|-------|-------|
| Milestone | v1.1 抽取质量与导出扩展 |
| Phase | **6** — 抽取质量与黄金回归 |
| Plan | 06-01 → 06-03（3 plans, 3 waves） |
| Status | Planned — ready for `/gsd-execute-phase 6` |

## Milestone v1.1 输入

- 黄金样例：`example/产品要素 - 副本(1).xlsx`、`产品运营费率导入模板.xlsx`、`产品申赎费率导入模板.xlsx`
- 合同：`石云中证1000…(1).docx`、`石云福禄1000…(1).docx`
- 图中误抽（管理人/投顾/外包/锁定期）为 v1.0 已知问题；部分规则修复已在仓库，本里程碑做回归与 LLM/校验闭环
- **字段调研入档：** `.planning/phases/06-extract-quality/06-FIELD-MATRIX.md`（12 项可抽、四分类可空、合同真值 vs 黄金表）

## Deferred from v1.0

| Item | Notes |
|------|-------|
| Phase 1 DB 集成验证 | Docker + alembic |
| 批量上传 | v2 BATCH-01 |
| PDF | v2 DOC-10 |
| audit-milestone v1.0 | 可选补跑 |

## Next Actions

1. `/gsd-execute-phase 6` — 按 Wave 0→1→2 执行 06-01~03
2. 确认生产 `OPENAI_API_KEY`（LLM 抽取 + 校验层）
3. 将 `example/*` 模板复制/同步到 `templates/`（若与现母版不一致）

---
*Updated: 2026-05-26*
