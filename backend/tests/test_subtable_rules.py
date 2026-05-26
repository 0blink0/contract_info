from backend.app.extract.rules.lock_normalize import merge_lock_rows, normalize_lock_row
from backend.app.extract.rules.lock_rules import extract_lock_periods_rules
from backend.app.extract.rules.share_rules import extract_share_classes_rules
from backend.app.extract.schemas import FieldValue, LockPeriodRow


def test_lock_rules_minimal_row():
    lock_fv = FieldValue(value="锁定期 180天", confidence="high", source="rule")
    rows = extract_lock_periods_rules("测试基金", lock_fv, "锁定期 180天")
    assert len(rows) == 1
    assert rows[0].产品名称 == "测试基金"
    assert rows[0].锁定期 == "有"
    assert rows[0].锁定时间 == "180天"


def test_lock_rules_share_type_all():
    text = "A类份额、B类份额、C类份额、D类份额 锁定期180天 一次性解锁"
    rows = extract_lock_periods_rules("测试基金", FieldValue(value="180天"), text)
    assert rows[0].份额类型 == "全部"


def test_lock_rules_dual_investor():
    text = (
        "一般投资者 管理人及其员工 份额锁定期限为180天 "
        "交易确认日（含） 一次性解锁 转让、转换"
    )
    rows = extract_lock_periods_rules("测试基金", FieldValue(value="180天"), text)
    types = {r.投资者类型 for r in rows}
    assert "一般投资者" in types
    assert "管理人及其员工" in types


def test_normalize_llm_misplaced_duration():
    bad = LockPeriodRow(
        产品名称="测试基金",
        份额类型="A类/B类/C类/D类",
        锁定期="180天",
        投资者类型="一般投资者",
        起始规则="认购份额",
    )
    fixed = normalize_lock_row(bad)
    assert fixed.锁定期 == "有"
    assert fixed.锁定时间 == "180天"
    assert fixed.份额类型 == "全部"


def test_merge_lock_rows_fills_start_rule():
    llm = [
        LockPeriodRow(
            产品名称="测试基金",
            锁定期="180天",
            投资者类型="一般投资者",
        )
    ]
    rules = [
        LockPeriodRow(
            产品名称="测试基金",
            锁定期="有",
            锁定时间="180天",
            起始规则="交易确认日（含）",
            解锁方式="一次性解锁",
        )
    ]
    merged = merge_lock_rows(llm, rules)
    assert merged[0].锁定期 == "有"
    assert merged[0].锁定时间 == "180天"
    assert merged[0].起始规则 == "交易确认日（含）"
    assert merged[0].解锁方式 == "一次性解锁"


def test_share_rules_empty_when_not_graded():
    product = {"份额结构": FieldValue(value="不分级", confidence="medium", source="llm")}
    rows = extract_share_classes_rules(
        {"blocks": []},
        {"subscription": "A类份额 B类份额"},
        fund_name="测试基金",
        fund_code="X001",
        product_elements=product,
    )
    assert rows == []
