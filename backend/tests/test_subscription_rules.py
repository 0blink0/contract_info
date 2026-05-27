"""申赎费率规则抽取（无 LLM）。"""

from pathlib import Path

import pytest

from backend.app.extract.pipeline import extract_document_sync
from backend.app.extract.rules.subscription_rules import extract_subscription_fees_rules
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict
from backend.app.extract.section_windows import build_section_windows
from backend.app.extract.rules.product_rules import extract_product_rules
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict
from backend.app.extract.rules.share_rules import extract_share_classes_rules
from backend.tests.golden.conftest import FULU_KEY, SHIYUN_KEY, load_contract_expected

EXAMPLE = Path(__file__).resolve().parents[2] / "example"


class LlmOff:
    available = False
    model_name = ""


def _run_rules(docx_name: str):
    path = EXAMPLE / docx_name
    if not path.is_file():
        pytest.skip(f"missing {path}")
    doc = document_to_dict(parse_docx(str(path)))
    windows, _ = build_section_windows(doc)
    product = extract_product_rules(doc, windows)
    fund_name = str(product["基金全称"].value) if product.get("基金全称") else None
    fund_code = str(product["基金代码"].value) if product.get("基金代码") else None
    share_classes = extract_share_classes_rules(
        doc, windows, fund_name=fund_name, fund_code=fund_code, product_elements=product
    )
    return extract_subscription_fees_rules(
        doc, windows, fund_name=fund_name, share_classes=share_classes, product_elements=product
    )


def _rates_by_share(rows, letter: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        name = row.基金名称 or ""
        if letter not in name.upper():
            continue
        if row.申赎费类型:
            out[row.申赎费类型] = row.费率 or "0"
    return out


@pytest.mark.parametrize("docx_key", [SHIYUN_KEY, FULU_KEY])
def test_subscription_min_rows(docx_key):
    rows = _run_rules(docx_key)
    assert len(rows) >= 8


@pytest.mark.parametrize("docx_key", [SHIYUN_KEY, FULU_KEY])
def test_subscription_fee_types(docx_key):
    rows = _run_rules(docx_key)
    types = {r.申赎费类型 for r in rows}
    assert "认购费" in types
    assert "申购费" in types


def test_shiyun_subscription_rates_match_contract():
    expected = load_contract_expected()[SHIYUN_KEY].get("subscription_fees_by_share", {})
    rows = _run_rules(SHIYUN_KEY)
    for letter, rates in expected.items():
        got = _rates_by_share(rows, letter)
        for fee_type, rate in rates.items():
            assert got.get(fee_type) == rate, f"{letter} {fee_type}"


def test_fulu_subscription_rates_match_contract():
    expected = load_contract_expected()[FULU_KEY].get("subscription_fees_by_share", {})
    rows = _run_rules(FULU_KEY)
    for letter, rates in expected.items():
        got = _rates_by_share(rows, letter)
        for fee_type, rate in rates.items():
            assert got.get(fee_type) == rate, f"{letter} {fee_type}"


def test_fulu_redeem_tier_rows():
    rows = _run_rules(FULU_KEY)
    redeem = [r for r in rows if r.申赎费类型 == "赎回费" and r.计费基准]
    assert len(redeem) == 3
    bases = {r.计费基准 for r in redeem}
    assert bases == {"区间"}
    ends = {r.区间结束 for r in redeem if not r.区间开始}
    assert ends == {"180"}


def test_redeem_line_skips_range_inner_lt():
    from backend.app.extract.rules.subscription_rules import _tier_from_redeem_line

    assert _tier_from_redeem_line(
        "2）若投资者赎回的基金份额持有天数：180日≤（t）＜360日，则短期赎回费率为0.2%。"
    ) == {
        "计费基准": "区间",
        "区间开始": "180",
        "区间结束": "360",
        "时间区间单位": "天",
        "费率": "0.2",
    }
    assert _tier_from_redeem_line(
        "1）若投资者赎回的基金份额持有天数：（t）＜180日，则短期赎回费率为1%。"
    )["计费基准"] == "区间"


ZHENGREN_DOCX = "正仁1号私募证券投资基金私募基金合同.docx"


def test_fulu_compose_snippet_table_and_formula():
    from backend.tests.golden.conftest import FULU_KEY

    rows = _run_rules(FULU_KEY)
    sub_a = [
        r
        for r in rows
        if r.申赎费类型 == "认购费" and r.基金名称 and "A" in (r.基金名称 or "").upper()
    ]
    assert sub_a, "missing A-class 认购费 row"
    snip = sub_a[0].snippet or ""
    assert "份额分类" in snip or "基本情况" in snip
    assert "0.5" in snip or "0.5%" in snip
    assert "净认购金额" in snip or "认购份额" in snip
    assert "认购资金从在中国境内开立" not in snip[:120]


def test_fulu_subscription_billing_inclusive_purchase():
    from backend.app.extract.rules.subscription_rules import (
        gather_subscription_rules_text,
        infer_subscription_billing_rules,
    )
    from backend.tests.golden.conftest import FULU_KEY

    rows = _run_rules(FULU_KEY)
    path = EXAMPLE / FULU_KEY
    doc = document_to_dict(parse_docx(str(path)))
    windows, _ = build_section_windows(doc)
    text = gather_subscription_rules_text(doc, windows)
    billing = infer_subscription_billing_rules(text)
    assert billing.get("申购费") == "价内法"
    purchase = [r for r in rows if r.申赎费类型 == "申购费"]
    assert purchase and purchase[0].计费方式 == "价内法"


def test_zhengren_narrative_subscription_fees():
    rows = _run_rules(ZHENGREN_DOCX)
    assert rows, "expected subscription fee rows"
    subscribe = [r for r in rows if r.申赎费类型 == "认购费"]
    assert subscribe and subscribe[0].费率 == "0"
    assert subscribe[0].snippet
    assert "认购费率为" in subscribe[0].snippet
    assert "七、私募基金的申购" not in (subscribe[0].snippet or "")
    purchase = [r for r in rows if r.申赎费类型 == "申购费"]
    assert purchase, "missing 申购费 row"
    assert purchase[0].费率 == "1"
    assert purchase[0].计费方式 == "价外法"
    assert purchase[0].计费基准 == "不分段"
    assert purchase[0].基金名称 and not purchase[0].基金名称.endswith("A")
    assert purchase[0].snippet
    assert "申购费率为" in purchase[0].snippet
    assert "五、私募基金的募集" not in (purchase[0].snippet or "")[:80]
    redeem = [r for r in rows if r.申赎费类型 == "赎回费" and r.计费基准]
    assert len(redeem) == 3
    assert all(r.计费基准 == "区间" for r in redeem)
    gte = [r for r in redeem if r.区间开始 == "365"]
    assert len(gte) == 1 and gte[0].费率 == "0"
    assert all(r.snippet for r in rows)
    assert redeem[0].snippet and "赎回费率" in redeem[0].snippet
    assert all(r.计费方式 == "价内法" for r in redeem)


def test_extract_document_sync_has_subscription_fees():
    path = EXAMPLE / SHIYUN_KEY
    if not path.is_file():
        pytest.skip("missing shiyun docx")
    doc = document_to_dict(parse_docx(str(path)))
    result, _, path_b = extract_document_sync(doc, llm_client=LlmOff())  # type: ignore[arg-type]
    assert path_b.get("performance_fee") or path_b.get("open_day")
    assert len(result.subscription_fees) >= 8
