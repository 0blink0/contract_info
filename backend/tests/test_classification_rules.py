from backend.app.extract.rules.classification_rules import (
    extract_classification_rules,
    infer_share_structure,
)
from backend.app.extract.schemas import ShareClassRow


def test_infer_share_structure_graded():
    rows = [
        ShareClassRow(分级份额简称="A类"),
        ShareClassRow(分级份额简称="B类"),
    ]
    windows = {"subscription": "A类份额、B类份额"}
    fv = infer_share_structure(rows, windows)
    assert fv and fv.value == "分级结构"


def test_infer_share_structure_not_graded():
    fv = infer_share_structure([], {"subscription": "申购赎回开放日"})
    assert fv and fv.value == "不分级"


def test_infer_share_structure_from_basic_abcd():
    basic = "（五）份额分类\nA类份额 B类份额 C类份额 D类份额"
    fv = infer_share_structure([], {"basic": basic})
    assert fv and fv.value == "分级结构"
    assert "A类" in (fv.snippet or "")


def test_extract_fund_and_product_type_fulu():
    from backend.app.parse.docx_parser import parse_docx
    from backend.app.parse.schemas import document_to_dict
    from backend.app.extract.section_windows import build_section_windows

    path = "example/石云福禄1000指数增强一号私募证券投资基金(1).docx"
    doc = document_to_dict(parse_docx(path))
    windows, _ = build_section_windows(doc)
    out = extract_classification_rules(doc, windows, {})
    assert "基金类型" not in out
    assert out["产品类型（协会）"].value == "权益类"
