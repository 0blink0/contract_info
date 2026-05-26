from __future__ import annotations

from backend.app.extract.rules.party_helpers import is_valid_party_name
from backend.app.extract.schemas import (
    ExtractionMeta,
    ExtractionResult,
    FeeRateRow,
    FieldValue,
)

_PARTY_FIELDS = frozenset({"管理人", "托管人", "投资顾问", "外包机构"})
_LONG_TEXT_FIELDS = frozenset(
    {"投资目标", "投资范围", "投资限制", "投资策略", "风险等级"}
)
_LINE_FIELDS = frozenset({"预警线", "止损线"})
_MIS_EXTRACT_MARKERS = (
    "保证",
    "登记为私募基金管理人",
    "若根据",
    "所涉风险",
    "经营风险",
    "技术系统",
)


def _confidence_rank(c: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(c, 0)


def is_invalid_rule_value(field_name: str, value: object) -> bool:
    if value is None or str(value).strip() == "":
        return True
    text = str(value).strip()
    if field_name in _PARTY_FIELDS:
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
    effective_rule = (
        None if is_invalid_rule_value(field_name, rule_val.value if rule_val else None) else rule_val
    )

    if field_name in _LINE_FIELDS and effective_rule and str(effective_rule.value).strip() == "无":
        return effective_rule

    if field_name in _LONG_TEXT_FIELDS and effective_rule and llm_val:
        rv = effective_rule.value
        lv = llm_val.value
        if rv not in (None, "") and lv not in (None, ""):
            if len(str(lv)) > len(str(rv)):
                return llm_val
            return effective_rule

    if field_name in _PARTY_FIELDS and effective_rule:
        return effective_rule

    if effective_rule and llm_val:
        if _confidence_rank(effective_rule.confidence) >= _confidence_rank(
            llm_val.confidence
        ):
            if effective_rule.value not in (None, ""):
                return effective_rule
        return llm_val if llm_val.value not in (None, "") else effective_rule
    return effective_rule or llm_val


def merge_extraction(
    product_rules: dict[str, FieldValue],
    llm_fields: dict[str, FieldValue],
    fee_rates: list[FeeRateRow],
    *,
    meta: ExtractionMeta,
    lock_periods: list | None = None,
    share_classes: list | None = None,
) -> ExtractionResult:
    merged: dict[str, FieldValue] = dict(product_rules)
    for key, llm_fv in llm_fields.items():
        merged[key] = (
            merge_field(merged.get(key), llm_fv, field_name=key) or llm_fv
        )
    return ExtractionResult(
        product_elements=merged,
        fee_rates=fee_rates,
        lock_periods=lock_periods or [],
        share_classes=share_classes or [],
        meta=meta,
    )
