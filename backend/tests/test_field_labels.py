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
