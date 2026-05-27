from backend.app.extract.rules.assoc_product_type import infer_assoc_product_type


def test_equity_80pct_from_stock_clause():
    text = (
        "（五）投资限制\n"
        "投资于股票等股权类资产的比例，按市值计算，"
        "在本基金存续期内不得低于本基金已投资产的80%。"
    )
    typ, snip = infer_assoc_product_type({"investment": text})
    assert typ == "权益类"
    assert snip and "80" in snip


def test_mixed_when_no_80pct():
    text = "投资范围包括股票、债券、期货等多种资产，无单一类别下限。"
    typ, _ = infer_assoc_product_type({"investment": text})
    assert typ == "混合类"


def test_mixed_when_multiple_80_categories():
    text = (
        "股权类资产不低于80%；固定收益类资产不低于80%。"
    )
    typ, _ = infer_assoc_product_type({"investment": text})
    assert typ == "混合类"


def test_fulu_contract_investment_window():
    from pathlib import Path

    from backend.app.extract.rules.classification_rules import extract_classification_rules
    from backend.app.extract.section_windows import build_section_windows
    from backend.app.parse.docx_parser import parse_docx
    from backend.app.parse.schemas import document_to_dict

    path = Path("example/石云福禄1000指数增强一号私募证券投资基金(1).docx")
    if not path.is_file():
        return
    doc = document_to_dict(parse_docx(str(path)))
    windows, _ = build_section_windows(doc)
    typ, _ = infer_assoc_product_type(windows)
    assert typ == "权益类"
    out = extract_classification_rules(doc, windows, {})
    assert out["产品类型（协会）"].value == "权益类"
    assert "80%" in out["产品类型（协会）"].snippet or "80" in out["产品类型（协会）"].snippet
