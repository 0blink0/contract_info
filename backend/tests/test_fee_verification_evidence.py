from backend.app.services.fee_verification_evidence import (
    narrative_excerpt_for_fee_type,
    resolve_fee_row_verification_evidence,
)

_SHARE_TABLE = {
    "id": "share-t",
    "type": "table",
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
    "text": (
        "1、基金管理费\n"
        "本基金的管理费按前一日资产净值年费率1%计提。\n"
        "2、基金的托管费\n"
        "本基金的托管费按前一日资产净值年费率0.05%计提。\n"
        "3、基金服务费\n"
        "外包服务费年费率为0.1%。"
    ),
}


def test_management_fee_gets_share_table_and_narrative():
    parse_json = {"blocks": [_SHARE_TABLE, _FEES_PARAGRAPH], "outline": []}
    row = {"运营费类型": "管理费", "费率（%/年）": "1"}
    excerpt, source, tables = resolve_fee_row_verification_evidence(row, parse_json)
    captions = [t.get("caption") for t in tables]
    assert "份额分类表" in captions
    assert excerpt
    assert "基金管理费" in excerpt
    assert source in ("table+narrative", "narrative", "table")


def test_custodian_fee_skips_share_table_has_narrative():
    parse_json = {"blocks": [_SHARE_TABLE, _FEES_PARAGRAPH], "outline": []}
    row = {"运营费类型": "托管费", "费率（%/年）": "0.05"}
    excerpt, source, tables = resolve_fee_row_verification_evidence(row, parse_json)
    captions = [t.get("caption") for t in tables]
    assert "份额分类表" not in captions
    assert excerpt
    assert "托管费" in excerpt


def test_narrative_excerpt_for_fee_type():
    text = _FEES_PARAGRAPH["text"]
    snip = narrative_excerpt_for_fee_type(text, "托管费")
    assert snip
    assert "托管费" in snip
