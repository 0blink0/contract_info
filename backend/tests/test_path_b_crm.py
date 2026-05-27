from backend.app.extract.path_b_crm import build_crm_handoff


def test_crm_handoff_fulu_like_sample():
    path_b = {
        "performance_fee": {
            "extraction_method": "份额净值：指所投资私募性质金融产品",
            "benchmark_type": "超额收益",
            "hurdle_nav": "有收益门槛（正收益基础）",
            "extraction_timing": "固定时点",
            "tiers": [
                {
                    "share_class": "A",
                    "ratio_pct": "20",
                    "description": "正收益基础上针对超过期间中证500以上的部分计提20%",
                },
                {
                    "share_class": "D",
                    "description": "不计提业绩报酬",
                },
            ],
        },
        "open_day": {
            "fixed_schedule": "本基金的开放日为基金成立之后每自然月的2日和16日",
        },
        "source_snippets": {
            "performance_fee.benchmark_type": "超额收益",
            "open_day.fixed_schedule": "本基金的开放日为基金成立之后每自然月的2日和16日",
        },
    }
    items = build_crm_handoff(path_b, fees_context="业绩报酬 赎回 分红")
    by_field = {i["crm_field"]: i for i in items}
    assert by_field["业绩报酬提取方式"]["suggested_value"] == "份额净值法"
    assert by_field["业绩基准类型"]["suggested_value"] == "超额收益"
    assert by_field["提取比例"]["suggested_value"]
    assert "20" in by_field["提取比例"]["suggested_value"]
    assert by_field["固定时点提取频率"]["suggested_value"]
    assert by_field["提取时点"]["suggested_value"]
    assert by_field["门槛净值类型"]["suggested_value"]


def test_crm_handoff_on_fulu_docx():
    from pathlib import Path

    from backend.app.extract.rules.path_b_rules import extract_path_b_rules
    from backend.app.extract.section_windows import build_section_windows
    from backend.app.extract.rules.product_rules import extract_product_rules
    from backend.app.parse.docx_parser import parse_docx

    path = Path("example/石云福禄1000指数增强一号私募证券投资基金(1).docx")
    if not path.exists():
        import pytest

        pytest.skip("fulu docx missing")
    doc = parse_docx(str(path))
    windows, _ = build_section_windows(doc)
    product = extract_product_rules(doc, windows)
    path_b, _ = extract_path_b_rules(
        doc, windows, fund_name=None, product_elements=product
    )
    fees_ctx = windows.get("fees", "") or ""
    items = build_crm_handoff(path_b, fees_context=fees_ctx)
    by_field = {i["crm_field"]: i for i in items}
    assert by_field["提取比例"]["suggested_value"]
    assert by_field["固定时点提取频率"]["suggested_value"]
    assert "2日" in by_field["固定时点提取频率"]["suggested_value"] or "16日" in (
        by_field["固定时点提取频率"]["suggested_value"] or ""
    )
