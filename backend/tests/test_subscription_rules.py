"""申赎费率规则抽取（无 LLM）。"""

from pathlib import Path

import pytest

from backend.app.extract.pipeline import extract_document_sync
from backend.app.extract.rules.subscription_rules import extract_subscription_fees_rules
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict
from backend.app.extract.section_windows import build_section_windows
from backend.app.extract.rules.product_rules import extract_product_rules
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
    assert len(redeem) >= 3
    bases = {r.计费基准 for r in redeem}
    assert "区间（P＜A）" in bases


def test_extract_document_sync_has_subscription_fees():
    path = EXAMPLE / SHIYUN_KEY
    if not path.is_file():
        pytest.skip("missing shiyun docx")
    doc = document_to_dict(parse_docx(str(path)))
    result, _, path_b = extract_document_sync(doc, llm_client=LlmOff())  # type: ignore[arg-type]
    assert path_b.get("performance_fee") or path_b.get("open_day")
    assert len(result.subscription_fees) >= 8
