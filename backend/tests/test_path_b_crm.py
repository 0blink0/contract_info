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
    """需 LLM 抽取的集成测试；无 API Key 时跳过。"""
    import os
    from pathlib import Path

    import pytest

    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    from backend.app.extract.pipeline import extract_document_sync
    from backend.app.parse.docx_parser import parse_docx
    from backend.app.parse.schemas import document_to_dict

    path = Path("example/石云福禄1000指数增强一号私募证券投资基金(1).docx")
    if not path.exists():
        pytest.skip("fulu docx missing")
    doc = document_to_dict(parse_docx(str(path)))
    _, _, path_b = extract_document_sync(doc)
    fees_ctx = (path_b.get("raw_sections") or {}).get("performance_fee", "")
    items = build_crm_handoff(path_b, fees_context=fees_ctx)
    by_field = {i["crm_field"]: i for i in items}
    assert by_field.get("提取比例", {}).get("suggested_value")
