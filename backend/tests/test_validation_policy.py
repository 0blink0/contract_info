from backend.app.validate.policy import (
    append_absence_notes,
    apply_validation_policy,
    soften_validation_items,
)
from backend.app.validate.schemas import ValidationItem


def test_optional_fail_softened_to_warn():
    items = [
        ValidationItem(
            field="业绩比较基准",
            status="fail",
            value="沪深300",
            reason="摘录中找不到该指数名称",
        )
    ]
    out = soften_validation_items(items, {"product_elements": {}})
    assert len(out) == 1
    assert out[0].status == "warn"
    assert "留空" in (out[0].suggestion or "")


def test_required_fail_stays_fail():
    items = [
        ValidationItem(
            field="管理人",
            status="fail",
            value="错误公司",
            reason="摘录中为另一主体",
        )
    ]
    out = apply_validation_policy(items, {"product_elements": {}})
    assert out[0].status == "fail"


def test_absence_note_for_empty_benchmark():
    extraction = {"product_elements": {}}
    items = append_absence_notes([], extraction)
    fields = {i.field for i in items}
    assert "业绩比较基准" in fields
    assert "风险收益特征" in fields
    bench = next(i for i in items if i.field == "业绩比较基准")
    assert bench.status == "warn"
    assert "留空" in bench.reason
