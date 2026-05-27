from backend.app.extract.field_snippets import resolve_field_snippet

_PAD = "前言说明。" * 80


def test_snippet_finds_anchor_late_in_chapter():
    text = (
        _PAD
        + "（八）业绩比较基准\n本基金不设业绩比较基准。"
        + _PAD
        + "（十二）投资经理\n1、投资经理简介\n王敏敏，曾任某公司总经理。"
    )
    snip = resolve_field_snippet("业绩比较基准", text, "无")
    assert "业绩比较基准" in snip
    assert "不设" in snip
    assert "（八）" in snip

    mgr = resolve_field_snippet("投资经理", text, "王敏敏")
    assert "投资经理" in mgr
    assert "王敏敏" in mgr


def test_snippet_empty_when_anchor_missing():
    assert resolve_field_snippet("业绩比较基准", _PAD, "无") == ""
