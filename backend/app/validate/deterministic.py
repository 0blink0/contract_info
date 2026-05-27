from __future__ import annotations

import re

from backend.app.validate.schemas import ValidationItem

_RE_NO_STOP_LINES = re.compile(
    r"不设置预警线[、,，\s]*止损线|预警线[、,，\s]*止损线.*不设置|未设预警.*止损",
    re.IGNORECASE,
)
_RE_FACE_VALUE = re.compile(r"初始募集面值[：:\s]*人民币\s*[\d.]+\s*元", re.IGNORECASE)


def _field_value(elements: dict, name: str) -> str | None:
    raw = elements.get(name)
    if not isinstance(raw, dict):
        return None
    val = raw.get("value")
    if val is None or str(val).strip() == "":
        return None
    return str(val).strip()


def _field_snippet(elements: dict, name: str) -> str:
    raw = elements.get(name)
    if not isinstance(raw, dict):
        return ""
    return str(raw.get("snippet") or "").strip()


def deterministic_validation_items(
    extraction_result: dict,
) -> dict[str, ValidationItem]:
    """Rule-based pass items that override flaky LLM validation for clear patterns."""
    elements = extraction_result.get("product_elements") or {}
    if not isinstance(elements, dict):
        return {}

    out: dict[str, ValidationItem] = {}

    warn_snip = _field_snippet(elements, "预警线")
    stop_snip = _field_snippet(elements, "止损线")
    combined_stop = f"{warn_snip}\n{stop_snip}"
    if _RE_NO_STOP_LINES.search(combined_stop):
        for field in ("预警线", "止损线"):
            val = _field_value(elements, field)
            if val == "无":
                out[field] = ValidationItem(
                    field=field,
                    status="pass",
                    value=val,
                    reason="摘录明确写明不设置预警线、止损线，抽取值「无」一致。",
                    suggestion=None,
                )

    face_val = _field_value(elements, "基金面值")
    face_snip = _field_snippet(elements, "基金面值")
    currency_snip = _field_snippet(elements, "币种")
    evidence = face_snip or currency_snip
    if face_val and _RE_FACE_VALUE.search(evidence):
        out["基金面值"] = ValidationItem(
            field="基金面值",
            status="pass",
            value=face_val,
            reason="摘录含初始募集面值（人民币），与抽取值一致。",
            suggestion=None,
        )
        currency = _field_value(elements, "币种")
        if currency and "人民币" in evidence:
            out["币种"] = ValidationItem(
                field="币种",
                status="pass",
                value=currency,
                reason="摘录初始募集面值为人民币，与币种一致。",
                suggestion=None,
            )

    add_val = _field_value(elements, "追加起点")
    add_snip = _field_snippet(elements, "追加起点")
    step_val = _field_value(elements, "最小变动单位")
    step_snip = _field_snippet(elements, "最小变动单位")
    if add_val == "无追加起点限制" and step_val and re.search(
        r"追加金额应不低于\s*1\s*万元", step_snip
    ):
        out["追加起点"] = ValidationItem(
            field="追加起点",
            status="pass",
            value=add_val,
            reason="合同对追加仅约定最低变动金额，运营表记为无追加起点限制。",
            suggestion=None,
        )
        out["最小变动单位"] = ValidationItem(
            field="最小变动单位",
            status="pass",
            value=step_val,
            reason="摘录写明追加金额不低于1万元，对应最小变动单位。",
            suggestion=None,
        )

    return out
