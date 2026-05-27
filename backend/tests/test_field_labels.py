from backend.app.validate.field_labels import label_for_validation_field


def test_path_b_open_day_label():
    assert (
        label_for_validation_field("path_b.open_day.fixed_schedule")
        == "开放日·固定安排"
    )


def test_path_b_tier_label():
    assert (
        label_for_validation_field("path_b.performance_fee.tiers[0].ratio_pct")
        == "业绩报酬·第1档·计提比例"
    )


def test_subscription_fee_row_label_uses_fee_type():
    extraction = {
        "subscription_fees": [
            {"申赎费类型": "认购费", "费率": "0"},
            {"申赎费类型": "申购费", "费率": "1"},
        ]
    }
    assert (
        label_for_validation_field(
            "subscription_fees[0].申赎费类型", extraction
        )
        == "认购费·第1行·申赎费类型"
    )
    assert (
        label_for_validation_field(
            "subscription_fees[1].费率", extraction
        )
        == "申购费·第2行·费率"
    )
