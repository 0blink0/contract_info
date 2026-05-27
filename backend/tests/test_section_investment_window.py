from pathlib import Path

from backend.app.extract.rules.product_rules import extract_product_rules
from backend.app.extract.section_windows import build_section_windows
from backend.app.parse.docx_parser import parse_docx
from backend.app.parse.schemas import document_to_dict

FULU = Path(__file__).resolve().parents[2] / (
    "example/石云福禄1000指数增强一号私募证券投资基金(1).docx"
)


def test_investment_window_excludes_investor_commitment():
    doc = document_to_dict(parse_docx(str(FULU)))
    windows, _ = build_section_windows(doc)
    inv = windows["investment"]
    assert "合格投资者" not in inv[:400] or "（五）投资限制" in inv
    assert "基金总资产与净资产的比例不得超过200%" in inv


def test_subscription_closed_period_none():
    doc = document_to_dict(parse_docx(str(FULU)))
    windows, _ = build_section_windows(doc)
    product = extract_product_rules(doc, windows)
    assert product["是否封闭"].value == "不封闭"
    assert "封闭期" in (product["是否封闭"].snippet or "")
    assert product.get("是否支持金额赎回")
    assert product["是否支持金额赎回"].value == "不支持"
