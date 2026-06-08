from __future__ import annotations

from backend.app.extract.field_catalog import (
    ALL_PRODUCT_FIELDS,
    CORE_REQUIRED_PRODUCT,
    SKIP_PRODUCT_FIELDS,
)

# 合同常无专节；未抽取时在校验结果中提示「留空」即可
ABSENCE_NOTE_PRODUCT_FIELDS: frozenset[str] = frozenset(
    {
        "业绩比较基准",
        "风险收益特征",
        "投资顾问",
        "外包机构",
        "备案编码",
        "封闭期",
        "锁定期",
        "到期日期",
    }
)

OPTIONAL_PRODUCT_FIELDS: frozenset[str] = frozenset(
    f
    for f in ALL_PRODUCT_FIELDS
    if f not in CORE_REQUIRED_PRODUCT and f not in SKIP_PRODUCT_FIELDS
)


def is_optional_validation_field(field: str) -> bool:
    if field.startswith("path_b."):
        return True
    if field.startswith("fee_rates[") or field.startswith("subscription_fees["):
        return False
    return field in OPTIONAL_PRODUCT_FIELDS
