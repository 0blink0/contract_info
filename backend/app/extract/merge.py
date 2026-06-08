"""Legacy merge helpers — extraction is LLM-only; kept for tests and party validation."""

from __future__ import annotations

from backend.app.extract.field_catalog import SKIP_PRODUCT_FIELDS
from backend.app.extract.party_helpers import is_valid_party_name
from backend.app.extract.schemas import (
    ExtractionMeta,
    ExtractionResult,
    FeeRateRow,
    FieldValue,
    SubscriptionFeeRow,
)

_MIS_EXTRACT_MARKERS = (
    "保证",
    "登记为私募基金管理人",
    "若根据",
    "所涉风险",
    "经营风险",
    "技术系统",
)


def is_invalid_field_value(field_name: str, value: object) -> bool:
    if value is None or str(value).strip() == "":
        return True
    text = str(value).strip()
    if field_name in frozenset({"管理人", "托管人", "投资顾问", "外包机构"}):
        return not is_valid_party_name(text)
    if any(marker in text for marker in _MIS_EXTRACT_MARKERS):
        return True
    return False


def merge_field(
    rule_val: FieldValue | None,
    llm_val: FieldValue | None,
    *,
    field_name: str = "",
) -> FieldValue | None:
    """Prefer LLM; ignore invalid values."""
    if llm_val and llm_val.value not in (None, "") and not is_invalid_field_value(
        field_name, llm_val.value
    ):
        return llm_val
    if rule_val and rule_val.value not in (None, "") and not is_invalid_field_value(
        field_name, rule_val.value
    ):
        return rule_val
    return llm_val or rule_val


def merge_extraction(
    product_rules: dict[str, FieldValue],
    llm_fields: dict[str, FieldValue],
    fee_rates: list[FeeRateRow],
    *,
    meta: ExtractionMeta,
    lock_periods: list | None = None,
    share_classes: list | None = None,
    subscription_fees: list[SubscriptionFeeRow] | None = None,
) -> ExtractionResult:
    merged: dict[str, FieldValue] = dict(llm_fields)
    for key, rule_fv in product_rules.items():
        if key not in merged:
            merged[key] = rule_fv
        else:
            merged[key] = merge_field(rule_fv, merged.get(key), field_name=key) or merged[key]
    for key in SKIP_PRODUCT_FIELDS:
        merged.pop(key, None)

    return ExtractionResult(
        product_elements=merged,
        fee_rates=fee_rates,
        lock_periods=lock_periods or [],
        share_classes=share_classes or [],
        subscription_fees=subscription_fees or [],
        meta=meta,
    )
