from pathlib import Path

from backend.app.extract.rules.product_rules import extract_product_rules
from backend.app.extract.section_windows import build_section_windows
from backend.app.parse.docx_parser import parse_docx
from backend.app.parse.schemas import document_to_dict

FULU = Path(__file__).resolve().parents[2] / (
    "example/石云福禄1000指数增强一号私募证券投资基金(1).docx"
)
ZHENGREN = Path(__file__).resolve().parents[2] / (
    "example/正仁1号私募证券投资基金私募基金合同.docx"
)


def test_investment_window_excludes_investor_commitment():
    doc = document_to_dict(parse_docx(str(FULU)))
    windows, _ = build_section_windows(doc)
    inv = windows["investment"]
    assert "合格投资者" not in inv[:400] or "（五）投资限制" in inv
    assert "基金总资产与净资产的比例不得超过200%" in inv


def test_investment_window_includes_benchmark_and_risk():
    doc = document_to_dict(parse_docx(str(FULU)))
    windows, _ = build_section_windows(doc)
    inv = windows["investment"]
    assert "（八）业绩比较基准" in inv
    assert "（十）风险收益特征" in inv
    product = extract_product_rules(doc, windows)
    assert product["业绩比较基准"].value == "无"
    assert "不设业绩比较基准" in (product["业绩比较基准"].snippet or "")
    assert product["风险收益特征"].value
    assert "R4" in str(product["风险收益特征"].value)


def test_zhengren_investment_chapter_rebuild_and_objective():
    if not ZHENGREN.exists():
        return
    doc = document_to_dict(parse_docx(str(ZHENGREN)))
    windows, _ = build_section_windows(doc)
    inv = windows["investment"]
    assert "十一、私募基金的投资" in inv
    assert "投资目标" in inv
    product = extract_product_rules(doc, windows)
    goal = product.get("投资目标")
    assert goal and "长期稳定" in str(goal.value)
    assert product.get("业绩比较基准") is None
    assert product.get("风险收益特征") is None


def test_subscription_closed_period_none():
    doc = document_to_dict(parse_docx(str(FULU)))
    windows, _ = build_section_windows(doc)
    product = extract_product_rules(doc, windows)
    assert product["是否封闭"].value == "不封闭"
    assert "封闭期" in (product["是否封闭"].snippet or "")
    assert product.get("是否支持金额赎回")
    assert product["是否支持金额赎回"].value == "不支持"
