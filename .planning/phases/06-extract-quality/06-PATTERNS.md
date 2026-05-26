# Phase 6: 抽取质量与黄金回归 - Pattern Map

**Mapped:** 2026-05-26  
**Files analyzed:** 18 new/modified  
**Analogs found:** 16 / 18

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/extract/merge.py` | utility | transform | `backend/app/extract/merge.py` (extend) | exact |
| `backend/app/extract/pipeline.py` | service | batch | `backend/app/extract/pipeline.py` | exact |
| `backend/app/extract/rules/party_helpers.py` | utility | transform | `backend/app/extract/rules/party_helpers.py` | exact |
| `backend/app/extract/rules/product_rules.py` | utility | transform | `backend/app/extract/rules/product_rules.py` | exact |
| `backend/app/extract/rules/fee_rules.py` | utility | transform | `backend/app/extract/rules/fee_rules.py` | exact |
| `backend/app/extract/rules/lock_rules.py` | utility | transform | `backend/app/extract/rules/lock_rules.py` | exact |
| `backend/tests/test_shiyun_contract_rules.py` | test | batch | `backend/tests/test_shiyun_contract_rules.py` | exact |
| `backend/tests/test_merge_field.py` | test | transform | `backend/tests/test_export_validate.py` | role-match |
| `backend/tests/golden/conftest.py` | test | file-I/O | `backend/tests/conftest.py` | role-match |
| `backend/tests/golden/fixtures/contract_expected.json` | config | file-I/O | `example/_contract_keys.json` | exact |
| `backend/tests/golden/helpers/normalize.py` | utility | transform | `backend/app/export/date_format.py` | role-match |
| `backend/tests/golden/helpers/xlsx_diff.py` | utility | file-I/O | `backend/app/export/xlsx_utils.py` + `column_map.py` | exact |
| `backend/tests/golden/helpers/pipeline_runner.py` | utility | batch | `backend/tests/test_extract_pipeline.py` | exact |
| `backend/tests/golden/test_golden_rules_shiyun.py` | test | batch | `backend/tests/test_shiyun_contract_rules.py` | exact |
| `backend/tests/golden/test_golden_rules_fulu.py` | test | batch | `backend/tests/test_shiyun_contract_rules.py` | exact |
| `backend/tests/golden/test_golden_export.py` | test | file-I/O | `backend/tests/test_export_pipeline.py` | exact |
| `backend/tests/golden/test_golden_llm.py` | test | batch | `backend/tests/test_extract_pipeline.py` | role-match |
| `backend/tests/golden/README.md` | config | — | `06-FIELD-MATRIX.md` (content only) | partial |

## Pattern Assignments

### `backend/app/extract/merge.py` (utility, transform)

**Analog:** `backend/app/extract/merge.py` + `backend/app/extract/rules/party_helpers.py`

**Current merge entry** (lines 15-24) — extend here, do not replace wholesale:

```15:24:contract_info/backend/app/extract/merge.py
def merge_field(
    rule_val: FieldValue | None,
    llm_val: FieldValue | None,
) -> FieldValue | None:
    if rule_val and llm_val:
        if _confidence_rank(rule_val.confidence) >= _confidence_rank(llm_val.confidence):
            if rule_val.value not in (None, ""):
                return rule_val
        return llm_val if llm_val.value not in (None, "") else rule_val
    return rule_val or llm_val
```

**Batch merge loop** (lines 36-38) — add `field_name=key` when signature extends:

```36:38:contract_info/backend/app/extract/merge.py
    for key, llm_fv in llm_fields.items():
        merged[key] = merge_field(merged.get(key), llm_fv) or llm_fv
```

**Reuse party validation** (lines 9-45 in `party_helpers.py`):

```9:45:contract_info/backend/app/extract/rules/party_helpers.py
_INVALID_PARTY_MARKERS = (
    "保证",
    "登记",
    "承诺",
    "风险",
    "投资者",
    "若根据",
    "所涉",
    "有权代表",
    "经营风险",
    "技术系统",
)
# ...
def is_valid_party_name(name: str) -> bool:
    if not name or len(name) < 4:
        return False
    if any(m in name for m in _INVALID_PARTY_MARKERS):
        return False
    if not re.search(r"公司|银行|证券|信托|基金|有限", name):
        return False
    return True
```

**Planner behavior (D-M02–M04):** Add `is_invalid_rule_value(field_name, value)` before confidence compare; import `is_valid_party_name` for `_PARTY_FIELDS`; for `预警线`/`止损线` with rule value `无`, return rule; for `_LONG_TEXT`, prefer longer non-empty string when rule invalid or shorter.

---

### `backend/app/extract/pipeline.py` (service, batch)

**Analog:** `backend/app/extract/pipeline.py`

**Sync entry for tests** (lines 257-267):

```257:267:contract_info/backend/app/extract/pipeline.py
def extract_document_sync(
    document: dict[str, Any],
    *,
    llm_client: LlmClient | None = None,
) -> tuple[ExtractionResult, list[ExtractionWarning]]:
    return asyncio.run(extract_document(document, llm_client=llm_client))
```

**Inline merge loop** (lines 147-149) — mirror `merge_extraction`; pass `field_name=key`:

```147:149:contract_info/backend/app/extract/pipeline.py
    for key, llm_fv in llm_fields.items():
        merged_product[key] = merge_field(merged_product.get(key), llm_fv) or llm_fv
```

**LLM gate** (lines 113-131) — golden export tests use client with `available=False`:

```113:131:contract_info/backend/app/extract/pipeline.py
    if getattr(client, "available", False):
        for key in LLM_WINDOW_KEYS:
            text = windows.get(key, "")
            if not text.strip():
                continue
            fields, w = await extract_chapter_fields(client, key, text)
            llm_fields.update(fields)
```

---

### `backend/app/extract/rules/party_helpers.py` (utility, transform)

**Analog:** `backend/app/extract/rules/party_helpers.py`

**Optional export:** Expose `_INVALID_PARTY_MARKERS` via `is_invalid_rule_value` in `merge.py` OR add thin `is_misextracted_text(text: str) -> bool` here using same tuple — avoid duplicating marker strings in two modules.

**Risk block skip** (lines 57-67) — product_rules already depends on this; no change required for Phase 6 unless new markers added:

```57:67:contract_info/backend/app/extract/rules/party_helpers.py
def block_is_risk_disclosure(document: dict[str, Any], block: dict[str, Any]) -> bool:
    title = section_title_for_block(document, block)
    if "风险揭示" in title or "风险提示" in title:
        return True
    # ...
    return "风险揭示书" in text[:200] or (
        "私募基金管理人保证" in text and "登记" in text
    )
```

---

### `backend/app/extract/rules/product_rules.py` (utility, transform)

**Analog:** `backend/app/extract/rules/product_rules.py`

**Party extraction with validation** (lines 131-164):

```131:164:contract_info/backend/app/extract/rules/product_rules.py
def _find_party(
    document: dict[str, Any],
    patterns: list[re.Pattern[str]],
    *,
    prefer_cover: str = "",
    role: str = "manager",
) -> tuple[str | None, str, str | None, str | None]:
    # ...
            name = clean_org_name(m.group(1))
            if not is_valid_party_name(name):
                continue
    # ...
        if block_is_risk_disclosure(document, block):
            continue
```

**预警/止损「无」** (lines 326-336) — merge must not let LLM override:

```326:336:contract_info/backend/app/extract/rules/product_rules.py
    no_stop = re.search(
        r"未设预警|不设预警|不设置预警线|本基金未设预警止损线",
        inv_text + risk_text + full_text[:80000],
    )
    if no_stop:
        out["预警线"] = _fv("无", snippet=no_stop.group(0))
        out["止损线"] = _fv("无", snippet=no_stop.group(0))
```

**锁定期 / 开放日** (lines 338-355) — assert in golden rules tests against `contract_expected.json`, not golden xlsx.

**FieldValue factory** (lines 93-107) — keep `_fv(...)` for any new rule outputs.

---

### `backend/app/extract/rules/fee_rules.py` (utility, transform)

**Analog:** `backend/app/extract/rules/fee_rules.py` + `backend/tests/test_shiyun_contract_rules.py`

**Fee type patterns** (lines 8-14) — extend for 福禄 `基金服务费`:

```8:14:contract_info/backend/app/extract/rules/fee_rules.py
_FEE_TYPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("管理费", re.compile(r"管理费")),
    ("托管费", re.compile(r"托管费")),
    ("投资顾问费", re.compile(r"投资顾问费|顾问费")),
    ("销售服务费", re.compile(r"销售服务费")),
    ("基金服务费", re.compile(r"基金服务费|运营服务费|运营外包服务费")),
]
```

**Test aggregation pattern** (from `test_shiyun_contract_rules.py` lines 47-58):

```47:58:contract_info/backend/tests/test_shiyun_contract_rules.py
def test_shiyun_fee_rates(shiyun_document):
    windows, _ = build_section_windows(shiyun_document)
    product = extract_product_rules(shiyun_document, windows)
    fund = product.get("基金全称")
    name = str(fund.value) if fund and fund.value else None
    fees = extract_fee_rates(windows["fees"], name, shiyun_document)
    by_type = {r.运营费类型: r for r in fees}
    assert by_type["管理费"].rate_annual_pct == "1"
```

Golden export diff: compare **by 运营费类型**, not row-for-row with golden A/B/C/D lines.

---

### `backend/app/extract/rules/lock_rules.py` (utility, transform)

**Analog:** `backend/app/extract/rules/lock_rules.py`

**Early return when no lock** (lines 71-73, 125-134) — tighten for 福禄 false `20天` + `B份额`:

```71:73:contract_info/backend/app/extract/rules/lock_rules.py
    if not fund_name and not lock_text:
        return []
```

```125:134:contract_info/backend/app/extract/rules/lock_rules.py
    if not any(
        getattr(row, f) for f in ("锁定期", "锁定时间", "份额类型", "起始规则")
    ):
        if not has_lock and not lock_text:
            return []
    return [row]
```

**Fix direction:** When `lock_summary` empty and no `has_lock`, return `[]` before `_RE_LOCK_TIME.search(combined)` on full subscription text (RESEARCH Pitfall 2).

---

### `backend/tests/test_shiyun_contract_rules.py` (test, batch)

**Analog:** `backend/tests/test_shiyun_contract_rules.py` (fix paths) → migrate to `tests/golden/test_golden_rules_shiyun.py`

**Path constant** (lines 13-17) — **must** use D-G01 `(1).docx` suffix:

```13:17:contract_info/backend/tests/test_shiyun_contract_rules.py
SHIYUN_DOCX = (
    Path(__file__).resolve().parents[2]
    / "example"
    / "石云中证1000资产进取一号私募证券投资基金-基金合同.docx"
)
```

Replace with: `石云中证1000资产进取一号私募证券投资基金-基金合同(1).docx`

**Module fixture + skip** (lines 20-25):

```20:25:contract_info/backend/tests/test_shiyun_contract_rules.py
@pytest.fixture(scope="module")
def shiyun_document():
    if not SHIYUN_DOCX.is_file():
        pytest.skip("石云示例合同不存在")
    doc = parse_docx(str(SHIYUN_DOCX))
    return document_to_dict(doc)
```

**Critical assertions** (lines 28-44) — load expected from `contract_expected.json` instead of hardcoding only where JSON is source of truth; keep substring checks for long 开放日/投资 fields.

---

### `backend/tests/test_merge_field.py` (test, transform)

**Analog:** `backend/tests/test_export_validate.py`

**Minimal unit test style** (lines 1-17):

```1:17:contract_info/backend/tests/test_export_validate.py
from backend.app.export.validate_export import check_fees, check_product


def test_check_product_empty():
    warnings = check_product({"product_elements": {}, "fee_rates": []})
    assert any(w.code == "export_required_missing" for w in warnings)
```

**Cases to cover:** invalid rule (marker substring) → LLM wins; valid party rule → rule wins; `预警线` rule `无` → rule wins; long text rule shorter than LLM → longer wins.

---

### `backend/tests/golden/conftest.py` (test, file-I/O)

**Analog:** `backend/tests/conftest.py` + `test_shiyun_contract_rules.py`

**Project root / example dir** (conftest lines 6-7):

```6:7:contract_info/backend/tests/conftest.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_DIR = PROJECT_ROOT / "example"
```

**Golden conftest should define:**

- `golden_docx_shiyun`, `golden_docx_fulu` → fixed D-G01 paths under `EXAMPLE_DIR`
- `contract_expected` → load `fixtures/contract_expected.json`
- `golden_product_xlsx`, `golden_fee_xlsx` → `产品要素 - 副本(1).xlsx`, `产品运营费率导入模板.xlsx`
- Re-export `pytest_configure` markers only if not inherited (parent `conftest.py` already registers `llm`)

**Docx parse fixture** — copy `shiyun_document` pattern from test_shiyun (parse_docx + document_to_dict).

---

### `backend/tests/golden/fixtures/contract_expected.json` (config, file-I/O)

**Analog:** `example/_contract_keys.json`

**Shape** — per-docx filename keys; migrate and extend with `风险等级`, fee rates, `基金全称`:

```1:15:contract_info/example/_contract_keys.json
{
  "石云中证1000资产进取一号私募证券投资基金-基金合同(1).docx": {
    "管理人": "北京石云科技有限公司",
    "托管人": "华福证券股份有限公司",
    "外包机构": "国泰海通证券股份有限公司",
    "投资顾问": "",
    "锁定期": "180天",
    "投资经理": "王敏敏、李森林",
    ...
```

Add nested `fee_rates_by_type` or top-level map per fund short name for TEST-01 Critical fee %.

---

### `backend/tests/golden/helpers/normalize.py` (utility, transform)

**Analog:** `backend/app/export/date_format.py` + `column_map.normalize_header`

**Date normalization** (lines 7-20):

```7:20:contract_info/backend/app/export/date_format.py
def normalize_date_slash(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    # ...
    m = re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日?", text)
    if m:
        return f"{int(m.group(1))}/{int(m.group(2))}/{int(m.group(3))}"
```

**Header strip** (lines 50-56 in column_map):

```50:56:contract_info/backend/app/export/column_map.py
def normalize_header(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"【[^】]*】", "", text)
    text = re.sub(r"\s+", "", text)
    return text
```

Add: `normalize_pct`, `normalize_party_name` (strip), `empty_equiv` (`无`/`不设` ↔ `""`) per D-G03.

---

### `backend/tests/golden/helpers/xlsx_diff.py` (utility, file-I/O)

**Analog:** `backend/app/export/xlsx_utils.py` + `column_map.py` + `test_export_pipeline.py`

**Header index** (lines 18-26):

```18:26:contract_info/backend/app/export/xlsx_utils.py
def build_header_index(ws: Worksheet, header_row: int) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(row=header_row, column=col).value
        name = normalize_header(cell)
        if not name:
            continue
        index.setdefault(name, []).append(col)
```

**Sheet constants** (lines 5-18 in column_map):

```5:18:contract_info/backend/app/export/column_map.py
PRODUCT_SHEET = "产品要素模板"
PRODUCT_HEADER_ROW = 2
PRODUCT_DATA_ROW = 3
FEE_SHEET = "产品运营费率导入模板"
FEE_HEADER_ROW = 3
FEE_DATA_START_ROW = 4
```

**openpyxl read in tests** (test_export_pipeline lines 31-34):

```31:34:contract_info/backend/tests/test_export_pipeline.py
    wb = load_workbook(product_abs, read_only=True)
    ws = wb[PRODUCT_SHEET]
    assert ws.cell(PRODUCT_DATA_ROW, 2).value  # 基金全称 col 2 typical
    wb.close()
```

Implement `find_product_row`, `read_cell`, `assert_critical_product`, `assert_fee_types_present`; **never** assert golden 管理人/托管人 against export when contract_expected differs (D-F04).

---

### `backend/tests/golden/helpers/pipeline_runner.py` (utility, batch)

**Analog:** `backend/tests/test_extract_pipeline.py` + `backend/app/export/pipeline.py`

**LlmOff stub** (lines 16-23):

```16:23:contract_info/backend/tests/test_extract_pipeline.py
class _LlmOff:
    available = False
    model_name = ""


def test_pipeline_without_llm(sample_document):
    os.environ.pop("OPENAI_API_KEY", None)
    result, warnings = extract_document_sync(sample_document, llm_client=_LlmOff())
```

**Export four paths** (export/pipeline lines 54-59):

```54:59:contract_info/backend/app/export/pipeline.py
def export_xlsx(
    extraction: dict[str, Any],
    file_id: uuid.UUID | str,
) -> tuple[str, str, str, str, list[dict[str, Any]]]:
```

Runner: `parse_docx` → `extract_document_sync(..., _LlmOff())` → `export_xlsx(result.model_dump(), uuid)` → return paths; monkeypatch `exports_dir` like `test_export_pipeline` for hermetic tmp dirs.

---

### `backend/tests/golden/test_golden_rules_shiyun.py` (test, batch)

**Analog:** `backend/tests/test_shiyun_contract_rules.py`

Copy structure: module-scoped docx fixture, `build_section_windows`, `extract_product_rules`, `extract_fee_rates`; assert against `contract_expected["石云中证1000…(1).docx"]` keys from FIELD-MATRIX §6.

---

### `backend/tests/golden/test_golden_rules_fulu.py` (test, batch)

**Analog:** `backend/tests/test_shiyun_contract_rules.py`

Same pattern; docx = `石云福禄1000指数增强一号私募证券投资基金(1).docx`; expected from JSON second key; include fee Critical for 基金服务费 when rule fixed.

---

### `backend/tests/golden/test_golden_export.py` (test, file-I/O)

**Analog:** `backend/tests/test_export_pipeline.py`

Use `pipeline_runner` + `xlsx_diff`; `@pytest.mark` not `llm`; monkeypatch exports_dir; compare export output to `contract_expected` (Critical) and golden xlsx (Extended: sheet exists, header row, fee row count ≥ N).

---

### `backend/tests/golden/test_golden_llm.py` (test, batch)

**Analog:** `backend/tests/test_extract_pipeline.py` + `conftest` llm marker

**Marker registration** (pytest.ini lines 4-6):

```4:6:contract_info/pytest.ini
markers =
    llm: requires OPENAI_API_KEY
    integration: requires DATABASE_URL
```

**Skip pattern** (RESEARCH — no existing llm test file yet; follow Phase 2 D-10):

```python
@pytest.mark.llm
def test_golden_extract_with_llm(shiyun_document):
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    from backend.app.llm.client import LlmClient
    result, _ = extract_document_sync(shiyun_document, llm_client=LlmClient())
    # assert critical long-text fill rate >= 0.8
```

Default CI: `pytest backend/tests/golden/ -m "not llm"`.

---

### `backend/tests/golden/README.md` (config, —)

**Analog:** `06-FIELD-MATRIX.md` §2 + §6 (content structure, not code)

Document: Critical list, A/B/C/D nullability, normalization table (D-G03), `OPENAI_BASE_URL` / `LLM_MODEL` (D-CI04), commands from RESEARCH Validation Architecture.

---

## Shared Patterns

### Parse → rules → merge → export (production)

**Source:** `backend/app/extract/pipeline.py`  
**Apply to:** `pipeline_runner.py`, all golden integration tests

```89:99:contract_info/backend/app/extract/pipeline.py
    windows, truncated = build_section_windows(document)
    product_rules = extract_product_rules(document, windows)
    fund_fv = product_rules.get("基金全称")
    fund_name = str(fund_fv.value) if fund_fv and fund_fv.value else None
    fee_rates = extract_fee_rates(windows.get("fees", ""), fund_name, document)
```

### Rule-layer test fixture

**Source:** `backend/tests/test_extract_rules.py`  
**Apply to:** all `test_golden_rules_*`

```10:13:contract_info/backend/tests/test_extract_rules.py
@pytest.fixture
def sample_document(example_docx_path):
    doc = parse_docx(str(example_docx_path))
    return document_to_dict(doc)
```

Prefer **fixed example paths** in golden tests over `example_docx_path` (first glob docx) to avoid wrong contract.

### LLM off for default CI

**Source:** `backend/tests/test_extract_pipeline.py`  
**Apply to:** `test_golden_export.py`, `test_golden_rules_*`

```16:18:contract_info/backend/tests/test_extract_pipeline.py
class _LlmOff:
    available = False
    model_name = ""
```

### Xlsx header semantics (export = diff)

**Source:** `backend/app/export/column_map.py`, `xlsx_utils.py`  
**Apply to:** `xlsx_diff.py` only — **do not** import golden files in `validate_export.py` (D-E03).

### Contract vs golden assertion split

**Source:** `06-FIELD-MATRIX.md` §4–§6  
**Apply to:** all golden tests

| Assert against | Fields |
|----------------|--------|
| `contract_expected.json` | 管理人, 托管人, 风险等级, 锁定期, 预警/止损, 费率%, 基金全称, … |
| Golden xlsx (soft) | Column presence, sheet names, fee row morphology |
| Neither (allow mismatch) | 基金代码, 成立/备案日, MANUAL_ONLY, golden 管理人=弈倍 |

### Pytest markers

**Source:** `backend/tests/conftest.py`, `pytest.ini`  
**Apply to:** `test_golden_llm.py`

```10:12:contract_info/backend/tests/conftest.py
def pytest_configure(config):
    config.addinivalue_line("markers", "llm: requires OPENAI_API_KEY")
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `backend/tests/golden/README.md` | config | — | No test README in repo; mirror FIELD-MATRIX sections as prose |

## Metadata

**Analog search scope:** `contract_info/backend/app/extract/`, `backend/app/export/`, `backend/tests/`, `example/_contract_keys.json`  
**Files scanned:** ~25  
**Pattern extraction date:** 2026-05-26
