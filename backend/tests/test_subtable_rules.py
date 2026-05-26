from backend.app.extract.rules.lock_rules import extract_lock_periods_rules
from backend.app.extract.rules.share_rules import extract_share_classes_rules
from backend.app.extract.schemas import FieldValue


def test_lock_rules_minimal_row():
    lock_fv = FieldValue(value="锁定期 180天", confidence="high", source="rule")
    rows = extract_lock_periods_rules("测试基金", lock_fv, "锁定期 180天")
    assert len(rows) == 1
    assert rows[0].产品名称 == "测试基金"
    assert rows[0].锁定期 == "有"


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
