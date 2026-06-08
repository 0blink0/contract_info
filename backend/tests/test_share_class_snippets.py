from backend.app.extract.evidence_enrich import resolve_share_class_cell_snippet


def test_share_risk_fields_use_investment_section_not_classification_snippet():
    row = {
        "snippet": "本基金分为A类基金份额和B类基金份额。",
        "分级份额名称": "石云诚致1号私募证券投资基金A类",
        "预警线": "0.850",
        "止损线": "0.800",
    }
    windows = {
        "basic": "本基金分为A类基金份额和B类基金份额。",
        "investment": (
            "（十一）基金的预警与止损\n"
            "本基金的预警线为0.850，当单位净值低于预警线时管理人应通知投资者；"
            "止损线为0.800。"
        ),
    }
    warn_snip = resolve_share_class_cell_snippet("预警线", "0.850", row, windows, {})
    stop_snip = resolve_share_class_cell_snippet("止损线", "0.800", row, windows, {})
    name_snip = resolve_share_class_cell_snippet(
        "分级份额名称",
        "石云诚致1号私募证券投资基金A类",
        row,
        windows,
        {},
    )

    assert warn_snip
    assert "预警" in warn_snip
    assert "0.850" in warn_snip
    assert "A类基金份额" not in warn_snip

    assert stop_snip
    assert "止损" in stop_snip
    assert "0.800" in stop_snip

    assert name_snip == row["snippet"]
