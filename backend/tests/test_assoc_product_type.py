from backend.app.extract.rules.assoc_product_type import infer_assoc_product_type


def test_equity_80pct_total_assets():
    """80% 相对总资产（无已投资产限定）→ 权益类。"""
    text = (
        "本基金存续期内，投资于股票等权益类资产的比例"
        "不低于基金净资产的80%。"
    )
    typ, snip = infer_assoc_product_type({"investment": text})
    assert typ == "权益类"
    assert snip and "80" in snip


def test_equity_80pct_invested_assets_no_deriv():
    """80% 相对已投资产但无期货独立类别 → 仍可识别为权益类（保守场景）。"""
    text = (
        "（五）投资限制\n"
        "投资于股票等股权类资产的比例，按市值计算，"
        "在本基金存续期内不得低于本基金已投资产的80%。"
    )
    typ, snip = infer_assoc_product_type({"investment": text})
    # 无期货独立类别 → 权益类（步骤2不触发，步骤4匹配）
    assert typ == "权益类"
    assert snip and "80" in snip


def test_mixed_invested_assets_with_deriv_category():
    """80% 相对已投资产（不含现金）+ 期货作为独立类别 → 混合类。

    典型场景：指数增强策略，投资限制"股票≥80%已投资产，
    已投资产不含现金工具"，且投资范围将"期货和衍生品类"列为大类。
    实际股票占总NAV可能远低于80%，协会归类为混合类。
    """
    text = (
        "（三）投资范围\n"
        "1、权益类：国内依法发行上市的股票（含新股申购）\n"
        "2、固定收益类：债券通用质押式回购\n"
        "3、期货和衍生品类：金融期货、商品期货、场内期权\n"
        "4、现金管理类：银行活期存款、货币市场基金\n"
        "（五）投资限制\n"
        "按市值计算，本基金直接和间接投资于股票等股权类资产的比例"
        "不低于本基金已投资产80%，已投资产不包含现金管理工具。"
    )
    typ, snip = infer_assoc_product_type({"investment": text})
    assert typ == "混合类", f"期望混合类，实际={typ!r}"
    assert snip


def test_mixed_when_no_80pct():
    """无任何80%约束但多类资产明确列举 → 混合类。"""
    text = "投资范围包括股票、债券、期货等多种资产，无单一类别下限。"
    typ, _ = infer_assoc_product_type({"investment": text})
    assert typ == "混合类"


def test_mixed_when_multiple_80_categories():
    """多资产类别各含80%约束（数学上不可能同时满足）→ 混合类。"""
    text = "股权类资产不低于80%；固定收益类资产不低于80%。"
    typ, _ = infer_assoc_product_type({"investment": text})
    assert typ == "混合类"


def test_fixed_income_80pct():
    """债券 ≥80% → 固定收益类。"""
    text = "本基金投资于固定收益类资产的比例不低于基金资产的80%。"
    typ, snip = infer_assoc_product_type({"investment": text})
    assert typ == "固定收益类"
    assert snip and "80" in snip


def test_shiyufulu_contract_is_mixed():
    """石云福禄1000指数增强一号合同：已投资产限定+期货独立类别 → 混合类。"""
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
    typ, snip = infer_assoc_product_type(windows)
    assert typ == "混合类", (
        f"期望混合类（已投资产限定+期货独立类别），实际={typ!r}\nsnip={snip}"
    )
    out = extract_classification_rules(doc, windows, {})
    assert out["产品类型（协会）"].value == "混合类"
