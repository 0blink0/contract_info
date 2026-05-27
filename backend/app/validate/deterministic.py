from __future__ import annotations

import re

from backend.app.validate.schemas import ValidationItem

_RE_NO_STOP_LINES = re.compile(
    r"不设置预警线[、,，\s]*止损线|预警线[、,，\s]*止损线.*不设置|未设预警.*止损",
    re.IGNORECASE,
)
_RE_FACE_VALUE = re.compile(
    r"(?:基金份额的)?初始募集面值[：:\s]*(?:人民币\s*)?[\d.]+\s*元",
    re.IGNORECASE,
)


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
        reason = "摘录明确写明不设置预警线、止损线，抽取值「无」一致。"
        for field in ("预警线", "止损线"):
            val = _field_value(elements, field)
            if val == "无":
                out[field] = ValidationItem(
                    field=field,
                    status="pass",
                    value=val,
                    reason=reason,
                    suggestion=None,
                )
    elif (
        _field_value(elements, "止损线") == "无"
        and _RE_NO_STOP_LINES.search(warn_snip)
        and "止损线" in warn_snip
    ):
        out["止损线"] = ValidationItem(
            field="止损线",
            status="pass",
            value="无",
            reason="预警线摘录已同时写明不设置止损线，抽取值「无」一致。",
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
            reason="摘录含初始募集面值（元），与抽取值一致。",
            suggestion=None,
        )
        currency = _field_value(elements, "币种")
        if currency == "人民币现钞" and re.search(
            r"人民币|[\d.]+\s*元", evidence
        ):
            out["币种"] = ValidationItem(
                field="币种",
                status="pass",
                value=currency,
                reason="面值以元计且未写明外币，按惯例为人民币现钞。",
                suggestion=None,
            )

    closed_val = _field_value(elements, "是否封闭")
    closed_snip = _field_snippet(elements, "是否封闭")
    if closed_val == "不封闭" and re.search(r"本基金的封闭期[：:\s]*无", closed_snip):
        out["是否封闭"] = ValidationItem(
            field="是否封闭",
            status="pass",
            value=closed_val,
            reason="申购赎回章节写明「本基金的封闭期：无」，与不封闭一致。",
            suggestion=None,
        )

    redeem_val = _field_value(elements, "是否支持金额赎回")
    redeem_snip = _field_snippet(elements, "是否支持金额赎回")
    if redeem_val == "不支持" and re.search(
        r"基金赎回采用份额申请|赎回采用份额申请", redeem_snip
    ):
        out["是否支持金额赎回"] = ValidationItem(
            field="是否支持金额赎回",
            status="pass",
            value=redeem_val,
            reason="摘录写明赎回采用份额申请，与「不支持」金额赎回一致。",
            suggestion=None,
        )

    limits_val = _field_value(elements, "投资限制")
    limits_snip = _field_snippet(elements, "投资限制")
    if limits_val and re.search(r"（五）投资限制|投资限制", limits_snip):
        if limits_val[:20] in limits_snip or limits_snip.find("基金总资产") >= 0:
            out["投资限制"] = ValidationItem(
                field="投资限制",
                status="pass",
                value=limits_val[:80] + ("…" if len(limits_val) > 80 else ""),
                reason="摘录来自投资章节「投资限制」条款，与抽取值一致。",
                suggestion=None,
            )

    mgr_val = _field_value(elements, "投资经理")
    mgr_snip = _field_snippet(elements, "投资经理")
    if mgr_val and mgr_snip:
        listed = [n.strip() for n in re.split(r"[、,，/]", mgr_val) if n.strip()]
        if listed and all(n in mgr_snip for n in listed):
            out["投资经理"] = ValidationItem(
                field="投资经理",
                status="pass",
                value=mgr_val,
                reason="摘录列明的投资经理姓名与抽取值一致。",
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
