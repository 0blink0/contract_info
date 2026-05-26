# Phase 6：抽取质量与黄金回归 — Research

**Researched:** 2026-05-26  
**Domain:** 规则/LLM 抽取合并、openpyxl 黄金回归测试、parse→extract→export E2E  
**Confidence:** HIGH（代码库已实测）/ MEDIUM（福禄费率/子表边界）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### 黄金回归怎么比（用户选定）

- **D-G01:** 黄金合同固定为 `example/石云中证1000资产进取一号私募证券投资基金-基金合同(1).docx`、`example/石云福禄1000指数增强一号私募证券投资基金(1).docx`；黄金表为 `example/产品要素 - 副本(1).xlsx`、`example/产品运营费率导入模板.xlsx`（申赎费率 xlsx **本阶段仅作 Phase 7 参考，不参与 pass/fail**）。
- **D-G02:** 对比采用 **「关键字段清单 + 全表结构检查」** 两层：  
  - **Critical（失败即红）**：基金全称、管理人、托管人、风险等级、投资经理、锁定期、开放日规则、预警线、止损线、投资目标/范围/策略（LLM 开启时）、运营费率类型与费率% 等（清单写入 `tests/golden/README.md` 或 conftest）。  
  - **Extended（警告/软断言）**：其余产品列、子表扩展列；空基金代码、运营补录字段允许与黄金不一致。
- **D-G03:** **归一化规则**（diff 前统一）：日期 → `yyyy/m/d` 或等价；去掉 `【】`；百分号与小数统一；机构名 trim；「无」/「不设」与黄金「空」的映射在测试中显式声明。
- **D-G04:** 按 **基金全称或黄金表中的基金代码行** 关联单测用例（石云两条产品各一套 expected）。

#### 规则与 LLM 谁优先（用户选定）

- **D-M01:** **当事人四字段**（管理人、托管人、投资顾问、外包机构）：规则层使用 `party_helpers`（评分选优、过滤风险揭示段）；仅当 `is_valid_party_name` 通过才写入规则结果。
- **D-M02:** **`merge_field` 增强（QUAL-04）**：若规则值为空，或命中 **误抽标记**（含：保证、登记为私募基金管理人、若根据、所涉风险、经营风险、技术系统），则 **视为无有效规则值**，由 LLM 填充；若规则与 LLM 均有效，**当事人字段仍优先规则**（规则已通过校验时）。
- **D-M03:** **预警线/止损线**：合同载明「未设」时规则输出 `无`，**覆盖** LLM 数字猜测。
- **D-M04:** **投资四要素 + 风险等级**：规则层已有章节标题抽取；LLM 负责长文本 refine；合并时 LLM 非空且规则仅为片段时 **取更长、更完整者**（实现细节交 planner，行为目标：接近黄金长文本）。

#### CI 是否跑 LLM（用户选定）

- **D-CI01:** **默认 CI / 本地 `pytest`**：黄金与规则测试 **不依赖** API Key，必须全绿。
- **D-CI02:** 需要 Key 的用例打 `@pytest.mark.llm`，无 `OPENAI_API_KEY` 时 **skip**（与 Phase 2 D-10 一致）。
- **D-CI03:** 至少 **1 条** 可选 e2e：`test_golden_extract_with_llm`（两合同之一），在 Key 存在时断言关键长文本字段非空率 ≥ 阈值（阈值在 TEST 文档写明，如 ≥80% critical 文本字段）。
- **D-CI04:** 文档注明：`.env` 使用 DeepSeek 时 `OPENAI_BASE_URL` + `LLM_MODEL=deepseek-v4-flash`（或项目当前约定）；Docker 重建 API 后生效。

#### 本阶段是否测导出（用户选定）

- **D-E01:** **TEST-01 落在 Phase 6**：`parse → extract → export` 对 **现有 4 类 xlsx**（产品要素、运营费率、锁定期、分级份额）与黄金 xlsx 对应 sheet 做关键字段 diff。
- **D-E02:** **申赎费率导出** 不在 Phase 6 验收范围（属 Phase 7 / XLS-01）。
- **D-E03:** 黄金 xlsx **绝不** 接入运行时 `validate` 或 LLM 校验层（仅 pytest 读取）。

#### 字段可抽取性与可空性（2026-05-26 调研锁定）

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

### Deferred Ideas (OUT OF SCOPE)

- 申赎费率第 5 表与 `产品申赎费率导入模板.xlsx` 对齐 — **Phase 7**
- 业绩报酬/开放日 JSON — **Phase 8**
- LLM 输出合理性校验（非 xlsx）— **Phase 9**
- 批量上传 — v2

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUAL-01 | 当事人字段不得命中风险揭示/承诺类散文；输出机构全称 | `party_helpers.py` 已实现 `_INVALID_PARTY_MARKERS` + `is_valid_party_name`；`product_rules._find_party` 已过滤风险揭示段 [VERIFIED: codebase]。需：福禄黄金回归、export diff 不读黄金当事人 |
| QUAL-02 | 锁定期/开放日/预警止损等与石云样本一致的规则层 pytest 黄金回归 | `(1).docx` 规则层与 `_contract_keys.json` 已对齐 [VERIFIED: 本地脚本]。需：修正 `test_shiyun_*` 路径、福禄用例、锁定期子表 export diff |
| QUAL-03 | LLM 可用时长文本非空率显著高于纯规则 | `@pytest.mark.llm` + 阈值断言；规则基线用 `_LlmOff` fixture [VERIFIED: test_extract_pipeline.py 模式] |
| QUAL-04 | `merge_field` 误抽可被 LLM 覆盖；策略文档化 | 当前 `merge.py` 仅 confidence 比较，**无**误抽钩子 [VERIFIED: codebase]。需集中 `is_invalid_rule_value` + 当事人/长文本/预警止损分支 |
| TEST-01 | parse→extract→export 与 example xlsx 字段级 diff | 复用 `export/pipeline.py` + `column_map` + openpyxl；新建 `tests/golden/helpers/xlsx_diff.py`；合同真值 fixture 与黄金结构分离 |

</phase_requirements>

## Summary

Phase 6 是在 **v1.0 已有 parse/extract/export 链路** 上叠加 **质量加固 + 可重复黄金回归**，不新增 DB 列、不接入运行时校验。规则层主体（`party_helpers`、`product_rules`、`fee_rules`）对石云 `(1).docx` 已与 `example/_contract_keys.json` 高度一致 [VERIFIED: 本地 extract 脚本]；主要缺口在 **测试基础设施**（`tests/golden/` 尚不存在、`test_shiyun_contract_rules.py` 指向错误文件名导致 skip）、**`merge_field` 误抽策略**（QUAL-04）、**福禄边界**（基金服务费缺失、锁定期误匹配 `20天`、无 LLM 时分级子表为空），以及 **export 与黄金 xlsx 的 diff 语义**（当事人以合同为准、费率按类型聚合而非逐 A/B/C/D 行硬比）。

**Primary recommendation：** 新建 `tests/golden/` 三层测试（规则 Critical / export E2E / 可选 LLM）；增强 `merge.py` 集中误抽判定；将 `_contract_keys.json` 迁入 `tests/golden/fixtures/contract_expected.json` 作为 Critical 真值；export diff 复用现有 `openpyxl` + `column_map.normalize_header`，不对黄金当事人做 hard assert。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 当事人/锁定期/开放日规则抽取 | API / Backend（extract rules） | — | 纯文本解析，无前端参与 |
| `merge_field` 误抽与 LLM 覆盖 | API / Backend（extract merge） | LLM client | 合并发生在 extract pipeline，非 export |
| 黄金 pytest（规则 + export diff） | Backend tests | — | CI/dev only，不进入运行时 |
| LLM 质量基线（QUAL-03） | Backend tests（`@pytest.mark.llm`） | LLM API | 无 Key 时 skip，不阻塞默认 CI |
| 4 类 xlsx 导出 | API / Backend（export） | — | `export_xlsx` 已有四文件输出 |
| 黄金 xlsx 读取与归一化 | Backend tests helpers | — | D-E03：仅 pytest 读黄金，不进 validate |

## 当前代码库状态（实测）

| 项 | 状态 | 证据 |
|----|------|------|
| `party_helpers` 误抽标记 | ✅ 已实现 | `_INVALID_PARTY_MARKERS` 含保证/登记/若根据/经营风险/技术系统等 [VERIFIED: party_helpers.py] |
| 石云 `(1).docx` 规则 Critical | ✅ 与 contract_keys 一致 | 管理人/托管人/180天/开放日/预警止损/投资经理 [VERIFIED: 本地脚本 2026-05-26] |
| 福禄 `(1).docx` 规则 Critical | ⚠️ 部分缺口 | 锁定期合同无值 OK；**基金服务费** 费率行缺失；锁定期子表误抽 `20天`+`B份额` [VERIFIED: pipeline 无 LLM 运行] |
| `test_shiyun_contract_rules.py` | ❌ 当前 skip | 路径为无 `(1)` 后缀文件，example 目录仅存在 `(1).docx` [VERIFIED: pytest + glob] |
| `tests/golden/` | ❌ 不存在 | glob 0 files [VERIFIED: codebase] |
| `merge_field` 误抽钩子 | ❌ 未实现 | 仅 `_confidence_rank` [VERIFIED: merge.py] |
| 份额结构 / 分级子表（无 LLM） | ❌ 空 | `份额结构` 规则层未抽，share_classes=[] [VERIFIED: 本地脚本] |
| openpyxl | ✅ 3.1.5 | `pip show openpyxl` [VERIFIED: registry] |
| pytest | ✅ 9.0.3 | `pytest.ini` + conftest markers [VERIFIED: codebase] |

## Standard Stack

### Core

| Library | Version | 用途 | Why Standard |
|---------|---------|------|--------------|
| openpyxl | 3.1.5 [VERIFIED: pip] | 读黄金 xlsx、读导出结果、表头索引 | 项目已用于 export；requirements 指定 `>=3.1` |
| pytest | 9.0.3 [VERIFIED: pip] | 黄金回归、规则/LLM 分层 | 全项目 test runner |
| python-docx | >=1.1.0 [VERIFIED: requirements.txt] | parse 石云/福禄 docx | Phase 1 已有 |
| pydantic | >=2.0 | FieldValue / ExtractionResult | extract schemas |
| httpx | >=0.27 | LlmClient（可选 e2e） | Phase 2 已有 |

### Supporting

| Library | Version | 用途 | When to Use |
|---------|---------|------|-------------|
| 现有 `export/column_map.py` | — | sheet 名、header 行、normalize_header | diff 与 fill 共用表头语义 |
| 现有 `export/date_format.py` | — | `normalize_date_slash` | D-G03 日期归一 |
| 现有 `export/xlsx_utils.py` | — | `build_header_index` | 按列名读/写 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openpyxl 自研 diff | pandas | 新增依赖；表头含【必填】需额外处理；**不推荐** |
| 运行时读黄金 xlsx | 仅 pytest fixture | D-E03 禁止运行时接入；**必须 pytest only** |
| 第三方 xlsx diff CLI | pytest + openpyxl | 中文字段/多 sheet 定制成本高 |

**Installation：** 无新依赖；确保 `pip install -r requirements.txt`（CI/Docker 已有）。

## 推荐目录与文件触点

```
contract_info/
├── backend/app/extract/
│   ├── merge.py                    # ★ merge_field 增强（QUAL-04）
│   ├── pipeline.py                 # 传入 field_name 给 merge（若签名扩展）
│   └── rules/
│       ├── party_helpers.py        # 已有；可导出 is_misextracted 复用
│       ├── product_rules.py        # 福禄锁定期误匹配修复
│       └── fee_rules.py            # 福禄基金服务费补抽
├── backend/app/export/             # diff 复用 column_map / date_format（只读）
├── backend/tests/
│   ├── test_shiyun_contract_rules.py  # ★ 修正路径 → (1).docx 或迁 golden/
│   └── golden/                     # ★ 新建
│       ├── README.md               # Critical 清单、四分类空值、归一化、LLM 说明
│       ├── conftest.py             # docx 路径、contract_expected、export tmp dir
│       ├── fixtures/
│       │   └── contract_expected.json   # 自 _contract_keys.json + 费率/风险等级
│       ├── helpers/
│       │   ├── normalize.py        # 日期/百分号/机构名/无↔空
│       │   ├── xlsx_diff.py        # 读 sheet、按基金全称找行、Critical diff
│       │   └── pipeline_runner.py  # parse→extract→export 一次调用
│       ├── test_golden_rules_shiyun.py
│       ├── test_golden_rules_fulu.py
│       ├── test_golden_export.py   # TEST-01，无 LLM
│       └── test_golden_llm.py      # @pytest.mark.llm
└── example/                        # 黄金样例（只读，不提交密钥）
    ├── _contract_keys.json         # 迁移源 → fixtures
    ├── 产品要素 - 副本(1).xlsx
    └── 产品运营费率导入模板.xlsx
```

## Architecture Patterns

### System Architecture Diagram

```mermaid
flowchart LR
  subgraph inputs [输入]
    DOCX[石云/福禄 docx]
    GOLD[黄金 xlsx\n仅 pytest]
    EXP_JSON[contract_expected.json]
  end

  subgraph pipeline [生产链路]
    PARSE[parse_docx]
    RULES[extract_product_rules\n+ fee/lock/share rules]
    LLM[chapter_extract\n可选]
    MERGE[merge_field\n★误抽钩子]
    EXPORT[export_xlsx\n4 类 xlsx]
  end

  subgraph tests [Phase 6 测试]
    R_TEST[test_golden_rules_*]
    E_TEST[test_golden_export]
    L_TEST[test_golden_llm\n@pytest.mark.llm]
    DIFF[xlsx_diff\nCritical vs EXP_JSON\nExtended vs GOLD]
  end

  DOCX --> PARSE --> RULES
  RULES --> MERGE
  LLM --> MERGE
  MERGE --> EXPORT

  RULES --> R_TEST
  EXP_JSON --> R_TEST
  EXPORT --> E_TEST
  GOLD --> DIFF
  EXP_JSON --> DIFF
  MERGE --> L_TEST
```

### Pattern 1：合同真值 vs 黄金表双轨断言

**What：** Critical 字段对比 `contract_expected.json`；Extended/结构对比黄金 xlsx（列存在、费率行形态、子表 sheet 存在）。  
**When：** 所有 TEST-01 / QUAL-02 用例。  
**Why：** D-F04/F05 — 黄金管理人=弈倍、福禄托管人=华福等与合同不符，对当事人 hard assert 黄金必失败。

**示例逻辑：**

```python
# 模式：tests/golden/helpers/xlsx_diff.py
CRITICAL_FROM_CONTRACT = {
    "管理人", "托管人", "风险等级", "投资经理", "锁定期",
    "开放日规则", "预警线", "止损线", "基金全称",
}
SKIP_GOLDEN_PARTY = {"管理人", "托管人", "外包机构", "投资顾问"}
A_CLASS_EMPTY_OK = {"基金代码", "成立日期", "备案日期", *MANUAL_ONLY_PRODUCT}
```

### Pattern 2：`merge_field` 集中误抽判定（推荐）

**What：** 单函数 `is_invalid_rule_value(field_name, value) -> bool`，在 `merge_field` 入口调用；当事人字段额外走 `is_valid_party_name`。  
**When：** D-M02 / QUAL-04。  
**Why：** `party_helpers._INVALID_PARTY_MARKERS` 已存在，避免 per-field 重复；当事人仍「规则优先」仅当 **未** invalid。

```python
# 推荐新增于 merge.py（示意）
_PARTY_FIELDS = frozenset({"管理人", "托管人", "投资顾问", "外包机构"})
_LONG_TEXT = frozenset({"投资目标", "投资范围", "投资限制", "投资策略", "风险等级"})
_MIS_EXTRACT_MARKERS = (
    "保证", "登记为私募基金管理人", "若根据", "所涉风险", "经营风险", "技术系统",
)

def is_invalid_rule_value(field_name: str, value: object) -> bool:
    if value is None or str(value).strip() == "":
        return True
    text = str(value)
    if field_name in _PARTY_FIELDS:
        from backend.app.extract.rules.party_helpers import is_valid_party_name
        return not is_valid_party_name(text)
    return any(m in text for m in _MIS_EXTRACT_MARKERS)

def merge_field(rule_val, llm_val, *, field_name: str = ""):
    rule_invalid = rule_val and is_invalid_rule_value(field_name, rule_val.value)
    effective_rule = None if rule_invalid else rule_val
    # D-M03: 预警/止损 规则「无」优先
    if field_name in ("预警线", "止损线") and effective_rule and effective_rule.value == "无":
        return effective_rule
    # D-M04: 长文本取更长者
    if field_name in _LONG_TEXT and effective_rule and llm_val:
        ...
    # D-M01: 当事人规则有效则优先
    if field_name in _PARTY_FIELDS and effective_rule and not rule_invalid:
        return effective_rule
    ...
```

[ASSUMED: `merge_field` 需增加 `field_name` 参数；`pipeline.py` 两处调用需同步 — 属小范围 API 变更]

### Pattern 3：Export E2E 与费率 diff 聚合

**What：** `pipeline_runner.run(docx) -> (extraction, product_path, fee_path, lock_path, share_path)`；费率按 `(基金名称, 运营费类型)` 聚合 rate%，允许导出 1 行 vs 黄金 A/B/C/D 多行。  
**When：** TEST-01 / D-E01。  
**Why：** 黄金运营费率 xlsx 按份额类多行（如石云进取 D/C/B/A 各一行管理费）[VERIFIED: openpyxl 读表]；当前 `extract_fee_rates` 产出每类型 1 行 [VERIFIED: 本地 pipeline]。

**Critical 费率断言：** 对每基金断言存在 管理费/托管费/销售服务费/基金服务费（合同有则必有）及 rate% 与 contract_expected 或规则层一致；**不**要求与黄金行数 1:1。

### Pattern 4：LLM 分层测试

**What：** 默认 CI 用 `_LlmOff()`（`test_extract_pipeline.py` 已有）；`@pytest.mark.llm` 跑真实 `LlmClient`，断言 critical 长文本非空率 ≥80%。  
**When：** QUAL-03 / D-CI03。  
**Why：** D-CI01/02 与 Phase 2 D-10 一致。

### Anti-Patterns to Avoid

- **用黄金 xlsx 断言管理人/托管人：** 违反 D-F04，必然误报。
- **无 LLM 断言分级子表行数 = 黄金：** `份额结构` 依赖 LLM basic 窗，规则层常为空 [VERIFIED]。
- **把黄金接入 `validate_export`：** 违反 D-E03。
- **申赎费率 xlsx 纳入 Phase 6 pass/fail：** 违反 D-E02 / D-G01。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| xlsx 表头解析 | 手写列号 | `build_header_index` + `normalize_header` | 模板含【必填】、重复逻辑字段 |
| 日期格式统一 | 自定义 strptime 集合 | `normalize_date_slash` | 与 export 写入一致 |
| LLM skip 逻辑 | 环境分支散落 | `@pytest.mark.llm` + conftest | Phase 2 既定模式 |
| 机构名清洗 | 新 regex | `clean_org_name` / `is_valid_party_name` | party_helpers 已覆盖 |
| OpenAI 客户端 | 新 HTTP 封装 | `LlmClient` | 已有 retry/JSON 解析 |

## Common Pitfalls

### Pitfall 1：测试 docx 路径与 example 不一致

**What goes wrong：** `test_shiyun_contract_rules.py` 引用无 `(1)` 后缀文件 → 全 skip [VERIFIED: pytest 2026-05-26]。  
**How to avoid：** 常量统一为 CONTEXT D-G01 路径，或 conftest `golden_docx_paths` fixture。

### Pitfall 2：福禄锁定期子表误匹配

**What goes wrong：** 无锁定期主字段时，`lock_rules` 从全文匹配 `20天`+`B份额` 产生假行 [VERIFIED: 福禄 pipeline]。  
**How to avoid：** 无 `锁定期` 主字段时 lock 子表返回 `[]` 或仅「无」；加强 `_RE_LOCK_TIME` 上下文（须在锁定期条款附近）。

### Pitfall 3：费率 diff 行级 1:1

**What goes wrong：** 黄金 16+ 行 vs 导出 3–4 行导致假失败。  
**How to avoid：** 按运营费类型聚合 rate%；Extended 检查「至少 N 种费率存在」。

### Pitfall 4：merge 仅比 confidence

**What goes wrong：** 规则 high confidence 误抽（承诺散文）压过 LLM 正确机构名。  
**How to avoid：** QUAL-04 集中 invalid 判定后再比 confidence。

### Pitfall 5：投资四要素规则片段覆盖 LLM 全文

**What goes wrong：** 规则 `_extract_investment_chapter` 截断 ~4000 字，merge 若规则优先则短于黄金长文本。  
**How to avoid：** D-M04 长文本字段取 `len` 更大者；LLM 测试单独覆盖。

## Code Examples

### 读产品要素 sheet 按基金全称定位行

```python
# 复用 export/column_map 常量 [VERIFIED: column_map.py]
from openpyxl import load_workbook
from backend.app.export.column_map import (
    PRODUCT_SHEET, PRODUCT_HEADER_ROW, normalize_header,
)
from backend.app.export.xlsx_utils import build_header_index

def find_product_row(xlsx_path, fund_full_name: str) -> int:
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb[PRODUCT_SHEET]
    idx = build_header_index(ws, PRODUCT_HEADER_ROW)
    name_cols = idx.get(normalize_header("基金全称"), [])
    for r in range(PRODUCT_HEADER_ROW + 1, ws.max_row + 1):
        for c in name_cols:
            if ws.cell(r, c).value == fund_full_name:
                wb.close()
                return r
    wb.close()
    raise AssertionError(f"row not found: {fund_full_name}")
```

### 无 LLM 的 export E2E（TEST-01 骨架）

```python
# 模式：tests/golden/test_golden_export.py
import uuid
import pytest
from backend.app.export.pipeline import export_xlsx
from backend.app.extract.pipeline import extract_document_sync

class _LlmOff:
    available = False
    model_name = ""

@pytest.fixture
def run_pipeline(shiyun_document):  # document fixture from conftest
    result, _ = extract_document_sync(shiyun_document, llm_client=_LlmOff())
    payload = result.model_dump()
    paths = export_xlsx(payload, uuid.uuid4())
    return result, paths
```

### pytest LLM skip（已有）

```python
# [VERIFIED: conftest.py + pytest.ini]
@pytest.mark.llm
def test_golden_extract_with_llm(shiyun_document):
    import os
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    ...
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| 单文件 `test_shiyun_*` | `tests/golden/` 分层 + 双轨真值 | 可扩展福禄、export、LLM |
| merge 纯 confidence | invalid 规则 + 字段策略 | QUAL-04 |
| 人工对照 example xlsx | pytest Critical + Extended | TEST-01 CI 化 |

**Deprecated/outdated：**

- 以黄金「上海弈倍」为管理人 expected — 已由 D-F04 废止。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `merge_field` 需增 `field_name` 参数 | Pattern 2 | pipeline 调用点遗漏导致行为不变 |
| A2 | 无 LLM 时福禄分级 export 可为空 sheet | Pattern 3 | 若用户要求无 LLM 也验分级，需规则层补 `份额结构` |
| A3 | Critical 长文本 LLM 阈值 80% | QUAL-03 | 需用户在 README 确认 |
| A4 | 福禄基金服务费在费用章可规则补抽 | 当前代码库状态 | 若合同表述特殊需 LLM |

## Open Questions

1. **福禄 `基金服务费` 费率行是否 Phase 6 Critical？**  
   - 已知：规则层当前 3 行（缺基金服务费）[VERIFIED]。  
   - 建议：纳入 Critical（FIELD-MATRIX #10）；优先扩展 `fee_rules._rates_from_fee_chapter`。

2. **无 LLM 时分级份额 export 是否 assert？**  
   - 已知：share_classes=[] [VERIFIED]。  
   - 建议：Phase 6 Extended/warn only；Critical 留 `@pytest.mark.llm` 或 Phase 10。

3. **`test_shiyun_*` 迁移还是改名？**  
   - 建议：迁到 `tests/golden/test_golden_rules_shiyun.py`，旧文件删除或 re-export，避免双份维护。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | pytest / extract | ✓ | 3.11.9 [VERIFIED] | — |
| python-docx | parse docx | ✓（需 pip install） | >=1.1.0 | CI Dockerfile 已装 |
| openpyxl | export diff | ✓ | 3.1.5 | requirements.txt |
| OPENAI_API_KEY | `@pytest.mark.llm` | 可选 | — | skip，不阻塞默认 CI |
| PostgreSQL | 本阶段 | ✗ 不需要 | — | 无 DB 集成测试 |
| example 黄金文件 | 全部 golden 测试 | ✓ | — | 缺失则 skip |

**Missing dependencies with no fallback：**

- 无（Phase 6 为代码 + pytest + example 文件）。

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 [VERIFIED: pip] |
| Config file | `contract_info/pytest.ini` |
| Quick run command | `python -m pytest backend/tests/golden/ -q -m "not llm"` |
| Full suite command | `python -m pytest backend/tests/ -q` |
| LLM optional | `python -m pytest backend/tests/golden/ -m llm` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUAL-01 | 当事人非散文、机构全称 | unit/integration | `pytest backend/tests/golden/test_golden_rules_*.py -k party -x` | ❌ Wave 0 |
| QUAL-02 | 锁定期/开放日/预警止损规则回归 | integration | `pytest backend/tests/golden/test_golden_rules_shiyun.py -x` | ⚠️ 部分（test_shiyun skip） |
| QUAL-03 | LLM 长文本非空率 ≥ 阈值 | e2e llm | `pytest backend/tests/golden/test_golden_llm.py -m llm -x` | ❌ Wave 0 |
| QUAL-04 | merge 误抽覆盖 | unit | `pytest backend/tests/test_merge_field.py -x` | ❌ Wave 0 |
| TEST-01 | parse→extract→export xlsx diff | integration | `pytest backend/tests/golden/test_golden_export.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit：** `pytest backend/tests/golden/ -q -m "not llm"`
- **Per wave merge：** `pytest backend/tests/ -q -m "not llm"`
- **Phase gate：** 全量 `-m "not llm"` 绿 + 可选 `-m llm` 本地/夜间

### Wave 0 Gaps

- [ ] `backend/tests/golden/` 目录与 README.md
- [ ] `backend/tests/golden/fixtures/contract_expected.json`
- [ ] `backend/tests/golden/helpers/{normalize,xlsx_diff,pipeline_runner}.py`
- [ ] `backend/tests/golden/test_golden_export.py` — TEST-01
- [ ] `backend/tests/test_merge_field.py` — QUAL-04
- [ ] 修正 `test_shiyun_contract_rules.py` docx 路径或迁移
- [ ] `merge.py` 误抽逻辑 + `tests/golden/README.md` 策略说明

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | 本阶段无 API 变更 |
| V5 Input Validation | yes | 误抽标记 / `is_valid_party_name` 属抽取输入卫生 |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `.env` API Key 进 git | Information Disclosure | 测试 skip 无 Key；不 commit `.env` [用户规则] |
| 黄金 xlsx 路径遍历 | — | fixture 固定 `example/` 相对路径 |

## Project Constraints (from .cursor/rules/)

无 `.cursor/rules/` 目录 [VERIFIED: glob 0 files]。遵循仓库既有 pytest / export 模式即可。

## Sources

### Primary (HIGH confidence)

- `contract_info/backend/app/extract/` — merge, pipeline, party_helpers, product_rules, fee_rules [VERIFIED: 代码阅读 + 本地脚本]
- `contract_info/backend/app/export/` — pipeline, column_map, xlsx_utils [VERIFIED]
- `contract_info/backend/tests/conftest.py`, `pytest.ini` [VERIFIED]
- `contract_info/example/_contract_keys.json` [VERIFIED]
- openpyxl 3.1.5, pytest 9.0.3 [VERIFIED: pip show]

### Secondary (MEDIUM confidence)

- `06-FIELD-MATRIX.md`, `06-CONTEXT.md` — 用户锁定决策
- Phase 2 `02-CONTEXT.md` D-10 LLM skip 语义

### Tertiary (LOW confidence)

- DeepSeek `deepseek-v4-flash` 型号命名 — 以项目 `.env` 实际为准 [ASSUMED: D-CI04]

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — 无新依赖，版本已 pip 验证
- Architecture: **HIGH** — 代码路径已跑通；福禄费率/锁定为 MEDIUM
- Pitfalls: **HIGH** — test skip 与 pipeline 实测可复现

**Research date:** 2026-05-26  
**Valid until:** 2026-06-26（stable stack）；福禄边界修复后需复验

## RESEARCH COMPLETE
