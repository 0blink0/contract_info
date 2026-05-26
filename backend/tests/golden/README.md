# Golden 回归测试（Phase 6）

石云/福禄两份示例合同：`parse → extract（规则层，无 LLM）→ export` 与 **合同真值** 对齐。

## Critical 字段（与 `06-FIELD-MATRIX.md` §6 一致）

**合同对齐（必验）：**

- 基金全称、基金简称（合同有则验）
- 管理人、托管人（**禁止**用黄金 xlsx 当事人列断言）
- 风险等级、投资经理
- 投资目标、投资范围、投资限制、投资策略（`@pytest.mark.llm`）
- 预警线、止损线
- 锁定期（有条款时）或锁定期子表行
- 开放日规则（摘要）
- 运营费率：管理费、托管费、销售服务费、基金服务费及费率（%/年）；管理费/销售服务费按份额分类表 **A–D 多行**；托管费/基金服务费按产品级一行；断言时费率在任一行匹配即可

## 空值四分类（测试用语）

| 类 | 含义 | 测试处理 |
|----|------|----------|
| A | 合同无、模板可空 | `基金代码`、`成立日期`、`备案日期` 等 — 空不失败 |
| B | 合同无、黄金有人工填 | 不以黄金为准 |
| C | 合同有、Phase 6 Critical | 对 `contract_expected.json` 断言 |
| D | 扩展/运维列 | 软检查或 warn |

`无` / `不设` / 空字符串在归一化后等价（见 `helpers/normalize.py`）。

## 合同真值 vs 黄金 xlsx

- Critical 当事人、费率真值：**仅** `fixtures/contract_expected.json`（源自合同 docx 规则层）
- 黄金 xlsx（`example/产品要素 - 副本(1).xlsx` 等）仅用于列结构、表头、扩展列软检查
- **禁止**用黄金表中的管理人/托管人/外包与导出结果比对（石云黄金管理人「弈倍」等为人工列，非合同真值）

## 归一化（D-G03）

| 规则 | 函数 |
|------|------|
| 日期 `yyyy/m/d` | `normalize_cell` → `normalize_date_slash` |
| 去掉 `【】` 标注 | `normalize_cell` |
| 百分号 `1` / `1%` | `normalize_pct` |
| 机构名 trim | `normalize_party_name` |
| `无`/`不设`/空 | `empty_equiv` |

## CI 命令

```bash
cd contract_info
python -m pytest backend/tests/golden/ -q -m "not llm"
```

## LLM 可选（QUAL-03）

- 标记：`@pytest.mark.llm`
- 阈值：Critical 长文本字段非空率 ≥ 80%，且 LLM 运行显著高于 `LlmOff` 基线
- 字段：`投资目标`、`投资范围`、`投资限制`、`投资策略`、`风险等级`
- 本地：`python -m pytest backend/tests/golden/ -m llm`（需 `OPENAI_API_KEY`）
- DeepSeek：`OPENAI_BASE_URL=https://api.deepseek.com`，`LLM_MODEL=deepseek-chat`（或项目约定）

## 合并策略（QUAL-04）

`merge_field(..., field_name=...)` + `is_invalid_rule_value`：

- 规则值含误抽标记（保证、登记为私募基金管理人等）→ 视为 invalid，LLM 可胜出
- 当事人：有效规则机构名优先于 LLM
- 预警线/止损线：规则为「无」时保持「无」
- 长文本（投资目标等）：双方非空时取更长者

## 范围说明

- **不包含** `产品申赎费率导入模板.xlsx` 的 pass/fail（Phase 7）
- 不在 `validate_export` 或生产 pipeline 中 import 黄金 xlsx
