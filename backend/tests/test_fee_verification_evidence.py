from backend.app.services.fee_verification_evidence import resolve_fee_row_verification_evidence

_FEES_SECTION_ID = "fees-section"

_SHARE_TABLE = {
    "id": "share-t",
    "type": "table",
    "section_id": _FEES_SECTION_ID,
    "rows": [
        ["", "A类", "B类"],
        ["分类标准", "专业投资者", "专业投资者"],
        ["认购费率", "【0.5%】", "【0%】"],
        ["申购费率", "【0.5%】", "【0%】"],
        ["年管理费率", "【1%】", "【0%】"],
    ],
}

_FEES_PARAGRAPH = {
    "id": "p-fee-1",
    "type": "paragraph",
    "section_id": _FEES_SECTION_ID,
    "text": (
        "1、基金管理费\n"
        "本基金的管理费按前一日资产净值年费率1%计提。\n"
        "2、基金的托管费\n"
        "本基金的托管费按前一日资产净值年费率0.05%计提。\n"
        "3、基金服务费\n"
        "外包服务费年费率为0.1%。"
    ),
}

_OUTLINE = [{"anchor_id": _FEES_SECTION_ID, "title": "基金的费用与税收"}]


def test_management_fee_gets_share_table_and_narrative():
    parse_json = {"blocks": [_SHARE_TABLE, _FEES_PARAGRAPH], "outline": _OUTLINE}
    row = {
        "运营费类型": "管理费",
        "费率（%/年）": "1",
        "snippet": "本基金的管理费按前一日资产净值年费率1%计提。",
    }
    excerpt, source, tables = resolve_fee_row_verification_evidence(row, parse_json)
    captions = [t.get("caption") for t in tables]
    assert "份额分类表" in captions
    assert excerpt
    assert "管理费" in excerpt
    assert source == "table+narrative"


def test_custodian_fee_skips_share_table_uses_row_snippet():
    parse_json = {"blocks": [_SHARE_TABLE, _FEES_PARAGRAPH], "outline": _OUTLINE}
    # snippet comes from LLM per-row 原文, not post-processing regex
    row = {
        "运营费类型": "托管费",
        "费率（%/年）": "0.05",
        "snippet": "本基金的托管费按前一日资产净值年费率0.05%计提。",
    }
    excerpt, source, tables = resolve_fee_row_verification_evidence(row, parse_json)
    captions = [t.get("caption") for t in tables]
    assert "份额分类表" not in captions
    assert excerpt
    assert "托管费" in excerpt


def test_custodian_fee_no_snippet_no_excerpt():
    parse_json = {"blocks": [_SHARE_TABLE, _FEES_PARAGRAPH], "outline": _OUTLINE}
    row = {"运营费类型": "托管费", "费率（%/年）": "0.05"}
    excerpt, source, tables = resolve_fee_row_verification_evidence(row, parse_json)
    assert excerpt is None
    assert source in (None, "table")
