from __future__ import annotations

from backend.app.validate.optional_fields import (
    ABSENCE_NOTE_PRODUCT_FIELDS,
    is_optional_validation_field,
)
from backend.app.validate.schemas import ValidationItem

_ABSENCE_REASON = "合同未载明或未抽取到该项，导出留空即可（非必填）。"
_OPTIONAL_SUGGESTION = "非必填项；摘录不足或无法核对时导出留空，无需强行填写。"


def _field_value(elements: dict, name: str) -> str | None:
    raw = elements.get(name)
    if not isinstance(raw, dict):
        return None
    val = raw.get("value")
    if val is None or str(val).strip() == "":
        return None
    return str(val).strip()


def soften_validation_items(
    items: list[ValidationItem],
    extraction_result: dict,
) -> list[ValidationItem]:
    """非必填字段：校验 fail 降为 warn，避免阻塞导出；必填项保持 fail。"""
    out: list[ValidationItem] = []
    for item in items:
        if item.status == "fail" and is_optional_validation_field(item.field):
            out.append(
                item.model_copy(
                    update={
                        "status": "warn",
                        "suggestion": item.suggestion or _OPTIONAL_SUGGESTION,
                    }
                )
            )
        else:
            out.append(item)
    return out


def append_absence_notes(
    items: list[ValidationItem],
    extraction_result: dict,
) -> list[ValidationItem]:
    """对合同常无的列，未抽取时在 validation 中标记留空（非 error）。"""
    elements = extraction_result.get("product_elements") or {}
    if not isinstance(elements, dict):
        return items
    present = {i.field for i in items}
    extra: list[ValidationItem] = []
    for name in ABSENCE_NOTE_PRODUCT_FIELDS:
        if name in present:
            continue
        if _field_value(elements, name):
            continue
        extra.append(
            ValidationItem(
                field=name,
                status="warn",
                value=None,
                reason=_ABSENCE_REASON,
                suggestion=None,
            )
        )
    return items + extra


def apply_validation_policy(
    items: list[ValidationItem],
    extraction_result: dict,
) -> list[ValidationItem]:
    softened = soften_validation_items(items, extraction_result)
    return append_absence_notes(softened, extraction_result)
