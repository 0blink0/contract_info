# Phase 7：申赎费率导出 — 调研

**调研日期：** 2026-05-26  
**领域：** 申赎费率规则抽取、多行 xlsx 导出、DB/API 扩展、黄金 E2E  
**置信度：** HIGH（现有 fee/share 模式可复用）/ MEDIUM（赎回分段解析边界）

<user_constraints>
## 用户约束（来自 07-CONTEXT.md）

- D-S01：份额分类表优先 + 申赎章补充
- D-S02：每份额至少认购+申购；赎回有则出
- D-S03：赎回分段 → 多行（区间列）
- D-S04：默认仅规则层，CI 不依赖 Key
- D-G01–G04：合同真值、基金名称后缀、代码有则填、未写明费率写 0
- D-T01–T04：templates 母版、修正 sheet 名、最小填列+warning、subscription_fee_rates.xlsx
- D-A01–A04：仅后端、download/subscription-fee-rates、并入 export_xlsx、扩展 golden 5 表
</user_constraints>

<phase_requirements>
| ID | 描述 | 调研结论 |
|----|------|----------|
| XLS-01 | 第 5 个申赎 xlsx，母版对齐 example | 复制 `example/产品申赎费率导入模板.xlsx` → `templates/`，修正 sheet 名为 `产品申赎费率导入模板`；新建 `subscription_workbook.py` 镜像 `fee_workbook.py` |
| XLS-02 | 列结构、份额类行数与黄金一致 | 黄金：两基金 × 4 份额 × 认购+申购（20 行）+ 部分赎回；按份额类展开行，不按黄金 1:1 硬比赎回行数（合同为准） |
| XLS-03 | 产品要素等 — Phase 6 已覆盖 | 本阶段不重复 |
| XLS-04 | DB path + 下载 API | 新增 `subscription_xlsx_path`；`export_service` 与 `export_xlsx` 五元组 |
| API-01 | GET download/subscription-fee-rates | 复制 `download/fee-rates` 模式 |
</phase_requirements>

## 摘要

Phase 7 在 **不改动前端** 前提下，沿 Phase 3 运营费率、Phase 6 黄金基础设施扩展：**抽取 → 第五文件导出 → DB 持久化 → 下载 API → golden 5 表 E2E**。核心新增 `SubscriptionFeeRow` + `subscription_rules.py`，导出侧 `fill_subscription_workbook`，流水线 `export_xlsx` 由 4 元组改为 5 元组（需同步 `export_service`、测试、golden runner）。

## 标准栈

| 层 | 选型 | 依据 |
|----|------|------|
| Schema | Pydantic `SubscriptionFeeRow` | 与 `FeeRateRow` 同模式，`extra=allow` |
| 抽取 | `subscription_rules.py` + `share_rules` 表数据 | CONTEXT D-S01 |
| 导出 | openpyxl + `column_map` 扩展 | `fee_workbook.py` 已验证 |
| DB | Alembic `005_subscription_xlsx_path` | 继 003/004 |
| API | FastAPI `FileResponse` | `jobs.py` 现有 4 端点 |
| 测试 | pytest golden 扩展 | `pipeline_runner` + `xlsx_diff` |

## 黄金样例结构（已读表）

- Sheet（修正后）：`产品申赎费率导入模板`
- 表头行：第 3 行
- 数据行：第 4 行起
- 列（节选）：基金名称、基金代码、申赎费类型、计费方式、费率生效日期、计费基准、区间开始/结束、费率类型、费率
- 石云 4 份额 × 认购 + 申购；福禄 4 份额 × 认购 + 申购；赎回费行较少

## 架构要点

### 1. Schema

```python
class SubscriptionFeeRow(BaseModel):
    基金名称: str | None = None
    基金代码: str | None = None
    申赎费类型: str | None = None  # 认购费/申购费/赎回费
    计费方式: str | None = None
    费率生效日期: str | None = None
    计费基准: str | None = None
    时间区间单位: str | None = None
    区间开始: str | None = None
    区间结束: str | None = None
    费率类型: str | None = None  # 百分比/金额
    费率: str | None = None
```

`ExtractionResult` 增加 `subscription_fees: list[SubscriptionFeeRow]`。

### 2. 抽取流程

1. `extract_share_classes_rules` → 份额类列表 + 分级份额代码/名称
2. 读份额分类表 block（`document.blocks` 表头含「年认购费率」「申购费率」等）→ 每类认购/申购 %
3. `windows["subscription"]` → 短期赎回分段 regex（`<180日` → 1% 等）→ 赎回多行
4. `expand_rows_per_share`：每份额至少 认购+申购；赎回按 D-S03
5. 缺费率 → 费率 `0` + warning（D-G04）；其他必填缺 → 空 + warning（D-T03）

### 3. 导出流水线变更面

| 文件 | 变更 |
|------|------|
| `export/pipeline.py` | 第五文件 `subscription_fee_rates.xlsx`；返回 5 路径 |
| `export/column_map.py` | `SUBSCRIPTION_SHEET`、表头行常量、`SUBSCRIPTION_EXTRACTION_TO_TEMPLATE` |
| `export/subscription_workbook.py` | `fill_subscription_workbook` |
| `export/validate_export.py` | 可选 `check_subscription_fees` |
| `services/export_service.py` | 解包 5 路径，写 `subscription_xlsx_path` |
| `models/contract_file.py` | 新列 |
| `api/schemas.py` | JobDetail 增加 path |
| `api/routes/jobs.py` | download 端点 |
| `extract/pipeline.py` | 调用 `extract_subscription_fees_rules` |
| `tests/golden/*` | 第五路径断言 |

**破坏性注意：** `export_xlsx` 签名变更 → 全仓库调用点需一次 PR 内改完（测试、CLI、export_service、golden）。

### 4. 母版入库脚本

规划任务中包含：复制 example → `templates/产品申赎费率导入模板.xlsx`，用 openpyxl **重命名 sheet**（一次性脚本或 plan 内 manual step + pytest 断言 sheet 名）。

## 勿用 / 陷阱

| 陷阱 | 说明 |
|------|------|
| 误用运营费率 sheet 名 | example 源文件 sheet 名错误，必须 D-T02 修正 |
| 默认填价外法 | 违反 D-T03；仅抽取到的列写入 |
| 黄金 xlsx 作费率真值 | 违反 D-G03；`contract_expected.subscription_fees` |
| 前端本阶段 | 违反 D-A01 |
| 赎回从全文误匹配 20天 | 复用 Phase 6 lock 修复思路，仅在 subscription 窗解析赎回 |

## 开放问题（Planner 定稿）

1. 福禄份额命名「A类」vs 石云「证券投资基金A」— 实现 `format_fund_name_for_subscription(全称, 份额类, 黄金风格=auto)`
2. `export_xlsx` 是否保持向后兼容（4 元组 + kwargs）— 建议 **直接 5 元组**，一次性改调用方

## 需求覆盖

| 需求 | 覆盖计划 |
|------|----------|
| XLS-01 | 07-01 + 07-02 |
| XLS-02 | 07-02 + 07-03 golden |
| XLS-04 | 07-02 + 07-03 API |
| API-01 | 07-03 |

---
*Phase 7 调研 — 2026-05-26*
