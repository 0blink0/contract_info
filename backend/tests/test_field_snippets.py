from backend.app.extract.field_snippets import extract_section_body, resolve_field_snippet

_PAD = "前言说明。" * 80


def test_snippet_finds_anchor_late_in_chapter():
    text = (
        _PAD
        + "（八）业绩比较基准\n本基金不设业绩比较基准。"
    )
    snip = resolve_field_snippet("业绩比较基准", text, "无")
    assert "业绩比较基准" in snip
    assert "不设" in snip
    assert "（八）" in snip


def test_snippet_empty_when_anchor_missing():
    assert resolve_field_snippet("业绩比较基准", _PAD, "无") == ""


def test_extract_section_body_benchmark():
    text = (
        "（七）关联交易\n略。\n"
        "（八）业绩比较基准\n本基金不设业绩比较基准。\n"
        "（九）融资融券\n其他内容。"
    )
    body, snip = extract_section_body("业绩比较基准", text)
    assert body == "本基金不设业绩比较基准。"
    assert snip and "业绩比较基准" in snip


def test_extract_section_body_risk():
    text = (
        "（十）风险收益特征：\n本基金属于R4级投资品种，适合专业投资者。\n"
        "（十一）基金的预警与止损：\n本基金不设置预警线。"
    )
    body, _ = extract_section_body("风险收益特征", text)
    assert body and "R4" in body
