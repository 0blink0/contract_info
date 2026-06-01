from pathlib import Path

import pytest

from backend.app.extract.rules.fee_rules import extract_fee_rates
from backend.app.extract.rules.product_rules import extract_product_rules
from backend.app.extract.section_windows import build_section_windows
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict

FULU_DOCX = (
    Path(__file__).resolve().parents[2]
    / "example"
    / "石云福禄1000指数增强一号私募证券投资基金(1).docx"
)


@pytest.fixture
def sample_document(example_docx_path):
    doc = parse_docx(str(example_docx_path))
    return document_to_dict(doc)


@pytest.fixture
def fulu_document():
    if not FULU_DOCX.is_file():
        pytest.skip("福禄 example docx missing")
    return document_to_dict(parse_docx(str(FULU_DOCX)))


def test_build_section_windows(sample_document):
    windows, truncated = build_section_windows(sample_document)
    assert windows["fees"]
    assert "基金管理人" in windows["cover_parties"] or "管理人" in windows["cover_parties"]


def test_product_rules_no_stop_lines_and_subscription(fulu_document):
    windows, _ = build_section_windows(fulu_document)
    product = extract_product_rules(fulu_document, windows)
    assert product["预警线"].value == "无"
    assert product["止损线"].value == "无"
    assert "不设置预警线" in (product["止损线"].snippet or "")
    assert product.get("首次申购起点")
    assert "100" in str(product["首次申购起点"].value)
    assert product.get("最小变动单位")
    assert product.get("追加起点")
    assert product["追加起点"].value == "无追加起点限制"
    assert "基金简称" not in product
    assert "银行账户信息" not in product
    assert "基金代码" not in product
    assert "成立日期" not in product
    assert "封闭期起始日" not in product


def test_product_rules_face_value_yuan_implies_rmb():
    from backend.app.extract.rules.product_rules import _currency_from_face_snippet

    assert _currency_from_face_snippet("初始募集面值：1.0000 元") == "人民币现钞"
    assert _currency_from_face_snippet("初始募集面值：人民币 1 元") == "人民币现钞"
    assert _currency_from_face_snippet("初始募集面值：1 美元") == ""


def test_product_rules_all_investment_managers(fulu_document):
    windows, _ = build_section_windows(fulu_document)
    product = extract_product_rules(fulu_document, windows)
    val = str(product["投资经理"].value)
    assert "王敏敏" in val
    assert "李森林" in val
    assert "、" in val


def test_product_rules_face_value_from_basic(fulu_document):
    windows, _ = build_section_windows(fulu_document)
    product = extract_product_rules(fulu_document, windows)
    assert product.get("基金面值")
    assert product["基金面值"].value == "1"
    assert product.get("币种")
    assert product["币种"].value == "人民币现钞"


def test_product_rules_key_fields(sample_document):
    windows, _ = build_section_windows(sample_document)
    product = extract_product_rules(sample_document, windows)
    assert product.get("基金全称") and product["基金全称"].value
    assert product.get("管理人") and product["管理人"].value
    assert product.get("托管人") and product["托管人"].value


def test_zhengren_fee_rules_only_three_operating_types():
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "example"
        / "正仁1号私募证券投资基金私募基金合同.docx"
    )
    if not path.is_file():
        pytest.skip("missing zhengren docx")
    doc = document_to_dict(parse_docx(str(path)))
    windows, _ = build_section_windows(doc)
    product = extract_product_rules(doc, windows)
    name = str(product["基金全称"].value)
    from backend.app.extract.rules.fee_rules import (
        enrich_fee_rates_from_fees_chapter,
        gather_fee_source_text,
    )

    source = gather_fee_source_text(windows.get("fees", ""), doc)
    fees = enrich_fee_rates_from_fees_chapter(
        extract_fee_rates(source, name, doc), source
    )
    types = {r.运营费类型 for r in fees}
    assert types == {"管理费", "托管费", "基金服务费"}
    by_type = {r.运营费类型: r.rate_annual_pct for r in fees}
    assert by_type["管理费"] == "0"
    assert by_type["托管费"] == "0.025"
    assert by_type["基金服务费"] == "0.025"


def test_fee_rules_at_least_two_rows(sample_document):
    windows, _ = build_section_windows(sample_document)
    product = extract_product_rules(sample_document, windows)
    fund = product.get("基金全称")
    name = str(fund.value) if fund and fund.value else None
    fees = extract_fee_rates(windows["fees"], name, sample_document)
    assert len(fees) >= 2
    types = {r.运营费类型 for r in fees}
    assert "管理费" in types
    assert "托管费" in types


def test_fee_rules_billing_from_fees_chapter(example_docx_path):
    doc = document_to_dict(parse_docx(str(example_docx_path)))
    windows, _ = build_section_windows(doc)
    product = extract_product_rules(doc, windows)
    name = str(product["基金全称"].value)
    from backend.app.extract.rules.fee_rules import enrich_fee_rates_from_fees_chapter

    fees = enrich_fee_rates_from_fees_chapter(
        extract_fee_rates(windows["fees"], name, doc), windows["fees"]
    )
    assert fees
    # Zero-rate rows (不收取) should not receive billing attributes from other
    # fee subsections; only rows with an actual rate are enriched.
    billed = [r for r in fees if r.rate_annual_pct != "0"]
    assert billed
    assert all(r.计费频率 == "按日" for r in billed)
    assert all(r.计费基准 == "前一日资产净值" for r in billed)


def test_fee_rules_per_share_class_when_table_present(example_docx_path):
    doc = document_to_dict(parse_docx(str(example_docx_path)))
    windows, _ = build_section_windows(doc)
    product = extract_product_rules(doc, windows)
    name = str(product["基金全称"].value)
    fees = extract_fee_rates(windows["fees"], name, doc)
    mgmt = [r for r in fees if r.运营费类型 == "管理费"]
    if len(mgmt) >= 4:
        names = {r.基金名称 for r in mgmt}
        assert len(names) >= 4
        rates = {r.rate_annual_pct for r in mgmt}
        assert "0" in rates or "0.0" in rates
        assert "1" in rates
