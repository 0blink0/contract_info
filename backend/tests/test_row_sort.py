from backend.app.extract.row_sort import sort_fee_rates, sort_subscription_fees
from backend.app.extract.schemas import FeeRateRow, SubscriptionFeeRow


def test_sort_fee_rates_groups_by_fee_type():
    rows = [
        FeeRateRow(基金名称="基金D", 运营费类型="销售服务费", rate_annual_pct="0"),
        FeeRateRow(基金名称="基金A", 运营费类型="管理费", rate_annual_pct="1"),
        FeeRateRow(基金名称="基金", 运营费类型="托管费", rate_annual_pct="0.03"),
        FeeRateRow(基金名称="基金B", 运营费类型="管理费", rate_annual_pct="1"),
    ]
    ordered = sort_fee_rates(rows)
    types = [r.运营费类型 for r in ordered]
    assert types == ["管理费", "管理费", "托管费", "销售服务费"]
    assert [r.基金名称 for r in ordered[:2]] == ["基金A", "基金B"]


def test_sort_subscription_fees_groups_by_fee_type():
    rows = [
        SubscriptionFeeRow(基金名称="基金B", 申赎费类型="申购费", 费率="0"),
        SubscriptionFeeRow(基金名称="基金A", 申赎费类型="认购费", 费率="0.5"),
        SubscriptionFeeRow(基金名称="基金A", 申赎费类型="申购费", 费率="0.5"),
        SubscriptionFeeRow(基金名称="基金B", 申赎费类型="认购费", 费率="0"),
    ]
    ordered = sort_subscription_fees(rows)
    types = [r.申赎费类型 for r in ordered]
    assert types == ["认购费", "认购费", "申购费", "申购费"]
