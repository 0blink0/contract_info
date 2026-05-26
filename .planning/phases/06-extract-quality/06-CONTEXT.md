# Phase 6: 抽取质量与黄金回归 - Context

**Gathered:** 2026-05-26  
**Status:** Ready for planning

<domain>
## Phase Boundary

在 **不改变 v1.1 新表/路径 B/校验层范围** 的前提下，使 **parse → extract → export（现有 4 类 xlsx）** 在石云两份合同样本上的结果 **接近 `example/` 人工填写表**；消除当事人误抽、锁定期/开放日/预警止损等关键错误；建立 **可重复的黄金 pytest**，供后续阶段防回归。

**本阶段包含：**

- 规则层与 `merge_field` 加固（当事人、投资章节、费用表等）
- 黄金样例回归测试（`example/` docx + xlsx，**仅 CI/dev**）
- LLM 可用时的抽取质量基线（QUAL-03），与规则层测试分离
- 现有 4 个导出文件与黄金 xlsx 的结构/关键字段对比

**本阶段不包含：**

- 申赎费率第 5 表（Phase 7）
- 路径 B JSON（Phase 8）
- LLM 校验层（Phase 9）
- 五表 UI 集成（Phase 10）
- 用黄金 xlsx 做线上任务自动批改

</domain>

<decisions>
## Implementation Decisions

### 黄金回归怎么比（用户选定）

- **D-G01:** 黄金合同固定为 `example/石云中证1000资产进取一号私募证券投资基金-基金合同(1).docx`、`example/石云福禄1000指数增强一号私募证券投资基金(1).docx`；黄金表为 `example/产品要素 - 副本(1).xlsx`、`example/产品运营费率导入模板.xlsx`（申赎费率 xlsx **本阶段仅作 Phase 7 参考，不参与 pass/fail**）。
- **D-G02:** 对比采用 **「关键字段清单 + 全表结构检查」** 两层：  
  - **Critical（失败即红）**：基金全称、管理人、托管人、风险等级、投资经理、锁定期、开放日规则、预警线、止损线、投资目标/范围/策略（LLM 开启时）、运营费率类型与费率% 等（清单写入 `tests/golden/README.md` 或 conftest）。  
  - **Extended（警告/软断言）**：其余产品列、子表扩展列；空基金代码、运营补录字段允许与黄金不一致。
- **D-G03:** **归一化规则**（diff 前统一）：日期 → `yyyy/m/d` 或等价；去掉 `【】`；百分号与小数统一；机构名 trim；「无」/「不设」与黄金「空」的映射在测试中显式声明。
- **D-G04:** 按 **基金全称或黄金表中的基金代码行** 关联单测用例（石云两条产品各一套 expected）。

### 规则与 LLM 谁优先（用户选定）

- **D-M01:** **当事人四字段**（管理人、托管人、投资顾问、外包机构）：规则层使用 `party_helpers`（评分选优、过滤风险揭示段）；仅当 `is_valid_party_name` 通过才写入规则 结果。
- **D-M02:** **`merge_field` 增强（QUAL-04）**：若规则值为空，或命中 **误抽标记**（含：保证、登记为私募基金管理人、若根据、所涉风险、经营风险、技术系统），则 **视为无有效规则 值**，由 LLM 填充；若规则与 LLM 均有效，**当事人字段仍优先规则**（规则已通过校验时）。
- **D-M03:** **预警线/止损线**：合同载明「未设」时规则输出 `无`，**覆盖** LLM 数字猜测。
- **D-M04:** **投资四要素 + 风险等级**：规则层已有章节标题抽取；LLM 负责长文本 refine；合并时 LLM 非空且规则仅为片段时 **取更长、更完整者**（实现细节交 planner，行为目标：接近黄金长文本）。

### CI 是否跑 LLM（用户选定）

- **D-CI01:** **默认 CI / 本地 `pytest`**：黄金与规则测试 **不依赖** API Key，必须全绿。
- **D-CI02:** 需要 Key 的用例打 `@pytest.mark.llm`，无 `OPENAI_API_KEY` 时 **skip**（与 Phase 2 D-10 一致）。
- **D-CI03:** 至少 **1 条** 可选 e2e：`test_golden_extract_with_llm`（两合同之一），在 Key 存在时断言关键长文本字段非空率 ≥ 阈值（阈值在 TEST 文档写明，如 ≥80% critical 文本 字段）。
- **D-CI04:** 文档注明：`.env` 使用 DeepSeek 时 `OPENAI_BASE_URL` + `LLM_MODEL=deepseek-v4-flash`（或项目当前约定）；Docker 重建 API 后生效。

### 本阶段是否测导出（用户选定）

- **D-E01:** **TEST-01 落在 Phase 6**：`parse → extract → export` 对 **现有 4 类 xlsx**（产品要素、运营费率、锁定期、分级份额）与黄金 xlsx 对应 sheet 做关键字段 diff。
- **D-E02:** **申赎费率导出** 不在 Phase 6 验收范围（属 Phase 7 / XLS-01）。
- **D-E03:** 黄金 xlsx **绝不** 接入运行时 `validate` 或 LLM 校验层（仅 pytest 读取）。

### 字段可抽取性与可空性（2026-05-26 调研锁定）

- **D-F01:** 完整矩阵见 **`06-FIELD-MATRIX.md`**（下游 planner/researcher **必读**）。
- **D-F02:** 空值 **四分类**：A 非合同源、B 合同可选、C 合同应有、D 延后交付；测试与文档统一用语。
- **D-F03:** 用户图中 **12 项业务要素** 在合同中 **均有依据**；Phase 6 验收其中 **已上线 Excel/抽取** 的项；第 9/11/12 项整体验收在 Phase 7/8。
- **D-F04:** **黄金表 ≠ 合同真值**：样本中黄金「管理人」为弈倍、福禄托管人与合同（招商）不一致；Critical 断言 **以合同为准**（`example/_contract_keys.json` 或 `tests/golden/fixtures/contract_expected.json`）。
- **D-F05:** **允许与黄金不一致**：基金代码、成立/备案日、运行状态、MANUAL_ONLY 六列；黄金主表空但合同有的字段（外包、锁定期、投资经理）抽取有值 **不失败**。
- **D-F06:** Phase 6 Critical 清单以 **FIELD-MATRIX §6** 为准写入 `tests/golden/README.md`；含风险等级、四要素、预警止损、开放日摘要、四类运营费率及 %。

### Claude's Discretion

- `tests/golden/` 目录结构与 diff 工具选型（openpyxl 读表 vs 导出后再读）
- Critical 字段清单的初始版本与迭代方式
- 福禄合同是否复用与石云相同的 `test_shiyun_*` 模式命名 `test_golden_fulu_*`
- `merge_field` 误抽检测是集中函数还是 per-field 配置

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 本阶段调研（必读）
- `contract_info/.planning/phases/06-extract-quality/06-FIELD-MATRIX.md` — 可抽取性、可空性、12 项对照、合同 vs 黄金
- `contract_info/example/_contract_keys.json` — 两份合同规则层关键字段快照
- `contract_info/example/_golden_two_funds.json` — 黄金主表填/空统计

### 里程碑与需求
- `contract_info/.planning/REQUIREMENTS.md` — QUAL-01–04, TEST-01；黄金样例说明
- `contract_info/.planning/ROADMAP.md` — Phase 6 目标与成功标准
- `contract_info/.planning/PROJECT.md` — v1.1 范围、DeepSeek 配置
- `contract_info/.planning/milestones/1.0-REQUIREMENTS.md` — v1.0 基线

### 黄金样例（开发/UAT only）
- `contract_info/example/产品要素 - 副本(1).xlsx`
- `contract_info/example/产品运营费率导入模板.xlsx`
- `contract_info/example/产品申赎费率导入模板.xlsx` — **Phase 7 用，Phase 6 不验收**
- `contract_info/example/石云中证1000资产进取一号私募证券投资基金-基金合同(1).docx`
- `contract_info/example/石云福禄1000指数增强一号私募证券投资基金(1).docx`

### 字段与规则
- `contract_info/FIELD_SPEC.md`
- `contract_info/backend/app/extract/field_catalog.py`
- `contract_info/backend/app/extract/rules/product_rules.py`
- `contract_info/backend/app/extract/rules/party_helpers.py`
- `contract_info/backend/app/extract/rules/fee_rules.py`
- `contract_info/backend/app/extract/merge.py`
- `contract_info/backend/app/extract/pipeline.py`
- `contract_info/backend/tests/test_shiyun_contract_rules.py` — 已有石云规则回归

###  prior phase
- `contract_info/.planning/phases/02-extract/02-CONTEXT.md` — 规则优先、LLM 分窗、merge 语义

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `party_helpers.py` + 已增强的 `product_rules.py` / `fee_rules.py` — 石云单测已覆盖，需扩展福禄与 export diff
- `test_shiyun_contract_rules.py` — 模板可复制为 `tests/golden/test_golden_*.py`
- `merge_field` in `merge.py` — 需加误抽判定钩子
- `export/pipeline.py` + `column_map.py` — Phase 6 export diff 入口

### Established Patterns
- 规则 → LLM 分窗 → merge → validate_enums → 子表规则后可选 LLM 整表替换
- pytest：`example_docx_path` 与固定路径并存；`@pytest.mark.llm` 跳过无 Key

### Integration Points
- 无新 DB 列本阶段；仅抽取/合并逻辑与测试
- 生产需 `.env` LLM + `docker compose` 重建后 UI 才与本地一致

</code_context>

<specifics>
## Specific Ideas

- 用户截图中的误抽（管理人=承诺散文、投顾=风险段、锁定期=「锁定期）」）为 **v1.0 未部署/无 LLM** 时的典型问题；本地规则+DeepSeek 已改善，本阶段用黄金测试锁住。
- 黄金表由运营人工填写，**基金代码** 等系统字段允许抽取为空。
- 托管人：释义条「华福」优先于封面「华泰」笔误（已实现评分逻辑，需黄金断言）。
- **2026-05-26：** 已确认图中 12 项均可从合同抽取；空值规则与黄金/合同分工见 `06-FIELD-MATRIX.md`。

</specifics>

<deferred>
## Deferred Ideas

- 申赎费率第 5 表与 `产品申赎费率导入模板.xlsx` 对齐 — **Phase 7**
- 业绩报酬/开放日 JSON — **Phase 8**
- LLM 输出合理性校验（非 xlsx）— **Phase 9**
- 批量上传 — v2

</deferred>

---

*Phase: 06-extract-quality*  
*Context gathered: 2026-05-26*
