from __future__ import annotations

from backend.app.extract.schemas import (
    ExtractionMeta,
    ExtractionResult,
    FeeRateRow,
    FieldValue,
)


def _confidence_rank(c: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(c, 0)


def merge_field(
    rule_val: FieldValue | None,
    llm_val: FieldValue | None,
) -> FieldValue | None:
    if rule_val and llm_val:
        if _confidence_rank(rule_val.confidence) >= _confidence_rank(llm_val.confidence):
            if rule_val.value not in (None, ""):
                return rule_val
        return llm_val if llm_val.value not in (None, "") else rule_val
    return rule_val or llm_val


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
        merged[key] = merge_field(merged.get(key), llm_fv) or llm_fv
    return ExtractionResult(
        product_elements=merged,
        fee_rates=fee_rates,
        lock_periods=lock_periods or [],
        share_classes=share_classes or [],
        meta=meta,
    )
