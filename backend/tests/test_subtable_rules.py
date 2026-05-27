from backend.app.extract.rules.lock_normalize import merge_lock_rows, normalize_lock_row
from backend.app.extract.rules.lock_rules import extract_lock_periods_rules
from backend.app.extract.rules.share_rules import extract_share_classes_rules
from backend.app.extract.schemas import FieldValue, LockPeriodRow


def test_lock_rules_no_lock_period_row():
    rows = extract_lock_periods_rules(
        "测试基金", FieldValue(value="", confidence="high", source="rule"), ""
    )
    assert len(rows) == 1
    assert rows[0].锁定期 == "无"
    assert rows[0].投资者类型 == "全部投资者"
    assert rows[0].份额类型 == "全部"


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


def test_lock_rules_employee_clause_implies_general_investor():
    text = (
        "本基金设置的份额锁定期限为90个自然日。"
        "本基金的管理人及其员工跟投本基金的，单笔认/申购份额的锁定期为6个月（180个自然日）。"
    )
    rows = extract_lock_periods_rules("测试基金", FieldValue(value="90天"), text)
    assert len(rows) == 2
    types = {r.投资者类型 for r in rows}
    assert types == {"一般投资者", "管理人及其员工"}
    by_type = {r.投资者类型: r for r in rows}
    assert "90" in str(by_type["一般投资者"].锁定时间 or "")
    assert "180" in str(by_type["管理人及其员工"].锁定时间 or "")
    assert all(r.份额类型 == "全部" for r in rows)


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


def test_merge_lock_dual_investor_prefers_rule_when_llm_matches_row_count():
    """LLM 两行都写 90 天时，仍应以申购章规则保留员工 180 天。"""
    text = (
        "本基金设置的份额锁定期限为90个自然日。"
        "本基金的管理人及其员工跟投本基金的，单笔认/申购份额的锁定期为6个月（180个自然日）。"
    )
    rules = extract_lock_periods_rules("测试基金", FieldValue(value="90天"), text)
    llm = [
        LockPeriodRow(
            产品名称="测试基金",
            份额类型="全部",
            锁定期="有",
            投资者类型="一般投资者",
            锁定时间="90天",
        ),
        LockPeriodRow(
            产品名称="测试基金",
            份额类型="全部",
            锁定期="有",
            投资者类型="管理人及其员工",
            锁定时间="90天",
        ),
    ]
    merged = merge_lock_rows(llm, rules, combined_text=text)
    by_type = {r.投资者类型: r for r in merged}
    assert "90" in str(by_type["一般投资者"].锁定时间 or "")
    assert "180" in str(by_type["管理人及其员工"].锁定时间 or "")


def test_merge_lock_keeps_dual_investor_when_llm_collapses():
    from backend.app.extract.rules.lock_normalize import merge_lock_rows

    rules = [
        LockPeriodRow(
            产品名称="石云中证1000资产进取一号私募证券投资基金",
            份额类型="全部",
            锁定期="有",
            投资者类型="一般投资者",
            锁定时间="180天",
        ),
        LockPeriodRow(
            产品名称="石云中证1000资产进取一号私募证券投资基金",
            份额类型="全部",
            锁定期="有",
            投资者类型="管理人及其员工",
            锁定时间="180天",
        ),
    ]
    llm = [
        LockPeriodRow(
            产品名称="石云中证1000资产进取一号私募证券投资基金",
            份额类型="A类",
            锁定期="180天",
            投资者类型="一般投资者",
        ),
    ]
    merged = merge_lock_rows(llm, rules)
    assert len(merged) == 2
    assert {r.投资者类型 for r in merged} == {"一般投资者", "管理人及其员工"}
    assert all(r.份额类型 == "全部" for r in merged)
    assert all(r.锁定时间 == "180天" for r in merged)


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


def test_share_rules_from_subscription_classification():
    product = {
        "预警线": FieldValue(value="无", confidence="high", source="rule"),
        "止损线": FieldValue(value="无", confidence="high", source="rule"),
    }
    rows = extract_share_classes_rules(
        {"blocks": []},
        {"subscription": "份额分类表 A类份额 B类份额 C类份额 D类份额"},
        fund_name="石云中证1000资产进取一号私募证券投资基金",
        fund_code=None,
        product_elements=product,
    )
    assert len(rows) == 4
    assert rows[0].预警线 == "无"
    assert all(r.基金全称 == "石云中证1000资产进取一号私募证券投资基金" for r in rows)
    assert any("证券投资基金A" in (r.分级份额名称 or "") for r in rows)


def test_merge_share_prefers_rules_when_llm_sparse():
    from backend.app.extract.rules.share_merge import merge_share_classes
    from backend.app.extract.schemas import ShareClassRow

    rules = [
        ShareClassRow(
            基金全称="石云福禄1000指数增强一号私募证券投资基金",
            分级份额名称="石云福禄1000指数增强一号A类",
            分级份额简称="A类",
            代码类型="A类份额",
        ),
        ShareClassRow(
            基金全称="石云福禄1000指数增强一号私募证券投资基金",
            分级份额名称="石云福禄1000指数增强一号B类",
            分级份额简称="B类",
            代码类型="B类份额",
        ),
    ]
    llm = [
        ShareClassRow(基金全称="石云福禄1000指数增强一号私募证券投资基金"),
    ]
    merged = merge_share_classes(rules, llm)
    assert len(merged) == 2
    assert merged[0].分级份额名称 == "石云福禄1000指数增强一号A类"
