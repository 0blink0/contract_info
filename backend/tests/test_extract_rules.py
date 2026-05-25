import pytest

from backend.app.extract.rules.fee_rules import extract_fee_rates
from backend.app.extract.rules.product_rules import extract_product_rules
from backend.app.extract.section_windows import build_section_windows
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict


@pytest.fixture
def sample_document(example_docx_path):
    doc = parse_docx(str(example_docx_path))
    return document_to_dict(doc)


def test_build_section_windows(sample_document):
    windows, truncated = build_section_windows(sample_document)
    assert windows["fees"]
    assert "基金管理人" in windows["cover_parties"] or "管理人" in windows["cover_parties"]


def test_product_rules_key_fields(sample_document):
    windows, _ = build_section_windows(sample_document)
    product = extract_product_rules(sample_document, windows)
    assert product.get("基金全称") and product["基金全称"].value
    assert product.get("管理人") and product["管理人"].value
    assert product.get("托管人") and product["托管人"].value


def test_fee_rules_at_least_two_rows(sample_document):
    windows, _ = build_section_windows(sample_document)
    product = extract_product_rules(sample_document, windows)
    fund = product.get("基金全称")
    name = str(fund.value) if fund and fund.value else None
    fees = extract_fee_rates(windows["fees"], name)
    assert len(fees) >= 2
    types = {r.运营费类型 for r in fees}
    assert "管理费" in types
    assert "托管费" in types
